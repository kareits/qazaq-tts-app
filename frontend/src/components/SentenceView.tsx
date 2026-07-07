import type { Sentence, SentenceRange } from '../api/ttsApi'

interface Props {
  sentences: Sentence[]
  selection: SentenceRange | null
  playingIndex: number | null
  onSentenceClick: (index: number, shiftKey: boolean) => void
}

// Отображение текста как последовательности кликабельных предложений.
// Клик — выбор/перемотка, Shift-клик — расширение диапазона. Подсветка:
// текущее произносимое предложение (playing) и выбранный диапазон (selected).
export function SentenceView({
  sentences,
  selection,
  playingIndex,
  onSentenceClick,
}: Props) {
  if (sentences.length === 0) return null

  return (
    <div className="sentence-view">
      {sentences.map((s) => {
        const selected =
          selection !== null && s.index >= selection.from && s.index <= selection.to
        const playing = s.index === playingIndex
        const className = [
          'sentence',
          selected ? 'selected' : '',
          playing ? 'playing' : '',
        ]
          .filter(Boolean)
          .join(' ')
        return (
          <span key={s.index}>
            <span
              className={className}
              onClick={(e) => onSentenceClick(s.index, e.shiftKey)}
              title={`Предложение ${s.index + 1}`}
            >
              {s.text}
            </span>{' '}
          </span>
        )
      })}
    </div>
  )
}
