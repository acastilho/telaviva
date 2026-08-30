import type { AuthUser, Role } from './auth'

const configuredBase = (import.meta.env.VITE_API_URL as string | undefined)?.trim()
const API_BASE = configuredBase ? configuredBase.replace(/\/$/, '') : ''
const REQUEST_TIMEOUT_MS = 12_000

async function apiRequest<T>(path: string, accessToken: string, init: RequestInit = {}): Promise<T> {
  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)
  try {
    const response = await fetch(`${API_BASE}${path}`, {
      ...init,
      signal: controller.signal,
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
        Authorization: `Bearer ${accessToken}`,
        ...init.headers,
      },
    })
    if (!response.ok) {
      let detail = 'Não foi possível concluir a operação administrativa.'
      try {
        const body = await response.json() as { detail?: string }
        if (body.detail) detail = body.detail
      } catch {
        // Preserve the generic message when the upstream response has no JSON detail.
      }
      throw new Error(detail)
    }
    return await response.json() as T
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new Error('A conexão com a administração demorou demais.')
    }
    throw error
  } finally {
    window.clearTimeout(timer)
  }
}

export const adminClient = {
  usesRemoteApi: Boolean(API_BASE),

  listUsers(accessToken: string): Promise<AuthUser[]> {
    return apiRequest<AuthUser[]>('/auth/users', accessToken)
  },

  updateUserRole(userId: string, role: Role, accessToken: string): Promise<AuthUser> {
    return apiRequest<AuthUser>(`/auth/users/${userId}/role`, accessToken, {
      method: 'PATCH',
      body: JSON.stringify({ role }),
    })
  },
}
