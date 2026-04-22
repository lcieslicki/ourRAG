import type { ChatSource } from "../../../lib/api/types";
import { BookOpen } from "lucide-react";
import { pl } from "../../../i18n/pl";

type SourcesPanelProps = {
  sources: readonly ChatSource[];
};

export function SourcesPanel({ sources }: SourcesPanelProps) {
  return (
    <aside className="sources-panel" aria-label={pl.sources.ariaLabel}>
      <h3>{pl.sources.title}</h3>
      {sources.length === 0 ? (
        <p className="muted empty-state">
          <BookOpen size={16} />
          {pl.sources.empty}
        </p>
      ) : null}
      <div className="source-items">
        {sources.map((source) => (
          <article key={`${source.document_version_id}-${source.chunk_id ?? source.section_path}`} className="source-item">
            <div>
              <strong>{source.document_title}</strong>
              {source.category ? <small>{source.category}</small> : null}
            </div>
            <span>{source.section_path || pl.sources.untitledSection}</span>
            <p>{source.snippet}</p>
          </article>
        ))}
      </div>
    </aside>
  );
}
