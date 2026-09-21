import type { AxiosResponse, InternalAxiosRequestConfig } from 'axios'
import { beforeEach, expect, test } from 'vitest'

import { atenciones } from '@/services/atenciones'
import { changeMyPassword, listActiveLoginUsernames, login } from '@/services/auth'
import { catalogos } from '@/services/catalogos'
import { configuracion } from '@/services/configuracion'
import http from '@/services/http'
import { pacientes } from '@/services/pacientes'
import { usuarios } from '@/services/usuarios'

interface Recorded {
  method: string
  url: string
  params: Record<string, unknown> | undefined
  body: unknown
}

const requests: Recorded[] = []
let responseData: unknown = null

function stub(payload: unknown = null): void {
  responseData = payload
  http.defaults.adapter = async (config: InternalAxiosRequestConfig) => {
    requests.push({
      method: (config.method ?? 'get').toLowerCase(),
      url: config.url ?? '',
      params: config.params as Record<string, unknown> | undefined,
      body: typeof config.data === 'string' ? JSON.parse(config.data) : config.data,
    })
    return {
      data: responseData,
      status: 200,
      statusText: 'OK',
      headers: {},
      config,
    } as AxiosResponse
  }
}

beforeEach(() => {
  requests.length = 0
  stub()
})

test('pacientes: búsqueda, ficha, alta, edición y baja usan las rutas documentadas', async () => {
  stub({ items: [{ id: 1 }], total: 1, limit: 25, offset: 0, has_more: false })
  const page = await pacientes.search({
    q: 'Quispe',
    incluir_inactivos: true,
    limit: 25,
    offset: 50,
  })
  expect(page.items).toHaveLength(1)
  expect(requests[0]).toEqual({
    method: 'get',
    url: '/patients',
    params: { q: 'Quispe', incluir_inactivos: true, limit: 25, offset: 50 },
    body: undefined,
  })

  stub({ id: 7, numero_documento: '12345678' })
  const patient = await pacientes.get(7)
  expect(patient.id).toBe(7)
  expect(requests[1]!.url).toBe('/patients/7')

  stub({ id: 8 })
  await pacientes.create({
    tipo_documento_codigo: 'DNI',
    numero_documento: '12345678',
    fecha_nacimiento: '1990-05-10',
  })
  expect(requests[2]!.method).toBe('post')
  expect(requests[2]!.url).toBe('/patients')
  expect(requests[2]!.body).toEqual({
    tipo_documento_codigo: 'DNI',
    numero_documento: '12345678',
    fecha_nacimiento: '1990-05-10',
  })

  await pacientes.update(8, { telefono_principal: null })
  expect(requests[3]).toMatchObject({ method: 'patch', url: '/patients/8' })
  expect(requests[3]!.body).toEqual({ telefono_principal: null })

  stub({ id: 8, estado: false, mensaje: 'Paciente dado de baja.' })
  const deactivated = await pacientes.deactivate(8)
  expect(deactivated.estado).toBe(false)
  expect(requests[4]).toMatchObject({ method: 'delete', url: '/patients/8' })
})

test('pacientes: responsables y grupos de riesgo viajan con la fecha de inicio en la ruta', async () => {
  await pacientes.addResponsible(3, {
    parentesco: 'MADRE',
    nombre_completo: 'Ana Quispe',
    es_principal: true,
    activo: true,
  })
  expect(requests[0]).toMatchObject({ method: 'post', url: '/patients/3/responsibles' })
  expect(requests[0]!.body).toEqual({
    parentesco: 'MADRE',
    nombre_completo: 'Ana Quispe',
    es_principal: true,
    activo: true,
  })

  await pacientes.updateResponsible(3, 11, { telefono: '900000000' })
  expect(requests[1]).toMatchObject({ method: 'patch', url: '/patients/3/responsibles/11' })

  await pacientes.addRisk(3, { grupo_riesgo_id: 2, fecha_inicio: '2026-01-01' })
  expect(requests[2]).toMatchObject({ method: 'post', url: '/patients/3/risk-groups' })

  await pacientes.updateRisk(3, 2, '2026-01-01', { fecha_fin: '2026-02-01' })
  expect(requests[3]).toMatchObject({
    method: 'patch',
    url: '/patients/3/risk-groups/2/2026-01-01',
  })
  expect(requests[3]!.body).toEqual({ fecha_fin: '2026-02-01' })
})

test('atenciones: la búsqueda, la vista previa y los documentos no se confunden de ruta', async () => {
  stub({ items: [], total: 0, limit: 25, offset: 0, has_more: false })
  await atenciones.search({ paciente_id: 5, limit: 25, offset: 0 })
  expect(requests[0]).toMatchObject({ url: '/atenciones/busqueda' })

  await atenciones.listByPatient(5)
  expect(requests[1]).toEqual({
    method: 'get',
    url: '/atenciones',
    params: { paciente_id: 5 },
    body: undefined,
  })

  await atenciones.get(9)
  expect(requests[2]!.url).toBe('/atenciones/9')

  await atenciones.previewNutritionalIndicators({
    paciente_id: 5,
    fecha_atencion: '2026-09-19',
    peso_kg: 60,
    talla_cm: 160,
  })
  expect(requests[3]).toMatchObject({
    method: 'post',
    url: '/atenciones/indicadores-nutricionales/vista-previa',
  })

  await atenciones.cancel(9, { observaciones: 'Registrada por error' })
  expect(requests[4]).toMatchObject({ method: 'post', url: '/atenciones/9/anulacion' })

  await atenciones.emitirFua({ atencion_id: 9 })
  expect(requests[5]).toMatchObject({ method: 'post', url: '/documentos/fua' })

  await atenciones.emitirCertificado({ atencion_id: 9, tipo: 'APTO' })
  expect(requests[6]).toMatchObject({ method: 'post', url: '/documentos/certificados' })

  await atenciones.crearReferencia({
    atencion_id: 9,
    tipo: 'EMERGENCIA',
    establecimiento_destino_id: 2,
    motivo: 'Requiere hospitalización',
    estado: 'PENDIENTE',
  })
  expect(requests[7]).toMatchObject({ method: 'post', url: '/documentos/referencias' })
})

