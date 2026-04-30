<template>
  <div class="home">
    <!-- Top nav (header de la home, bare-bones para R2.2; el shell completo llega en R2.3) -->
    <header class="home-nav">
      <div class="home-brand">
        <LoBuenoMark :size="26" />
        <span class="brand-name">Sin<span class="brand-dot">·</span>tetic</span>
        <span class="brand-sub mono">Prediction AI</span>
      </div>
      <div class="grow"></div>
      <button class="lang-btn" :class="{ on: $i18n.locale === 'es' }" @click="setLang('es')">ES</button>
      <button class="lang-btn" :class="{ on: $i18n.locale === 'en' }" @click="setLang('en')">EN</button>
    </header>

    <main id="main" class="home-main" tabindex="-1">
      <!-- HERO -->
      <section class="hero">
        <div class="hero-left">
          <div class="eyebrow">grupo lobueno · prediction ai</div>
          <h1 class="h-display">{{ $t('home2.heroTitle') }}</h1>
          <p class="hero-sub">{{ $t('home2.heroSub') }}</p>
          <div class="hero-actions">
            <Button v-if="firstClientId" variant="primary" icon="arrow-r" @click="goToFirst">
              {{ $t('home2.openFirst', { name: firstClientName }) }}
            </Button>
            <Button v-if="available" icon="plus" @click="openCreate">
              {{ $t('clients.createClient') }}
            </Button>
          </div>
        </div>

        <!-- Network state KPIs -->
        <Card v-if="available" tone="tonal" class="hero-stats">
          <div class="hero-stats-head">
            <div class="label">{{ $t('home2.networkState') }}</div>
            <div class="serif hero-stats-title">{{ $t('home2.thisWeek') }}</div>
          </div>
          <div class="kpi-row hero-kpis">
            <div class="kpi">
              <div class="k">{{ $t('home2.kpi.clients') }}</div>
              <div class="v num">{{ clients.length }}</div>
            </div>
            <div class="kpi">
              <div class="k">{{ $t('home2.kpi.tests') }}</div>
              <div class="v num">{{ totalTests }}</div>
            </div>
            <div class="kpi">
              <div class="k">{{ $t('home2.kpi.episodes') }}</div>
              <div class="v num">{{ totalEpisodes }}</div>
            </div>
            <div class="kpi">
              <div class="k">{{ $t('home2.kpi.entities') }}</div>
              <div class="v num">{{ totalEntities }}</div>
            </div>
          </div>
        </Card>
      </section>

      <!-- Disabled (no DATABASE_URL) -->
      <EmptyState
        v-if="!healthLoading && !available"
        :title="$t('clients.disabledTitle')"
        :hint="$t('clients.disabledDesc')"
      >
        <code class="kbd">DATABASE_URL=postgresql://…</code>
      </EmptyState>

      <!-- Loading -->
      <div v-else-if="loading" class="grid-3">
        <div v-for="n in 6" :key="n" class="card skeleton">
          <div class="sk-head"></div>
          <div class="sk-body">
            <div class="sk-line"></div>
            <div class="sk-line short"></div>
          </div>
        </div>
      </div>

      <!-- Empty -->
      <EmptyState
        v-else-if="clients.length === 0"
        :title="$t('home2.emptyTitle')"
        :hint="$t('home2.emptyHint')"
      >
        <Button variant="signal" icon="plus" @click="openCreate">
          {{ $t('clients.createClient') }}
        </Button>
      </EmptyState>

      <!-- Clients section -->
      <section v-else class="clients-section">
        <div class="section-head">
          <div class="lt">
            <h2 class="h-1">{{ $t('clients.listTitle') }}</h2>
            <span class="ct">{{ filtered.length }} / {{ clients.length }}</span>
          </div>
          <div class="chips">
            <span
              v-for="ind in industries"
              :key="ind"
              class="chip"
              :class="{ on: filter === ind }"
              @click="filter = ind"
            >
              {{ ind === 'all' ? $t('home2.filterAll') : ind }}
            </span>
          </div>
        </div>

        <div class="grid-3">
          <Card
            v-for="c in filtered"
            :key="c.client_id"
            hoverable
            class="client-card"
            @click="openClient(c.client_id)"
          >
            <div class="cc-head" :style="{ background: accentFor(c) }">
              <div class="avatar cc-avatar">{{ initialsFor(c) }}</div>
              <div class="cc-head-text">
                <div class="serif cc-name">{{ c.name }}</div>
                <div class="mono cc-industry">{{ c.industry || $t('clients.noIndustry') }}</div>
              </div>
              <span class="mono cc-slug">/{{ c.slug }}</span>
            </div>
            <div class="cc-body">
              <div class="cc-stats">
                <div>
                  <div class="label">{{ $t('clients.creativeTests.tests') }}</div>
                  <div class="num serif cc-stat">{{ c.tests ?? 0 }}</div>
                </div>
                <div>
                  <div class="label">{{ $t('home2.kpi.episodes') }}</div>
                  <div class="num serif cc-stat">{{ c.episodes ?? 0 }}</div>
                </div>
                <div>
                  <div class="label">{{ $t('home2.kpi.entities') }}</div>
                  <div class="num serif cc-stat">{{ c.entities ?? 0 }}</div>
                </div>
              </div>
              <hr class="hdiv" />
              <div class="cc-foot">
                <span class="cc-meta">
                  <span class="mono cc-meta-id">{{ c.client_id }}</span>
                </span>
                <Button
                  size="sm"
                  icon="plus"
                  @click.stop="newTest(c.client_id)"
                >
                  test
                </Button>
              </div>
            </div>
          </Card>
        </div>
      </section>
    </main>

    <!-- Create client modal (reusada de ClientsListView) -->
    <div v-if="showCreate" class="modal-overlay" @click.self="showCreate = false">
      <div class="modal">
        <h3 class="serif">{{ $t('clients.createClient') }}</h3>

        <label class="field">
          <span class="label">{{ $t('clients.fields.name') }} *</span>
          <input v-model="form.name" type="text" :placeholder="$t('clients.fields.namePh')" />
        </label>

        <label class="field">
          <span class="label">{{ $t('clients.fields.industry') }}</span>
          <input v-model="form.industry" type="text" :placeholder="$t('clients.fields.industryPh')" />
        </label>

        <label class="field">
          <span class="label">{{ $t('clients.fields.description') }}</span>
          <textarea v-model="form.description" rows="2" :placeholder="$t('clients.fields.descriptionPh')" />
        </label>

        <label class="field">
          <span class="label">{{ $t('clients.fields.brandGuidelines') }}</span>
          <textarea v-model="form.brand_guidelines" rows="3" :placeholder="$t('clients.fields.brandGuidelinesPh')" />
        </label>

        <div v-if="createError" class="error-inline">{{ createError }}</div>

        <div class="modal-actions">
          <Button variant="ghost" @click="showCreate = false">{{ $t('common.cancel') }}</Button>
          <Button
            variant="primary"
            :disabled="!form.name || creating"
            @click="submit"
          >
            {{ creating ? $t('common.loading') : $t('common.confirm') }}
          </Button>
        </div>
      </div>
    </div>

    <CmdK :open="cmdK" :all-clients="clients" @close="cmdK = false" />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { checkClientsHealth, listClients, createClient } from '../api/clients'
