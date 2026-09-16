import { computed, shallowRef, toValue, watch, type MaybeRefOrGetter } from 'vue'

import {
  catalogos,
  type AgeGroupCatalogItem,
  type CodeCatalogItem,
  type EstablishmentCatalogItem,
  type IdCatalogItem,
  type UbigeoCatalogItem,
} from '@/services/catalogos'
import type { Patient } from '@/services/pacientes'

export interface AdmissionPatientDetail {
  label: string
  value: string
  editableField?: AdmissionPatientEditableField
}

export type AdmissionPatientEditableField =
  | 'sexo_codigo'
  | 'localidad'
  | 'direccion'
  | 'establecimiento_registro_id'
  | 'seguro_id'

function valueOrDash(value: string | null | undefined): string {
  return value?.trim() || '—'
}

function formatDate(value: string | null): string {
  if (!value) return '—'
  const [year, month, day] = value.slice(0, 10).split('-')
  return year && month && day ? `${day}/${month}/${year}` : value
}

function ageAtToday(value: string): { years: number; months: number } | null {
  const [year, month, day] = value.slice(0, 10).split('-').map(Number)
  if (!year || !month || !day) return null

  const today = new Date()
  const dayHasPassed = today.getDate() >= day
  const birthdayHasPassed =
    today.getMonth() + 1 > month || (today.getMonth() + 1 === month && dayHasPassed)
  const years = Math.max(today.getFullYear() - year - Number(!birthdayHasPassed), 0)
  const months = Math.max(
    (today.getFullYear() - year) * 12 + (today.getMonth() + 1 - month) - Number(!dayHasPassed),
    0,
  )
  return { years, months }
}

