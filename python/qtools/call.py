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

_description = "Send an AMQP request and wait for a response"

class CallCommand(Command):
    def __init__(self, home_dir):
        super(CallCommand, self).__init__(home_dir)

        self.parser.description = _description

        self.parser.add_argument("address", metavar="ADDRESS-URL")
        self.parser.add_argument("body", metavar="MESSAGE-BODY", nargs="?")

        self.add_common_arguments()

    def init(self):
        super(CallCommand, self).init()

        self.address = self.args.address
        self.body = self.args.body

        self.init_common_attributes()

    def run(self):
        handler = _CallHandler(self)
        container = _reactor.Container(handler)

        container.run()

class _CallHandler(_handlers.MessagingHandler):
    def __init__(self, command):
        super(_CallHandler, self).__init__()

        self.command = command

        self.sender = None
        self.receiver = None

    def on_start(self, event):
        host, port, path = parse_address_url(self.command.address)
        domain = "{}:{}".format(host, port)

        conn = event.container.connect(domain, allowed_mechs=b"ANONYMOUS")

        self.sender = event.container.create_sender(conn, path)
        self.command.notice("Created sender for target address '{}'", path)

        self.receiver = event.container.create_receiver(conn, None, dynamic=True)
        self.command.notice("Created dynamic receiver for responses")

    def on_link_opened(self, event):
        if event.receiver == self.receiver:
            request = _proton.Message(unicode(self.command.body))
            request.reply_to = self.receiver.remote_source.address

            self.sender.send(request)

            self.command.notice("Sent request '{}'", self.command.body)

    def on_message(self, event):
        self.command.notice("Received response '{}'", event.message.body)
        event.connection.close()        
