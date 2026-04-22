import { useEffect, useState } from "react";
import { ApiClient } from "../../lib/api/client";
import type { AdminUserResponse, WorkspaceSummary } from "../../lib/api/types";
import { config } from "../../config";
import { pl } from "../../i18n/pl";

export type Session = {
  userId: string;
  userEmail: string;
  workspaceId: string;
  workspaceName: string;
};

type Props = {
  onLogin: (session: Session) => void;
};

export function LoginScreen({ onLogin }: Props) {
  const [users, setUsers] = useState<AdminUserResponse[]>([]);
  const [workspaces, setWorkspaces] = useState<WorkspaceSummary[]>([]);
  const [selectedUserId, setSelectedUserId] = useState("");
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState("");
  const [loadingUsers, setLoadingUsers] = useState(true);
  const [loadingWorkspaces, setLoadingWorkspaces] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const adminClient = new ApiClient(config.api.baseUrl, () => "");
    adminClient.adminListUsers()
      .then(setUsers)
      .catch((e) => setError(String(e)))
      .finally(() => setLoadingUsers(false));
  }, []);

  useEffect(() => {
    if (!selectedUserId) {
      setWorkspaces([]);
      setSelectedWorkspaceId("");
      return;
    }
    setLoadingWorkspaces(true);
    setWorkspaces([]);
    setSelectedWorkspaceId("");
    const client = new ApiClient(config.api.baseUrl, () => selectedUserId);
    client.listWorkspaces()
      .then(setWorkspaces)
      .catch((e) => setError(String(e)))
      .finally(() => setLoadingWorkspaces(false));
  }, [selectedUserId]);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const user = users.find((u) => u.id === selectedUserId);
    const workspace = workspaces.find((w) => w.id === selectedWorkspaceId);
    if (!user || !workspace) return;
    onLogin({
      userId: user.id,
      userEmail: user.email,
      workspaceId: workspace.id,
      workspaceName: workspace.name,
    });
  }

  return (
    <div className="login-screen">
      <div className="login-card">
        <p className="eyebrow">ourRAG</p>
        <h1>Wybierz sesję</h1>

        {error && (
          <div className="error-banner" style={{ marginBottom: 16 }}>
            {error}
            <button className="admin-dismiss" onClick={() => setError(null)}>✕</button>
          </div>
        )}

        <form className="login-form" onSubmit={handleSubmit}>
          <label>
            Użytkownik
            <select
              value={selectedUserId}
              onChange={(e) => setSelectedUserId(e.target.value)}
              required
              disabled={loadingUsers}
            >
              <option value="">{loadingUsers ? "Ładowanie…" : "Wybierz użytkownika…"}</option>
              {users.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.email} — {u.display_name}
                </option>
              ))}
            </select>
          </label>

          <label>
            {pl.login.workspaceLabel}
            <select
              value={selectedWorkspaceId}
              onChange={(e) => setSelectedWorkspaceId(e.target.value)}
              required
              disabled={!selectedUserId || loadingWorkspaces}
            >
              <option value="">
                {!selectedUserId
                  ? "Najpierw wybierz użytkownika"
                  : loadingWorkspaces
                    ? pl.login.loadingWorkspaces
                    : workspaces.length === 0
                      ? pl.login.noAssignedWorkspaces
                      : pl.login.selectWorkspace}
              </option>
              {workspaces.map((w) => (
                <option key={w.id} value={w.id}>
                  {w.name}
                </option>
              ))}
            </select>
          </label>

          <button
            type="submit"
            disabled={!selectedUserId || !selectedWorkspaceId}
          >
            {pl.login.openWorkspace}
          </button>
        </form>
      </div>
    </div>
  );
}
