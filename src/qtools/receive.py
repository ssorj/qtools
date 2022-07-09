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

import json as _json
import os as _os
import proton as _proton
import proton.reactor as _reactor
import sys as _sys

from .common import *

_description = """
Receive AMQP messages.  Use qreceive in combination with the qsend
command to transfer messages through an AMQP message server.
"""

_epilog = """
Example usage:
  $ qreceive amqps://example.net/queue1  # Receive messages indefinitely
  $ qreceive jobs --count 1              # Receive one message
  $ qreceive jobs > messages.txt         # Receive messages to a file
  $ qreceive jobs                        # Receive messages on the console
"""

class ReceiveCommand(MessagingCommand):
    def __init__(self):
        super().__init__("qreceive", _Handler(self))

        self.parser.description = _description + suite_description
        self.parser.epilog = url_epilog + _epilog

        self.parser.add_argument("url", metavar="URL",
                                 help="The location of a message source or target")
        self.parser.add_argument("-c", "--count", metavar="COUNT", type=int,
                                 help="Exit after receiving COUNT messages")
        self.parser.add_argument("--output", metavar="FILE",
                                 help="Write messages to FILE (default stdout)")
        self.parser.add_argument("--json", action="store_true",
                                 help="Write messages in JSON format")

        self.messaging_options.add_argument("--annotations", action="store_true",
                                            help="Print delivery and message annotations")
        self.messaging_options.add_argument("--properties", action="store_true",
                                            help="Print message application properties")

    def init(self, args):
        super().init(args)

        self.scheme, self.host, self.port, self.address = self.parse_url(args.url)

        self.json_enabled = args.json
        self.annotations_enabled = args.annotations
        self.properties_enabled = args.properties
        self.desired_messages = args.count

        if args.output is not None:
            self.output_file = open(args.output, "w")

    def run(self):
        self.output_thread.start()

        try:
            super().run()
        finally:
            self.output_thread.stop()
            self.output_thead.join()

class _Handler(MessagingHandler):
    def __init__(self, command):
        super().__init__(command)

        self.receiver = None
        self.received_messages = 0

    def open(self, event):
        super().open(event)

        self.receiver = event.container.create_receiver(self.connection, self.command.address)

    def close(self, event):
        super().close(event)

        self.command.notice("Received {} {}", self.received_messages, plural("message", self.received_messages))

    def on_message(self, event):
        self.received_messages += 1

        message = event.message
        extra_info = False

        if self.command.annotations_enabled:
            if message.instructions is not None:
                for name in sorted(message.instructions):
                    value = message.instructions[name]
                    self.write_line("[delivery annotation] {}: {}", name, value)

            if message.annotations is not None:
                for name in sorted(message.annotations):
                    value = message.annotations[name]
                    self.write_line("[message annotation] {}: {}", name, value)

        if self.command.properties_enabled:
            if message.properties is not None:
                for name in sorted(message.properties):
                    value = message.properties[name]
                    self.write_line("[property] {}: {}", name, value)

        out = list()

        if self.command.json_enabled:
            data = convert_message_to_data(message)
            json = _json.dumps(data)
            out.append(json)
        else:
            out.append(str(message.body))

        self.command.output_thread.push_line("".join(out))

        self.command.info("Received {} from {} on {}", message, event.link.source, event.connection)

        if self.received_messages == self.command.desired_messages:
            self.close(event)

    def write_line(self, template="", *args):
        line = template.format(*args)
        self.command.output_thread.push_line(line)

def main():
    ReceiveCommand().main()
