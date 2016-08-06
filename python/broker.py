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

from proton import Endpoint as _Endpoint
from proton.handlers import MessagingHandler as _MessagingHandler
from proton.reactor import Container as _Container

_log = _logging.getLogger("broker")

class _Queue(object):
    def __init__(self):
        self.messages = _collections.deque()
        self.consumers = list()

    def add_consumer(self, consumer):
        assert consumer not in self.consumers
        self.consumers.append(consumer)

    def remove_consumer(self, consumer):
        assert consumer in self.consumers
        self.consumers.remove(consumer)

    def store_message(self, message):
        self.messages.append(message)
        self.forward_messages()

    def forward_messages(self):
        for consumer in self.consumers:
            if consumer.credit > 0:
                try:
                    message = self.messages.popleft()
                except IndexError:
                    return

                consumer.send(message)

class _BrokerHandler(_MessagingHandler):
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
            queue = self.queues[address] = Queue()

        return queue

    def on_link_opening(self, event):
        if event.link.is_sender:
            # if event.link.remote_source.dynamic:
            #     address = str(_uuid.uuid4())
            #     event.link.source.address = address
            
            #     queue = Queue(True)
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

    def unsubscribe(self, link):
        try:
            queue = self.queues[link.source.address]
        except KeyError:
            _log.warn("I can't find queue {}".format(queue))
            return

        queue.remove_consumer(link)
        
        # XXX handle dynamic
        if queue.consumers == 0 and queue.messages.count == 0:
            del self.queues[link.source.address]

    def on_link_closing(self, event):
        if event.link.is_sender:
            self.remove_consumer(event.link)

    def on_connection_closing(self, event):
        self.remove_stale_consumers(event.connection)

    def on_disconnected(self, event):
        self.remove_stale_consumers(event.connection)

    def remove_stale_consumers(self, connection):
        link = connection.link_head(_Endpoint.REMOTE_ACTIVE)

        while link is not None:
            if link.is_sender:
                self.unsubscribe(link)
                
            link = link.next(_Endpoint.REMOTE_ACTIVE)

    def on_sendable(self, event):
        queue = self.get_queue(event.link.source.address)
        queue.dispatch(event.link)

    def on_message(self, event):
        queue = self.get_queue(event.link.target.address)
        queue.publish(event.message)

class Broker(object):
    def __init__(self, interface):
        self.interface = interface
        self.container = _Container(_BrokerHandler(self.interface))

    def __repr__(self):
        return _pencil.format_repr(self, self.interface)
        
    def run(self):
        _log.info("Starting {}".format(self))
        
        self.container.run()
