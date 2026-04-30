<template>
  <div class="rt fadein">
    <Breadcrumb :items="breadcrumb" />

    <header class="rt-head">
      <div>
        <div class="eyebrow">{{ $t('clients.tabs.reports') }}</div>
        <h1 class="h-1 rt-title">{{ $t('clients.reportsHelper') }}</h1>
      </div>
    </header>

    <div v-if="loading" class="state-loading">{{ $t('common.loading') }}</div>

    <EmptyState
      v-else-if="!reports.length"
      :title="$t('clients.reports.empty')"
    />

    <ul v-else class="rows">
      <li
        v-for="r in reports"
        :key="r.report_id"
        class="row"
        @click="openReport(r.report_id)"
      >
        <div class="row-main">
          <div class="line1">
            <strong class="serif row-title">
              {{ r.title || $t('clients.reports.untitled') }}
            </strong>
            <Badge :variant="statusVariant(r.status)">{{ r.status }}</Badge>
          </div>
          <div class="line2 mono">
            <span class="dim">{{ r.report_id }}</span>
            <span v-if="r.simulation_id" class="sep">·</span>
            <span v-if="r.simulation_id" class="dim">{{ r.simulation_id }}</span>
            <span v-if="r.completed_at || r.created_at" class="sep">·</span>
            <span v-if="r.completed_at || r.created_at" class="dim">
              {{ formatDate(r.completed_at || r.created_at) }}
            </span>
          </div>
        </div>
        <Icon name="chevron-r" :size="16" />
      </li>
    </ul>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { listClientReports } from '../../api/clients'
import Breadcrumb from '../../components/shell/Breadcrumb.vue'
import Badge from '../../components/ui/Badge.vue'
import Icon from '../../components/ui/Icon.vue'
import EmptyState from '../../components/ui/EmptyState.vue'

const props = defineProps({
  client: { type: Object, required: true }
})

const { t } = useI18n()
const router = useRouter()

const reports = ref([])
const loading = ref(false)

const breadcrumb = computed(() => [
  { label: t('side.clients'), to: '/' },
  { label: props.client.name, to: `/clients/${props.client.client_id}/overview` },
  { label: t('clients.tabs.reports') }
])

const openReport = (id) => {
  if (id) router.push(`/report/${id}`)
}

const statusVariant = (s) =>
  s === 'completed' ? 'ok'
  : s === 'failed' ? 'bad'
  : (s === 'running' || s === 'generating') ? 'warn'
  : 'default'

const formatDate = (iso) => {
  if (!iso) return ''
  try {
    return new Date(iso).toISOString().slice(0, 16).replace('T', ' ')
  } catch {
    return iso
  }
}

const refresh = async () => {
  loading.value = true
  try {
    const res = await listClientReports(props.client.client_id)
    reports.value = res.data || []
  } catch {
    reports.value = []
  } finally {
    loading.value = false
  }
}

onMounted(refresh)
watch(() => props.client.client_id, refresh)
</script>

<style scoped>
.rt-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 22px;
}
.rt-title { margin: 4px 0 0; font-weight: 400; }

.state-loading {
  padding: 24px;
  background: var(--surface-2);
  border: 1px dashed var(--line);
  border-radius: var(--r);
  color: var(--ink-3);
  text-align: center;
  font-size: 13px;
}

.rows {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  border: 1px solid var(--line);
  background: var(--surface);
  border-radius: var(--r);
  cursor: pointer;
  transition: background 0.12s, border-color 0.12s;
}
.row:hover { background: var(--surface-2); border-color: var(--line-2); }

.row-main { flex: 1; min-width: 0; }

.line1 {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  font-size: 15px;
}
.row-title { font-weight: 500; color: var(--ink); }

.line2 {
  margin-top: 4px;
  font-size: 11px;
  color: var(--ink-3);
  letter-spacing: 0.04em;
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.line2 .sep { color: var(--ink-5); }
.line2 .dim { color: var(--ink-4); }
</style>
