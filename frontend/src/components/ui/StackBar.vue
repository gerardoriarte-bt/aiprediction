<template>
  <div class="stack-bar" role="img" :aria-label="ariaLabel">
    <span
      v-for="(p, i) in parts"
      :key="i"
      :title="`${p.label}: ${p.value}`"
      :style="{ width: pct(p.value), background: p.color }"
    />
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  parts: { type: Array, required: true },
  ariaLabel: { type: String, default: 'distribution' }
})

const total = computed(() => props.parts.reduce((s, p) => s + (Number(p.value) || 0), 0) || 1)
const pct = (v) => `${((Number(v) || 0) / total.value) * 100}%`
</script>
