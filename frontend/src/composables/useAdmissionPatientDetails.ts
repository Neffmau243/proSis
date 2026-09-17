import { computed, onScopeDispose, shallowRef, toValue, watch, type MaybeRefOrGetter } from 'vue'
import {
  catalogos,
  type AgeGroupCatalogItem,
  type CodeCatalogItem,
  type IdCatalogItem,
  type RiskGroupCatalogItem,
} from '@/services/catalogos'
import type { Patient } from '@/services/pacientes'
import { calculateCalendarAge } from '@/utils/calendarAge'
import { useRemoteCatalog } from '@/composables/useRemoteCatalog'

/** Read-only catalog labels and calculated data, independent of persistence. */
export function useAdmissionPatientDetails(patient: MaybeRefOrGetter<Patient>) {
  const source = computed(() => toValue(patient))
  const tiposDocumento = shallowRef<CodeCatalogItem[]>([])
  const sexos = shallowRef<CodeCatalogItem[]>([])
  const seguros = shallowRef<IdCatalogItem[]>([])
  const gruposEtarios = shallowRef<AgeGroupCatalogItem[]>([])
  const gruposRiesgo = shallowRef<RiskGroupCatalogItem[]>([])
  const catalogError = shallowRef<string | null>(null)
  let version = 0
  const establishments = useRemoteCatalog({
    fetch: (query) => catalogos.establecimientos(query, 50, 0),
    key: (item) => item.id,
  })
  const districts = useRemoteCatalog({
    fetch: (query) => catalogos.ubigeos(query, 25, 0),
    key: (item) => item.codigo,
  })

  async function loadCatalogs(): Promise<void> {
    const request = ++version
    catalogError.value = null
    const results = await Promise.allSettled([
      catalogos.tiposDocumento().then((items) => {
        if (request === version) tiposDocumento.value = items
      }),
      catalogos.sexos().then((items) => {
        if (request === version) sexos.value = items
      }),
      catalogos.seguros().then((items) => {
        if (request === version) seguros.value = items
      }),
      catalogos.gruposEtarios().then((items) => {
        if (request === version) gruposEtarios.value = items
      }),
      catalogos.gruposRiesgo().then((items) => {
        if (request === version) gruposRiesgo.value = items
      }),
    ])
    if (request === version && results.some((result) => result.status === 'rejected')) {
      catalogError.value =
        'No se cargaron todos los catálogos. Puede reintentar y conservar sus cambios.'
    }
  }
  void loadCatalogs()
  void establishments.load()
  watch(
    () => source.value.ubigeo_residencia_codigo,
    (code) => {
      void districts.load(code || undefined)
    },
    { immediate: true },
  )
  onScopeDispose(() => {
    version += 1
  })

  const age = computed(() => calculateCalendarAge(source.value.fecha_nacimiento, new Date()))
  const ageLabel = computed(() => (age.value ? `${age.value.years} años` : '—'))
  const grupoEtarioLabel = computed(() => {
    if (!age.value) return '—'
    const months = age.value.years * 12 + age.value.months
    return (
      gruposEtarios.value.find(
        (group) =>
          group.activo &&
          group.edad_minima_meses !== null &&
          months >= group.edad_minima_meses &&
          (group.edad_maxima_meses === null || months <= group.edad_maxima_meses),
      )?.nombre ?? '—'
    )
  })

  return {
    tiposDocumento,
    sexos,
    seguros,
    gruposRiesgo,
    catalogError,
    loadCatalogs,
    establishments,
    districts,
    ageLabel,
    grupoEtarioLabel,
  }
}
