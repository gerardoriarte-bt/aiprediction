<template>
  <header class="topnav">
    <router-link to="/" class="brand">
      <LoBuenoMark :size="26" />
      <span class="brand-name">Sin<span class="brand-dot">·</span>tetic</span>
      <span class="brand-sub mono">Prediction AI</span>
    </router-link>

    <span class="divider" v-if="activeClient" />

    <div
      v-if="activeClient"
      class="client-switcher"
      tabindex="0"
      role="button"
      :aria-label="$t('topnav.switchClient')"
      @click="toggleSwitcher"
      @blur="closeSwitcher"
      @keydown.enter="toggleSwitcher"
      @keydown.escape="closeSwitcher"
    >
      <span class="dot" :style="{ background: accent }"></span>
      <span class="name serif">{{ activeClient.name }}</span>
      <span class="industry mono" v-if="activeClient.industry">· {{ activeClient.industry }}</span>
      <Icon name="chevron-d" :size="14" />

      <div v-if="open" class="switcher-pop" role="menu">
        <div class="pop-search">
          <Icon name="search" :size="14" />
          <input
            v-model="query"
            :placeholder="$t('topnav.searchClient')"
            class="pop-input"
          />
        </div>
        <ul class="pop-list">
          <li
            v-for="c in filtered"
            :key="c.client_id"
            :class="{ on: c.client_id === activeClient.client_id }"
            @mousedown.prevent="selectClient(c)"
          >
            <span class="dot" :style="{ background: accentFor(c) }"></span>
            <span class="serif">{{ c.name }}</span>
            <span class="mono industry">· {{ c.industry || $t('clients.noIndustry') }}</span>
          </li>
          <li v-if="!filtered.length" class="pop-empty">
            {{ $t('topnav.noMatch') }}
          </li>
        </ul>
      </div>
    </div>

    <div class="grow"></div>

    <router-link to="/guide" class="nav-pill" :title="$t('topnav.guideHint')">
      <Icon name="help" :size="14" />
      <span>{{ $t('side.guide') }}</span>
    </router-link>

    <button class="search-trigger" @click="$emit('open-cmd-k')">
      <Icon name="search" :size="14" />
      <span>{{ $t('topnav.search') }}</span>
      <span class="kbd">⌘K</span>
    </button>

    <div class="lang-toggle" role="group" :aria-label="$t('topnav.language')">
      <button
        class="lang-btn"
        :class="{ on: $i18n.locale === 'es' }"
        @click="setLang('es')"
      >
        ES
      </button>
      <button
        class="lang-btn"
        :class="{ on: $i18n.locale === 'en' }"
        @click="setLang('en')"
      >
        EN
      </button>
    </div>

    <div class="user-chip">P</div>
  </header>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import LoBuenoMark from '../ui/LoBuenoMark.vue'
import Icon from '../ui/Icon.vue'

const props = defineProps({
  activeClient: { type: Object, default: null },
  allClients: { type: Array, default: () => [] }
})

defineEmits(['open-cmd-k'])

const router = useRouter()
const { locale } = useI18n()

const open = ref(false)
const query = ref('')

const setLang = (l) => {
  locale.value = l
  localStorage.setItem('locale', l)
}

const PALETTE = ['#1f3a2e', '#6b3a52', '#d97706', '#2d5240', '#1a1814', '#a8650b', '#3d3a32', '#8b2a1f']
const accentFor = (c) => {
  if (c?.metadata?.accent) return c.metadata.accent
  let h = 0
  const slug = c?.slug || c?.client_id || ''
  for (let i = 0; i < slug.length; i++) h = (h * 31 + slug.charCodeAt(i)) >>> 0
  return PALETTE[h % PALETTE.length]
}

const accent = computed(() => accentFor(props.activeClient))

const filtered = computed(() => {
  const q = query.value.trim().toLowerCase()
  if (!q) return props.allClients
  return props.allClients.filter(
    (c) => (c.name || '').toLowerCase().includes(q) || (c.slug || '').toLowerCase().includes(q)
  )
})

const toggleSwitcher = () => {
  open.value = !open.value
  if (open.value) query.value = ''
}

const closeSwitcher = () => {
  // setTimeout so a click on a list item still fires before we hide it.
  setTimeout(() => { open.value = false }, 120)
}

