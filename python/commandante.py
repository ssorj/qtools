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
import sys as _sys

class Command(object):
    def __init__(self, home_dir, name=None):
        self.name = name
        self.home_dir = home_dir

        self._parser = _argparse.ArgumentParser()
        self._parser.formatter_class = _argparse.RawDescriptionHelpFormatter

        self._args = None

        self.add_argument("--quiet", action="store_true",
                          help="Print no logging to the console")
        self.add_argument("--verbose", action="store_true",
                          help="Print detailed logging to the console")
        self.add_argument("--init-only", action="store_true",
                          help=_argparse.SUPPRESS)

        self.id = self.name

    def add_argument(self, *args, **kwargs):
        self.parser.add_argument(*args, **kwargs)

    @property
    def parser(self):
        return self._parser

    @property
    def args(self):
        return self._args

    @property
    def description(self):
        return self.parser.description

    @description.setter
    def description(self, text):
        text = text.strip()
        self.parser.description = text

    @property
    def epilog(self):
        return self.parser.epilog

    @epilog.setter
    def epilog(self, text):
        text = text.strip()
        self.parser.epilog = text

    def init(self):
        assert self._args is None

        self._args = self.parser.parse_args()

        self.quiet = self.args.quiet
        self.verbose = self.args.verbose
        self.init_only = self.args.init_only

    def run(self):
        raise NotImplementedError()

    def main(self):
        try:
            self.init()

            assert self._args is not None

            if self.init_only:
                return

            self.run()
        except KeyboardInterrupt:
            pass

    def info(self, message, *args):
        if self.verbose:
            self.print(message, *args)

    def notice(self, message, *args):
        if not self.quiet:
            self.print(message, *args)

    def warn(self, message, *args):
        message = "Warning! {}".format(message)

        self.print(message, *args)

    def error(self, message, *args):
        message = "Error! {}".format(message)

        self.print(message, *args)

        _sys.exit(1)

    def print(self, message, *args):
        message = message[0].upper() + message[1:]
        message = message.format(*args)
        message = "{}: {}".format(self.id, message)

        _sys.stderr.write("{}\n".format(message))
        _sys.stderr.flush()
