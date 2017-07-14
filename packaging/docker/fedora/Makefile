.PHONY: build
build:
	sudo docker build -t ssorj/qtools .

.PHONY: test
test: build
	sudo docker run -t ssorj/qtools /bin/bash -c "qtools-test"

.PHONY: push
push:
	sudo docker push ssorj/qtools
