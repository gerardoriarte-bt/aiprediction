<template>
  <div ref="root" class="gc-root" :class="{ 'gc-mini': mini }">
    <svg ref="svg" class="gc-svg" :viewBox="viewBox" preserveAspectRatio="xMidYMid meet">
      <g ref="zoomLayer">
        <!-- Edges -->
        <g class="gc-edges">
          <line
            v-for="(e, i) in renderedEdges"
            :key="`e-${e.id || i}`"
            :x1="e.source.x"
            :y1="e.source.y"
            :x2="e.target.x"
            :y2="e.target.y"
            :stroke="edgeColor(e)"
            :stroke-width="edgeWidth(e)"
            :stroke-dasharray="e.kind === 'inferred' ? '3 4' : ''"
            :stroke-opacity="edgeOpacity(e)"
          />
        </g>

        <!-- Nodes -->
        <g class="gc-nodes">
          <g
            v-for="n in renderedNodes"
            :key="n.id"
            :transform="`translate(${n.x},${n.y})`"
            :class="['gc-node', { dim: dimNodeId(n) }]"
            @mouseenter="hover = n.id"
            @mouseleave="hover = null"
            @click="onClick(n)"
          >
            <circle
              :r="nodeRadius(n)"
              :fill="nodeColor(n)"
              :stroke="strokeFor(n)"
              :stroke-width="n.id === selectedId ? 3 : 1"
            />
            <text
              v-if="!mini"
              class="gc-label"
              :y="nodeRadius(n) + 13"
              text-anchor="middle"
            >
              {{ truncate(n.label, 22) }}
            </text>
          </g>
        </g>
      </g>
    </svg>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import {
  forceSimulation,
  forceLink,
  forceManyBody,
  forceCenter,
  forceCollide,
  zoom as d3Zoom,
  zoomIdentity,
  drag as d3Drag,
  select as d3Select
} from 'd3'

const props = defineProps({
  data: { type: Object, required: true }, // { nodes, edges }
  width: { type: Number, default: 720 },
  height: { type: Number, default: 480 },
  mini: { type: Boolean, default: false },
  filterTypes: { type: Object, default: null },     // { Brand: true, ... }
  query: { type: String, default: '' },
  selectedId: { type: String, default: '' }
})

const emit = defineEmits(['select', 'hover'])

// Lo.Bueno warm palette mapped to entity types.
const TYPE_COLORS = {
  Brand:        '#1f3a2e',
  Audience:     '#2d5240',
  Channel:      '#d97706',
  Claim:        '#6b3a52',
  Competitor:   '#8b2a1f',
  Study:        '#3d3a32',
  Metric:       '#a8650b',
  Risk:         '#b91c1c',
  Person:       '#475569',
  Organization: '#1a1814',
  Product:      '#1f3a2e',
  Entity:       '#9a9686'
}

const root = ref(null)
const svg = ref(null)
const zoomLayer = ref(null)

const renderedNodes = ref([])
const renderedEdges = ref([])
const hover = ref(null)
const transform = ref(zoomIdentity)

let simulation = null
let zoomBehavior = null

const viewBox = computed(() => `0 0 ${props.width} ${props.height}`)

// — Filtering ---------------------------------------------------------

const filteredNodes = computed(() => {
  const q = (props.query || '').trim().toLowerCase()
  return (props.data?.nodes || []).filter((n) => {
    if (props.filterTypes && props.filterTypes[n.type] === false) return false
    if (q && !(n.label || '').toLowerCase().includes(q)) return false
    return true
  })
})

const filteredEdges = computed(() => {
  const ids = new Set(filteredNodes.value.map((n) => n.id))
  return (props.data?.edges || []).filter((e) =>
    ids.has(typeof e.source === 'object' ? e.source.id : e.source) &&
    ids.has(typeof e.target === 'object' ? e.target.id : e.target)
  )
})

// — Hover / selection neighbourhood -----------------------------------

const neighbourhood = computed(() => {
  const id = props.selectedId || hover.value
  if (!id) return null
  const set = new Set([id])
  for (const e of renderedEdges.value) {
    const sid = typeof e.source === 'object' ? e.source.id : e.source
    const tid = typeof e.target === 'object' ? e.target.id : e.target
    if (sid === id) set.add(tid)
    if (tid === id) set.add(sid)
  }
  return set
})

const dimNodeId = (n) => neighbourhood.value && !neighbourhood.value.has(n.id)

// — Encoding ----------------------------------------------------------

const nodeColor = (n) => TYPE_COLORS[n.type] || TYPE_COLORS.Entity

const nodeRadius = (n) => {
  const w = Number(n.weight) || 0
  if (props.mini) return Math.max(3, Math.min(8, 3 + w * 0.6))
  return Math.max(6, Math.min(22, 6 + w * 1.2))
}

const strokeFor = (n) => {
  if (n.id === props.selectedId) return '#1a1814'
  if (n.id === hover.value) return '#1a1814'
  return 'rgba(255,255,255,0.85)'
}

const edgeColor = (e) => {
  if (neighbourhood.value) {
    const sid = typeof e.source === 'object' ? e.source.id : e.source
    const tid = typeof e.target === 'object' ? e.target.id : e.target
    if (!neighbourhood.value.has(sid) || !neighbourhood.value.has(tid)) return '#d4cebd'
  }
  return e.kind === 'inferred' ? '#9a9686' : '#6b6757'
}

