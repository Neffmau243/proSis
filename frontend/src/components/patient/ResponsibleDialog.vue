<template>
  <el-dialog
    :model-value="modelValue"
    :title="responsible ? 'Editar responsable' : 'Agregar responsable'"
    width="min(520px, 94vw)"
    :close-on-click-modal="!saving"
    :close-on-press-escape="!saving"
    :show-close="!saving"
    destroy-on-close
    @update:model-value="emit('update:modelValue', $event)"
    @open="init"
  >
    <el-alert
      v-if="errorMessage"
      :title="errorMessage"
      type="error"
      :closable="false"
      class="dialog-alert"
    />

    <el-form ref="formRef" :model="form" :rules="rules" label-position="top" :disabled="saving">
      <el-form-item label="Parentesco" prop="parentesco">
        <el-select v-model="form.parentesco" style="width: 100%">
          <el-option label="Madre" value="MADRE" />
          <el-option label="Padre" value="PADRE" />
          <el-option label="Tutor" value="TUTOR" />
        </el-select>
      </el-form-item>
      <el-form-item label="Nombre completo" prop="nombre_completo">
        <el-input v-model="form.nombre_completo" />
      </el-form-item>
      <el-form-item label="Tipo documento">
        <el-select v-model="form.tipo_documento_codigo" clearable style="width: 100%">
          <el-option
            v-for="tipo in tiposDocumento"
            :key="tipo.codigo"
            :label="tipo.nombre"
            :value="tipo.codigo"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="N° documento">
        <el-input v-model="form.numero_documento" :disabled="!form.tipo_documento_codigo" />
      </el-form-item>
      <el-form-item label="Teléfono">
        <el-input v-model="form.telefono" />
      </el-form-item>
      <el-form-item label="Principal">
        <el-switch v-model="form.es_principal" />
      </el-form-item>
      <el-form-item label="Activo">
        <el-switch v-model="form.activo" />
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button :disabled="saving" @click="emit('update:modelValue', false)">Cancelar</el-button>
      <el-button type="primary" :loading="saving" @click="save">Guardar</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'

import {
  pacientes,
  type PatientResponsible,
  type ResponsibleCreatePayload,
  type ResponsibleUpdatePayload,
} from '@/services/pacientes'
import type { CodeCatalogItem } from '@/services/catalogos'

const props = defineProps<{
  modelValue: boolean
  patientId: number
  /** Cuando se pasa, el diálogo edita; si no, crea. */
  responsible: PatientResponsible | null
  tiposDocumento: CodeCatalogItem[]
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  saved: [responsible: PatientResponsible]
}>()

const formRef = ref<FormInstance>()
const saving = ref(false)
const errorMessage = ref<string | null>(null)

const form = reactive<{
  parentesco: 'MADRE' | 'PADRE' | 'TUTOR'
  nombre_completo: string
  tipo_documento_codigo: string | null
  numero_documento: string | null
  telefono: string | null
  es_principal: boolean
  activo: boolean
}>({
  parentesco: 'MADRE',
  nombre_completo: '',
  tipo_documento_codigo: null,
  numero_documento: null,
  telefono: null,
  es_principal: false,
  activo: true,
})

const rules: FormRules = {
  parentesco: [{ required: true, message: 'Seleccione el parentesco.', trigger: 'change' }],
  nombre_completo: [
    { required: true, message: 'Ingrese el nombre completo.', trigger: 'blur' },
    { min: 2, message: 'Mínimo 2 caracteres.', trigger: 'blur' },
  ],
}

function init(): void {
  errorMessage.value = null
  const source = props.responsible
  form.parentesco = (source?.parentesco as 'MADRE' | 'PADRE' | 'TUTOR') ?? 'MADRE'
  form.nombre_completo = source?.nombre_completo ?? ''
  form.tipo_documento_codigo = source?.tipo_documento_codigo ?? null
  form.numero_documento = source?.numero_documento ?? null
  form.telefono = source?.telefono ?? null
  form.es_principal = source?.es_principal ?? false
  form.activo = source?.activo ?? true
}

async function save(): Promise<void> {
  if (saving.value) return
  saving.value = true
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) {
    saving.value = false
    return
  }

  errorMessage.value = null
  try {
    const payload = {
      parentesco: form.parentesco,
      nombre_completo: form.nombre_completo,
      tipo_documento_codigo: form.tipo_documento_codigo || null,
      numero_documento: form.numero_documento || null,
      telefono: form.telefono || null,
      es_principal: form.es_principal,
      activo: form.activo,
    } satisfies ResponsibleCreatePayload | ResponsibleUpdatePayload

    const saved = props.responsible
      ? await pacientes.updateResponsible(props.patientId, props.responsible.id, payload)
      : await pacientes.addResponsible(props.patientId, payload)

    emit('saved', saved)
    emit('update:modelValue', false)
  } catch (error) {
    errorMessage.value =
      error instanceof Error ? error.message : 'No se pudo guardar el responsable.'
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.dialog-alert {
  margin-bottom: 16px;
}
</style>
