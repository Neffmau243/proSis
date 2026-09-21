<script setup lang="ts">
import PatientSisFields from './PatientSisFields.vue'
import type {
  CodeCatalogItem,
  EstablishmentCatalogItem,
  IdCatalogItem,
  UbigeoCatalogItem,
} from '@/services/catalogos'

import type {
  PatientRegistrationDraft,
  PatientRegistrationPatch,
} from './patientRegistration.types'

defineProps<{
  form: PatientRegistrationDraft
  tiposDocumento: CodeCatalogItem[]
  sexos: CodeCatalogItem[]
  seguros: IdCatalogItem[]
  establecimientos: EstablishmentCatalogItem[]
  establecimientosLoading: boolean
  ubigeos: UbigeoCatalogItem[]
  ubigeosLoading: boolean
}>()

const emit = defineEmits<{
  update: [changes: PatientRegistrationPatch]
  searchEstablecimientos: [query: string]
  searchUbigeos: [query: string]
}>()

function update(changes: PatientRegistrationPatch): void {
  emit('update', changes)
}
</script>

<template>
  <section class="base-section" aria-labelledby="patient-data-title">
    <header class="base-section__header">
      <h3 id="patient-data-title" class="base-section__title">Base de datos</h3>
    </header>

    <div class="base-section__fields">
      <el-form-item class="base-field" label="N.° historia clínica">
        <el-input
          :model-value="form.historia_clinica"
          @update:model-value="update({ historia_clinica: $event })"
        />
      </el-form-item>

      <el-form-item class="base-field" label="Historia familiar">
        <el-input
          :model-value="form.historia_familiar"
          @update:model-value="update({ historia_familiar: $event })"
        />
      </el-form-item>

      <div class="base-section__document-row">
        <span class="base-section__document-label">Documento</span>
        <div class="base-section__document-fields">
          <el-form-item class="base-field" label="Tipo de documento" prop="tipo_documento_codigo">
            <el-select
              :model-value="form.tipo_documento_codigo"
              @update:model-value="update({ tipo_documento_codigo: $event })"
            >
              <el-option
                v-for="tipo in tiposDocumento"
                :key="tipo.codigo"
                :label="tipo.nombre"
                :value="tipo.codigo"
              />
            </el-select>
          </el-form-item>

          <el-form-item class="base-field" label="N.° documento" prop="numero_documento">
            <el-input
              :model-value="form.numero_documento"
              @update:model-value="update({ numero_documento: $event })"
            />
          </el-form-item>
        </div>
      </div>

      <el-form-item class="base-field" label="Fecha de nacimiento" prop="fecha_nacimiento">
        <el-date-picker
          :model-value="form.fecha_nacimiento"
          type="date"
          value-format="YYYY-MM-DD"
          :disabled-date="(date: Date) => date.getTime() > Date.now()"
          @update:model-value="update({ fecha_nacimiento: $event ?? '' })"
        />
      </el-form-item>

      <el-form-item class="base-field" label="Apellido paterno">
        <el-input
          :model-value="form.apellido_paterno"
          @update:model-value="update({ apellido_paterno: $event })"
        />
      </el-form-item>

      <el-form-item class="base-field" label="Apellido materno">
        <el-input
          :model-value="form.apellido_materno"
          @update:model-value="update({ apellido_materno: $event })"
        />
      </el-form-item>

      <el-form-item class="base-field" label="Primer nombre" prop="primer_nombre">
        <el-input
          :model-value="form.primer_nombre"
          @update:model-value="update({ primer_nombre: $event })"
        />
      </el-form-item>

      <el-form-item class="base-field" label="Otros nombres">
        <el-input
          :model-value="form.otros_nombres"
          @update:model-value="update({ otros_nombres: $event })"
        />
      </el-form-item>

      <el-form-item class="base-field" label="Sexo">
        <el-select
          clearable
          :model-value="form.sexo_codigo"
          @update:model-value="update({ sexo_codigo: $event })"
        >
          <el-option
            v-for="sexo in sexos"
            :key="sexo.codigo"
            :label="sexo.nombre"
            :value="sexo.codigo"
          />
        </el-select>
      </el-form-item>

      <el-form-item class="base-field" label="Distrito">
        <el-select
          clearable
          filterable
          remote
          :model-value="form.ubigeo_residencia_codigo"
          :remote-method="(query: string) => emit('searchUbigeos', query)"
          :loading="ubigeosLoading"
          placeholder="Busque por distrito"
          @update:model-value="update({ ubigeo_residencia_codigo: $event })"
        >
          <el-option
            v-for="ubigeo in ubigeos"
            :key="ubigeo.codigo"
            :label="`${ubigeo.departamento} / ${ubigeo.provincia} / ${ubigeo.distrito}`"
            :value="ubigeo.codigo"
          />
        </el-select>
      </el-form-item>

      <el-form-item class="base-field" label="Localidad">
        <el-input
          :model-value="form.localidad"
          placeholder="Ej. Alto Selva Alegre"
          @update:model-value="update({ localidad: $event })"
        />
      </el-form-item>

      <el-form-item class="base-field" label="Dirección">
        <el-input
          :model-value="form.direccion"
          placeholder="Ej. Calle Cahuide 504"
          @update:model-value="update({ direccion: $event })"
        />
      </el-form-item>

      <el-form-item class="base-field" label="Establecimiento">
        <el-select
          clearable
          filterable
          remote
          :model-value="form.establecimiento_registro_id"
          :remote-method="(query: string) => emit('searchEstablecimientos', query)"
          :loading="establecimientosLoading"
          placeholder="Busque por nombre"
          @update:model-value="update({ establecimiento_registro_id: $event })"
        >
          <el-option
            v-for="establecimiento in establecimientos"
            :key="establecimiento.id"
            :label="establecimiento.nombre"
            :value="establecimiento.id"
          />
        </el-select>
      </el-form-item>

      <el-form-item class="base-field" label="Seguro de salud">
        <el-select
          clearable
          filterable
          :model-value="form.seguro_id"
          @update:model-value="update({ seguro_id: $event })"
        >
          <el-option
            v-for="seguro in seguros"
            :key="seguro.id"
            :label="seguro.nombre"
            :value="seguro.id"
          />
        </el-select>
      </el-form-item>

      <el-form-item class="base-field" label="Fecha de inscripción">
        <el-date-picker
          :model-value="form.fecha_inscripcion"
          type="date"
          value-format="YYYY-MM-DD"
          @update:model-value="update({ fecha_inscripcion: $event ?? '' })"
        />
      </el-form-item>

      <el-form-item class="base-field" label="Condición">
        <el-input
          :model-value="form.condicion"
          @update:model-value="update({ condicion: $event })"
        />
      </el-form-item>
    </div>
    <PatientSisFields :value="form" @update="update" />
  </section>
