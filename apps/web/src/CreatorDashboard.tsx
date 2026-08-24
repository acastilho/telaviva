import { FormEvent, useEffect, useMemo, useState } from 'react'
import { BrandMark } from './BrandMark'
import { schedulingClient, type ScheduledStream } from './scheduling'

type CreatorDashboardProps = {
  onClose: () => void
  onStartLive: (streamId?: string) => void
  accessToken?: string
  creatorId?: string
  remoteApi?: boolean
}

type ScheduledClass = {
  id: string
  day: string
  month: string
  title: string
  time: string
  students: number
  audience: string
  chatEnabled: boolean
}

const metrics = [
  { label: 'Receita este mês', value: 'R$ 8.420', change: '+18%', icon: 'R$' },
  { label: 'Alunos', value: '1.284', change: '+84', icon: '◎' },
  { label: 'Seguidores', value: '24,8 mil', change: '+6,2%', icon: '♡' },
  { label: 'Vendas', value: '196', change: '+12%', icon: '↗' },
]

const initialUpcomingClasses: ScheduledClass[] = [
  { id: 'demo-1', day: '18', month: 'AGO', title: 'Direção de arte para marcas reais', time: '19:00', students: 128, audience: 'Adultos', chatEnabled: true },
  { id: 'demo-2', day: '22', month: 'AGO', title: 'Figma: componentes que escalam', time: '18:30', students: 96, audience: 'Adolescentes e adultos', chatEnabled: true },
  { id: 'demo-3', day: '29', month: 'AGO', title: 'Como apresentar um projeto criativo', time: '20:00', students: 74, audience: 'Adultos', chatEnabled: true },
]

const recordings = [
  { title: 'Identidade visual do zero', views: '3.842', duration: '1h 24min', accent: 'coral' },
  { title: 'Portfólio que conta uma história', views: '2.116', duration: '58min', accent: 'violet' },
  { title: 'Tipografia na prática', views: '1.908', duration: '1h 12min', accent: 'blue' },
]

const transactions = [
  { label: 'Venda · Identidade visual do zero', date: 'Hoje, 14:32', value: '+ R$ 89,00', kind: 'Venda' },
  { label: 'Gorjeta de Ana Ribeiro', date: 'Hoje, 11:08', value: '+ R$ 25,00', kind: 'Gorjeta' },
  { label: 'Venda · Assinatura mensal', date: 'Ontem, 20:16', value: '+ R$ 39,00', kind: 'Assinatura' },
  { label: 'Saque processado', date: '12 ago, 09:10', value: '− R$ 1.500,00', kind: 'Saque' },
]

const monthNames = ['JAN', 'FEV', 'MAR', 'ABR', 'MAI', 'JUN', 'JUL', 'AGO', 'SET', 'OUT', 'NOV', 'DEZ']
const EDUCATION_CATEGORY_ID = '00000000-0000-4000-8000-000000000015'

function toScheduledClass(stream: ScheduledStream): ScheduledClass {
  const startsAt = new Date(stream.starts_at)
  return {
    id: stream.id,
    day: String(startsAt.getDate()).padStart(2, '0'),
    month: monthNames[startsAt.getMonth()] ?? '',
    title: stream.title,
    time: startsAt.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }),
    students: 0,
    audience: 'Adultos',
    chatEnabled: true,
  }
}

