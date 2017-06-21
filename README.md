# Qtools

    qsend [//DOMAIN/]ADDRESS -m MESSAGE
    qreceive [//DOMAIN/]ADDRESS
    qrequest [//DOMAIN/]ADDRESS -r REQUEST
    qrespond [//DOMAIN/]ADDRESS
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
