<template>
  <div class="guide">
    <TopNav :all-clients="allClients" @open-cmd-k="cmdK = true" />

    <main id="main" class="guide-main" tabindex="-1">
      <aside class="guide-toc">
        <div class="toc-eyebrow">{{ $t('guide.toc') }}</div>
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
          <div class="mono toc-eyebrow">{{ $t('guide.tip') }}</div>
          <p>{{ $t('guide.tipBody') }}</p>
        </div>
      </aside>

      <article class="guide-article prose" ref="article">
        <header class="guide-hero">
          <div class="eyebrow">{{ $t('side.guide') }}</div>
          <h1>{{ $t('guide.heroTitle') }}</h1>
          <p class="lead">{{ $t('guide.heroSub') }}</p>
        </header>

        <!-- 1. Cómo procesa la herramienta lo que subes -->
        <section :id="sections[0].id">
          <h2>{{ sections[0].num }}. {{ sections[0].title }}</h2>
          <p>{{ content.s1.intro }}</p>
          <ol class="num-steps">
            <li v-for="(step, i) in content.s1.steps" :key="i">
              <strong>{{ step.label }}</strong> — {{ step.body }}
            </li>
          </ol>
          <Card tone="tonal" class="callout">
            <strong>{{ content.s1.implTitle }}</strong>
            <p>{{ content.s1.implBody }}</p>
          </Card>
        </section>

        <!-- 2. Las 5 categorías de información -->
        <section :id="sections[1].id">
          <h2>{{ sections[1].num }}. {{ sections[1].title }}</h2>
          <p class="lead-sub">{{ content.s2.intro }}</p>

          <div v-for="(cat, i) in content.s2.categories" :key="i" class="cat">
            <div class="cat-head">
              <span class="cat-num mono">{{ String(i + 1).padStart(2, '0') }}</span>
              <div>
                <h3 class="cat-title">{{ cat.title }}</h3>
                <span class="cat-impact" :class="impactClass(cat.impact)">{{ cat.impact }}</span>
              </div>
            </div>
            <p>{{ cat.body }}</p>
            <div class="examples">
              <div class="ex ex-good">
                <div class="ex-label mono">{{ $t('guide.good') }}</div>
                <pre>{{ cat.good }}</pre>
              </div>
              <div v-if="cat.bad" class="ex ex-bad">
                <div class="ex-label mono">{{ $t('guide.bad') }}</div>
                <p class="ex-bad-text">{{ cat.bad }}</p>
              </div>
            </div>
          </div>
        </section>

        <!-- 3. Anti-patrones -->
        <section :id="sections[2].id">
          <h2>{{ sections[2].num }}. {{ sections[2].title }}</h2>
          <p>{{ content.s3.intro }}</p>
          <ul class="anti">
            <li v-for="(a, i) in content.s3.items" :key="i">
              <strong>{{ a.title }}</strong> — {{ a.body }}
            </li>
          </ul>
        </section>

        <!-- 4. Checklist -->
        <section :id="sections[3].id">
          <h2>{{ sections[3].num }}. {{ sections[3].title }}</h2>
          <p>{{ content.s4.intro }}</p>
          <ul class="checklist">
            <li v-for="(c, i) in content.s4.items" :key="i">
              <span class="ck">☐</span>
              <span><strong>{{ c.title }}</strong> {{ c.body }}</span>
            </li>
          </ul>
        </section>

        <!-- 5. Estructura recomendada -->
        <section :id="sections[4].id">
          <h2>{{ sections[4].num }}. {{ sections[4].title }}</h2>
          <p>{{ content.s5.intro }}</p>
          <pre class="template">{{ content.s5.template }}</pre>
          <p class="muted">{{ content.s5.size }}</p>
          <Card tone="tonal" class="callout">
            <strong>{{ content.s5.copyTitle }}</strong>
            <p>{{ content.s5.copyBody }}</p>
            <Button variant="primary" icon="copy" @click="copyTemplate">
              {{ copied ? $t('guide.copied') : $t('guide.copyBtn') }}
            </Button>
          </Card>
        </section>

        <!-- 6. Cómo se ve un buen resultado -->
        <section :id="sections[5].id">
          <h2>{{ sections[5].num }}. {{ sections[5].title }}</h2>
          <p>{{ content.s6.intro }}</p>
          <ul>
            <li v-for="(line, i) in content.s6.signals" :key="i">{{ line }}</li>
          </ul>
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
import Card from '../components/ui/Card.vue'
import Button from '../components/ui/Button.vue'
import { listClients } from '../api/clients'
import { useShortcuts } from '../composables/useShortcuts'

