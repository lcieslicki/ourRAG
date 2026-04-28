import type { CitationSource } from "../../../lib/api/types";
import { BookOpen, AlertTriangle, Ban } from "lucide-react";
import { pl } from "../../../i18n/pl";

type SourcesPanelProps = {
  sources: readonly CitationSource[];
  responseMode?: string;
  guardrailReason?: string | null;
};

export function SourcesPanel({ sources, responseMode, guardrailReason: _guardrailReason }: SourcesPanelProps) {
  const isOutOfScope = responseMode === "refuse_out_of_scope";
  const isInsufficient = responseMode === "insufficient_context";
  const showBadge = isOutOfScope || isInsufficient;

  return (
    <aside className="sources-panel" aria-label={pl.sources.ariaLabel}>
      <h3>{pl.sources.title}</h3>

      {showBadge && (
        <div className={`response-mode-badge response-mode-badge--${responseMode}`}>
          {isOutOfScope ? (
            <><Ban size={13} /> {pl.sources.responseMode.outOfScope}</>
          ) : (
            <><AlertTriangle size={13} /> {pl.sources.responseMode.insufficientContext}</>
          )}
        </div>
      )}

      {sources.length === 0 ? (
        <p className="muted empty-state">
          <BookOpen size={16} />
          {pl.sources.empty}
        </p>
      ) : null}

      <div className="source-items">
        {sources.map((source) => (
          <article
            key={`${source.document_version_id}-${source.chunk_id}`}
            className="source-item"
          >
            <div className="source-item-header">
              <strong>{source.document_title}</strong>
              {source.rank > 0 && <span className="source-rank">#{source.rank}</span>}
              {source.category ? <small>{source.category}</small> : null}
            </div>
            {source.heading ? (
              <span className="source-heading">{source.heading}</span>
            ) : null}
            <span className="source-section">
              {source.section_path.join(" > ") || pl.sources.untitledSection}
            </span>
            <p className="source-excerpt">{source.excerpt}</p>
            {source.retrieval_score > 0 && (
              <span className="source-score">
                {pl.sources.score}: {(source.retrieval_score * 100).toFixed(0)}%
              </span>
            )}
          </article>
        ))}
      </div>
    </aside>
  );
}
