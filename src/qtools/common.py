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

import argparse as _argparse
import collections as _collections
import json as _json
import os as _os
import proton as _proton
import proton.handlers as _handlers
import proton.reactor as _reactor
import sys as _sys
import threading as _threading
import time as _time
import traceback as _traceback
import urllib.parse as _urlparse
import uuid as _uuid

suite_description = """
This command is part of the Qtools suite of AMQP 1.0 messaging tools
including qconnect, qsend, qreceive, qmessage, qrespond, qrequest, and
qbroker.
"""

url_epilog = """
URLs:
  [SCHEME:][//HOST[:PORT]/]ADDRESS (default amqp://localhost:5672/ADDRESS)
  queue1
  amqp://example.net/queue1
  amqps://example.net:1000/notifications/system
"""

message_epilog = """
Messages:
  Message input strings are converted to AMQP messages with
  corresponding string bodies.  If messages are supplied directly,
  each string argument is one message.  If messages are read from a
  file, each line is one message.

  If the message input starts with "{" and ends with "}", it is parsed
  as a JSON message input, allowing you to set other parts of the AMQP
  message.  See qmessage for more information.

    '{"id": "1", "properties": {"key": "value"}, "body": "hello"}'
  """

class Command:
    def __init__(self, name):
        self.name = name

        try:
            from importlib.metadata import version
        except ImportError:
            self.version = "[Unknown]"
        else:
            self.version = version("ssorj-qtools")

        self.parser = _argparse.ArgumentParser()
        self.parser.formatter_class = _argparse.RawDescriptionHelpFormatter

        logging = self.parser.add_argument_group("Logging options")

        logging.add_argument("--quiet", action="store_true",
                             help="Print no logging to the console")
        logging.add_argument("--verbose", action="store_true",
                             help="Print detailed logging to the console")
        logging.add_argument("--debug", action="store_true",
                             help="Print debugging output to the console")

        self.parser.add_argument("--version", action="version", version=self.version,
                                 help="Print the Qtools version and exit")
        self.parser.add_argument("--init-only", action="store_true",
                                 help=_argparse.SUPPRESS)

        self.quiet = False
        self.verbose = False
        self.debug_enabled = False
        self.init_only = False

    def log(self, message, *args):
        summarized_args = [_summarize(x) for x in args]
        message = message.format(*summarized_args)
        print("{}: {}".format(self.id, message), file=_sys.stderr)

    def info(self, message, *args):
        if self.verbose:
            self.log(message, *args)

    def notice(self, message, *args):
        if not self.quiet:
            self.log(message, *args)

    def warn(self, message, *args):
        self.log("Warning! {}".format(message), *args)

    def error(self, message, *args):
        self.log("Error! {}".format(message), *args)

    def fail(self, message, *args):
        raise CommandError(message.format(*args))

    def check_file(self, path):
        if path is not None and not _os.path.exists(path):
            raise CommandError("File '{}' not found".format(path))

    def main(self, args=None):
        args = self.parser.parse_args(args)

        assert args is None or isinstance(args, _argparse.Namespace), args

        try:
            self.init(args)

            if self.init_only:
                return

            self.run()
        except KeyboardInterrupt:
            pass
        except CommandError as e:
            if self.debug_enabled:
                _traceback.print_exc()
                exit(1)
            else:
                exit(str(e))

    def init(self, args):
        self.quiet = args.quiet
        self.verbose = args.verbose
        self.debug_enabled = args.debug
        self.init_only = args.init_only

        if self.debug_enabled:
            self.verbose = True

    def run(self):
        pass

class CommandError(Exception):
    pass

class MessagingCommand(Command):
    def __init__(self, name, handler):
        super().__init__(name)

        self.container = _reactor.Container(handler)

        self.events = _reactor.EventInjector()
        self.container.selectable(self.events)

        self.input_file = _sys.stdin
        self.input_thread = _InputThread(self)

        self.output_file = _sys.stdout
        self.output_thread = _OutputThread(self)

        self.ready = _threading.Event()

        self.messaging_options = self.parser.add_argument_group("Messaging options")

        self.messaging_options.add_argument("--id", metavar="ID",
                                            help="Set the client identity to ID (a default is generated)")

        auth = self.parser.add_argument_group("Authentication options")

        auth.add_argument("--user", metavar="USER",
                          help="Identify as USER")
        auth.add_argument("--password", metavar="SECRET",
                          help="Prove your identity with SECRET")
        auth.add_argument("--sasl-mechs", metavar="MECHS", default="anonymous,plain",
                          help="Restrict allowed SASL mechanisms to MECHS (default \"anonymous,plain\")")

        tls = self.parser.add_argument_group("TLS options", "Certificate and key files are in PEM format")

        tls.add_argument("--tls", action="store_true",
                         help="Enable TLS authentication and encryption")
        tls.add_argument("--cert", metavar="FILE",
                         help="The client TLS certificate file")
        tls.add_argument("--key", metavar="FILE",
                         help="The client TLS private key file (default is the value for --cert)")
        tls.add_argument("--trust", metavar="FILE",
                         help="Trust server TLS certificates in FILE")

        self.parser.add_argument("--ready-file", metavar="FILE",
                                 help="Write \"ready\\n\" to FILE when the client is connected")

    def init(self, args):
        super().init(args)

        self.id = args.id

        if self.id is None:
            self.id = "{}-{}".format(self.name, unique_id())

        self.container.container_id = self.id

        self.user = args.user
        self.password = args.password
        self.sasl_mechs = args.sasl_mechs.replace(",", " ").upper()

        self.check_file(args.cert)
        self.check_file(args.key)
        self.check_file(args.trust)

        self.tls_enabled = args.tls
        self.tls_cert = args.cert
        self.tls_key = args.key
        self.tls_trust = args.trust

        if self.tls_key is None and self.tls_cert is not None:
            self.tls_key = self.tls_cert

        self.ready_file = args.ready_file

    def parse_url(self, string):
        url = _urlparse.urlparse(string)

        if url.path is None:
            self.fail("The URL has no path")

        scheme = url.scheme
        host = url.hostname
        port = url.port
        address = url.path

        if not scheme:
            if self.tls_enabled:
                scheme = "amqps"
            else:
                scheme = "amqp"

        if host is None:
            host = "localhost"

        if port is None:
            port = 5672

        port = str(port)

        if address.startswith("/"):
            address = address[1:]

        return scheme, host, port, address

    def run(self):
        self.container.run()

