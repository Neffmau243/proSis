import { ref, watch } from 'vue'
import { emptyFuaInput } from '../utils/fuaPrint.ts'

/** Supplemental identity data belongs to exactly one selected patient. */
export function useFuaAdmissionDraft(patientId: () => number | null) {
  const fuaDialog = ref(false)
  const fuaDatos = ref(emptyFuaInput())
  watch(patientId, (id, previousId) => {
    if (id === previousId) return
    fuaDatos.value = emptyFuaInput()
    fuaDialog.value = false
  }, { flush: 'sync' })
  return { fuaDialog, fuaDatos }
}
