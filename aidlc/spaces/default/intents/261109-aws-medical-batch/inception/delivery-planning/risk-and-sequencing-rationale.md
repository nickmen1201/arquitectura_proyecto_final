# Risk and Sequencing Rationale — 261109-aws-medical-batch

> Upstream: requirements, unit-of-work-dependency, components

## Heurística de Secuenciación

**Walking skeleton first** (Cockburn): el primer Bolt construye la rodaja extremo-a-extremo más delgada que demuestra que la arquitectura completa funciona antes de invertir en infraestructura. Esta elección está respaldada por la práctica del equipo (`team.md` — Walking Skeleton: on).

No se usa WSJF formal porque el proyecto tiene solo 2 unidades y el orden del DAG fuerza la secuencia de todos modos (U2 depende de U1). La heurística y el DAG coinciden.

## Riesgos y Mitigaciones

| # | Riesgo | Probabilidad | Impacto | Bolt afectado | Mitigación |
|---|---|---|---|---|---|
| R1 | Incompatibilidad del código PySpark con el runtime de AWS Glue (versión de Spark, dependencias) | Media | Alto | Bolt 2 | Bolt 1 usa una sesión local de Spark con la misma versión que Glue; los tests con moto simulan S3. Detecta problemas de dependencias antes de desplegar. |
| R2 | Sesiones de laboratorio AWS Academy de 4 horas: el job Glue sobre 1,2 M de órdenes podría cortar una sesión | Media | Medio | Bolt 2 | Estimar el tiempo de ejecución en Bolt 1 (extrapolación desde los tests locales) antes del despliegue. Planificar el despliegue completo en una sola sesión. |
| R3 | Créditos de laboratorio insuficientes para pruebas repetidas | Baja | Medio | Bolt 2 | Validar el pipeline completamente con el dataset de 1,2 M en una sola ejecución de producción; no correr pruebas destructivas múltiples veces en AWS. |
| R4 | Catálogo CSV con datos incorrectos o formato inesperado | Baja | Alto | Bolt 1 | Validar los catálogos con fixtures en los tests de CatalogRepository antes de cualquier ejecución. |
| R5 | Incompatibilidad del LabRole con los permisos de Glue/S3 | Media | Alto | Bolt 2 | Verificar los permisos del LabRole contra los recursos del template antes del despliegue. Incluir un paso de validación (`aws iam simulate-principal-policy`) si el tiempo lo permite. |

## Justificación del Orden

**Bolt 1 antes de Bolt 2 porque:**
1. **DAG:** U2 referencia el script de U1 — no es posible construir el template CloudFormation sin el script listo.
2. **Riesgo:** Los riesgos R1 y R4 se descubren en Bolt 1 con costo bajo (pruebas locales), no en AWS.
3. **Valor de aprendizaje:** Bolt 1 valida que la lógica de negocio es correcta antes de gastar créditos de laboratorio en Bolt 2.
4. **Requisito académico:** El Comité Evaluador evalúa el código y las pruebas (Bolt 1) tanto como la evidencia de AWS (Bolt 2). Bolt 1 es necesario para Bolt 2 en ambas dimensiones.
