// National oyu-ornek ornament (Kazakh style) — a subtle accent.
// A horizontal border of a repeating motif: a tumarsha rhombus in the center and
// a pair of "qoshqar muyiz" (ram's horns) scrolls on the sides. Color — flag gold.

interface OrnamentProps {
  className?: string
}

export function Ornament({ className }: OrnamentProps) {
  return (
    <svg
      className={className}
      width="100%"
      height="22"
      role="presentation"
      aria-hidden="true"
    >
      <defs>
        <pattern
          id="oyu-ornek"
          width="60"
          height="22"
          patternUnits="userSpaceOnUse"
        >
          <g
            fill="none"
            stroke="var(--gold)"
            strokeWidth="1.4"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M30 4.5 L34.5 11 L30 17.5 L25.5 11 Z" />
            <path d="M25.5 11 C 19 11 16 5 10 7 C 5 8.7 6 14 10 13 C 12.3 12.4 11.4 10 9 11" />
            <path d="M34.5 11 C 41 11 44 5 50 7 C 55 8.7 54 14 50 13 C 47.7 12.4 48.6 10 51 11" />
          </g>
        </pattern>
      </defs>
      <rect width="100%" height="22" fill="url(#oyu-ornek)" />
    </svg>
  )
}

// Brand mark — a sun with rays (Kazakh flag motif), gold.
export function SunMark({ size = 30 }: { size?: number }) {
  const rays = Array.from({ length: 12 }, (_, i) => {
    const a = (i * 30 * Math.PI) / 180
    return (
      <line
        key={i}
        x1={12 + Math.cos(a) * 7.5}
        y1={12 + Math.sin(a) * 7.5}
        x2={12 + Math.cos(a) * 10.5}
        y2={12 + Math.sin(a) * 10.5}
      />
    )
  })
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="var(--gold)"
      strokeWidth="1.6"
      strokeLinecap="round"
      role="presentation"
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="4.5" fill="var(--gold)" stroke="none" />
      {rays}
    </svg>
  )
}
