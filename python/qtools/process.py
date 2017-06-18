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
import sys as _sys

from .common import *

_description = "Process AMQP requests"

class ProcessCommand(Command):
    def __init__(self, home_dir):
        super(ProcessCommand, self).__init__(home_dir)

        self.parser.description = _description

        self.add_link_arguments()

        #self.parser.add_argument("--max", metavar="COUNT", type=int,
        #                         help="Stop after receiving COUNT messages")

        self.add_common_arguments()

        self.container = _reactor.Container(_ProcessHandler(self))

    def init(self):
        super(ProcessCommand, self).init()

        self.init_common_attributes()

        self.urls = self.args.url
        #self.max_count = self.args.max

        self.container.container_id = self.id

    def run(self):
        self.container.run()

class _ProcessHandler(LinkHandler):
    def __init__(self, command):
        super(_ProcessHandler, self).__init__(command)

        self.receivers = list()
        self.senders_by_receiver = dict()

        self.received_requests = 0
        self.processed_requests = 0

    def open_link(self, event, connection, address):
        receiver = event.container.create_receiver(connection, address)
        sender = event.container.create_sender(connection, None)

        self.receivers.append(receiver)
        self.senders_by_receiver[receiver] = sender
        self.links.appendleft(sender)

        return receiver

    def on_message(self, event):
        #if self.received_requests == self.command.max_count:
        #    return

        self.received_requests += 1

        request = event.message
        receiver = event.link

        if self.command.verbose:
            self.command.notice("Received request '{}' from '{}' on '{}'",
                                request.body,
                                receiver.source.address,
                                event.connection.remote_container)

        response = self.process(event.link, request)
        response.address = request.reply_to
        response.correlation_id = request.correlation_id

        sender = self.senders_by_receiver[event.link]
        sender.send(response)

        if self.command.verbose:
            self.command.notice("Sent response '{}' to '{}' on '{}'",
                                response.body,
                                response.address,
                                event.connection.remote_container)

    def process(self, receiver, request):
        response_body = request.body.upper()
        response = _proton.Message(response_body)

        return response
