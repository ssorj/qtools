# Qtools

[![main](https://github.com/ssorj/qtools/workflows/main/badge.svg)](https://github.com/ssorj/qtools/actions?query=workflow%3Amain)

Qtools is a collection of command-line programs for sending and
receiving AMQP messages.

Start a test broker (or use your own instead):

~~~ shell
$ qbroker
broker-b39f903f: Listening for connections on 'localhost:5672'
~~~

Make a client connection:

~~~
$ qconnect amqp://localhost:5672
qconnect-bcd96594: Connected to server 'broker-b39f903f'
~~~

Send and receive messages:

~~~ shell
$ qsend amqp://localhost:5672/jobs job1
$ qreceive amqp://localhost:5672/jobs --count 1
job1
~~~

Send requests, process them, and return responses:

~~~ shell
$ qrespond amqp://localhost:5672/requests --upper &
$ qrequest amqp://localhost:5672/requests hello
HELLO
~~~

Generate messages of different kinds for sending:

~~~ shell
$ qmessage --count 10 | qsend jobs
$ qmessage --rate 1 | qrequest requests
~~~

## Installation

~~~
pip install --index-url https://test.pypi.org/simple/ ssorj-qtools
~~~

## Command-line interface

### Common arguments

The messaging commands take a URL indicating the location of a message
queue or topic.

    qsend URL [MESSAGE ...]

A URL has optional scheme, host, and port parts.  The default scheme
is `amqp`, and the default host and port are `localhost:5672`.

    [SCHEME:][//HOST[:PORT]/]ADDRESS

The send and request commands take message content from the optional
`MESSAGE` arguments (one message per argument), from standard input
(one message per line), or from a file (one message per line).

The receive and respond commands run forever unless you use the
`--count` option to tell them to stop after processing a given number
of messages.

Tools that read messages from or write messages to the console take
the following options:

    --input FILE          Read messages from FILE
    --output FILE         Write messages to FILE

With a few exceptions, all the tools share these options:

    -h, --help            Show this help message and exit
    --version             Print the Qtools version and exit
    --quiet               Print no logging to the console
    --verbose             Print detailed logging to the console
    --debug               Print debugging output to the console

### The qconnect command

This command is for testing connections to AMQP servers.  It only
connects (or fails to connect).  It doesn't transfer any messages.

    qconnect [OPTIONS] [URL]

Typical usage:

    $ qbroker &
    $ qconnect --verbose
    qconnect-21511c30: Connecting to amqp://localhost:5672
    qconnect-21511c30: Connected to server 'broker-dec74e10'

    $ qbroker --cert cert.pem --key key.pem &
    $ qconnect --tls

    $ qconnect --user alice --password secret amqps://example.net

### The qsend and qreceive commands

These commands perform one-way message transfers.

    qsend [OPTIONS] URL [MESSAGE ...] [< messages.txt]
    qreceive [OPTIONS] URL [URLS] [> messages.txt]

Typical usage:

    $ qbroker &
    $ qsend amqp://localhost/queue1 message1
    $ qreceive amqp://localhost/queue1 --count 1
    message1

### The qrequest and qrespond commands

The request command sends a request and waits for a response.  The
respond command listens for requests, processes them, and sends
responses.

    qrequest [OPTIONS] URL [MESSAGE ...] [< requests.txt] [> responses.txt]
    qrespond [OPTIONS] URL

Typical usage:

    $ qbroker &
    $ qrespond amqp://localhost/jobs --upper --reverse &
    $ qrequest amqp://localhost/jobs abc
    CBA

### The qmessage command

This command generates message inputs for use by the `qsend` and
`qrequest` tools.

    qmessage [OPTIONS] | {qsend,qrequest}

The output is in JSON format.  The send and request tools can consume
it.  Usually you pipe it in, like this:

    $ qmessage | qsend queue1
    $ qmessage --rate 1 | qrequest amqp://example.net/jobs

### The qbroker command

This is a simple broker implementation that you can use for testing.

    qbroker [--host HOST] [--port PORT]

## Using the container image

Pull the Qtools image:

~~~ shell
$ docker pull quay.io/ssorj/qtools
~~~

Run the broker:

~~~ shell
$ docker run -it --net host quay.io/ssorj/qtools qbroker
broker-328b71e8: Listening for connections on 'localhost:5672'
broker-328b71e8: Opened connection from client 'qsend-b01fea78'
broker-328b71e8: Stored Message(priority=4, body='job1') from client 'qsend-b01fea78' on queue 'jobs'
broker-328b71e8: Forwarded Message(priority=4, body='job1') on queue 'jobs' to client 'qreceive-61c5ad0a'
broker-328b71e8: Opened connection from client 'qreceive-61c5ad0a'
~~~

Run client commands:

~~~ shell
$ docker run -it --net host quay.io/ssorj/qtools qsend jobs job1
qsend-b01fea78: Created sender for target 'jobs' on server 'broker-328b71e8'
qsend-b01fea78: Sent 1 message

$ docker run -it --net host quay.io/ssorj/qtools qreceive jobs --count 1
qreceive-61c5ad0a: Created receiver for source 'jobs' on server 'broker-328b71e8'
job1
qreceive-61c5ad0a: Received 1 message
~~~
