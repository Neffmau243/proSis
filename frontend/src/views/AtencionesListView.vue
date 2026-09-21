<template>
  <div>
    <div class="page-header">
      <h2>Historial de atenciones</h2>
      <el-button
        v-if="can('ATENCION_CREAR')"
        type="primary"
        @click="router.push({ name: 'atencion-nueva' })"
      >
        <el-icon><Plus /></el-icon>
        <span class="btn-label">Nueva atención</span>
      </el-button>
    </div>

    <el-card class="filters">
      <el-form inline @submit.prevent="search(1)">
        <el-form-item label="Paciente ID">
          <el-input-number
            v-model="filters.paciente_id"
            :min="1"
            :controls="false"
            placeholder="ID del paciente"
            style="width: 130px"
          />
        </el-form-item>
        <el-form-item label="Establecimiento">
          <el-select
            v-model="filters.establecimiento_id"
            clearable
            filterable
            remote
            :remote-method="searchEstablecimientos"
            :loading="establecimientosLoading"
            placeholder="Busque"
            style="width: 220px"
          >
            <el-option
              v-for="est in establecimientos"
              :key="est.id"
              :label="est.nombre"
              :value="est.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="Desde">
          <el-date-picker
            v-model="filters.desde"
            type="date"
            value-format="YYYY-MM-DD"
            style="width: 150px"
          />
        </el-form-item>
        <el-form-item label="Hasta">
          <el-date-picker
            v-model="filters.hasta"
            type="date"
            value-format="YYYY-MM-DD"
            style="width: 150px"
          />
        </el-form-item>
        <el-form-item label="Estado">
          <el-select v-model="filters.estado" clearable placeholder="Todos" style="width: 140px">
            <el-option label="ATENDIDO" value="ATENDIDO" />
            <el-option label="ANULADO" value="ANULADO" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" native-type="submit">Buscar</el-button>
          <el-button @click="clearFilters">Limpiar</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card>
      <el-table :data="rows" v-loading="loading" empty-text="Sin atenciones">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="fecha_atencion" label="Fecha" width="170" />
        <el-table-column prop="paciente_id" label="Paciente" width="100" />
        <el-table-column prop="modalidad_atencion_codigo" label="Modalidad" width="130" />
        <el-table-column prop="grupo_etario_codigo" label="Grupo etario" width="130" />
        <el-table-column label="Grupo de atención" min-width="170">
          <template #default="{ row }">{{ careGroupLabel(row.grupo_atencion_codigo) }}</template>
        </el-table-column>
        <el-table-column label="Edad" width="70">
          <template #default="{ row }">{{ row.edad_anios ?? '—' }}</template>
        </el-table-column>
        <el-table-column label="Estado" width="110">
          <template #default="{ row }">
            <el-tag :type="row.estado === 'ANULADO' ? 'danger' : 'success'">
              {{ row.estado }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="Acciones" width="110" fixed="right">
          <template #default="{ row }">
            <el-button
              link
              type="primary"
              @click="router.push({ name: 'atencion-detalle', params: { id: row.id } })"
            >
              Ver
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

import { usePagination } from '@/composables/usePagination'
import { useAuthStore } from '@/stores/auth'
import { catalogos, type EstablishmentCatalogItem } from '@/services/catalogos'
import { atenciones, type Attention } from '@/services/atenciones'
import { careGroupLabel } from '@/utils/careGroup'

const router = useRouter()
const auth = useAuthStore()
const { limit, total, currentPage, applyPage, goToPage, changeLimit } = usePagination()

const rows = ref<Attention[]>([])
const loading = ref(false)
const establecimientos = ref<EstablishmentCatalogItem[]>([])
const establecimientosLoading = ref(false)

const filters = reactive<{
  paciente_id?: number
  establecimiento_id?: number
  desde?: string
  hasta?: string
  estado?: 'ATENDIDO' | 'ANULADO'
}>({
  paciente_id: undefined,
  establecimiento_id: undefined,
  desde: undefined,
  hasta: undefined,
  estado: undefined,
})

function can(permission: string): boolean {
  return auth.hasPermission(permission)
}

async function searchEstablecimientos(query: string): Promise<void> {
  establecimientosLoading.value = true
  try {
    const page = await catalogos.establecimientos(query || undefined, 25, 0)
    establecimientos.value = page.items
  } finally {
    establecimientosLoading.value = false
  }
}

async function search(page: number): Promise<void> {
  goToPage(page)
  loading.value = true
  try {
    const result = await atenciones.search({
      paciente_id: filters.paciente_id,
      establecimiento_id: filters.establecimiento_id,
      desde: filters.desde,
      hasta: filters.hasta,
      estado: filters.estado,
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
  filters.paciente_id = undefined
  filters.establecimiento_id = undefined
  filters.desde = undefined
  filters.hasta = undefined
  filters.estado = undefined
  search(1)
}

onMounted(() => search(1))
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

.pagination {
  margin-top: 16px;
  justify-content: flex-end;
}

.btn-label {
  margin-left: 6px;
}
</style>