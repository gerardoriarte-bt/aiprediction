<template>
  <div class="td fadein">
    <Breadcrumb :items="breadcrumb" />

    <div v-if="loading" class="state-loading">{{ $t('common.loading') }}</div>

    <div v-else-if="error" class="state-error">{{ error }}</div>

    <template v-else-if="test">
      <!-- Header -->
      <header class="td-head">
        <div class="td-head-left">
          <div class="eyebrow td-meta">
            <span class="mono">{{ test.test_id }}</span>
            <span class="sep">·</span>
            <span>{{ formatDate(test.created_at) }}</span>
            <span v-if="test.mode" class="sep">·</span>
            <span v-if="test.mode" :class="['td-mode', `td-mode--${test.mode}`]">
              ● {{ $t('creativeTest.modeBanner', { mode: test.mode }) }}
            </span>
          </div>
          <h1 class="h-display td-title">{{ businessGoal || $t('creativeTest.resultsTitle') }}</h1>
          <p class="td-sub">
            <span v-if="scenario">{{ scenario }}</span>
            <span v-if="scenario && audience" class="sep">·</span>
            <strong v-if="audience" class="td-audience">{{ audience }}</strong>
          </p>
        </div>
        <div class="td-head-actions">
          <Button icon="download" disabled>{{ $t('td.exportPdf') }}</Button>
          <Button icon="share" disabled>{{ $t('td.share') }}</Button>
          <Button
            v-if="winner"
            variant="signal"
            icon="play"
            disabled
          >
            {{ $t('td.runSimWithWinner', { label: winner.label }) }}
          </Button>
        </div>
      </header>

      <!-- Decision hero -->
      <Card v-if="winner" tone="dark" class="td-decision">
        <div class="td-decision-grid">
          <div class="td-dec-left">
            <div class="eyebrow">{{ $t('td.winner') }}</div>
            <div class="td-dec-row">
              <div class="td-winner-tile">{{ winner.label }}</div>
              <div class="td-winner-text">
                <div class="serif td-winner-headline">"{{ winner.headline || '—' }}"</div>
                <div class="td-winner-tags">
                  <Badge variant="signal">{{ $t(`creativeTest.reco.${recommendation}`) }}</Badge>
                  <Badge :variant="riskVariant(winner.risk_level)">
                    {{ $t(`creativeTest.risk.${winner.risk_level}`) }}
                  </Badge>
                </div>
              </div>
            </div>
          </div>
          <div class="td-dec-right">
            <div class="eyebrow">{{ $t('td.nextAction') }}</div>
            <p class="serif td-next">{{ nextAction || winner.rationale || '—' }}</p>
          </div>
        </div>
      </Card>

      <!-- Comparative: radar + ranking bars -->
      <div class="section-head">
        <div class="lt">
          <h2 class="h-1">{{ $t('td.compare') }}</h2>
        </div>
        <span class="ct">{{ $t('td.compareSub') }}</span>
      </div>
      <Card class="td-compare">
        <div class="td-compare-grid">
          <div class="td-radar-wrap">
            <RadarChart
              :axes="dimensionLabels"
              :variants="radarVariants"
              :size="320"
              :max="100"
            />
          </div>
          <div class="td-ranking">
            <div class="label">{{ $t('td.totalScore') }}</div>
            <div
              v-for="(v, i) in variants"
              :key="v.label"
              class="td-rank-row"
            >
              <div class="td-rank-head">
                <span
                  class="td-rank-dot"
                  :style="{ background: colorAt(i) }"
                ></span>
                <span class="serif td-rank-label">{{ v.label }}</span>
                <Badge v-if="v === winner" variant="solid">★</Badge>
                <span class="num mono td-rank-total">{{ v.total_score }}</span>
              </div>
              <ScoreBar
                :value="v.total_score"
                :max="400"
                :color="colorAt(i)"
              />
              <div class="td-rank-foot">
                <Badge :variant="recoVariant(v.recommendation)">
                  {{ $t(`creativeTest.reco.${v.recommendation}`) }}
                </Badge>
                <span class="td-rank-risk">
                  {{ $t(`creativeTest.risk.${v.risk_level}`) }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </Card>

      <!-- Variant scorecards -->
      <div class="section-head">
        <div class="lt">
          <h2 class="h-1">{{ $t('td.scorecards') }}</h2>
        </div>
      </div>
      <div class="td-cards-grid">
        <Card
          v-for="(v, i) in variants"
          :key="v.label"
          :class="['td-card', { 'td-card--winner': v === winner }]"
          :style="v === winner ? { borderColor: colorAt(i), borderWidth: '2px' } : {}"
        >
          <div class="td-card-head">
            <div class="td-card-tile" :style="{ background: colorAt(i) }">{{ v.label }}</div>
            <Badge v-if="v === winner" variant="signal">★ {{ $t('clients.creativeTests.winner') }}</Badge>
            <div class="grow"></div>
            <Badge :variant="recoVariant(v.recommendation)">
              {{ $t(`creativeTest.reco.${v.recommendation}`) }}
            </Badge>
          </div>
          <div class="td-card-body">
            <video
              v-if="v.video_url"
              :src="v.video_url"
              class="td-card-video"
              controls
              preload="metadata"
            ></video>
            <div
              v-else-if="(v.image_urls && v.image_urls.length) || v.image_url"
              class="td-card-assets"
              :class="{ 'is-carousel': (v.image_urls && v.image_urls.length > 1) }"
            >
              <img
                v-for="(src, si) in (v.image_urls && v.image_urls.length ? v.image_urls : [v.image_url])"
                :key="si"
                :src="src"
                class="td-card-asset"
                alt=""
              />
            </div>
            <p
              v-if="v.audio_transcript"
              class="td-card-transcript mono"
              :title="v.audio_transcript"
            >
              {{ truncate(v.audio_transcript, 200) }}
            </p>
            <p class="serif td-card-headline">"{{ v.headline || $t('td.headlinePlaceholder') }}"</p>
            <div class="hdiv"></div>
            <div
              v-for="dim in dimensionsFor(v)"
              :key="dim"
              class="td-card-dim"
            >
              <div class="td-card-dim-row">
                <span class="td-card-dim-label">{{ $t(`creativeTest.scoreDim.${dim}`) }}</span>
                <span class="num mono">{{ v.scores[dim] }}</span>
              </div>
              <ScoreBar :value="v.scores[dim]" :color="colorAt(i)" />
            </div>
            <div class="hdiv"></div>
            <div class="td-card-foot">
              <span class="td-card-risk">{{ $t(`creativeTest.risk.${v.risk_level}`) }}</span>
            </div>
          </div>
        </Card>
      </div>

      <!-- Evidence (accordion) -->
      <div v-if="hasEvidence" class="section-head">
        <div class="lt">
          <h2 class="h-1">{{ $t('td.evidence') }}</h2>
        </div>
      </div>
      <Card v-if="hasEvidence" class="td-evidence">
        <div
          v-for="(group, gi) in evidenceGroups"
          :key="group.key"
          class="td-ev-group"
          :class="{ 'first': gi === 0 }"
        >
          <button
            type="button"
            class="td-ev-toggle"
            @click="toggleEvidence(group.key)"
          >
            <Icon
              :name="openEvidence[group.key] ? 'chevron-d' : 'chevron-r'"
              :size="14"
            />
            <span class="serif td-ev-title">{{ group.title }}</span>
            <Badge>{{ group.facts.length }} {{ $t('td.facts') }}</Badge>
          </button>
          <ol v-if="openEvidence[group.key]" class="td-ev-list">
            <li
              v-for="(f, fi) in group.facts"
              :key="fi"
              class="td-ev-item"
            >
              <span class="num mono td-ev-num">{{ String(fi + 1).padStart(2, '0') }}</span>
              <div class="td-ev-content">
                <p class="td-ev-text">"{{ f.text || f }}"</p>
                <p v-if="f.source" class="mono td-ev-source">— {{ f.source }}</p>
              </div>
            </li>
          </ol>
        </div>
      </Card>

      <!-- Activation plan -->
      <div v-if="planEntries.length" class="section-head">
        <div class="lt">
          <h2 class="h-1">{{ $t('td.plan') }}</h2>
        </div>
      </div>
      <div v-if="planEntries.length" class="td-plan-grid">
        <Card
          v-for="entry in planEntries"
          :key="entry.key"
          class="td-plan-card"
        >
          <div class="td-plan-head">
            <span class="num mono td-plan-range">{{ entry.range }}</span>
            <span class="label">{{ entry.label }}</span>
          </div>
          <ul class="td-plan-list">
            <li v-for="(item, ii) in entry.items" :key="ii">
              <span class="td-plan-bullet"></span>
              <span>{{ item }}</span>
            </li>
          </ul>
        </Card>
      </div>

      <!-- Technical accordion -->
      <Card class="td-tech">
        <button
          type="button"
          class="td-tech-toggle"
          @click="techOpen = !techOpen"
        >
          <Icon :name="techOpen ? 'chevron-d' : 'chevron-r'" :size="14" />
          <span>{{ $t('td.tech') }}</span>
          <span class="mono td-tech-meta">
            test_id {{ test.test_id }}
            <template v-if="test.client_id"> · client {{ test.client_id }}</template>
          </span>
        </button>
        <div v-if="techOpen" class="td-tech-body">
          <div class="label">{{ $t('td.brief') }}</div>
          <pre class="mono td-tech-pre">{{ briefSnippet }}</pre>
        </div>
      </Card>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, reactive } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { getCreativeTest } from '../../api/creativeTest'
