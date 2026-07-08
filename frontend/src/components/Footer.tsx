import { useI18n } from '../i18n/I18nContext'
import type { Lang } from '../i18n/translations'

// A single "Credits & Licenses" footer item whose popover shows on hover or
// keyboard focus. Only three tokens are links: the model (KazakhTTS2), its
// CC-BY-4.0 license, and the paper (LREC 2022). The block credits the most
// sensitive component (the KazakhTTS2 model, ISSAI) and states non-affiliation.
const KAZAKHTTS2_REPO = 'https://github.com/IS2AI/Kazakh_TTS'
const KAZAKHTTS2_PAPER = 'https://arxiv.org/abs/2201.05771'
const CC_BY_URL = 'https://creativecommons.org/licenses/by/4.0/'
const PAPER_TITLE =
  'KazakhTTS2: Extending the Open-Source Kazakh TTS Corpus With More Data, Speakers, and Topics'
const DEVELOPER = 'kareits'

function Ext({ href, children }: { href: string; children: string }) {
  return (
    <a href={href} target="_blank" rel="noreferrer noopener">
      {children}
    </a>
  )
}

// The model/license sentence with inline links, phrased per language so the
// links sit at grammatically natural positions.
function ModelSentence({ lang }: { lang: Lang }) {
  const model = <Ext href={KAZAKHTTS2_REPO}>KazakhTTS2</Ext>
  const cc = <Ext href={CC_BY_URL}>CC BY 4.0</Ext>
  if (lang === 'ru')
    return (
      <p>
        Синтез казахской речи основан на {model} от ISSAI, Nazarbayev University;
        лицензия — {cc}.
      </p>
    )
  if (lang === 'kk')
    return (
      <p>
        Қазақ сөйлеуін синтездеу {model} моделіне негізделген (ISSAI, Nazarbayev
        University); лицензиясы — {cc}.
      </p>
    )
  return (
    <p>
      Kazakh speech synthesis is based on {model} by ISSAI, Nazarbayev
      University, licensed under {cc}.
    </p>
  )
}

function citeLabel(lang: Lang): string {
  if (lang === 'ru') return 'Цитирование'
  if (lang === 'kk') return 'Дереккөз'
  return 'Please cite'
}

export function Footer() {
  const { t, lang } = useI18n()
  return (
    <footer className="footer">
      <div className="footer-item">
        <button className="footer-trigger" type="button">
          {t('footerCreditsLicenses')}
        </button>
        <div className="popover" role="tooltip">
          <p className="popover-title">iSoyle</p>
          <p>{t('creditsP1', { dev: DEVELOPER })}</p>
          <ModelSentence lang={lang} />
          <p className="popover-cite">
            {citeLabel(lang)}: Mussakhojayeva, Khassanov &amp; Varol, “
            {PAPER_TITLE}”, <Ext href={KAZAKHTTS2_PAPER}>LREC 2022</Ext>.
          </p>
          <p>{t('creditsBuiltWith')}</p>
          <p className="popover-muted">{t('creditsDisclaimer')}</p>
        </div>
      </div>
    </footer>
  )
}
