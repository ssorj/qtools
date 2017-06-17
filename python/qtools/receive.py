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

import proton as _proton
import proton.handlers as _handlers
import proton.reactor as _reactor

from .common import *

_description = "Receive AMQP messages"

class ReceiveCommand(Command):
    def __init__(self, home_dir):
        super(ReceiveCommand, self).__init__(home_dir)

        self.parser.description = _description

        self.parser.add_argument("url", metavar="ADDRESS-URL",
                                 help="The location of a queue or topic")
        self.parser.add_argument("-m", "--messages", metavar="COUNT",
                                 type=int, default=1)
        self.parser.add_argument("--forever", action="store_true")

        self.add_common_arguments()

    def init(self):
        super(ReceiveCommand, self).init()

        self.url = self.args.url
        self.messages = self.args.messages

        self.init_common_attributes()

    def run(self):
        handler = _ReceiveHandler(self)
        container = _reactor.Container(handler)

        container.run()

class _ReceiveHandler(_handlers.MessagingHandler):
    def __init__(self, command):
        super(_ReceiveHandler, self).__init__()

        self.command = command
        self.connection = None
        self.receiver = None
        self.count = 0

    def on_start(self, event):
        host, port, path = parse_address_url(self.command.url)
        domain = "{}:{}".format(host, port)

        self.connection = event.container.connect(domain, allowed_mechs=b"ANONYMOUS")
        self.receiver = event.container.create_receiver(self.connection, path)

    def on_connection_opened(self, event):
        # XXX "is" checks fail here
        assert event.connection == self.connection

        # XXX Connected to what?  Transport doesn't have what I need.
        self.command.notice("Connected")

    def on_link_opened(self, event):
        # XXX "is" checks fail here
        assert event.link == self.sender

        self.command.notice("Created receiver for source address '{}'", event.link.source.address)

    def on_message(self, event):
        if self.count == self.command.messages:
            return

        if self.command.verbose:
            self.command.notice("Received message '{}'", event.message.body)

        print(event.message.body)

        self.count += 1

        if self.count == self.command.messages:
            event.connection.close()
