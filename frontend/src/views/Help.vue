<template>
  <div class="help">
    <TopNav :all-clients="allClients" @open-cmd-k="cmdK = true" />

    <main id="main" class="help-main" tabindex="-1">
      <header class="help-hero">
        <div class="eyebrow">{{ $t('side.help') }}</div>
        <h1>{{ $t('help.heroTitle') }}</h1>
        <p class="lead">{{ $t('help.heroSub') }}</p>
        <div class="hero-actions">
          <Button variant="primary" icon="search" @click="cmdK = true">
            {{ $t('topnav.search') }}
            <span class="kbd ml">⌘K</span>
          </Button>
          <router-link to="/manual" class="link">
            {{ $t('help.openManual') }} →
          </router-link>
        </div>
      </header>

      <section v-for="g in groups" :key="g.key" class="help-section">
        <h2 class="h-1">{{ g.title }}</h2>
        <table class="kbd-table">
          <tbody>
            <tr v-for="(row, i) in g.items" :key="i">
              <td class="kbd-cell">
                <code v-for="(k, ki) in row.keys" :key="ki" class="kbd">{{ k }}</code>
                <span v-if="row.combine" class="combine">{{ row.combine }}</span>
              </td>
              <td>{{ row.action }}</td>
            </tr>
          </tbody>
        </table>
      </section>
    </main>

    <CmdK :open="cmdK" :all-clients="allClients" @close="cmdK = false" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import TopNav from '../components/shell/TopNav.vue'
import CmdK from '../components/shell/CmdK.vue'
import Button from '../components/ui/Button.vue'
import { listClients } from '../api/clients'
import { useShortcuts } from '../composables/useShortcuts'

const { t, locale } = useI18n()
const allClients = ref([])
const cmdK = ref(false)

useShortcuts({
  onCmdK: () => { cmdK.value = true },
  onEscape: () => { cmdK.value = false }
})

onMounted(async () => {
  try {
    const res = await listClients(200, false)
    allClients.value = res.data || []
  } catch {
    allClients.value = []
  }
})

const ES = {
  global: 'Global',
  nav: 'Navegación',
  client: 'Dentro de un cliente',
  globalRows: [
    { keys: ['⌘', 'K'], action: 'Abrir búsqueda global (clientes, tests, manual)' },
    { keys: ['Esc'], action: 'Cerrar modal o panel abierto' },
    { keys: ['?'], action: 'Abrir esta página' }
  ],
  navRows: [
    { keys: ['G'], combine: 'luego', actionKeys: ['C'], action: 'Ir a Clientes' },
    { keys: ['G'], combine: 'luego', actionKeys: ['M'], action: 'Ir al Manual' },
    { keys: ['G'], combine: 'luego', actionKeys: ['H'], action: 'Ir a Atajos' }
  ],
  clientRows: [
    { keys: ['G'], combine: 'luego', actionKeys: ['O'], action: 'Resumen del cliente' },
    { keys: ['G'], combine: 'luego', actionKeys: ['X'], action: 'Brand context' },
    { keys: ['G'], combine: 'luego', actionKeys: ['T'], action: 'Creative tests' },
    { keys: ['N'], action: 'Crear nuevo (contextual)' }
  ]
}
const EN = {
  global: 'Global',
  nav: 'Navigation',
  client: 'Within a client',
  globalRows: [
    { keys: ['⌘', 'K'], action: 'Open global search (clients, tests, manual)' },
    { keys: ['Esc'], action: 'Close any open modal or pane' },
    { keys: ['?'], action: 'Open this page' }
  ],
  navRows: [
    { keys: ['G'], combine: 'then', actionKeys: ['C'], action: 'Go to Clients' },
    { keys: ['G'], combine: 'then', actionKeys: ['M'], action: 'Go to Manual' },
    { keys: ['G'], combine: 'then', actionKeys: ['H'], action: 'Go to Shortcuts' }
  ],
  clientRows: [
    { keys: ['G'], combine: 'then', actionKeys: ['O'], action: 'Client overview' },
    { keys: ['G'], combine: 'then', actionKeys: ['X'], action: 'Brand context' },
    { keys: ['G'], combine: 'then', actionKeys: ['T'], action: 'Creative tests' },
    { keys: ['N'], action: 'Create new (contextual)' }
  ]
}

const data = computed(() => (locale.value === 'en' ? EN : ES))

const groups = computed(() => {
  // Flatten "G then X" rows by appending the second key visually.
  const flatten = (rows) =>
    rows.map((r) => {
      if (r.actionKeys) {
        return { keys: [...r.keys, ...r.actionKeys], combine: r.combine, action: r.action }
      }
      return { keys: r.keys, combine: r.combine, action: r.action }
    })
  return [
    { key: 'global', title: data.value.global, items: flatten(data.value.globalRows) },
    { key: 'nav',    title: data.value.nav,    items: flatten(data.value.navRows) },
    { key: 'client', title: data.value.client, items: flatten(data.value.clientRows) }
  ]
})
</script>

<style scoped>
.help { min-height: 100vh; }
.help-main {
  max-width: 880px;
  margin: 0 auto;
  padding: 36px 32px 80px;
}
.help-hero { margin-bottom: 28px; }
.help-hero h1 {
  font-family: var(--serif);
  font-size: 32px;
  margin: 8px 0 6px;
}
.help-hero .lead { font-size: 15px; color: var(--ink-2); max-width: 600px; }
.hero-actions {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-top: 16px;
}
.hero-actions .link {
  color: var(--ink-3);
  text-decoration: none;
  font-size: 13px;
}
.hero-actions .link:hover { color: var(--ink); }
.ml { margin-left: 6px; }

.help-section + .help-section { margin-top: 32px; }

.kbd-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 12px;
}
.kbd-table td {
  padding: 10px 12px;
  border-bottom: 1px solid var(--line);
  font-size: 14px;
  color: var(--ink-2);
}
.kbd-table tr:last-child td { border-bottom: 0; }
.kbd-cell { width: 200px; }
.combine {
  font-family: var(--mono);
  font-size: 11px;
  color: var(--ink-4);
  margin: 0 6px;
}
</style>