import Breadcrumb from '../../components/shell/Breadcrumb.vue'
import Card from '../../components/ui/Card.vue'
import Badge from '../../components/ui/Badge.vue'
import Button from '../../components/ui/Button.vue'
import Icon from '../../components/ui/Icon.vue'
import ScoreBar from '../../components/ui/ScoreBar.vue'
import RadarChart from '../../components/charts/RadarChart.vue'

const props = defineProps({
  client: { type: Object, required: true }
})

const { t, locale } = useI18n()
const route = useRoute()

const loading = ref(true)
const error = ref('')
const test = ref(null)

const techOpen = ref(false)
const openEvidence = reactive({ cc: true, b: true, c: false, ab: false })

const PALETTE = ['#1f3a2e', '#d97706', '#6b3a52', '#2d5240', '#a8650b']
const colorAt = (i) => PALETTE[i % PALETTE.length]

const dimensionKeys = [
  'message_clarity_score',
  'audience_fit_score',
  'conversion_intent_score',
  'brand_risk_score'
]

const VISUAL_DIM_KEYS = [
  'visual_composition_score',
  'visual_legibility_score',
  'visual_narrative_coherence_score',
  'video_pacing_score',
  'audio_message_alignment_score'
]

const truncate = (text, max) => {
  if (!text) return ''
  if (text.length <= max) return text
  return text.slice(0, max).replace(/\s+\S*$/, '') + '…'
}

