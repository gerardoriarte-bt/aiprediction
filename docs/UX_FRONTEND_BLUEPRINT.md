# Blueprint de frontend — plataforma cliente-céntrica

Documento de referencia para el equipo de diseño. Define arquitectura de
información, layout, componentes, sistema visual y patrones para mostrar
grafos de conocimiento y reportes accionables a un equipo de planners y
medios digitales.

> Estado: post-R1 (modelo cliente-céntrico cableado en backend). Esta es
> la base sobre la que el rediseño completo se va a aplicar.

---

## 1. Principios rectores

1. **Cliente primero**. La plataforma es un workspace por cliente. Toda
   acción nace dentro de un cliente.
2. **Decisiones, no logs**. La UI prioriza recomendaciones accionables y
   esconde el detalle técnico bajo capas opcionales.
3. **Comparativas visuales antes que tablas**. Para audiencias creativas
   (planners, copywriters, account leads), un radar es más útil que una
   tabla con 4 columnas.
4. **Lenguaje del oficio**. "Activar / Iterar / Descartar" en vez de
   "score 73". "Riesgo de marca" en vez de "brand_risk_score".
5. **Cero jerga técnica visible**. `graph_id`, `episode_id`, `task_id`
   solo aparecen en una pestaña *Devtools* opcional o en tooltips.

---

## 2. Sitemap

```
/                                  Lista de clientes (Home)
/clients/new                       Wizard: crear cliente

/clients/:id                       Workspace del cliente (3 paneles)
  └─ /overview                     KPIs + últimas corridas + accesos rápidos
  └─ /context                      Brand context + grafo + búsqueda
       └─ /context/graph           Grafo full-screen (modo análisis)
  └─ /creative-tests               Lista de tests del cliente
       └─ /new                     Wizard: nuevo test
       └─ /:test_id                Detalle de resultados
  └─ /simulations                  Lista de simulaciones
       └─ /new                     Wizard: nueva simulación
       └─ /:sim_id                 Run en vivo + resultados
  └─ /reports                      Lista de reportes generados
       └─ /:report_id              Reporte detallado (multi-sección)
  └─ /settings                     Editar nombre / industria / lineamientos

/manual                            Manual de uso (todas las secciones)
/help                              Atajos rápidos + glosario
```

Reglas de navegación:
- El usuario está siempre dentro de **un cliente** o en la lista raíz.
- En cualquier pantalla, el header muestra el cliente activo y permite
  cambiar de cliente con un combobox (sin perder la pestaña actual).
- "Volver" siempre va a la pestaña padre, no a la home.

---

## 3. Layout global

```
┌─────────────────────────────────────────────────────────────────┐
│  LO.BUENO                  ▾ Cliente: UA           ⌕  ES  ●     │  ← Top nav
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐  ┌─────────────────────────────────────────┐  │
│  │ Sidebar     │  │ Contenido principal                     │  │
│  │             │  │                                         │  │
│  │ Overview    │  │                                         │  │
│  │ Context  ●  │  │                                         │  │
│  │ Tests       │  │                                         │  │
│  │ Sims        │  │                                         │  │
│  │ Reports     │  │                                         │  │
│  │ Settings    │  │                                         │  │
│  └─────────────┘  └─────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Top nav (siempre visible)

| Bloque | Comportamiento |
|---|---|
| Logo / brand | Click → `/` (lista de clientes) |
| Selector de cliente | Combobox con búsqueda. Cambia el contexto sin recargar. Muestra los 5 últimos arriba, el resto debajo. |
| Búsqueda global | `⌕` abre comando central (Cmd+K). Busca clientes, tests, reportes, episodios del grafo del cliente activo. |
| Selector de idioma | EN / ES |
| Usuario | (futuro: auth + workspace) |

### Sidebar contextual

Solo aparece dentro de un cliente. 6 entradas verticales con ícono +
label. Al colapsar, queda solo el ícono.

### Breadcrumb

Bajo el top nav: `UA › Creative Tests › ctest_58dbb…` con cada nivel
clickeable.

---

## 4. Páginas — detalle de estructura

### 4.1 `/` — Lista de clientes

**Cuándo**: el usuario abre la app sin contexto, o vuelve desde un cliente.

**Layout**:
```
┌── Header ───────────────────────────────────┐
│ Clientes                       + Nuevo cliente │
└─────────────────────────────────────────────┘
┌── Filtros (chips) ──────────────────────────┐
│ [Todos] [Retail] [eCommerce] [FMCG] ⌕ Buscar │
└─────────────────────────────────────────────┘
┌── Grid de cards 3-col ──────────────────────┐
│  ┌───────┐  ┌───────┐  ┌───────┐            │
│  │ UA    │  │ Acme  │  │ ...   │            │
│  │ Retail│  │ FMCG  │  │       │            │
│  │ 12 t  │  │ 4 t   │  │       │            │
│  │ KPIs  │  │ KPIs  │  │       │            │
│  └───────┘  └───────┘  └───────┘            │
└─────────────────────────────────────────────┘
```

**Card de cliente**:
- Header: nombre + badge de industria.
- Stats compactos: `12 tests · 4 reportes · 1 simulación activa`.
- Última actividad: "hace 2 días — test BF24".
- Click → `/clients/:id/overview`.
- Hover: leve elevación de sombra + acción rápida `+ test`.

**Estados**:
- Vacío: ilustración minimalista + CTA grande "Crear tu primer cliente".
- Cargando: 6 skeleton cards.
- Error: banner top + retry.

### 4.2 `/clients/:id/overview` — Vista general del cliente

**Layout 12-col**:

```
┌── Hero del cliente ─────────────────────────────────────────────┐
│ UA · Retail / eCommerce          [✎ Editar] [+ Nuevo test]      │
│ 12 tests · 4 reportes · grafo con 137 entidades                 │
└─────────────────────────────────────────────────────────────────┘

