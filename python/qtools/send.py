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

class SendCommand(MessagingCommand):
    def __init__(self, home_dir):
        super(SendCommand, self).__init__(home_dir, "qsend", _Handler(self))

        self.description = _description
        self.epilog = url_epilog + _epilog

        self.add_link_arguments()

        self.add_argument("-m", "--message", metavar="CONTENT",
                          action="append", default=list(),
                          help="Send a message containing CONTENT.  This option can be repeated.")
        self.add_argument("--input", metavar="FILE",
                          help="Read messages from FILE, one per line (default stdin)")
        self.add_argument("--presettled", action="store_true",
                          help="Send messages fire-and-forget (at-most-once delivery)")

    def init(self):
        super(SendCommand, self).init()

        self.init_link_attributes()

        self.presettled = self.args.presettled

        if self.args.input is not None:
            self.input_file = open(self.args.input, "r")

        if self.args.message:
            for value in self.args.message:
                self.input_thread.push_line(unicode(value))

            self.input_thread.push_line(DONE)

    def run(self):
        self.input_thread.start()
        super(SendCommand, self).run()

class _Handler(LinkHandler):
    def __init__(self, command):
        super(_Handler, self).__init__(command)

        self.senders = _collections.deque()

        self.sent_messages = 0
        self.settled_messages = 0

    def open_links(self, event, connection, address):
        options = None

        if self.command.presettled:
            options = _reactor.AtMostOnce()

        sender = event.container.create_sender(connection, address, options=options)

        self.senders.appendleft(sender)

        return sender,

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

            if self.command.presettled:
                self.close(event)

            if self.sent_messages == self.settled_messages:
                self.close(event)

            return

        message = process_input_line(line)

        if message.address is None:
            message.address = sender.target.address

        delivery = sender.send(message)

        self.sent_messages += 1

        self.command.info("Sent {} as {} to {} on {}",
                          message,
                          delivery,
                          sender.target,
                          sender.connection)

    def on_settled(self, event):
        super(_Handler, self).on_settled(event)

        self.settled_messages += 1

        if self.done_sending and self.sent_messages == self.settled_messages:
            self.close(event)

    def close(self, event):
        super(_Handler, self).close(event)

        self.command.notice("Sent {} {}",
                            self.sent_messages,
                            plural("message", self.sent_messages))
