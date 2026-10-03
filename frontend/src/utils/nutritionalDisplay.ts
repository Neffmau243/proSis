import type { NutritionalIndicatorsPreview } from '@/services/atenciones'

/** Select the applicable results without relabeling one indicator as another. */
export function nutritionalRows(result: NutritionalIndicatorsPreview | null) {
  if (!result) return ['Diagnóstico P/E', 'Diagnóstico T/E', 'Diagnóstico P/T'].map(label => ({ label, value: 'Ingrese peso y talla' }))
  const group = result.grupo_referencia ?? 'INFANTIL'
  const value = (raw: string | null | undefined, diagnosis?: string | null, z = false) =>
    raw == null ? 'No disponible' : `${diagnosis ? `${diagnosis} · ` : ''}${z ? 'Z: ' : ''}${raw}`
  const notApplicable = ['ADULTO', 'ADULTO_MAYOR', 'GESTANTE', 'PUERPERA'].includes(group)
  const rows = [
    { label: 'Diagnóstico P/E', value: value(result.pe, result.diagnostico_peso_edad, true) },
    { label: 'Diagnóstico T/E', value: value(result.te, result.diagnostico_talla_edad, true) },
    { label: 'Diagnóstico P/T', value: value(result.pt, result.diagnostico_peso_talla, true) },
  ]
  if (notApplicable) return rows.map(row => ({ ...row, value: 'No aplica' }))
  if (group === 'ESCOLAR') {
    rows[2]!.value = 'No aplica'
    if (result.pe == null && result.estado === 'CALCULADO') rows[0]!.value = 'No aplica'
  }
  return rows
}
