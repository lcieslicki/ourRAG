import type { Session } from "../features/auth/LoginScreen";
import { LogOut } from "lucide-react";
import { pl } from "../i18n/pl";

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
        <span className="session-label">{pl.workspaceSwitcher.workspaceLabel}</span>
        <span className="session-value">{session.workspaceName}</span>
      </div>
      <button type="button" className="session-change-btn" onClick={onLogout}>
        <LogOut size={16} />
        Zmień sesję
      </button>
    </section>
  );
}
