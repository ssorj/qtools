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

from .main import *

import argparse as _argparse
import collections as _collections
import importlib as _importlib
import inspect as _inspect
import os as _os
import sys as _sys
import traceback as _traceback

class BaseCommand:
    def main(self, args=None):
        if args is None:
            args = ARGS[1:]

        args = self.parse_args(args)

        assert isinstance(args, _argparse.Namespace), args

        self.verbose = args.verbose or args.debug
        self.quiet = args.quiet
        self.debug_enabled = args.debug
        self.init_only = args.init_only

        level = "notice"

        if self.verbose:
            level = "info"

        if self.quiet:
            level = "error"

        if self.debug_enabled:
            level = "debug"

        with logging_enabled(level=level):
            try:
                self.init(args)

                if self.init_only:
                    return

                self.run()
            except KeyboardInterrupt:
                pass
            except PlanoError as e:
                if self.debug_enabled:
                    _traceback.print_exc()
                    exit(1)
                else:
                    exit(str(e))

    def parse_args(self, args): # pragma: nocover
        raise NotImplementedError()

    def init(self, args): # pragma: nocover
        pass

    def run(self): # pragma: nocover
        raise NotImplementedError()

class BaseArgumentParser(_argparse.ArgumentParser):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.allow_abbrev = False
        self.formatter_class = _argparse.RawDescriptionHelpFormatter

        self.add_argument("--verbose", action="store_true",
                          help="Print detailed logging to the console")
        self.add_argument("--quiet", action="store_true",
                          help="Print no logging to the console")
        self.add_argument("--debug", action="store_true",
                          help="Print debugging output to the console")
        self.add_argument("--init-only", action="store_true",
                          help=_argparse.SUPPRESS)

        _capitalize_help(self)

_plano_command = None

