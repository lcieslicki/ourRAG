import { AssistantThread } from "./components/AssistantThread";
import { SourcesPanel } from "./components/SourcesPanel";
import type { ChatProcessingLogEvent, ChatSource } from "../../lib/api/types";
import type { ChatReadiness } from "./useWorkspaceChat";
import type { ReactNode } from "react";
import { pl } from "../../i18n/pl";

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
    <section className="chat-page" aria-label={pl.chat.ariaLabel}>
      <header className="chat-header">
        <div>
          <p className="eyebrow">{pl.app.chatTab}</p>
          <h2>{pl.chat.heading}</h2>
        </div>
        <dl>
          <div>
            <dt>{pl.chat.workspaceLabel}</dt>
            <dd>{workspaceId || pl.chat.workspaceNotSelected}</dd>
          </div>
          <div>
            <dt>{pl.chat.conversationLabel}</dt>
            <dd>{conversationId || pl.chat.conversationAuto}</dd>
          </div>
        </dl>
      </header>
      <section className={`chat-readiness chat-readiness-${chatReadiness.status}`} aria-label={pl.chat.readinessAria}>
        <div className="chat-readiness-header">
          <strong>{chatReadiness.title}</strong>
          <span>{chatReadiness.hint}</span>
        </div>
        <details className="chat-readiness-details">
          <summary>{pl.chat.detailsSummary}</summary>
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
      {isLoadingConversation ? <div className="status-banner">{pl.chat.loadingConversation}</div> : null}
      {isSending ? <div className="status-banner">{pl.chat.waitingResponse}</div> : null}
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
