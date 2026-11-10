# Requisitos — Clasificación batch de órdenes médicas en AWS

> Fuente: [proyecto_coil_big_data_metodologia.md](../proyecto_coil_big_data_metodologia.md) y `data/COIL_diccionario_datos.md`.
> Alcance: **Opción 1 del enunciado (procesamiento por lotes)**.

## 1. Problema

Un sistema público de salud recibe órdenes médicas y debe decidir, para cada una, si el Estado **cubre o no cubre** el servicio y qué **porcentaje** reconoce (100 %, 50 % o 25 % según el perfil del usuario), dejando una **decisión trazable**. Meta: **12 millones de órdenes en menos de 24 horas**, con costo razonable.

Variables críticas de evaluación: tiempo total, costo de operación, escalabilidad y trazabilidad.

## 2. Datos disponibles (perfilados sobre el archivo real)

| Archivo | Contenido |
|---|---|
| `COIL_dataset_glosas_salud_1_2M.csv` | 1 200 000 órdenes, columnas `id_solicitud, fecha_solicitud, glosa, medio_emisor, valor_procedimiento, entidad_emisora` |
| `COIL_catalogo_servicios_cubiertos.csv` | 20 servicios, columnas `codigo_servicio, servicio, categoria, medicaciones_referencia, valor_min_referencia, valor_max_referencia, cubre_sistema_publico` |
| `COIL_catalogo_perfiles_cobertura.csv` | 3 perfiles: `PRIORITARIO=100`, `ESTANDAR=50`, `COPAGO=25` |

Formato de la glosa:
`Paciente: <nombre>; DNO: <id>; SeguroSocial: <id>; Edad: <edad>; PerfilCobertura: <perfil>; ServicioSolicitado: <servicio>; Medicacion: <m1>|<m2>|...`

Perfil del dataset real (sirve como **resultado esperado** para validar la ejecución):

| Métrica | Valor |
|---|---|
| Registros | 1 200 000 (sin `id_solicitud` duplicados) |
| Glosas con formato inválido | 0 |
| Perfiles fuera de catálogo | 0 |
| `valor_procedimiento` no numérico | 0 |
| Órdenes con servicio cubierto | 780 000 |
| Órdenes con servicio no cubierto | 420 000 (12 servicios "premium"/estéticos) |
| Perfiles | ESTANDAR 480 255 · PRIORITARIO 419 653 · COPAGO 300 092 |
| Fechas | 2026-05-04 (402 000) · 2026-05-05 (396 000) · 2026-05-06 (402 000) |
| Medios emisores | Portal Ciudadano, Hospital Público, App Móvil Salud, Clínica Aliada, Farmacia Aliada, Call Center, Ventanilla Física |

Como el dataset real no trae errores, la cuarentena se demuestra con un **archivo de muestra con glosas dañadas a propósito** (ver FR3).

## 3. Requisitos funcionales

