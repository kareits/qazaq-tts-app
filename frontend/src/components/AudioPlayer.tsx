import { forwardRef } from 'react'

interface Props {
  src: string
  onTimeUpdate: (currentTime: number) => void
  onEnded: () => void
  onPlay: () => void
  onPause: () => void
}

// Hidden <audio>: controlled only by the custom buttons (PlayerControls); the
// native controls are not shown. The ref is forwarded out so App can call
// play/pause and seek (currentTime).
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
