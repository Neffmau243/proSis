import { effectScope, ref } from 'vue'
import { expect, test } from 'vitest'

import { useFuaAdmissionDraft } from '../src/composables/useFuaAdmissionDraft'

test('changing patient clears SIS, ethnicity, referral and open preview synchronously', () => {
  const scope = effectScope()
  scope.run(() => {
    const patientId = ref<number | null>(1)
    const state = useFuaAdmissionDraft(() => patientId.value)
    state.fuaDatos.value.sis_numero = '00000001'
    state.fuaDatos.value.etnia_codigo = '58'
    state.fuaDatos.value.referencia_nombre = 'HOSPITAL DE PRUEBA'
    state.fuaDialog.value = true
    patientId.value = 2
    expect(state.fuaDatos.value.sis_numero).toBeNull()
    expect(state.fuaDatos.value.etnia_codigo).toBeNull()
    expect(state.fuaDatos.value.referencia_nombre).toBeNull()
    expect(state.fuaDialog.value).toBe(false)
    state.fuaDatos.value.sis_numero = '00000002'
    patientId.value = 2
    expect(state.fuaDatos.value.sis_numero).toBe('00000002')
    patientId.value = null
    expect(state.fuaDatos.value.sis_numero).toBeNull()
  })
  scope.stop()
})
