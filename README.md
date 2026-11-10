# Clasificación batch de órdenes médicas en AWS

Proyecto COIL (Big Data + Metodología de la Investigación). Enunciado: [proyecto_coil_big_data_metodologia.md](proyecto_coil_big_data_metodologia.md).

## Estructura

| Ruta | Contenido |
|---|---|
| [entregables/01-propuesta.docx](entregables/01-propuesta.docx) | Entregable 01: propuesta metodológica (APA 7) |
| [docs/requisitos.md](docs/requisitos.md) | Problema, datos, requisitos, historias, plan de ejecución |
| [docs/arquitectura.md](docs/arquitectura.md) | Entregable 02: diagrama, componentes, decisiones (ADR), escalabilidad, costo |
| [docs/contratos.md](docs/contratos.md) | Organización de S3, parámetros, workflows, secreto, esquemas, métricas, consultas Athena |
| [src/job_cobertura.py](src/job_cobertura.py) | Glue Job (PySpark): lógica en Python puro + punto de entrada de Glue |
| [infra/plantilla.yaml](infra/plantilla.yaml) | CloudFormation: bucket, secreto, job, workflows, tablas del catálogo, workgroup de Athena |
| [tests/](tests/) | Pruebas con pytest (sin Spark ni AWS) |
| [scripts/preparar_muestras.py](scripts/preparar_muestras.py) | Genera la muestra de 1 000 órdenes y la muestra dañada |
| [scripts/verificar_local.py](scripts/verificar_local.py) | Aplica la lógica localmente y muestra los conteos esperados |

## Uso local (PowerShell, desde la raíz)

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install "pytest>=8" "pytest-cov>=5"
.\.venv\Scripts\python -m pytest --cov=src --cov-report=term-missing
.\.venv\Scripts\python scripts\preparar_muestras.py
.\.venv\Scripts\python scripts\verificar_local.py data\COIL_dataset_glosas_salud_1_2M.csv
```

## Datos

Los CSV van en `data/` (no se versionan por tamaño): dataset de 1,2 M de órdenes, dos catálogos y el diccionario de datos. Las muestras generadas quedan en `data/muestras/`. Las pruebas usan copias de los catálogos en `tests/fixtures/`.
