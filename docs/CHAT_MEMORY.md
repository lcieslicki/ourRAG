# Chat Memory

## Goal

Chat memory is a core product feature.

The system must allow users to:

- continue a topic naturally,
- ask follow-up questions,
- refer back to earlier context in the same conversation,
- avoid repeating full context each time.

## Memory model

Use a two-layer memory strategy.

### 1. Recent messages
Keep a rolling window of the most recent turns.

Purpose:
- preserve short-term dialogue continuity,
- support follow-up references such as "and what about that case?".

### 2. Conversation summary
Maintain a compact rolling summary of older conversation context.

Purpose:
- preserve relevant context without endlessly growing prompt size,
- reduce token pressure for local models.

## Why not include the full conversation every time

For a local smaller model, full-history prompting will become:

- slow,
- expensive in tokens,
- less reliable,
- more vulnerable to context dilution.

Therefore memory must be curated, not dumped.

## Recommended strategy

### Recent window
Start with:
- last 6–10 turns.

### Summary refresh
Generate or refresh summary:
- after a configurable number of turns,
- after topic shifts,
- after long conversations.

## Prompt memory package

PromptBuilder should receive:

- conversation summary,
- recent messages,
- current user message,
- retrieved document chunks.

## Memory isolation rules

Mandatory rules:

- memory belongs to one conversation only,
- conversation belongs to one workspace only,
- memory must never cross workspace boundaries,
- when user switches workspace, they are not continuing the same conversation context unless they explicitly open another conversation in that workspace.

## Summary generation

Summary should capture:

- topics discussed,
- assumptions stated by the user,
- document references already used,
- unresolved questions,
- temporary conversation context needed for follow-up questions.

Summary should avoid:

- copying full raw dialogue,
- storing unnecessary verbosity,
- storing internal implementation metadata inside user-facing content.

## Example memory behavior

Conversation:

1. User asks about vacation policy.
2. Assistant answers using HR handbook.
3. User asks "and what about vacation on demand?"

The system should preserve enough memory to understand that "what about" still refers to the HR topic unless retrieval or scope suggests otherwise.

## Failure prevention

Memory must not:

- override explicit retrieved facts,
- manufacture unavailable facts,
- leak previous workspace content,
- silently persist incorrect assumptions forever.

## Testing priorities

Memory testing must cover:

- topic continuity,
- summary refresh logic,
- recent window truncation,
- token budget handling,
- cross-workspace isolation,
- interaction with explicit scope filters.
