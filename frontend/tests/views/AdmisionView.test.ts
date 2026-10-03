import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import ElementPlus, { ElFormItem, ElInputNumber, ElSelect } from 'element-plus'
import { afterEach, expect, test, vi } from 'vitest'
import AtencionNuevaView from '@/views/AtencionNuevaView.vue'
import AdmissionPatientSummary from '@/components/admission/AdmissionPatientSummary.vue'
import AdmissionHistory from '@/components/admission/AdmissionHistory.vue'
import { aPatient } from '../fixtures/patient'

const { create, get, listByPatient, previewNutritionalIndicators } = vi.hoisted(() => ({
  previewNutritionalIndicators: vi.fn(async () => ({ estado: 'DATOS_INCOMPLETOS', mensaje: 'Ingrese peso y talla', pe: null, te: null, pt: null })),
  create: vi.fn(),
  get: vi.fn(),
  listByPatient: vi.fn(async () => []),
}))
vi.mock('@/services/pacientes', () => ({ pacientes: { get } }))
vi.mock('@/services/atenciones', () => ({ atenciones: { create, listByPatient, previewNutritionalIndicators } }))
vi.mock('@/services/catalogos', () => ({
  catalogos: {
    especialidades: async () => [{ codigo: '001', nombre: 'MEDICINA' }],
    establecimientos: async () => ({ items: [{ id: 1, nombre: 'Sede de prueba' }] }),
    profesionales: async () => ({ items: [{ id: 2, nombre_completo: 'Profesional de prueba' }] }),
    consultorios: async () => ({
      items: [
        {
          id: 3,
          nombre: 'Consultorio de prueba',
          establecimiento_id: 1,
          especialidad_codigo: '001',
        },
      ],
    }),
    gruposEtarios: async () => [],
    tiposDocumento: async () => [],
    gruposRiesgo: async () => [],
  },
}))

const mounted: { unmount: () => void }[] = []

test('la valoración muestra cálculos de solo lectura y descarta resultados al borrar medidas', async () => {
  const wrapper = await mountAdmission()
  const field = (label: string) => wrapper.findAllComponents(ElFormItem).find(item => item.props('label') === label)!
  previewNutritionalIndicators.mockResolvedValueOnce({ estado: 'CALCULADO', mensaje: 'OMS 2006', pe: '-0.147', te: '-0.243', pt: '-0.056', diagnostico_peso_edad: 'Normal', diagnostico_talla_edad: 'Normal', diagnostico_peso_talla: 'Normal' } as never)
  field('Peso actual (kg)').getComponent(ElInputNumber).vm.$emit('update:modelValue', 9.5)
  field('Talla (cm)').getComponent(ElInputNumber).vm.$emit('update:modelValue', 75.2)
  await new Promise(resolve => setTimeout(resolve, 400))
  await flushPromises()
  const output = field('Diagnóstico P/E').get('input')
  expect(output.attributes('readonly')).toBeDefined()
  expect((output.element as HTMLInputElement).value).toBe('Normal · Z: -0.147')
  field('Peso actual (kg)').getComponent(ElInputNumber).vm.$emit('update:modelValue', null)
  await flushPromises()
  expect((field('Diagnóstico P/E').get('input').element as HTMLInputElement).value).toBe('Calculando…')
  await new Promise(resolve => setTimeout(resolve, 400))
  await flushPromises()
  expect((field('Diagnóstico P/E').get('input').element as HTMLInputElement).value).toBe('No disponible')
})
afterEach(() => {
  while (mounted.length) mounted.pop()?.unmount()
  vi.clearAllMocks()
})

async function mountAdmission() {
  get.mockResolvedValue(aPatient({ condicion: 'NO GESTANTE' }))
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/admision', component: AtencionNuevaView },
      { path: '/', name: 'inicio', component: { template: '<div />' } },
    ],
  })
  await router.push('/admision?patientId=100')
  await router.isReady()
  const wrapper = mount(AtencionNuevaView, {
    props: { admission: true },
    global: {
      plugins: [ElementPlus, createPinia(), router],
      stubs: { AdmissionPatientSummary: true, AdmissionHistory: true, FuaPrintDialog: true },
    },
  })
  mounted.push(wrapper)
  await flushPromises()
  return wrapper
}

