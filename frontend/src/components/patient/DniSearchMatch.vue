<script setup lang="ts">
defineProps<{
  patientName: string | null
}>()
</script>

<template>
  <section class="dni-search-match" aria-live="polite" aria-label="Resultado de búsqueda por DNI">
    <strong v-if="patientName" class="dni-search-match__name">{{ patientName }}</strong>
  </section>
</template>

<style scoped>
.dni-search-match {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 36px;
  margin-top: 8px;
  padding: 6px 12px;
  background-color: var(--el-bg-color);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  text-align: center;
}

.dni-search-match__name {
  color: var(--el-text-color-primary);
  font-size: clamp(15px, 1.3vw, 18px);
  font-weight: 700;
  line-height: 1.25;
  overflow-wrap: anywhere;
}
</style>
