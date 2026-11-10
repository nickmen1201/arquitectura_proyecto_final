# User Stories — 261109-aws-medical-batch

## Sources

- requirements.md (FR1–FR11, NFR1–NFR6)
- personas.md (Operador de Proceso, Analista de Resultados, Comité Evaluador)

---

## Grupo 1: Despliegue e Infraestructura

### US1.1 — Despliegue con CloudFormation
**Como** Operador de Proceso, **quiero** desplegar toda la infraestructura (buckets S3 y Glue Job) con un único comando `aws cloudformation deploy --parameter-overrides GlueRoleArn=<LabRole-ARN>`, **para** no realizar ninguna configuración manual en la consola AWS y poder reproducir el entorno desde cero.

**Prioridad:** Must Have

**Criterios de aceptación:**

- **AC1.1.1:**
  - **Given** un CloudFormation template con el parámetro `GlueRoleArn` y sin ningún recurso `AWS::IAM::Role`
  - **When** se ejecuta `aws cloudformation deploy --parameter-overrides GlueRoleArn=<LabRole-ARN>`
  - **Then** el stack alcanza estado `CREATE_COMPLETE` o `UPDATE_COMPLETE` sin errores

- **AC1.1.2:**
  - **Given** un stack desplegado con el template
  - **When** se revisan los recursos del stack en la consola o con `aws cloudformation describe-stack-resources`
  - **Then** existen los buckets S3 de entrada, salida y scripts, y el Glue Job usa el ARN del LabRole recibido como parámetro; no existe ningún recurso IAM Role creado por el template

- **AC1.1.3:**
  - **Given** el CloudFormation template versionado en Git
  - **When** se inspecciona el archivo buscando `AWS::IAM::Role`
  - **Then** no se encuentra ninguna declaración de ese tipo de recurso

- **AC1.1.4:**
  - **Given** un stack recién desplegado con el template
  - **When** se intenta disparar el Glue Job sin pasos adicionales
  - **Then** el job pasa a estado `RUNNING` sin requerir configuración manual adicional

**Dependencias:** NFR5 (seguridad credenciales), FR9

---

### US1.2 — Rollback del stack
**Como** Operador de Proceso, **quiero** poder eliminar y redesplegar el stack completo con `aws cloudformation delete-stack` seguido de `deploy`, **para** recuperarme de un despliegue fallido sin dejar recursos huérfanos en AWS.

**Prioridad:** Should Have

**Criterios de aceptación:**

- **AC1.2.1:**
  - **Given** un stack existente en AWS
  - **When** se ejecuta `aws cloudformation delete-stack --stack-name <nombre>`
  - **Then** todos los recursos del stack son eliminados sin errores y el stack desaparece de la consola

- **AC1.2.2:**
  - **Given** que el stack fue eliminado previamente
  - **When** se ejecuta `aws cloudformation deploy` desde el template versionado en Git
  - **Then** el entorno completo se recrea y el job puede ejecutarse de nuevo

**Dependencias:** US1.1

---

## Grupo 2: Ejecución del Job de Clasificación

### US2.1 — Ejecutar clasificación batch
**Como** Operador de Proceso, **quiero** disparar el Glue Job pasando la ruta S3 del archivo de glosas como parámetro, **para** clasificar todas las órdenes médicas del lote en modo batch sin intervención manual durante el procesamiento.

**Prioridad:** Must Have

**Criterios de aceptación:**

- **AC2.1.1:**
  - **Given** un Glue Job desplegado con el template
  - **When** se inicia el job con la ruta S3 del archivo de entrada como parámetro de Glue Job Arguments
  - **Then** el job acepta el parámetro y comienza el procesamiento

- **AC2.1.2:**
  - **Given** el dataset `COIL_dataset_glosas_salud_1_2M.csv` (1 200 000 registros) en S3
  - **When** el job termina su ejecución
  - **Then** el log del job registra `records_input = 1200000` y no se truncó ningún registro

- **AC2.1.3:**
  - **Given** un job en ejecución con el dataset completo
  - **When** el job finaliza su procesamiento
  - **Then** el estado del job en la consola AWS Glue es `SUCCEEDED`

- **AC2.1.4:**
  - **Given** un job con estado `SUCCEEDED`
  - **When** se revisa el bucket S3 de salida
  - **Then** el archivo Parquet de resultados está escrito y es legible

**Dependencias:** US1.1, FR1

---

