<template>
  <div class="ct fadein">
    <Breadcrumb :items="breadcrumb" />

    <header class="ct-head">
      <div>
        <div class="eyebrow">{{ $t('clients.tabs.context') }}</div>
        <h1 class="h-1 ct-title">{{ $t('clients.contextHelper') }}</h1>
      </div>
    </header>

    <!-- Brand fact card (read-only for R2.3, editable in R2.7) -->
    <Card class="ct-brand">
      <div class="kv">
        <div class="kv-row">
          <span class="label">{{ $t('clients.fields.description') }}</span>
          <p class="kv-value">{{ client.description || $t('common.none') }}</p>
        </div>
        <div class="kv-row">
          <span class="label">{{ $t('clients.fields.brandGuidelines') }}</span>
          <p class="kv-value">{{ client.brand_guidelines || $t('common.none') }}</p>
        </div>
      </div>
    </Card>

    <!-- Bootstrap CTA when there is no graph yet -->
    <Card v-if="!client.graph_id" class="ct-bootstrap" tone="tonal">
      <h2 class="h-1">{{ $t('clients.graph.bootstrapTitle') }}</h2>
      <p>{{ $t('clients.graph.bootstrapDesc') }}</p>
      <Button
        variant="signal"
        icon="spark"
        :disabled="bootstrapping"
        @click="bootstrap"
      >
        {{ bootstrapping ? $t('common.loading') : $t('clients.graph.bootstrapBtn') }}
      </Button>
      <p v-if="bootstrapError" class="error-inline">{{ bootstrapError }}</p>
    </Card>

    <!-- Graph state with totals + ingest + search + episodes -->
    <template v-else>
      <Card class="ct-stats-card" tone="tonal">
        <div class="kpi-row">
          <div class="kpi">
            <div class="k">{{ $t('clients.graph.episodes') }}</div>
            <div class="v num">{{ contextSummary?.totals?.episodes ?? 0 }}</div>
          </div>
          <div class="kpi">
            <div class="k">{{ $t('clients.graph.chunks') }}</div>
            <div class="v num">{{ contextSummary?.totals?.chunks ?? 0 }}</div>
          </div>
          <div class="kpi">
            <div class="k">{{ $t('clients.graph.nodes') }}</div>
            <div class="v num">{{ contextSummary?.totals?.nodes ?? 0 }}</div>
          </div>
          <div class="kpi">
            <div class="k">{{ $t('clients.graph.edges') }}</div>
            <div class="v num">{{ contextSummary?.totals?.edges ?? 0 }}</div>
          </div>
        </div>
      </Card>

      <!-- Knowledge graph (mini) -->
      <section
        v-if="(contextSummary?.totals?.nodes ?? 0) > 0"
        class="ct-section"
      >
        <div class="section-head">
          <div class="lt">
            <h2 class="h-1">{{ $t('clients.graph.knowledgeTitle') }}</h2>
            <span class="ct-count">
              {{ contextSummary.totals.nodes }} · {{ contextSummary.totals.edges }}
            </span>
          </div>
          <Button
            size="sm"
            icon="expand"
            @click="$router.push(`/clients/${client.client_id}/graph`)"
          >
            {{ $t('clients.graph.openFullscreen') }}
          </Button>
        </div>
        <Card class="ct-graph-card">
          <div class="ct-graph-grid">
            <div class="ct-graph-mini">
              <GraphCanvas
                v-if="graphData"
                :data="graphData"
                :width="540"
                :height="280"
                mini
              />
            </div>
            <div class="ct-graph-side">
              <GraphLegend :counts="graphData?.type_counts || {}" />
              <p class="ct-graph-hint">{{ $t('clients.graph.miniHint') }}</p>
            </div>
          </div>
        </Card>
      </section>

      <!-- File upload -->
      <section class="ct-section">
        <div class="section-head">
          <div class="lt">
            <h2 class="h-1">{{ $t('clients.graph.uploadTitle') }}</h2>
          </div>
          <router-link to="/guide" class="ct-guide-link">
            <Icon name="help" :size="13" />
            <span>{{ $t('clients.graph.openGuide') }}</span>
          </router-link>
        </div>
        <p class="ct-helper">{{ $t('clients.graph.uploadHelper') }}</p>
        <Card>
          <div
            class="dropzone"
            :class="{ over: dragOver, busy: uploading }"
            @dragover.prevent="dragOver = true"
            @dragleave.prevent="dragOver = false"
            @drop.prevent="onDrop"
            @click="!uploading && $refs.fileInput.click()"
          >
            <input
              ref="fileInput"
              type="file"
              multiple
              accept=".pdf,.md,.markdown,.txt"
              class="visually-hidden"
              @change="onFilesSelected"
            />
            <p v-if="!pendingFiles.length">{{ $t('clients.graph.dropzoneEmpty') }}</p>
            <ul v-else class="files">
              <li v-for="(f, i) in pendingFiles" :key="i">
                <span class="fname">{{ f.name }}</span>
                <span class="fsize mono">{{ humanSize(f.size) }}</span>
                <button
                  type="button"
                  class="remove-btn"
                  @click.stop="removePending(i)"
                  :disabled="uploading"
                >×</button>
              </li>
            </ul>
          </div>
          <div class="row-actions">
            <Button
              variant="primary"
              icon="upload"
              :disabled="!pendingFiles.length || uploading"
              @click="uploadFiles"
            >
              {{ uploading ? $t('clients.graph.uploading') : $t('clients.graph.uploadBtn') }}
            </Button>
            <span v-if="uploadSummary" class="success-pill">{{ uploadSummary }}</span>
            <span v-if="uploadError" class="error-inline">{{ uploadError }}</span>
          </div>
          <ul v-if="lastUploadResults.length" class="upload-results">
            <li
              v-for="(r, i) in lastUploadResults"
              :key="i"
              :class="{ err: !r.success }"
            >
              <strong>{{ r.filename }}</strong>
              <span v-if="r.success">
                · {{ r.chunk_count }} chunks · {{ (r.stats || {}).entities_upserted || 0 }} entities · {{ (r.stats || {}).edges_inserted || 0 }} edges
              </span>
              <span v-else>· {{ r.error }}</span>
            </li>
          </ul>
        </Card>
      </section>

      <!-- Paste text -->
      <section class="ct-section">
        <div class="section-head">
          <div class="lt">
            <h2 class="h-1">{{ $t('clients.graph.addContextTitle') }}</h2>
          </div>
        </div>
        <p class="ct-helper">{{ $t('clients.graph.addContextHelper') }}</p>
        <Card>
          <div class="field">
            <input
              v-model="ingestSource"
              type="text"
              :placeholder="$t('clients.graph.sourcePlaceholder')"
            />
          </div>
          <div class="field">
            <textarea
              v-model="ingestText"
              rows="6"
              :placeholder="$t('clients.graph.textPlaceholder')"
            ></textarea>
          </div>
          <div class="row-actions">
            <Button
              variant="primary"
              icon="plus"
              :disabled="!ingestText || ingesting"
              @click="ingest"
            >
              {{ ingesting ? $t('clients.graph.ingesting') : $t('clients.graph.ingestBtn') }}
            </Button>
            <span v-if="lastIngestSummary" class="success-pill">{{ lastIngestSummary }}</span>
            <span v-if="ingestError" class="error-inline">{{ ingestError }}</span>
          </div>
        </Card>
      </section>

      <!-- Search -->
      <section class="ct-section">
        <div class="section-head">
          <div class="lt">
            <h2 class="h-1">{{ $t('clients.graph.searchTitle') }}</h2>
          </div>
        </div>
        <p class="ct-helper">{{ $t('clients.graph.searchHelper') }}</p>
        <Card>
          <div class="search-row">
            <input
              v-model="searchQuery"
              type="text"
              class="search-input"
              :placeholder="$t('clients.graph.searchPlaceholder')"
              @keyup.enter="runSearch"
            />
            <Button
              variant="primary"
              icon="search"
              :disabled="!searchQuery || searching"
              @click="runSearch"
            >
              {{ searching ? $t('common.loading') : $t('clients.graph.searchBtn') }}
            </Button>
          </div>
          <div v-if="searchError" class="error-inline">{{ searchError }}</div>
          <div v-else-if="searchResult" class="search-results">
            <p class="ct-helper">
              {{ $t('clients.graph.searchResults', { count: searchResult.total_count }) }}
            </p>
            <ul v-if="searchResult.facts.length" class="facts-list">
              <li v-for="(f, i) in searchResult.facts" :key="i">{{ f }}</li>
            </ul>
          </div>
        </Card>
      </section>

      <!-- Episode list -->
      <section v-if="contextSummary?.episodes?.length" class="ct-section">
        <div class="section-head">
          <div class="lt">
            <h2 class="h-1">{{ $t('clients.graph.episodesTitle') }}</h2>
            <span class="ct-count">{{ contextSummary.episodes.length }}</span>
          </div>
        </div>
        <Card>
          <ul class="ep-list">
            <li
              v-for="ep in contextSummary.episodes"
              :key="ep.episode_id"
              class="ep-row"
            >
              <div>
                <strong class="mono">#{{ ep.episode_id }}</strong>
                <Badge :variant="statusVariant(ep.status)">{{ ep.status }}</Badge>
                <span v-if="ep.source" class="ep-source mono">{{ ep.source }}</span>
              </div>
              <span class="ep-date mono">{{ ep.created_at }}</span>
            </li>
          </ul>
        </Card>
      </section>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  bootstrapClientGraph,
  ingestClientContext,
  listClientContext,
  searchClientGraph,
  uploadClientContext,
  getClientGraphData
} from '../../api/clients'
import Breadcrumb from '../../components/shell/Breadcrumb.vue'
import Card from '../../components/ui/Card.vue'
import Button from '../../components/ui/Button.vue'
import Badge from '../../components/ui/Badge.vue'
import Icon from '../../components/ui/Icon.vue'
import GraphCanvas from '../../components/graph/GraphCanvas.vue'
import GraphLegend from '../../components/graph/GraphLegend.vue'

