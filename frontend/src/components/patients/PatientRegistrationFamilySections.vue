<script setup lang="ts">
import { Delete } from '@element-plus/icons-vue'

import type { CodeCatalogItem, RiskGroupCatalogItem } from '@/services/catalogos'

interface ResponsibleRow {
  parentesco: 'MADRE' | 'PADRE' | 'TUTOR'
  nombre_completo: string
  tipo_documento_codigo: string | null
  numero_documento: string | null
  telefono: string | null
  es_principal: boolean
}

interface RiskRow {
  grupo_riesgo_id: number | null
  fecha_inicio: string
  fecha_fin: string | null
  observacion: string
}

defineProps<{
  tiposDocumento: CodeCatalogItem[]
  gruposRiesgo: RiskGroupCatalogItem[]
}>()

const responsables = defineModel<ResponsibleRow[]>('responsables', { required: true })
const riesgos = defineModel<RiskRow[]>('riesgos', { required: true })

function addResponsible(): void {
  responsables.value = [
    ...responsables.value,
    {
      parentesco: 'MADRE',
      nombre_completo: '',
      tipo_documento_codigo: null,
      numero_documento: null,
      telefono: null,
      es_principal: false,
    },
  ]
}

function updateResponsible(index: number, changes: Partial<ResponsibleRow>): void {
  responsables.value = responsables.value.map((responsable, rowIndex) =>
    rowIndex === index ? { ...responsable, ...changes } : responsable,
  )
}

function removeResponsible(index: number): void {
  responsables.value = responsables.value.filter((_, rowIndex) => rowIndex !== index)
}

function addRisk(): void {
  riesgos.value = [
    ...riesgos.value,
    {
      grupo_riesgo_id: null,
      fecha_inicio: '',
      fecha_fin: null,
      observacion: '',
    },
  ]
}

function updateRisk(index: number, changes: Partial<RiskRow>): void {
  riesgos.value = riesgos.value.map((risk, rowIndex) =>
    rowIndex === index ? { ...risk, ...changes } : risk,
  )
}

function removeRisk(index: number): void {
  riesgos.value = riesgos.value.filter((_, rowIndex) => rowIndex !== index)
}
</script>