// Per-variant: visual dims appear only when the variant carries them.
// visual_narrative_coherence_score appears only for carousel variants
// (the runner only emits it when 2+ slides were attached).
const dimensionsFor = (v) => {
  const base = [...dimensionKeys]
  for (const k of VISUAL_DIM_KEYS) {
    if (v && v.scores && v.scores[k] != null) base.push(k)
  }
  return base
}

const dimensionLabels = computed(() => dimensionKeys.map((k) => t(`creativeTest.scoreDim.${k}`)))

const breadcrumb = computed(() => [
  { label: t('side.clients'), to: '/' },
  { label: props.client.name, to: `/clients/${props.client.client_id}/overview` },
  { label: t('clients.tabs.creativeTests'), to: `/clients/${props.client.client_id}/tests` },
  { label: businessGoal.value || (test.value && test.value.test_id) || '…' }
])

// --- Derived from test record -----------------------------------------------

const result = computed(() => test.value?.result || {})
const summary = computed(() => result.value.summary || {})
const variants = computed(() => result.value.variants || [])
const ranking = computed(() => result.value.ranking || [])

const winner = computed(() => {
  const label = summary.value.winner_label
  if (!label) return variants.value[0] || null
  return variants.value.find((v) => v.label === label) || variants.value[0] || null
})

const recommendation = computed(() => summary.value.winner_recommendation || winner.value?.recommendation || 'iterate')

const radarVariants = computed(() =>
  variants.value.map((v, i) => ({
    id: v.label,
    color: colorAt(i),
    scores: dimensionKeys.map((k) => Number((v.scores || {})[k] || 0))
  }))
)

const businessGoal = computed(() => {
  if (test.value?.request?.business_goal) return test.value.request.business_goal
  return summary.value.business_goal || ''
})

const scenario = computed(() => test.value?.request?.scenario || '')

const audience = computed(() => {
  if (summary.value.audience) return summary.value.audience
  return test.value?.request?.audience_profile?.name || ''
})

