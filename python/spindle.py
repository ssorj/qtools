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

import collections as _collections
import logging as _logging
import sys as _sys
import threading as _threading

_logged_modules = list()

_levels_by_name = {
    "debug": _logging.DEBUG,
    "info": _logging.INFO,
    "warn": _logging.WARN,
    "error": _logging.ERROR,
    "critical": _logging.CRITICAL
    }

_handlers_by_logger = _collections.defaultdict(list)

_formatter = _logging.Formatter \
    ("%(threadName)-6.6s %(asctime)s %(levelname)-4.4s %(message)s")

def _add_logging(name, level, file):
    assert level, level
    assert file, file

    if isinstance(level, str):
        level = _levels_by_name[level.lower()]

    if isinstance(file, str):
        file = open(file, "a")

    handler = _logging.StreamHandler(file)

    handler.setFormatter(_formatter)
    handler.setLevel(level)

    log = _logging.getLogger(name)
    log.setLevel(_logging.DEBUG)
    log.addHandler(handler)

    _handlers_by_logger[log].append(handler)

def _remove_logging(name):
    log = _logging.getLogger(name)
    handlers = _handlers_by_logger[log]

    for handler in handlers:
        log.removeHandler(handler)

    del _handlers_by_logger[log]

def enable_initial_logging():
    log_level = "warn"

    for name in _logged_modules:
        _add_logging(name, log_level, _sys.stderr)

def enable_console_logging(level):
    for name in _logged_modules:
        _remove_logging(name)

    for name in _logged_modules:
        _add_logging(name, level, _sys.stderr)

def enable_file_logging(level, file):
    for name in _logged_modules:
        _remove_logging(name)

    if file is not None:
        for name in _logged_modules:
            _add_logging(name, level, file)

def add_logged_module(name):
    assert isinstance(name, str), name

    _logged_modules.append(name)

def set_thread_name(name):
    _threading.current_thread().name = name
