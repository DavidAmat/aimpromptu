/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Base URL for aitu-backend FastAPI (no trailing slash). Unset: `/api`, through the Vite proxy. */
  readonly VITE_AITU_API_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
