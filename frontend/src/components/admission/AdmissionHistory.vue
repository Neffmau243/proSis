<script setup lang="ts">
import type { Attention } from '@/services/atenciones'

defineProps<{
  entries: Attention[]
  loading: boolean
  error?: string | null
}>()

const emit = defineEmits<{
  refresh: []
}>()

function formatDate(value: string | null): string {
  if (!value) return '—'
  const parsed = new Date(value)
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleDateString('es-PE')
}
</script>

<template>
  <el-card class="admission-history" shadow="never">
    <header class="admission-history__header">
      <div>
        <h3 class="admission-history__title">Historial de atenciones del paciente</h3>
        <p class="admission-history__description">
          Atenciones registradas previamente para este paciente.
        </p>
      </div>
      <el-button size="small" :loading="loading" @click="emit('refresh')">Refrescar</el-button>
    </header>

    <el-alert v-if="error" :title="error" type="error" :closable="false" />
    <div v-else class="admission-history__table-wrap">
      <el-table
        :data="entries"
        :height="124"
        table-layout="fixed"
        v-loading="loading"
        size="small"
        class="admission-history__table"
        empty-text="Sin atenciones registradas"
      >
        <el-table-column label="N.° historia" width="108">
          <template #default="{ row }">{{ row.historia_clinica_snapshot || '—' }}</template>
        </el-table-column>
        <el-table-column label="Fecha atención" width="82">
          <template #default="{ row }">{{ formatDate(row.fecha_atencion) }}</template>
        </el-table-column>
        <el-table-column label="Edad del paciente" width="118">
          <template #default="{ row }">
            {{ row.edad_detallada ?? (row.edad_anios !== null ? `${row.edad_anios} años` : '—') }}
          </template>
        </el-table-column>
        <el-table-column label="Peso" width="46" align="center">
          <template #default="{ row }">{{ row.peso_kg ?? '—' }}</template>
        </el-table-column>
        <el-table-column label="Talla" width="46" align="center">
          <template #default="{ row }">{{ row.talla_cm ?? '—' }}</template>
        </el-table-column>
        <el-table-column label="Diast." width="50" align="center">
          <template #default="{ row }">{{ row.presion_diastolica ?? '—' }}</template>
        </el-table-column>
        <el-table-column label="Sist." width="47" align="center">
          <template #default="{ row }">{{ row.presion_sistolica ?? '—' }}</template>
        </el-table-column>
        <el-table-column label="IMC" width="50" align="center">
          <template #default="{ row }">{{ row.imc ?? '—' }}</template>
        </el-table-column>
        <el-table-column label="P/E" width="42" align="center">
          <template #default="{ row }">{{ row.pe || '—' }}</template>
        </el-table-column>
        <el-table-column label="T/E" width="42" align="center">
          <template #default="{ row }">{{ row.te || '—' }}</template>
        </el-table-column>
        <el-table-column label="P/T" width="42" align="center">
          <template #default="{ row }">{{ row.pt || '—' }}</template>
        </el-table-column>
        <el-table-column label="Consultorio" min-width="124">
          <template #default="{ row }">{{ row.consultorio_nombre || '—' }}</template>
        </el-table-column>
        <el-table-column label="Estado" width="82" align="center">
          <template #default="{ row }">
            <el-tag :type="row.estado === 'ANULADO' ? 'danger' : 'success'" size="small">
              {{ row.estado }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </el-card>
</template>

<style scoped>
.admission-history {
  min-width: 0;
  border-color: var(--el-border-color-lighter);
  border-radius: 12px;
}

.admission-history :deep(.el-card__body) {
  padding: 10px 12px;
}

.admission-history__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}

.admission-history__title {
  margin: 0;
  color: var(--el-text-color-primary);
  font-size: 14px;
  font-weight: 700;
  line-height: 1.35;
}

.admission-history__description {
  margin: 2px 0 0;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  line-height: 1.4;
}

.admission-history__table-wrap {
  overflow: hidden;
}

.admission-history__table {
  width: 100%;
  min-width: 0;
}

.admission-history__table :deep(.el-table__header-wrapper th.el-table__cell) {
  color: var(--el-color-primary-dark-2);
  background-color: var(--el-color-primary-light-9);
  font-size: 11px;
  font-weight: 700;
  line-height: 1.2;
}

.admission-history__table :deep(.el-table__cell) {
  padding: 4px 0;
  font-size: 12px;
}

.admission-history__table :deep(.el-table__cell .cell) {
  line-height: 1.25;
  overflow-wrap: anywhere;
  white-space: normal;
}

@media (max-width: 680px) {
  .admission-history :deep(.el-card__body) {
    padding: 12px;
  }

  .admission-history__header {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
