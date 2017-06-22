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

## Installation

### Dependencies

 - make
 - python-qpid-proton

### Docker

    $ docker run -it ssorj/qtools

### Fedora 25

    $ sudo dnf install dnf-plugins-core
    $ sudo dnf copr enable jross/ssorj
    $ sudo dnf install qtools

### RHEL 7

    $ cd /etc/yum.repos.d && sudo wget https://copr.fedorainfracloud.org/coprs/jross/ssorj/repo/epel-7/jross-ssorj-epel-7.repo
    $ sudo dnf install qtools

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