class PlanoCommand(BaseCommand):
    def __init__(self, module=None, description="Run commands defined as Python functions", epilog=None):
        self.module = module
        self.bound_commands = dict()
        self.running_commands = list()
        self.passthrough_args = None

        assert self.module is None or _inspect.ismodule(self.module), self.module

        self.pre_parser = BaseArgumentParser(description=description, add_help=False)
        self.pre_parser.add_argument("-h", "--help", action="store_true",
                                     help="Show this help message and exit")

        if self.module is None:
            self.pre_parser.add_argument("-f", "--file", help="Load commands from FILE (default '.plano.py')")
            self.pre_parser.add_argument("-m", "--module", help="Load commands from MODULE")

        self.parser = _argparse.ArgumentParser(parents=(self.pre_parser,),
                                               description=description, epilog=epilog,
                                               add_help=False, allow_abbrev=False)

        # This is intentionally added after self.pre_parser is passed
        # as parent to self.parser, since it is used only in the
        # preliminary parsing.
        self.pre_parser.add_argument("command", nargs="?", help=_argparse.SUPPRESS)

        global _plano_command
        _plano_command = self

    def parse_args(self, args):
        pre_args, _ = self.pre_parser.parse_known_args(args)

        if self.module is None:
            if pre_args.module is None:
                self.module = self._load_file(pre_args.file)
            else:
                self.module = self._load_module(pre_args.module)

        if self.module is not None:
            self._bind_commands(self.module)

        self._process_commands()

        self.preceding_commands = list()

        if pre_args.command is not None and "," in pre_args.command:
            names = pre_args.command.split(",")

            for name in names[:-1]:
                try:
                    self.preceding_commands.append(self.bound_commands[name])
                except KeyError:
                    self.parser.error(f"Command '{name}' is unknown")

            args[args.index(pre_args.command)] = names[-1]

        args, self.passthrough_args = self.parser.parse_known_args(args)

        return args

    def init(self, args):
        self.help = args.help

        self.selected_command = None
        self.command_args = list()
        self.command_kwargs = dict()

        if args.command is not None:
            for command in self.preceding_commands:
                command()

            self.selected_command = self.bound_commands[args.command]

            if not self.selected_command.passthrough and self.passthrough_args:
                self.parser.error(f"unrecognized arguments: {' '.join(self.passthrough_args)}")

            for arg in self.selected_command.args.values():
                if arg.name == "passthrough_args":
                    continue

                if arg.positional:
                    if arg.multiple:
                        self.command_args.extend(getattr(args, arg.name))
                    else:
                        self.command_args.append(getattr(args, arg.name))
                else:
                    self.command_kwargs[arg.name] = getattr(args, arg.name)

            if self.selected_command.passthrough:
                self.command_kwargs["passthrough_args"] = self.passthrough_args

    def run(self):
        if self.help or self.module is None or self.selected_command is None:
            self.parser.print_help()
            return

        with Timer() as timer:
            self.selected_command(*self.command_args, **self.command_kwargs)

        cprint("OK", color="green", file=_sys.stderr, end="")
        cprint(" ({})".format(format_duration(timer.elapsed_time)), color="magenta", file=_sys.stderr)

    def _load_module(self, name):
        try:
            return _importlib.import_module(name)
        except ImportError:
            exit("Module '{}' not found", name)

    def _load_file(self, path):
        if path is not None and is_dir(path):
            path = self._find_file(path)

        if path is not None and not is_file(path):
            exit("File '{}' not found", path)

        if path is None:
            path = self._find_file(get_current_dir())

        if path is None:
            return

        debug("Loading '{}'", path)

        _sys.path.insert(0, join(get_parent_dir(path), "python"))

        spec = _importlib.util.spec_from_file_location("_plano", path)
        module = _importlib.util.module_from_spec(spec)
        _sys.modules["_plano"] = module

        try:
            spec.loader.exec_module(module)
        except Exception as e:
            error(e)
            exit("Failure loading {}: {}", path, str(e))

        return module

    def _find_file(self, dir):
        # Planofile and .planofile remain temporarily for backward compatibility
        for name in (".plano.py", "Planofile", ".planofile"):
            path = join(dir, name)

            if is_file(path):
                return path

    def _bind_commands(self, module):
        for var in vars(module).values():
            if callable(var) and var.__class__.__name__ == "Command":
                self.bound_commands[var.name] = var

    def _process_commands(self):
        subparsers = self.parser.add_subparsers(title="commands", dest="command")

        for command in self.bound_commands.values():
            add_help = False if command.passthrough else True

            subparser = subparsers.add_parser(command.name, help=command.help,
                                              description=nvl(command.description, command.help), add_help=add_help,
                                              formatter_class=_argparse.RawDescriptionHelpFormatter)

            for arg in command.args.values():
                if arg.positional:
                    if arg.multiple:
                        subparser.add_argument(arg.name, metavar=arg.metavar, type=arg.type, help=arg.help, nargs="*")
                    elif arg.optional:
                        subparser.add_argument(arg.name, metavar=arg.metavar, type=arg.type, help=arg.help, nargs="?", default=arg.default)
                    else:
                        subparser.add_argument(arg.name, metavar=arg.metavar, type=arg.type, help=arg.help)
                else:
                    flag_args = list()

                    if arg.short_option is not None:
                        flag_args.append("-{}".format(arg.short_option))

                    flag_args.append("--{}".format(arg.display_name))

                    help = arg.help

                    if arg.default not in (None, False):
                        if help is None:
                            help = "Default value is {}".format(repr(arg.default))
                        else:
                            help += " (default {})".format(repr(arg.default))

                    if arg.default is False:
                        subparser.add_argument(*flag_args, dest=arg.name, default=arg.default, action="store_true", help=help)
                    else:
                        subparser.add_argument(*flag_args, dest=arg.name, default=arg.default, metavar=arg.metavar, type=arg.type, help=help)

            _capitalize_help(subparser)

_command_help = {
    "build":    "Build artifacts from source",
    "clean":    "Clean up the source tree",
    "dist":     "Generate distribution artifacts",
    "install":  "Install the built artifacts on your system",
    "test":     "Run the tests",
}

