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

import proton as _proton
import proton.handlers as _handlers
import proton.reactor as _reactor
import runpy as _runpy
import sys as _sys
import traceback as _traceback

from .common import *

_description = """
Respond to AMQP requests.  Use qrespond in combination with the
qrequest command to transfer requests through an AMQP message server.
"""

_epilog = """
Example usage:
  $ qrespond amqps://example.net/queue1  # Respond to requests indefinitely
  $ qrespond jobs --count 1              # Respond to one request
  $ qrespond jobs --upper --reverse      # Transform the request text
"""

class RespondCommand(MessagingCommand):
    def __init__(self, home_dir):
        super().__init__(home_dir, "qrespond", _Handler(self))

        self.parser.description = _description + suite_description
        self.parser.epilog = url_epilog + _epilog

        self.parser.add_argument("url", metavar="URL",
                                 help="The location of a message source or target")
        self.parser.add_argument("-c", "--count", metavar="COUNT", type=int,
                                 help="Exit after processing COUNT requests")

        processing_options = self.parser.add_argument_group \
            ("Request processing options",
             "By default, qrespond returns the request text unchanged")

        processing_options.add_argument("--upper", action="store_true",
                                        help="Convert the request text to upper case")
        processing_options.add_argument("--reverse", action="store_true",
                                        help="Reverse the request text")
        processing_options.add_argument("--append", metavar="STRING",
                                        help="Append STRING to the request text")

    def init(self, args):
        super().init(args)

        self.scheme, self.host, self.port, self.address = self.parse_url(args.url)

        self.desired_messages = args.count
        self.upper = args.upper
        self.reverse = args.reverse
        self.append = args.append

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

class _Handler(MessagingHandler):
    def __init__(self, command):
        super().__init__(command, auto_accept=False)

        self.receiver = None
        self.processed_requests = 0

    def open(self, event):
        super().open(event)

        self.receiver = event.container.create_receiver(self.connection, self.command.address)
        self.sender = event.container.create_sender(self.connection, None)

    def close(self, event):
        super().close(event)

        self.command.notice("Processed {} {}", self.processed_requests, plural("request", self.processed_requests))

    def on_message(self, event):
        request = event.message

        self.command.info("Received request {} from {} on {}", request, self.receiver, event.connection)

        response = _proton.Message()
        response.address = request.reply_to
        response.correlation_id = request.id

        try:
            self.command.process(request, response)
        except:
            processing_succeeded = False
            _traceback.print_exc()
        else:
            processing_succeeded = True

        self.processed_requests += 1

        if processing_succeeded:
            self.sender.send(response)

            self.command.info("Sent response {} to address '{}' on {}", response, response.address, event.connection)

            self.accept(event.delivery)
        else:
            self.command.warn("Processing request {} failed", request)

            self.reject(event.delivery)

        if self.processed_requests == self.command.desired_messages:
            self.close(event)
