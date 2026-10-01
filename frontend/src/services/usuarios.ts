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

export interface PasswordResetPayload {
  new_password: string
  new_password_confirmation: string
}

export const usuarios = {
  /** `incluir_inactivos` es el único filtro que acepta el backend. */
  async list(incluirInactivos = false): Promise<UserResponse[]> {
    const { data } = await http.get<UserResponse[]>('/usuarios', {
      params: incluirInactivos ? { incluir_inactivos: true } : undefined,
    })
    return data
  },
  async create(payload: UserCreatePayload): Promise<UserResponse> {
    const { data } = await http.post<UserResponse>('/usuarios', payload)
    return data
  },
  async updateRoles(id: number, roles: string[]): Promise<UserResponse> {
    const { data } = await http.put<UserResponse>(`/usuarios/${id}/roles`, { roles })
    return data
  },
  async resetPassword(id: number, payload: PasswordResetPayload): Promise<void> {
    await http.put(`/usuarios/${id}/password`, payload)
  },
  async deactivate(id: number): Promise<UserResponse> {
    const { data } = await http.delete<UserResponse>(`/usuarios/${id}`)
    return data
  },
}
