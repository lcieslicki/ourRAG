import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import type { ApiClient } from "../../lib/api/client";
import type {
  ChatMessage,
  ChatSource,
  ChatProcessingLogEvent,
  ConversationSummary,
  DocumentListItem,
  RetrievalScope,
} from "../../lib/api/types";
import { subscribeChatLogs } from "../../lib/api/ws";
import { config } from "../../config";

type UseWorkspaceChatOptions = {
  apiClient: ApiClient;
  userId: string;
  workspaceId: string;
};

export function useWorkspaceChat({ apiClient, userId, workspaceId }: UseWorkspaceChatOptions) {
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [activeConversationId, setActiveConversationId] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [documents, setDocuments] = useState<DocumentListItem[]>([]);
  const [scope, setScope] = useState<RetrievalScope>({ mode: "all" });
  const [isLoadingConversations, setIsLoadingConversations] = useState(false);
  const [isLoadingConversation, setIsLoadingConversation] = useState(false);
  const [isLoadingDocuments, setIsLoadingDocuments] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [chatLogsByMessage, setChatLogsByMessage] = useState<Record<string, ChatProcessingLogEvent[]>>({});
  const pendingMessageIdRef = useRef<string | null>(null);

  const canUseApi = userId.trim() !== "" && workspaceId.trim() !== "";

  const loadConversations = useCallback(async () => {
    if (!canUseApi) {
      setConversations([]);
      setDocuments([]);
      setActiveConversationId("");
      setMessages([]);
      return;
    }

    setIsLoadingConversations(true);
    setError(null);
    try {
      const loaded = await apiClient.listConversations(workspaceId);
      setConversations(loaded);
      if (activeConversationId && !loaded.some((conversation) => conversation.id === activeConversationId)) {
        setActiveConversationId("");
        setMessages([]);
      }
    } catch (error) {
      setError(errorMessage(error));
    } finally {
      setIsLoadingConversations(false);
    }
  }, [activeConversationId, apiClient, canUseApi, workspaceId]);

  useEffect(() => {
    void loadConversations();
  }, [loadConversations]);

  const loadDocuments = useCallback(async () => {
    if (!canUseApi) {
      setDocuments([]);
      return;
    }

    setIsLoadingDocuments(true);
    setError(null);
    try {
      const loaded = await apiClient.listDocuments(workspaceId);
      setDocuments(loaded);
    } catch (error) {
      setError(errorMessage(error));
      setDocuments([]);
    } finally {
      setIsLoadingDocuments(false);
    }
  }, [apiClient, canUseApi, workspaceId]);

  useEffect(() => {
    void loadDocuments();
  }, [loadDocuments]);

  const selectConversation = useCallback(
    async (conversationId: string) => {
      if (!conversationId) {
        setActiveConversationId("");
        setMessages([]);
        return;
      }

      setActiveConversationId(conversationId);
      setIsLoadingConversation(true);
      setError(null);
      try {
        const detail = await apiClient.getConversation(conversationId);
        if (detail.workspace_id !== workspaceId) {
          throw new Error("Conversation does not belong to the active workspace.");
        }
        setMessages(detail.messages.map(withExtractedSources));
        setChatLogsByMessage(extractLogsFromMessages(detail.messages));
      } catch (error) {
        setError(errorMessage(error));
        setMessages([]);
        setChatLogsByMessage({});
      } finally {
        setIsLoadingConversation(false);
      }
    },
    [apiClient, workspaceId],
  );

  const startNewConversation = useCallback(() => {
    setActiveConversationId("");
    setMessages([]);
    setError(null);
    setChatLogsByMessage({});
    pendingMessageIdRef.current = null;
  }, []);

  useEffect(() => {
    if (!activeConversationId || !canUseApi) {
      return undefined;
    }

    return subscribeChatLogs({
      apiBaseUrl: config.api.baseUrl,
      conversationId: activeConversationId,
      userId,
      onEvent: (event) => {
        setChatLogsByMessage((current) => {
          const targetMessageId = event.message_id ?? pendingMessageIdRef.current;
          if (!targetMessageId) {
            return current;
          }
          const next = { ...current };
          next[targetMessageId] = [...(next[targetMessageId] ?? []), event];
          return next;
        });

        if (event.category === "persistence" && event.stage === "user_message_saved" && event.message_id) {
          const previousPendingId = pendingMessageIdRef.current;
          pendingMessageIdRef.current = event.message_id;
          if (previousPendingId && previousPendingId !== event.message_id) {
            setChatLogsByMessage((current) => remapLogs(current, previousPendingId, event.message_id!));
          }
        }
      },
      onError: () => {
        setError((current) => current ?? "Chat log stream disconnected.");
      },
    });
  }, [activeConversationId, canUseApi, userId]);

  const sendMessage = useCallback(
    async (content: string) => {
      if (!canUseApi) {
        setError("Set both User ID and Workspace ID before sending a message.");
        return;
      }

      const trimmed = content.trim();
      if (!trimmed) {
        return;
      }

      setIsSending(true);
      setError(null);
      const temporaryMessage = temporaryUserMessage(trimmed, workspaceId, activeConversationId);
      pendingMessageIdRef.current = temporaryMessage.id;
      setMessages((current) => [...current, temporaryMessage]);
      setChatLogsByMessage((current) => ({ ...current, [temporaryMessage.id]: [] }));

      try {
        let conversationId = activeConversationId;
        if (!conversationId) {
          const conversation = await apiClient.createConversation({
            workspace_id: workspaceId,
            title: titleFromMessage(trimmed),
          });
          conversationId = conversation.id;
          setActiveConversationId(conversation.id);
          setConversations((current) => [conversation, ...current]);
        }

        const response = await apiClient.sendChatMessage({
          workspace_id: workspaceId,
          conversation_id: conversationId,
          message: trimmed,
          scope: scopeForRequest(scope),
        });

        setActiveConversationId(response.conversation_id);
        pendingMessageIdRef.current = response.user_message.id;
        setMessages((current) => [
          ...current.filter((message) => message.id !== temporaryMessage.id),
          response.user_message,
          assistantMessageFromResponse(response.conversation_id, workspaceId, response.assistant_message),
        ]);
        setChatLogsByMessage((current) => remapLogs(current, temporaryMessage.id, response.user_message.id));
        void loadConversations();
      } catch (error) {
        setMessages((current) => current.filter((message) => message.id !== temporaryMessage.id));
        setChatLogsByMessage((current) => {
          const next = { ...current };
          delete next[temporaryMessage.id];
          return next;
        });
        pendingMessageIdRef.current = null;
        setError(errorMessage(error));
      } finally {
        setIsSending(false);
      }
    },
    [activeConversationId, apiClient, canUseApi, loadConversations, scope, workspaceId],
  );

  const latestSources = useMemo(() => {
    const latestAssistantMessage = [...messages]
      .reverse()
      .find((message) => message.role === "assistant" && message.sources && message.sources.length > 0);
    return latestAssistantMessage?.sources ?? [];
  }, [messages]);

  return {
    activeConversationId,
    conversations,
    documents,
    error,
    isDisabled: !canUseApi || isLoadingConversation,
    isLoadingConversation,
    isLoadingConversations,
    isLoadingDocuments,
    isSending,
    latestSources,
    loadConversations,
    loadDocuments,
    messages,
    chatLogsByMessage,
    scope,
    selectConversation,
    sendMessage,
    setScope,
    startNewConversation,
  };
}

