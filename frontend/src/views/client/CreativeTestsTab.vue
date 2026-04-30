<template>
  <div class="ctt fadein">
    <Breadcrumb :items="breadcrumb" />

    <header class="ctt-head">
      <div>
        <div class="eyebrow">{{ $t('clients.tabs.creativeTests') }}</div>
        <h1 class="h-1 ctt-title">{{ $t('clients.creativeTestsHelper') }}</h1>
      </div>
      <Button
        variant="primary"
        icon="plus"
        @click="$router.push(`/creative-test?client=${client.client_id}`)"
      >
        {{ $t('clients.creativeTests.newTest') }}
      </Button>
    </header>

    <div v-if="loading" class="state-loading">{{ $t('common.loading') }}</div>

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

    <ul v-else class="tests-list">
      <li
        v-for="t in tests"
        :key="t.test_id"
        class="test-row"
        @click="openTest(t.test_id)"
      >
        <div class="test-main">
          <div class="line1">
            <strong class="serif test-goal">{{ t.business_goal || t.test_id }}</strong>
            <Badge
              v-if="t.winner_recommendation"
              :variant="recoVariant(t.winner_recommendation)"
            >
              {{ $t(`creativeTest.reco.${t.winner_recommendation}`) }}
            </Badge>
            <Badge :variant="statusVariant(t.status)">{{ t.status }}</Badge>
          </div>
          <div class="line2 mono">
            <span v-if="t.audience">{{ t.audience }}</span>
            <span v-if="t.winner_label" class="sep">·</span>
            <span v-if="t.winner_label">
              {{ $t('clients.creativeTests.winner') }}: <strong>{{ t.winner_label }}</strong>
            </span>
            <span class="sep">·</span>
            <span class="test-id">{{ t.test_id }}</span>
            <span class="sep">·</span>
            <span class="test-date">{{ formatDate(t.created_at) }}</span>
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
import { listClientCreativeTests } from '../../api/clients'
import Breadcrumb from '../../components/shell/Breadcrumb.vue'
import Button from '../../components/ui/Button.vue'
import Badge from '../../components/ui/Badge.vue'
import Icon from '../../components/ui/Icon.vue'
import EmptyState from '../../components/ui/EmptyState.vue'

const props = defineProps({
  client: { type: Object, required: true }
})

const { t } = useI18n()
const router = useRouter()

const openTest = (testId) => {
  router.push(`/clients/${props.client.client_id}/tests/${testId}`)
}

const tests = ref([])
const loading = ref(false)

const breadcrumb = computed(() => [
  { label: t('side.clients'), to: '/' },
  { label: props.client.name, to: `/clients/${props.client.client_id}/overview` },
  { label: t('clients.tabs.creativeTests') }
])

const recoVariant = (r) => (r === 'activate' ? 'ok' : r === 'discard' ? 'bad' : 'warn')
const statusVariant = (s) =>
  s === 'completed' ? 'ok' : s === 'failed' ? 'bad' : s === 'running' ? 'warn' : 'default'

const formatDate = (iso) => {
  if (!iso) return ''
  try {
    const d = new Date(iso)
    return d.toISOString().slice(0, 16).replace('T', ' ')
  } catch {
    return iso
  }
}

const refresh = async () => {
  loading.value = true
  try {
    const res = await listClientCreativeTests(props.client.client_id)
    tests.value = res.data || []
  } catch {
    tests.value = []
  } finally {
    loading.value = false
  }
}

onMounted(refresh)
watch(() => props.client.client_id, refresh)
</script>

<style scoped>
.ctt-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 22px;
}

.ctt-title { margin: 4px 0 0; font-weight: 400; }

.state-loading {
  padding: 24px;
  background: var(--surface-2);
  border: 1px dashed var(--line);
  border-radius: var(--r);
  color: var(--ink-3);
  text-align: center;
  font-size: 13px;
}

.tests-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.test-row {
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
.test-row:hover { background: var(--surface-2); border-color: var(--line-2); }

.test-main { flex: 1; min-width: 0; }

.line1 {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  font-size: 15px;
}
.test-goal { font-weight: 500; color: var(--ink); }

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
.test-id, .test-date { color: var(--ink-4); }
</style>
