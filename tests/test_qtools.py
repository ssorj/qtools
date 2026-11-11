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

import json
import shutil
import socket
import subprocess
import tempfile
import time
from pathlib import Path

import pytest

COMMANDS = ("qbroker", "qconnect", "qmessage", "qreceive", "qrequest", "qrespond", "qsend")

test_cert_dir = Path(__file__).resolve().parent / "testcerts"

@pytest.fixture(scope="session", autouse=True)
def check_commands():
    missing = [name for name in COMMANDS if shutil.which(name) is None]

    if missing:
        pytest.skip("Qtools commands not installed: {}".format(", ".join(missing)))

def command(args):
    args = list(args)
    args[0] = shutil.which(args[0]) or args[0]
    return [str(x) for x in args]

def start(args, **kwargs):
    return subprocess.Popen(command(args), text=True, **kwargs)

def wait(proc, timeout=60):
    proc.wait(timeout=timeout)
    assert proc.returncode == 0, "{} exited with code {}".format(proc.args[0], proc.returncode)
    return proc

def stop(proc, timeout=10):
    if proc.poll() is None:
        proc.terminate()

    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()

    if proc.stdin is not None:
        proc.stdin.close()

def run(args, *, check=True, timeout=None, **kwargs):
    return subprocess.run(command(args), check=check, timeout=timeout, text=True, **kwargs)

def call(args, *, timeout=None):
    return run(args, stdout=subprocess.PIPE, timeout=timeout).stdout

def get_random_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("localhost", 0))
        return sock.getsockname()[1]

def await_file(proc, path, timeout=30):
    deadline = time.time() + timeout

    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError("Process exited with code {} before file {} appeared".format \
                               (proc.returncode, path))

        try:
            if Path(path).read_text() == "ready\n":
                return
        except FileNotFoundError:
            pass

        time.sleep(0.05)

    raise TimeoutError("Timed out waiting for file {}".format(path))

def start_qmessage(args=(), **kwargs):
    return start(["qmessage", "--verbose", *args], **kwargs)

def start_qsend(url, args=(), **kwargs):
    return start(["qsend", "--verbose", url, *args], **kwargs)

def start_qreceive(url, args=(), **kwargs):
    return start(["qreceive", "--verbose", url, *args], **kwargs)

def start_qrequest(url, args=(), **kwargs):
    return start(["qrequest", "--verbose", url, *args], **kwargs)

def start_qrespond(url, args=(), **kwargs):
    return start(["qrespond", "--verbose", url, *args], **kwargs)

def run_qsend_and_qreceive(url, qmessage_args=(), qsend_args=(), qreceive_args=("--count", "1")):
    with tempfile.TemporaryDirectory(prefix="qtools-") as temp_dir:
        output = Path(temp_dir, "output")

        with open(output, "w") as out:
            message_proc = start_qmessage(qmessage_args, stdout=subprocess.PIPE)
            message_stdout = message_proc.stdout
            send_proc = start_qsend(url, qsend_args, stdin=message_stdout)
            message_stdout.close()
            receive_proc = start_qreceive(url, qreceive_args, stdout=out)

            try:
                wait(message_proc)
                wait(send_proc)
                wait(receive_proc)
            except BaseException:
                for proc in (message_proc, send_proc, receive_proc):
                    stop(proc)

                raise

        return output.read_text()[:-1]

def run_qrequest_and_qrespond(url, qmessage_args=(), qrequest_args=(), qrespond_args=("--count", "1")):
    with tempfile.TemporaryDirectory(prefix="qtools-") as temp_dir:
        output = Path(temp_dir, "output")

        with open(output, "w") as out:
            message_proc = start_qmessage(qmessage_args, stdout=subprocess.PIPE)
            message_stdout = message_proc.stdout
            request_proc = start_qrequest(url, qrequest_args, stdin=message_stdout, stdout=out)
            message_stdout.close()
            respond_proc = start_qrespond(url, qrespond_args)

            try:
                wait(message_proc)
                wait(request_proc)
                wait(respond_proc)
            except BaseException:
                for proc in (message_proc, request_proc, respond_proc):
                    stop(proc)

                raise

        return output.read_text()[:-1]

