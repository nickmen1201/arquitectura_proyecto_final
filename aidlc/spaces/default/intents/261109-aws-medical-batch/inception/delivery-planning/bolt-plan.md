# Bolt Plan — 261109-aws-medical-batch

> Upstream: unit-of-work, unit-of-work-dependency, requirements, components

A **Bolt** (un pase de construcción completo sobre una parte del trabajo, que termina en algo que corre) define qué Unidades de Trabajo se construyen juntas, en qué orden, y qué debe ser verdad para que ese pase se considere terminado.

## Secuencia

| # | Bolt | Unidades | Walking Skeleton | Propietario |
|---|---|---|---|---|
| 1 | `bolt-1-batch-job` | U1 `u1-batch-job` | ⚡ Sí | aidlc-developer-agent |
| 2 | `bolt-2-infrastructure` | U2 `u2-infrastructure` | No | aidlc-developer-agent |

---

## Bolt 1 — batch-job ⚡ (Walking Skeleton)

**Unidades incluidas:** U1 (`u1-batch-job`)

**Walking skeleton:** Sí. Esta es la rodaja extremo-a-extremo más delgada (Cockburn): implementa todos los componentes Python del sistema — GlosaParser, CatalogRepository, CoverageClassifier, PatientPrivacyService y BatchPipeline — y demuestra el flujo completo con un dataset de ~1 000 órdenes antes de que Bolt 2 despliegue el sistema en AWS.

**Qué demuestra el skeleton:**
- Lectura de CSV desde S3 (simulado con moto en tests de integración)
- Parseo de glosa y clasificación correcta (RG-01/RG-00)
- Hash irreversible de paciente con separador `|` (SHA-256)
- Escritura de Parquet con 14 campos y registros de cuarentena (ERROR_PARSEO / ERROR_PERFIL)
- Métricas en stdout (capturables por CloudWatch)

**Demo esperado:** Correr `pytest` completo + smoke test que procesa ~1 000 órdenes y verifica que el Parquet de salida contiene los 14 campos definidos en FR7 y que los registros malformados van a cuarentena.

**Definición de Done:**
- Todos los componentes implementados (GlosaParser, CatalogRepository, CoverageClassifier, PatientPrivacyService, BatchPipeline)
- Suite pytest pasa sin errores
- Cobertura de líneas ≥ 80% (`pytest --cov=src --cov-fail-under=80`)
- Smoke test con ~1 000 órdenes produce Parquet con 14 campos correctos y cuarentena con códigos ERROR_PARSEO / ERROR_PERFIL según corresponda
- Ninguna credencial hardcodeada en el código (NFR5)
- Black + Ruff sin errores

**Hipótesis de confianza:** La lógica de clasificación funciona correctamente según los catálogos CSV, y los tests de integración con moto confirman que el acceso a S3 es sólido antes de tocar AWS real.

---

## Bolt 2 — infrastructure

**Unidades incluidas:** U2 (`u2-infrastructure`)

**Walking skeleton:** No. Consolida el despliegue real en AWS Academy y produce la evidencia de ejecución que el Comité Evaluador evalúa.

**Demo esperado:** Stack CloudFormation desplegado con un único comando `aws cloudformation deploy`; job Glue ejecutado sobre el dataset real de 1,2 M de órdenes; log de CloudWatch con métricas; muestra de Parquet de salida (comando `aws s3 select` o pandas); documento de diseño técnico con argumento analítico de escalado a 12 M en < 24 h.

**Definición de Done:**
- Template CloudFormation válido: S3 bucket, Glue job, parámetro `GlueRoleArn` (sin crear IAM roles)
- Despliegue exitoso con `aws cloudformation deploy` desde cero
- Job Glue ejecuta el dataset de 1,2 M de órdenes sin errores; Parquet de salida en S3
- Log de CloudWatch con la línea de métricas (`records_input`, `records_output`, `records_quarantined_parseo`, `records_quarantined_perfil`, `duration_seconds`, `run_id`)
- Argumento analítico de escalado a 12 M en < 24 h documentado (FR8/FR10): estimación de DPUs Glue × tiempo, con soporte del AWS Pricing Calculator o métricas reales del laboratorio (nunca inventadas)
- Documento de diseño técnico completo (FR10 / US5.1): diagrama de arquitectura, justificación de servicios, lógica de clasificación, escalado, costo
- Evidencia de ejecución capturada para entrega académica (FR11 / US5.2)
- Stack eliminable con `aws cloudformation delete-stack` sin residuos

**Hipótesis de confianza:** El template CloudFormation es correcto para el laboratorio AWS Academy (LabRole, sin crear IAM roles), y el diseño PySpark escala al volumen del enunciado según el argumento analítico.

---

## Orden del DAG

```
Bolt 1 (u1-batch-job)  →  Bolt 2 (u2-infrastructure)
```

Bolt 2 no puede comenzar hasta que Bolt 1 esté verificado y aprobado (el template CloudFormation referencia el script de Bolt 1 en `--ScriptLocation`).
