type AppEnvironment = "local" | "docker" | "test" | "production";

export type FrontendConfig = {
  app: {
    env: AppEnvironment;
    debug: boolean;
  };
  api: {
    baseUrl: string;
  };
};

function required(name: string): string {
  const value = import.meta.env[name];

  if (typeof value !== "string" || value.trim() === "") {
    throw new Error(`Missing required environment variable: ${name}`);
  }

  return value;
}

function parseBoolean(name: string): boolean {
  const value = required(name);

  if (value === "true") {
    return true;
  }

  if (value === "false") {
    return false;
  }

  throw new Error(`${name} must be "true" or "false"`);
}

function parseAppEnv(value: string): AppEnvironment {
  if (["local", "docker", "test", "production"].includes(value)) {
    return value as AppEnvironment;
  }

  throw new Error("VITE_APP_ENV must be one of local, docker, test, production");
}

function parseUrl(name: string): string {
  const value = required(name);

  try {
    return new URL(value).toString().replace(/\/$/, "");
  } catch {
    throw new Error(`${name} must be a valid absolute URL`);
  }
}

export const config: FrontendConfig = {
  app: {
    env: parseAppEnv(required("VITE_APP_ENV")),
    debug: parseBoolean("VITE_APP_DEBUG"),
  },
  api: {
    baseUrl: parseUrl("VITE_API_BASE_URL"),
  },
};
