<template>
  <div class="ct-container">
    <header class="ct-header">
      <button class="ct-back" @click="goBackToClient">← {{ clientInfo ? clientInfo.name : $t('common.back') }}</button>
      <h1>{{ $t('creativeTest.title') }}</h1>
      <p class="ct-subtitle">
        <template v-if="clientInfo">
          {{ $t('creativeTest.forClient', { name: clientInfo.name }) }}
        </template>
        <template v-else>
          {{ $t('creativeTest.subtitle') }}
        </template>
      </p>
      <div v-if="enabled && healthInfo" class="ct-mode-banner" :class="`ct-mode-banner--${healthInfo.mode}`">
        <span class="ct-mode-dot"></span>
        {{ $t('creativeTest.modeBanner', { mode: healthInfo.mode }) }}
      </div>
    </header>

    <div v-if="healthLoading" class="ct-state">{{ $t('common.loading') }}</div>

    <div v-else-if="!enabled" class="ct-disabled">
      <h2>{{ $t('creativeTest.disabledTitle') }}</h2>
      <p>{{ $t('creativeTest.disabledDesc') }}</p>
      <code>CREATIVE_TESTING_ENABLED=true</code>
    </div>

    <div v-else-if="!clientId" class="ct-disabled">
      <h2>{{ $t('creativeTest.requireClientTitle') }}</h2>
      <p>{{ $t('creativeTest.requireClientDesc') }}</p>
      <button class="ct-submit" @click="$router.push('/clients')">
        {{ $t('clients.allClients') }} →
      </button>
    </div>

    <div v-else class="ct-body">
      <!-- Phase 1: Brief -->
      <section v-if="phase === 'brief'" class="ct-card">
        <h2>{{ $t('creativeTest.briefTitle') }}</h2>

        <label class="ct-field">
          <span>
            {{ $t('creativeTest.businessGoal') }} *
            <HelpHint :text="$t('creativeTest.help.businessGoal')" />
          </span>
          <textarea v-model="form.business_goal" rows="2" :placeholder="$t('creativeTest.businessGoalPh')" />
        </label>

        <label class="ct-field">
          <span>
            {{ $t('creativeTest.scenario') }} *
            <HelpHint :text="$t('creativeTest.help.scenario')" />
          </span>
          <textarea v-model="form.scenario" rows="2" :placeholder="$t('creativeTest.scenarioPh')" />
        </label>

        <fieldset class="ct-fieldset">
          <legend>
            {{ $t('creativeTest.audience') }} *
            <HelpHint :text="$t('creativeTest.help.audience')" />
          </legend>
          <div class="ct-grid-2">
            <label class="ct-field">
              <span>{{ $t('creativeTest.audienceName') }}</span>
              <input v-model="form.audience.name" type="text" :placeholder="$t('creativeTest.audienceNamePh')" />
            </label>
            <label class="ct-field">
              <span>{{ $t('creativeTest.audienceCountry') }}</span>
              <input v-model="form.audience.country" type="text" placeholder="MX" />
            </label>
            <label class="ct-field">
              <span>{{ $t('creativeTest.audiencePrimaryChannel') }}</span>
              <input v-model="form.audience.primary_channel" type="text" placeholder="Instagram" />
            </label>
            <label class="ct-field">
              <span>{{ $t('creativeTest.audienceAge') }}</span>
              <input v-model="form.audience.age_range" type="text" placeholder="25-34" />
            </label>
          </div>
        </fieldset>

        <fieldset class="ct-fieldset">
          <legend>
            {{ $t('creativeTest.variants') }} *
            <HelpHint :text="$t('creativeTest.help.variants')" />
          </legend>
          <div v-for="(v, idx) in form.variants" :key="idx" class="ct-variant">
            <div class="ct-variant-head">
              <strong>{{ v.label }}</strong>
              <button class="ct-link" type="button" @click="removeVariant(idx)" :disabled="form.variants.length <= 2">
                {{ $t('creativeTest.removeVariant') }}
              </button>
            </div>
            <label class="ct-field">
              <span>{{ $t('creativeTest.headline') }} *</span>
              <input v-model="v.headline" type="text" :placeholder="$t('creativeTest.headlinePh')" />
            </label>
            <div class="ct-grid-2">
              <label class="ct-field">
                <span>{{ $t('creativeTest.cta') }}</span>
                <input v-model="v.cta" type="text" />
              </label>
              <label class="ct-field">
                <span>{{ $t('creativeTest.tone') }}</span>
                <input v-model="v.tone" type="text" />
              </label>
            </div>
            <div class="ct-image">
              <label class="ct-image-label">
                <span>{{ $t('creativeTest.imageOptional') }}</span>
                <span class="ct-image-hint">{{ $t('creativeTest.imageHint') }}</span>
              </label>
              <div class="ct-image-row">
                <div
                  v-for="(p, i) in variantImagePreviews[v.label] || []"
                  :key="i"
                  class="ct-image-thumb"
                >
                  <img :src="p" alt="" />
                  <button
                    type="button"
                    class="ct-image-remove"
                    :title="$t('creativeTest.removeImage')"
                    @click="removeSlide(v.label, i)"
                  >
                    ×
                  </button>
                </div>
                <input
                  type="file"
                  multiple
                  accept="image/png,image/jpeg,image/webp"
                  @change="onPickImages(v.label, $event)"
                />
              </div>
              <p
                v-if="(variantImages[v.label] || []).length >= 2"
                class="ct-image-meta"
              >
                {{ $t('creativeTest.carouselMeta', { n: (variantImages[v.label] || []).length }) }}
              </p>
            </div>

            <div class="ct-image">
              <label class="ct-image-label">
                <span>{{ $t('creativeTest.videoOptional') }}</span>
                <span class="ct-image-hint">{{ $t('creativeTest.videoHint') }}</span>
              </label>
              <div class="ct-image-row">
                <video
                  v-if="variantVideoPreviews[v.label]"
                  :src="variantVideoPreviews[v.label]"
                  class="ct-video-preview"
                  controls
                  muted
                  preload="metadata"
                ></video>
                <input
                  type="file"
                  accept="video/mp4,video/webm,video/quicktime"
                  @change="onPickVideo(v.label, $event)"
                />
                <button
                  v-if="variantVideos[v.label]"
                  type="button"
                  class="ct-link"
                  @click="clearVideo(v.label)"
                >
                  {{ $t('creativeTest.removeVideo') }}
                </button>
              </div>
            </div>
          </div>
          <button class="ct-add" type="button" @click="addVariant" :disabled="form.variants.length >= 8">
            + {{ $t('creativeTest.addVariant') }}
          </button>
        </fieldset>

        <label class="ct-field">
          <span>
            {{ $t('creativeTest.channels') }} *
            <HelpHint :text="$t('creativeTest.help.channels')" />
          </span>
          <input v-model="channelsRaw" type="text" :placeholder="$t('creativeTest.channelsPh')" />
        </label>

        <label class="ct-field">
          <span>
            {{ $t('creativeTest.successMetrics') }} *
            <HelpHint :text="$t('creativeTest.help.successMetrics')" />
          </span>
          <input v-model="metricsRaw" type="text" :placeholder="$t('creativeTest.successMetricsPh')" />
        </label>

        <div v-if="errors.length" class="ct-errors">
          <strong>{{ $t('creativeTest.fixErrors') }}</strong>
          <ul>
            <li v-for="e in errors" :key="e">{{ e }}</li>
          </ul>
        </div>

        <button class="ct-submit" :disabled="loading" @click="submit">
          {{ loading ? $t('creativeTest.starting') : $t('creativeTest.startTest') }}
        </button>
      </section>

      <!-- Phase 2: Running -->
      <section v-else-if="phase === 'running'" class="ct-card">
        <h2>{{ $t('creativeTest.runningTitle') }}</h2>
        <p class="ct-subtle">{{ $t('creativeTest.runningSubtitle') }}</p>

        <div class="ct-progress-bar">
          <div class="ct-progress-fill" :style="{ width: progress + '%' }"></div>
        </div>
        <div class="ct-progress-meta">
          <span>{{ progress }}%</span>
          <span class="ct-stage-current">{{ $t(`creativeTest.stages.${currentStage || 'planning'}`) }}</span>
        </div>

        <ol class="ct-stage-list">
          <li
            v-for="s in stageList"
            :key="s.key"
            :class="{
              'ct-stage--done': stageOrder.indexOf(s.key) < stageOrder.indexOf(currentStage),
              'ct-stage--active': s.key === currentStage,
              'ct-stage--pending': stageOrder.indexOf(s.key) > stageOrder.indexOf(currentStage)
            }"
          >
            <span class="ct-stage-bullet"></span>
            <span class="ct-stage-label">{{ $t(`creativeTest.stages.${s.key}`) }}</span>
          </li>
        </ol>

        <p v-if="statusMessage" class="ct-log">{{ statusMessage }}</p>

        <div class="ct-actions">
          <button class="ct-submit ct-submit--secondary" @click="cancelPolling">
            {{ $t('creativeTest.leaveRunning') }}
          </button>
        </div>
      </section>

      <!-- Phase 2.5: Failed -->
      <section v-else-if="phase === 'failed'" class="ct-card">
        <h2>{{ $t('creativeTest.failedTitle') }}</h2>
        <p class="ct-error-text">{{ failureMessage }}</p>
        <div class="ct-actions">
          <button class="ct-submit" @click="reset">{{ $t('creativeTest.tryAgain') }}</button>
        </div>
      </section>

      <!-- Phase 3: Results -->
      <section v-else-if="phase === 'results' && result" class="ct-card">
        <div class="ct-result-head">
          <h2>{{ $t('creativeTest.resultsTitle') }}</h2>
          <span class="ct-mode-pill">{{ result.mode }}</span>
        </div>

        <!-- "How to read this report" collapsible guide -->
        <details class="ct-howto">
          <summary>{{ $t('creativeTest.howToRead.title') }}</summary>
          <p>{{ $t('creativeTest.howToRead.intro') }}</p>

          <h4>{{ $t('creativeTest.howToRead.scoreDimsTitle') }}</h4>
          <ul>
            <li>
              <strong>{{ $t('creativeTest.scoreDim.message_clarity_score') }}:</strong>
              {{ $t('creativeTest.help.scoreDim.message_clarity_score') }}
            </li>
            <li>
              <strong>{{ $t('creativeTest.scoreDim.audience_fit_score') }}:</strong>
              {{ $t('creativeTest.help.scoreDim.audience_fit_score') }}
            </li>
            <li>
              <strong>{{ $t('creativeTest.scoreDim.conversion_intent_score') }}:</strong>
              {{ $t('creativeTest.help.scoreDim.conversion_intent_score') }}
            </li>
            <li>
              <strong>{{ $t('creativeTest.scoreDim.brand_risk_score') }}:</strong>
              {{ $t('creativeTest.help.scoreDim.brand_risk_score') }}
            </li>
          </ul>

          <h4>{{ $t('creativeTest.howToRead.totalScoreTitle') }}</h4>
          <p>{{ $t('creativeTest.howToRead.totalScore') }}</p>

          <h4>{{ $t('creativeTest.howToRead.riskTitle') }}</h4>
          <ul>
            <li>
              <span class="ct-risk ct-risk--low">{{ $t('creativeTest.risk.low') }}</span>
              {{ $t('creativeTest.help.risk.low') }}
            </li>
            <li>
              <span class="ct-risk ct-risk--medium">{{ $t('creativeTest.risk.medium') }}</span>
              {{ $t('creativeTest.help.risk.medium') }}
            </li>
            <li>
              <span class="ct-risk ct-risk--high">{{ $t('creativeTest.risk.high') }}</span>
              {{ $t('creativeTest.help.risk.high') }}
            </li>
          </ul>

          <h4>{{ $t('creativeTest.howToRead.recoTitle') }}</h4>
          <ul>
            <li>
              <span class="ct-reco ct-reco--activate">{{ $t('creativeTest.reco.activate') }}:</span>
              {{ $t('creativeTest.help.reco.activate') }}
            </li>
            <li>
              <span class="ct-reco ct-reco--iterate">{{ $t('creativeTest.reco.iterate') }}:</span>
              {{ $t('creativeTest.help.reco.iterate') }}
            </li>
            <li>
              <span class="ct-reco ct-reco--discard">{{ $t('creativeTest.reco.discard') }}:</span>
              {{ $t('creativeTest.help.reco.discard') }}
            </li>
          </ul>
        </details>

        <div class="ct-summary">
          <div>
            <span class="ct-summary-label">
              {{ $t('creativeTest.winner') }}
              <HelpHint :text="$t('creativeTest.help.winner')" />
            </span>
            <strong>{{ result.summary.winner_label }}</strong>
          </div>
          <div>
            <span class="ct-summary-label">
              {{ $t('creativeTest.recommendation') }}
              <HelpHint :text="$t('creativeTest.help.recommendation')" />
            </span>
            <strong :class="`ct-reco ct-reco--${result.summary.winner_recommendation}`">
              {{ $t(`creativeTest.reco.${result.summary.winner_recommendation}`) }}
            </strong>
          </div>
          <div>
            <span class="ct-summary-label">{{ $t('creativeTest.audienceShort') }}</span>
            <strong>{{ result.summary.audience }}</strong>
          </div>
        </div>

        <h3>
          {{ $t('creativeTest.ranking') }}
          <HelpHint :text="$t('creativeTest.help.ranking')" />
        </h3>
        <ol class="ct-ranking">
          <li v-for="r in result.ranking" :key="r.label">
            <span class="ct-rank-pos">#{{ r.rank }}</span>
            <span class="ct-rank-label">{{ r.label }}</span>
            <span class="ct-rank-score">{{ r.total_score }}</span>
          </li>
        </ol>

        <h3>
          {{ $t('creativeTest.scorecards') }}
          <HelpHint :text="$t('creativeTest.help.scorecards')" />
        </h3>
        <div class="ct-scorecards">
          <div v-for="v in result.variants" :key="v.label" class="ct-scorecard">
            <div class="ct-scorecard-head">
              <strong>{{ v.label }}</strong>
              <span :class="`ct-risk ct-risk--${v.risk_level}`">
                {{ $t(`creativeTest.risk.${v.risk_level}`) }}
                <HelpHint :text="$t(`creativeTest.help.risk.${v.risk_level}`)" placement="right" />
              </span>
            </div>
            <p class="ct-headline">{{ v.headline }}</p>
            <ul class="ct-scores">
              <li v-for="(score, dim) in v.scores" :key="dim">
                <span>
                  {{ $t(`creativeTest.scoreDim.${dim}`) }}
                  <HelpHint :text="$t(`creativeTest.help.scoreDim.${dim}`)" />
                </span>
                <span>{{ score }}</span>
              </li>
            </ul>
            <p v-if="v.rationale" class="ct-rationale">{{ v.rationale }}</p>
          </div>
        </div>

        <div v-if="result.next_steps && result.next_steps.length" class="ct-next">
          <h3>{{ $t('creativeTest.nextSteps') }}</h3>
          <ul>
            <li v-for="(step, i) in result.next_steps" :key="i">{{ step }}</li>
          </ul>
        </div>

        <button class="ct-submit ct-submit--secondary" @click="reset">
          {{ $t('creativeTest.runAnother') }}
        </button>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  checkCreativeTestHealth,
  startCreativeTest,
  getCreativeTestStatus
} from '../api/creativeTest'
import { getClient } from '../api/clients'
import HelpHint from '../components/HelpHint.vue'

