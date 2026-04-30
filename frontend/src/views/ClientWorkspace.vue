<template>
  <div class="ws">
    <TopNav
      :active-client="client"
      :all-clients="allClients"
      @open-cmd-k="cmdK = true"
    />

    <div v-if="loading" class="ws-loading">{{ $t('common.loading') }}</div>

    <div v-else-if="error" class="ws-error">{{ error }}</div>

    <div v-else-if="!client" class="ws-error">
      {{ $t('clients.notFound', { id: $route.params.clientId }) }}
    </div>

    <div v-else class="ws-body">
      <Sidebar :client-id="client.client_id" :stats="stats" />

      <main id="main" class="ws-content" tabindex="-1">
        <router-view
          :client="client"
          :stats="stats"
          @client-updated="onClientUpdated"
          @stats-updated="onStatsUpdated"
        />
      </main>
    </div>

    <CmdK :open="cmdK" :all-clients="allClients" @close="cmdK = false" />
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import TopNav from '../components/shell/TopNav.vue'
import Sidebar from '../components/shell/Sidebar.vue'
import CmdK from '../components/shell/CmdK.vue'
import { getClient, listClients } from '../api/clients'
import { useShortcuts } from '../composables/useShortcuts'

const route = useRoute()

const loading = ref(true)
const error = ref('')
const client = ref(null)
const allClients = ref([])
const stats = ref({ tests: 0, episodes: 0, entities: 0, edges: 0, reports: 0, sims: 0 })

const refresh = async (id) => {
  loading.value = true
  error.value = ''
  try {
    const [cRes, listRes] = await Promise.all([
      getClient(id),
      listClients(200, true)
    ])
    client.value = cRes.data || null
    allClients.value = listRes.data || []
    // Derive stats from the with_stats list (1 round-trip serves the
    // sidebar counters + the client switcher).
    const fromList = (listRes.data || []).find((c) => c.client_id === id)
    if (fromList) {
      stats.value = {
        tests: fromList.tests || 0,
        episodes: fromList.episodes || 0,
        entities: fromList.entities || 0,
        edges: fromList.edges || 0,
        reports: fromList.reports || 0,
        sims: fromList.sims || 0
      }
    }
  } catch (err) {
    error.value = err?.response?.data?.error || err.message || 'Error'
    client.value = null
  } finally {
    loading.value = false
  }
}

const onClientUpdated = (next) => {
  if (next) client.value = next
}
const onStatsUpdated = (patch) => {
  stats.value = { ...stats.value, ...(patch || {}) }
}

// Cmd+K + global shortcuts (G then letter)
const cmdK = ref(false)
useShortcuts({
  onCmdK: () => { cmdK.value = true },
  onEscape: () => { cmdK.value = false }
})

onMounted(() => refresh(route.params.clientId))
watch(
  () => route.params.clientId,
  (id) => id && refresh(id)
)
</script>

<style scoped>
.ws {
  min-height: 100vh;
  background: var(--bg);
  display: flex;
  flex-direction: column;
}

.ws-body {
  display: flex;
  flex: 1;
  align-items: stretch;
  min-height: 0;
}

.ws-content {
  flex: 1;
  min-width: 0;
  padding: 32px 32px 64px;
  max-width: 1180px;
  margin: 0 auto;
  width: 100%;
}

.ws-loading,
.ws-error {
  padding: 48px;
  text-align: center;
  color: var(--ink-3);
}
.ws-error { color: var(--bad); }

@media (max-width: 900px) {
  .ws-body { flex-direction: column; }
  .ws-content { padding: 20px 16px 48px; }
}
</style>
