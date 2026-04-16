# Docker Local Setup

`compose.local.yml` starts the local service dependencies documented for the MVP:

- PostgreSQL
- Redis
- Qdrant
- Ollama

Use the top-level Makefile:

```sh
make infra-up
make infra-logs
make infra-down
```
