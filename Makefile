PROJECT = youtube_dl_tiny_grpc
PROTOS_DIR_SOURCE := protos
PROTOS_DIR_TARGET := $(PROJECT)/protobuf
DOCKER_EXTRA_ARGS :=
IMAGENAME := ghcr.io/someone-stole-my-name/youtube-dl-tiny-grpc

all: clean test build

clean:
	rm -rf dist
	rm -rf $(PROJECT).egg-info
	rm -rf $(PROTOS_DIR_TARGET)/$(PROJECT)_pb2_grpc.py
	rm -rf $(PROTOS_DIR_TARGET)/$(PROJECT)_pb2.py

install_requires:
	python3 -c "import configparser; c = configparser.ConfigParser(); c.read('setup.cfg'); print(c['options']['install_requires'])" | xargs pip install

build: install_requires pb
	pip install build twine wheel
	python3 -m build -n
	twine check dist/*

flake:
	pip install flake8
	flake8 $(PROJECT) --exclude protobuf

test: install_requires pb flake
	python test/test_youtube_dl_tiny_grpc.py

$(PROTOS_DIR_TARGET)/$(PROJECT)_pb2_grpc.py:
	python -m grpc_tools.protoc -I$(PROTOS_DIR_SOURCE) --grpc_python_out=$(PROJECT)/protobuf $(PROTOS_DIR_SOURCE)/$(PROJECT).proto

$(PROTOS_DIR_TARGET)/$(PROJECT)_pb2.py:
	python -m grpc_tools.protoc -I$(PROTOS_DIR_SOURCE) --python_out=$(PROJECT)/protobuf $(PROTOS_DIR_SOURCE)/$(PROJECT).proto

pb-dep:
	pip install grpcio-tools
pb: pb-dep $(PROTOS_DIR_TARGET)/$(PROJECT)_pb2_grpc.py
pb: pb-dep $(PROTOS_DIR_TARGET)/$(PROJECT)_pb2.py

ci-deps:
	apt-get -qq -y install \
		binfmt-support \
		ca-certificates \
		curl \
		git \
		gnupg \
		lsb-release \
		qemu-user-static \
		wget \
		jq

ci-deps-docker: ci-deps
	curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg && \
	echo "deb [arch=$(shell dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian $(shell lsb_release -cs) stable" |\
	tee /etc/apt/sources.list.d/docker.list > /dev/null && \
	cat /etc/apt/sources.list.d/docker.list && \
	apt-get update && \
	apt-get -qq -y install \
		docker-ce \
		docker-ce-cli \
		containerd.io

ci-setup-buildx: ci-deps-docker
	docker run --privileged --rm tonistiigi/binfmt --install all
	docker buildx create --name mybuilder
	docker buildx use mybuilder

push: ci-setup-buildx build
	docker buildx build --platform linux/amd64 -t $(IMAGENAME):latest . --push
	docker buildx build --platform linux/amd64 -t $(IMAGENAME):$(shell git describe --tags --abbrev=0) . --push

docker-%: # Run a make command in a container
	docker run \
		--rm \
		--privileged \
		-v /var/run/docker.sock:/var/run/docker.sock \
		-v $(shell pwd):/data \
		-w /data $(DOCKER_EXTRA_ARGS) \
		python:3.9-slim sh -c "apt-get update && apt-get install make git -y && make $*"
