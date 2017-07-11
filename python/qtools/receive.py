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
import os as _os
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
                          help="Print delivery and message annotations")
        self.add_argument("--properties", action="store_true",
                          help="Print message application properties")
        self.add_argument("--router-trace", action="store_true",
                          help="Print the list of routers the message passed through")
        self.add_argument("--no-prefix", action="store_true",
                          help="Suppress address prefix")
        self.add_argument("-c", "--count", metavar="COUNT", type=int,
                          help="Exit after receiving COUNT messages")

    def init(self):
        super(ReceiveCommand, self).init()

        self.init_link_attributes()

        self.json_enabled = self.args.json
        self.annotations_enabled = self.args.annotations
        self.properties_enabled = self.args.properties
        self.router_trace_enabled = self.args.router_trace
        self.prefix_disabled = self.args.no_prefix
        self.max_count = self.args.count

        if self.args.output is not None:
            self.output_file = open(self.args.output, "w")

    def run(self):
        self.output_thread.start()
        super(ReceiveCommand, self).run()

class _Handler(LinkHandler):
    def __init__(self, command):
        super(_Handler, self).__init__(command)

        self.received_messages = 0

    def open_links(self, event, connection, address):
        return event.container.create_receiver(connection, address),

    def on_message(self, event):
        if self.command.done.is_set():
            return

        self.received_messages += 1

        message = event.message
        extra_info = False

        if self.command.annotations_enabled:
            if message.instructions is not None:
                for name in sorted(message.instructions):
                    value = message.instructions[name]
                    self.writeln("[delivery annotation] {}: {}", name, value)

            if message.annotations is not None:
                for name in sorted(message.annotations):
                    value = message.annotations[name]
                    self.writeln("[message annotation] {}: {}", name, value)

        if self.command.properties_enabled:
            if message.properties is not None:
                for name in sorted(message.properties):
                    value = message.properties[name]
                    self.writeln("[property] {}: {}", name, value)

        if self.command.router_trace_enabled:
            value = message.annotations.get("x-opt-qd.trace")
            value = ", ".join(value)

            if value is not None:
                self.writeln("[router trace] {}", value)

        if not self.command.prefix_disabled:
            prefix = event.link.source.address + ": "
            self.write(prefix)

        if self.command.json_enabled:
            data = convert_message_to_data(message)
            _json.dump(data, self.command.output_file)
        else:
            self.write(message.body)

        self.writeln()

        self.command.info("Received {} from {} on {}",
                          message,
                          event.link.source,
                          event.connection)

        if self.received_messages == self.command.max_count:
            self.command.done.set()
            self.command.output_thread.send(None)

    def close(self):
        super(_Handler, self).close()

        self.command.notice("Received {} {}",
                            self.received_messages,
                            plural("message", self.received_messages))

        print_threads()

    def write(self, template=None, *args):
        #self.command.output_thread.send((event.delivery, event.message))

        if template is None:
            return

        string = template.format(*args)
        self.command.output_file.write(string)

    def writeln(self, template=None, *args):
        self.write(template, *args)
        self.write(_os.linesep)