### US2.2 — Resultado con los 14 campos del esquema de salida definido en FR7
**Como** Analista de Resultados, **quiero** que cada orden procesada tenga en el Parquet de salida los 14 campos definidos en FR7 (incluyendo `id_solicitud`, `cubre`, `porcentaje_cobertura`, `regla_aplicada`, `valor_cubierto`, `paciente_hash`, `run_id`, `perfil_cobertura`, `servicio_solicitado`, `entidad_emisora`, `medio_emisor`, `valor_procedimiento`, `fecha` y `timestamp_proceso`), **para** verificar la decisión de cobertura de cada solicitud sin acceder a datos de identificación personal del paciente.

**Prioridad:** Must Have

**Criterios de aceptación:**

- **AC2.2.1:**
  - **Given** el Parquet de salida generado por el job
  - **When** se inspecciona el esquema del archivo
  - **Then** contiene exactamente los 14 campos de FR7 y no existen columnas `nombre_paciente` ni `seguro_social`

- **AC2.2.2:**
  - **Given** cualquier registro en el Parquet de salida
  - **When** se inspecciona el campo `paciente_hash`
  - **Then** es un string hexadecimal de exactamente 64 caracteres (SHA-256 de DNO+SeguroSocial)

- **AC2.2.3:**
  - **Given** un registro con `cubre = SI` y `porcentaje_cobertura = P` y `valor_procedimiento = V`
  - **When** se calcula `valor_cubierto`
  - **Then** `valor_cubierto = V × P / 100`; para registros con `cubre = NO`, `valor_cubierto = 0`

- **AC2.2.4:**
  - **Given** cualquier registro clasificado en el Parquet de salida
  - **When** se inspecciona el campo `regla_aplicada`
  - **Then** es `RG-01` para registros con `cubre = SI` y `RG-00` para registros con `cubre = NO`

- **AC2.2.5:**
  - **Given** dos ejecuciones del job con el mismo archivo de entrada
  - **When** se comparan los campos de clasificación de los registros de salida
  - **Then** `cubre`, `porcentaje_cobertura`, `regla_aplicada` y `paciente_hash` son idénticos en ambas ejecuciones; solo `run_id` y `timestamp_proceso` difieren

**Dependencias:** FR2, FR4, FR5, FR6, FR7, NFR2

---

### US2.3 — Clasificación correcta según catálogos
**Como** Analista de Resultados, **quiero** que la clasificación de cada orden siga exactamente la tabla de verdad de los dos catálogos (servicios cubiertos y perfiles de cobertura), **para** confiar en que la lógica de negocio está implementada correctamente.

**Prioridad:** Must Have

**Criterios de aceptación:**

- **AC2.3.1:**
  - **Given** un registro con `ServicioSolicitado` presente en `COIL_catalogo_servicios_cubiertos.csv` con `cubre_sistema_publico = SI` y `PerfilCobertura = PRIORITARIO`
  - **When** el job clasifica el registro
  - **Then** el Parquet muestra `cubre = SI` y `porcentaje_cobertura = 100`

- **AC2.3.2:**
  - **Given** un registro con `ServicioSolicitado` ausente del catálogo de servicios cubiertos
  - **When** el job clasifica el registro
  - **Then** `cubre = NO` y `porcentaje_cobertura = 0` independientemente del perfil

- **AC2.3.3:**
  - **Given** los catálogos de perfiles (PRIORITARIO=100, ESTANDAR=50, COPAGO=25)
  - **When** las pruebas unitarias ejecutan la función de clasificación para cada combinación de perfil y servicio cubierto
  - **Then** todas las combinaciones producen el porcentaje correcto y la cobertura de líneas es ≥ 80%

**Dependencias:** FR4, FR5

---

## Grupo 3: Cuarentena y Trazabilidad de Errores

### US3.1 — Registros malformados en cuarentena
**Como** Analista de Resultados, **quiero** que los registros que no pueden parsearse o cuyos perfiles son desconocidos sean escritos en un archivo separado de cuarentena en S3, **para** revisarlos sin que bloqueen el procesamiento del lote principal.

**Prioridad:** Must Have

**Criterios de aceptación:**

- **AC3.1.1:**
  - **Given** un lote con registros válidos y registros con glosas malformadas o perfiles desconocidos
  - **When** el job termina su ejecución
  - **Then** los registros con `ERROR_PARSEO` o `ERROR_PERFIL` están únicamente en `s3://<bucket-output>/quarantine/` y no en el Parquet de resultados principales

