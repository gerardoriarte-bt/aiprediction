<template>
  <div class="empty">
    <div v-if="title" class="serif" style="font-size: 22px; margin-bottom: 8px; color: var(--ink);">
      {{ title }}
    </div>
    <div v-if="hint" style="margin-bottom: 16px;">{{ hint }}</div>
    <slot />
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, default: '' },
  hint: { type: String, default: '' }
})
</script>
