import { flushPromises, mount } from '@vue/test-utils'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import ElementPlus, { ElMessageBox, type MessageBoxData } from 'element-plus'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'

import AdmissionPatientSummary from '@/components/admission/AdmissionPatientSummary.vue'
import type { Patient } from '@/services/pacientes'
import { aPatient } from '../fixtures/patient'

const { update, deactivate } = vi.hoisted(() => ({
  update: vi.fn<(id: number, payload: Record<string, unknown>) => Promise<Patient>>(),
  deactivate: vi.fn<(id: number) => Promise<{ id: number; estado: boolean; mensaje: string }>>(),
}))

const emptyPage = { items: [], total: 0, limit: 25, offset: 0 }

vi.mock('@/services/pacientes', () => ({ pacientes: { update, deactivate } }))
vi.mock('@/services/catalogos', () => ({
  catalogos: {
    sexos: vi.fn(async () => []),
    seguros: vi.fn(async () => []),
    etnias: vi.fn(async () => []),
    establecimientos: vi.fn(async () => emptyPage),
    ubigeos: vi.fn(async () => emptyPage),
    localidades: vi.fn(async () => emptyPage),
  },
}))

const mounted: { unmount: () => void }[] = []

async function mountPanel(canDelete: boolean, overrides: Partial<Patient> = {}) {
  const wrapper = mount(AdmissionPatientSummary, {
    props: {
      patient: aPatient(overrides),
      canEdit: true,
      canDelete,
      tiposDocumento: [],
    },
    global: { plugins: [ElementPlus], components: ElementPlusIconsVue },
  })
  mounted.push(wrapper)
  await flushPromises()
  return wrapper
}

function deleteButton(wrapper: Awaited<ReturnType<typeof mountPanel>>) {
  return wrapper.findAll('button').find((button) => button.text().includes('Eliminar paciente'))
}

beforeEach(() => {
  update.mockReset()
  deactivate.mockReset()
  deactivate.mockResolvedValue({ id: 100, estado: false, mensaje: 'Paciente dado de baja.' })
})

afterEach(() => {
  vi.restoreAllMocks()
  while (mounted.length) mounted.pop()?.unmount()
})

// Montar el panel es costoso (Element Plus + catálogos), así que cada caso
// reutiliza el mismo montaje cambiando solo las props.
test('el botón de eliminar solo aparece con permiso y paciente activo', { timeout: 30_000 }, async () => {
  const wrapper = await mountPanel(true)
  expect(deleteButton(wrapper)).toBeTruthy()

  await wrapper.setProps({ canDelete: false })
  expect(deleteButton(wrapper)).toBeUndefined()

  await wrapper.setProps({ canDelete: true, patient: aPatient({ estado: false }) })
  expect(
    deleteButton(wrapper),
    'un paciente ya inactivo no se vuelve a dar de baja',
  ).toBeUndefined()
})

test('eliminar pide confirmación, da de baja al paciente y avisa a la vista', { timeout: 30_000 }, async () => {
  // El tipo de Element Plus cruza la acción con su payload, así que se declara
  // solo lo que este test consume.
  vi.spyOn(ElMessageBox, 'confirm').mockResolvedValue('confirm' as unknown as MessageBoxData)
  const wrapper = await mountPanel(true)

  const button = deleteButton(wrapper)!
  expect(button.classes()).toContain('el-button--danger')
  await button.trigger('click')
  await flushPromises()

  expect(ElMessageBox.confirm).toHaveBeenCalledOnce()
  expect(deactivate).toHaveBeenCalledWith(100)
  expect(wrapper.emitted('removed')?.[0]?.[0]).toMatchObject({ id: 100 })
})

test('cancelar la confirmación no da de baja a nadie', { timeout: 30_000 }, async () => {
  vi.spyOn(ElMessageBox, 'confirm').mockRejectedValue('cancel')
  const wrapper = await mountPanel(true)

  await deleteButton(wrapper)!.trigger('click')
  await flushPromises()

  expect(deactivate).not.toHaveBeenCalled()
  expect(wrapper.emitted('removed')).toBeUndefined()
})

// La admisión edita la ficha vigente, no el registro: la secuencia/etnia SIS, la
// fecha de inscripción y la condición se completan al dar de alta al paciente.
test(
  'el panel de admisión no edita secuencia, etnia, inscripción ni condición',
  { timeout: 30_000 },
  async () => {
    const wrapper = await mountPanel(false)

    expect(wrapper.find('.patient-context__sis-extra').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('SIS · Secuencia / RN')
    expect(wrapper.text()).not.toContain('Etnia declarada')
    expect(wrapper.text()).not.toContain('Fecha inscripción')
    expect(wrapper.text()).not.toContain('Condición')
  },
)

// El panel reúne grupo de riesgo, nombre de madre y grupo etario, en ese orden.
test(
  'el panel muestra grupo de riesgo, nombre de madre y grupo etáreo',
  { timeout: 30_000 },
  async () => {
    const wrapper = await mountPanel(false)
    const text = wrapper.text()

    expect(text).toContain('Grupo de riesgo')
    expect(text).toContain('Nombre de madre')
    expect(text).toContain('Grupo etáreo')
    expect(text.indexOf('Grupo de riesgo')).toBeLessThan(text.indexOf('Nombre de madre'))
    expect(text.indexOf('Nombre de madre')).toBeLessThan(text.indexOf('Grupo etáreo'))
  },
)
