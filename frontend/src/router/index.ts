import { createRouter, createWebHistory } from 'vue-router'

import { isSessionExpired, loadSession } from '@/services/session-storage'

// Tipado adicional para el meta de cada ruta.
declare module 'vue-router' {
  interface RouteMeta {
    title?: string
    requiresAuth?: boolean
    /** Permisos (códigos del backend) requeridos para ver la ruta. */
    permissions?: string[]
  }
}

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { title: 'Iniciar sesión' },
    },
    {
      path: '/',
      component: () => import('@/layouts/AppLayout.vue'),
      meta: { requiresAuth: true },
      children: [
        {
          path: '',
          name: 'inicio',
          component: () => import('@/views/DashboardView.vue'),
          meta: { title: 'Inicio' },
        },
        {
          path: 'cuenta/cambiar-contrasena',
          name: 'cambiar-contrasena',
          component: () => import('@/views/CambiarContrasenaView.vue'),
          meta: { title: 'Cambiar contraseña' },
        },
        {
          path: 'pacientes',
          name: 'pacientes',
          component: () => import('@/views/PacientesListView.vue'),
          meta: { title: 'Pacientes', permissions: ['PACIENTE_LEER'] },
        },
        {
          path: 'pacientes/nuevo',
          name: 'paciente-nuevo',
          component: () => import('@/views/PacienteNuevoView.vue'),
          meta: { title: 'Nuevo paciente', permissions: ['PACIENTE_EDITAR'] },
        },
        {
          path: 'pacientes/:id',
          name: 'paciente-detalle',
          component: () => import('@/views/PacienteDetalleView.vue'),
          meta: { title: 'Ficha del paciente', permissions: ['PACIENTE_LEER'] },
        },
        {
          path: 'pacientes/:id/editar',
          name: 'paciente-editar',
          component: () => import('@/views/PacienteEditarView.vue'),
          meta: { title: 'Editar paciente', permissions: ['PACIENTE_EDITAR'] },
        },
        {
          path: 'atenciones',
          name: 'atenciones',
          component: () => import('@/views/AtencionesListView.vue'),
          meta: { title: 'Historial de atenciones', permissions: ['ATENCION_LEER'] },
        },
        {
          path: 'atenciones/nueva',
          name: 'atencion-nueva',
          component: () => import('@/views/AtencionNuevaView.vue'),
          meta: { title: 'Nueva atención', permissions: ['ATENCION_CREAR'] },
        },
        {
          path: 'atenciones/:id',
          name: 'atencion-detalle',
          component: () => import('@/views/AtencionDetalleView.vue'),
          meta: { title: 'Detalle de atención', permissions: ['ATENCION_LEER'] },
        },
        {
          path: 'configuracion/usuarios',
          name: 'usuarios',
          component: () => import('@/views/UsuariosView.vue'),
          meta: { title: 'Usuarios', permissions: ['USUARIO_GESTIONAR'] },
        },
        {
          path: 'configuracion/auditoria',
          name: 'auditoria',
          component: () => import('@/views/AuditoriaView.vue'),
          meta: { title: 'Auditoría', permissions: ['AUDITORIA_LEER'] },
        },
        {
          path: 'configuracion/grupos-etarios',
          name: 'grupos-etarios',
          component: () => import('@/views/GruposEtariosView.vue'),
          meta: {
            title: 'Grupos etarios',
            permissions: ['GRUPO_ETARIO_CONFIGURAR'],
          },
        },
        {
          path: 'configuracion/profesionales',
          name: 'profesionales',
          component: () => import('@/views/ProfesionalesView.vue'),
          meta: { title: 'Profesionales', permissions: ['PROFESIONAL_GESTIONAR'] },
        },
        {
          path: 'configuracion/consultorios',
          name: 'consultorios',
          component: () => import('@/views/ConsultoriosView.vue'),
          meta: { title: 'Consultorios', permissions: ['CONSULTORIO_GESTIONAR'] },
        },
      ],
    },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

router.beforeEach((to) => {
  const session = loadSession()

  if (to.meta.requiresAuth) {
    if (!session || isSessionExpired(session)) {
      return { name: 'login', query: { redirect: to.fullPath } }
    }
    // Los permisos viajan en el token/sesión; el backend sigue siendo la
    // autoridad final, esto solo oculta rutas en la interfaz.
    if (to.meta.permissions?.length) {
      const missing = to.meta.permissions.filter(
        (permission) => !session.permisos.includes(permission),
      )
      if (missing.length > 0) {
        return { name: 'inicio' }
      }
    }
  }

  if (to.name === 'login' && session && !isSessionExpired(session)) {
    return { name: 'inicio' }
  }

  return true
})

router.afterEach((to) => {
  document.title = to.meta.title
    ? `${to.meta.title} · Sistema de Salud IPRESS`
    : 'Sistema de Salud IPRESS'
})

export default router