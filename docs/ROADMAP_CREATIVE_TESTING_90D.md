# Roadmap 90 dias - Creative Testing First

## Proposito
Convertir la herramienta actual en un motor interno de decisiones para agencia (retail/eCommerce), priorizando `creative testing` como capacidad complementaria al flujo existente.

## Principio de implementacion
- Todo el roadmap es aditivo.
- No reemplaza ni degrada el pipeline actual de reportes.
- El flujo actual debe seguir operando igual si las nuevas capacidades no se activan.

## Alcance de negocio (uso interno)
- Usuarios objetivo: planner, estratega, creativo, account lead.
- Resultado esperado: decidir rapidamente que variante creativa activar por segmento y canal.
- Tiempo objetivo por corrida: menor a 30 minutos desde brief hasta recomendacion.

## Fase 1 (Semanas 1-3) - Fundacion de Creative Testing

### Objetivo
Estandarizar entradas y habilitar corridas comparativas de variantes creativas.

### Entregables
- Contrato de entrada de creative testing:
  - `business_goal`
  - `audience_profile`
  - `scenario`
  - `creative_variants[]`
  - `channels[]`
  - `success_metrics[]`
- Endpoint dedicado para iniciar pruebas de creatividades.
- Prompt pack base para retail/eCommerce.
- Plantilla de brief oficial para el equipo.

### Criterio de exito
- Ejecutar una corrida con 3-5 variantes y obtener comparativo consistente.

## Fase 2 (Semanas 4-7) - Scoring y decision

### Objetivo
Pasar de narrativa a scorecards accionables para toma de decisiones.

### Entregables
- Marco de scoring por variante y segmento:
  - `message_clarity_score`
  - `audience_fit_score`
  - `conversion_intent_score`
  - `brand_risk_score`
- Matriz de riesgos (reputacional, legal/compliance, promesa no sustentada, fatiga de mensaje).
- Ranking final de variantes con recomendacion de activacion por canal.

### Criterio de exito
- El equipo puede decidir la creatividad ganadora sin revisar logs tecnicos.

## Fase 3 (Semanas 8-10) - Operacion interna de agencia

### Objetivo
Hacer el flujo repetible por cuentas y por roles.

### Entregables
- Workflow interno por rol:
  - planner prepara brief
  - estrategia define criterios de exito
  - creativo itera variantes
  - account lider valida decision
- Biblioteca de audiencias reutilizables retail/eCommerce.
- Plantillas de salida para comite interno.

### Criterio de exito
- Proceso semanal estable, sin configuraciones ad-hoc.

## Fase 4 (Semanas 11-13) - Medicion y calibracion

### Objetivo
Medir impacto real y ajustar recomendaciones.

### Entregables
- Captura de resultados reales post-campana (ganadora real vs sugerida).
- Ajuste de pesos de scoring segun desempeno observado.
- Dashboard de impacto:
  - tiempo brief->decision
  - adopcion del flujo
  - lift de performance en piezas testeadas

### Criterio de exito
- Evidencia de ROI interno y base para escalar a experiencia cliente-visible.

## Backlog priorizado
1. Contrato de entrada y validaciones de creative testing.
2. Endpoint dedicado de ejecucion.
3. Prompt pack retail/eCommerce.
4. Scoring engine por variante/segmento.
5. UI comparativa de resultados y ranking.
6. Export ejecutivo para decision interna.
7. Biblioteca de audiencias reutilizables.
8. Loop de calibracion con resultados reales.

## Riesgos y mitigaciones
- Brief incompleto:
  - mitigacion: validaciones obligatorias y plantilla guiada.
- Exceso de narrativa:
  - mitigacion: salida estructurada obligatoria (ranking + accion + riesgo).
- Baja adopcion:
  - mitigacion: interfaz por rol y SLA de entrega corto.

## Hitos de evaluacion al dia 90
- 80% de corridas internas usan plantilla estructurada.
- 70% de decisiones creativas pasan por creative testing.
- Reduccion medible del tiempo de analisis pre-lanzamiento.
- Scorecard usado como fuente principal en comite de campana.
