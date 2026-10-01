import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus, { ElDropdown, ElDropdownItem } from 'element-plus'
import { afterEach, expect, test } from 'vitest'
import AdmissionPatientRelations from '@/components/admission/AdmissionPatientRelations.vue'
import RiskDialog from '@/components/patient/RiskDialog.vue'
import ResponsibleDialog from '@/components/patient/ResponsibleDialog.vue'
import type { PatientRisk } from '@/services/pacientes'
import { aPatient } from '../fixtures/patient'

const risk = (id: number, name: string, start: string, end: string | null = null): PatientRisk => ({
  grupo_riesgo_id: id,
  grupo_riesgo_codigo: `R${id}`,
  grupo_riesgo_nombre: name,
  fecha_inicio: start,
  fecha_fin: end,
  observacion: null,
})
const risks = [
  risk(1, 'Riesgo vigente', '2000-01-01'),
  risk(2, 'Riesgo cerrado', '2000-01-01', '2001-01-01'),
  risk(3, 'Riesgo futuro', '2099-01-01'),
  risk(4, 'Otro vigente', '2000-01-01'),
]
const mother = {
  id: 7,
  parentesco: 'MADRE',
  nombre_completo: 'Madre de prueba',
  tipo_documento_codigo: null,
  numero_documento: null,
  telefono: null,
  es_principal: true,
  activo: true,
}
const mounted: { unmount: () => void }[] = []
afterEach(() => {
  while (mounted.length) mounted.pop()?.unmount()
})
function panel(canEdit = true) {
  const wrapper = mount(AdmissionPatientRelations, {
    props: {
      patient: aPatient({ riesgos: risks, responsables: [mother] }),
      canEdit,
      tiposDocumento: [],
      gruposRiesgo: [],
    },
    slots: { condition: '<div data-testid="condition">Condición del paciente</div>' },
    global: { plugins: [ElementPlus], stubs: { RiskDialog: true, ResponsibleDialog: true } },
  })
  mounted.push(wrapper)
  return wrapper
}

test('el panel no agrega datos adicionales y conserva los periodos en el desplegable de riesgos', () => {
  const wrapper = panel()
  expect(wrapper.findAll('.patient-relations__entry')).toHaveLength(2)
  expect(wrapper.get('.patient-relations__risk-trigger').text()).toBe(
    'Riesgo vigente · Otro vigente',
  )
  expect(wrapper.find('details').exists()).toBe(false)
  expect(wrapper.get('[data-testid="condition"]').text()).toBe('Condición del paciente')
  expect(wrapper.findAllComponents(ElDropdownItem).map((item) => item.props('command'))).toEqual([
    '1|2000-01-01',
    '2|2000-01-01',
    '3|2099-01-01',
    '4|2000-01-01',
    'add',
  ])
})

test('los periodos cerrados siguen siendo editables desde el desplegable', async () => {
  const wrapper = panel()
  wrapper.getComponent(ElDropdown).vm.$emit('command', '2|2000-01-01')
  await flushPromises()
  expect(wrapper.getComponent(RiskDialog).props('riesgo')).toEqual(risks[1])
  expect(wrapper.getComponent(RiskDialog).props('modelValue')).toBe(true)
})

test('editar un riesgo desde el desplegable conserva los demás periodos y avisa del guardado', async () => {
  const wrapper = panel()
  wrapper.getComponent(ElDropdown).vm.$emit('command', '1|2000-01-01')
  await flushPromises()
  const dialog = wrapper.getComponent(RiskDialog)
  expect(dialog.props('modelValue')).toBe(true)
  expect(dialog.props('riesgo')).toEqual(risks[0])
  expect(wrapper.emitted('busyChange')).toContainEqual([true])
  dialog.vm.$emit('saved', { ...risks[0], observacion: 'Corregido' })
  const saved = wrapper.emitted('saved')?.[0]?.[0] as ReturnType<typeof aPatient>
  expect(saved.riesgos).toHaveLength(4)
  expect(saved.riesgos).toContainEqual(risks[1])
  expect(saved.riesgos.find((r) => r.grupo_riesgo_id === 1)?.observacion).toBe('Corregido')
})

test('el icono de la madre abre el editor existente y los permisos siguen vigentes', async () => {
  const wrapper = panel()
  await wrapper.get('button[aria-label="Editar madre"]').trigger('click')
  expect(wrapper.getComponent(ResponsibleDialog).props('responsible')).toEqual(mother)
  expect(wrapper.getComponent(ResponsibleDialog).props('modelValue')).toBe(true)
  await wrapper.setProps({ disabled: true })
  expect(wrapper.get('button[aria-label="Editar madre"]').attributes('disabled')).toBeDefined()
  await wrapper.setProps({ canEdit: false })
  expect(wrapper.findComponent(ElDropdown).exists()).toBe(false)
  expect(wrapper.find('button[aria-label="Editar madre"]').exists()).toBe(false)
  expect(wrapper.get('input[aria-label="Grupo de riesgo"]').attributes('readonly')).toBeDefined()
})
