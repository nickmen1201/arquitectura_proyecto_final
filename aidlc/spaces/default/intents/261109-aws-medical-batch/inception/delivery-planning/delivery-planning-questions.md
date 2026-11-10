# Delivery Planning — Questions

> Upstream: requirements, components, unit-of-work, unit-of-work-dependency, stories, unit-of-work-story-map, contract-summary, team-practices

## Strategic Questions

**Q1 — ¿Qué construir primero?**
Walking skeleton: U1 primero (flujo completo con ~1 000 órdenes), luego U2 cuando el código esté verificado.
[Answer]: A

**Q2 — ¿Usar modelo de puntuación formal (WSJF)?**
No aplica: proyecto de 2 unidades con un único desarrollador y orden de DAG forzado.
[Answer]: A

**Q3 — ¿Tamaño del Bolt?**
Una unidad por Bolt. No hay ganancia en subdividir o agrupar para un proyecto unipersonal.
[Answer]: A

**Q4 — ¿Bolts en paralelo?**
No: único desarrollador + DAG lineal (U2 depende de U1).
[Answer]: A

**Q5 — ¿Bloqueos externos?**
AWS Academy: sesiones de 4 horas y créditos limitados. El despliegue en AWS (Bolt 2) debe planificarse dentro de una sesión.
[Answer]: A

**Q6 — ¿Qué preocupa más?**
La compatibilidad del job PySpark con el runtime de AWS Glue (Bolt 1 lo valida antes de desplegar en Bolt 2).
[Answer]: A

## Per-Bolt Questions

**Bolt 1 — u1-batch-job**

- Unidades: U1 (u1-batch-job)
- ¿Es el walking skeleton? Sí — recorre el flujo completo S3 → parsear → clasificar → Parquet + cuarentena.
- Definición de Done: suite pytest pasa, cobertura ≥ 80%, smoke test con ~1 000 órdenes produce Parquet con los 14 campos y registros de cuarentena correctos.
- Hipótesis de confianza: la lógica de clasificación funciona correctamente y los tests con moto confirman que S3 I/O es sólida antes de tocar AWS real.
- Propietario: aidlc-developer-agent (proyecto solo, sin equipo).

**Bolt 2 — u2-infrastructure**

- Unidades: U2 (u2-infrastructure)
- ¿Es el walking skeleton? No — consolida el despliegue real en AWS.
- Definición de Done: stack CloudFormation desplegado exitosamente en AWS Academy; job Glue procesa el dataset de 1,2 M de órdenes sin errores; argumento analítico de escalado a 12 M en < 24 h documentado (FR8/FR10/US4.1); evidencia capturada (logs CloudWatch, muestra de Parquet de salida).
- Hipótesis de confianza: el template CloudFormation es correcto para el laboratorio AWS Academy (LabRole, sin crear IAM roles), y el diseño PySpark escala al volumen del enunciado según el argumento analítico.
- Propietario: aidlc-developer-agent.

## Verification Command

Comando propuesto: `pytest --cov=src --cov-report=term-missing --cov-fail-under=80`
[Answer]: A — aprobado por el usuario.
