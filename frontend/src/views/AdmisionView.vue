<template>
  <AtencionNuevaView :key="route.fullPath" admission />
</template>

<script setup lang="ts">
import AtencionNuevaView from '@/views/AtencionNuevaView.vue'
import { useRoute } from 'vue-router'
const route = useRoute()
</script>
