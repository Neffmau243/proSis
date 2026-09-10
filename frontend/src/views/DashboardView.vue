<template>
  <div class="dashboard">
    <h2 class="dashboard__heading">Hola, {{ auth.nombreUsuario || 'usuario' }}</h2>
    <p class="dashboard__hint">
      Use el menú lateral para navegar. Las opciones visibles dependen de sus
      permisos ({{ auth.roles.join(', ') || 'sin roles' }}).
    </p>

    <el-alert
      v-if="!auth.permisos.length"
      type="info"
      :closable="false"
      title="Su usuario no tiene permisos asignados. Contacte a un administrador."
    />

    <el-row :gutter="16">
      <el-col :span="8" v-if="can('PACIENTE_LEER')">
        <el-card shadow="hover" class="dashboard__card" @click="go('pacientes')">
          <h3>Pacientes</h3>
          <p>Buscar, registrar y administrar pacientes.</p>
        </el-card>
      </el-col>
      <el-col :span="8" v-if="can('ATENCION_CREAR')">
        <el-card shadow="hover" class="dashboard__card" @click="go('atencion-nueva')">
          <h3>Nueva atención</h3>
          <p>Registrar una atención clínica.</p>
        </el-card>
      </el-col>
      <el-col :span="8" v-if="can('ATENCION_LEER')">
        <el-card shadow="hover" class="dashboard__card" @click="go('atenciones')">
          <h3>Historial</h3>
          <p>Historial de atenciones con filtros y paginación.</p>
        </el-card>
      </el-col>
      <el-col :span="8" v-if="can('GRUPO_ETARIO_CONFIGURAR')">
        <el-card shadow="hover" class="dashboard__card" @click="go('grupos-etarios')">
          <h3>Grupos etarios</h3>
          <p>Configurar rangos y cobertura continua.</p>
        </el-card>
      </el-col>
      <el-col :span="8" v-if="can('PROFESIONAL_GESTIONAR')">
        <el-card shadow="hover" class="dashboard__card" @click="go('profesionales')">
          <h3>Profesionales</h3>
          <p>Gestionar profesionales y especialidades.</p>
        </el-card>
      </el-col>
      <el-col :span="8" v-if="can('CONSULTORIO_GESTIONAR')">
        <el-card shadow="hover" class="dashboard__card" @click="go('consultorios')">
          <h3>Consultorios</h3>
          <p>Gestionar consultorios y asignaciones.</p>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

function can(permission: string): boolean {
  return auth.hasPermission(permission)
}

function go(name: string): void {
  router.push({ name })
}
</script>

<style scoped>
.dashboard__heading {
  margin: 0 0 4px;
}

.dashboard__hint {
  margin: 0 0 24px;
  color: var(--el-text-color-secondary);
}

.dashboard__card {
  margin-bottom: 16px;
  cursor: pointer;
}

.dashboard__card h3 {
  margin: 0 0 8px;
}

.dashboard__card p {
  margin: 0;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}
</style>