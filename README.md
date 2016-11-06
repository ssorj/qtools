# Qtools

Command-line tools for sending and receiving AMQP messages.

## Arguments

- DOMAIN (HOST[:PORT])
- ADDRESS ([//DOMAIN/]PATH)
- -m, --messages COUNT
- --verbose
- --quiet

## Programs

- qbroker HOST:PORT
- qsend //HOST:PORT/PATH MESSAGE-BODY
- qreceive //HOST:PORT/PATH

## Scenario 1

    % qbroker &
    % qsend q0 "Hello!"
    qbroker: Received message "Hello!"
    qbroker: Created queue "q0"
    qbroker: Stored message "Hello!" in queue "q0"
    qbroker: Queue "q0" has 1 message
    % qsend q0 "Hello again!"
    qbroker: Received message "Hello again!"
    qbroker: Stored message "Hello again!" in queue "q0"
    qbroker: Queue "q0" has 2 messages
    % qreceive q0
    qbroker: ...
    Hello!
    % qreceive q0
    qbroker: ...
    Hello again!

## Ideas

- qsend q0 --interactive
- qreceive q0 --interactive - accept or reject
- qreceive q0 --drain

## Dependencies

- python
- python-qpid-proton
