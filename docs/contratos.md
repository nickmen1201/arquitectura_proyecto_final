# Contratos — parámetros, almacenamiento y esquemas

> Lo que deben respetar por igual el código ([src/job_cobertura.py](../src/job_cobertura.py)) y la plantilla ([infra/plantilla.yaml](../infra/plantilla.yaml)).

## 1. Organización del bucket

Un bucket creado por la plantilla (nombre generado por CloudFormation; aparece en las salidas del stack como `BucketDatos`).

| Prefijo | Contenido | Quién escribe |
|---|---|---|
| `raw/` | `COIL_dataset_glosas_salud_1_2M.csv` | Operador (subida) |
| `raw/muestras/` | `muestra_esqueleto_1000.csv`, `muestra_danada.csv` (generadas con `scripts/preparar_muestras.py`) | Operador (subida) |
| `catalogs/` | `COIL_catalogo_servicios_cubiertos.csv`, `COIL_catalogo_perfiles_cobertura.csv` | Operador (subida) |
| `scripts/` | `job_cobertura.py` | Operador (subida) |
| `curated/ordenes_clasificadas/ejecucion=<etiqueta>/fecha=AAAA-MM-DD/` | Parquet con las decisiones. Tabla de Athena `ordenes_clasificadas` | Glue Job |
| `quarantine/ordenes_cuarentena/ejecucion=<etiqueta>/` | Parquet con los errores (solo si hubo). Tabla de Athena `ordenes_cuarentena` | Glue Job |
| `athena-results/` | Resultados de consultas (se borran a los 7 días) | Athena |
| `temp/` | Temporales de Glue (se borran a los 7 días) | Glue |

**Etiquetas de ejecución** (`ejecucion`): `esqueleto`, `muestra_danada`, `completo_1_2m`, `escala_12m`, `diaria`. Cada escenario escribe solo en su partición, así ninguna ejecución borra la evidencia de otra; repetir un escenario reemplaza solo su partición. Las mismas cinco etiquetas están en el código (`ETIQUETAS_VALIDAS`) y en la proyección de particiones de las tablas; el job rechaza cualquier otra.

## 2. Parámetros del Glue Job

Definidos en `DefaultArguments` del job. Cada workflow los sobrescribe en su disparador (columna "por escenario"). El job los lee con `getResolvedOptions`.

| Parámetro | Valor por defecto | Por escenario | Descripción |
|---|---|---|---|
| `--input_path` | `s3://<bucket>/raw/COIL_dataset_glosas_salud_1_2M.csv` | esqueleto y muestra dañada usan `raw/muestras/...` | CSV de órdenes |
| `--catalog_services_path` | `s3://<bucket>/catalogs/COIL_catalogo_servicios_cubiertos.csv` | — | Catálogo de servicios |
| `--catalog_profiles_path` | `s3://<bucket>/catalogs/COIL_catalogo_perfiles_cobertura.csv` | — | Catálogo de perfiles |
| `--output_path` | `s3://<bucket>/curated/ordenes_clasificadas/` | — | Destino de las decisiones |
| `--quarantine_path` | `s3://<bucket>/quarantine/ordenes_cuarentena/` | — | Destino de los errores |
| `--secret_id` | ARN del secreto (`!Ref SecretoClave`) | — | **Es el ARN, no la clave** |
| `--factor_replicacion` | `1` | `10` en `escala_12m` | Copias del dataset (1 a 100) |
| `--etiqueta_ejecucion` | `completo_1_2m` | una por workflow | Partición `ejecucion` |

Configuración del job: `GlueVersion` (parámetro `VersionGlue`, por defecto `5.1`; admite `5.0`), `WorkerType` `G.1X`, `NumberOfWorkers` (parámetro `NumeroWorkers`, por defecto 4), `Timeout` (parámetro `TimeoutMinutos`, por defecto 120), `MaxRetries` 0, `MaxConcurrentRuns` 1 (un escenario a la vez), métricas de job activadas. Rol: `arn:<partición>:iam::<cuenta>:role/<NombreRol>`, con `NombreRol` = `LabRole` por defecto; la plantilla no crea roles.

## 2.1 Workflows (orquestación)

Cada workflow de Glue admite un único disparador de inicio, por eso hay uno por escenario. Todos ejecutan el mismo job con argumentos distintos.

