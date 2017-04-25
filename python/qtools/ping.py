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
import proton.handlers as _handlers

from .common import *

_description = "Ping an AMQP server"

class PingCommand(Command):
    def __init__(self, home_dir):
        super(PingCommand, self).__init__(home_dir)

        self.parser.description = _description

        self.parser.add_argument("domain", metavar="DOMAIN", default="localhost:5672")

        self.add_common_arguments()

    def init(self):
        super(PingCommand, self).init()

        self.domain = self.args.domain

        self.init_common_attributes()

    def run(self):
        handler = _PingHandler(self.domain)
        container = Container(handler)

        container.run()

class _PingHandler(_handlers.MessagingHandler):
    def __init__(self, command):
        super(_PingHandler, self).__init__()

        self.command = command

    def on_start(self, event):
        event.container.connect(self.command.domain, allowed_mechs="ANONYMOUS")

    def on_connection_opened(self, event):
        self.command.notice("Connected to domain '{}'", self.command.domain)

        event.connection.close()

def connect_1(domain):
    import socket
    import struct

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        sock.connect((domain, 5672))

        s = struct.pack("!ccccBBBB", "A", "M", "Q", "P", 0, 1, 0, 0)
        sock.send(s)
        print("S: {}".format(s))

        r = sock.recv(4096)
        print("R: {}".format(r))

        print(len(r))
        print(len(r[:8]))

        d = struct.unpack("!ccccBBBB", r[:8])
        print("D: {}".format(d))
        
        if r == s:
            print("SUCCESS")
    except socket.error:
        print("Connection refused!")
    finally:
        sock.close()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass

# XXX Qpidd doesn't seem to do this:
#
# The protocol id is not a part of the protocol version and thus the
# rule above regarding the highest supported version does not apply. A
# client might request use of a protocol id that is unacceptable to a
# server - for example, it might request a raw AMQP connection when
# the server is configured to require a TLS or SASL security layer
# (See section 5.1). In this case, the server MUST send a protocol
# header with an acceptable protocol id (and version) and then close
# the socket. It MAY choose any protocol id.

# Figure 2.13: Protocol ID Rejection Example

# TCP Client                               TCP Server
# ======================================================
# AMQP%d0.1.0.0       ------------->
#                     <-------------       AMQP%d3.1.0.0
#                                          *TCP CLOSE*
# ------------------------------------------------------
#       Server rejects connection for: AMQP, protocol=0,
#       major=1, minor=0, revision=0, Server responds
#       that it requires: SASL security layer, protocol=3,
#       major=1, minor=0, revision=0 
        
