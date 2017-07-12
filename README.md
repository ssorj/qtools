# Qtools

    qsend [SCHEME:][//SERVER/]ADDRESS --message MESSAGE

    qreceive [SCHEME:][//SERVER/]ADDRESS --count 1
    -> MESSAGE

    qrequest [SCHEME:][//SERVER/]ADDRESS --message REQUEST
    -> RESPONSE

    qrespond [SCHEME:][//SERVER/]ADDRESS --count 1

    qmessage --count 1 --id ID --body CONTENT
    -> MESSAGE

    qbroker [--host HOST] [--port PORT]

## Common arguments

The 'qsend', 'qreceive', 'qrequest', and 'qrespond' commands take one
or more URLs.  These indicate the location of a message source or
target, such as a queue or topic.

    qsend ADDRESS-URL [ADDRESS-URL ...]

An address URL has optional scheme and server parts.  The default
scheme is 'amqp' and 'server' is '127.0.0.1:5672'.

    [SCHEME:][//SERVER/]ADDRESS

With a few exceptions, all the tools share these options.

    -h, --help            Print help output
    --verbose             Print detailed logging
    --quiet               Print no logging

Tools that read from or write to the console take these options.

    -i, --input FILE      Read input from FILE
    -o, --output FILE     Write output to FILE

## Installation

### Dependencies

 - make
 - python-qpid-proton

### Docker

    $ docker run -it ssorj/qtools

### Docker (RHEL Atomic base image)

    You can build the Docker image based on RHEL Atomic and run the environment with the following commands:

    `docker build -t <myuser>/qtools-rhel docker/rhel-7`

    *you must build the image in a correctly entitled host system*

    `docker run -it <myuser>/qtools-rhel`

### Fedora 25

    $ sudo dnf install dnf-plugins-core
    $ sudo dnf copr enable jross/ssorj
    $ sudo dnf install qtools

### RHEL 7

    $ cd /etc/yum.repos.d && sudo wget https://copr.fedorainfracloud.org/coprs/jross/ssorj/repo/epel-7/jross-ssorj-epel-7.repo
    $ sudo yum install qtools

### Ubuntu 16.04

Qtools requires a newer version of python-qpid-proton than Ubuntu
provides by default.  Use these commands to install it from an Ubuntu
PPA.

    $ sudo apt-get install software-properties-common
    $ sudo add-apt-repository ppa:qpid/released
    $ sudo apt-get upgrade python-qpid-proton

After this you can install from source.

### Installing from source

    $ sudo make install PREFIX=/usr/local

<!--
(while true; do echo message; sleep 1; done) | qsend //amqp.zone/q0
-->
