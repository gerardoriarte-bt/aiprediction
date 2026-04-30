<template>
  <ul class="gl">
    <li
      v-for="t in types"
      :key="t.key"
      :class="{ off: filter && filter[t.key] === false }"
      @click="toggle(t.key)"
      role="button"
      :aria-pressed="!filter || filter[t.key] !== false"
    >
      <span class="dot" :style="{ background: t.color }"></span>
      <span class="name">{{ t.label }}</span>
      <span v-if="counts && counts[t.key]" class="count mono">{{ counts[t.key] }}</span>
    </li>
  </ul>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  filter: { type: Object, default: null },     // { Brand: true|false, ... }
  counts: { type: Object, default: () => ({}) }
})

const emit = defineEmits(['toggle'])

const PALETTE = {
  Brand:        '#1f3a2e',
  Audience:     '#2d5240',
  Channel:      '#d97706',
  Claim:        '#6b3a52',
  Competitor:   '#8b2a1f',
  Study:        '#3d3a32',
  Metric:       '#a8650b',
  Risk:         '#b91c1c',
  Person:       '#475569',
  Organization: '#1a1814',
  Product:      '#1f3a2e',
  Entity:       '#9a9686'
}

const types = computed(() => {
  // Show only types that exist in the dataset (or all if no counts).
  const keys = Object.keys(props.counts).length
    ? Object.keys(props.counts)
    : Object.keys(PALETTE)
  return keys.map((k) => ({ key: k, label: k, color: PALETTE[k] || '#9a9686' }))
})

const toggle = (key) => emit('toggle', key)
</script>

<style scoped>
.gl {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.gl li {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 5px 10px;
  border: 1px solid var(--line);
  background: var(--surface);
  border-radius: 999px;
  cursor: pointer;
  font-size: 12px;
  color: var(--ink-2);
  transition: opacity 0.12s, background 0.12s;
}

.gl li:hover { background: var(--surface-2); }

.gl li.off { opacity: 0.4; background: var(--surface-2); }

.dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  flex-shrink: 0;
}

.count {
  font-size: 11px;
  color: var(--ink-4);
  letter-spacing: 0.03em;
}
</style>
