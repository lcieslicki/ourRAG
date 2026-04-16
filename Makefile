.PHONY: infra-up infra-down infra-logs backend-test frontend-test

COMPOSE_FILE := infra/docker/compose.local.yml

infra-up:
	docker compose -f $(COMPOSE_FILE) up -d

infra-down:
	docker compose -f $(COMPOSE_FILE) down

infra-logs:
	docker compose -f $(COMPOSE_FILE) logs -f

backend-test:
	cd backend && pytest

frontend-test:
	cd frontend && npm test
