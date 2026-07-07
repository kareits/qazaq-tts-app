import { useI18n } from '../i18n/I18nContext'

interface Props {
  disabled: boolean
  isPlaying: boolean
  currentTime: number
  duration: number
  speed: number
  onSpeedChange: (speed: number) => void
  onPlay: () => void
  onPause: () => void
  onStop: () => void
}

// Playback speed bounds.
const SPEED_MIN = 0.1
const SPEED_MAX = 3.0
const SPEED_STEP = 0.1

function formatTime(sec: number): string {
  if (!isFinite(sec)) return '0:00'
  const m = Math.floor(sec / 60)
  const s = Math.floor(sec % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

// Custom playback control buttons: Start / Pause / Stop.
// The buttons are disabled until audio has been generated.
export function PlayerControls({
  disabled,
  isPlaying,
  currentTime,
  duration,
  speed,
  onSpeedChange,
  onPlay,
  onPause,
  onStop,
}: Props) {
  const { t } = useI18n()
  const progress = duration > 0 ? (currentTime / duration) * 100 : 0
  return (
    <div className="player">
      <div className="player-buttons">
        <button onClick={onPlay} disabled={disabled || isPlaying}>
          ▶ {t('start')}
        </button>
        <button onClick={onPause} disabled={disabled || !isPlaying}>
          ⏸ {t('pause')}
        </button>
        <button onClick={onStop} disabled={disabled}>
          ⏹ {t('stop')}
        </button>
        <span className="player-time">
          {formatTime(currentTime)} / {formatTime(duration)}
        </span>
      </div>
      <div className="progress">
        <div className="progress-fill" style={{ width: `${progress}%` }} />
      </div>
      <div className="speed">
        <label htmlFor="speed-range">{t('speed')}</label>
        <input
          id="speed-range"
          type="range"
          min={SPEED_MIN}
          max={SPEED_MAX}
          step={SPEED_STEP}
          value={speed}
          disabled={disabled}
          onChange={(e) => onSpeedChange(Number(e.target.value))}
        />
        <span className="speed-value">{speed.toFixed(1)}×</span>
      </div>
    </div>
  )
}
