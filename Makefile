PROJECT = youtube_dl_tiny_grpc
PROTOS_DIR_SOURCE := protos
PROTOS_DIR_TARGET := $(PROJECT)/protobuf
DOCKER_EXTRA_ARGS :=

all: clean test build

clean:
	rm -rf dist
	rm -rf $(PROJECT).egg-info
	rm -rf $(PROTOS_DIR_TARGET)/$(PROJECT)_pb2_grpc.py
	rm -rf $(PROTOS_DIR_TARGET)/$(PROJECT)_pb2.py

install_requires:
	python3 -c "import configparser; c = configparser.ConfigParser(); c.read('setup.cfg'); print(c['options']['install_requires'])" | xargs pip install

build: install_requires pb
	pip install build twine
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

docker-%: # Run a make command in a container
	docker run \
		--rm \
		--privileged \
		-v /var/run/docker.sock:/var/run/docker.sock \
		-v $(shell pwd):/data \
		-w /data $(DOCKER_EXTRA_ARGS) \
		python:3.9-slim sh -c "apt-get update && apt-get install make && make $*"
