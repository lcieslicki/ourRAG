type WorkspaceSwitcherProps = {
  userId: string;
  workspaceId: string;
  onUserIdChange: (value: string) => void;
  onWorkspaceIdChange: (value: string) => void;
  onWorkspaceCommitted: () => void;
};

export function WorkspaceSwitcher({
  userId,
  workspaceId,
  onUserIdChange,
  onWorkspaceIdChange,
  onWorkspaceCommitted,
}: WorkspaceSwitcherProps) {
  return (
    <section className="workspace-switcher" aria-label="Workspace selection">
      <label>
        User ID
        <input
          value={userId}
          onChange={(event) => onUserIdChange(event.target.value)}
          placeholder="Backend X-User-Id"
        />
      </label>
      <label>
        Workspace ID
        <input
          value={workspaceId}
          onChange={(event) => onWorkspaceIdChange(event.target.value)}
          placeholder="Workspace UUID"
        />
      </label>
      <button type="button" onClick={onWorkspaceCommitted} disabled={!userId.trim() || !workspaceId.trim()}>
        Load workspace
      </button>
      <p>
        The active workspace is explicit and sent with chat requests. Access checks still happen on the backend.
      </p>
    </section>
  );
}
