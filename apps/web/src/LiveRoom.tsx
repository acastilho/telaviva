import { useMemo, useState } from 'react'
import type { Audience, AuthUser } from './auth'
import { BrandMark } from './BrandMark'

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
  id: number
  author: string
  text: string
  kind: 'message' | 'question'
}

const initialMessages: Message[] = [
  { id: 1, author: 'Lia', text: 'Que material você recomenda para começar?', kind: 'question' },
  { id: 2, author: 'Rafael', text: 'Muito bom ver a decisão sendo explicada ao vivo.', kind: 'message' },
]

export function LiveRoom({ session, audience, user, onClose }: LiveRoomProps) {
  const [messages, setMessages] = useState(initialMessages)
  const [draft, setDraft] = useState('')
  const [tab, setTab] = useState<'chat' | 'questions'>('chat')
  const [liked, setLiked] = useState(false)
  const [notes, setNotes] = useState('')

  const interaction = useMemo(() => {
    if (audience === 'CHILD') return { chat: false, questions: true, label: 'Interação infantil protegida' }
    if (audience === 'TEEN') return { chat: true, questions: true, label: 'Interação moderada para adolescentes' }
    return { chat: true, questions: true, label: 'Interação ao vivo' }
  }, [audience])

  const visibleMessages = messages.filter((message) => tab === 'chat' ? message.kind === 'message' : message.kind === 'question')
  const canSubmit = draft.trim().length > 1 && (tab === 'questions' ? interaction.questions : interaction.chat)

  const send = () => {
    if (!canSubmit) return
    setMessages((current) => [...current, {
      id: Date.now(),
      author: user.email.split('@')[0] || 'Você',
      text: draft.trim().slice(0, 500),
      kind: tab === 'questions' ? 'question' : 'message',
    }])
    setDraft('')
  }

  return (
    <div className="live-room-shell">
      <header className="live-room-header">
        <button className="brand brand-button institute-brand-link" onClick={onClose} aria-label="Voltar ao início"><BrandMark /></button>
        <div className="live-room-status"><span>● AO VIVO</span><small>{session.viewers ?? 'ao vivo'} assistindo</small></div>
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
            <button className={`reaction-button ${liked ? 'active' : ''}`} onClick={() => setLiked(!liked)} aria-pressed={liked}>♡ <span>{liked ? 'Apoiando' : 'Apoiar'}</span></button>
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
            <span className="moderation-chip">Protegido</span>
          </div>

          <div className="interaction-tabs" role="tablist" aria-label="Canais de interação">
            <button role="tab" aria-selected={tab === 'chat'} disabled={!interaction.chat} onClick={() => setTab('chat')}>Conversa</button>
            <button role="tab" aria-selected={tab === 'questions'} onClick={() => setTab('questions')}>Perguntas</button>
          </div>

          {!interaction.chat && tab === 'chat' && <div className="interaction-guardrail"><strong>Conversa livre desativada</strong><p>Na área infantil, a participação acontece por perguntas que passam por moderação.</p></div>}

          <div className="message-list" aria-live="polite">
            {visibleMessages.map((message) => <article key={message.id}><span>{message.author.slice(0, 2).toUpperCase()}</span><div><strong>{message.author}</strong><p>{message.text}</p></div></article>)}
            {!visibleMessages.length && <p className="message-empty">Ainda não há mensagens neste canal.</p>}
          </div>

          <div className="interaction-compose">
            <label htmlFor="live-message">{tab === 'questions' ? 'Envie uma pergunta' : 'Escreva na conversa'}</label>
            <textarea id="live-message" value={draft} onChange={(event) => setDraft(event.target.value)} maxLength={500} disabled={tab === 'chat' && !interaction.chat} placeholder={tab === 'questions' ? 'Pergunte sobre o que está acontecendo...' : 'Compartilhe uma observação respeitosa...'} />
            <div><small>{draft.length}/500</small><button className="primary small" disabled={!canSubmit} onClick={send}>Enviar</button></div>
          </div>
          <p className="safety-note">Não compartilhe dados pessoais. Denúncias e moderação ficam disponíveis durante toda a experiência.</p>
        </aside>
      </main>
    </div>
  )
}
