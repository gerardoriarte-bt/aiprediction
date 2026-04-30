<template>
  <component
    :is="tag"
    :class="['btn', variantClass, sizeClass]"
    :disabled="disabled"
    :type="tag === 'button' ? type : undefined"
    :to="to"
    :href="href"
    @click="onClick"
  >
    <Icon v-if="icon" :name="icon" :size="iconSize" />
    <span v-if="$slots.default || label"><slot>{{ label }}</slot></span>
  </component>
</template>

<script setup>
import { computed } from 'vue'
import Icon from './Icon.vue'

const props = defineProps({
  variant: {
    type: String,
    default: 'default',
    validator: (v) => ['default', 'primary', 'signal', 'brand', 'ghost', 'danger'].includes(v)
  },
  size: { type: String, default: 'md', validator: (v) => ['sm', 'md', 'lg'].includes(v) },
  icon: { type: String, default: '' },
  label: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
  type: { type: String, default: 'button' },
  // Optional: render as <router-link> or <a> when these are passed
  to: { type: [String, Object], default: null },
  href: { type: String, default: '' }
})

const emit = defineEmits(['click'])

const variantClass = computed(() => {
  if (props.variant === 'default') return ''
  return props.variant
})
const sizeClass = computed(() => (props.size === 'md' ? '' : props.size))

const iconSize = computed(() => (props.size === 'sm' ? 12 : props.size === 'lg' ? 16 : 14))

const tag = computed(() => {
  if (props.to) return 'router-link'
  if (props.href) return 'a'
  return 'button'
})

const onClick = (e) => {
  if (props.disabled) {
    e.preventDefault()
    return
  }
  emit('click', e)
}
</script>
