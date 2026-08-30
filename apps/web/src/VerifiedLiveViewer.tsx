import { useEffect, useState } from 'react'
import { authClient } from './auth'
import { BrandMark } from './BrandMark'
import { LiveViewer } from './LiveViewer'
import { schedulingClient, usesRemoteSchedulingApi } from './scheduling'

type ViewerStatus = 'checking' | 'active' | 'inactive' | 'unauthenticated' | 'denied' | 'error'

export function VerifiedLiveViewer({ streamId }: { streamId: string }) {
  const [roomId, setRoomId] = useState<string | null>(null)
  const [status, setStatus] = useState<ViewerStatus>(usesRemoteSchedulingApi ? 'checking' : 'inactive')

  useEffect(() => {
    if (!usesRemoteSchedulingApi) return
    let mounted = true

    const verify = async () => {
      const session = await authClient.restore()
      if (!mounted) return
      if (!session) {
        setRoomId(null)
        setStatus('unauthenticated')
        return
      }

      try {
        const access = await schedulingClient.access(streamId, session.accessToken)
        if (!mounted) return
        if (!access.granted) {
          setRoomId(null)
          setStatus('denied')
          return
        }
        if (!access.live_room_id) {
          setRoomId(null)
          setStatus('inactive')
          return
        }
        setRoomId(access.live_room_id)
        setStatus('active')
      } catch {
        if (!mounted) return
        setRoomId(null)
        setStatus('denied')
      }
    }

    void verify()
    const timer = window.setInterval(() => void verify(), 12_000)
    return () => {
      mounted = false
      window.clearInterval(timer)
    }
  }, [streamId])

  if (status === 'active' && roomId) return <LiveViewer roomId={roomId} />

  const title = status === 'checking'
    ? 'Verificando seu acesso'
    : status === 'unauthenticated'
      ? 'Entre para assistir'
      : status === 'inactive'
        ? 'Esta aula não está ao vivo'
        : status === 'denied'
          ? 'Acesso não autorizado'
          : 'Não foi possível verificar a aula'

  const description = status === 'checking'
    ? 'Confirmando sua sessão e a permissão para esta transmissão.'
    : status === 'unauthenticated'
      ? 'O identificador da sala só é liberado após autenticação e verificação de acesso.'
      : status === 'inactive'
        ? 'Sua permissão foi verificada, mas não existe uma sala ativa para esta aula.'
        : status === 'denied'
          ? 'Esta transmissão exige a permissão, compra, assinatura ou convite aplicável à aula.'
          : 'A fonte oficial de acesso está indisponível. Nenhuma sala será presumida como autorizada.'

  return (
    <div className="broadcast-viewer">
      <header className="broadcast-viewer-header"><BrandMark /></header>
      <main className="broadcast-viewer-main">
        <section className="broadcast-stage" aria-live="polite">
          <div className="broadcast-waiting">
            <BrandMark symbolOnly />
            <h1>{title}</h1>
            <p>{description}</p>
          </div>
        </section>
      </main>
    </div>
  )
}
