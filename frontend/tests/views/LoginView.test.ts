import { flushPromises, mount } from '@vue/test-utils'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import ElementPlus from 'element-plus'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import LoginAccessForm from '@/components/auth/LoginAccessForm.vue'
import type { LoginPayload } from '@/services/auth'
import { SESSION_STORAGE_KEY } from '@/services/session-storage'
import type { LoginResponse } from '@/types/api'
import LoginView from '@/views/LoginView.vue'

const { login, listActiveLoginUsernames } = vi.hoisted(() => ({
  login: vi.fn<(payload: LoginPayload) => Promise<LoginResponse>>(),
  listActiveLoginUsernames: vi.fn<() => Promise<string[]>>(),
}))

vi.mock('@/services/auth', () => ({
  login,
  listActiveLoginUsernames,
  changeMyPassword: vi.fn(),
}))

function loginResponse() {
  return {
    access_token: 'token-1',
    expires_in: 3600,
    usuario_id: 1,
    roles: ['ADMIN'],
    permisos: [],
  }
}

const mounted: { unmount: () => void }[] = []

async function mountLogin(query: Record<string, string> = {}) {
  const stub = { template: '<div />' }
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/login', name: 'login', component: stub },
      { path: '/', name: 'inicio', component: stub },
      { path: '/atenciones', name: 'atenciones', component: stub },
    ],
  })
  const pinia = createPinia()
  setActivePinia(pinia)
  await router.push({ name: 'login', query })
  await router.isReady()

  const wrapper = mount(LoginView, {
    global: { plugins: [router, pinia, ElementPlus], components: ElementPlusIconsVue },
  })
  mounted.push(wrapper)
  await flushPromises()
  return { wrapper, router }
}

beforeEach(() => {
  localStorage.clear()
  vi.clearAllMocks()
  listActiveLoginUsernames.mockResolvedValue([])
})

afterEach(() => {
  mounted.splice(0).forEach((wrapper) => wrapper.unmount())
})

test('un login correcto guarda la sesión y entra al sistema', async () => {
  login.mockResolvedValue(loginResponse())
  const { wrapper, router } = await mountLogin()

  wrapper.findComponent(LoginAccessForm).vm.$emit('submit', {
    nombre_usuario: 'admin',
    password: '12345678',
  })
  await flushPromises()

  expect(login).toHaveBeenCalledWith({ nombre_usuario: 'admin', password: '12345678' })
  expect(JSON.parse(localStorage.getItem(SESSION_STORAGE_KEY)!).access_token).toBe('token-1')
  expect(router.currentRoute.value.name).toBe('inicio')
})

test('tras el login se respeta el destino que pedía el guard', async () => {
  login.mockResolvedValue(loginResponse())
  const { wrapper, router } = await mountLogin({ redirect: '/atenciones' })

  wrapper.findComponent(LoginAccessForm).vm.$emit('submit', {
    nombre_usuario: 'admin',
    password: '12345678',
  })
  await flushPromises()

  expect(router.currentRoute.value.path).toBe('/atenciones')
})

test('las credenciales rechazadas se muestran en el formulario sin crear sesión', async () => {
  login.mockRejectedValue(new Error('Usuario o contraseña incorrectos.'))
  const { wrapper, router } = await mountLogin()

  wrapper.findComponent(LoginAccessForm).vm.$emit('submit', {
    nombre_usuario: 'admin',
    password: '00000000',
  })
  await flushPromises()

  expect(wrapper.find('.el-alert__title').text()).toBe('Usuario o contraseña incorrectos.')
  expect(wrapper.findComponent(LoginAccessForm).props('errorMessage')).toBe(
    'Usuario o contraseña incorrectos.',
  )
  expect(wrapper.findComponent(LoginAccessForm).props('loading')).toBe(false)
  expect(localStorage.getItem(SESSION_STORAGE_KEY)).toBeNull()
  expect(router.currentRoute.value.name).toBe('login')
})

test('un error que no es Error no se inventa un mensaje del backend', async () => {
  login.mockRejectedValue('caída de red')
  const { wrapper } = await mountLogin()

  wrapper.findComponent(LoginAccessForm).vm.$emit('submit', {
    nombre_usuario: 'admin',
    password: '12345678',
  })
  await flushPromises()

  expect(wrapper.findComponent(LoginAccessForm).props('errorMessage')).toBe(
    'No se pudo iniciar sesión.',
  )
})

test('el formulario se bloquea mientras el backend responde', async () => {
  let resolveLogin: (value: LoginResponse) => void = () => {}
  login.mockImplementation(() => new Promise((resolve) => (resolveLogin = resolve)))
  const { wrapper } = await mountLogin()

  wrapper.findComponent(LoginAccessForm).vm.$emit('submit', {
    nombre_usuario: 'admin',
    password: '12345678',
  })
  await flushPromises()
  expect(wrapper.findComponent(LoginAccessForm).props('loading')).toBe(true)

  resolveLogin(loginResponse())
  await flushPromises()
  expect(wrapper.findComponent(LoginAccessForm).props('loading')).toBe(false)
})
