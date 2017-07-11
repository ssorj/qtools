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

import json as _json
import proton as _proton
import proton.reactor as _reactor
import sys as _sys

from .common import *

_description = "Receive AMQP messages"

_epilog = """
example usage:
  $ qreceive //example.net/queue0
  $ qreceive queue0 queue1 > messages.txt
"""

class ReceiveCommand(MessagingCommand):
    def __init__(self, home_dir):
        super(ReceiveCommand, self).__init__(home_dir, "qreceive", _Handler(self))

        self.description = _description
        self.epilog = url_epilog + _epilog

        self.add_link_arguments()

        self.add_argument("--output", metavar="FILE",
                          help="Write messages to FILE (default stdout)")
        self.add_argument("--json", action="store_true",
                          help="Write messages in JSON format")
        self.add_argument("--annotations", action="store_true",
                          help="Print delivery and message metadata")
        self.add_argument("--router-trace", action="store_true",
                          help="Print the routers the message passed through")
        self.add_argument("--no-prefix", action="store_true",
                          help="Suppress address prefix")
        self.add_argument("-c", "--count", metavar="COUNT", type=int,
                          help="Exit after receiving COUNT messages")

    def init(self):
        super(ReceiveCommand, self).init()

        self.init_link_attributes()

        self.json = self.args.json
        self.annotations = self.args.annotations
        self.router_trace = self.args.router_trace
        self.no_prefix = self.args.no_prefix
        self.max_count = self.args.count

        if self.args.output is not None:
            self.output_file = open(self.args.output, "w")

class _Handler(LinkHandler):
    def __init__(self, command):
        super(_Handler, self).__init__(command)

        self.received_messages = 0

    def open_links(self, event, connection, address):
        return event.container.create_receiver(connection, address),

    def on_message(self, event):
        if self.received_messages == self.command.max_count:
            return

        self.received_messages += 1

        message = event.message
        extra_info = False

        if self.command.annotations:
            if message.instructions is not None:
                for name in sorted(message.instructions):
                    value = message.instructions[name]
                    self.command.output_file.write("[delivery annotation] {}: {}\n".format(name, value))

            if message.annotations is not None:
                for name in sorted(message.annotations):
                    value = message.annotations[name]
                    self.command.output_file.write("[message annotation] {}: {}\n".format(name, value))

        if self.command.router_trace:
            value = message.annotations.get("x-opt-qd.trace")

            if value is not None:
                self.command.output_file.write("[router trace] {}\n".format(", ".join(value)))

        if not self.command.no_prefix:
            prefix = event.link.source.address + ": "
            self.command.output_file.write(prefix)

        if self.command.json:
            data = convert_message_to_data(message)
            _json.dump(data, self.command.output_file)
        else:
            self.command.output_file.write(message.body)

        self.command.output_file.write("\n")

        self.command.info("Received {} from {} on {}",
                          message,
                          event.link.source,
                          event.connection)

        if self.received_messages == self.command.max_count:
            self.command.output_file.flush()
            self.close()

    def close(self):
        super(_Handler, self).close()

        self.command.notice("Received {} {}",
                            self.received_messages,
                            plural("message", self.received_messages))
