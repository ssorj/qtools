# Qtools

    qsend [//DOMAIN/]ADDRESS -m MESSAGE
    qreceive [//DOMAIN/]ADDRESS
    qrequest [//DOMAIN/]ADDRESS -r REQUEST
    qrespond [//DOMAIN/]ADDRESS
    qbroker [--host HOST] [--port PORT]

## Dependencies

 - make
 - python-qpid-proton

## Ubuntu

Qtools requires a newer version of python-qpid-proton than Ubuntu
provides by default.  Use these commands to install from the Ubuntu
PPA.

    $ sudo add-apt-repository ppa:qpid/released
    $ apt-get install software-properties-common
    $ add-apt-repository ppa:qpid/released
    $ apt-get upgrade python-qpid-proton
