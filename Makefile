.PHONY: infra-up infra-build infra-down infra-logs backend-test frontend-test

COMPOSE_FILE := infra/docker/compose.local.yml
COMPOSE_ENV_FILES := --env-file .env.example --env-file .env.docker.example

ifneq ("$(wildcard .env)","")
COMPOSE_ENV_FILES += --env-file .env
endif

ifneq ("$(wildcard .env.local)","")
COMPOSE_ENV_FILES += --env-file .env.local
endif

ifneq ("$(wildcard .env.docker)","")
COMPOSE_ENV_FILES += --env-file .env.docker
endif

COMPOSE := docker compose $(COMPOSE_ENV_FILES) -f $(COMPOSE_FILE)

infra-up:
	$(COMPOSE) up -d

infra-build:
	$(COMPOSE) build

infra-down:
	$(COMPOSE) down

infra-logs:
	$(COMPOSE) logs -f

backend-test:
	cd backend && pytest

frontend-test:
	cd frontend && npm test
