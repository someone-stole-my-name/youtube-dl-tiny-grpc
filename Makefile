PROJECT = youtube_dl_tiny_grpc
TRIVY_VERSION := 0.24.2
PROTOS_DIR := protos
DOCKER_EXTRA_ARGS :=
BUILDARG_PLATFORM := --platform linux/amd64,linux/arm64/v8
IMAGENAME := ghcr.io/someone-stole-my-name/youtube-dl-tiny-grpc

clean:
	rm -rf dist
	rm -rf $(PROJECT)/youtube_dl_tiny_grpc_pb2_grpc.py
	rm -rf $(PROJECT)/youtube_dl_tiny_grpc_pb2.py

build:
	docker buildx build $(BUILDARG_PLATFORM) -t $(IMAGENAME):latest .
	docker buildx build --load -t $(IMAGENAME):latest .

push: grpc
	docker buildx build $(BUILDARG_PLATFORM) -t $(IMAGENAME):latest . --push
	docker buildx build $(BUILDARG_PLATFORM) -t $(IMAGENAME):$(shell git describe --tags --abbrev=0) . --push

$(PROJECT)/protobuf/youtube_dl_tiny_grpc_pb2_grpc.py:
	python3 -m grpc_tools.protoc -I$(PROTOS_DIR) --grpc_python_out=$(PROJECT)/protobuf $(PROTOS_DIR)/$(PROJECT).proto

$(PROJECT)/protobuf/youtube_dl_tiny_grpc_pb2.py:
	python3 -m grpc_tools.protoc -I$(PROTOS_DIR) --python_out=$(PROJECT)/protobuf $(PROTOS_DIR)/$(PROJECT).proto

dev:
	python3 -m venv venv
	source venv/bin/activate
	pip install -r requirements.txt

grpc: $(PROJECT)/protobuf/youtube_dl_tiny_grpc_pb2_grpc.py
grpc: $(PROJECT)/protobuf/youtube_dl_tiny_grpc_pb2.py
# grpc:
# 	find $(PROJECT)/protobuf -type f -name "*.py" -print0 | xargs -0 gsed -i -e 's, import '"$target"'_pb2, from . import '"$target"'_pb2, g'

trivy:
	trivy i \
		--ignore-unfixed \
		--exit-code 1 \
		$(IMAGENAME):latest

test-int-start:
	docker kill youtube_dl || true
	docker rm youtube_dl || true
	docker run --rm -d --name youtube_dl -p 50051:50051 $(IMAGENAME):latest
	sleep 5

test-int-run: IP=$(subst ",,$(shell docker inspect youtube_dl | jq '.[0].NetworkSettings.IPAddress'))
test-int-run:
	find $(SRC_DIR) -name 'test*py' -exec sh -c 'python3 {} "$(IP)"' \;

test-int: test-int-start test-int-run

flake:
	flake8 $(PROJECT) --exclude protobuf

test: grpc build trivy test-int

docker-%:
	docker run \
		--rm \
		--privileged \
		-v /var/run/docker.sock:/var/run/docker.sock \
		-v $(shell pwd):/data \
		-w /data $(DOCKER_EXTRA_ARGS) \
		debian:stable sh -c "apt-get update && apt-get install make && make ci-prepare && make $*"

ci-deps:
	apt-get -qq -y install \
		binfmt-support \
		ca-certificates \
		curl \
		git \
		gnupg \
		jq \
		lsb-release \
		python3 \
		python3-pip \
		qemu-user-static \
		wget
	pip3 install -r requirements.txt
	pip3 install flake8

ci-deps-docker:
	curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg && \
	echo "deb [arch=$(shell dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian $(shell lsb_release -cs) stable" |\
	tee /etc/apt/sources.list.d/docker.list > /dev/null && \
	cat /etc/apt/sources.list.d/docker.list && \
	apt-get update && \
	apt-get -qq -y install \
		docker-ce \
		docker-ce-cli \
		containerd.io

ci-deps-trivy:
	wget https://github.com/aquasecurity/trivy/releases/download/v$(TRIVY_VERSION)/trivy_$(TRIVY_VERSION)_Linux-64bit.deb && \
	dpkg -i trivy_$(TRIVY_VERSION)_Linux-64bit.deb

ci-setup-buildx:
	docker run --privileged --rm tonistiigi/binfmt --install all
	docker buildx create --name mybuilder
	docker buildx use mybuilder

ci-prepare: ci-deps ci-deps-docker ci-deps-trivy ci-setup-buildx
