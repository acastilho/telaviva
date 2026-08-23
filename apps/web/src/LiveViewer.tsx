import { useEffect, useRef, useState } from 'react'
import { BrandMark } from './BrandMark'
import { createLiveRoom, type BroadcastMediaKind, type BroadcastRoom } from './peerBroadcast'

type RemoteMedia = Partial<Record<BroadcastMediaKind, MediaStream>>

function RemoteVideo({ stream, className, label }: { stream?: MediaStream; className?: string; label: string }) {
  const ref = useRef<HTMLVideoElement>(null)

  useEffect(() => {
    if (!ref.current) return
    ref.current.srcObject = stream ?? null
    if (stream) void ref.current.play().catch(() => undefined)
  }, [stream])

  if (!stream) return null
  return <video ref={ref} className={className} autoPlay playsInline aria-label={label} />
}

function RemoteAudio({ stream }: { stream?: MediaStream }) {
  const ref = useRef<HTMLAudioElement>(null)

  useEffect(() => {
    if (!ref.current) return
    ref.current.srcObject = stream ?? null
    if (stream) void ref.current.play().catch(() => undefined)
  }, [stream])

  return <audio ref={ref} autoPlay />
}

export function LiveViewer({ roomId }: { roomId: string }) {
  const [media, setMedia] = useState<RemoteMedia>({})
  const [status, setStatus] = useState<'connecting' | 'waiting' | 'live' | 'error'>('connecting')
  const [error, setError] = useState('')
  const [soundUnlocked, setSoundUnlocked] = useState(false)
  const roomRef = useRef<BroadcastRoom | null>(null)

  useEffect(() => {
    let active = true
    let room: BroadcastRoom

    try {
      room = createLiveRoom(roomId, () => {
        if (!active) return
        setStatus('error')
        setError('A conexão direta não pôde ser criada nesta rede. Tente outra rede ou desative VPN/bloqueios de WebRTC.')
      })
    } catch (reason) {
      setStatus('error')
      setError(reason instanceof Error ? reason.message : 'Código de transmissão inválido.')
      return
    }

    roomRef.current = room
    setStatus('waiting')

    room.onPeerStream = (stream, _peerId, metadata) => {
      if (!active) return
      const kind = metadata && typeof metadata === 'object' && 'kind' in metadata
        ? (metadata as { kind?: BroadcastMediaKind }).kind
        : undefined
      if (!kind || !['screen', 'camera', 'microphone'].includes(kind)) return
      setMedia((current) => ({ ...current, [kind]: stream }))
      setStatus('live')
      stream.getTracks().forEach((track) => {
        track.addEventListener('ended', () => {
          setMedia((current) => current[kind] === stream ? { ...current, [kind]: undefined } : current)
        }, { once: true })
      })
    }

    room.onPeerLeave = () => {
      if (!active) return
      window.setTimeout(() => {
        setMedia((current) => {
          const hasActiveTrack = Object.values(current).some((stream) => stream?.getTracks().some((track) => track.readyState === 'live'))
          if (!hasActiveTrack) setStatus('waiting')
          return current
        })
      }, 400)
    }

    return () => {
      active = false
      room.leave()
      roomRef.current = null
      Object.values(media).forEach((stream) => stream?.getTracks().forEach((track) => track.stop()))
    }
    // media is intentionally not a dependency: remote tracks are owned by the room lifecycle.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [roomId])

  const primary = media.screen ?? media.camera
  const showCameraPip = Boolean(media.screen && media.camera)

  const unlockSound = async () => {
    const elements = Array.from(document.querySelectorAll<HTMLMediaElement>('.broadcast-viewer video, .broadcast-viewer audio'))
    await Promise.allSettled(elements.map((element) => element.play()))
    setSoundUnlocked(true)
  }

  return (
    <div className="broadcast-viewer">
      <header className="broadcast-viewer-header">
        <BrandMark />
        <span className={`broadcast-connection ${status}`}>{status === 'live' ? '● AO VIVO' : status === 'error' ? 'CONEXÃO INDISPONÍVEL' : 'CONECTANDO'}</span>
      </header>

      <main className="broadcast-viewer-main">
        <section className="broadcast-stage" aria-live="polite">
          {primary ? (
            <>
              <RemoteVideo stream={primary} className="broadcast-primary-video" label="Transmissão ao vivo" />
              {showCameraPip && <RemoteVideo stream={media.camera} className="broadcast-camera-pip" label="Câmera do apresentador" />}
              <RemoteAudio stream={media.microphone} />
              <div className="broadcast-live-badge">● AO VIVO</div>
            </>
          ) : (
            <div className="broadcast-waiting">
              <BrandMark symbolOnly />
              <h1>{status === 'error' ? 'Não foi possível conectar' : 'Aguardando a transmissão'}</h1>
              <p>{error || 'Mantenha esta tela aberta. O vídeo aparecerá assim que o criador iniciar a live.'}</p>
            </div>
          )}
        </section>

        <section className="broadcast-viewer-info">
          <div>
            <p className="eyebrow">INSTITUTO TELA VIVA</p>
            <h2>Conhecimento acontecendo agora</h2>
            <p>Esta visualização recebe áudio e vídeo diretamente da transmissão ativa.</p>
          </div>
          {primary && <button className="primary" onClick={unlockSound}>{soundUnlocked ? 'Som ativado' : 'Ativar som'}</button>}
        </section>
      </main>
    </div>
  )
}
