.PHONY: help init infra-up infra-build infra-down infra-logs infra-ps ollama-refresh backend-shell backend-run backend-test db-upgrade db-downgrade db-current db-revision frontend-shell frontend-run frontend-test

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

help:
	@echo "Infrastructure:"
	@echo "  make init                     Build and fully initialize local stack"
	@echo "  make infra-build              Build local Docker images"
	@echo "  make infra-up                 Start the local stack"
	@echo "  make infra-down               Stop the local stack"
	@echo "  make infra-logs               Follow all container logs"
	@echo "  make infra-ps                 Show container status"
	@echo "  make ollama-refresh           Rebuild Ollama and pull OLLAMA_MODEL"
	@echo ""
	@echo "Backend commands run inside the backend container:"
	@echo "  make backend-shell            Open a shell in backend"
	@echo "  make backend-run CMD='...'    Run an arbitrary backend command"
	@echo "  make backend-test             Run backend tests"
	@echo "  make db-upgrade               Apply Alembic migrations"
	@echo "  make db-downgrade             Roll back one Alembic migration"
	@echo "  make db-current               Show current Alembic revision"
	@echo "  make db-revision MSG='...'    Create an Alembic migration revision"
	@echo ""
	@echo "Frontend commands run inside the frontend container:"
	@echo "  make frontend-shell           Open a shell in frontend"
	@echo "  make frontend-run CMD='...'   Run an arbitrary frontend command"
	@echo "  make frontend-test            Run frontend tests"

init: infra-build infra-up db-upgrade
	@echo "Initialization complete. Stack is running and migrations are applied."

infra-up:
	$(COMPOSE) up -d

infra-build:
	$(COMPOSE) build

infra-down:
	$(COMPOSE) down

infra-logs:
	$(COMPOSE) logs -f

infra-ps:
	$(COMPOSE) ps

ollama-refresh:
	@test -n "$(OLLAMA_MODEL)" || (echo "Usage: make ollama-refresh OLLAMA_MODEL='bielik'"; exit 1)
	$(COMPOSE) up -d --build ollama
	$(COMPOSE) exec ollama ollama pull "$(OLLAMA_MODEL)"

backend-shell:
	$(COMPOSE) exec backend sh

backend-run:
	@test -n "$(CMD)" || (echo "Usage: make backend-run CMD='python -m pytest'"; exit 1)
	$(COMPOSE) exec backend sh -lc "$(CMD)"

backend-test:
	$(COMPOSE) exec backend pytest

db-upgrade:
	$(COMPOSE) exec backend alembic upgrade head

db-downgrade:
	$(COMPOSE) exec backend alembic downgrade -1

db-current:
	$(COMPOSE) exec backend alembic current

db-revision:
	@test -n "$(MSG)" || (echo "Usage: make db-revision MSG='describe change'"; exit 1)
	$(COMPOSE) exec backend alembic revision --autogenerate -m "$(MSG)"

frontend-shell:
	$(COMPOSE) exec frontend sh

frontend-run:
	@test -n "$(CMD)" || (echo "Usage: make frontend-run CMD='npm run build'"; exit 1)
	$(COMPOSE) exec frontend sh -lc "$(CMD)"

frontend-test:
	$(COMPOSE) exec frontend npm test
