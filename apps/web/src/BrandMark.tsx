type BrandMarkProps = {
  symbolOnly?: boolean
  className?: string
}

export function BrandMark({ symbolOnly = false, className = '' }: BrandMarkProps) {
  const classes = ['instituto-brand', symbolOnly ? 'symbol-only' : '', className].filter(Boolean).join(' ')

  return (
    <span className={classes} aria-label="Instituto Tela Viva">
      <svg className="instituto-mark" viewBox="0 0 96 96" role="img" aria-hidden="true">
        <defs>
          <linearGradient id="instituto-rainbow" x1="10" y1="18" x2="86" y2="46" gradientUnits="userSpaceOnUse">
            <stop offset="0" stopColor="#f07b68" />
            <stop offset="0.24" stopColor="#e8bc5b" />
            <stop offset="0.48" stopColor="#77bd8d" />
            <stop offset="0.72" stopColor="#6f98cf" />
            <stop offset="1" stopColor="#a982c5" />
          </linearGradient>
          <linearGradient id="instituto-door" x1="43" y1="48" x2="69" y2="78" gradientUnits="userSpaceOnUse">
            <stop offset="0" stopColor="#eef4dd" />
            <stop offset="1" stopColor="#d7f36b" />
          </linearGradient>
          <filter id="instituto-glow" x="-40%" y="-40%" width="180%" height="180%">
            <feGaussianBlur stdDeviation="3.5" result="blur" />
            <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>

        <path className="rainbow-arc arc-one" d="M12 47C14 25 30 12 48 12s34 13 36 35" />
        <path className="rainbow-arc arc-two" d="M19 47c2-17 14-28 29-28s27 11 29 28" />
        <path className="rainbow-arc arc-three" d="M26 47c2-12 11-20 22-20s20 8 22 20" />

        <path className="door-glow" d="M38 77V48h22v29" />
        <path className="door-frame" d="M36 79V46h26v33M33 79h34" />
        <path className="door-panel" d="M39 49l18 4v26l-18-3z" />
        <circle className="door-handle" cx="53" cy="64" r="1.5" />
        <path className="path-light" d="M49 79c0 5-5 7-12 10h24c-7-3-12-5-12-10z" />
      </svg>
      {!symbolOnly && (
        <span className="instituto-brand-copy">
          <small>Instituto</small>
          <strong>Tela Viva</strong>
        </span>
      )}
    </span>
  )
}