const nextAction = computed(() => {
  const steps = result.value.next_steps
  if (Array.isArray(steps) && steps.length) return steps[0]
  return ''
})

const planEntries = computed(() => {
  const plan = result.value.plan || test.value?.request?.plan || {}
  const entries = []
  const map = {
    d7: { range: '0–7d',   label: t('td.planImmediate') },
    d30:{ range: '30d',    label: t('td.planMeasure') },
    d90:{ range: '60–90d', label: t('td.planDecide') }
  }
  for (const k of ['d7', 'd30', 'd90']) {
    const items = plan[k]
    if (Array.isArray(items) && items.length) {
      entries.push({
        key: k,
        range: map[k].range,
        label: map[k].label,
        items: items.map((it) => (typeof it === 'string' ? it : it.text || it[locale.value] || JSON.stringify(it)))
      })
    }
  }
  return entries
})

const evidenceGroups = computed(() => {
  // Groups assembled in display order:
  //  - "Client context"    : facts pulled from the client knowledge graph (R3.1)
  //  - "Why <winner> won"  : winner.evidence
  //  - "Why <last> failed" : last variant if reco === 'discard'
  const groups = []

  // R3.1 — surface the client-context facts the runner used to bias
  // the prediction (top-level result.client_context_facts).
  const clientFacts = result.value?.client_context_facts || []
  if (Array.isArray(clientFacts) && clientFacts.length) {
    groups.push({
      key: 'cc',
      title: t('td.evClientContext'),
      facts: clientFacts.map((f) =>
        typeof f === 'string'
          ? { text: f, source: t('td.evClientContextSource') }
          : { text: f.finding || f.text, source: f.segment || f.source || t('td.evClientContextSource') }
      )
    })
  }

  if (winner.value?.evidence?.length) {
    groups.push({
      key: 'b',
      title: t('td.evWinner', { label: winner.value.label }),
      facts: winner.value.evidence.map((e) =>
        typeof e === 'string'
          ? { text: e }
          : { text: e.finding || e.text, source: e.segment || e.source }
      )
    })
  }
  const discarded = variants.value.find((v) => v.recommendation === 'discard' && v !== winner.value)
  if (discarded?.evidence?.length) {
    groups.push({
      key: 'c',
      title: t('td.evDiscarded', { label: discarded.label }),
      facts: discarded.evidence.map((e) =>
        typeof e === 'string'
          ? { text: e }
          : { text: e.finding || e.text, source: e.segment || e.source }
      )
    })
  }
  return groups
})

const hasEvidence = computed(() => evidenceGroups.value.length > 0)

const briefSnippet = computed(() => {
  const req = test.value?.request || {}
  const audienceName = req.audience_profile?.name || ''
  const lines = [
    `business_goal: ${req.business_goal || '-'}`,
    `scenario: ${req.scenario || '-'}`,
    `audience: ${audienceName || '-'}`,
    `channels: ${(req.channels || []).join(', ') || '-'}`,
    `success_metrics: ${(req.success_metrics || [])
      .map((m) => (typeof m === 'string' ? m : m.name))
      .join(', ') || '-'}`,
    `variants: ${(req.creative_variants || []).length}`
  ]
  return lines.join('\n')
})

const recoVariant = (r) => (r === 'activate' ? 'ok' : r === 'discard' ? 'bad' : 'warn')
const riskVariant = (l) => (l === 'low' ? 'ok' : l === 'high' ? 'bad' : 'warn')

const formatDate = (iso) => {
  if (!iso) return ''
  try {
    return new Date(iso).toLocaleString(locale.value === 'es' ? 'es-MX' : 'en-US', {
      dateStyle: 'medium',
      timeStyle: 'short'
    })
  } catch {
    return iso
  }
}

const toggleEvidence = (key) => {
  openEvidence[key] = !openEvidence[key]
}

const fetchTest = async () => {
  loading.value = true
  error.value = ''
  try {
    const res = await getCreativeTest(route.params.testId)
    test.value = res.data || null
  } catch (err) {
    error.value = err?.response?.data?.error || err.message || 'Error'
    test.value = null
  } finally {
    loading.value = false
  }
}

onMounted(fetchTest)
watch(() => route.params.testId, (id) => id && fetchTest())
</script>

