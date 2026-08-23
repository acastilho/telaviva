export type Audience = 'CHILD' | 'TEEN' | 'ADULT'
export type Role = 'VIEWER' | 'CREATOR' | 'ADMIN'

export type AuthUser = {
  id: string
  email: string
  role: Role
  audience: Audience
  guardian_email?: string | null
}

export type AuthSession = {
  accessToken: string
  refreshToken: string
  user: AuthUser
}

type TokenResponse = {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

type DemoUserRecord = AuthUser & {
  salt: string
  passwordHash: string
}

const configuredBase = (import.meta.env.VITE_API_URL as string | undefined)?.trim()
const API_BASE = configuredBase ? configuredBase.replace(/\/$/, '') : ''
const SESSION_KEY = 'tv_session_v1'
const DEMO_USERS_KEY = 'tv_homolog_users_v1'
const REQUEST_TIMEOUT_MS = 12_000

const isBrowser = () => typeof window !== 'undefined'

function readSession(): AuthSession | null {
  if (!isBrowser()) return null
  const raw = window.sessionStorage.getItem(SESSION_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw) as AuthSession
  } catch {
    window.sessionStorage.removeItem(SESSION_KEY)
    return null
  }
}

function saveSession(session: AuthSession | null) {
  if (!isBrowser()) return
  if (session) window.sessionStorage.setItem(SESSION_KEY, JSON.stringify(session))
  else window.sessionStorage.removeItem(SESSION_KEY)
}

function readDemoUsers(): DemoUserRecord[] {
  if (!isBrowser()) return []
  const raw = window.localStorage.getItem(DEMO_USERS_KEY)
  if (!raw) return []
  try {
    const parsed = JSON.parse(raw) as DemoUserRecord[]
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function saveDemoUsers(users: DemoUserRecord[]) {
  if (!isBrowser()) return
  window.localStorage.setItem(DEMO_USERS_KEY, JSON.stringify(users))
}

function bytesToBase64(bytes: Uint8Array): string {
  let binary = ''
  bytes.forEach((byte) => { binary += String.fromCharCode(byte) })
  return btoa(binary)
}

function base64ToBytes(value: string): Uint8Array {
  const binary = atob(value)
  return Uint8Array.from(binary, (char) => char.charCodeAt(0))
}

function fallbackDigest(value: string): string {
  let first = 0x811c9dc5
  let second = 0x9e3779b9
  for (let index = 0; index < value.length; index += 1) {
    const code = value.charCodeAt(index)
    first ^= code
    first = Math.imul(first, 0x01000193)
    second ^= code + index
    second = Math.imul(second, 0x85ebca6b)
  }
  return `${(first >>> 0).toString(16).padStart(8, '0')}${(second >>> 0).toString(16).padStart(8, '0')}`
}

async function hashDemoPassword(password: string, salt: Uint8Array): Promise<string> {
  if (globalThis.crypto?.subtle) {
    const key = await globalThis.crypto.subtle.importKey(
      'raw',
      new TextEncoder().encode(password),
      'PBKDF2',
      false,
      ['deriveBits'],
    )
    const bits = await globalThis.crypto.subtle.deriveBits(
      { name: 'PBKDF2', hash: 'SHA-256', salt, iterations: 120_000 },
      key,
      256,
    )
    return bytesToBase64(new Uint8Array(bits))
  }
  return fallbackDigest(`${bytesToBase64(salt)}:${password}`)
}

function randomBytes(size: number): Uint8Array {
  const bytes = new Uint8Array(size)
  if (globalThis.crypto?.getRandomValues) return globalThis.crypto.getRandomValues(bytes)
  for (let index = 0; index < size; index += 1) bytes[index] = Math.floor(Math.random() * 256)
  return bytes
}

function randomId(): string {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID()
  return `homolog-${Date.now()}-${Math.random().toString(36).slice(2)}`
}

async function apiRequest<T>(path: string, init: RequestInit = {}, accessToken?: string): Promise<T> {
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
      let detail = 'Não foi possível concluir a operação.'
      try {
        const body = await response.json() as { detail?: string }
        if (body.detail) detail = body.detail
      } catch {
        // Keep the generic message. Never leak an upstream response body.
      }
      throw new Error(detail)
    }
    if (response.status === 204) return undefined as T
    return await response.json() as T
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new Error('A conexão demorou demais. Tente novamente.')
    }
    throw error
  } finally {
    window.clearTimeout(timer)
  }
}

