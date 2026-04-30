<template>
  <div class="ot fadein">
    <Breadcrumb :items="breadcrumb" />

    <header class="ot-hero">
      <div class="ot-hero-left">
        <div class="eyebrow">{{ $t('ov.eyebrow') }}</div>
        <h1 class="h-display ot-title">
          {{ client.name }}
          <span v-if="client.is_default" class="ot-default-badge">{{ $t('clients.defaultBadge') }}</span>
        </h1>
        <p class="ot-sub">
          {{ client.industry || $t('clients.noIndustry') }}
          <span class="sep">·</span>
          {{ stats.tests }} {{ $t('home2.tests_count') }}
          <span class="sep">·</span>
          {{ stats.reports }} {{ $t('home2.reports_count') }}
          <span class="sep">·</span>
          {{ stats.entities }} {{ $t('clients.graph.nodes') }}
        </p>
      </div>
      <div class="ot-hero-actions">
        <Button
          variant="primary"
          icon="plus"
          @click="$router.push(`/creative-test?client=${client.client_id}`)"
        >
          {{ $t('clients.creativeTests.newTest') }}
        </Button>
        <Button
          icon="upload"
          @click="$router.push(`/clients/${client.client_id}/context`)"
        >
          {{ $t('ov.action.context') }}
        </Button>
      </div>
    </header>

    <!-- KPI row -->
    <Card class="ot-kpis-card">
      <div class="kpi-row ot-kpi-row">
        <div class="kpi">
          <div class="k">{{ $t('home2.kpi.tests') }}</div>
          <div class="v num">{{ stats.tests }}</div>
        </div>
        <div class="kpi">
          <div class="k">{{ $t('home2.kpi.episodes') }}</div>
          <div class="v num">{{ stats.episodes }}</div>
        </div>
        <div class="kpi">
          <div class="k">{{ $t('home2.kpi.entities') }}</div>
          <div class="v num">{{ stats.entities }}</div>
        </div>
        <div class="kpi">
          <div class="k">{{ $t('clients.graph.edges') }}</div>
          <div class="v num">{{ stats.edges }}</div>
        </div>
      </div>
    </Card>

    <!-- 2-col: latest tests + graph health -->
    <div class="ot-grid">
      <section class="ot-tests">
        <div class="section-head">
          <div class="lt">
            <h2 class="h-1">{{ $t('ov.last_results') }}</h2>
            <span class="ct">{{ tests.length }}</span>
          </div>
          <Button
            v-if="tests.length"
            variant="ghost"
            size="sm"
            icon="arrow-r"
            @click="$router.push(`/clients/${client.client_id}/tests`)"
          >
            {{ $t('common.see_all') }}
          </Button>
        </div>

        <div v-if="testsLoading" class="ot-empty">{{ $t('common.loading') }}</div>

        <EmptyState
          v-else-if="!tests.length"
          :title="$t('clients.creativeTests.empty')"
        >
          <Button
            variant="signal"
            icon="plus"
            @click="$router.push(`/creative-test?client=${client.client_id}`)"
          >
            {{ $t('clients.creativeTests.newTest') }}
          </Button>
        </EmptyState>

        <ul v-else class="ot-test-list">
          <li
            v-for="t in tests.slice(0, 4)"
            :key="t.test_id"
            class="ot-test-row"
            @click="openTest(t.test_id)"
          >
            <div class="ot-test-main">
              <div class="ot-test-line1">
                <strong class="serif">{{ t.business_goal || t.test_id }}</strong>
                <Badge
                  v-if="t.winner_recommendation"
                  :variant="recoVariant(t.winner_recommendation)"
                >
                  {{ $t(`creativeTest.reco.${t.winner_recommendation}`) }}
                </Badge>
              </div>
              <div class="ot-test-line2 mono">
                <span v-if="t.audience">{{ t.audience }}</span>
                <span v-if="t.winner_label" class="sep">·</span>
                <span v-if="t.winner_label">
                  {{ $t('clients.creativeTests.winner') }}: <strong>{{ t.winner_label }}</strong>
                </span>
                <span class="sep">·</span>
                <span class="ot-test-id">{{ t.test_id }}</span>
              </div>
            </div>
            <Icon name="chevron-r" :size="16" />
          </li>
        </ul>
      </section>

      <aside class="ot-graph-health">
        <div class="section-head">
          <div class="lt">
            <h2 class="h-1">{{ $t('ov.graph_health') }}</h2>
          </div>
        </div>
        <Card>
          <div class="ot-gh-stats">
            <div>
              <div class="label">{{ $t('clients.graph.episodes') }}</div>
              <div class="num serif ot-gh-stat">{{ stats.episodes }}</div>
            </div>
            <div>
              <div class="label">{{ $t('clients.graph.nodes') }}</div>
              <div class="num serif ot-gh-stat">{{ stats.entities }}</div>
            </div>
            <div>
              <div class="label">{{ $t('clients.graph.edges') }}</div>
              <div class="num serif ot-gh-stat">{{ stats.edges }}</div>
            </div>
          </div>

          <hr class="hdiv" />

          <Button
            v-if="client.graph_id"
            variant="ghost"
            icon="arrow-r"
            @click="$router.push(`/clients/${client.client_id}/context`)"
          >
            {{ $t('ov.explore_graph') }}
          </Button>

          <EmptyState
            v-else
            :title="$t('clients.graph.bootstrapTitle')"
            :hint="$t('clients.graph.bootstrapDesc')"
          >
            <Button
              variant="signal"
              icon="spark"
              @click="$router.push(`/clients/${client.client_id}/context`)"
            >
              {{ $t('clients.graph.bootstrapBtn') }}
            </Button>
          </EmptyState>
        </Card>
      </aside>
    </div>

    <!-- Quick prediction (R3.2) -->
    <section v-if="client.graph_id" class="ot-quick">
      <div class="section-head">
        <div class="lt">
          <h2 class="h-1">{{ $t('ov.quickPrediction.title') }}</h2>
        </div>
        <span class="ct">{{ $t('ov.quickPrediction.subtitle') }}</span>
      </div>
      <Card>
        <div class="ot-qp-row">
          <input
            v-model="predictionQuery"
            type="text"
            class="ot-qp-input"
            :placeholder="$t('ov.quickPrediction.placeholder')"
            @keyup.enter="askPrediction"
          />
          <Button
            variant="primary"
            icon="spark"
            :disabled="!predictionQuery || predicting"
            @click="askPrediction"
          >
            {{ predicting ? $t('common.loading') : $t('ov.quickPrediction.ask') }}
          </Button>
        </div>
        <div v-if="predictionError" class="ot-qp-error">{{ predictionError }}</div>
        <div v-else-if="prediction" class="ot-qp-result">
          <p class="ot-qp-answer">{{ prediction.answer }}</p>
          <div v-if="prediction.facts && prediction.facts.length" class="ot-qp-facts">
            <div class="label">{{ $t('ov.quickPrediction.factsCited', { n: prediction.facts.length }) }}</div>
            <ul>
              <li v-for="(f, i) in prediction.facts" :key="i">{{ f }}</li>
            </ul>
          </div>
        </div>
        <p v-else class="ot-qp-hint">{{ $t('ov.quickPrediction.hint') }}</p>
      </Card>
    </section>

    <!-- Next steps -->
    <section class="ot-next">
      <div class="section-head">
        <div class="lt">
          <h2 class="h-1">{{ $t('ov.next_steps') }}</h2>
        </div>
      </div>
      <div class="ot-next-grid">
        <Card hoverable @click="$router.push(`/clients/${client.client_id}/context`)">
          <div class="ot-next-row">
            <Icon name="upload" :size="20" />
            <div>
              <div class="serif ot-next-title">{{ $t('ov.action.context') }}</div>
              <p class="ot-next-hint">{{ $t('ov.action.contextHint') }}</p>
            </div>
            <Icon name="arrow-r" :size="16" />
          </div>
        </Card>
        <Card hoverable @click="$router.push(`/creative-test?client=${client.client_id}`)">
          <div class="ot-next-row">
            <Icon name="tests" :size="20" />
            <div>
              <div class="serif ot-next-title">{{ $t('ov.action.test') }}</div>
              <p class="ot-next-hint">{{ $t('ov.action.testHint') }}</p>
            </div>
            <Icon name="arrow-r" :size="16" />
          </div>
        </Card>
        <Card hoverable @click="$router.push(`/clients/${client.client_id}/sims`)">
          <div class="ot-next-row">
            <Icon name="sims" :size="20" />
            <div>
              <div class="serif ot-next-title">{{ $t('ov.action.sim') }}</div>
              <p class="ot-next-hint">{{ $t('ov.action.simHint') }}</p>
            </div>
            <Icon name="arrow-r" :size="16" />
          </div>
        </Card>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { listClientCreativeTests, predictForClient } from '../../api/clients'