<style scoped>
.state-loading,
.state-error {
  padding: 32px;
  text-align: center;
  color: var(--ink-3);
  background: var(--surface-2);
  border: 1px dashed var(--line);
  border-radius: var(--r);
}
.state-error { color: var(--bad); border-color: var(--bad-soft); background: var(--bad-soft); }

/* Header */
.td-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 22px;
}
.td-head-left { min-width: 0; flex: 1; }
.td-meta {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
}
.td-meta .sep { color: var(--ink-5); }
.td-mode {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.td-mode--mock { color: var(--warn); }
.td-mode--live { color: var(--ok); }

.td-title { margin: 8px 0 6px; }
.td-sub {
  margin: 0;
  font-size: 14px;
  color: var(--ink-2);
  line-height: 1.5;
}
.td-sub .sep { margin: 0 6px; color: var(--ink-5); }
.td-audience { font-weight: 500; color: var(--ink); }

.td-head-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

/* Decision hero */
.td-decision {
  margin-bottom: 24px;
  padding: 0 !important;
  overflow: hidden;
}
.td-decision-grid {
  display: grid;
  grid-template-columns: 1.5fr 1fr;
  min-height: 0;
}
.td-dec-left {
  padding: 32px 36px;
}
.td-dec-right {
  padding: 32px 36px;
  border-left: 1px solid rgba(255, 255, 255, 0.10);
  background: rgba(255, 255, 255, 0.03);
}
@media (max-width: 800px) {
  .td-decision-grid { grid-template-columns: 1fr; }
  .td-dec-right { border-left: 0; border-top: 1px solid rgba(255, 255, 255, 0.10); }
}

.td-dec-row {
  display: flex;
  align-items: center;
  gap: 18px;
  flex-wrap: wrap;
  margin-top: 12px;
}

.td-winner-tile {
  width: 64px;
  height: 64px;
  border-radius: 14px;
  background: var(--signal);
  color: white;
  display: grid;
  place-items: center;
  font-family: var(--serif);
  font-size: 38px;
  flex-shrink: 0;
}

.td-winner-text { min-width: 0; flex: 1; }
.td-winner-headline {
  font-size: 24px;
  line-height: 1.18;
  color: var(--bg);
}
.td-winner-tags {
  margin-top: 10px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.td-next {
  margin: 12px 0 0;
  font-size: 19px;
  line-height: 1.4;
  color: var(--bg);
}

/* Comparative card */
.td-compare { margin-bottom: 22px; }

.td-compare-grid {
  display: grid;
  grid-template-columns: 1.1fr 1fr;
  gap: 32px;
  align-items: center;
}
@media (max-width: 800px) {
  .td-compare-grid { grid-template-columns: 1fr; }
  .td-radar-wrap { display: flex; justify-content: center; }
}

.td-radar-wrap { display: flex; align-items: center; justify-content: center; }

.td-ranking { display: flex; flex-direction: column; gap: 14px; }
.td-rank-row + .td-rank-row { padding-top: 14px; border-top: 1px dashed var(--line); }

.td-rank-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}
.td-rank-dot {
  width: 12px;
  height: 12px;
  border-radius: 3px;
  flex-shrink: 0;
}
.td-rank-label { font-size: 17px; }
.td-rank-total {
  margin-left: auto;
  font-size: 13px;
  color: var(--ink-2);
}

.td-rank-foot {
  display: flex;
  justify-content: space-between;
  margin-top: 6px;
  font-size: 11px;
  color: var(--ink-3);
}
.td-rank-risk { letter-spacing: 0.04em; }

/* Scorecards */
.td-cards-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
  margin-bottom: 22px;
}
@media (max-width: 920px) {
  .td-cards-grid { grid-template-columns: 1fr 1fr; }
}
@media (max-width: 600px) {
  .td-cards-grid { grid-template-columns: 1fr; }
}

