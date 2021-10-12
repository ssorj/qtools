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

from commandant import TestSkipped
from plano import *
from subprocess import PIPE

home_dir = get_parent_dir(get_parent_dir(get_parent_dir(__file__)))
test_cert_dir = join(home_dir, "test-certs")
version_file = join(home_dir, "VERSION.txt")

def start_qmessage(args, **kwargs):
    return start(f"qmessage --verbose {args}", **kwargs)

def start_qsend(url, args, **kwargs):
    return start(f"qsend --verbose {url} {args}", **kwargs)

def start_qreceive(url, args, **kwargs):
    return start(f"qreceive --verbose {url} {args}", **kwargs)

def start_qrequest(url, args, **kwargs):
    return start(f"qrequest --verbose {url} {args}", **kwargs)

def start_qrespond(url, args, **kwargs):
    return start(f"qrespond --verbose {url} {args}", **kwargs)

def run_qsend_and_qreceive(url, qmessage_args="", qsend_args="", qreceive_args="--count 1"):
    with temp_file() as output:
        message_proc = start_qmessage(qmessage_args, stdout=PIPE)
        send_proc = start_qsend(url, qsend_args, stdin=message_proc.stdout)
        receive_proc = start_qreceive(url, qreceive_args, stdout=output)

        try:
            wait(message_proc)
            wait(send_proc)
            wait(receive_proc)
        except:
            kill(message_proc)
            kill(send_proc)
            kill(receive_proc)

            raise

        return read(output)[:-1]

def run_qrequest_and_qrespond(url, qmessage_args="", qrequest_args="", qrespond_args="--count 1"):
    with temp_file() as output:
        message_proc = start_qmessage(qmessage_args, stdout=PIPE)
        request_proc = start_qrequest(url, qrequest_args, stdin=message_proc.stdout, stdout=output)
        respond_proc = start_qrespond(url, qrespond_args)

        try:
            wait(message_proc)
            wait(request_proc)
            wait(respond_proc)
        except:
            kill(message_proc)
            kill(request_proc)
            kill(respond_proc)

            raise

        return read(output)[:-1]

class TestServer:
    def __init__(self, **extra_args):
        port = get_random_port()
        args = " ".join(["--{} {}".format(k, v) for k, v in extra_args.items()])

        self.proc = start(f"qbroker --verbose --port {port} {args}")
        self.proc.url = f"//localhost:{port}/queue1"

    def __enter__(self):
        return self.proc

    def __exit__(self, exc_type, exc_value, traceback):
        stop(self.proc)

@test(timeout=5)
def version():
    result = call("qconnect --version")
    assert result == read(version_file), (result, read(version_file))

@test(timeout=5)
def logging():
    result = call("qconnect --version")
    assert result

    run("qconnect --init-only --quiet")
    run("qconnect --init-only --verbose")
    run("qconnect --init-only --debug")

@test(timeout=5)
def ready_file():
    def await_ready(temp):
            while True:
                with open(temp) as f:
                    if f.read() == "ready\n":
                        break

                sleep(0.2)

    with TestServer() as server:
        with temp_file() as temp:
            proc = start_qsend(server.url, "--ready-file {}".format(temp))
            await_ready(temp)
            kill(proc)

        with temp_file() as temp:
            proc = start_qreceive(server.url, "--ready-file {}".format(temp))
            await_ready(temp)
            kill(proc)

@test(timeout=20)
def qconnect():
    with TestServer() as server:
        run(f"qconnect --verbose {server.url}")

        try:
            run("qconnect --verbose no-such-host")
        except:
            pass

@test(timeout=5)
def qsend_and_qreceive():
    with TestServer() as server:
        result = run_qsend_and_qreceive(server.url, "--body abc123", "", "--count 1")
        assert result == "abc123", result

        run_qsend_and_qreceive(server.url, "", "--presettled")
        run_qsend_and_qreceive(server.url, "", "abc xyz", "--count 2")
        run_qsend_and_qreceive(server.url, "--count 10", "", "--count 10")
        run_qsend_and_qreceive(server.url, "--count 10 --rate 1000", "", "--count 10")

@test(timeout=5)
def qrequest_and_qrespond():
    with TestServer() as server:
        result = run_qrequest_and_qrespond(server.url, "--body abc123", "", "--count 1 --reverse --upper --append ' and this'")
        assert result == "321CBA and this", result

        run_qrequest_and_qrespond(server.url, "", "abc xyz", "--count 2")
        run_qrequest_and_qrespond(server.url, "--count 10", "", "--count 10")
        run_qrequest_and_qrespond(server.url, "--count 10 --rate 1000", "", "--count 10")

@test(timeout=5)
def qmessage():
    with TestServer() as server:
        run_qsend_and_qreceive(server.url, "--id m1 --correlation-id c1")
        run_qsend_and_qreceive(server.url, "--user ssorj")
        run_qsend_and_qreceive(server.url, "--to xyz --reply-to abc")
        run_qsend_and_qreceive(server.url, "--durable")
        run_qsend_and_qreceive(server.url, "--priority 100")
        run_qsend_and_qreceive(server.url, "--ttl 100.1")
        run_qsend_and_qreceive(server.url, "--body hello")
        run_qsend_and_qreceive(server.url, "--property x y --property a b")

@test(timeout=5)
def sasl():
    with TestServer() as server:
        run_qsend_and_qreceive(server.url, "", "--sasl-mechs anonymous --user harry", "--sasl-mechs anonymous --user sally --count 1")

    # with TestServer(user="harold", password="x") as server:
    #     body = run_qsend_and_qreceive(server.url, "--body abc123", "--user harold --password x", "--count 1 --user harold --password x")
    #     assert body == "abc123", body

@test(timeout=5)
def tls():
    server_cert = join(test_cert_dir, "server-cert.pem")
    server_key = join(test_cert_dir, "server-key.pem")
    client_cert = join(test_cert_dir, "client-cert.pem")
    client_key = join(test_cert_dir, "client-key.pem")
    client_cert_and_key = join(test_cert_dir, "client-cert-and-key.pem")

    with TestServer(cert=server_cert, key=server_key) as server:
        client_args = "--tls --trust {}".format(server_cert)
        qreceive_args = "{} --count 1".format(client_args)

        run_qsend_and_qreceive(server.url, qsend_args=client_args, qreceive_args=qreceive_args)

    with TestServer(cert=server_cert, key=server_key, trust=client_cert) as server:
        client_args = "--tls --cert {} --key {} --trust {}".format(client_cert, client_key, server_cert)
        qreceive_args = "{} --count 1".format(client_args)

        run_qsend_and_qreceive(server.url, qsend_args=client_args, qreceive_args=qreceive_args)

    with TestServer(cert=server_cert, key=server_key, trust=client_cert) as server:
        client_args = "--tls --cert {} --trust {}".format(client_cert_and_key, server_cert)
        qreceive_args = "{} --count 1".format(client_args)

        run_qsend_and_qreceive(server.url, qsend_args=client_args, qreceive_args=qreceive_args)
