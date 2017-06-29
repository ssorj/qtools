FROM registry.access.redhat.com/rhel7-atomic
MAINTAINER Hugo Guerrero "hguerrer@redhat.com"

ADD jross.repo /etc/yum.repos.d/

RUN rpm --import https://copr-be.cloud.fedoraproject.org/results/jross/ssorj/pubkey.gpg

# Install all dependencies
RUN microdnf --enablerepo=rhel-7-server-rpms \
  --enablerepo=a-mq-clients-1-for-rhel-7-server-rpms \
  install qtools \
  --nodocs; \
  microdnf clean all

# Run
CMD ["/bin/bash"]
