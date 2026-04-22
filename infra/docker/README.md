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

ss

After stack startup, pull the generation model configured in `OLLAMA_MODEL` (default: `SpeakLeash/bielik-11b-v2.3-instruct:Q8_0`):

```sh
docker compose --env-file .env.example --env-file .env.docker.example --env-file .env --env-file .env.docker -f infra/docker/compose.local.yml exec ollama ollama pull SpeakLeash/bielik-11b-v2.3-instruct:Q8_0
```

All backend and frontend project commands should run inside containers. This keeps dependency versions, service hostnames, and environment loading aligned with the Docker stack.

Backend examples::

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

If port `11434` is already in use on the host (for example by a local Ollama process), set `OLLAMA_HOST_PORT=11435` in `.env.docker`. Keep `OLLAMA_PORT=11434` unchanged so backend-to-ollama communication inside Docker still works.
