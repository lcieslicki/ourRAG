# Fixtures

## Purpose

Fixtures support:

- local development,
- integration testing,
- retrieval quality evaluation,
- E2E scenarios.

## Recommended initial fixture set

### Workspaces
Create at least three workspaces:

- `acme_hr`
- `acme_it`
- `beta_legal`

### Users
Create:
- one multi-workspace admin,
- one workspace-limited member,
- one viewer if supported.

### Documents
Prepare markdown documents such as:

- HR handbook
- remote work policy
- IT onboarding guide
- incident reporting process
- legal compliance memo

### Versioning fixtures
At least one document should have:
- version 1,
- version 2,
- version 1 invalidated after version 2 activation.

## Example question set

### HR
- How do I request vacation leave?
- What is the rule for remote work approval?

### IT
- How do I report an incident?
- Where is onboarding described?

### Legal
- Which policy covers compliance reporting?

## Fixture design rules

- keep fixtures small but semantically distinct,
- include overlapping vocabulary across workspaces to validate isolation,
- include category tags such as HR / IT / Legal,
- include at least one follow-up-friendly topic for memory testing.

## Local seed goals

Local seed should make it possible to test:

- upload flow,
- retrieval flow,
- source attribution,
- version invalidation,
- multi-workspace access,
- conversation continuity.

## Storage

Fixtures should include both:
- input markdown files,
- expected retrieval assertions where feasible.
