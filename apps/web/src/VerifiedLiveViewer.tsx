import { useEffect, useState } from 'react'
import { BrandMark } from './BrandMark'
import { LiveViewer } from './LiveViewer'
import { schedulingClient, usesRemoteSchedulingApi, type ScheduledStream } from './scheduling'

export function VerifiedLiveViewer({ roomId }: { roomId: string }) {
  const [stream, setStream] = useState<ScheduledStream | null>(null)
  const [status, setStatus] = useState<'checking' | 'active' | 'inactive' | 'error'>(usesRemoteSchedulingApi ? 'checking' : 'active')

  useEffect(() => {
    if (!usesRemoteSchedulingApi) return
    let mounted = true

    const verify = async () => {
      try {
        const active = await schedulingClient.activeByRoom(roomId)
        if (!mounted) return
        setStream(active)
        setStatus(active ? 'active' : 'inactive')
      } catch {
        if (mounted) setStatus('error')
      }
    }

    void verify()
    const timer = window.setInterval(() => void verify(), 15_000)
    return () => {
      mounted = false
      window.clearInterval(timer)
    }
  }, [roomId])

  if (status === 'active') return <LiveViewer roomId={roomId} />

  return (
    <div className="broadcast-viewer">
      <header className="broadcast-viewer-header"><BrandMark /></header>
      <main className="broadcast-viewer-main">
        <section className="broadcast-stage" aria-live="polite">
          <div className="broadcast-waiting">
            <BrandMark symbolOnly />
            <h1>{status === 'checking' ? 'Verificando a aula' : status === 'inactive' ? 'Esta aula não está ao vivo' : 'Não foi possível verificar a aula'}</h1>
            <p>{status === 'checking'
              ? 'Confirmando no sistema se existe uma transmissão ativa para este link.'
              : status === 'inactive'
                ? 'O vídeo só é exibido quando uma aula cadastrada é iniciada pelo criador.'
                : 'A API de aulas está indisponível. Tente novamente em instantes.'}</p>
          </div>
        </section>
        {stream && <section className="broadcast-viewer-info"><div><p className="eyebrow">INSTITUTO TELA VIVA</p><h2>{stream.title}</h2></div></section>}
      </main>
    </div>
  )
}
