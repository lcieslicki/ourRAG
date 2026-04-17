import type { ConversationSummary } from "../lib/api/types";

type ConversationListProps = {
  conversations: readonly ConversationSummary[];
  activeConversationId: string;
  isLoading: boolean;
  onSelectConversation: (conversationId: string) => void;
  onStartNewConversation: () => void;
  onRefresh: () => void;
};

export function ConversationList({
  conversations,
  activeConversationId,
  isLoading,
  onSelectConversation,
  onStartNewConversation,
  onRefresh,
}: ConversationListProps) {
  return (
    <section className="conversation-list" aria-label="Conversations">
      <div className="sidebar-section-header">
        <h2>Conversations</h2>
        <button type="button" onClick={onRefresh} disabled={isLoading}>
          Refresh
        </button>
      </div>
      <button type="button" className="new-conversation-button" onClick={onStartNewConversation}>
        New conversation
      </button>
      {isLoading ? <p className="muted">Loading conversations...</p> : null}
      {!isLoading && conversations.length === 0 ? <p className="muted">No conversations loaded.</p> : null}
      <div className="conversation-items">
        {conversations.map((conversation) => (
          <button
            type="button"
            key={conversation.id}
            className={conversation.id === activeConversationId ? "conversation-item active" : "conversation-item"}
            onClick={() => onSelectConversation(conversation.id)}
          >
            <span>{conversation.title || "Untitled conversation"}</span>
            <small>{conversation.status}</small>
          </button>
        ))}
      </div>
    </section>
  );
}
