import type { Patient } from '@/services/pacientes'

/** Paciente completo tal como lo devuelve `GET /patients/{id}`. */
export function aPatient(overrides: Partial<Patient> = {}): Patient {
  return {
    id: 100,
    codclie_legacy: null,
    historia_clinica: 'HC-TEST',
    historia_familiar: null,
    tipo_documento_codigo: 'DNI',
    numero_documento: '12345678',
    fecha_inscripcion: '2024-01-15',
    fecha_nacimiento: '1990-05-10',
    apellido_paterno: 'Prueba',
    apellido_materno: null,
    primer_nombre: 'Paciente',
    otros_nombres: null,
    sexo_codigo: 'F',
    ubigeo_residencia_codigo: '040101',
    distrito_residencia: 'Arequipa',
    localidad: 'Centro',
    localidad_id: null,
    direccion: 'Calle 1',
    establecimiento_registro_id: 1,
    seguro_id: 2,
    telefono_principal: '900000000',
    condicion: null,
    estado: true,
    created_at: '2024-01-15T00:00:00',
    updated_at: '2024-01-15T00:00:00',
    responsables: [],
    riesgos: [],
    ...overrides,
  }
}
