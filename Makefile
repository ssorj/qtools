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
	@echo "devel          Build, install, and test in this checkout"

.PHONY: clean
clean:
	find python -type f -name \*.pyc -delete
	find python -type d -name __pycache__ -delete
	rm -rf build
	rm -rf install

.PHONY: build
build:
	scripts/configure-file bin/qbroker.in build/bin/qbroker qtools_home ${QTOOLS_HOME}
	scripts/configure-file bin/qsend.in build/bin/qsend qtools_home ${QTOOLS_HOME}
	scripts/configure-file bin/qreceive.in build/bin/qreceive qtools_home ${QTOOLS_HOME}
	scripts/configure-file bin/qexec.in build/bin/qexec qtools_home ${QTOOLS_HOME}

.PHONY: install
install: build
	scripts/install-files python ${DESTDIR}${QTOOLS_HOME}/python \*.py
	scripts/install-executable build/bin/qbroker ${DESTDIR}${PREFIX}/bin/qbroker
	scripts/install-executable build/bin/qsend ${DESTDIR}${PREFIX}/bin/qsend
	scripts/install-executable build/bin/qreceive ${DESTDIR}${PREFIX}/bin/qreceive
	scripts/install-executable build/bin/qexec ${DESTDIR}${PREFIX}/bin/qexec

.PHONY: devel
devel: PREFIX := ${PWD}/install
devel: clean install
	qbroker --help
	qexec --help
