import { BACKEND_URL } from '../api/ttsApi'

interface Props {
  audioUrl: string | null
}

// Кнопка скачивания готового mp3. Активна только после генерации.
export function DownloadButton({ audioUrl }: Props) {
  if (!audioUrl) return null
  return (
    <a className="download" href={`${BACKEND_URL}${audioUrl}`} download="speech.mp3">
      ⬇ Скачать mp3
    </a>
  )
}