┌── Últimos resultados (col-8) ──┐ ┌── Salud del grafo (col-4) ──┐
│ 4 tarjetas horizontales:        │ │ Anillo: cobertura por tipo  │
│ - últimos 4 tests               │ │ Brand · Audience · Channel  │
│ - cada uno: ganador + reco       │ │ Lista: top 5 entidades      │
│ - micro-radar de scores         │ │ Botón: "Explorar grafo →"   │
└────────────────────────────────┘ └─────────────────────────────┘

┌── Próximos pasos (col-12) ─────────────────────────────────────┐
│ [Cargar contexto al cliente] [Crear test] [Crear simulación] │
│ Cada acción tiene 1 frase explicando el porqué.              │
└────────────────────────────────────────────────────────────────┘

┌── Actividad reciente (timeline) ───────────────────────────────┐
│ • hace 2h — Test ctest_xxx completado · ganadora: B           │
│ • hace 1d — Episodio 12 ingestado: Estudio Q1 2026            │
│ • hace 3d — Reporte rep_xxx publicado                          │
└────────────────────────────────────────────────────────────────┘
```

### 4.3 `/clients/:id/context` — Brand context + grafo

Es la "memoria viva del cliente". Tres bloques:

#### Bloque A: ficha de marca

Editable in-place: nombre, industria, descripción, lineamientos. Al
hacer click en cualquier campo, se vuelve textarea con `Guardar / Cancelar`.

#### Bloque B: grafo de conocimiento

Vista compacta + botón "Abrir vista completa".

```
┌── Conocimiento ingestado ─────────────────────────────────┐
│  137 entidades · 412 hechos · 8 episodios                 │
│                                                           │
│  ┌─ Mini-grafo (200px alto) ───────┐  ┌─ Top entidades ─┐│
│  │  visualización fuerza-dirigida │  │ • Glow Inc       ││
│  │  con clusters por tipo         │  │ • Q1 2026 study  ││
│  │  [Abrir vista completa →]       │  │ • Audience F25-34││
│  └────────────────────────────────┘  └──────────────────┘│
└───────────────────────────────────────────────────────────┘
```

Vista completa (`/context/graph`): cubre toda la pantalla, descrita en
sección 6.

#### Bloque C: subir contexto

Drag&drop + paste de texto + lista de episodios. Tal como ya está
implementado, pero con mejor jerarquía visual.

#### Bloque D: buscador del cliente

Caja única arriba: `Pregúntale a UA: "¿qué dice el estudio Q1 sobre pricing?"`.

Resultado: lista de hechos relevantes con la fuente (qué episodio).

### 4.4 `/clients/:id/creative-tests` — Lista de tests

**Tabla densa con vista previa visual**:

```
┌──────────────────────────────────────────────────────────────┐
│ Tests creativos                          + Nuevo test         │
├──────────────────────────────────────────────────────────────┤
│ Filtros: [Todos] [Activar] [Iterar] [Descartar] · ⌕ Buscar   │
├──────────────────────────────────────────────────────────────┤
│ ✓ ctest_xxx · BF MX claim                                     │
│   Audiencia: Mujeres 25-34 CDMX · Ganadora: B (iterar)        │
│   ▓▓▓▓░ A 287 │ ▓▓▓▓▓ B 313 │ ▓▓▓░░ C 245                    │
│   hace 2h                                                     │
├──────────────────────────────────────────────────────────────┤
│ ✓ ctest_yyy · Lanzamiento Skincare Q3                         │
│   ...                                                         │
└──────────────────────────────────────────────────────────────┘
```

Cada fila tiene una **mini-barra horizontal apilada** con los scores de
todas las variantes — el planner puede comparar tests de un vistazo.

### 4.5 `/clients/:id/creative-tests/:test_id` — Detalle de test

Esta es **la pantalla más importante del producto**. Diseñada como un
reporte one-page.

```
┌── Header del test ──────────────────────────────────────────────┐
│ ← Volver  ·  ctest_58dbb…  ·  Ejecutado hace 2h  ·  modo: live  │
│                                                                 │
│ BF MX claim — Black Friday MX, 7 días, alta saturación          │
│ Audiencia: Mujeres 25-34 CDMX                                   │
└─────────────────────────────────────────────────────────────────┘

