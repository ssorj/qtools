# Qtools

[![main](https://github.com/ssorj/qtools/workflows/main/badge.svg)](https://github.com/ssorj/qtools/actions?query=workflow%3Amain)

    $ qsend amqp://example.net/queue1 hello
    $ qreceive amqp://example.net/queue1 --count 1
    hello

    $ qrespond amqp://example.net/requests --upper &
    $ qrequest amqp://example.net/requests hello
    HELLO

    $ qmessage --count 10 | qsend amqp://example.net/queue1
    $ qmessage --rate 1 | qrequest amqp://example.net/requests

## Installation

### Dependencies

 - python3-qpid-proton
 - python3-distutils

### Installing from source

By default, installs from source go to `$HOME/.local`.  Make sure
`$HOME/.local/bin` is in your path.

    $ cd quiver/
    $ ./plano install

Use the `--prefix` option to change the install location.

    $ sudo ./plano install --prefix /usr/local

## Command-line interface

### Common arguments

The messaging commands take a URL indicating the location of a message
source or target, such as a queue or topic.

    qsend URL [MESSAGE ...]

A URL has optional scheme, host, and port parts.  The default scheme
is `amqp`, and the default host and port are `localhost:5672`.

    [SCHEME:][//HOST[:PORT]/]ADDRESS

The send and request commands take message content from the optional
`MESSAGE` arguments (one message per argument) or from standard input
or a file (one message per line).

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
