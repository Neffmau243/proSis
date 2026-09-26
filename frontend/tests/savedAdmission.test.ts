import { effectScope, ref } from 'vue'
import { expect, test } from 'vitest'

import { useSavedAdmission } from '../src/composables/useSavedAdmission'
import { buildPatientPatch, createPatientDraft } from '../src/utils/patientDraft'
import { emptyPatientSis, patientSisErrors, patientSisSummary } from '../src/utils/patientSis'
import { aPatient } from './fixtures/patient'

test('printing uses only the saved server copy, keeps inputs, and clears on patient change', () => {
  const scope = effectScope()
  scope.run(() => {
    const patientId = ref<number | null>(11)
    const filledForm = { peso_kg: 60, talla_cm: 160 }
    const state = useSavedAdmission(() => patientId.value)
    expect(state.fuaSnapshot.value).toBeNull()
    expect(state.attentionCreated.value).toBe(false)
    const attention = {
      paciente_id: 11,
      id: 123,
      fua_impresion: { version: 2, imc: '23.438' },
    }
    state.remember(attention as never)
    expect(state.attentionCreated.value).toBe(true)
    expect(state.fuaSnapshot.value).toEqual(attention.fua_impresion)
    expect(filledForm).toEqual({ peso_kg: 60, talla_cm: 160 })
    state.fuaDialog.value = true
    state.fuaDialog.value = false
    expect(state.savedAttention.value?.id).toBe(123)
    expect(() => state.remember({ ...attention, paciente_id: 12 } as never)).toThrow()
    patientId.value = 12
    expect(state.fuaSnapshot.value).toBeNull()
    expect(state.attentionCreated.value).toBe(false)
    expect(state.fuaDialog.value).toBe(false)
  })
  scope.stop()
})

test('admission edits SIS, sequence and declared ethnicity in the patient master', () => {
  const baseline = createPatientDraft(aPatient(emptyPatientSis()))
  const draft = {
    ...baseline,
    sis_diresa: '001',
    sis_tipo: 'E1',
    sis_numero: '000000001',
    sis_secuencia: '01',
    etnia_codigo: '2',
  }
  expect(baseline.sis_numero).toBeNull()
  // La etnia forma parte del borrador editable: un paciente con etnia nula (como
  // el paciente demo) puede completarse desde admisión sin crear otro registro.
  expect(baseline.etnia_codigo).toBeNull()
  expect(buildPatientPatch(baseline, draft)).toEqual({
    sis_diresa: '001',
    sis_tipo: 'E1',
    sis_numero: '000000001',
    sis_secuencia: '01',
    etnia_codigo: '2',
  })
})

test('master registration keeps official length validation independently of admission', () => {
  const draft = {
    sis_diresa: '001',
    sis_tipo: 'E1',
    sis_numero: '000000001',
    sis_secuencia: '01',
    etnia_codigo: '2',
  }
  expect(patientSisErrors(draft)).toEqual({})
  expect(patientSisErrors({ sis_tipo: '2' }).sis_numero).toBeTruthy()
  expect(patientSisErrors({ sis_numero: '1234567' }).sis_numero).toBeTruthy()
  expect(patientSisErrors({ sis_secuencia: 'RN' }).sis_secuencia).toBeTruthy()
  expect(patientSisErrors(emptyPatientSis())).toEqual({})
})

test('read-only summary uses patient and catalog API values without defaults or invented affiliation', () => {
  const patient = {
    sis_diresa: '001',
    sis_tipo: 'E1',
    sis_numero: '000000001',
    sis_secuencia: '01',
    etnia_codigo: '2',
  }
  const before = { ...patient }
  const summary = patientSisSummary(patient, [
    { codigo: '2', nombre: 'Nombre provisto por el backend' },
  ])
  expect(summary.affiliation).toBe('001 - E1 - 000000001 - 01')
  expect(summary.ethnicity).toBe('2 · Nombre provisto por el backend')
  expect(patient).toEqual(before)
  expect(patientSisSummary(emptyPatientSis())).toEqual({
    affiliation: 'Pendiente de carga',
    ethnicity: 'Pendiente de carga',
  })
  expect(patientSisSummary({ etnia_codigo: '58' }).ethnicity).toBe('Código 58')
  expect(patientSisSummary({ sis_tipo: '2', sis_numero: '00000001' }).affiliation).toBe(
    '— - 2 - 00000001',
  )
})
