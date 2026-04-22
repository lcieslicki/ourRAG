import { useEffect, useReducer, useRef, useState } from "react";
import { Eye, FileText, FolderSearch, Plus, RotateCcw, Trash2, Upload, UserPlus, Users } from "lucide-react";
import type {
  AdminDocumentListItem,
  AdminProcessingJob,
  AdminUserResponse,
  AdminWorkspaceMemberResponse,
  AdminWorkspaceResponse,
} from "../../lib/api/types";
import type { ApiClient } from "../../lib/api/client";

type Tab = "users" | "workspaces";

type State = {
  tab: Tab;
  users: AdminUserResponse[];
  workspaces: AdminWorkspaceResponse[];
  selectedWorkspaceId: string | null;
  members: AdminWorkspaceMemberResponse[];
  loading: boolean;
  error: string | null;
};

type Action =
  | { type: "SET_TAB"; tab: Tab }
  | { type: "SET_USERS"; users: AdminUserResponse[] }
  | { type: "ADD_USER"; user: AdminUserResponse }
  | { type: "SET_WORKSPACES"; workspaces: AdminWorkspaceResponse[] }
  | { type: "ADD_WORKSPACE"; workspace: AdminWorkspaceResponse }
  | { type: "UPDATE_WORKSPACE"; workspace: AdminWorkspaceResponse }
  | { type: "SELECT_WORKSPACE"; id: string }
  | { type: "SET_MEMBERS"; members: AdminWorkspaceMemberResponse[] }
  | { type: "ADD_MEMBER"; member: AdminWorkspaceMemberResponse }
  | { type: "SET_LOADING"; loading: boolean }
  | { type: "SET_ERROR"; error: string | null };

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "SET_TAB": return { ...state, tab: action.tab, error: null };
    case "SET_USERS": return { ...state, users: action.users, loading: false };
    case "ADD_USER": return { ...state, users: [action.user, ...state.users] };
    case "SET_WORKSPACES": return { ...state, workspaces: action.workspaces, loading: false };
    case "ADD_WORKSPACE": return { ...state, workspaces: [action.workspace, ...state.workspaces] };
    case "UPDATE_WORKSPACE": return { ...state, workspaces: state.workspaces.map((w) => w.id === action.workspace.id ? action.workspace : w) };
    case "SELECT_WORKSPACE": return { ...state, selectedWorkspaceId: action.id, members: [] };
    case "SET_MEMBERS": return { ...state, members: action.members, loading: false };
    case "ADD_MEMBER": return { ...state, members: [...state.members, action.member] };
    case "SET_LOADING": return { ...state, loading: action.loading };
    case "SET_ERROR": return { ...state, error: action.error, loading: false };
    default: return state;
  }
}

const initialState: State = {
  tab: "users",
  users: [],
  workspaces: [],
  selectedWorkspaceId: null,
  members: [],
  loading: false,
  error: null,
};

type Props = { apiClient: ApiClient };

