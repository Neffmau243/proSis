import type { PregnancyTypeCode } from '@/services/atenciones'

/** Opciones de pluralidad de la gestación, en el orden que muestra el formulario. */
export const PREGNANCY_TYPES: { value: PregnancyTypeCode; label: string }[] = [
  { value: 'UNICO', label: 'Embarazo único' },
  { value: 'MULTIPLE', label: 'Embarazo múltiple' },
]

/** Muestra la etiqueta del tipo cuando se conoce y el código crudo si no. */
export function pregnancyTypeLabel(code: string | null | undefined): string {
  if (!code) return '—'
  return PREGNANCY_TYPES.find((type) => type.value === code)?.label ?? code
}
