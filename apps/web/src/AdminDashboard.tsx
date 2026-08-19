import { useMemo, useState } from 'react'
import { BrandMark } from './BrandMark'

type AdminDashboardProps = { onClose: () => void }
type Status = 'Ativo' | 'Pendente' | 'Bloqueado' | 'Em análise'

const sections = [
  ['visao-geral', '▦', 'Visão geral'], ['usuarios', '♙', 'Usuários'],
  ['criadores', '✦', 'Criadores'], ['transmissoes', '◉', 'Transmissões'],
  ['gravacoes', '▻', 'Gravações'], ['pagamentos', 'R$', 'Pagamentos'],
  ['denuncias', '⚑', 'Denúncias'], ['categorias', '◇', 'Categorias'],
  ['comissoes', '%', 'Comissões'], ['auditoria', '≡', 'Auditoria'],
  ['metricas', '⌁', 'Métricas'], ['bloqueios', '⊘', 'Bloqueios'],
  ['moderacao', '✓', 'Moderação'],
]

const queue = [
  { id: 1, kind: 'Denúncia', title: 'Mensagem ofensiva no chat', subject: 'Live: Cerâmica ao vivo', owner: 'Recebida há 8 min', status: 'Em análise' as Status },
  { id: 2, kind: 'Criador', title: 'Validação de perfil profissional', subject: 'Ravi Nunes · Marcenaria', owner: 'Enviada há 2 h', status: 'Pendente' as Status },
  { id: 3, kind: 'Gravação', title: 'Revisão por direitos autorais', subject: 'Mixando vocais em casa', owner: 'Sinalizada ontem', status: 'Pendente' as Status },
  { id: 4, kind: 'Pagamento', title: 'Contestação de pagamento', subject: 'Pedido #TV-4821', owner: 'Aberta em 12 ago', status: 'Em análise' as Status },
]

const recentUsers = [
  { name: 'Ana Ribeiro', email: 'ana@exemplo.com', role: 'Espectadora', joined: 'Hoje, 14:28', status: 'Ativo' as Status },
  { name: 'Ravi Nunes', email: 'ravi@exemplo.com', role: 'Criador', joined: 'Hoje, 11:06', status: 'Pendente' as Status },
  { name: 'João Barro', email: 'joao@exemplo.com', role: 'Criador', joined: '12 ago, 18:40', status: 'Ativo' as Status },
  { name: 'Conta sinalizada', email: 'revisao@exemplo.com', role: 'Espectadora', joined: '11 ago, 09:12', status: 'Bloqueado' as Status },
]

const audit = [
  ['Moderação aplicada', 'admin@telaviva.com', 'Usuário silenciado por 24 horas', 'Agora'],
  ['Categoria atualizada', 'admin@telaviva.com', 'Tecnologia · descrição alterada', 'Hoje, 13:20'],
  ['Comissão ajustada', 'financeiro@telaviva.com', 'Plano padrão · 10%', 'Ontem, 17:45'],
]

