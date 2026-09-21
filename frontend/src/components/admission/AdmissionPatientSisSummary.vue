<script setup lang="ts">
import { computed } from 'vue'
import { patientSisSummary, type PatientSisData } from '@/utils/patientSis'
import type { CodeCatalogItem } from '@/services/catalogos'

const props = defineProps<{
  patient: Partial<PatientSisData>
  ethnicities: CodeCatalogItem[]
  showAffiliation?: boolean
}>()
const summary = computed(() => patientSisSummary(props.patient, props.ethnicities))
</script>

<template>
  <section class="patient-sis-summary" aria-label="Datos guardados en la ficha">
    <dl class="patient-sis-summary__data">
      <div v-if="showAffiliation !== false" class="patient-sis-summary__row">
        <dt class="patient-sis-summary__label">Afiliación SIS</dt>
        <dd class="patient-sis-summary__value">{{ summary.affiliation }}</dd>
      </div>
      <div class="patient-sis-summary__row">
        <dt class="patient-sis-summary__label">Etnia</dt>
        <dd class="patient-sis-summary__value">{{ summary.ethnicity }}</dd>
      </div>
    </dl>
    <p class="patient-sis-summary__note">Datos de la ficha del paciente · solo lectura.</p>
  </section>
</template>

<style scoped>
.patient-sis-summary {
  margin-top: 16px;
}
.patient-sis-summary__data {
  display: grid;
  gap: 8px;
  margin: 0;
  font-size: 12px;
  line-height: 1.5;
}
.patient-sis-summary__row {
  display: grid;
  grid-template-columns: 110px minmax(0, 1fr);
}
.patient-sis-summary__label {
  color: var(--el-text-color-regular);
}
.patient-sis-summary__value {
  margin: 0;
  color: var(--el-text-color-primary);
  overflow-wrap: anywhere;
}
.patient-sis-summary__note {
  margin: 8px 0 0;
  font-size: 12px;
  line-height: 1.5;
  color: var(--el-text-color-regular);
}
@media (max-width: 560px) {
  .patient-sis-summary__row {
    grid-template-columns: minmax(0, 1fr);
    gap: 2px;
  }
}
</style>
