import { useEffect, useMemo, useState } from 'react'
import { adminClient } from './adminClient'
import type { AuthUser, Role } from './auth'
import { BrandMark } from './BrandMark'

type AdminDashboardProps = { onClose: () => void; accessToken?: string }

const sections = [
  ['visao-geral', '▦', 'Visão geral'], ['usuarios', '♙', 'Usuários'],
  ['criadores', '✦', 'Criadores'], ['transmissoes', '◉', 'Transmissões'],
  ['gravacoes', '▻', 'Gravações'], ['pagamentos', 'R$', 'Pagamentos'],
  ['denuncias', '⚑', 'Denúncias'], ['categorias', '◇', 'Categorias'],
  ['comissoes', '%', 'Comissões'], ['auditoria', '≡', 'Auditoria'],
  ['metricas', '⌁', 'Métricas'], ['bloqueios', '⊘', 'Bloqueios'],
  ['moderacao', '✓', 'Moderação'],
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

const roleLabels: Record<Role, string> = {
  VIEWER: 'Aluno / espectador',
  CREATOR: 'Criador',
  ADMIN: 'Administrador',
}

export function AdminDashboard({ onClose, accessToken }: AdminDashboardProps) {
  const [active, setActive] = useState('visao-geral')
  const [users, setUsers] = useState<AuthUser[]>([])
  const [usersLoading, setUsersLoading] = useState(true)
  const [usersError, setUsersError] = useState('')
  const [pendingUserId, setPendingUserId] = useState<string | null>(null)
  const [usersMessage, setUsersMessage] = useState('')
  const adminToken = useMemo(() => accessToken || adminClient.currentAccessToken(), [accessToken])

  const navigate = (id: string) => {
    setActive(id)
    document.getElementById(id)?.scrollIntoView()
  }

  useEffect(() => {
    let mounted = true
    if (!adminToken || !adminClient.usesRemoteApi) {
      setUsersLoading(false)
      setUsersError('A sessão administrativa ou a API não está disponível.')
      return () => { mounted = false }
    }

    adminClient.listUsers(adminToken)
      .then((items) => {
        if (!mounted) return
        setUsers(items)
        setUsersError('')
      })
      .catch((error) => {
        if (mounted) setUsersError(error instanceof Error ? error.message : 'Não foi possível carregar os usuários.')
      })
      .finally(() => {
        if (mounted) setUsersLoading(false)
      })

    return () => { mounted = false }
  }, [adminToken])

  const changeRole = async (user: AuthUser, role: Role) => {
    if (!adminToken || role === user.role) return
    setPendingUserId(user.id)
    setUsersError('')
    setUsersMessage('')
    try {
      const updated = await adminClient.updateUserRole(user.id, role, adminToken)
      setUsers((current) => current.map((item) => item.id === updated.id ? updated : item))
      setUsersMessage(`${updated.email} agora possui o perfil ${roleLabels[updated.role]}. Sessões anteriores foram revogadas.`)
    } catch (error) {
      setUsersError(error instanceof Error ? error.message : 'Não foi possível alterar o perfil do usuário.')
    } finally {
      setPendingUserId(null)
    }
  }

  const creatorCount = users.filter((user) => user.role === 'CREATOR').length
  const adminCount = users.filter((user) => user.role === 'ADMIN').length
  const metrics = [
    ['Usuários cadastrados', usersLoading ? 'Carregando…' : String(users.length)],
    ['Criadores', usersLoading ? 'Carregando…' : String(creatorCount)],
    ['Administradores', usersLoading ? 'Carregando…' : String(adminCount)],
    ['Ao vivo agora', 'Fonte de telemetria pendente'],
  ]

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
      <header className="admin-topbar"><div><p className="eyebrow">ADMINISTRAÇÃO</p><h1>Visão geral</h1><p>Operação, segurança e saúde da plataforma em um só lugar.</p></div><div className="admin-identity"><span className="health-dot" /> {usersError ? 'Atenção necessária' : usersLoading ? 'Carregando fonte administrativa' : 'Usuários sincronizados'} <b>AD</b></div></header>

      <section className="admin-metrics" id="metricas" aria-label="Métricas da plataforma">
        {metrics.map(([label, detail]) => <article key={label}><p>{label}</p><strong>{detail === 'Fonte de telemetria pendente' ? '—' : detail}</strong><small>{detail === 'Fonte de telemetria pendente' ? detail : 'Fonte administrativa real'}</small></article>)}
      </section>

      <section className="admin-card admin-queue" id="moderacao">
        <div className="admin-card-heading"><div><p className="eyebrow">AÇÃO NECESSÁRIA</p><h2>Fila de moderação</h2></div><span>Fonte operacional pendente</span></div>
        <div className="admin-tools"><label><span aria-hidden="true">⌕</span><input aria-label="Buscar na administração" placeholder="Buscar usuário, conteúdo ou pedido" disabled /></label><select aria-label="Filtrar status" disabled><option>Todos</option></select></div>
        <div className="admin-empty" role="status"><strong>Nenhuma informação de moderação foi carregada.</strong><p>Esta tela só exibirá denúncias e pendências confirmadas pela fonte administrativa.</p></div>
      </section>

      <div className="admin-columns">
        <section className="admin-card" id="usuarios">
          <div className="admin-card-heading"><div><p className="eyebrow">COMUNIDADE</p><h2>Usuários e permissões</h2></div><span>{usersLoading ? 'Carregando…' : `${users.length} cadastrados`}</span></div>
          {usersMessage && <p className="creator-success" role="status">{usersMessage}</p>}
          {usersError && <p className="auth-error" role="alert">{usersError}</p>}
          {usersLoading ? <div className="admin-empty" role="status">Carregando usuários verificados…</div> : users.length ? <div className="dashboard-class-list">
            {users.map((user) => <article key={user.id}>
              <div className="calendar-date"><strong>{user.email.slice(0, 1).toUpperCase()}</strong><span>{user.audience}</span></div>
              <div className="class-row-copy"><h3>{user.email}</h3><p>{roleLabels[user.role]}</p><small className="chat-on">Conta persistida na API</small></div>
              <div className="class-row-actions">
                <select aria-label={`Perfil de ${user.email}`} value={user.role} disabled={pendingUserId === user.id} onChange={(event) => void changeRole(user, event.target.value as Role)}>
                  <option value="VIEWER">Aluno</option>
                  <option value="CREATOR">Criador</option>
                  <option value="ADMIN">Administrador</option>
                </select>
              </div>
            </article>)}
          </div> : <div className="admin-empty" role="status">Nenhum usuário cadastrado foi retornado pela API.</div>}
        </section>
        <section className="admin-card" id="transmissoes"><div className="admin-card-heading"><div><p className="eyebrow">TEMPO REAL</p><h2>Transmissões</h2></div><span>Telemetria pendente</span></div><div className="admin-live-summary"><strong>—</strong><span>audiência não disponível</span><small>Aguardando fonte real de telemetria.</small></div></section>
      </div>

      <section className="admin-domain-grid" aria-label="Áreas administrativas">
        {domains.map(([id, title]) => <article className="admin-card" id={id} key={id}><span>↗</span><h2>{title}</h2><strong>{id === 'criadores' ? `${creatorCount} criadores autorizados` : 'Dados não carregados'}</strong><p>{id === 'criadores' ? 'Perfis de acesso são administrados na seção Usuários.' : 'Nenhum valor operacional será simulado.'}</p><button disabled>Gerenciar</button></article>)}
      </section>

      <section className="admin-card audit-card" id="auditoria"><div className="admin-card-heading"><div><p className="eyebrow">RASTREABILIDADE</p><h2>Auditoria</h2></div><button disabled>Exportar relatório</button></div><div className="admin-empty" role="status">Nenhum evento de auditoria verificado foi carregado.</div></section>
    </main>
  </div>
}