const props = defineProps({
  client: { type: Object, required: true }
})
const emit = defineEmits(['client-updated', 'stats-updated'])

const { t } = useI18n()

const breadcrumb = computed(() => [
  { label: t('side.clients'), to: '/' },
  { label: props.client.name, to: `/clients/${props.client.client_id}/overview` },
  { label: t('clients.tabs.context') }
])

// Bootstrap state
const bootstrapping = ref(false)
const bootstrapError = ref('')

// Ingest state
const ingestSource = ref('')
const ingestText = ref('')
const ingesting = ref(false)
const ingestError = ref('')
const lastIngestSummary = ref('')

// Context summary (totals + episodes)
const contextSummary = ref(null)

// Graph data for the mini canvas in the context tab
const graphData = ref(null)
const fetchGraphData = async () => {
  try {
    const res = await getClientGraphData(props.client.client_id)
    graphData.value = res.data
  } catch {
    graphData.value = null
  }
}

// Search state
const searchQuery = ref('')
const searching = ref(false)
const searchError = ref('')
const searchResult = ref(null)

// Upload state
const ALLOWED_EXTS = ['.pdf', '.md', '.markdown', '.txt']
const pendingFiles = ref([])
const dragOver = ref(false)
const uploading = ref(false)
const uploadError = ref('')
const uploadSummary = ref('')
const lastUploadResults = ref([])

