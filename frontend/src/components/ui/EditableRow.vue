<template>
  <div class="er-row">
    <div class="er-label-row">
      <span class="label">{{ label }}</span>
      <button
        v-if="!editing"
        type="button"
        class="er-edit"
        @click="enterEdit"
        :aria-label="$t('common.edit') || 'Edit'"
      >
        <Icon name="edit" :size="13" />
        <span>{{ editLabel }}</span>
      </button>
    </div>

    <p v-if="!editing" class="er-value">
      {{ value || placeholderEmpty }}
    </p>

    <div v-else class="er-edit-block">
      <textarea
        v-if="multiline"
        ref="input"
        v-model="draft"
        rows="3"
        class="er-input"
        :placeholder="placeholder"
        @keydown.escape="cancel"
        @keydown.meta.enter="commit"
        @keydown.ctrl.enter="commit"
      />
      <input
        v-else
        ref="input"
        v-model="draft"
        type="text"
        class="er-input"
        :placeholder="placeholder"
        @keydown.escape="cancel"
        @keydown.enter="commit"
      />
      <div class="er-actions">
        <button
          type="button"
          class="er-cancel"
          @click="cancel"
          :disabled="saving"
        >
          {{ $t('common.cancel') }}
        </button>
        <button
          type="button"
          class="er-save"
          @click="commit"
          :disabled="saving || draft === value"
        >
          {{ saving ? $t('common.loading') : $t('common.confirm') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import Icon from './Icon.vue'

const props = defineProps({
  label: { type: String, required: true },
  value: { type: String, default: '' },
  field: { type: String, required: true },
  multiline: { type: Boolean, default: false },
  placeholder: { type: String, default: '' },
  saving: { type: Boolean, default: false }
})

const emit = defineEmits(['save'])

const { t } = useI18n()

const editing = ref(false)
const draft = ref(props.value)
const input = ref(null)

const editLabel = computed(() => t('common.edit') || 'Edit')
const placeholderEmpty = computed(() => t('common.none') || '—')

const enterEdit = async () => {
  draft.value = props.value
  editing.value = true
  await nextTick()
  if (input.value) {
    input.value.focus()
    if (typeof input.value.select === 'function') input.value.select()
  }
}

const cancel = () => {
  editing.value = false
  draft.value = props.value
}

const commit = () => {
  if (props.saving) return
  editing.value = false
  emit('save', (draft.value || '').trim())
}
</script>

<style scoped>
.er-row {
  padding: 12px 0;
  border-bottom: 1px solid var(--line);
}
.er-row:last-of-type { border-bottom: 0; }

.er-label-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 4px;
}

.er-edit {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 10px;
  border: 1px solid var(--line);
  background: var(--surface);
  color: var(--ink-3);
  border-radius: var(--r-sm);
  font-size: 11px;
  cursor: pointer;
  font-family: inherit;
  letter-spacing: 0.03em;
  text-transform: uppercase;
  transition: background 0.12s, color 0.12s, border-color 0.12s;
}
.er-edit:hover {
  background: var(--surface-2);
  color: var(--ink);
  border-color: var(--line-2);
}

.er-value {
  margin: 4px 0 0;
  color: var(--ink);
  white-space: pre-wrap;
  line-height: 1.55;
  font-size: 14px;
}

.er-edit-block {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 6px;
}

.er-input {
  width: 100%;
  border: 1px solid var(--line-2);
  border-radius: var(--r-sm);
  padding: 9px 11px;
  font-family: inherit;
  font-size: 14px;
  background: var(--surface);
  color: var(--ink);
  box-sizing: border-box;
  resize: vertical;
}
.er-input:focus { outline: none; border-color: var(--signal); }

.er-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.er-cancel,
.er-save {
  padding: 6px 14px;
  border-radius: var(--r-sm);
  border: 1px solid var(--line-2);
  background: var(--surface);
  color: var(--ink);
  font-family: inherit;
  font-size: 13px;
  cursor: pointer;
  transition: background 0.12s, border-color 0.12s;
}
.er-cancel:hover { background: var(--surface-2); }
.er-save {
  background: var(--ink);
  color: var(--bg);
  border-color: var(--ink);
}
.er-save:hover { background: var(--ink-2); border-color: var(--ink-2); }
.er-save:disabled,
.er-cancel:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
