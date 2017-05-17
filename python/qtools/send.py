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

_description = "Send an AMQP message"

class SendCommand(Command):
    def __init__(self, home_dir):
        super(SendCommand, self).__init__(home_dir)

        self.parser.description = _description

        self.parser.add_argument("address", metavar="ADDRESS-URL")
        self.parser.add_argument("body", metavar="MESSAGE-BODY", nargs="?")

        self.add_common_arguments()

    def init(self):
        super(SendCommand, self).init()

        self.address = self.args.address
        self.body = self.args.body

        self.init_common_attributes()

    def run(self):
        handler = _SendHandler(self)
        container = _reactor.Container(handler)

        container.run()

class _SendHandler(_handlers.MessagingHandler):
    def __init__(self, command):
        super(_SendHandler, self).__init__()

        self.command = command

        self.sent = False

    def on_start(self, event):
        host, port, path = parse_address_url(self.command.address)
        domain = "{}:{}".format(host, port)

        conn = event.container.connect(domain, allowed_mechs=b"ANONYMOUS")
        event.container.create_sender(conn, path)

        self.command.notice("Created sender for target address '{}'", path)

    def on_sendable(self, event):
        if self.sent:
            return

        message = _proton.Message(self.command.body)
        event.sender.send(message)

        self.command.notice("Sent message '{}'", self.command.body)

        self.sent = True

    def on_accepted(self, event):
        event.connection.close()
