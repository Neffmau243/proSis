<template>
  <section class="placeholder">
    <h2 class="placeholder__title">{{ title }}</h2>
    <el-empty :description="description" />
    <ul v-if="planned.length" class="placeholder__planned">
      <li v-for="item in planned" :key="item">{{ item }}</li>
    </ul>
  </section>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    title: string
    description: string
    /** Funcionalidades previstas por GUIA_FRONTEND_RUTAS.md para esta vista. */
    planned?: string[]
  }>(),
  { planned: () => [] },
)
</script>

<style scoped>
.placeholder__title {
  margin-top: 0;
}

.placeholder__planned {
  max-width: 560px;
  margin: 0 auto;
  color: var(--el-text-color-secondary);
  line-height: 1.7;
}
</style>