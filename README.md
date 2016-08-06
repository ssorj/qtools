# Quiver

## Arguments

- ADDRESS
- HOST
- PORT
- --verbose

## Programs

- qbroker --host HOST --port PORT --verbose
- qsend ADDRESS MESSAGE
- qreceive ADDRESS COUNT

## Scenario 1

    % qbroker &
    % qsend test0 "Hello!"
    qbroker: Received message "Hello!"
    qbroker: Created queue "test0"
    qbroker: Stored message "Hello!" in queue "test0"
    qbroker: Queue "test0" has 1 message
    % qsend test0 "Hello again!"
    qbroker: Received message "Hello again!"
    qbroker: Stored message "Hello again!" in queue "test0"
    qbroker: Queue "test0" has 2 messages
    % qreceive test0
    qbroker: ...
    Hello!
    % qreceive test0
    qbroker: ...
    Hello again!

## Ideas

- qsend test0 --interactive
- qreceive test0 100 or qreceive test0 --count 100
- qreceive test0 --interactive - accept or reject
- qreceive test0 --drain
- qexec ADDRESS COMMAND

## Dependencies

- python3
- python3-qpid-proton
