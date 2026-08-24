import { useEffect, useMemo, useRef, useState } from 'react'
import { BrandMark } from './BrandMark'
import {
  createLiveRoom,
  createRoomId,
  createViewerUrl,
  publishStream,
  type BroadcastMediaKind,
  type BroadcastRoom,
  unpublishStream,
} from './peerBroadcast'
import { schedulingClient, usesRemoteSchedulingApi } from './scheduling'

type Layout = 'screen' | 'screen-camera' | 'camera'
type LiveState = 'preparing' | 'preview' | 'live' | 'paused' | 'ended'
type InteractionChannel = 'chat' | 'questions' | 'reactions'

type LiveStudioProps = {
  onClose: () => void
  streamId?: string
  accessToken?: string
}

const stopStream = (stream: MediaStream | null) => stream?.getTracks().forEach((track) => track.stop())

function Video({ stream, muted, label }: { stream: MediaStream | null; muted: boolean; label: string }) {
  const ref = useRef<HTMLVideoElement>(null)

  useEffect(() => {
    if (!ref.current) return
    ref.current.srcObject = stream
    if (stream) void ref.current.play().catch(() => undefined)
  }, [stream])

  return stream ? <video ref={ref} autoPlay playsInline muted={muted} aria-label={label} /> : null
}

function mediaErrorMessage(error: unknown, kind: 'camera' | 'microphone' | 'screen') {
  const name = error instanceof DOMException ? error.name : ''
  if (!window.isSecureContext && window.location.hostname !== 'localhost') {
    return 'Câmera e microfone exigem HTTPS. Abra o ambiente seguro de homologação para transmitir.'
  }
  if (name === 'NotAllowedError' || name === 'PermissionDeniedError') {
    return kind === 'screen'
      ? 'O compartilhamento foi cancelado ou bloqueado. Escolha uma tela, janela ou aba para continuar.'
      : `Permissão de ${kind === 'camera' ? 'câmera' : 'microfone'} bloqueada. Libere o acesso no ícone de permissões do navegador e tente novamente.`
  }
  if (name === 'NotFoundError' || name === 'DevicesNotFoundError') {
    return `Nenhum dispositivo de ${kind === 'camera' ? 'câmera' : 'áudio'} foi encontrado.`
  }
  if (name === 'NotReadableError' || name === 'TrackStartError') {
    return 'O dispositivo está ocupado por outro aplicativo. Feche outros apps que estejam usando a câmera ou o microfone.'
  }
  return kind === 'screen'
    ? 'Não foi possível iniciar o compartilhamento de tela neste navegador.'
    : `Não foi possível acessar ${kind === 'camera' ? 'a câmera' : 'o microfone'}.`
}

