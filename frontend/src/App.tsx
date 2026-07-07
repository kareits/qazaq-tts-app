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

function App() {
  const [health, setHealth] = useState<Health | null>(null)
  const [voices, setVoices] = useState<Voice[]>([])
  const [voice, setVoice] = useState('female1')

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
  // Подсветка активна во время воспроизведения и на паузе; сбрасывается на
  // Стоп и по окончании (ended).
  const [highlightActive, setHighlightActive] = useState(false)

  const maxLength = health?.max_text_length ?? 1000

  // Загрузка статуса и голосов при старте.
  useEffect(() => {
    getHealth()
      .then(setHealth)
      .catch((e) => setError(e.message))
    getVoices()
      .then(setVoices)
      .catch(() => {
        /* список голосов не критичен для отображения */
      })
  }, [])

  // При изменении текста: сброс выделения/аудио + повторный /api/split с debounce.
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

  // Текущее произносимое предложение по таймингам сегментов.
  const playingIndex =
    highlightActive && result
      ? (result.segments.find(
          (s) => currentTime >= s.start_sec && currentTime < s.end_sec,
        )?.index ?? null)
      : null

  const handleVoiceChange = (v: string) => {
    setVoice(v)
    // Аудио было синтезировано другим голосом — сбрасываем.
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
    // Клик-перемотка: если есть аудио и у предложения есть сегмент — перематываем.
    const seg = result?.segments.find((s) => s.index === index)
    if (seg) seekTo(seg.start_sec)

    // Выбор предложения (повторный клик по одиночному выбору — снять выделение).
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

  // Управление плеером.
  const handlePlay = () => audioRef.current?.play()
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
    if (p.stage === 'synth') return `Синтез предложения ${p.done} из ${p.total}`
    if (p.stage === 'concat') return 'Склейка сегментов'
    return 'Конвертация в mp3'
  }

  const selectionLabel = !selection
    ? 'Озвучить: весь текст'
    : selection.from === selection.to
      ? `Озвучить: предложение ${selection.from + 1}`
      : `Озвучить: предложения ${selection.from + 1}–${selection.to + 1}`

  return (
    <main className="app">
      <header className="app-header">
        <div className="brand">
          <SunMark size={34} />
          <div>
            <h1>Kazakh TTS</h1>
            <p className="subtitle">Қазақ мәтінін дыбысқа айналдыру</p>
          </div>
        </div>
        <Ornament className="ornament" />
      </header>

      <div className="status">
        {health ? (
          <span>
            backend: {health.status} · {health.device} ·{' '}
            {health.active_engine ?? '—'} ·{' '}
            {health.model_loaded ? 'модель загружена' : 'модель не загружена'}
          </span>
        ) : (
          <span>подключение к backend…</span>
        )}
      </div>

      <VoiceSelect
        voices={voices}
        value={voice}
        disabled={loading}
        onChange={handleVoiceChange}
      />

      <TextInput value={text} maxLength={maxLength} onChange={setText} />

      {splitWarning && <div className="warning">{splitWarning}</div>}

      {sentences.length > 0 && (
        <>
          <div className="selection-hint">
            {selectionLabel}. Клик — выбрать предложение, Shift+клик — диапазон,
            повторный клик — снять. Во время воспроизведения клик перематывает.
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
          {loading ? 'Генерация…' : 'Синтезировать'}
        </button>
        {result?.cached && <span className="cached">из кэша</span>}
      </div>

      {loading && (
        <div className="synth-progress">
          <div className="synth-progress-head">
            <span>{progress ? progressLabel(progress) : 'Подготовка…'}</span>
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

      {error && <div className="error">Ошибка: {error}</div>}

      {result && (
        <>
          <PlayerControls
            disabled={!result}
            isPlaying={isPlaying}
            currentTime={currentTime}
            duration={result.duration_sec}
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
