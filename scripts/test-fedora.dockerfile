#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#

FROM fedora
MAINTAINER Justin Ross <jross@apache.org>

RUN dnf -qy --setopt deltarpm=0 update && dnf -q clean all

RUN dnf -qy --setopt deltarpm=0 install findutils make python-qpid-proton && dnf -q clean all

COPY . /root/qtools

RUN cd /root/qtools && make install PREFIX=/usr

WORKDIR /root
CMD ["qtools-test"]