class BrokerServer:
    def __init__(self, **extra_args):
        self.port = get_random_port()
        self.url = "//localhost:{}/queue1".format(self.port)
        self.temp_dir = tempfile.TemporaryDirectory(prefix="qtools-")
        self.ready_file = Path(self.temp_dir.name, "ready")
        self.proc = None

        self.args = ["qbroker", "--verbose", "--port", str(self.port),
                     "--ready-file", str(self.ready_file)]

        for name, value in extra_args.items():
            self.args.extend(["--{}".format(name.replace("_", "-")), str(value)])

    def __enter__(self):
        self.proc = start(self.args)

        try:
            await_file(self.proc, self.ready_file)
        except BaseException:
            self.__exit__(None, None, None)
            raise

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.proc is not None:
            stop(self.proc)

        self.temp_dir.cleanup()

def test_version():
    output = call(["qconnect", "--version"])
    assert output.strip()

def test_logging():
    output = call(["qconnect", "--version"])
    assert output

    run(["qconnect", "--init-only", "--quiet"])
    run(["qconnect", "--init-only", "--verbose"])
    run(["qconnect", "--init-only", "--debug"])

def test_ready_file(tmp_path):
    with BrokerServer() as server:
        ready = tmp_path / "send-ready"
        proc = start_qsend(server.url, ["--ready-file", str(ready)], stdin=subprocess.PIPE)

        try:
            await_file(proc, ready)
        finally:
            stop(proc)

        ready = tmp_path / "receive-ready"
        proc = start_qreceive(server.url, ["--ready-file", str(ready)])

        try:
            await_file(proc, ready)
        finally:
            stop(proc)

def test_qconnect():
    with BrokerServer() as server:
        run(["qconnect", "--verbose", server.url])

    # A failed connection should terminate with a non-zero exit code.
    proc = run(["qconnect", "--verbose", "no-such-host"], check=False, timeout=20)
    assert proc.returncode != 0

@pytest.mark.tls
def test_connect_config(tmp_path, monkeypatch):
    server_cert = test_cert_dir / "server-cert.pem"
    server_key = test_cert_dir / "server-key.pem"
    client_cert_and_key = test_cert_dir / "client-cert-and-key.pem"

    with BrokerServer(cert=server_cert, key=server_key) as server:
        config = {
            "scheme": "amqps",
            "host": "localhost",
            "port": server.port,
            "tls": {
                "cert": str(client_cert_and_key),
                "key": str(client_cert_and_key),
                "ca": str(server_cert),
                "verify": False,
            },
        }

        config_file = tmp_path / "connect.json"
        config_file.write_text(json.dumps(config))
        output = tmp_path / "output"

        monkeypatch.setenv("MESSAGING_CONNECT_FILE", str(config_file))

        with open(output, "w") as out:
            run(["qconnect", "--verbose"], stdout=out, stderr=subprocess.STDOUT)

        log = output.read_text()
        assert "Connected to server" in log, log

def test_connect_config_messaging(tmp_path, monkeypatch):
    with BrokerServer() as server:
        config = {
            "scheme": "amqp",
            "host": "localhost",
            "port": server.port,
        }

        config_file = tmp_path / "connect.json"
        config_file.write_text(json.dumps(config))

        monkeypatch.setenv("MESSAGING_CONNECT_FILE", str(config_file))

        result = run_qsend_and_qreceive("queue1", ("--body", "abc123"))
        assert result == "abc123", result

        result = run_qrequest_and_qrespond("queue1", ("--body", "abc123"), (),
                                           ("--count", "1", "--reverse", "--upper"))
        assert result == "321CBA", result

def test_qsend_and_qreceive():
    with BrokerServer() as server:
        result = run_qsend_and_qreceive(server.url, ("--body", "abc123"))
        assert result == "abc123", result

        run_qsend_and_qreceive(server.url, qsend_args=("--presettled",))
        run_qsend_and_qreceive(server.url, qsend_args=("abc", "xyz"), qreceive_args=("--count", "2"))
        run_qsend_and_qreceive(server.url, ("--count", "10"), (), ("--count", "10"))
        run_qsend_and_qreceive(server.url, ("--count", "10", "--rate", "1000"), (), ("--count", "10"))

def test_qsend_direct_messages_ignore_stdin():
    with BrokerServer() as server:
        with tempfile.TemporaryFile("w+") as stdin:
            stdin.write("from stdin\n")
            stdin.flush()
            stdin.seek(0)

            with tempfile.TemporaryDirectory(prefix="qtools-") as temp_dir:
                output = Path(temp_dir, "output")

                with open(output, "w") as out:
                    receive_proc = start_qreceive(server.url, ("--count", "1"), stdout=out)
                    send_proc = start_qsend(server.url, ("hello",), stdin=stdin)

                    try:
                        wait(send_proc)
                        wait(receive_proc)
                    except BaseException:
                        stop(send_proc)
                        stop(receive_proc)
                        raise

                assert output.read_text() == "hello\n"
                assert stdin.tell() == 0

