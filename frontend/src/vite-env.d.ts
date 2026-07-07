/// <reference types="vite/client" />

interface ImportMetaEnv {
  // Base URL of the backend API. Empty/relative path — for the single-domain setup.
  readonly VITE_BACKEND_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
