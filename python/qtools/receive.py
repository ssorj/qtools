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

        self.parser.add_argument("url", metavar="ADDRESS-URL", nargs="+",
                                 help="The location of a message source")
        self.parser.add_argument("-m", "--messages", metavar="COUNT",
                                 type=int, default=0,
                                 help="Receive COUNT messages; 0 means no limit")

        self.add_common_arguments()

        handler = _ReceiveHandler(self)

        self.container = _reactor.Container(handler)

    def init(self):
        super(ReceiveCommand, self).init()

        self.init_common_attributes()

        self.urls = self.args.url
        self.max_messages = self.args.messages

        self.container.container_id = self.id

    def run(self):
        self.container.run()

class _ReceiveHandler(_handlers.MessagingHandler):
    def __init__(self, command):
        super(_ReceiveHandler, self).__init__()

        self.command = command
        self.connections = set()
        self.receivers = set()
        self.count = 0

    def on_start(self, event):
        for url in self.command.urls:
            host, port, path = parse_address_url(url)
            domain = "{}:{}".format(host, port)

            connection = event.container.connect(domain, allowed_mechs=b"ANONYMOUS")
            receiver = event.container.create_receiver(connection, path)

            self.connections.add(connection)
            self.receivers.add(receiver)

    def on_connection_opened(self, event):
        assert event.connection in self.connections

        self.command.notice("Connected to container '{}'", event.connection.remote_container)

    def on_link_opened(self, event):
        assert event.link in self.receivers

        self.command.notice("Created receiver for source address '{}' on container '{}'",
                            event.link.source.address,
                            event.connection.remote_container)

    def on_message(self, event):
        self.count += 1

        if self.count == self.command.max_messages:
            return

        print(event.message.body)

        if self.command.verbose:
            self.command.notice("Received message '{}' from '{}' on '{}'",
                                event.message.body,
                                event.link.source.address,
                                event.connection.remote_container)

        if self.count == self.command.max_messages:
            self.connection.close()
