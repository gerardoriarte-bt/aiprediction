<template>
  <div class="breadcrumb">
    <template v-for="(item, i) in items" :key="i">
      <span v-if="i > 0" class="sep">›</span>
      <span
        :class="i === items.length - 1 ? 'current' : 'crumb'"
        :tabindex="i === items.length - 1 ? -1 : 0"
        @click="onClick(item)"
        @keydown.enter="onClick(item)"
      >
        {{ item.label }}
      </span>
    </template>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'

const props = defineProps({
  items: { type: Array, required: true } // [{label, to?, onClick?}]
})

const router = useRouter()

const onClick = (item) => {
  if (item.onClick) return item.onClick()
  if (item.to) router.push(item.to)
}
</script>
