import { effectScope, nextTick, shallowRef } from 'vue'
import { expect, test } from 'vitest'

import { useAdmissionPatientEditor } from '../src/composables/useAdmissionPatientEditor'
import type { Patient } from '../src/services/pacientes'
import {
  buildPatientPatch,
  createPatientDraft,
  validatePatientDraft,
} from '../src/utils/patientDraft'
import { aPatient as patient } from './fixtures/patient'

/** Respuesta del servidor: el paciente guardado con el PATCH aplicado. */
const aPatientFrom = (patch: object) => patient(patch as Partial<Patient>)

test('PATCH sends only changed columns, including clears; never child/derived fields', () => {
  const original = patient()
  const baseline = createPatientDraft(original)
  const draft = {
    ...baseline,
    primer_nombre: '  Ana  ',
    telefono_principal: '',
    responsables: [{}],
    edad: 99,
  }
  expect(buildPatientPatch(baseline, draft)).toEqual({
    primer_nombre: 'Ana',
    telefono_principal: null,
  })
  expect(original.primer_nombre).toBe('Paciente')
  expect(buildPatientPatch(baseline, { ...baseline, primer_nombre: ' Paciente ' })).toEqual({})
})

test('validation handles required values, real dates and residence hierarchy', () => {
  const draft = createPatientDraft(patient())
  expect(validatePatientDraft(draft, '2026-09-17')).toEqual({})
  expect(validatePatientDraft({ ...draft, fecha_nacimiento: '' }, '2026-09-17').fecha_nacimiento)
    .toBeTruthy()
  expect(
    validatePatientDraft({ ...draft, fecha_nacimiento: '2026-02-30' }, '2026-09-17').fecha_nacimiento,
  ).toBeTruthy()
  expect(
    validatePatientDraft({ ...draft, fecha_nacimiento: '2027-01-01' }, '2026-09-17').fecha_nacimiento,
  ).toBeTruthy()
  expect(
    validatePatientDraft({ ...draft, numero_documento: ' ' }, '2026-09-17').numero_documento,
  ).toBeTruthy()
  expect(
    validatePatientDraft({ ...draft, ubigeo_residencia_codigo: null }, '2026-09-17').localidad,
  ).toBeTruthy()
  expect(validatePatientDraft({ ...draft, localidad: '040101' }, '2026-09-17').localidad)
    .toBeTruthy()
})

test('editing the three visible SIS fields preserves an existing sequence without sending it', () => {
  const baseline = createPatientDraft({
    ...patient(),
    sis_diresa: '001',
    sis_tipo: '2',
    sis_numero: '00000001',
    sis_secuencia: '01',
  })
  const draft = { ...baseline, sis_diresa: '040' }
  expect(buildPatientPatch(baseline, draft)).toEqual({ sis_diresa: '040' })
  expect(draft.sis_secuencia).toBe('01')
})

type EditorOptions = Parameters<typeof useAdmissionPatientEditor>[0]
type Update = EditorOptions['update']

function setup(update: Update, overrides: Partial<EditorOptions> = {}) {
  const scope = effectScope()
  const source = shallowRef<Patient>(patient())
  const saves: Patient[] = []
  const editor = scope.run(() =>
    useAdmissionPatientEditor({
      patient: source,
      canEdit: true,
      blocked: false,
      update,
      onSaved: (value: Patient) => {
        saves.push(value)
        source.value = value
      },
      ...overrides,
    }),
  )!
  return { editor, source, saves, stop: () => scope.stop() }
}

test('typing has no HTTP side effect; one click saves all changes and disables resubmission', async () => {
  const calls: { id: number; patch: Record<string, unknown> }[] = []
  let finish: (value: Patient) => void = () => {}
  const harness = setup((id, patch) => {
    calls.push({ id, patch })
    return new Promise((resolve) => {
      finish = resolve
    })
  })
  try {
    const { editor } = harness
    editor.draft.primer_nombre = 'Ana'
    editor.draft.telefono_principal = ''
    await nextTick()
    expect(calls.length).toBe(0)
    expect(editor.dirty.value).toBe(true)
    const pending = editor.save()
    await editor.save()
    expect(calls.length).toBe(1)
    expect(calls[0]).toEqual({
      id: 100,
      patch: { primer_nombre: 'Ana', telefono_principal: null },
    })
    finish(aPatientFrom(calls[0]!.patch))
    await pending
    expect(editor.dirty.value).toBe(false)
    expect(editor.saving.value).toBe(false)
    expect(harness.saves.length).toBe(1)
    await editor.save()
    expect(calls.length).toBe(1)
  } finally {
    harness.stop()
  }
})

