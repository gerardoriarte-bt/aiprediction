<template>
  <div v-if="open" class="cmdk-overlay" @click.self="$emit('close')">
    <div class="cmdk" role="dialog" aria-modal="true">
      <div class="cmdk-search">
        <Icon name="search" :size="16" />
        <input
          ref="input"
          v-model="query"
          :placeholder="$t('topnav.search')"
          @keydown="onKey"
        />
        <span class="kbd">ESC</span>
      </div>
      <div class="cmdk-list" ref="list">
        <template v-if="results.length">
          <div
            v-for="(item, i) in results"
            :key="i"
            :class="['cmdk-item', { on: i === activeIdx }]"
            @mouseenter="activeIdx = i"
            @click="selectItem(item)"
          >
            <Badge>{{ item.kind }}</Badge>
            <span class="cmdk-label">{{ item.label }}</span>
            <span v-if="item.hint" class="cmdk-hint mono">{{ item.hint }}</span>
            <Icon name="arrow-r" :size="14" />
          </div>
        </template>
        <div v-else class="cmdk-empty">{{ $t('topnav.noMatch') }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onBeforeUnmount } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import Icon from '../ui/Icon.vue'
import Badge from '../ui/Badge.vue'
import { listClientCreativeTests } from '../../api/clients'

const props = defineProps({
  open: { type: Boolean, default: false },
  allClients: { type: Array, default: () => [] }
})

const emit = defineEmits(['close'])

const router = useRouter()
const route = useRoute()
const { t } = useI18n()

const query = ref('')
const activeIdx = ref(0)
const input = ref(null)
const list = ref(null)
const clientTests = ref([])

const activeClientId = computed(() => {
  const m = (route.path || '').match(/^\/clients\/([^\/]+)/)
  return m ? m[1] : ''
})

// Reset on close, focus input on open. When opened inside a client,
// fetch its tests so the palette surfaces them at the top.
watch(
  () => props.open,
  async (v) => {
    if (v) {
      query.value = ''
      activeIdx.value = 0
      await nextTick()
      input.value && input.value.focus()
      if (activeClientId.value) {
        try {
          const res = await listClientCreativeTests(activeClientId.value)
          clientTests.value = (res.data || []).slice(0, 8)
        } catch {
          clientTests.value = []
        }
      } else {
        clientTests.value = []
      }
    }
  }
)

// Active-client tests first (highest signal), then clients, then pages.
const items = computed(() => {
  const out = []
  for (const tt of clientTests.value) {
    const goal = tt.business_goal || tt.test_id
    out.push({
      kind: 'test',
      label: goal,
      hint: tt.test_id,
      to: `/clients/${activeClientId.value}/tests/${tt.test_id}`,
      keywords: [goal, tt.test_id, tt.audience, tt.winner_label].filter(Boolean).join(' ')
    })
  }
  for (const c of props.allClients) {
    out.push({
      kind: 'client',
      label: c.name + (c.industry ? ' · ' + c.industry : ''),
      hint: '/' + c.slug,
      to: `/clients/${c.client_id}/overview`,
      keywords: [c.name, c.slug, c.industry].filter(Boolean).join(' ')
    })
  }
  out.push({
    kind: 'page',
    label: t('side.manual'),
    hint: '/manual',
    to: '/manual',
    keywords: 'manual help docs'
  })
  out.push({
    kind: 'page',
    label: t('side.help'),
    hint: '/help',
    to: '/help',
    keywords: 'shortcuts atajos help keys'
  })
  out.push({
    kind: 'page',
    label: t('side.clients'),
    hint: '/',
    to: '/',
    keywords: 'clientes home dashboard'
  })
  return out
})

const results = computed(() => {
  const q = query.value.trim().toLowerCase()
  if (!q) return items.value
  return items.value.filter((it) =>
    (it.label + ' ' + (it.keywords || '')).toLowerCase().includes(q)
  )
})

watch(results, () => { activeIdx.value = 0 })

const selectItem = (item) => {
  emit('close')
  router.push(item.to)
}

const onKey = (e) => {
  if (e.key === 'ArrowDown') {
    e.preventDefault()
    activeIdx.value = Math.min(results.value.length - 1, activeIdx.value + 1)
    scrollActiveIntoView()
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    activeIdx.value = Math.max(0, activeIdx.value - 1)
    scrollActiveIntoView()
  } else if (e.key === 'Enter') {
    e.preventDefault()
    const item = results.value[activeIdx.value]
    if (item) selectItem(item)
  } else if (e.key === 'Escape') {
    emit('close')
  }
}

const scrollActiveIntoView = async () => {
  await nextTick()
  if (!list.value) return
  const node = list.value.querySelector('.cmdk-item.on')
  if (node) node.scrollIntoView({ block: 'nearest' })
}

// Listen to ESC at the window level so Cmd+K → ESC also closes.
const onWindowKey = (e) => {
  if (props.open && e.key === 'Escape') emit('close')
}
if (typeof window !== 'undefined') {
  window.addEventListener('keydown', onWindowKey)
  onBeforeUnmount(() => window.removeEventListener('keydown', onWindowKey))
}
</script>

<style scoped>
.cmdk-overlay {
  position: fixed;
  inset: 0;
  background: rgba(26, 24, 20, 0.42);
  z-index: var(--z-modal);
  display: grid;
  place-items: start center;
  padding-top: 96px;
}

.cmdk {
  width: 100%;
  max-width: 580px;
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: var(--r-lg);
  box-shadow: var(--shadow-pop);
  overflow: hidden;
  animation: cmd-in 0.16s ease-out;
}

@keyframes cmd-in {
  from { opacity: 0; transform: translateY(-6px); }
  to { opacity: 1; transform: none; }
}

.cmdk-search {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 18px;
  border-bottom: 1px solid var(--line);
  color: var(--ink-3);
}
.cmdk-search input {
  border: 0;
  outline: 0;
  flex: 1;
  background: transparent;
  font-size: 15px;
  font-family: inherit;
  color: var(--ink);
}

.cmdk-list {
  max-height: 380px;
  overflow-y: auto;
}

.cmdk-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 18px;
  cursor: pointer;
  border-bottom: 1px solid var(--line);
  font-size: 14px;
}
.cmdk-item:last-child { border-bottom: 0; }
.cmdk-item.on { background: var(--surface-2); }

.cmdk-item .badge { min-width: 64px; justify-content: center; }
.cmdk-label { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cmdk-hint { font-size: 11px; color: var(--ink-4); }

.cmdk-empty {
  padding: 24px;
  text-align: center;
  color: var(--ink-3);
  font-size: 13px;
}
</style>
