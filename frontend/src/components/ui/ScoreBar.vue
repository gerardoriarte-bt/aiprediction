<template>
  <div class="score-bar" role="img" :aria-label="ariaLabel">
    <div class="fill" :style="{ width: width, background: color }"></div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  value: { type: [Number, String], required: true },
  max: { type: [Number, String], default: 100 },
  color: { type: String, default: 'var(--ink)' },
  ariaLabel: { type: String, default: '' }
})

const width = computed(() => {
  const v = Number(props.value)
  const m = Number(props.max) || 1
  const ratio = Math.max(0, Math.min(1, v / m))
  return `${ratio * 100}%`
})
</script>
