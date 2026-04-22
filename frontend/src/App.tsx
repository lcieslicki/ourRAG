import React, { useMemo, useState } from "react";
import { Link, Navigate, Route, Routes } from "react-router-dom";

import { AppLayout } from "./app/AppLayout";
import { ConversationList } from "./components/ConversationList";
import { WorkspaceSwitcher } from "./components/WorkspaceSwitcher";
import { AssistantRuntimeBridge } from "./features/chat/AssistantRuntimeBridge";
import { ChatPage } from "./features/chat/ChatPage";
import { ScopeFilters } from "./features/chat/ScopeFilters";
import { useWorkspaceChat } from "./features/chat/useWorkspaceChat";
import { AdminCrudRoutes } from "./features/admin/AdminCrudRoutes";
import { LoginScreen, type Session } from "./features/auth/LoginScreen";
import { ApiClient } from "./lib/api/client";
import { config } from "./config";
import { pl } from "./i18n/pl";

const SESSION_KEY = "ourrag_session";

function loadSession(): Session | null {
  try {
    const raw = localStorage.getItem(SESSION_KEY);
    return raw ? (JSON.parse(raw) as Session) : null;
  } catch {
    return null;
  }
}

function saveSession(session: Session): void {
  localStorage.setItem(SESSION_KEY, JSON.stringify(session));
}

function clearSession(): void {
  localStorage.removeItem(SESSION_KEY);
}

export function App() {
  const [session, setSession] = useState<Session | null>(loadSession);

  const apiClient = useMemo(
    () => new ApiClient(config.api.baseUrl, () => session?.userId ?? ""),
    [session?.userId],
  );

  const chat = useWorkspaceChat({ apiClient, userId: session?.userId ?? "", workspaceId: session?.workspaceId ?? "" });

  function handleLogin(newSession: Session) {
    saveSession(newSession);
    setSession(newSession);
    void chat.loadConversations();
  }

  function handleLogout() {
    clearSession();
    setSession(null);
  }

  if (!session) {
    return <LoginScreen onLogin={handleLogin} />;
  }

  return (
    <AssistantRuntimeBridge
      messages={chat.messages}
      isRunning={chat.isSending}
      isDisabled={chat.isDisabled}
      onSubmit={chat.sendMessage}
      children={(
        <AppLayout
          sidebar={(
            <>
              <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
                <Link className="admin-toggle" to="/chat">{pl.app.chatTab}</Link>
                <Link className="admin-toggle" to="/admin/workspaces">{pl.app.adminTab}</Link>
              </div>
              <WorkspaceSwitcher session={session} onLogout={handleLogout} />
              <ConversationList
                conversations={chat.conversations}
                activeConversationId={chat.activeConversationId}
                isLoading={chat.isLoadingConversations}
                onSelectConversation={(conversationId) => void chat.selectConversation(conversationId)}
                onStartNewConversation={chat.startNewConversation}
                onRefresh={() => void chat.loadConversations()}
                onDeleteAll={() => void chat.clearConversations()}
              />
            </>
          )}
          children={(
            <Routes>
              <Route
                path="/chat"
                element={(
                  <ChatPage
                    workspaceId={session.workspaceId}
                    conversationId={chat.activeConversationId}
                    error={chat.error}
                    isLoadingConversation={chat.isLoadingConversation}
                    isSending={chat.isSending}
                    scopeFilters={(
                      <ScopeFilters
                        documents={chat.documents}
                        isLoading={chat.isLoadingDocuments}
                        scope={chat.scope}
                        onScopeChange={chat.setScope}
                        onApplyScope={chat.applyScope}
                        hasPendingScopeChanges={chat.hasPendingScopeChanges}
                        onRefreshDocuments={() => void chat.loadDocuments()}
                      />
                    )}
                    sources={chat.latestSources}
                    chatLogsByMessage={chat.chatLogsByMessage}
                    chatReadiness={chat.chatReadiness}
                  />
                )}
              />
              <Route path="/admin/*" element={<AdminCrudRoutes apiClient={apiClient} />} />
              <Route path="*" element={<Navigate to="/chat" replace />} />
            </Routes>
          )}
        />
      )}
    />
  );
}
