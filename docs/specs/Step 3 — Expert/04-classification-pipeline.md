# Spec: Classification Pipeline

## Goal
Introduce lightweight document and query classification capabilities that improve routing, filtering, and domain control.

## Baseline assumption
The system already has categories and guardrails, but does not yet have a formal classification pipeline for documents or user intents.

## Scope

### In scope
- document classification
- query/intent classification
- in-scope vs out-of-scope classification support
- config-driven classifier abstraction
- local-first implementation paths

### Out of scope
- large-scale supervised training platform
- human annotation UI in v1
- production auto-learning from feedback in the same phase

## Functional requirements

### FR-1 Classification targets
Initial recommended classification tasks:
- document type: `procedure`, `policy`, `instruction`, `faq`, `form`, `other`
- department/category inference
- query intent: `qa`, `summary`, `extraction`, `admin_lookup`, `other`
- in-scope vs out-of-scope signal

### FR-2 Classifier abstraction
Expose a stable classifier interface so implementations may later vary between:
- rule-based
- embedding-similarity based
- LLM-assisted classification
- classical ML model

### FR-3 Integration points
Classification may be used to:
- enrich document metadata at ingestion time
- assist routing/orchestration
- improve guardrail decisions
- prefill or suggest retrieval filters

### FR-4 Confidence and fallback
Every classification result should include:
- label
- confidence if available
- provider or strategy name
- fallback behavior when uncertain

### FR-5 Non-authoritative defaults
Until proven reliable, classifier outputs should be advisory or softly enforced except for explicitly configured rules.

## Suggested interfaces
- `DocumentClassifier.classify(document_version) -> ClassificationResult`
- `QueryClassifier.classify(query_context) -> ClassificationResult`

## Configuration
- `CLASSIFICATION_ENABLED=true`
- `CLASSIFICATION_DOCUMENT_ENABLED=true`
- `CLASSIFICATION_QUERY_ENABLED=true`
- `CLASSIFICATION_MIN_CONFIDENCE=0.65`
- `CLASSIFICATION_PROVIDER=<rule_based|embedding|llm>`

## Testing

### Unit
- label normalization
- confidence threshold behavior
- fallback mapping

### Integration
- document fixture classification enriches metadata
- query intent classification feeds router safely
- low-confidence results do not break baseline flow

### Evaluation
- maintain a small labeled fixture set for intent/document classification smoke checks

## Definition of Done
- at least one document and one query classification path exist
- classification results are exposed in a reusable internal contract
- routing and metadata enrichment can consume classifier outputs safely
