type BrandMarkProps = {
  symbolOnly?: boolean
  className?: string
}

export function BrandMark({ symbolOnly = false, className = '' }: BrandMarkProps) {
  const classes = ['instituto-brand', symbolOnly ? 'symbol-only' : '', className].filter(Boolean).join(' ')

  return (
    <span className={classes} aria-label="Instituto Tela Viva">
      <svg className="instituto-mark" viewBox="0 0 120 96" role="img" aria-hidden="true">
        <path className="brand-arc brand-arc-one" d="M12 48C16 22 35 9 60 9s44 13 48 39" />
        <path className="brand-arc brand-arc-two" d="M20 49C24 28 40 17 60 17s36 11 40 32" />
        <path className="brand-arc brand-arc-three" d="M28 50C32 34 44 25 60 25s28 9 32 25" />
        <path className="brand-arc brand-arc-four" d="M36 51C40 40 49 33 60 33s20 7 24 18" />
        <path className="brand-arc brand-arc-five" d="M44 52C47 45 53 41 60 41s13 4 16 11" />

        <path className="portal-glow" d="M45 82V61c0-9 6-16 15-16s15 7 15 16v21" />
        <path className="portal-frame" d="M45 82V61c0-9 6-16 15-16s15 7 15 16v21M41 82h38" />
        <path className="portal-opening" d="M50 79V62c0-6 4-11 10-11s10 5 10 11v17z" />
        <path className="portal-light" d="M54 79V63c0-4 2-7 6-7s6 3 6 7v16z" />
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
