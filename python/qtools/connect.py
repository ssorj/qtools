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
import proton.reactor as _reactor
import sys as _sys

from .common import *

_description = "Connect to an AMQP server"

_epilog = """
URLs:
  [SCHEME:][//HOST[:PORT]] (default amqp://localhost:5672)
  amqp://example.net
  amqps://example.net:1000

Example usage:
  $ qconnect amqp://example.net
  $ qconnect amqps://example.net --user alice --password secret
  $ qconnect
"""

class ConnectCommand(MessagingCommand):
    def __init__(self, home_dir):
        super().__init__(home_dir, "qconnect", _Handler(self))

        self.parser.description = _description
        self.parser.epilog = _epilog

        self.parser.add_argument("url", metavar="URL", nargs="?", default="amqp://localhost",
                                 help="The location of an AMQP server (default amqp://localhost:5672)")

    def init(self, args):
        super().init(args)

        if "//" in args.url:
            self.scheme, self.host, self.port, _ = self.parse_url(args.url)
        else:
            self.scheme, self.host, self.port = "amqp", "localhost", 5672

            try:
                self.host, self.port = args.url.split(":", 1)
            except ValueError:
                self.host = args.url

class _Handler(MessagingHandler):
    def on_connection_opened(self, event):
        self.command.notice("Connected to server '{}'", event.connection.remote_container)
        self.close(event)

    def on_transport_error(self, event):
        super().on_transport_error(event)
        self.close(event)
