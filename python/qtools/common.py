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
import commandant as _commandant
import json as _json
import os as _os
import proton as _proton
import proton.handlers as _handlers
import proton.reactor as _reactor
import sys as _sys
import time as _time
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
"""

class MessagingCommand(_commandant.Command):
    def __init__(self, home, name, handler):
        super(MessagingCommand, self).__init__(home, name)

        self.container = _reactor.Container(handler)

        self.events = _reactor.EventInjector()
        self.container.selectable(self.events)

        self.input_file = _sys.stdin
        self.input_thread = _InputThread(self)

        self.output_file = _sys.stdout
        self.output_thread = _OutputThread(self)

        self.ready = _threading.Event()

        self.add_argument("--id", metavar="ID",
                          help="Set the container identity to ID")

    def add_link_arguments(self):
        self.add_argument("url", metavar="ADDRESS-URL", nargs="+",
                          help="The location of a message source or target")
        self.add_argument("--server", metavar="HOST[:PORT]", default="127.0.0.1:5672",
                          help="Use HOST[:PORT] as the default server (default 127.0.0.1:5672)")
        self.add_argument("--tls", action="store_true",
                          help="Connect using SSL/TLS authentication and encryption")

    def init(self):
        super(MessagingCommand, self).init()

        self.id = self.args.id

        if self.id is None:
            self.id = "{0}-{1}".format(self.name, unique_id())

        self.container.container_id = self.id

    def init_link_attributes(self):
        self.server = self.args.server
        self.tls_enabled = self.args.tls
        self.urls = self.args.url

    def parse_address_url(self, address):
        url = _urlparse(address)

        if url.path is None:
            self.fail("The URL has no path")

        scheme = url.scheme
        host = url.hostname
        port = url.port
        path = url.path

        default_scheme = "amqps" if self.tls_enabled else "amqp"

        try:
            default_host, default_port = self.server.split(":", 1)
        except ValueError:
            default_host, default_port = self.server, 5672

        if not scheme:
            scheme = default_scheme

        if host is None:
            host = default_host

        if port is None:
            port = default_port

        port = str(port)

        if path.startswith("/"):
            path = path[1:]

        return scheme, host, port, path

    def run(self):
        self.container.run()

    def print_message(self, message, *args):
        summarized_args = [_summarize(x) for x in args]
        super(MessagingCommand, self).print_message(message, *summarized_args)

class LinkHandler(_handlers.MessagingHandler):
    def __init__(self, command, **kwargs):
        super(LinkHandler, self).__init__(**kwargs)

        self.command = command

        self.connections = list()
        self.links = list()

        self.opened_links = 0

        self.done_sending = False
        self.done_receiving = False

    def on_start(self, event):
        for url in self.command.urls:
            scheme, host, port, address = self.command.parse_address_url(url)
            connection_url = "{0}://{1}:{2}".format(scheme, host, port)

            self.command.info("Connecting to {0}", connection_url)

            allowed_mechs = "ANONYMOUS"

            if _sys.version_info[0] == 2:
                allowed_mechs = b"ANONYMOUS"

            connection = event.container.connect(connection_url, allowed_mechs=allowed_mechs)
            links = self.open_links(event, connection, address)

            self.connections.append(connection)
            self.links.extend(links)

    def open_links(self, connection):
        raise NotImplementedError()

    def on_connection_opened(self, event):
        assert event.connection in self.connections

        self.command.info("Connected to {0}", event.connection)

    def on_link_opened(self, event):
        assert event.link in self.links

        self.opened_links += 1

        if event.link.is_receiver:
            self.command.notice("Created receiver for {0} on {1}",
                                event.link.source,
                                event.connection)

        if event.link.is_sender and event.link.target.address is not None:
            self.command.notice("Created sender for {0} on {1}",
                                event.link.target,
                                event.connection)

        if self.opened_links == len(self.links):
            self.command.ready.set()

    def on_settled(self, event):
        delivery = event.delivery

        template = "{0} {{0}} {1}"
        template = template.format(_summarize(event.connection),
                                   _summarize(delivery))

        if delivery.remote_state == delivery.ACCEPTED:
            self.command.info(template, "accepted")
        elif delivery.remote_state == delivery.REJECTED:
            self.command.warn(template, "rejected")
        elif delivery.remote_state == delivery.RELEASED:
            self.command.notice(template, "released")
        elif delivery.remote_state == delivery.MODIFIED:
            self.command.notice(template, "modified")

    def close(self, event):
        for connection in self.connections:
            connection.close()

        self.command.events.close()

DONE = object()

class _InputOutputThread(_threading.Thread):
    def __init__(self, command):
        _threading.Thread.__init__(self)

        self.command = command
        self.name = self.__class__.__name__
        self.daemon = True

        self.lines = _collections.deque()
        self.lines_queued = _threading.Event()

    def push_line(self, line):
        self.lines.appendleft(line)
        self.lines_queued.set()

class _InputThread(_InputOutputThread):
    def run(self):
        self.command.ready.wait()

        with self.command.input_file as f:
            while True:
                line = f.readline()

                if line == "":
                    self.push_line(DONE)
                    return

                self.push_line(line[:-1])

    def push_line(self, line):
        super(_InputThread, self).push_line(line)
        self.command.events.trigger(_reactor.ApplicationEvent("input"))

class _OutputThread(_InputOutputThread):
    def run(self):
        self.command.ready.wait()

        with self.command.output_file as f:
            while True:
                self.lines_queued.wait()
                self.lines_queued.clear()

                while True:
                    try:
                        line = self.lines.pop()
                    except IndexError:
                        break

                    if line is DONE:
                        return

                    f.write(line + "\n")
                    f.flush()

def _summarize(entity):
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
    return "container '{0}'".format(connection.remote_container)

def _summarize_terminus(terminus):
    if terminus.type == terminus.SOURCE:
        type_ = "source"
    elif terminus.type == terminus.TARGET:
        type_ = "target"
    else:
        raise Exception()

    if terminus.address is None:
        if terminus.dynamic:
            return "dynamic {0}".format(type_)

        return "null {0}".format(type_)

    return "{0} '{1}'".format(type_, terminus.address)

def _summarize_delivery(delivery):
    return "delivery '{0}'".format(delivery.tag)

def _summarize_message(message):
    desc = message.body

    if desc is None:
        desc = message.id

    if desc is None:
        return "message"

    if len(desc) > 16:
        desc = "{0}...".format(desc[:12])

    return "message '{0}'".format(desc)

def process_input_line(line):
    if line.endswith("\n"):
        line = line[:-1]

    if line.startswith("{") and line.endswith("}"):
        data = _json.loads(line)
        message = convert_data_to_message(data)
    else:
#        line = unicode(line)
        message = _proton.Message(line)

    return message

def convert_data_to_message(data):
    message = _proton.Message()

    _set_message_attribute(message, "id", data, "id")
    _set_message_attribute(message, "correlation_id", data, "correlation_id")
    _set_message_attribute(message, "user", data, "user")
    _set_message_attribute(message, "address", data, "to")
    _set_message_attribute(message, "reply_to", data, "reply_to")
    _set_message_attribute(message, "durable", data, "durable")
    _set_message_attribute(message, "priority", data, "priority")
    _set_message_attribute(message, "ttl", data, "ttl")
    _set_message_attribute(message, "subject", data, "subject")
    _set_message_attribute(message, "body", data, "body")

    if "properties" in data:
        props = data["properties"]
        message.properties = dict()

        for name in props:
            message.properties[name] = props[name]

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

    if message.durable:
        _set_data_attribute(data, "durable", message, "durable")

    if message.priority != 4:
        _set_data_attribute(data, "priority", message, "priority")

    if message.ttl != 0:
        _set_data_attribute(data, "ttl", message, "ttl")

    if message.properties:
        props = data["properties"] = _collections.OrderedDict()

        for name in message.properties:
            props[name] = message.properties[name]

    _set_data_attribute(data, "subject", message, "subject")
    _set_data_attribute(data, "body", message, "body")

    return data

def _set_data_attribute(data, dname, message, mname, omit_if_empty=True):
    value = getattr(message, mname)

    if omit_if_empty and value in (None, "", b""):
        return

    if isinstance(value, bytes):
        value = value.decode()

    data[dname] = value

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
