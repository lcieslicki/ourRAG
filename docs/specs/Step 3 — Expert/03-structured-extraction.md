# Spec: Structured Extraction

## Goal
Add a mode that extracts normalized structured data from internal documents instead of only generating conversational answers.

## Baseline assumption
The current system is optimized for chat answers grounded in retrieved chunks. Structured extraction introduces a separate output mode with schema enforcement.

## Scope

### In scope
- extraction mode and API surface
- schema-driven extraction
- JSON validation
- extraction over selected document scope or retrieved chunks
- extraction auditability

### Out of scope
- training custom extraction models
- arbitrary user-defined code execution
- bulk ETL platform features beyond pragmatic local-first support

## Functional requirements

### FR-1 Extraction modes
The system must support at least:
- `extract_from_selected_documents`
- `extract_from_retrieved_context`

### FR-2 Schema definition
Extraction requests must declare a target schema.
Recommended v1 options:
- predefined named schemas in backend config/code
- uploaded or request-provided JSON schema/Pydantic-like schema only if safely validated

### FR-3 Output validation
The backend must validate model output against the target schema and either:
- return a validated structured payload, or
- return a typed extraction failure with validation errors

### FR-4 Source attribution
Structured extraction responses must include supporting sources similarly to answer citations.

### FR-5 Deterministic response envelope
Suggested response envelope:
```json
{
  "mode": "structured_extraction",
  "schema_name": "procedure_metadata_v1",
  "status": "success",
  "data": {
    "title": "Wniosek szkoleniowy",
    "owner": "HR",
    "approval_steps": ["Przełożony", "HR", "Finanse"]
  },
  "sources": [...]
}
```

### FR-6 Reusable schemas
Initial recommended schemas:
- `procedure_metadata_v1`
- `approval_path_v1`
- `document_brief_v1`
- `deadline_and_required_documents_v1`

## Suggested backend modules
- extraction request DTO/schema
- extraction schema registry
- extraction prompt builder
- structured response validator
- extraction audit/result store if practical

## Configuration
- `EXTRACTION_ENABLED=true`
- `EXTRACTION_MAX_SCHEMA_FIELDS=30`
- `EXTRACTION_VALIDATION_STRICT=true`
- `EXTRACTION_TIMEOUT_MS=5000`

## Testing

### Unit
- schema registry lookup
- validation success/failure mapping
- structured response envelope building

### Integration
- extract approval path from known document fixture
- extraction response includes sources
- invalid model output is surfaced as validation failure

### E2E
- user triggers extraction mode from selected document scope and receives validated JSON

## Definition of Done
- extraction mode exists as a first-class backend capability
- schema validation is enforced
- sources are returned with structured output
- at least two useful predefined schemas work end-to-end
