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
