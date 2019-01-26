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

.NOTPARALLEL:

DESTDIR := ""
PREFIX := /usr/local
INSTALLED_QTOOLS_HOME = ${PREFIX}/share/qtools

VIRTUALENV_ENABLED := 1

export QTOOLS_HOME = ${CURDIR}/build/qtools
export PATH := ${CURDIR}/build/bin:${PATH}
export PYTHONPATH := ${QTOOLS_HOME}/python:${CURDIR}/python:${PYTHONPATH}

VERSION := $(shell cat VERSION.txt)

BIN_SOURCES := $(shell find bin -type f -name \*.in)
BIN_TARGETS := ${BIN_SOURCES:%.in=build/%}

PYTHON_SOURCES := $(shell find python -type f -name \*.py)
PYTHON_TARGETS := ${PYTHON_SOURCES:%=build/qtools/%} ${PYTHON_SOURCES:%.in=build/qtools/%}

.PHONY: default
default: build

.PHONY: help
help:
	@echo "build          Build the code"
	@echo "install        Install the code"
	@echo "clean          Clean up the source tree"
	@echo "test           Run the tests"

.PHONY: clean
clean:
	find python -type f -name \*.pyc -delete
	find python -type d -name __pycache__ -delete
	rm -rf build

.PHONY: build
build: ${BIN_TARGETS} ${PYTHON_TARGETS} build/prefix.txt
	scripts/smoke-test

.PHONY: install
install: build
	scripts/install-files build/bin ${DESTDIR}$$(cat build/prefix.txt)/bin
	scripts/install-files build/qtools ${DESTDIR}$$(cat build/prefix.txt)/share/qtools

.PHONY: test
test: build
	scripts/test ${VIRTUALENV_ENABLED}

.PHONY: big-test
big-test: test test-centos test-centos-6 test-fedora test-ubuntu test-ubuntu-xenial

.PHONY: test-centos
test-centos:
	sudo docker build -f scripts/test-centos.dockerfile -t ${USER}/qtools-test-centos --build-arg CACHE_BUST=$${RANDOM} .
	sudo docker run --rm ${USER}/qtools-test-centos

.PHONY: test-centos-6
test-centos-6:
	sudo docker build -f scripts/test-centos-6.dockerfile -t ${USER}/qtools-test-centos-6 --build-arg CACHE_BUST=$${RANDOM} .
	sudo docker run --rm ${USER}/qtools-test-centos-6

.PHONY: test-fedora
test-fedora:
	sudo docker build -f scripts/test-fedora.dockerfile -t ${USER}/qtools-test-fedora --build-arg CACHE_BUST=$${RANDOM} .
	sudo docker run --rm ${USER}/qtools-test-fedora

.PHONY: test-ubuntu
test-ubuntu:
	sudo docker build -f scripts/test-ubuntu.dockerfile -t ${USER}/qtools-test-ubuntu --build-arg CACHE_BUST=$${RANDOM} .
	sudo docker run --rm ${USER}/qtools-test-ubuntu

.PHONY: test-ubuntu-xenial
test-ubuntu-xenial:
	sudo docker build -f scripts/test-ubuntu-xenial.dockerfile -t ${USER}/qtools-test-ubuntu-xenial --build-arg CACHE_BUST=$${RANDOM} .
	sudo docker run --rm ${USER}/qtools-test-ubuntu-xenial

.PHONY: test-ubuntu-trusty
test-ubuntu-trusty:
	sudo docker build -f scripts/test-ubuntu-trusty.dockerfile -t ${USER}/qtools-test-ubuntu-trusty --build-arg CACHE_BUST=$${RANDOM} .
	sudo docker run --rm ${USER}/qtools-test-ubuntu-trusty

build/prefix.txt:
	echo ${PREFIX} > build/prefix.txt

build/bin/%: bin/%.in
	scripts/configure-file -a qtools_home=${INSTALLED_QTOOLS_HOME} $< $@

build/qtools/python/qtools/%: python/qtools/% python/qtools/common.py python/brokerlib.py python/commandant.py python/plano.py
	@mkdir -p ${@D}
	cp $< $@

build/qtools/python/%: python/%
	@mkdir -p ${@D}
	cp $< $@

.PHONY: update-%
update-%:
	curl "https://raw.githubusercontent.com/ssorj/$*/master/python/$*.py" -o python/$*.py