┌── Decisión (hero) ──────────────────────────────────────────────┐
│   GANADORA                                                      │
│   ┌────────┐                                                    │
│   │   B    │   "Tu rutina, tu ritual"                            │
│   └────────┘                                                    │
│                                                                 │
│   Recomendación: ITERAR (riesgo medio)                          │
│   Próxima acción: ajustar CTA antes de invertir budget          │
└─────────────────────────────────────────────────────────────────┘

┌── Comparativa visual ───────────────────────────────────────────┐
│  Radar 4-axis (Claridad, Ajuste, Intención, Seguridad)          │
│  Las 3 variantes superpuestas en colores distintos              │
│  Total: barras horizontales con badge de recomendación          │
└─────────────────────────────────────────────────────────────────┘

┌── Scorecards (grid 3-col) ──────────────────────────────────────┐
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                       │
│  │ A        │  │ B   ★    │  │ C        │                       │
│  │ headline │  │ headline │  │ headline │                       │
│  │ ▓▓▓▓░    │  │ ▓▓▓▓▓    │  │ ▓▓▓░░    │                       │
│  │ riesgo M │  │ riesgo M │  │ riesgo H │                       │
│  │ Activar  │  │ Iterar   │  │ Descartar│                       │
│  │ Ver det.→│  │ Ver det.→│  │ Ver det.→│                       │
│  └──────────┘  └──────────┘  └──────────┘                       │
└─────────────────────────────────────────────────────────────────┘

┌── Evidencia (acordeón colapsable) ──────────────────────────────┐
│ ▸ Por qué B ganó (3 hechos del grafo del cliente citados)       │
│ ▸ Por qué C falló (riesgo identificado)                         │
│ ▸ Diferencia A vs B                                             │
└─────────────────────────────────────────────────────────────────┘

┌── Plan de activación (3 horizontes) ────────────────────────────┐
│ 0-7 días                  30 días                  60-90 días   │
│ • Briefar B con CTA…     • Medir CTR vs goal…      • Ajustar…  │
│ • A/B en Instagram        • Recolectar quotes      • Decidir    │
└─────────────────────────────────────────────────────────────────┘

┌── Acciones del reporte ─────────────────────────────────────────┐
│ [Exportar PDF] [Compartir link] [Crear simulación con B]        │
└─────────────────────────────────────────────────────────────────┘

