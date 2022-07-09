#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#

import argparse as _argparse
import json as _json
import proton as _proton
import proton.reactor as _reactor
import sys as _sys

from .common import *

_description = """
Send AMQP requests.  Use qrequest in combination with the qrespond
command to transfer requests through an AMQP message server.
"""

_epilog = """
Example usage:
  $ qrequest amqps://example.net/queue1 message1  # Send one request
  $ qrequest jobs message1 message2 message3      # Send three requests
  $ qrequest jobs < requests.txt                  # Send requests from a file
  $ qrequest jobs                                 # Send requests from the console
"""

class RequestCommand(MessagingCommand):
    def __init__(self):
        super().__init__("qrequest", _Handler(self))

        self.parser.description = _description + suite_description
        self.parser.epilog = url_epilog + message_epilog + _epilog

        self.parser.add_argument("url", metavar="URL",
                                 help="The location of a message source or target")
        self.parser.add_argument("message", metavar="MESSAGE", nargs="*",
                                 help="The content of a request message")
        self.parser.add_argument("-m", "--message", metavar="CONTENT",
                                 action="append", default=list(), dest="message_compat",
                                 help=_argparse.SUPPRESS)
        self.parser.add_argument("--input", metavar="FILE",
                                 help="Read request messages from FILE, one per line (default stdin)")
        self.parser.add_argument("--output", metavar="FILE",
                                 help="Write response messages to FILE (default stdout)")
        self.parser.add_argument("--json", action="store_true",
                                 help="Write messages in JSON format")

    def init(self, args):
        super().init(args)

        self.scheme, self.host, self.port, self.address = self.parse_url(args.url)

        self.json_enabled = args.json

        if args.input is not None:
            self.input_file = open(args.input, "r")

        if args.output is not None:
            self.output_file = open(args.output, "w")

        if args.message or args.message_compat:
            for value in args.message:
                self.input_thread.push_line(value)

            for value in args.message_compat:
                self.input_thread.push_line(value)

            self.input_thread.push_line("")

    def run(self):
        self.input_thread.start()
        self.output_thread.start()

        try:
            super().run()
        finally:
            self.output_thread.stop()
            self.output_thread.join()

class _Handler(MessagingHandler):
    def __init__(self, command):
        super().__init__(command)

        self.sender = None
        self.receiver = None

        self.current_request_id = 0
        self.pending_request_ids = set()

        self.sent_requests = 0
        self.received_responses = 0

    def open(self, event):
        super().open(event)

        self.sender = event.container.create_sender(self.connection, self.command.address)
        self.receiver = event.container.create_receiver(self.connection, None, dynamic=True, name="responses")

    def close(self, event):
        super().close(event)

        self.command.notice("Sent {} {} and received {} {}", self.sent_requests, plural("request", self.sent_requests),
                            self.received_responses, plural("response", self.received_responses))

    def on_input(self, event):
        self.send_message(event)

    def on_sendable(self, event):
        self.send_message(event)

    def send_message(self, event):
        if not self.command.ready.is_set():
            return

        if self.done_sending:
            return

        if not self.sender.credit:
            return

        try:
            line = self.command.input_thread.lines.pop()
        except IndexError:
            return

        if line == "":
            self.done_sending = True

            if self.sent_requests == self.received_responses:
                self.close(event)

            return

        message = process_input_line(line)
        message.reply_to = self.receiver.remote_source.address

        if message.id is None:
            self.current_request_id += 1
            message.id = self.current_request_id

        delivery = self.sender.send(message)

        self.sent_requests += 1
        self.pending_request_ids.add(message.id)

        self.command.info("Sent request {} as {} to {} on {}", message, delivery, self.sender.target,
                          self.sender.connection)

    def on_message(self, event):
        assert event.message.correlation_id in self.pending_request_ids, \
            (event.message.correlation_id, self.pending_request_ids)

        if self.command.json_enabled:
            data = convert_message_to_data(event.message)
            line = _json.dumps(data)
        else:
            line = event.message.body

        self.command.output_thread.push_line(line)

        self.command.info("Received response {} from {} on {}", event.message, event.link.source, event.connection)

        self.received_responses += 1
        self.pending_request_ids.remove(event.message.correlation_id)

        if self.done_sending and self.sent_requests == self.received_responses:
            self.close(event)

def main():
    RequestCommand().main()
