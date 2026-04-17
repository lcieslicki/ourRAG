import type { Session } from "../features/auth/LoginScreen";

type Props = {
  session: Session;
  onLogout: () => void;
};

export function WorkspaceSwitcher({ session, onLogout }: Props) {
  return (
    <section className="session-info" aria-label="Aktywna sesja">
      <div className="session-row">
        <span className="session-label">Użytkownik</span>
        <span className="session-value">{session.userEmail}</span>
      </div>
      <div className="session-row">
        <span className="session-label">Workspace</span>
        <span className="session-value">{session.workspaceName}</span>
      </div>
      <button type="button" className="session-change-btn" onClick={onLogout}>
        Zmień sesję
      </button>
    </section>
  );
}
