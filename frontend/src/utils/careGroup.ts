import type { CareGroupCode } from '@/services/atenciones'

/** Etiquetas legibles para la población clínica declarada en la atención. */
export const CARE_GROUP_LABELS: Record<CareGroupCode, string> = {
  NINOS_ADOLESCENTES_ADULTOS_MAYORES: 'Niños, adolescentes, adultos y adultos mayores',
  GESTANTES: 'Gestantes',
  PUERPERAS: 'Puérperas',
}

/** Muestra la etiqueta del grupo cuando se conoce y el código crudo si no. */
export function careGroupLabel(code: string | null | undefined): string {
  if (!code) return '—'
  return CARE_GROUP_LABELS[code as CareGroupCode] ?? code
}
