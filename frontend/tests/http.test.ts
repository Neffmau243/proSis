import { AxiosError, type AxiosResponse, type InternalAxiosRequestConfig } from 'axios'
import { beforeEach, expect, test, vi } from 'vitest'

import router from '@/router'
import http, { ApiError } from '@/services/http'
import { SESSION_STORAGE_KEY } from '@/services/session-storage'

vi.mock('@/router', () => ({
  default: {
    currentRoute: { value: { name: 'inicio', fullPath: '/?filtro=HC-1' } },
    push: vi.fn(),
  },
}))

interface AdapterResult {
  status?: number
  data?: unknown
}

let lastRequest: InternalAxiosRequestConfig | null = null

function respondWith(handler: (config: InternalAxiosRequestConfig) => AdapterResult): void {
  http.defaults.adapter = async (config) => {
    lastRequest = config
    const { status = 200, data = null } = handler(config)
    const response = {
      data,
      status,
      statusText: '',
      headers: {},
      config,
    } as AxiosResponse
    if (status >= 400) {
      throw new AxiosError('Request failed', 'ERR_BAD_RESPONSE', config, null, response)
    }
    return response
  }
}

function persistSession(payload: unknown): void {
  localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(payload))
}

beforeEach(() => {
  localStorage.clear()
  lastRequest = null
  vi.mocked(router.push).mockClear()
})

test('el cliente apunta al prefijo versionado de la API y espera un tiempo acotado', () => {
  expect(http.defaults.baseURL).toBe('/api/v1')
  expect(http.defaults.timeout).toBe(15000)
})

test('el token guardado se agrega como Bearer en cada petición', async () => {
  persistSession({ access_token: 'abc.def.ghi' })
  respondWith(() => ({ data: { ok: true } }))

  await http.get('/patients')

  expect(lastRequest?.headers.Authorization).toBe('Bearer abc.def.ghi')
})

test('sin sesión, o con una sesión corrupta, la petición sale sin token', async () => {
  respondWith(() => ({ data: {} }))
  await http.get('/patients')
  expect(lastRequest?.headers.Authorization).toBeUndefined()

  localStorage.setItem(SESSION_STORAGE_KEY, '{no-es-json')
  await http.get('/patients')
  expect(lastRequest?.headers.Authorization).toBeUndefined()

  persistSession({ expires_at: 1 })
  await http.get('/patients')
  expect(lastRequest?.headers.Authorization).toBeUndefined()
})

test('el sobre de error del backend se convierte en ApiError con su código y request id', async () => {
  respondWith(() => ({
    status: 422,
    data: {
      error: {
        code: 'RANGOS_ETARIOS_SUPERPUESTOS',
        message: 'Los rangos se superponen.',
        details: { codigo: 'NINO' },
        request_id: 'req-1',
      },
    },
  }))

  const error = await http.get('/configuracion/grupos-etarios').catch((cause) => cause)

  expect(error).toBeInstanceOf(ApiError)
  expect(error.message).toBe('Los rangos se superponen.')
  expect(error.status).toBe(422)
  expect(error.code).toBe('RANGOS_ETARIOS_SUPERPUESTOS')
  expect(error.details).toEqual({ codigo: 'NINO' })
  expect(error.requestId).toBe('req-1')
  expect(error.name).toBe('ApiError')
})

test('un error sin sobre conserva el status y no inventa códigos', async () => {
  respondWith(() => ({ status: 502, data: '<html>Bad Gateway</html>' }))

  const error = await http.get('/patients').catch((cause) => cause)

  expect(error).toBeInstanceOf(ApiError)
  expect(error.message).toBe('La solicitud no pudo completarse.')
  expect(error.status).toBe(502)
  expect(error.code).toBeNull()
  expect(error.details).toBeNull()
  expect(error.requestId).toBeNull()
})

test('sin respuesta del servidor se explica que el backend está apagado', async () => {
  http.defaults.adapter = async (config) => {
    throw new AxiosError('Network Error', 'ERR_NETWORK', config)
  }

  const error = await http.get('/patients').catch((cause) => cause)

  expect(error).toBeInstanceOf(ApiError)
  expect(error.message).toMatch(/No se pudo conectar con el servidor/)
  expect(error.status).toBeNull()
})

test('un 401 fuera del login borra la sesión y devuelve al usuario al login', async () => {
  persistSession({ access_token: 'expirado', expires_at: Date.now() + 1000 })
  respondWith(() => ({
    status: 401,
    data: {
      error: { code: 'SESSION_EXPIRED', message: 'Sesión expirada.', details: null, request_id: null },
    },
  }))

  await expect(http.get('/patients')).rejects.toBeInstanceOf(ApiError)

  expect(localStorage.getItem(SESSION_STORAGE_KEY)).toBeNull()
  expect(router.push).toHaveBeenCalledWith({
    name: 'login',
    query: { redirect: '/?filtro=HC-1' },
  })
})

test('el 401 del propio login no redirige ni borra nada', async () => {
  const currentRoute = router.currentRoute as { value: { name: string; fullPath: string } }
  currentRoute.value = { name: 'login', fullPath: '/login' }
  respondWith(() => ({
    status: 401,
    data: {
      error: { code: 'CREDENCIALES_INVALIDAS', message: 'Datos incorrectos.', details: null, request_id: null },
    },
  }))

  const error = await http.post('/auth/login', {}).catch((cause) => cause)

  expect(error.code).toBe('CREDENCIALES_INVALIDAS')
  expect(router.push).not.toHaveBeenCalled()
  currentRoute.value = { name: 'inicio', fullPath: '/?filtro=HC-1' }
})