const router = useRouter()
const route = useRoute()

// R1 — every run must belong to a client. The wizard expects ?client=<id>
// in the query string; without it we surface a clear "missing client"
// state instead of letting users fire orphan runs.
const clientId = computed(() => route.query.client || '')
const clientInfo = ref(null)

const healthLoading = ref(true)
const enabled = ref(false)
const healthInfo = ref(null)

// phase: 'brief' | 'running' | 'results' | 'failed'
const phase = ref('brief')
const loading = ref(false)
const result = ref(null)
const errors = ref([])
const failureMessage = ref('')

const testId = ref(null)
const progress = ref(0)
const currentStage = ref('planning')
const statusMessage = ref('')

const stageOrder = ['planning', 'evaluating', 'scoring', 'composing', 'completed']
const stageList = stageOrder.slice(0, -1).map((key) => ({ key }))

let pollTimer = null

const form = reactive({
  business_goal: '',
  scenario: '',
  audience: { name: '', country: '', primary_channel: '', age_range: '' },
  variants: [
    { label: 'A', headline: '', cta: '', tone: '' },
    { label: 'B', headline: '', cta: '', tone: '' },
    { label: 'C', headline: '', cta: '', tone: '' }
  ]
})

const channelsRaw = ref('')
const metricsRaw = ref('')

