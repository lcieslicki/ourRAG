import type { ChatSource } from "../../../lib/api/types";

type SourcesPanelProps = {
  sources: readonly ChatSource[];
};

export function SourcesPanel({ sources }: SourcesPanelProps) {
  return (
    <aside className="sources-panel" aria-label="Latest answer sources">
      <h3>Sources</h3>
      {sources.length === 0 ? <p className="muted">No sources for the latest answer.</p> : null}
      <div className="source-items">
        {sources.map((source) => (
          <article key={`${source.document_version_id}-${source.chunk_id ?? source.section_path}`} className="source-item">
            <div>
              <strong>{source.document_title}</strong>
              {source.category ? <small>{source.category}</small> : null}
            </div>
            <span>{source.section_path || "Untitled section"}</span>
            <p>{source.snippet}</p>
          </article>
        ))}
      </div>
    </aside>
  );
}