.td-card { padding: 0 !important; overflow: hidden; }
.td-card-head {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 18px;
  border-bottom: 1px solid var(--line);
}
.grow { flex: 1; }
.td-card-tile {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  color: white;
  display: grid;
  place-items: center;
  font-family: var(--serif);
  font-size: 18px;
  flex-shrink: 0;
}
.td-card-body { padding: 18px; }
.td-card-assets {
  margin-bottom: 14px;
}
.td-card-assets .td-card-asset {
  display: block;
  width: 100%;
  height: 180px;
  object-fit: cover;
  border-radius: var(--r);
  border: 1px solid var(--line);
  background: var(--surface-2);
}
.td-card-assets.is-carousel {
  display: flex;
  gap: 6px;
  overflow-x: auto;
  scroll-snap-type: x mandatory;
  padding-bottom: 4px;
}
.td-card-assets.is-carousel .td-card-asset {
  flex: 0 0 auto;
  width: 70%;
  scroll-snap-align: start;
}
.td-card-video {
  display: block;
  width: 100%;
  max-height: 220px;
  background: #000;
  border-radius: var(--r);
  border: 1px solid var(--line);
  margin-bottom: 14px;
}
.td-card-transcript {
  margin: 0 0 14px;
  padding: 10px 12px;
  background: var(--surface-2);
  border-left: 3px solid var(--accent, var(--ink-3));
  border-radius: 4px;
  font-size: 12px;
  color: var(--ink-2);
  line-height: 1.5;
  cursor: help;
}
.td-card-headline {
  font-size: 17px;
  line-height: 1.28;
  min-height: 50px;
  margin: 0;
}
.td-card-dim { margin-bottom: 10px; }
.td-card-dim-row {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  margin-bottom: 4px;
  color: var(--ink-3);
}
.td-card-dim-label { color: var(--ink-3); }
.td-card-foot {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.td-card-risk { font-size: 11px; color: var(--ink-3); letter-spacing: 0.05em; }
.td-card--winner { box-shadow: var(--shadow-2); }

/* Evidence */
.td-evidence { padding: 0 !important; margin-bottom: 22px; }
.td-ev-group { border-top: 1px solid var(--line); }
.td-ev-group.first { border-top: 0; }

.td-ev-toggle {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 16px 22px;
  background: transparent;
  border: 0;
  cursor: pointer;
  text-align: left;
  font-family: inherit;
  color: var(--ink);
}
.td-ev-toggle:hover { background: var(--surface-2); }

.td-ev-title { font-size: 17px; flex: 1; }

.td-ev-list {
  list-style: none;
  margin: 0;
  padding: 0 22px 22px 50px;
}
.td-ev-item {
  display: flex;
  gap: 14px;
  padding: 10px 0;
  border-top: 1px dashed var(--line);
}
.td-ev-item:first-child { border-top: 0; }
.td-ev-num {
  color: var(--ink-4);
  font-size: 11px;
  width: 20px;
  flex-shrink: 0;
}
.td-ev-content { flex: 1; min-width: 0; }
.td-ev-text {
  font-size: 14px;
  line-height: 1.55;
  font-style: italic;
  margin: 0;
  color: var(--ink-2);
}
.td-ev-source {
  font-size: 11px;
  color: var(--ink-4);
  margin: 4px 0 0;
}

/* Plan */
.td-plan-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
  margin-bottom: 22px;
}
@media (max-width: 760px) { .td-plan-grid { grid-template-columns: 1fr; } }

.td-plan-head {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 4px;
}
.td-plan-range {
  font-size: 13px;
  color: var(--signal);
  letter-spacing: 0.05em;
}
.td-plan-list {
  list-style: none;
  margin: 10px 0 0;
  padding: 0;
}
.td-plan-list li {
  display: flex;
  gap: 10px;
  padding: 8px 0;
  border-top: 1px dashed var(--line);
  font-size: 13px;
  line-height: 1.5;
}
.td-plan-list li:first-child { border-top: 0; }
.td-plan-bullet {
  width: 6px;
  height: 6px;
  margin-top: 7px;
  background: var(--ink);
  border-radius: 1px;
  flex-shrink: 0;
}

/* Tech accordion */
.td-tech { padding: 0 !important; }
.td-tech-toggle {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 22px;
  background: transparent;
  border: 0;
  cursor: pointer;
  width: 100%;
  text-align: left;
  font-size: 13px;
  color: var(--ink-3);
  font-family: inherit;
}
.td-tech-toggle:hover { background: var(--surface-2); }
.td-tech-meta {
  font-size: 11px;
  color: var(--ink-4);
  margin-left: auto;
}
.td-tech-body {
  padding: 0 22px 22px;
  border-top: 1px solid var(--line);
  font-size: 12px;
  color: var(--ink-3);
  line-height: 1.7;
}
.td-tech-pre {
  background: var(--surface-2);
  padding: 12px;
  border-radius: var(--r-sm);
  margin-top: 6px;
  white-space: pre-wrap;
  font-size: 11.5px;
}
</style>
