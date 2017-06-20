# Qtools

    qsend [//HOST:PORT/]ADDRESS -m MESSAGE
    qreceive [//HOST:PORT/]ADDRESS
    qrequest [//HOST:PORT/]ADDRESS -r REQUEST
    qrespond [//HOST:PORT/]ADDRESS
    qbroker [--host HOST] [--port PORT]

## Common arguments

`qsend`, `qreceive`, `qrequest`, and `qrespond` take one or more
`ADDRESS-URL` arguments.

 - `ADDRESS-URL`

`qsend` and `qrequest` take ....

## qsend

## qreceive

## qrequest

## qrespond

## qbroker

## Dependencies

 - python-qpid-proton

## Ubuntu

    $ sudo add-apt-repository ppa:qpid/released
    $ apt-get install software-properties-common
    $ add-apt-repository ppa:qpid/released
    $ apt-get upgrade python-qpid-proton