test('catálogos simples: cada método consulta su propio endpoint', async () => {
  await catalogos.etnias()
  await catalogos.tiposDocumento()
  await catalogos.sexos()
  await catalogos.seguros()
  await catalogos.profesiones()
  await catalogos.especialidades()
  await catalogos.modalidades()
  await catalogos.gruposEtarios()
  await catalogos.gruposRiesgo()

  expect(requests.map((request) => request.url)).toEqual([
    '/catalogos/etnias',
    '/catalogos/tipos-documento',
    '/catalogos/sexos',
    '/catalogos/seguros',
    '/catalogos/profesiones',
    '/catalogos/especialidades',
    '/catalogos/modalidades-atencion',
    '/catalogos/grupos-etarios',
    '/catalogos/grupos-riesgo',
  ])
  expect(requests.every((request) => request.method === 'get')).toBe(true)
})

test('catálogos buscables: los filtros vacíos se omiten y q exige dos caracteres', async () => {
  await catalogos.establecimientos(undefined, 50, 0)
  expect(requests[0]!.params).toEqual({ q: undefined, limit: 50, offset: 0 })

  await catalogos.prestaciones('  ', 25, 0)
  expect(requests[1]!.params).toEqual({ limit: 25, offset: 0 })

  await catalogos.prestaciones('A', 25, 0)
  expect(requests[2]!.params).toEqual({ limit: 25, offset: 0 })

  await catalogos.prestaciones('  laboratorio  ', 25, 25)
  expect(requests[3]!.params).toEqual({ q: 'laboratorio', limit: 25, offset: 25 })

  await catalogos.consultorios(4, undefined, 25, 0)
  expect(requests[4]!.params).toEqual({ establecimiento_id: 4, limit: 25, offset: 0 })

  await catalogos.consultorios(undefined, 'pediatría', 25, 0)
  expect(requests[5]!.params).toEqual({ q: 'pediatría', limit: 25, offset: 0 })

  await catalogos.cie10(undefined, 25, 0)
  await catalogos.profesionales('A', 25, 0)
  await catalogos.ubigeos('AREQUIPA', 25, 0)
  expect(requests[6]!.params).toEqual({ limit: 25, offset: 0 })
  expect(requests[7]!.params).toEqual({ limit: 25, offset: 0 })
  expect(requests[8]!.params).toEqual({ q: 'AREQUIPA', limit: 25, offset: 0 })
})

test('configuración de grupos etarios: lee y guarda el bloque completo', async () => {
  stub([{ codigo: 'NINO', nombre: 'Niño', activo: true }])
  const groups = await configuracion.gruposEtarios()
  expect(groups).toHaveLength(1)
  expect(requests[0]).toMatchObject({ method: 'get', url: '/configuracion/grupos-etarios' })

  await configuracion.guardarGruposEtarios({
    grupos: [{ codigo: 'NINO', edad_minima_meses: 0, edad_maxima_meses: 11, activo: true }],
    exigir_cobertura_continua: true,
  })
  expect(requests[1]).toMatchObject({ method: 'put', url: '/configuracion/grupos-etarios' })
  expect(requests[1]!.body).toEqual({
    grupos: [{ codigo: 'NINO', edad_minima_meses: 0, edad_maxima_meses: 11, activo: true }],
    exigir_cobertura_continua: true,
  })
})

test('autenticación: el login devuelve el token y el cambio de contraseña no espera cuerpo', async () => {
  stub({
    access_token: 'a.b.c',
    expires_in: 3600,
    usuario_id: 1,
    roles: ['ADMIN'],
    permisos: [],
  })
  const response = await login({ nombre_usuario: 'admin', password: '12345678' })
  expect(response.access_token).toBe('a.b.c')
  expect(requests[0]).toEqual({
    method: 'post',
    url: '/auth/login',
    params: undefined,
    body: { nombre_usuario: 'admin', password: '12345678' },
  })

  stub([{ nombre_usuario: 'admin' }, { nombre_usuario: 'medico.demo' }])
  expect(await listActiveLoginUsernames()).toEqual(['admin', 'medico.demo'])
  expect(requests[1]!.url).toBe('/auth/usuarios-activos')

  stub(null)
  await expect(
    changeMyPassword({
      current_password: '12345678',
      new_password: '87654321',
      new_password_confirmation: '87654321',
    }),
  ).resolves.toBeUndefined()
  expect(requests[2]).toMatchObject({ method: 'put', url: '/auth/me/password' })
})

test('usuarios: el alta de cuenta envía roles y profesional', async () => {
  stub({ id: 4, nombre_usuario: 'nuevo', roles: ['PROFESIONAL'] })

  const created = await usuarios.create({
    nombre_usuario: 'nuevo',
    password: '12345678',
    profesional_id: 12,
    roles: ['PROFESIONAL'],
  })

  expect(created.id).toBe(4)
  expect(requests[0]).toMatchObject({ method: 'post', url: '/usuarios' })
  expect(requests[0]!.body).toEqual({
    nombre_usuario: 'nuevo',
    password: '12345678',
    profesional_id: 12,
    roles: ['PROFESIONAL'],
  })
})