import Breadcrumb from '../../components/shell/Breadcrumb.vue'
import Button from '../../components/ui/Button.vue'
import Card from '../../components/ui/Card.vue'
import Badge from '../../components/ui/Badge.vue'
import Icon from '../../components/ui/Icon.vue'
import EmptyState from '../../components/ui/EmptyState.vue'

const props = defineProps({
  client: { type: Object, required: true },
  stats: { type: Object, required: true }
})

const { t } = useI18n()
const router = useRouter()

const openTest = (testId) => {
  router.push(`/clients/${props.client.client_id}/tests/${testId}`)
}

const tests = ref([])
const testsLoading = ref(false)

// Quick prediction (R3.2)
const predictionQuery = ref('')
const predicting = ref(false)
const prediction = ref(null)
const predictionError = ref('')

const askPrediction = async () => {
  if (!predictionQuery.value.trim()) return
  predicting.value = true
  predictionError.value = ''
  prediction.value = null
  try {
    const res = await predictForClient(props.client.client_id, predictionQuery.value)
    prediction.value = res.data
  } catch (err) {
    predictionError.value = err?.response?.data?.error || err.message || 'Error'
  } finally {
    predicting.value = false
  }
}

const breadcrumb = computed(() => [
  { label: t('side.clients'), to: '/' },
  { label: props.client.name }
])

