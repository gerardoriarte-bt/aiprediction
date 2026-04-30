<template>
  <div class="gf fadein">
    <Breadcrumb :items="breadcrumb" />

    <header class="gf-head">
      <div>
        <div class="eyebrow">{{ $t('clients.graph.fullscreenEyebrow') }}</div>
        <h1 class="h-1 gf-title">
          {{ client.name }} · {{ $t('clients.graph.knowledgeTitle') }}
        </h1>
      </div>
      <Button
        variant="ghost"
        icon="arrow-l"
        size="sm"
        @click="$router.push(`/clients/${client.client_id}/context`)"
      >
        {{ $t('common.back') }}
      </Button>
    </header>

    <div v-if="loading" class="gf-loading">{{ $t('common.loading') }}</div>

    <div v-else-if="!graphData?.nodes?.length" class="gf-empty">
      <EmptyState
        :title="$t('clients.graph.bootstrapTitle')"
        :hint="$t('clients.graph.bootstrapDesc')"
      >
        <Button
          variant="signal"
          icon="upload"
          @click="$router.push(`/clients/${client.client_id}/context`)"
        >
          {{ $t('ov.action.context') }}
        </Button>
      </EmptyState>
    </div>

    <div v-else class="gf-shell">
      <Card class="gf-card">
        <!-- Toolbar -->
        <div class="gf-toolbar">
          <div class="gf-search">
            <Icon name="search" :size="14" />
            <input
              v-model="query"
              type="text"
              :placeholder="$t('clients.graph.searchInGraph')"
            />
          </div>
          <div class="gf-toolbar-spacer"></div>
          <span class="gf-totals mono">
            {{ graphData.totals.nodes }} {{ $t('clients.graph.nodes') }}
            · {{ graphData.totals.edges }} {{ $t('clients.graph.edges') }}
          </span>
        </div>

        <!-- Legend -->
        <div class="gf-legend">
          <GraphLegend
            :counts="graphData.type_counts"
            :filter="filter"
            @toggle="toggleType"
          />
        </div>

        <div class="gf-canvas-row">
          <div class="gf-canvas-wrap">
            <GraphCanvas
              :data="graphData"
              :width="canvasW"
              :height="canvasH"
              :filter-types="filter"
              :query="query"
              :selected-id="selected?.id || ''"
              @select="onSelect"
            />
          </div>

          <aside class="gf-detail">
            <div v-if="!selected" class="gf-detail-empty">
              <p>{{ $t('clients.graph.selectHint') }}</p>
            </div>
            <div v-else>
              <div class="gf-detail-head">
                <span class="gf-detail-dot" :style="{ background: typeColor(selected.type) }"></span>
                <span class="mono gf-detail-type">{{ selected.type }}</span>
              </div>
              <h3 class="serif gf-detail-name">{{ selected.label }}</h3>
              <p v-if="selected.summary" class="gf-detail-summary">{{ selected.summary }}</p>

              <div class="gf-detail-stats">
                <div>
                  <span class="label">{{ $t('clients.graph.degree') }}</span>
                  <span class="num gf-detail-num">{{ selected.weight }}</span>
                </div>
              </div>

              <div v-if="neighbours.length">
                <div class="label gf-detail-section">{{ $t('clients.graph.neighbours') }}</div>
                <ul class="gf-nbr-list">
                  <li
                    v-for="n in neighbours.slice(0, 8)"
                    :key="n.id"
                    @click="selectId(n.id)"
                  >
                    <span class="dot" :style="{ background: typeColor(n.type) }"></span>
                    <span>{{ n.label }}</span>
                    <span class="mono gf-nbr-rel">{{ n.relation }}</span>
                  </li>
                </ul>
                <p v-if="neighbours.length > 8" class="gf-nbr-more mono">
                  +{{ neighbours.length - 8 }} {{ $t('common.more') }}
                </p>
              </div>
            </div>
          </aside>
        </div>
      </Card>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, reactive } from 'vue'
import { useI18n } from 'vue-i18n'
import { getClientGraphData } from '../../api/clients'
import Breadcrumb from '../../components/shell/Breadcrumb.vue'
import Card from '../../components/ui/Card.vue'
import Button from '../../components/ui/Button.vue'
import Icon from '../../components/ui/Icon.vue'
import EmptyState from '../../components/ui/EmptyState.vue'
import GraphCanvas from '../../components/graph/GraphCanvas.vue'
import GraphLegend from '../../components/graph/GraphLegend.vue'

const props = defineProps({
  client: { type: Object, required: true }
})

const { t } = useI18n()

const TYPE_COLORS = {
  Brand:        '#1f3a2e',
  Audience:     '#2d5240',
  Channel:      '#d97706',
  Claim:        '#6b3a52',
  Competitor:   '#8b2a1f',
  Study:        '#3d3a32',
  Metric:       '#a8650b',
  Risk:         '#b91c1c',
  Person:       '#475569',
  Organization: '#1a1814',
  Product:      '#1f3a2e',
  Entity:       '#9a9686'
}
const typeColor = (t) => TYPE_COLORS[t] || TYPE_COLORS.Entity

