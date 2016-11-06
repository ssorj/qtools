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

from __future__ import print_function

import collections as _collections
import logging as _logging
import pencil as _pencil
import uuid as _uuid

from argparse import ArgumentParser
from proton import Message, Endpoint
from proton import Url # XXX
from proton.handlers import MessagingHandler
from proton.reactor import Container

try:
    from urllib.parse import urlparse as _urlparse
except ImportError:
    from urlparse import urlparse as _urlparse

_log = _logging.getLogger("qtools")

class SendHandler(MessagingHandler):
    def __init__(self, address, message_body):
        super(SendHandler, self).__init__()

        self.address = address
        self.message_body = message_body

        self.sent = False
        self.verbose = False

    def print(self, message, *args):
        if not self.verbose:
            return

        message = "qsend: {}".format(message)

        print(message.format(*args))

    def on_start(self, event):
        host, port, path = _parse_address(self.address)
        domain = "{}:{}".format(host, port)

        # XXX
        # - Connection is not anonymous by default
        # - Can't set mechs on create_sender or on container
        # - Requires this two-step procedure
        conn = event.container.connect(domain, allowed_mechs="ANONYMOUS")
        event.container.create_sender(conn, path)

        self.print("Created sender for target address '{}'", path)

    def on_sendable(self, event):
        if self.sent:
            return

        message = Message(self.message_body)
        event.sender.send(message)

        self.print("Sent message '{}'", self.message_body)

        self.sent = True

    def on_accepted(self, event):
        event.connection.close()

class ReceiveHandler(MessagingHandler):
    def __init__(self, address, messages):
        super(ReceiveHandler, self).__init__()

        self.address = address
        self.messages = messages

        self.verbose = False
        self.count = 0

    def print(self, message, *args):
        if not self.verbose:
            return

        message = "qreceive: {}".format(message)

        print(message.format(*args))

    def on_start(self, event):
        host, port, path = _parse_address(self.address)
        domain = "{}:{}".format(host, port)

        conn = event.container.connect(domain, allowed_mechs="ANONYMOUS")
        event.container.create_receiver(conn, path)

        self.print("Created receiver for source address '{}'", path)

    def on_message(self, event):
        if self.count == self.messages:
            return

        self.print("Received message '{}'", event.message.body)

        print(event.message.body)

        self.count += 1

        if self.count == self.messages:
            event.connection.close()

class DrainHandler(MessagingHandler):
    def __init__(self, address, messages):
        super(DrainHandler, self).__init__()

        self.address = address
        self.messages = messages

        self.verbose = False

    def print(self, message, *args):
        if not self.verbose:
            return

        message = "qdrain: {}".format(message)

        print(message.format(*args))

    def on_start(self, event):
        conn = event.container.connect(self.address, allowed_mechs="ANONYMOUS")
        url = Url(self.address)

        event.container.create_receiver(conn, url.path)

        self.print("Created receiver for source address '{}'", url.path)

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

class _BrokerQueue(object):
    def __init__(self, broker, address):
        self.broker = broker
        self.address = address

        self.messages = _collections.deque()
        self.consumers = list()

        self.broker.notice("Creating {}", self)

    def __repr__(self):
        return "queue '{}'".format(self.address)

    def add_consumer(self, link):
        assert link.is_sender
        assert link not in self.consumers

        m = "Adding consumer for '{}' to {}"
        self.broker.notice(m, link.connection.remote_container, self)

        self.consumers.append(link)

    def remove_consumer(self, link):
        assert link.is_sender

        m = "Removing consumer for '{}' from {}"
        self.broker.notice(m, link.connection.remote_container, self)

        try:
            self.consumers.remove(link)
        except ValueError:
            pass

    def store_message(self, message):
        self.messages.append(message)

    def forward_messages(self, link):
        assert link.is_sender

        while link.credit > 0:
            try:
                message = self.messages.popleft()
            except IndexError:
                break

            link.send(message)

class _BrokerHandler(MessagingHandler):
    def __init__(self, broker):
        super(_BrokerHandler, self).__init__()

        self.broker = broker
        self.queues = dict()

        self.verbose = False

    def on_start(self, event):
        self.acceptor = event.container.listen(self.broker.domain)

        self.broker.notice("Listening on '{}'", self.broker.domain)

    def get_queue(self, address):
        try:
            queue = self.queues[address]
        except KeyError:
            queue = self.queues[address] = _BrokerQueue(self.broker, address)

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

            assert address is not None

            event.link.target.address = address

    def on_link_closing(self, event):
        if event.link.is_sender:
            queue = self.queues[link.source.address]
            queue.remove_consumer(link)

    def on_connection_opening(self, event):
        m = "Opening connection from '{}'"
        self.broker.notice(m, event.connection.remote_container)

        # XXX I think this should happen automatically
        event.connection.container = event.container.container_id

    def on_connection_closing(self, event):
        m = "Closing connection from '{}'"
        self.broker.notice(m, event.connection.remote_container)

        self.remove_consumers(event.connection)

    def on_disconnected(self, event):
        m = "Disconnected from {}"
        self.broker.notice(m, event.connection.remote_container)

        self.remove_consumers(event.connection)

    def remove_consumers(self, connection):
        link = connection.link_head(Endpoint.REMOTE_ACTIVE)

        while link is not None:
            if link.is_sender:
                queue = self.queues[link.source.address]
                queue.remove_consumer(link)

            link = link.next(Endpoint.REMOTE_ACTIVE)

    def on_sendable(self, event):
        queue = self.get_queue(event.link.source.address)
        queue.forward_messages(event.link)

    def on_message(self, event):
        queue = self.get_queue(event.link.target.address)
        queue.store_message(event.message)

        for link in queue.consumers:
            queue.forward_messages(link)

class Broker(object):
    def __init__(self, domain):
        self.domain = domain
        self.container = Container(_BrokerHandler(self))

    def __repr__(self):
        return _pencil.format_repr(self, self.domain)

    def notice(self, message, *args):
        message = message.format(*args)
        _log.info(message)

    def run(self):
        self.container.run()

class QtoolsError(Exception):
    pass

def _parse_address(address):
    url = _urlparse(address)

    if url.path is None:
        raise QtoolsError("The address URL has no path")

    host = url.hostname
    port = url.port
    path = url.path[1:]

    if host is None:
        host = "localhost"

    if port is None:
        port = 5672

    port = str(port)

    return host, port, path