const humanSize = (bytes) => {
  if (!bytes && bytes !== 0) return ''
  const units = ['B', 'KB', 'MB', 'GB']
  let i = 0
  let size = bytes
  while (size >= 1024 && i < units.length - 1) {
    size /= 1024
    i++
  }
  return `${size.toFixed(size < 10 && i > 0 ? 1 : 0)} ${units[i]}`
}

const filterAccepted = (files) =>
  Array.from(files).filter((f) => {
    const dot = f.name.lastIndexOf('.')
    const ext = dot >= 0 ? f.name.slice(dot).toLowerCase() : ''
    return ALLOWED_EXTS.includes(ext)
  })

const onFilesSelected = (e) => {
  pendingFiles.value = pendingFiles.value.concat(filterAccepted(e.target.files || []))
  e.target.value = ''
}

const onDrop = (e) => {
  dragOver.value = false
  if (uploading.value) return
  pendingFiles.value = pendingFiles.value.concat(filterAccepted(e.dataTransfer?.files || []))
}

const removePending = (idx) => pendingFiles.value.splice(idx, 1)

const statusVariant = (s) => (s === 'processed' ? 'ok' : s === 'processing' ? 'warn' : 'default')

const refreshContext = async () => {
  try {
    const res = await listClientContext(props.client.client_id)
    contextSummary.value = res.data
    emit('stats-updated', {
      episodes: res.data?.totals?.episodes || 0,
      entities: res.data?.totals?.nodes || 0,
      edges: res.data?.totals?.edges || 0
    })
    if ((res.data?.totals?.nodes || 0) > 0) {
      await fetchGraphData()
    } else {
      graphData.value = null
    }
  } catch {
    contextSummary.value = null
  }
}

