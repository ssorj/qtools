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
import proton as _proton
import proton.reactor as _reactor
import sys as _sys

from .common import *

_description = "Send AMQP requests"

_epilog = """
example usage:
  $ qrequest //example.net/queue0 -m abc -m xyz
  $ qrequest queue0 queue1 < requests.txt
"""

class RequestCommand(Command):
    def __init__(self, home_dir):
        super(RequestCommand, self).__init__(home_dir)

        self.parser.description = _description
        self.parser.epilog = url_epilog + _epilog

        self.add_link_arguments()

        self.parser.add_argument("-m", "--message", metavar="CONTENT",
                                 action="append", default=list(),
                                 help="Send a request message containing CONTENT.  This option can be repeated.")
        self.parser.add_argument("-i", "--input", metavar="FILE",
                                 help="Read request messages from FILE, one per line (default stdin)")
        self.parser.add_argument("-o", "--output", metavar="FILE",
                                 help="Write response messages to FILE (default stdout)")
        self.parser.add_argument("--presettled", action="store_true",
                                 help="Send messages with at-most-once reliability")

        self.add_container_arguments()
        self.add_common_arguments()

        self.container.handler = _Handler(self)

        self.messages = _collections.deque()
        self.input_thread = InputThread(self)

    def init(self):
        super(RequestCommand, self).init()

        self.init_link_attributes()
        self.init_container_attributes()
        self.init_common_attributes()

        self.input_file = _sys.stdin
        self.output_file = _sys.stdout
        self.presettled = self.args.presettled

        if self.args.input is not None:
            self.input_file = open(self.args.input, "r")

        if self.args.output is not None:
            self.output_file = open(self.args.output, "w")

        for value in self.args.message:
            message = _proton.Message(unicode(value))
            self.send_input(message)

        if self.messages:
            self.send_input(None)

    def send_input(self, message):
        self.messages.appendleft(message)
        self.events.trigger(_reactor.ApplicationEvent("input"))

    def run(self):
        self.input_thread.start()

        super(RequestCommand, self).run()

class _Handler(LinkHandler):
    def __init__(self, command):
        super(_Handler, self).__init__(command)

        self.senders = _collections.deque()
        self.receivers_by_sender = dict()

        self.sent_requests = 0
        self.received_responses = 0
        self.stop_requested = False

    def open_links(self, event, connection, address):
        options = None

        if self.command.presettled:
            options = _reactor.AtMostOnce()

        sender = event.container.create_sender(connection, address, options=options)
        receiver = event.container.create_receiver(connection, None, dynamic=True)

        self.senders.appendleft(sender)
        self.receivers_by_sender[sender] = receiver

        return sender, receiver

    def on_sendable(self, event):
        self.send_request(event)

    def on_input(self, event):
        self.send_request(event)

    def on_message(self, event):
        self.received_responses += 1

        self.command.output_file.write(event.message.body)
        self.command.output_file.write("\n")

        self.command.info("Received response '{}' from '{}' on '{}'",
                          event.message.body,
                          event.link.source.address,
                          event.connection.remote_container)

        if self.stop_requested and self.sent_requests == self.received_responses:
            self.command.output_file.flush()
            self.close()

    def send_request(self, event):
        if self.stop_requested:
            return

        if not self.command.ready.is_set():
            return

        try:
            message = self.command.messages.pop()
        except IndexError:
            return

        if message is None:
            if self.sent_requests == self.received_responses:
                self.close()
            else:
                self.stop_requested = True

            return

        sender = event.link

        if sender is None:
            sender = self.senders.pop()
            self.senders.appendleft(sender)

        if not sender.credit:
            self.command.messages.append(message)
            return

        receiver = self.receivers_by_sender[sender]
        message.reply_to = receiver.remote_source.address

        if message.address is None:
            message.address = sender.target.address

        delivery = sender.send(message)

        self.sent_requests += 1

        self.command.info("Sent request '{}' as delivery '{}' to '{}' on '{}'",
                          message.body,
                          delivery.tag,
                          sender.target.address,
                          sender.connection.remote_container)
