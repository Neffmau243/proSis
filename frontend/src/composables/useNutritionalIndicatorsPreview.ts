import { onScopeDispose, readonly, shallowRef, toValue, watch, type MaybeRefOrGetter } from 'vue'

import { atenciones, type NutritionalIndicatorsPreview } from '@/services/atenciones'

interface NutritionalIndicatorsPreviewSource {
  patientId: MaybeRefOrGetter<number | null>
  attendedAt: MaybeRefOrGetter<string>
  weightKg: MaybeRefOrGetter<number | null>
  heightCm: MaybeRefOrGetter<number | null>
}

/**
 * Requests a debounced server-side nutritional calculation for the form.
 * Values returned here are strictly a preview: `create` calculates them again
 * before persisting the encounter.
 */
export function useNutritionalIndicatorsPreview(source: NutritionalIndicatorsPreviewSource) {
  const indicators = shallowRef<NutritionalIndicatorsPreview | null>(null)
  const loading = shallowRef(false)
  const error = shallowRef<string | null>(null)
  let timer: ReturnType<typeof setTimeout> | undefined
  let requestVersion = 0

  watch(
    [
      () => toValue(source.patientId),
      () => toValue(source.attendedAt),
      () => toValue(source.weightKg),
      () => toValue(source.heightCm),
    ],
    ([patientId, attendedAt, weightKg, heightCm]) => {
      requestVersion += 1
      const version = requestVersion
      if (timer) clearTimeout(timer)

      if (!patientId || !attendedAt) {
        indicators.value = null
        loading.value = false
        error.value = null
        return
      }

      loading.value = true
      error.value = null
      timer = setTimeout(async () => {
        try {
          const response = await atenciones.previewNutritionalIndicators({
            paciente_id: patientId,
            fecha_atencion: attendedAt,
            peso_kg: weightKg,
            talla_cm: heightCm,
          })
          if (version === requestVersion) indicators.value = response
        } catch {
          if (version === requestVersion) {
            indicators.value = null
            error.value =
              'No se pudo calcular los indicadores. Revise las medidas e intente de nuevo.'
          }
        } finally {
          if (version === requestVersion) loading.value = false
        }
      }, 300)
    },
    { immediate: true },
  )

  onScopeDispose(() => {
    if (timer) clearTimeout(timer)
    requestVersion += 1
  })

  return { indicators: readonly(indicators), loading: readonly(loading), error: readonly(error) }
}