| ID | Requisito | Criterio de aceptación |
|---|---|---|
| **FR1** Ingesta | Un job de AWS Glue lee el CSV de órdenes desde la zona `raw/` de S3; la ruta llega como parámetro del job. | Con el dataset real se registra `records_input = 1200000`. |
| **FR2** Parseo | Se extraen de la glosa `DNO`, `SeguroSocial`, `PerfilCobertura` y `ServicioSolicitado`. `Paciente`, `Edad` y `Medicacion` no se usan para decidir. | El 100 % de las glosas válidas se parsean; las inválidas van a FR3. |
| **FR3** Cuarentena | Los registros que no se pueden clasificar se escriben en la zona `quarantine/` y **no detienen el job**. Motivos: `ERROR_PARSEO` (falta DNO, SeguroSocial, PerfilCobertura o ServicioSolicitado, o `valor_procedimiento` no es numérico) y `ERROR_PERFIL` (perfil fuera de catálogo). | El job termina en `SUCCEEDED` con la muestra dañada; cada error aparece en cuarentena con su `id_solicitud` y su motivo. |
| **FR4** Clasificación | Regla determinista: (1) si el perfil no está en el catálogo → `ERROR_PERFIL`; (2) si `ServicioSolicitado` está en la columna `servicio` del catálogo con `cubre_sistema_publico = SI` → `cubre = SI`, regla `RG-01`, porcentaje según el perfil; (3) si no → `cubre = NO`, regla `RG-00`, porcentaje 0. | Coincide con la tabla de verdad de los catálogos para todas las combinaciones; con el dataset real: 780 000 `SI` y 420 000 `NO`. |
| **FR5** Valor cubierto | `valor_cubierto = valor_procedimiento × porcentaje / 100` (0 si no cubre). | Correcto para el 100 % de los registros. |
| **FR6** Privacidad | `paciente_hash = SHA-256( upper(trim(DNO)) + "\|" + upper(trim(SeguroSocial)) )` en hexadecimal. Nombre, DNO y seguro social **nunca** se escriben en la salida. | Hash de 64 caracteres, estable entre ejecuciones; no existen columnas con PII. |
| **FR7** Salida trazable | Resultado en Parquet en la zona `curated/`, particionado por `fecha`, con los 14 campos de [contratos.md](contratos.md#3-esquema-de-salida-curated). | `records_output + records_quarantined = records_input`. |
| **FR8** Escala | 12 M de órdenes en menos de 24 h. Se **demuestra con una ejecución real de 12 M** (dataset replicado 10 veces dentro del job con el parámetro `factor_replicacion`), además de la ejecución de 1,2 M. Cada ejecución escribe en su propia carpeta de salida para no borrar la evidencia de la otra. | Para ambas ejecuciones se registran dos tiempos: el de procesamiento (línea `METRICAS`) y el **tiempo total** que muestra la consola de Glue (incluye el arranque). El tiempo total de la de 12 M < 86 400 s. |
| **FR9** Infraestructura como código | Toda la infraestructura se crea con una plantilla de CloudFormation que recibe el ARN del `LabRole` como parámetro y **no crea roles IAM**. | Crear el stack desde la consola con la plantilla deja el job listo para ejecutar, sin pasos manuales adicionales salvo subir archivos a S3. |
| **FR10** Orquestación | Un Glue Workflow encadena la ejecución: disparador bajo demanda para la demo y disparador diario programado (desactivado por defecto) que representa la operación real del lote. | Ejecutar el workflow lanza el job y queda registrado en el historial del workflow. |
| **FR11** Consulta de trazabilidad | Las salidas `curated/` y `quarantine/` quedan registradas como tablas en el Glue Data Catalog y se consultan con Athena. | Una consulta por `id_solicitud` devuelve la decisión, la regla aplicada, el `run_id` y el `timestamp_proceso`. |

## 4. Requisitos no funcionales

| ID | Requisito |
|---|---|
| **NFR1** Trazabilidad | Cada orden de entrada termina exactamente en `curated/` o en `quarantine/`, con `run_id` y `timestamp_proceso`. |
| **NFR2** Privacidad | Ningún dato personal (nombre, DNO, seguro social) en salidas, cuarentena ni logs. |
| **NFR3** Idempotencia | Dos ejecuciones con la misma entrada producen las mismas decisiones; solo cambian `run_id` y `timestamp_proceso`. Repetir una ejecución sobre la misma carpeta de salida la sobrescribe. |
| **NFR4** Observabilidad | Al terminar, el job escribe en CloudWatch una línea `METRICAS {json}` con `run_id`, `records_input`, `records_output`, `records_quarantined_parseo`, `records_quarantined_perfil`, `duration_seconds`, `workers`, `worker_type`. |
| **NFR5** Seguridad | Sin credenciales, ARNs ni nombres de bucket en el código o la plantilla; todo llega por parámetros. Se usa el `LabRole` del laboratorio. Bucket con cifrado SSE-S3 y acceso público bloqueado. |
| **NFR6** Costo | Servicios serverless con pago por uso (Glue, S3, Athena); nada queda encendido entre ejecuciones. Las cifras de costo se toman de la AWS Pricing Calculator o de la consola del laboratorio; **nunca se inventan**. |

## 5. Historias de usuario

Actores: **Operador** (despliega y ejecuta), **Analista** (revisa resultados), **Comité** (evalúa).

| ID | Historia | Criterios clave (Given/When/Then resumidos) |
|---|---|---|
| **US1.1** | Como Operador, quiero crear toda la infraestructura con la plantilla, para no configurar nada a mano. | El stack llega a `CREATE_COMPLETE`; no hay recursos `AWS::IAM::Role`; el job queda listo para ejecutar. |
| **US2.1** | Como Operador, quiero ejecutar la clasificación por lotes indicando la ruta del archivo. | El job termina en `SUCCEEDED` con `records_input = 1200000` y deja Parquet legible en `curated/`. |
| **US2.2** | Como Analista, quiero que cada orden tenga los 14 campos de salida, para verificar la decisión sin ver datos personales. | Esquema exacto de 14 columnas; `paciente_hash` de 64 caracteres; `valor_cubierto` y `regla_aplicada` correctos; decisiones idénticas entre dos ejecuciones. |
| **US2.3** | Como Analista, quiero que la clasificación siga exactamente los catálogos. | Las 3 × 20 combinaciones cubiertas dan el porcentaje del perfil; los servicios no cubiertos dan 0. |
| **US3.1** | Como Analista, quiero que los registros inválidos vayan a cuarentena sin detener el lote. | Con la muestra dañada: los errores solo están en `quarantine/`, con su motivo; la suma cuadra con la entrada; el job termina en `SUCCEEDED`. |
| **US3.2** | Como Operador, quiero ver las métricas de la ejecución en CloudWatch. | La línea `METRICAS` aparece con todos sus campos y su `run_id` coincide con el del Parquet. |
| **US3.3** | Como Analista, quiero consultar con Athena por qué se decidió una orden. | `SELECT ... WHERE id_solicitud = 'CHV-0000004'` devuelve la decisión, la regla, el `run_id` y la hora de proceso. |
| **US4.1** | Como Operador, quiero demostrar que 12 M de órdenes se procesan en menos de 24 h. | Ejecución real con `factor_replicacion = 10`: `records_input = 12000000` y tiempo total en la consola de Glue < 86 400 s; el documento compara 1,2 M vs 12 M y los workers usados. |
| **US5.1** | Como Comité, quiero un documento de diseño técnico con diagrama, justificación, lógica, escalado y costo. | Diagrama de servicios y flujo; Glue justificado frente a EMR, Lambda y Athena; tabla de costo con fuente de cada cifra. |
| **US5.2** | Como Comité, quiero código, pruebas y evidencia de ejecución. | Pruebas de clasificación, cuarentena y hash con ≥ 80 % de cobertura de la lógica; capturas de Glue, CloudWatch, S3 y Athena; ninguna credencial en el repositorio. |

## 6. Fuera de alcance

- Procesamiento en tiempo real o streaming (Opción 2 del enunciado).
- Bases de datos operacionales (DynamoDB, RDS); los resultados viven en S3 y se consultan con Athena.
- Interfaz de usuario o API.
- Creación de roles IAM (el laboratorio no lo permite).

## 7. Supuestos

- Los catálogos no cambian durante una ejecución.
- El `LabRole` tiene permisos sobre Glue, S3, Athena y CloudWatch Logs. **Verificar en el laboratorio.**
- El laboratorio ofrece **Glue 5.1** (Python 3.11, Spark 3.5.6). **Verificar**; si no, se usa 5.0 (mismo Python) cambiando un parámetro de la plantilla.
- Las sesiones del laboratorio duran 4 horas y los créditos son limitados: cada ejecución se planifica para hacerse una sola vez.

## 8. Prácticas de trabajo

- Python 3.11 en Glue (el código evita sintaxis exclusiva de 3.12 para que las pruebas corran con el Python 3.12 local) · `pytest` + `pytest-cov`.
- Pruebas: la lógica de negocio es Python puro y se prueba localmente sin Spark ni AWS (≥ 80 % de cobertura de líneas sobre esos módulos). La parte que usa Spark se valida con la ejecución real en Glue, que es la evidencia.
- Infraestructura: se crea subiendo la plantilla de CloudFormation desde la consola del laboratorio. Lo único manual es subir archivos a S3 y lanzar las ejecuciones.
