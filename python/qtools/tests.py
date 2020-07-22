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

from plano import *

def open_test_session(session):
    enable_logging(level="error")
    session.test_timeout = 10

def start_qmessage(args, **kwargs):
    return start_process("qmessage --verbose {0}", args, **kwargs)

def start_qsend(url, args, **kwargs):
    return start_process("qsend --verbose {0} {1}", url, args, **kwargs)

def start_qreceive(url, args, **kwargs):
    return start_process("qreceive --verbose {0} {1}", url, args, **kwargs)

def start_qrequest(url, args, **kwargs):
    return start_process("qrequest --verbose {0} {1}", url, args, **kwargs)

def start_qrespond(url, args, **kwargs):
    return start_process("qrespond --verbose {0} {1}", url, args, **kwargs)

def send_and_receive(url, qmessage_args="", qsend_args="", qreceive_args="--count 1"):
    message_proc = start_qmessage(qmessage_args, stdout=PIPE)
    send_proc = start_qsend(url, qsend_args, stdin=message_proc.stdout)
    receive_proc = start_qreceive(url, qreceive_args, stdout=PIPE)

    try:
        check_process(message_proc)
        check_process(send_proc)
        check_process(receive_proc)
    except CalledProcessError:
        terminate_process(message_proc)
        terminate_process(send_proc)
        terminate_process(receive_proc)

        raise

    receive_proc.stdout.flush() # XXX Hack to see if this fixes periodic empty string output

    output = receive_proc.communicate()[0].decode()

    return output[:-1]

def request_and_respond(url, qmessage_args="", qrequest_args="", qrespond_args="--count 1"):
    message_proc = start_qmessage(qmessage_args, stdout=PIPE)
    request_proc = start_qrequest(url, qrequest_args, stdin=message_proc.stdout, stdout=PIPE)
    respond_proc = start_qrespond(url, qrespond_args)

    try:
        check_process(message_proc)
        check_process(request_proc)
        check_process(respond_proc)
    except CalledProcessError:
        terminate_process(message_proc)
        terminate_process(request_proc)
        terminate_process(respond_proc)

        raise

    receive_proc.stdout.flush() # XXX Hack to see if this fixes periodic empty string output

    output = request_proc.communicate()[0].decode()

    return output[:-1]

class TestServer(object):
    def __init__(self, user=None, password=None):
        port = random_port()

        if user is None:
            assert password is None
            self.proc = start_process("qbroker --verbose --port {0}", port)
        else:
            assert password is not None
            self.proc = start_process("qbroker --verbose --port {0} --user {1} --password {2}",
                                      port, user, password)

        self.proc.url = "//127.0.0.1:{0}/q0".format(port)

    def __enter__(self):
        return self.proc

    def __exit__(self, exc_type, exc_value, traceback):
        stop_process(self.proc)

def test_send_receive(session):
    with TestServer() as server:
        body = send_and_receive(server.url, "--body abc123", "", "--count 1 --no-prefix")
        assert body == "abc123", body

        send_and_receive(server.url, "", "--presettled")
        send_and_receive(server.url, "", "-m abc --message xyz", "--count 2")
        send_and_receive(server.url, "--count 10", "", "--count 10")
        send_and_receive(server.url, "--count 10 --rate 1000", "", "--count 10")
        send_and_receive(server.url, "", "--allowed-mechs anonymous --user harry", "--allowed-mechs anonymous --user sally --count 1")

def disabled_test_user_password_auth(session):
    with TestServer(user="harold", password="x") as server:
        body = send_and_receive(server.url, "--body abc123", "--user harold --password x", "--count 1 --no-prefix --user harold --password x")
        assert body == "abc123", body

def test_request_respond(session):
    with TestServer() as server:
        body = request_and_respond(server.url, "--body abc123", "--no-prefix", "--count 1 --reverse --upper --append ' and this'")
        assert body == "321CBA and this", body

        request_and_respond(server.url, "", "--presettled")
        request_and_respond(server.url, "", "-m abc --message xyz", "--count 2")
        request_and_respond(server.url, "--count 10", "", "--count 10")
        request_and_respond(server.url, "--count 10 --rate 1000", "", "--count 10")
        request_and_respond(server.url, "", "--user harold --password when", "--user maude --password why --count 1")

def test_message(session):
    with TestServer() as server:
        send_and_receive(server.url, "--id m1 --correlation-id c1")
        send_and_receive(server.url, "--user ssorj")
        send_and_receive(server.url, "--to xyz --reply-to abc")
        send_and_receive(server.url, "--durable")
        send_and_receive(server.url, "--priority 100")
        send_and_receive(server.url, "--ttl 100.1")
        send_and_receive(server.url, "--body hello")
        send_and_receive(server.url, "--property x y --property a b")

def test_ready_file(session):
    def wait_for_ready(temp):
            while True:
                with open(temp) as f:
                    if f.read() == "ready\n":
                        break

                sleep(0.2)

    with TestServer() as server:
        with temp_file() as temp:
            proc = start_qsend(server.url, "--ready-file {0}".format(temp))
            wait_for_ready(temp)
            terminate_process(proc)

        with temp_file() as temp:
            proc = start_qreceive(server.url, "--ready-file {0}".format(temp))
            wait_for_ready(temp)
            terminate_process(proc)
