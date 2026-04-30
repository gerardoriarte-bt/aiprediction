<template>
  <div class="manual">
    <TopNav :all-clients="allClients" @open-cmd-k="cmdK = true" />

    <main id="main" class="manual-main" tabindex="-1">
      <aside class="manual-toc">
        <div class="toc-eyebrow">{{ $t('manual.toc') }}</div>
        <nav>
          <a
            v-for="s in sections"
            :key="s.id"
            :href="`#${s.id}`"
            :class="{ on: activeId === s.id }"
            @click.prevent="goTo(s.id)"
          >
            <span class="toc-num mono">{{ s.num }}</span>
            <span>{{ s.title }}</span>
          </a>
        </nav>
        <div class="toc-card">
          <div class="mono toc-eyebrow">{{ $t('manual.shortcuts') }}</div>
          <p>
            {{ $t('manual.shortcutsHint') }}
            <button class="toc-cmdk" @click="cmdK = true">⌘K</button>
          </p>
        </div>
      </aside>

      <article class="manual-article prose" ref="article">
        <header class="manual-hero">
          <div class="eyebrow">{{ $t('side.manual') }}</div>
          <h1>{{ $t('manual.heroTitle') }}</h1>
          <p class="lead">{{ $t('manual.heroSub') }}</p>
        </header>

        <!-- 1. How it works -->
        <section :id="sections[0].id">
          <h2>{{ sections[0].num }}. {{ sections[0].title }}</h2>
          <p v-html="content.intro"></p>
          <h3>{{ $t('manual.s1.conceptsTitle') }}</h3>
          <dl class="concepts">
            <template v-for="(item, k) in content.concepts" :key="k">
              <dt>{{ item.term }}</dt>
              <dd>{{ item.def }}</dd>
            </template>
          </dl>
        </section>

        <!-- 2. Crear un cliente -->
        <section :id="sections[1].id">
          <h2>{{ sections[1].num }}. {{ sections[1].title }}</h2>
          <ol>
            <li v-for="(step, i) in content.createClient" :key="i">{{ step }}</li>
          </ol>
        </section>

        <!-- 3. Cargar contexto -->
        <section :id="sections[2].id">
          <h2>{{ sections[2].num }}. {{ sections[2].title }}</h2>
          <p>{{ content.contextIntro }}</p>
          <h3>{{ $t('manual.s3.uploadTitle') }}</h3>
          <ul>
            <li v-for="(t, i) in content.uploadTips" :key="i">{{ t }}</li>
          </ul>
          <h3>{{ $t('manual.s3.searchTitle') }}</h3>
          <p>{{ content.searchHint }}</p>
        </section>

        <!-- 4. Creative test -->
        <section :id="sections[3].id">
          <h2>{{ sections[3].num }}. {{ sections[3].title }}</h2>
          <p>{{ content.testIntro }}</p>
          <ol>
            <li v-for="(step, i) in content.testSteps" :key="i">{{ step }}</li>
          </ol>
          <h3>{{ $t('manual.s4.readingTitle') }}</h3>
          <ul>
            <li v-for="(line, i) in content.readingTips" :key="i">{{ line }}</li>
          </ul>
        </section>

        <!-- 5. Simulación -->
        <section :id="sections[4].id">
          <h2>{{ sections[4].num }}. {{ sections[4].title }}</h2>
          <p>{{ content.simIntro }}</p>
          <ul>
            <li v-for="(line, i) in content.simTips" :key="i">{{ line }}</li>
          </ul>
        </section>

        <!-- 6. Reportes -->
        <section :id="sections[5].id">
          <h2>{{ sections[5].num }}. {{ sections[5].title }}</h2>
          <p>{{ content.reportIntro }}</p>
        </section>

        <!-- 7. Glosario -->
        <section :id="sections[6].id">
          <h2>{{ sections[6].num }}. {{ sections[6].title }}</h2>
          <dl class="concepts">
            <template v-for="(item, k) in content.glossary" :key="k">
              <dt>{{ item.term }}</dt>
              <dd>{{ item.def }}</dd>
            </template>
          </dl>
        </section>

        <!-- 8. Atajos -->
        <section :id="sections[7].id">
          <h2>{{ sections[7].num }}. {{ sections[7].title }}</h2>
          <table class="kbd-table">
            <thead>
              <tr>
                <th>{{ $t('manual.s8.keyHeader') }}</th>
                <th>{{ $t('manual.s8.actionHeader') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, i) in content.shortcuts" :key="i">
                <td><code class="kbd">{{ row.key }}</code></td>
                <td>{{ row.action }}</td>
              </tr>
            </tbody>
          </table>
        </section>

        <!-- 9. FAQ -->
        <section :id="sections[8].id">
          <h2>{{ sections[8].num }}. {{ sections[8].title }}</h2>
          <dl class="concepts">
            <template v-for="(item, k) in content.faq" :key="k">
              <dt>{{ item.q }}</dt>
              <dd>{{ item.a }}</dd>
            </template>
          </dl>
        </section>
      </article>
    </main>

    <CmdK :open="cmdK" :all-clients="allClients" @close="cmdK = false" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useI18n } from 'vue-i18n'
