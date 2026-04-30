<template>
  <div class="st fadein">
    <Breadcrumb :items="breadcrumb" />

    <header class="st-head">
      <div>
        <div class="eyebrow">{{ $t('clients.tabs.simulations') }}</div>
        <h1 class="h-1 st-title">{{ $t('clients.simulationsHelper') }}</h1>
      </div>
      <Button
        variant="primary"
        icon="plus"
        @click="showLauncher = !showLauncher"
      >
        {{ $t('clients.simulations.newCta') }}
      </Button>
    </header>

    <Card v-if="showLauncher" tone="tonal" class="launcher">
      <div class="lf">
        <label class="lf-label">{{ $t('clients.simulations.requirementLabel') }}</label>
        <textarea
          v-model="requirement"
          class="lf-textarea mono"
          rows="3"
          :placeholder="$t('clients.simulations.requirementPh')"
        ></textarea>
      </div>

      <div class="lf">
        <label class="lf-label">{{ $t('clients.simulations.filesLabel') }}</label>
        <div
          class="lf-drop"
          :class="{ 'is-over': dragOver }"
          @dragover.prevent="dragOver = true"
          @dragleave="dragOver = false"
          @drop.prevent="onDrop"
          @click="$refs.fileInput.click()"
        >
          <input
            ref="fileInput"
            type="file"
            multiple
            accept=".pdf,.txt,.md,.docx"
            style="display:none"
            @change="onPick"
          />
          <span v-if="!files.length">{{ $t('clients.simulations.dropzone') }}</span>
          <ul v-else class="lf-files mono">
            <li v-for="(f, i) in files" :key="i">{{ f.name }} <span class="dim">({{ formatBytes(f.size) }})</span></li>
          </ul>
        </div>
      </div>

      <div class="lf-actions">
        <Button variant="ghost" @click="resetLauncher">
          {{ $t('common.cancel') }}
        </Button>
        <Button
          variant="signal"
          icon="play"
          :disabled="!canLaunch"
          @click="launch"
        >
          {{ $t('clients.simulations.launch') }}
        </Button>
      </div>
    </Card>

    <div v-if="loading" class="state-loading">{{ $t('common.loading') }}</div>

    <EmptyState
      v-else-if="!sims.length"
      :title="$t('clients.simulations.empty')"
    />

    <ul v-else class="rows">
      <li
        v-for="s in sims"
        :key="s.simulation_id"
        class="row"
        @click="openSim(s.simulation_id)"
      >
        <div class="row-main">
          <div class="line1">
            <strong class="serif row-title">{{ s.simulation_id }}</strong>
            <Badge :variant="statusVariant(s.status)">{{ s.status }}</Badge>
          </div>
          <div class="line2 mono">
            <span v-if="s.entities_count != null">
              {{ s.entities_count }} {{ $t('clients.simulations.entities') }}
            </span>
            <span v-if="s.profiles_count != null" class="sep">·</span>
            <span v-if="s.profiles_count != null">
              {{ s.profiles_count }} {{ $t('clients.simulations.profiles') }}
            </span>
            <span class="sep">·</span>
            <span class="dim">{{ s.project_id }}</span>
            <span v-if="s.created_at" class="sep">·</span>
            <span v-if="s.created_at" class="dim">{{ formatDate(s.created_at) }}</span>
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
import { listClientSimulations } from '../../api/clients'
import { setPendingUpload } from '../../store/pendingUpload'
import Breadcrumb from '../../components/shell/Breadcrumb.vue'
import Badge from '../../components/ui/Badge.vue'
import Button from '../../components/ui/Button.vue'
import Card from '../../components/ui/Card.vue'
import Icon from '../../components/ui/Icon.vue'
import EmptyState from '../../components/ui/EmptyState.vue'

const props = defineProps({
  client: { type: Object, required: true }
})

const { t } = useI18n()
const router = useRouter()

const sims = ref([])
const loading = ref(false)

const showLauncher = ref(false)
const requirement = ref('')
const files = ref([])
const dragOver = ref(false)

const breadcrumb = computed(() => [
  { label: t('side.clients'), to: '/' },
  { label: props.client.name, to: `/clients/${props.client.client_id}/overview` },
  { label: t('clients.tabs.simulations') }
])

const canLaunch = computed(() => !!requirement.value.trim() && files.value.length > 0)

const openSim = (id) => router.push(`/simulation/${id}`)

const statusVariant = (s) =>
  s === 'completed' ? 'ok'
  : s === 'failed' ? 'bad'
  : (s === 'running' || s === 'preparing') ? 'warn'
  : 'default'

const formatDate = (iso) => {
  if (!iso) return ''
  try {
    return new Date(iso).toISOString().slice(0, 16).replace('T', ' ')
  } catch {
    return iso
  }
}

const formatBytes = (n) => {
  if (n == null) return ''
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / 1024 / 1024).toFixed(1)} MB`
}

const onPick = (e) => {
  files.value = Array.from(e.target.files || [])
}

const onDrop = (e) => {
  dragOver.value = false
  files.value = Array.from(e.dataTransfer?.files || [])
}

const resetLauncher = () => {
  showLauncher.value = false
  requirement.value = ''
  files.value = []
}

const launch = () => {
  if (!canLaunch.value) return
  setPendingUpload(files.value, requirement.value.trim(), props.client.client_id)
  router.push({ name: 'Process', params: { projectId: 'new' } })
}

const refresh = async () => {
  loading.value = true
  try {
    const res = await listClientSimulations(props.client.client_id)
    sims.value = res.data || []
  } catch {
    sims.value = []
  } finally {
    loading.value = false
  }
}

onMounted(refresh)
watch(() => props.client.client_id, refresh)
</script>

<style scoped>
.st-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 22px;
}
.st-title { margin: 4px 0 0; font-weight: 400; }

.launcher {
  margin-bottom: 18px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.lf-label {
  display: block;
  font-size: 11px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--ink-3);
  margin-bottom: 6px;
}
.lf-textarea {
  width: 100%;
  border: 1px solid var(--line);
  border-radius: var(--r);
  background: var(--surface);
  padding: 10px 12px;
  font-size: 13px;
  resize: vertical;
  color: var(--ink);
}
.lf-textarea:focus {
  outline: none;
  border-color: var(--ink-3);
}
.lf-drop {
  border: 1px dashed var(--line-2);
  background: var(--surface);
  border-radius: var(--r);
  padding: 18px;
  text-align: center;
  cursor: pointer;
  font-size: 13px;
  color: var(--ink-3);
  transition: border-color 0.12s, background 0.12s;
}
.lf-drop.is-over { border-color: var(--accent, var(--ink-2)); background: var(--surface-2); }
.lf-files {
  list-style: none;
  margin: 0;
  padding: 0;
  text-align: left;
  font-size: 12px;
  color: var(--ink);
}
.lf-files li { padding: 2px 0; }
.lf-files .dim { color: var(--ink-4); }
.lf-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

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
