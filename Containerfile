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

FROM python:alpine AS build

RUN apk add --update gcc musl-dev openssl-dev pkgconfig
RUN pip install --no-cache-dir build

RUN addgroup -S fritz && adduser -S fritz -G fritz
COPY --chown=fritz:fritz . /home/fritz/repo
USER fritz
WORKDIR /home/fritz/repo

RUN python plano install

FROM python:alpine AS run

RUN apk add --update --no-cache openssl

RUN addgroup -S fritz && adduser -S fritz -G fritz
COPY --chown=fritz:fritz --from=build /home/fritz/.local /home/fritz/.local
USER fritz
ENV PATH="/home/fritz/.local/bin:$PATH"

CMD ["/home/fritz/.local/bin/qtools-self-test"]
