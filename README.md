# Qtools

Simple command-line tools for sending and receiving AMQP messages.

## Arguments

- ADDRESS
- HOST
- PORT
- --verbose

## Programs

- qbroker --host HOST --port PORT
- qsend ADDRESS MESSAGE
- qreceive ADDRESS COUNT

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
- qexec ADDRESS COMMAND

## Dependencies

- python
- python-qpid-proton