┌── Detalles técnicos (colapsado por default) ────────────────────┐
│ ▾ Brief original                                                 │
│ ▾ Logs del agente                                                │
│ ▾ Prompts utilizados                                             │
└─────────────────────────────────────────────────────────────────┘
```

### 4.6 `/clients/:id/simulations`

Reusa wizard actual de `Process.vue` adaptado a layout sobrio + `client_id`
inyectado. Lista de simulaciones con cronograma de runs.

### 4.7 `/clients/:id/reports`

Cada reporte se ve como un **documento de varias páginas** con sidebar
de navegación de secciones (executive summary, hallazgos, riesgos,
plan).

---

## 5. Componentes reutilizables (kit)

### 5.1 Atómicos

| Componente | Uso |
|---|---|
| `Button` (primary, secondary, ghost, danger) | Acciones |
| `Input`, `Textarea`, `Select`, `Combobox` | Formularios |
| `Badge` (info, success, warn, danger) | Status, recommendations, risk |
| `Pill` (recommendation, risk_level) | Decisiones del agente |
| `Card` (default, hover, accent) | Contenedor genérico |
| `Tooltip` (existing `HelpHint`) | Glosario en contexto |
| `Tabs` (horizontal) | Navegación dentro de página |
| `Stepper` | Wizards de creación |
| `Skeleton` | Loading |
| `EmptyState` | Estados vacíos con CTA |

### 5.2 Compuestos

| Componente | Uso |
|---|---|
| `ClientHeader` | Nombre + breadcrumb + acciones rápidas |
| `KPIRow` | Tira de 3-4 métricas grandes |
| `RadarChart` | Comparativa multidimensional |
| `BarRanking` | Ranking horizontal con etiquetas |
| `ScoreCard` (variant detail) | Headline + 4 scores + risk + recommendation |
| `EvidenceAccordion` | Hechos citados con su fuente |
| `ActionTimeline` (0-7d / 30d / 60-90d) | Plan de activación |
| `EpisodeList` | Episodios ingestados con status pill |
| `GraphMini` | Mini-grafo en card |
| `GraphFullscreen` | Vista completa de exploración |
| `ChatBox` | Pregunta-respuesta sobre el grafo del cliente |

---

## 6. Visualización del grafo de conocimiento

### 6.1 Tecnología sugerida

| Opción | Pros | Contras |
|---|---|---|
| **D3.js force layout** | Ya está en deps. Total control. | Más código. Performance baja >500 nodos. |
| **Cytoscape.js** | Maduro, layouts varios, extensible. | Curva de aprendizaje. |
| **vue-flow** | Vue-native, bonito out of the box. | Mejor para flowcharts que para grafos densos. |
| **sigma.js** | Muy rápido (>10k nodos). | Estética más técnica. |

**Recomendación**: empezar con **D3 force layout** si el grafo típico es
<300 nodos (suficiente para la mayoría de clientes), saltar a
**Cytoscape** si crece.

### 6.2 Vista compacta (mini-grafo)

- 200px de alto, en card.
- Sin labels, solo nodos coloreados por tipo.
- Auto-layout, no interactivo (solo preview).
- Botón overlay "Abrir vista completa →".

### 6.3 Vista completa (`/context/graph`)

```
┌── Top toolbar ──────────────────────────────────────────────────┐
│ ⌕ Buscar · Filtros: [Brand] [Audience] [Claim] [+] · Layout: [⛶]│
└─────────────────────────────────────────────────────────────────┘
┌── Lienzo (ocupa 80% pantalla) ──────────────────────────────────┐
│                                                                 │
│         (visualización fuerza-dirigida)                         │
│                                                                 │
│  Click izquierdo nodo: panel detalle a la derecha               │
│  Click derecho: menú contextual (expandir vecinos, ocultar)     │
│  Drag: reposicionar manual                                      │
│  Scroll: zoom                                                   │
│  Espaciador: pause de simulación                                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
┌── Panel detalle (slide-in) ─────────────────────────────────────┐
│ Glow Inc · Competitor                                           │
│ Resumen: …                                                       │
│ 12 hechos relacionados:                                         │
│   • Compete con UA en MX                                        │
│   • Mencionada en estudio Q1                                    │
│ Aparece en episodios: #2, #5                                    │
└─────────────────────────────────────────────────────────────────┘
```

### 6.4 Encoding visual

| Atributo | Encoding |
|---|---|
| Tipo de entidad | Color (Brand=azul, Audience=verde, Channel=naranja, Claim=violeta, Competitor=rojo, Study=gris azulado, Metric=oro, Risk=rojo intenso) |
| Importancia (centralidad) | Tamaño del nodo (radio 6-24px) |
| Estado de hecho (active/expired) | Opacity edge (1.0 active, 0.35 expired) |
| Tipo de relación | Estilo de edge (sólida = factual, punteada = inferencial) |
| Selección | Borde grueso + halo |
| Hover | Highlight del nodo + edges + 1er vecindario |

### 6.5 Interacciones

- **Buscar**: input top, hace zoom-to-fit del match.
- **Filtros por tipo**: chips que ocultan/muestran familias.
- **Filtros por episodio**: dropdown "Solo lo del estudio Q1".
- **Modo temporal**: toggle activo/histórico/todo.
- **Layouts**: force-directed (default), hierarchical, circular, radial.
- **Export**: PNG / SVG.

---

## 7. Reportes — patrones visuales

### 7.1 Jerarquía de información

```
1. Decisión        ← lo que el comité necesita
2. Recomendación   ← acción concreta
3. Comparativa     ← respaldo visual rápido
4. Evidencia       ← respaldo detallado opcional
5. Plan            ← qué hacer ahora
6. Detalle técnico ← oculto por default, expandible
```

### 7.2 Charts recomendados

| Dato | Chart |
|---|---|
| 4 dimensiones × N variantes | **Radar superpuesto** (límite 4 variantes para legibilidad) |
| Total scores ranking | **Barras horizontales** con etiquetas grandes |
| Evolución de un test re-corrido | **Line chart** |
| Distribución de tipos de entidad en grafo | **Anillo (donut)** o **treemap** |
| Hechos por episodio | **Sparkline** en cada fila |
| Riesgos por categoría | **Bar chart agrupado** + color por nivel |
| Sentiment / brand lift histórico | **Area chart** |

Librería sugerida: **Recharts** (Vue-friendly via vue-recharts) o
**Chart.js** + **vue-chartjs**. Para el radar, vue-chartjs es suficiente
y se ve limpio.

### 7.3 Reglas para el reporte

- Cada sección tiene un **resumen ejecutivo de 1-2 frases** arriba.
- Cualquier número que no esté en una visualización debe tener **contexto**:
  no "73", sino "73 — bueno (rango 60-100)".
- **Citas en cursiva** del grafo del cliente cuando se respalda algo.
- **Glosario flotante** (`HelpHint`) para términos técnicos.
- Botón **Exportar PDF** que produce un documento idéntico a la web (no
  un dump de console).
- Botón **Compartir link** que genera URL pública (futuro: con token).

---

## 8. Sistema de diseño

### 8.1 Paleta

| Token | Hex | Uso |
|---|---|---|
| `--bg` | `#fafafa` | Fondo de página |
| `--surface` | `#ffffff` | Cards |
| `--surface-2` | `#f5f5f5` | Cards secundarios, blocks de código |
| `--border` | `#e5e7eb` | Bordes finos |
| `--border-strong` | `#d1d5db` | Bordes inputs |
| `--text` | `#0f172a` | Texto principal |
| `--text-muted` | `#64748b` | Texto secundario |
| `--text-soft` | `#94a3b8` | Placeholders, timestamps |
| `--accent` | `#1e3a8a` | Acción primaria, links activos |
| `--accent-soft` | `#dbeafe` | Backgrounds de badges info |
| `--success` | `#047857` | Recomendación activar, OK |
| `--success-soft` | `#d1fae5` | Background success |
| `--warn` | `#b45309` | Recomendación iterar, riesgo medio |
| `--warn-soft` | `#fef3c7` | Background warn |
| `--danger` | `#b91c1c` | Recomendación descartar, riesgo alto |
| `--danger-soft` | `#fee2e2` | Background danger |

