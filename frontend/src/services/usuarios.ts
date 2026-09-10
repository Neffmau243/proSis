import http from './http'

export interface UserResponse {
  id: number
  profesional_id: number | null
  nombre_usuario: string
  activo: boolean
  ultimo_acceso_at: string | null
  created_at: string
  updated_at: string
  roles: string[]
}

export interface UserCreatePayload {
  profesional_id?: number | null
  nombre_usuario: string
  password: string
  roles: string[]
}

export const usuarios = {
  async create(payload: UserCreatePayload): Promise<UserResponse> {
    const { data } = await http.post<UserResponse>('/usuarios', payload)
    return data
  },
}