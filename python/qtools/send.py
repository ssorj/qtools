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
import proton.handlers as _handlers
import proton.reactor as _reactor
import threading as _threading

from .common import *

_description = "Send AMQP messages"

class SendCommand(Command):
    def __init__(self, home_dir):
        super(SendCommand, self).__init__(home_dir)

        self.parser.description = _description

        self.parser.add_argument("url", metavar="ADDRESS-URL",
                                 help="The location of a queue or topic")
        self.parser.add_argument("message", metavar="MESSAGE", nargs="*",
                                 help="The message content")
        self.parser.add_argument("--prompt", action="store_true",
                                 help="Prompt for messages on the console")

        self.add_common_arguments()

        handler = _SendHandler(self)

        self.container = _reactor.Container(handler)
        self.events = _reactor.EventInjector()
        self.messages = _collections.deque()
        self.console_input_thread = _ConsoleInputThread(self)

    def init(self):
        super(SendCommand, self).init()

        self.init_common_attributes()

        self.url = self.args.url
        self.command_line_messages = self.args.message
        self.prompt = self.args.prompt

        for message in self.command_line_messages:
            pmessage = _proton.Message(unicode(message))
            self.messages.appendleft(pmessage)

        if not self.prompt:
            self.messages.appendleft(None)

    def run(self):
        self.container.run()

class _ConsoleInputThread(_threading.Thread):
    def __init__(self, command):
        _threading.Thread.__init__(self)

        self.command = command
        self.daemon = True

    def run(self):
        while True:
            try:
                body = raw_input("> ")
            except EOFError:
                self.command.messages.appendleft(None)
                self.command.events.trigger(_reactor.ApplicationEvent("input"))
                print()

                break

            message = _proton.Message(unicode(body))

            self.command.messages.appendleft(message)
            self.command.events.trigger(_reactor.ApplicationEvent("input"))

class _SendHandler(_handlers.MessagingHandler):
    def __init__(self, command):
        super(_SendHandler, self).__init__()

        self.command = command
        self.connection = None
        self.sender = None
        self.stop_requested = False

    def on_start(self, event):
        host, port, path = parse_address_url(self.command.url)
        domain = "{}:{}".format(host, port)

        self.connection = event.container.connect(domain, allowed_mechs=b"ANONYMOUS")
        self.sender = event.container.create_sender(self.connection, path)

    def on_connection_opened(self, event):
        # XXX "is" checks fail here
        assert event.connection == self.connection

        # XXX Connected to what?  Transport doesn't have what I need.
        self.command.notice("Connected")

    def on_link_opened(self, event):
        # XXX "is" checks fail here
        assert event.link == self.sender

        self.command.notice("Created sender for target address '{}'", event.link.target.address)

        if self.command.prompt:
            self.command.container.selectable(self.command.events)
            self.command.console_input_thread.start()

    def on_sendable(self, event):
        self.send_message()

    def on_input(self, event):
        self.send_message()

    def on_accepted(self, event):
        if self.stop_requested:
            self.close()

    def send_message(self):
        if self.stop_requested:
            return

        try:
            message = self.command.messages.pop()
        except IndexError:
            return

        if message is None:
            if self.sender.unsettled == 0:
                self.close()
            else:
                self.stop_requested = True

            return

        if not self.sender.credit:
            self.command.messages.append(message)
            return

        self.sender.send(message)

        if not self.command.prompt:
            self.command.notice("Sent message '{}'", message.body)

    def close(self):
        self.connection.close()
        self.command.events.close()
