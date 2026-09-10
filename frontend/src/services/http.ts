import axios, { AxiosError, type AxiosInstance, type InternalAxiosRequestConfig } from 'axios'

import router from '@/router'
import { clearSession } from '@/services/session-storage'
import type { ApiErrorEnvelope } from '@/types/api'

/** Error normalizado con los campos del sobre del backend, listo para mostrar. */
export class ApiError extends Error {
  status: number | null
  code: string | null
  details: unknown
  requestId: string | null

  constructor(
    message: string,
    options: {
      status?: number | null
      code?: string | null
      details?: unknown
      requestId?: string | null
    } = {},
  ) {
    super(message)
    this.name = 'ApiError'
    this.status = options.status ?? null
    this.code = options.code ?? null
    this.details = options.details ?? null
    this.requestId = options.requestId ?? null
  }
}

const http: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? '/api/v1',
  timeout: 15000,
})

http.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  // Se lee de localStorage directamente para no acoplar el cliente HTTP al
  // store de Pinia (evita ciclos de importación).
  const raw = localStorage.getItem('ipress:session')
  if (raw) {
    try {
      const session = JSON.parse(raw) as { access_token?: string }
      if (session.access_token) {
        config.headers.Authorization = `Bearer ${session.access_token}`
      }
    } catch {
      // Sesión corrupta: se ignora y la petición sale sin token.
    }
  }
  return config
})

http.interceptors.response.use(
  (response) => response,
  (error: AxiosError<ApiErrorEnvelope>) => {
    // 401 en cualquier endpoint (menos el propio login): la sesión caducó o
    // fue invalidada por el backend (cambio de contraseña, baja de usuario).
    if (error.response?.status === 401 && router.currentRoute.value.name !== 'login') {
      clearSession()
      router.push({ name: 'login', query: { redirect: router.currentRoute.value.fullPath } })
    }

    const envelope = error.response?.data?.error
    if (envelope) {
      return Promise.reject(
        new ApiError(envelope.message, {
          status: error.response?.status ?? null,
          code: envelope.code,
          details: envelope.details,
          requestId: envelope.request_id,
        }),
      )
    }

    if (error.response) {
      return Promise.reject(
        new ApiError('La solicitud no pudo completarse.', {
          status: error.response.status,
        }),
      )
    }

    return Promise.reject(
      new ApiError('No se pudo conectar con el servidor. Verifique que el backend esté iniciado.'),
    )
  },
)

export default http