export function CreatorDashboard({ onClose, onStartLive, accessToken, creatorId, remoteApi = false }: CreatorDashboardProps) {
  const [period, setPeriod] = useState('30 dias')
  const [priceOpen, setPriceOpen] = useState(false)
  const [classPrice, setClassPrice] = useState('89,00')
  const [subscriptionPrice, setSubscriptionPrice] = useState('39,00')
  const [saved, setSaved] = useState(false)
  const [scheduleOpen, setScheduleOpen] = useState(false)
  const [upcomingClasses, setUpcomingClasses] = useState<ScheduledClass[]>(remoteApi ? [] : initialUpcomingClasses)
  const [scheduledMessage, setScheduledMessage] = useState('')
  const [scheduleError, setScheduleError] = useState('')
  const [scheduleLoading, setScheduleLoading] = useState(false)
  const [newClassTitle, setNewClassTitle] = useState('')
  const [newClassDate, setNewClassDate] = useState('')
  const [newClassTime, setNewClassTime] = useState('19:00')
  const [newClassAudience, setNewClassAudience] = useState('Adultos')
  const [newClassChat, setNewClassChat] = useState(true)

  useEffect(() => {
    if (!remoteApi || !creatorId) return
    let mounted = true
    setScheduleLoading(true)
    schedulingClient.listUpcoming(creatorId)
      .then((streams) => {
        if (!mounted) return
        setUpcomingClasses(streams.map(toScheduledClass))
        setScheduleError('')
      })
      .catch((error) => {
        if (mounted) setScheduleError(error instanceof Error ? error.message : 'Não foi possível carregar as aulas cadastradas.')
      })
      .finally(() => {
        if (mounted) setScheduleLoading(false)
      })
    return () => { mounted = false }
  }, [creatorId, remoteApi])

  const nextClass = useMemo(() => upcomingClasses[0], [upcomingClasses])

  const savePrices = () => {
    setSaved(true)
    setPriceOpen(false)
  }

  const resetScheduleForm = () => {
    setNewClassTitle('')
    setNewClassDate('')
    setNewClassTime('19:00')
    setNewClassAudience('Adultos')
    setNewClassChat(true)
  }

  const scheduleClass = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!newClassTitle.trim() || !newClassDate || !newClassTime) return
    setScheduleError('')
    setScheduleLoading(true)

    try {
      let item: ScheduledClass
      if (remoteApi) {
        if (!accessToken || !creatorId) throw new Error('Sessão de criador inválida. Entre novamente.')
        const startsAt = new Date(`${newClassDate}T${newClassTime}:00`)
        if (Number.isNaN(startsAt.getTime())) throw new Error('Data ou horário inválido.')
        const created = await schedulingClient.create({
          title: newClassTitle.trim(),
          description: `Aula cadastrada no painel do Instituto Tela Viva. Público: ${newClassAudience}. Chat: ${newClassChat ? 'habilitado' : 'desabilitado'}.`,
          objective: `Acompanhar ${newClassTitle.trim()} em uma experiência de aprendizado ao vivo.`,
          starts_at: startsAt.toISOString(),
          estimated_duration_minutes: 60,
          category_id: EDUCATION_CATEGORY_ID,
          level: 'ALL_LEVELS',
          price: '0',
          access_type: 'FREE',
        }, accessToken)
        item = { ...toScheduledClass(created), audience: newClassAudience, chatEnabled: newClassChat }
        setUpcomingClasses((current) => [...current, item].sort((a, b) => `${a.month}${a.day}${a.time}`.localeCompare(`${b.month}${b.day}${b.time}`)))
      } else {
        const parsedDate = new Date(`${newClassDate}T12:00:00`)
        item = {
          id: `local-${Date.now()}`,
          day: String(parsedDate.getDate()).padStart(2, '0'),
          month: monthNames[parsedDate.getMonth()] ?? '',
          title: newClassTitle.trim(),
          time: newClassTime,
          students: 0,
          audience: newClassAudience,
          chatEnabled: newClassChat,
        }
        setUpcomingClasses((current) => [...current, item])
      }

      setScheduledMessage(`Aula “${item.title}” cadastrada. Ela só aparecerá em Ao vivo depois que você iniciar a transmissão.`)
      setScheduleOpen(false)
      resetScheduleForm()
    } catch (error) {
      setScheduleError(error instanceof Error ? error.message : 'Não foi possível cadastrar a aula.')
    } finally {
      setScheduleLoading(false)
    }
  }

  const startNextClass = () => {
    if (!nextClass) {
      setScheduleOpen(true)
      setScheduleError('Cadastre uma aula antes de abrir o estúdio.')
      return
    }
    onStartLive(remoteApi ? nextClass.id : undefined)
  }

  return (
    <div className="creator-dashboard">
      <aside className="creator-sidebar">
        <button className="brand brand-button institute-brand-link" onClick={onClose} aria-label="Voltar ao Instituto Tela Viva"><BrandMark /></button>
        <div className="creator-profile"><span className="dashboard-avatar">ML</span><div><strong>Marina Luz</strong><small>Conta de criador</small></div></div>
        <nav aria-label="Navegação do painel">
          <a className="active" href="#visao-geral">▦ <span>Visão geral</span></a>
          <a href="#aulas">◷ <span>Aulas</span></a>
          <a href="#gravacoes">▻ <span>Gravações</span></a>
          <a href="#publico">♙ <span>Alunos e seguidores</span></a>
          <a href="#analytics">⌁ <span>Analytics</span></a>
          <a href="#financeiro">R$ <span>Financeiro</span></a>
        </nav>
        <button className="sidebar-back" onClick={onClose}>← Voltar para o Instituto Tela Viva</button>
      </aside>

      <main className="creator-main" id="visao-geral">
        <header className="creator-topbar">
          <div><p className="eyebrow">PAINEL DO CRIADOR</p><h1>Olá, Marina <span>✦</span></h1><p>Cadastre aulas, acompanhe sua comunidade e transmita ao vivo com chat.</p></div>
          <div className="creator-top-actions">
            <button className="secondary schedule-cta" onClick={() => setScheduleOpen(true)}>＋ Cadastrar aula</button>
            <button className="primary live-cta" aria-label="Iniciar transmissão" onClick={startNextClass}><i /> Transmitir ao vivo</button>
          </div>
        </header>

        <section className="creator-command-center" aria-label="Central de trabalho do criador">
          <article>
            <span className="command-icon">◷</span>
            <div><small>PRÓXIMA AULA</small><strong>{scheduleLoading ? 'Carregando aulas…' : nextClass?.title ?? 'Nenhuma aula cadastrada'}</strong><p>{nextClass ? `${nextClass.day} ${nextClass.month} · ${nextClass.time} · ${nextClass.audience}` : 'Cadastre uma aula para começar.'}</p></div>
            <button onClick={() => setScheduleOpen(true)}>Cadastrar</button>
          </article>
          <article>
            <span className="command-icon live">●</span>
            <div><small>TRANSMISSÃO</small><strong>Estúdio ao vivo</strong><p>O estúdio só entra ao vivo quando estiver associado a uma aula cadastrada.</p></div>
            <button className="command-live" onClick={startNextClass}>Abrir estúdio</button>
          </article>
        </section>

        {scheduledMessage && <p className="creator-success" role="status">✓ {scheduledMessage}</p>}
        {scheduleError && <p className="auth-error" role="alert">{scheduleError}</p>}

        <section className="metric-grid" aria-label="Resumo do desempenho">
          {metrics.map((metric) => <article key={metric.label}><span className="metric-icon">{metric.icon}</span><p>{metric.label}</p><strong>{metric.value}</strong><small>{metric.change} <i>no período</i></small></article>)}
        </section>

        <div className="dashboard-grid">
          <section className="dashboard-card revenue-card" id="analytics">
            <div className="dashboard-card-heading"><div><p className="eyebrow">ANALYTICS</p><h2>Receita</h2></div><select aria-label="Período dos analytics" value={period} onChange={(event) => setPeriod(event.target.value)}><option>7 dias</option><option>30 dias</option><option>12 meses</option></select></div>
            <div className="chart-summary"><strong>R$ 8.420</strong><span>↗ 18% vs. período anterior</span></div>
            <div className="bar-chart" role="img" aria-label={`Gráfico de receita dos últimos ${period}`}>
              {[42, 55, 38, 72, 62, 84, 68, 91, 76, 88, 71, 100].map((height, index) => <i key={index} style={{ height: `${height}%` }} />)}
            </div>
            <div className="chart-labels"><span>1 ago</span><span>15 ago</span><span>Hoje</span></div>
          </section>

          <section className="dashboard-card tips-card">
            <div className="dashboard-card-heading"><div><p className="eyebrow">APOIO DA COMUNIDADE</p><h2>Gorjetas</h2></div><span className="tip-heart">♥</span></div>
            <strong>R$ 1.280</strong><p>recebidos neste mês</p>
            <div><span>42 apoiadores</span><span>Média de R$ 30,48</span></div>
            <small>“Sua aula mudou a forma como apresento meus projetos!”</small>
          </section>
        </div>

        <section className="dashboard-card classes-card" id="aulas">
          <div className="dashboard-card-heading"><div><p className="eyebrow">SUA AGENDA</p><h2>Aulas cadastradas</h2></div><button onClick={() => setScheduleOpen(true)}>+ Cadastrar aula</button></div>
          <div className="dashboard-class-list">{upcomingClasses.map((item) => <article key={item.id}><div className="calendar-date"><strong>{item.day}</strong><span>{item.month}</span></div><div className="class-row-copy"><h3>{item.title}</h3><p>{item.time} · {item.students} alunos inscritos · {item.audience}</p><small className={item.chatEnabled ? 'chat-on' : 'chat-off'}>{item.chatEnabled ? '☵ Chat ao vivo habilitado' : '⊘ Chat desabilitado'}</small></div><div className="class-row-actions"><button onClick={() => onStartLive(remoteApi ? item.id : undefined)}>Transmitir</button><button aria-label={`Opções de ${item.title}`}>•••</button></div></article>)}</div>
          {!scheduleLoading && upcomingClasses.length === 0 && <p className="message-empty">Nenhuma aula cadastrada. Cadastre uma aula antes de transmitir.</p>}
        </section>

        <section className="dashboard-card" id="gravacoes">
          <div className="dashboard-card-heading"><div><p className="eyebrow">CONTEÚDO SOB DEMANDA</p><h2>Gravações</h2></div><button>Ver todas →</button></div>
          <div className="dashboard-recordings">{recordings.map((recording) => <article key={recording.title}><div className={`recording-thumb ${recording.accent}`}><span>▶</span><small>{recording.duration}</small></div><h3>{recording.title}</h3><p>◉ {recording.views} visualizações</p></article>)}</div>
        </section>

        <section className="audience-row" id="publico">
          <article className="dashboard-card"><p className="eyebrow">COMUNIDADE</p><h2>Seus alunos</h2><strong>1.284</strong><p>84 novos neste mês</p><button>Ver alunos →</button></article>
          <article className="dashboard-card"><p className="eyebrow">ALCANCE</p><h2>Seguidores</h2><strong>24,8 mil</strong><p>1.460 novos neste mês</p><button>Ver seguidores →</button></article>
          <article className="dashboard-card"><p className="eyebrow">CONVERSÃO</p><h2>Vendas</h2><strong>196</strong><p>15,3% dos visitantes</p><button>Ver produtos →</button></article>
        </section>

        <section className="dashboard-card finance-card" id="financeiro">
          <div className="dashboard-card-heading"><div><p className="eyebrow">FINANCEIRO</p><h2>Histórico financeiro</h2></div><button>Ver extrato completo →</button></div>
          <div className="balance-strip"><div><span>Saldo disponível</span><strong>R$ 6.735,40</strong></div><button className="primary">Solicitar saque</button></div>
          <div className="transaction-list">{transactions.map((item) => <article key={`${item.label}-${item.date}`}><div><strong>{item.label}</strong><span>{item.date}</span></div><span>{item.kind}</span><strong>{item.value}</strong></article>)}</div>
        </section>

        <section className="dashboard-card" id="precos">
          <div className="dashboard-card-heading"><div><p className="eyebrow">MONETIZAÇÃO</p><h2>Configuração de preços</h2></div>{saved && <span className="saved-pill">✓ Salvo</span>}</div>
          <div className="price-summary"><div><span>Aula avulsa</span><strong>R$ {classPrice}</strong></div><div><span>Assinatura mensal</span><strong>R$ {subscriptionPrice}</strong></div><button className="secondary" onClick={() => setPriceOpen(true)}>Configurar preços</button></div>
        </section>
      </main>

      {scheduleOpen && <div className="dashboard-modal-backdrop" role="presentation"><form className="dashboard-modal schedule-modal" onSubmit={(event) => void scheduleClass(event)} aria-label="Cadastrar aula"><button type="button" className="dashboard-modal-close" onClick={() => setScheduleOpen(false)} aria-label="Fechar">×</button><p className="eyebrow">NOVA EXPERIÊNCIA</p><h2>Cadastrar aula</h2><label>Título<input required value={newClassTitle} onChange={(event) => setNewClassTitle(event.target.value)} placeholder="Ex.: Desenho de observação ao vivo" /></label><div className="schedule-form-row"><label>Data<input required type="date" value={newClassDate} onChange={(event) => setNewClassDate(event.target.value)} /></label><label>Horário<input required type="time" value={newClassTime} onChange={(event) => setNewClassTime(event.target.value)} /></label></div><label>Público<select value={newClassAudience} onChange={(event) => setNewClassAudience(event.target.value)}><option>Crianças</option><option>Adolescentes</option><option>Adultos</option><option>Adolescentes e adultos</option></select></label><label className="schedule-toggle"><input type="checkbox" checked={newClassChat} onChange={(event) => setNewClassChat(event.target.checked)} /><span><strong>Chat ao vivo</strong><small>Permite conversa moderada durante a transmissão.</small></span></label>{scheduleError && <p className="auth-error" role="alert">{scheduleError}</p>}<div className="dashboard-modal-actions"><button type="button" className="secondary" onClick={() => setScheduleOpen(false)}>Cancelar</button><button type="submit" className="primary" disabled={scheduleLoading}>{scheduleLoading ? 'Cadastrando…' : 'Cadastrar aula'}</button></div></form></div>}

      {priceOpen && <div className="dashboard-modal-backdrop" role="presentation"><div className="dashboard-modal" role="dialog" aria-modal="true" aria-labelledby="price-title"><button className="dashboard-modal-close" onClick={() => setPriceOpen(false)} aria-label="Fechar">×</button><p className="eyebrow">PREÇOS</p><h2 id="price-title">Configurar monetização</h2><label>Valor da aula (R$)<input value={classPrice} onChange={(event) => setClassPrice(event.target.value)} /></label><label>Assinatura mensal (R$)<input value={subscriptionPrice} onChange={(event) => setSubscriptionPrice(event.target.value)} /></label><div className="dashboard-modal-actions"><button className="secondary" onClick={() => setPriceOpen(false)}>Cancelar</button><button className="primary" onClick={savePrices}>Salvar preços</button></div></div></div>}
    </div>
  )
}
