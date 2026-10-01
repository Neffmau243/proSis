import { mount } from '@vue/test-utils'
import ElementPlus, { ElOption, ElSelect } from 'element-plus'
import { expect, test } from 'vitest'
import PatientConditionSelect from '@/components/patients/PatientConditionSelect.vue'
import { PATIENT_CONDITIONS } from '@/utils/patientCondition'
import { buildPatientPatch, createPatientDraft } from '@/utils/patientDraft'
import { aPatient } from '../fixtures/patient'

test('ofrece solo nueve opciones y no permite crear texto libre', () => {
  const wrapper = mount(PatientConditionSelect, {
    props: { modelValue: null },
    global: { plugins: [ElementPlus] },
  })
  expect(wrapper.findAllComponents(ElOption).map((c) => c.props('value'))).toEqual(
    PATIENT_CONDITIONS,
  )
  expect(wrapper.getComponent(ElSelect).props('allowCreate')).toBe(false)
  wrapper.getComponent(ElSelect).vm.$emit('update:modelValue', undefined)
  expect(wrapper.emitted('update:modelValue')).toEqual([[null]])
  wrapper.unmount()
})

test('muestra el texto histórico sin convertirlo en otra opción válida', () => {
  const wrapper = mount(PatientConditionSelect, {
    props: { modelValue: 'DATO ANTIGUO', disabled: true },
    global: { plugins: [ElementPlus] },
  })
  const historical = wrapper
    .findAllComponents(ElOption)
    .find((c) => c.props('value') === 'DATO ANTIGUO')!
  expect(historical.props('disabled')).toBe(true)
  expect(wrapper.getComponent(ElSelect).props('disabled')).toBe(true)
  expect(wrapper.emitted('update:modelValue')).toBeUndefined()
  wrapper.unmount()
})

test('el PATCH conserva condiciones históricas al editar otro campo y permite limpiar la condición', () => {
  const baseline = createPatientDraft(aPatient({ condicion: 'DATO ANTIGUO' }))
  expect(buildPatientPatch(baseline, { ...baseline, primer_nombre: 'Ana' })).toEqual({
    primer_nombre: 'Ana',
  })
  expect(buildPatientPatch(baseline, { ...baseline, condicion: null })).toEqual({ condicion: null })
})
