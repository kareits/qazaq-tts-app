import { useI18n } from '../i18n/I18nContext'
import { LANGS } from '../i18n/translations'

// UI language switcher (RU / KK / EN).
export function LanguageSwitcher() {
  const { lang, setLang } = useI18n()
  return (
    <div className="lang-switch" role="group" aria-label="Language">
      {LANGS.map((l) => (
        <button
          key={l.code}
          className={l.code === lang ? 'active' : ''}
          aria-pressed={l.code === lang}
          onClick={() => setLang(l.code)}
        >
          {l.label}
        </button>
      ))}
    </div>
  )
}
