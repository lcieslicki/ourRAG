import type { ReactNode } from "react";

type AppLayoutProps = {
  sidebar: ReactNode;
  children: ReactNode;
};

export function AppLayout({ sidebar, children }: AppLayoutProps) {
  return (
    <div className="app-shell">
      <aside className="app-sidebar">
        <div>
          <p className="eyebrow">ourRAG</p>
          <h1>Workspace chat</h1>
        </div>
        {sidebar}
      </aside>
      <main className="app-main">{children}</main>
    </div>
  );
}
