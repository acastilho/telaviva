import { FormEvent, useEffect, useMemo, useState } from 'react'
import { AdminDashboard } from './AdminDashboard'
import { authClient, type Audience, type AuthSession } from './auth'
import { BrandMark } from './BrandMark'
import { CreatorDashboard } from './CreatorDashboard'
import { LiveStudio } from './LiveStudio'
import { RecordingLibrary } from './RecordingLibrary'
import { schedulingClient, usesRemoteSchedulingApi, type ScheduledStream } from './scheduling'

type Session = {
  id: string
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
  objective: string
  audiences: Audience[]
  liveStreamId?: string
}

type CreatorSummary = {
  name: string
  role: string
  followers?: string
  initials: string
  accent: string
}

type AuthMode = 'login' | 'register' | 'recover'

// Regra de integridade: catálogo, audiência e estado Ao vivo vêm da API.
// Sem fonte oficial, a interface permanece vazia em vez de inventar conteúdo.
const creators: CreatorSummary[] = []
const newCreators: CreatorSummary[] = []

const categories = [
  ['◌', 'Natureza'], ['✎', 'Criatividade'], ['{ }', 'Tecnologia'],
  ['◉', 'Fotografia'], ['✦', 'Gastronomia'], ['◇', 'Ofícios'],
]

const audienceCopy: Record<Audience, { eyebrow: string; title: string; description: string }> = {
  CHILD: { eyebrow: 'CRIANÇAS', title: 'Descobrir brincando', description: 'Experiências curadas, perguntas moderadas e linguagem simples. A conversa livre fica protegida.' },
  TEEN: { eyebrow: 'ADOLESCENTES', title: 'Aprender fazendo', description: 'Mais autonomia para explorar projetos reais, com interação moderada e proteção adequada à idade.' },
  ADULT: { eyebrow: 'ADULTOS', title: 'Acompanhar o processo', description: 'Acesso completo a aulas, profissionais, trilhas, comunidade e experiências de aprendizado vivo.' },
}

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
        {session.status === 'Ao vivo' ? <span className="live-badge"><i /> AO VIVO</span> : <span className="schedule-badge">{session.schedule}</span>}
        {session.viewers && <span className="viewer-count">◉ {session.viewers}</span>}
        <span className="play">▶</span>
      </button>
      <div className="session-info">
        <Avatar initials={session.initials} accent={session.accent} />
        <div><h3>{session.title}</h3><p>{session.creator}</p></div>
      </div>
      <div className="card-meta"><span>{session.category}</span><strong>{session.price === 0 ? 'Gratuito' : `R$ ${session.price}`}</strong></div>
    </article>
  )
}

function streamLevel(level: ScheduledStream['level']): string {
  if (level === 'BEGINNER') return 'Iniciante'
  if (level === 'INTERMEDIATE') return 'Intermediário'
  if (level === 'ADVANCED') return 'Avançado'
  return 'Todos os níveis'
}

function streamAudiences(description: string): Audience[] {
  const normalized = description.toLocaleLowerCase('pt-BR')
  if (normalized.includes('público: crianças')) return ['CHILD']
  if (normalized.includes('público: adolescentes e adultos')) return ['TEEN', 'ADULT']
  if (normalized.includes('público: adolescentes')) return ['TEEN']
  if (normalized.includes('público: adultos')) return ['ADULT']
  // Metadado legado ausente: falha fechada para menores em vez de presumir acesso.
  return ['ADULT']
}

