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
import threading as _threading

from .common import *

_description = "Send AMQP messages"

_epilog = """
example usage:
  $ qsend //example.net/queue0 -m abc -m xyz
  $ qsend queue0 queue1 < messages.txt
"""

class SendCommand(Command):
    def __init__(self, home_dir):
        super(SendCommand, self).__init__(home_dir)

        self.parser.description = _description
        self.parser.epilog = url_epilog + _epilog

        self.add_link_arguments()

        self.parser.add_argument("-m", "--message", metavar="CONTENT",
                                 action="append", default=list(),
                                 help="Send a message containing CONTENT.  This option can be repeated.")
        self.parser.add_argument("-i", "--input", metavar="FILE",
                                 help="Read messages from FILE, one per line (default stdin)")

        self.add_container_arguments()
        self.add_common_arguments()

        self.container.handler = _Handler(self)

        self.messages = _collections.deque()
        self.input_thread = InputThread(self)

    def init(self):
        super(SendCommand, self).init()

        self.init_link_attributes()
        self.init_container_attributes()
        self.init_common_attributes()

        self.input_file = _sys.stdin

        if self.args.input is not None:
            self.input_file = open(self.args.input, "r")

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

        super(SendCommand, self).run()

class _Handler(LinkHandler):
    def __init__(self, command):
        super(_Handler, self).__init__(command)

        self.senders = _collections.deque()

        self.sent_messages = 0
        self.settled_messages = 0
        self.stop_requested = False

    def open_links(self, event, connection, address):
        sender = event.container.create_sender(connection, address)

        self.senders.appendleft(sender)

        return sender,

    def on_sendable(self, event):
        self.send_message(event)

    def on_input(self, event):
        self.send_message(event)

    def on_settled(self, event):
        self.settled_messages += 1

        if self.command.verbose:
            self.command.notice("Settled delivery '{}' to '{}'",
                                event.delivery.tag, event.link.target.address)

        if self.stop_requested and self.sent_messages == self.settled_messages:
            self.close()

    def send_message(self, event):
        if self.stop_requested:
            return

        if not self.command.ready.is_set():
            return

        try:
            message = self.command.messages.pop()
        except IndexError:
            return

        if message is None:
            if self.sent_messages == self.settled_messages:
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

        if message.address is None:
            message.address = sender.target.address

        delivery = sender.send(message)

        self.sent_messages += 1

        if self.command.verbose:
            self.command.notice("Sent message '{}' as delivery '{}' to '{}' on '{}'",
                                message.body,
                                delivery.tag,
                                sender.target.address,
                                sender.connection.remote_container)
