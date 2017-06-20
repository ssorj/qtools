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
import uuid as _uuid

from .common import *

_description = "An AMQP message broker for testing"

class BrokerCommand(Command):
    def __init__(self, home_dir):
        super(BrokerCommand, self).__init__(home_dir)

        self.parser.description = _description

        self.parser.add_argument("--host", metavar="HOST", default="127.0.0.1",
                                 help="Listen on HOST (default 127.0.0.1)")
        self.parser.add_argument("--port", metavar="PORT", default=5672,
                                 help="Listen on PORT (default 5672)")

        self.add_common_arguments()

    def init(self):
        super(BrokerCommand, self).init()

        self.init_common_attributes()

        self.host = self.args.host
        self.port = self.args.port

    def run(self):
        handler = _BrokerHandler(self)
        container = _reactor.Container(handler)

        container.container_id = self.id
        container.run()

class _BrokerQueue(object):
    def __init__(self, command, address):
        self.command = command
        self.address = address

        self.messages = _collections.deque()
        self.consumers = list()

        self.command.notice("Created {}", self)

    def __repr__(self):
        return "queue '{}'".format(self.address)

    def add_consumer(self, link):
        assert link.is_sender
        assert link not in self.consumers

        self.consumers.append(link)

        self.command.notice("Added consumer for container '{}' to {}",
                            link.connection.remote_container, self)

    def remove_consumer(self, link):
        assert link.is_sender

        try:
            self.consumers.remove(link)
        except ValueError:
            return

        self.command.notice("Removed consumer for container '{}' from {}",
                            link.connection.remote_container, self)

    def store_message(self, message):
        self.messages.append(message)

        self.command.notice("Stored message '{}' on {}", message.body, self)

    def forward_messages(self, link):
        assert link.is_sender

        while link.credit > 0:
            try:
                message = self.messages.popleft()
            except IndexError:
                break

            link.send(message)

            self.command.notice("Forwarded message '{}' to container '{}'",
                                message.body, link.connection.remote_container)

class _BrokerHandler(_handlers.MessagingHandler):
    def __init__(self, command):
        super(_BrokerHandler, self).__init__()

        self.command = command
        self.queues = dict()
        self.verbose = False

    def on_start(self, event):
        domain = "{}:{}".format(self.command.host, self.command.port)

        self.acceptor = event.container.listen(domain)

        self.command.notice("Listening on '{}'", domain)

    def get_queue(self, address):
        try:
            queue = self.queues[address]
        except KeyError:
            queue = self.queues[address] = _BrokerQueue(self.command, address)

        return queue

    def on_link_opening(self, event):
        if event.link.is_sender:
            if event.link.remote_source.dynamic:
                address = str(_uuid.uuid4())
            else:
                address = event.link.remote_source.address

            assert address is not None

            event.link.source.address = address

            queue = self.get_queue(address)
            queue.add_consumer(event.link)

        if event.link.is_receiver:
            address = event.link.remote_target.address
            event.link.target.address = address

    def on_link_closing(self, event):
        if event.link.is_sender:
            queue = self.queues[link.source.address]
            queue.remove_consumer(link)

    def on_connection_opening(self, event):
        # XXX I think this should happen automatically
        event.connection.container = event.container.container_id

    def on_connection_opened(self, event):
        self.command.notice("Opened connection from container '{}'",
                            event.connection.remote_container)

    def on_connection_closing(self, event):
        self.remove_consumers(event.connection)

    def on_connection_closed(self, event):
        self.command.notice("Closed connection from container '{}'",
                            event.connection.remote_container)

    def on_disconnected(self, event):
        self.command.notice("Disconnected from container '{}'",
                            event.connection.remote_container)

        self.remove_consumers(event.connection)

    def remove_consumers(self, connection):
        link = connection.link_head(_proton.Endpoint.REMOTE_ACTIVE)

        while link is not None:
            if link.is_sender:
                queue = self.queues[link.source.address]
                queue.remove_consumer(link)

            link = link.next(_proton.Endpoint.REMOTE_ACTIVE)

    def on_sendable(self, event):
        queue = self.get_queue(event.link.source.address)
        queue.forward_messages(event.link)

    def on_message(self, event):
        message = event.message
        address = event.link.target.address

        if address is None:
            address = message.address

        queue = self.get_queue(address)
        queue.store_message(message)

        for link in queue.consumers:
            queue.forward_messages(link)