// R4/R5 — assets per variant. Files live here as ordered arrays; previews
// are matching arrays of object URLs. Single-image (R4) is just an array of
// length 1 — the wizard does not branch.
const variantImages = reactive({})
const variantImagePreviews = reactive({})

const _revokeAll = (label) => {
  for (const url of variantImagePreviews[label] || []) URL.revokeObjectURL(url)
}

// Cap mirrors backend MAX_SLIDES_PER_VARIANT — keeps a per-corrida vision
// cost bounded even if the user drag-drops a folder.
const MAX_SLIDES_PER_VARIANT = 10

const onPickImages = (label, event) => {
  const files = Array.from(event.target.files || [])
  if (!files.length) return
  // Append rather than replace so users can add slides incrementally.
  const prev = variantImages[label] || []
  let combined = [...prev, ...files]
  if (combined.length > MAX_SLIDES_PER_VARIANT) {
    combined = combined.slice(0, MAX_SLIDES_PER_VARIANT)
  }
  variantImages[label] = combined
  const previews = variantImagePreviews[label] || []
  const newPreviews = files.map((f) => URL.createObjectURL(f))
  let combinedPreviews = [...previews, ...newPreviews]
  if (combinedPreviews.length > MAX_SLIDES_PER_VARIANT) {
    // Free the object URLs we are about to drop.
    combinedPreviews
      .slice(MAX_SLIDES_PER_VARIANT)
      .forEach((url) => URL.revokeObjectURL(url))
    combinedPreviews = combinedPreviews.slice(0, MAX_SLIDES_PER_VARIANT)
  }
  variantImagePreviews[label] = combinedPreviews
  event.target.value = ''
}

