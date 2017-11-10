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
import runpy as _runpy
import sys as _sys
import traceback as _traceback

from .common import *

_description = "Respond to AMQP requests"

_epilog = """
processing configuration:
  The supplied config file must define a Python function like this:

    def process(request, response):
        response.body = request.body.upper()

  The request and response arguments are Proton message objects.  The
  return value is ignored.

example usage:
  $ qrespond //example.net/queue0
  $ qrespond queue0 queue1
"""

class RespondCommand(MessagingCommand):
    def __init__(self, home_dir):
        super(RespondCommand, self).__init__(home_dir, "qrespond", _Handler(self))

        self.description = _description
        self.epilog = url_epilog + _epilog

        self.add_link_arguments()

        self.add_argument("-c", "--count", metavar="COUNT", type=int,
                          help="Exit after processing COUNT requests")
        self.add_argument("--config", metavar="FILE",
                          help="Load processing code from FILE")
        self.add_argument("--upper", action="store_true",
                          help="Convert the request text to upper case")
        self.add_argument("--reverse", action="store_true",
                          help="Reverse the request text")
        self.add_argument("--append", metavar="STRING",
                          help="Append STRING to the request text")

    def init(self):
        super(RespondCommand, self).init()

        self.init_link_attributes()

        if self.args.config is not None:
            config_file = self.args.config

            if config_file == "-":
                config_file = "/dev/stdin"

            try:
                config = _runpy.run_path(config_file)
            except:
                self.fail("Failed to load config from '{0}'", config_file)

            try:
                self.process = config["process"]
            except KeyError:
                self.fail("Function 'process' not found in '{0}'", config_file)

        self.max_count = self.args.count
        self.upper = self.args.upper
        self.reverse = self.args.reverse
        self.append = self.args.append

    def process(self, request, response):
        text = request.body

        if text is None:
            return

        if self.upper:
            text = text.upper()

        if self.reverse:
            text = "".join(reversed(text))

        if self.append is not None:
            text += self.append

        response.body = text

class _Handler(LinkHandler):
    def __init__(self, command):
        super(_Handler, self).__init__(command, auto_accept=False)

        self.receivers = list()
        self.senders_by_receiver = dict()

        self.processed_requests = 0

    def open_links(self, event, connection, address):
        receiver = event.container.create_receiver(connection, address)
        sender = event.container.create_sender(connection, None)

        self.receivers.append(receiver)
        self.senders_by_receiver[receiver] = sender

        return receiver, sender

    def on_message(self, event):
        if self.done_receiving:
            return

        delivery = event.delivery
        request = event.message
        receiver = event.link

        self.command.info("Received request {0} from {1} on {2}",
                          request,
                          receiver.source,
                          event.connection)

        response = _proton.Message()
        response.address = request.reply_to
        response.correlation_id = request.id

        try:
            self.command.process(request, response)
            processing_succeeded = True
        except:
            processing_succeeded = False
            _traceback.print_exc()

        self.processed_requests += 1

        if processing_succeeded:
            sender = self.senders_by_receiver[event.link]
            sender.send(response)

            self.command.info("Sent response {0} to address '{1}' on {2}",
                              response,
                              response.address,
                              event.connection)

            self.accept(delivery)
        else:
            self.command.warn("Processing request {0} failed", request)

            self.reject(delivery)

        if self.processed_requests == self.command.max_count:
            self.done_receiving = True
            self.close(event)

    def close(self, event):
        super(_Handler, self).close(event)

        self.command.notice("Processed {0} {1}",
                            self.processed_requests,
                            plural("request", self.processed_requests))
