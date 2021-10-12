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
import proton as _proton
import proton.reactor as _reactor
import sys as _sys

from .common import *

_description = """
Send AMQP messages.  Use qsend in combination with the qreceive
command to transfer messages through an AMQP message server.
"""

_epilog = """
Example usage:
  $ qsend amqps://example.net/queue1 message1  # Send one message
  $ qsend jobs message1 message2 message3      # Send three messages
  $ qsend jobs < messages.txt                  # Send messages from a file
  $ qsend jobs                                 # Send messages from the console
"""

class SendCommand(MessagingCommand):
    def __init__(self, home_dir):
        super().__init__(home_dir, "qsend", _Handler(self))

        self.parser.description = _description + suite_description
        self.parser.epilog = url_epilog + message_epilog + _epilog

        self.parser.add_argument("url", metavar="URL",
                                 help="The location of a message source or target")
        self.parser.add_argument("message", metavar="MESSAGE", nargs="*",
                                 help="The content of a message")
        self.parser.add_argument("-m", "--message", metavar="CONTENT",
                                 action="append", default=list(), dest="message_compat",
                                 help=_argparse.SUPPRESS)
        self.parser.add_argument("--input", metavar="FILE",
                                 help="Read messages from FILE, one per line (default stdin)")

        self.messaging_options.add_argument("--presettled", action="store_true",
                                            help="Send messages fire-and-forget (at-most-once delivery)")

    def init(self, args):
        super().init(args)

        self.scheme, self.host, self.port, self.address = self.parse_url(args.url)

        self.presettled = args.presettled

        if args.input is not None:
            self.input_file = open(args.input, "r")

        if args.message or args.message_compat:
            for value in args.message:
                self.input_thread.push_line(value)

            for value in args.message_compat:
                self.input_thread.push_line(value)

            self.input_thread.push_line(DONE)

    def run(self):
        self.input_thread.start()

        super().run()

class _Handler(MessagingHandler):
    def __init__(self, command):
        super().__init__(command)

        self.sender = None
        self.sent_messages = 0
        self.settled_messages = 0

    def open(self, event):
        super().open(event)

        options = None

        if self.command.presettled:
            options = _reactor.AtMostOnce()

        self.sender = event.container.create_sender(self.connection, self.command.address, options=options)

    def close(self, event):
        super().close(event)

        self.command.notice("Sent {} {}", self.sent_messages, plural("message", self.sent_messages))

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

        if line is DONE:
            self.done_sending = True

            if self.command.presettled:
                self.close(event)

            if self.sent_messages == self.settled_messages:
                self.close(event)

            return

        message = process_input_line(line)
        delivery = self.sender.send(message)

        self.sent_messages += 1

        self.command.info("Sent {} as {} to {} on {}", message, delivery, self.sender.target, self.sender.connection)

    def on_settled(self, event):
        super().on_settled(event)

        self.settled_messages += 1

        if self.done_sending and self.sent_messages == self.settled_messages:
            self.close(event)
