import { flushPromises, mount } from '@vue/test-utils'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import ElementPlus from 'element-plus'
import { beforeEach, expect, test, vi } from 'vitest'

import LoginAccessForm from '@/components/auth/LoginAccessForm.vue'

const { listActiveLoginUsernames } = vi.hoisted(() => ({
  listActiveLoginUsernames: vi.fn<() => Promise<string[]>>(),
}))

vi.mock('@/services/auth', () => ({ listActiveLoginUsernames }))

async function mountForm(props: { loading?: boolean; errorMessage?: string | null } = {}) {
  const wrapper = mount(LoginAccessForm, {
    props: { loading: false, errorMessage: null, ...props },
    global: { plugins: [ElementPlus], components: ElementPlusIconsVue },
  })
  await flushPromises()
  return wrapper
}

function inputs(wrapper: Awaited<ReturnType<typeof mountForm>>) {
  return wrapper.findAll('input')
}

beforeEach(() => {
  vi.clearAllMocks()
  // Por defecto se usa el campo de texto: es el camino más simple de completar
  // en una prueba y el que se usa cuando el directorio no responde.
  listActiveLoginUsernames.mockRejectedValue(new Error('sin red'))
})

test('con directorio disponible el usuario se elige de la lista', async () => {
  listActiveLoginUsernames.mockResolvedValue(['admin', 'medico.demo'])
  const wrapper = await mountForm()

  expect(wrapper.find('.el-select').exists()).toBe(true)
  expect(wrapper.find('input[name="username"]').exists()).toBe(false)
  expect(listActiveLoginUsernames).toHaveBeenCalledTimes(1)
})

test('si el directorio falla se escribe el usuario a mano sin bloquear el acceso', async () => {
  const wrapper = await mountForm()

  expect(wrapper.find('.el-select').exists()).toBe(false)
  expect(wrapper.find('input[name="username"]').exists()).toBe(true)
  expect(wrapper.find('input[type="password"]').exists()).toBe(true)
})

test('la contraseña se limita a ocho dígitos al escribir', async () => {
  const wrapper = await mountForm()
  const [username, password] = inputs(wrapper)

  await username!.setValue('medico.demo')
  await password!.setValue('12ab3456789')

  await wrapper.find('form').trigger('submit')
  await flushPromises()

  expect(wrapper.emitted('submit')).toEqual([[{ nombre_usuario: 'medico.demo', password: '12345678' }]])
})

test('un formulario incompleto no se envía y muestra el motivo', async () => {
  const wrapper = await mountForm()

  await wrapper.find('form').trigger('submit')
  await flushPromises()
  expect(wrapper.emitted('submit')).toBeUndefined()

  const [, password] = inputs(wrapper)
  await password!.setValue('1234')
  await wrapper.find('form').trigger('submit')
  await flushPromises()
  // El mensaje del campo aparece tras el retardo del propio formulario.
  await new Promise((resolve) => setTimeout(resolve, 150))

  expect(wrapper.emitted('submit')).toBeUndefined()
  expect(wrapper.find('.el-form-item.is-error').exists()).toBe(true)
  expect(wrapper.text()).toContain('La contraseña debe contener exactamente 8 dígitos.')
})

test('el error del backend se muestra y el botón se bloquea mientras carga', async () => {
  const wrapper = await mountForm({ errorMessage: 'Credenciales inválidas.' })
  expect(wrapper.find('.el-alert__title').text()).toBe('Credenciales inválidas.')
  expect(wrapper.find('.login-form__submit').attributes('disabled')).toBeUndefined()

  const loading = await mountForm({ loading: true })
  expect(loading.find('.login-form__submit').attributes('disabled')).toBeDefined()
})

test('enter en la contraseña envía el formulario', async () => {
  const wrapper = await mountForm({ errorMessage: null })
  const [username, password] = inputs(wrapper)
  await username!.setValue('admin')
  await password!.setValue('12345678')

  await password!.trigger('keyup.enter')
  await flushPromises()

  expect(wrapper.emitted('submit')).toEqual([[{ nombre_usuario: 'admin', password: '12345678' }]])
})