class MessagingHandler(_handlers.MessagingHandler):
    def __init__(self, command, **kwargs):
        super().__init__(**kwargs)

        self.command = command
        self.connection = None
        self.done_sending = False

    def on_start(self, event):
        self.open(event)

    def open(self, event):
        scheme = "amqps" if self.command.tls_enabled else self.command.scheme
        connection_url = "{}://{}:{}".format(scheme, self.command.host, self.command.port)
        ssl_domain = None

        if self.command.tls_enabled or scheme == "amqps":
            self.command.info("Enabling TLS")

            ssl_domain = _proton.SSLDomain(_proton.SSLDomain.MODE_CLIENT)

            if self.command.tls_cert:
                self.command.info("Using TLS cert in {}", self.command.tls_cert)
                self.command.info("Using TLS key in {}", self.command.tls_key)

                ssl_domain.set_credentials(self.command.tls_cert, self.command.tls_key, None)

            if self.command.tls_trust is not None:
                self.command.info("Trusting certs in {}", self.command.tls_trust)

                ssl_domain.set_peer_authentication(_proton.SSLDomain.VERIFY_PEER, self.command.tls_trust)
                ssl_domain.set_trusted_ca_db(self.command.tls_trust)
            else:
                ssl_domain.set_peer_authentication(_proton.SSLDomain.VERIFY_PEER_NAME)

        if self.command.user is not None:
            self.command.info("Connecting to {} as user '{}'", connection_url, self.command.user)
        else:
            self.command.info("Connecting to {}", connection_url)

        self.connection = event.container.connect(connection_url,
                                                  user=self.command.user,
                                                  password=self.command.password,
                                                  allowed_mechs=self.command.sasl_mechs,
                                                  ssl_domain=ssl_domain)

    def close(self, event):
        self.connection.close()
        self.command.events.close()

    def on_connection_opened(self, event):
        self.command.info("Connected to {}", event.connection)

    def on_link_opened(self, event):
        if event.link.is_receiver:
            self.command.notice("Created receiver for {} on {}", event.link.source, event.connection)

        if event.link.is_sender and event.link.target.address is not None:
            self.command.notice("Created sender for {} on {}", event.link.target, event.connection)

        if self.command.ready_file is not None:
            with open(self.command.ready_file, "w") as f:
                f.write("ready\n")

        self.command.ready.set()

    def on_settled(self, event):
        template = "Server '{}' {} {}"
        server = event.connection.remote_container
        delivery = event.delivery

        if delivery.remote_state == delivery.ACCEPTED:
            self.command.info(template, server, "accepted", delivery)
        elif delivery.remote_state == delivery.REJECTED:
            self.command.warn(template, server, "rejected", delivery)
        elif delivery.remote_state == delivery.RELEASED:
            self.command.notice(template, server, "released", delivery)
        elif delivery.remote_state == delivery.MODIFIED:
            self.command.notice(template, server, "modified", delivery)

    def on_transport_error(self, event):
        cond = event.transport.condition
        self.command.error("{}: {}", cond.name, cond.description)

class _InputOutputThread(_threading.Thread):
    def __init__(self, command):
        _threading.Thread.__init__(self)

        self.command = command
        self.name = self.__class__.__name__

        self.lines = _collections.deque()
        self.lines_cv = _threading.Condition(_threading.Lock())

    def push_line(self, line):
        with self.lines_cv:
            self.lines.appendleft(line)
            self.lines_cv.notify()

class _InputThread(_InputOutputThread):
    def __init__(self, command):
        super().__init__(command)
        self.daemon = True

    def run(self):
        self.command.ready.wait()

        with self.command.input_file as f:
            while True:
                line = f.readline()

                if line == "":
                    self.push_line("")
                    return

                self.push_line(line[:-1])

    def push_line(self, line):
        super().push_line(line)
        self.command.events.trigger(_reactor.ApplicationEvent("input"))

class _OutputThread(_InputOutputThread):
    STOP = object()

    def run(self):
        self.command.ready.wait()

        with self.command.output_file as f:
            with self.lines_cv:
                while True:
                    while len(self.lines) == 0:
                        self.lines_cv.wait()

                    line = self.lines.pop()

                    if line is self.STOP:
                        return

                    f.write(line + "\n")
                    f.flush()

    def stop(self):
        self.push_line(self.STOP)

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
    return "server '{}'".format(connection.remote_container)

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

    if isinstance(desc, _proton.Described):
        desc = desc.value

    if len(desc) > 16:
        desc = "{}...".format(desc[:12])

    return "message '{}'".format(desc)

def process_input_line(line):
    if line.endswith("\n"):
        line = line[:-1]

    if line.startswith("{") and line.endswith("}"):
        data = _json.loads(line)
        message = convert_data_to_message(data)
    else:
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
    return _uuid.uuid4().hex[:8]

def plural(word, count, override=None):
    if count == 1:
        return word

    if override is not None:
        return override

    return word + "s"
