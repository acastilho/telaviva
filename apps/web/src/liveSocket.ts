export type LiveSocketStatus = 'idle' | 'connecting' | 'connected' | 'reconnecting' | 'closed' | 'error'

export type LiveSocketEvent = {
  type: string
  [key: string]: unknown
}

type StoredSession = {
  accessToken?: string
}

const SESSION_KEY = 'tv_session_v1'
const configuredApiBase = (import.meta.env.VITE_API_URL as string | undefined)?.trim().replace(/\/$/, '') ?? ''
const configuredStreamId = (import.meta.env.VITE_HOMOLOG_STREAM_ID as string | undefined)?.trim() ?? ''
const configuredSocketPath = (import.meta.env.VITE_HOMOLOG_SOCKET_PATH as string | undefined)?.trim() ?? ''

function readAccessToken(): string | null {
  if (typeof window === 'undefined') return null
  const raw = window.sessionStorage.getItem(SESSION_KEY)
  if (!raw) return null
  try {
    const session = JSON.parse(raw) as StoredSession
    return typeof session.accessToken === 'string' && session.accessToken ? session.accessToken : null
  } catch {
    return null
  }
}

function websocketBase(apiBase: string): string {
  if (!apiBase) return ''
  if (apiBase.startsWith('https://')) return `wss://${apiBase.slice('https://'.length)}`
  if (apiBase.startsWith('http://')) return `ws://${apiBase.slice('http://'.length)}`
  if (apiBase.startsWith('wss://') || apiBase.startsWith('ws://')) return apiBase
  return ''
}

function normalizePath(path: string): string {
  if (!path) return ''
  return path.startsWith('/') ? path : `/${path}`
}

export function homologationLiveConfiguration() {
  const socketPath = configuredSocketPath
    ? normalizePath(configuredSocketPath)
    : configuredStreamId
      ? `/streams/${encodeURIComponent(configuredStreamId)}/live`
      : ''
  return {
    apiBase: configuredApiBase,
    socketPath,
    enabled: Boolean(configuredApiBase && socketPath),
  }
}

export class LiveSocketClient {
  private socket: WebSocket | null = null
  private reconnectTimer: number | null = null
  private stopped = false
  private reconnectAttempt = 0

  constructor(
    private readonly onEvent: (event: LiveSocketEvent) => void,
    private readonly onStatus: (status: LiveSocketStatus) => void,
  ) {}

  connect() {
    this.stopped = false
    this.open(false)
  }

  stop() {
    this.stopped = true
    if (this.reconnectTimer !== null) {
      window.clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    if (this.socket) {
      this.socket.onclose = null
      this.socket.close(1000, 'Client leaving live room')
      this.socket = null
    }
    this.onStatus('closed')
  }

  send(type: 'message' | 'question' | 'reaction', content: string): boolean {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) return false
    this.socket.send(JSON.stringify({ type, content }))
    return true
  }

  private open(reconnecting: boolean) {
    const { apiBase, socketPath, enabled } = homologationLiveConfiguration()
    const token = readAccessToken()
    const base = websocketBase(apiBase)

    if (!enabled || !token || !base) {
      this.onStatus('error')
      return
    }

    this.onStatus(reconnecting ? 'reconnecting' : 'connecting')
    const socket = new WebSocket(`${base}${socketPath}`)
    this.socket = socket

    socket.onopen = () => {
      this.reconnectAttempt = 0
      socket.send(JSON.stringify({ type: 'authenticate', token }))
    }

    socket.onmessage = (message) => {
      try {
        const event = JSON.parse(String(message.data)) as LiveSocketEvent
        if (event.type === 'ready') this.onStatus('connected')
        this.onEvent(event)
      } catch {
        this.onEvent({ type: 'error', code: 'invalid_server_payload' })
      }
    }

    socket.onerror = () => {
      this.onStatus('error')
    }

    socket.onclose = (event) => {
      if (this.socket === socket) this.socket = null
      if (this.stopped || event.code === 1000 || event.code === 1008) {
        this.onStatus(event.code === 1008 ? 'error' : 'closed')
        return
      }
      this.scheduleReconnect()
    }
  }

  private scheduleReconnect() {
    if (this.stopped || this.reconnectTimer !== null) return
    this.reconnectAttempt += 1
    const delay = Math.min(1000 * (2 ** Math.min(this.reconnectAttempt - 1, 4)), 15_000)
    this.onStatus('reconnecting')
    this.reconnectTimer = window.setTimeout(() => {
      this.reconnectTimer = null
      this.open(true)
    }, delay)
  }
}
