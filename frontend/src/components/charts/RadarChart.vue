<template>
  <svg
    :viewBox="`0 0 ${size} ${size}`"
    :width="size"
    :height="size"
    role="img"
    :aria-label="ariaLabel"
    class="radar"
  >
    <!-- Concentric grid -->
    <g class="grid">
      <polygon
        v-for="(ring, i) in rings"
        :key="`ring-${i}`"
        :points="ringPoints(ring)"
        fill="none"
        :stroke="i === rings.length - 1 ? 'var(--line-2)' : 'var(--line)'"
        stroke-width="1"
      />
      <line
        v-for="(axis, i) in axisLines"
        :key="`axis-${i}`"
        :x1="cx"
        :y1="cy"
        :x2="axis.x"
        :y2="axis.y"
        stroke="var(--line)"
        stroke-width="1"
      />
    </g>

    <!-- Variant polygons -->
    <g class="series">
      <g v-for="(v, vi) in variants" :key="`v-${vi}`">
        <polygon
          :points="seriesPoints(v.scores)"
          :fill="colorAt(vi)"
          fill-opacity="0.18"
          :stroke="colorAt(vi)"
          stroke-width="1.5"
          stroke-linejoin="round"
        />
        <circle
          v-for="(s, i) in v.scores"
          :key="`pt-${vi}-${i}`"
          :cx="pointAt(i, s).x"
          :cy="pointAt(i, s).y"
          r="3"
          :fill="colorAt(vi)"
          stroke="white"
          stroke-width="1.2"
        />
      </g>
    </g>

    <!-- Axis labels -->
    <g class="labels">
      <text
        v-for="(ax, i) in axes"
        :key="`lbl-${i}`"
        :x="labelAt(i).x"
        :y="labelAt(i).y"
        :text-anchor="labelAt(i).anchor"
        :dominant-baseline="labelAt(i).baseline"
        class="axis-label"
      >
        {{ ax }}
      </text>
    </g>

    <!-- Tick numbers (only at the outermost ring corners on top axis) -->
    <text
      v-if="showMax"
      :x="cx"
      :y="cy - radius - 6"
      text-anchor="middle"
      class="tick-label"
    >
      {{ max }}
    </text>
  </svg>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  /** Axis labels, in order. Length defines the number of axes. */
  axes: { type: Array, required: true },
  /**
   * Variants with scores aligned to axes.
   * [{ id, scores: [n1, n2, n3, n4], color? }]
   */
  variants: { type: Array, required: true },
  size: { type: [Number, String], default: 320 },
  max: { type: Number, default: 100 },
  rings: { type: Array, default: () => [25, 50, 75, 100] },
  /** Color palette used when variant.color is not set. */
  palette: {
    type: Array,
    default: () => ['#1f3a2e', '#d97706', '#6b3a52', '#2d5240', '#a8650b']
  },
  ariaLabel: { type: String, default: 'Radar comparison' },
  showMax: { type: Boolean, default: true }
})

const cx = computed(() => Number(props.size) / 2)
const cy = computed(() => Number(props.size) / 2)
// Padding leaves room for axis labels.
const radius = computed(() => Number(props.size) / 2 - 38)

const angles = computed(() => {
  const n = props.axes.length
  const out = []
  for (let i = 0; i < n; i++) {
    // Start at top (-PI/2) so the first axis points up.
    const ang = -Math.PI / 2 + (i * 2 * Math.PI) / n
    out.push(ang)
  }
  return out
})

const colorAt = (i) => props.variants[i]?.color || props.palette[i % props.palette.length]

const pointAt = (axisIndex, value) => {
  const ang = angles.value[axisIndex]
  const ratio = Math.max(0, Math.min(1, Number(value) / props.max))
  return {
    x: cx.value + Math.cos(ang) * radius.value * ratio,
    y: cy.value + Math.sin(ang) * radius.value * ratio
  }
}

const ringPoints = (level) => {
  const ratio = level / props.max
  return angles.value
    .map((ang) => {
      const x = cx.value + Math.cos(ang) * radius.value * ratio
      const y = cy.value + Math.sin(ang) * radius.value * ratio
      return `${x.toFixed(2)},${y.toFixed(2)}`
    })
    .join(' ')
}

const seriesPoints = (scores) => {
  return scores
    .map((s, i) => {
      const p = pointAt(i, s)
      return `${p.x.toFixed(2)},${p.y.toFixed(2)}`
    })
    .join(' ')
}

const axisLines = computed(() =>
  angles.value.map((ang) => ({
    x: cx.value + Math.cos(ang) * radius.value,
    y: cy.value + Math.sin(ang) * radius.value
  }))
)

const labelAt = (i) => {
  const ang = angles.value[i]
  const dist = radius.value + 18
  const x = cx.value + Math.cos(ang) * dist
  const y = cy.value + Math.sin(ang) * dist
  // Tilt anchor based on quadrant for clean alignment.
  let anchor = 'middle'
  if (Math.cos(ang) > 0.3) anchor = 'start'
  if (Math.cos(ang) < -0.3) anchor = 'end'
  let baseline = 'middle'
  if (Math.sin(ang) < -0.3) baseline = 'auto'
  if (Math.sin(ang) > 0.3) baseline = 'hanging'
  return { x, y, anchor, baseline }
}
</script>

<style scoped>
.radar { display: block; }
.axis-label {
  font-family: var(--mono);
  font-size: 10.5px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  fill: var(--ink-3);
}
.tick-label {
  font-family: var(--mono);
  font-size: 9.5px;
  fill: var(--ink-4);
}
</style>
