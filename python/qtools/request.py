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

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import with_statement

import collections as _collections
import json as _json
import proton as _proton
import proton.reactor as _reactor
import sys as _sys

from .common import *

_description = "Send AMQP requests"

_epilog = """
example usage:
  $ qrequest //example.net/queue0 -m abc -m xyz
  $ qrequest queue0 queue1 < messages.txt
"""

class RequestCommand(MessagingCommand):
    def __init__(self, home_dir):
        super(RequestCommand, self).__init__(home_dir, "qrequest", _Handler(self))

        self.description = _description
        self.epilog = url_epilog + _epilog

        self.add_link_arguments()

        self.add_argument("-m", "--message", metavar="CONTENT",
                          action="append", default=list(),
                          help="Send a request message containing CONTENT.  This option can be repeated.")
        self.add_argument("--input", metavar="FILE",
                          help="Read request messages from FILE, one per line (default stdin)")
        self.add_argument("--output", metavar="FILE",
                          help="Write response messages to FILE (default stdout)")
        self.add_argument("--json", action="store_true",
                          help="Write messages in JSON format")
        self.add_argument("--no-prefix", action="store_true",
                          help="Suppress address prefix")
        self.add_argument("--presettled", action="store_true",
                          help="Send messages fire-and-forget (at-most-once delivery)")

    def init(self):
        super(RequestCommand, self).init()

        self.init_link_attributes()

        self.json_enabled = self.args.json
        self.prefix_disabled = self.args.no_prefix
        self.presettled = self.args.presettled

        if self.args.input is not None:
            self.input_file = open(self.args.input, "r")

        if self.args.output is not None:
            self.output_file = open(self.args.output, "w")

        if self.args.message:
            for value in self.args.message:
                self.input_thread.push_line(unicode(value))

            self.input_thread.push_line(DONE)

    def run(self):
        self.input_thread.start()
        self.output_thread.start()

        super(RequestCommand, self).run()

class _Handler(LinkHandler):
    def __init__(self, command):
        super(_Handler, self).__init__(command)

        self.senders = _collections.deque()
        self.receivers_by_sender = dict()
        self.senders_by_receiver = dict()

        self.sent_requests = 0
        self.received_responses = 0

    def open_links(self, event, connection, address):
        options = None

        if self.command.presettled:
            options = _reactor.AtMostOnce()

        sender = event.container.create_sender(connection, address, options=options)
        receiver = event.container.create_receiver(connection, None, dynamic=True)

        self.senders.appendleft(sender)
        self.receivers_by_sender[sender] = receiver
        self.senders_by_receiver[receiver] = sender

        return sender, receiver

    def on_input(self, event):
        self.send_message(event)

    def on_sendable(self, event):
        self.send_message(event)

    def send_message(self, event):
        if not self.command.ready.is_set():
            return

        if self.done_sending:
            return

        sender = event.link

        if sender is None:
            sender = self.senders.pop()
            self.senders.appendleft(sender)

        if not sender.credit:
            return

        try:
            line = self.command.input_thread.lines.pop()
        except IndexError:
            return

        if line is DONE:
            self.done_sending = True

            if self.sent_requests == self.received_responses:
                self.close(event)

            return

        receiver = self.receivers_by_sender[sender]

        message = process_input_line(line)
        message.reply_to = receiver.remote_source.address

        if message.address is None:
            message.address = sender.target.address

        if message.id is None:
            message.id = unique_id()

        delivery = sender.send(message)

        self.sent_requests += 1

        self.command.info("Sent request {} as {} to {} on {}",
                          message,
                          delivery,
                          sender.target,
                          sender.connection)

    def on_message(self, event):
        if self.done_receiving:
            return

        message = event.message

        self.received_responses += 1

        out = list()

        if not self.command.prefix_disabled:
            sender = self.senders_by_receiver[event.link]
            prefix = sender.target.address + ": "
            out.append(prefix)

        if self.command.json_enabled:
            data = convert_message_to_data(message)
            json = _json.dumps(data)
            out.append(json)
        else:
            out.append(message.body)

        self.command.output_thread.push_line("".join(out))

        self.command.info("Received response {} from {} on {}",
                          event.message,
                          event.link.source,
                          event.connection)

        if self.done_sending and self.sent_requests == self.received_responses:
            self.command.output_thread.push_line(DONE)
            self.done_receiving = True
            self.close(event)

    def close(self, event):
        super(_Handler, self).close(event)

        self.command.notice("Sent {} {} and received {} {}",
                            self.sent_requests,
                            plural("request", self.sent_requests),
                            self.received_responses,
                            plural("response", self.received_responses))
