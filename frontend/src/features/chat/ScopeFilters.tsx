import type { DocumentListItem, RetrievalScope } from "../../lib/api/types";
import { pl } from "../../i18n/pl";

type ScopeFiltersProps = {
  documents: readonly DocumentListItem[];
  isLoading: boolean;
  scope: RetrievalScope;
  onScopeChange: (scope: RetrievalScope) => void;
  onApplyScope: () => void;
  hasPendingScopeChanges: boolean;
  onRefreshDocuments: () => void;
};

export function ScopeFilters({
  documents,
  isLoading,
  scope,
  onScopeChange,
  onApplyScope,
  hasPendingScopeChanges,
  onRefreshDocuments,
}: ScopeFiltersProps) {
  const categories = Array.from(new Set(documents.map((document) => document.category).filter(Boolean))).sort();
  const selectedDocumentIds = new Set(scope.document_ids ?? []);

  return (
    <section className="scope-filters" aria-label={pl.scope.ariaLabel}>
      <div className="scope-header">
        <div>
          <h3>{pl.scope.title}</h3>
          <p>{pl.scope.hint}</p>
        </div>
        <button type="button" onClick={onRefreshDocuments} disabled={isLoading}>
          {pl.scope.refreshDocs}
        </button>
      </div>

      <div className="scope-mode-group" role="radiogroup" aria-label={pl.scope.modeAria}>
        <label>
          <input
            type="radio"
            name="scope-mode"
            checked={scope.mode === "all"}
            onChange={() => onScopeChange({ mode: "all" })}
          />
          {pl.scope.allDocs}
        </label>
        <label>
          <input
            type="radio"
            name="scope-mode"
            checked={scope.mode === "category"}
            onChange={() => onScopeChange({ mode: "category", category: categories[0] ?? "" })}
          />
          {pl.scope.category}
        </label>
        <label>
          <input
            type="radio"
            name="scope-mode"
            checked={scope.mode === "documents"}
            onChange={() => onScopeChange({ mode: "documents", document_ids: [] })}
          />
          {pl.scope.selectedDocs}
        </label>
      </div>

      {scope.mode === "category" ? (
        <label className="scope-field">
          {pl.scope.category}
          <select
            value={scope.category ?? ""}
            onChange={(event) => onScopeChange({ mode: "category", category: event.target.value })}
          >
            <option value="">{pl.scope.chooseCategory}</option>
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
          {documents.length === 0 ? <p className="muted">{pl.scope.noDocs}</p> : null}
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

      <div className="scope-actions">
        <button type="button" onClick={onApplyScope} disabled={!hasPendingScopeChanges}>
          {pl.scope.apply}
        </button>
        {hasPendingScopeChanges ? <p className="muted">{pl.scope.unappliedChanges}</p> : null}
      </div>
    </section>
  );
}
