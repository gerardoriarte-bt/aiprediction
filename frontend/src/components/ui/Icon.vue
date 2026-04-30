<template>
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    :stroke-width="stroke"
    stroke-linecap="round"
    stroke-linejoin="round"
    role="img"
    :aria-label="label || name"
  >
    <g v-html="path"></g>
  </svg>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  name: { type: String, required: true },
  size: { type: [Number, String], default: 16 },
  stroke: { type: [Number, String], default: 1.6 },
  label: { type: String, default: '' }
})

// Single source of truth for the line-icon set used across the workspace.
// Same shapes as the design mockup (Prediction AI Design/shell.jsx Icon).
const ICONS = {
  home:      '<path d="M3 11.5 12 4l9 7.5"/><path d="M5 10v10h14V10"/>',
  grid:      '<rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/>',
  context:   '<circle cx="12" cy="12" r="3"/><circle cx="5" cy="6" r="2"/><circle cx="19" cy="7" r="2"/><circle cx="6" cy="18" r="2"/><circle cx="18" cy="17" r="2"/><path d="M9.6 11 7 7m7.5 4 3-3M9.5 13.5 8 17m6.6-4 3 3"/>',
  tests:     '<path d="M4 20V8m6 12V4m6 16v-9m6 9V12"/>',
  sims:      '<path d="M3 12h4l2-7 4 14 2-7h6"/>',
  report:    '<path d="M6 3h9l3 3v15H6z"/><path d="M9 8h6M9 12h6M9 16h4"/>',
  settings:  '<circle cx="12" cy="12" r="3"/><path d="M19 12a7 7 0 0 0-.1-1.1l2-1.5-2-3.4-2.3.8a7 7 0 0 0-2-1.2L14 3h-4l-.6 2.6a7 7 0 0 0-2 1.2l-2.3-.8-2 3.4 2 1.5A7 7 0 0 0 5 12c0 .4 0 .7.1 1.1l-2 1.5 2 3.4 2.3-.8a7 7 0 0 0 2 1.2L10 21h4l.6-2.6a7 7 0 0 0 2-1.2l2.3.8 2-3.4-2-1.5c.1-.4.1-.7.1-1.1z"/>',
  search:    '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
  plus:      '<path d="M12 5v14M5 12h14"/>',
  'arrow-r': '<path d="M5 12h14m-5-6 6 6-6 6"/>',
  'arrow-l': '<path d="M19 12H5m6-6-6 6 6 6"/>',
  'chevron-d':'<path d="m6 9 6 6 6-6"/>',
  'chevron-r':'<path d="m9 6 6 6-6 6"/>',
  edit:      '<path d="M4 20h4l10-10-4-4L4 16v4z"/><path d="m13 6 4 4"/>',
  upload:    '<path d="M12 16V4m-5 5 5-5 5 5"/><path d="M4 17v3h16v-3"/>',
  spark:     '<path d="m12 4 1.8 5.2L19 11l-5.2 1.8L12 18l-1.8-5.2L5 11l5.2-1.8z"/>',
  book:      '<path d="M4 4h6a3 3 0 0 1 3 3v13a2 2 0 0 0-2-2H4z"/><path d="M20 4h-6a3 3 0 0 0-3 3v13a2 2 0 0 1 2-2h7z"/>',
  key:       '<circle cx="8" cy="14" r="4"/><path d="m11 11 9-9m-3 3 3 3m-6 0 3 3"/>',
  expand:    '<path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5"/>',
  graph:     '<circle cx="6" cy="6" r="2"/><circle cx="18" cy="6" r="2"/><circle cx="12" cy="14" r="2"/><circle cx="5" cy="19" r="2"/><circle cx="19" cy="18" r="2"/><path d="M7.5 7.5 11 13m6.5-5.5L13 13m-2 3-5 2.5M13 15.5l5 2"/>',
  check:     '<path d="m5 12 5 5L20 7"/>',
  x:         '<path d="m6 6 12 12M6 18 18 6"/>',
  filter:    '<path d="M4 5h16l-6 8v6l-4-2v-4z"/>',
  download:  '<path d="M12 4v12m-5-5 5 5 5-5"/><path d="M4 17v3h16v-3"/>',
  share:     '<circle cx="6" cy="12" r="2.5"/><circle cx="18" cy="6" r="2.5"/><circle cx="18" cy="18" r="2.5"/><path d="m8 11 8-4M8 13l8 4"/>',
  play:      '<path d="M7 4v16l13-8z"/>',
  doc:       '<path d="M6 3h8l4 4v14H6z"/><path d="M14 3v4h4"/>',
  star:      '<path d="m12 3 2.6 6 6.4.5-4.9 4.2 1.5 6.3L12 16.7 6.4 20l1.5-6.3L3 9.5 9.4 9z"/>',
  circle:    '<circle cx="12" cy="12" r="6"/>',
  users:     '<circle cx="9" cy="8" r="3"/><path d="M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6"/><circle cx="17" cy="9" r="2.5"/><path d="M14 20c0-3 2-5 5-5"/>',
  lang:      '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/>',
  trash:     '<path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13"/>',
  link:      '<path d="M10 14a4 4 0 0 0 5.6 0l3-3a4 4 0 0 0-5.6-5.6L11 7"/><path d="M14 10a4 4 0 0 0-5.6 0l-3 3a4 4 0 0 0 5.6 5.6L13 17"/>',
  help:      '<circle cx="12" cy="12" r="9"/><path d="M9.5 9a2.5 2.5 0 1 1 3.5 2.3c-.7.3-1 .9-1 1.6V14"/><circle cx="12" cy="17" r="0.6" fill="currentColor"/>',
  copy:      '<rect x="8" y="8" width="12" height="12" rx="1.5"/><path d="M16 8V5a1 1 0 0 0-1-1H5a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h3"/>'
}

const path = computed(() => ICONS[props.name] || '')
</script>
