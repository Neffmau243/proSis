import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import ElementPlus, { ElMessage, ElMessageBox } from 'element-plus'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'

import UsersPanel from '@/components/configuracion/UsersPanel.vue'
import type { ProfessionalResponse } from '@/services/profesionales'
import { useAuthStore } from '@/stores/auth'
import type { UserResponse } from '@/services/usuarios'

const { list, create, updateRoles, resetPassword, deactivate } = vi.hoisted(() => ({
  list: vi.fn(),
  create: vi.fn(),
  updateRoles: vi.fn(),
  resetPassword: vi.fn(),
  deactivate: vi.fn(),
}))

const { catalogos } = vi.hoisted(() => ({ catalogos: { profesionales: vi.fn() } }))

vi.mock('@/services/usuarios', () => ({
  usuarios: { list, create, updateRoles, resetPassword, deactivate },
}))
vi.mock('@/services/catalogos', () => ({ catalogos }))

function aUser(overrides: Partial<UserResponse> = {}): UserResponse {
  return {
    id: 1,
    profesional_id: null,
    nombre_usuario: 'ana.quispe',
    activo: true,
    ultimo_acceso_at: null,
    created_at: '2026-01-01T00:00:00',
    updated_at: '2026-01-01T00:00:00',
    roles: ['ADMIN'],
    ...overrides,
  }
}

const aProfessional = {
  id: 5,
  nombre_completo: 'Luis Torres',
  colegiatura: 'CMP-009',
  activo: true,
} as unknown as ProfessionalResponse

const mounted: { unmount: () => void }[] = []

async function mountPanel(props: Partial<InstanceType<typeof UsersPanel>['$props']> = {}) {
  const pinia = createPinia()
  setActivePinia(pinia)
  const auth = useAuthStore()
  auth.usuarioId = 99
  const wrapper = mount(UsersPanel, {
    props: {
      rows: [aUser()],
      loading: false,
      incluirInactivos: false,
      professionals: [aProfessional],
      prefillProfessionalId: null,
      ...props,
    },
    global: { plugins: [pinia, ElementPlus], components: ElementPlusIconsVue },
  })
  mounted.push(wrapper)
  await flushPromises()
  return { wrapper, auth }
}

function button(wrapper: VueWrapper, label: string) {
  const found = wrapper.findAll('button').find((item) => item.text().includes(label))
  if (!found) throw new Error(`No se encontró el botón "${label}"`)
  return found
}

async function setField(wrapper: VueWrapper, label: string, value: string): Promise<void> {
  const item = wrapper
    .findAll('.el-form-item')
    .find((element) => element.find('.el-form-item__label').text().startsWith(label))
  if (!item) throw new Error(`No se encontró el campo "${label}"`)
  await item.find('input').setValue(value)
}

beforeEach(() => {
  vi.clearAllMocks()
  catalogos.profesionales.mockResolvedValue({ items: [], total: 0, limit: 25, offset: 0, has_more: false })
  create.mockResolvedValue(aUser({ id: 2 }))
  updateRoles.mockResolvedValue(aUser())
  resetPassword.mockResolvedValue(undefined)
  deactivate.mockResolvedValue(aUser({ activo: false }))
  vi.spyOn(ElMessage, 'success').mockImplementation(() => ({}) as never)
  vi.spyOn(ElMessage, 'error').mockImplementation(() => ({}) as never)
  vi.spyOn(ElMessageBox, 'confirm').mockResolvedValue('confirm' as never)
})

afterEach(() => {
  mounted.splice(0).forEach((wrapper) => wrapper.unmount())
  vi.restoreAllMocks()
})

test('muestra la lista, sus roles y el profesional vinculado', async () => {
  const { wrapper } = await mountPanel({
    rows: [aUser({ profesional_id: 5, roles: ['ADMIN', 'PROFESIONAL'] })],
  })

  expect(wrapper.text()).toContain('ana.quispe')
  expect(wrapper.text()).toContain('ADMIN')
  expect(wrapper.text()).toContain('PROFESIONAL')
  expect(wrapper.text()).toContain('Luis Torres')
})

test('un usuario sin último acceso no muestra una fecha inválida', async () => {
  const { wrapper } = await mountPanel({ rows: [aUser({ ultimo_acceso_at: null })] })

  expect(wrapper.text()).not.toContain('Invalid Date')
  expect(wrapper.text()).toContain('—')
})

test('incluir inactivos delega el cambio al contenedor', async () => {
  const { wrapper } = await mountPanel()
  wrapper.findComponent({ name: 'ElSwitch' }).vm.$emit('update:modelValue', true)
  await flushPromises()

  expect(wrapper.emitted('update:incluirInactivos')?.[0]).toEqual([true])
})

test('el alta envía el contrato del backend y pide refrescar', async () => {
  const { wrapper } = await mountPanel()
  await button(wrapper, 'Nuevo usuario').trigger('click')
  await flushPromises()

  await setField(wrapper, 'Nombre de usuario', 'luis.torres')
  await setField(wrapper, 'Contraseña', '12345678')
  await setField(wrapper, 'Confirmar contraseña', '12345678')
  wrapper.findComponent({ name: 'ElCheckboxGroup' }).vm.$emit('update:modelValue', ['ADMIN'])
  await flushPromises()

  await button(wrapper, 'Crear usuario').trigger('click')
  await flushPromises()

  expect(create).toHaveBeenCalledWith({
    nombre_usuario: 'luis.torres',
    password: '12345678',
    roles: ['ADMIN'],
    profesional_id: null,
  })
  expect(wrapper.emitted('refresh')).toBeTruthy()
})

