<template>
  <div class="st fadein">
    <Breadcrumb :items="breadcrumb" />
    <header class="st-head">
      <div>
        <div class="eyebrow">{{ $t('clients.tabs.settings') }}</div>
        <h1 class="h-1 st-title">{{ client.name }}</h1>
      </div>
      <span class="mono st-id">/{{ client.slug }} · {{ client.client_id }}</span>
    </header>

    <Card class="st-card">
      <div class="kv">
        <EditableRow
          :label="$t('clients.fields.name')"
          :value="form.name"
          field="name"
          :saving="savingField === 'name'"
          @save="(val) => save('name', val)"
        />
        <EditableRow
          :label="$t('clients.fields.industry')"
          :value="form.industry"
          field="industry"
          :saving="savingField === 'industry'"
          :placeholder="$t('clients.fields.industryPh')"
          @save="(val) => save('industry', val)"
        />
        <EditableRow
          :label="$t('clients.fields.description')"
          :value="form.description"
          field="description"
          multiline
          :saving="savingField === 'description'"
          :placeholder="$t('clients.fields.descriptionPh')"
          @save="(val) => save('description', val)"
        />
        <EditableRow
          :label="$t('clients.fields.brandGuidelines')"
          :value="form.brand_guidelines"
          field="brand_guidelines"
          multiline
          :saving="savingField === 'brand_guidelines'"
          :placeholder="$t('clients.fields.brandGuidelinesPh')"
          @save="(val) => save('brand_guidelines', val)"
        />

        <div class="kv-row">
          <span class="label">{{ $t('clients.fields.metadata') }}</span>
          <pre class="kv-value mono code-block">{{ JSON.stringify(client.metadata || {}, null, 2) }}</pre>
        </div>
        <div class="kv-row">
          <span class="label">{{ $t('clients.fields.graphId') }}</span>
          <p class="kv-value mono">{{ client.graph_id || $t('clients.graphPending') }}</p>
        </div>
      </div>

      <div v-if="lastSaveAt" class="st-saved">
        {{ $t('clients.settings.saved', { at: lastSaveAt }) }}
      </div>
      <div v-if="error" class="error-inline">{{ error }}</div>
    </Card>
  </div>
</template>

<script setup>
import { reactive, ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { updateClient } from '../../api/clients'
import Breadcrumb from '../../components/shell/Breadcrumb.vue'
import Card from '../../components/ui/Card.vue'
import EditableRow from '../../components/ui/EditableRow.vue'

const props = defineProps({
  client: { type: Object, required: true }
})
const emit = defineEmits(['client-updated'])

const { t } = useI18n()

const form = reactive({
  name: props.client.name || '',
  industry: props.client.industry || '',
  description: props.client.description || '',
  brand_guidelines: props.client.brand_guidelines || ''
})

watch(
  () => props.client,
  (c) => {
    form.name = c?.name || ''
    form.industry = c?.industry || ''
    form.description = c?.description || ''
    form.brand_guidelines = c?.brand_guidelines || ''
  }
)

const savingField = ref('')
const error = ref('')
const lastSaveAt = ref('')

const breadcrumb = computed(() => [
  { label: t('side.clients'), to: '/' },
  { label: props.client.name, to: `/clients/${props.client.client_id}/overview` },
  { label: t('clients.tabs.settings') }
])

const save = async (field, value) => {
  savingField.value = field
  error.value = ''
  try {
    const res = await updateClient(props.client.client_id, { [field]: value || null })
    form[field] = value
    if (res.data) emit('client-updated', res.data)
    lastSaveAt.value = new Date().toLocaleTimeString()
  } catch (err) {
    error.value = err?.response?.data?.error || err.message || 'Error'
  } finally {
    savingField.value = ''
  }
}
</script>

<style scoped>
.st-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 22px;
  flex-wrap: wrap;
}
.st-title { margin: 4px 0 0; font-weight: 400; }
.st-id {
  font-size: 11px;
  color: var(--ink-4);
  letter-spacing: 0.06em;
}

.st-card { display: flex; flex-direction: column; gap: 0; }

.kv-row { padding: 12px 0; border-bottom: 1px solid var(--line); }
.kv-row:last-child { border-bottom: 0; }
.kv-value { margin: 4px 0 0; color: var(--ink); white-space: pre-wrap; line-height: 1.55; font-size: 14px; }

.code-block {
  font-size: 12px;
  background: var(--surface-2);
  padding: 10px 12px;
  border-radius: var(--r-sm);
  border: 1px solid var(--line);
}

.st-saved {
  margin-top: 14px;
  font-size: 11px;
  color: var(--ok);
  letter-spacing: 0.04em;
}

.error-inline {
  margin-top: 14px;
  color: var(--bad);
  background: var(--bad-soft);
  border: 1px solid var(--bad-soft);
  padding: 8px 12px;
  border-radius: var(--r-sm);
  font-size: 13px;
}
</style>
