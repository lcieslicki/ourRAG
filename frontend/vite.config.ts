import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

function required(env: Record<string, string>, name: string): string {
  const value = env[name];

  if (!value) {
    throw new Error(`Missing required environment variable: ${name}`);
  }

  return value;
}

function parsePort(value: string): number {
  const port = Number(value);

  if (!Number.isInteger(port) || port < 1 || port > 65535) {
    throw new Error("FRONTEND_PORT must be an integer between 1 and 65535");
  }

  return port;
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, "..", "");

  required(env, "VITE_API_BASE_URL");
  required(env, "VITE_APP_ENV");

  return {
    envDir: "..",
    plugins: [react()],
    test: {
      environment: "jsdom",
      setupFiles: ["./tests/setup.ts"],
    },
    server: {
      host: required(env, "FRONTEND_HOST"),
      port: parsePort(required(env, "FRONTEND_PORT")),
      strictPort: true,
    },
  };
});