export function LiveStudio({ onClose, streamId, accessToken }: LiveStudioProps) {
  const [layout, setLayout] = useState<Layout>('screen')
  const [state, setState] = useState<LiveState>('preparing')
  const [screen, setScreen] = useState<MediaStream | null>(null)
  const [camera, setCamera] = useState<MediaStream | null>(null)
  const [microphone, setMicrophone] = useState<MediaStream | null>(null)
  const [cameraEnabled, setCameraEnabled] = useState(false)
  const [micEnabled, setMicEnabled] = useState(true)
  const [error, setError] = useState('')
  const [roomId] = useState(createRoomId)
  const [viewerCount, setViewerCount] = useState(0)
  const [shareMessage, setShareMessage] = useState('')
  const [lifecycleLoading, setLifecycleLoading] = useState(false)
  const [finishPending, setFinishPending] = useState(false)
  const [interactions, setInteractions] = useState<Record<InteractionChannel, boolean>>({
    chat: true,
    questions: true,
    reactions: true,
  })

  const screenRef = useRef<MediaStream | null>(null)
  const cameraRef = useRef<MediaStream | null>(null)
  const microphoneRef = useRef<MediaStream | null>(null)
  const roomRef = useRef<BroadcastRoom | null>(null)
  const stateRef = useRef<LiveState>('preparing')

  const viewerUrl = useMemo(() => createViewerUrl(roomId), [roomId])
  const isLocalhost = typeof window !== 'undefined' && ['localhost', '127.0.0.1'].includes(window.location.hostname)
  const hasPersistedClass = usesRemoteSchedulingApi && Boolean(streamId && accessToken)

  useEffect(() => {
    stateRef.current = state
  }, [state])

  const currentStreams = () => ({
    screen: screenRef.current,
    camera: cameraRef.current,
    microphone: microphoneRef.current,
  })

  const publishCurrentTo = (target?: string) => {
    const room = roomRef.current
    if (!room) return
    const streams = currentStreams()
    ;(Object.entries(streams) as Array<[BroadcastMediaKind, MediaStream | null]>).forEach(([kind, stream]) => {
      if (stream) publishStream(room, stream, kind, target)
    })
  }

  const replaceStream = (kind: BroadcastMediaKind, next: MediaStream | null) => {
    const refs = { screen: screenRef, camera: cameraRef, microphone: microphoneRef }
    const setters = { screen: setScreen, camera: setCamera, microphone: setMicrophone }
    const previous = refs[kind].current
    const room = roomRef.current

    if (previous && room) {
      try { unpublishStream(room, previous) } catch { /* peer may already be gone */ }
    }
    stopStream(previous)
    refs[kind].current = next
    setters[kind](next)

    if (next && room && (stateRef.current === 'live' || stateRef.current === 'paused')) {
      publishStream(room, next, kind)
    }
  }

  const leaveRoom = () => {
    roomRef.current?.leave()
    roomRef.current = null
    setViewerCount(0)
  }

  useEffect(() => () => {
    leaveRoom()
    stopStream(screenRef.current)
    stopStream(cameraRef.current)
    stopStream(microphoneRef.current)
  }, [])

  const requestScreen = async () => {
    setError('')
    if (!navigator.mediaDevices?.getDisplayMedia) {
      setError('Este navegador não oferece compartilhamento de tela. Use o modo Somente câmera ou um navegador compatível.')
      return false
    }
    try {
      const next = await navigator.mediaDevices.getDisplayMedia({
        video: true,
        audio: false,
        preferCurrentTab: true,
        selfBrowserSurface: 'exclude',
        surfaceSwitching: 'include',
      } as DisplayMediaStreamOptions)
      const track = next.getVideoTracks()[0]
      track?.addEventListener('ended', () => {
        if (screenRef.current !== next) return
        replaceStream('screen', null)
        if (layout !== 'camera' && stateRef.current !== 'ended') setState('preparing')
      }, { once: true })
      replaceStream('screen', next)
      return true
    } catch (reason) {
      setError(mediaErrorMessage(reason, 'screen'))
      return false
    }
  }

  const requestCamera = async () => {
    setError('')
    if (!navigator.mediaDevices?.getUserMedia) {
      setError('Este navegador não disponibiliza acesso à câmera.')
      return false
    }
    try {
      const next = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 1280 },
          height: { ideal: 720 },
          frameRate: { ideal: 30, max: 30 },
          facingMode: 'user',
        },
        audio: false,
      })
      replaceStream('camera', next)
      setCameraEnabled(true)
      if (layout === 'screen') setLayout(screenRef.current ? 'screen-camera' : 'camera')
      return true
    } catch (reason) {
      setCameraEnabled(false)
      setError(mediaErrorMessage(reason, 'camera'))
      return false
    }
  }

  const requestMicrophone = async () => {
    setError('')
    if (!navigator.mediaDevices?.getUserMedia) {
      setMicEnabled(false)
      setError('Este navegador não disponibiliza acesso ao microfone.')
      return false
    }
    try {
      const next = await navigator.mediaDevices.getUserMedia({
        video: false,
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      })
      replaceStream('microphone', next)
      setMicEnabled(true)
      return true
    } catch (reason) {
      setMicEnabled(false)
      setError(mediaErrorMessage(reason, 'microphone'))
      return false
    }
  }

  const selectLayout = async (next: Layout) => {
    setLayout(next)
    setError('')
    if (next === 'camera' && !cameraRef.current) await requestCamera()
    if (next === 'screen-camera' && !cameraRef.current) await requestCamera()
  }

  const preview = async () => {
    if (!usesRemoteSchedulingApi) {
      setError('A API de aulas precisa estar configurada para validar uma aula antes da transmissão.')
      return
    }
    if (!hasPersistedClass) {
      setError('Selecione uma aula cadastrada no Painel do criador antes de preparar a transmissão.')
      return
    }
    let hasVideo = false
    if (layout === 'camera') hasVideo = Boolean(cameraRef.current) || await requestCamera()
    else hasVideo = Boolean(screenRef.current) || await requestScreen()
    if (!hasVideo) return

    if (layout === 'screen-camera' && !cameraRef.current) await requestCamera()
    if (micEnabled && !microphoneRef.current) await requestMicrophone()
    setState('preview')
  }

  const toggleCamera = async () => {
    if (cameraEnabled) {
      replaceStream('camera', null)
      setCameraEnabled(false)
      if (layout === 'screen-camera') setLayout('screen')
    } else {
      await requestCamera()
    }
  }

  const toggleMic = async () => {
    if (!microphoneRef.current) {
      await requestMicrophone()
      return
    }
    const enabled = !micEnabled
    microphoneRef.current.getAudioTracks().forEach((track) => { track.enabled = enabled })
    setMicEnabled(enabled)
  }

  const startBroadcast = async () => {
    setError('')
    if (!ready || lifecycleLoading) return
    if (!usesRemoteSchedulingApi || !streamId || !accessToken) {
      setError('Esta transmissão precisa estar vinculada a uma aula cadastrada e confirmada no sistema.')
      return
    }

    let room: BroadcastRoom | null = null
    setLifecycleLoading(true)
    try {
      room = createLiveRoom(roomId, () => {
        setError('Algumas redes podem bloquear conexões diretas. Se o celular não conectar, teste sem VPN e, de preferência, em outra combinação de Wi-Fi/dados móveis.')
      })
      roomRef.current = room
      await schedulingClient.activate(streamId, roomId, accessToken)
      room.onPeerJoin = (peerId) => {
        setViewerCount(Object.keys(room!.getPeers()).length)
        publishCurrentTo(peerId)
      }
      room.onPeerLeave = () => setViewerCount(Object.keys(room!.getPeers()).length)
      publishCurrentTo()
      setFinishPending(false)
      setState('live')
    } catch (reason) {
      room?.leave()
      roomRef.current = null
      setError(reason instanceof Error ? reason.message : 'Não foi possível iniciar a transmissão.')
    } finally {
      setLifecycleLoading(false)
    }
  }

  const pause = () => {
    screenRef.current?.getVideoTracks().forEach((track) => { track.enabled = false })
    cameraRef.current?.getVideoTracks().forEach((track) => { track.enabled = false })
    microphoneRef.current?.getAudioTracks().forEach((track) => { track.enabled = false })
    setState('paused')
  }

  const resume = () => {
    screenRef.current?.getVideoTracks().forEach((track) => { track.enabled = true })
    cameraRef.current?.getVideoTracks().forEach((track) => { track.enabled = true })
    microphoneRef.current?.getAudioTracks().forEach((track) => { track.enabled = micEnabled })
    setState('live')
  }

  const persistFinish = async () => {
    if (!usesRemoteSchedulingApi || !streamId || !accessToken) return false
    try {
      await schedulingClient.finish(streamId, accessToken)
      setFinishPending(false)
      return true
    } catch (reason) {
      setFinishPending(true)
      setError(`A mídia foi encerrada, mas o sistema ainda não confirmou o fim da aula. ${reason instanceof Error ? reason.message : 'Tente confirmar novamente.'}`)
      return false
    }
  }

  const finish = async () => {
    setLifecycleLoading(true)
    await persistFinish()
    leaveRoom()
    replaceStream('screen', null)
    replaceStream('camera', null)
    replaceStream('microphone', null)
    setCameraEnabled(false)
    setMicEnabled(false)
    setState('ended')
    setLifecycleLoading(false)
  }

  const retryFinish = async () => {
    setLifecycleLoading(true)
    const confirmed = await persistFinish()
    if (confirmed) setError('')
    setLifecycleLoading(false)
  }

  const closeStudio = async () => {
    if (stateRef.current === 'live' || stateRef.current === 'paused') await finish()
    onClose()
  }

  const copyViewerUrl = async () => {
    try {
      await navigator.clipboard.writeText(viewerUrl)
      setShareMessage('Link copiado. Abra no celular para assistir.')
    } catch {
      setShareMessage('Copie o endereço abaixo e abra no celular.')
    }
  }

  const needsScreen = layout !== 'camera'
  const ready = (needsScreen ? Boolean(screen) : Boolean(camera)) && state !== 'ended' && hasPersistedClass
  const toggleInteraction = (channel: InteractionChannel) => {
    setInteractions((current) => ({ ...current, [channel]: !current[channel] }))
  }

  return <div className="studio-shell" role="dialog" aria-modal="true" aria-labelledby="studio-title">
    <header className="studio-header">
      <a className="brand institute-brand-link" href="#inicio" aria-label="Instituto Tela Viva"><BrandMark /></a>
      <div className="studio-status-wrap">
        <span className={`studio-status ${state}`}>{state === 'live' ? '● AO VIVO' : state === 'paused' ? 'Ⅱ PAUSADA' : state === 'ended' ? 'FINALIZADA' : 'ESTÚDIO'}</span>
        {state === 'live' && <small className="studio-viewer-count">{viewerCount} assistindo</small>}
      </div>
      <button className="studio-close" onClick={() => void closeStudio()} aria-label="Fechar estúdio">×</button>
    </header>

    <main className="studio-main">
      <section className="studio-preview-panel">
        <div className={`video-stage layout-${layout}`}>
          {state === 'paused' && <div className="stage-message"><strong>Transmissão pausada</strong><span>Áudio e vídeo estão temporariamente suspensos.</span></div>}
          {state === 'ended' && <div className="stage-message"><strong>Live finalizada</strong><span>As fontes foram desconectadas com segurança.</span></div>}
          {state !== 'paused' && state !== 'ended' && <>
            {needsScreen && <Video stream={screen} muted label="Prévia da tela compartilhada" />}
            {(layout === 'camera' || layout === 'screen-camera') && <Video stream={camera} muted label="Prévia da câmera" />}
            {!ready && <div className="stage-message"><span className="stage-icon">▣</span><strong>{!usesRemoteSchedulingApi ? 'API de aulas não configurada' : hasPersistedClass ? 'Sua prévia aparecerá aqui' : 'Selecione uma aula cadastrada'}</strong><span>{!usesRemoteSchedulingApi ? 'Sem a fonte oficial não é possível confirmar uma aula ativa nem iniciar a transmissão.' : hasPersistedClass ? 'Escolha Somente câmera para testar rapidamente, ou selecione uma tela para compartilhar.' : 'O estúdio não entra ao vivo sem uma aula existente no sistema.'}</span></div>}
          </>}
        </div>

        <div className="studio-controls" aria-label="Controles da transmissão">
          {state === 'live' && <button onClick={pause} aria-label="Pausar">Ⅱ <span>Pausar</span></button>}
          {state === 'paused' && <button onClick={resume} aria-label="Retomar">▶ <span>Retomar</span></button>}
          <button onClick={toggleMic} aria-pressed={!micEnabled} aria-label={micEnabled ? 'Silenciar' : 'Ativar microfone'}>{micEnabled ? '◉' : '⊘'} <span>{micEnabled ? 'Silenciar' : 'Ativar microfone'}</span></button>
          <button onClick={toggleCamera} aria-pressed={cameraEnabled} aria-label={cameraEnabled ? 'Desligar câmera' : 'Ligar câmera'}>▣ <span>{cameraEnabled ? 'Desligar câmera' : 'Ligar câmera'}</span></button>
          {needsScreen && <button onClick={requestScreen} aria-label="Trocar fonte">↻ <span>{screen ? 'Trocar fonte' : 'Escolher tela'}</span></button>}
          {(state === 'live' || state === 'paused') && <button className="danger" disabled={lifecycleLoading} onClick={() => void finish()} aria-label="Finalizar">■ <span>{lifecycleLoading ? 'Finalizando…' : 'Finalizar'}</span></button>}
        </div>
      </section>

      <aside className="studio-settings">
        <p className="eyebrow">CONFIGURAÇÃO</p><h1 id="studio-title">Prepare sua live</h1>
        <p className="interaction-note" role="status">{!usesRemoteSchedulingApi ? 'API de aulas não configurada. A transmissão permanece bloqueada.' : streamId ? `Aula vinculada: ${streamId.slice(0, 8)}…` : 'Nenhuma aula vinculada. Volte ao Painel do criador e escolha Transmitir em uma aula.'}</p>
        <fieldset><legend>Layout</legend>
          <label><input type="radio" name="layout" checked={layout === 'screen'} onChange={() => void selectLayout('screen')} /><span>▱</span><b>Tela</b></label>
          <label><input type="radio" name="layout" checked={layout === 'screen-camera'} onChange={() => void selectLayout('screen-camera')} /><span>▰</span><b>Tela + câmera</b></label>
          <label><input type="radio" name="layout" checked={layout === 'camera'} onChange={() => void selectLayout('camera')} /><span>▣</span><b>Somente câmera</b></label>
        </fieldset>

        <div className="device-status-card" aria-live="polite">
          <span className={camera ? 'ok' : ''}>Câmera {camera ? 'pronta' : 'desligada'}</span>
          <span className={microphone && micEnabled ? 'ok' : ''}>Microfone {microphone && micEnabled ? 'pronto' : 'desligado'}</span>
          <span className={screen ? 'ok' : ''}>Tela {screen ? 'selecionada' : 'não selecionada'}</span>
        </div>

        <fieldset className="interaction-settings"><legend>Interação ao vivo</legend>
          <label><input type="checkbox" checked={interactions.chat} onChange={() => toggleInteraction('chat')} /><span aria-hidden="true">☵</span><b>Chat</b></label>
          <label><input type="checkbox" checked={interactions.questions} onChange={() => toggleInteraction('questions')} /><span aria-hidden="true">?</span><b>Perguntas</b></label>
          <label><input type="checkbox" checked={interactions.reactions} onChange={() => toggleInteraction('reactions')} /><span aria-hidden="true">♡</span><b>Reações</b></label>
        </fieldset>
        <p className="interaction-note" role="status">{Object.values(interactions).filter(Boolean).length} de 3 canais habilitados.</p>

        {needsScreen && <div className="source-card"><div><strong>Monitor, janela ou aba</strong><p>O navegador abrirá um seletor seguro para você escolher exatamente o que compartilhar.</p></div><button className="secondary" onClick={requestScreen}>{screen ? 'Trocar fonte' : 'Escolher fonte'}</button></div>}

        {(state === 'live' || state === 'paused') && <div className="broadcast-share-card">
          <div><strong>Teste no celular</strong><p>Este link só é aceito enquanto a aula estiver marcada como ativa no sistema.</p></div>
          <code>{viewerUrl}</code>
          <button className="primary" onClick={copyViewerUrl}>Copiar link para assistir</button>
          {shareMessage && <small>{shareMessage}</small>}
          {isLocalhost && <p className="broadcast-local-warning">Você está em localhost. Para abrir no celular, inicie a transmissão pela URL HTTPS de homologação ou acesse este servidor por um endereço seguro da sua rede.</p>}
        </div>}

        <div className="permission-note"><strong>Você está no controle</strong><p>O Tela Viva não acessa nem controla seu computador. Câmera, microfone e tela só são usados após sua autorização explícita. Ao finalizar, todas as fontes locais e conexões ao vivo são encerradas.</p></div>
        {error && <p className="studio-error" role="alert">{error}</p>}
        {finishPending && <button className="secondary" disabled={lifecycleLoading} onClick={() => void retryFinish()}>{lifecycleLoading ? 'Confirmando…' : 'Confirmar encerramento no sistema'}</button>}

        <div className="studio-actions">
          {(state === 'preparing' || state === 'ended') && !finishPending && <button className="secondary" disabled={!hasPersistedClass} onClick={() => void preview()}>Ver preview</button>}
          {state === 'preview' && <button className="primary" disabled={!ready || lifecycleLoading} onClick={() => void startBroadcast()}>{lifecycleLoading ? 'Ativando aula…' : 'Iniciar transmissão'}</button>}
        </div>
        <small className="broadcast-note">Uma live só passa ao estado AO VIVO depois que a aula vinculada é ativada no backend. Sem confirmação do sistema, nenhum link é tratado como transmissão ativa.</small>
      </aside>
    </main>
  </div>
}
