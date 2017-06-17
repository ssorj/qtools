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
import pencil as _pencil
import proton as _proton
import sys as _sys

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

        self.init_only = False
        self.quiet = False
        self.verbose = False

        for arg in _sys.argv:
            if "=" not in arg:
                self.name = arg.rsplit("/", 1)[-1]
                break

        self.args = None

    def __repr__(self):
        return _pencil.format_repr(self)

    def add_common_arguments(self):
        self.parser.add_argument("--init-only", action="store_true",
                                 help=_argparse.SUPPRESS)
        self.parser.add_argument("--quiet", action="store_true",
                                 help="Print no logging to the console")
        self.parser.add_argument("--verbose", action="store_true",
                                 help="Print detailed logging to the console")

    def init(self):
        assert self.parser is not None
        assert self.args is None

        self.args = self.parser.parse_args()

    def init_common_attributes(self):
        self.init_only = self.args.init_only
        self.quiet = self.args.quiet
        self.verbose = self.args.verbose

    def run(self):
        raise NotImplementedError()

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
        message = "{}: {}".format(self.name, message)

        _sys.stderr.write("{}\n".format(message))
        _sys.stderr.flush()

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
