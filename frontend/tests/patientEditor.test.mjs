import assert from 'node:assert/strict'
import test from 'node:test'
import { effectScope, nextTick, shallowRef } from 'vue'
import {
  buildPatientPatch,
  createPatientDraft,
  validatePatientDraft,
} from '../src/utils/patientDraft.ts'
import { useAdmissionPatientEditor } from '../src/composables/useAdmissionPatientEditor.ts'

const patient = () => ({
  id: 100,
  estado: true,
  historia_clinica: 'HC-TEST',
  historia_familiar: null,
  tipo_documento_codigo: 'DNI',
  numero_documento: '12345678',
  fecha_nacimiento: '1990-05-10',
  fecha_inscripcion: '2024-01-15',
  apellido_paterno: 'Prueba',
  apellido_materno: null,
  primer_nombre: 'Paciente',
  otros_nombres: null,
  sexo_codigo: 'F',
  ubigeo_residencia_codigo: '040101',
  distrito_residencia: 'Arequipa',
  localidad: 'Centro',
  direccion: 'Calle 1',
  establecimiento_registro_id: 1,
  seguro_id: 2,
  telefono_principal: '900000000',
  condicion: null,
  responsables: [],
  riesgos: [],
})

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
  assert.deepEqual(buildPatientPatch(baseline, draft), {
    primer_nombre: 'Ana',
    telefono_principal: null,
  })
  assert.equal(original.primer_nombre, 'Paciente')
  assert.deepEqual(buildPatientPatch(baseline, { ...baseline, primer_nombre: ' Paciente ' }), {})
})

test('validation handles required values, real dates and residence hierarchy', () => {
  const draft = createPatientDraft(patient())
  assert.deepEqual(validatePatientDraft(draft, '2026-09-17'), {})
  assert.ok(validatePatientDraft({ ...draft, fecha_nacimiento: '' }, '2026-09-17').fecha_nacimiento)
  assert.ok(
    validatePatientDraft({ ...draft, fecha_nacimiento: '2026-02-30' }, '2026-09-17')
      .fecha_nacimiento,
  )
  assert.ok(
    validatePatientDraft({ ...draft, fecha_nacimiento: '2027-01-01' }, '2026-09-17')
      .fecha_nacimiento,
  )
  assert.ok(
    validatePatientDraft({ ...draft, numero_documento: ' ' }, '2026-09-17').numero_documento,
  )
  assert.ok(
    validatePatientDraft({ ...draft, ubigeo_residencia_codigo: null }, '2026-09-17').localidad,
  )
  assert.ok(validatePatientDraft({ ...draft, localidad: '040101' }, '2026-09-17').localidad)
})

function setup(update, overrides = {}) {
  const scope = effectScope()
  const source = shallowRef(patient())
  const saves = []
  const editor = scope.run(() =>
    useAdmissionPatientEditor({
      patient: source,
      canEdit: true,
      blocked: false,
      update,
      onSaved: (value) => {
        saves.push(value)
        source.value = value
      },
      ...overrides,
    }),
  )
  return { editor, source, saves, stop: () => scope.stop() }
}

test('typing has no HTTP side effect; one click saves all changes and disables resubmission', async () => {
  const calls = []
  let finish
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
    assert.equal(calls.length, 0)
    assert.equal(editor.dirty.value, true)
    const pending = editor.save()
    await editor.save()
    assert.equal(calls.length, 1)
    assert.deepEqual(calls[0], {
      id: 100,
      patch: { primer_nombre: 'Ana', telefono_principal: null },
    })
    finish({ ...patient(), ...calls[0].patch })
    await pending
    assert.equal(editor.dirty.value, false)
    assert.equal(editor.saving.value, false)
    assert.equal(harness.saves.length, 1)
    await editor.save()
    assert.equal(calls.length, 1)
  } finally {
    harness.stop()
  }
})

test('a failed save retains the draft and can be retried', async () => {
  let attempts = 0
  const harness = setup(async (_id, patch) => {
    if (++attempts === 1) throw new Error('Documento duplicado')
    return { ...patient(), ...patch }
  })
  try {
    harness.editor.draft.numero_documento = '87654321'
    await harness.editor.save()
    assert.equal(harness.editor.error.value, 'Documento duplicado')
    assert.equal(harness.editor.draft.numero_documento, '87654321')
    assert.equal(harness.editor.dirty.value, true)
    assert.equal(harness.saves.length, 0)
    await harness.editor.save()
    assert.equal(harness.editor.error.value, null)
    assert.equal(harness.editor.dirty.value, false)
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
    harness.source.value = {
      ...harness.source.value,
      responsables: [{ id: 1, nombre_completo: 'Madre' }],
    }
    await nextTick()
    assert.equal(harness.editor.draft.primer_nombre, 'Cambio pendiente')
    harness.editor.reset()
    assert.equal(harness.editor.draft.primer_nombre, 'Paciente')
    assert.equal(harness.editor.dirty.value, false)
    assert.equal(harness.source.value.responsables.length, 1)
    harness.source.value = { ...patient(), id: 101, primer_nombre: 'Otro paciente' }
    await nextTick()
    assert.equal(harness.editor.draft.primer_nombre, 'Otro paciente')
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
      assert.equal(calls, 0)
    } finally {
      harness.stop()
    }
  }
})
