.PHONY: build test install clean upload image-build image-test image-push

build:
	python -m build

test: build
	python -m pip install --force-reinstall dist/ssorj_qtools-*.whl
	python -m pytest

install: build
	python -m pip install --user --force-reinstall dist/ssorj_qtools-*.whl

clean:
	rm -rf build dist src/*.egg-info .pytest_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +

upload:
	python -m build
	python -m twine upload --repository testpypi dist/*

image-build:
	docker build -f Containerfile -t ssorj/qtools .

image-test: build
	docker run -it ssorj/qtools

image-push: build
	docker login quay.io
	docker tag ssorj/qtools quay.io/ssorj/qtools
	docker push quay.io/ssorj/qtools
