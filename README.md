# Qtools

    qsend URL [URLS] [OPTIONS] [< messages.txt]
    qreceive URL [URLS] [OPTIONS] [> messages.txt]

    $ qreceive amqp://amqp.zone/queue1 --count 1 &
    $ qsend amqp://amqp.zone/queue1 --message hello

    qrequest URL [URLS] [OPTIONS] [< requests.txt] [> responses.txt]
    qrespond URL [URLS] [OPTIONS]

    $ qrespond amqp://amqp.zone/requests &
    $ qrequest amqp://amqp.zone/requests < requests.txt

    qmessage [OPTIONS] | {qsend,qrequest}

    $ qmessage --count 10 | qsend amqp://amqp.zone/queue1
    $ qmessage --rate 1 | qrequest amqp://amqp.zone/requests

## Installation

### Dependencies

 - make
 - python-qpid-proton

### Using Docker images

    $ docker run -it ssorj/qtools

### Using Fedora packages

    $ sudo dnf install dnf-plugins-core
    $ sudo dnf copr enable jross/ssorj
    $ sudo dnf install qtools

### Using RHEL 7 packages

    $ cd /etc/yum.repos.d && sudo wget https://copr.fedorainfracloud.org/coprs/jross/ssorj/repo/epel-7/jross-ssorj-epel-7.repo
    $ sudo yum install qtools

### Using Ubuntu packages

Qtools requires a newer version of python-qpid-proton than Ubuntu
provides by default.  Use these commands to install it from an Ubuntu
PPA.

    $ sudo apt-get install software-properties-common
    $ sudo add-apt-repository ppa:qpid/released
    $ sudo apt-get upgrade python-qpid-proton

After this you can install from source.

### Installing from source

    $ sudo make install PREFIX=/usr/local

## Command-line interface

### Common arguments

The core commands take one or more URLs.  These indicate the location
of a message source or target, such as a queue or topic.

    qsend ADDRESS-URL [ADDRESS-URL ...]

An address URL has optional scheme and server parts.  The default
scheme is 'amqp' and 'server' is '127.0.0.1:5672'.

    [SCHEME:][//SERVER/]ADDRESS

With a few exceptions, all the tools share the following options.

    -h, --help            Print help output
    --verbose             Print detailed logging
    --quiet               Print no logging

Tools that read from or write to the console take these options.

    --input FILE          Read input from FILE
    --output FILE         Write output to FILE

## Unfiled

    qsend [SCHEME:][//SERVER/]ADDRESS --message MESSAGE

    qreceive [SCHEME:][//SERVER/]ADDRESS --count 1
    -> MESSAGE

    qrequest [SCHEME:][//SERVER/]ADDRESS --message REQUEST
    -> RESPONSE

    qrespond [SCHEME:][//SERVER/]ADDRESS --count 1

    qmessage --count 1 --id ID --body CONTENT
    -> MESSAGE

    qbroker [--host HOST] [--port PORT]
