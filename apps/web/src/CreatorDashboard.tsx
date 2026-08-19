import { useState } from 'react'
import { BrandMark } from './BrandMark'

type CreatorDashboardProps = {
  onClose: () => void
  onStartLive: () => void
}

const metrics = [
  { label: 'Receita este mês', value: 'R$ 8.420', change: '+18%', icon: 'R$' },
  { label: 'Alunos', value: '1.284', change: '+84', icon: '◎' },
  { label: 'Seguidores', value: '24,8 mil', change: '+6,2%', icon: '♡' },
  { label: 'Vendas', value: '196', change: '+12%', icon: '↗' },
]

const upcomingClasses = [
  { day: '18', month: 'AGO', title: 'Direção de arte para marcas reais', time: '19:00', students: 128 },
  { day: '22', month: 'AGO', title: 'Figma: componentes que escalam', time: '18:30', students: 96 },
  { day: '29', month: 'AGO', title: 'Como apresentar um projeto criativo', time: '20:00', students: 74 },
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

export function CreatorDashboard({ onClose, onStartLive }: CreatorDashboardProps) {
  const [period, setPeriod] = useState('30 dias')
  const [priceOpen, setPriceOpen] = useState(false)
  const [classPrice, setClassPrice] = useState('89,00')
  const [subscriptionPrice, setSubscriptionPrice] = useState('39,00')
  const [saved, setSaved] = useState(false)

  const savePrices = () => {
    setSaved(true)
    setPriceOpen(false)
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
          <div><p className="eyebrow">PAINEL DO CRIADOR</p><h1>Olá, Marina <span>✦</span></h1><p>Acompanhe sua comunidade e faça seu trabalho crescer.</p></div>
          <button className="primary live-cta" onClick={onStartLive}><i /> Iniciar transmissão</button>
        </header>

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
          <div className="dashboard-card-heading"><div><p className="eyebrow">SUA AGENDA</p><h2>Próximas aulas</h2></div><button>+ Agendar aula</button></div>
          <div className="dashboard-class-list">{upcomingClasses.map((item) => <article key={item.title}><div className="calendar-date"><strong>{item.day}</strong><span>{item.month}</span></div><div><h3>{item.title}</h3><p>{item.time} · {item.students} alunos inscritos</p></div><button aria-label={`Opções de ${item.title}`}>•••</button></article>)}</div>
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
          <div className="transaction-list">{transactions.map((transaction) => <article key={transaction.label}><span className={`transaction-icon ${transaction.kind.toLowerCase()}`}>{transaction.kind === 'Saque' ? '↓' : '↑'}</span><div><strong>{transaction.label}</strong><small>{transaction.date} · {transaction.kind}</small></div><b className={transaction.kind === 'Saque' ? 'negative' : ''}>{transaction.value}</b></article>)}</div>
        </section>

        <section className="dashboard-card price-card">
          <div><p className="eyebrow">MONETIZAÇÃO</p><h2>Configuração de preços</h2><p>Defina o valor das aulas avulsas e da sua assinatura.</p>{saved && <small role="status">Preços atualizados com sucesso.</small>}</div>
          <button className="secondary" onClick={() => setPriceOpen(true)}>Configurar preços</button>
        </section>
      </main>

      {priceOpen && <div className="modal-backdrop" role="presentation" onMouseDown={() => setPriceOpen(false)}><section className="modal price-modal" role="dialog" aria-modal="true" aria-labelledby="price-title" onMouseDown={(event) => event.stopPropagation()}><button className="modal-close" onClick={() => setPriceOpen(false)} aria-label="Fechar">×</button><p className="eyebrow">MONETIZAÇÃO</p><h2 id="price-title">Configurar preços</h2><label>Preço padrão da aula (R$)<input aria-label="Preço padrão da aula" value={classPrice} onChange={(event) => setClassPrice(event.target.value)} /></label><label>Assinatura mensal (R$)<input aria-label="Assinatura mensal" value={subscriptionPrice} onChange={(event) => setSubscriptionPrice(event.target.value)} /></label><button className="primary full" onClick={savePrices}>Salvar preços</button></section></div>}
    </div>
  )
}