function toSession(stream: ScheduledStream, live: boolean): Session {
  const startsAt = new Date(stream.starts_at)
  return {
    id: stream.id,
    title: stream.title,
    creator: 'Criador cadastrado',
    profession: 'Criador',
    category: 'Categoria cadastrada',
    tool: live ? 'Transmissão ao vivo' : 'Aula online',
    language: 'Não informado',
    level: streamLevel(stream.level),
    price: Number(stream.price),
    status: live ? 'Ao vivo' : 'Agendado',
    schedule: live ? 'Agora' : startsAt.toLocaleString('pt-BR', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }),
    accent: live ? 'green' : 'blue',
    initials: 'TV',
    objective: stream.objective,
    audiences: streamAudiences(stream.description),
    liveStreamId: live ? stream.id : undefined,
  }
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
  const [audience, setAudience] = useState<Audience>(() => {
    const saved = typeof window !== 'undefined' ? window.localStorage.getItem('tv_audience') : null
    return saved === 'CHILD' || saved === 'TEEN' || saved === 'ADULT' ? saved : 'ADULT'
  })
  const [authSession, setAuthSession] = useState<AuthSession | null>(null)
  const [authReady, setAuthReady] = useState(false)
  const [loginOpen, setLoginOpen] = useState(false)
  const [authMode, setAuthMode] = useState<AuthMode>('login')
  const [authEmail, setAuthEmail] = useState('')
  const [authPassword, setAuthPassword] = useState('')
  const [guardianEmail, setGuardianEmail] = useState('')
  const [authAudience, setAuthAudience] = useState<Audience>(audience)
  const [authError, setAuthError] = useState('')
  const [authMessage, setAuthMessage] = useState('')
  const [authLoading, setAuthLoading] = useState(false)
  const [pendingSessionId, setPendingSessionId] = useState<string | null>(null)
  const [studioOpen, setStudioOpen] = useState(false)
  const [selectedStudioStreamId, setSelectedStudioStreamId] = useState<string | undefined>()
  const [libraryOpen, setLibraryOpen] = useState(false)
  const [dashboardOpen, setDashboardOpen] = useState(false)
  const [adminOpen, setAdminOpen] = useState(false)
  const [toast, setToast] = useState('')
  const [sessions, setSessions] = useState<Session[]>([])
  const [catalogLoading, setCatalogLoading] = useState(usesRemoteSchedulingApi)
  const [catalogError, setCatalogError] = useState('')

  useEffect(() => {
    let active = true
    authClient.restore().then((session) => {
      if (!active) return
      setAuthSession(session)
      if (session) setAudience(session.user.audience)
      setAuthReady(true)
    })
    return () => { active = false }
  }, [])

  useEffect(() => {
    if (!usesRemoteSchedulingApi) {
      setSessions([])
      setCatalogLoading(false)
      setCatalogError('API de aulas não configurada.')
      return
    }

    let mounted = true
    const loadCatalog = async () => {
      try {
        const [activeStreams, upcomingStreams] = await Promise.all([
          schedulingClient.listActive(),
          schedulingClient.listUpcoming(),
        ])
        if (!mounted) return
        const activeIds = new Set(activeStreams.map((stream) => stream.id))
        setSessions([
          ...activeStreams.map((stream) => toSession(stream, true)),
          ...upcomingStreams.filter((stream) => !activeIds.has(stream.id)).map((stream) => toSession(stream, false)),
        ])
        setCatalogError('')
      } catch (error) {
        if (!mounted) return
        setSessions([])
        setCatalogError(error instanceof Error ? error.message : 'Não foi possível carregar a fonte oficial de aulas.')
      } finally {
        if (mounted) setCatalogLoading(false)
      }
    }

    void loadCatalog()
    const timer = window.setInterval(() => void loadCatalog(), 12_000)
    const onFocus = () => void loadCatalog()
    window.addEventListener('focus', onFocus)
    return () => {
      mounted = false
      window.clearInterval(timer)
      window.removeEventListener('focus', onFocus)
    }
  }, [])

  useEffect(() => {
    window.localStorage.setItem('tv_audience', audience)
    setAuthAudience(audience)
  }, [audience])

  useEffect(() => {
    if (!toast) return
    const timer = window.setTimeout(() => setToast(''), 3200)
    return () => window.clearTimeout(timer)
  }, [toast])

  const filtered = useMemo(() => sessions.filter((session) => {
    const term = query.toLocaleLowerCase('pt-BR')
    const matchesQuery = [session.title, session.creator, session.profession, session.category, session.tool].some((value) => value.toLocaleLowerCase('pt-BR').includes(term))
    return session.audiences.includes(audience) && matchesQuery &&
      (category === 'Todas' || session.category === category) &&
      (profession === 'Todas' || session.profession === profession) &&
      (tool === 'Todas' || session.tool === tool) &&
      (language === 'Todos' || session.language === language) &&
      (level === 'Todos' || session.level === level) &&
      (payment === 'Todos' || (payment === 'Gratuito' ? session.price === 0 : session.price > 0)) &&
      (timing === 'Todos' || session.status === timing) && session.price <= maxPrice
  }), [audience, category, language, level, maxPrice, payment, profession, query, sessions, timing, tool])

  const liveSessions = filtered.filter((session) => session.status === 'Ao vivo')
  const upcoming = filtered.filter((session) => session.status === 'Agendado')
  const activeFilterCount = [category !== 'Todas', profession !== 'Todas', tool !== 'Todas', language !== 'Todos', level !== 'Todos', payment !== 'Todos', timing !== 'Todos', maxPrice < 50].filter(Boolean).length
  const professionOptions = ['Todas', ...Array.from(new Set(sessions.map((session) => session.profession)))]
  const toolOptions = ['Todas', ...Array.from(new Set(sessions.map((session) => session.tool)))]
  const languageOptions = ['Todos', ...Array.from(new Set(sessions.map((session) => session.language)))]
  const levelOptions = ['Todos', ...Array.from(new Set(sessions.map((session) => session.level)))]

  const clearFilters = () => {
    setCategory('Todas'); setProfession('Todas'); setTool('Todas'); setLanguage('Todos')
    setLevel('Todos'); setPayment('Todos'); setTiming('Todos'); setMaxPrice(50)
  }

  const openAuth = (mode: AuthMode = 'login', pendingId: string | null = null) => {
    setAuthMode(mode)
    setPendingSessionId(pendingId)
    setAuthError('')
    setAuthMessage('')
    setAuthPassword('')
    setLoginOpen(true)
  }

  const openVerifiedLive = (session: Session) => {
    if (!session.liveStreamId) {
      setToast('Esta aula não possui uma transmissão ativa confirmada no sistema.')
      return
    }
    const url = new URL(window.location.href)
    url.search = ''
    url.hash = ''
    url.searchParams.set('live', session.liveStreamId)
    window.location.assign(url.toString())
  }

  const watchSession = (session: Session) => {
    if (!authSession) {
      openAuth('login', session.id)
      return
    }
    if (!session.audiences.includes(authSession.user.audience)) {
      setToast('Esta aula pertence a outra faixa de experiência.')
      return
    }
    if (session.status === 'Agendado') {
      setToast('O lembrete só será confirmado quando o serviço de agenda responder.')
      return
    }
    openVerifiedLive(session)
  }

  const submitAuth = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setAuthError('')
    setAuthMessage('')
    setAuthLoading(true)
    try {
      if (authMode === 'recover') {
        await authClient.recover(authEmail)
        setAuthMessage('Se a conta existir, as instruções de recuperação serão enviadas.')
        return
      }
      const session = authMode === 'register'
        ? await authClient.register(authEmail, authPassword, authAudience, guardianEmail)
        : await authClient.login(authEmail, authPassword)
      setAuthSession(session)
      setAudience(session.user.audience)
      setLoginOpen(false)
      setAuthEmail('')
      setAuthPassword('')
      setGuardianEmail('')
      if (pendingSessionId) {
        const pending = sessions.find((item) => item.id === pendingSessionId)
        if (pending?.status === 'Ao vivo' && pending.audiences.includes(session.user.audience)) openVerifiedLive(pending)
      }
      setPendingSessionId(null)
      setToast('Sessão iniciada com segurança.')
    } catch (error) {
      setAuthError(error instanceof Error ? translateAuthError(error.message) : 'Não foi possível entrar.')
    } finally {
      setAuthLoading(false)
    }
  }

  const logout = async () => {
    await authClient.logout()
    setAuthSession(null)
    setStudioOpen(false)
    setSelectedStudioStreamId(undefined)
    setDashboardOpen(false)
    setAdminOpen(false)
    setToast('Você saiu da sua conta.')
  }

  const openLibrary = () => {
    if (!authSession) return openAuth('login')
    setLibraryOpen(true)
  }

  const openCreator = () => {
    if (!authSession && authClient.usesRemoteApi) return openAuth('login')
    if (authSession && !['CREATOR', 'ADMIN'].includes(authSession.user.role) && authClient.usesRemoteApi) {
      setToast('Seu perfil ainda não possui acesso ao painel do criador.')
      return
    }
    setDashboardOpen(true)
  }

  const openAdmin = () => {
    if (!authSession && authClient.usesRemoteApi) return openAuth('login')
    if (authSession?.user.role !== 'ADMIN' && authClient.usesRemoteApi) {
      setToast('Área restrita a administradores.')
      return
    }
    setAdminOpen(true)
  }

  const openStudio = () => {
    if (!usesRemoteSchedulingApi) {
      setToast('A API de aulas precisa estar configurada para iniciar uma transmissão.')
      return
    }
    if (!authSession) return openAuth('login')
    if (!['CREATOR', 'ADMIN'].includes(authSession.user.role)) {
      setToast('Somente criadores autorizados podem iniciar transmissões.')
      return
    }
    setToast('Escolha uma aula cadastrada e toque em Transmitir.')
    setDashboardOpen(true)
  }

  if (studioOpen) return <LiveStudio streamId={selectedStudioStreamId} accessToken={authSession?.accessToken} onClose={() => { setStudioOpen(false); setSelectedStudioStreamId(undefined) }} />
  if (libraryOpen) return <RecordingLibrary onClose={() => setLibraryOpen(false)} />
  if (dashboardOpen) return <CreatorDashboard
    creatorLabel={authSession?.user.email.split('@')[0] ?? 'Criador'}
    creatorId={authSession?.user.id}
    accessToken={authSession?.accessToken}
    remoteApi={usesRemoteSchedulingApi}
    onClose={() => setDashboardOpen(false)}
    onStartLive={(streamId) => {
      if (!streamId) {
        setToast('Selecione uma aula confirmada pelo sistema antes de abrir o estúdio.')
        return
      }
      setSelectedStudioStreamId(streamId)
      setDashboardOpen(false)
      setStudioOpen(true)
    }}
  />
  if (adminOpen) return <AdminDashboard onClose={() => setAdminOpen(false)} />

  return (
    <div className="app-shell">
      <header className="main-header">
        <a className="brand institute-brand-link" href="#inicio" aria-label="Instituto Tela Viva, início"><BrandMark /></a>
        <nav aria-label="Navegação principal"><a className="active" href="#inicio">Descobrir</a><a href="#experiencias">Experiências</a><a href="#proximas">Agenda</a><button onClick={openLibrary}>Minha biblioteca</button></nav>
        <div className="header-actions">
          {authReady && authSession ? <>
            <button className="account-chip" onClick={() => setToast(`${authSession.user.email} · ${audienceLabel(authSession.user.audience)}`)}><span>{authSession.user.email.slice(0, 1).toUpperCase()}</span><b>{authSession.user.email.split('@')[0]}</b></button>
            <button className="link-button" onClick={logout}>Sair</button>
          </> : <>
            <button className="link-button" onClick={() => openAuth('login')}>Entrar</button>
            <button className="primary small" onClick={() => openAuth('register')}>Criar conta</button>
          </>}
        </div>
      </header>

      <main id="inicio">
        <section className="welcome">
          <div className="welcome-copy"><p className="eyebrow">INSTITUTO DE APRENDIZADO VIVO</p><h1>Onde o conhecimento<br /><em>acontece vivo.</em></h1><p className="mission">Aprenda acompanhando pessoas, natureza e tecnologia em processo. <em>Porque tecnologia também é natureza.</em></p><div className="welcome-actions"><a className="primary hero-button" href="#experiencias">Explorar experiências</a><button className="secondary" onClick={() => openAuth(authSession ? 'login' : 'register')}>{authSession ? 'Minha conta' : 'Começar gratuitamente'}</button></div></div>
          <div className="brand-stage"><BrandMark symbolOnly className="hero-mark" /><p className="live-now">{catalogLoading ? 'Verificando transmissões ativas…' : catalogError ? 'Fonte de transmissões indisponível' : <><strong>● {liveSessions.length}</strong> {liveSessions.length === 1 ? 'aula ao vivo' : 'aulas ao vivo'} para você</>}</p></div>
        </section>

        <section className="audience-section" aria-labelledby="audience-title">
          <div className="section-heading audience-heading"><div><p>UM INSTITUTO PARA CADA FASE DA VIDA</p><h2 id="audience-title">Escolha sua experiência</h2></div><span>Você pode mudar quando quiser.</span></div>
          <div className="audience-grid">
            {(Object.keys(audienceCopy) as Audience[]).map((item) => <button key={item} className={audience === item ? 'selected' : ''} onClick={() => setAudience(item)} aria-pressed={audience === item}><span className="audience-symbol">{item === 'CHILD' ? '✦' : item === 'TEEN' ? '↗' : '∞'}</span><small>{audienceCopy[item].eyebrow}</small><strong>{audienceCopy[item].title}</strong><p>{audienceCopy[item].description}</p><i>{audience === item ? 'Selecionado' : 'Escolher'}</i></button>)}
          </div>
        </section>

        <section className="discovery" aria-label="Pesquisa e filtros">
          <label className="search"><span aria-hidden="true">⌕</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Busque por tema, profissional ou ferramenta..." /></label>
          <button className={`filter-trigger ${filtersOpen ? 'selected' : ''}`} onClick={() => setFiltersOpen(!filtersOpen)} aria-expanded={filtersOpen} aria-controls="filters"><span>☷</span> Filtros {activeFilterCount > 0 && <b>{activeFilterCount}</b>}</button>
          {filtersOpen && <div className="filters" id="filters">
            <Filter label="Profissão" value={profession} onChange={setProfession} options={professionOptions} />
            <Filter label="Categoria" value={category} onChange={setCategory} options={['Todas', ...categories.map(([, name]) => name), 'Categoria cadastrada']} />
            <Filter label="Ferramenta" value={tool} onChange={setTool} options={toolOptions} />
            <Filter label="Idioma" value={language} onChange={setLanguage} options={languageOptions} />
            <Filter label="Nível" value={level} onChange={setLevel} options={levelOptions} />
            <Filter label="Preço" value={payment} onChange={setPayment} options={['Todos', 'Gratuito', 'Pago']} />
            <Filter label="Quando" value={timing} onChange={setTiming} options={['Todos', 'Ao vivo', 'Agendado']} />
            <label className="range-filter"><span>Até R$ {maxPrice}</span><input aria-label="Faixa de preço máxima" type="range" min="0" max="50" step="5" value={maxPrice} onChange={(event) => setMaxPrice(Number(event.target.value))} /></label>
            <button className="clear" onClick={clearFilters}>Limpar filtros</button>
          </div>}
        </section>

        <section className="content-section" id="experiencias">
          <SectionHeading eyebrow="ACONTECENDO AGORA" title="Profissionais ao vivo" action="Ver todos" />
          {catalogLoading ? <CatalogState title="Verificando aulas ativas" description="Consultando a fonte oficial para mostrar somente transmissões realmente iniciadas." /> : catalogError ? <CatalogState title="Não foi possível consultar as aulas" description={catalogError} /> : liveSessions.length ? <div className="session-grid">{liveSessions.map((session) => <SessionCard key={session.id} session={session} onWatch={() => watchSession(session)} />)}</div> : <LiveEmptyState />}
        </section>

        <section className="principle-section" aria-label="Princípio do Instituto Tela Viva">
          <p className="eyebrow">NOSSA TESE</p><blockquote>“O ser humano cria a partir do que observa. Tudo o que observa faz parte da natureza. A tecnologia não está fora dela: é uma continuação da capacidade humana de perceber, combinar e transformar.”</blockquote><span>O Instituto Tela Viva transforma essa ideia em aprendizado por presença, processo e descoberta.</span>
        </section>

        <section className="category-section" id="categorias">
          <SectionHeading eyebrow="CAMINHOS DE DESCOBERTA" title="Categorias" />
          <div className="category-grid">{categories.map(([icon, name]) => <button key={name} onClick={() => { setCategory(name); setFiltersOpen(true); document.getElementById('experiencias')?.scrollIntoView() }}><span>{icon}</span><strong>{name}</strong><small>Área de aprendizado</small><i>↗</i></button>)}</div>
        </section>

        <section className="split-sections" id="proximas">
          <div><SectionHeading eyebrow="PROGRAME-SE" title="Próximas aulas" />{catalogLoading ? <CatalogState title="Carregando agenda" description="Buscando aulas cadastradas na fonte oficial." /> : catalogError ? <CatalogState title="Agenda indisponível" description={catalogError} /> : upcoming.length ? <div className="upcoming-list">{upcoming.map((session) => <SessionCard key={session.id} session={session} compact onWatch={() => watchSession(session)} />)}</div> : <EmptyState />}</div>
          <div><SectionHeading eyebrow="EM DESTAQUE" title="Criadores populares" />
            {creators.length ? <div className="creator-list">{creators.map((creator, index) => <article key={creator.name}><span className="rank">{String(index + 1).padStart(2, '0')}</span><Avatar {...creator} large /><div><h3>{creator.name}</h3><p>{creator.role}</p>{creator.followers && <small>{creator.followers}</small>}</div><button aria-label={`Seguir ${creator.name}`} onClick={() => authSession ? setToast(`Solicitação para seguir ${creator.name} enviada.`) : openAuth('login')}>+</button></article>)}</div> : <VerifiedEmptyState label="Nenhum criador verificado foi carregado." />}
          </div>
        </section>

        <section className="new-creators">
          <SectionHeading eyebrow="NOVOS TALENTOS" title="Acabaram de chegar" action="Conhecer todos" />
          {newCreators.length ? <div className="new-grid">{newCreators.map((creator) => <article key={creator.name}><Avatar {...creator} large /><div><h3>{creator.name}</h3><p>{creator.role}</p></div><span>Novo</span></article>)}</div> : <VerifiedEmptyState label="Nenhum novo criador verificado foi carregado." />}
        </section>

        <section className="workspace-section" aria-labelledby="workspace-title">
          <div><p className="eyebrow">FAZER O CONHECIMENTO ACONTECER</p><h2 id="workspace-title">Ferramentas para quem aprende e para quem ensina</h2><p>Biblioteca, estúdio, acompanhamento e operação ficam atrás de sessão autenticada e permissões adequadas. Uma transmissão só aparece em Ao vivo depois que uma aula cadastrada é ativada pelo criador e confirmada pelo backend.</p></div>
          <div className="workspace-actions"><button onClick={openLibrary}>Minha biblioteca</button><button onClick={openCreator}>Painel do criador</button><button onClick={openStudio}>Criar live</button><button onClick={openAdmin}>Administração</button></div>
        </section>
      </main>

      <footer><a className="brand institute-brand-link" href="#inicio"><BrandMark /></a><p>Onde o conhecimento acontece vivo.</p><nav aria-label="Links institucionais"><a href="#experiencias">Experiências</a><a href="#categorias">Categorias</a><button onClick={() => setToast('Política de privacidade ainda não publicada nesta versão.')}>Privacidade</button></nav><span>© 2026 Instituto Tela Viva</span></footer>

      {loginOpen && <div className="modal-backdrop" role="presentation" onMouseDown={() => setLoginOpen(false)}><section className="modal auth-modal" role="dialog" aria-modal="true" aria-labelledby="login-title" onMouseDown={(event) => event.stopPropagation()}><button className="modal-close" onClick={() => setLoginOpen(false)} aria-label="Fechar">×</button><BrandMark symbolOnly className="modal-brand-mark" />
        <div className="auth-tabs" role="tablist" aria-label="Acesso à conta"><button role="tab" aria-selected={authMode === 'login'} onClick={() => { setAuthMode('login'); setAuthError(''); setAuthMessage('') }}>Entrar</button><button role="tab" aria-selected={authMode === 'register'} onClick={() => { setAuthMode('register'); setAuthError(''); setAuthMessage('') }}>Criar conta</button></div>
        <p className="eyebrow">ACESSO PROTEGIDO</p><h2 id="login-title">{authMode === 'login' ? 'Entre para assistir' : authMode === 'register' ? 'Comece seu aprendizado' : 'Recupere seu acesso'}</h2><p>{authMode === 'register' ? 'Sua experiência é adequada à faixa escolhida e pode ser alterada depois.' : authMode === 'recover' ? 'Informe seu e-mail. A resposta não confirma se uma conta existe.' : 'Entre para acompanhar transmissões, participar com segurança e salvar suas aulas.'}</p>
        <form className="auth-form" onSubmit={submitAuth}>
          <label><span>E-mail</span><input type="email" autoComplete="email" required value={authEmail} onChange={(event) => setAuthEmail(event.target.value)} placeholder="voce@exemplo.com" /></label>
          {authMode !== 'recover' && <label><span>Senha</span><input type="password" autoComplete={authMode === 'register' ? 'new-password' : 'current-password'} required minLength={authMode === 'register' ? 12 : 1} maxLength={128} value={authPassword} onChange={(event) => setAuthPassword(event.target.value)} placeholder={authMode === 'register' ? 'Mínimo de 12 caracteres' : 'Sua senha'} /></label>}
          {authMode === 'register' && <><fieldset className="auth-audience"><legend>Área de aprendizado</legend><label><input type="radio" name="auth-audience" checked={authAudience === 'CHILD'} onChange={() => setAuthAudience('CHILD')} /> Criança</label><label><input type="radio" name="auth-audience" checked={authAudience === 'TEEN'} onChange={() => setAuthAudience('TEEN')} /> Adolescente</label><label><input type="radio" name="auth-audience" checked={authAudience === 'ADULT'} onChange={() => setAuthAudience('ADULT')} /> Adulto</label></fieldset>{authAudience === 'CHILD' && <label><span>E-mail do responsável</span><input type="email" required value={guardianEmail} onChange={(event) => setGuardianEmail(event.target.value)} placeholder="responsavel@exemplo.com" /></label>}</>}
          {authError && <p className="auth-error" role="alert">{authError}</p>}
          {authMessage && <p className="auth-success" role="status">{authMessage}</p>}
          <button className="primary full" disabled={authLoading}>{authLoading ? 'Aguarde…' : authMode === 'login' ? 'Entrar na minha conta' : authMode === 'register' ? 'Criar minha conta' : 'Enviar instruções'}</button>
        </form>
        {authMode === 'login' && <button className="text-action" onClick={() => { setAuthMode('recover'); setAuthError(''); setAuthMessage('') }}>Esqueci minha senha</button>}
        {authMode === 'recover' && <button className="text-action" onClick={() => setAuthMode('login')}>← Voltar para entrar</button>}
        <small>Senhas nunca são exibidas. Sessões de homologação ficam isoladas no navegador quando o serviço de autenticação não está conectado.</small>
      </section></div>}

      {toast && <div className="toast" role="status">{toast}</div>}
    </div>
  )
}

