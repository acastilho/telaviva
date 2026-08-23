import { useEffect, useMemo, useRef, useState } from 'react'
import type { Audience, AuthUser } from './auth'
import { BrandMark } from './BrandMark'
import { homologationLiveConfiguration, LiveSocketClient, type LiveSocketEvent, type LiveSocketStatus } from './liveSocket'

type LiveRoomSession = {
  title: string
  creator: string
  profession: string
  viewers?: string
  objective?: string
}

type LiveRoomProps = {
  session: LiveRoomSession
  audience: Audience
  user: AuthUser
  onClose: () => void
}

type Message = {
  id: string
  author: string
  text: string
  kind: 'message' | 'question'
}

type RemoteSettings = {
  chat: boolean
  questions: boolean
  reactions: boolean
}

const initialMessages: Message[] = [
  { id: 'demo-1', author: 'Lia', text: 'Que material você recomenda para começar?', kind: 'question' },
  { id: 'demo-2', author: 'Rafael', text: 'Muito bom ver a decisão sendo explicada ao vivo.', kind: 'message' },
]

const socketLabel: Record<LiveSocketStatus, string> = {
  idle: 'modo demonstração',
  connecting: 'conectando…',
  connected: 'dados ao vivo',
  reconnecting: 'reconectando…',
  closed: 'desconectado',
  error: 'socket indisponível',
}

function eventString(event: LiveSocketEvent, key: string): string | null {
  const value = event[key]
  return typeof value === 'string' ? value : null
}

