export PATH := ${PWD}/install/bin:${PATH}

DESTDIR := ""
PREFIX := ${HOME}/.local
QUIVER_HOME = ${PREFIX}/share/quiver

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
	scripts/configure-file bin/qexec.in build/bin/qexec quiver_home ${QUIVER_HOME}

.PHONY: install
install: build
	scripts/install-files python ${DESTDIR}${PREFIX}${QUIVER_HOME}/python \*.py
	scripts/install-executable build/bin/qexec ${DESTDIR}${PREFIX}/bin/qexec

.PHONY: devel
devel: PREFIX := ${PWD}/install
devel: clean install
	which qexec
	qexec --help
