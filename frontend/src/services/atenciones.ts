import http from './http'
import type { PageResponse } from '@/types/api'

export interface AttentionServiceItem {
  numero_orden: number
  prestacion_codigo: string
  cantidad: string
}

export interface AttentionDiagnosisItem {
  numero_orden: number
  cie10_codigo: string
  tipo_diagnostico: string | null
  observacion: string | null
}

export interface Attention {
  id: number
  paciente_id: number
  establecimiento_id: number
  profesional_id: number
  especialidad_codigo: string | null
  consultorio_id: number
  modalidad_atencion_codigo: string
  grupo_etario_codigo: string
  fecha_atencion: string
  fecha_atendido: string | null
  historia_clinica_snapshot: string | null
  edad_anios: number | null
  peso_kg: string | null
  talla_cm: string | null
  perimetro_abdominal_cm: string | null
  presion_sistolica: number | null
  presion_diastolica: number | null
  temperatura_c: string | null
  pe: string | null
  te: string | null
  pt: string | null
  hora_inicio: string | null
  hora_fin: string | null
  admision: string | null
  observaciones: string | null
  estado: string
  created_by_usuario_id: number | null
  created_at: string
  updated_at: string
  prestaciones: AttentionServiceItem[]
  diagnosticos: AttentionDiagnosisItem[]
}

export interface AttentionSearchParams {
  paciente_id?: number
  establecimiento_id?: number
  profesional_id?: number
  desde?: string
  hasta?: string
  estado?: 'ATENDIDO' | 'ANULADO'
  limit: number
  offset: number
}

/**
 * Los indicadores derivados (P/E, T/E, P/T) se envían solo cuando el
 * profesional los registra: el backend no los calcula sin un protocolo activo.
 * `tipo` es obligatorio en el backend cuando se envía la valoración.
 */
export interface NutritionalSnapshotPayload {
  tipo: string
  hemoglobina?: number | null
  fecha_hemoglobina?: string | null
  edad_gestacional_semanas?: number | null
  imc?: number | null
  whz?: number | null
  haz?: number | null
  waz?: number | null
  diagnostico_peso_edad?: string | null
  diagnostico_talla_edad?: string | null
  diagnostico_peso_talla?: string | null
  diagnostico?: string | null
}

export interface AttentionCreatePayload {
  paciente_id: number
  establecimiento_id: number
  profesional_id: number
  especialidad_codigo?: string | null
  consultorio_id: number
  modalidad_atencion_codigo: 'AMBULATORIA' | 'EMERGENCIA'
  fecha_atencion: string
  fecha_atendido?: string | null
  peso_kg?: number | null
  talla_cm?: number | null
  perimetro_abdominal_cm?: number | null
  presion_sistolica?: number | null
  presion_diastolica?: number | null
  temperatura_c?: number | null
  pe?: string | null
  te?: string | null
  pt?: string | null
  hora_inicio?: string | null
  hora_fin?: string | null
  admision?: string | null
  observaciones?: string | null
  prestaciones?: { prestacion_codigo: string; cantidad: string }[]
  diagnosticos?: { cie10_codigo: string; tipo_diagnostico?: string | null; observacion?: string | null }[]
  valoracion_nutricional?: NutritionalSnapshotPayload | null
}

export interface FuaIssuePayload {
  atencion_id: number
  codigo_ciudad?: string | null
  codigo_eess?: string | null
  observaciones?: string | null
}

export interface FuaResponse {
  id: number
  atencion_id: number
  numero_fua: string | null
  codigo_ciudad: string | null
  codigo_anio: string | null
  codigo_eess: string | null
  edad_declarada: string | null
  fecha_emision: string
  estado: string
  observaciones: string | null
}

export interface CertificateIssuePayload {
  atencion_id: number
  tipo: string
  profesional_id?: number | null
  prestaciones?: string[]
}

export interface CertificateResponse {
  id: number
  atencion_id: number
  establecimiento_id: number
  profesional_id: number
  numero_certificado: string
  tipo: string
  fecha_emision: string
  consultorio: string | null
  admision: string | null
  estado: string
  prestaciones: string[]
}

export interface ReferralCreatePayload {
  atencion_id: number
  tipo: string
  establecimiento_destino_id: number
  motivo: string
  observaciones?: string | null
  estado: 'PENDIENTE'
}

export interface ReferralResponse {
  id: number
  atencion_id: number
  numero_referencia: string | null
  tipo: string
  establecimiento_origen_id: number
  establecimiento_destino_id: number
  fecha_emision: string
  motivo: string | null
  observaciones: string | null
  estado: string
}

export const atenciones = {
  async search(params: AttentionSearchParams): Promise<PageResponse<Attention>> {
    const { data } = await http.get<PageResponse<Attention>>('/atenciones/busqueda', {
      params,
    })
    return data
  },
  async listByPatient(patientId: number): Promise<Attention[]> {
    const { data } = await http.get<Attention[]>('/atenciones', {
      params: { paciente_id: patientId },
    })
    return data
  },
  async get(id: number): Promise<Attention> {
    const { data } = await http.get<Attention>(`/atenciones/${id}`)
    return data
  },
  async create(payload: AttentionCreatePayload): Promise<Attention> {
    const { data } = await http.post<Attention>('/atenciones', payload)
    return data
  },
  async cancel(
    id: number,
    payload: { observaciones: string },
  ): Promise<Attention> {
    const { data } = await http.post<Attention>(`/atenciones/${id}/anulacion`, payload)
    return data
  },
  async emitirFua(payload: FuaIssuePayload): Promise<FuaResponse> {
    const { data } = await http.post<FuaResponse>('/documentos/fua', payload)
    return data
  },
  async emitirCertificado(payload: CertificateIssuePayload): Promise<CertificateResponse> {
    const { data } = await http.post<CertificateResponse>(
      '/documentos/certificados',
      payload,
    )
    return data
  },
  async crearReferencia(payload: ReferralCreatePayload): Promise<ReferralResponse> {
    const { data } = await http.post<ReferralResponse>('/documentos/referencias', payload)
    return data
  },
}