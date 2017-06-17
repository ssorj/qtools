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

        self.parser.add_argument("url", metavar="ADDRESS-URL", nargs="+",
                                 help="The location of a message target")
        self.parser.add_argument("-m", "--message", metavar="MESSAGE",
                                 action="append", default=list(),
                                 help="A string containing message content")
        self.parser.add_argument("--prompt", action="store_true",
                                 help="Prompt for messages on the console")

        self.add_common_arguments()

        handler = _SendHandler(self)

        self.container = _reactor.Container(handler)
        self.events = _reactor.EventInjector()
        self.messages = _collections.deque()
        self.ready = _threading.Event()
        self.console_input_thread = _ConsoleInputThread(self)

        self.container.selectable(self.events)

    def init(self):
        super(SendCommand, self).init()

        self.init_common_attributes()

        self.urls = self.args.url
        self.prompt = self.args.prompt

        for value in self.args.message:
            message = _proton.Message(unicode(value))
            self.messages.appendleft(message)

        if self.prompt:
            self.quiet = True
        else:
            if not self.messages:
                self.parser.error("No message. Use --prompt or --message.")

            self.messages.appendleft(None)

    def run(self):
        self.console_input_thread.start()
        self.container.run()

class _ConsoleInputThread(_threading.Thread):
    def __init__(self, command):
        _threading.Thread.__init__(self)

        self.command = command
        self.daemon = True

    def run(self):
        print("Connecting...")

        self.command.ready.wait()

        print("Ready. Type Ctrl-D to exit.")

        while True:
            try:
                body = raw_input("> ")
            except EOFError:
                self.send_input(None)
                print()
                break

            message = _proton.Message(unicode(body))
            self.send_input(message)

    def send_input(self, message):
        self.command.messages.appendleft(message)
        self.command.events.trigger(_reactor.ApplicationEvent("input"))

class _SendHandler(_handlers.MessagingHandler):
    def __init__(self, command):
        super(_SendHandler, self).__init__()

        self.command = command
        self.connections = set()
        self.senders = _collections.deque()
        self.stop_requested = False

    def on_start(self, event):
        for url in self.command.urls:
            host, port, path = parse_address_url(url)
            domain = "{}:{}".format(host, port)

            connection = event.container.connect(domain, allowed_mechs=b"ANONYMOUS")
            sender = event.container.create_sender(connection, path)

            self.connections.add(connection)
            self.senders.appendleft(sender)

    def on_connection_opened(self, event):
        assert event.connection in self.connections

        # XXX Connected to what?  Transport doesn't have what I need.
        self.command.notice("Connected")

    def on_link_opened(self, event):
        assert event.link in self.senders

        self.command.notice("Created sender for target address '{}'", event.link.target.address)

        if self.command.prompt and len(self.senders) == len(self.command.urls):
            self.command.ready.set()

    def on_sendable(self, event):
        self.send_message(event)

    def on_input(self, event):
        self.send_message(event)

    def on_accepted(self, event):
        if self.stop_requested:
            self.close()

    def send_message(self, event):
        if self.stop_requested:
            return

        try:
            message = self.command.messages.pop()
        except IndexError:
            return

        sender = event.link

        if sender is None:
            sender = self.senders.pop()
            self.senders.appendleft(sender)

        if message is None:
            if sender.unsettled == 0:
                self.close()
            else:
                self.stop_requested = True

            return

        if not sender.credit:
            self.command.messages.append(message)
            return

        sender.send(message)

        self.command.notice("Sent message '{}' to '{}'", message.body, sender.target.address)

    def close(self):
        for connection in self.connections:
            connection.close()

        self.command.events.close()
