<script setup lang="ts">
import { computed } from 'vue'
import { PATIENT_CONDITIONS } from '@/utils/patientCondition'

const props = withDefaults(
  defineProps<{ modelValue?: string | null; disabled?: boolean; ariaLabel?: string }>(),
  { ariaLabel: 'Condición' },
)
const emit = defineEmits<{ 'update:modelValue': [value: string | null] }>()
const historicalValue = computed(() =>
  props.modelValue && !PATIENT_CONDITIONS.some((value) => value === props.modelValue)
    ? props.modelValue
    : null,
)
</script>

<template>
  <el-select
    :model-value="modelValue"
    :disabled="disabled"
    clearable
    :value-on-clear="null"
    placeholder="Sin condición registrada"
    :aria-label="ariaLabel"
    @update:model-value="emit('update:modelValue', $event ?? null)"
  >
    <el-option
      v-if="historicalValue"
      :value="historicalValue"
      :label="`${historicalValue} (histórico)`"
      disabled
    />
    <el-option v-for="value in PATIENT_CONDITIONS" :key="value" :value="value" :label="value" />
  </el-select>
</template>
