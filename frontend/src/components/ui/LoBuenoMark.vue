<template>
  <div
    class="lobueno-mark"
    :style="{ width: size + 'px', height: size + 'px' }"
    role="img"
    aria-label="Sintetic"
  >
    <span /><span /><span /><span />
  </div>
</template>

<script setup>
defineProps({
  size: { type: [Number, String], default: 28 }
})
</script>
