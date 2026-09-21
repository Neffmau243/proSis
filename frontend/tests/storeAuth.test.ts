import type { AxiosResponse, InternalAxiosRequestConfig } from 'axios'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, expect, test, vi } from 'vitest'

import http from '@/services/http'
import {
  SESSION_STORAGE_KEY,
  clearSession,
  isSessionExpired,
  loadSession,
  saveSession,
  type PersistedSession,
} from '@/services/session-storage'
import { useAuthStore } from '@/stores/auth'

function session(overrides: Partial<PersistedSession> = {}): PersistedSession {
  return {
    access_token: 'a.b.c',
    expires_at: Date.now() + 3_600_000,
    usuario_id: 1,
    nombre_usuario: 'admin',
    roles: ['ADMIN'],
    permisos: ['PACIENTE_LEER', 'ATENCION_CREAR'],
    ...overrides,
  }
}

function stubLogin(payload: unknown): void {
  http.defaults.adapter = async (config: InternalAxiosRequestConfig) =>
    ({
      data: payload,
      status: 200,
      statusText: 'OK',
      headers: {},
      config,
    }) as AxiosResponse
}

beforeEach(() => {
  localStorage.clear()
  setActivePinia(createPinia())
  vi.useRealTimers()
})

test('la sesión persistida se descarta cuando falta el token o está corrupta', () => {
  expect(loadSession()).toBeNull()

  localStorage.setItem(SESSION_STORAGE_KEY, '{roto')
  expect(loadSession()).toBeNull()

  localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify({ access_token: '' }))
  expect(loadSession()).toBeNull()

  saveSession(session())
  expect(loadSession()?.access_token).toBe('a.b.c')

  clearSession()
  expect(loadSession()).toBeNull()
})

test('una sesión vencida se detecta por su marca de tiempo', () => {
  vi.useFakeTimers()
  vi.setSystemTime(new Date('2026-09-20T10:00:00Z'))
  const persisted = session({ expires_at: Date.now() + 1000 })

  expect(isSessionExpired(persisted)).toBe(false)

  vi.setSystemTime(new Date('2026-09-20T10:00:02Z'))
  expect(isSessionExpired(persisted)).toBe(true)
})

test('iniciar sesión guarda el vencimiento derivado de expires_in y llena el store', async () => {
  stubLogin({
    access_token: 'token-1',
    expires_in: 3600,
    usuario_id: 42,
    roles: ['PROFESIONAL'],
    permisos: ['ATENCION_CREAR'],
  })
  const before = Date.now()
  const store = useAuthStore()

  await store.login({ nombre_usuario: 'medico.demo', password: '12345678' })

  const persisted = loadSession()
  expect(persisted).not.toBeNull()
  expect(persisted!.access_token).toBe('token-1')
  expect(persisted!.usuario_id).toBe(42)
  // El login público no devuelve el nombre de usuario: se toma del formulario.
  expect(persisted!.nombre_usuario).toBe('medico.demo')
  expect(persisted!.expires_at).toBeGreaterThanOrEqual(before + 3_600_000)
  expect(persisted!.expires_at).toBeLessThanOrEqual(Date.now() + 3_600_000)

  expect(store.token).toBe('token-1')
  expect(store.usuarioId).toBe(42)
  expect(store.isAuthenticated).toBe(true)
  expect(store.isProfesional).toBe(true)
  expect(store.isAdmin).toBe(false)
})

test('un login fallido no deja sesión ni autentica al usuario', async () => {
  http.defaults.adapter = async (config: InternalAxiosRequestConfig) => {
    const { AxiosError } = await import('axios')
    throw new AxiosError('Unauthorized', 'ERR_BAD_REQUEST', config, null, {
      data: {
        error: {
          code: 'CREDENCIALES_INVALIDAS',
          message: 'Usuario o contraseña incorrectos.',
          details: null,
          request_id: null,
        },
      },
      status: 401,
      statusText: '',
      headers: {},
      config,
    } as AxiosResponse)
  }
  const store = useAuthStore()

  await expect(
    store.login({ nombre_usuario: 'medico.demo', password: '00000000' }),
  ).rejects.toThrow('Usuario o contraseña incorrectos.')

  expect(loadSession()).toBeNull()
  expect(store.isAuthenticated).toBe(false)
})

test('el store se hidrata desde localStorage y descarta una sesión vencida', () => {
  const store = useAuthStore()

  store.hydrateFromStorage()
  expect(store.isAuthenticated).toBe(false)

  saveSession(session({ roles: ['ADMIN'], permisos: ['USUARIO_GESTIONAR'] }))
  store.hydrateFromStorage()
  expect(store.isAdmin).toBe(true)
  expect(store.nombreUsuario).toBe('admin')
  expect(store.hasPermission('USUARIO_GESTIONAR')).toBe(true)
  expect(store.hasPermission('ATENCION_CREAR')).toBe(false)

  saveSession(session({ expires_at: Date.now() - 1 }))
  store.hydrateFromStorage()
  expect(store.isAuthenticated).toBe(false)
  expect(store.roles).toEqual([])
  // La sesión vencida no debe quedar guardada para el próximo arranque.
  expect(localStorage.getItem(SESSION_STORAGE_KEY)).toBeNull()
})

test('un permiso compuesto exige todos los permisos del token', async () => {
  saveSession(session({ permisos: ['PACIENTE_LEER', 'ATENCION_CREAR'] }))
  const store = useAuthStore()
  store.hydrateFromStorage()

  expect(store.hasPermission(['PACIENTE_LEER', 'ATENCION_CREAR'])).toBe(true)
  expect(store.hasPermission(['PACIENTE_LEER', 'AUDITORIA_LEER'])).toBe(false)
  expect(store.hasPermission([])).toBe(true)
})

test('cerrar sesión borra el token y todos los datos derivados', () => {
  saveSession(session())
  const store = useAuthStore()
  store.hydrateFromStorage()
  expect(store.isAuthenticated).toBe(true)

  store.logout()

  expect(loadSession()).toBeNull()
  expect(store.token).toBeNull()
  expect(store.usuarioId).toBeNull()
  expect(store.nombreUsuario).toBeNull()
  expect(store.permisos).toEqual([])
  expect(store.isAuthenticated).toBe(false)
})
