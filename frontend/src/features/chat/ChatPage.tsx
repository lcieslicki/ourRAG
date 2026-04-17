import { AssistantThread } from "./components/AssistantThread";
import { SourcesPanel } from "./components/SourcesPanel";
import type { ChatSource } from "../../lib/api/types";
import type { ReactNode } from "react";

type ChatPageProps = {
  workspaceId: string;
  conversationId: string;
  error: string | null;
  isLoadingConversation: boolean;
  isSending: boolean;
  scopeFilters: ReactNode;
  sources: readonly ChatSource[];
};

export function ChatPage({
  workspaceId,
  conversationId,
  error,
  isLoadingConversation,
  isSending,
  scopeFilters,
  sources,
}: ChatPageProps) {
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
      {error ? <div className="error-banner">{error}</div> : null}
      {isLoadingConversation ? <div className="status-banner">Loading conversation...</div> : null}
      {isSending ? <div className="status-banner">Waiting for backend response...</div> : null}
      <div className="chat-content">
        <AssistantThread />
        <aside className="chat-aside">
          {scopeFilters}
          <SourcesPanel sources={sources} />
        </aside>
      </div>
    </section>
  );
}
