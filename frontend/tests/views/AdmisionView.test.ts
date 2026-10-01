import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import ElementPlus, { ElFormItem, ElInputNumber, ElSelect } from 'element-plus'
import { afterEach, expect, test, vi } from 'vitest'
import AtencionNuevaView from '@/views/AtencionNuevaView.vue'
import AdmissionPatientSummary from '@/components/admission/AdmissionPatientSummary.vue'
import AdmissionHistory from '@/components/admission/AdmissionHistory.vue'
import { aPatient } from '../fixtures/patient'

const { create, get, listByPatient } = vi.hoisted(() => ({
  create: vi.fn(),
  get: vi.fn(),
  listByPatient: vi.fn(async () => []),
}))
vi.mock('@/services/pacientes', () => ({ pacientes: { get } }))
vi.mock('@/services/atenciones', () => ({ atenciones: { create, listByPatient } }))
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
