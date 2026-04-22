import type { ConversationSummary } from "../lib/api/types";
import { pl } from "../i18n/pl";

type ConversationListProps = {
  conversations: readonly ConversationSummary[];
  activeConversationId: string;
  isLoading: boolean;
  onSelectConversation: (conversationId: string) => void;
  onStartNewConversation: () => void;
  onRefresh: () => void;
  onDeleteAll: () => void;
};

export function ConversationList({
  conversations,
  activeConversationId,
  isLoading,
  onSelectConversation,
  onStartNewConversation,
  onRefresh,
  onDeleteAll,
}: ConversationListProps) {
  return (
    <section className="conversation-list" aria-label={pl.conversations.ariaLabel}>
      <div className="sidebar-section-header">
        <h2>{pl.conversations.title}</h2>
        <button type="button" onClick={onRefresh} disabled={isLoading}>
          {pl.conversations.refresh}
        </button>
      </div>
      <button type="button" className="new-conversation-button" onClick={onStartNewConversation}>
        {pl.conversations.newConversation}
      </button>
      <button type="button" className="new-conversation-button" onClick={onDeleteAll} disabled={isLoading}>
        Usuń rozmowy
      </button>
      {isLoading ? <p className="muted">{pl.conversations.loading}</p> : null}
      {!isLoading && conversations.length === 0 ? <p className="muted">{pl.conversations.empty}</p> : null}
      <div className="conversation-items">
        {conversations.map((conversation) => (
          <button
            type="button"
            key={conversation.id}
            className={conversation.id === activeConversationId ? "conversation-item active" : "conversation-item"}
            onClick={() => onSelectConversation(conversation.id)}
          >
            <span>{conversation.title || pl.conversations.untitled}</span>
            <small>{conversation.status}</small>
          </button>
        ))}
      </div>
    </section>
  );
}
