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

        self.parser.add_argument("url", metavar="ADDRESS-URL", nargs="+",
                                 help="The location of a message source")
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

class _ProcessHandler(_handlers.MessagingHandler):
    def __init__(self, command):
        super(_ProcessHandler, self).__init__()

        self.command = command
        self.connections = set()
        self.receivers = set()
        self.senders_by_receiver = dict()

        self.received_requests = 0
        self.processed_requests = 0

    def on_start(self, event):
        for url in self.command.urls:
            host, port, path = parse_address_url(url)
            domain = "{}:{}".format(host, port)

            connection = event.container.connect(domain, allowed_mechs=b"ANONYMOUS")
            receiver = event.container.create_receiver(connection, path)
            sender = event.container.create_sender(connection, None)

            self.connections.add(connection)
            self.receivers.add(receiver)
            self.senders_by_receiver[receiver] = sender

    def on_connection_opened(self, event):
        assert event.connection in self.connections

        if self.command.verbose:
            self.command.notice("Connected to container '{}'",
                                event.connection.remote_container)

    def on_link_opened(self, event):
        if event.link.is_receiver:
            assert event.link in self.receivers

            self.command.notice("Created receiver for source address '{}' on container '{}'",
                                event.link.source.address,
                                event.connection.remote_container)

        if event.link.is_sender:
            assert event.link in self.senders_by_receiver.values()

            self.command.notice("Created sender for target address '{}' on container '{}'",
                                event.link.target.address,
                                event.connection.remote_container)

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
            
    def close(self):
        for connection in self.connections:
            connection.close()