export function AdminPanel({ apiClient }: Props) {
  const [state, dispatch] = useReducer(reducer, initialState);

  useEffect(() => {
    void loadUsers();
    void loadWorkspaces();
  }, []);

  useEffect(() => {
    if (state.selectedWorkspaceId) void loadMembers(state.selectedWorkspaceId);
  }, [state.selectedWorkspaceId]);

  async function loadUsers() {
    dispatch({ type: "SET_LOADING", loading: true });
    try {
      const users = await apiClient.adminListUsers();
      dispatch({ type: "SET_USERS", users });
    } catch (e) {
      dispatch({ type: "SET_ERROR", error: String(e) });
    }
  }

  async function loadWorkspaces() {
    try {
      const workspaces = await apiClient.adminListWorkspaces();
      dispatch({ type: "SET_WORKSPACES", workspaces });
    } catch (e) {
      dispatch({ type: "SET_ERROR", error: String(e) });
    }
  }

  async function loadMembers(workspaceId: string) {
    dispatch({ type: "SET_LOADING", loading: true });
    try {
      const members = await apiClient.adminListMembers(workspaceId);
      dispatch({ type: "SET_MEMBERS", members });
    } catch (e) {
      dispatch({ type: "SET_ERROR", error: String(e) });
    }
  }

  return (
    <div className="admin-panel">
      <div className="admin-header">
        <h2>Panel Admina</h2>
        <p className="muted">Zarządzaj użytkownikami i przestrzeniami roboczymi do testowania aplikacji.</p>
      </div>

      {state.error && (
        <div className="error-banner" style={{ margin: "0 24px 0" }}>
          {state.error}
          <button className="admin-dismiss" onClick={() => dispatch({ type: "SET_ERROR", error: null })}>✕</button>
        </div>
      )}

      <div className="admin-tabs">
        <button className={`admin-tab${state.tab === "users" ? " active" : ""}`} onClick={() => dispatch({ type: "SET_TAB", tab: "users" })}>
          <Users size={14} />
          Użytkownicy ({state.users.length})
        </button>
        <button className={`admin-tab${state.tab === "workspaces" ? " active" : ""}`} onClick={() => dispatch({ type: "SET_TAB", tab: "workspaces" })}>
          <FileText size={14} />
          Przestrzenie robocze ({state.workspaces.length})
        </button>
      </div>

      <div className="admin-content">
        {state.tab === "users" && (
          <UsersTab users={state.users} onCreated={(u) => dispatch({ type: "ADD_USER", user: u })} apiClient={apiClient} onError={(e) => dispatch({ type: "SET_ERROR", error: e })} />
        )}
        {state.tab === "workspaces" && (
          <WorkspacesTab
            workspaces={state.workspaces}
            users={state.users}
            selectedWorkspaceId={state.selectedWorkspaceId}
            members={state.members}
            onCreated={(w) => dispatch({ type: "ADD_WORKSPACE", workspace: w })}
            onSelect={(id) => dispatch({ type: "SELECT_WORKSPACE", id })}
            onMemberAdded={(m) => dispatch({ type: "ADD_MEMBER", member: m })}
            onWorkspaceUpdated={(w) => dispatch({ type: "UPDATE_WORKSPACE", workspace: w })}
            apiClient={apiClient}
            onError={(e) => dispatch({ type: "SET_ERROR", error: e })}
          />
        )}
      </div>
    </div>
  );
}

// ── Users Tab ────────────────────────────────────────────────────────────────