def test_qrequest_and_qrespond():
    with BrokerServer() as server:
        result = run_qrequest_and_qrespond(server.url, ("--body", "abc123"), (),
                                           ("--count", "1", "--reverse", "--upper",
                                            "--append", " and this"))
        assert result == "321CBA and this", result

        run_qrequest_and_qrespond(server.url, qrequest_args=("abc", "xyz"),
                                  qrespond_args=("--count", "2"))
        run_qrequest_and_qrespond(server.url, ("--count", "10"), (), ("--count", "10"))
        run_qrequest_and_qrespond(server.url, ("--count", "10", "--rate", "1000"), (), ("--count", "10"))

def test_qrequest_direct_messages_ignore_stdin():
    with BrokerServer() as server:
        with tempfile.TemporaryFile("w+") as stdin:
            stdin.write("from stdin\n")
            stdin.flush()
            stdin.seek(0)

            with tempfile.TemporaryDirectory(prefix="qtools-") as temp_dir:
                output = Path(temp_dir, "output")

                with open(output, "w") as out:
                    respond_proc = start_qrespond(server.url, ("--count", "1"), stdout=subprocess.DEVNULL)
                    request_proc = start_qrequest(server.url, ("hello",), stdin=stdin, stdout=out)

                    try:
                        wait(request_proc)
                        wait(respond_proc)
                    except BaseException:
                        stop(request_proc)
                        stop(respond_proc)
                        raise

                assert output.read_text() == "hello\n"
                assert stdin.tell() == 0

def test_qmessage():
    with BrokerServer() as server:
        run_qsend_and_qreceive(server.url, ("--id", "m1", "--correlation-id", "c1"))
        run_qsend_and_qreceive(server.url, ("--user", "ssorj"))
        run_qsend_and_qreceive(server.url, ("--to", "xyz", "--reply-to", "abc"))
        run_qsend_and_qreceive(server.url, ("--durable",))
        run_qsend_and_qreceive(server.url, ("--priority", "100"))
        run_qsend_and_qreceive(server.url, ("--ttl", "100.1"))
        run_qsend_and_qreceive(server.url, ("--body", "hello"))
        run_qsend_and_qreceive(server.url, ("--property", "x", "y", "--property", "a", "b"))

def test_sasl():
    with BrokerServer() as server:
        run_qsend_and_qreceive(server.url, (),
                               ("--sasl-mechs", "anonymous", "--user", "harry"),
                               ("--sasl-mechs", "anonymous", "--user", "sally", "--count", "1"))

    # with BrokerServer(user="harold", password="x") as server:
    #     body = run_qsend_and_qreceive(server.url, ("--body", "abc123"),
    #                                   ("--user", "harold", "--password", "x"),
    #                                   ("--count", "1", "--user", "harold", "--password", "x"))
    #     assert body == "abc123", body

@pytest.mark.tls
def test_tls():
    server_cert = test_cert_dir / "server-cert.pem"
    server_key = test_cert_dir / "server-key.pem"
    client_cert = test_cert_dir / "client-cert.pem"
    client_key = test_cert_dir / "client-key.pem"
    client_cert_and_key = test_cert_dir / "client-cert-and-key.pem"

    with BrokerServer(cert=server_cert, key=server_key) as server:
        client_args = ("--tls", "--trust", str(server_cert))
        qreceive_args = (*client_args, "--count", "1")

        run_qsend_and_qreceive(server.url, qsend_args=client_args, qreceive_args=qreceive_args)

    with BrokerServer(cert=server_cert, key=server_key, trust=client_cert) as server:
        client_args = ("--tls", "--cert", str(client_cert), "--key", str(client_key),
                       "--trust", str(server_cert))
        qreceive_args = (*client_args, "--count", "1")

        run_qsend_and_qreceive(server.url, qsend_args=client_args, qreceive_args=qreceive_args)

    with BrokerServer(cert=server_cert, key=server_key, trust=client_cert) as server:
        client_args = ("--tls", "--cert", str(client_cert_and_key), "--trust", str(server_cert))
        qreceive_args = (*client_args, "--count", "1")

        run_qsend_and_qreceive(server.url, qsend_args=client_args, qreceive_args=qreceive_args)
