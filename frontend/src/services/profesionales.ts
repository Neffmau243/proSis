import http from './http'

export interface ProfessionalSpecialty {
  especialidad_codigo: string
  es_principal: boolean
}

export interface ProfessionalResponse {
  id: number
  codigo_legacy: number | null
  numero_documento: string | null
  nombre_completo: string
  profesion_id: number | null
  colegiatura: string | null
  activo: boolean
  created_at: string
  updated_at: string
  especialidades: ProfessionalSpecialty[]
}

export interface ProfessionalCreatePayload {
  codigo_legacy?: number | null
  numero_documento?: string | null
  nombre_completo: string
  profesion_id?: number | null
  colegiatura?: string | null
  especialidades?: ProfessionalSpecialty[]
}

/**
 * The PATCH contract never touches specialties: those are replaced through
 * `replaceSpecialties` (PUT .../especialidades).
 */
export type ProfessionalUpdatePayload = Omit<
  Partial<ProfessionalCreatePayload>,
  'especialidades'
>

export const profesionales = {
  /** `incluir_inactivos` is the only query parameter the backend accepts. */
  async list(incluirInactivos = false): Promise<ProfessionalResponse[]> {
    const { data } = await http.get<ProfessionalResponse[]>('/configuracion/profesionales', {
      params: incluirInactivos ? { incluir_inactivos: true } : undefined,
    })
    return data
  },
  async get(id: number): Promise<ProfessionalResponse> {
    const { data } = await http.get<ProfessionalResponse>(`/configuracion/profesionales/${id}`)
    return data
  },
  async create(payload: ProfessionalCreatePayload): Promise<ProfessionalResponse> {
    const { data } = await http.post<ProfessionalResponse>('/configuracion/profesionales', payload)
    return data
  },
  async update(id: number, payload: ProfessionalUpdatePayload): Promise<ProfessionalResponse> {
    const { data } = await http.patch<ProfessionalResponse>(
      `/configuracion/profesionales/${id}`,
      payload,
    )
    return data
  },
  async replaceSpecialties(
    id: number,
    especialidades: ProfessionalSpecialty[],
  ): Promise<ProfessionalResponse> {
    const { data } = await http.put<ProfessionalResponse>(
      `/configuracion/profesionales/${id}/especialidades`,
      { especialidades },
    )
    return data
  },
  async deactivate(id: number): Promise<ProfessionalResponse> {
    const { data } = await http.delete<ProfessionalResponse>(`/configuracion/profesionales/${id}`)
    return data
  },
}
