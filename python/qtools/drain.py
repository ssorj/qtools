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

from .common import *

_description = "Drain AMQP messages"

class DrainCommand(Command):
    def __init__(self, home_dir):
        super(DrainCommand, self).__init__(home_dir)

        self.parser.description = _description

        self.parser.add_argument("address", metavar="ADDRESS")
        self.parser.add_argument("-m", "--messages", metavar="COUNT",
                                 type=int, default=1)

        self.add_common_arguments()

    def init(self):
        super(DrainCommand, self).init()

        self.address = self.args.address
        self.messages = self.args.messages
        
        self.init_common_attributes()

    def run(self):
        handler = _DrainHandler(self.address)
        handler.verbose = self.verbose

        container = Container(handler)
        container.run()

class _DrainHandler(_handlers.MessagingHandler):
    def __init__(self, command):
        super(DrainHandler, self).__init__()

        self.command = command

    def print(self, message, *args):
        if not self.verbose:
            return

        message = "qdrain: {}".format(message)

        print(message.format(*args))

    def on_start(self, event):
        host, port, path = _parse_address(self.address)
        domain = "{}:{}".format(host, port)

        conn = event.container.connect(domain, allowed_mechs="ANONYMOUS")
        event.container.create_receiver(conn, path)

        self.print("Created receiver for source address '{}'", path)

    def on_link_opened(self, event):
        event.link.flow(1000000000)
        event.link.drain(1000000000)

    def on_message(self, event):
        if self.count == self.messages:
            return

    def on_message(self, event):
        print(event.message.id)

        if event.receiver.queued == 0 and event.receiver.drained:
            event.connection.close()
