import { FormEvent, useMemo, useState } from 'react'
import { BrandMark } from './BrandMark'

type CreatorDashboardProps = {
  onClose: () => void
  onStartLive: () => void
  creatorLabel?: string
}

type ScheduledClass = {
  id: number
  day: string
  month: string
  title: string
  time: string
  audience: string
  chatEnabled: boolean
  persisted: false
}

const metrics = [
  { label: 'Receita este mês', icon: 'R$' },
  { label: 'Alunos', icon: '◎' },
  { label: 'Seguidores', icon: '♡' },
  { label: 'Vendas', icon: '↗' },
]

const monthNames = ['JAN', 'FEV', 'MAR', 'ABR', 'MAI', 'JUN', 'JUL', 'AGO', 'SET', 'OUT', 'NOV', 'DEZ']

export function CreatorDashboard({ onClose, onStartLive, creatorLabel = 'Criador' }: CreatorDashboardProps) {
  const [period, setPeriod] = useState('30 dias')
  const [priceOpen, setPriceOpen] = useState(false)
  const [classPrice, setClassPrice] = useState('')
  const [subscriptionPrice, setSubscriptionPrice] = useState('')
  const [priceMessage, setPriceMessage] = useState('')
  const [scheduleOpen, setScheduleOpen] = useState(false)
  const [upcomingClasses, setUpcomingClasses] = useState<ScheduledClass[]>([])
  const [scheduledMessage, setScheduledMessage] = useState('')
  const [newClassTitle, setNewClassTitle] = useState('')
  const [newClassDate, setNewClassDate] = useState('')
  const [newClassTime, setNewClassTime] = useState('19:00')
  const [newClassAudience, setNewClassAudience] = useState('Adultos')
  const [newClassChat, setNewClassChat] = useState(true)

  const nextClass = useMemo(() => upcomingClasses[0], [upcomingClasses])
  const initials = creatorLabel.trim().slice(0, 2).toUpperCase() || 'CR'

  const savePrices = () => {
    setPriceMessage('Alteração mantida somente nesta tela. A persistência no backend ainda não foi confirmada.')
    setPriceOpen(false)
  }

  const resetScheduleForm = () => {
    setNewClassTitle('')
    setNewClassDate('')
    setNewClassTime('19:00')
    setNewClassAudience('Adultos')
    setNewClassChat(true)
  }

  const scheduleClass = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!newClassTitle.trim() || !newClassDate || !newClassTime) return

    const parsedDate = new Date(`${newClassDate}T12:00:00`)
    const item: ScheduledClass = {
      id: Date.now(),
      day: String(parsedDate.getDate()).padStart(2, '0'),
      month: monthNames[parsedDate.getMonth()] ?? '',
      title: newClassTitle.trim(),
      time: newClassTime,
      audience: newClassAudience,
      chatEnabled: newClassChat,
      persisted: false,
    }

    setUpcomingClasses((current) => [...current, item])
    setScheduledMessage(`Rascunho local “${item.title}” criado. Ele ainda não foi confirmado pelo backend.`)
    setScheduleOpen(false)
    resetScheduleForm()
  }

  return (
    <div className="creator-dashboard">
      <aside className="creator-sidebar">
        <button className="brand brand-button institute-brand-link" onClick={onClose} aria-label="Voltar ao Instituto Tela Viva"><BrandMark /></button>
        <div className="creator-profile"><span className="dashboard-avatar">{initials}</span><div><strong>{creatorLabel}</strong><small>Conta de criador</small></div></div>
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
          <div><p className="eyebrow">PAINEL DO CRIADOR</p><h1>Olá, {creatorLabel} <span>✦</span></h1><p>Cadastre aulas, acompanhe sua comunidade e transmita ao vivo com chat.</p></div>
          <div className="creator-top-actions">
            <button className="secondary schedule-cta" onClick={() => setScheduleOpen(true)}>＋ Cadastrar aula</button>
            <button className="primary live-cta" aria-label="Iniciar transmissão" onClick={onStartLive}><i /> Transmitir ao vivo</button>
          </div>
        </header>

        <section className="creator-command-center" aria-label="Central de trabalho do criador">
          <article>
            <span className="command-icon">◷</span>
            <div><small>PRÓXIMA AULA</small><strong>{nextClass?.title ?? 'Nenhuma aula verificada carregada'}</strong><p>{nextClass ? `${nextClass.day} ${nextClass.month} · ${nextClass.time} · ${nextClass.audience} · rascunho não persistido` : 'As aulas reais devem ser carregadas do serviço de agenda.'}</p></div>
            <button onClick={() => setScheduleOpen(true)}>Cadastrar</button>
          </article>
          <article>
            <span className="command-icon live">●</span>
            <div><small>TRANSMISSÃO</small><strong>Estúdio ao vivo</strong><p>Câmera, tela, microfone e chat no mesmo fluxo.</p></div>
            <button className="command-live" onClick={onStartLive}>Abrir estúdio</button>
          </article>
        </section>

        {scheduledMessage && <p className="creator-success" role="status">{scheduledMessage}</p>}

        <section className="metric-grid" aria-label="Resumo do desempenho">
          {metrics.map((metric) => <article key={metric.label}><span className="metric-icon">{metric.icon}</span><p>{metric.label}</p><strong>—</strong><small>Sem dados verificados</small></article>)}
        </section>

        <div className="dashboard-grid">
          <section className="dashboard-card revenue-card" id="analytics">
            <div className="dashboard-card-heading"><div><p className="eyebrow">ANALYTICS</p><h2>Receita</h2></div><select aria-label="Período dos analytics" value={period} onChange={(event) => setPeriod(event.target.value)}><option>7 dias</option><option>30 dias</option><option>12 meses</option></select></div>
            <div className="chart-summary"><strong>—</strong><span>Sem dados verificados para {period}</span></div>
            <div className="admin-empty" role="status">O gráfico será exibido quando houver métricas reais carregadas.</div>
          </section>

          <section className="dashboard-card tips-card">
            <div className="dashboard-card-heading"><div><p className="eyebrow">APOIO DA COMUNIDADE</p><h2>Gorjetas</h2></div><span className="tip-heart">♥</span></div>
            <strong>—</strong><p>Sem dados verificados</p>
            <small>Nenhum valor, apoiador ou depoimento será simulado.</small>
          </section>
        </div>

        <section className="dashboard-card classes-card" id="aulas">
          <div className="dashboard-card-heading"><div><p className="eyebrow">SUA AGENDA</p><h2>Aulas</h2></div><button onClick={() => setScheduleOpen(true)}>+ Cadastrar aula</button></div>
          {upcomingClasses.length ? <div className="dashboard-class-list">{upcomingClasses.map((item) => <article key={item.id}><div className="calendar-date"><strong>{item.day}</strong><span>{item.month}</span></div><div className="class-row-copy"><h3>{item.title}</h3><p>{item.time} · inscrições não carregadas · {item.audience}</p><small className="chat-off">Rascunho local · ainda não persistido</small></div><div className="class-row-actions"><button disabled>Transmitir</button><button aria-label={`Opções de ${item.title}`} disabled>•••</button></div></article>)}</div> : <div className="admin-empty" role="status">Nenhuma aula verificada foi carregada.</div>}
        </section>

        <section className="dashboard-card" id="gravacoes">
          <div className="dashboard-card-heading"><div><p className="eyebrow">CONTEÚDO SOB DEMANDA</p><h2>Gravações</h2></div><button disabled>Ver todas →</button></div>
          <div className="admin-empty" role="status">Nenhuma gravação verificada foi carregada.</div>
        </section>

        <section className="audience-row" id="publico">
          <article className="dashboard-card"><p className="eyebrow">COMUNIDADE</p><h2>Seus alunos</h2><strong>—</strong><p>Sem dados verificados</p><button disabled>Ver alunos →</button></article>
          <article className="dashboard-card"><p className="eyebrow">ALCANCE</p><h2>Seguidores</h2><strong>—</strong><p>Sem dados verificados</p><button disabled>Ver seguidores →</button></article>
          <article className="dashboard-card"><p className="eyebrow">CONVERSÃO</p><h2>Vendas</h2><strong>—</strong><p>Sem dados verificados</p><button disabled>Ver produtos →</button></article>
        </section>

        <section className="dashboard-card finance-card" id="financeiro">
          <div className="dashboard-card-heading"><div><p className="eyebrow">FINANCEIRO</p><h2>Histórico financeiro</h2></div><button disabled>Ver extrato completo →</button></div>
          <div className="balance-strip"><div><span>Saldo disponível</span><strong>—</strong></div><button className="primary" disabled>Solicitar saque</button></div>
          <div className="admin-empty" role="status">Nenhuma transação verificada foi carregada.</div>
        </section>

        <section className="dashboard-card" id="precos">
          <div className="dashboard-card-heading"><div><p className="eyebrow">MONETIZAÇÃO</p><h2>Configuração de preços</h2></div></div>
          {priceMessage && <p className="creator-success" role="status">{priceMessage}</p>}
          <div className="price-summary"><div><span>Aula avulsa</span><strong>{classPrice ? `R$ ${classPrice}` : 'Não configurado'}</strong></div><div><span>Assinatura mensal</span><strong>{subscriptionPrice ? `R$ ${subscriptionPrice}` : 'Não configurado'}</strong></div><button className="secondary" onClick={() => setPriceOpen(true)}>Configurar preços</button></div>
        </section>
      </main>

      {scheduleOpen && <div className="dashboard-modal-backdrop" role="presentation"><form className="dashboard-modal schedule-modal" onSubmit={scheduleClass} aria-label="Cadastrar aula"><button type="button" className="dashboard-modal-close" onClick={() => setScheduleOpen(false)} aria-label="Fechar">×</button><p className="eyebrow">NOVA EXPERIÊNCIA</p><h2>Cadastrar aula</h2><p>Enquanto a persistência da agenda não estiver ligada a este formulário, os dados abaixo serão mantidos apenas como rascunho local.</p><label>Título<input required value={newClassTitle} onChange={(event) => setNewClassTitle(event.target.value)} placeholder="Ex.: Desenho de observação ao vivo" /></label><div className="schedule-form-row"><label>Data<input required type="date" value={newClassDate} onChange={(event) => setNewClassDate(event.target.value)} /></label><label>Horário<input required type="time" value={newClassTime} onChange={(event) => setNewClassTime(event.target.value)} /></label></div><label>Público<select value={newClassAudience} onChange={(event) => setNewClassAudience(event.target.value)}><option>Crianças</option><option>Adolescentes</option><option>Adultos</option><option>Adolescentes e adultos</option></select></label><label className="schedule-toggle"><input type="checkbox" checked={newClassChat} onChange={(event) => setNewClassChat(event.target.checked)} /><span><strong>Chat ao vivo</strong><small>Preferência do rascunho; a configuração só será efetiva após persistência.</small></span></label><div className="dashboard-modal-actions"><button type="button" className="secondary" onClick={() => setScheduleOpen(false)}>Cancelar</button><button type="submit" className="primary">Criar rascunho local</button></div></form></div>}

      {priceOpen && <div className="dashboard-modal-backdrop" role="presentation"><div className="dashboard-modal" role="dialog" aria-modal="true" aria-labelledby="price-title"><button className="dashboard-modal-close" onClick={() => setPriceOpen(false)} aria-label="Fechar">×</button><p className="eyebrow">PREÇOS</p><h2 id="price-title">Configurar monetização</h2><p>Os valores só serão considerados efetivos depois que o backend confirmar a persistência.</p><label>Valor da aula (R$)<input value={classPrice} onChange={(event) => setClassPrice(event.target.value)} /></label><label>Assinatura mensal (R$)<input value={subscriptionPrice} onChange={(event) => setSubscriptionPrice(event.target.value)} /></label><div className="dashboard-modal-actions"><button className="secondary" onClick={() => setPriceOpen(false)}>Cancelar</button><button className="primary" onClick={savePrices}>Manter nesta tela</button></div></div></div>}
    </div>
  )
}