const bootstrap = async () => {
  bootstrapping.value = true
  bootstrapError.value = ''
  try {
    const res = await bootstrapClientGraph(props.client.client_id)
    emit('client-updated', res.data)
    await refreshContext()
  } catch (err) {
    bootstrapError.value = err?.response?.data?.error || err.message || 'Error'
  } finally {
    bootstrapping.value = false
  }
}

const ingest = async () => {
  if (!ingestText.value) return
  ingesting.value = true
  ingestError.value = ''
  lastIngestSummary.value = ''
  try {
    const res = await ingestClientContext(props.client.client_id, {
      text: ingestText.value,
      source: ingestSource.value || null
    })
    const data = res.data || {}
    const stats = data.stats || {}
    lastIngestSummary.value = `+${data.chunk_count || 0} chunks · ${stats.entities_upserted || 0} entities · ${stats.edges_inserted || 0} edges`
    ingestText.value = ''
    ingestSource.value = ''
    await refreshContext()
  } catch (err) {
    ingestError.value = err?.response?.data?.error || err.message || 'Error'
  } finally {
    ingesting.value = false
  }
}

const uploadFiles = async () => {
  if (!pendingFiles.value.length) return
  uploading.value = true
  uploadError.value = ''
  uploadSummary.value = ''
  lastUploadResults.value = []
  try {
    const res = await uploadClientContext(props.client.client_id, pendingFiles.value)
    const data = res.data || {}
    lastUploadResults.value = data.files || []
    uploadSummary.value = `${data.succeeded || 0}/${data.uploaded || 0} files ingested`
    pendingFiles.value = []
    await refreshContext()
  } catch (err) {
    uploadError.value = err?.response?.data?.error || err.message || 'Error'
  } finally {
    uploading.value = false
  }
}

const runSearch = async () => {
  if (!searchQuery.value) return
  searching.value = true
  searchError.value = ''
  searchResult.value = null
  try {
    const res = await searchClientGraph(props.client.client_id, searchQuery.value, 10)
    searchResult.value = res.data
  } catch (err) {
    searchError.value = err?.response?.data?.error || err.message || 'Error'
  } finally {
    searching.value = false
  }
}

const init = async () => {
  if (props.client.graph_id) await refreshContext()
}
onMounted(init)
watch(() => props.client.graph_id, init)
</script>

<style scoped>
.ct-head { margin-bottom: 22px; }
.ct-title { margin: 4px 0 0; font-weight: 400; }

.ct-brand { margin-bottom: 18px; }

.kv-row { margin-bottom: 14px; }
.kv-row:last-child { margin-bottom: 0; }
.kv-value { margin: 4px 0 0; color: var(--ink); white-space: pre-wrap; line-height: 1.55; }

.ct-bootstrap { margin-bottom: 22px; text-align: center; }
.ct-bootstrap h2 { margin: 0 0 6px; }
.ct-bootstrap p { color: var(--ink-2); margin: 0 0 14px; max-width: 520px; margin-inline: auto; }

.ct-stats-card { padding: 0 !important; margin-bottom: 24px; overflow: hidden; }
.ct-stats-card .kpi-row { border: 0; border-radius: 0; }

.ct-section { margin-bottom: 24px; }

.ct-guide-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border: 1px solid var(--line);
  border-radius: 999px;
  font-size: 12px;
  color: var(--ink-2);
  text-decoration: none;
  background: var(--surface);
  transition: background 0.12s, border-color 0.12s, color 0.12s;
}
.ct-guide-link:hover {
  background: var(--surface-2);
  border-color: var(--line-2);
  color: var(--ink);
}

.ct-helper {
  margin: 0 0 12px;
  color: var(--ink-3);
  font-size: 13px;
}

.ct-count {
  font-family: var(--mono);
  font-size: 11px;
  color: var(--ink-4);
}