import LoBuenoMark from '../components/ui/LoBuenoMark.vue'
import Button from '../components/ui/Button.vue'
import Card from '../components/ui/Card.vue'
import EmptyState from '../components/ui/EmptyState.vue'
import CmdK from '../components/shell/CmdK.vue'
import { useShortcuts } from '../composables/useShortcuts'

const router = useRouter()
const { locale } = useI18n()

const setLang = (l) => {
  locale.value = l
  localStorage.setItem('locale', l)
}

const healthLoading = ref(true)
const available = ref(false)
const loading = ref(true)
const clients = ref([])
const filter = ref('all')

const showCreate = ref(false)
const creating = ref(false)
const createError = ref('')
const form = reactive({
  name: '',
  industry: '',
  description: '',
  brand_guidelines: ''
})

const industries = computed(() => {
  const set = new Set()
  clients.value.forEach((c) => c.industry && set.add(c.industry))
  return ['all', ...Array.from(set)]
})

const filtered = computed(() =>
  filter.value === 'all'
    ? clients.value
    : clients.value.filter((c) => c.industry === filter.value)
)

const totalTests = computed(() => clients.value.reduce((s, c) => s + (c.tests || 0), 0))
const totalEpisodes = computed(() => clients.value.reduce((s, c) => s + (c.episodes || 0), 0))
const totalEntities = computed(() => clients.value.reduce((s, c) => s + (c.entities || 0), 0))

