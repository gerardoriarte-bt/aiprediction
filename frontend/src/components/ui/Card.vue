<template>
  <div :class="['card', toneClass, { hoverable: hoverable }]">
    <slot />
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  tone: { type: String, default: 'default', validator: (v) => ['default', 'tonal', 'dark'].includes(v) },
  hoverable: { type: Boolean, default: false }
})

const toneClass = computed(() => (props.tone === 'default' ? '' : props.tone))
</script>