const edgeOpacity = (e) => {
  if (e.active === false) return 0.35
  if (neighbourhood.value) {
    const sid = typeof e.source === 'object' ? e.source.id : e.source
    const tid = typeof e.target === 'object' ? e.target.id : e.target
    if (!neighbourhood.value.has(sid) || !neighbourhood.value.has(tid)) return 0.25
  }
  return 1
}

const edgeWidth = (e) => (e.kind === 'inferred' ? 1 : 1.4)

const truncate = (s, n) => (s && s.length > n ? s.slice(0, n - 1) + '…' : s)

const onClick = (n) => emit('select', n)

watch(() => hover.value, (v) => emit('hover', v))

// — Simulation --------------------------------------------------------

const buildSimulation = () => {
  if (simulation) {
    simulation.stop()
  }

  // Deep-copy nodes so D3 can mutate x/y without leaking back to props.
  const nodes = filteredNodes.value.map((n) => ({ ...n }))
  const idx = new Map(nodes.map((n) => [n.id, n]))
  const edges = filteredEdges.value.map((e) => {
    const sid = typeof e.source === 'object' ? e.source.id : e.source
    const tid = typeof e.target === 'object' ? e.target.id : e.target
    return {
      id: e.id,
      source: idx.get(sid),
      target: idx.get(tid),
      kind: e.kind,
      name: e.name,
      fact: e.fact,
      active: e.active
    }
  }).filter((e) => e.source && e.target)

  renderedNodes.value = nodes
  renderedEdges.value = edges

  simulation = forceSimulation(nodes)
    .force(
      'link',
      forceLink(edges).id((d) => d.id).distance(props.mini ? 60 : 110).strength(0.55)
    )
    .force('charge', forceManyBody().strength(props.mini ? -120 : -260))
    .force('center', forceCenter(props.width / 2, props.height / 2))
    .force(
      'collide',
      forceCollide((n) => nodeRadius(n) + (props.mini ? 4 : 10))
    )
    .alpha(1)
    .alphaDecay(0.05)
    .on('tick', () => {
      // Trigger reactive update — Vue diff is fine for ~150 nodes.
      renderedNodes.value = [...nodes]
      renderedEdges.value = [...edges]
    })

  if (!props.mini) {
    bindDrag(nodes)
    bindZoom()
  } else {
    // Mini view doesn't need interactions: stop after a short layout pass.
    setTimeout(() => simulation && simulation.stop(), 1500)
  }
}

const bindZoom = () => {
  if (!svg.value) return
  zoomBehavior = d3Zoom()
    .scaleExtent([0.4, 4])
    .on('zoom', (ev) => {
      transform.value = ev.transform
      if (zoomLayer.value) {
        zoomLayer.value.setAttribute(
          'transform',
          `translate(${ev.transform.x},${ev.transform.y}) scale(${ev.transform.k})`
        )
      }
    })
  d3Select(svg.value).call(zoomBehavior)
}

const bindDrag = (nodes) => {
  if (!svg.value) return
  const dragBehavior = d3Drag()
    .subject((event) => {
      const { x, y } = pointerToWorld(event)
      // Find closest node within tolerance.
      let best = null
      let bestDist = Infinity
      for (const n of nodes) {
        const dx = n.x - x, dy = n.y - y
        const d = dx * dx + dy * dy
        if (d < bestDist) { bestDist = d; best = n }
      }
      const r = best ? nodeRadius(best) + 4 : 0
      if (best && bestDist < r * r) return best
      return null
    })
    .on('start', (event) => {
      if (!event.subject) return
      if (!event.active) simulation.alphaTarget(0.3).restart()
      event.subject.fx = event.subject.x
      event.subject.fy = event.subject.y
    })
    .on('drag', (event) => {
      if (!event.subject) return
      const { x, y } = pointerToWorld(event)
      event.subject.fx = x
      event.subject.fy = y
    })
    .on('end', (event) => {
      if (!event.subject) return
      if (!event.active) simulation.alphaTarget(0)
      event.subject.fx = null
      event.subject.fy = null
    })
  d3Select(svg.value).call(dragBehavior)
}

const pointerToWorld = (event) => {
  // Inverse of the current zoom transform.
  const t = transform.value
  return {
    x: (event.x - t.x) / t.k,
    y: (event.y - t.y) / t.k
  }
}

// — Lifecycle ---------------------------------------------------------

onMounted(buildSimulation)
onBeforeUnmount(() => simulation && simulation.stop())

watch(
  () => [props.data, props.filterTypes, props.query],
  () => buildSimulation(),
  { deep: true }
)
</script>

<style scoped>
.gc-root {
  width: 100%;
  height: 100%;
  background: var(--surface-2);
  border-radius: var(--r);
  position: relative;
  overflow: hidden;
}

.gc-mini { background: var(--surface-2); }

.gc-svg {
  width: 100%;
  height: 100%;
  display: block;
  cursor: grab;
}
.gc-svg:active { cursor: grabbing; }

.gc-node { cursor: pointer; }
.gc-node.dim { opacity: 0.25; }
.gc-node:hover circle { filter: brightness(1.05); }

.gc-label {
  font-family: var(--mono);
  font-size: 10px;
  letter-spacing: 0.04em;
  fill: var(--ink-2);
  pointer-events: none;
}

.gc-edges line { transition: stroke-opacity 0.15s; }
</style>