export function useAdmissionPatientDetails(patient: MaybeRefOrGetter<Patient>) {
  const sexos = shallowRef<CodeCatalogItem[]>([])
  const seguros = shallowRef<IdCatalogItem[]>([])
  const gruposEtarios = shallowRef<AgeGroupCatalogItem[]>([])
  const establecimientos = shallowRef<EstablishmentCatalogItem[]>([])
  const establecimientosLoading = shallowRef(false)
  const ubigeos = shallowRef<UbigeoCatalogItem[]>([])
  let requestVersion = 0
  let establishmentSearchVersion = 0

  const currentPatient = computed(() => toValue(patient))

  const sexoLabel = computed(
    () =>
      sexos.value.find((sexo) => sexo.codigo === currentPatient.value.sexo_codigo)?.nombre ??
      valueOrDash(currentPatient.value.sexo_codigo),
  )

  const age = computed(() => ageAtToday(currentPatient.value.fecha_nacimiento))

  const birthLabel = computed(() => {
    const ageLabel = age.value ? `${age.value.years} años` : 'Edad no disponible'
    return `${formatDate(currentPatient.value.fecha_nacimiento)} · ${ageLabel}`
  })

  const distritoLabel = computed(() => {
    const code = currentPatient.value.ubigeo_residencia_codigo
    return ubigeos.value.find((ubigeo) => ubigeo.codigo === code)?.distrito ?? valueOrDash(code)
  })

  const establecimientoLabel = computed(() => {
    const id = currentPatient.value.establecimiento_registro_id
    if (!id) return '—'
    return (
      establecimientos.value.find((establecimiento) => establecimiento.id === id)?.nombre ??
      `#${id}`
    )
  })

  const seguroLabel = computed(() => {
    const id = currentPatient.value.seguro_id
    if (!id) return '—'
    return seguros.value.find((seguro) => seguro.id === id)?.nombre ?? `#${id}`
  })

  const riesgoLabel = computed(() => {
    const activos = currentPatient.value.riesgos
      .filter((riesgo) => !riesgo.fecha_fin)
      .map((riesgo) => riesgo.grupo_riesgo_nombre)
      .filter((nombre): nombre is string => Boolean(nombre))
    return activos.length > 0 ? activos.join(', ') : '—'
  })

  const motherLabel = computed(() => {
    const mothers = currentPatient.value.responsables.filter(
      (responsable) => responsable.activo && responsable.parentesco === 'MADRE',
    )
    return (
      mothers.find((responsable) => responsable.es_principal)?.nombre_completo ??
      mothers[0]?.nombre_completo ??
      '—'
    )
  })

  const grupoEtarioLabel = computed(() => {
    if (!age.value) return '—'
    return (
      gruposEtarios.value.find(
        (grupo) =>
          grupo.activo &&
          grupo.edad_minima_meses !== null &&
          age.value!.months >= grupo.edad_minima_meses &&
          (grupo.edad_maxima_meses === null || age.value!.months <= grupo.edad_maxima_meses),
      )?.nombre ?? '—'
    )
  })

  const details = computed<AdmissionPatientDetail[]>(() => {
    const source = currentPatient.value
    return [
      { label: 'N.° H. clínica', value: valueOrDash(source.historia_clinica) },
      { label: 'Historia familiar', value: valueOrDash(source.historia_familiar) },
      {
        label: source.tipo_documento_codigo === 'DNI' ? 'N.° DNI' : 'N.° documento',
        value: valueOrDash(source.numero_documento),
      },
      { label: 'Fecha nacimiento', value: birthLabel.value },
      { label: 'Apellido paterno', value: valueOrDash(source.apellido_paterno) },
      { label: 'Apellido materno', value: valueOrDash(source.apellido_materno) },
      { label: 'Primer nombre', value: valueOrDash(source.primer_nombre) },
      { label: 'Otros nombres', value: valueOrDash(source.otros_nombres) },
      { label: 'Sexo', value: sexoLabel.value, editableField: 'sexo_codigo' },
      { label: 'Distrito', value: distritoLabel.value },
      { label: 'Localidad', value: valueOrDash(source.localidad), editableField: 'localidad' },
      { label: 'Dirección', value: valueOrDash(source.direccion), editableField: 'direccion' },
      {
        label: 'Establecimiento',
        value: establecimientoLabel.value,
        editableField: 'establecimiento_registro_id',
      },
      { label: 'Seguro', value: seguroLabel.value, editableField: 'seguro_id' },
      { label: 'Teléfono', value: valueOrDash(source.telefono_principal) },
      { label: 'Grupo de riesgo', value: riesgoLabel.value },
      { label: 'Nombre de madre', value: motherLabel.value },
      { label: 'Grupo etáreo', value: grupoEtarioLabel.value },
    ]
  })

  watch(
    () => {
      const source = currentPatient.value
      return [
        source.id,
        source.ubigeo_residencia_codigo,
        source.establecimiento_registro_id,
      ] as const
    },
    async () => {
      const source = currentPatient.value
      const currentRequest = ++requestVersion
      establecimientosLoading.value = true

      try {
        const [
          sexosResult,
          segurosResult,
          gruposEtariosResult,
          establecimientosResult,
          ubigeosResult,
        ] = await Promise.all([
          catalogos.sexos(),
          catalogos.seguros(),
          catalogos.gruposEtarios(),
          catalogos.establecimientos(undefined, 100, 0),
          source.ubigeo_residencia_codigo
            ? catalogos.ubigeos(source.ubigeo_residencia_codigo, 25, 0)
            : Promise.resolve(null),
        ])

        if (currentRequest !== requestVersion) return
        sexos.value = sexosResult
        seguros.value = segurosResult
        gruposEtarios.value = gruposEtariosResult
        establecimientos.value = establecimientosResult.items
        ubigeos.value = ubigeosResult?.items ?? []
      } catch {
        // Los valores directos del paciente siguen siendo visibles si un catálogo no responde.
      } finally {
        if (currentRequest === requestVersion) establecimientosLoading.value = false
      }
    },
    { immediate: true },
  )

  async function searchEstablecimientos(query: string): Promise<void> {
    const currentRequest = ++establishmentSearchVersion
    establecimientosLoading.value = true
    try {
      const page = await catalogos.establecimientos(query.trim() || undefined, 100, 0)
      if (currentRequest !== establishmentSearchVersion) return
      establecimientos.value = page.items
    } catch {
      // El selector conserva las opciones ya cargadas si la búsqueda falla.
    } finally {
      if (currentRequest === establishmentSearchVersion) establecimientosLoading.value = false
    }
  }

  return {
    details,
    sexos,
    seguros,
    establecimientos,
    establecimientosLoading,
    searchEstablecimientos,
  }
}
