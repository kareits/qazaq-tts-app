import { forwardRef } from 'react'

interface Props {
  src: string
  onTimeUpdate: (currentTime: number) => void
  onEnded: () => void
  onPlay: () => void
  onPause: () => void
}

// Скрытый <audio>: управление только кастомными кнопками (PlayerControls),
// стандартные controls не показываются. Ref пробрасывается наружу, чтобы
// вызывать play/pause и перематывать (currentTime) из App.
export const AudioPlayer = forwardRef<HTMLAudioElement, Props>(
  ({ src, onTimeUpdate, onEnded, onPlay, onPause }, ref) => (
    <audio
      ref={ref}
      src={src}
      style={{ display: 'none' }}
      onTimeUpdate={(e) => onTimeUpdate(e.currentTarget.currentTime)}
      onEnded={onEnded}
      onPlay={onPlay}
      onPause={onPause}
    />
  ),
)

AudioPlayer.displayName = 'AudioPlayer'
