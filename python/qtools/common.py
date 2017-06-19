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

import argparse as _argparse
import binascii as _binascii
import proton as _proton
import proton.handlers as _handlers
import proton.reactor as _reactor
import sys as _sys
import threading as _threading
import uuid as _uuid

try:
    from urllib.parse import urlparse as _urlparse
except ImportError:
    from urlparse import urlparse as _urlparse

class CommandError(Exception):
    def __init__(self, message, *args):
        if isinstance(message, Exception):
            message = str(message)

        message = message.format(*args)

        super(CommandError, self).__init__(message)

class Command(object):
    def __init__(self, home_dir):
        self.home_dir = home_dir

        self.parser = _argparse.ArgumentParser()
        self.parser.formatter_class = _Formatter

        self.args = None

        self.container = _reactor.Container()
        self.events = _reactor.EventInjector()

        self.container.selectable(self.events)

        self.quiet = False
        self.verbose = False
        self.init_only = False

        for arg in _sys.argv:
            if "=" not in arg:
                self.name = arg.rsplit("/", 1)[-1]
                break

        self.ready = _threading.Event()
        self.done = _threading.Event()

    def add_link_arguments(self):
        self.parser.add_argument("url", metavar="ADDRESS-URL", nargs="+",
                                 help="The location of a message source or target")

    def add_common_arguments(self):
        self.parser.add_argument("--id", metavar="ID",
                                 help="Set the container identity to ID")
        self.parser.add_argument("--quiet", action="store_true",
                                 help="Print no logging to the console")
        self.parser.add_argument("--verbose", action="store_true",
                                 help="Print detailed logging to the console")
        self.parser.add_argument("--init-only", action="store_true",
                                 help=_argparse.SUPPRESS)

    def init(self):
        assert self.parser is not None
        assert self.args is None

        self.args = self.parser.parse_args()

    def init_link_attributes(self):
        self.urls = self.args.url

    def init_common_attributes(self):
        self.id = self.args.id
        self.quiet = self.args.quiet
        self.verbose = self.args.verbose
        self.init_only = self.args.init_only

        if self.id is None:
            bytes_ = _uuid.uuid4().bytes[:2]
            hex_ = _binascii.hexlify(bytes_).decode("utf-8")

            self.id = "{}-{}".format(self.name, hex_)

        self.container.container_id = self.id

    def send_input(self, message):
        raise NotImplementedError()

    def run(self):
        self.container.run()

    def main(self):
        try:
            self.init()

            if self.init_only:
                return

            self.run()
        except CommandError as e:
            self.error(str(e))
            _sys.exit(1)
        except KeyboardInterrupt:
            pass

    def debug(self, message, *args):
        if not self.verbose:
            return

        self._print_message(message, args)

    def notice(self, message, *args):
        if self.quiet:
            return

        self._print_message(message, args)

    def error(self, message, *args):
        self._print_message(message, args)

    def _print_message(self, message, args):
        message = message.format(*args)
        message = "{}: {}".format(self.id, message)

        _sys.stderr.write("{}\n".format(message))
        _sys.stderr.flush()

class InputThread(_threading.Thread):
    def __init__(self, command):
        _threading.Thread.__init__(self)

        self.command = command
        self.daemon = True

    def run(self):
        self.command.ready.wait()

        with self.command.input_file as f:
            while True:
                if self.command.done.is_set():
                    break

                body = f.readline()

                if body == "":
                    self.command.send_input(None)
                    break

                body = unicode(body[:-1])
                message = _proton.Message(body)

                self.command.send_input(message)

class LinkHandler(_handlers.MessagingHandler):
    def __init__(self, command):
        super(LinkHandler, self).__init__()

        self.command = command

        self.connections = list()
        self.links = list()

        self.opened_links = 0

    def on_start(self, event):
        for url in self.command.urls:
            host, port, address = parse_address_url(url)
            domain = "{}:{}".format(host, port)

            connection = event.container.connect(domain, allowed_mechs=b"ANONYMOUS")
            links = self.open_links(event, connection, address)

            self.connections.append(connection)
            self.links.extend(links)

    def open_links(self, connection):
        raise NotImplementedError()

    def on_connection_opened(self, event):
        assert event.connection in self.connections

        if self.command.verbose:
            self.command.notice("Connected to container '{}'",
                                event.connection.remote_container)

    def on_link_opened(self, event):
        assert event.link in self.links

        self.opened_links += 1

        if event.link.is_receiver:
            self.command.notice("Created receiver for source address '{}' on container '{}'",
                                event.link.source.address,
                                event.connection.remote_container)

        if event.link.is_sender:
            self.command.notice("Created sender for target address '{}' on container '{}'",
                                event.link.target.address,
                                event.connection.remote_container)

        if self.opened_links == len(self.links):
            self.command.ready.set()

    def close(self):
        self.command.done.set()

        for connection in self.connections:
            connection.close()

        self.command.events.close()

def parse_address_url(address):
    url = _urlparse(address)

    if url.path is None:
        raise CommandError("The URL has no path")

    host = url.hostname
    port = url.port
    path = url.path

    if host is None:
        # XXX Should be "localhost" - a workaround for a proton issue
        host = "127.0.0.1"

    if port is None:
        port = "5672"

    port = str(port)

    if path.startswith("/"):
        path = path[1:]

    return host, port, path

class _Formatter(_argparse.ArgumentDefaultsHelpFormatter,
                 _argparse.RawDescriptionHelpFormatter):
    pass