import TopNav from '../components/shell/TopNav.vue'
import CmdK from '../components/shell/CmdK.vue'
import { listClients } from '../api/clients'
import { useShortcuts } from '../composables/useShortcuts'

const { locale, t } = useI18n()

const allClients = ref([])
const cmdK = ref(false)
const activeId = ref('s1-concepts')
const article = ref(null)

const sections = computed(() => [
  { num: '1', id: 's1-concepts', title: t('manual.s1.title') },
  { num: '2', id: 's2-client',   title: t('manual.s2.title') },
  { num: '3', id: 's3-context',  title: t('manual.s3.title') },
  { num: '4', id: 's4-test',     title: t('manual.s4.title') },
  { num: '5', id: 's5-sim',      title: t('manual.s5.title') },
  { num: '6', id: 's6-report',   title: t('manual.s6.title') },
  { num: '7', id: 's7-glossary', title: t('manual.s7.title') },
  { num: '8', id: 's8-shortcuts',title: t('manual.s8.title') },
  { num: '9', id: 's9-faq',      title: t('manual.s9.title') }
])

// Bilingual prose. Kept inline (instead of dozens of i18n keys) so the
// editor experience for copy is direct and the strings stay together.
const ES = {
  intro:
    'Sintetic Prediction AI es un workspace por cliente para planners y equipos de medios digitales. ' +
    'Cada cuenta tiene su propio espacio con contexto de marca, creative tests, simulaciones y reportes. ' +
    'La idea: <strong>decidir más rápido y con evidencia</strong>, sin perder historial entre campañas.',
  concepts: [
    { term: 'Cliente', def: 'Cuenta de la agencia. Agrupa todo el trabajo: contexto, tests, sims, reportes.' },
    { term: 'Brand context', def: 'La memoria del cliente: briefs, estudios, copy y métricas que lo definen.' },
    { term: 'Grafo de conocimiento', def: 'Visualización de entidades y relaciones extraídas del contexto. Cada cliente tiene el suyo.' },
    { term: 'Creative test', def: 'Comparación 2-8 variantes creativas para una audiencia. Devuelve un ganador con recomendación.' },
    { term: 'Simulación', def: 'Stress-test de una decisión con agentes sintéticos en redes sociales.' },
    { term: 'Reporte', def: 'Documento de hallazgos generado tras una simulación o test.' }
  ],
  createClient: [
    'Desde la home, click en + Nuevo cliente.',
    'Completa nombre y opcionalmente industria, descripción y lineamientos de marca.',
    'Slug se genera automáticamente desde el nombre y debe ser único.',
    'Al crear, te lleva al workspace del cliente, donde la pestaña Resumen es el punto de partida.'
  ],
  contextIntro:
    'El brand context es lo que hace que el resto de funciones (tests, sims, reportes) den respuestas inteligentes. ' +
    'Cuanto más rico el contexto, mejor el output.',
  uploadTips: [
    'Formatos soportados: PDF, Markdown, TXT. Cada archivo se vuelve un episodio independiente en el grafo.',
    'Buenos candidatos: briefs, estudios cualitativos/cuantitativos, manual de marca, transcripciones de focus group.',
    'Evita subir secretos o credenciales. El contenido se procesa con LLM.',
    'También puedes pegar texto directo si no tienes el archivo a mano.'
  ],
  searchHint:
    'El buscador del cliente responde preguntas en lenguaje natural sobre los episodios cargados. ' +
    'Pregunta como hablarías con un colega: "¿qué dijo el estudio Q1 sobre pricing?"',
  testIntro:
    'Un creative test compara 2 a 8 variantes creativas (copy, claim, CTA) bajo el mismo brief. ' +
    'En 2-3 minutos obtienes un ranking, scorecards, evidencia y un plan de activación.',
  testSteps: [
    'Desde el cliente, abre la pestaña Creative tests y click en + Nuevo creative test.',
    'Llena el brief: objetivo, escenario, audiencia, variantes (con headline mínimo), canales y métricas.',
    'Click en Iniciar prueba. Verás el progreso en cuatro etapas.',
    'Cuando complete, te lleva directo al reporte con la decisión arriba.'
  ],
  readingTips: [
    'El bloque oscuro es la decisión: variante ganadora + recomendación + próxima acción.',
    'El radar muestra las 4 dimensiones de scoring superpuestas para comparar fortaleza/debilidad.',
    'Los scorecards detallan cada variante con su recomendación individual.',
    'La evidencia cita hechos del grafo del cliente que respaldan la decisión.',
    'El plan de activación está dividido en 0-7d, 30d y 60-90d.'
  ],
  simIntro:
    'Las simulaciones lanzan agentes sintéticos en plataformas (Twitter, Reddit) que reaccionan a un contenido. ' +
    'Útil para anticipar sentimiento y ajustar narrativa antes de lanzar campaña real.',
  simTips: [
    'Cada simulación cuesta tokens de LLM. Estima ~$5 USD por corrida típica.',
    'La simulación tarda minutos a horas dependiendo de la cantidad de agentes y rondas.',
    'Los reportes resultantes citan al agente y plataforma de cada hallazgo.'
  ],
  reportIntro:
    'Los reportes consolidan hallazgos de una simulación en un documento accionable. ' +
    'Incluyen resumen ejecutivo, análisis por segmento, riesgos y recomendaciones por canal. ' +
    'Se exportan como PDF para presentación a comité.',
  glossary: [
    { term: 'Activar', def: 'Recomendación: confianza suficiente para lanzar. Briefar al equipo de canal.' },
    { term: 'Iterar', def: 'Recomendación: prometedora pero no lista. Ajustar copy/CTA antes de invertir budget.' },
    { term: 'Descartar', def: 'Recomendación: la evidencia combinada no respalda lanzarla.' },
    { term: 'Riesgo bajo / medio / alto', def: 'Probabilidad de que la pieza dañe la marca. Alto = revisar antes de lanzar.' },
    { term: 'Episodio', def: 'Una unidad de contenido ingestada al grafo. Suele corresponder a un archivo o un texto pegado.' },
    { term: 'Entidad', def: 'Nodo del grafo. Persona, marca, audiencia, claim, etc.' },
    { term: 'Relación', def: 'Arista del grafo. Conecta dos entidades con un tipo (TARGETS, COMPETES_WITH, …).' }
  ],
  shortcuts: [
    { key: '⌘K', action: 'Abrir búsqueda global (clientes, tests, manual)' },
    { key: 'Esc', action: 'Cerrar modal o panel abierto' },
    { key: 'G luego C', action: 'Ir a Clientes' },
    { key: 'G luego M', action: 'Ir al Manual' },
    { key: '?', action: 'Abrir esta página de atajos' }
  ],
  faq: [
    {
      q: '¿Mis datos salen del workspace?',
      a:
        'El procesamiento envía texto al modelo LLM configurado (OpenAI o Ollama local). ' +
        'Si necesitas zero data egress, usa Ollama local; si usas OpenAI, los datos salen pero no se reentrenan.'
    },
    {
      q: '¿Puedo borrar un cliente?',
      a:
        'Sí, pero borra todos los tests y episodios asociados. El "Default workspace" no se puede borrar.'
    },
    {
      q: '¿Por qué un test tarda tanto en modo live?',
      a:
        'El modo live llama al LLM por cada variante y eje. En mock se usa un generador determinista para validar UX en segundos.'
    }
  ]
}

