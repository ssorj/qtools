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

_description = "Respond to AMQP requests"

_epilog = """
example usage:
  $ qrespond //example.net/queue0
  $ qrespond queue0 queue1
"""

class RespondCommand(Command):
    def __init__(self, home_dir):
        super(RespondCommand, self).__init__(home_dir)

        self.parser.description = _description
        self.parser.epilog = url_epilog + _epilog

        self.add_link_arguments()

        self.parser.add_argument("-c", "--count", metavar="COUNT", type=int,
                                 help="Exit after sending COUNT responses")

        self.add_container_arguments()
        self.add_common_arguments()

        self.container.handler = _Handler(self)

    def init(self):
        super(RespondCommand, self).init()

        self.init_link_attributes()
        self.init_container_attributes()
        self.init_common_attributes()

        self.max_count = self.args.count

class _Handler(LinkHandler):
    def __init__(self, command):
        super(_Handler, self).__init__(command)

        self.receivers = list()
        self.senders_by_receiver = dict()

        self.sent_responses = 0

    def open_links(self, event, connection, address):
        receiver = event.container.create_receiver(connection, address)
        sender = event.container.create_sender(connection, None)

        self.receivers.append(receiver)
        self.senders_by_receiver[receiver] = sender

        return receiver, sender

    def on_message(self, event):
        if self.sent_responses == self.command.max_count:
            return

        request = event.message
        receiver = event.link

        self.command.info("Received request '{}' from '{}' on '{}'",
                          request.body,
                          receiver.source.address,
                          event.connection.remote_container)

        response = self.process(event.link, request)
        response.address = request.reply_to
        response.correlation_id = request.correlation_id

        sender = self.senders_by_receiver[event.link]
        sender.send(response)

        self.command.info("Sent response '{}' to '{}' on '{}'",
                          response.body,
                          response.address,
                          event.connection.remote_container)

        self.sent_responses += 1

        if self.sent_responses == self.command.max_count:
            self.close()
            
    def process(self, receiver, request):
        response_body = request.body.upper()
        response = _proton.Message(response_body)

        return response
