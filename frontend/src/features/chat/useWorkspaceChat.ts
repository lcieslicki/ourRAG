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

export type ChatReadinessItemStatus = "ok" | "loading" | "error";

export type ChatReadinessCheck = {
  id: "user" | "workspace" | "backend" | "llm" | "documents" | "conversation";
  label: string;
  status: ChatReadinessItemStatus;
  hint: string;
};

export type ChatReadinessStatus = "ready" | "loading" | "error";

export type ChatReadiness = {
  status: ChatReadinessStatus;
  title: string;
  hint: string;
  checks: ChatReadinessCheck[];
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
  const [hasLoadedConversations, setHasLoadedConversations] = useState(false);
  const [hasLoadedDocuments, setHasLoadedDocuments] = useState(false);
  const [isCheckingBackend, setIsCheckingBackend] = useState(false);
  const [isBackendReachable, setIsBackendReachable] = useState(false);
  const [isCheckingLlm, setIsCheckingLlm] = useState(false);
  const [isLlmReady, setIsLlmReady] = useState(false);
  const pendingMessageIdRef = useRef<string | null>(null);

  const canUseApi = userId.trim() !== "" && workspaceId.trim() !== "";

  const loadConversations = useCallback(async () => {
    if (!canUseApi) {
      setConversations([]);
      setDocuments([]);
      setActiveConversationId("");
      setMessages([]);
      setHasLoadedConversations(false);
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
      setHasLoadedConversations(true);
    }
  }, [activeConversationId, apiClient, canUseApi, workspaceId]);

  useEffect(() => {
    void loadConversations();
  }, [loadConversations]);

  const loadDocuments = useCallback(async () => {
    if (!canUseApi) {
      setDocuments([]);
      setHasLoadedDocuments(false);
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
      setHasLoadedDocuments(true);
    }
  }, [apiClient, canUseApi, workspaceId]);

  useEffect(() => {
    void loadDocuments();
  }, [loadDocuments]);

  useEffect(() => {
    if (!canUseApi) {
      setIsCheckingBackend(false);
      setIsBackendReachable(false);
      return;
    }

    let isMounted = true;
    setIsCheckingBackend(true);
    void apiClient
      .ping()
      .then(() => {
        if (isMounted) {
          setIsBackendReachable(true);
        }
      })
      .catch(() => {
        if (isMounted) {
          setIsBackendReachable(false);
        }
      })
      .finally(() => {
        if (isMounted) {
          setIsCheckingBackend(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [apiClient, canUseApi]);

  useEffect(() => {
    if (!canUseApi) {
      setIsCheckingLlm(false);
      setIsLlmReady(false);
      return;
    }
    if (!isBackendReachable) {
      setIsCheckingLlm(false);
      setIsLlmReady(false);
      return;
    }

    let isMounted = true;
    setIsCheckingLlm(true);
    void apiClient
      .checkLlmHealth()
      .then(() => {
        if (isMounted) {
          setIsLlmReady(true);
        }
      })
      .catch(() => {
        if (isMounted) {
          setIsLlmReady(false);
        }
      })
      .finally(() => {
        if (isMounted) {
          setIsCheckingLlm(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [apiClient, canUseApi, isBackendReachable]);

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

  const readinessChecks = useMemo<ChatReadinessCheck[]>(() => {
    const hasUser = userId.trim() !== "";
    const hasWorkspace = workspaceId.trim() !== "";
    const canCheckBackend = hasUser && hasWorkspace;
    const backendLoading = canCheckBackend && isCheckingBackend;
    const backendError = !!error;
    const llmLoading = canCheckBackend && isBackendReachable && isCheckingLlm;
    const documentsLoading = canCheckBackend && (!hasLoadedDocuments || isLoadingDocuments);
    const conversationLoading = canCheckBackend && isLoadingConversation;

    return [
      {
        id: "user",
        label: "User session",
        status: hasUser ? "ok" : "error",
        hint: hasUser ? "Authenticated user is available." : "Login is required to start chat.",
      },
      {
        id: "workspace",
        label: "Workspace selected",
        status: hasWorkspace ? "ok" : "error",
        hint: hasWorkspace ? "Workspace context is active." : "Select a workspace before chatting.",
      },
      {
        id: "backend",
        label: "Backend API",
        status: !canCheckBackend
          ? "loading"
          : backendLoading
            ? "loading"
            : isBackendReachable
              ? "ok"
              : "error",
        hint: !canCheckBackend
          ? "Waiting for session and workspace."
          : backendLoading
              ? "Checking backend availability..."
              : isBackendReachable
                ? "Backend ping check passed."
                : "Backend is unreachable. Check API health.",
      },
      {
        id: "documents",
        label: "Documents scope",
        status: !canCheckBackend
          ? "loading"
          : backendError || !isBackendReachable
            ? "error"
            : documentsLoading
              ? "loading"
              : "ok",
        hint: !canCheckBackend
          ? "Waiting for workspace context."
          : backendError || !isBackendReachable
            ? "Could not load workspace documents."
            : documentsLoading
              ? "Loading available documents..."
              : "Document scope is ready.",
      },
      {
        id: "llm",
        label: "Ollama / Chat model",
        status: !canCheckBackend
          ? "loading"
          : !isBackendReachable
            ? "error"
            : llmLoading
              ? "loading"
              : isLlmReady
                ? "ok"
                : "error",
        hint: !canCheckBackend
          ? "Waiting for session and workspace."
          : !isBackendReachable
            ? "Cannot verify LLM while backend is unreachable."
            : llmLoading
              ? "Checking Ollama model readiness..."
              : isLlmReady
                ? "Ollama model is ready."
                : "Ollama is reachable but model is not ready.",
      },
      {
        id: "conversation",
        label: "Conversation state",
        status: !canCheckBackend
          ? "loading"
          : backendError || !isBackendReachable || !isLlmReady
            ? "error"
            : conversationLoading
              ? "loading"
              : "ok",
        hint: !canCheckBackend
          ? "Waiting for workspace context."
          : backendError || !isBackendReachable || !isLlmReady
            ? "Conversation cannot be loaded because of an error."
            : conversationLoading
              ? "Loading active conversation..."
              : "Conversation is ready for input.",
      },
    ];
  }, [
    error,
    hasLoadedConversations,
    hasLoadedDocuments,
    isBackendReachable,
    isCheckingBackend,
    isCheckingLlm,
    isLoadingConversation,
    isLoadingConversations,
    isLoadingDocuments,
    isLlmReady,
    userId,
    workspaceId,
  ]);

  const chatReadiness = useMemo<ChatReadiness>(() => {
    const hasError = readinessChecks.some((check) => check.status === "error");
    const hasLoading = readinessChecks.some((check) => check.status === "loading");

    if (hasError) {
      return {
        status: "error",
        title: "Chat requires attention",
        hint: "Fix failing checks to start using chat safely.",
        checks: readinessChecks,
      };
    }

    if (hasLoading) {
      return {
        status: "loading",
        title: "Preparing chat",
        hint: "A few startup checks are still running.",
        checks: readinessChecks,
      };
    }

    return {
      status: "ready",
      title: "Chat is ready",
      hint: "All checks passed. You can ask your question now.",
      checks: readinessChecks,
    };
  }, [readinessChecks]);

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
    chatReadiness,
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