def command(_function=None, name=None, args=None, parent=None, passthrough=False):
    class Command:
        def __init__(self, function):
            self.function = function
            self.module = _inspect.getmodule(self.function)

            self.name = name
            self.args = args
            self.parent = parent

            if self.parent is None:
                self.name = nvl(self.name, self.function.__name__.rstrip("_").replace("_", "-"))
                self.args = self.process_args(self.args)
            else:
                self.name = nvl(self.name, self.parent.name)
                self.args = nvl(self.args, self.parent.args)

            doc = _inspect.getdoc(self.function)

            if doc is None:
                self.help = _command_help.get(self.name)
                self.description = self.help
            else:
                self.help = doc.split("\n")[0]
                self.description = doc

            if self.parent is not None:
                self.help = nvl(self.help, self.parent.help)
                self.description = nvl(self.description, self.parent.description)

            self.passthrough = passthrough

            debug("Defining {}", self)

            for arg in self.args.values():
                debug("  {}", str(arg).capitalize())

        def __repr__(self):
            return "command '{}:{}'".format(self.module.__name__, self.name)

        def process_args(self, input_args):
            sig = _inspect.signature(self.function)
            params = list(sig.parameters.values())
            input_args = {x.name: x for x in nvl(input_args, ())}
            output_args = _collections.OrderedDict()

            for param in params:
                try:
                    arg = input_args[param.name]
                except KeyError:
                    arg = CommandArgument(param.name)

                if param.kind is param.POSITIONAL_ONLY: # pragma: nocover
                    if arg.positional is None:
                        arg.positional = True
                elif param.kind is param.POSITIONAL_OR_KEYWORD and param.default is param.empty:
                    if arg.positional is None:
                        arg.positional = True
                elif param.kind is param.POSITIONAL_OR_KEYWORD and param.default is not param.empty:
                    arg.optional = True
                    arg.default = param.default
                elif param.kind is param.VAR_POSITIONAL:
                    if arg.positional is None:
                        arg.positional = True
                    arg.multiple = True
                elif param.kind is param.VAR_KEYWORD:
                    continue
                elif param.kind is param.KEYWORD_ONLY:
                    arg.optional = True
                    arg.default = param.default
                else: # pragma: nocover
                    raise NotImplementedError(param.kind)

                if arg.type is None and arg.default not in (None, False): # XXX why false?
                    arg.type = type(arg.default)

                output_args[arg.name] = arg

            return output_args

        def __call__(self, *args, **kwargs):
            from .commands import _plano_command, PlanoCommand
            assert isinstance(_plano_command, PlanoCommand), _plano_command

            app = _plano_command
            command = app.bound_commands[self.name]

            if command is not self:
                # The command bound to this name has been overridden.
                # This happens when a parent command invokes a peer
                # command that is overridden.

                command(*args, **kwargs)

                return

            debug("Running {} {} {}".format(self, args, kwargs))

            app.running_commands.append(self)

            dashes = "--" * len(app.running_commands)
            display_args = list(self.get_display_args(args, kwargs))

            with console_color("magenta", file=_sys.stderr):
                eprint("{}> {}".format(dashes, self.name), end="")

                if display_args:
                    eprint(" ({})".format(", ".join(display_args)), end="")

                eprint()

            self.function(*args, **kwargs)

            cprint("<{} {}".format(dashes, self.name), color="magenta", file=_sys.stderr)

            app.running_commands.pop()

            if app.running_commands:
                name = app.running_commands[-1].name

                cprint("{}| {}".format(dashes[:-2], name), color="magenta", file=_sys.stderr)

        def get_display_args(self, args, kwargs):
            for i, arg in enumerate(self.args.values()):
                if arg.positional:
                    if arg.multiple:
                        for va in args[i:]:
                            yield repr(va)
                    elif arg.optional:
                        value = args[i]

                        if value == arg.default:
                            continue

                        yield repr(value)
                    else:
                        yield repr(args[i])
                else:
                    value = kwargs.get(arg.name, arg.default)

                    if value == arg.default:
                        continue

                    if value in (True, False):
                        value = str(value).lower()
                    else:
                        value = repr(value)

                    yield "{}={}".format(arg.display_name, value)

    if _function is None:
        return Command
    else:
        return Command(_function)

def parent(*args, **kwargs):
    try:
        f_locals = _inspect.stack()[2].frame.f_locals
        parent_fn = f_locals["self"].parent.function
    except:
        fail("Missing parent command")

    parent_fn(*args, **kwargs)

class CommandArgument:
    def __init__(self, name, display_name=None, type=None, metavar=None, help=None, short_option=None, default=None, positional=None):
        self.name = name
        self.display_name = nvl(display_name, self.name.replace("_", "-"))
        self.type = type
        self.metavar = nvl(metavar, self.display_name.upper())
        self.help = help
        self.short_option = short_option
        self.default = default
        self.positional = positional

        self.optional = False
        self.multiple = False

    def __repr__(self):
        return "argument '{}' (default {})".format(self.name, repr(self.default))

# Patch the default help text
def _capitalize_help(parser):
    try:
        for action in parser._actions:
            if action.help and action.help is not _argparse.SUPPRESS:
                action.help = capitalize(action.help)
    except: # pragma: nocover
        pass

def _main(): # pragma: nocover
    PlanoCommand().main()
