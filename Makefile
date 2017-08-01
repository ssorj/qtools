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

DESTDIR := ""
PREFIX := ${HOME}/.local
QTOOLS_HOME = ${PREFIX}/share/qtools

export PATH := install/bin:${PATH}
export PYTHONPATH := python

.PHONY: default
default: devel

.PHONY: help
help:
	@echo "build          Build the code"
	@echo "install        Install the code"
	@echo "clean          Clean up the source tree"
	@echo "devel          Build, install, and run a basic test in this checkout"
	@echo "test           Run the tests"

.PHONY: clean
clean:
	find python -type f -name \*.pyc -delete
	find python -type d -name __pycache__ -delete
	rm -rf build
	rm -rf install

.PHONY: build
build:
	scripts/configure-files -a qtools_home=${QTOOLS_HOME} bin/*.in build/bin

.PHONY: install
install: build
	scripts/install-files build/bin ${DESTDIR}${PREFIX}/bin
	scripts/install-files -n \*.py python ${DESTDIR}${QTOOLS_HOME}/python

.PHONY: devel
devel: PREFIX := ${PWD}/install
devel: install
	scripts/run-smoke-tests

.PHONY:
test: devel
	qtools-test

.PHONY: big-test
big-test: test test-centos test-fedora test-ubuntu

.PHONY: test-centos
test-centos:
	sudo docker build -f scripts/Dockerfile.test-centos -t ${USER}/qtools-test-centos .
	sudo docker run ${USER}/qtools-test-centos

.PHONY: test-fedora
test-fedora:
	sudo docker build -f scripts/Dockerfile.test-fedora -t ${USER}/qtools-test-fedora .
	sudo docker run ${USER}/qtools-test-fedora

.PHONY: test-ubuntu
test-ubuntu:
	sudo docker build -f scripts/Dockerfile.test-ubuntu -t ${USER}/qtools-test-ubuntu .
	sudo docker run ${USER}/qtools-test-ubuntu

.PHONY: update-%
update-%:
	curl "https://raw.githubusercontent.com/ssorj/$*/master/python/$*.py" -o python/$*.py
