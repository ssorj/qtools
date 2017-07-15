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

import argparse
import sys

from plano import *

def start_message(args="", **kwargs):
    return start_process("qmessage --verbose {}", args, **kwargs)

def start_send(url, args="", **kwargs):
    return start_process("qsend --verbose {} {}", url, args, **kwargs)

def start_receive(url, args="", **kwargs):
    return start_process("qreceive --verbose {} {}", url, args, **kwargs)

def start_request(url, args="", **kwargs):
    return start_process("qrequest --verbose {} {}", url, args, **kwargs)

def start_respond(url, args="", **kwargs):
    return start_process("qrespond --verbose {} {}", url, args, **kwargs)

def test_send_receive_args(out, url, message_args="", send_args="", receive_args="--count 1"):
    message_proc = start_message(message_args, stdout=PIPE, stderr=out)
    send_proc = start_send(url, stdin=message_proc.stdout, stderr=out)
    receive_proc = start_receive(url, receive_args, stdout=PIPE, stderr=out)

    try:
        check_process(message_proc)
        check_process(send_proc)
        check_process(receive_proc)
    except CalledProcessError:
        terminate_process(message_proc)
        terminate_process(send_proc)
        terminate_process(receive_proc)

        raise

    output = receive_proc.communicate()[0]

    return output[:-1]

def test_request_respond_args(out, url, message_args="", request_args="", respond_args="--count 1"):
    message_proc = start_message(message_args, stdout=PIPE, stderr=out)
    request_proc = start_request(url, stdin=message_proc.stdout, stdout=PIPE, stderr=out)
    respond_proc = start_respond(url, respond_args, stderr=out)

    try:
        check_process(message_proc)
        check_process(request_proc)
        check_process(respond_proc)
    except CalledProcessError:
        terminate_process(message_proc)
        terminate_process(request_proc)
        terminate_process(respond_proc)

        raise

    output = request_proc.communicate()[0]

    return output[:-1]

def test_send_receive(out, url):
    body = test_send_receive_args(out, url, "--body abc123", "", "--count 1 --no-prefix")
    assert body == "abc123", body

    test_send_receive_args(out, url, "", "--presettled")
    test_send_receive_args(out, url, "--count 10", "", "--count 10")
    test_send_receive_args(out, url, "--count 10 --rate 1000", "", "--count 10")

def test_request_respond(out, url):
    body = test_request_respond_args(out, url, "--body abc123", "", "--count 1 --reverse --upper --append ' and this'")
    assert body == "321CBA and this", body

    test_request_respond_args(out, url, "", "--presettled")
    test_request_respond_args(out, url, "--count 10", "", "--count 10")
    test_request_respond_args(out, url, "--count 10 --rate 1000", "", "--count 10")

def test_message(out, url):
    test_send_receive_args(out, url, "--id m1 --correlation-id c1")
    test_send_receive_args(out, url, "--user ssorj")
    test_send_receive_args(out, url, "--to xyz --reply-to abc")
    test_send_receive_args(out, url, "--durable")
    test_send_receive_args(out, url, "--priority 100")
    test_send_receive_args(out, url, "--ttl 100.1")
    test_send_receive_args(out, url, "--body hello")
    test_send_receive_args(out, url, "--property x y --property a b")

def run_test(name, *args):
    sys.stdout.write("{:.<73} ".format(name + " "))

    namespace = globals()
    function = namespace["test_{}".format(name)]

    output_file = make_temp_file()

    try:
        with open(output_file, "w") as out:
            function(out, *args)
    except CalledProcessError:
        print("FAILED")

        for line in read_lines(output_file):
            eprint("> {}".format(line), end="")

        return 1

    print("PASSED")

    return 0

def main():
    set_message_threshold("warn")

    parser = argparse.ArgumentParser()
    parser.add_argument("url", metavar="ADDRESS-URL", nargs="?",
                        help="An AMQP message address to test against")

    args = parser.parse_args()

    url = args.url
    server = None

    if url is None:
        port = random_port()
        url = "//127.0.0.1:{}/q1".format(port)
        server = start_process("qbroker --quiet --port {}", port)

    try:
        failures = 0
        failures += run_test("send_receive", url)
        failures += run_test("request_respond", url)
        failures += run_test("message", url)
    finally:
        if server is not None:
            stop_process(server)

    if failures == 0:
        print("All tests passed")
    else:
        exit("Some tests failed")
