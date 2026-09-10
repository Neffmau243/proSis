/** Forma del sobre de error que expone el backend (app/exceptions/handlers.py). */
export interface ApiErrorEnvelope {
  error: {
    code: string
    message: string
    details: unknown
    request_id: string | null
  }
}

/** Forma de toda respuesta paginada del backend. */
export interface PageResponse<T> {
  items: T[]
  total: number
  limit: number
  offset: number
  has_more: boolean
}

/** Respuesta de POST /auth/login. */
export interface LoginResponse {
  access_token: string
  expires_in: number
  usuario_id: number
  roles: string[]
  permisos: string[]
}