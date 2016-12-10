DESTDIR := ""
PREFIX := ${HOME}/.local
home = ${PREFIX}/share/qtools

export PATH := ${PWD}/install/bin:${PATH}

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
	scripts/configure-files -a qtools_home=${home} bin/*.in build/bin

.PHONY: install
install: build
	scripts/install-files build/bin ${DESTDIR}${PREFIX}/bin
	scripts/install-files --name \*.py python ${DESTDIR}${home}/python

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
