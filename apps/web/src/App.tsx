import { useMemo, useState } from 'react'
import { LiveStudio } from './LiveStudio'
import { RecordingLibrary } from './RecordingLibrary'

type Session = {
  id: number
  title: string
  creator: string
  profession: string
  category: string
  tool: string
  language: string
  level: string
  price: number
  status: 'Ao vivo' | 'Agendado'
  schedule: string
  viewers?: string
  accent: string
  initials: string
}

const sessions: Session[] = [
  { id: 1, title: 'Identidade visual do zero', creator: 'Marina Luz', profession: 'Designer', category: 'Design', tool: 'Figma', language: 'Português', level: 'Intermediário', price: 0, status: 'Ao vivo', schedule: 'Agora', viewers: '1,2 mil', accent: 'coral', initials: 'ML' },
  { id: 2, title: 'Cerâmica: torneando uma xícara', creator: 'João Barro', profession: 'Ceramista', category: 'Artesanato', tool: 'Torno', language: 'Português', level: 'Iniciante', price: 18, status: 'Ao vivo', schedule: 'Agora', viewers: '842', accent: 'clay', initials: 'JB' },
  { id: 3, title: 'Luz natural em retratos', creator: 'Clara Reis', profession: 'Fotógrafa', category: 'Fotografia', tool: 'Câmera', language: 'Português', level: 'Todos os níveis', price: 0, status: 'Ao vivo', schedule: 'Agora', viewers: '618', accent: 'blue', initials: 'CR' },
  { id: 4, title: 'Do rascunho ao personagem', creator: 'Bia Yamada', profession: 'Ilustradora', category: 'Ilustração', tool: 'Procreate', language: 'Português', level: 'Intermediário', price: 22, status: 'Ao vivo', schedule: 'Agora', viewers: '375', accent: 'violet', initials: 'BY' },
  { id: 5, title: 'Pão de fermentação natural', creator: 'Caio Mendes', profession: 'Chef', category: 'Gastronomia', tool: 'Forno', language: 'Português', level: 'Iniciante', price: 0, status: 'Agendado', schedule: 'Hoje, 19:00', accent: 'gold', initials: 'CM' },
  { id: 6, title: 'Mixando vocais em casa', creator: 'Nina Alves', profession: 'Produtora musical', category: 'Música', tool: 'Ableton', language: 'Português', level: 'Avançado', price: 35, status: 'Agendado', schedule: 'Amanhã, 18:30', accent: 'green', initials: 'NA' },
  { id: 7, title: 'Portfólio que conta uma história', creator: 'Leo Costa', profession: 'Designer', category: 'Carreira', tool: 'Figma', language: 'Inglês', level: 'Todos os níveis', price: 15, status: 'Agendado', schedule: 'Qui, 20:00', accent: 'pink', initials: 'LC' },
]

const categories = [
  ['✎', 'Design', '128 aulas'], ['◉', 'Fotografia', '86 aulas'], ['♫', 'Música', '72 aulas'],
  ['◌', 'Artesanato', '64 aulas'], ['✦', 'Gastronomia', '53 aulas'], ['{ }', 'Tecnologia', '91 aulas'],
]

const creators = [
  { name: 'Marina Luz', role: 'Designer de marcas', followers: '24 mil seguidores', initials: 'ML', accent: 'coral' },
  { name: 'Caio Mendes', role: 'Chef e padeiro', followers: '18 mil seguidores', initials: 'CM', accent: 'gold' },
  { name: 'Nina Alves', role: 'Produtora musical', followers: '15 mil seguidores', initials: 'NA', accent: 'green' },
  { name: 'Clara Reis', role: 'Fotógrafa', followers: '12 mil seguidores', initials: 'CR', accent: 'blue' },
]

const newCreators = [
  { name: 'Ravi Nunes', role: 'Marceneiro', initials: 'RN', accent: 'clay' },
  { name: 'Eva Campos', role: 'Artista têxtil', initials: 'EC', accent: 'violet' },
  { name: 'Tomás Lee', role: 'Desenvolvedor criativo', initials: 'TL', accent: 'green' },
]

function Avatar({ initials, accent, large = false }: { initials: string; accent: string; large?: boolean }) {
  return <span className={`avatar ${accent} ${large ? 'avatar-large' : ''}`} aria-hidden="true">{initials}</span>
}

function SessionCard({ session, onWatch, compact = false }: { session: Session; onWatch: () => void; compact?: boolean }) {
  if (compact) {
    return (
      <article className="upcoming-card">
        <div className={`mini-art ${session.accent}`}><span>{session.initials}</span></div>
        <div className="upcoming-copy">
          <span className="date">{session.schedule}</span>
          <h3>{session.title}</h3>
          <p>{session.creator} · {session.level}</p>
          <span className="price">{session.price === 0 ? 'Gratuito' : `R$ ${session.price}`}</span>
        </div>
        <button className="icon-button" aria-label={`Lembrar da aula ${session.title}`} title="Adicionar lembrete">♡</button>
      </article>
    )
  }

  return (
    <article className="session-card">
      <button className={`session-art ${session.accent}`} onClick={onWatch} aria-label={`Assistir ${session.title}`}>
        <span className="art-mark">{session.initials}</span>
        <span className="live-badge"><i /> AO VIVO</span>
        <span className="viewer-count">◉ {session.viewers}</span>
        <span className="play">▶</span>
      </button>
      <div className="session-info">
        <Avatar initials={session.initials} accent={session.accent} />
        <div><h3>{session.title}</h3><p>{session.creator} <span className="verified">✓</span></p></div>
      </div>
      <div className="card-meta"><span>{session.category}</span><strong>{session.price === 0 ? 'Gratuito' : `R$ ${session.price}`}</strong></div>
    </article>
  )
}