<template>
  <aside class="family-sections" aria-label="Datos familiares y grupos de riesgo">
    <section class="family-sections__section">
      <header class="family-sections__header">
        <div>
          <h3 class="family-sections__title">Datos familiares</h3>
          <p class="family-sections__hint">Registre responsables cuando corresponda.</p>
        </div>
        <el-button size="small" @click="addResponsible">Agregar</el-button>
      </header>

      <p v-if="!responsables.length" class="family-sections__empty">
        Sin responsables registrados.
      </p>

      <div v-else class="family-sections__list">
        <div v-for="(responsable, index) in responsables" :key="index" class="family-sections__entry">
          <div class="family-sections__entry-header">
            <span>Responsable {{ index + 1 }}</span>
            <el-button
              link
              type="danger"
              size="small"
              :aria-label="`Quitar responsable ${index + 1}`"
              @click="removeResponsible(index)"
            >
              <el-icon><Delete /></el-icon>
            </el-button>
          </div>

          <div class="family-sections__fields">
            <el-form-item label="Parentesco">
              <el-select
                :model-value="responsable.parentesco"
                @update:model-value="updateResponsible(index, { parentesco: $event })"
              >
                <el-option label="Madre" value="MADRE" />
                <el-option label="Padre" value="PADRE" />
                <el-option label="Tutor" value="TUTOR" />
              </el-select>
            </el-form-item>
            <el-form-item label="Apellidos y nombres">
              <el-input
                :model-value="responsable.nombre_completo"
                @update:model-value="updateResponsible(index, { nombre_completo: $event })"
              />
            </el-form-item>
            <el-form-item label="Tipo de documento">
              <el-select
                clearable
                :model-value="responsable.tipo_documento_codigo"
                @update:model-value="updateResponsible(index, { tipo_documento_codigo: $event })"
              >
                <el-option
                  v-for="tipo in tiposDocumento"
                  :key="tipo.codigo"
                  :label="tipo.nombre"
                  :value="tipo.codigo"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="N.° documento">
              <el-input
                :model-value="responsable.numero_documento"
                :disabled="!responsable.tipo_documento_codigo"
                @update:model-value="updateResponsible(index, { numero_documento: $event })"
              />
            </el-form-item>
            <el-form-item label="Teléfono">
              <el-input
                :model-value="responsable.telefono"
                @update:model-value="updateResponsible(index, { telefono: $event })"
              />
            </el-form-item>
            <el-form-item class="family-sections__principal" label="Principal">
              <el-switch
                :model-value="responsable.es_principal"
                @update:model-value="updateResponsible(index, { es_principal: $event })"
              />
            </el-form-item>
          </div>
        </div>
      </div>
    </section>

    <section class="family-sections__section">
      <header class="family-sections__header">
        <div>
          <h3 class="family-sections__title">Grupo de riesgo</h3>
          <p class="family-sections__hint">Opcional para el registro del paciente.</p>
        </div>
        <el-button size="small" @click="addRisk">Agregar</el-button>
      </header>

      <p v-if="!riesgos.length" class="family-sections__empty">Sin grupos de riesgo registrados.</p>

      <div v-else class="family-sections__list">
        <div v-for="(riesgo, index) in riesgos" :key="index" class="family-sections__entry">
          <div class="family-sections__entry-header">
            <span>Grupo {{ index + 1 }}</span>
            <el-button
              link
              type="danger"
              size="small"
              :aria-label="`Quitar grupo de riesgo ${index + 1}`"
              @click="removeRisk(index)"
            >
              <el-icon><Delete /></el-icon>
            </el-button>
          </div>

          <div class="family-sections__fields family-sections__fields--risk">
            <el-form-item label="Grupo de riesgo">
              <el-select
                :model-value="riesgo.grupo_riesgo_id"
                @update:model-value="updateRisk(index, { grupo_riesgo_id: $event })"
              >
                <el-option
                  v-for="grupo in gruposRiesgo"
                  :key="grupo.id"
                  :label="grupo.nombre"
                  :value="grupo.id"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="Inicio">
              <el-date-picker
                :model-value="riesgo.fecha_inicio"
                type="date"
                value-format="YYYY-MM-DD"
                @update:model-value="updateRisk(index, { fecha_inicio: $event })"
              />
            </el-form-item>
            <el-form-item label="Fin">
              <el-date-picker
                clearable
                :model-value="riesgo.fecha_fin"
                type="date"
                value-format="YYYY-MM-DD"
                @update:model-value="updateRisk(index, { fecha_fin: $event })"
              />
            </el-form-item>
            <el-form-item label="Observación">
              <el-input
                :model-value="riesgo.observacion"
                @update:model-value="updateRisk(index, { observacion: $event })"
              />
            </el-form-item>
          </div>
        </div>
      </div>
    </section>
  </aside>
</template>

<style scoped>
.family-sections {
  display: grid;
  min-width: 0;
  align-content: start;
  gap: 12px;
}

.family-sections__section {
  padding: 12px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 10px;
  background-color: var(--el-fill-color-blank);
}

.family-sections__header,
.family-sections__entry-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
}

.family-sections__title,
.family-sections__entry-header span {
  margin: 0;
  color: var(--el-text-color-primary);
  font-weight: 700;
}

.family-sections__title {
  font-size: 14px;
  line-height: 1.3;
}

.family-sections__hint,
.family-sections__empty {
  margin: 2px 0 0;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  line-height: 1.35;
}

.family-sections__empty {
  padding-top: 10px;
}

.family-sections__list {
  display: grid;
  gap: 8px;
  margin-top: 10px;
}

.family-sections__entry {
  padding-top: 8px;
  border-top: 1px solid var(--el-border-color-lighter);
}

.family-sections__entry-header span {
  font-size: 12px;
}

.family-sections__fields {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 6px 8px;
  margin-top: 6px;
}

.family-sections__fields :deep(.el-form-item) {
  min-width: 0;
  margin-bottom: 0;
}

.family-sections__fields :deep(.el-form-item__label) {
  height: auto;
  padding: 0 0 2px;
  color: var(--el-text-color-secondary);
  font-size: 11px;
  line-height: 1.25;
}

.family-sections__fields :deep(.el-form-item__content),
.family-sections__fields :deep(.el-select),
.family-sections__fields :deep(.el-date-editor) {
  min-width: 0;
  width: 100%;
}

.family-sections__principal {
  align-self: end;
}

.family-sections__fields--risk {
  grid-template-columns: minmax(0, 1fr);
}

@media (max-width: 560px) {
  .family-sections__section {
    padding: 10px;
  }

  .family-sections__fields {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
