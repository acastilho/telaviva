import { useState } from 'react'
import { BrandMark } from './BrandMark'

type AdminDashboardProps = { onClose: () => void }

const sections = [
  ['visao-geral', '▦', 'Visão geral'], ['usuarios', '♙', 'Usuários'],
  ['criadores', '✦', 'Criadores'], ['transmissoes', '◉', 'Transmissões'],
  ['gravacoes', '▻', 'Gravações'], ['pagamentos', 'R$', 'Pagamentos'],
  ['denuncias', '⚑', 'Denúncias'], ['categorias', '◇', 'Categorias'],
  ['comissoes', '%', 'Comissões'], ['auditoria', '≡', 'Auditoria'],
  ['metricas', '⌁', 'Métricas'], ['bloqueios', '⊘', 'Bloqueios'],
  ['moderacao', '✓', 'Moderação'],
]

const metrics = [
  ['Usuários ativos', 'Sem dados verificados'],
  ['Criadores', 'Sem dados verificados'],
  ['Ao vivo agora', 'Sem dados verificados'],
  ['Receita no mês', 'Sem dados verificados'],
]

const domains = [
  ['criadores', 'Criadores'],
  ['gravacoes', 'Gravações'],
  ['pagamentos', 'Pagamentos'],
  ['denuncias', 'Denúncias'],
  ['categorias', 'Categorias'],
  ['comissoes', 'Comissões'],
  ['bloqueios', 'Bloqueios'],
]

export function AdminDashboard({ onClose }: AdminDashboardProps) {
  const [active, setActive] = useState('visao-geral')

  const navigate = (id: string) => {
    setActive(id)
    document.getElementById(id)?.scrollIntoView()
  }

  return <div className="admin-dashboard">
    <aside className="admin-sidebar">
      <button className="brand brand-button institute-brand-link" onClick={onClose} aria-label="Voltar ao início"><BrandMark /></button>
      <div className="admin-profile"><span>AD</span><div><strong>Área administrativa</strong><small>Acesso protegido</small></div></div>
      <nav aria-label="Navegação administrativa">
        {sections.map(([id, icon, label]) => <button key={id} className={active === id ? 'active' : ''} onClick={() => navigate(id)}><i aria-hidden="true">{icon}</i><span>{label}</span></button>)}
      </nav>
      <button className="sidebar-back" onClick={onClose}>← Voltar para o Instituto Tela Viva</button>
    </aside>

    <main className="admin-main" id="visao-geral">
      <header className="admin-topbar"><div><p className="eyebrow">ADMINISTRAÇÃO</p><h1>Visão geral</h1><p>Operação, segurança e saúde da plataforma em um só lugar.</p></div><div className="admin-identity"><span className="health-dot" /> Dados operacionais não carregados <b>AD</b></div></header>

      <section className="admin-metrics" id="metricas" aria-label="Métricas da plataforma">
        {metrics.map(([label, detail]) => <article key={label}><p>{label}</p><strong>—</strong><small>{detail}</small></article>)}
      </section>

      <section className="admin-card admin-queue" id="moderacao">
        <div className="admin-card-heading"><div><p className="eyebrow">AÇÃO NECESSÁRIA</p><h2>Fila de moderação</h2></div><span>Dados não carregados</span></div>
        <div className="admin-tools"><label><span aria-hidden="true">⌕</span><input aria-label="Buscar na administração" placeholder="Buscar usuário, conteúdo ou pedido" disabled /></label><select aria-label="Filtrar status" disabled><option>Todos</option></select></div>
        <div className="admin-empty" role="status"><strong>Nenhuma informação de moderação foi carregada.</strong><p>Esta tela só exibirá denúncias e pendências confirmadas pela fonte administrativa.</p></div>
      </section>

      <div className="admin-columns">
        <section className="admin-card" id="usuarios"><div className="admin-card-heading"><div><p className="eyebrow">COMUNIDADE</p><h2>Usuários recentes</h2></div><button disabled>Ver todos →</button></div><div className="admin-empty" role="status">Nenhum usuário verificado foi carregado nesta tela.</div></section>
        <section className="admin-card" id="transmissoes"><div className="admin-card-heading"><div><p className="eyebrow">TEMPO REAL</p><h2>Transmissões</h2></div><span>Dados não carregados</span></div><div className="admin-live-summary"><strong>—</strong><span>audiência não disponível</span><small>Aguardando fonte real de telemetria.</small></div></section>
      </div>

      <section className="admin-domain-grid" aria-label="Áreas administrativas">
        {domains.map(([id, title]) => <article className="admin-card" id={id} key={id}><span>↗</span><h2>{title}</h2><strong>Dados não carregados</strong><p>Nenhum valor operacional será simulado.</p><button disabled>Gerenciar</button></article>)}
      </section>

      <section className="admin-card audit-card" id="auditoria"><div className="admin-card-heading"><div><p className="eyebrow">RASTREABILIDADE</p><h2>Auditoria</h2></div><button disabled>Exportar relatório</button></div><div className="admin-empty" role="status">Nenhum evento de auditoria verificado foi carregado.</div></section>
    </main>
  </div>
}
