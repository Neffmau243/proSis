<template>
  <el-container class="app-layout">
    <el-aside width="240px" class="app-layout__aside">
      <div class="app-layout__brand">IPRESS · Salud</div>
      <el-menu :default-active="activeMenu" router class="app-layout__menu">
        <!-- Sección ADMIN: lo administrativo primero, pacientes debajo -->
        <template
          v-if="
            can('USUARIO_GESTIONAR') ||
            can('AUDITORIA_LEER') ||
            can('GRUPO_ETARIO_CONFIGURAR') ||
            can('PROFESIONAL_GESTIONAR') ||
            can('CONSULTORIO_GESTIONAR')
          "
        >
          <el-menu-item-group title="Administración">
            <el-menu-item index="/configuracion/usuarios" v-if="can('USUARIO_GESTIONAR')">
              <el-icon><User /></el-icon>
              <span>Usuarios</span>
            </el-menu-item>
            <el-menu-item index="/configuracion/auditoria" v-if="can('AUDITORIA_LEER')">
              <el-icon><DataLine /></el-icon>
              <span>Auditoría</span>
            </el-menu-item>
          </el-menu-item-group>
          <el-menu-item-group title="Configuración">
            <el-menu-item
              index="/configuracion/grupos-etarios"
              v-if="can('GRUPO_ETARIO_CONFIGURAR')"
            >
              <el-icon><Odometer /></el-icon>
              <span>Grupos etarios</span>
            </el-menu-item>
            <el-menu-item index="/configuracion/profesionales" v-if="can('PROFESIONAL_GESTIONAR')">
              <el-icon><UserFilled /></el-icon>
              <span>Profesionales</span>
            </el-menu-item>
            <el-menu-item index="/configuracion/consultorios" v-if="can('CONSULTORIO_GESTIONAR')">
              <el-icon><OfficeBuilding /></el-icon>
              <span>Consultorios</span>
            </el-menu-item>
          </el-menu-item-group>
        </template>

        <!-- Pacientes: compartido por ambos roles -->
        <el-menu-item-group title="Pacientes">
          <el-menu-item index="/pacientes" v-if="can('PACIENTE_LEER')">
            <el-icon><User /></el-icon>
            <span>Pacientes</span>
          </el-menu-item>
          <el-menu-item index="/pacientes/nuevo" v-if="can('PACIENTE_EDITAR')">
            <el-icon><Plus /></el-icon>
            <span>Nuevo paciente</span>
          </el-menu-item>
        </el-menu-item-group>

        <!-- Sección clínica: solo PROFESIONAL -->
        <el-menu-item-group
          v-if="can('ATENCION_LEER') || can('ATENCION_CREAR')"
          title="Atenciones"
        >
          <el-menu-item index="/atenciones" v-if="can('ATENCION_LEER')">
            <el-icon><Document /></el-icon>
            <span>Historial de atenciones</span>
          </el-menu-item>
          <el-menu-item index="/atenciones/nueva" v-if="can('ATENCION_CREAR')">
            <el-icon><FirstAidKit /></el-icon>
            <span>Nueva atención</span>
          </el-menu-item>
        </el-menu-item-group>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="app-layout__header">
        <div class="app-layout__title">{{ currentTitle }}</div>
        <el-dropdown @command="handleCommand">
          <span class="app-layout__user">
            {{ auth.nombreUsuario || 'Usuario' }}
            <el-icon><ArrowDown /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="password">Cambiar contraseña</el-dropdown-item>
              <el-dropdown-item command="logout" divided>Salir</el-dropdown-item>
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

import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

// Resalta la sección del menú aunque estemos en una ruta hija
// (/pacientes/12, /configuracion/consultorios/5, ...).
const activeMenu = computed(() => {
  const path = route.path
  if (path.startsWith('/pacientes')) return '/pacientes'
  if (path.startsWith('/atenciones')) return '/atenciones'
  return path
})

const currentTitle = computed(() => route.meta.title ?? '')

function can(permission: string): boolean {
  return auth.hasPermission(permission)
}

function handleCommand(command: string): void {
  if (command === 'logout') {
    auth.logout()
    router.push({ name: 'login' })
  } else if (command === 'password') {
    router.push({ name: 'cambiar-contrasena' })
  }
}
</script>

<style scoped>
.app-layout {
  height: 100%;
}

.app-layout__aside {
  display: flex;
  flex-direction: column;
  background-color: #fff;
  border-right: 1px solid var(--el-border-color-light);
  overflow-y: auto;
}

.app-layout__brand {
  padding: 18px 20px;
  font-weight: 700;
  color: var(--el-color-primary);
  letter-spacing: 0.02em;
}

.app-layout__menu {
  flex: 1;
  border-right: none;
}

.app-layout__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background-color: #fff;
  border-bottom: 1px solid var(--el-border-color-light);
}

.app-layout__title {
  font-weight: 600;
}

.app-layout__user {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  color: var(--el-text-color-primary);
  outline: none;
}

.app-layout__main {
  background-color: #f5f7fa;
}
</style>