import http from './http'
import type { LoginResponse } from '@/types/api'

export interface LoginPayload {
  nombre_usuario: string
  password: string
}

interface LoginUsernameOption {
  nombre_usuario: string
}

export async function login(payload: LoginPayload): Promise<LoginResponse> {
  const { data } = await http.post<LoginResponse>('/auth/login', payload)
  return data
}

export async function listActiveLoginUsernames(): Promise<string[]> {
  const { data } = await http.get<LoginUsernameOption[]>('/auth/usuarios-activos')
  return data.map((item) => item.nombre_usuario)
}

/** PUT /auth/me/password responde 204 sin cuerpo. */
export async function changeMyPassword(payload: {
  current_password: string
  new_password: string
  new_password_confirmation: string
}): Promise<void> {
  await http.put('/auth/me/password', payload)
}
