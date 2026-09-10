import http from './http'

export interface AgeBoundary {
  anios: number
  meses: number
}

export interface AgeGroupResponse {
  codigo: string
  nombre: string
  edad_minima_meses: number | null
  edad_maxima_meses: number | null
  edad_minima: AgeBoundary | null
  edad_maxima: AgeBoundary | null
  rango_edad_legible: string
  activo: boolean
}

export interface AgeGroupSavePayload {
  grupos: {
    codigo: string
    edad_minima_meses: number | null
    edad_maxima_meses: number | null
    activo: boolean
  }[]
  exigir_cobertura_continua: boolean
}

export const configuracion = {
  async gruposEtarios(): Promise<AgeGroupResponse[]> {
    const { data } = await http.get<AgeGroupResponse[]>('/configuracion/grupos-etarios')
    return data
  },
  async guardarGruposEtarios(payload: AgeGroupSavePayload): Promise<AgeGroupResponse[]> {
    const { data } = await http.put<AgeGroupResponse[]>('/configuracion/grupos-etarios', payload)
    return data
  },
}