export function AdminDashboard({ onClose }: AdminDashboardProps) {
  const [active, setActive] = useState('visao-geral')
  const [query, setQuery] = useState('')
  const [status, setStatus] = useState('Todos')
  const [resolved, setResolved] = useState<number[]>([])

  const filteredQueue = useMemo(() => queue.filter((item) => {
    const term = query.toLocaleLowerCase('pt-BR')
    return !resolved.includes(item.id) && (status === 'Todos' || item.status === status) &&
      [item.kind, item.title, item.subject].some((value) => value.toLocaleLowerCase('pt-BR').includes(term))
  }), [query, resolved, status])

  const navigate = (id: string) => {
    setActive(id)
    document.getElementById(id)?.scrollIntoView()
  }

  return <div className="admin-dashboard">
    <aside className="admin-sidebar">
      <button className="brand brand-button institute-brand-link" onClick={onClose} aria-label="Voltar ao Instituto Tela Viva"><BrandMark /></button>
      <div className="admin-profile"><span>AD</span><div><strong>Administrador</strong><small>Acesso protegido</small></div></div>
      <nav aria-label="Navegação administrativa">
        {sections.map(([id, icon, label]) => <button key={id} className={active === id ? 'active' : ''} onClick={() => navigate(id)}><i>{icon}</i><span>{label}</span></button>)}
      </nav>
      <button className="sidebar-back" onClick={onClose}>← Voltar para o Instituto Tela Viva</button>
    </aside>

    <main className="admin-main" id="visao-geral">
      <header className="admin-topbar"><div><p className="eyebrow">ADMINISTRAÇÃO</p><h1>Visão geral</h1><p>Operação, segurança e saúde da plataforma em um só lugar.</p></div><div className="admin-identity"><span className="health-dot" /> Todos os sistemas operacionais <b>AD</b></div></header>

      <section className="admin-metrics" id="metricas" aria-label="Métricas da plataforma">
        {[['Usuários ativos', '48.290', '+8,4%'], ['Criadores', '1.842', '+36'], ['Ao vivo agora', '24', '3.618 espectadores'], ['Receita no mês', 'R$ 284 mil', '+14,2%']].map(([label, value, detail]) => <article key={label}><p>{label}</p><strong>{value}</strong><small>{detail}</small></article>)}
      </section>

      <section className="admin-card admin-queue" id="moderacao">
        <div className="admin-card-heading"><div><p className="eyebrow">AÇÃO NECESSÁRIA</p><h2>Fila de moderação</h2></div><span>{filteredQueue.length} pendências</span></div>
        <div className="admin-tools"><label><span aria-hidden="true">⌕</span><input aria-label="Buscar na administração" placeholder="Buscar usuário, conteúdo ou pedido" value={query} onChange={(event) => setQuery(event.target.value)} /></label><select aria-label="Filtrar status" value={status} onChange={(event) => setStatus(event.target.value)}><option>Todos</option><option>Pendente</option><option>Em análise</option></select></div>
        <div className="admin-queue-list">{filteredQueue.map((item) => <article key={item.id}><span className={`queue-icon ${item.kind.toLowerCase()}`}>{item.kind === 'Denúncia' ? '⚑' : item.kind === 'Criador' ? '✦' : item.kind === 'Gravação' ? '▻' : 'R$'}</span><div><small>{item.kind}</small><strong>{item.title}</strong><p>{item.subject} · {item.owner}</p></div><span className="status pending">{item.status}</span><button onClick={() => setResolved([...resolved, item.id])} aria-label={`Revisar ${item.title}`}>Revisar</button></article>)}</div>
        {!filteredQueue.length && <div className="admin-empty" role="status">Nenhuma pendência encontrada.</div>}
      </section>

      <div className="admin-columns">
        <section className="admin-card" id="usuarios"><div className="admin-card-heading"><div><p className="eyebrow">COMUNIDADE</p><h2>Usuários recentes</h2></div><button>Ver todos →</button></div><div className="admin-user-list">{recentUsers.map((user) => <article key={user.email}><span className="user-monogram">{user.name.slice(0, 2).toUpperCase()}</span><div><strong>{user.name}</strong><small>{user.email} · {user.role}</small></div><time>{user.joined}</time><span className={`status ${user.status.toLowerCase().replace(' ', '-')}`}>{user.status}</span></article>)}</div></section>
        <section className="admin-card" id="transmissoes"><div className="admin-card-heading"><div><p className="eyebrow">TEMPO REAL</p><h2>Transmissões</h2></div><span className="live-label">● 24 AO VIVO</span></div><div className="admin-live-summary"><strong>3.618</strong><span>espectadores agora</span><div role="img" aria-label="Audiência das transmissões ao vivo">{[28, 42, 38, 62, 48, 71, 66, 88, 73, 95, 82, 100].map((height, index) => <i key={index} style={{ height: `${height}%` }} />)}</div><small>Últimos 60 minutos</small></div></section>
      </div>

      <section className="admin-domain-grid" aria-label="Áreas administrativas">
        {[['criadores', 'Criadores', '18 aguardando verificação', '1.824 ativos'], ['gravacoes', 'Gravações', '7 em processamento', '12.480 disponíveis'], ['pagamentos', 'Pagamentos', 'R$ 18.420 a repassar', '32 contestações'], ['denuncias', 'Denúncias', '14 abertas', '86% resolvidas em 24 h'], ['categorias', 'Categorias', '18 publicadas', '3 rascunhos'], ['comissoes', 'Comissões', '10% taxa padrão', 'R$ 28,4 mil no mês'], ['bloqueios', 'Bloqueios', '42 contas bloqueadas', '8 expiram hoje']].map(([id, title, primary, secondary]) => <article className="admin-card" id={id} key={id}><span>↗</span><h2>{title}</h2><strong>{primary}</strong><p>{secondary}</p><button onClick={() => setActive(id)}>Gerenciar</button></article>)}
      </section>

      <section className="admin-card audit-card" id="auditoria"><div className="admin-card-heading"><div><p className="eyebrow">RASTREABILIDADE</p><h2>Auditoria</h2></div><button>Exportar relatório</button></div>{audit.map(([action, actor, detail, date]) => <article key={action + date}><span>✓</span><div><strong>{action}</strong><p>{detail} · por {actor}</p></div><time>{date}</time></article>)}</section>
    </main>
  </div>
}
