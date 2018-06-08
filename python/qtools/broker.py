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

import commandant as _commandant

from .brokerlib import *
from .common import *
from .common import _summarize

_description = "An AMQP message broker for testing"

class BrokerCommand(_commandant.Command):
    def __init__(self, home_dir):
        super(BrokerCommand, self).__init__(home_dir, "qbroker")

        self.description = _description

        self.add_argument("--id", metavar="ID",
                          help="Set the container identity to ID")
        self.add_argument("--host", metavar="HOST", default="127.0.0.1",
                          help="Listen for connections on HOST (default 127.0.0.1)")
        self.add_argument("--port", metavar="PORT", default=5672,
                          help="Listen for connections on PORT (default 5672)")

        self.broker = None

    def init(self):
        super(BrokerCommand, self).init()

        assert self.broker is None

        self.broker = _Broker(self, self.args.host, self.args.port)

        self.id = self.args.id

        if self.id is None:
            self.id = "{0}-{1}".format(self.name, unique_id())

        self.broker.container.container_id = self.id

    def run(self):
        self.broker.run()

    def print_message(self, message, *args):
        summarized_args = [_summarize(x) for x in args]
        super(BrokerCommand, self).print_message(message, *summarized_args)

class _Broker(Broker):
    def __init__(self, command, host, port):
        super(_Broker, self).__init__(host, port)

        self.command = command

    def info(self, message, *args):
        self.command.info(message, *args)

    def notice(self, message, *args):
        self.command.notice(message, *args)

    def warn(self, message, *args):
        self.command.warn(message, *args)

    def error(self, message, *args):
        self.command.error(message, *args)

    def fail(self, message, *args):
        self.command.fail(message, *args)
