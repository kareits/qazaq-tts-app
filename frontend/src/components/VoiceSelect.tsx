import type { Voice } from '../api/ttsApi'
import { useI18n } from '../i18n/I18nContext'

interface Props {
  voices: Voice[]
  value: string
  disabled?: boolean
  onChange: (voice: string) => void
}

// Synthesis voice selector.
export function VoiceSelect({ voices, value, disabled, onChange }: Props) {
  const { t } = useI18n()
  return (
    <label className="field">
      <span className="field-label">{t('voiceLabel')}</span>
      <select
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
      >
        {voices.map((v) => (
          <option key={v.id} value={v.id}>
            {v.name}
          </option>
        ))}
      </select>
    </label>
  )
}