export function App() {
  const [query, setQuery] = useState('')
  const [filtersOpen, setFiltersOpen] = useState(false)
  const [category, setCategory] = useState('Todas')
  const [profession, setProfession] = useState('Todas')
  const [tool, setTool] = useState('Todas')
  const [language, setLanguage] = useState('Todos')
  const [level, setLevel] = useState('Todos')
  const [payment, setPayment] = useState('Todos')
  const [timing, setTiming] = useState('Todos')
  const [maxPrice, setMaxPrice] = useState(50)
  const [loginOpen, setLoginOpen] = useState(false)
  const [studioOpen, setStudioOpen] = useState(false)
  const [libraryOpen, setLibraryOpen] = useState(false)

  const filtered = useMemo(() => sessions.filter((session) => {
    const term = query.toLocaleLowerCase('pt-BR')
    const matchesQuery = [session.title, session.creator, session.profession, session.category, session.tool].some((value) => value.toLocaleLowerCase('pt-BR').includes(term))
    return matchesQuery &&
      (category === 'Todas' || session.category === category) &&
      (profession === 'Todas' || session.profession === profession) &&
      (tool === 'Todas' || session.tool === tool) &&
      (language === 'Todos' || session.language === language) &&
      (level === 'Todos' || session.level === level) &&
      (payment === 'Todos' || (payment === 'Gratuito' ? session.price === 0 : session.price > 0)) &&
      (timing === 'Todos' || session.status === timing) && session.price <= maxPrice
  }), [category, language, level, maxPrice, payment, profession, query, timing, tool])

  const liveSessions = filtered.filter((session) => session.status === 'Ao vivo')
  const upcoming = filtered.filter((session) => session.status === 'Agendado')
  const activeFilterCount = [category !== 'Todas', profession !== 'Todas', tool !== 'Todas', language !== 'Todos', level !== 'Todos', payment !== 'Todos', timing !== 'Todos', maxPrice < 50].filter(Boolean).length

  const clearFilters = () => {
    setCategory('Todas'); setProfession('Todas'); setTool('Todas'); setLanguage('Todos')
    setLevel('Todos'); setPayment('Todos'); setTiming('Todos'); setMaxPrice(50)
  }

  if (studioOpen) return <LiveStudio onClose={() => setStudioOpen(false)} />
  if (libraryOpen) return <RecordingLibrary onClose={() => setLibraryOpen(false)} />

  return (
    <div className="app-shell">
      <header>
        <a className="brand" href="#inicio" aria-label="TelaViva, início"><span className="brand-icon">▶</span>TelaViva</a>
        <nav aria-label="Navegação principal"><a className="active" href="#inicio">Descobrir</a><a href="#categorias">Categorias</a><a href="#proximas">Agenda</a><button onClick={() => setLibraryOpen(true)}>Minha biblioteca</button></nav>
        <div className="header-actions"><button className="link-button" onClick={() => setLoginOpen(true)}>Entrar</button><button className="link-button create-live" onClick={() => setStudioOpen(true)}>Criar live</button><button className="primary small" onClick={() => setLoginOpen(true)}>Criar conta</button></div>
      </header>

      <main id="inicio">
        <section className="welcome">
          <div><p className="eyebrow">BEM-VINDO À TELAVIVA</p><h1>O que você quer<br /><em>aprender hoje?</em></h1><p>Entre nos bastidores do trabalho real. Aprenda ao vivo com quem faz.</p></div>
          <div className="live-orbit"><span className="orbit one"><b /></span><span className="orbit two"><b /></span><span className="orbit three"><b /></span><div><strong>4</strong><span>ao vivo agora</span></div></div>
        </section>

        <section className="discovery" aria-label="Pesquisa e filtros">
          <label className="search"><span aria-hidden="true">⌕</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Busque por tema, profissional ou ferramenta..." /></label>
          <button className={`filter-trigger ${filtersOpen ? 'selected' : ''}`} onClick={() => setFiltersOpen(!filtersOpen)} aria-expanded={filtersOpen} aria-controls="filters"><span>☷</span> Filtros {activeFilterCount > 0 && <b>{activeFilterCount}</b>}</button>
          {filtersOpen && <div className="filters" id="filters">
            <Filter label="Profissão" value={profession} onChange={setProfession} options={['Todas', 'Designer', 'Ceramista', 'Fotógrafa', 'Ilustradora', 'Chef', 'Produtora musical']} />
            <Filter label="Categoria" value={category} onChange={setCategory} options={['Todas', 'Design', 'Artesanato', 'Fotografia', 'Ilustração', 'Gastronomia', 'Música', 'Carreira']} />
            <Filter label="Ferramenta" value={tool} onChange={setTool} options={['Todas', 'Figma', 'Torno', 'Câmera', 'Procreate', 'Forno', 'Ableton']} />
            <Filter label="Idioma" value={language} onChange={setLanguage} options={['Todos', 'Português', 'Inglês']} />
            <Filter label="Nível" value={level} onChange={setLevel} options={['Todos', 'Iniciante', 'Intermediário', 'Avançado', 'Todos os níveis']} />
            <Filter label="Preço" value={payment} onChange={setPayment} options={['Todos', 'Gratuito', 'Pago']} />
            <Filter label="Quando" value={timing} onChange={setTiming} options={['Todos', 'Ao vivo', 'Agendado']} />
            <label className="range-filter"><span>Até R$ {maxPrice}</span><input aria-label="Faixa de preço máxima" type="range" min="0" max="50" step="5" value={maxPrice} onChange={(event) => setMaxPrice(Number(event.target.value))} /></label>
            <button className="clear" onClick={clearFilters}>Limpar filtros</button>
          </div>}
        </section>

        <section className="content-section">
          <SectionHeading eyebrow="ACONTECENDO AGORA" title="Profissionais ao vivo" action="Ver todos" />
          {liveSessions.length ? <div className="session-grid">{liveSessions.map((session) => <SessionCard key={session.id} session={session} onWatch={() => setLoginOpen(true)} />)}</div> : <EmptyState />}
        </section>

        <section className="category-section" id="categorias">
          <SectionHeading eyebrow="EXPLORE SEU INTERESSE" title="Categorias" />
          <div className="category-grid">{categories.map(([icon, name, count]) => <button key={name} onClick={() => { setCategory(name); setFiltersOpen(true); document.getElementById('inicio')?.scrollIntoView() }}><span>{icon}</span><strong>{name}</strong><small>{count}</small><i>↗</i></button>)}</div>
        </section>

        <section className="split-sections" id="proximas">
          <div><SectionHeading eyebrow="PROGRAME-SE" title="Próximas aulas" />{upcoming.length ? <div className="upcoming-list">{upcoming.map((session) => <SessionCard key={session.id} session={session} compact onWatch={() => setLoginOpen(true)} />)}</div> : <EmptyState />}</div>
          <div><SectionHeading eyebrow="EM DESTAQUE" title="Criadores populares" />
            <div className="creator-list">{creators.map((creator, index) => <article key={creator.name}><span className="rank">0{index + 1}</span><Avatar {...creator} large /><div><h3>{creator.name} <span className="verified">✓</span></h3><p>{creator.role}</p><small>{creator.followers}</small></div><button aria-label={`Seguir ${creator.name}`}>+</button></article>)}</div>
          </div>
        </section>

        <section className="new-creators">
          <SectionHeading eyebrow="NOVOS TALENTOS" title="Acabaram de chegar" action="Conhecer todos" />
          <div className="new-grid">{newCreators.map((creator) => <article key={creator.name}><Avatar {...creator} large /><div><h3>{creator.name}</h3><p>{creator.role}</p></div><span>Novo</span></article>)}</div>
        </section>
      </main>

      <footer><a className="brand" href="#inicio"><span className="brand-icon">▶</span>TelaViva</a><p>Trabalho real. Conhecimento ao vivo.</p><span>© 2026 TelaViva</span></footer>

      {loginOpen && <div className="modal-backdrop" role="presentation" onMouseDown={() => setLoginOpen(false)}><section className="modal" role="dialog" aria-modal="true" aria-labelledby="login-title" onMouseDown={(event) => event.stopPropagation()}><button className="modal-close" onClick={() => setLoginOpen(false)} aria-label="Fechar">×</button><span className="modal-icon">▶</span><p className="eyebrow">QUASE LÁ</p><h2 id="login-title">Entre para assistir</h2><p>Crie sua conta gratuita ou entre para acompanhar transmissões, conversar com profissionais e salvar suas aulas.</p><button className="primary full">Criar conta grátis</button><button className="secondary full">Já tenho uma conta</button><small>Assistir transmissões requer login.</small></section></div>}
    </div>
  )
}

function Filter({ label, value, options, onChange }: { label: string; value: string; options: string[]; onChange: (value: string) => void }) {
  return <label><span>{label}</span><select aria-label={label} value={value} onChange={(event) => onChange(event.target.value)}>{options.map((option) => <option key={option}>{option}</option>)}</select></label>
}

function SectionHeading({ eyebrow, title, action }: { eyebrow: string; title: string; action?: string }) {
  return <div className="section-heading"><div><p>{eyebrow}</p><h2>{title}</h2></div>{action && <a href="#inicio">{action} <span>→</span></a>}</div>
}

function EmptyState() {
  return <div className="empty-state"><strong>Nenhuma aula encontrada</strong><p>Tente ajustar a busca ou remover alguns filtros.</p></div>
}
