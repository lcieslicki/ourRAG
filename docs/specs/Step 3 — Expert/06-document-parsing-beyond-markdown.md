# Spec: Document Parsing Beyond Markdown

## Goal
Extend ingestion beyond Markdown so the system can process more realistic enterprise document formats such as PDF, DOCX, TXT, and spreadsheet-like sources.

## Baseline assumption
The MVP ingestion pipeline supports Markdown only, with parser abstraction already present. This feature expands parser implementations and format-specific normalization.

## Scope

### In scope
- parser implementations for additional file types
- normalized parser output contracts
- ingestion safety checks for new file types
- format-specific chunking considerations
- parser evaluation fixtures

### Out of scope
- perfect OCR for arbitrary scans in v1
- full layout reconstruction
- image understanding beyond pragmatic text extraction

## Functional requirements

### FR-1 New file types
Initial recommended support:
- `.txt`
- `.pdf`
- `.docx`
- `.xlsx` or CSV-like tabular support if practical

### FR-2 Parser contract stability
All parsers must emit a normalized intermediate representation compatible with downstream chunking.

### FR-3 Metadata preservation
Where possible preserve:
- filename
- page number for PDF
- heading/section markers
- table boundaries
- worksheet name for spreadsheets
- language if detected or inferred

### FR-4 Safe fallback
If a document cannot be parsed confidently, the system must mark the version as failed with a typed failure reason rather than silently indexing garbage.

### FR-5 Format-aware chunking hooks
Chunking must remain extensible so format-specific strategies can be introduced later without breaking the baseline parser contract.

## Suggested parser modules
- `PlainTextParser`
- `PdfParser`
- `DocxParser`
- `SpreadsheetParser`
- optional `OcrAdapter` behind feature flag

## Configuration
- `INGESTION_ALLOWED_FILE_TYPES=.md,.txt,.pdf,.docx,.xlsx`
- `PARSER_PDF_ENABLED=true`
- `PARSER_DOCX_ENABLED=true`
- `PARSER_SPREADSHEET_ENABLED=false`
- `PARSER_OCR_ENABLED=false`

## Testing

### Unit
- parser contract normalization for each file type
- metadata extraction mapping
- parse failure classification

### Integration
- upload and parse each supported file type
- failed parse does not mark version ready
- workspace storage/versioning behavior remains correct

### Fixtures
- small representative PDF, DOCX, TXT, and spreadsheet samples committed to test fixtures

## Definition of Done
- at least PDF, DOCX, and TXT are supported end-to-end
- parser output remains normalized for chunking/indexing
- parse failures are explicit and observable