const selectClient = (c) => {
  open.value = false
  if (c.client_id !== props.activeClient?.client_id) {
    router.push(`/clients/${c.client_id}/overview`)
  }
}
</script>

<style scoped>
.topnav {
  position: sticky;
  top: 0;
  z-index: var(--z-nav);
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 24px;
  background: var(--surface);
  border-bottom: 1px solid var(--line);
  min-height: 56px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  text-decoration: none;
  color: inherit;
  cursor: pointer;
}

.brand-name {
  font-family: var(--serif);
  font-size: 18px;
  letter-spacing: -0.01em;
  color: var(--ink);
}
.brand-dot { color: var(--signal); }
.brand-sub {
  font-size: 10.5px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--ink-3);
  padding: 2px 8px;
  border: 1px solid var(--line);
  border-radius: var(--r-xs);
  margin-left: 4px;
}

.divider {
  width: 1px;
  height: 22px;
  background: var(--line);
}

/* — Client switcher — */
.client-switcher {
  position: relative;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  border-radius: var(--r-sm);
  cursor: pointer;
  outline: none;
  transition: background 0.12s;
}
.client-switcher:hover,
.client-switcher:focus-visible { background: var(--surface-2); }

.client-switcher .dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.client-switcher .name { font-size: 15px; color: var(--ink); }
.client-switcher .industry { font-size: 11px; color: var(--ink-3); letter-spacing: 0.04em; }

.switcher-pop {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  width: 320px;
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: var(--r);
  box-shadow: var(--shadow-pop);
  padding: 0;
  z-index: var(--z-popup);
  cursor: default;
  animation: pop-in 0.15s ease-out;
}

@keyframes pop-in {
  from { opacity: 0; transform: translateY(-3px); }
  to { opacity: 1; transform: none; }
}

.pop-search {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border-bottom: 1px solid var(--line);
  color: var(--ink-3);
}
.pop-input {
  border: none;
  outline: none;
  background: transparent;
  flex: 1;
  font-family: inherit;
  font-size: 13px;
  color: var(--ink);
}

.pop-list {
  list-style: none;
  margin: 0;
  padding: 4px 0;
  max-height: 280px;
  overflow-y: auto;
}
.pop-list li {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  cursor: pointer;
  font-size: 13px;
}
.pop-list li:hover { background: var(--surface-2); }
.pop-list li.on { background: var(--surface-3); }
.pop-list li .industry { color: var(--ink-3); font-size: 11px; }
.pop-list li .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.pop-empty {
  padding: 16px;
  color: var(--ink-3);
  text-align: center;
  font-size: 12px;
}

.grow { flex: 1; }

/* — Always-on guide pill — */
.nav-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border: 1px solid var(--line);
  background: var(--surface);
  color: var(--ink-2);
  border-radius: var(--r-sm);
  font-size: 12px;
  text-decoration: none;
  transition: background 0.12s, border-color 0.12s, color 0.12s;
}
.nav-pill:hover {
  background: var(--surface-2);
  border-color: var(--line-2);
  color: var(--ink);
}
.nav-pill.router-link-active {
  background: var(--ink);
  color: var(--bg);
  border-color: var(--ink);
}

/* — Search trigger (Cmd+K) — */
.search-trigger {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border: 1px solid var(--line);
  background: var(--surface-2);
  color: var(--ink-3);
  border-radius: var(--r-sm);
  cursor: pointer;
  font-size: 12px;
  font-family: inherit;
}
.search-trigger:hover { background: var(--surface-3); color: var(--ink-2); }

/* — Language toggle — */
.lang-toggle {
  display: flex;
  border: 1px solid var(--line);
  border-radius: var(--r-sm);
  overflow: hidden;
}
.lang-btn {
  background: transparent;
  border: 0;
  color: var(--ink-3);
  padding: 5px 10px;
  cursor: pointer;
  font-family: var(--mono);
  font-size: 11px;
  letter-spacing: 0.08em;
}
.lang-btn.on {
  background: var(--ink);
  color: var(--bg);
}

/* — User chip — */
.user-chip {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: var(--ink);
  color: var(--bg);
  display: grid;
  place-items: center;
  font-family: var(--serif);
  font-size: 14px;
}

@media (max-width: 760px) {
  .brand-sub, .industry, .lang-toggle { display: none; }
  .nav-pill span { display: none; }
}
</style>
