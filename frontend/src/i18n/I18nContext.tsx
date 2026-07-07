// Lightweight i18n: a context providing the current language, a setter, and a
// t() function with {placeholder} interpolation. The choice is persisted in
// localStorage; the default is Russian.

import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react'
import { translations, type Lang, type TKey } from './translations'

const STORAGE_KEY = 'kazakh-tts-lang'
const DEFAULT_LANG: Lang = 'ru'

interface I18nValue {
  lang: Lang
  setLang: (lang: Lang) => void
  t: (key: TKey, params?: Record<string, string | number>) => string
}

const I18nContext = createContext<I18nValue | null>(null)

function getInitialLang(): Lang {
  const saved = localStorage.getItem(STORAGE_KEY)
  if (saved === 'ru' || saved === 'kk' || saved === 'en') return saved
  return DEFAULT_LANG
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLang] = useState<Lang>(getInitialLang)

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, lang)
    document.documentElement.lang = lang
  }, [lang])

  const t: I18nValue['t'] = (key, params) => {
    let s: string = translations[lang][key] ?? translations.ru[key] ?? key
    if (params) {
      for (const [k, v] of Object.entries(params)) {
        s = s.split(`{${k}}`).join(String(v))
      }
    }
    return s
  }

  return (
    <I18nContext.Provider value={{ lang, setLang, t }}>
      {children}
    </I18nContext.Provider>
  )
}

export function useI18n(): I18nValue {
  const ctx = useContext(I18nContext)
  if (!ctx) throw new Error('useI18n must be used within I18nProvider')
  return ctx
}
