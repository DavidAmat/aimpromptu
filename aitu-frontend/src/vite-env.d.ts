/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Base URL for aitu-backend FastAPI (no trailing slash), e.g. http://127.0.0.1:8765 */
  readonly VITE_AITU_API_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
