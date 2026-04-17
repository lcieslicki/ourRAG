import { ComposerPrimitive, MessagePrimitive, ThreadPrimitive } from "@assistant-ui/react";

export function AssistantThread() {
  return (
    <ThreadPrimitive.Root className="assistant-thread">
      <ThreadPrimitive.Viewport className="assistant-thread-viewport">
        <ThreadPrimitive.Empty>
          <div className="assistant-empty">
            <h3>Ask a question about the selected workspace.</h3>
            <p>Sources and scope controls will be rendered here as the backend surface expands.</p>
          </div>
        </ThreadPrimitive.Empty>
        <ThreadPrimitive.Messages
          components={{
            UserMessage,
            AssistantMessage,
          }}
        />
        <ThreadPrimitive.ScrollToBottom className="scroll-button">Scroll to bottom</ThreadPrimitive.ScrollToBottom>
      </ThreadPrimitive.Viewport>
      <ComposerPrimitive.Root className="assistant-composer">
        <ComposerPrimitive.Input
          className="assistant-input"
          placeholder="Ask a question..."
          rows={2}
        />
        <ComposerPrimitive.Send className="assistant-send">Send</ComposerPrimitive.Send>
      </ComposerPrimitive.Root>
    </ThreadPrimitive.Root>
  );
}

function UserMessage() {
  return (
    <MessagePrimitive.Root className="message-row message-row-user">
      <div className="message-bubble user-bubble">
        <MessagePrimitive.Parts />
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
