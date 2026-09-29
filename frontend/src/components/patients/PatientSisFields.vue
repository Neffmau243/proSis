<script setup lang="ts">
import { onMounted, shallowRef } from 'vue'
import { catalogos, type CodeCatalogItem } from '@/services/catalogos'
import { patientSisContractFields, type PatientSisData } from '@/utils/patientSis'

defineProps<{
  value: Partial<PatientSisData>
  disabled?: boolean
  errors?: Partial<Record<keyof PatientSisData, string>>
}>()
const emit = defineEmits<{ update: [value: Partial<PatientSisData>] }>()
const etnias = shallowRef<CodeCatalogItem[]>([])
const loading = shallowRef(false)
const error = shallowRef(false)
const shortLabels = {
  sis_diresa: 'DIRESA / DISA',
  sis_tipo: 'Tipo',
  sis_numero: 'N.° afiliación',
  sis_secuencia: 'Secuencia / RN',
}
async function load(): Promise<void> {
  loading.value = true
  error.value = false
  try {
    etnias.value = await catalogos.etnias()
  } catch {
    error.value = true
  } finally {
    loading.value = false
  }
}
onMounted(load)
</script>

<template>
  <div class="patient-sis-fields">
    <fieldset class="patient-sis-fields__code" :disabled="disabled">
      <legend class="patient-sis-fields__legend">Código del asegurado SIS</legend>
      <div class="patient-sis-fields__segments">
        <el-form-item
          v-for="field in patientSisContractFields"
          :key="field.key"
          :label="shortLabels[field.key]"
          :error="errors?.[field.key]"
        >
          <el-input
            :model-value="value[field.key]"
            :maxlength="field.max"
            :disabled="disabled"
            :aria-label="field.label"
            :inputmode="['sis_numero', 'sis_secuencia'].includes(field.key) ? 'numeric' : 'text'"
            @update:model-value="emit('update', { [field.key]: $event.toUpperCase() || null })"
          />
        </el-form-item>
      </div>
    </fieldset>

    <slot />

    <details class="patient-sis-fields__additional">
      <summary>Datos adicionales</summary>
      <div class="patient-sis-fields__additional-content">
        <slot name="additional" />
        <el-form-item label="Etnia declarada" :error="errors?.etnia_codigo">
          <el-select
            :model-value="value.etnia_codigo"
            clearable
            filterable
            :disabled="disabled"
            :loading="loading"
            placeholder="Sin declarar"
            aria-label="Etnia declarada"
            @update:model-value="emit('update', { etnia_codigo: $event || null })"
          >
            <el-option
              v-if="value.etnia_codigo && !etnias.some((e) => e.codigo === value.etnia_codigo)"
              :value="value.etnia_codigo"
              :label="`Código ${value.etnia_codigo}`"
            />
            <el-option
              v-for="item in etnias"
              :key="item.codigo"
              :value="item.codigo"
              :label="`${item.codigo} · ${item.nombre}`"
            />
          </el-select>
        </el-form-item>
        <p v-if="error" role="alert" class="patient-sis-fields__help">
          No se cargó el catálogo de etnias.
          <el-button link type="primary" @click="load">Reintentar</el-button>
        </p>
        <p class="patient-sis-fields__help">
          Copie el código de la acreditación SIS: DIRESA de 3 caracteres, tipo de 1–2, número de 8–9
          dígitos y secuencia/RN de hasta 2, si corresponde. La etnia es declarada.
        </p>
      </div>
    </details>
  </div>
</template>

<style scoped>
.patient-sis-fields {
  display: grid;
  gap: 8px;
  margin-top: 8px;
  min-width: 0;
}

.patient-sis-fields__code {
  min-width: 0;
  padding: 0;
  margin: 0 0 0 136px;
  border: 0;
}

.patient-sis-fields__legend {
  margin-bottom: 4px;
  padding: 0;
  color: var(--registration-ink, #304f6d);
  font-size: 12px;
  font-weight: 600;
}

.patient-sis-fields__segments {
  display: grid;
  align-items: end;
  grid-template-columns: minmax(0, 0.9fr) minmax(0, 0.6fr) minmax(0, 1.5fr) minmax(0, 1fr);
  gap: 6px;
}

.patient-sis-fields :deep(.el-form-item) {
  min-width: 0;
  margin-bottom: 0;
}

.patient-sis-fields :deep(.el-form-item__label) {
  height: auto;
  margin: 0 0 4px;
  padding: 0;
  font-size: 12px;
  line-height: 1.25;
  color: var(--registration-ink, #304f6d);
}

.patient-sis-fields__segments :deep(.el-form-item__label) {
  font-size: 11px;
}

.patient-sis-fields__segments :deep(.el-input__wrapper) {
  padding-inline: 6px;
}

.patient-sis-fields :deep(.el-input__inner) {
  font-size: 12px;
  font-variant-numeric: tabular-nums;
}

.patient-sis-fields :deep(.el-form-item__error) {
  position: static;
}

.patient-sis-fields__additional {
  border-top: 1px solid var(--registration-border, #b9cbdf);
  margin-top: 4px;
  padding-top: 4px;
}

.patient-sis-fields__additional summary {
  padding-block: 8px;
  color: var(--registration-ink, #304f6d);
  font-size: 12px;
  cursor: pointer;
}

.patient-sis-fields__additional summary:focus-visible {
  outline: 2px solid var(--el-color-primary);
  outline-offset: 2px;
}

.patient-sis-fields__additional-content {
  display: grid;
  gap: 12px;
  padding-top: 4px;
}

.patient-sis-fields__additional-content :deep(.el-date-editor) {
  width: 100%;
}

.patient-sis-fields__help {
  margin: 0;
  color: var(--registration-ink, #304f6d);
  font-size: 12px;
  line-height: 1.5;
}

@media (max-width: 640px) {
  .patient-sis-fields__code {
    margin-left: 0;
  }

  .patient-sis-fields__segments {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
