import http from './http'
import type { LoginResponse } from '@/types/api'

export interface LoginPayload {
  nombre_usuario: string
  password: string
}

export async function login(payload: LoginPayload): Promise<LoginResponse> {
  const { data } = await http.post<LoginResponse>('/auth/login', payload)
  return data
}

/** PUT /auth/me/password responde 204 sin cuerpo. */
export async function changeMyPassword(payload: {
  current_password: string
  new_password: string
}): Promise<void> {
  await http.put('/auth/me/password', payload)
}