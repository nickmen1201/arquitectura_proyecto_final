# Contratos — parámetros, almacenamiento y esquemas

> Lo que deben respetar por igual el código (`src/job_cobertura.py`) y la plantilla de CloudFormation.

## 1. Organización del bucket

Un bucket creado por la plantilla (nombre generado por CloudFormation, publicado en las salidas del stack como `DataLakeBucket`).

| Prefijo | Contenido | Quién escribe |
|---|---|---|
| `raw/` | Archivos CSV de órdenes (`COIL_dataset_glosas_salud_1_2M.csv`, muestra dañada) | Operador (subida) |
| `catalogs/` | `COIL_catalogo_servicios_cubiertos.csv`, `COIL_catalogo_perfiles_cobertura.csv` | Operador (subida) |
| `scripts/` | `job_cobertura.py` | Operador (subida) |
| `curated/ordenes_clasificadas/fecha=YYYY-MM-DD/` | Parquet con las decisiones (ejecución de 1,2 M y muestra dañada; tabla de Athena) | Glue Job |
| `quarantine/ordenes_cuarentena/` | Parquet con los errores (tabla de Athena) | Glue Job |
| `curated/escala_12m/`, `quarantine/escala_12m/` | Salidas de la prueba de 12 M; carpeta aparte para no borrar la evidencia de 1,2 M. No se registran en Athena: la evidencia es la línea `METRICAS` | Glue Job |
| `athena-results/` | Resultados de consultas | Athena |
| `temp/` | Archivos temporales de Glue | Glue |

## 2. Parámetros del Glue Job

Definidos en `DefaultArguments` de la plantilla; se pueden sobrescribir al ejecutar. El job los lee con `getResolvedOptions`.

| Parámetro | Obligatorio | Valor por defecto en la plantilla | Descripción |
|---|---|---|---|
| `--input_path` | sí | `s3://<bucket>/raw/COIL_dataset_glosas_salud_1_2M.csv` | CSV de órdenes a procesar |
| `--catalog_services_path` | sí | `s3://<bucket>/catalogs/COIL_catalogo_servicios_cubiertos.csv` | Catálogo de servicios |
| `--catalog_profiles_path` | sí | `s3://<bucket>/catalogs/COIL_catalogo_perfiles_cobertura.csv` | Catálogo de perfiles |
| `--output_path` | sí | `s3://<bucket>/curated/ordenes_clasificadas/` | Destino de las decisiones |
| `--quarantine_path` | sí | `s3://<bucket>/quarantine/ordenes_cuarentena/` | Destino de los errores |
| `--factor_replicacion` | sí | `1` | `10` para la prueba de 12 M (junto con `--output_path` y `--quarantine_path` apuntando a `escala_12m/`) |

Configuración del job en la plantilla: `GlueVersion` (parámetro, por defecto `5.1`), `WorkerType` `G.1X`, `NumberOfWorkers` (parámetro), `Timeout` en minutos (parámetro), métricas de job y log continuo activados.

**Orden de despliegue:** crear el stack → subir script, catálogos y CSV a sus prefijos → ejecutar el workflow o el job. Glue no exige que el script exista al crear el job, solo al ejecutarlo.

## 3. Esquema de salida (`curated/`)

Parquet comprimido con Snappy, particionado por `fecha`. Tabla de Athena: `ordenes_clasificadas`.

| # | Columna | Tipo | Nulo | Origen / regla |
|---|---|---|---|---|
| 1 | `id_solicitud` | string | no | CSV |
| 2 | `paciente_hash` | string | no | SHA-256 normalizado (FR6), 64 caracteres hexadecimales |
| 3 | `cubre` | string | no | `SI` / `NO` |
| 4 | `porcentaje_cobertura` | int | no | `100`, `50`, `25` o `0` |
| 5 | `perfil_cobertura` | string | no | glosa |
| 6 | `servicio_solicitado` | string | no | glosa |
| 7 | `entidad_emisora` | string | sí | CSV |
| 8 | `medio_emisor` | string | sí | CSV |
| 9 | `valor_procedimiento` | double | no | CSV |
| 10 | `valor_cubierto` | double | no | `valor_procedimiento × porcentaje / 100`, redondeado a 2 decimales |
| 11 | `regla_aplicada` | string | no | `RG-01` (cubre) / `RG-00` (no cubre) |
| 12 | `run_id` | string | no | UUID generado una vez por ejecución |
| 13 | `timestamp_proceso` | timestamp | no | UTC del momento de clasificación |
| 14 | `fecha` | date (partición) | no | parte fecha de `fecha_solicitud` |

En los archivos Parquet, `fecha` no va como columna sino en la ruta (`fecha=2026-05-04/`), como es estándar en Spark; Athena la expone como columna.

En la ejecución con `factor_replicacion > 1`, cada copia lleva `id_solicitud` con sufijo `-R01`, `-R02`, …, para que sigan siendo únicos. La copia 0 conserva el identificador original.

## 4. Esquema de cuarentena (`quarantine/`)

Parquet sin particionar. Tabla de Athena: `ordenes_cuarentena`. **Sin datos personales**: no incluye la glosa.

| Columna | Tipo | Nulo | Descripción |
|---|---|---|---|
| `id_solicitud` | string | no | CSV (o `SIN_ID` si la fila no trae identificador) |
| `cubre` | string | no | `ERROR_PARSEO` / `ERROR_PERFIL` |
| `detalle` | string | no | Motivo legible, p. ej. `falta campo DNO`, `perfil fuera de catálogo: VIP` |
| `fecha_solicitud` | string | sí | CSV, tal como llegó |
| `run_id` | string | no | UUID de la ejecución |
| `timestamp_proceso` | timestamp | no | UTC |

## 5. Línea de métricas en CloudWatch

Una única línea en el log de salida del job (grupo `/aws-glue/jobs/output`), con el prefijo fijo `METRICAS` seguido de un JSON:

```text
METRICAS {"run_id": "…", "records_input": 1200000, "records_output": 1200000, "records_quarantined_parseo": 0, "records_quarantined_perfil": 0, "duration_seconds": 0.0, "factor_replicacion": 1, "workers": 0, "worker_type": "G.1X"}
```

Invariante: `records_input = records_output + records_quarantined_parseo + records_quarantined_perfil`. Si no se cumple, el job falla.

## 6. Consultas de trazabilidad (Athena)

```sql
-- ¿Por qué se decidió así una orden?
SELECT id_solicitud, cubre, porcentaje_cobertura, regla_aplicada,
       valor_procedimiento, valor_cubierto, run_id, timestamp_proceso
FROM ordenes_clasificadas
WHERE id_solicitud = 'CHV-0000004';

-- Resumen por fecha y decisión
SELECT fecha, cubre, count(*) AS ordenes, sum(valor_cubierto) AS total_cubierto
FROM ordenes_clasificadas
GROUP BY fecha, cubre
ORDER BY fecha, cubre;

-- Errores por motivo
SELECT cubre, detalle, count(*) FROM ordenes_cuarentena GROUP BY cubre, detalle;
```
