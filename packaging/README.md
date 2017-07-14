# Packaging

## Docker

#### RHEL Atomic base image

You can build the Docker image based on RHEL Atomic and run the
environment with the following commands:

    $ docker build -t <user>/qtools-rhel docker/rhel

*Note: you must build the image in a correctly entitled host system.*

    $ docker run -it <user>/qtools-rhel
