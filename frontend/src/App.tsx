import { useEffect, useRef, useState } from 'react'
import './App.css'
import {
  BACKEND_URL,
  getHealth,
  getVoices,
  splitText,
  synthesizeStream,
  type Health,
  type Sentence,
  type SentenceRange,
  type SynthProgress,
  type TTSResult,
  type Voice,
} from './api/ttsApi'
import { VoiceSelect } from './components/VoiceSelect'
import { TextInput } from './components/TextInput'
import { SentenceView } from './components/SentenceView'
import { AudioPlayer } from './components/AudioPlayer'
import { PlayerControls } from './components/PlayerControls'
import { DownloadButton } from './components/DownloadButton'
import { Ornament, SunMark } from './components/Ornament'
import { LanguageSwitcher } from './components/LanguageSwitcher'
import { useI18n } from './i18n/I18nContext'

function App() {
  const { t } = useI18n()

  const [health, setHealth] = useState<Health | null>(null)
  const [voices, setVoices] = useState<Voice[]>([])
  const [voice, setVoice] = useState('female3')

  const [text, setText] = useState(
    'Сәлеметсіз бе! Бұл қазақ тілінде сөйлеу синтезінің мысалы. Тағы бір сөйлем.',
  )
  const [sentences, setSentences] = useState<Sentence[]>([])
  const [splitWarning, setSplitWarning] = useState<string | null>(null)

  const [selection, setSelection] = useState<SentenceRange | null>(null)
  const [anchor, setAnchor] = useState<number | null>(null)

  const [result, setResult] = useState<TTSResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [progress, setProgress] = useState<SynthProgress | null>(null)
  const [error, setError] = useState<string | null>(null)

  const audioRef = useRef<HTMLAudioElement>(null)
  const [currentTime, setCurrentTime] = useState(0)
  const [isPlaying, setIsPlaying] = useState(false)
  // Playback speed (0.1–3.0, step 0.1). Persists across syntheses.
  const [speed, setSpeed] = useState(1.0)
  // Highlight is active during playback and while paused; cleared on Stop and
  // when playback ends.
  const [highlightActive, setHighlightActive] = useState(false)

  const maxLength = health?.max_text_length ?? 1000

  // Load status and voices on startup.
  useEffect(() => {
    getHealth()
      .then(setHealth)
      .catch((e) => setError(e.message))
    getVoices()
      .then(setVoices)
      .catch(() => {
        /* the voice list is not critical for rendering */
      })
  }, [])

  // On text change: reset selection/audio + re-run /api/split with a debounce.
  useEffect(() => {
    setSelection(null)
    setAnchor(null)
    setResult(null)
    setError(null)
    setIsPlaying(false)
    setHighlightActive(false)
    setCurrentTime(0)

    if (!text.trim()) {
      setSentences([])
      setSplitWarning(null)
      return
    }

    const id = setTimeout(() => {
      splitText(text)
        .then((r) => {
          setSentences(r.sentences)
          setSplitWarning(r.warning)
        })
        .catch(() => {
          setSentences([])
          setSplitWarning(null)
        })
    }, 500)
    return () => clearTimeout(id)
  }, [text])

  // Currently spoken sentence, derived from the segment timings.
  const playingIndex =
    highlightActive && result
      ? (result.segments.find(
          (s) => currentTime >= s.start_sec && currentTime < s.end_sec,
        )?.index ?? null)
      : null

  const handleVoiceChange = (v: string) => {
    setVoice(v)
    // The audio was synthesized with another voice — reset it.
    setResult(null)
    setIsPlaying(false)
    setHighlightActive(false)
    setCurrentTime(0)
  }

  const seekTo = (sec: number) => {
    const a = audioRef.current
    if (a) {
      a.currentTime = sec
      setCurrentTime(sec)
    }
  }

  const handleSentenceClick = (index: number, shiftKey: boolean) => {
    if (shiftKey && anchor !== null) {
      setSelection({ from: Math.min(anchor, index), to: Math.max(anchor, index) })
      return
    }
    // Click-to-seek: if there is audio and the sentence has a segment, seek to it.
    const seg = result?.segments.find((s) => s.index === index)
    if (seg) seekTo(seg.start_sec)

    // Sentence selection (clicking the single selected one again clears it).
    if (selection && selection.from === index && selection.to === index) {
      setSelection(null)
      setAnchor(null)
    } else {
      setSelection({ from: index, to: index })
      setAnchor(index)
    }
  }

  const handleSynthesize = () => {
    setLoading(true)
    setError(null)
    setResult(null)
    setProgress(null)
    setIsPlaying(false)
    setHighlightActive(false)
    setCurrentTime(0)
    synthesizeStream(text, voice, selection, setProgress)
      .then(setResult)
      .catch((e) => setError(e.message))
      .finally(() => {
        setLoading(false)
        setProgress(null)
      })
  }

  // Apply the speed to the audio when it changes and when new audio appears.
  useEffect(() => {
    const a = audioRef.current
    if (a) {
      a.defaultPlaybackRate = speed
      a.playbackRate = speed
    }
  }, [speed, result])

  // Player controls.
  const handlePlay = () => {
    const a = audioRef.current
    if (a) {
      a.playbackRate = speed
      a.play()
    }
  }
  const handlePause = () => audioRef.current?.pause()
  const handleStop = () => {
    const a = audioRef.current
    if (a) {
      a.pause()
      a.currentTime = 0
    }
    setCurrentTime(0)
    setHighlightActive(false)
  }

  const progressLabel = (p: SynthProgress): string => {
    if (p.stage === 'synth')
      return t('progressSynth', { done: p.done, total: p.total })
    if (p.stage === 'concat') return t('progressConcat')
    return t('progressEncode')
  }

  const selectionLabel = !selection
    ? t('selectionAll')
    : selection.from === selection.to
      ? t('selectionOne', { n: selection.from + 1 })
      : t('selectionRange', { from: selection.from + 1, to: selection.to + 1 })

  return (
    <main className="app">
      <header className="app-header">
        <div className="header-top">
          <div className="brand">
            <SunMark size={34} />
            <div>
              <h1>Kazakh TTS</h1>
              <p className="subtitle">{t('appSubtitle')}</p>
            </div>
          </div>
          <LanguageSwitcher />
        </div>
        <Ornament className="ornament" />
      </header>

      <div className="status">
        {health ? (
          <span>
            backend: {health.status} · {health.device} ·{' '}
            {health.active_engine ?? '—'} ·{' '}
            {health.model_loaded
              ? t('statusModelLoaded')
              : t('statusModelNotLoaded')}
          </span>
        ) : (
          <span>{t('statusConnecting')}</span>
        )}
      </div>

      <VoiceSelect
        voices={voices}
        value={voice}
        disabled={loading}
        onChange={handleVoiceChange}
      />

      <TextInput value={text} maxLength={maxLength} onChange={setText} />

      {splitWarning && <div className="warning">{t('warningNotKazakh')}</div>}

      {sentences.length > 0 && (
        <>
          <div className="selection-hint">
            {selectionLabel}. {t('selectionHint')}
          </div>
          <SentenceView
            sentences={sentences}
            selection={selection}
            playingIndex={playingIndex}
            onSentenceClick={handleSentenceClick}
          />
        </>
      )}

      <div className="actions">
        <button
          className="synth"
          onClick={handleSynthesize}
          disabled={loading || !health?.model_loaded || text.trim().length === 0}
        >
          {loading ? t('generating') : t('synthesize')}
        </button>
        {result?.cached && <span className="cached">{t('cached')}</span>}
      </div>

      {loading && (
        <div className="synth-progress">
          <div className="synth-progress-head">
            <span>{progress ? progressLabel(progress) : t('preparing')}</span>
            <span className="synth-percent">{progress?.percent ?? 0}%</span>
          </div>
          <div className="progress">
            <div
              className="progress-fill"
              style={{ width: `${progress?.percent ?? 5}%` }}
            />
          </div>
        </div>
      )}

      {error && (
        <div className="error">
          {t('errorPrefix')}: {error}
        </div>
      )}

      {result && (
        <>
          <PlayerControls
            disabled={!result}
            isPlaying={isPlaying}
            currentTime={currentTime}
            duration={result.duration_sec}
            speed={speed}
            onSpeedChange={setSpeed}
            onPlay={handlePlay}
            onPause={handlePause}
            onStop={handleStop}
          />
          <DownloadButton audioUrl={result.audio_url} />
          <AudioPlayer
            ref={audioRef}
            src={`${BACKEND_URL}${result.audio_url}`}
            onTimeUpdate={setCurrentTime}
            onEnded={() => {
              setIsPlaying(false)
              setHighlightActive(false)
              setCurrentTime(0)
            }}
            onPlay={() => {
              setIsPlaying(true)
              setHighlightActive(true)
            }}
            onPause={() => setIsPlaying(false)}
          />
        </>
      )}
    </main>
  )
}

export default App