const { locale, t } = useI18n()

const allClients = ref([])
const cmdK = ref(false)
const activeId = ref('s1-pipeline')
const article = ref(null)
const copied = ref(false)

const sections = computed(() => [
  { num: '1', id: 's1-pipeline',  title: t('guide.s1.title') },
  { num: '2', id: 's2-categories', title: t('guide.s2.title') },
  { num: '3', id: 's3-anti',      title: t('guide.s3.title') },
  { num: '4', id: 's4-check',     title: t('guide.s4.title') },
  { num: '5', id: 's5-template',  title: t('guide.s5.title') },
  { num: '6', id: 's6-signals',   title: t('guide.s6.title') }
])

const ES = {
  s1: {
    intro: 'El backend hace cuatro cosas con cada documento que cargas:',
    steps: [
      { label: 'Trocea', body: 'el texto en chunks de ~500 caracteres.' },
      { label: 'Extrae entidades y relaciones', body: 'vía LLM (Marca → Audiencia, Producto → Precio…) usando la ontología.' },
      { label: 'Vectoriza', body: 'cada chunk con OpenAI embeddings y los guarda en pgvector.' },
      { label: 'Busca por similitud semántica', body: 'las 8–12 facts más relevantes cuando lanzas un test, una predicción o el wizard pregunta algo.' }
    ],
    implTitle: 'Implicación clave',
    implBody:
      'La calidad de las predicciones depende de qué tan explícita, atómica y declarativa sea la información. ' +
      'El LLM extrae mejor cuando los hechos están escritos como afirmaciones autosuficientes, no como prosa narrativa o storytelling de marca.'
  },
  s2: {
    intro: 'En orden de impacto sobre la calidad del output:',
    categories: [
      {
        title: 'Identidad y posicionamiento',
        impact: 'Alto impacto · una sola vez por cliente',
        body:
          'Sube el brand book sintetizado, no el deck de 80 páginas. Texto plano con afirmaciones autosuficientes. ' +
          'Lo importante: nombre, año, posicionamiento, voz, restricciones explícitas.',
        good:
`Brand X es una marca de belleza vegana fundada en 2024 en CDMX.
Posicionamiento: premium accesible — precio entre $30-40 USD.
Promesa central: ingredientes limpios sin sacrificar performance.
Voz: cálida, directa, sin superlativos.
Restricciones: no usar before/after, no hacer claims clínicos.`,
        bad: 'Párrafos narrativos del estilo "imagina una mujer que despierta y se siente segura..."'
      },
      {
        title: 'Audiencia(s) declaradas',
        impact: 'Alto impacto · alta variabilidad',
        body:
          'Una audiencia por bloque, con todos los atributos juntos. Cada bloque debe poder leerse aislado. ' +
          'Demografía, comportamiento, canal, trigger emocional.',
        good:
`Audiencia primaria: mujeres 25-34, CDMX y GDL, NSE B/C+.
Universitarias, ingreso $25-50K MXN/mes.
Compran en línea 2-3 veces por mes.
Sensibles a precio en categoría comparada.
Canal principal: Instagram (60% del consumo).
Secundario: TikTok (cada vez más para descubrimiento).
Trigger emocional: identidad y autocuidado, no FOMO.`,
        bad: '"Nuestro target son millennials que valoran lo auténtico" (vago, no extraíble como hecho específico).'
      },
      {
        title: 'Estudios cuantitativos y métricas históricas',
        impact: 'Alto impacto · depende de tener data real',
        body:
          'Aplana las tablas a oraciones. El LLM lee texto, no parsea bien CSVs ni PDFs con celdas. ' +
          'Si tienes números, escríbelos como oraciones.',
        good:
`En la campaña Black Friday 2025, el carrusel A obtuvo 2.4% CTR vs 1.1% del video B.
La razón principal según encuesta post-campaña: el carrusel mostraba precio claramente.
Top objeción: "demasiado caro" (38% de respuestas), seguida de "no conozco la marca" (24%).
Engagement por canal Q4 2025: Instagram 4.2%, TikTok 6.1%, YouTube 0.8% (no escaló).`,
        bad: 'Subir el dashboard de Looker como PDF — las tablas se pierden y los números también.'
      },
      {
        title: 'Contexto competitivo',
        impact: 'Impacto medio',
        body:
          'Quiénes son tus competidores, qué claims usan, qué espacios ya están saturados. ' +
          'Permite detectar brand_risk en variantes que repiten claims de la categoría.',
        good:
`Competidor directo: Glossier — posicionamiento similar, precio +15%.
Su claim "skin first" satura el feed desde 2024.
The Ordinary domina el discurso de "ingredientes activos" — evitar entrar ahí.
La Roche Posay se percibe como clínica/farmacia, no aspiracional.`,
        bad: ''
      },
      {
        title: 'Contexto del momento (scenario)',
        impact: 'Alto impacto en cada test · no permanente',
        body:
          'Esto va en el campo "scenario" del wizard de cada test, no en el contexto del cliente. ' +
          'Tiene que ser específico y temporal: ventana, restricciones, presión competitiva.',
        good:
`Lanzamiento BF24, ventana 3 semanas (Oct 28 – Nov 18).
Inventario limitado en SKU principal (350 units).
Restricción legal: claims comparativos requieren disclaimer.
Presión competitiva: Glossier corre promo paralela 25% off.`,
        bad: '"Queremos probar diferentes mensajes" (no es un escenario, es un objetivo vacío).'
      }
    ]
  },
  s3: {
    intro: 'Estos patrones gastan tokens, ensucian la búsqueda y degradan las predicciones:',
    items: [
      { title: 'Decks de marca con mucha imagen', body: 'la herramienta no lee imágenes en PDFs (solo el texto). Mejor extrae los puntos clave a un .md o .txt.' },
      { title: 'Documentos legales completos', body: 'generan ruido en embeddings y gastan tokens. Si hay restricciones legales relevantes, escríbelas como 3-5 oraciones, no 40 páginas.' },
      { title: 'Múltiples versiones del mismo brief', body: '(v1, v2, v3, "final_FINAL") ingestás el mismo concepto N veces y la búsqueda se llena de duplicados. Sube solo la versión vigente.' },
      { title: 'Transcripciones crudas de focus groups', body: 'son larguísimas y poco estructuradas. Mejor sube el resumen ejecutivo con los 5-10 hallazgos clave.' },
      { title: 'Texto en mezcla ES/EN inconsistente', body: 'el LLM puede manejar ambos pero la extracción es más precisa cuando el documento mantiene un idioma. Si el brief está en español, mantenlo en español.' }
    ]
  },
  s4: {
    intro: 'Antes de subir cada archivo, revisa esta lista:',
    items: [
      { title: 'Una afirmación por línea o párrafo corto.', body: 'Cada bloque se lee solo, sin contexto previo.' },
      { title: 'Nombres explícitos.', body: '"Brand X" no "la marca", "audiencia A" no "ellas".' },
      { title: 'Números cuando hay números.', body: 'Precios, edades, fechas, porcentajes — al texto, no en tabla.' },
      { title: 'Restricciones explícitas.', body: 'Lo que NO se puede decir importa tanto como lo que sí.' },
      { title: 'Idioma consistente.', body: 'Dentro del documento.' },
      { title: 'Tamaño total razonable.', body: '5–20 KB de texto curado vale más que 200 KB de documento extendido. Si pasa de 50 KB por archivo, probablemente sobra contenido.' },
      { title: 'Marca el origen.', body: 'En la "Etiqueta de origen" del upload, pon brief_BF24, estudio_marca_Q1, metricas_FY25 — eso aparece en las facts y el LLM lo cita.' }
    ]
  },
  s5: {
    intro: 'Para cargar un cliente nuevo, basta un solo archivo .md con cinco secciones cortas:',
    template:
`## Identidad
[5-10 líneas con nombre, año, categoría, posicionamiento, voz, restricciones]

## Audiencia(s) declarada(s)
[10-15 líneas, una audiencia por bloque, con demografía + comportamiento + canal + trigger]

## Posicionamiento y restricciones
[5-10 líneas; voz, claims permitidos, no-go zones, compliance]

## Métricas y aprendizajes recientes
[10-20 líneas; campañas pasadas, CTR/ROAS por canal, top objeciones de audiencia]

## Contexto competitivo
[5-10 líneas; competidores directos, sus claims, qué espacios están saturados]
`,
    size: 'Eso son ~50–80 líneas de texto curado. Suficiente para que las predicciones tengan respuestas concretas sin saturar la búsqueda ni inflar costos.',
    copyTitle: 'Plantilla lista para usar',
    copyBody: 'Copia el bloque anterior, pégalo en un .md, llena cada sección con la información de tu cliente, y súbelo en la pestaña Contexto.'
  },
  s6: {
    intro: 'Si cargaste el contexto bien, deberías ver estas señales en el reporte de un creative test:',
    signals: [
      'En la sección Evidencia, citas verbatim de tus facts (señal de que el modelo está usando el contexto, no inventando).',
      'En el bloque client_context_facts del resultado, las 5–8 facts más relevantes a tu brief.',
      'Diferencias de scoring claras entre variantes que respetan tus restricciones vs las que las violan.',
      'Si las explicaciones son genéricas ("apela a millennials urbanos…") sin nombrar nada específico de tu marca, es señal de que el contexto cargado fue muy narrativo o muy genérico — vale la pena aplanarlo siguiendo esta guía.'
    ]
  }
}

