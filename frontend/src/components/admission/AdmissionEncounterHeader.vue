<script setup lang="ts">
defineProps<{ modelValue: string }>()
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()
</script>

<template>
  <header class="encounter-header">
    <el-form-item label="Fecha y hora de atención" prop="fecha_atencion">
      <el-date-picker
        :model-value="modelValue"
        type="datetime"
        format="DD/MM/YYYY HH:mm"
        value-format="YYYY-MM-DDTHH:mm:ss"
        :clearable="false"
        aria-label="Fecha y hora de atención"
        @update:model-value="emit('update:modelValue', $event ?? '')"
      />
    </el-form-item>
  </header>
</template>

<style scoped>
.encounter-header {
  grid-area: header;
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 12px;
  min-width: 0;
}
.encounter-header :deep(.el-form-item) {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 8px;
  min-width: 0;
  margin: 0;
}
.encounter-header :deep(.el-form-item__label) {
  height: auto;
  line-height: 1.4;
  padding: 0;
}
.encounter-header :deep(.el-form-item__content) {
  flex: 0 1 216px;
  min-width: 0;
}
.encounter-header :deep(.el-date-editor) {
  width: 100%;
}
@media (max-width: 600px) {
  .encounter-header {
    flex-direction: column;
    align-items: stretch;
  }
  .encounter-header :deep(.el-form-item) {
    flex-wrap: wrap;
  }
  .encounter-header :deep(.el-form-item__content) {
    flex: 1 1 216px;
  }
}
</style>
