import { Fragment, useEffect, useRef, useState } from "react";
import { Link, Navigate, Route, Routes, useNavigate, useParams } from "react-router-dom";
import type { ApiClient } from "../../lib/api/client";
import type {
  AdminDocumentListItem,
  AdminUserResponse,
  AdminWorkspaceMemberResponse,
  AdminWorkspaceResponse,
} from "../../lib/api/types";

type Props = { apiClient: ApiClient };

export function AdminCrudRoutes({ apiClient }: Props) {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/admin/workspaces" replace />} />
      <Route path="/workspaces" element={<WorkspaceListView apiClient={apiClient} />} />
      <Route path="/workspaces/new" element={<WorkspaceCreateView apiClient={apiClient} />} />
      <Route path="/workspaces/:workspaceId/edit" element={<WorkspaceEditView apiClient={apiClient} />} />
      <Route path="/workspaces/:workspaceId" element={<WorkspaceDetailsView apiClient={apiClient} />} />
      <Route path="/users" element={<UsersListView apiClient={apiClient} />} />
      <Route path="/users/new" element={<UserCreateView apiClient={apiClient} />} />
      <Route path="/users/:userId" element={<UserDetailsView apiClient={apiClient} />} />
    </Routes>
  );
}

function AdminHeader() {
  return (
    <div className="admin-header">
      <h2>Panel Admina</h2>
      <p className="muted">Standardowy CRUD: listy, podglądy, tworzenie i usuwanie zasobów.</p>
    </div>
  );
}