- **AC3.1.2:**
  - **Given** cualquier registro en el archivo de cuarentena
  - **When** se inspecciona su contenido
  - **Then** conserva su `id_solicitud` original y el campo `cubre` contiene `ERROR_PARSEO` o `ERROR_PERFIL`

- **AC3.1.3:**
  - **Given** el Parquet de resultados y el archivo de cuarentena de un job completado
  - **When** se suman `records_output + records_quarantined`
  - **Then** el total es igual a `records_input` (ningún registro se pierde silenciosamente)

- **AC3.1.4:**
  - **Given** un lote que contiene al menos un registro malformado
  - **When** el job procesa el lote completo
  - **Then** el job termina con estado `SUCCEEDED`; ningún registro malformado detiene el procesamiento

**Dependencias:** FR3, FR4, NFR1

---

### US3.2 — Trazabilidad de ejecución en CloudWatch
**Como** Operador de Proceso, **quiero** ver en CloudWatch Logs el `run_id`, el recuento de registros procesados, el recuento de errores por tipo y el tiempo de ejecución, **para** verificar que el job terminó correctamente y detectar anomalías sin acceder a los datos en S3.

**Prioridad:** Must Have

**Criterios de aceptación:**

- **AC3.2.1:**
  - **Given** un job que acaba de terminar con estado `SUCCEEDED`
  - **When** se consultan los logs del job en CloudWatch
  - **Then** los logs contienen `run_id`, `records_input`, `records_output`, `records_quarantined_parseo`, `records_quarantined_perfil` y `duration_seconds`

- **AC3.2.2:**
  - **Given** un job completado
  - **When** se accede a CloudWatch Logs dentro de los 5 minutos posteriores a la finalización
  - **Then** los logs del job están disponibles y son legibles

- **AC3.2.3:**
  - **Given** los logs de CloudWatch y el Parquet de salida de la misma ejecución
  - **When** se compara el `run_id` en los logs con el `run_id` en el Parquet
  - **Then** son idénticos

**Dependencias:** NFR1, NFR4, FR7

---

## Grupo 4: Escala y Rendimiento

### US4.1 — Argumento de escala a 12 M de órdenes
**Como** Operador de Proceso, **quiero** que el sistema procese el dataset de 1,2 M de órdenes y que el documento de arquitectura incluya el argumento analítico de escalado a 12 M, **para** demostrar ante el comité que la solución cumple el objetivo de volumen sin necesidad de generar datos sintéticos.

**Prioridad:** Must Have

**Criterios de aceptación:**

- **AC4.1.1:**
  - **Given** el dataset de 1,2 M registros en S3
  - **When** el job termina con estado `SUCCEEDED`
  - **Then** los logs de CloudWatch registran el tiempo de ejecución T en segundos y `records_input = 1200000`

- **AC4.1.2:**
  - **Given** el tiempo T medido en la ejecución con 1,2 M registros y la configuración de DPU utilizada
  - **When** se revisa el documento de arquitectura
  - **Then** el documento incluye la extrapolación T × 10 con la misma configuración de DPU, demostrando que 12 M se procesan en < 86 400 segundos (24 horas)

- **AC4.1.3:**
  - **Given** el documento de arquitectura
  - **When** se revisa la sección de escalado
  - **Then** especifica el número de DPU utilizado en la prueba y el número requerido para el volumen de 12 M

**Dependencias:** FR8, NFR6

---

## Grupo 5: Entregables Académicos

### US5.1 — Documento de diseño técnico evaluable
**Como** Comité Evaluador, **quiero** recibir un documento de arquitectura que incluya diagrama de servicios, justificación de la elección de AWS Glue, descripción de la lógica de clasificación, argumento de escalado y análisis de costo, **para** evaluar el criterio de diseño técnico (25%) según el enunciado.

**Prioridad:** Must Have

**Criterios de aceptación:**

- **AC5.1.1:**
  - **Given** el documento de arquitectura en el repositorio
  - **When** se abre la sección de arquitectura
  - **Then** contiene un diagrama que muestra los servicios AWS y el flujo de datos: S3 entrada → Glue Job → S3 salida / cuarentena

- **AC5.1.2:**
  - **Given** el documento de arquitectura
  - **When** se revisa la sección de justificación de servicios
  - **Then** justifica AWS Glue sobre al menos una alternativa (ej. EMR), con argumentos de costo y simplicidad operativa para el laboratorio