const removeSlide = (label, idx) => {
  const previews = variantImagePreviews[label] || []
  if (previews[idx]) URL.revokeObjectURL(previews[idx])
  const nextFiles = (variantImages[label] || []).filter((_, i) => i !== idx)
  const nextPreviews = previews.filter((_, i) => i !== idx)
  if (nextFiles.length === 0) {
    delete variantImages[label]
    delete variantImagePreviews[label]
  } else {
    variantImages[label] = nextFiles
    variantImagePreviews[label] = nextPreviews
  }
}

const clearImage = (label) => {
  _revokeAll(label)
  delete variantImages[label]
  delete variantImagePreviews[label]
}

// R6 — one optional video upload per variant. The backend extracts frames
// and a Whisper transcript on the fly; the wizard only needs to capture the
// file and show a quick preview.
const variantVideos = reactive({})
const variantVideoPreviews = reactive({})

const onPickVideo = (label, event) => {
  const file = event.target.files?.[0]
  if (!file) return
  if (variantVideoPreviews[label]) URL.revokeObjectURL(variantVideoPreviews[label])
  variantVideos[label] = file
  variantVideoPreviews[label] = URL.createObjectURL(file)
  event.target.value = ''
}

const clearVideo = (label) => {
  if (variantVideoPreviews[label]) URL.revokeObjectURL(variantVideoPreviews[label])
  delete variantVideos[label]
  delete variantVideoPreviews[label]
}

