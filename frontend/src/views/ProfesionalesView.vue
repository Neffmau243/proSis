<template>
  <PagePlaceholder
    title="Profesionales"
    description="Gestión de profesionales, especialidades y bajas lógicas."
    :planned="[
      'Lista con incluir_inactivos y alta POST /configuracion/profesionales',
      'Ficha: PATCH, PUT .../especialidades y DELETE (baja lógica)',
      'Catálogos: profesiones y especialidades',
      'Los DELETE no son borrados irreversibles: no ofrecer confirmación destructiva',
    ]"
  />
</template>

<script setup lang="ts">
import PagePlaceholder from '@/components/PagePlaceholder.vue'
</script>