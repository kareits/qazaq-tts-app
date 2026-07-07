// Клиент backend API. Все запросы идут на локальный backend.

export const BACKEND_URL = 'http://127.0.0.1:8000'

export interface Health {
  status: string
  device: string
  model_loaded: boolean
  active_engine: string | null
  max_text_length: number
}

export interface Voice {
  id: string
  name: string
  language: string
  engine: string
}

export interface Sentence {
  index: number
  text: string
  char_start: number
  char_end: number
}

export interface SplitResult {
  sentences: Sentence[]
  warning: string | null
}

export interface Segment {
  index: number
  char_start: number
  char_end: number
  start_sec: number
  end_sec: number
}

export interface TTSResult {
  audio_url: string
  format: string
  voice: string
  engine: string
  cached: boolean
  duration_sec: number
  segments: Segment[]
}

export interface SentenceRange {
  from: number
  to: number
}

async function parseError(res: Response): Promise<string> {
  const data = await res.json().catch(() => null)
  return (data && data.detail) || `Ошибка backend: ${res.status}`
}

export async function getHealth(): Promise<Health> {
  const res = await fetch(`${BACKEND_URL}/api/health`)
  if (!res.ok) throw new Error(await parseError(res))
  return res.json()
}

export async function getVoices(): Promise<Voice[]> {
  const res = await fetch(`${BACKEND_URL}/api/voices`)
  if (!res.ok) throw new Error(await parseError(res))
  const data = await res.json()
  return data.voices
}

export async function splitText(text: string): Promise<SplitResult> {
  const res = await fetch(`${BACKEND_URL}/api/split`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  })
  if (!res.ok) throw new Error(await parseError(res))
  return res.json()
}

export async function synthesize(
  text: string,
  voice: string,
  sentenceRange: SentenceRange | null,
): Promise<TTSResult> {
  const body: Record<string, unknown> = { text, voice }
  if (sentenceRange) body.sentence_range = sentenceRange
  const res = await fetch(`${BACKEND_URL}/api/tts`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(await parseError(res))
  return res.json()
}

export interface SynthProgress {
  stage: 'synth' | 'concat' | 'encode'
  done: number
  total: number
  percent: number
}

// Потоковый синтез (Server-Sent Events): вызывает onProgress по мере готовности
// предложений и возвращает итоговый результат.
export async function synthesizeStream(
  text: string,
  voice: string,
  sentenceRange: SentenceRange | null,
  onProgress: (p: SynthProgress) => void,
): Promise<TTSResult> {
  const body: Record<string, unknown> = { text, voice }
  if (sentenceRange) body.sentence_range = sentenceRange

  const res = await fetch(`${BACKEND_URL}/api/tts/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok || !res.body) throw new Error(await parseError(res))

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let result: TTSResult | null = null

  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    // SSE-события разделяются пустой строкой.
    const frames = buffer.split('\n\n')
    buffer = frames.pop() ?? ''
    for (const frame of frames) {
      const dataLine = frame.split('\n').find((l) => l.startsWith('data:'))
      if (!dataLine) continue
      const event = JSON.parse(dataLine.slice(5).trim())
      if (event.type === 'progress') onProgress(event as SynthProgress)
      else if (event.type === 'done') result = event.result as TTSResult
      else if (event.type === 'error') throw new Error(event.detail)
    }
  }

  if (!result) throw new Error('Синтез не вернул результат')
  return result
}