const splitCsv = (raw) =>
  (raw || '').split(/[,\n;]/).map((s) => s.trim()).filter(Boolean)

const addVariant = () => {
  if (form.variants.length >= 8) return
  const nextLabel = String.fromCharCode('A'.charCodeAt(0) + form.variants.length)
  form.variants.push({ label: nextLabel, headline: '', cta: '', tone: '' })
}

const removeVariant = (idx) => {
  if (form.variants.length <= 2) return
  const removed = form.variants[idx].label
  clearImage(removed)
  clearVideo(removed)
  form.variants.splice(idx, 1)
  form.variants.forEach((v, i) => {
    v.label = String.fromCharCode('A'.charCodeAt(0) + i)
  })
}

const buildPayload = () => ({
  business_goal: form.business_goal,
  scenario: form.scenario,
  audience_profile: { ...form.audience },
  creative_variants: form.variants.map((v) => ({ ...v })),
  channels: splitCsv(channelsRaw.value),
  success_metrics: splitCsv(metricsRaw.value).map((name) => ({ name }))
})

const cancelPolling = () => {
  if (pollTimer) {
    clearTimeout(pollTimer)
    pollTimer = null
  }
}

const pollOnce = async () => {
  if (!testId.value) return
  try {
    const res = await getCreativeTestStatus(testId.value)
    const data = res.data || {}
    progress.value = Math.max(progress.value, data.progress || 0)
    if (data.stage) currentStage.value = data.stage
    if (data.message) statusMessage.value = data.message

    if (data.status === 'completed' && data.result) {
      result.value = data.result
      cancelPolling()
      // R2.4: redirect to the cliente-céntrica detail report; the inline
      // results panel below stays as a fallback for when the wizard is
      // opened without a client_id (legacy paths).
      if (clientId.value && testId.value) {
        router.push(`/clients/${clientId.value}/tests/${testId.value}`)
        return
      }
      phase.value = 'results'
      return
    }
    if (data.status === 'failed') {
      failureMessage.value = data.error || 'Run failed'
      phase.value = 'failed'
      cancelPolling()
      return
    }
    pollTimer = setTimeout(pollOnce, 1000)
  } catch (err) {
    failureMessage.value = err?.response?.data?.error || err.message || 'Network error'
    phase.value = 'failed'
    cancelPolling()
  }
}

