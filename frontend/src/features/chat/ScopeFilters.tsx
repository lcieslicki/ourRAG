import type { DocumentListItem, RetrievalScope } from "../../lib/api/types";

type ScopeFiltersProps = {
  documents: readonly DocumentListItem[];
  isLoading: boolean;
  scope: RetrievalScope;
  onScopeChange: (scope: RetrievalScope) => void;
  onRefreshDocuments: () => void;
};

export function ScopeFilters({
  documents,
  isLoading,
  scope,
  onScopeChange,
  onRefreshDocuments,
}: ScopeFiltersProps) {
  const categories = Array.from(new Set(documents.map((document) => document.category).filter(Boolean))).sort();
  const selectedDocumentIds = new Set(scope.document_ids ?? []);

  return (
    <section className="scope-filters" aria-label="Retrieval scope">
      <div className="scope-header">
        <div>
          <h3>Scope</h3>
          <p>Optional retrieval filters. Backend validates access and eligibility.</p>
        </div>
        <button type="button" onClick={onRefreshDocuments} disabled={isLoading}>
          Refresh docs
        </button>
      </div>

      <div className="scope-mode-group" role="radiogroup" aria-label="Scope mode">
        <label>
          <input
            type="radio"
            name="scope-mode"
            checked={scope.mode === "all"}
            onChange={() => onScopeChange({ mode: "all" })}
          />
          All active documents
        </label>
        <label>
          <input
            type="radio"
            name="scope-mode"
            checked={scope.mode === "category"}
            onChange={() => onScopeChange({ mode: "category", category: categories[0] ?? "" })}
          />
          Category
        </label>
        <label>
          <input
            type="radio"
            name="scope-mode"
            checked={scope.mode === "documents"}
            onChange={() => onScopeChange({ mode: "documents", document_ids: [] })}
          />
          Selected documents
        </label>
      </div>

      {scope.mode === "category" ? (
        <label className="scope-field">
          Category
          <select
            value={scope.category ?? ""}
            onChange={(event) => onScopeChange({ mode: "category", category: event.target.value })}
          >
            <option value="">Choose category</option>
            {categories.map((category) => (
              <option key={category} value={category}>
                {category}
              </option>
            ))}
          </select>
        </label>
      ) : null}

      {scope.mode === "documents" ? (
        <div className="scope-document-list">
          {documents.length === 0 ? <p className="muted">No documents loaded for this workspace.</p> : null}
          {documents.map((document) => (
            <label key={document.id} className="scope-document-option">
              <input
                type="checkbox"
                checked={selectedDocumentIds.has(document.id)}
                onChange={(event) => {
                  const next = new Set(selectedDocumentIds);
                  if (event.target.checked) {
                    next.add(document.id);
                  } else {
                    next.delete(document.id);
                  }
                  onScopeChange({ mode: "documents", document_ids: Array.from(next) });
                }}
              />
              <span>
                <strong>{document.title}</strong>
                <small>{document.category}</small>
              </span>
            </label>
          ))}
        </div>
      ) : null}
    </section>
  );
}
