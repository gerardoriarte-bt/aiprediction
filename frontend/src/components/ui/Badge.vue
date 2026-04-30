<template>
  <span :class="['badge', variantClass]">
    <slot>{{ label }}</slot>
  </span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  variant: {
    type: String,
    default: 'default',
    validator: (v) => ['default', 'solid', 'signal', 'ok', 'warn', 'bad', 'brand', 'plum'].includes(v)
  },
  label: { type: String, default: '' }
})

const variantClass = computed(() => (props.variant === 'default' ? '' : props.variant))
</script>
