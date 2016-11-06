export PATH := ${PWD}/install/bin:${PATH}

DESTDIR := ""
PREFIX := ${HOME}/.local
QTOOLS_HOME = ${PREFIX}/share/qtools

.PHONY: default
default: devel

.PHONY: help
help:
	@echo "build          Build the code"
	@echo "install        Install the code"
	@echo "clean          Clean up the source tree"
	@echo "devel          Build, install, and sanity test in this checkout"
	@echo "test           Run the tests"

.PHONY: clean
clean:
	find python -type f -name \*.pyc -delete
	find python -type d -name __pycache__ -delete
	rm -rf build
	rm -rf install

.PHONY: build
build:
	scripts/configure-file bin/qbroker.in build/bin/qbroker qtools_home ${QTOOLS_HOME}
	scripts/configure-file bin/qping.in build/bin/qping qtools_home ${QTOOLS_HOME}
	scripts/configure-file bin/qsend.in build/bin/qsend qtools_home ${QTOOLS_HOME}
	scripts/configure-file bin/qreceive.in build/bin/qreceive qtools_home ${QTOOLS_HOME}
	scripts/configure-file bin/qdrain.in build/bin/qdrain qtools_home ${QTOOLS_HOME}

.PHONY: install
install: build
	scripts/install-files python ${DESTDIR}${QTOOLS_HOME}/python \*.py
	scripts/install-files build/bin ${DESTDIR}${PREFIX}/bin \*

.PHONY: devel
devel: PREFIX := ${PWD}/install
devel: install
	qbroker --help > /dev/null
	qping --help > /dev/null
	qsend --help > /dev/null
	qreceive --help > /dev/null
	qdrain --help > /dev/null

.PHONY:
test: devel
	scripts/smoke-test
