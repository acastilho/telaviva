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

// A biblioteca não contém gravações semeadas. Somente itens vindos da fonte
// oficial devem ser atribuídos a esta coleção.
const recordings: Recording[] = []

export function RecordingLibrary({ onClose }: { onClose: () => void }) {
  const [tab, setTab] = useState<'Todas' | 'Compradas' | 'Assinaturas' | 'Histórico'>('Todas')
  const [playing, setPlaying] = useState<Recording | null>(null)
  const filtered = recordings.filter((recording) =>
    tab === 'Todas' || tab === 'Histórico' && recording.progress > 0 ||
    tab === 'Compradas' && recording.source === 'Compra avulsa' ||
    tab === 'Assinaturas' && recording.source === 'Assinatura')

  if (playing) return <Replay recording={playing} onClose={() => setPlaying(null)} />

  const inProgress = recordings.filter((item) => item.progress > 0 && item.progress < 100)

  return <div className="library-shell">
    <header>
      <button className="brand brand-button institute-brand-link" onClick={onClose} aria-label="Voltar ao Instituto Tela Viva"><BrandMark /></button>
      <nav aria-label="Navegação da biblioteca"><button onClick={onClose}>Descobrir</button><button className="active">Minha biblioteca</button></nav>
    </header>
    <main className="library-main">
      <p className="eyebrow">SEU ESPAÇO</p><h1>Minhas aulas</h1><p className="library-intro">Somente gravações confirmadas pela biblioteca da sua conta aparecem aqui.</p>
      <section aria-labelledby="continue-title">
        <div className="section-heading"><div><p>CONTINUAR ASSISTINDO</p><h2 id="continue-title">De onde você parou</h2></div></div>
        {inProgress.length ? <div className="recording-grid">{inProgress.map((item) => <RecordingCard key={item.id} item={item} onPlay={() => setPlaying(item)} />)}</div> : <LibraryEmptyState text="Nenhum progresso verificado foi carregado." />}
      </section>
      <section className="library-all" aria-labelledby="all-title">
        <div className="section-heading"><div><p>SUA COLEÇÃO</p><h2 id="all-title">Todas as gravações</h2></div></div>
        <div className="library-tabs" role="tablist">{(['Todas', 'Compradas', 'Assinaturas', 'Histórico'] as const).map((name) => <button role="tab" aria-selected={tab === name} key={name} onClick={() => setTab(name)}>{name}</button>)}</div>
        {filtered.length ? <div className="recording-grid">{filtered.map((item) => <RecordingCard key={item.id} item={item} onPlay={() => setPlaying(item)} />)}</div> : <LibraryEmptyState text="Nenhuma gravação verificada foi carregada para esta conta." />}
      </section>
    </main>
  </div>
}

function LibraryEmptyState({ text }: { text: string }) {
  return <div className="empty-state" role="status"><strong>{text}</strong><p>A interface não usa gravações ou progresso fictícios para preencher este espaço.</p></div>
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
      <p className="resume-note">Progresso desta sessão: {progress}%</p>
    </main>
  </div>
}
