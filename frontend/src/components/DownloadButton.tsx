import { BACKEND_URL } from '../api/ttsApi'
import { useI18n } from '../i18n/I18nContext'

interface Props {
  audioUrl: string | null
}

// Download button for the ready mp3. Shown only after generation.
export function DownloadButton({ audioUrl }: Props) {
  const { t } = useI18n()
  if (!audioUrl) return null
  return (
    <a className="download" href={`${BACKEND_URL}${audioUrl}`} download="speech.mp3">
      ⬇ {t('download')}
    </a>
  )
}
