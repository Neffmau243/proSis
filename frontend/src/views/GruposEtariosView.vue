<template>
  <div>
    <div class="page-header">
      <h2>Grupos etarios</h2>
      <el-button @click="router.back()">Volver</el-button>
    </div>

    <el-alert
      v-if="errorMessage"
      :title="errorMessage"
      type="error"
      :closable="false"
      class="form-alert"
    />

    <el-card v-loading="loading">
      <el-alert
        type="info"
        :closable="false"
        title="El PUT reemplaza la configuración completa. Los rangos no pueden superponerse y la cobertura continua es opcional."
        class="form-alert"
      />

      <el-table :data="rows" empty-text="Sin grupos configurados">
        <el-table-column prop="codigo" label="Código" width="140" />
        <el-table-column prop="nombre" label="Nombre" min-width="150" />
        <el-table-column label="Edad mínima" width="240">
          <template #default="{ row }">
            <div class="boundary">
              <el-input-number v-model="row.min_anios" :min="0" :controls="false" size="small" style="width: 90px" />
              <span>años</span>
              <el-input-number v-model="row.min_meses" :min="0" :max="11" :controls="false" size="small" style="width: 80px" />
              <span>meses</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="Edad máxima" width="280">
          <template #default="{ row }">
            <div class="boundary">
              <el-checkbox v-model="row.open_ended" size="small">Sin máximo</el-checkbox>
              <template v-if="!row.open_ended">
                <el-input-number v-model="row.max_anios" :min="0" :controls="false" size="small" style="width: 90px" />
                <span>años</span>
                <el-input-number v-model="row.max_meses" :min="0" :max="11" :controls="false" size="small" style="width: 80px" />
                <span>meses</span>
              </template>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="Activo" width="90">
          <template #default="{ row }">
            <el-switch v-model="row.activo" />
          </template>
        </el-table-column>
      </el-table>

      <div class="continuity">
        <el-switch v-model="exigirCoberturaContinua" />
        <span class="continuity-label">Exigir cobertura continua (sin huecos entre rangos activos)</span>
      </div>

      <div class="form-actions">
        <el-button type="primary" :loading="saving" @click="save">Guardar configuración</el-button>
        <el-button @click="load">Recargar</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import { configuracion, type AgeGroupResponse } from '@/services/configuracion'

const router = useRouter()

interface EditableGroup {
  codigo: string
  nombre: string
  min_anios: number
  min_meses: number
  max_anios: number
  max_meses: number
  open_ended: boolean
  activo: boolean
}

const rows = ref<EditableGroup[]>([])
const exigirCoberturaContinua = ref(false)
const loading = ref(false)
const saving = ref(false)
const errorMessage = ref<string | null>(null)

function monthsToBoundary(months: number | null): { anios: number; meses: number } {
  if (months === null) return { anios: 0, meses: 0 }
  return { anios: Math.floor(months / 12), meses: months % 12 }
}

function toEditable(group: AgeGroupResponse): EditableGroup {
  const min = monthsToBoundary(group.edad_minima_meses)
  const max = monthsToBoundary(group.edad_maxima_meses)
  return {
    codigo: group.codigo,
    nombre: group.nombre,
    min_anios: min.anios,
    min_meses: min.meses,
    max_anios: max.anios,
    max_meses: max.meses,
    open_ended: group.edad_maxima_meses === null,
    activo: group.activo,
  }
}

async function load(): Promise<void> {
  loading.value = true
  errorMessage.value = null
  try {
    const groups = await configuracion.gruposEtarios()
    rows.value = groups.map(toEditable)
  } catch (error) {
    errorMessage.value =
      error instanceof Error ? error.message : 'No se pudo cargar la configuración.'
  } finally {
    loading.value = false
  }
}

async function save(): Promise<void> {
  saving.value = true
  errorMessage.value = null
  try {
    await configuracion.guardarGruposEtarios({
      grupos: rows.value.map((row) => ({
        codigo: row.codigo,
        edad_minima_meses: row.min_anios * 12 + row.min_meses,
        edad_maxima_meses: row.open_ended ? null : row.max_anios * 12 + row.max_meses,
        activo: row.activo,
      })),
      exigir_cobertura_continua: exigirCoberturaContinua.value,
    })
    ElMessage.success('Configuración de grupos etarios guardada.')
    load()
  } catch (error) {
    errorMessage.value =
      error instanceof Error ? error.message : 'No se pudo guardar la configuración.'
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.page-header h2 {
  margin: 0;
}

.form-alert {
  margin-bottom: 16px;
}

.boundary {
  display: flex;
  align-items: center;
  gap: 6px;
}

.continuity {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 16px;
}

.continuity-label {
  color: var(--el-text-color-regular);
  font-size: 13px;
}

.form-actions {
  margin-top: 16px;
  display: flex;
  gap: 8px;
}
</style>