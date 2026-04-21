import { useEffect, useRef, useState } from "react";
import { Link, Navigate, Route, Routes, useNavigate, useParams } from "react-router-dom";
import type { ApiClient } from "../../lib/api/client";
import type {
  AdminDocumentListItem,
  AdminProcessingJob,
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
            <Link className="admin-btn-small" to="/admin/users/new">Utwórz nowego usera</Link>
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
          <h3>Nowy user</h3>
          {error && <div className="error-banner">{error}</div>}
          <form className="admin-form" onSubmit={(e) => void handleCreate(e)}>
            <label>Email<input value={email} onChange={(e) => setEmail(e.target.value)} type="email" required /></label>
            <label>Nazwa wyświetlana<input value={displayName} onChange={(e) => setDisplayName(e.target.value)} required /></label>
            <div style={{ display: "flex", gap: 8 }}>
              <button type="submit" disabled={saving || !email.trim() || !displayName.trim()}>{saving ? "Tworzenie..." : "Utwórz usera"}</button>
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
    const ok = window.confirm("Usunąć tego usera?");
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
          <h3>Podgląd usera</h3>
          {error && <div className="error-banner">{error}</div>}
          {loading ? <p className="muted">Ładowanie...</p> : user ? (
            <>
              <p><strong>ID:</strong> <code>{user.id}</code></p>
              <p><strong>Email:</strong> {user.email}</p>
              <p><strong>Nazwa:</strong> {user.display_name}</p>
              <p><strong>Status:</strong> {user.status}</p>
              <div style={{ display: "flex", gap: 8 }}>
                <button className="admin-btn-small" type="button" onClick={() => void handleDelete()} disabled={deleting}>
                  {deleting ? "Usuwanie..." : "Usuń usera"}
                </button>
                <Link className="admin-btn-small" to="/admin/users">Powrót do listy</Link>
              </div>
            </>
          ) : <p className="muted">Nie znaleziono usera.</p>}
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
            <h3>Workspace&apos;y ({workspaces.length})</h3>
            <Link className="admin-btn-small" to="/admin/workspaces/new">Utwórz nowy workspace</Link>
          </div>
          {error && <div className="error-banner">{error}</div>}
          {workspaces.length === 0 ? (
            <p className="muted">Brak workspace&apos;ów.</p>
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
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim() || !slug.trim()) return;
    setSaving(true);
    setError(null);
    try {
      const workspace = await apiClient.adminCreateWorkspace({ name: name.trim(), slug: slug.trim() });
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
          <h3>Nowy workspace</h3>
          {error && <div className="error-banner">{error}</div>}
          <form className="admin-form" onSubmit={(e) => void handleCreate(e)}>
            <label>Nazwa<input value={name} onChange={(e) => setName(e.target.value)} required /></label>
            <label>Slug<input value={slug} onChange={(e) => setSlug(e.target.value)} required /></label>
            <div style={{ display: "flex", gap: 8 }}>
              <button type="submit" disabled={saving || !name.trim() || !slug.trim()}>{saving ? "Tworzenie..." : "Utwórz workspace"}</button>
              <Link className="admin-btn-small" to="/admin/workspaces">Powrót do listy</Link>
            </div>
          </form>
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
    const ok = window.confirm("Usunąć workspace? Operacja jest nieodwracalna.");
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

  if (!workspaceId) return null;

  return (
    <div className="admin-panel">
      <AdminHeader />
      <div className="admin-content">
        <div className="admin-list-block">
          <h3>Podgląd workspace</h3>
          {error && <div className="error-banner">{error}</div>}
          {!workspace ? <p className="muted">Ładowanie...</p> : (
            <>
              <p><strong>ID:</strong> <code>{workspace.id}</code></p>
              <p><strong>Nazwa:</strong> {workspace.name}</p>
              <p><strong>Slug:</strong> <code>{workspace.slug}</code></p>
              <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
                <button className="admin-btn-small" type="button" onClick={() => void handleDeleteWorkspace()} disabled={deleting}>
                  {deleting ? "Usuwanie..." : "Usuń workspace"}
                </button>
                <Link className="admin-btn-small" to="/admin/workspaces">Powrót do listy</Link>
              </div>
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
                users={users}
                onWorkspaceUpdated={setWorkspace}
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
      <h3>Zarządzanie użytkownikami workspace</h3>
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
              <option value="">Wybierz...</option>
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

function DocumentsBlock({ workspace, users, onWorkspaceUpdated, apiClient, onError }: {
  workspace: AdminWorkspaceResponse;
  users: AdminUserResponse[];
  onWorkspaceUpdated: (w: AdminWorkspaceResponse) => void;
  apiClient: ApiClient;
  onError: (e: string) => void;
}) {
  const [documents, setDocuments] = useState<AdminDocumentListItem[]>([]);
  const [userId, setUserId] = useState("");
  const [category, setCategory] = useState("admin");
  const [files, setFiles] = useState<FileList | null>(null);
  const [folderEdit, setFolderEdit] = useState(workspace.data_folder ?? "");
  const [savingFolder, setSavingFolder] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [indexing, setIndexing] = useState(false);
  const [warnings, setWarnings] = useState<{ file_name: string; error: string }[]>([]);
  const uploadInputRef = useRef<HTMLInputElement | null>(null);
  const [processingJobs, setProcessingJobs] = useState<AdminProcessingJob[]>([]);
  const [loadingJobs, setLoadingJobs] = useState(false);
  const [retryingJobId, setRetryingJobId] = useState<string | null>(null);
  const [deletingDocumentId, setDeletingDocumentId] = useState<string | null>(null);

  useEffect(() => {
    void loadDocuments();
    void loadProcessingJobs();
    setFolderEdit(workspace.data_folder ?? "");
  }, [workspace.id]);

  async function loadDocuments() {
    try {
      setDocuments(await apiClient.adminListWorkspaceDocuments(workspace.id));
    } catch (e) {
      onError(String(e));
    }
  }
  async function loadProcessingJobs() {
    setLoadingJobs(true);
    try {
      setProcessingJobs(await apiClient.adminListProcessingJobs(workspace.id));
    } catch (e) {
      onError(String(e));
    } finally {
      setLoadingJobs(false);
    }
  }
  async function handleSaveFolder(e: React.FormEvent) {
    e.preventDefault();
    if (!folderEdit.trim()) return;
    setSavingFolder(true);
    try {
      onWorkspaceUpdated(await apiClient.adminSetDataFolder(workspace.id, folderEdit.trim()));
    } catch (e) {
      onError(String(e));
    } finally {
      setSavingFolder(false);
    }
  }
  async function handleUpload() {
    if (!files?.length || !userId) return;
    setUploading(true);
    setWarnings([]);
    try {
      const res = await apiClient.adminUploadDocuments(workspace.id, { userId, category, files });
      setWarnings(res.failed);
      setFiles(null);
      if (uploadInputRef.current) uploadInputRef.current.value = "";
      await loadDocuments();
      await loadProcessingJobs();
    } catch (e) {
      onError(String(e));
    } finally {
      setUploading(false);
    }
  }
  async function handleIndexFolder() {
    if (!userId) return;
    setIndexing(true);
    setWarnings([]);
    try {
      const res = await apiClient.adminIndexFolder(workspace.id, { user_id: userId, folder: null as unknown as string, category });
      setWarnings(res.failed);
      await loadDocuments();
      await loadProcessingJobs();
    } catch (e) {
      onError(String(e));
    } finally {
      setIndexing(false);
    }
  }
  async function handleDeleteDocument(documentId: string) {
    if (!window.confirm("Na pewno usunąć dokument?")) return;
    setDeletingDocumentId(documentId);
    try {
      await apiClient.adminDeleteDocument(workspace.id, documentId);
      await loadDocuments();
      await loadProcessingJobs();
    } catch (e) {
      onError(String(e));
    } finally {
      setDeletingDocumentId(null);
    }
  }

  return (
    <div className="admin-members-block">
      <h3>Zarządzanie dokumentami workspace</h3>
      <form className="admin-form admin-form-inline" onSubmit={(e) => void handleSaveFolder(e)}>
        <label>Folder danych<input value={folderEdit} onChange={(e) => setFolderEdit(e.target.value)} placeholder="np. firma_ABC" /></label>
        <button type="submit" disabled={savingFolder || !folderEdit.trim()}>{savingFolder ? "Zapisywanie..." : "Zapisz folder"}</button>
      </form>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 8 }}>
        <select value={userId} onChange={(e) => setUserId(e.target.value)}>
          <option value="">Wybierz użytkownika...</option>
          {users.map((u) => <option key={u.id} value={u.id}>{u.email}</option>)}
        </select>
        <input value={category} onChange={(e) => setCategory(e.target.value)} placeholder="Kategoria" />
        <button className="admin-btn-small" type="button" onClick={() => void handleIndexFolder()} disabled={indexing || !userId || !workspace.data_folder}>
          {indexing ? "Indeksowanie..." : "Indeksuj folder"}
        </button>
        <input ref={uploadInputRef} type="file" accept=".md" multiple onChange={(e) => setFiles(e.target.files)} />
        <button className="admin-btn-small" type="button" onClick={() => void handleUpload()} disabled={uploading || !userId || !files?.length}>
          {uploading ? "Przesyłanie..." : "Prześlij .md"}
        </button>
      </div>
      {warnings.length > 0 && <div className="error-banner">{warnings.map((w) => <div key={w.file_name}>{w.file_name}: {w.error}</div>)}</div>}
      <h4>Lista dokumentów ({documents.length})</h4>
      {documents.length === 0 ? <p className="muted">Brak dokumentów.</p> : (
        <table className="admin-table">
          <thead><tr><th>Tytuł</th><th>Status</th><th>Wersje</th><th>Akcje</th></tr></thead>
          <tbody>
            {documents.map((d) => (
              <tr key={d.id}>
                <td>{d.title}</td>
                <td>{d.latest_processing_status ?? "-"}</td>
                <td>{d.version_count}</td>
                <td>
                  <button className="admin-btn-small" type="button" onClick={() => void handleDeleteDocument(d.id)} disabled={deletingDocumentId === d.id}>
                    {deletingDocumentId === d.id ? "Usuwanie..." : "Usuń"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <div style={{ marginTop: 8 }}>
        <h4>Błędy indeksacji</h4>
        <button className="admin-btn-small" type="button" onClick={() => void loadProcessingJobs()}>{loadingJobs ? "Odświeżanie..." : "Odśwież"}</button>
        {processingJobs.filter((j) => j.status === "failed").length === 0 ? <p className="muted">Brak błędów.</p> : (
          <table className="admin-table">
            <thead><tr><th>Dokument</th><th>Etap</th><th>Błąd</th><th>Akcja</th></tr></thead>
            <tbody>
              {processingJobs.filter((j) => j.status === "failed").slice(0, 20).map((job) => (
                <tr key={job.id}>
                  <td>{job.document_title}</td>
                  <td>{job.job_type}</td>
                  <td>{job.error_message ?? "-"}</td>
                  <td>
                    <button
                      className="admin-btn-small"
                      type="button"
                      onClick={async () => {
                        setRetryingJobId(job.id);
                        try {
                          await apiClient.adminRetryProcessingJob(workspace.id, job.id);
                          await loadProcessingJobs();
                          await loadDocuments();
                        } catch (e) {
                          onError(String(e));
                        } finally {
                          setRetryingJobId(null);
                        }
                      }}
                      disabled={retryingJobId === job.id}
                    >
                      {retryingJobId === job.id ? "Ponawianie..." : "Ponów"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
