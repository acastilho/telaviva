export type ScheduledStream = {
  id: string
  creator_id: string
  title: string
  description: string
  objective: string
  starts_at: string
  estimated_duration_minutes: number
  category_id: string
  level: 'BEGINNER' | 'INTERMEDIATE' | 'ADVANCED' | 'ALL_LEVELS'
  price: string | number
  access_type: 'FREE' | 'PAID' | 'SUBSCRIBERS' | 'PRIVATE'
  created_at: string
  live_started_at?: string | null
  live_ended_at?: string | null
}

export type StreamCreatePayload = {
  title: string
  description?: string
  objective: string
  starts_at: string
  estimated_duration_minutes: number
  category_id: string
  level: ScheduledStream['level']
  price: string
  access_type: ScheduledStream['access_type']
}

export type StreamAccessResponse = {
  stream_id: string
  granted: boolean
  reason: string
  entitlement_id: string | null
  checked_at: string
  live_room_id: string | null
}

const configuredBase = (import.meta.env.VITE_API_URL as string | undefined)?.trim()
const API_BASE = configuredBase ? configuredBase.replace(/\/$/, '') : ''
const REQUEST_TIMEOUT_MS = 12_000

export const usesRemoteSchedulingApi = Boolean(API_BASE)

async function request<T>(path: string, init: RequestInit = {}, accessToken?: string): Promise<T> {
  if (!API_BASE) throw new Error('API de aulas não configurada.')
  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)
  try {
    const response = await fetch(`${API_BASE}${path}`, {
      ...init,
      signal: controller.signal,
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
        ...init.headers,
      },
    })
    if (!response.ok) {
      let detail = `Falha ao acessar aulas (${response.status}).`
      try {
        const body = await response.json() as { detail?: string }
        if (body.detail) detail = body.detail
      } catch {
        // Preserve the verified HTTP status when the upstream body is not JSON.
      }
      throw new Error(detail)
    }
    if (response.status === 204) return undefined as T
    return await response.json() as T
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new Error('A API de aulas demorou demais para responder.')
    }
    throw error
  } finally {
    window.clearTimeout(timer)
  }
}

export const schedulingClient = {
  listActive(): Promise<ScheduledStream[]> {
    return request<ScheduledStream[]>('/streams/active')
  },

  listUpcoming(creatorId?: string): Promise<ScheduledStream[]> {
    const query = new URLSearchParams({ starts_after: new Date().toISOString() })
    if (creatorId) query.set('creator_id', creatorId)
    return request<ScheduledStream[]>(`/streams?${query.toString()}`)
  },

  create(payload: StreamCreatePayload, accessToken: string): Promise<ScheduledStream> {
    return request<ScheduledStream>('/streams', { method: 'POST', body: JSON.stringify(payload) }, accessToken)
  },

  activate(streamId: string, roomId: string, accessToken: string): Promise<ScheduledStream> {
    return request<ScheduledStream>(`/streams/${encodeURIComponent(streamId)}/activate`, {
      method: 'POST', body: JSON.stringify({ room_id: roomId }),
    }, accessToken)
  },

  finish(streamId: string, accessToken: string): Promise<ScheduledStream> {
    return request<ScheduledStream>(`/streams/${encodeURIComponent(streamId)}/finish`, { method: 'POST' }, accessToken)
  },

  access(streamId: string, accessToken: string): Promise<StreamAccessResponse> {
    return request<StreamAccessResponse>(
      `/streams/${encodeURIComponent(streamId)}/access`,
      { method: 'POST' },
      accessToken,
    )
  },
}
