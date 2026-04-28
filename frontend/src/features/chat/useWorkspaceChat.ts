import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import type { ApiClient } from "../../lib/api/client";
import type {
  ChatMessage,
  ChatSource,
  CitationSource,
  ChatProcessingLogEvent,
  ConversationSummary,
  DocumentListItem,
  RetrievalScope,
} from "../../lib/api/types";
import { subscribeChatLogs } from "../../lib/api/ws";
import { config } from "../../config";
import { pl } from "../../i18n/pl";

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
  const [scopeDraft, setScopeDraft] = useState<RetrievalScope>({ mode: "all" });
  const [appliedScope, setAppliedScope] = useState<RetrievalScope>({ mode: "all" });
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
          throw new Error("Rozmowa nie należy do aktywnej przestrzeni roboczej.");
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

  const clearConversations = useCallback(async () => {
    if (!canUseApi) {
      return;
    }
    const shouldDelete = window.confirm("Czy na pewno chcesz usunąć wszystkie rozmowy w tym workspace?");
    if (!shouldDelete) {
      return;
    }

    setError(null);
    try {
      await apiClient.deleteAllConversations(workspaceId);
      setConversations([]);
      setActiveConversationId("");
      setMessages([]);
      setChatLogsByMessage({});
      pendingMessageIdRef.current = null;
    } catch (error) {
      setError(errorMessage(error));
    }
  }, [apiClient, canUseApi, workspaceId]);

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
        setError((current) => current ?? pl.errors.streamDisconnected);
      },
    });
  }, [activeConversationId, canUseApi, userId]);

  const sendMessage = useCallback(
    async (content: string) => {
      if (!canUseApi) {
        setError(pl.errors.missingIdsBeforeSend);
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
          scope: scopeForRequest(appliedScope),
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
    [activeConversationId, apiClient, appliedScope, canUseApi, loadConversations, workspaceId],
  );

  const applyScope = useCallback(() => {
    setAppliedScope(normalizeScopeSelection(scopeDraft));
  }, [scopeDraft]);

  const hasPendingScopeChanges = useMemo(() => !areScopesEqual(scopeDraft, appliedScope), [appliedScope, scopeDraft]);

  const latestSources = useMemo(() => {
    const latestAssistantMessage = [...messages]
      .reverse()
      .find((message) => message.role === "assistant");
    if (!latestAssistantMessage) return [];
    // prefer normalized cited_sources; fall back to legacy sources converted to CitationSource
    if (latestAssistantMessage.cited_sources?.length) {
      return latestAssistantMessage.cited_sources;
    }
    return (latestAssistantMessage.sources ?? []).map(chatSourceToCitation);
  }, [messages]);

  const latestResponseMode = useMemo(() => {
    const latestAssistantMessage = [...messages]
      .reverse()
      .find((message) => message.role === "assistant");
    return latestAssistantMessage?.response_mode ?? "answer_from_context";
  }, [messages]);

  const latestGuardrailReason = useMemo(() => {
    const latestAssistantMessage = [...messages]
      .reverse()
      .find((message) => message.role === "assistant");
    return latestAssistantMessage?.guardrail_reason ?? null;
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
        label: pl.chat.checks.userSession,
        status: hasUser ? "ok" : "error",
        hint: hasUser ? pl.chat.checks.userSessionOk : pl.chat.checks.userSessionMissing,
      },
      {
        id: "workspace",
        label: pl.chat.checks.workspaceSelected,
        status: hasWorkspace ? "ok" : "error",
        hint: hasWorkspace ? pl.chat.checks.workspaceSelectedOk : pl.chat.checks.workspaceSelectedMissing,
      },
      {
        id: "backend",
        label: pl.chat.checks.backendApi,
        status: !canCheckBackend
          ? "loading"
          : backendLoading
            ? "loading"
            : isBackendReachable
              ? "ok"
              : "error",
        hint: !canCheckBackend
          ? pl.chat.checks.waitingSession
          : backendLoading
              ? pl.chat.checks.checkingBackend
              : isBackendReachable
                ? pl.chat.checks.backendOk
                : pl.chat.checks.backendFail,
      },
      {
        id: "documents",
        label: pl.chat.checks.documentsScope,
        status: !canCheckBackend
          ? "loading"
          : backendError || !isBackendReachable
            ? "error"
            : documentsLoading
              ? "loading"
              : "ok",
        hint: !canCheckBackend
          ? pl.chat.checks.waitingWorkspace
          : backendError || !isBackendReachable
            ? pl.chat.checks.documentsFail
            : documentsLoading
              ? pl.chat.checks.loadingDocuments
              : pl.chat.checks.documentsOk,
      },
      {
        id: "llm",
        label: pl.chat.checks.llmModel,
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
          ? pl.chat.checks.waitingSession
          : !isBackendReachable
            ? pl.chat.checks.llmCannotVerify
            : llmLoading
              ? pl.chat.checks.checkingLlm
              : isLlmReady
                ? pl.chat.checks.llmOk
                : pl.chat.checks.llmFail,
      },
      {
        id: "conversation",
        label: pl.chat.checks.conversationState,
        status: !canCheckBackend
          ? "loading"
          : backendError || !isBackendReachable || !isLlmReady
            ? "error"
            : conversationLoading
              ? "loading"
              : "ok",
        hint: !canCheckBackend
          ? pl.chat.checks.waitingWorkspace
          : backendError || !isBackendReachable || !isLlmReady
            ? pl.chat.checks.conversationFail
            : conversationLoading
              ? pl.chat.checks.conversationLoading
              : pl.chat.checks.conversationOk,
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
        title: pl.chat.requiresAttention,
        hint: pl.chat.requiresAttentionHint,
        checks: readinessChecks,
      };
    }

    if (hasLoading) {
      return {
        status: "loading",
        title: pl.chat.preparing,
        hint: pl.chat.preparingHint,
        checks: readinessChecks,
      };
    }

    return {
      status: "ready",
      title: pl.chat.ready,
      hint: pl.chat.readyHint,
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
    latestResponseMode,
    latestGuardrailReason,
    loadConversations,
    loadDocuments,
    messages,
    chatLogsByMessage,
    chatReadiness,
    scope: scopeDraft,
    hasPendingScopeChanges,
    selectConversation,
    sendMessage,
    setScope: setScopeDraft,
    applyScope,
    startNewConversation,
    clearConversations,
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

function normalizeScopeSelection(scope: RetrievalScope): RetrievalScope {
  if (scope.mode === "all") {
    return { mode: "all" };
  }

  if (scope.mode === "category") {
    const category = scope.category?.trim() ?? "";
    return category ? { mode: "category", category } : { mode: "all" };
  }

  const documentIds = Array.isArray(scope.document_ids) ? scope.document_ids : [];
  return documentIds.length > 0 ? { mode: "documents", document_ids: documentIds } : { mode: "all" };
}

function areScopesEqual(left: RetrievalScope, right: RetrievalScope): boolean {
  const normalizedLeft = normalizeScopeSelection(left);
  const normalizedRight = normalizeScopeSelection(right);

  if (normalizedLeft.mode !== normalizedRight.mode) {
    return false;
  }

  if (normalizedLeft.mode === "all") {
    return true;
  }

  if (normalizedLeft.mode === "category" && normalizedRight.mode === "category") {
    return normalizedLeft.category === normalizedRight.category;
  }

  if (normalizedLeft.mode === "documents" && normalizedRight.mode === "documents") {
    if (normalizedLeft.document_ids.length !== normalizedRight.document_ids.length) {
      return false;
    }
    return normalizedLeft.document_ids.every((id, index) => id === normalizedRight.document_ids[index]);
  }

  return false;
}

function assistantMessageFromResponse(
  conversationId: string,
  workspaceId: string,
  message: {
    id: string;
    role: "assistant";
    content: string;
    sources: ChatSource[];
    cited_sources?: CitationSource[];
    retrieved_sources?: CitationSource[];
    response_mode?: string;
    guardrail_reason?: string | null;
  },
): ChatMessage {
  return {
    id: message.id,
    conversation_id: conversationId,
    workspace_id: workspaceId,
    user_id: null,
    role: message.role,
    content: message.content,
    response_metadata: {
      sources: message.sources,
      cited_sources: message.cited_sources ?? [],
      response_mode: message.response_mode ?? "answer_from_context",
      guardrail_reason: message.guardrail_reason ?? null,
    },
    sources: message.sources,
    cited_sources: message.cited_sources ?? [],
    response_mode: message.response_mode ?? "answer_from_context",
    guardrail_reason: message.guardrail_reason ?? null,
    created_at: new Date().toISOString(),
  };
}

function withExtractedSources(message: ChatMessage): ChatMessage {
  const metadata = message.response_metadata;
  if (!metadata) return message;

  const rawSources = metadata.sources;
  const rawCited = metadata.cited_sources;
  const responseMode = typeof metadata.response_mode === "string" ? metadata.response_mode : undefined;
  const guardrailReason = typeof metadata.guardrail_reason === "string" ? metadata.guardrail_reason : null;

  return {
    ...message,
    sources: Array.isArray(rawSources) ? rawSources.filter(isChatSource) : message.sources,
    cited_sources: Array.isArray(rawCited) ? rawCited.filter(isCitationSource) : message.cited_sources,
    response_mode: responseMode ?? message.response_mode,
    guardrail_reason: guardrailReason ?? message.guardrail_reason,
  };
}

function isChatSource(value: unknown): value is ChatSource {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  return "document_id" in value && "document_title" in value && "snippet" in value;
}

function isCitationSource(value: unknown): value is CitationSource {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  return "citation_id" in value && "excerpt" in value && "document_id" in value;
}

/** Convert legacy ChatSource to CitationSource for unified rendering */
function chatSourceToCitation(source: ChatSource, index: number): CitationSource {
  return {
    citation_id: `legacy-${source.chunk_id ?? source.document_id}-${index}`,
    chunk_id: source.chunk_id ?? "",
    chunk_index: index,
    document_id: source.document_id,
    document_version_id: source.document_version_id,
    document_title: source.document_title,
    section_path: source.section_path ? [source.section_path] : [],
    excerpt: source.snippet,
    heading: null,
    retrieval_score: source.score,
    rank: index + 1,
    workspace_id: "",
    category: source.category,
  };
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
  return pl.errors.frontendUnexpected;
}