test('sin profesional vinculado no se puede asignar PROFESIONAL', async () => {
  const { wrapper } = await mountPanel({ rows: [aUser({ profesional_id: null })] })
  await button(wrapper, 'Roles').trigger('click')
  await flushPromises()

  const professionalCheckbox = wrapper
    .findAll('.el-checkbox')
    .find((item) => item.text().includes('PROFESIONAL'))
  expect(professionalCheckbox?.classes()).toContain('is-disabled')

  wrapper.findComponent({ name: 'ElCheckboxGroup' }).vm.$emit('update:modelValue', ['ADMIN'])
  await button(wrapper, 'Guardar roles').trigger('click')
  await flushPromises()

  expect(updateRoles).toHaveBeenCalledWith(1, ['ADMIN'])
})

test('un error al guardar roles se muestra dentro del diálogo abierto', async () => {
  const { wrapper } = await mountPanel()
  await button(wrapper, 'Roles').trigger('click')
  wrapper.findComponent({ name: 'ElCheckboxGroup' }).vm.$emit('update:modelValue', [])
  await flushPromises()
  await button(wrapper, 'Guardar roles').trigger('click')
  await flushPromises()

  expect(updateRoles).not.toHaveBeenCalled()
  const dialog = wrapper.findAll('[role="dialog"]').find(item => item.text().includes('Roles del usuario'))!
  expect(dialog.get('[role="alert"]').text()).toContain('Seleccione al menos un rol.')
})

test('el error del servidor en el alta permanece visible en el formulario', async () => {
  create.mockRejectedValueOnce(new Error('El nombre de usuario ya está registrado.'))
  const { wrapper } = await mountPanel()
  await button(wrapper, 'Nuevo usuario').trigger('click')
  await flushPromises()
  await setField(wrapper, 'Nombre de usuario', 'usuario.prueba')
  await setField(wrapper, 'Contraseña', '12345678')
  await setField(wrapper, 'Confirmar contraseña', '12345678')
  wrapper.findComponent({ name: 'ElCheckboxGroup' }).vm.$emit('update:modelValue', ['ADMIN'])
  await flushPromises()
  await button(wrapper, 'Crear usuario').trigger('click')
  await flushPromises()

  const dialog = wrapper.findAll('[role="dialog"]').find(item => item.text().includes('Nuevo usuario'))!
  expect(dialog.get('[role="alert"]').text()).toContain('El nombre de usuario ya está registrado.')
  expect(wrapper.emitted('refresh')).toBeUndefined()
})

test('la cuenta propia no ofrece restablecimiento administrativo de contraseña', async () => {
  const { wrapper, auth } = await mountPanel()
  auth.usuarioId = 1
  await flushPromises()
  expect(button(wrapper, 'Contraseña').attributes('disabled')).toBeDefined()
  expect(button(wrapper, 'Dar de baja').attributes('disabled')).toBeDefined()
})

test('con profesional vinculado se puede guardar PROFESIONAL', async () => {
  const { wrapper } = await mountPanel({ rows: [aUser({ profesional_id: 5 })] })
  await button(wrapper, 'Roles').trigger('click')
  await flushPromises()

  wrapper.findComponent({ name: 'ElCheckboxGroup' }).vm.$emit('update:modelValue', ['ADMIN', 'PROFESIONAL'])
  await button(wrapper, 'Guardar roles').trigger('click')
  await flushPromises()

  expect(updateRoles).toHaveBeenCalledWith(1, ['ADMIN', 'PROFESIONAL'])
})

test('el restablecimiento exige contraseñas de 8 dígitos coincidentes', async () => {
  const { wrapper } = await mountPanel()
  await button(wrapper, 'Contraseña').trigger('click')
  await flushPromises()

  await setField(wrapper, 'Nueva contraseña', '11112222')
  await setField(wrapper, 'Confirmar', '11112223')
  await button(wrapper, 'Restablecer').trigger('click')
  await flushPromises()

  expect(resetPassword).not.toHaveBeenCalled()

  await setField(wrapper, 'Confirmar', '11112222')
  await button(wrapper, 'Restablecer').trigger('click')
  await flushPromises()

  expect(resetPassword).toHaveBeenCalledWith(1, {
    new_password: '11112222',
    new_password_confirmation: '11112222',
  })
})

test('la baja de otro usuario es informativa y no se ofrece sobre uno mismo', async () => {
  const { wrapper } = await mountPanel({ rows: [aUser({ id: 1 })] })
  await button(wrapper, 'Dar de baja').trigger('click')
  await flushPromises()

  expect(ElMessageBox.confirm).toHaveBeenCalledWith(
    expect.stringContaining('La baja es lógica'),
    'Dar de baja usuario',
    expect.objectContaining({ type: 'info' }),
  )
  expect(deactivate).toHaveBeenCalledWith(1)

  const { wrapper: selfWrapper } = await mountPanel({ rows: [aUser({ id: 99 })] })
  const selfButton = selfWrapper.findAll('button').find((item) => item.text().includes('Dar de baja'))
  expect(selfButton?.attributes('disabled')).toBeDefined()
})

test('crear cuenta desde una ficha abre el alta ya vinculada', async () => {
  const { wrapper } = await mountPanel({ prefillProfessionalId: 5 })

  expect(wrapper.emitted('consume-prefill')).toBeTruthy()
  await setField(wrapper, 'Nombre de usuario', 'luis.torres')
  await setField(wrapper, 'Contraseña', '12345678')
  await setField(wrapper, 'Confirmar contraseña', '12345678')
  await button(wrapper, 'Crear usuario').trigger('click')
  await flushPromises()

  expect(create).toHaveBeenCalledWith(
    expect.objectContaining({ profesional_id: 5, roles: ['PROFESIONAL'] }),
  )
})
