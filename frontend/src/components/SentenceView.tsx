import type { Sentence, SentenceRange } from '../api/ttsApi'
import { useI18n } from '../i18n/I18nContext'

interface Props {
  sentences: Sentence[]
  selection: SentenceRange | null
  playingIndex: number | null
  onSentenceClick: (index: number, shiftKey: boolean) => void
}

// Renders text as a sequence of clickable sentences.
// Click — select/seek, Shift-click — extend the range. Highlighting:
// the currently spoken sentence (playing) and the selected range (selected).
export function SentenceView({
  sentences,
  selection,
  playingIndex,
  onSentenceClick,
}: Props) {
  const { t } = useI18n()
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
              title={t('sentenceTitle', { n: s.index + 1 })}
            >
              {s.text}
            </span>{' '}
          </span>
        )
      })}
    </div>
  )
}
