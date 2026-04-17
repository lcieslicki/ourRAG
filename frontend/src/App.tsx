import React, { useMemo, useState } from "react";

import { AppLayout } from "./app/AppLayout";
import { ConversationList } from "./components/ConversationList";
import { WorkspaceSwitcher } from "./components/WorkspaceSwitcher";
import { AssistantRuntimeBridge } from "./features/chat/AssistantRuntimeBridge";
import { ChatPage } from "./features/chat/ChatPage";
import { ScopeFilters } from "./features/chat/ScopeFilters";
import { useWorkspaceChat } from "./features/chat/useWorkspaceChat";
import { ApiClient } from "./lib/api/client";
import { config } from "./config";

export function App() {
  const [userId, setUserId] = useState("");
  const [workspaceId, setWorkspaceId] = useState("");

  const apiClient = useMemo(() => new ApiClient(config.api.baseUrl, () => userId), [userId]);
  const chat = useWorkspaceChat({ apiClient, userId, workspaceId });

  return (
    <AssistantRuntimeBridge
      messages={chat.messages}
      isRunning={chat.isSending}
      isDisabled={chat.isDisabled}
      onSubmit={chat.sendMessage}
    >
      <AppLayout
        sidebar={
          <>
            <WorkspaceSwitcher
              userId={userId}
              workspaceId={workspaceId}
              onUserIdChange={setUserId}
              onWorkspaceIdChange={setWorkspaceId}
              onWorkspaceCommitted={() => void chat.loadConversations()}
            />
            <ConversationList
              conversations={chat.conversations}
              activeConversationId={chat.activeConversationId}
              isLoading={chat.isLoadingConversations}
              onSelectConversation={(conversationId) => void chat.selectConversation(conversationId)}
              onStartNewConversation={chat.startNewConversation}
              onRefresh={() => void chat.loadConversations()}
            />
          </>
        }
      >
        <ChatPage
          workspaceId={workspaceId}
          conversationId={chat.activeConversationId}
          error={chat.error}
          isLoadingConversation={chat.isLoadingConversation}
          isSending={chat.isSending}
          scopeFilters={
            <ScopeFilters
              documents={chat.documents}
              isLoading={chat.isLoadingDocuments}
              scope={chat.scope}
              onScopeChange={chat.setScope}
              onRefreshDocuments={() => void chat.loadDocuments()}
            />
          }
          sources={chat.latestSources}
        />
      </AppLayout>
    </AssistantRuntimeBridge>
  );
}
