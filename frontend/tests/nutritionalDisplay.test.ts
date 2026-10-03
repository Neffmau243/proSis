import { expect, test } from 'vitest'
import { nutritionalRows } from '@/utils/nutritionalDisplay'
import type { NutritionalIndicatorsPreview } from '@/services/atenciones'

const result: NutritionalIndicatorsPreview = { imc: '23.438', pe: null, te: null, pt: null, estado: 'CALCULADO', mensaje: '', referencia: '', grupo_referencia: 'ADULTO', diagnostico_imc: 'Normal' }

test('adultos conservan los tres indicadores originales sin sustituirlos por IMC', () => {
  expect(nutritionalRows(result)).toHaveLength(3)
  expect(nutritionalRows(result).map(row => row.label)).toEqual(['Diagnóstico P/E', 'Diagnóstico T/E', 'Diagnóstico P/T'])
  expect(nutritionalRows(result).map(row => row.value)).toEqual(['No aplica', 'No aplica', 'No aplica'])
  expect(nutritionalRows({ ...result, grupo_referencia: 'ADULTO_MAYOR' })[1]?.value).toBe('No aplica')
})

test('escolares conservan las etiquetas y muestran solo puntajes aplicables', () => {
  const rows = nutritionalRows({ ...result, grupo_referencia: 'ESCOLAR', imc_edad: '1.8', te: '-0.5' })
  expect(rows.map(row => row.label)).toEqual(['Diagnóstico P/E', 'Diagnóstico T/E', 'Diagnóstico P/T'])
  expect(rows.map(row => row.value)).toEqual(['No aplica', 'Z: -0.5', 'No aplica'])
  expect(nutritionalRows({ ...result, grupo_referencia: 'ESCOLAR', pe: '0.1' }).map(row => row.label)).toContain('Diagnóstico P/E')
})

test('embarazo y puerperio mantienen los tres campos como No aplica', () => {
  const rows = nutritionalRows({ ...result, grupo_referencia: 'GESTANTE', imc_pregestacional: '21.5', ganancia_peso_kg: '5' })
  expect(rows.map(row => row.value)).toEqual(['No aplica', 'No aplica', 'No aplica'])
  expect(nutritionalRows({ ...result, grupo_referencia: 'PUERPERA' })).toHaveLength(3)
  expect(nutritionalRows({ ...result, grupo_referencia: 'PUERPERA' })[0]).toEqual({ label: 'Diagnóstico P/E', value: 'No aplica' })
})
