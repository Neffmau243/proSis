/**
 * Persistencia de la sesión en localStorage.
 *
 * Este módulo es la única fuente de verdad para "¿hay sesión activa?" y lo
 * consumen tanto el store de auth como el router (guards) y el cliente HTTP
 * (401), evitando importaciones circulares.
 */

export const SESSION_STORAGE_KEY = 'ipress:session'

export interface PersistedSession {
  access_token: string
  /** Época en milisegundos en la que vence la sesión (expires_in del login). */
  expires_at: number
  usuario_id: number
  nombre_usuario: string | null
  roles: string[]
  permisos: string[]
}

export function loadSession(): PersistedSession | null {
  const raw = localStorage.getItem(SESSION_STORAGE_KEY)
  if (!raw) return null
  try {
    const parsed = JSON.parse(raw) as PersistedSession
    if (typeof parsed.access_token !== 'string' || !parsed.access_token) {
      return null
    }
    return parsed
  } catch {
    return null
  }
}

export function saveSession(session: PersistedSession): void {
  localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(session))
}

export function clearSession(): void {
  localStorage.removeItem(SESSION_STORAGE_KEY)
}

export function isSessionExpired(session: PersistedSession): boolean {
  return Date.now() >= session.expires_at
}