const EN = {
  s1: {
    intro: 'The backend does four things with every document you upload:',
    steps: [
      { label: 'Chunks', body: 'the text into ~500-character chunks.' },
      { label: 'Extracts entities and relationships', body: 'via LLM (Brand → Audience, Product → Price…) using the ontology.' },
      { label: 'Embeds', body: 'each chunk with OpenAI embeddings and stores them in pgvector.' },
      { label: 'Semantic-searches', body: 'the 8–12 most relevant facts whenever you launch a test, run a prediction or the wizard asks something.' }
    ],
    implTitle: 'Key implication',
    implBody:
      'Prediction quality depends on how explicit, atomic and declarative the information is. ' +
      'The LLM extracts best when facts are written as self-contained statements, not narrative or brand storytelling.'
  },
  s2: {
    intro: 'In order of impact on output quality:',
    categories: [
      {
        title: 'Identity and positioning',
        impact: 'High impact · once per client',
        body:
          'Upload a synthesised brand book, not the 80-page deck. Plain text with self-contained statements. ' +
          'What matters: name, year, positioning, voice, explicit restrictions.',
        good:
`Brand X is a vegan beauty brand founded in 2024 in Mexico City.
Positioning: accessible premium — price between $30-40 USD.
Core promise: clean ingredients without sacrificing performance.
Voice: warm, direct, no superlatives.
Restrictions: no before/after imagery, no clinical claims.`,
        bad: 'Narrative paragraphs like "imagine a woman who wakes up and feels confident..."'
      },
      {
        title: 'Declared audience(s)',
        impact: 'High impact · high variance',
        body:
          'One audience per block, with all attributes together. Each block must read on its own. ' +
          'Demographics, behaviour, channel, emotional trigger.',
        good:
`Primary audience: women 25-34, Mexico City and Guadalajara, mid-to-high income.
University-educated, $25-50K MXN/month income.
Buy online 2-3 times per month.
Price-sensitive within the comparable category.
Main channel: Instagram (60% of media consumption).
Secondary: TikTok (increasingly used for discovery).
Emotional trigger: identity and self-care, not FOMO.`,
        bad: '"Our target is millennials who value authenticity" (vague, not extractable as a specific fact).'
      },
      {
        title: 'Quantitative studies and historical metrics',
        impact: 'High impact · requires real data',
        body:
          'Flatten tables to sentences. The LLM reads text; it does not parse CSVs or table-heavy PDFs well. ' +
          'If you have numbers, write them as sentences.',
        good:
`In the Black Friday 2025 campaign, carousel A delivered 2.4% CTR vs 1.1% from video B.
Main reason per post-campaign survey: the carousel showed price clearly.
Top objection: "too expensive" (38% of responses), followed by "I don't know the brand" (24%).
Channel engagement Q4 2025: Instagram 4.2%, TikTok 6.1%, YouTube 0.8% (did not scale).`,
        bad: 'Uploading the Looker dashboard as a PDF — tables are lost and so are the numbers.'
      },
      {
        title: 'Competitive context',
        impact: 'Medium impact',
        body:
          'Who your direct competitors are, what claims they use, which spaces are already saturated. ' +
          'Lets the tool detect brand_risk in variants that repeat category-saturated claims.',
        good:
`Direct competitor: Glossier — similar positioning, price +15%.
Their "skin first" claim has saturated the feed since 2024.
The Ordinary owns the "active ingredients" discourse — avoid entering there.
La Roche Posay is perceived as clinical/pharmacy, not aspirational.`,
        bad: ''
      },
      {
        title: 'Moment context (scenario)',
        impact: 'High impact per test · not stored permanently',
        body:
          'This goes in the "scenario" field of each test wizard, not in the client context. ' +
          'Must be specific and time-bound: window, constraints, competitive pressure.',
        good:
`BF24 launch, 3-week window (Oct 28 – Nov 18).
Limited inventory on hero SKU (350 units).
Legal constraint: comparative claims require a disclaimer.
Competitive pressure: Glossier runs a parallel 25% off promo.`,
        bad: '"We want to test different messages" — that is a goal, not a scenario.'
      }
    ]
  },
  s3: {
    intro: 'These patterns waste tokens, pollute search and degrade predictions:',
    items: [
      { title: 'Image-heavy brand decks', body: 'the tool does not read images in PDFs (text only). Better extract the key points to a .md or .txt.' },
      { title: 'Full legal documents', body: 'add embedding noise and burn tokens. If you have relevant restrictions, write them as 3-5 sentences, not 40 pages.' },
      { title: 'Multiple versions of the same brief', body: '(v1, v2, v3, "final_FINAL") ingest the same concept N times and search fills with duplicates. Upload only the live version.' },
      { title: 'Raw focus-group transcripts', body: 'they are long and unstructured. Better upload the executive summary with the 5-10 key findings.' },
      { title: 'Inconsistent ES/EN mix in one doc', body: 'the LLM can handle both languages but extraction is more accurate when each document keeps a single language.' }
    ]
  },
  s4: {
    intro: 'Before uploading each file, run through this list:',
    items: [
      { title: 'One assertion per line or short paragraph.', body: 'Each block reads on its own.' },
      { title: 'Explicit names.', body: '"Brand X" not "the brand", "audience A" not "they".' },
      { title: 'Numbers when there are numbers.', body: 'Prices, ages, dates, percentages — in text, not tables.' },
      { title: 'Explicit restrictions.', body: 'What CAN\'T be said matters as much as what can.' },
      { title: 'Consistent language.', body: 'Within each document.' },
      { title: 'Reasonable total size.', body: '5–20 KB of curated text beats 200 KB of extended doc. Past 50 KB per file there is probably bloat.' },
      { title: 'Tag the source.', body: 'In the upload "Source label" field, use brief_BF24, brand_study_Q1, metrics_FY25 — that label shows up in facts when the LLM cites them.' }
    ]
  },
  s5: {
    intro: 'To onboard a new client, a single .md file with five short sections is enough:',
    template:
`## Identity
[5-10 lines with name, year, category, positioning, voice, restrictions]

## Declared audience(s)
[10-15 lines, one audience per block, with demographics + behaviour + channel + trigger]

## Positioning and restrictions
[5-10 lines; voice, allowed claims, no-go zones, compliance]

## Recent metrics and learnings
[10-20 lines; past campaigns, CTR/ROAS by channel, top audience objections]

## Competitive context
[5-10 lines; direct competitors, their claims, which spaces are saturated]
`,
    size: 'About 50–80 lines of curated text. Enough for predictions to give specific answers without saturating search or inflating cost.',
    copyTitle: 'Ready-to-use template',
    copyBody: 'Copy the block above, paste it into a .md, fill each section with your client info, and upload it from the Context tab.'
  },
  s6: {
    intro: 'When the context is loaded well, you should see these signals in any creative-test report:',
    signals: [
      'In the Evidence section, verbatim quotes from your own facts (proof the model is using the context, not making things up).',
      'In the result\'s client_context_facts block, the 5–8 most relevant facts to your brief.',
      'Clear scoring differences between variants that respect your restrictions vs those that violate them.',
      'If explanations are generic ("appeals to urban millennials…") with nothing specific to your brand, that is a sign the context was too narrative or too general — flatten it following this guide.'
    ]
  }
}