**Nota**: paleta neutra deliberadamente. Color saturado solo en estados
y badges.

### 8.2 Tipografía

| Rol | Familia | Tamaño base |
|---|---|---|
| UI body | **Inter** (variable) | 14-15px |
| Headings | Inter (peso 600-700) | escala modular 1.25 |
| Datos / mono | **JetBrains Mono** o **IBM Plex Mono** | 12-13px |
| Reportes (lectura larga) | Inter 16px / interlineado 1.55 | |

Importar via Fontsource o Google Fonts. **No SVG icons artísticos**:
usar Lucide Icons (line) o Heroicons (outline).

### 8.3 Espaciado

Base 4px. Escala: `4 · 8 · 12 · 16 · 24 · 32 · 48 · 64`. Cards padding
24px. Secciones gap 32px. Tabs padding 12px 16px.

### 8.4 Bordes y sombras

| Elemento | Radio | Sombra |
|---|---|---|
| Inputs | 6px | none |
| Botones | 6px | none |
| Cards | 12px | `shadow-sm` (1px 2px rgba 0,0,0,.04) |
| Cards hover | 12px | `shadow-md` (4px 8px rgba 0,0,0,.06) |
| Modales | 16px | `shadow-xl` |
| Badges/pills | 9999px (full) | none |

