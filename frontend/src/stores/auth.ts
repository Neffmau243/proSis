import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import * as authApi from '@/services/auth'
import {
  clearSession,
  isSessionExpired,
  loadSession,
  saveSession,
  type PersistedSession,
} from '@/services/session-storage'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(null)
  const usuarioId = ref<number | null>(null)
  const nombreUsuario = ref<string | null>(null)
  const roles = ref<string[]>([])
  const permisos = ref<string[]>([])

  function reset(): void {
    token.value = null
    usuarioId.value = null
    nombreUsuario.value = null
    roles.value = []
    permisos.value = []
  }

  /** Hidrata el store desde localStorage; si la sesión venció, la descarta. */
  function hydrateFromStorage(): void {
    const session = loadSession()
    if (!session || isSessionExpired(session)) {
      if (session) clearSession()
      reset()
      return
    }
    token.value = session.access_token
    usuarioId.value = session.usuario_id
    nombreUsuario.value = session.nombre_usuario
    roles.value = session.roles
    permisos.value = session.permisos
  }

  const isAuthenticated = computed(() => token.value !== null)
  const isAdmin = computed(() => roles.value.includes('ADMIN'))
  const isProfesional = computed(() => roles.value.includes('PROFESIONAL'))

  /** Un usuario necesita TODOS los permisos indicados (los trae el login). */
  function hasPermission(required: string | string[]): boolean {
    const needed = Array.isArray(required) ? required : [required]
    return needed.every((permission) => permisos.value.includes(permission))
  }

  async function login(payload: { nombre_usuario: string; password: string }): Promise<void> {
    const response = await authApi.login(payload)
    const session: PersistedSession = {
      access_token: response.access_token,
      expires_at: Date.now() + response.expires_in * 1000,
      usuario_id: response.usuario_id,
      nombre_usuario: payload.nombre_usuario,
      roles: response.roles,
      permisos: response.permisos,
    }
    saveSession(session)
    hydrateFromStorage()
  }

  function logout(): void {
    clearSession()
    reset()
  }

  return {
    token,
    usuarioId,
    nombreUsuario,
    roles,
    permisos,
    isAuthenticated,
    isAdmin,
    isProfesional,
    hasPermission,
    login,
    logout,
    hydrateFromStorage,
  }
})