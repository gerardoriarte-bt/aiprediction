# Index de Roadmaps

## Objetivo
Centralizar los roadmaps del proyecto y dejar claro el orden de ejecución recomendado para el equipo.

## Principio de ejecución
- Todos los roadmaps son complementarios.
- Ningún roadmap debe romper o reemplazar el flujo actual.
- Cada fase posterior depende de la estabilidad de la fase anterior.

## Orden recomendado

### 1) Base y gobernanza de cambios
- [REGLAS_COMPLEMENTO.md](/Users/buentipo/Documents/GitHub/prediction/REGLAS_COMPLEMENTO.md)
  - Define las reglas de no regresión y compatibilidad.
  - Debe considerarse documento obligatorio antes de ejecutar cualquier roadmap.

### 2) Roadmap principal (prioridad alta)
- [ROADMAP_CREATIVE_TESTING_90D.md](/Users/buentipo/Documents/GitHub/prediction/docs/ROADMAP_CREATIVE_TESTING_90D.md)
  - Primer bloque de implementación.
  - Objetivo: habilitar creative testing de extremo a extremo para uso interno.

- [roadmap_creative_testing_9e49b2d5.plan.md](/Users/buentipo/Documents/GitHub/prediction/docs/roadmap_creative_testing_9e49b2d5.plan.md)
  - Versión de plan detallado en formato plan.
  - Sirve como referencia complementaria del roadmap principal.

- [UX_CREATIVE_TESTING_EXPERIENCE.md](/Users/buentipo/Documents/GitHub/prediction/docs/UX_CREATIVE_TESTING_EXPERIENCE.md)
  - Documento UX detallado para diseño de experiencia y operación por roles.
  - Debe guiar la implementación de interfaz durante el roadmap de creative testing.

### 3) Roadmap posterior (prioridad media, dependiente)
- [ROADMAP_CHANNEL_FREQUENCY_PLANNER_POST_CREATIVE_TESTING.md](/Users/buentipo/Documents/GitHub/prediction/docs/ROADMAP_CHANNEL_FREQUENCY_PLANNER_POST_CREATIVE_TESTING.md)
  - Se ejecuta solo después de completar la base de creative testing.
  - Objetivo: planificador de canal y frecuencia por funnel.

### 4) Infraestructura de conocimiento (transversal, coexistencia prolongada)
- [IMPLEMENTATION_ZEP_TO_POSTGRES.md](/Users/buentipo/Documents/GitHub/prediction/docs/IMPLEMENTATION_ZEP_TO_POSTGRES.md)
  - Plan de migración completa de Zep Cloud a PostgreSQL + pgvector con `GRAPH_BACKEND=zep|postgres`.
  - Puede avanzar en paralelo a otros roadmaps siempre respetando [REGLAS_COMPLEMENTO.md](/Users/buentipo/Documents/GitHub/prediction/REGLAS_COMPLEMENTO.md).

### 5) Runbooks operacionales
- [RUNBOOK_POSTGRES_BACKEND.md](/Users/buentipo/Documents/GitHub/prediction/docs/RUNBOOK_POSTGRES_BACKEND.md)
  - Operación del backend Postgres + pgvector.
- [RUNBOOK_CREATIVE_TESTING.md](/Users/buentipo/Documents/GitHub/prediction/docs/RUNBOOK_CREATIVE_TESTING.md)
  - Despliegue, requisitos de sistema (ffmpeg), envvars, costos por modalidad y smoke E2E.

## Dependencias resumidas
- `REGLAS_COMPLEMENTO` -> obligatorio para todos.
- `CREATIVE_TESTING_90D` -> prerrequisito para `CHANNEL_FREQUENCY_PLANNER`.
- `UX_CREATIVE_TESTING_EXPERIENCE` -> soporte de diseño para `CREATIVE_TESTING_90D`.
- `IMPLEMENTATION_ZEP_TO_POSTGRES` -> transversal; no sustituye otros roadmaps; habilita stack local sin Zep cuando `GRAPH_BACKEND=postgres`.

## Checklist de arranque por roadmap
- Confirmar que no introduce cambios breaking.
- Confirmar que es opt-in y complementario.
- Definir criterio de salida por fase.
- Definir plan de rollback.
- Validar continuidad del flujo actual de reporte.

## Nota de gobernanza
Si existe conflicto entre velocidad de implementación y compatibilidad, prevalece compatibilidad y estabilidad del sistema actual.
