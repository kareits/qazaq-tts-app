import type { Voice } from '../api/ttsApi'

interface Props {
  voices: Voice[]
  value: string
  disabled?: boolean
  onChange: (voice: string) => void
}

// Выбор голоса синтеза.
export function VoiceSelect({ voices, value, disabled, onChange }: Props) {
  return (
    <label className="field">
      <span className="field-label">Голос</span>
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
