# Architecture Decision Records — 261109-aws-medical-batch

> Upstream: requirements, user-stories

## ADR-001: AWS Glue sobre EMR para el procesamiento batch

**Estado:** Aceptado

**Contexto:**
El job debe procesar hasta 12 millones de órdenes médicas en menos de 24 horas sobre un entorno de laboratorio AWS Academy con sesiones de 4 horas y créditos limitados. Se evaluaron tres opciones: AWS Glue (PySpark serverless administrado), Amazon EMR (clúster PySpark autogestionado) y AWS Lambda (procesamiento por eventos).

**Decisión:**
Usar AWS Glue con PySpark como motor de procesamiento.

**Consecuencias:**
- Positivas: sin gestión de clúster, facturación por segundo de uso, integración nativa con S3 y CloudWatch, soporte de IAM roles de laboratorio sin configuración adicional de red.
- Negativas: mayor costo por DPU-hora que EMR en cargas sostenidas; Glue no admite Spark UI interactivo en el laboratorio.
- Deuda: si el volumen crece más allá de 12 M o el costo resulta prohibitivo, migrar a EMR Auto-scaling es el camino natural sin cambios en la lógica PySpark.

**Alternativas descartadas:**
- *EMR*: requiere gestión de clúster (bootstrap, Auto Scaling), mayor complejidad operativa en un laboratorio con sesiones cortas, y la misma lógica PySpark igualmente funciona en Glue.
- *Lambda*: límite de 15 min de ejecución y 10 GB de memoria, inadecuado para un DataFrame de 12 M de filas; no admite PySpark nativo.

---

## ADR-002: S3 Parquet como único destino de salida (sin DynamoDB ni Athena)

**Estado:** Aceptado

**Contexto:**
Los resultados de clasificación deben ser consultables por el Analista de Resultados y auditables por el Comité Evaluador. Se evaluaron tres patrones de salida: solo S3 Parquet, S3 + DynamoDB (registro por ítem), S3 + Athena (tabla registrada).

**Decisión:**
Escribir únicamente a S3 en formato Parquet particionado por `fecha`. No registrar tabla en Athena ni escribir a DynamoDB en el job principal.

**Consecuencias:**
- Positivas: menor complejidad (un solo destino), menor costo (no se paga escritura DPU en DynamoDB), Parquet es nativo para análisis con pandas/Athena ad hoc.
- Negativas: sin tabla Athena preconfigurada; el Analista debe leer el Parquet directamente o registrar la tabla manualmente.
- El Comité Evaluador puede usar `aws s3 cp` + pandas para verificar la salida sin herramientas adicionales.

**Alternativas descartadas:**
- *DynamoDB*: escritura ítem por ítem a 12 M de registros es costosa y lenta desde Glue; el caso de uso es analítico (consulta por lotes), no transaccional.
- *Athena catalog*: agrega valor pero no es requerido por los criterios de aceptación; se puede registrar post-facto sin modificar el job.

---

## ADR-003: SHA-256(DNO + SeguroSocial) como identificador irreversible de paciente

**Estado:** Aceptado

**Contexto:**
Los archivos de salida no deben contener PII (NFR2). El registro de entrada tiene `dno` y `seguro_social` como identificadores del paciente. Se necesita un identificador que permita correlacionar registros del mismo paciente entre ejecuciones sin revelar la identidad.

**Decisión:**
Calcular `paciente_hash = SHA-256(dno + seguro_social)` como cadena hexadecimal de 64 caracteres. Los campos `dno` y `seguro_social` no se incluyen en ningún archivo de salida.

**Consecuencias:**
- Positivas: función unidireccional, determinista entre ejecuciones (mismo par produce el mismo hash), sin dependencia de servicio externo, cero costo adicional.
- Negativas: si el formato de entrada de `dno` o `seguro_social` varía, el hash cambiaría para el mismo paciente; por ello `PatientPrivacyService` aplica normalización antes de hashear: strip de espacios extremos y conversión a mayúsculas en ambos campos.
- El componente `PatientPrivacyService` es el único punto donde los campos PII se consumen y se normaliza su formato; cualquier auditoría de privacidad solo examina ese componente.

**Alternativas descartadas:**
- *Tokenización con AWS Secrets Manager*: mayor complejidad, costo adicional por API call, y el token requeriría una tabla de mapeo que sí contendría PII.
- *Encriptación simétrica*: reversible; no cumple el requisito NFR2 de "identificador irreversible".
- *Omitir el identificador*: imposibilita correlacionar registros del mismo paciente entre runs, perdiendo valor analítico.

---

## ADR-004: Clasificación por lookup de catálogo (no modelo ML)

**Estado:** Aceptado

**Contexto:**
La clasificación de cobertura podría implementarse como reglas deterministas o como un modelo de aprendizaje automático. El enunciado provee dos archivos CSV de catálogo (`COIL_catalogo_servicios_cubiertos.csv`, `COIL_catalogo_perfiles_cobertura.csv`) que definen exhaustivamente el espacio de decisión.