const submit = async () => {
  errors.value = []
  loading.value = true
  try {
    if (!clientId.value) {
      errors.value = ['client_id is required (open this from a client page)']
      loading.value = false
      return
    }
    const payload = { ...buildPayload(), client_id: clientId.value }
    const images = Object.fromEntries(
      Object.entries(variantImages).filter(
        ([, files]) => Array.isArray(files) && files.length > 0
      )
    )
    const videos = Object.fromEntries(
      Object.entries(variantVideos).filter(([, file]) => !!file)
    )
    const res = await startCreativeTest(payload, images, videos)
    const data = res.data || {}
    testId.value = data.test_id
    progress.value = 0
    currentStage.value = 'planning'
    statusMessage.value = ''
    phase.value = 'running'
    pollTimer = setTimeout(pollOnce, 600)
  } catch (err) {
    const data = err?.response?.data
    if (data?.validation_errors) {
      errors.value = data.validation_errors
    } else {
      errors.value = [data?.error || err.message || 'Unknown error']
    }
  } finally {
    loading.value = false
  }
}

const goBackToClient = () => {
  if (clientId.value) {
    router.push(`/clients/${clientId.value}`)
  } else {
    router.push('/clients')
  }
}

const reset = () => {
  cancelPolling()
  result.value = null
  errors.value = []
  failureMessage.value = ''
  testId.value = null
  progress.value = 0
  currentStage.value = 'planning'
  statusMessage.value = ''
  phase.value = 'brief'
}

onMounted(async () => {
  try {
    const res = await checkCreativeTestHealth()
    enabled.value = !!res?.data?.enabled
    healthInfo.value = res?.data || null
  } catch {
    enabled.value = false
  }
  if (clientId.value) {
    try {
      const res = await getClient(clientId.value)
      clientInfo.value = res?.data || null
    } catch {
      clientInfo.value = null
    }
  }
  healthLoading.value = false
})

onBeforeUnmount(cancelPolling)
</script>

<style scoped>
.ct-container {
  max-width: 920px;
  margin: 0 auto;
  padding: 32px 24px 64px;
  color: #1f2937;
  font-family: system-ui, -apple-system, sans-serif;
}

.ct-back {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 14px;
  color: #6b7280;
  padding: 0;
  margin-bottom: 12px;
}

.ct-header h1 {
  font-size: 28px;
  margin: 0 0 4px;
}

.ct-subtitle {
  color: #6b7280;
  margin: 0 0 12px;
}

.ct-mode-banner {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  padding: 4px 10px;
  border-radius: 12px;
  margin-bottom: 12px;
}