async function remoteLogin(email: string, password: string): Promise<AuthSession> {
  const tokens = await apiRequest<TokenResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })
  const user = await apiRequest<AuthUser>('/auth/me', {}, tokens.access_token)
  const session = { accessToken: tokens.access_token, refreshToken: tokens.refresh_token, user }
  saveSession(session)
  return session
}

async function demoRegister(
  email: string,
  password: string,
  audience: Audience,
  guardianEmail?: string,
): Promise<AuthSession> {
  const normalizedEmail = email.trim().toLowerCase()
  const users = readDemoUsers()
  if (users.some((user) => user.email === normalizedEmail)) throw new Error('Este e-mail já possui uma conta.')
  if (password.length < 12) throw new Error('Use uma senha com pelo menos 12 caracteres.')
  if (audience === 'CHILD' && !guardianEmail?.trim()) {
    throw new Error('A área infantil exige o e-mail de um responsável.')
  }
  const salt = randomBytes(16)
  const passwordHash = await hashDemoPassword(password, salt)
  const user: AuthUser = {
    id: randomId(),
    email: normalizedEmail,
    role: 'VIEWER',
    audience,
    guardian_email: guardianEmail?.trim().toLowerCase() || null,
  }
  saveDemoUsers([...users, { ...user, salt: bytesToBase64(salt), passwordHash }])
  const session = { accessToken: randomId(), refreshToken: randomId(), user }
  saveSession(session)
  return session
}

async function demoLogin(email: string, password: string): Promise<AuthSession> {
  const normalizedEmail = email.trim().toLowerCase()
  const record = readDemoUsers().find((user) => user.email === normalizedEmail)
  if (!record) throw new Error('E-mail ou senha inválidos.')
  const candidate = await hashDemoPassword(password, base64ToBytes(record.salt))
  if (candidate !== record.passwordHash) throw new Error('E-mail ou senha inválidos.')
  const { salt: _salt, passwordHash: _passwordHash, ...user } = record
  const session = { accessToken: randomId(), refreshToken: randomId(), user }
  saveSession(session)
  return session
}

export const authClient = {
  usesRemoteApi: Boolean(API_BASE),

  async restore(): Promise<AuthSession | null> {
    const session = readSession()
    if (!session) return null
    if (!API_BASE) return session
    try {
      const user = await apiRequest<AuthUser>('/auth/me', {}, session.accessToken)
      const refreshed = { ...session, user }
      saveSession(refreshed)
      return refreshed
    } catch {
      try {
        const tokens = await apiRequest<TokenResponse>('/auth/refresh', {
          method: 'POST',
          body: JSON.stringify({ refresh_token: session.refreshToken }),
        })
        const user = await apiRequest<AuthUser>('/auth/me', {}, tokens.access_token)
        const refreshed = { accessToken: tokens.access_token, refreshToken: tokens.refresh_token, user }
        saveSession(refreshed)
        return refreshed
      } catch {
        saveSession(null)
        return null
      }
    }
  },

  async login(email: string, password: string): Promise<AuthSession> {
    if (API_BASE) return remoteLogin(email.trim().toLowerCase(), password)
    return demoLogin(email, password)
  },

  async register(
    email: string,
    password: string,
    audience: Audience,
    guardianEmail?: string,
  ): Promise<AuthSession> {
    if (!API_BASE) return demoRegister(email, password, audience, guardianEmail)
    await apiRequest<AuthUser>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({
        email: email.trim().toLowerCase(),
        password,
        audience,
        guardian_email: guardianEmail?.trim().toLowerCase() || null,
      }),
    })
    return remoteLogin(email.trim().toLowerCase(), password)
  },

  async recover(email: string): Promise<void> {
    if (!API_BASE) return
    await apiRequest('/auth/password-recovery', {
      method: 'POST',
      body: JSON.stringify({ email: email.trim().toLowerCase() }),
    })
  },

  async logout(): Promise<void> {
    const session = readSession()
    if (session && API_BASE) {
      try {
        await apiRequest('/auth/logout', {
          method: 'POST',
          body: JSON.stringify({ refresh_token: session.refreshToken }),
        })
      } catch {
        // Local cleanup still happens when the upstream session is already unavailable.
      }
    }
    saveSession(null)
  },
}