function UsersTab({ users, onCreated, apiClient, onError }: {
  users: AdminUserResponse[];
  onCreated: (u: AdminUserResponse) => void;
  apiClient: ApiClient;
  onError: (e: string) => void;
}) {
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [saving, setSaving] = useState(false);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!email.trim() || !displayName.trim()) return;
    setSaving(true);
    try {
      const user = await apiClient.adminCreateUser({ email: email.trim(), display_name: displayName.trim() });
      onCreated(user);
      setEmail("");
      setDisplayName("");
    } catch (err) {
      onError(String(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="admin-section">
      <div className="admin-form-block">
        <h3>Nowy użytkownik</h3>
        <form className="admin-form" onSubmit={(e) => void handleCreate(e)}>
          <label>
            Email
            <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="jan@firma.pl" type="email" required />
          </label>
          <label>
            Nazwa wyświetlana
            <input value={displayName} onChange={(e) => setDisplayName(e.target.value)} placeholder="Jan Kowalski" required />
          </label>
          <button type="submit" disabled={saving || !email.trim() || !displayName.trim()}>
            <Plus size={14} />
            {saving ? "Tworzenie…" : "Utwórz użytkownika"}
          </button>
        </form>
      </div>

      <div className="admin-list-block">
        <h3>Użytkownicy ({users.length})</h3>
        {users.length === 0 ? (
          <p className="muted">Brak użytkowników.</p>
        ) : (
          <table className="admin-table">
            <thead>
              <tr><th>ID</th><th>Email</th><th>Nazwa</th><th>Status</th></tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td><code>{u.id}</code></td>
                  <td>{u.email}</td>
                  <td>{u.display_name}</td>
                  <td>{u.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

// ── Workspaces Tab ───────────────────────────────────────────────────────────

function WorkspacesTab({ workspaces, users, selectedWorkspaceId, members, onCreated, onSelect, onMemberAdded, onWorkspaceUpdated, apiClient, onError }: {
  workspaces: AdminWorkspaceResponse[];
  users: AdminUserResponse[];
  selectedWorkspaceId: string | null;
  members: AdminWorkspaceMemberResponse[];
  onCreated: (w: AdminWorkspaceResponse) => void;
  onSelect: (id: string) => void;
  onMemberAdded: (m: AdminWorkspaceMemberResponse) => void;
  onWorkspaceUpdated: (w: AdminWorkspaceResponse) => void;
  apiClient: ApiClient;
  onError: (e: string) => void;
}) {
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [saving, setSaving] = useState(false);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim() || !slug.trim()) return;
    setSaving(true);
    try {
      const workspace = await apiClient.adminCreateWorkspace({ name: name.trim(), slug: slug.trim() });
      onCreated(workspace);
      setName("");
      setSlug("");
    } catch (err) {
      onError(String(err));
    } finally {
      setSaving(false);
    }
  }

  const selectedWorkspace = workspaces.find((w) => w.id === selectedWorkspaceId) ?? null;

  return (
    <div className="admin-section">
      <div className="admin-form-block">
        <h3>Nowa przestrzeń robocza</h3>
        <form className="admin-form" onSubmit={(e) => void handleCreate(e)}>
          <label>
            Nazwa
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Firma ABC" required />
          </label>
          <label>
            Slug (ID)
            <input value={slug} onChange={(e) => setSlug(e.target.value)} placeholder="firma_abc" required />
          </label>
          <button type="submit" disabled={saving || !name.trim() || !slug.trim()}>
            <Plus size={14} />
            {saving ? "Tworzenie…" : "Utwórz przestrzeń roboczą"}
          </button>
        </form>
      </div>

      <div className="admin-list-block">
        <h3>Przestrzenie robocze ({workspaces.length})</h3>
        {workspaces.length === 0 ? (
          <p className="muted">Brak przestrzeni roboczych.</p>
        ) : (
          <table className="admin-table">
            <thead>
              <tr><th>ID / Slug</th><th>Nazwa</th><th>Folder danych</th><th>Status</th><th></th></tr>
            </thead>
            <tbody>
              {workspaces.map((w) => (
                <tr key={w.id} className={w.id === selectedWorkspaceId ? "admin-row-selected" : ""}>
                  <td><code>{w.slug}</code><br /><small className="muted">{w.id}</small></td>
                  <td>{w.name}</td>
                  <td>{w.data_folder ? <code>{w.data_folder}</code> : <span className="muted">—</span>}</td>
                  <td>{w.status}</td>
                  <td>
                    <button className="admin-btn-small" onClick={() => onSelect(w.id)}>
                      <Eye size={14} />
                      Zarządzaj
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {selectedWorkspace && (
        <>
          <MembersBlock
            workspace={selectedWorkspace}
            members={members}
            users={users}
            onMemberAdded={onMemberAdded}
            apiClient={apiClient}
            onError={onError}
          />
          <DocumentsBlock
            workspace={selectedWorkspace}
            users={users}
            onWorkspaceUpdated={onWorkspaceUpdated}
            apiClient={apiClient}
            onError={onError}
          />
        </>
      )}
    </div>
  );
}

// ── Members Block ────────────────────────────────────────────────────────────

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
      <h3>Członkowie: {workspace.name}</h3>

      {members.length === 0 ? (
        <p className="muted">Brak członków.</p>
      ) : (
        <table className="admin-table">
          <thead>
            <tr><th>Email</th><th>Nazwa</th><th>Rola</th></tr>
          </thead>
          <tbody>
            {members.map((m) => (
              <tr key={m.user_id}>
                <td>{m.email}</td>
                <td>{m.display_name}</td>
                <td><span className="admin-role-badge">{m.role}</span></td>
              </tr>
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
              {availableUsers.map((u) => (
                <option key={u.id} value={u.id}>{u.email} — {u.display_name}</option>
              ))}
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
          <button type="submit" disabled={saving || !userId}>
            <UserPlus size={14} />
            {saving ? "Dodawanie…" : "Dodaj członka"}
          </button>
        </form>
      )}
    </div>
  );
}

// ── Documents Block ──────────────────────────────────────────────────────────

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
  const [bulkDeleting, setBulkDeleting] = useState(false);
  const [bulkReindexing, setBulkReindexing] = useState(false);

  useEffect(() => {
    void loadDocuments();
    void loadProcessingJobs();
    setFolderEdit(workspace.data_folder ?? "");
  }, [workspace.id]);

  async function loadDocuments() {
    try {
      const docs = await apiClient.adminListWorkspaceDocuments(workspace.id);
      setDocuments(docs);
    } catch (e) {
      onError(String(e));
    }
  }

  async function loadProcessingJobs() {
    setLoadingJobs(true);
    try {
      const jobs = await apiClient.adminListProcessingJobs(workspace.id);
      setProcessingJobs(jobs);
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
      const updated = await apiClient.adminSetDataFolder(workspace.id, folderEdit.trim());
      onWorkspaceUpdated(updated);
    } catch (err) {
      onError(String(err));
    } finally {
      setSavingFolder(false);
    }
  }

  async function handleUpload() {
    if (!files?.length || !userId) return;
    setUploading(true);
    setWarnings([]);
    try {
      const res = await apiClient.adminUploadDocuments(workspace.id, { files });
      setWarnings(res.failed);
      setFiles(null);
      if (uploadInputRef.current) {
        uploadInputRef.current.value = "";
      }
      await loadDocuments();
      await loadProcessingJobs();
    } catch (err) {
      onError(String(err));
    } finally {
      setUploading(false);
    }
  }

  async function handleIndexFolder() {
    if (!userId) return;
    setIndexing(true);
    setWarnings([]);
    try {
      const res = await apiClient.adminIndexFolder(workspace.id);
      setWarnings(res.failed);
      await loadDocuments();
      await loadProcessingJobs();
    } catch (err) {
      onError(String(err));
    } finally {
      setIndexing(false);
    }
  }

  async function handleDeleteDocument(documentId: string) {
    const confirmed = window.confirm("Na pewno usunąć dokument? Ta operacja usunie też wersje i wektory.");
    if (!confirmed) {
      return;
    }

    setDeletingDocumentId(documentId);
    try {
      await apiClient.adminDeleteDocument(workspace.id, documentId);
      await loadDocuments();
      await loadProcessingJobs();
    } catch (err) {
      onError(String(err));
    } finally {
      setDeletingDocumentId(null);
    }
  }

  async function handleDeleteAllDocuments() {
    const confirmed = window.confirm("Na pewno usunąć wszystkie dokumenty z tej przestrzeni roboczej? Operacja jest nieodwracalna.");
    if (!confirmed) {
      return;
    }

    setBulkDeleting(true);
    try {
      await apiClient.adminDeleteAllDocuments(workspace.id);
      await loadDocuments();
      await loadProcessingJobs();
    } catch (err) {
      onError(String(err));
    } finally {
      setBulkDeleting(false);
    }
  }

  async function handleReindexAllDocuments() {
    setBulkReindexing(true);
    try {
      await apiClient.adminReindexAllDocuments(workspace.id);
      await loadDocuments();
      await loadProcessingJobs();
    } catch (err) {
      onError(String(err));
    } finally {
      setBulkReindexing(false);
    }
  }

  function latestFailedJobForDocument(documentId: string): AdminProcessingJob | null {
    return (
      processingJobs.find(
        (job) => job.document_id === documentId && job.status === "failed",
      ) ?? null
    );
  }

  async function handleRetryForDocument(document: AdminDocumentListItem) {
    const failedJob = latestFailedJobForDocument(document.id);
    try {
      if (failedJob) {
        setRetryingJobId(failedJob.id);
        await apiClient.adminRetryProcessingJob(workspace.id, failedJob.id);
      } else if (document.latest_version_id) {
        setRetryingJobId(document.id);
        await apiClient.reindexDocumentVersion(document.id, document.latest_version_id);
      } else {
        onError("Dokument nie ma wersji do ponownej indeksacji.");
        return;
      }

      await loadProcessingJobs();
      await loadDocuments();
    } catch (err) {
      onError(String(err));
    } finally {
      setRetryingJobId(null);
    }
  }

  async function handleRetryJob(job: AdminProcessingJob) {
    setRetryingJobId(job.id);
    try {
      await apiClient.adminRetryProcessingJob(workspace.id, job.id);
      await loadProcessingJobs();
      await loadDocuments();
    } catch (err) {
      onError(String(err));
    } finally {
      setRetryingJobId(null);
    }
  }

  function indexingBadge(document: AdminDocumentListItem): { label: string; color: string } {
    const status = document.latest_processing_status;
    if (status === "ready" && document.indexed_at) {
      return { label: "OK", color: "#1f7a1f" };
    }
    if (status === "failed") {
      return { label: "Błąd", color: "#b42318" };
    }
    if (status === "pending" || status === "processing") {
      return { label: "W trakcie", color: "#9a6700" };
    }
    return { label: "Nieznany", color: "#475467" };
  }

  return (
    <div className="admin-members-block">
      <h3>Dokumenty: {workspace.name}</h3>

      {/* ── Folder konfiguracja ── */}
      <div className="admin-form-block" style={{ marginBottom: 12 }}>
        <h4 style={{ margin: "0 0 8px" }}>Folder danych</h4>
        <form className="admin-form admin-form-inline" onSubmit={(e) => void handleSaveFolder(e)}>
          <label style={{ flex: "1 1 200px" }}>
            Podfolder w <code>data/</code>
            <input
              value={folderEdit}
              onChange={(e) => setFolderEdit(e.target.value)}
              placeholder="np. firma_ABC"
            />
          </label>
          <button type="submit" disabled={savingFolder || !folderEdit.trim()} style={{ alignSelf: "flex-end" }}>
            {savingFolder ? "Zapisywanie…" : "Zapisz folder"}
          </button>
        </form>
        {workspace.data_folder ? (
          <p className="muted" style={{ fontSize: "0.82em", marginTop: 4 }}>
            Aktywny folder: <code>{workspace.data_folder}</code>
          </p>
        ) : (
          <p className="muted" style={{ fontSize: "0.82em", marginTop: 4 }}>Brak skonfigurowanego folderu.</p>
        )}
      </div>

      {/* ── Indeksowanie i upload ── */}
      <div className="admin-form-block" style={{ marginBottom: 0 }}>
        <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
          <label style={{ flex: "1 1 180px" }}>
            Użytkownik (właściciel pliku)
            <select value={userId} onChange={(e) => setUserId(e.target.value)}>
              <option value="">Wybierz…</option>
              {users.map((u) => (
                <option key={u.id} value={u.id}>{u.email}</option>
              ))}
            </select>
          </label>
          <label style={{ flex: "1 1 120px" }}>
            Kategoria
            <input value={category} onChange={(e) => setCategory(e.target.value)} placeholder="admin" />
          </label>
        </div>
        <p className="muted" style={{ fontSize: "0.82em", margin: "4px 0 8px" }}>Użytkownik musi być właścicielem lub administratorem przestrzeni roboczej.</p>

        <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginTop: 8 }}>
          <button
            className="admin-btn-small"
            type="button"
            onClick={() => void handleIndexFolder()}
            disabled={indexing || !userId || !workspace.data_folder}
            title={!workspace.data_folder ? "Najpierw skonfiguruj folder danych" : undefined}
          >
            <FolderSearch size={14} />
            {indexing ? "Indeksowanie…" : `Indeksuj folder${workspace.data_folder ? ` (${workspace.data_folder})` : ""}`}
          </button>

          <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <input
              ref={uploadInputRef}
              type="file"
              accept=".md"
              multiple
              style={{ fontSize: "0.85em" }}
              onChange={(e) => setFiles(e.target.files)}
            />
          </label>
          <button
            className="admin-btn-small"
            type="button"
            onClick={() => void handleUpload()}
            disabled={uploading || !userId || !files?.length}
          >
            <Upload size={14} />
            {uploading ? "Przesyłanie…" : "Prześlij pliki .md"}
          </button>
        </div>

        {warnings.length > 0 && (
          <div className="error-banner" style={{ marginTop: 8 }}>
            {warnings.map((w) => (
              <div key={w.file_name}><strong>{w.file_name}</strong>: {w.error}</div>
            ))}
          </div>
        )}
      </div>

      {/* ── Lista dokumentów ── */}
      <div style={{ marginTop: 16 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
          <h4 style={{ margin: 0 }}>Dokumenty ({documents.length})</h4>
          <button className="admin-btn-small" onClick={() => void loadDocuments()}>Odśwież</button>
          <button
            className="admin-btn-small"
            onClick={() => void handleReindexAllDocuments()}
            disabled={bulkReindexing || documents.length === 0}
          >
            <RotateCcw size={14} />
            {bulkReindexing ? "Zlecanie…" : "Zleć indeksację wszystkich"}
          </button>
          <button
            className="admin-btn-small"
            onClick={() => void handleDeleteAllDocuments()}
            disabled={bulkDeleting || documents.length === 0}
          >
            <Trash2 size={14} />
            {bulkDeleting ? "Usuwanie…" : "Usuń wszystkie"}
          </button>
        </div>
        {documents.length === 0 ? (
          <p className="muted">Brak dokumentów.</p>
        ) : (
          <table className="admin-table">
            <thead>
              <tr><th>Tytuł</th><th>Status indeksacji</th><th>Dane zasilające model</th><th>Wersje</th><th>Akcje</th></tr>
            </thead>
            <tbody>
              {documents.map((d) => {
                const badge = indexingBadge(d);
                return (
                <tr key={d.id}>
                  <td>
                    <div>{d.title}</div>
                    <div className="muted" style={{ marginTop: 4, fontSize: "0.82em" }}>
                      Kategoria: <code>{d.category || "—"}</code>
                    </div>
                  </td>
                  <td>
                    <span
                      style={{
                        display: "inline-block",
                        border: `1px solid ${badge.color}`,
                        color: badge.color,
                        borderRadius: 999,
                        padding: "2px 10px",
                        fontWeight: 600,
                        fontSize: "0.82em",
                      }}
                    >
                      {badge.label}
                    </span>
                    <div className="muted" style={{ marginTop: 4, fontSize: "0.82em" }}>
                      pipeline: <code>{d.latest_processing_status ?? "—"}</code>
                    </div>
                    {d.latest_error_message && (
                      <div className="muted" style={{ marginTop: 4, maxWidth: 420, whiteSpace: "pre-wrap" }}>
                        <strong>{d.latest_error_job_type ?? "error"}:</strong> {d.latest_error_message}
                      </div>
                    )}
                  </td>
                  <td>
                    <div className="muted" style={{ fontSize: "0.82em" }}>
                      chunks: <code>{d.chunk_count ?? 0}</code>, vectors(Qdrant): <code>{d.qdrant_vector_count ?? "?"}</code>
                    </div>
                    <div className="muted" style={{ marginTop: 4, fontSize: "0.82em" }}>
                      embedding: <code>{d.embedding_model_name ?? "—"}</code>{d.embedding_model_version ? ` (${d.embedding_model_version})` : ""}
                    </div>
                    <div className="muted" style={{ marginTop: 4, fontSize: "0.82em" }}>
                      język: <code>{d.language ?? "—"}</code>, indeksacja: <code>{d.indexed_at ? new Date(d.indexed_at).toLocaleString() : "—"}</code>
                    </div>
                    <div className="muted" style={{ marginTop: 4, fontSize: "0.82em" }}>
                      aktywna: <code>{String(d.is_active ?? false)}</code>, invalidated: <code>{String(d.is_invalidated ?? false)}</code>
                    </div>
                    <div className="muted" style={{ marginTop: 4, fontSize: "0.82em" }}>
                      tagi: {d.tags.length > 0 ? d.tags.map((tag) => <code key={`${d.id}-${tag}`} style={{ marginRight: 6 }}>{tag}</code>) : <code>—</code>}
                    </div>
                  </td>
                  <td>{d.version_count}</td>
                  <td style={{ display: "flex", gap: 8 }}>
                    <button
                      className="admin-btn-small"
                      onClick={() => void handleRetryForDocument(d)}
                      disabled={retryingJobId === d.id || retryingJobId === latestFailedJobForDocument(d.id)?.id}
                    >
                      <RotateCcw size={14} />
                      {latestFailedJobForDocument(d.id) ? "Ponów failed job" : "Ponów indeksację"}
                    </button>
                    <button
                      className="admin-btn-small"
                      onClick={() => void handleDeleteDocument(d.id)}
                      disabled={deletingDocumentId === d.id}
                    >
                      <Trash2 size={14} />
                      {deletingDocumentId === d.id ? "Usuwanie…" : "Usuń"}
                    </button>
                  </td>
                </tr>
              )})}
            </tbody>
          </table>
        )}
      </div>

      <div style={{ marginTop: 16 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
          <h4 style={{ margin: 0 }}>Błędy indeksacji</h4>
          <button className="admin-btn-small" onClick={() => void loadProcessingJobs()}>
            {loadingJobs ? "Odświeżanie…" : "Odśwież"}
          </button>
        </div>
        {processingJobs.filter((job) => job.status === "failed").length === 0 ? (
          <p className="muted">Brak błędów indeksacji.</p>
        ) : (
          <table className="admin-table">
            <thead>
              <tr><th>Dokument</th><th>Etap</th><th>Błąd</th><th>Próby</th><th>Akcja</th></tr>
            </thead>
            <tbody>
              {processingJobs
                .filter((job) => job.status === "failed")
                .slice(0, 20)
                .map((job) => (
                  <tr key={job.id}>
                    <td>{job.document_title}</td>
                    <td><code>{job.job_type}</code></td>
                    <td style={{ maxWidth: 420, whiteSpace: "pre-wrap" }}>{job.error_message ?? "—"}</td>
                    <td>{job.attempts}</td>
                    <td>
                      <button
                        className="admin-btn-small"
                        onClick={() => void handleRetryJob(job)}
                        disabled={retryingJobId === job.id}
                      >
                        <RotateCcw size={14} />
                        {retryingJobId === job.id ? "Ponawianie…" : "Ponów"}
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
