# Qtools

[![Build Status](https://travis-ci.org/ssorj/qtools.svg?branch=master)](https://travis-ci.org/ssorj/qtools)

    $ qreceive amqp://example.net/queue1 --count 1 &
    $ qsend amqp://example.net/queue1 --message hello

    $ qrespond amqp://example.net/requests &
    $ qrequest amqp://example.net/requests < requests.txt

    $ qmessage --count 10 | qsend amqp://example.net/queue1
    $ qmessage --rate 1 | qrequest amqp://example.net/requests

## Installation

For more ways to build and use Docker images and packages, see
[the packaging README](packaging).

### Dependencies

 - findutils
 - make
 - python-qpid-proton
 - python3-qpid-proton
 - python-argparse (required only on RHEL 6)

### Using Docker

    $ sudo docker run -it ssorj/qtools

### Installing on Fedora

    $ sudo dnf install dnf-plugins-core
    $ sudo dnf copr enable jross/ssorj
    $ sudo dnf install qtools

If you don't have `dnf`, use the repo files at
<https://copr.fedorainfracloud.org/coprs/jross/ssorj/>.

### Installing on RHEL 7

    $ cd /etc/yum.repos.d && sudo wget https://copr.fedorainfracloud.org/coprs/jross/ssorj/repo/epel-7/jross-ssorj-epel-7.repo
    $ sudo yum install qtools

### Installing on Ubuntu

Qtools requires a newer version of python-qpid-proton than Ubuntu
provides by default.  Use these commands to install it from an Ubuntu
PPA.

    $ sudo apt-get install software-properties-common
    $ sudo add-apt-repository ppa:qpid/released
    $ sudo apt-get update
    $ sudo apt-get install make python-qpid-proton

After this you can install from source.

### Installing from source

By default, installs from source go to `$HOME/.local`.  Make sure
`$HOME/.local/bin` is in your path.

    $ cd quiver/
    $ make install

Use the `PREFIX` option to change the install location.

    $ sudo make install PREFIX=/usr/local

## Command-line interface

### Common arguments

The core commands take one or more URLs.  These indicate the location
of a message source or target, such as a queue or topic.

    qsend ADDRESS-URL [ADDRESS-URL ...]

An address URL has optional scheme and server parts.  The default
scheme is 'amqp', and the default server is '127.0.0.1:5672'.  You
can use the `--server` option to change the default server.

    [SCHEME:][//SERVER/]ADDRESS

The send and request commands take message content on standard input
(one message per line) or via the `--message` option.  The `--message`
option can be repeated.

The receive and respond commands run forever unless you use the
`--count` option to tell them to stop after processing a given number
of messages or requests.

Tools that read from or write to the console take the following
options:

    --input FILE          Read input from FILE
    --output FILE         Write output to FILE

With a few exceptions, all the tools share these options:

    -h, --help            Print help output
    --verbose             Print detailed logging
    --quiet               Print no logging

### The `qsend` and `qreceive` commands

These commands perform one-way message transfers.

    qsend URL [URLS] [OPTIONS] [< messages.txt]
    qreceive URL [URLS] [OPTIONS] [> messages.txt]

    qsend URL --message MESSAGE

    qreceive URL --count 1
    -> MESSAGE

The send command reads messages, one per line, from standard input.
Alternatively, you can input messages using the `--message` option.
The receive command prints each message it receives to standard
output.

Typical usage:

    $ qsend amqp://example.net/queue1 --message m1 &
    $ qreceive amqp://example.net/queue1
    queue1: m1

### The `qrequest` and `qrespond` commands

The request command sends a request and waits for a response.  The
respond command listens for requests, processes them, and sends
responses.

    qrequest URL [URLS] [OPTIONS] [< requests.txt] [> responses.txt]
    qrespond URL [URLS] [OPTIONS]

    qrequest URL --message REQUEST
    -> RESPONSE

    qrespond URL --count 1

The request command reads request messages from standard input and
writes responses to standard output.

Typical usage:

    $ qrespond amqp://example.net/jobs --upper &
    $ qrequest amqp://example.net/jobs --message abc
    ABC

### The `qmessage` command

This command generates message content for use by the `qsend` and
`qrequest` tools.

    qmessage [OPTIONS] | {qsend,qrequest}

    qmessage --id ID --body CONTENT
    -> MESSAGE

    qmessage --count 3
    -> MESSAGE
    -> MESSAGE
    -> MESSAGE

The output is in JSON format.  The send and request tools can consume
it.  Usually you pipe it in, like this:

    $ qmessage | qsend queue1
    $ qmessage --rate 1 | qrequest amqp://example.net/jobs

### The `qbroker` command

This is a simple broker implementation that you can use for testing.

    qbroker [--host HOST] [--port PORT]
