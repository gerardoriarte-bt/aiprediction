<template>
  <span class="hh-root" :class="{ 'hh-root--open': open }">
    <button
      type="button"
      class="hh-trigger"
      :aria-label="ariaLabel"
      :aria-expanded="open"
      @click.stop="toggle"
      @blur="open = false"
      @keydown.escape="open = false"
    >
      ?
    </button>
    <span
      v-if="open"
      class="hh-tip"
      :class="`hh-tip--${placement}`"
      role="tooltip"
    >
      <slot>{{ text }}</slot>
    </span>
  </span>
</template>

<script setup>
import { ref } from 'vue'

defineProps({
  text: { type: String, default: '' },
  placement: { type: String, default: 'top' }, // top | right
  ariaLabel: { type: String, default: 'Help' }
})

const open = ref(false)
const toggle = () => { open.value = !open.value }
</script>

<style scoped>
.hh-root {
  display: inline-flex;
  align-items: center;
  position: relative;
  margin-left: 6px;
  vertical-align: middle;
}

.hh-trigger {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  border: 1px solid #9ca3af;
  background: #f3f4f6;
  color: #4b5563;
  font-size: 11px;
  font-weight: 600;
  line-height: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  padding: 0;
  font-family: inherit;
}

.hh-trigger:hover,
.hh-root--open .hh-trigger {
  background: #2563eb;
  color: #fff;
  border-color: #2563eb;
}

.hh-tip {
  position: absolute;
  z-index: 10;
  width: max-content;
  max-width: 280px;
  background: #111827;
  color: #f9fafb;
  padding: 8px 10px;
  border-radius: 6px;
  font-size: 12px;
  line-height: 1.45;
  font-weight: 400;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.18);
  text-align: left;
  white-space: normal;
  pointer-events: none;
}

.hh-tip--top {
  bottom: calc(100% + 6px);
  left: 50%;
  transform: translateX(-50%);
}

.hh-tip--right {
  top: 50%;
  left: calc(100% + 8px);
  transform: translateY(-50%);
}
</style>