function UsersListView({ apiClient }: Props) {
  const [users, setUsers] = useState<AdminUserResponse[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void apiClient.adminListUsers().then(setUsers).catch((e) => setError(String(e)));
  }, [apiClient]);

  return (
    <div className="admin-panel">
      <AdminHeader />
      <div className="admin-content">
        <div className="admin-list-block">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <h3>Użytkownicy ({users.length})</h3>
            <Link className="admin-btn-small" to="/admin/users/new">Utwórz nowego użytkownika</Link>
          </div>
          {error && <div className="error-banner">{error}</div>}
          {users.length === 0 ? (
            <p className="muted">Brak użytkowników.</p>
          ) : (
            <table className="admin-table">
              <thead>
                <tr><th>Email</th><th>Nazwa</th><th>Status</th><th>Akcje</th></tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id}>
                    <td>{u.email}</td>
                    <td>{u.display_name}</td>
                    <td>{u.status}</td>
                    <td style={{ display: "flex", gap: 8 }}>
                      <Link className="admin-btn-small" to={`/admin/users/${u.id}`}>Podgląd</Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}

function UserCreateView({ apiClient }: Props) {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!email.trim() || !displayName.trim()) return;
    setSaving(true);
    setError(null);
    try {
      const user = await apiClient.adminCreateUser({ email: email.trim(), display_name: displayName.trim() });
      navigate(`/admin/users/${user.id}`);
    } catch (err) {
      setError(String(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="admin-panel">
      <AdminHeader />
      <div className="admin-content">
        <div className="admin-form-block">
          <h3>Nowy użytkownik</h3>
          {error && <div className="error-banner">{error}</div>}
          <form className="admin-form" onSubmit={(e) => void handleCreate(e)}>
            <label>Email<input value={email} onChange={(e) => setEmail(e.target.value)} type="email" required /></label>
            <label>Nazwa wyświetlana<input value={displayName} onChange={(e) => setDisplayName(e.target.value)} required /></label>
            <div style={{ display: "flex", gap: 8 }}>
              <button type="submit" disabled={saving || !email.trim() || !displayName.trim()}>{saving ? "Tworzenie..." : "Utwórz użytkownika"}</button>
              <Link className="admin-btn-small" to="/admin/users">Powrót do listy</Link>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

function UserDetailsView({ apiClient }: Props) {
  const { userId } = useParams();
  const navigate = useNavigate();
  const [user, setUser] = useState<AdminUserResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!userId) return;
    void apiClient.adminGetUser(userId).then(setUser).catch((e) => setError(String(e))).finally(() => setLoading(false));
  }, [apiClient, userId]);

  async function handleDelete() {
    if (!userId) return;
    const ok = window.confirm("Usunąć tego użytkownika?");
    if (!ok) return;
    setDeleting(true);
    try {
      await apiClient.adminDeleteUser(userId);
      navigate("/admin/users");
    } catch (e) {
      setError(String(e));
    } finally {
      setDeleting(false);
    }
  }

  return (
    <div className="admin-panel">
      <AdminHeader />
      <div className="admin-content">
        <div className="admin-list-block">
          <h3>Podgląd użytkownika</h3>
          {error && <div className="error-banner">{error}</div>}
          {loading ? <p className="muted">Ładowanie...</p> : user ? (
            <>
              <p><strong>ID:</strong> <code>{user.id}</code></p>
              <p><strong>Email:</strong> {user.email}</p>
              <p><strong>Nazwa:</strong> {user.display_name}</p>
              <p><strong>Status:</strong> {user.status}</p>
              <div style={{ display: "flex", gap: 8 }}>
                <button className="admin-btn-small" type="button" onClick={() => void handleDelete()} disabled={deleting}>
                  {deleting ? "Usuwanie..." : "Usuń użytkownika"}
                </button>
                <Link className="admin-btn-small" to="/admin/users">Powrót do listy</Link>
              </div>
            </>
          ) : <p className="muted">Nie znaleziono użytkownika.</p>}
        </div>
      </div>
    </div>
  );
}

function WorkspaceListView({ apiClient }: Props) {
  const [workspaces, setWorkspaces] = useState<AdminWorkspaceResponse[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void apiClient.adminListWorkspaces().then(setWorkspaces).catch((e) => setError(String(e)));
  }, [apiClient]);

  return (
    <div className="admin-panel">
      <AdminHeader />
      <div className="admin-content">
        <div className="admin-list-block">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <h3>Przestrzenie robocze ({workspaces.length})</h3>
            <Link className="admin-btn-small" to="/admin/workspaces/new">Utwórz nową przestrzeń roboczą</Link>
          </div>
          {error && <div className="error-banner">{error}</div>}
          {workspaces.length === 0 ? (
            <p className="muted">Brak przestrzeni roboczych.</p>
          ) : (
            <table className="admin-table">
              <thead>
                <tr><th>Slug</th><th>Nazwa</th><th>Status</th><th>Akcje</th></tr>
              </thead>
              <tbody>
                {workspaces.map((w) => (
                  <tr key={w.id}>
                    <td><code>{w.slug}</code></td>
                    <td>{w.name}</td>
                    <td>{w.status}</td>
                    <td><Link className="admin-btn-small" to={`/admin/workspaces/${w.id}`}>Podgląd</Link></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}

function WorkspaceCreateView({ apiClient }: Props) {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [dataFolder, setDataFolder] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim() || !slug.trim()) return;
    setSaving(true);
    setError(null);
    try {
      const workspace = await apiClient.adminCreateWorkspace({ name: name.trim(), slug: slug.trim() });
      if (dataFolder.trim()) {
        await apiClient.adminUpdateWorkspace(workspace.id, {
          name: workspace.name,
          slug: workspace.slug,
          data_folder: dataFolder.trim(),
        });
      }
      navigate(`/admin/workspaces/${workspace.id}`);
    } catch (err) {
      setError(String(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="admin-panel">
      <AdminHeader />
      <div className="admin-content">
        <div className="admin-form-block">
          <h3>Nowa przestrzeń robocza</h3>
          {error && <div className="error-banner">{error}</div>}
          <form className="admin-form" onSubmit={(e) => void handleCreate(e)}>
            <label>Nazwa<input value={name} onChange={(e) => setName(e.target.value)} required /></label>
            <label>Slug<input value={slug} onChange={(e) => setSlug(e.target.value)} required /></label>
            <label>Folder danych<input value={dataFolder} onChange={(e) => setDataFolder(e.target.value)} placeholder="np. firma_ABC" /></label>
            <div style={{ display: "flex", gap: 8 }}>
              <button type="submit" disabled={saving || !name.trim() || !slug.trim()}>{saving ? "Tworzenie..." : "Utwórz przestrzeń roboczą"}</button>
              <Link className="admin-btn-small" to="/admin/workspaces">Powrót do listy</Link>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

function WorkspaceEditView({ apiClient }: Props) {
  const { workspaceId } = useParams();
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [dataFolder, setDataFolder] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!workspaceId) return;
    void apiClient.adminGetWorkspace(workspaceId)
      .then((workspace) => {
        setName(workspace.name);
        setSlug(workspace.slug);
        setDataFolder(workspace.data_folder ?? "");
      })
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, [apiClient, workspaceId]);

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    if (!workspaceId || !name.trim() || !slug.trim()) return;
    setSaving(true);
    setError(null);
    try {
      await apiClient.adminUpdateWorkspace(workspaceId, {
        name: name.trim(),
        slug: slug.trim(),
        data_folder: dataFolder.trim() || null,
      });
      navigate(`/admin/workspaces/${workspaceId}`);
    } catch (err) {
      setError(String(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="admin-panel">
      <AdminHeader />
      <div className="admin-content">
        <div className="admin-form-block">
          <h3>Edycja workspace</h3>
          {error && <div className="error-banner">{error}</div>}
          {loading ? <p className="muted">Ładowanie...</p> : (
            <form className="admin-form" onSubmit={(e) => void handleSave(e)}>
              <label>Nazwa<input value={name} onChange={(e) => setName(e.target.value)} required /></label>
              <label>Slug<input value={slug} onChange={(e) => setSlug(e.target.value)} required /></label>
              <label>Folder danych<input value={dataFolder} onChange={(e) => setDataFolder(e.target.value)} placeholder="np. firma_ABC" /></label>
              <div style={{ display: "flex", gap: 8 }}>
                <button type="submit" disabled={saving || !name.trim() || !slug.trim()}>{saving ? "Zapisywanie..." : "Zapisz zmiany"}</button>
                {workspaceId && <Link className="admin-btn-small" to={`/admin/workspaces/${workspaceId}`}>Powrót do podglądu</Link>}
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}

function WorkspaceDetailsView({ apiClient }: Props) {
  const { workspaceId } = useParams();
  const navigate = useNavigate();
  const [workspace, setWorkspace] = useState<AdminWorkspaceResponse | null>(null);
  const [users, setUsers] = useState<AdminUserResponse[]>([]);
  const [members, setMembers] = useState<AdminWorkspaceMemberResponse[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [indexing, setIndexing] = useState(false);
  const [warnings, setWarnings] = useState<{ file_name: string; error: string }[]>([]);

  useEffect(() => {
    if (!workspaceId) return;
    void Promise.all([
      apiClient.adminGetWorkspace(workspaceId),
      apiClient.adminListUsers(),
      apiClient.adminListMembers(workspaceId),
    ])
      .then(([w, allUsers, wsMembers]) => {
        setWorkspace(w);
        setUsers(allUsers);
        setMembers(wsMembers);
      })
      .catch((e) => setError(String(e)));
  }, [apiClient, workspaceId]);

  async function handleDeleteWorkspace() {
    if (!workspaceId) return;
    const ok = window.confirm("Usunąć przestrzeń roboczą? Operacja jest nieodwracalna.");
    if (!ok) return;
    setDeleting(true);
    try {
      await apiClient.adminDeleteWorkspace(workspaceId);
      navigate("/admin/workspaces");
    } catch (e) {
      setError(String(e));
    } finally {
      setDeleting(false);
    }
  }

  async function handleIndexFolder() {
    if (!workspaceId || !workspace?.data_folder) return;
    setIndexing(true);
    setWarnings([]);
    try {
      const res = await apiClient.adminIndexFolder(workspaceId);
      setWarnings(res.failed);
    } catch (e) {
      setError(String(e));
    } finally {
      setIndexing(false);
    }
  }

  if (!workspaceId) return null;

  return (
    <div className="admin-panel">
      <AdminHeader />
      <div className="admin-content">
        <div className="admin-list-block">
          <h3>Podgląd przestrzeni roboczej</h3>
          {error && <div className="error-banner">{error}</div>}
          {!workspace ? <p className="muted">Ładowanie...</p> : (
            <>
              <p><strong>ID:</strong> <code>{workspace.id}</code></p>
              <p><strong>Nazwa:</strong> {workspace.name}</p>
              <p><strong>Slug:</strong> <code>{workspace.slug}</code></p>
              <p><strong>Folder danych:</strong> {workspace.data_folder ? <code>{workspace.data_folder}</code> : <span className="muted">Nie ustawiono</span>}</p>
              <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
                <button
                  className="admin-btn-small"
                  type="button"
                  onClick={() => void handleIndexFolder()}
                  disabled={indexing || !workspace.data_folder}
                >
                  {indexing ? "Indeksowanie..." : "Indeksuj folder"}
                </button>
                <Link className="admin-btn-small" to={`/admin/workspaces/${workspace.id}/edit`}>Edytuj przestrzeń roboczą</Link>
                <button className="admin-btn-small" type="button" onClick={() => void handleDeleteWorkspace()} disabled={deleting}>
                  {deleting ? "Usuwanie..." : "Usuń przestrzeń roboczą"}
                </button>
                <Link className="admin-btn-small" to="/admin/workspaces">Powrót do listy</Link>
              </div>
              {warnings.length > 0 && <div className="error-banner">{warnings.map((w) => <div key={w.file_name}>{w.file_name}: {w.error}</div>)}</div>}
              <MembersBlock
                workspace={workspace}
                members={members}
                users={users}
                onMemberAdded={(member) => setMembers((prev) => [...prev, member])}
                apiClient={apiClient}
                onError={setError}
              />
              <DocumentsBlock
                workspace={workspace}
                apiClient={apiClient}
                onError={setError}
              />
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function MembersBlock({ workspace, members, users, onMemberAdded, apiClient, onError }: {
  workspace: AdminWorkspaceResponse;
  members: AdminWorkspaceMemberResponse[];
  users: AdminUserResponse[];
  onMemberAdded: (m: AdminWorkspaceMemberResponse) => void;
  apiClient: ApiClient;
  onError: (e: string) => void;
}) {
  const [userId, setUserId] = useState("");
  const [role, setRole] = useState("owner");
  const [saving, setSaving] = useState(false);
  const existingIds = new Set(members.map((m) => m.user_id));
  const availableUsers = users.filter((u) => !existingIds.has(u.id));

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    if (!userId) return;
    setSaving(true);
    try {
      const member = await apiClient.adminAddMember(workspace.id, { user_id: userId, role });
      onMemberAdded(member);
      setUserId("");
    } catch (err) {
      onError(String(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="admin-members-block">
      <h3>Zarządzanie użytkownikami przestrzeni roboczej</h3>
      {members.length === 0 ? <p className="muted">Brak członków.</p> : (
        <table className="admin-table">
          <thead><tr><th>Email</th><th>Nazwa</th><th>Rola</th></tr></thead>
          <tbody>
            {members.map((m) => (
              <tr key={m.user_id}><td>{m.email}</td><td>{m.display_name}</td><td>{m.role}</td></tr>
            ))}
          </tbody>
        </table>
      )}
      {availableUsers.length > 0 && (
        <form className="admin-form admin-form-inline" onSubmit={(e) => void handleAdd(e)}>
          <label>
            Użytkownik
            <select value={userId} onChange={(e) => setUserId(e.target.value)} required>
              <option value="">Wybierz…</option>
              {availableUsers.map((u) => <option key={u.id} value={u.id}>{u.email} - {u.display_name}</option>)}
            </select>
          </label>
          <label>
            Rola
            <select value={role} onChange={(e) => setRole(e.target.value)}>
              <option value="owner">owner</option>
              <option value="admin">admin</option>
              <option value="member">member</option>
              <option value="viewer">viewer</option>
            </select>
          </label>
          <button type="submit" disabled={saving || !userId}>{saving ? "Dodawanie..." : "Dodaj członka"}</button>
        </form>
      )}
    </div>
  );
}

function DocumentsBlock({ workspace, apiClient, onError }: {
  workspace: AdminWorkspaceResponse;
  apiClient: ApiClient;
  onError: (e: string) => void;
}) {
  const [documents, setDocuments] = useState<AdminDocumentListItem[]>([]);
  const [files, setFiles] = useState<FileList | null>(null);
  const [uploading, setUploading] = useState(false);
  const [warnings, setWarnings] = useState<{ file_name: string; error: string }[]>([]);
  const uploadInputRef = useRef<HTMLInputElement | null>(null);
  const [deletingDocumentId, setDeletingDocumentId] = useState<string | null>(null);
  const [selectedDocumentIds, setSelectedDocumentIds] = useState<Set<string>>(new Set());
  const [bulkDeleting, setBulkDeleting] = useState(false);
  const [bulkReindexing, setBulkReindexing] = useState(false);
  const [bulkFeedback, setBulkFeedback] = useState<string | null>(null);

  useEffect(() => {
    void loadDocuments();
  }, [workspace.id]);

  async function loadDocuments() {
    try {
      setDocuments(await apiClient.adminListWorkspaceDocuments(workspace.id));
      setSelectedDocumentIds(new Set());
    } catch (e) {
      onError(String(e));
    }
  }
  async function handleUpload() {
    if (!files?.length) return;
    setUploading(true);
    setWarnings([]);
    try {
      const res = await apiClient.adminUploadDocuments(workspace.id, { files });
      setWarnings(res.failed);
      setFiles(null);
      if (uploadInputRef.current) uploadInputRef.current.value = "";
      await loadDocuments();
    } catch (e) {
      onError(String(e));
    } finally {
      setUploading(false);
    }
  }
  async function handleDeleteDocument(documentId: string) {
    if (!window.confirm("Na pewno usunąć dokument?")) return;
    setDeletingDocumentId(documentId);
    try {
      await apiClient.adminDeleteDocument(workspace.id, documentId);
      await loadDocuments();
    } catch (e) {
      onError(String(e));
    } finally {
      setDeletingDocumentId(null);
    }
  }

  function toggleDocumentSelection(documentId: string) {
    setSelectedDocumentIds((previous) => {
      const next = new Set(previous);
      if (next.has(documentId)) {
        next.delete(documentId);
      } else {
        next.add(documentId);
      }
      return next;
    });
  }

  function toggleSelectAllVisible() {
    const visibleIds = documents.map((document) => document.id);
    setSelectedDocumentIds((previous) => {
      const allSelected = visibleIds.length > 0 && visibleIds.every((id) => previous.has(id));
      if (allSelected) {
        return new Set();
      }
      return new Set(visibleIds);
    });
  }

  async function handleDeleteSelected() {
    if (selectedDocumentIds.size === 0) return;
    const ok = window.confirm(`Usunąć ${selectedDocumentIds.size} zaznaczonych dokumentów?`);
    if (!ok) return;
    setBulkDeleting(true);
    setBulkFeedback(null);
    let successCount = 0;
    let failureCount = 0;
    try {
      for (const documentId of selectedDocumentIds) {
        try {
          await apiClient.adminDeleteDocument(workspace.id, documentId);
          successCount += 1;
        } catch {
          failureCount += 1;
        }
      }
      await loadDocuments();
      setBulkFeedback(`Usunięto: ${successCount}, błędy: ${failureCount}.`);
    } finally {
      setBulkDeleting(false);
    }
  }

  async function handleReindexSelected() {
    if (selectedDocumentIds.size === 0) return;
    setBulkReindexing(true);
    setBulkFeedback(null);
    let queuedCount = 0;
    let skippedCount = 0;
    let failureCount = 0;
    const selectedDocuments = documents.filter((document) => selectedDocumentIds.has(document.id));
    try {
      for (const document of selectedDocuments) {
        if (!document.latest_version_id || document.is_active === false) {
          skippedCount += 1;
          continue;
        }
        try {
          await apiClient.reindexDocumentVersion(document.id, document.latest_version_id);
          queuedCount += 1;
        } catch {
          failureCount += 1;
        }
      }
      await loadDocuments();
      setBulkFeedback(`Do reprocessingu: ${queuedCount}, pominięte: ${skippedCount}, błędy: ${failureCount}.`);
    } finally {
      setBulkReindexing(false);
    }
  }

  const allVisibleSelected =
    documents.length > 0 && documents.every((document) => selectedDocumentIds.has(document.id));

  return (
    <div className="admin-members-block">
      <h3>Zarządzanie dokumentami przestrzeni roboczej</h3>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 8 }}>
        <input ref={uploadInputRef} type="file" accept=".md" multiple onChange={(e) => setFiles(e.target.files)} />
        <button className="admin-btn-small" type="button" onClick={() => void handleUpload()} disabled={uploading || !files?.length}>
          {uploading ? "Przesyłanie..." : "Dodaj plik"}
        </button>
      </div>
      {warnings.length > 0 && <div className="error-banner">{warnings.map((w) => <div key={w.file_name}>{w.file_name}: {w.error}</div>)}</div>}
      <h4>Lista dokumentów ({documents.length})</h4>
      {bulkFeedback && <div className="error-banner">{bulkFeedback}</div>}
      {documents.length > 0 && (
        <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 8 }}>
          <label style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <input type="checkbox" checked={allVisibleSelected} onChange={() => toggleSelectAllVisible()} />
            Zaznacz wszystko (widoczne)
          </label>
          <span className="muted">Zaznaczono: {selectedDocumentIds.size}</span>
          <button
            className="admin-btn-small"
            type="button"
            onClick={() => void handleDeleteSelected()}
            disabled={selectedDocumentIds.size === 0 || bulkDeleting || bulkReindexing}
          >
            {bulkDeleting ? "Usuwanie zaznaczonych..." : "Usuń zaznaczone"}
          </button>
          <button
            className="admin-btn-small"
            type="button"
            onClick={() => void handleReindexSelected()}
            disabled={selectedDocumentIds.size === 0 || bulkReindexing || bulkDeleting}
          >
            {bulkReindexing ? "Kolejkowanie..." : "Prześlij zaznaczone do przetwarzania"}
          </button>
        </div>
      )}
      {documents.length === 0 ? <p className="muted">Brak dokumentów.</p> : (
        <table className="admin-table">
          <thead><tr><th></th><th>Tytuł</th><th>Status</th><th>Wersje</th><th>Akcje</th></tr></thead>
          <tbody>
            {documents.map((d) => (
              <Fragment key={d.id}>
                <tr>
                  <td>
                    <input
                      type="checkbox"
                      checked={selectedDocumentIds.has(d.id)}
                      onChange={() => toggleDocumentSelection(d.id)}
                    />
                  </td>
                  <td>{d.title}</td>
                  <td>{d.latest_processing_status ?? "-"}</td>
                  <td>{d.version_count}</td>
                  <td>
                    <button className="admin-btn-small" type="button" onClick={() => void handleDeleteDocument(d.id)} disabled={deletingDocumentId === d.id}>
                      {deletingDocumentId === d.id ? "Usuwanie..." : "Usuń"}
                    </button>
                  </td>
                </tr>
                {d.latest_error_message && (
                  <tr>
                    <td></td>
                    <td colSpan={4}>
                      <div className="error-banner" style={{ margin: 0 }}>
                        <strong>Błąd indeksacji{d.latest_error_job_type ? ` (${d.latest_error_job_type})` : ""}:</strong> {d.latest_error_message}
                      </div>
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
