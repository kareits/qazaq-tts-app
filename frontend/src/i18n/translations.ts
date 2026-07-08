// UI translations for the multilingual interface (ru / kk / en).
// `{placeholders}` are interpolated by the t() function.

export const translations = {
  ru: {
    appSubtitle: 'Синтез казахской речи из текста',
    statusModelLoaded: 'модель загружена',
    statusModelNotLoaded: 'модель не загружена',
    statusConnecting: 'подключение к backend…',
    voiceLabel: 'Голос',
    textLabel: 'Текст (казахская кириллица)',
    textPlaceholder: 'Введите текст на казахском языке…',
    textHint: 'Числа и даты пишите словами.',
    selectionAll: 'Озвучить: весь текст',
    selectionOne: 'Озвучить: предложение {n}',
    selectionRange: 'Озвучить: предложения {from}–{to}',
    selectionHint:
      'Клик — выбрать предложение, Shift+клик — диапазон, повторный клик — снять. Во время воспроизведения клик перематывает.',
    synthesize: 'Синтезировать',
    generating: 'Генерация…',
    cached: 'из кэша',
    preparing: 'Подготовка…',
    progressSynth: 'Синтез предложения {done} из {total}',
    progressConcat: 'Склейка сегментов',
    progressEncode: 'Конвертация в mp3',
    errorPrefix: 'Ошибка',
    start: 'Старт',
    pause: 'Пауза',
    stop: 'Стоп',
    speed: 'Скорость',
    download: 'Скачать mp3',
    sentenceTitle: 'Предложение {n}',
    warningNotKazakh:
      'Текст не похож на казахскую кириллицу — KazakhTTS2 работает только с казахским текстом на кириллице.',
    footerCreditsLicenses: 'Авторы и лицензии',
    creditsP1: 'iSoyle — независимый проект, разработанный {dev}.',
    creditsBuiltWith:
      'Собрано на ESPnet2, ParallelWaveGAN, FastAPI и React. Эти компоненты используются по их open-source лицензиям.',
    creditsDisclaimer:
      'iSoyle не аффилирован с ISSAI или Nazarbayev University и не одобрен ими.',
  },
  kk: {
    appSubtitle: 'Қазақ мәтінін дыбысқа айналдыру',
    statusModelLoaded: 'модель жүктелді',
    statusModelNotLoaded: 'модель жүктелмеген',
    statusConnecting: 'бэкендке қосылу…',
    voiceLabel: 'Дауыс',
    textLabel: 'Мәтін (қазақ кириллицасы)',
    textPlaceholder: 'Қазақ тіліндегі мәтінді енгізіңіз…',
    textHint: 'Сандар мен күндерді сөзбен жазыңыз.',
    selectionAll: 'Дыбыстау: бүкіл мәтін',
    selectionOne: 'Дыбыстау: {n}-сөйлем',
    selectionRange: 'Дыбыстау: {from}–{to} сөйлемдер',
    selectionHint:
      'Басу — сөйлемді таңдау, Shift+басу — ауқым, қайта басу — алып тастау. Ойнату кезінде басу сол жерге өткізеді.',
    synthesize: 'Дыбыстау',
    generating: 'Жасалуда…',
    cached: 'кэштен',
    preparing: 'Дайындау…',
    progressSynth: '{done}/{total} сөйлем дыбысталуда',
    progressConcat: 'Сегменттерді біріктіру',
    progressEncode: 'mp3 форматына түрлендіру',
    errorPrefix: 'Қате',
    start: 'Бастау',
    pause: 'Пауза',
    stop: 'Тоқтату',
    speed: 'Жылдамдық',
    download: 'mp3 жүктеу',
    sentenceTitle: '{n}-сөйлем',
    warningNotKazakh:
      'Мәтін қазақ кириллицасына ұқсамайды — KazakhTTS2 тек қазақ кириллица мәтінімен жұмыс істейді.',
    footerCreditsLicenses: 'Авторлар мен лицензиялар',
    creditsP1: 'iSoyle — {dev} әзірлеген тәуелсіз жоба.',
    creditsBuiltWith:
      'ESPnet2, ParallelWaveGAN, FastAPI және React негізінде жасалған. Бұл компоненттер өз open-source лицензиялары бойынша қолданылады.',
    creditsDisclaimer:
      'iSoyle ISSAI немесе Nazarbayev University-мен байланысты емес және олармен мақұлданбаған.',
  },
  en: {
    appSubtitle: 'Kazakh text-to-speech',
    statusModelLoaded: 'model loaded',
    statusModelNotLoaded: 'model not loaded',
    statusConnecting: 'connecting to backend…',
    voiceLabel: 'Voice',
    textLabel: 'Text (Kazakh Cyrillic)',
    textPlaceholder: 'Enter Kazakh text…',
    textHint: 'Write numbers and dates as words.',
    selectionAll: 'Synthesize: whole text',
    selectionOne: 'Synthesize: sentence {n}',
    selectionRange: 'Synthesize: sentences {from}–{to}',
    selectionHint:
      'Click — select a sentence, Shift+click — a range, click again — deselect. During playback, click seeks.',
    synthesize: 'Synthesize',
    generating: 'Generating…',
    cached: 'from cache',
    preparing: 'Preparing…',
    progressSynth: 'Synthesizing sentence {done} of {total}',
    progressConcat: 'Merging segments',
    progressEncode: 'Converting to mp3',
    errorPrefix: 'Error',
    start: 'Start',
    pause: 'Pause',
    stop: 'Stop',
    speed: 'Speed',
    download: 'Download mp3',
    sentenceTitle: 'Sentence {n}',
    warningNotKazakh:
      "The text doesn't look like Kazakh Cyrillic — KazakhTTS2 works only with Kazakh Cyrillic text.",
    footerCreditsLicenses: 'Credits & Licenses',
    creditsP1: 'iSoyle is an independent project developed by {dev}.',
    creditsBuiltWith:
      'Built with ESPnet2, ParallelWaveGAN, FastAPI and React. These components are used under their respective open-source licenses.',
    creditsDisclaimer:
      'iSoyle is not affiliated with or endorsed by ISSAI or Nazarbayev University.',
  },
} as const

export type Lang = keyof typeof translations
export type TKey = keyof (typeof translations)['ru']

// Languages for the switcher (default first). Russian is the default.
export const LANGS: { code: Lang; label: string }[] = [
  { code: 'ru', label: 'RU' },
  { code: 'kk', label: 'KK' },
  { code: 'en', label: 'EN' },
]
