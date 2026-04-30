# Reglas de Implementacion Complementaria

## Objetivo
Este documento define reglas obligatorias para asegurar que toda mejora futura sea un complemento del sistema actual, sin romper, sobrescribir ni alterar el comportamiento existente.

## Principio rector
- Todo cambio nuevo debe ser aditivo y reversible.
- La funcionalidad actual es la linea base y no debe degradarse.

## Reglas obligatorias

### 1) No regresion funcional
- No eliminar rutas, componentes, servicios o flujos existentes.
- No cambiar contratos de entrada/salida ya usados por frontend o backend.
- Si se requiere un ajuste en contratos, debe ser compatible hacia atras.

### 2) Extension por capas, no reemplazo
- Crear nuevas capacidades en endpoints, servicios o componentes nuevos cuando sea posible.
- Evitar reescrituras completas de modulos que ya funcionan.
- Si un modulo requiere evolucion, hacerlo por extension controlada (banderas de modo, adaptadores o estrategias).

### 3) Compatibilidad hacia atras
- Mantener comportamiento por defecto igual al actual.
- Cualquier nueva opcion debe ser opt-in, no obligatoria para flujos existentes.
- Soportar datos antiguos y formatos actuales durante transicion.

### 4) Seguridad de configuracion
- No hardcodear secretos, claves o configuraciones sensibles.
- Toda configuracion nueva debe entrar por variables de entorno y valores por defecto seguros.

### 5) Integridad de experiencia actual
- No modificar copy, estructura o navegacion actual salvo que sea estrictamente necesario.
- Cualquier cambio visual debe convivir con la interfaz actual y no bloquear flujos existentes.

### 6) Persistencia y datos
- No sobrescribir archivos existentes de reporte, logs o metadata historica.
- Nuevos artefactos deben guardarse en archivos/campos nuevos o versionados.
- Mantener lectura de formatos previos para no perder historial.

### 7) Calidad y validacion
- Todo complemento debe incluir validacion de no regresion.
- Probar al menos:
  - Generacion de reporte actual.
  - Visualizacion actual en Step 4.
  - Exportacion PDF actual.
- Si un complemento falla, el sistema debe poder seguir operando con el flujo actual.

### 8) Observabilidad sin ruido
- No eliminar logs actuales.
- Los logs nuevos deben ser trazables y no romper el formato existente.
- Priorizar mensajes utiles para diagnosticar sin afectar rendimiento.

### 9) Gobernanza de cambios
- Cada entrega debe incluir:
  - Alcance aditivo exacto.
  - Riesgo de impacto.
  - Plan de rollback.
- Ninguna entrega debe fusionarse sin evidencia de compatibilidad.

### 10) Prioridad del roadmap
- Lo planificado se implementa como complemento de capacidades existentes.
- En este proyecto, el foco inicial (creative testing) debe integrarse como modulo adicional, no como sustitucion del flujo de reporte actual.

## Criterios de aceptacion globales
- El flujo actual funciona igual antes y despues del cambio.
- Las nuevas funciones pueden activarse sin afectar usuarios actuales.
- Existe ruta clara para desactivar el complemento si se detecta incidencia.

## Clausula de proteccion
Si una propuesta requiere romper compatibilidad o reemplazar comportamiento base, debe detenerse y rediseñarse bajo un enfoque aditivo.
