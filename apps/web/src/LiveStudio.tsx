import { useEffect, useRef, useState } from 'react'
import { BrandMark } from './BrandMark'

type Layout = 'screen' | 'screen-camera' | 'camera'
type LiveState = 'preparing' | 'preview' | 'live' | 'paused' | 'ended'
type InteractionChannel = 'chat' | 'questions' | 'reactions'

const stopStream = (stream: MediaStream | null) => stream?.getTracks().forEach((track) => track.stop())

function Video({ stream, muted, label }: { stream: MediaStream | null; muted: boolean; label: string }) {
  const ref = useRef<HTMLVideoElement>(null)
  useEffect(() => {
    if (ref.current) ref.current.srcObject = stream
  }, [stream])
  return stream ? <video ref={ref} autoPlay playsInline muted={muted} aria-label={label} /> : null
}

export function LiveStudio({ onClose }: { onClose: () => void }) {
  const [layout, setLayout] = useState<Layout>('screen')
  const [state, setState] = useState<LiveState>('preparing')
  const [screen, setScreen] = useState<MediaStream | null>(null)
  const [camera, setCamera] = useState<MediaStream | null>(null)
  const [microphone, setMicrophone] = useState<MediaStream | null>(null)
  const [cameraEnabled, setCameraEnabled] = useState(false)
  const [micEnabled, setMicEnabled] = useState(true)
  const [error, setError] = useState('')
  const [interactions, setInteractions] = useState<Record<InteractionChannel, boolean>>({
    chat: true,
    questions: true,
    reactions: true,
  })
  const screenRef = useRef<MediaStream | null>(null)
  const cameraRef = useRef<MediaStream | null>(null)
  const microphoneRef = useRef<MediaStream | null>(null)

  const replaceStream = (kind: 'screen' | 'camera' | 'microphone', next: MediaStream | null) => {
    const refs = { screen: screenRef, camera: cameraRef, microphone: microphoneRef }
    const setters = { screen: setScreen, camera: setCamera, microphone: setMicrophone }
    stopStream(refs[kind].current)
    refs[kind].current = next
    setters[kind](next)
  }

  useEffect(() => () => {
    stopStream(screenRef.current)
    stopStream(cameraRef.current)
    stopStream(microphoneRef.current)
  }, [])

  const requestScreen = async () => {
    setError('')
    if (!navigator.mediaDevices?.getDisplayMedia) {
      setError('Este navegador não oferece compartilhamento de tela.')
      return false
    }
    try {
      const privacyConstraints = {
        video: true,
        audio: false,
        // Prefer a tab and keep this application's own tab out of the picker where supported.
        preferCurrentTab: true,
        selfBrowserSurface: 'exclude',
        surfaceSwitching: 'include',
      } as DisplayMediaStreamOptions
      const next = await navigator.mediaDevices.getDisplayMedia(privacyConstraints)
      const track = next.getVideoTracks()[0]
      track?.addEventListener('ended', () => {
        if (screenRef.current === next) {
          screenRef.current = null
          setScreen(null)
          if (layout !== 'camera') setState('preparing')
        }
      }, { once: true })
      replaceStream('screen', next)
      return true
    } catch {
      setError('Compartilhamento não autorizado. Escolha uma fonte no seletor do navegador para continuar.')
      return false
    }
  }

  const requestCamera = async () => {
    setError('')
    try {
      const next = await navigator.mediaDevices.getUserMedia({ video: true, audio: false })
      replaceStream('camera', next)
      setCameraEnabled(true)
      return true
    } catch {
      setCameraEnabled(false)
      setError('Não foi possível acessar a câmera. Verifique a permissão do navegador.')
      return false
    }
  }

  const requestMicrophone = async () => {
    setError('')
    try {
      const next = await navigator.mediaDevices.getUserMedia({ video: false, audio: true })
      replaceStream('microphone', next)
      setMicEnabled(true)
    } catch {
      setMicEnabled(false)
      setError('Não foi possível acessar o microfone. Você pode continuar sem áudio.')
    }
  }

  const preview = async () => {
    const hasVideo = layout === 'camera' ? (camera || await requestCamera()) : (screen || await requestScreen())
    if (!hasVideo) return
    if (layout === 'screen-camera' && !camera) await requestCamera()
    if (micEnabled && !microphone) await requestMicrophone()
    setState('preview')
  }

  const toggleCamera = async () => {
    if (cameraEnabled) {
      replaceStream('camera', null)
      setCameraEnabled(false)
      if (layout === 'camera') setLayout(screen ? 'screen' : 'camera')
    } else await requestCamera()
  }

  const toggleMic = async () => {
    if (!microphone) return requestMicrophone()
    const enabled = !micEnabled
    microphone.getAudioTracks().forEach((track) => { track.enabled = enabled })
    setMicEnabled(enabled)
  }

  const pause = () => {
    screen?.getVideoTracks().forEach((track) => { track.enabled = false })
    camera?.getVideoTracks().forEach((track) => { track.enabled = false })
    setState('paused')
  }

  const resume = () => {
    screen?.getVideoTracks().forEach((track) => { track.enabled = true })
    camera?.getVideoTracks().forEach((track) => { track.enabled = true })
    setState('live')
  }

  const finish = () => {
    replaceStream('screen', null)
    replaceStream('camera', null)
    replaceStream('microphone', null)
    setCameraEnabled(false)
    setMicEnabled(false)
    setState('ended')
  }

  const needsScreen = layout !== 'camera'
  const ready = (needsScreen ? !!screen : !!camera) && state !== 'ended'
  const toggleInteraction = (channel: InteractionChannel) => {
    setInteractions((current) => ({ ...current, [channel]: !current[channel] }))
  }

  return <div className="studio-shell" role="dialog" aria-modal="true" aria-labelledby="studio-title">
    <header className="studio-header">
      <a className="brand institute-brand-link" href="#inicio" aria-label="Instituto Tela Viva"><BrandMark /></a>
      <span className={`studio-status ${state}`}>{state === 'live' ? '● AO VIVO' : state === 'paused' ? 'Ⅱ PAUSADA' : state === 'ended' ? 'FINALIZADA' : 'ESTÚDIO'}</span>
      <button className="studio-close" onClick={() => { finish(); onClose() }} aria-label="Fechar estúdio">×</button>
    </header>
    <main className="studio-main">
      <section className="studio-preview-panel">
        <div className={`video-stage layout-${layout}`}>
          {state === 'paused' && <div className="stage-message"><strong>Transmissão pausada</strong><span>Seu vídeo está temporariamente oculto.</span></div>}
          {state === 'ended' && <div className="stage-message"><strong>Live finalizada</strong><span>As fontes foram desconectadas com segurança.</span></div>}
          {state !== 'paused' && state !== 'ended' && <>
            {needsScreen && <Video stream={screen} muted label="Prévia da tela compartilhada" />}
            {(layout === 'camera' || layout === 'screen-camera') && <Video stream={camera} muted label="Prévia da câmera" />}
            {!ready && <div className="stage-message"><span className="stage-icon">▣</span><strong>Sua prévia aparecerá aqui</strong><span>Nenhuma fonte é acessada sem sua autorização.</span></div>}
          </>}
        </div>
        <div className="studio-controls" aria-label="Controles da transmissão">
          {state === 'live' && <button onClick={pause}>Ⅱ <span>Pausar</span></button>}
          {state === 'paused' && <button onClick={resume}>▶ <span>Retomar</span></button>}
          <button onClick={toggleMic} aria-pressed={!micEnabled}>{micEnabled ? '◉' : '⊘'} <span>{micEnabled ? 'Silenciar' : 'Ativar microfone'}</span></button>
          <button onClick={toggleCamera} aria-pressed={cameraEnabled}>▣ <span>{cameraEnabled ? 'Desligar câmera' : 'Ligar câmera'}</span></button>
          {needsScreen && <button onClick={requestScreen}>↻ <span>Trocar fonte</span></button>}
          {(state === 'live' || state === 'paused') && <button className="danger" onClick={finish}>■ <span>Finalizar</span></button>}
        </div>
      </section>
      <aside className="studio-settings">
        <p className="eyebrow">CONFIGURAÇÃO</p><h1 id="studio-title">Prepare sua live</h1>
        <fieldset><legend>Layout</legend>
          <label><input type="radio" name="layout" checked={layout === 'screen'} onChange={() => setLayout('screen')} /><span>▱</span><b>Tela</b></label>
          <label><input type="radio" name="layout" checked={layout === 'screen-camera'} onChange={() => setLayout('screen-camera')} /><span>▰</span><b>Tela + câmera</b></label>
          <label><input type="radio" name="layout" checked={layout === 'camera'} onChange={() => setLayout('camera')} /><span>▣</span><b>Somente câmera</b></label>
        </fieldset>
        <fieldset className="interaction-settings"><legend>Interação ao vivo</legend>
          <label><input type="checkbox" checked={interactions.chat} onChange={() => toggleInteraction('chat')} /><span aria-hidden="true">☵</span><b>Chat</b></label>
          <label><input type="checkbox" checked={interactions.questions} onChange={() => toggleInteraction('questions')} /><span aria-hidden="true">?</span><b>Perguntas</b></label>
          <label><input type="checkbox" checked={interactions.reactions} onChange={() => toggleInteraction('reactions')} /><span aria-hidden="true">♡</span><b>Reações</b></label>
        </fieldset>
        <p className="interaction-note" role="status">
          {Object.values(interactions).filter(Boolean).length} de 3 canais habilitados. Você pode alterá-los durante a live.
        </p>
        {needsScreen && <div className="source-card"><div><strong>Monitor, janela ou aba</strong><p>O navegador abrirá um seletor seguro para você escolher exatamente o que compartilhar.</p></div><button className="secondary" onClick={requestScreen}>{screen ? 'Trocar fonte' : 'Escolher fonte'}</button></div>}
        <div className="permission-note"><strong>Você está no controle</strong><p>O Instituto Tela Viva não acessa nem controla seu computador. O compartilhamento só começa após sua autorização explícita e pode ser interrompido a qualquer momento.</p></div>
        {error && <p className="studio-error" role="alert">{error}</p>}
        <div className="studio-actions">
          {(state === 'preparing' || state === 'ended') && <button className="secondary" onClick={preview}>Ver preview</button>}
          {state === 'preview' && <button className="primary" disabled={!ready} onClick={() => setState('live')}>Iniciar transmissão</button>}
        </div>
        <small className="broadcast-note">A versão atual prepara e controla as fontes locais. A distribuição para espectadores será conectada ao provedor de vídeo.</small>
      </aside>
    </main>
  </div>
}
