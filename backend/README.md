# Backend

FastAPI backend for the ourRAG MVP.

This directory will contain the API, domain services, database integration, storage adapters, queue adapters, and worker entry points. Business logic is intentionally not implemented in this skeleton phase.

Planned layout:

```text
app/
  api/
  core/
  domain/
  infrastructure/
  workers/
tests/
```

Initial local commands:

```sh
python -m venv .venv
pip install -e ".[dev]"
pytest
```

Configuration is loaded from environment variables using `.env` and `.env.<environment>` files at the repository root. See `.env.example` and `docs/CONFIGURATION.md`.