| Workflow | Disparador | Argumentos |
|---|---|---|
| `<stack>-1-esqueleto` | bajo demanda | `raw/muestras/muestra_esqueleto_1000.csv`, `esqueleto` |
| `<stack>-2-muestra-danada` | bajo demanda | `raw/muestras/muestra_danada.csv`, `muestra_danada` |
| `<stack>-3-completo-1-2m` | bajo demanda | dataset completo, `completo_1_2m` |
| `<stack>-4-escala-12m` | bajo demanda | dataset completo, `escala_12m`, factor `10` |
| `<stack>-operacion-diaria` | programado `cron(0 5 * * ? *)` (05:00 UTC), **creado desactivado** | dataset completo, `diaria` |

## 2.2 Secreto de seudonimización

| Aspecto | Contrato |
|---|---|
| Recurso | `AWS::SecretsManager::Secret`, sin nombre fijo (lo genera CloudFormation, para evitar choques si el stack se recrea) |
| Contenido | JSON `{"clave": "<64 caracteres alfanuméricos aleatorios>"}`, generado con `GenerateSecretString` (`SecretStringTemplate: '{}'`, `GenerateStringKey: clave`, `PasswordLength: 64`, `ExcludePunctuation: true`). Nadie escribe la clave. |
| Lectura | El job llama a `secretsmanager:GetSecretValue` **una vez**, en el driver, antes de leer datos. Extrae `clave`, verifica que exista y tenga al menos 32 caracteres, y la usa como bytes UTF-8. |
| Fallo | Si el secreto no existe, no hay permiso o falta `clave`: el job termina con error y mensaje claro, **sin procesar nada**. No hay respaldo con SHA-256 sin clave. |
| Registros | La clave nunca se imprime ni aparece en `METRICAS`, excepciones ni salidas. |
| Vida útil | Mientras el stack exista, la clave no cambia y los `paciente_hash` son estables. Borrar el stack programa el borrado del secreto; un stack nuevo genera una clave distinta. |

## 2.3 Orden de despliegue

Crear el stack (eso también genera el secreto) → subir script, catálogos y CSV a sus prefijos → ejecutar los workflows en orden (esqueleto, muestra dañada, 1,2 M, 12 M). Glue no exige que el script exista al crear el job, solo al ejecutarlo.

## 3. Esquema de salida (`curated/`)

Parquet (Snappy). Tabla de Athena: `ordenes_clasificadas`, con *partition projection* (no hace falta crawler ni `MSCK REPAIR`).

| # | Columna | Tipo | Nulo | Origen / regla |
|---|---|---|---|---|
| 1 | `id_solicitud` | string | no | CSV |
| 2 | `paciente_hash` | string | no | HMAC-SHA-256 con la clave del secreto sobre DNO y seguro social normalizados (FR6); 64 caracteres hexadecimales en minúscula |
| 3 | `cubre` | string | no | `SI` / `NO` |
| 4 | `porcentaje_cobertura` | int | no | `100`, `50`, `25` o `0` |
| 5 | `perfil_cobertura` | string | no | glosa, en mayúsculas |
| 6 | `servicio_solicitado` | string | no | glosa |
| 7 | `entidad_emisora` | string | sí | CSV |
| 8 | `medio_emisor` | string | sí | CSV |
| 9 | `valor_procedimiento` | double | no | CSV |
| 10 | `valor_cubierto` | double | no | `valor_procedimiento × porcentaje / 100`, redondeado a 2 decimales |
| 11 | `regla_aplicada` | string | no | `RG-01` (cubre) / `RG-00` (no cubre) |
| 12 | `run_id` | string | no | UUID generado una vez por ejecución |
| 13 | `timestamp_proceso` | timestamp | no | UTC del momento de clasificación |
| 14 | `fecha` | partición | no | fecha (sin hora) de `fecha_solicitud`; en Spark es `date`, en Athena se expone como texto `AAAA-MM-DD` |
| — | `ejecucion` | partición técnica | no | etiqueta del escenario; no es un campo de la decisión |

En los archivos Parquet, `ejecucion` y `fecha` van en la ruta, no como columnas (estándar de Spark); Athena las expone como columnas.

