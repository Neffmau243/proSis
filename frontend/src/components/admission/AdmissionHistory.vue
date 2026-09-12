<script setup lang="ts">
import type { Attention } from '@/services/atenciones'

defineProps<{
  entries: Attention[]
  loading: boolean
  consultorioLabel: (id: number) => string
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

    <div class="admission-history__table-wrap">
      <el-table
        :data="entries"
        v-loading="loading"
        size="small"
        class="admission-history__table"
        empty-text="Sin atenciones registradas"
      >
        <el-table-column label="HC" min-width="108">
          <template #default="{ row }">{{ row.historia_clinica_snapshot || '—' }}</template>
        </el-table-column>
        <el-table-column label="Fecha" min-width="96">
          <template #default="{ row }">{{ formatDate(row.fecha_atencion) }}</template>
        </el-table-column>
        <el-table-column label="Edad" width="56" align="center">
          <template #default="{ row }">{{ row.edad_anios ?? '—' }}</template>
        </el-table-column>
        <el-table-column label="Peso" width="62" align="center">
          <template #default="{ row }">{{ row.peso_kg ?? '—' }}</template>
        </el-table-column>
        <el-table-column label="Talla" width="62" align="center">
          <template #default="{ row }">{{ row.talla_cm ?? '—' }}</template>
        </el-table-column>
        <el-table-column label="DIA" width="56" align="center">
          <template #default="{ row }">{{ row.presion_diastolica ?? '—' }}</template>
        </el-table-column>
        <el-table-column label="SIS" width="56" align="center">
          <template #default="{ row }">{{ row.presion_sistolica ?? '—' }}</template>
        </el-table-column>
        <el-table-column label="P/E" width="54" align="center">
          <template #default="{ row }">{{ row.pe || '—' }}</template>
        </el-table-column>
        <el-table-column label="T/E" width="54" align="center">
          <template #default="{ row }">{{ row.te || '—' }}</template>
        </el-table-column>
        <el-table-column label="P/T" width="54" align="center">
          <template #default="{ row }">{{ row.pt || '—' }}</template>
        </el-table-column>
        <el-table-column label="Consultorio" min-width="150">
          <template #default="{ row }">{{ consultorioLabel(row.consultorio_id) }}</template>
        </el-table-column>
        <el-table-column label="Estado" width="104" align="center">
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
  padding: 16px;
}

.admission-history__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 12px;
}

.admission-history__title {
  margin: 0;
  color: var(--el-text-color-primary);
  font-size: 15px;
  font-weight: 700;
  line-height: 1.35;
}

.admission-history__description {
  margin: 3px 0 0;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  line-height: 1.4;
}

.admission-history__table-wrap {
  overflow-x: auto;
}

.admission-history__table {
  min-width: 900px;
}

.admission-history__table :deep(.el-table__header-wrapper th.el-table__cell) {
  color: var(--el-color-primary-dark-2);
  background-color: var(--el-color-primary-light-9);
  font-size: 11px;
  font-weight: 700;
}

.admission-history__table :deep(.el-table__cell) {
  padding: 4px 0;
  font-size: 12px;
}

.admission-history__table :deep(.el-table__cell .cell) {
  line-height: 1.35;
}

@media (max-width: 680px) {
  .admission-history :deep(.el-card__body) {
    padding: 16px;
  }

  .admission-history__header {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