.ct-mode-banner--mock { background: #fef3c7; color: #92400e; }
.ct-mode-banner--live { background: #dcfce7; color: #166534; }

.ct-mode-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}

.ct-state,
.ct-disabled {
  background: #f9fafb;
  border: 1px dashed #d1d5db;
  padding: 24px;
  border-radius: 8px;
}

.ct-disabled code {
  background: #111827;
  color: #f9fafb;
  padding: 4px 8px;
  border-radius: 4px;
  font-family: monospace;
}

.ct-card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 24px;
  margin-top: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.ct-card h2 {
  margin: 0 0 16px;
  font-size: 20px;
}

.ct-subtle { color: #6b7280; margin-top: -8px; }

.ct-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 14px;
}

.ct-field span {
  font-size: 13px;
  color: #4b5563;
  font-weight: 500;
}

.ct-field input,
.ct-field textarea {
  border: 1px solid #d1d5db;
  border-radius: 6px;
  padding: 8px 10px;
  font-size: 14px;
  font-family: inherit;
}

.ct-field input:focus,
.ct-field textarea:focus {
  outline: none;
  border-color: #2563eb;
}

.ct-fieldset {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
}

.ct-fieldset legend {
  font-size: 13px;
  font-weight: 600;
  padding: 0 8px;
  color: #374151;
}

.ct-grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.ct-variant {
  border: 1px solid #f3f4f6;
  border-radius: 6px;
  padding: 12px;
  margin-bottom: 10px;
  background: #fafafa;
}

.ct-variant-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.ct-link {
  background: none;
  border: none;
  color: #2563eb;
  cursor: pointer;
  font-size: 12px;
  padding: 0;
}

.ct-link:disabled { color: #9ca3af; cursor: not-allowed; }

.ct-image {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed #e5e7eb;
}
.ct-image-label {
  display: flex;
  flex-direction: column;
  font-size: 12px;
  color: #6b7280;
  margin-bottom: 6px;
}
.ct-image-label span:first-child { font-weight: 600; color: #374151; }
.ct-image-hint { font-size: 11px; color: #9ca3af; margin-top: 2px; }
.ct-image-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.ct-image-thumb {
  position: relative;
  width: 56px;
  height: 56px;
}
.ct-image-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 4px;
  border: 1px solid #e5e7eb;
  display: block;
}
.ct-image-remove {
  position: absolute;
  top: -6px;
  right: -6px;
  width: 18px;
  height: 18px;
  border-radius: 9px;
  border: 1px solid #d1d5db;
  background: #fff;
  font-size: 12px;
  line-height: 1;
  cursor: pointer;
  color: #6b7280;
  padding: 0;
}
.ct-image-meta {
  font-size: 11px;
  color: #6b7280;
  margin: 6px 0 0;
}
.ct-video-preview {
  width: 160px;
  max-height: 90px;
  background: #000;
  border-radius: 4px;
  border: 1px solid #e5e7eb;
}

.ct-add {
  background: #f3f4f6;
  border: 1px dashed #9ca3af;
  border-radius: 6px;
  padding: 8px 12px;
  cursor: pointer;
  font-size: 13px;
}

.ct-add:disabled { opacity: 0.5; cursor: not-allowed; }

.ct-errors {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #991b1b;
  padding: 12px;
  border-radius: 6px;
  margin: 12px 0;
  font-size: 13px;
}

.ct-errors ul { margin: 6px 0 0 18px; padding: 0; }

.ct-submit {
  margin-top: 16px;
  background: #2563eb;
  color: #fff;
  border: none;
  border-radius: 6px;
  padding: 10px 20px;
  font-size: 15px;
  cursor: pointer;
}

.ct-submit:disabled { background: #9ca3af; cursor: not-allowed; }

.ct-submit--secondary {
  background: #f3f4f6;
  color: #1f2937;
  border: 1px solid #d1d5db;
}

.ct-actions { display: flex; gap: 8px; margin-top: 20px; }

.ct-result-head {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.ct-mode-pill {
  background: #fef3c7;
  color: #92400e;
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.ct-summary {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  background: #f9fafb;
  padding: 16px;
  border-radius: 8px;
  margin-bottom: 20px;
}

.ct-summary > div { display: flex; flex-direction: column; gap: 2px; }

.ct-summary-label {
  font-size: 11px;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.ct-reco--activate { color: #047857; }
.ct-reco--iterate { color: #b45309; }
.ct-reco--discard { color: #b91c1c; }

.ct-ranking { list-style: none; padding: 0; margin: 0 0 24px; }

.ct-ranking li {
  display: grid;
  grid-template-columns: 60px 1fr 80px;
  align-items: center;
  padding: 10px 12px;
  background: #f9fafb;
  border-radius: 6px;
  margin-bottom: 6px;
}

.ct-rank-pos { font-weight: 700; color: #6b7280; }
.ct-rank-score { text-align: right; font-weight: 600; }

.ct-scorecards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 12px;
}

.ct-scorecard {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 14px;
  background: #fff;
}

.ct-scorecard-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.ct-risk {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  text-transform: uppercase;
}

.ct-risk--low { background: #d1fae5; color: #065f46; }
.ct-risk--medium { background: #fef3c7; color: #92400e; }
.ct-risk--high { background: #fee2e2; color: #991b1b; }

.ct-headline { font-size: 14px; color: #374151; margin: 4px 0 10px; }

.ct-scores {
  list-style: none;
  padding: 0;
  margin: 0 0 8px;
  font-size: 13px;
}

.ct-scores li {
  display: flex;
  justify-content: space-between;
  padding: 3px 0;
  border-bottom: 1px dashed #f3f4f6;
}

.ct-rationale {
  font-size: 12px;
  color: #6b7280;
  margin: 6px 0 0;
  font-style: italic;
}

/* Progress (Phase 2) */
.ct-progress-bar {
  width: 100%;
  height: 8px;
  background: #e5e7eb;
  border-radius: 4px;
  overflow: hidden;
  margin-top: 12px;
}

.ct-progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #2563eb 0%, #60a5fa 100%);
  transition: width 0.4s ease;
}

.ct-progress-meta {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #6b7280;
  margin-top: 6px;
}

.ct-stage-current { font-weight: 600; color: #2563eb; }

.ct-stage-list {
  list-style: none;
  padding: 0;
  margin: 24px 0 0;
}

.ct-stage-list li {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 0;
  font-size: 14px;
  color: #6b7280;
}

.ct-stage-bullet {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #e5e7eb;
  flex-shrink: 0;
}

.ct-stage--done { color: #047857; }
.ct-stage--done .ct-stage-bullet { background: #10b981; }

.ct-stage--active { color: #1f2937; font-weight: 600; }
.ct-stage--active .ct-stage-bullet {
  background: #2563eb;
  box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.18);
  animation: ct-pulse 1.4s ease-in-out infinite;
}

@keyframes ct-pulse {
  0%, 100% { box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.18); }
  50%      { box-shadow: 0 0 0 7px rgba(37, 99, 235, 0.08); }
}

.ct-log {
  margin-top: 16px;
  font-family: ui-monospace, monospace;
  font-size: 12px;
  background: #111827;
  color: #d1d5db;
  padding: 8px 12px;
  border-radius: 6px;
}

.ct-error-text {
  color: #b91c1c;
  background: #fef2f2;
  padding: 12px;
  border-radius: 6px;
  border: 1px solid #fecaca;
}

.ct-next ul { margin: 8px 0 16px 20px; padding: 0; font-size: 14px; color: #374151; }
.ct-next li { padding: 4px 0; }

/* "How to read this report" collapsible guide */
.ct-howto {
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 12px 16px;
  margin: 0 0 20px;
  font-size: 13px;
}

.ct-howto > summary {
  cursor: pointer;
  font-weight: 600;
  color: #374151;
  list-style: none;
  display: flex;
  align-items: center;
  gap: 6px;
}

.ct-howto > summary::before {
  content: '▸';
  display: inline-block;
  font-size: 11px;
  color: #6b7280;
  transition: transform 0.18s;
}

.ct-howto[open] > summary::before {
  transform: rotate(90deg);
}

.ct-howto > summary::-webkit-details-marker { display: none; }

.ct-howto p {
  margin: 8px 0;
  color: #4b5563;
  line-height: 1.55;
}

.ct-howto h4 {
  margin: 14px 0 4px;
  font-size: 13px;
  color: #111827;
}

.ct-howto ul {
  margin: 4px 0 0 0;
  padding-left: 18px;
  color: #4b5563;
  line-height: 1.55;
}

.ct-howto li { padding: 3px 0; }

.ct-howto .ct-risk,
.ct-howto .ct-reco {
  margin-right: 6px;
}
</style>