function eventNumber(event: LiveSocketEvent, key: string): number | null {
  const value = event[key]
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

export function LiveRoom({ session, audience, user, onClose }: LiveRoomProps) {
  const liveConfiguration = useMemo(() => homologationLiveConfiguration(), [])
  const [messages, setMessages] = useState<Message[]>(liveConfiguration.enabled ? [] : initialMessages)
  const [draft, setDraft] = useState('')
  const [tab, setTab] = useState<'chat' | 'questions'>('chat')
  const [liked, setLiked] = useState(false)
  const [notes, setNotes] = useState('')
  const [socketStatus, setSocketStatus] = useState<LiveSocketStatus>(liveConfiguration.enabled ? 'connecting' : 'idle')
  const [socketError, setSocketError] = useState('')
  const [viewerCount, setViewerCount] = useState<number | null>(null)
  const [remoteSettings, setRemoteSettings] = useState<RemoteSettings>({ chat: true, questions: true, reactions: true })
  const socketRef = useRef<LiveSocketClient | null>(null)

  useEffect(() => {
    if (!liveConfiguration.enabled) return

    const onEvent = (event: LiveSocketEvent) => {
      if (event.type === 'viewer_count') {
        const count = eventNumber(event, 'count')
        if (count !== null) setViewerCount(count)
        return
      }

      if (event.type === 'ready') {
        const settings = event.settings
        if (settings && typeof settings === 'object') {
          const values = settings as Record<string, unknown>
          setRemoteSettings({
            chat: values.chat_enabled !== false,
            questions: values.questions_enabled !== false,
            reactions: values.reactions_enabled !== false,
          })
        }
        setSocketError('')
        return
      }

      if (event.type === 'settings') {
        setRemoteSettings({
          chat: event.chat_enabled !== false,
          questions: event.questions_enabled !== false,
          reactions: event.reactions_enabled !== false,
        })
        return
      }

      if (event.type === 'event') {
        const kind = eventString(event, 'kind')
        const content = eventString(event, 'content')
        const id = eventString(event, 'id')
        const userId = eventString(event, 'user_id')
        if (!content || !id || !userId) return
        if (kind === 'reaction') return
        if (kind !== 'message' && kind !== 'question') return
        setMessages((current) => current.some((message) => message.id === id) ? current : [...current, {
          id,
          author: userId === user.id ? 'Você' : `Participante ${userId.slice(0, 4)}`,
          text: content,
          kind,
        }])
        return
      }

      if (event.type === 'error') {
        const code = eventString(event, 'code') ?? 'socket_error'
        const messagesByCode: Record<string, string> = {
          invalid_event: 'Evento inválido para esta sala.',
          interaction_disabled: 'Este canal foi desativado pelo criador.',
          restricted: 'Sua participação está temporariamente restrita.',
          invalid_content: 'A mensagem não atende aos limites da sala.',
          rate_limited: 'Muitas mensagens em sequência. Aguarde alguns segundos.',
          invalid_server_payload: 'O servidor enviou uma resposta inválida.',
        }
        setSocketError(messagesByCode[code] ?? 'Não foi possível enviar o evento ao vivo.')
      }
    }

    const client = new LiveSocketClient(onEvent, (status) => {
      setSocketStatus(status)
      if (status === 'connected') setSocketError('')
      if (status === 'error') setSocketError('Não foi possível conectar aos dados ao vivo desta transmissão.')
    })
    socketRef.current = client
    client.connect()

    return () => {
      client.stop()
      socketRef.current = null
    }
  }, [liveConfiguration.enabled, user.id])

  const audienceInteraction = useMemo(() => {
    if (audience === 'CHILD') return { chat: false, questions: true, label: 'Interação infantil protegida' }
    if (audience === 'TEEN') return { chat: true, questions: true, label: 'Interação moderada para adolescentes' }
    return { chat: true, questions: true, label: 'Interação ao vivo' }
  }, [audience])

  const interaction = {
    chat: audienceInteraction.chat && remoteSettings.chat,
    questions: audienceInteraction.questions && remoteSettings.questions,
    reactions: remoteSettings.reactions,
    label: audienceInteraction.label,
  }

  const visibleMessages = messages.filter((message) => tab === 'chat' ? message.kind === 'message' : message.kind === 'question')
  const canSubmit = draft.trim().length > 1 && (tab === 'questions' ? interaction.questions : interaction.chat) && (!liveConfiguration.enabled || socketStatus === 'connected')

  const send = () => {
    if (!canSubmit) return
    const text = draft.trim().slice(0, 500)
    const kind = tab === 'questions' ? 'question' : 'message'

    if (liveConfiguration.enabled) {
      const sent = socketRef.current?.send(kind, text) ?? false
      if (!sent) {
        setSocketError('A conexão ao vivo ainda não está pronta. Tente novamente em instantes.')
        return
      }
    } else {
      setMessages((current) => [...current, {
        id: `local-${Date.now()}`,
        author: user.email.split('@')[0] || 'Você',
        text,
        kind,
      }])
    }
    setDraft('')
  }

  const toggleLike = () => {
    const next = !liked
    if (next && liveConfiguration.enabled && interaction.reactions && socketStatus === 'connected') {
      socketRef.current?.send('reaction', '♡')
    }
    setLiked(next)
  }

  const viewers = viewerCount !== null ? String(viewerCount) : session.viewers ?? 'ao vivo'

  return (
    <div className="live-room-shell">
      <header className="live-room-header">
        <button className="brand brand-button institute-brand-link" onClick={onClose} aria-label="Voltar ao início"><BrandMark /></button>
        <div className="live-room-status">
          <span>● AO VIVO</span>
          <small>{viewers} assistindo · {socketLabel[socketStatus]}</small>
        </div>
        <button className="secondary compact" onClick={onClose}>Sair da aula</button>
      </header>

      <main className="live-room-main">
        <section className="live-video-column">
          <div className="live-video" role="region" aria-label={`Transmissão ${session.title}`}>
            <div className="live-video-watermark"><BrandMark symbolOnly /></div>
            <div className="live-video-copy">
              <span className="live-pill">AO VIVO</span>
              <strong>{session.title}</strong>
              <small>{session.creator} · {session.profession}</small>
            </div>
            <div className="live-video-controls" aria-label="Controles do player">
              <button aria-label="Pausar reprodução">Ⅱ</button>
              <span className="live-progress"><i /></span>
              <button aria-label="Ativar ou desativar som">◉</button>
              <button aria-label="Tela cheia">⛶</button>
            </div>
          </div>

          <div className="live-class-info">
            <div>
              <p className="eyebrow">CONHECIMENTO ACONTECENDO AGORA</p>
              <h1>{session.title}</h1>
              <p>{session.objective ?? 'Acompanhe o processo, as escolhas e os erros enquanto o trabalho acontece.'}</p>
            </div>
            <button className={`reaction-button ${liked ? 'active' : ''}`} onClick={toggleLike} aria-pressed={liked} disabled={!interaction.reactions}>♡ <span>{liked ? 'Apoiando' : 'Apoiar'}</span></button>
          </div>

          <section className="learning-notes" aria-labelledby="notes-title">
            <div><p className="eyebrow">SEU CADERNO</p><h2 id="notes-title">Anotações da aula</h2></div>
            <textarea value={notes} onChange={(event) => setNotes(event.target.value)} maxLength={3000} placeholder="Registre ideias, dúvidas e descobertas. Estas anotações ficam somente neste dispositivo durante a homologação." />
            <small>{notes.length}/3000</small>
          </section>
        </section>

        <aside className="live-interaction" aria-label={interaction.label}>
          <div className="interaction-heading">
            <div><p className="eyebrow">{interaction.label.toUpperCase()}</p><h2>Participe</h2></div>
            <span className="moderation-chip">{socketStatus === 'connected' ? 'Conectado' : 'Protegido'}</span>
          </div>

          {socketError && <div className="interaction-guardrail" role="alert"><strong>Conexão em tempo real</strong><p>{socketError}</p></div>}

          <div className="interaction-tabs" role="tablist" aria-label="Canais de interação">
            <button role="tab" aria-selected={tab === 'chat'} disabled={!interaction.chat} onClick={() => setTab('chat')}>Conversa</button>
            <button role="tab" aria-selected={tab === 'questions'} disabled={!interaction.questions} onClick={() => setTab('questions')}>Perguntas</button>
          </div>

          {!interaction.chat && tab === 'chat' && <div className="interaction-guardrail"><strong>Conversa livre desativada</strong><p>Na área infantil, a participação acontece por perguntas que passam por moderação.</p></div>}

          <div className="message-list" aria-live="polite">
            {visibleMessages.map((message) => <article key={message.id}><span>{message.author.slice(0, 2).toUpperCase()}</span><div><strong>{message.author}</strong><p>{message.text}</p></div></article>)}
            {!visibleMessages.length && <p className="message-empty">{liveConfiguration.enabled ? 'Ainda não há mensagens ao vivo neste canal.' : 'Ainda não há mensagens neste canal.'}</p>}
          </div>

          <div className="interaction-compose">
            <label htmlFor="live-message">{tab === 'questions' ? 'Envie uma pergunta' : 'Escreva na conversa'}</label>
            <textarea id="live-message" value={draft} onChange={(event) => setDraft(event.target.value)} maxLength={500} disabled={(tab === 'chat' && !interaction.chat) || (tab === 'questions' && !interaction.questions)} placeholder={tab === 'questions' ? 'Pergunte sobre o que está acontecendo...' : 'Compartilhe uma observação respeitosa...'} />
            <div><small>{draft.length}/500</small><button className="primary small" disabled={!canSubmit} onClick={send}>Enviar</button></div>
          </div>
          <p className="safety-note">Não compartilhe dados pessoais. Denúncias e moderação ficam disponíveis durante toda a experiência.</p>
        </aside>
      </main>
    </div>
  )
}
