import { useState } from 'react'
import { BrandMark } from './BrandMark'

type Recording = {
  id: number
  title: string
  creator: string
  source: 'Compra avulsa' | 'Assinatura'
  duration: string
  progress: number
  accent: string
  initials: string
}

const recordings: Recording[] = [
  { id: 1, title: 'Identidade visual do zero', creator: 'Marina Luz', source: 'Compra avulsa', duration: '1h 18min', progress: 42, accent: 'coral', initials: 'ML' },
  { id: 2, title: 'Luz natural em retratos', creator: 'Clara Reis', source: 'Assinatura', duration: '52min', progress: 0, accent: 'blue', initials: 'CR' },
  { id: 3, title: 'Mixando vocais em casa', creator: 'Nina Alves', source: 'Assinatura', duration: '1h 34min', progress: 100, accent: 'green', initials: 'NA' },
]

export function RecordingLibrary({ onClose }: { onClose: () => void }) {
  const [tab, setTab] = useState<'Todas' | 'Compradas' | 'Assinaturas' | 'Histórico'>('Todas')
  const [playing, setPlaying] = useState<Recording | null>(null)
  const filtered = recordings.filter((recording) =>
    tab === 'Todas' || tab === 'Histórico' && recording.progress > 0 ||
    tab === 'Compradas' && recording.source === 'Compra avulsa' ||
    tab === 'Assinaturas' && recording.source === 'Assinatura')

  if (playing) return <Replay recording={playing} onClose={() => setPlaying(null)} />

  return <div className="library-shell">
    <header>
      <button className="brand brand-button institute-brand-link" onClick={onClose} aria-label="Voltar ao Instituto Tela Viva"><BrandMark /></button>
      <nav aria-label="Navegação da biblioteca"><button onClick={onClose}>Descobrir</button><button className="active">Minha biblioteca</button></nav>
    </header>
    <main className="library-main">
      <p className="eyebrow">SEU ESPAÇO</p><h1>Minhas aulas</h1><p className="library-intro">Retome de onde parou ou reveja suas aulas quando quiser.</p>
      <section aria-labelledby="continue-title">
        <div className="section-heading"><div><p>CONTINUAR ASSISTINDO</p><h2 id="continue-title">De onde você parou</h2></div></div>
        <div className="recording-grid">{recordings.filter((item) => item.progress > 0 && item.progress < 100).map((item) => <RecordingCard key={item.id} item={item} onPlay={() => setPlaying(item)} />)}</div>
      </section>
      <section className="library-all" aria-labelledby="all-title">
        <div className="section-heading"><div><p>SUA COLEÇÃO</p><h2 id="all-title">Todas as gravações</h2></div></div>
        <div className="library-tabs" role="tablist">{(['Todas', 'Compradas', 'Assinaturas', 'Histórico'] as const).map((name) => <button role="tab" aria-selected={tab === name} key={name} onClick={() => setTab(name)}>{name}</button>)}</div>
        <div className="recording-grid">{filtered.map((item) => <RecordingCard key={item.id} item={item} onPlay={() => setPlaying(item)} />)}</div>
      </section>
    </main>
  </div>
}

function RecordingCard({ item, onPlay }: { item: Recording; onPlay: () => void }) {
  return <article className="recording-card">
    <button className={`recording-art ${item.accent}`} onClick={onPlay} aria-label={`Assistir gravação ${item.title}`}><span>{item.initials}</span><i>▶</i></button>
    <div className="recording-copy"><small>{item.source} · {item.duration}</small><h3>{item.title}</h3><p>{item.creator}</p>{item.progress > 0 && <div className="watch-progress" aria-label={`${item.progress}% assistido`}><i style={{ width: `${item.progress}%` }} /></div>}</div>
  </article>
}

function Replay({ recording, onClose }: { recording: Recording; onClose: () => void }) {
  const [progress, setProgress] = useState(recording.progress)
  return <div className="replay-shell">
    <header><button className="brand brand-button" onClick={onClose}><span className="brand-icon">←</span>Minha biblioteca</button></header>
    <main className="replay-main">
      <div className={`replay-video ${recording.accent}`} role="region" aria-label={`Player de ${recording.title}`}><span>{recording.initials}</span><button aria-label="Reproduzir" onClick={() => setProgress(Math.min(100, progress + 10))}>▶</button></div>
      <div className="replay-progress"><i style={{ width: `${progress}%` }} /></div>
      <p className="eyebrow">REPLAY · {recording.source}</p><h1>{recording.title}</h1><p>com {recording.creator} · {recording.duration}</p>
      <p className="resume-note">Progresso salvo automaticamente · {progress}% assistido</p>
    </main>
  </div>
}
