FROM fedora

MAINTAINER Justin Ross <jross@apache.org>

RUN dnf -y update && dnf clean all

RUN dnf -y install dnf-plugins-core \
    && dnf -y copr enable jross/ssorj \
    && dnf -y install qtools \
    && dnf clean all

CMD ["/bin/bash"]
