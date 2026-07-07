/// <reference types="vite/client" />

interface ImportMetaEnv {
  // Базовый URL backend API. Пусто/относительный путь — для схемы «один домен».
  readonly VITE_BACKEND_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