test('a failed save retains the draft and can be retried', async () => {
  let attempts = 0
  const harness = setup(async (_id, patch) => {
    if (++attempts === 1) throw new Error('Documento duplicado')
    return aPatientFrom(patch)
  })
  try {
    harness.editor.draft.numero_documento = '87654321'
    await harness.editor.save()
    expect(harness.editor.error.value).toBe('Documento duplicado')
    expect(harness.editor.draft.numero_documento).toBe('87654321')
    expect(harness.editor.dirty.value).toBe(true)
    expect(harness.saves.length).toBe(0)
    await harness.editor.save()
    expect(harness.editor.error.value).toBeNull()
    expect(harness.editor.dirty.value).toBe(false)
  } finally {
    harness.stop()
  }
})

test('related-record updates preserve pending core edits; discard restores saved data', async () => {
  const harness = setup(async () => {
    throw new Error('Unexpected request')
  })
  try {
    harness.editor.draft.primer_nombre = 'Cambio pendiente'
    harness.source.value = patient({
      responsables: [
        {
          id: 1,
          parentesco: 'MADRE',
          nombre_completo: 'Madre',
          tipo_documento_codigo: null,
          numero_documento: null,
          telefono: null,
          es_principal: true,
          activo: true,
        },
      ],
    })
    await nextTick()
    expect(harness.editor.draft.primer_nombre).toBe('Cambio pendiente')
    harness.editor.reset()
    expect(harness.editor.draft.primer_nombre).toBe('Paciente')
    expect(harness.editor.dirty.value).toBe(false)
    expect(harness.source.value.responsables.length).toBe(1)
    harness.source.value = { ...patient(), id: 101, primer_nombre: 'Otro paciente' }
    await nextTick()
    expect(harness.editor.draft.primer_nombre).toBe('Otro paciente')
  } finally {
    harness.stop()
  }
})

test('permission, ongoing attention and validation prevent writes', async () => {
  for (const overrides of [{ canEdit: false }, { blocked: true }, {}]) {
    let calls = 0
    const harness = setup(async () => {
      calls++
      return patient()
    }, overrides)
    try {
      harness.editor.draft.numero_documento = ''
      await harness.editor.save()
      expect(calls).toBe(0)
    } finally {
      harness.stop()
    }
  }
})

test('SIS is never inferred from the document or insurance; partial/invalid codes block save', async () => {
  const calls: { id: number; patch: Record<string, unknown> }[] = []
  const harness = setup(async (id, patch) => {
    calls.push({ id, patch })
    // El servidor conserva lo ya guardado y aplica solo el PATCH recibido.
    return { ...harness.source.value, ...patch }
  })
  try {
    const { editor } = harness
    expect(editor.draft.sis_numero).toBeNull()
    editor.draft.sis_tipo = '2'
    await editor.save()
    expect(editor.fieldErrors.value.sis_numero).toBeTruthy()
    expect(calls.length).toBe(0)
    editor.draft.sis_diresa = '040'
    editor.draft.sis_numero = '1234567'
    await editor.save()
    expect(calls.length).toBe(0)
    editor.draft.sis_numero = '00000001'
    await editor.save()
    expect(calls[0]!.patch).toEqual({
      sis_diresa: '040',
      sis_tipo: '2',
      sis_numero: '00000001',
    })
    expect(editor.draft.sis_numero).toBe('00000001')
    expect(editor.dirty.value).toBe(false)
    editor.draft.telefono_principal = '900000001'
    await editor.save()
    expect(calls[1]!.patch).toEqual({ telefono_principal: '900000001' })
    editor.draft.sis_diresa = ''
    editor.draft.sis_tipo = ''
    editor.draft.sis_numero = ''
    await editor.save()
    expect(calls[2]!.patch).toEqual({ sis_diresa: null, sis_tipo: null, sis_numero: null })
  } finally {
    harness.stop()
  }
})

test('changing patients and discarding edits never carries an affiliation across patients', async () => {
  const harness = setup(async (_id, patch) => aPatientFrom(patch))
  try {
    Object.assign(harness.editor.draft, {
      sis_diresa: '001',
      sis_tipo: 'E1',
      sis_numero: '000000001',
      sis_secuencia: '01',
    })
    expect(validatePatientDraft(harness.editor.draft, '2026-09-20')).toEqual({})
    harness.editor.reset()
    expect(harness.editor.draft.sis_secuencia).toBeNull()
    harness.editor.draft.sis_numero = '000000001'
    harness.source.value = { ...patient(), id: 101 }
    await nextTick()
    expect(harness.editor.draft.sis_numero).toBeNull()
    expect(harness.editor.dirty.value).toBe(false)
  } finally {
    harness.stop()
  }
})
