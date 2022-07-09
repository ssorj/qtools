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
import json as _json
import proton as _proton
import sys as _sys
import time as _time

from .common import *

_description = """
Generate message inputs for use with the qsend and qrequest commands.
"""

_epilog = """
Example usage:
  $ qmessage --body abc --property color red | qsend amqp://example.net/queue1
  $ qmessage --count 10 --rate 1 | qrequest amqp://example.net/requests
"""

class MessageCommand(Command):
    def __init__(self):
        super().__init__("qmessage")

        self.parser.description = _description + suite_description
        self.parser.epilog = _epilog

        self.parser.add_argument("--output", metavar="FILE",
                                 help="Write messages to FILE (default stdout)")
        self.parser.add_argument("-c", "--count", metavar="COUNT", type=int,
                                 help="Exit after generating COUNT messages (default 1)")
        self.parser.add_argument("--rate", metavar="COUNT", type=int,
                                 help="Generate COUNT messages per second")

        field_options = self.parser.add_argument_group("Message field options")

        field_options.add_argument("--id", metavar="STRING",
                                   help="Set the message ID")
        field_options.add_argument("--correlation-id", metavar="STRING",
                                   help="Set the ID for matching related messages")
        field_options.add_argument("--user", metavar="STRING",
                                   help="Set the ID of the user producing the message")
        field_options.add_argument("--to", metavar="ADDRESS",
                                   help="Set the target address")
        field_options.add_argument("--reply-to", metavar="ADDRESS",
                                   help="Set the address for replies")
        field_options.add_argument("--durable", action="store_true",
                                   help="Set the durable flag")
        field_options.add_argument("--priority", metavar="INTEGER",
                                   help="Set the priority to INTEGER")
        field_options.add_argument("--ttl", metavar="FLOAT",
                                   help="Set the time-to-live to FLOAT seconds")
        field_options.add_argument("--subject", metavar="STRING",
                                   help="Set the message summary")
        field_options.add_argument("--body", metavar="STRING",
                                   help="Set the main message content")
        field_options.add_argument("--property", metavar=("NAME", "VALUE"),
                                   nargs=2, action="append",
                                   help="Set an application property. This option can be repeated.")

        self.output_file = _sys.stdout

    def init(self, args):
        self.max_count = args.count
        self.rate = args.rate

        self.interval = None

        if self.rate is None:
            if self.max_count is None:
                self.max_count = 1
        else:
            self.interval = 1.0 / self.rate

            if self.max_count is None:
                self.max_count = -1

        if args.output is not None:
            self.output_file = open(args.output, "w")

        self.init_message(args)

    def init_message(self, args):
        self.message = _proton.Message()
        self.message.id = args.id
        self.message.correlation_id = args.correlation_id
        self.message.address = args.to
        self.message.reply_to = args.reply_to
        self.message.subject = args.subject
        self.message.body = args.body
        self.message.durable = args.durable

        if args.user is not None:
            self.message.user_id = args.user.encode()

        if args.priority is not None:
            try:
                priority = int(args.priority)
            except ValueError:
                self.fail("Priority value must be an integer")

            self.message.priority = priority

        if args.ttl is not None:
            try:
                ttl = float(args.ttl)
            except ValueError:
                self.fail("TTL value must be a float")

            self.message.ttl = ttl

        self.message.properties = _collections.OrderedDict()

        if args.property is not None:
            for name, value in args.property:
                self.message.properties[name] = value

        self.generate_message_id = False
        self.generate_message_body = False

        if self.message.id is None:
            self.generate_message_id = True

        if self.message.body is None:
            self.generate_message_body = True

        self.id_prefix = unique_id()

    def run(self):
        count = 0

        with self.output_file as f:
            while count != self.max_count:
                count += 1
                start_time = _time.time()

                if self.generate_message_id:
                    self.message.id = "{}-{:04}".format(self.id_prefix, count)

                if self.generate_message_body:
                    self.message.body = "message-{:04}".format(count)

                data = convert_message_to_data(self.message)

                _json.dump(data, f)

                f.write("\n")
                f.flush()

                if self.interval is not None:
                    adjusted = max(0, self.interval - (_time.time() - start_time))
                    _time.sleep(adjusted)

def main():
    MessageCommand().main()
