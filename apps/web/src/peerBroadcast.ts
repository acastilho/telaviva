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
        const message = typeof error === 'string' && error.trim()
          ? error
          : 'Não foi possível estabelecer a conexão ao vivo.'
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
  const randomId = globalThis.crypto?.randomUUID?.()
  if (randomId) return randomId.replaceAll('-', '')

  return Array.from({ length: 32 }, () => Math.floor(Math.random() * 16).toString(16)).join('')
}

export function createViewerUrl(roomId: string) {
  const url = new URL(window.location.href)
  url.search = ''
  url.hash = ''
  url.searchParams.set('live', normalizeRoomId(roomId))
  return url.toString()
}
