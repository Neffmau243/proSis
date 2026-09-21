import type { PatientSearchParams } from '../services/pacientes'

/** Modalidades de búsqueda del padrón; cada una usa un único criterio. */
export type SearchMode = 'dni' | 'hc_exacta' | 'hc_similar' | 'h_familiar' | 'nombres'

export interface SearchModeOption {
  value: SearchMode
  label: string
  placeholder: string
  /** Modalidad del sistema antiguo que el backend todavía no filtra. */
  pending?: string
}

/** El DNI es el dato que más se usa: es la modalidad por defecto. */
export const PATIENT_SEARCH_MODES: SearchModeOption[] = [
  { value: 'dni', label: 'DNI', placeholder: 'Escriba el número de DNI…' },
  {
    value: 'hc_exacta',
    label: 'H. Clínica exacta',
    placeholder: 'N° de historia clínica completo',
  },
  {
    value: 'hc_similar',
    label: 'H. Clínica similar',
    placeholder: 'Parte del N° de historia clínica',
  },
  { value: 'nombres', label: 'Apellidos y nombres', placeholder: 'Apellidos o nombres' },
  {
    value: 'h_familiar',
    label: 'H. Familiar',
    placeholder: 'Código de historia familiar',
    pending: 'Pendiente: el backend aún no filtra por historia familiar.',
  },
]

/** `q` es coincidencia parcial: la API rechaza patrones de un solo carácter. */
export const MIN_PARTIAL_SEARCH_LENGTH = 2

export interface SearchFilterOptions {
  incluirInactivos: boolean
  limit: number
  offset: number
}

/**
 * Traduce la modalidad elegida a los filtros que acepta el backend.
 *
 * Devuelve `null` cuando la modalidad todavía no tiene filtro en la API. Un
 * término vacío o demasiado corto para `q` lista toda la base, igual que al
 * abrir la tabla sin datos.
 */
export function buildPatientSearchParams(
  mode: SearchMode,
  term: string,
  options: SearchFilterOptions,
): PatientSearchParams | null {
  const value = term.trim()
  const base = {
    incluir_inactivos: options.incluirInactivos,
    limit: options.limit,
    offset: options.offset,
  }

  if (mode === 'h_familiar') return null

  // Sin dato: se lista toda la base, como al abrir la tabla en el sistema antiguo.
  if (!value) return { ...base }

  switch (mode) {
    case 'hc_exacta':
      return { ...base, historia_clinica: value }
    // El backend solo ofrece coincidencia parcial con `q` (DNI, historia
    // clínica y nombres); se usa para DNI, "dato similar" y apellidos. Con
    // menos de 2 caracteres no filtra y se sigue mostrando toda la base.
    case 'dni':
    case 'hc_similar':
    case 'nombres':
      if (value.length < MIN_PARTIAL_SEARCH_LENGTH) return { ...base }
      return { ...base, q: value }
  }
}

/** Aviso asociado a una modalidad que la API todavía no puede filtrar. */
export function pendingSearchModeNotice(mode: SearchMode): string | undefined {
  return PATIENT_SEARCH_MODES.find((option) => option.value === mode)?.pending
}
