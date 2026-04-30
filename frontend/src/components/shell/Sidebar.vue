<template>
  <nav class="sidebar" :aria-label="$t('side.workspace')">
    <template v-if="clientId">
      <div class="group-label">{{ $t('side.workspace') }}</div>
      <router-link
        v-for="it in workspaceItems"
        :key="it.id"
        :to="it.to"
        class="nav-item"
        :class="{ on: isActive(it.id) }"
        :aria-current="isActive(it.id) ? 'page' : null"
      >
        <span class="nav-icon"><Icon :name="it.icon" :size="15" /></span>
        <span>{{ it.label }}</span>
        <span v-if="it.meta != null" class="nav-meta">{{ it.meta }}</span>
        <span v-if="it.dot" class="nav-dot"></span>
      </router-link>
      <div class="group-spacer"></div>
    </template>

    <div class="group-label">{{ $t('side.global') }}</div>
    <router-link
      v-for="it in globalItems"
      :key="it.id"
      :to="it.to"
      class="nav-item"
      :class="{ on: isGlobalActive(it.to), highlight: it.highlight }"
      :aria-current="isGlobalActive(it.to) ? 'page' : null"
    >
      <span class="nav-icon"><Icon :name="it.icon" :size="15" /></span>
      <span>{{ it.label }}</span>
    </router-link>

    <div class="sidebar-card">
      <div class="mono sb-eyebrow">SINTETIC</div>
      <div class="serif sb-title">Prediction AI</div>
      <div class="sb-body">{{ $t('side.feedback') }}</div>
    </div>
  </nav>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import Icon from '../ui/Icon.vue'

const props = defineProps({
  clientId: { type: String, default: '' },
  stats: { type: Object, default: () => ({}) }
})

const { t } = useI18n()
const route = useRoute()

const workspaceItems = computed(() => {
  if (!props.clientId) return []
  const base = `/clients/${props.clientId}`
  return [
    { id: 'overview', icon: 'home',     label: t('side.overview'), to: `${base}/overview` },
    { id: 'context',  icon: 'context',  label: t('side.context'),  to: `${base}/context`, dot: !props.stats.episodes },
    { id: 'tests',    icon: 'tests',    label: t('side.tests'),    to: `${base}/tests`,   meta: props.stats.tests ?? '' },
    { id: 'sims',     icon: 'sims',     label: t('side.sims'),     to: `${base}/sims`,    meta: props.stats.sims ?? '' },
    { id: 'reports',  icon: 'report',   label: t('side.reports'),  to: `${base}/reports`, meta: props.stats.reports ?? '' },
    { id: 'settings', icon: 'settings', label: t('side.settings'), to: `${base}/settings` }
  ]
})

const globalItems = computed(() => [
  { id: 'clients', icon: 'grid', label: t('side.clients'), to: '/' },
  { id: 'guide',   icon: 'help', label: t('side.guide'),   to: '/guide', highlight: true },
  { id: 'manual',  icon: 'book', label: t('side.manual'),  to: '/manual' },
  { id: 'help',    icon: 'key',  label: t('side.help'),    to: '/help' }
])

const isActive = (tabId) => {
  if (!route.path.startsWith(`/clients/${props.clientId}`)) return false
  // Path looks like /clients/<id>/<tab>[/...]
  const segs = route.path.split('/').filter(Boolean)
  return segs[2] === tabId
}

const isGlobalActive = (to) => {
  if (to === '/') return route.path === '/'
  return route.path === to || route.path.startsWith(to + '/')
}
</script>

<style scoped>
.sidebar {
  position: sticky;
  top: 56px;
  height: calc(100vh - 56px);
  width: 232px;
  border-right: 1px solid var(--line);
  background: var(--surface);
  padding: 18px 14px 18px 16px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex-shrink: 0;
}

.group-label {
  font-family: var(--mono);
  font-size: 10px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--ink-4);
  padding: 4px 10px;
  margin-top: 4px;
}

.group-spacer { height: 12px; }

.nav-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 7px 10px;
  border-radius: var(--r-sm);
  font-size: 13px;
  color: var(--ink-2);
  text-decoration: none;
  cursor: pointer;
  transition: background 0.12s, color 0.12s;
}

.nav-item:hover { background: var(--surface-2); color: var(--ink); }

.nav-item.on {
  background: var(--ink);
  color: var(--bg);
}
.nav-item.on .nav-meta { color: rgba(255,255,255,.55); }

/* Highlight: persistent visual cue for the always-on usage guide. */
.nav-item.highlight:not(.on) {
  color: var(--ink);
}
.nav-item.highlight:not(.on) .nav-icon {
  color: var(--signal, var(--ink));
}
.nav-item.highlight:not(.on)::after {
  content: "";
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--signal, var(--ink));
  margin-left: auto;
  margin-right: 2px;
  align-self: center;
}

.nav-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  flex-shrink: 0;
}

.nav-meta {
  margin-left: auto;
  font-family: var(--mono);
  font-size: 11px;
  color: var(--ink-4);
}

.nav-dot {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--signal);
}

.sidebar-card {
  margin-top: auto;
  padding: 12px;
  background: var(--ink);
  color: var(--bg);
  border-radius: var(--r);
  font-size: 12px;
  line-height: 1.45;
}
.sb-eyebrow {
  font-size: 10px;
  letter-spacing: 0.15em;
  opacity: 0.65;
  margin-bottom: 6px;
}
.sb-title { font-size: 16px; margin-bottom: 6px; }
.sb-body { opacity: 0.6; }

@media (max-width: 900px) {
  .sidebar {
    position: static;
    width: 100%;
    height: auto;
    flex-direction: row;
    overflow-x: auto;
    padding: 12px;
    gap: 8px;
  }
  .group-label, .group-spacer, .sidebar-card { display: none; }
  .nav-item { white-space: nowrap; }
}
</style>
