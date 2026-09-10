<template>
  <PagePlaceholder
    title="Consultorios"
    description="Gestión de consultorios y asignaciones de profesionales."
    :planned="[
      'Lista filtrable por establecimiento; alta y ficha con PATCH/DELETE lógico',
      'Asignaciones: GET .../profesionales puede devolver [] (estado vacío válido)',
      'Asignar profesional y cerrar asignación con PATCH .../cierre',
      'Tras POST de asignación, recargar el mismo GET',
    ]"
  />
</template>

<script setup lang="ts">
import PagePlaceholder from '@/components/PagePlaceholder.vue'
</script>