/* — Dropzone — */
.dropzone {
  border: 2px dashed var(--line-2);
  border-radius: var(--r);
  padding: 18px;
  text-align: center;
  cursor: pointer;
  background: var(--surface-2);
  transition: border-color 0.12s, background 0.12s;
  min-height: 72px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.dropzone:hover { border-color: var(--signal); background: var(--surface-3); }
.dropzone.over { border-color: var(--signal); background: var(--signal-soft); }
.dropzone.busy { opacity: 0.6; cursor: progress; }
.dropzone p { margin: 0; color: var(--ink-3); font-size: 13px; }

.visually-hidden { display: none; }

.files {
  list-style: none;
  margin: 0;
  padding: 0;
  width: 100%;
  text-align: left;
}
.files li {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 4px 0;
  font-size: 13px;
}
.fname {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.fsize { color: var(--ink-4); font-size: 11px; }

.remove-btn {
  background: none;
  border: none;
  color: var(--ink-3);
  cursor: pointer;
  font-size: 16px;
  padding: 0 4px;
  line-height: 1;
}
.remove-btn:hover { color: var(--bad); }
.remove-btn:disabled { color: var(--ink-5); cursor: not-allowed; }

.row-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 12px;
  flex-wrap: wrap;
}

.success-pill {
  color: var(--ok);
  background: var(--ok-soft);
  border: 1px solid var(--ok-soft);
  padding: 4px 10px;
  border-radius: var(--r-sm);
  font-size: 12px;
}

.error-inline {
  color: var(--bad);
  background: var(--bad-soft);
  border: 1px solid var(--bad-soft);
  padding: 4px 10px;
  border-radius: var(--r-sm);
  font-size: 12px;
}

.upload-results {
  list-style: none;
  padding: 0;
  margin: 14px 0 0;
  font-size: 12px;
}
.upload-results li {
  padding: 6px 10px;
  background: var(--ok-soft);
  color: var(--ok);
  border-left: 3px solid var(--ok);
  border-radius: var(--r-xs);
  margin-bottom: 4px;
}
.upload-results li.err {
  background: var(--bad-soft);
  color: var(--bad);
  border-left-color: var(--bad);
}

/* — Forms — */
.field { margin-bottom: 10px; }
.field input,
.field textarea {
  width: 100%;
  border: 1px solid var(--line-2);
  border-radius: var(--r-sm);
  padding: 9px 11px;
  font-family: inherit;
  font-size: 14px;
  background: var(--surface);
  color: var(--ink);
  box-sizing: border-box;
}
.field input:focus,
.field textarea:focus { outline: none; border-color: var(--signal); }

.search-row { display: flex; gap: 8px; align-items: stretch; }
.search-input {
  flex: 1;
  border: 1px solid var(--line-2);
  border-radius: var(--r-sm);
  padding: 9px 11px;
  font-family: inherit;
  font-size: 14px;
  background: var(--surface);
  color: var(--ink);
}
.search-input:focus { outline: none; border-color: var(--signal); }

.facts-list {
  margin: 8px 0 0;
  padding-left: 20px;
  font-size: 13px;
  color: var(--ink-2);
}
.facts-list li { padding: 4px 0; }

.search-results { margin-top: 4px; }

/* — Episodes list — */
.ep-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.ep-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: var(--surface-2);
  border-radius: var(--r-sm);
  font-size: 13px;
}
.ep-row strong {
  color: var(--ink-2);
  margin-right: 8px;
  font-size: 12px;
}
.ep-source {
  color: var(--ink-3);
  font-size: 11px;
  margin-left: 6px;
}
.ep-date {
  color: var(--ink-4);
  font-size: 11px;
}

/* — Knowledge graph card — */
.ct-graph-card { padding: 0 !important; overflow: hidden; }
.ct-graph-grid {
  display: grid;
  grid-template-columns: 1.6fr 1fr;
  align-items: stretch;
  min-height: 280px;
}
@media (max-width: 800px) {
  .ct-graph-grid { grid-template-columns: 1fr; }
}
.ct-graph-mini {
  height: 280px;
  border-right: 1px solid var(--line);
}
@media (max-width: 800px) {
  .ct-graph-mini { border-right: 0; border-bottom: 1px solid var(--line); }
}
.ct-graph-side {
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.ct-graph-hint {
  margin: auto 0 0;
  color: var(--ink-3);
  font-size: 12px;
  line-height: 1.5;
}
</style>
