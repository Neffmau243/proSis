<template>
  <el-container class="app-layout">
    <el-aside width="264px" class="side">
      <!-- Marca -->
      <div class="side__brand">
        <span class="side__logo"><el-icon><FirstAidKit /></el-icon></span>
        <span class="side__brand-text">
          <span class="side__brand-name">IPRESS</span>
          <span class="side__brand-sub">Sistema de Salud</span>
        </span>
      </div>

      <!-- Registro de pacientes -->
      <div v-if="can('PACIENTE_EDITAR')" class="side__actions">
        <el-button class="side__action side__action--ghost" @click="nuevoPaciente">
          <el-icon><UserFilled /></el-icon>
          <span>Nuevo paciente</span>
        </el-button>
      </div>

      <!-- Contexto: paciente activo -->
      <div v-if="can('PACIENTE_LEER')" class="side__patient" :class="{ 'is-empty': !seleccionado }">
        <template v-if="seleccionado">
          <span class="side__patient-label">Paciente seleccionado</span>
          <span class="side__patient-name">{{ nombreSeleccionado }}</span>
          <span class="side__patient-meta">
            {{ seleccionado.tipo_documento_codigo }} {{ seleccionado.numero_documento }}
            <template v-if="seleccionado.historia_clinica">
              · HC {{ seleccionado.historia_clinica }}
            </template>
          </span>
          <div class="side__patient-actions">
            <el-button
              v-if="can('ATENCION_CREAR')"
              size="small"
              type="primary"
              @click="iniciarAdmision"
            >
              <el-icon><FirstAidKit /></el-icon>
              <span>Iniciar admisión</span>
            </el-button>
          </div>
        </template>
        <span v-else class="side__patient-hint">
          Seleccione un paciente en la tabla para iniciar su admisión.
        </span>
      </div>

      <!-- Navegación -->
      <nav class="side__nav">
        <template v-for="section in navSections" :key="section.title">
          <p class="side__section">{{ section.title }}</p>
          <router-link
            v-for="item in section.items"
            :key="item.to"
            :to="item.to"
            class="side__link"
            :class="{ 'is-active': isActive(item) }"
          >
            <el-icon class="side__link-icon"><component :is="item.icon" /></el-icon>
            <span>{{ item.label }}</span>
          </router-link>
        </template>
      </nav>

      <!-- Usuario + salir -->
      <div class="side__footer">
        <div class="side__user">
          <span class="side__avatar">{{ iniciales }}</span>
          <span class="side__user-info">
            <span class="side__user-name">{{ auth.nombreUsuario || 'Usuario' }}</span>
            <span class="side__user-role">{{ auth.roles.join(' · ') || 'sin rol' }}</span>
          </span>
        </div>
        <el-button class="side__salir" @click="salir">
          <el-icon><SwitchButton /></el-icon>
          <span>Salir</span>
        </el-button>
      </div>
    </el-aside>

    <el-container>
      <el-header class="topbar">
        <div class="topbar__title">{{ currentTitle }}</div>
        <el-dropdown @command="handleCommand">
          <span class="topbar__user">
            <span class="topbar__avatar">{{ iniciales }}</span>
            {{ auth.nombreUsuario || 'Usuario' }}
            <el-icon><ArrowDown /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="password">Cambiar contraseña</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </el-header>

      <el-main class="app-layout__main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import { usePacienteSeleccionado } from '@/composables/usePacienteSeleccionado'
import { useAuthStore } from '@/stores/auth'

interface NavItem {
  to: string
  label: string
  icon: string
  /** Rutas hijas que también deben marcar el ítem como activo. */
  match?: (path: string) => boolean
}

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const { seleccionado } = usePacienteSeleccionado()

const currentTitle = computed(() => route.meta.title ?? '')

const iniciales = computed(() => {
  const name = (auth.nombreUsuario || 'U').trim()
  return name
    .split(/[\s._-]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? '')
    .join('')
})

const nombreSeleccionado = computed(() => {
  const patient = seleccionado.value
  if (!patient) return ''
  return (
    [patient.apellido_paterno, patient.apellido_materno, patient.primer_nombre]
      .filter(Boolean)
      .join(' ') || patient.numero_documento
  )
})

/** Secciones de navegación filtradas por permiso (no por rol escrito). */
const navSections = computed(() => {
  const sections: { title: string; items: NavItem[] }[] = []

  const main: NavItem[] = []
  if (can('PACIENTE_LEER')) {
    main.push({
      to: '/',
      label: 'Base de datos',
      icon: 'Grid',
      match: (path) => path === '/' || path.startsWith('/pacientes'),
    })
  }
  main.push({ to: '/laboratorio', label: 'Ref. Laboratorio', icon: 'Files' })
  sections.push({ title: 'Principal', items: main })

  const clinic: NavItem[] = []
  if (can('ATENCION_LEER')) {
    clinic.push({
      to: '/atenciones',
      label: 'Historial de atenciones',
      icon: 'Document',
      match: (path) => path.startsWith('/atenciones') && path !== '/atenciones/nueva',
    })
  }
  if (can('ATENCION_CREAR')) {
    clinic.push({ to: '/atenciones/nueva', label: 'Nueva atención', icon: 'FirstAidKit' })
  }
  if (clinic.length) sections.push({ title: 'Clínico', items: clinic })

  const admin: NavItem[] = []
  if (can('USUARIO_GESTIONAR')) admin.push({ to: '/configuracion/usuarios', label: 'Usuarios', icon: 'User' })
  if (can('AUDITORIA_LEER')) admin.push({ to: '/configuracion/auditoria', label: 'Auditoría', icon: 'DataLine' })
  if (admin.length) sections.push({ title: 'Administración', items: admin })

  const config: NavItem[] = []
  if (can('GRUPO_ETARIO_CONFIGURAR')) {
    config.push({ to: '/configuracion/grupos-etarios', label: 'Grupos etarios', icon: 'Odometer' })
  }
  if (can('PROFESIONAL_GESTIONAR')) {
    config.push({ to: '/configuracion/profesionales', label: 'Profesionales', icon: 'UserFilled' })
  }
  if (can('CONSULTORIO_GESTIONAR')) {
    config.push({ to: '/configuracion/consultorios', label: 'Consultorios', icon: 'OfficeBuilding' })
  }
  if (config.length) sections.push({ title: 'Configuración', items: config })

  return sections
})

