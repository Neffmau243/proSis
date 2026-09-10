<template>
  <div>
    <div class="page-header">
      <h2>Pacientes</h2>
      <el-button
        v-if="can('PACIENTE_EDITAR')"
        type="primary"
        @click="router.push({ name: 'paciente-nuevo' })"
      >
        <el-icon><Plus /></el-icon>
        <span class="btn-label">Nuevo paciente</span>
      </el-button>
    </div>

    <el-card class="filters">
      <el-form inline @submit.prevent="search(1)">
        <el-form-item label="Tipo doc.">
          <el-select
            v-model="filters.tipo_documento_codigo"
            clearable
            placeholder="Todos"
            style="width: 150px"
          >
            <el-option
              v-for="tipo in tiposDocumento"
              :key="tipo.codigo"
              :label="tipo.nombre"
              :value="tipo.codigo"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="N° documento">
          <el-input v-model="filters.numero_documento" clearable style="width: 150px" />
        </el-form-item>
        <el-form-item label="Historia clínica">
          <el-input v-model="filters.historia_clinica" clearable style="width: 160px" />
        </el-form-item>
        <el-form-item label="Buscar">
          <el-input
            v-model="filters.q"
            clearable
            placeholder="Nombre (mín. 2 letras)"
            style="width: 220px"
            @keyup.enter="search(1)"
          />
        </el-form-item>
        <el-form-item v-if="can('PACIENTE_DAR_BAJA')">
          <el-checkbox v-model="filters.incluir_inactivos">Incluir inactivos</el-checkbox>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" native-type="submit">Buscar</el-button>
          <el-button @click="clearFilters">Limpiar</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card>
      <el-table :data="rows" v-loading="loading" empty-text="Sin resultados">
        <el-table-column label="Paciente" min-width="240">
          <template #default="{ row }">
            <strong>{{ fullName(row) }}</strong>
            <div class="muted">
              {{ row.tipo_documento_codigo }} {{ row.numero_documento }}
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="historia_clinica" label="Historia clínica" width="160" />
        <el-table-column label="Sexo" width="80">
          <template #default="{ row }">
            {{ sexLabel(row.sexo_codigo) }}
          </template>
        </el-table-column>
        <el-table-column label="Nacimiento" width="120">
          <template #default="{ row }">{{ row.fecha_nacimiento }}</template>
        </el-table-column>
        <el-table-column label="Estado" width="100">
          <template #default="{ row }">
            <el-tag :type="row.estado ? 'success' : 'info'">
              {{ row.estado ? 'Activo' : 'Inactivo' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="Acciones" width="240" fixed="right">
          <template #default="{ row }">
            <el-button
              link
              type="primary"
              @click="router.push({ name: 'paciente-detalle', params: { id: row.id } })"
            >
              Ver
            </el-button>
            <el-button
              v-if="can('PACIENTE_EDITAR')"
              link
              type="primary"
              @click="router.push({ name: 'paciente-editar', params: { id: row.id } })"
            >
              Editar
            </el-button>
            <el-button
              v-if="can('PACIENTE_DAR_BAJA') && row.estado"
              link
              type="danger"
              @click="confirmDeactivate(row)"
            >
              Dar de baja
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        class="pagination"
        layout="total, prev, pager, next, sizes"
        :total="total"
        :page-size="limit"
        :current-page="currentPage"
        :page-sizes="[10, 25, 50, 100]"
        @current-change="(page: number) => search(page)"
        @size-change="(size: number) => { changeLimit(size); search(1) }"
      />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

import { usePagination } from '@/composables/usePagination'
import { useAuthStore } from '@/stores/auth'
import { catalogos, type CodeCatalogItem } from '@/services/catalogos'
import { pacientes, type Patient } from '@/services/pacientes'

const router = useRouter()
const auth = useAuthStore()
const { limit, total, currentPage, applyPage, goToPage, changeLimit } = usePagination()

const tiposDocumento = ref<CodeCatalogItem[]>([])
const sexos = ref<CodeCatalogItem[]>([])
const rows = ref<Patient[]>([])
const loading = ref(false)

const filters = reactive<{
  tipo_documento_codigo?: string
  numero_documento?: string
  historia_clinica?: string
  q?: string
  incluir_inactivos: boolean
}>({
  tipo_documento_codigo: undefined,
  numero_documento: undefined,
  historia_clinica: undefined,
  q: undefined,
  incluir_inactivos: false,
})

function can(permission: string): boolean {
  return auth.hasPermission(permission)
}

function fullName(patient: Patient): string {
  return [patient.apellido_paterno, patient.apellido_materno, patient.primer_nombre, patient.otros_nombres]
    .filter(Boolean)
    .join(' ')
}

function sexLabel(codigo: string | null): string {
  const found = sexos.value.find((sexo) => sexo.codigo === codigo)
  return found?.nombre ?? (codigo ?? '—')
}

async function search(page: number): Promise<void> {
  goToPage(page)
  loading.value = true
  try {
    const result = await pacientes.search({
      tipo_documento_codigo: filters.tipo_documento_codigo || undefined,
      numero_documento: filters.numero_documento || undefined,
      historia_clinica: filters.historia_clinica || undefined,
      // El backend exige mínimo 2 caracteres para q; solo se envía si cumple.
      q: filters.q && filters.q.trim().length >= 2 ? filters.q.trim() : undefined,
      incluir_inactivos: filters.incluir_inactivos,
      limit: limit.value,
      offset: (page - 1) * limit.value,
    })
    rows.value = result.items
    applyPage(result)
  } finally {
    loading.value = false
  }
}

function clearFilters(): void {
  filters.tipo_documento_codigo = undefined
  filters.numero_documento = undefined
  filters.historia_clinica = undefined
  filters.q = undefined
  filters.incluir_inactivos = false
  search(1)
}

async function confirmDeactivate(patient: Patient): Promise<void> {
  try {
    await ElMessageBox.confirm(
      `¿Dar de baja a ${fullName(patient)}? La baja es lógica: el historial se conserva.`,
      'Dar de baja paciente',
      { type: 'warning', confirmButtonText: 'Dar de baja', cancelButtonText: 'Cancelar' },
    )
  } catch {
    return
  }
  try {
    const result = await pacientes.deactivate(patient.id)
    ElMessage.success(result.mensaje)
    search(1)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : 'No se pudo dar de baja.')
  }
}

onMounted(async () => {
  const [tipos, sexosResult] = await Promise.all([
    catalogos.tiposDocumento(),
    catalogos.sexos(),
  ])
  tiposDocumento.value = tipos
  sexos.value = sexosResult
  search(1)
})
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

.filters {
  margin-bottom: 16px;
}

.muted {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.pagination {
  margin-top: 16px;
  justify-content: flex-end;
}

.btn-label {
  margin-left: 6px;
}
</style>