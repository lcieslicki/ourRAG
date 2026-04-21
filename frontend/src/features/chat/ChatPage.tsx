import { AssistantThread } from "./components/AssistantThread";
import { SourcesPanel } from "./components/SourcesPanel";
import type { ChatProcessingLogEvent, ChatSource } from "../../lib/api/types";
import type { ChatReadiness } from "./useWorkspaceChat";
import type { ReactNode } from "react";

type ChatPageProps = {
  workspaceId: string;
  conversationId: string;
  error: string | null;
  isLoadingConversation: boolean;
  isSending: boolean;
  scopeFilters: ReactNode;
  sources: readonly ChatSource[];
  chatLogsByMessage: Record<string, ChatProcessingLogEvent[]>;
  chatReadiness: ChatReadiness;
};

export function ChatPage({
  workspaceId,
  conversationId,
  error,
  isLoadingConversation,
  isSending,
  scopeFilters,
  sources,
  chatLogsByMessage,
  chatReadiness,
}: ChatPageProps) {
  const orderedChecks = [...chatReadiness.checks].sort((left, right) => {
    const priority: Record<string, number> = { loading: 0, error: 1, ok: 2 };
    return (priority[left.status] ?? 99) - (priority[right.status] ?? 99);
  });

  return (
    <section className="chat-page" aria-label="Chat">
      <header className="chat-header">
        <div>
          <p className="eyebrow">Chat</p>
          <h2>Ask from workspace knowledge</h2>
        </div>
        <dl>
          <div>
            <dt>Workspace</dt>
            <dd>{workspaceId || "not selected"}</dd>
          </div>
          <div>
            <dt>Conversation</dt>
            <dd>{conversationId || "new or backend-selected"}</dd>
          </div>
        </dl>
      </header>
      <section className={`chat-readiness chat-readiness-${chatReadiness.status}`} aria-label="Chat readiness">
        <div className="chat-readiness-header">
          <strong>{chatReadiness.title}</strong>
          <span>{chatReadiness.hint}</span>
        </div>
        <details className="chat-readiness-details">
          <summary>Show detailed checks</summary>
          <ul className="chat-readiness-list">
            {orderedChecks.map((check) => (
              <li key={check.id} className={`chat-readiness-item chat-readiness-item-${check.status}`}>
                <span className="chat-readiness-item-label">{check.label}</span>
                <span className="chat-readiness-item-hint">{check.hint}</span>
              </li>
            ))}
          </ul>
        </details>
      </section>
      {error ? <div className="error-banner">{error}</div> : null}
      {isLoadingConversation ? <div className="status-banner">Loading conversation...</div> : null}
      {isSending ? <div className="status-banner">Waiting for backend response...</div> : null}
      <div className="chat-content">
        <AssistantThread chatLogsByMessage={chatLogsByMessage} />
        <aside className="chat-aside">
          {scopeFilters}
          <SourcesPanel sources={sources} />
        </aside>
      </div>
    </section>
  );
}