function can(permission: string): boolean {
  return auth.hasPermission(permission)
}

function isActive(item: NavItem): boolean {
  return item.match ? item.match(route.path) : route.path === item.to
}

function nuevoPaciente(): void {
  router.push({ name: 'paciente-nuevo' })
}

function iniciarAdmision(): void {
  const patient = seleccionado.value
  if (!patient) {
    ElMessage.warning('Seleccione un paciente en la tabla Base de datos.')
    return
  }
  router.push({ name: 'admision', query: { patientId: String(patient.id) } })
}

function salir(): void {
  auth.logout()
  router.push({ name: 'login' })
}

function handleCommand(command: string): void {
  if (command === 'password') {
    router.push({ name: 'cambiar-contrasena' })
  }
}
</script>

<style scoped>
.app-layout {
  height: 100%;
}

/* ---------- Barra lateral ---------- */
.side {
  display: flex;
  flex-direction: column;
  background-color: #fff;
  border-right: 1px solid var(--el-border-color-lighter);
}

.side__brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 18px 18px 14px;
}

.side__logo {
  display: grid;
  place-items: center;
  width: 40px;
  height: 40px;
  border-radius: 12px;
  font-size: 20px;
  color: #fff;
  background: linear-gradient(140deg, var(--el-color-primary), var(--el-color-primary-dark-2));
  box-shadow: 0 6px 14px -6px var(--el-color-primary);
}

.side__brand-text {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}

.side__brand-name {
  font-size: 15px;
  font-weight: 700;
  letter-spacing: 0.04em;
  color: var(--el-text-color-primary);
}

.side__brand-sub {
  font-size: 11px;
  color: var(--el-text-color-secondary);
}

.side__actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 4px 16px 16px;
}

.side__action {
  width: 100%;
  height: 42px;
  margin-left: 0 !important;
  border-radius: 10px;
  font-weight: 600;
  justify-content: center;
}

.side__action--ghost {
  background-color: var(--el-fill-color-light);
  border-color: transparent;
  color: var(--el-text-color-primary);
}

.side__action--ghost:hover {
  background-color: var(--el-fill-color);
  border-color: transparent;
  color: var(--el-color-primary);
}

/* Tarjeta de paciente activo */
.side__patient {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin: 0 16px 8px;
  padding: 12px;
  border-radius: 12px;
  border: 1px solid var(--el-color-primary-light-7);
  background-color: var(--el-color-primary-light-9);
}

.side__patient.is-empty {
  border-style: dashed;
  border-color: var(--el-border-color);
  background-color: transparent;
}

.side__patient-label {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--el-color-primary);
}

.side__patient-name {
  font-size: 13.5px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.side__patient-meta {
  font-size: 11.5px;
  color: var(--el-text-color-secondary);
}

.side__patient-hint {
  font-size: 11.5px;
  font-style: italic;
  color: var(--el-text-color-secondary);
}

.side__patient-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 8px;
}

/* Navegación */
.side__nav {
  flex: 1;
  overflow-y: auto;
  padding: 4px 12px 12px;
}

.side__section {
  margin: 14px 8px 6px;
  font-size: 10.5px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--el-text-color-secondary);
}

.side__section:first-child {
  margin-top: 6px;
}

.side__link {
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 12px;
  border-radius: 9px;
  font-size: 13.5px;
  color: var(--el-text-color-primary);
  text-decoration: none;
  transition:
    background-color 0.15s ease,
    color 0.15s ease;
}

.side__link:hover {
  background-color: var(--el-fill-color-light);
}

.side__link-icon {
  font-size: 17px;
  color: var(--el-text-color-secondary);
}

.side__link.is-active {
  background-color: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
  font-weight: 600;
}

.side__link.is-active .side__link-icon {
  color: var(--el-color-primary);
}

.side__link.is-active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 18px;
  border-radius: 0 3px 3px 0;
  background-color: var(--el-color-primary);
}

/* Pie */
.side__footer {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px 16px 16px;
  border-top: 1px solid var(--el-border-color-lighter);
}

.side__user {
  display: flex;
  align-items: center;
  gap: 10px;
}

.side__avatar,
.topbar__avatar {
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  font-size: 12px;
  font-weight: 700;
  color: var(--el-color-primary);
  background-color: var(--el-color-primary-light-8);
}

.side__user-info {
  display: flex;
  flex-direction: column;
  line-height: 1.25;
  overflow: hidden;
}

.side__user-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.side__user-role {
  font-size: 11px;
  color: var(--el-text-color-secondary);
}

.side__salir {
  width: 100%;
  margin-left: 0 !important;
  border-radius: 10px;
  color: var(--el-color-danger);
  border-color: var(--el-color-danger-light-5);
}

.side__salir:hover {
  background-color: var(--el-color-danger-light-9);
  border-color: var(--el-color-danger-light-3);
  color: var(--el-color-danger);
}

/* ---------- Barra superior ---------- */
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background-color: #fff;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.topbar__title {
  font-size: 15px;
  font-weight: 600;
}

.topbar__user {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  color: var(--el-text-color-primary);
  outline: none;
}

.app-layout__main {
  background-color: #f5f7fa;
}
</style>
