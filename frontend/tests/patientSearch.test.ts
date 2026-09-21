import { describe, expect, test } from 'vitest'

import {
  MIN_PARTIAL_SEARCH_LENGTH,
  PATIENT_SEARCH_MODES,
  buildPatientSearchParams,
  pendingSearchModeNotice,
} from '../src/utils/patientSearch'

const options = { incluirInactivos: false, limit: 100, offset: 0 }
const build = (mode: Parameters<typeof buildPatientSearchParams>[0], term: string) =>
  buildPatientSearchParams(mode, term, options)

describe('contrato de búsqueda de pacientes', () => {
  test('cada modalidad usa un solo criterio y el que le corresponde', () => {
    expect(build('dni', '12345678')).toEqual({
      incluir_inactivos: false,
      limit: 100,
      offset: 0,
      q: '12345678',
    })
    expect(build('hc_exacta', 'HC-0001')).toEqual({
      incluir_inactivos: false,
      limit: 100,
      offset: 0,
      historia_clinica: 'HC-0001',
    })
    expect(build('hc_similar', 'HC-0')).toEqual({
      incluir_inactivos: false,
      limit: 100,
      offset: 0,
      q: 'HC-0',
    })
    expect(build('nombres', 'Quispe Mamani')).toEqual({
      incluir_inactivos: false,
      limit: 100,
      offset: 0,
      q: 'Quispe Mamani',
    })
  })

  test('la historia clínica exacta nunca se mezcla con la coincidencia parcial', () => {
    for (const mode of ['dni', 'hc_exacta', 'hc_similar', 'nombres'] as const) {
      const params = build(mode, 'HC-0001')!
      expect('q' in params && 'historia_clinica' in params, mode).toBe(false)
      // Solo se agrega el criterio de texto: el resto son flags de paginación.
      const criteria = Object.keys(params).filter(
        (key) => !['incluir_inactivos', 'limit', 'offset'].includes(key),
      )
      expect(criteria.length, mode).toBe(1)
    }
  })

  test('un término vacío lista la base sin criterio de texto', () => {
    for (const mode of ['dni', 'hc_exacta', 'hc_similar', 'nombres'] as const) {
      for (const term of ['', '   ']) {
        expect(build(mode, term), `${mode} con "${term}"`).toEqual({
          incluir_inactivos: false,
          limit: 100,
          offset: 0,
        })
      }
    }
  })

  test('un término de un carácter solo filtra en historia clínica exacta', () => {
    // La API acepta `historia_clinica` desde un carácter, pero `q` desde dos.
    for (const mode of ['dni', 'hc_similar', 'nombres'] as const) {
      expect(build(mode, 'A'), mode).toEqual({ incluir_inactivos: false, limit: 100, offset: 0 })
    }
    expect(build('hc_exacta', 'A')).toEqual({
      incluir_inactivos: false,
      limit: 100,
      offset: 0,
      historia_clinica: 'A',
    })
  })

  test('q solo viaja a partir del mínimo que exige la API y sin espacios sobrantes', () => {
    expect(MIN_PARTIAL_SEARCH_LENGTH).toBe(2)
    expect(build('dni', ' 12345678 ')!.q).toBe('12345678')
    expect(build('nombres', '  AB ')!.q).toBe('AB')
    expect('q' in build('dni', '1')!).toBe(false)
    expect('q' in build('nombres', ' A ')!).toBe(false)
  })

  test('historia familiar sigue sin filtro y su aviso se obtiene de la definición', () => {
    expect(build('h_familiar', 'HF-9')).toBeNull()
    expect(build('h_familiar', '')).toBeNull()
    expect(pendingSearchModeNotice('h_familiar')).toMatch(/historia familiar/i)
    expect(pendingSearchModeNotice('dni')).toBeUndefined()
  })

  test('incluir bajas y paginación se conservan en todas las modalidades', () => {
    expect(
      buildPatientSearchParams('hc_exacta', 'HC-1', {
        incluirInactivos: true,
        limit: 25,
        offset: 50,
      }),
    ).toEqual({
      incluir_inactivos: true,
      limit: 25,
      offset: 50,
      historia_clinica: 'HC-1',
    })
  })

  test('el selector ofrece cada modalidad una vez y solo H. Familiar queda pendiente', () => {
    const values = PATIENT_SEARCH_MODES.map((option) => option.value)
    expect(new Set(values).size).toBe(values.length)
    expect(
      PATIENT_SEARCH_MODES.filter((option) => option.pending).map((option) => option.value),
    ).toEqual(['h_familiar'])
    // El DNI encabeza la lista porque es el criterio más usado.
    expect(values[0]).toBe('dni')
    for (const option of PATIENT_SEARCH_MODES) {
      expect(option.label, option.value).toBeTruthy()
      expect(option.placeholder, option.value).toBeTruthy()
    }
  })
})
