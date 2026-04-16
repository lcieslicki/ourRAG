import React from "react";
import { createRoot } from "react-dom/client";

import { config } from "./config";

createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <main>
      <h1>ourRAG</h1>
      <p>Environment: {config.app.env}</p>
    </main>
  </React.StrictMode>,
);
