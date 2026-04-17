import type { ReactNode } from "react";
import { useCallback, useMemo } from "react";
import {
  AssistantRuntimeProvider,
  useExternalStoreRuntime,
  type AppendMessage,
  type ThreadMessageLike,
} from "@assistant-ui/react";

import type { ChatMessage } from "../../lib/api/types";

type AssistantRuntimeBridgeProps = {
  messages: readonly ChatMessage[];
  isRunning: boolean;
  isDisabled: boolean;
  onSubmit: (message: string) => Promise<void>;
  children: ReactNode;
};

export function AssistantRuntimeBridge({
  messages,
  isRunning,
  isDisabled,
  onSubmit,
  children,
}: AssistantRuntimeBridgeProps) {
  const convertMessage = useCallback((message: ChatMessage): ThreadMessageLike => {
    return {
      id: message.id,
      role: message.role,
      content: [{ type: "text", text: message.content }],
      createdAt: new Date(message.created_at),
    };
  }, []);

  const onNew = useCallback(
    async (message: AppendMessage) => {
      const text = extractText(message.content).trim();
      if (!text) {
        return;
      }
      await onSubmit(text);
    },
    [onSubmit],
  );

  const runtime = useExternalStoreRuntime<ChatMessage>(
    useMemo(
      () => ({
        messages,
        convertMessage,
        onNew,
        isRunning,
        isDisabled,
      }),
      [convertMessage, isDisabled, isRunning, messages, onNew],
    ),
  );

  return <AssistantRuntimeProvider runtime={runtime}>{children}</AssistantRuntimeProvider>;
}

function extractText(content: AppendMessage["content"]): string {
  return content
    .map((part) => {
      if (part.type === "text") {
        return part.text;
      }
      return "";
    })
    .join("\n");
}