test(
  'el formulario mantiene fecha, selección exclusiva y payload al guardar la atención',
  { timeout: 30_000 },
  async () => {
    const wrapper = await mountAdmission()
    const field = (label: string) =>
      wrapper.findAllComponents(ElFormItem).find((item) => item.props('label') === label)!
    expect(wrapper.text()).toContain('Fecha y hora de atención')
    expect(wrapper.getComponent(AdmissionHistory).props('compact')).toBe(true)
    expect(wrapper.find('.encounter-header h2').exists()).toBe(false)
    expect(wrapper.get('.encounter-header').text()).not.toContain('Sede de prueba')
    field('Consultorio').getComponent(ElSelect).vm.$emit('update:modelValue', 3)
    field('Profesional').getComponent(ElSelect).vm.$emit('update:modelValue', 2)
    await wrapper.get('input[value="EMERGENCIA"]').setValue(true)
    await wrapper.get('input[value="GESTANTES"]').setValue(true)
    expect(wrapper.text()).toContain('Fecha probable de parto')
    expect(wrapper.text()).not.toContain('Perímetro abdominal (cm)')
    field('Peso antes del embarazo (kg)')
      .getComponent(ElInputNumber)
      .vm.$emit('update:modelValue', 55)
    await wrapper.get('input[value="PUERPERAS"]').setValue(true)
    expect(wrapper.text()).not.toContain('Fecha probable de parto')
    field('Peso actual (kg)').getComponent(ElInputNumber).vm.$emit('update:modelValue', 60)
    field('Talla (cm)').getComponent(ElInputNumber).vm.$emit('update:modelValue', 160)
    await flushPromises()
    create.mockImplementation(async (payload) => ({ ...payload, id: 500, fua_impresion: null }))
    const save = wrapper.findAll('button').find((b) => b.text() === 'Guardar atención')!
    await save.trigger('click')
    await flushPromises()
    expect(create).toHaveBeenCalledOnce()
    expect(create.mock.calls[0]?.[0]).toMatchObject({
      paciente_id: 100,
      establecimiento_id: 1,
      consultorio_id: 3,
      profesional_id: 2,
      especialidad_codigo: '001',
      modalidad_atencion_codigo: 'EMERGENCIA',
      grupo_atencion_codigo: 'PUERPERAS',
      peso_kg: 60,
      talla_cm: 160,
      peso_antes_embarazo_kg: null,
      fecha_probable_parto: null,
    })
    expect(create.mock.calls[0]?.[0].fecha_atencion).toMatch(/^\d{4}-\d{2}-\d{2}T/)
    expect(create.mock.calls[0]?.[0]).not.toHaveProperty('condicion')
    expect(wrapper.text()).toContain('Atención guardada')
    expect(wrapper.get('input[value="PUERPERAS"]').attributes('disabled')).toBeDefined()
    expect(listByPatient).toHaveBeenCalledTimes(2)
    await wrapper.setProps({ admission: false })
    expect(wrapper.getComponent(AdmissionHistory).props('compact')).toBe(false)
  },
)

test(
  'los cambios del paciente bloquean la atención hasta guardarlos o descartarlos',
  { timeout: 30_000 },
  async () => {
    const wrapper = await mountAdmission()
    wrapper.getComponent(AdmissionPatientSummary).vm.$emit('dirtyChange', true)
    await flushPromises()
    const save = wrapper.findAll('button').find((b) => b.text() === 'Guardar atención')!
    expect(save.attributes('disabled')).toBeDefined()
    expect(wrapper.text()).toContain('Guarde o descarte los cambios del paciente')
    expect(create).not.toHaveBeenCalled()
    for (const text of ['Otra consulta', 'FUA adicional']) {
      expect(
        wrapper
          .findAll('button')
          .find((b) => b.text() === text)
          ?.attributes('disabled'),
      ).toBeDefined()
    }
  },
)

test.each(['GESTANTES', 'PUERPERAS'])(
  'guardar %s refresca la condición confirmada por el servidor',
  async (group) => {
    const wrapper = await mountAdmission()
    const field = (label: string) =>
      wrapper.findAllComponents(ElFormItem).find((item) => item.props('label') === label)!
    field('Consultorio').getComponent(ElSelect).vm.$emit('update:modelValue', 3)
    field('Profesional').getComponent(ElSelect).vm.$emit('update:modelValue', 2)
    await wrapper.get(`input[value="${group}"]`).setValue(true)
    const condition = group === 'GESTANTES' ? 'GESTANTE' : 'PUERPERA'
    expect(wrapper.getComponent(AdmissionPatientSummary).props('patient').condicion).toBe(
      'NO GESTANTE',
    )
    get.mockResolvedValue(aPatient({ condicion: condition }))
    create.mockImplementation(async (payload) => ({ ...payload, id: 501, fua_impresion: null }))
    await wrapper
      .findAll('button')
      .find((b) => b.text() === 'Guardar atención')!
      .trigger('click')
    await flushPromises()
    expect(create).toHaveBeenCalledOnce()
    expect(wrapper.getComponent(AdmissionPatientSummary).props('patient').condicion).toBe(condition)
    expect(wrapper.text()).toContain('Atención guardada')
  },
)

test('fallar el refresco de ficha después del POST no permite duplicar la atención', async () => {
  const wrapper = await mountAdmission()
  const field = (label: string) =>
    wrapper.findAllComponents(ElFormItem).find((item) => item.props('label') === label)!
  field('Consultorio').getComponent(ElSelect).vm.$emit('update:modelValue', 3)
  field('Profesional').getComponent(ElSelect).vm.$emit('update:modelValue', 2)
  await wrapper.get('input[value="PUERPERAS"]').setValue(true)
  get.mockRejectedValue(new Error('Refresh unavailable'))
  create.mockImplementation(async (payload) => ({ ...payload, id: 502, fua_impresion: null }))
  const save = wrapper.findAll('button').find((b) => b.text() === 'Guardar atención')!
  await save.trigger('click')
  await flushPromises()
  expect(wrapper.text()).toContain('Atención guardada')
  await save.trigger('click')
  await flushPromises()
  expect(create).toHaveBeenCalledOnce()
})

test('una atención rechazada conserva la condición visible y no refresca la ficha', async () => {
  const wrapper = await mountAdmission()
  const field = (label: string) =>
    wrapper.findAllComponents(ElFormItem).find((item) => item.props('label') === label)!
  field('Consultorio').getComponent(ElSelect).vm.$emit('update:modelValue', 3)
  field('Profesional').getComponent(ElSelect).vm.$emit('update:modelValue', 2)
  await wrapper.get('input[value="GESTANTES"]').setValue(true)
  const reads = get.mock.calls.length
  create.mockRejectedValue(new Error('Atención rechazada de prueba'))
  await wrapper
    .findAll('button')
    .find((b) => b.text() === 'Guardar atención')!
    .trigger('click')
  await flushPromises()
  expect(get.mock.calls.length).toBe(reads)
  expect(wrapper.getComponent(AdmissionPatientSummary).props('patient').condicion).toBe(
    'NO GESTANTE',
  )
  expect(wrapper.text()).toContain('Atención rechazada de prueba')
  expect(wrapper.text()).not.toContain('Atención guardada')
})