const content = computed(() => (locale.value === 'en' ? EN : ES))

const goTo = (id) => {
  activeId.value = id
  const el = document.getElementById(id)
  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

const impactClass = (label) => {
  const lower = (label || '').toLowerCase()
  if (lower.includes('alto') || lower.includes('high')) return 'impact-high'
  if (lower.includes('medio') || lower.includes('medium')) return 'impact-mid'
  return ''
}

const copyTemplate = async () => {
  try {
    await navigator.clipboard.writeText(content.value.s5.template)
    copied.value = true
    setTimeout(() => { copied.value = false }, 1800)
  } catch {
    // Fallback for browsers without clipboard API
    const ta = document.createElement('textarea')
    ta.value = content.value.s5.template
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
    copied.value = true
    setTimeout(() => { copied.value = false }, 1800)
  }
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
  document.querySelectorAll('.guide-article section[id]').forEach((s) => {
    observer.observe(s)
  })
}

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
.guide { min-height: 100vh; }

.guide-main {
  max-width: 1200px;
  margin: 0 auto;
  padding: 36px 32px 80px;
  display: grid;
  grid-template-columns: 240px 1fr;
  gap: 40px;
  align-items: start;
}
@media (max-width: 900px) {
  .guide-main { grid-template-columns: 1fr; }
  .guide-toc { display: none; }
}

.guide-toc {
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
.guide-toc nav { display: flex; flex-direction: column; gap: 4px; }
.guide-toc a {
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
.guide-toc a:hover { color: var(--ink); }
.guide-toc a.on {
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
  color: var(--ink-2);
  line-height: 1.5;
}
.toc-card p { margin: 6px 0 0; }

.guide-hero { margin-bottom: 32px; }
.guide-hero h1 {
  font-family: var(--serif);
  font-size: 36px;
  line-height: 1.15;
  margin: 8px 0 6px;
}
.guide-hero .lead {
  font-size: 16px;
  color: var(--ink-2);
  max-width: 640px;
}

.guide-article section {
  border-top: 1px solid var(--line);
  padding-top: 28px;
  margin-top: 28px;
}
.guide-article section:first-of-type {
  border-top: 0;
  padding-top: 0;
  margin-top: 0;
}

.guide-article h2 {
  font-family: var(--serif);
  font-size: 26px;
  margin: 0 0 12px;
}

.guide-article p,
.guide-article li {
  font-size: 15px;
  line-height: 1.7;
  color: var(--ink-2);
}

.guide-article ol,
.guide-article ul { padding-left: 1.4em; margin: 0.6em 0; }
.guide-article li { margin: 6px 0; }

.lead-sub {
  color: var(--ink-3);
  font-size: 14px;
  margin-bottom: 12px;
}

.num-steps li { padding: 4px 0; }
.num-steps li strong { color: var(--ink); }

.callout { margin-top: 16px; padding: 14px 16px; }
.callout strong {
  display: block;
  font-family: var(--serif);
  font-size: 16px;
  color: var(--ink);
  margin-bottom: 4px;
}
.callout p { margin: 4px 0 0; }

.cat {
  margin: 22px 0;
  padding: 18px 20px;
  border: 1px solid var(--line);
  border-radius: var(--r);
  background: var(--surface);
}
.cat-head {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  margin-bottom: 8px;
}
.cat-num {
  font-size: 11px;
  color: var(--ink-4);
  letter-spacing: 0.12em;
  padding-top: 4px;
}
.cat-title {
  font-family: var(--serif);
  font-size: 19px;
  margin: 0;
}
.cat-impact {
  display: inline-block;
  margin-top: 4px;
  font-size: 11px;
  color: var(--ink-3);
  font-family: var(--mono);
  letter-spacing: 0.04em;
}
.cat-impact.impact-high { color: var(--signal); }
.cat-impact.impact-mid  { color: var(--ink-3); }

.examples {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-top: 12px;
}
@media (max-width: 700px) {
  .examples { grid-template-columns: 1fr; }
}
.ex {
  padding: 10px 12px;
  border-radius: var(--r);
  border: 1px solid var(--line);
  background: var(--surface-2);
}
.ex-good { border-left: 3px solid var(--signal); }
.ex-bad  { border-left: 3px solid var(--ink-4); }
.ex-label {
  font-size: 10px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--ink-4);
  margin-bottom: 6px;
}
.ex pre {
  margin: 0;
  white-space: pre-wrap;
  font-family: var(--mono);
  font-size: 12.5px;
  line-height: 1.55;
  color: var(--ink-2);
}
.ex-bad-text {
  margin: 0;
  font-size: 13px;
  color: var(--ink-3);
  font-style: italic;
}

.anti li { padding: 6px 0; }
.anti li strong { color: var(--ink); }

.checklist {
  list-style: none;
  padding: 0;
  margin: 12px 0;
}
.checklist li {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  padding: 6px 0;
}
.checklist .ck {
  font-family: var(--mono);
  color: var(--ink-3);
  font-size: 14px;
  padding-top: 1px;
}
.checklist strong { color: var(--ink); }

.template {
  margin: 12px 0;
  padding: 14px 16px;
  background: var(--surface-2);
  border: 1px solid var(--line);
  border-left: 3px solid var(--signal);
  border-radius: var(--r);
  font-family: var(--mono);
  font-size: 12.5px;
  line-height: 1.6;
  color: var(--ink-2);
  white-space: pre-wrap;
}

.muted { color: var(--ink-3); font-size: 13px; }
</style>
