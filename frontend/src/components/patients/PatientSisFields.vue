<script setup lang="ts">
import { onMounted, shallowRef } from 'vue'
import { catalogos, type CodeCatalogItem } from '@/services/catalogos'
import { patientSisFields, type PatientSisData } from '@/utils/patientSis'

defineProps<{
  value: Partial<PatientSisData>
  disabled?: boolean
  errors?: Partial<Record<keyof PatientSisData, string>>
}>()
const emit = defineEmits<{ update: [value: Partial<PatientSisData>] }>()
const etnias = shallowRef<CodeCatalogItem[]>([])
const loading = shallowRef(false)
const error = shallowRef(false)
async function load(): Promise<void> {
  loading.value = true
  error.value = false
  try { etnias.value = await catalogos.etnias() }
  catch { error.value = true }
  finally { loading.value = false }
}
onMounted(load)
</script>

<template>
  <div class="patient-sis-fields">
    <h4>Afiliación SIS y etnia</h4>
    <p>Se guardan en la ficha del paciente y se reutilizan en sus atenciones. Copie la afiliación de la acreditación SIS; no se deduce del DNI.</p>
    <el-form-item v-for="field in patientSisFields" :key="field.key" :label="field.label" :error="errors?.[field.key]">
      <el-select v-if="field.key === 'etnia_codigo'" :model-value="value.etnia_codigo" clearable filterable
        :disabled="disabled" :loading="loading" placeholder="Sin declarar" aria-label="Etnia declarada"
        @update:model-value="emit('update', { etnia_codigo: $event || null })">
        <el-option v-if="value.etnia_codigo && !etnias.some(e => e.codigo === value.etnia_codigo)"
          :value="value.etnia_codigo" :label="`Código ${value.etnia_codigo}`" />
        <el-option v-for="item in etnias" :key="item.codigo" :value="item.codigo" :label="`${item.codigo} · ${item.nombre}`" />
      </el-select>
      <el-input v-else :model-value="value[field.key]" :maxlength="field.max" :disabled="disabled"
        :aria-label="field.label" :inputmode="['sis_numero', 'sis_secuencia'].includes(field.key) ? 'numeric' : 'text'"
        @update:model-value="emit('update', { [field.key]: $event.toUpperCase() || null })" />
    </el-form-item>
    <p>DIRESA: 3 caracteres · tipo/formato: 1–2 · número: 8–9 dígitos · secuencia/RN: hasta 2, si corresponde. La secuencia no es el régimen del seguro. La etnia es declarada, nunca inferida.</p>
    <p v-if="error" role="alert">No se cargó el catálogo de etnias. <el-button link type="primary" @click="load">Reintentar</el-button></p>
  </div>
</template>

<style scoped>
.patient-sis-fields { margin-top: 20px; min-width: 0; }
.patient-sis-fields h4 { margin: 0 0 8px; font-size: 14px; }
.patient-sis-fields p { margin: 8px 0 12px; color: var(--el-text-color-regular); font-size: 12px; line-height: 1.5; }
</style>