const loading = ref(true)
const graphData = ref(null)
const filter = reactive({})
const query = ref('')
const selected = ref(null)

const canvasW = ref(900)
const canvasH = ref(560)

const breadcrumb = computed(() => [
  { label: t('side.clients'), to: '/' },
  { label: props.client.name, to: `/clients/${props.client.client_id}/overview` },
  { label: t('clients.tabs.context'), to: `/clients/${props.client.client_id}/context` },
  { label: t('clients.graph.knowledgeTitle') }
])

const refresh = async () => {
  loading.value = true
  try {
    const res = await getClientGraphData(props.client.client_id)
    graphData.value = res.data
    Object.keys(graphData.value.type_counts || {}).forEach((k) => {
      if (filter[k] === undefined) filter[k] = true
    })
  } catch {
    graphData.value = { nodes: [], edges: [], totals: { nodes: 0, edges: 0 }, type_counts: {} }
  } finally {
    loading.value = false
  }
}

const toggleType = (key) => {
  filter[key] = filter[key] === false ? true : false
}

const onSelect = (n) => { selected.value = n }
const selectId = (id) => {
  const n = (graphData.value?.nodes || []).find((x) => x.id === id)
  if (n) selected.value = n
}

const neighbours = computed(() => {
  if (!selected.value || !graphData.value) return []
  const id = selected.value.id
  const ids = []
  for (const e of graphData.value.edges) {
    const sid = typeof e.source === 'object' ? e.source.id : e.source
    const tid = typeof e.target === 'object' ? e.target.id : e.target
    if (sid === id) ids.push({ id: tid, relation: e.name })
    else if (tid === id) ids.push({ id: sid, relation: e.name })
  }
  return ids
    .map(({ id, relation }) => {
      const n = graphData.value.nodes.find((x) => x.id === id)
      return n ? { ...n, relation } : null
    })
    .filter(Boolean)
})

onMounted(refresh)
watch(() => props.client.client_id, refresh)
</script>

<style scoped>
.gf { padding-top: 0; }

.gf-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 18px;
}

.gf-title {
  margin: 4px 0 0;
  font-weight: 400;
}

.gf-loading,
.gf-empty {
  padding: 48px 24px;
  text-align: center;
  color: var(--ink-3);
}

.gf-card { padding: 0 !important; overflow: hidden; }

.gf-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 18px;
  border-bottom: 1px solid var(--line);
  background: var(--surface-2);
}

.gf-search {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: var(--r-sm);
  padding: 6px 10px;
  flex: 1;
  max-width: 380px;
  color: var(--ink-3);
}
.gf-search input {
  border: 0;
  outline: 0;
  background: transparent;
  flex: 1;
  font-family: inherit;
  font-size: 13px;
  color: var(--ink);
}

.gf-toolbar-spacer { flex: 1; }
.gf-totals {
  font-size: 11px;
  color: var(--ink-4);
  letter-spacing: 0.04em;
}

.gf-legend {
  padding: 12px 18px;
  border-bottom: 1px solid var(--line);
}

.gf-canvas-row {
  display: grid;
  grid-template-columns: 1fr 280px;
  min-height: 560px;
}

@media (max-width: 900px) {
  .gf-canvas-row { grid-template-columns: 1fr; }
}

.gf-canvas-wrap {
  position: relative;
  min-height: 560px;
}

.gf-detail {
  border-left: 1px solid var(--line);
  background: var(--surface);
  padding: 18px 20px;
  overflow-y: auto;
}
@media (max-width: 900px) {
  .gf-detail { border-left: 0; border-top: 1px solid var(--line); }
}

.gf-detail-empty {
  color: var(--ink-3);
  font-size: 13px;
  line-height: 1.5;
}

.gf-detail-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.gf-detail-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}
.gf-detail-type {
  font-size: 10.5px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--ink-3);
}

.gf-detail-name {
  font-size: 22px;
  margin: 0 0 8px;
  line-height: 1.2;
}

.gf-detail-summary {
  font-size: 13px;
  color: var(--ink-2);
  line-height: 1.5;
  margin: 0 0 14px;
}

.gf-detail-stats {
  display: flex;
  gap: 16px;
  margin-bottom: 14px;
}
.gf-detail-stats > div {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.gf-detail-num { font-family: var(--serif); font-size: 22px; }

.gf-detail-section {
  margin: 14px 0 6px;
}

.gf-nbr-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.gf-nbr-list li {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  background: var(--surface-2);
  border-radius: var(--r-sm);
  cursor: pointer;
  font-size: 12px;
}
.gf-nbr-list li:hover { background: var(--surface-3); }
.gf-nbr-list .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.gf-nbr-rel {
  margin-left: auto;
  font-size: 10px;
  color: var(--ink-4);
  letter-spacing: 0.04em;
}

.gf-nbr-more {
  margin: 8px 0 0;
  font-size: 11px;
  color: var(--ink-4);
}
</style>