const EN = {
  intro:
    'Sintetic Prediction AI is a per-client workspace for planners and digital media teams. ' +
    'Every account has its own space with brand context, creative tests, simulations and reports. ' +
    'The point: <strong>decide faster and with evidence</strong>, without losing history across campaigns.',
  concepts: [
    { term: 'Client', def: 'An agency account. Groups all the work: context, tests, sims, reports.' },
    { term: 'Brand context', def: "The client's memory: briefs, studies, copy and metrics that define it." },
    { term: 'Knowledge graph', def: 'Visualisation of entities and relationships pulled from context. Each client owns one.' },
    { term: 'Creative test', def: 'Compares 2–8 creative variants for an audience. Returns a winner with a recommendation.' },
    { term: 'Simulation', def: 'Stress-test of a decision using synthetic agents on social media.' },
    { term: 'Report', def: 'Document of findings generated after a simulation or test.' }
  ],
  createClient: [
    'From the home, click + New client.',
    'Fill in name and optionally industry, description and brand guidelines.',
    'Slug is generated from the name and must be unique.',
    'On creation you land in the client workspace; the Overview tab is the starting point.'
  ],
  contextIntro:
    'Brand context is what makes the rest of the platform (tests, sims, reports) give intelligent answers. ' +
    'The richer the context, the better the output.',
  uploadTips: [
    'Supported formats: PDF, Markdown, TXT. Each file becomes an independent episode in the graph.',
    'Good candidates: briefs, qualitative/quantitative studies, brand book, focus-group transcripts.',
    'Avoid uploading secrets or credentials. Content goes through an LLM.',
    "You can also paste text directly when you don't have the file at hand."
  ],
  searchHint:
    "The client search answers natural-language questions across the ingested episodes. " +
    "Ask like you'd ask a teammate: \"what did the Q1 study say about pricing?\"",
  testIntro:
    'A creative test compares 2 to 8 creative variants (copy, claim, CTA) under the same brief. ' +
    'In 2–3 minutes you get a ranking, scorecards, evidence and an activation plan.',
  testSteps: [
    'From the client, open the Creative tests tab and click + New creative test.',
    'Fill the brief: goal, scenario, audience, variants (with at least a headline), channels and metrics.',
    'Click Start test. You will see four progress stages.',
    'When done you land directly in the report with the decision at the top.'
  ],
  readingTips: [
    'The dark hero is the decision: winning variant + recommendation + next action.',
    'The radar shows the 4 scoring dimensions overlapped so you can compare strengths/weaknesses at a glance.',
    'Scorecards expand each variant with its individual recommendation.',
    "Evidence cites facts from the client's graph backing the decision.",
    'The activation plan is split into 0–7d, 30d and 60–90d horizons.'
  ],
  simIntro:
    'Simulations launch synthetic agents on platforms (Twitter, Reddit) reacting to a piece of content. ' +
    'Useful to anticipate sentiment and adjust narrative before going live.',
  simTips: [
    'Each simulation burns LLM tokens. Budget about $5 USD per typical run.',
    'A simulation takes minutes to hours depending on agent count and rounds.',
    'Resulting reports cite the agent and platform of each finding.'
  ],
  reportIntro:
    'Reports consolidate simulation findings into an actionable document. ' +
    'They include exec summary, segment analysis, risks and channel recommendations. ' +
    'Export to PDF for committee review.',
  glossary: [
    { term: 'Activate', def: 'Recommendation: confidence is high enough to launch. Brief the channel team.' },
    { term: 'Iterate', def: 'Recommendation: promising but not ready. Adjust copy/CTA before committing budget.' },
    { term: 'Discard', def: 'Recommendation: combined evidence does not back launching.' },
    { term: 'Low / medium / high risk', def: 'Likelihood the piece damages the brand. High = review before launch.' },
    { term: 'Episode', def: 'One unit of content ingested into the graph. Usually one file or a pasted text.' },
    { term: 'Entity', def: 'Graph node. A person, brand, audience, claim, etc.' },
    { term: 'Relation', def: 'Graph edge. Connects two entities with a type (TARGETS, COMPETES_WITH, …).' }
  ],
  shortcuts: [
    { key: '⌘K', action: 'Open global search (clients, tests, manual)' },
    { key: 'Esc', action: 'Close any open modal or pane' },
    { key: 'G then C', action: 'Go to Clients' },
    { key: 'G then M', action: 'Go to Manual' },
    { key: '?', action: 'Open this shortcuts page' }
  ],
  faq: [
    {
      q: 'Does my data leave the workspace?',
      a:
        'Processing sends text to the configured LLM (OpenAI or local Ollama). ' +
        'If you need zero data egress, use local Ollama; with OpenAI the data leaves but is not retrained on.'
    },
    {
      q: 'Can I delete a client?',
      a:
        'Yes, but it removes every test and episode tied to it. The "Default workspace" cannot be deleted.'
    },
    {
      q: 'Why is a test slow in live mode?',
      a:
        'Live mode hits the LLM per variant and dimension. Mock uses a deterministic generator to validate UX in seconds.'
    }
  ]
}

