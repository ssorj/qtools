# Qtools

Command-line tools for sending and receiving AMQP messages.

    % qbroker localhost:5672 &
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

## Programs

 - qbroker HOST:PORT
 - qsend [//HOST:PORT/]PATH MESSAGE-BODY
 - qreceive [//HOST:PORT]/PATH
 - qcall [//HOST:PORT/]PATH MESSAGE-BODY

## Dependencies

 - python
 - python-qpid-proton