function Filter({ label, value, options, onChange }: { label: string; value: string; options: string[]; onChange: (value: string) => void }) {
  return <label><span>{label}</span><select aria-label={label} value={value} onChange={(event) => onChange(event.target.value)}>{options.map((option) => <option key={option}>{option}</option>)}</select></label>
}

function SectionHeading({ eyebrow, title, action }: { eyebrow: string; title: string; action?: string }) {
  return <div className="section-heading"><div><p>{eyebrow}</p><h2>{title}</h2></div>{action && <a href="#experiencias">{action} <span>→</span></a>}</div>
}

function CatalogState({ title, description }: { title: string; description: string }) {
  return <div className="empty-state"><strong>{title}</strong><p>{description}</p></div>
}

function LiveEmptyState() {
  return <div className="empty-state"><strong>Nenhuma aula ao vivo agora</strong><p>Uma aula só aparece aqui depois que o criador inicia a transmissão e o backend confirma o estado ativo.</p></div>
}

function EmptyState() {
  return <div className="empty-state"><strong>Nenhuma aula verificada foi carregada</strong><p>O Tela Viva não preenche o catálogo com dados fictícios. Conteúdo real aparecerá aqui quando vier da fonte oficial.</p></div>
}

function VerifiedEmptyState({ label }: { label: string }) {
  return <div className="empty-state"><strong>{label}</strong><p>Sem dados inventados para preencher a interface.</p></div>
}

function audienceLabel(audience: Audience): string {
  if (audience === 'CHILD') return 'Crianças'
  if (audience === 'TEEN') return 'Adolescentes'
  return 'Adultos'
}

function translateAuthError(message: string): string {
  const normalized = message.toLowerCase()
  if (normalized.includes('invalid credentials')) return 'E-mail ou senha inválidos.'
  if (normalized.includes('already registered')) return 'Este e-mail já possui uma conta.'
  if (normalized.includes('too many requests')) return 'Muitas tentativas. Aguarde um pouco e tente novamente.'
  return message
}
