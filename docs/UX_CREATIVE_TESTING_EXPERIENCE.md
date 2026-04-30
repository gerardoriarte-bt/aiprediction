# UX detallada - Creative Testing y acciones del plan

## Objetivo de experiencia
Disenar una experiencia interna para agencia que reduzca incertidumbre creativa antes del lanzamiento, con foco en decisiones rapidas y trazables por segmento y canal.

## Principios UX
- Claridad sobre complejidad: mostrar decisiones primero, detalle despues.
- Flujo guiado: evitar formularios ambiguos y pasos abiertos.
- Evidencia visible: cada recomendacion debe mostrar por que.
- Cero friccion operativa: tiempo total de corrida corto.
- Compatibilidad total: no interrumpir el flujo de reporte actual.

## Usuarios y necesidades
- Planner:
  - necesita estructurar brief rapidamente y comparar variantes.
- Estratega:
  - necesita validar ajuste a audiencia y riesgo de marca.
- Creativo:
  - necesita feedback util para iterar copy/claim/CTA.
- Account Lead:
  - necesita decision ejecutiva defendible frente al equipo.

## Mapa de experiencia extremo a extremo

### Paso 1: Crear corrida de Creative Testing
Pantalla: `Nuevo Test Creativo`

Objetivo del usuario:
- Definir que decision quiere tomar y sobre que audiencia.

Contenido y comportamiento:
- Bloque 1: Objetivo de negocio.
- Bloque 2: Audiencia objetivo (pais, region, NSE, edad, canal, sensibilidades).
- Bloque 3: Escenario detonante.
- Bloque 4: Variantes creativas (A/B/C...).
- Bloque 5: Criterios de exito.

Validaciones UX:
- Campos obligatorios visibles.
- Alertas de calidad del brief en tiempo real.
- Boton `Iniciar Test` habilitado solo cuando hay datos minimos validos.

### Paso 2: Ejecucion y seguimiento
Pantalla: `Test en progreso`

Objetivo del usuario:
- Entender que esta pasando sin revisar detalles tecnicos.

Contenido y comportamiento:
- Barra de progreso por etapa:
  - planificacion
  - evaluacion de variantes
  - scoring y riesgos
  - composicion de recomendaciones
- Estado por variante (pendiente, procesando, completada).
- Log resumido de hitos (no tecnico por defecto).

Patrones de UX:
- Mostrar tiempo estimado restante.
- Permitir salir de la pantalla sin perder corrida.
- Notificacion al completar.

### Paso 3: Resultado comparativo (nucleo de valor)
Pantalla: `Comparative Results`

Objetivo del usuario:
- Elegir variante ganadora por objetivo de campana.

Contenido y comportamiento:
- Ranking general de variantes.
- Scorecards por variante:
  - claridad de mensaje
  - ajuste a audiencia
  - intencion de conversion
  - riesgo de marca
- Semaforo de riesgo por variante.
- Recomendacion principal:
  - `activar`, `iterar`, o `descartar`.

Patrones de UX:
- Decision summary fijo en parte superior.
- Boton rapido `Ver evidencia`.
- Filtros por segmento, canal y objetivo.

### Paso 4: Evidencia y trazabilidad
Pantalla: `Evidencia por segmento`

Objetivo del usuario:
- Confirmar por que una variante quedo arriba/abajo.

Contenido y comportamiento:
- Hallazgos por segmento de audiencia.
- Fragmentos/citas de simulacion asociadas a cada score.
- Riesgos detectados con explicacion concreta.
- Diferencias frente a la segunda mejor variante.

Patrones de UX:
- Cada insight debe responder:
  - que paso
  - en quien paso
  - impacto esperado
  - accion sugerida

### Paso 5: Recomendaciones accionables
Pantalla: `Plan de activacion`

Objetivo del usuario:
- Salir con acciones listas para operar.

Contenido y comportamiento:
- Recomendaciones por horizonte:
  - 0-7 dias
  - 30 dias
  - 60-90 dias
- Ajustes de copy y CTA sugeridos por canal.
- Lista de riesgos a monitorear durante activacion.

Salida:
- Export ejecutivo para comite interno.
- Resumen de 1 pagina con decision, racional y riesgos.

## Arquitectura de pantallas (MVP interno)
- Vista 1: Nuevo Test Creativo.
- Vista 2: Test en Progreso.
- Vista 3: Resultados Comparativos.
- Vista 4: Evidencia y Detalle.
- Vista 5: Plan de Activacion + Export.

## Estados de interfaz que deben existir
- Empty state:
  - no hay corridas creadas.
- Loading state:
  - corrida inicializando o evaluando variantes.
- Success state:
  - resultados listos con recomendacion.
- Error state:
  - falla de corrida, con opcion de reintentar.
- Partial state:
  - corrida completa con secciones parciales (si alguna variante fallo).

## Reglas UX de no regresion
- El flujo actual de reporte debe mantenerse disponible.
- Las nuevas vistas de creative testing deben estar desacopladas y ser opt-in.
- Ninguna etiqueta o accion nueva debe bloquear rutas existentes.
- El export PDF actual debe seguir funcionando.

## Estandares de contenido para reportes de creative testing
- Resumen ejecutivo en lenguaje de negocio.
- Hallazgos separados por audiencia/segmento.
- Ranking de variantes con criterio explicito.
- Riesgos y mitigaciones accionables.
- Recomendaciones por canal con siguiente paso claro.

## Instrumentacion y metricas UX
- Tiempo de completitud de brief.
- Tiempo total de corrida.
- Tiempo hasta decision final.
- Tasa de uso de filtros (segmento/canal).
- Tasa de export de resultado.
- Tasa de cambios de decision despues de ver evidencia.

## Roadmap UX por fases

### Fase UX-1 (Semanas 1-3)
- Wizard de brief guiado + validaciones.
- Vista simple de progreso.

### Fase UX-2 (Semanas 4-7)
- Scorecards comparativos y ranking.
- Evidencia por segmento y riesgos.

### Fase UX-3 (Semanas 8-10)
- Biblioteca de audiencias reutilizables.
- Flujos por rol (planner/estratega/creativo).

### Fase UX-4 (Semanas 11-13)
- Dashboard de impacto interno.
- Ajustes de usabilidad por analitica real.

## Criterios de aceptacion UX
- Un planner nuevo puede crear una corrida en menos de 10 minutos.
- Un estratega puede seleccionar variante ganadora en menos de 5 minutos tras resultados.
- Un creativo recibe sugerencias concretas de iteracion por canal.
- Un account lead puede presentar un resumen ejecutivo sin abrir logs tecnicos.
