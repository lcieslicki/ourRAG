import { ComposerPrimitive, MessagePrimitive, ThreadPrimitive, useMessage } from "@assistant-ui/react";

import type { ChatProcessingLogEvent } from "../../../lib/api/types";
import { pl } from "../../../i18n/pl";

type AssistantThreadProps = {
  chatLogsByMessage: Record<string, ChatProcessingLogEvent[]>;
};

export function AssistantThread({ chatLogsByMessage }: AssistantThreadProps) {
  const renderUserMessage = () => <UserMessage chatLogsByMessage={chatLogsByMessage} />;
  return (
    <ThreadPrimitive.Root className="assistant-thread">
      <ThreadPrimitive.Viewport className="assistant-thread-viewport">
        <ThreadPrimitive.Empty>
          <div className="assistant-empty">
            <h3>{pl.assistantThread.emptyTitle}</h3>
            <p>{pl.assistantThread.emptyHint}</p>
          </div>
        </ThreadPrimitive.Empty>
        <ThreadPrimitive.Messages
          components={{
            UserMessage: renderUserMessage,
            AssistantMessage,
          }}
        />
        <ThreadPrimitive.ScrollToBottom className="scroll-button">{pl.assistantThread.scrollToBottom}</ThreadPrimitive.ScrollToBottom>
      </ThreadPrimitive.Viewport>
      <ComposerPrimitive.Root className="assistant-composer">
        <ComposerPrimitive.Input
          className="assistant-input"
          placeholder={pl.assistantThread.inputPlaceholder}
          rows={2}
        />
        <ComposerPrimitive.Send className="assistant-send">{pl.assistantThread.send}</ComposerPrimitive.Send>
      </ComposerPrimitive.Root>
    </ThreadPrimitive.Root>
  );
}

function UserMessage({ chatLogsByMessage }: AssistantThreadProps) {
  const message = useMessage();
  const logs = chatLogsByMessage[message.id] ?? [];
  const groupedLogs = groupLogsByCategory(logs);

  return (
    <MessagePrimitive.Root className="message-row message-row-user">
      <div className="message-bubble user-bubble user-bubble-with-logs">
        <div className="question-label">{pl.assistantThread.questionLabel}</div>
        <MessagePrimitive.Parts />
        {logs.length > 0 ? (
          <details className="chat-logs-panel">
            <summary>{pl.assistantThread.processingLogs} ({logs.length})</summary>
            <div className="chat-logs-content">
              {Object.entries(groupedLogs).map(([category, categoryLogs]) => (
                <section key={category} className="chat-logs-category">
                  <h5>{category}</h5>
                  <ul>
                    {categoryLogs.map((logEvent) => (
                      <li key={logEvent.event_id}>
                        <strong>{logEvent.stage}</strong> [{logEvent.status}] {new Date(logEvent.timestamp).toLocaleTimeString()}
                        <pre>{JSON.stringify(logEvent.payload, null, 2)}</pre>
                      </li>
                    ))}
                  </ul>
                </section>
              ))}
            </div>
          </details>
        ) : null}
      </div>
    </MessagePrimitive.Root>
  );
}

function AssistantMessage() {
  return (
    <MessagePrimitive.Root className="message-row message-row-assistant">
      <div className="message-bubble assistant-bubble">
        <MessagePrimitive.Parts />
      </div>
    </MessagePrimitive.Root>
  );
}

function groupLogsByCategory(logs: ChatProcessingLogEvent[]): Record<string, ChatProcessingLogEvent[]> {
  return logs.reduce<Record<string, ChatProcessingLogEvent[]>>((acc, logEvent) => {
    const key = logEvent.category || pl.assistantThread.otherCategory;
    acc[key] = [...(acc[key] ?? []), logEvent];
    return acc;
  }, {});
}
