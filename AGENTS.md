# Repository Guidelines

## Project Structure & Module Organization

This repository currently contains documentation and sample knowledge-base data for an internal RAG-style project.

- `data/firma_ABC/` contains Markdown source documents grouped by business domain in the filename, for example `hr_polityka_urlopowa.md`, `finanse_procedura_zakupow.md`, and `it_polityka_bezpieczenstwa.md`.
- `docs/` contains supporting documentation assets, currently including `overview.png`.
- `.claude/` and `CLAUDE.md` contain assistant-specific guidance. Keep Codex-facing guidance in this `AGENTS.md`.

If application code is added later, place it under a dedicated source directory such as `src/`, and place tests under `tests/` or next to modules using the project language's normal convention.

## Build, Test, and Development Commands

No build system, package manager, or test runner is currently configured. Do not invent commands in documentation or automation until the related tooling exists.

Useful repository checks for the current structure:

```sh
find data -name '*.md'
find docs -maxdepth 1 -type f
```

When adding a runtime, document the canonical commands here, for example `npm test`, `pytest`, `make build`, or `uv run`.

## Coding Style & Naming Conventions

Keep Markdown files concise and structured with clear headings. Use UTF-8 and preserve Polish domain terminology where it appears in source documents.

For knowledge-base files in `data/firma_ABC/`, use lowercase snake_case names with a domain prefix:

```text
hr_praca_zdalna.md
finanse_planowanie_budzetu.md
logistyka_zarzadzanie_magazynem.md
```

If code is introduced, follow the formatter and linting tools configured for that language. Avoid broad refactors unrelated to the requested change.

## Testing Guidelines

There are no tests yet. For document-only changes, verify filenames, Markdown rendering, and that links or image references resolve. For future code, add focused tests for behavior changes and document the test command in this file.

Prefer test names that describe expected behavior, such as `test_retrieves_hr_policy_document` or `shouldReturnMatchingFinanceProcedure`.

## Commit & Pull Request Guidelines

This directory is not currently initialized as a git repository, so there is no existing commit history to follow. Use short, imperative commit messages once git is initialized, for example:

```text
Add HR remote work policy document
Document repository contributor guidelines
```

Pull requests should include a concise description, the reason for the change, verification performed, and screenshots only when visual assets or rendered documentation changed.

## Agent-Specific Instructions

Make small, targeted changes. Match the existing structure, do not rename data files without a clear reason, and surface uncertainty before changing project conventions.