// First non-default client for the "Open UA" CTA in hero.
const firstClient = computed(() => clients.value.find((c) => !c.is_default) || clients.value[0])
const firstClientId = computed(() => firstClient.value?.client_id || '')
const firstClientName = computed(() => firstClient.value?.name || '')

// Deterministic accent per client based on slug → palette colour.
const PALETTE = ['#1f3a2e', '#6b3a52', '#d97706', '#2d5240', '#1a1814', '#a8650b', '#3d3a32', '#8b2a1f']
const accentFor = (c) => {
  if (c.metadata && typeof c.metadata.accent === 'string') return c.metadata.accent
  let h = 0
  const slug = c.slug || c.client_id || ''
  for (let i = 0; i < slug.length; i++) h = (h * 31 + slug.charCodeAt(i)) >>> 0
  return PALETTE[h % PALETTE.length]
}

const initialsFor = (c) => (c.name || '?').trim().charAt(0).toUpperCase()

const openClient = (id) => router.push(`/clients/${id}`)
const goToFirst = () => firstClientId.value && router.push(`/clients/${firstClientId.value}`)
const newTest = (id) => router.push(`/creative-test?client=${id}`)

const openCreate = () => {
  form.name = ''
  form.industry = ''
  form.description = ''
  form.brand_guidelines = ''
  createError.value = ''
  showCreate.value = true
}

const refresh = async () => {
  loading.value = true
  try {
    const res = await listClients(200, true)
    clients.value = res.data || []
  } catch {
    clients.value = []
  } finally {
    loading.value = false
  }
}

const submit = async () => {
  if (!form.name) return
  creating.value = true
  createError.value = ''
  try {
    const res = await createClient({
      name: form.name,
      industry: form.industry || null,
      description: form.description || null,
      brand_guidelines: form.brand_guidelines || null
    })
    showCreate.value = false
    if (res.data?.client_id) {
      router.push(`/clients/${res.data.client_id}`)
    } else {
      await refresh()
    }
  } catch (err) {
    createError.value = err?.response?.data?.error || err.message || 'Error'
  } finally {
    creating.value = false
  }
}

// Cmd+K + global shortcuts (G then C/M/H, ?, …)
const cmdK = ref(false)
useShortcuts({
  onCmdK: () => { cmdK.value = true },
  onEscape: () => { cmdK.value = false }
})

onMounted(async () => {
  try {
    const res = await checkClientsHealth()
    available.value = !!res?.data?.available
  } catch {
    available.value = false
  }
  healthLoading.value = false
  if (available.value) {
    await refresh()
  } else {
    loading.value = false
  }
})
</script>

<style scoped>
.home { min-height: 100vh; }

/* — top nav — */
.home-nav {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 32px;
  border-bottom: 1px solid var(--line);
  background: var(--surface);
}

.home-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: default;
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
.grow { flex: 1; }

.lang-btn {
  background: transparent;
  border: 1px solid var(--line);
  color: var(--ink-3);
  padding: 4px 10px;
  border-radius: var(--r-sm);
  cursor: pointer;
  font-family: var(--mono);
  font-size: 11px;
  letter-spacing: 0.08em;
}
.lang-btn.on { background: var(--ink); color: var(--bg); border-color: var(--ink); }

