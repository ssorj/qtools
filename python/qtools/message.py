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
import sys as _sys
import time as _time
import uuid as _uuid

from .common import *

_description = "Generate AMQP messages"

class MessageCommand(Command):
    def __init__(self, home_dir):
        super(MessageCommand, self).__init__(home_dir)

        self.parser.description = _description

        self.parser.add_argument("-o", "--output", metavar="FILE",
                                 help="Write messages to FILE (default stdout)")
        self.parser.add_argument("-c", "--count", metavar="COUNT", type=int, default=1,
                                 help="Exit after generating COUNT messages (default 1)")

        self.add_common_arguments()

    def init(self):
        super(MessageCommand, self).init()

        self.output_file = _sys.stdout
        self.max_count = self.args.count

        if self.args.output is not None:
            self.output_file = open(self.args.output, "w")
            
    def run(self):
        count = 0

        with self.output_file as f:
            while count < self.max_count:
                count += 1

                message = "message-{}".format(count)

                f.write(message)
                f.write("\n")
                f.flush()
                
