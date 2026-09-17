<template>
  <el-dialog
    :model-value="modelValue"
    :title="riesgo ? 'Editar periodo de riesgo' : 'Agregar periodo de riesgo'"
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
      <el-form-item label="Grupo de riesgo" prop="grupo_riesgo_id">
        <el-select
          v-model="form.grupo_riesgo_id"
          style="width: 100%"
          :disabled="riesgo !== null"
          placeholder="Seleccione"
        >
          <el-option
            v-for="grupo in gruposRiesgo"
            :key="grupo.id"
            :label="grupo.nombre"
            :value="grupo.id"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="Fecha de inicio" prop="fecha_inicio">
        <el-date-picker
          v-model="form.fecha_inicio"
          type="date"
          value-format="YYYY-MM-DD"
          style="width: 100%"
          :disabled="riesgo !== null"
        />
      </el-form-item>
      <el-form-item label="Fecha de fin">
        <el-date-picker
          v-model="form.fecha_fin"
          type="date"
          value-format="YYYY-MM-DD"
          style="width: 100%"
          clearable
          placeholder="Sin fecha de fin (vigente)"
        />
      </el-form-item>
      <el-form-item label="Observación">
        <el-input
          v-model="form.observacion"
          type="textarea"
          :rows="2"
          maxlength="500"
          show-word-limit
        />
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
  type PatientRisk,
  type RiskCreatePayload,
  type RiskUpdatePayload,
} from '@/services/pacientes'
import type { RiskGroupCatalogItem } from '@/services/catalogos'

const props = defineProps<{
  modelValue: boolean
  patientId: number
  /** Cuando se pasa, el diálogo edita; si no, crea. */
  riesgo: PatientRisk | null
  gruposRiesgo: RiskGroupCatalogItem[]
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  saved: [riesgo: PatientRisk]
}>()

const formRef = ref<FormInstance>()
const saving = ref(false)
const errorMessage = ref<string | null>(null)

const form = reactive({
  grupo_riesgo_id: null as number | null,
  fecha_inicio: '',
  fecha_fin: null as string | null,
  observacion: '',
})

const rules: FormRules = {
  grupo_riesgo_id: [
    { required: true, message: 'Seleccione el grupo de riesgo.', trigger: 'change' },
  ],
  fecha_inicio: [{ required: true, message: 'Indique la fecha de inicio.', trigger: 'change' }],
}

function init(): void {
  errorMessage.value = null
  const source = props.riesgo
  form.grupo_riesgo_id = source?.grupo_riesgo_id ?? null
  form.fecha_inicio = source?.fecha_inicio ?? ''
  form.fecha_fin = source?.fecha_fin ?? null
  form.observacion = source?.observacion ?? ''
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
    const saved = props.riesgo
      ? await pacientes.updateRisk(
          props.patientId,
          props.riesgo.grupo_riesgo_id,
          props.riesgo.fecha_inicio,
          {
            fecha_fin: form.fecha_fin,
            observacion: form.observacion || null,
          } satisfies RiskUpdatePayload,
        )
      : await pacientes.addRisk(props.patientId, {
          grupo_riesgo_id: form.grupo_riesgo_id!,
          fecha_inicio: form.fecha_inicio,
          fecha_fin: form.fecha_fin,
          observacion: form.observacion || null,
        } satisfies RiskCreatePayload)

    emit('saved', saved)
    emit('update:modelValue', false)
  } catch (error) {
    errorMessage.value =
      error instanceof Error ? error.message : 'No se pudo guardar el periodo de riesgo.'
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
