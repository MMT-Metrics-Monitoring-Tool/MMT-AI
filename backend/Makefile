SHELL := /bin/bash

ENV_FILE ?= ../.env

ifneq (,$(wildcard $(ENV_FILE)))
include $(ENV_FILE)
export
endif

IMAGE_NAME ?= mmt-backend:latest
CONTAINER_NAME ?= mmt-backend
VOLUME_NAME ?= mmt-backend-chroma
NETWORK_NAME ?= mmt-shared

APP_HOST ?= 0.0.0.0
HOST ?= localhost
PORT ?= 8000
HOST_PORT ?= $(PORT)
RELOAD ?= false
PROMPT_DIR ?= prompts
PROMPT_TTL ?= 30
LOAD_STARTUP_DOCUMENTS ?= false

DB_HOST ?= mariadb
DB_PORT ?= 3306
DB_USER ?= my_app
DB_PASS ?= secret
DB_NAME ?= my_app

.PHONY: network run start stop clean

network:
	@docker network inspect $(NETWORK_NAME) >/dev/null 2>&1 || docker network create $(NETWORK_NAME) >/dev/null

run: network
	@if [ ! -f "$(ENV_FILE)" ]; then \
		echo "Missing $(ENV_FILE). Copy env.example to $(ENV_FILE) and fill in the required values."; \
		exit 1; \
	fi
	@docker rm -f $(CONTAINER_NAME) >/dev/null 2>&1 || true
	docker build -t $(IMAGE_NAME) .
	docker run -d \
		--name $(CONTAINER_NAME) \
		--hostname $(CONTAINER_NAME) \
		--network $(NETWORK_NAME) \
		--network-alias $(CONTAINER_NAME) \
		--env-file $(ENV_FILE) \
		--env APP_HOST \
		--env HOST \
		--env PORT \
		--env RELOAD \
		--env PROMPT_DIR \
		--env PROMPT_TTL \
		--env LOAD_STARTUP_DOCUMENTS \
		--env DB_HOST \
		--env DB_PORT \
		--env DB_USER \
		--env DB_PASS \
		--env DB_NAME \
		--publish $(HOST_PORT):$(PORT) \
		--volume $(VOLUME_NAME):/app/chroma_db \
		$(IMAGE_NAME)

start:
	docker start $(CONTAINER_NAME)

stop:
	docker stop $(CONTAINER_NAME)

clean:
	docker rm -f $(CONTAINER_NAME)
	docker image rm $(IMAGE_NAME)
	docker volume rm $(VOLUME_NAME) 
