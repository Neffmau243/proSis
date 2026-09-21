import { flushPromises, mount } from '@vue/test-utils'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import ElementPlus from 'element-plus'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import { SESSION_STORAGE_KEY, saveSession } from '@/services/session-storage'
import type { PersistedSession } from '@/services/session-storage'
import { useAuthStore } from '@/stores/auth'
import CambiarContrasenaView from '@/views/CambiarContrasenaView.vue'

const { changeMyPassword } = vi.hoisted(() => ({
  changeMyPassword: vi.fn<() => Promise<void>>(),
}))

vi.mock('@/services/auth', () => ({ changeMyPassword }))

const mounted: { unmount: () => void }[] = []

async function mountView() {
  const stub = { template: '<div />' }
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/cuenta/cambiar-contrasena', name: 'cambiar-contrasena', component: stub },
      { path: '/login', name: 'login', component: stub },
    ],
  })
  const pinia = createPinia()
  setActivePinia(pinia)
  await router.push('/cuenta/cambiar-contrasena')
  await router.isReady()

  const wrapper = mount(CambiarContrasenaView, {
    global: { plugins: [router, pinia, ElementPlus], components: ElementPlusIconsVue },
  })
  mounted.push(wrapper)
  await flushPromises()
  return { wrapper, router }
}

/** Los tres campos, en el orden del formulario. */
function fields(wrapper: Awaited<ReturnType<typeof mountView>>['wrapper']) {
  return wrapper.findAll('input[type="password"]')
}

async function fill(
  wrapper: Awaited<ReturnType<typeof mountView>>['wrapper'],
  values: [string, string, string],
) {
  const inputs = fields(wrapper)
  for (const [index, value] of values.entries()) {
    await inputs[index]!.setValue(value)
  }
}

async function submit(wrapper: Awaited<ReturnType<typeof mountView>>['wrapper']) {
  await wrapper.find('form').trigger('submit')
  await flushPromises()
}

beforeEach(() => {
  localStorage.clear()
  vi.clearAllMocks()
  vi.useFakeTimers({ shouldAdvanceTime: true })
  const session: PersistedSession = {
    access_token: 'token',
    expires_at: Date.now() + 3_600_000,
    usuario_id: 1,
    nombre_usuario: 'admin',
    roles: ['ADMIN'],
    permisos: [],
  }
  saveSession(session)
})

afterEach(() => {
  mounted.splice(0).forEach((wrapper) => wrapper.unmount())
  vi.useRealTimers()
})

test('la contraseña solo admite ocho dígitos en los tres campos', async () => {
  const { wrapper } = await mountView()

  await fill(wrapper, ['12ab345678', '87654x321', '87654321'])

  const inputs = fields(wrapper)
  expect((inputs[0]!.element as HTMLInputElement).value).toBe('12345678')
  expect((inputs[1]!.element as HTMLInputElement).value).toBe('87654321')
  expect((inputs[2]!.element as HTMLInputElement).value).toBe('87654321')
})

test('un formulario incompleto o con contraseñas distintas no llama a la API', async () => {
  const { wrapper } = await mountView()

  await submit(wrapper)
  expect(changeMyPassword).not.toHaveBeenCalled()

  // La confirmación que no coincide bloquea el envío.
  await fill(wrapper, ['12345678', '87654321', '11111111'])
  await submit(wrapper)
  await vi.advanceTimersByTimeAsync(150)
  expect(changeMyPassword).not.toHaveBeenCalled()
  expect(wrapper.text()).toContain('Las contraseñas no coinciden.')

  // La nueva no puede repetir la actual.
  await fill(wrapper, ['12345678', '12345678', '12345678'])
  await submit(wrapper)
  await vi.advanceTimersByTimeAsync(150)
  expect(changeMyPassword).not.toHaveBeenCalled()
  expect(wrapper.text()).toContain('La nueva contraseña debe ser diferente de la actual.')
})

test('un cambio válido cierra la sesión y vuelve al login tras el aviso', async () => {
  changeMyPassword.mockResolvedValue()
  const { wrapper, router } = await mountView()
  const auth = useAuthStore()
  auth.token = 'token'

  await fill(wrapper, ['12345678', '87654321', '87654321'])
  await submit(wrapper)

  expect(changeMyPassword).toHaveBeenCalledWith({
    current_password: '12345678',
    new_password: '87654321',
    new_password_confirmation: '87654321',
  })
  expect(wrapper.text()).toContain('Contraseña actualizada. Vuelva a iniciar sesión.')
  // La sesión se invalida en el servidor: el cliente no debe conservar el token.
  expect(auth.token).toBeNull()
  expect(localStorage.getItem(SESSION_STORAGE_KEY)).toBeNull()

  // Todavía en la pantalla hasta que se cumple el aviso.
  expect(router.currentRoute.value.name).toBe('cambiar-contrasena')

  await vi.advanceTimersByTimeAsync(1500)
  await flushPromises()
  expect(router.currentRoute.value.name).toBe('login')
})

test('el error de la API se muestra y conserva la sesión', async () => {
  changeMyPassword.mockRejectedValue(new Error('La contraseña actual no coincide.'))
  const { wrapper, router } = await mountView()
  const auth = useAuthStore()
  auth.token = 'token'

  await fill(wrapper, ['12345678', '87654321', '87654321'])
  await submit(wrapper)

  expect(wrapper.find('.el-alert__title').text()).toBe('La contraseña actual no coincide.')
  expect(auth.token).toBe('token')
  expect(localStorage.getItem(SESSION_STORAGE_KEY)).not.toBeNull()
  expect(router.currentRoute.value.name).toBe('cambiar-contrasena')
})

test('un error sin mensaje usa el texto por defecto y el botón no se bloquea de más', async () => {
  changeMyPassword.mockRejectedValue('caída de red')
  const { wrapper } = await mountView()
  const submitButton = wrapper.find('button[type="submit"]')

  await fill(wrapper, ['12345678', '87654321', '87654321'])
  await submit(wrapper)

  expect(wrapper.find('.el-alert__title').text()).toBe('No se pudo cambiar la contraseña.')
  expect(submitButton.attributes('disabled')).toBeUndefined()

  // Tras el éxito el formulario queda bloqueado para evitar un segundo envío.
  changeMyPassword.mockResolvedValue()
  await submit(wrapper)
  expect(submitButton.attributes('disabled')).toBeDefined()
})
