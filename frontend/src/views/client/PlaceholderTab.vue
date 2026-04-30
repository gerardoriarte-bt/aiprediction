<template>
  <div class="pt fadein">
    <Breadcrumb :items="breadcrumb" />
    <header class="pt-head">
      <div>
        <div class="eyebrow">{{ $t(`clients.tabs.${tabKey}`) }}</div>
        <h1 class="h-1 pt-title">{{ $t(helperKey) }}</h1>
      </div>
    </header>

    <Card tone="tonal" class="pt-card">
      <p class="pt-soon">{{ $t('clients.scopedSoon') }}</p>
      <p class="pt-hint">{{ $t('clients.scopedHint') }}</p>
    </Card>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Breadcrumb from '../../components/shell/Breadcrumb.vue'
import Card from '../../components/ui/Card.vue'

const props = defineProps({
  client: { type: Object, required: true },
  tabKey: { type: String, required: true }, // 'reports' | 'simulations' | 'settings'
  helperKey: { type: String, required: true }
})

const { t } = useI18n()

const breadcrumb = computed(() => [
  { label: t('side.clients'), to: '/' },
  { label: props.client.name, to: `/clients/${props.client.client_id}/overview` },
  { label: t(`clients.tabs.${props.tabKey}`) }
])
</script>

<style scoped>
.pt-head { margin-bottom: 22px; }
.pt-title { margin: 4px 0 0; font-weight: 400; }
.pt-card { text-align: center; padding: 48px 24px !important; }
.pt-soon {
  color: var(--ink);
  font-family: var(--serif);
  font-size: 18px;
  margin: 0 0 8px;
}
.pt-hint {
  color: var(--ink-3);
  font-size: 13px;
  margin: 0;
  max-width: 440px;
  margin-inline: auto;
}
</style>
