import { computed, ref, shallowRef, watch } from 'vue'
import type { Attention } from '../services/atenciones'

/** The print dialog can only see the server's successfully saved attention. */
export function useSavedAdmission(patientId: () => number | null) {
  const savedAttention = shallowRef<Attention | null>(null)
  const fuaDialog = ref(false)
  const attentionCreated = computed(() => savedAttention.value !== null)
  const fuaSnapshot = computed(() => savedAttention.value?.fua_impresion ?? null)
  function remember(attention: Attention): void {
    if (attention.paciente_id !== patientId()) throw new Error('La atención guardada no corresponde al paciente seleccionado.')
    savedAttention.value = attention
  }
  watch(patientId, () => {
    savedAttention.value = null
    fuaDialog.value = false
  }, { flush: 'sync' })
  return { savedAttention, attentionCreated, fuaSnapshot, fuaDialog, remember }
}
