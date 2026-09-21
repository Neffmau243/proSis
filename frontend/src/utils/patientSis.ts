/** SIS contract fields belong to the patient, not to an individual print request. */
export interface PatientSisData {
  sis_diresa: string | null
  sis_tipo: string | null
  sis_numero: string | null
  sis_secuencia: string | null
  etnia_codigo: string | null
}

export const patientSisContractFields = [
  { key: 'sis_diresa', label: 'SIS · DIRESA / DISA', kind: 'text', max: 3 },
  { key: 'sis_tipo', label: 'SIS · Tipo / formato', kind: 'text', max: 2 },
  { key: 'sis_numero', label: 'SIS · N.° afiliación', kind: 'text', max: 9 },
  { key: 'sis_secuencia', label: 'SIS · Secuencia / RN', kind: 'text', max: 2 },
] as const
export type PatientSisContractKey = (typeof patientSisContractFields)[number]['key']

export const patientSisFields = [
  ...patientSisContractFields,
  { key: 'etnia_codigo', label: 'Etnia declarada', kind: 'select' },
] as const

export function emptyPatientSis(): PatientSisData {
  return {
    sis_diresa: null,
    sis_tipo: null,
    sis_numero: null,
    sis_secuencia: null,
    etnia_codigo: null,
  }
}

/** Presentation only: values and ethnicity labels are supplied by the API. */
export function patientSisSummary(
  patient: Partial<PatientSisData>,
  ethnicities: readonly { codigo: string; nombre: string }[] = [],
) {
  const hasAffiliation = Boolean(
    patient.sis_diresa || patient.sis_tipo || patient.sis_numero || patient.sis_secuencia,
  )
  const ethnicity = ethnicities.find((item) => item.codigo === patient.etnia_codigo)
  return {
    affiliation: hasAffiliation
      ? [
          patient.sis_diresa || '—',
          patient.sis_tipo || '—',
          patient.sis_numero || '—',
          ...(patient.sis_secuencia ? [patient.sis_secuencia] : []),
        ].join(' - ')
      : 'Pendiente de carga',
    ethnicity: patient.etnia_codigo
      ? ethnicity
        ? `${ethnicity.codigo} · ${ethnicity.nombre}`
        : `Código ${patient.etnia_codigo}`
      : 'Pendiente de carga',
  }
}

export function patientSisErrors(
  value: Partial<PatientSisData>,
): Partial<Record<keyof PatientSisData, string>> {
  const errors: Partial<Record<keyof PatientSisData, string>> = {}
  const patterns = [
    ['sis_diresa', /^[A-Z0-9]{3}$/, 'Use 3 caracteres de la acreditación SIS.'],
    ['sis_tipo', /^[A-Z0-9]{1,2}$/, 'Use 1 o 2 caracteres del tipo/formato.'],
    ['sis_numero', /^\d{8,9}$/, 'Use 8 o 9 dígitos, incluidos los ceros iniciales.'],
    ['sis_secuencia', /^\d{1,2}$/, 'Use 1 o 2 dígitos, solo si corresponde.'],
  ] as const
  for (const [key, pattern, message] of patterns) {
    if (value[key]?.trim() && !pattern.test(value[key]!.trim().toUpperCase())) errors[key] = message
  }
  if (patterns.some(([key]) => value[key]?.trim())) {
    if (!value.sis_tipo?.trim()) errors.sis_tipo = 'Complete el tipo/formato de afiliación.'
    if (!value.sis_numero?.trim()) errors.sis_numero = 'Complete el número de afiliación.'
  }
  return errors
}
