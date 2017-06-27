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
import collections as _collections
import json as _json
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

url_epilog = """
address URLs:
  [SCHEME:][//SERVER/]ADDRESS
  queue0
  //localhost/queue0
  amqp://example.net:10000/jobs
  amqps://10.0.0.10/jobs/alpha

  By default, SCHEME is 'amqp' and SERVER is '127.0.0.1:5672'.
"""

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

    def add_container_arguments(self):
        self.parser.add_argument("--id", metavar="ID",
                                 help="Set the container identity to ID")

    def add_common_arguments(self):
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

    def init_container_attributes(self):
        self.id = self.args.id

    def init_common_attributes(self):
        self.quiet = self.args.quiet
        self.verbose = self.args.verbose
        self.init_only = self.args.init_only

        if self.id is None:
            self.id = "{}-{}".format(self.name, unique_id())

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

    def info(self, message, *args):
        if self.verbose:
            self._print_message(message, args)

    def notice(self, message, *args):
        if not self.quiet:
            self._print_message(message, args)

    def warn(self, message, *args):
        message = "Warning! {}".format(message)

        self._print_message(message, args)

    def error(self, message, *args):
        message = "Error! {}".format(message)

        self._print_message(message, args)

        _sys.exit(1)

    def _print_message(self, message, args):
        summarized_args = [summarize(x) for x in args]

        message = message[0].upper() + message[1:]
        message = message.format(*summarized_args)
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

                string = f.readline()

                if string == "":
                    self.command.send_input(None)
                    break

                if string.endswith("\n"):
                    string = string[:-1]

                if string.startswith("{") and string.endswith("}"):
                    data = _json.loads(string)
                    message = convert_data_to_message(data)
                else:
                    string = unicode(string)
                    message = _proton.Message(string)

                self.command.send_input(message)

class LinkHandler(_handlers.MessagingHandler):
    def __init__(self, command, **kwargs):
        super(LinkHandler, self).__init__(**kwargs)

        self.command = command

        self.connections = list()
        self.links = list()

        self.opened_links = 0

    def on_start(self, event):
        for url in self.command.urls:
            scheme, host, port, address = parse_address_url(url)
            connection_url = "{}://{}:{}".format(scheme, host, port)

            connection = event.container.connect(connection_url, allowed_mechs=b"ANONYMOUS")
            links = self.open_links(event, connection, address)

            self.connections.append(connection)
            self.links.extend(links)

    def open_links(self, connection):
        raise NotImplementedError()

    def on_connection_opened(self, event):
        assert event.connection in self.connections

        self.command.info("Connected to {}", event.connection)

    def on_link_opened(self, event):
        assert event.link in self.links

        self.opened_links += 1

        if event.link.is_receiver:
            self.command.notice("Created receiver for {} on {}",
                                event.link.source,
                                event.connection)

        if event.link.is_sender:
            self.command.notice("Created sender for {} on {}",
                                event.link.target,
                                event.connection)

        if self.opened_links == len(self.links):
            self.command.ready.set()

    def on_settled(self, event):
        delivery = event.delivery

        template = "{} {{}} {} to {}"
        template = template.format(summarize(event.connection),
                                   summarize(delivery),
                                   summarize(event.link.target))

        if delivery.remote_state == delivery.ACCEPTED:
            self.command.info(template, "accepted")
        elif delivery.remote_state == delivery.REJECTED:
            self.command.warn(template, "rejected")
        elif delivery.remote_state == delivery.RELEASED:
            self.command.notice(template, "released")
        elif delivery.remote_state == delivery.MODIFIED:
            self.command.notice(template, "modified")

    def close(self):
        self.command.done.set()

        for connection in self.connections:
            connection.close()

        self.command.events.close()

def summarize(entity):
    if isinstance(entity, _proton.Connection):
        return _summarize_connection(entity)

    if isinstance(entity, _proton.Terminus):
        return _summarize_terminus(entity)

    if isinstance(entity, _proton.Delivery):
        return _summarize_delivery(entity)

    if isinstance(entity, _proton.Message):
        return _summarize_message(entity)

    return entity

def _summarize_connection(connection):
    return "container '{}'".format(connection.remote_container)

def _summarize_terminus(terminus):
    if terminus.type == terminus.SOURCE:
        type_ = "source"
    elif terminus.type == terminus.TARGET:
        type_ = "target"
    else:
        raise Exception()

    if terminus.address is None:
        if terminus.dynamic:
            return "dynamic {}".format(type_)

        return "null {}".format(type_)

    return "{} '{}'".format(type_, terminus.address)

def _summarize_delivery(delivery):
    return "delivery '{}'".format(delivery.tag)

def _summarize_message(message):
    desc = message.body

    if desc is None:
        desc = message.id

    if desc is None:
        return "message"

    if len(desc) > 16:
        desc = "{}...".format(desc[:12])

    return "message '{}'".format(desc)

def unique_id():
    bytes_ = _uuid.uuid4().bytes[:2]
    hex_ = _binascii.hexlify(bytes_).decode("utf-8")

    return hex_

def plural(word, count, override=None):
    if count == 1:
        return word

    if override is not None:
        return override

    return word + "s"

def parse_address_url(address):
    url = _urlparse(address)

    if url.path is None:
        raise CommandError("The URL has no path")

    scheme = url.scheme
    host = url.hostname
    port = url.port
    path = url.path

    if scheme is None:
        scheme = "amqp"

    if host is None:
        # XXX Should be "localhost" - a workaround for a proton issue
        host = "127.0.0.1"

    if port is None:
        port = 5672

    port = str(port)

    if path.startswith("/"):
        path = path[1:]

    return scheme, host, port, path

def convert_data_to_message(data):
    message = _proton.Message()

    _set_message_attribute(message, "id", data, "id")
    _set_message_attribute(message, "correlation_id", data, "correlation_id")
    _set_message_attribute(message, "user", data, "user")
    _set_message_attribute(message, "address", data, "to")
    _set_message_attribute(message, "reply_to", data, "reply_to")
    _set_message_attribute(message, "durable", data, "durable")
    _set_message_attribute(message, "subject", data, "subject")
    _set_message_attribute(message, "body", data, "body")

    return message

def _set_message_attribute(message, mname, data, dname):
    try:
        value = data[dname]
    except KeyError:
        return

    setattr(message, mname, value)

def convert_message_to_data(message):
    data = _collections.OrderedDict()

    _set_data_attribute(data, "id", message, "id")
    _set_data_attribute(data, "correlation_id", message, "correlation_id")
    _set_data_attribute(data, "user", message, "user_id")
    _set_data_attribute(data, "to", message, "address")
    _set_data_attribute(data, "reply_to", message, "reply_to")
    _set_data_attribute(data, "durable", message, "durable")
    _set_data_attribute(data, "subject", message, "subject")
    _set_data_attribute(data, "body", message, "body")

    return data

def _set_data_attribute(data, dname, message, mname, omit_if_empty=True):
    value = getattr(message, mname)

    if omit_if_empty and value in (None, ""):
        return

    data[dname] = getattr(message, mname)

class _Formatter(_argparse.RawDescriptionHelpFormatter):
    pass
