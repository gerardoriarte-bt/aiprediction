# Creative Testing - Plantilla de Brief

Plantilla operativa para preparar una corrida de Creative Testing.
Copia esta seccion como punto de partida para cada cuenta o campana.

> Esta plantilla es complementaria. No reemplaza el flujo actual de reporte;
> alimenta el endpoint dedicado `POST /api/report/creative-test/generate`.

## 1. Objetivo de negocio
> Una linea: que decision necesita tomar el equipo en las proximas 1-2 semanas.

Ejemplo: "Decidir el claim principal para el lanzamiento de la nueva linea de skincare en Black Friday MX."

## 2. Escenario detonante
> Contexto que justifica la prueba: ventana de campana, presion competitiva, urgencia.

Ejemplo: "Black Friday MX, 7 dias de runway, alta saturacion de mensajes promocionales en categoria belleza."

## 3. Audiencia objetivo
- Nombre interno: `_______________`
- Pais / region: `_______________`
- NSE: `_______________`
- Rango de edad: `_______________`
- Canal preferido: `_______________`
- Sensibilidades / banderas rojas: `_______________`
- Notas adicionales: `_______________`

## 4. Variantes creativas (2 a 8)
Llenar una entrada por variante. El `label` debe ser unico (A, B, C, ...).

| Label | Headline | Cuerpo | CTA | Tono | Concepto visual |
|-------|----------|--------|-----|------|-----------------|
| A     |          |        |     |      |                 |
| B     |          |        |     |      |                 |
| C     |          |        |     |      |                 |

## 5. Canales de activacion candidatos
- `instagram, tiktok, youtube, ...`

## 6. Metricas de exito
- Nombre / objetivo / descripcion. Ejemplos:
  - `CTR / >= 1.5% / clic en pieza paga`
  - `Add-to-cart rate / >= 3% / con tracking en carrito`
  - `Brand lift / +5pp recall / encuesta post-exposicion`

## 7. Riesgos a vigilar (opcional, ayuda al scoring)
- Reputacionales: `_______________`
- Legales / compliance: `_______________`
- Promesa no sustentada: `_______________`
- Fatiga de mensaje: `_______________`

## 8. Calidad minima del brief
Antes de iniciar la corrida, confirmar:
- Objetivo de negocio claro y cerrado.
- Audiencia con al menos `nombre`.
- Minimo 2 variantes con `headline` no vacio.
- Al menos un canal y una metrica de exito.
- Sin datos sensibles ni secretos en el cuerpo del brief.

## 9. JSON de envio (referencia para el endpoint)
```json
{
  "business_goal": "Decidir el claim principal para Black Friday MX",
  "scenario": "Black Friday MX, 7 dias de runway, alta saturacion",
  "audience_profile": {
    "name": "Mujeres 25-34 CDMX",
    "country": "MX",
    "primary_channel": "Instagram",
    "age_range": "25-34",
    "sensitivities": ["claims clinicos sin sustento"]
  },
  "creative_variants": [
    { "label": "A", "headline": "Glow real, sin filtros", "cta": "Comprar ya", "tone": "Confianza" },
    { "label": "B", "headline": "Tu rutina, tu ritual", "cta": "Descubrir", "tone": "Aspiracional" },
    { "label": "C", "headline": "24h hidratacion clinica", "cta": "Probar 7 dias", "tone": "Funcional" }
  ],
  "channels": ["instagram", "tiktok"],
  "success_metrics": [
    { "name": "CTR", "target": ">= 1.5%" },
    { "name": "Add-to-cart rate", "target": ">= 3%" }
  ]
}
```

## 10. Activacion del endpoint
1. Verificar que el backend tenga `CREATIVE_TESTING_ENABLED=true` (default: false).
2. `POST http://<host>/api/report/creative-test/generate` con el JSON anterior.
3. Recuperar resultados: `GET /api/report/creative-test/<test_id>`.
4. Listar corridas recientes: `GET /api/report/creative-test/list`.
5. Estado de la feature: `GET /api/report/creative-test/health`.

> Nota: la rebanada actual usa un runner mock determinista. Cuando se habilite
> Fase 2, el mismo contrato alimentara el motor de scoring real sin cambiar la
> forma de respuesta esperada por el frontend.
