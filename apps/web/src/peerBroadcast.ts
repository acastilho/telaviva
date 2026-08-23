import { joinRoom } from 'trystero'

export type BroadcastMediaKind = 'screen' | 'camera' | 'microphone'
export type BroadcastRoom = ReturnType<typeof joinRoom>

const APP_ID = 'instituto-tela-viva-live-v1'

function normalizeRoomId(roomId: string) {
  return roomId.toLowerCase().replace(/[^a-z0-9]/g, '').slice(0, 64)
}

export function createLiveRoom(
  roomId: string,
  onJoinError?: (message: string) => void,
): BroadcastRoom {
  const normalized = normalizeRoomId(roomId)
  if (!normalized) throw new Error('Código de transmissão inválido.')

  return joinRoom(
    { appId: APP_ID },
    `live-${normalized}`,
    {
      onJoinError: ({ error }) => {
        const message = error instanceof Error ? error.message : 'Não foi possível estabelecer a conexão ao vivo.'
        onJoinError?.(message)
      },
    },
  )
}

export function publishStream(
  room: BroadcastRoom,
  stream: MediaStream,
  kind: BroadcastMediaKind,
  target?: string,
) {
  room.addStream(stream, {
    ...(target ? { target } : {}),
    metadata: { kind },
  })
}

export function unpublishStream(room: BroadcastRoom, stream: MediaStream) {
  room.removeStream(stream)
}

export function createRoomId() {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID().replaceAll('-', '')
  }

  const bytes = new Uint8Array(16)
  crypto.getRandomValues(bytes)
  return Array.from(bytes, (value) => value.toString(16).padStart(2, '0')).join('')
}

export function createViewerUrl(roomId: string) {
  const url = new URL(window.location.href)
  url.search = ''
  url.hash = ''
  url.searchParams.set('live', normalizeRoomId(roomId))
  return url.toString()
}