### 8.5 Iconografía

- **Lucide Icons** vía `lucide-vue-next`.
- Stroke 1.5px, tamaño 16-20px en UI, 24px en heroes.
- Nunca emojis salvo si el usuario los pide.

---

## 9. Patrones específicos para planners y medios digitales

### 9.1 Terminología en UI (NO técnica)

| ❌ Evitar | ✅ Usar |
|---|---|
| "Score 73" | "Claridad: 73 (alta)" |
| "graph_id mirofish_…" | "Conocimiento del cliente" |
| "Episodio procesado" | "Documento ingerido" |
| "Embedding fallido" | "No pudimos analizar este chunk; revisar formato" |
| "Run completed" | "Test listo" |
| "Token usage" | (oculto en panel devtools) |

### 9.2 Comportamiento esperado

- **Cero refrescos manuales**. Toda lista se actualiza sola tras una
  acción (ingest, crear test).
- **Atajos de teclado** estilo Linear:
  - `Cmd+K` → búsqueda global.
  - `C` → crear (contextual).
  - `G + C` → ir a Clientes.
  - `Esc` → cerrar modal.
- **Indicador de progreso** siempre que algo tarde >1s (ingest, test).
- **Mensajes de error humanos**, nunca stack traces. Si hay traceback,
  ocultarlo bajo "Detalles técnicos".
- **Confirmaciones solo para destructivo**. Activar/descartar
  recomendación NO pide confirmación. Borrar cliente sí.

### 9.3 Onboarding

Primera vez que el usuario entra a un cliente vacío:
1. Un banner amigable "Empieza cargando contexto del cliente" → CTA al
   bloque de upload.
2. Después de subir el primer archivo, banner se cambia por
   "Crea tu primer creative test" → CTA al wizard.
3. Después del primer test, banner se reemplaza por la timeline normal.

---

## 10. Manual de uso (`/manual`)

Página única con sidebar TOC y contenido en columna derecha.

