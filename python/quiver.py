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

import collections as _collections
import logging as _logging
import pencil as _pencil
import uuid as _uuid

from proton import *
from proton.handlers import *
from proton.reactor import *

_log = _logging.getLogger("quiver")

class SendHandler(MessagingHandler):
    def __init__(self, address, message_body):
        super().__init__()

        self.address = address
        self.message_body = message_body

        self.sent = False
    
    def on_start(self, event):
        # XXX I have to parse the address here because for some reason
        # I need to explicitly pass anonymous here (I don't understand
        # why that's not a reasonable default for an outbound
        # connection), and that can only be done via connect (don't
        # like that much - most users are going to want to set it at
        # the container level - disable_sasl too), and the form of
        # create_sender that takes a connection as context needs a
        # naked amqp address. Gah.
        
        conn = event.container.connect(self.address, allowed_mechs="ANONYMOUS")
        url = Url(self.address)
        
        event.container.create_sender(conn, url.path)

        print("SENDER: Created sender for target address '{0}'".format(url.path))

    def on_sendable(self, event):
        if self.sent:
            return

        message = Message(self.message_body)
        event.sender.send(message)

        print("SENDER: Sent message '{0}'".format(self.message_body))
        
        event.connection.close()

        self.sent = True

class ReceiveHandler(MessagingHandler):
    def __init__(self, address, max_count):
        super().__init__()

        self.address = address
        self.max_count = max_count

        self.count = 0
    
    def on_start(self, event):
        conn = event.container.connect(self.address, allowed_mechs="ANONYMOUS")
        url = Url(self.address)
        
        event.container.create_receiver(conn, url.path)

        print("RECEIVER: Created receiver for source address '{0}'".format(url.path))

    def on_message(self, event):
        print("RECEIVER: Received message '{0}'".format(event.message.body))

        self.count += 1

        if self.count == self.max_count:
            event.connection.close()

class _Queue(object):
    def __init__(self):
        self.messages = _collections.deque()
        self.consumers = list()

    def add_consumer(self, link):
        assert link.is_sender
        assert link not in self.consumers

        self.consumers.append(link)

    def remove_consumer(self, link):
        assert link.is_sender

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
    def __init__(self, address):
        super(_BrokerHandler, self).__init__()

        self.address = address
        self.queues = dict()

    def on_start(self, event):
        self.acceptor = event.container.listen(self.address)

        _log.info("Listening on {}".format(self.address))

    def get_queue(self, address):
        try:
            queue = self.queues[address]
        except KeyError:
            queue = self.queues[address] = _Queue()

        return queue

    def on_link_opening(self, event):
        if event.link.is_sender:
            # if event.link.remote_source.dynamic:
            #     address = str(_uuid.uuid4())
            #     event.link.source.address = address
            
            #     queue = _Queue(True)
            #     queue.subscribe(event.link)

            #     self.queues[address] = queue

            #     return

            address = event.link.remote_source.address

            assert address is not None
            
            event.link.source.address = address

            queue = self.get_queue(address)
            queue.add_consumer(event.link)

            return

        if event.link.is_receiver:
            address = event.link.remote_target.address

            assert address is not None
            
            event.link.target.address = address

    def on_link_closing(self, event):
        if event.link.is_sender:
            self.remove_consumer(event.link)

    def on_connection_closing(self, event):
        self.remove_consumers(event.connection)

    def on_disconnected(self, event):
        self.remove_consumers(event.connection)

    def remove_consumers(self, connection):
        link = connection.link_head(Endpoint.REMOTE_ACTIVE)

        while link is not None:
            if link.is_sender:
                queue = self.queues.get(link.source.address)

                if queue is not None:
                    queue.remove_consumer(link)
                
                # XXX handle dynamic
                #if queue.consumers == 0 and queue.messages.count == 0:
                #    del self.queues[link.source.address]

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
    def __init__(self, interface):
        self.interface = interface
        self.container = Container(_BrokerHandler(self.interface))

    def __repr__(self):
        return _pencil.format_repr(self, self.interface)
        
    def run(self):
        _log.info("Starting {}".format(self))
        
        self.container.run()
