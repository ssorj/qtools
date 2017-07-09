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

import collections as _collections
import json as _json
import proton as _proton
import sys as _sys
import time as _time

from .common import *

_description = "Generate AMQP messages"

class MessageCommand(Command):
    def __init__(self, home_dir):
        super(MessageCommand, self).__init__(home_dir)

        self.parser.description = _description

        self.parser.add_argument("--output", metavar="FILE",
                                 help="Write messages to FILE (default stdout)")
        self.parser.add_argument("-c", "--count", metavar="COUNT", type=int,
                                 help="Exit after generating COUNT messages (default 1)")
        self.parser.add_argument("--rate", metavar="COUNT", type=int,
                                 help="Generate COUNT messages per second")

        self.parser.add_argument("--id", metavar="STRING",
                                 help="Set the message ID")
        self.parser.add_argument("--correlation-id", metavar="STRING",
                                 help="Set the ID for matching related messages")
        self.parser.add_argument("--user", metavar="STRING",
                                 help="Set the ID of the user producing the message")
        self.parser.add_argument("--to", metavar="ADDRESS",
                                 help="Set the target address")
        self.parser.add_argument("--reply-to", metavar="ADDRESS",
                                 help="Set the address for replies")
        self.parser.add_argument("--durable", action="store_true",
                                 help="Set the durable flag")
        self.parser.add_argument("--subject", metavar="STRING",
                                 help="Set the message summary")
        self.parser.add_argument("--body", metavar="STRING",
                                 help="Set the main message content")
        self.parser.add_argument("--prop", metavar=("NAME", "VALUE"),
                                 nargs=2, action="append",
                                 help="Set an application property")

        self.add_common_arguments()

    def init(self):
        super(MessageCommand, self).init()

        self.output_file = _sys.stdout
        self.max_count = self.args.count
        self.rate = self.args.rate

        self.interval = None

        if self.rate is None:
            if self.max_count is None:
                self.max_count = 1
        else:
            self.interval = 1.0 / self.rate

            if self.max_count is None:
                self.max_count = -1

        if self.args.output is not None:
            self.output_file = open(self.args.output, "w")

        self.init_message()

    def init_message(self):
        self.message = _proton.Message()
        self.message.id = self.args.id
        self.message.correlation_id = self.args.correlation_id
        self.message.user_id = self.args.user
        self.message.address = self.args.to
        self.message.reply_to = self.args.reply_to
        self.message.subject = self.args.subject
        self.message.body = self.args.body
        self.message.durable = self.args.durable

        self.message.properties = _collections.OrderedDict()

        if self.args.prop is not None:
            for name, value in self.args.prop:
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