function remapLogs(
  current: Record<string, ChatProcessingLogEvent[]>,
  fromMessageId: string,
  toMessageId: string,
): Record<string, ChatProcessingLogEvent[]> {
  if (fromMessageId === toMessageId || !current[fromMessageId]) {
    return current;
  }
  const next = { ...current };
  const merged = [...(next[toMessageId] ?? []), ...next[fromMessageId]];
  next[toMessageId] = merged;
  delete next[fromMessageId];
  return next;
}

function extractLogsFromMessages(messages: readonly ChatMessage[]): Record<string, ChatProcessingLogEvent[]> {
  return messages.reduce<Record<string, ChatProcessingLogEvent[]>>((acc, message) => {
    if (message.role !== "user") {
      return acc;
    }
    const raw = message.response_metadata?.processing_logs;
    if (!Array.isArray(raw)) {
      return acc;
    }
    const logs = raw.filter(isChatLogEvent);
    if (logs.length > 0) {
      acc[message.id] = logs;
    }
    return acc;
  }, {});
}

function isChatLogEvent(value: unknown): value is ChatProcessingLogEvent {
  if (!value || typeof value !== "object") {
    return false;
  }
  const candidate = value as Partial<ChatProcessingLogEvent>;
  return typeof candidate.event_id === "string" && typeof candidate.category === "string";
}

function scopeForRequest(scope: RetrievalScope): RetrievalScope | undefined {
  if (scope.mode === "all") {
    return { mode: "all" };
  }

  if (scope.mode === "category" && scope.category?.trim()) {
    return { mode: "category", category: scope.category.trim() };
  }

  if (scope.mode === "documents" && scope.document_ids && scope.document_ids.length > 0) {
    return { mode: "documents", document_ids: scope.document_ids };
  }

  return { mode: "all" };
}

function assistantMessageFromResponse(
  conversationId: string,
  workspaceId: string,
  message: { id: string; role: "assistant"; content: string; sources: ChatSource[] },
): ChatMessage {
  return {
    id: message.id,
    conversation_id: conversationId,
    workspace_id: workspaceId,
    user_id: null,
    role: message.role,
    content: message.content,
    response_metadata: { sources: message.sources },
    sources: message.sources,
    created_at: new Date().toISOString(),
  };
}

function withExtractedSources(message: ChatMessage): ChatMessage {
  const rawSources = message.response_metadata?.sources;
  if (!Array.isArray(rawSources)) {
    return message;
  }

  return {
    ...message,
    sources: rawSources.filter(isChatSource),
  };
}

function isChatSource(value: unknown): value is ChatSource {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  return "document_id" in value && "document_title" in value && "snippet" in value;
}

function temporaryUserMessage(content: string, workspaceId: string, conversationId: string): ChatMessage {
  return {
    id: `pending-${crypto.randomUUID()}`,
    conversation_id: conversationId || "pending",
    workspace_id: workspaceId,
    user_id: null,
    role: "user",
    content,
    response_metadata: null,
    created_at: new Date().toISOString(),
  };
}

function titleFromMessage(message: string): string {
  return message.length > 80 ? `${message.slice(0, 77)}...` : message;
}

function errorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  return "Unexpected frontend error.";
}
