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
import proton.reactor as _reactor
import sys as _sys

from .common import *

_description = "Receive AMQP messages"

_epilog = """
example usage:
  $ qreceive //example.net/queue0
  $ qreceive queue0 queue1 > messages.txt
"""

class ReceiveCommand(Command):
    def __init__(self, home_dir):
        super(ReceiveCommand, self).__init__(home_dir)

        self.parser.description = _description
        self.parser.epilog = url_epilog + _epilog

        self.add_link_arguments()

        self.parser.add_argument("-o", "--output", metavar="FILE",
                                 help="Write messages to FILE (default stdout)")
        self.parser.add_argument("-c", "--count", metavar="COUNT", type=int,
                                 help="Exit after receiving COUNT messages")

        self.add_common_arguments()

        self.container.handler = _Handler(self)

    def init(self):
        super(ReceiveCommand, self).init()

        self.init_link_attributes()
        self.init_common_attributes()

        self.output_file = _sys.stdout
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

        self.command.output_file.write(event.message.body)
        self.command.output_file.write("\n")

        if self.command.verbose:
            self.command.notice("Received message '{}' from '{}' on '{}'",
                                event.message.body,
                                event.link.source.address,
                                event.connection.remote_container)

        if self.received_messages == self.command.max_count:
            self.close()