```
┌── /manual ──────────────────────────────────────────────────────┐
│ ┌── TOC ────┐  ┌── Contenido ──────────────────────────────┐    │
│ │ 1. Cómo   │  │ # 1. Cómo funciona la plataforma          │    │
│ │ 2. Cliente│  │                                            │    │
│ │ 3. Brand  │  │ 3 frases de qué hace y por qué.            │    │
│ │ 4. Tests  │  │                                            │    │
│ │ 5. Repor. │  │ ## Conceptos clave                          │    │
│ │ 6. Simul. │  │ - Cliente: agrupa todo el trabajo de una    │    │
│ │ 7. Glos.  │  │   marca.                                    │    │
│ └───────────┘  │ - Brand context: la memoria del cliente…    │    │
│                │ ...                                          │    │
│                └─────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

Secciones obligatorias:
1. **Cómo funciona la plataforma** — overview producto.
2. **Crear un cliente** — paso a paso con screenshots.
3. **Cargar contexto** — qué subir, qué evitar, formatos.
4. **Crear un creative test** — brief mínimo, lectura del reporte.
5. **Lanzar una simulación** — cuándo, costo aproximado, lectura.
6. **Generar un reporte** — qué incluye, cómo exportar.
7. **Glosario** — todos los términos con definición de 1 línea.
8. **Atajos de teclado** — tabla.
9. **FAQ** — Q&A frecuentes (cuota de Zep, embedding lento, etc.).

---

## 11. Estados globales (responsabilidad del frontend)

Todos los componentes de listado deben manejar:
- **Vacío inicial**: ilustración + CTA primario.
- **Cargando**: skeleton (no spinner — muestra estructura).
- **Error de red**: banner con retry.
- **Búsqueda sin resultados**: "No encontramos nada con ese filtro" + CTA limpiar.
- **Permisos** (futuro): "No tienes acceso a este cliente".

---

## 12. Accesibilidad (no-negociable)

- Contraste mínimo WCAG AA (4.5:1 texto, 3:1 elementos UI).
- Focus visible (outline azul 2px) en todos los elementos clickeables.
- Skip links arriba ("Saltar al contenido").
- Tab order coherente.
- ARIA labels en iconos sin texto.
- Tooltips también accesibles por teclado (foco activa + Esc cierra).

---

## 13. Roadmap de implementación del rediseño

| Fase | Entregable | Sesiones |
|---|---|---|
| R2.1 | Sistema de diseño base + tokens CSS + componentes atómicos refactorizados | 1 |
| R2.2 | Home / lista de clientes con nueva estética | 0.5 |
| R2.3 | Workspace cliente: layout 3-paneles + tabs | 1 |
| R2.4 | Pantalla de resultados de creative test (reporte one-page) | 1 |
| R2.5 | Vista de grafo (mini + fullscreen) | 1-2 |
| R2.6 | Manual de uso completo + buscador interno | 0.5 |
| R2.7 | Pulido + accesibilidad + atajos de teclado | 0.5 |

Total estimado: **5-6 sesiones**.

---

## 14. Referencias visuales sugeridas

Para inspirar estética sobria:
- **Linear** — densidad, jerarquía, atajos.
- **Vercel Dashboard** — paleta neutra + acento.
- **Notion** — composición de contenido en docs/reportes.
- **Stripe Sigma** — visualizaciones financieras claras.
- **Datadog** — dashboards de operación, sidebar contextual.

Para grafos:
- **ObservableHQ** — interacciones D3.
- **Neo4j Bloom** — exploración de grafos con filtros.
- **Maltego** — encoding visual robusto.

---

## Apéndice A: rutas existentes vs nuevas

| Ruta actual (R1) | Ruta nueva propuesta | Cambio |
|---|---|---|
| `/` (Home matrix-like) | `/` (Lista de clientes) | Reemplazo total |
| `/process/:projectId` | `/clients/:id/simulations/new` | Mover dentro del cliente |
| `/simulation/:simId` | `/clients/:id/simulations/:simId` | Mover |
| `/simulation/:simId/start` | `/clients/:id/simulations/:simId/run` | Mover |
| `/report/:reportId` | `/clients/:id/reports/:reportId` | Mover |
| `/interaction/:reportId` | `/clients/:id/reports/:reportId/chat` | Mover |
| `/clients` | `/` (mismo contenido) | Promover a raíz |
| `/clients/:id` | `/clients/:id/overview` | Default tab |
| `/creative-test?client=…` | `/clients/:id/creative-tests/new` | Reescribir como subruta |
| (nuevo) | `/manual` | Crear |
| (nuevo) | `/help` (atajos) | Crear |

Migración: redirects HTTP en el frontend mantienen compatibilidad por
~30 días. Después se eliminan.

---

## Apéndice B: API que ya está lista (para que diseño no la pida nuevamente)

- `GET /api/clients` — lista de clientes.
- `GET /api/clients/<id>` — detalle.
- `POST /api/clients` — crear.
- `PATCH /api/clients/<id>` — editar.
- `POST /api/clients/<id>/graph` — bootstrap del grafo.
- `POST /api/clients/<id>/context` — ingest de texto.
- `POST /api/clients/<id>/context/upload` — ingest de archivos.
- `GET /api/clients/<id>/context` — lista episodios + totales.
- `POST /api/clients/<id>/search` — búsqueda semántica.
- `GET /api/clients/<id>/creative-tests` — lista tests del cliente.
- `POST /api/report/creative-test/start` — crear test (con `client_id`).
- `GET /api/report/creative-test/<id>/status` — polling.
- `GET /api/report/creative-test/<id>` — detalle final.
- `GET /api/admin/graph-backend/health` — diagnóstico operativo.
- `GET /api/admin/graph-backend/metrics` — latencia por tool.

Todas devuelven `{ success: true, data: ... }` o errores con `error`
y código HTTP apropiado. El frontend solo necesita un cliente axios
con interceptor (ya existe en `frontend/src/api/index.js`).