/* — main canvas — */
.home-main {
  max-width: 1180px;
  margin: 0 auto;
  padding: 36px 32px 80px;
}

/* — Hero — */
.hero {
  display: grid;
  grid-template-columns: 1.4fr 1fr;
  gap: 28px;
  margin-bottom: 36px;
}

.hero-sub {
  font-size: 16px;
  color: var(--ink-2);
  max-width: 560px;
  line-height: 1.55;
  margin: 14px 0 22px;
}

.hero-actions { display: flex; gap: 10px; flex-wrap: wrap; }

.hero-stats { padding: 0; overflow: hidden; }
.hero-stats-head { padding: 20px 22px; border-bottom: 1px solid var(--line); }
.hero-stats-title { font-size: 22px; margin-top: 6px; color: var(--ink); }

.hero-kpis {
  border: 0;
  border-radius: 0;
  grid-template-columns: 1fr 1fr;
}

/* — Section head — */
.clients-section { margin-top: 28px; }

/* — Grid — */
.grid-3 {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}
@media (max-width: 980px) {
  .grid-3 { grid-template-columns: repeat(2, 1fr); }
  .hero { grid-template-columns: 1fr; }
}
@media (max-width: 640px) {
  .grid-3 { grid-template-columns: 1fr; }
}

/* — Client card — */
.client-card {
  padding: 0 !important;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.cc-head {
  color: #fff;
  padding: 16px 18px;
  display: flex;
  align-items: center;
  gap: 12px;
  position: relative;
  min-height: 84px;
}

.cc-avatar {
  background: rgba(255, 255, 255, 0.15);
  color: #fff;
  border: 1px solid rgba(255, 255, 255, 0.25);
}

.cc-head-text { min-width: 0; flex: 1; padding-right: 28px; }
.cc-name {
  font-size: 19px;
  line-height: 1.15;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.cc-industry {
  font-size: 10.5px;
  opacity: 0.78;
  margin-top: 4px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.cc-slug {
  position: absolute;
  top: 14px;
  right: 16px;
  font-size: 10px;
  opacity: 0.7;
  letter-spacing: 0.15em;
}

.cc-body {
  padding: 18px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  flex: 1;
}

.cc-stats { display: flex; gap: 18px; }
.cc-stat { font-size: 22px; }

.cc-foot {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.cc-meta { font-size: 11px; color: var(--ink-3); }
.cc-meta-id { font-size: 10.5px; color: var(--ink-4); letter-spacing: 0.04em; }

/* — Skeleton — */
.skeleton .sk-head {
  height: 84px;
  background: var(--surface-3);
  border-bottom: 1px solid var(--line);
}
.skeleton .sk-body { padding: 18px; display: flex; flex-direction: column; gap: 12px; }
.skeleton .sk-line {
  height: 12px;
  background: var(--surface-3);
  border-radius: 4px;
  width: 100%;
}
.skeleton .sk-line.short { width: 60%; }
.skeleton {
  padding: 0 !important;
  animation: sk-pulse 1.4s ease-in-out infinite;
}
@keyframes sk-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.55; }
}

/* — Modal — */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(26, 24, 20, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: var(--z-modal);
}
.modal {
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: var(--r-lg);
  padding: 24px;
  width: 100%;
  max-width: 540px;
  box-shadow: var(--shadow-pop);
}
.modal h3 { margin: 0 0 16px; font-size: 20px; }

.field { display: flex; flex-direction: column; gap: 6px; margin-bottom: 14px; }
.field input,
.field textarea {
  border: 1px solid var(--line-2);
  border-radius: var(--r-sm);
  padding: 9px 11px;
  font-size: 14px;
  font-family: inherit;
  background: var(--surface);
  color: var(--ink);
}
.field input:focus,
.field textarea:focus { outline: none; border-color: var(--signal); }

.error-inline {
  color: var(--bad);
  background: var(--bad-soft);
  border: 1px solid var(--bad-soft);
  padding: 8px 12px;
  border-radius: var(--r-sm);
  font-size: 13px;
  margin: 8px 0;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 16px;
}
</style>
