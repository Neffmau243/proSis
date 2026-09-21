<script setup lang="ts">
import { useId } from 'vue'
import type { PatientSisContractKey, PatientSisData } from '@/utils/patientSis'

defineProps<{
  value: Partial<PatientSisData>
  disabled?: boolean
  errors?: Partial<Record<PatientSisContractKey, string>>
}>()
const emit = defineEmits<{
  update: [value: Partial<Pick<PatientSisData, PatientSisContractKey>>]
}>()
const id = useId()
const fields = [
  { key: 'sis_diresa', label: 'DIRESA', aria: 'SIS · DIRESA / DISA', max: 3, hint: '3 caracteres' },
  { key: 'sis_tipo', label: 'Tipo', aria: 'SIS · Tipo / formato', max: 2, hint: '1–2 caracteres' },
  {
    key: 'sis_numero',
    label: 'Número',
    aria: 'SIS · Número de afiliación',
    max: 9,
    hint: '8–9 dígitos',
  },
] as const
</script>

<template>
  <fieldset class="sis-code" :disabled="disabled">
    <legend class="sis-code__legend">Código del asegurado SIS</legend>
    <div class="sis-code__segments">
      <div v-for="field in fields" :key="field.key" class="sis-code__field">
        <label :for="`${id}-${field.key}`" class="sis-code__label">{{ field.label }}</label>
        <el-input
          :id="`${id}-${field.key}`"
          :model-value="value[field.key]"
          :disabled="disabled"
          :maxlength="field.max"
          :aria-label="field.aria"
          :aria-invalid="Boolean(errors?.[field.key])"
          :aria-describedby="`${id}-${field.key}-help${errors?.[field.key] ? ` ${id}-errors` : ''}`"
          :inputmode="field.key === 'sis_numero' ? 'numeric' : 'text'"
          autocomplete="off"
          @update:model-value="emit('update', { [field.key]: $event.toUpperCase() || null })"
        />
        <p :id="`${id}-${field.key}-help`" class="sis-code__hint">{{ field.hint }}</p>
      </div>
    </div>
    <ul
      v-if="fields.some((field) => errors?.[field.key])"
      :id="`${id}-errors`"
      class="sis-code__errors"
      role="alert"
    >
      <template v-for="field in fields" :key="field.key">
        <li v-if="errors?.[field.key]">{{ field.label }}: {{ errors[field.key] }}</li>
      </template>
    </ul>
  </fieldset>
</template>

<style scoped>
.sis-code {
  min-width: 0;
  margin: 8px 0 0;
  padding: 0;
  border: 0;
  color: var(--el-text-color-regular);
  font-size: 12px;
  line-height: 1.5;
}
.sis-code__legend {
  padding: 0;
  margin-bottom: 4px;
  font-weight: 600;
}
.sis-code__segments {
  display: grid;
  grid-template-columns: minmax(0, 0.8fr) minmax(0, 0.7fr) minmax(0, 1.6fr);
  gap: 6px;
}
.sis-code__field {
  min-width: 0;
}
.sis-code__label {
  display: block;
  margin-bottom: 4px;
}
.sis-code__field :deep(.el-input__inner) {
  font-variant-numeric: tabular-nums;
}
.sis-code__hint {
  margin: 4px 0 0;
  font-size: 12px;
  line-height: 1.5;
  overflow-wrap: anywhere;
}
.sis-code__errors {
  padding: 0;
  margin: 4px 0;
  list-style: none;
  color: #b42318;
}
</style>