- **AC5.1.3:**
  - **Given** el documento de arquitectura
  - **When** se revisa la sección de lógica de clasificación
  - **Then** describe la búsqueda determinista sobre los dos catálogos CSV (servicios cubiertos y perfiles de cobertura), con los valores posibles de `porcentaje_cobertura`

- **AC5.1.4:**
  - **Given** el documento de arquitectura
  - **When** se revisa la sección de escalado
  - **Then** incluye el argumento analítico de escalado de 1,2 M a 12 M (throughput real × factor DPU)

- **AC5.1.5:**
  - **Given** el documento de arquitectura
  - **When** se revisa la sección de costo
  - **Then** contiene al menos las dimensiones Glue DPU-horas y almacenamiento S3; los valores son cifras reales del Pricing Calculator o de la consola, o están explícitamente marcados como estimaciones pendientes

**Dependencias:** FR10, FR8

---

### US5.2 — Implementación funcional evaluable
**Como** Comité Evaluador, **quiero** recibir el código PySpark del Glue Job, el CloudFormation template, una suite de pruebas con ≥80% de cobertura y evidencia de ejecución en AWS, **para** evaluar el criterio de implementación (25%) según el enunciado.

**Prioridad:** Must Have

**Criterios de aceptación:**

- **AC5.2.1:**
  - **Given** el repositorio Git del proyecto
  - **When** se revisa su estructura
  - **Then** contiene el código PySpark del job, el CloudFormation template, los archivos de prueba y la evidencia de ejecución

- **AC5.2.2:**
  - **Given** el código fuente del proyecto
  - **When** se ejecuta `pytest --cov` sobre el módulo de clasificación
  - **Then** el reporte de cobertura muestra ≥ 80% de cobertura de líneas

- **AC5.2.3:**
  - **Given** la suite de pruebas
  - **When** se revisan los casos de prueba
  - **Then** existen pruebas para: (a) clasificación correcta por perfil y servicio, (b) cuarentena de glosas malformadas (`ERROR_PARSEO` y `ERROR_PERFIL`), y (c) generación del hash irreversible del paciente

- **AC5.2.4:**
  - **Given** los artefactos de evidencia en el repositorio
  - **When** se revisa la carpeta de evidencia
  - **Then** incluye al menos una captura de consola o log de CloudWatch que muestre `records_input`, `records_output` y `records_quarantined` del run sobre el dataset de 1,2 M

- **AC5.2.5:**
  - **Given** el CloudFormation template versionado en Git
  - **When** se ejecuta `aws cloudformation deploy` con el template
  - **Then** el stack se crea sin errores (documentado con captura o log del deploy)

- **AC5.2.6:**
  - **Given** el código fuente PySpark del Glue Job y el CloudFormation template
  - **When** se inspecciona el código con `grep -rn "AKIA\|aws_access_key\|aws_secret\|aws_session_token"` o equivalente
  - **Then** no se encuentran credenciales AWS, ARNs de recursos ni secretos hardcodeados; toda configuración sensible proviene de variables de entorno o del IAM Role asociado al job

**Dependencias:** FR11, FR9, FR1–FR7, NFR5

---

## Resumen de Prioridades

| Historia | Prioridad | Actor Principal | Requisitos cubiertos |
|---|---|---|---|
| US1.1 Despliegue CloudFormation | Must Have | Operador | FR9, NFR5 |
| US1.2 Rollback del stack | Should Have | Operador | FR9 |
| US2.1 Ejecutar clasificación batch | Must Have | Operador | FR1, FR8 |
| US2.2 Resultado con los 14 campos de FR7 | Must Have | Analista | FR2, FR5, FR6, FR7, NFR2 |
| US2.3 Clasificación correcta | Must Have | Analista | FR4, FR5 |
| US3.1 Cuarentena de errores | Must Have | Analista | FR3, NFR1 |
| US3.2 Trazabilidad CloudWatch | Must Have | Operador | NFR1, NFR4 |
| US4.1 Escala a 12 M | Must Have | Operador | FR8, NFR6 |
| US5.1 Diseño técnico evaluable | Must Have | Comité | FR10 |
| US5.2 Implementación evaluable | Must Have | Comité | FR11, NFR5 |

**Conteo:** 10 historias, 9 Must Have, 1 Should Have. Las 10 historias son el scope mínimo entregable para la defensa ante el comité.