</template>

<style scoped>
.base-section {
  min-width: 0;
  --el-component-size: 26px;
}

/* Element Plus fija min-height: 32px en el wrapper del select y no respeta
   --el-component-size, así que quedaba 6px más alto que los inputs vecinos. */
.base-section :deep(.el-select__wrapper) {
  min-height: var(--el-component-size);
  padding-top: 0;
  padding-bottom: 0;
}

.base-section__header {
  margin-bottom: 8px;
}

.base-section__title {
  margin: 0;
  color: var(--el-text-color-primary);
  font-size: 14px;
  font-weight: 700;
  line-height: 1.25;
}

.base-section__fields {
  display: grid;
  gap: 5px;
}

.base-section__fields :deep(.base-field) {
  display: grid;
  grid-template-columns: minmax(122px, 0.42fr) minmax(0, 1fr);
  align-items: center;
  min-width: 0;
  margin: 0;
}

.base-section__fields :deep(.base-field .el-form-item__label) {
  height: auto;
  /* Element Plus le pone 8px de margen inferior a la etiqueta en label-position
     "top"; dentro de la grilla eso la subía 4px respecto al centro de la fila. */
  margin: 0;
  padding: 0 8px 0 0;
  color: var(--el-text-color-secondary);
  font-size: 11px;
  line-height: 1.2;
}

.base-section__fields :deep(.base-field .el-form-item__content) {
  min-width: 0;
  margin-left: 0 !important;
}

.base-section__fields :deep(.el-select),
.base-section__fields :deep(.el-date-editor) {
  width: 100%;
}

.base-section__fields :deep(.el-input__inner),
.base-section__fields :deep(.el-select__selected-item),
.base-section__fields :deep(.el-select__placeholder) {
  font-size: 12px;
}

/* Fila de documento: reusa la misma columna de etiquetas que el resto del
   formulario y reparte su contenido entre los dos campos. Cada campo lleva su
   etiqueta encima, así los dos inputs quedan alineados con los demás. */
.base-section__document-row {
  display: grid;
  grid-template-columns: minmax(122px, 0.42fr) minmax(0, 1fr);
  align-items: center;
  min-width: 0;
}

.base-section__document-label {
  padding: 0 8px 0 0;
  color: var(--el-text-color-secondary);
  font-size: 11px;
  line-height: 1.2;
}

.base-section__document-fields {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  min-width: 0;
}

.base-section__document-fields :deep(.base-field) {
  display: block;
  margin: 0;
}

.base-section__document-fields :deep(.base-field .el-form-item__label) {
  display: block;
  height: auto;
  margin: 0;
  padding: 0 0 2px;
  line-height: 1.2;
}

@media (max-width: 640px) {
  .base-section__document-row {
    grid-template-columns: minmax(0, 1fr);
    gap: 2px;
  }

  .base-section__document-label {
    padding-right: 0;
  }

  .base-section__document-fields {
    grid-template-columns: minmax(0, 1fr);
  }

  .base-section__fields :deep(.base-field) {
    grid-template-columns: minmax(0, 1fr);
    gap: 2px;
  }

  .base-section__fields :deep(.base-field .el-form-item__label) {
    padding-right: 0;
  }
}
</style>
