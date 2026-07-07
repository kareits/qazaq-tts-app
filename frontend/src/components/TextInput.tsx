import { useI18n } from '../i18n/I18nContext'

interface Props {
  value: string
  maxLength: number
  onChange: (text: string) => void
}

// Text input field with a character counter and a hint.
export function TextInput({ value, maxLength, onChange }: Props) {
  const { t } = useI18n()
  return (
    <div className="field">
      <span className="field-label">{t('textLabel')}</span>
      <textarea
        value={value}
        rows={5}
        maxLength={maxLength}
        placeholder={t('textPlaceholder')}
        onChange={(e) => onChange(e.target.value)}
      />
      <div className="text-meta">
        <span>
          {value.length} / {maxLength}
        </span>
        <span className="hint">{t('textHint')}</span>
      </div>
    </div>
  )
}