En la ejecución con `factor_replicacion > 1`, cada copia lleva `id_solicitud` con sufijo `-R01` … `-R09`, para que sigan siendo únicos. La copia 0 conserva el identificador original.

## 4. Esquema de cuarentena (`quarantine/`)

Parquet particionado por `ejecucion`. Tabla de Athena: `ordenes_cuarentena`. **Sin datos personales**: no incluye la glosa. Si una ejecución no tiene errores, no escribe nada en cuarentena.

| Columna | Tipo | Nulo | Descripción |
|---|---|---|---|
| `id_solicitud` | string | no | CSV (o `SIN_ID` si la fila no trae identificador) |
| `cubre` | string | no | `ERROR_PARSEO` / `ERROR_PERFIL` |
| `detalle` | string | no | Motivo legible, p. ej. `falta campo DNO`, `perfil fuera de catálogo: VIP` |
| `fecha_solicitud` | string | sí | CSV, tal como llegó |
| `run_id` | string | no | UUID de la ejecución |
| `timestamp_proceso` | timestamp | no | UTC |
| `ejecucion` | partición | no | etiqueta del escenario |

## 5. Línea de métricas en CloudWatch

Una línea al final de cada ejecución exitosa, con el prefijo fijo `METRICAS` y un JSON (claves en orden alfabético). Se escribe en la salida estándar (grupo `/aws-glue/jobs/output`) y también en la de error (`/aws-glue/jobs/error`). Al inicio el job escribe además una línea `INICIO run_id=... ejecucion=... factor=...` y otra `CATALOGOS servicios_cubiertos=20 perfiles=[...]`.

```text
METRICAS {"duration_seconds": 0.0, "ejecucion": "completo_1_2m", "factor_replicacion": 1, "paralelismo": 0, "particiones": 0, "records_cubre_no": 420000, "records_cubre_si": 780000, "records_input": 1200000, "records_output": 1200000, "records_quarantined_parseo": 0, "records_quarantined_perfil": 0, "run_id": "…"}
```

- `duration_seconds`: tiempo de procesamiento medido dentro del job (sin el arranque de Glue). El **tiempo total** se toma de la consola de Glue.
- `paralelismo`: núcleos de ejecución que Spark tuvo disponibles; `particiones`: particiones usadas (2 × paralelismo).
- Invariante: `records_input = records_output + records_quarantined_parseo + records_quarantined_perfil`. Si no se cumple, el job falla **antes de escribir**.

Valores esperados (verificados localmente con `scripts/verificar_local.py`):

| Ejecución | input | output | SI | NO | parseo | perfil |
|---|---|---|---|---|---|---|
| `esqueleto` | 1 000 | 1 000 | 645 | 355 | 0 | 0 |
| `muestra_danada` | 34 | 22 | 12 | 10 | 10 | 2 |
| `completo_1_2m` | 1 200 000 | 1 200 000 | 780 000 | 420 000 | 0 | 0 |
| `escala_12m` | 12 000 000 | 12 000 000 | 7 800 000 | 4 200 000 | 0 | 0 |

## 6. Consultas de trazabilidad (Athena)

Workgroup `<stack>-consultas`, base de datos `coil_cobertura`.

```sql
-- ¿Por qué se decidió así una orden?
SELECT id_solicitud, cubre, porcentaje_cobertura, regla_aplicada,
       valor_procedimiento, valor_cubierto, run_id, timestamp_proceso
FROM ordenes_clasificadas
WHERE ejecucion = 'completo_1_2m' AND id_solicitud = 'CHV-0000004';

-- Exactitud: conteos por decisión (deben coincidir con la tabla de la sección 5)
SELECT ejecucion, cubre, count(*) AS ordenes
FROM ordenes_clasificadas
GROUP BY ejecucion, cubre
ORDER BY ejecucion, cubre;

-- Resumen por fecha y decisión
SELECT fecha, cubre, count(*) AS ordenes, sum(valor_cubierto) AS total_cubierto
FROM ordenes_clasificadas
WHERE ejecucion = 'completo_1_2m'
GROUP BY fecha, cubre
ORDER BY fecha, cubre;

-- Errores de la muestra dañada
SELECT id_solicitud, cubre, detalle FROM ordenes_cuarentena
WHERE ejecucion = 'muestra_danada'
ORDER BY id_solicitud;
```
