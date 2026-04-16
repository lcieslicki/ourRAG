# Docker Local Setup

`compose.local.yml` starts the local development stack documented for the MVP:

- backend
- frontend
- PostgreSQL
- Redis
- Qdrant
- Ollama

Use the top-level Makefile:

```sh
make infra-build
make infra-up
make infra-logs
make infra-down
```

All backend and frontend project commands should run inside containers. This keeps dependency versions, service hostnames, and environment loading aligned with the Docker stack.

Backend examples:

```sh
make backend-shell
make backend-test
make db-upgrade
make db-current
make db-revision MSG="add documents table"
make backend-run CMD="python -m pytest tests/unit"
```

Frontend examples:

```sh
make frontend-shell
make frontend-test
make frontend-run CMD="npm run build"
```

Avoid running commands such as `pytest`, `alembic`, or `npm test` directly on the host unless you are intentionally debugging the host environment.

Create local overrides when needed:

```sh
cp .env.example .env
cp .env.docker.example .env.docker
```

Compose loads checked-in example defaults first, then optional local override files:

```text
.env
.env.local
.env.docker
```

The top-level Makefile passes these files to Docker Compose in that order, so later files override earlier values.
