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

After stack startup, pull the generation model configured in `OLLAMA_MODEL` (default: `SpeakLeash/bielik-11b-v2.3-instruct:Q4_K_M`):

```sh
docker compose --env-file .env.example --env-file .env.docker.example --env-file .env --env-file .env.docker -f infra/docker/compose.local.yml exec ollama ollama pull SpeakLeash/bielik-11b-v2.3-instruct:Q4_K_M
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

## Using host Ollama with Bielik Q4_K_M

If you want to run Ollama on the host machine (outside Docker) and let the backend container use it, follow these steps.

1. Install Ollama on host:

```sh
curl -fsSL https://ollama.com/install.sh | sh
```

For macOS, you can also install the official app from [ollama.com](https://ollama.com/).

2. Start Ollama on host:

```sh
ollama serve
```

3. Pull the model on host:

```sh
ollama pull SpeakLeash/bielik-11b-v2.3-instruct:Q4_K_M
```

4. Verify host runtime and model:

```sh
ollama list
ollama run SpeakLeash/bielik-11b-v2.3-instruct:Q4_K_M
```

5. Configure `.env.docker` to point backend to host Ollama:

```env
OLLAMA_HOST=host.docker.internal
OLLAMA_PORT=11434
OLLAMA_HOST_PORT=11435
OLLAMA_MODEL=SpeakLeash/bielik-11b-v2.3-instruct:Q4_K_M
OLLAMA_TIMEOUT_SECONDS=120
```

`OLLAMA_HOST=host.docker.internal` makes containerized backend connect to the host machine. `OLLAMA_PORT` is the Ollama service port on host. `OLLAMA_HOST_PORT` is only the published port for the optional Docker `ollama` service and can stay at `11435` to avoid collisions with host Ollama.
