interface Props {
  value: string
  maxLength: number
  onChange: (text: string) => void
}

// Поле ввода текста со счётчиком символов и подсказкой.
export function TextInput({ value, maxLength, onChange }: Props) {
  return (
    <div className="field">
      <span className="field-label">Текст (казахская кириллица)</span>
      <textarea
        value={value}
        rows={5}
        maxLength={maxLength}
        placeholder="Введите текст на казахском языке…"
        onChange={(e) => onChange(e.target.value)}
      />
      <div className="text-meta">
        <span>
          {value.length} / {maxLength}
        </span>
        <span className="hint">Числа и даты пишите словами.</span>
      </div>
    </div>
  )
}
