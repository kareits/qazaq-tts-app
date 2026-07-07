interface Props {
  disabled: boolean
  isPlaying: boolean
  currentTime: number
  duration: number
  onPlay: () => void
  onPause: () => void
  onStop: () => void
}

function formatTime(sec: number): string {
  if (!isFinite(sec)) return '0:00'
  const m = Math.floor(sec / 60)
  const s = Math.floor(sec % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

// Кастомные кнопки управления воспроизведением: Старт / Пауза / Стоп.
// Кнопки неактивны, пока нет сгенерированного аудио.
export function PlayerControls({
  disabled,
  isPlaying,
  currentTime,
  duration,
  onPlay,
  onPause,
  onStop,
}: Props) {
  const progress = duration > 0 ? (currentTime / duration) * 100 : 0
  return (
    <div className="player">
      <div className="player-buttons">
        <button onClick={onPlay} disabled={disabled || isPlaying}>
          ▶ Старт
        </button>
        <button onClick={onPause} disabled={disabled || !isPlaying}>
          ⏸ Пауза
        </button>
        <button onClick={onStop} disabled={disabled}>
          ⏹ Стоп
        </button>
        <span className="player-time">
          {formatTime(currentTime)} / {formatTime(duration)}
        </span>
      </div>
      <div className="progress">
        <div className="progress-fill" style={{ width: `${progress}%` }} />
      </div>
    </div>
  )
}