const recoVariant = (r) => {
  if (r === 'activate') return 'ok'
  if (r === 'discard') return 'bad'
  return 'warn'
}

const refreshTests = async () => {
  testsLoading.value = true
  try {
    const res = await listClientCreativeTests(props.client.client_id)
    tests.value = res.data || []
  } catch {
    tests.value = []
  } finally {
    testsLoading.value = false
  }
}

onMounted(refreshTests)
watch(() => props.client.client_id, refreshTests)
</script>

<style scoped>
.ot-hero {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 22px;
}

.ot-hero-left { min-width: 0; flex: 1; }

.ot-title {
  margin: 8px 0 6px;
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.ot-default-badge {
  font-family: var(--mono);
  font-size: 10px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  padding: 4px 10px;
  border: 1px solid var(--line);
  background: var(--surface-2);
  border-radius: 999px;
  color: var(--ink-3);
}

.ot-sub {
  margin: 0;
  font-size: 14px;
  color: var(--ink-2);
}
.ot-sub .sep { margin: 0 6px; color: var(--ink-5); }

.ot-hero-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.ot-kpis-card {
  padding: 0 !important;
  margin-bottom: 24px;
  overflow: hidden;
}
.ot-kpi-row {
  border: 0;
  border-radius: 0;
}

.ot-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 24px;
  margin-bottom: 28px;
}
@media (max-width: 900px) {
  .ot-grid { grid-template-columns: 1fr; }
}

.ot-test-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.ot-test-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  border: 1px solid var(--line);
  background: var(--surface);
  border-radius: var(--r);
  transition: background 0.12s, border-color 0.12s;
}
.ot-test-row:hover { background: var(--surface-2); border-color: var(--line-2); }

.ot-test-main { flex: 1; min-width: 0; }
.ot-test-line1 {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 15px;
  color: var(--ink);
}
.ot-test-line1 strong { font-weight: 500; }

.ot-test-line2 {
  margin-top: 4px;
  font-size: 11px;
  color: var(--ink-3);
  letter-spacing: 0.04em;
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.ot-test-line2 .sep { color: var(--ink-5); }
.ot-test-id { color: var(--ink-4); }

.ot-empty {
  padding: 16px;
  background: var(--surface-2);
  border: 1px dashed var(--line);
  border-radius: var(--r);
  color: var(--ink-3);
  text-align: center;
  font-size: 13px;
}

.ot-gh-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  text-align: center;
}
.ot-gh-stat { font-size: 22px; }

.ot-next-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}
@media (max-width: 760px) {
  .ot-next-grid { grid-template-columns: 1fr; }
}

.ot-next-row {
  display: flex;
  align-items: center;
  gap: 14px;
}

/* — Quick prediction — */
.ot-quick { margin-bottom: 28px; }

.ot-qp-row {
  display: flex;
  gap: 8px;
  align-items: stretch;
}

.ot-qp-input {
  flex: 1;
  border: 1px solid var(--line-2);
  border-radius: var(--r-sm);
  padding: 9px 12px;
  font-family: inherit;
  font-size: 14px;
  background: var(--surface);
  color: var(--ink);
}
.ot-qp-input:focus { outline: none; border-color: var(--signal); }

.ot-qp-error {
  margin-top: 12px;
  color: var(--bad);
  background: var(--bad-soft);
  border: 1px solid var(--bad-soft);
  padding: 8px 12px;
  border-radius: var(--r-sm);
  font-size: 13px;
}

.ot-qp-result {
  margin-top: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.ot-qp-answer {
  margin: 0;
  font-size: 15px;
  line-height: 1.6;
  color: var(--ink);
  background: var(--surface-2);
  border-left: 3px solid var(--signal);
  padding: 12px 14px;
  border-radius: 0 var(--r-sm) var(--r-sm) 0;
  white-space: pre-wrap;
}

.ot-qp-facts ul {
  list-style: none;
  padding-left: 0;
  margin: 6px 0 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.ot-qp-facts li {
  font-size: 12.5px;
  color: var(--ink-2);
  line-height: 1.5;
  padding: 6px 10px;
  background: var(--surface-2);
  border-radius: var(--r-xs);
}

.ot-qp-hint {
  margin: 12px 0 0;
  color: var(--ink-3);
  font-size: 12px;
  line-height: 1.5;
}
.ot-next-row > div { flex: 1; min-width: 0; }
.ot-next-title { font-size: 15px; color: var(--ink); }
.ot-next-hint {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--ink-3);
  line-height: 1.4;
}
</style>