**Decisión:**
Implementar la clasificación como lookup determinista en memoria: buscar `servicio_solicitado` en el catálogo de servicios y `perfil_cobertura` en el catálogo de perfiles. No usar ML.

**Consecuencias:**
- Positivas: totalmente trazable (FR10, NFR1), sin dependencia de entrenamiento ni infraestructura ML, determinista entre ejecuciones (NFR3), 100% testeable con fixtures.
- Negativas: sin capacidad de generalización; si aparece un servicio fuera del catálogo, el sistema devuelve `cubre=NO` (RG-00). Un perfil fuera del catálogo se considera error grave (ERROR_PERFIL) y va a cuarentena.
- Esta decisión es coherente con el diseño del enunciado: los catálogos son la fuente de verdad.

**Alternativas descartadas:**
- *ML/NLP*: sobredimensionado para un espacio de decisión cerrado y completamente definido por dos CSVs; añade complejidad de entrenamiento, validación y drift sin beneficio para este caso.

---

## ADR-005: CloudFormation como única herramienta IaC (sin CDK)

**Estado:** Aceptado

**Contexto:**
La infraestructura (bucket S3, Glue Job, parámetros SSM) debe desplegarse de forma reproducible. Se evaluaron CloudFormation (YAML nativo) y AWS CDK (TypeScript/Python que genera CloudFormation).

**Decisión:**
Usar CloudFormation YAML directamente, desplegado con `aws cloudformation deploy`. El template recibe el parámetro `GlueRoleArn` para el ARN del LabRole existente (el laboratorio no permite crear IAM Roles).

**Consecuencias:**
- Positivas: sin dependencia de runtime adicional (Node.js para CDK), evaluable directamente por el Comité Evaluador leyendo el YAML, alineado con el mandato `team.md` (IaC = CloudFormation).
- Negativas: más verboso que CDK para recursos complejos; sin abstracciones de alto nivel.
- El parámetro `GlueRoleArn` desacopla el template del ARN específico del laboratorio, cumpliendo NFR5.

**Alternativas descartadas:**
- *CDK*: añade Node.js como dependencia de build, genera CloudFormation de todos modos, y no ofrece ventaja observable para 3-4 recursos.
- *Terraform*: no está en el stack del equipo y requiere state backend externo.

---

## ADR-006: CatalogRepository como componente independiente de CoverageClassifier

**Estado:** Aceptado

**Contexto:**
La lógica de clasificación necesita acceder a los dos catálogos CSV. Este acceso podría integrarse dentro de `CoverageClassifier` o delegarse a un componente separado.

**Decisión:**
Separar la carga y exposición de catálogos en `CatalogRepository`, que `CoverageClassifier` consulta mediante dos métodos: `is_service_covered(name)` y `get_profile_percentage(profile)`.

**Consecuencias:**
- Positivas: `CoverageClassifier` es testeable con un mock de `CatalogRepository` sin necesidad de CSV reales; `CatalogRepository` es testeable independientemente con CSV fixtures. Cambio de fuente (S3 → base de datos) solo toca `CatalogRepository`.
- Negativas: una indirección adicional en el código; mayor número de clases para un proyecto pequeño.
- Esta separación satisface directamente el requisito de pruebas unitarias aisladas (team.md, 80% coverage floor).

**Alternativas descartadas:**
- *CoverageClassifier lee los CSVs directamente*: acopla I/O con lógica; imposibilita pruebas unitarias de clasificación sin acceso a S3 o archivos locales.

---

## ADR-007: ERROR_PERFIL enruta a cuarentena (sin fallback a 0%)

**Estado:** Aceptado

**Contexto:**
Cuando un registro contiene un `perfil_cobertura` que no existe en `ProfileCatalog`, hay dos estrategias posibles: (a) reportar el registro en cuarentena con código ERROR_PERFIL, o (b) aplicar un default de 0% de cobertura y continuar.

**Decisión:**
Un perfil desconocido es un error de datos irrecuperable: el registro va a cuarentena con código ERROR_PERFIL. No se aplica ningún porcentaje por defecto.

**Consecuencias:**
- Positivas: el Analista de Resultados puede detectar y corregir catálogos incompletos; ningún registro recibe una clasificación incorrecta silenciosamente.
- Negativas: registros válidos (servicio cubierto) se pierden en cuarentena si el catálogo de perfiles está desactualizado.
- Esta decisión hace que la integridad del catálogo sea un prerrequisito operacional, coherente con el diseño académico del proyecto.

**Alternativas descartadas:**
- *Default 0% (RG-00)*: oculta errores de catálogo; un perfil nuevo legítimo (p.ej. ESPECIAL al 75%) sería clasificado erróneamente como no cubierto, generando un resultado incorrecto sin señal de error.