const content = computed(() => (locale.value === 'en' ? EN : ES))

const goTo = (id) => {
  activeId.value = id
  const el = document.getElementById(id)
  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

let observer = null
const setupObserver = () => {
  if (typeof IntersectionObserver === 'undefined') return
  observer = new IntersectionObserver(
    (entries) => {
      const visible = entries
        .filter((e) => e.isIntersecting)
        .sort((a, b) => a.target.offsetTop - b.target.offsetTop)
      if (visible.length) activeId.value = visible[0].target.id
    },
    { rootMargin: '-25% 0px -65% 0px', threshold: 0 }
  )
  document.querySelectorAll('.manual-article section[id]').forEach((s) => {
    observer.observe(s)
  })
}

// Cmd+K + global shortcuts
useShortcuts({
  onCmdK: () => { cmdK.value = true },
  onEscape: () => { cmdK.value = false }
})

onMounted(async () => {
  try {
    const res = await listClients(200, false)
    allClients.value = res.data || []
  } catch {
    allClients.value = []
  }
  setupObserver()
})
onBeforeUnmount(() => {
  observer && observer.disconnect()
})
</script>

<style scoped>
.manual { min-height: 100vh; }

.manual-main {
  max-width: 1200px;
  margin: 0 auto;
  padding: 36px 32px 80px;
  display: grid;
  grid-template-columns: 240px 1fr;
  gap: 40px;
  align-items: start;
}
@media (max-width: 900px) {
  .manual-main { grid-template-columns: 1fr; }
  .manual-toc { display: none; }
}

.manual-toc {
  position: sticky;
  top: 88px;
  align-self: start;
  font-size: 13px;
}
.toc-eyebrow {
  font-family: var(--mono);
  font-size: 10px;
  letter-spacing: 0.16em;
  color: var(--ink-4);
  text-transform: uppercase;
  margin-bottom: 12px;
}
.manual-toc nav {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.manual-toc a {
  display: flex;
  gap: 10px;
  align-items: baseline;
  padding: 6px 10px;
  border-left: 2px solid transparent;
  color: var(--ink-3);
  text-decoration: none;
  cursor: pointer;
  transition: color 0.12s, border-color 0.12s;
}
.manual-toc a:hover { color: var(--ink); }
.manual-toc a.on {
  color: var(--ink);
  border-left-color: var(--signal);
  background: var(--surface-2);
}
.toc-num { font-size: 10.5px; color: var(--ink-4); width: 14px; flex-shrink: 0; }

.toc-card {
  margin-top: 28px;
  padding: 12px 14px;
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: var(--r);
  font-size: 12px;
}
.toc-card p { margin: 6px 0 0; line-height: 1.5; }

.toc-cmdk {
  display: inline-block;
  background: var(--ink);
  color: var(--bg);
  padding: 1px 8px;
  border: 0;
  border-radius: var(--r-xs);
  font-family: var(--mono);
  font-size: 11px;
  cursor: pointer;
  margin-left: 4px;
}

.manual-hero { margin-bottom: 32px; }
.manual-hero h1 {
  font-family: var(--serif);
  font-size: 36px;
  line-height: 1.15;
  margin: 8px 0 6px;
}
.manual-hero .lead {
  font-size: 16px;
  color: var(--ink-2);
  max-width: 640px;
}

.manual-article section {
  border-top: 1px solid var(--line);
  padding-top: 28px;
  margin-top: 28px;
}
.manual-article section:first-of-type { border-top: 0; padding-top: 0; margin-top: 0; }

.manual-article h2 {
  font-family: var(--serif);
  font-size: 26px;
  margin: 0 0 12px;
}
.manual-article h3 {
  font-family: var(--serif);
  font-size: 18px;
  margin: 22px 0 8px;
  color: var(--ink-2);
}

.manual-article p,
.manual-article li {
  font-size: 15px;
  line-height: 1.7;
  color: var(--ink-2);
}

.manual-article ol,
.manual-article ul { padding-left: 1.4em; margin: 0.6em 0; }
.manual-article li { margin: 6px 0; }

.concepts {
  display: grid;
  grid-template-columns: 180px 1fr;
  gap: 8px 24px;
  margin: 14px 0;
}
.concepts dt {
  font-family: var(--serif);
  font-size: 16px;
  color: var(--ink);
  padding-top: 4px;
}
.concepts dd {
  margin: 0;
  font-size: 14px;
  color: var(--ink-2);
  line-height: 1.55;
  padding-bottom: 8px;
  border-bottom: 1px dashed var(--line);
}

@media (max-width: 600px) {
  .concepts { grid-template-columns: 1fr; }
  .concepts dt { padding-top: 12px; }
}

.kbd-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 8px;
}
.kbd-table th,
.kbd-table td {
  text-align: left;
  padding: 8px 12px;
  border-bottom: 1px solid var(--line);
  font-size: 13px;
}
.kbd-table th {
  font-family: var(--mono);
  font-size: 10.5px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--ink-4);
  font-weight: 500;
}
</style>
