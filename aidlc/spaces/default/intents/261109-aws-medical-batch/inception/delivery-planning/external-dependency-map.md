# External Dependency Map — 261109-aws-medical-batch

> Upstream: requirements, unit-of-work, components

## Resumen

Los dos Bolts tienen dependencias externas diferenciadas: Bolt 1 opera completamente offline (dependencias de desarrollo local), mientras que Bolt 2 requiere un entorno de laboratorio AWS Academy activo.

## Dependencias por Bolt

### Bolt 1 — batch-job (u1-batch-job)

| Dependencia | Tipo | Versión requerida | Propósito | Riesgo | Mitigación |
|---|---|---|---|---|---|
| Python | Runtime local | 3.11+ | Lenguaje principal | Bajo — estándar | Verificar con `python --version` |
| PySpark | Librería Python | ≥ 3.3 (compatible con Glue 4.0) | Procesamiento local de DataFrames | Medio — versión debe coincidir con Glue | Anclar versión en `pyproject.toml`; misma versión que el runtime Glue |
| pytest | Framework de pruebas | ≥ 7.x | Suite de tests unitarios e integración | Bajo | Declarar en `pyproject.toml` |
| pytest-cov | Plugin cobertura | ≥ 4.x | Verificar floor del 80% | Bajo | Declarar en `pyproject.toml` |
| moto | Simulación AWS | ≥ 4.x (S3 + IAM) | Tests de integración S3 | Bajo — soporte S3 estable en moto | Declarar en `pyproject.toml` |
| Black | Formatter | ≥ 23.x | Estilo de código | Bajo | Declarar en `pyproject.toml` |
| Ruff | Linter | ≥ 0.1.x | Calidad de código | Bajo | Declarar en `pyproject.toml` |
| `COIL_catalogo_servicios_cubiertos.csv` | Archivo de datos | Estático (versión del enunciado) | Catálogo de servicios cubiertos para tests | Bajo | Incluido en `data/` del repositorio |
| `COIL_catalogo_perfiles_cobertura.csv` | Archivo de datos | Estático (versión del enunciado) | Catálogo de perfiles para tests | Bajo | Incluido en `data/` del repositorio |

**Nota:** Bolt 1 no requiere conectividad con AWS. Todas las dependencias de runtime se declaran en `pyproject.toml` y se instalan localmente.

---

### Bolt 2 — infrastructure (u2-infrastructure)

| Dependencia | Tipo | Disponibilidad | Propósito | Riesgo | Mitigación |
|---|---|---|---|---|---|
| AWS Academy Lab (sesión activa) | Entorno externo | Sesiones de 4 horas; créditos limitados | Despliegue y ejecución en AWS real | Alto — ventana temporal fija | Planificar el despliegue completo en una sola sesión (ver R2 en risk-and-sequencing-rationale.md) |
| `LabRole` ARN | IAM Role preexistente | Provisto por AWS Academy | Permisos de ejecución del Glue Job | Medio — permisos no verificables sin sesión activa | Verificar con `aws iam simulate-principal-policy` antes de desplegar (ver R5) |
| AWS CLI | Herramienta CLI | Local, instalada | `aws cloudformation deploy`, `aws glue start-job-run` | Bajo | Instalado y configurado en entorno local |
| `COIL_dataset_glosas_salud_1_2M.csv` | Dataset | Provisto por el enunciado (data/) | Ejecución del job Glue en AWS con 1,2 M de órdenes | Bajo — archivo ya disponible | Dataset incluido localmente; subir a S3 de entrada antes del despliegue |
| AWS Glue 4.0 runtime | Servicio AWS | Disponible en AWS Academy | Ejecutar el script PySpark sobre el dataset | Medio — compatibilidad de dependencias (R1) | Validada en Bolt 1 con misma versión de PySpark |
| Amazon S3 | Servicio AWS | Disponible en AWS Academy | Almacenamiento de inputs, outputs, scripts y cuarentena | Bajo | Creado por CloudFormation template |
| AWS CloudWatch Logs | Servicio AWS | Disponible en AWS Academy | Captura de métricas y evidencia de ejecución (FR11) | Bajo | Configurado automáticamente por Glue |

---

## Restricciones del Laboratorio

| Restricción | Impacto | Gestión |
|---|---|---|
| Sesiones de 4 horas | Todo el despliegue de Bolt 2 (upload dataset + `cloudformation deploy` + `glue start-job-run` + captura de evidencia) debe completarse en una sola sesión | Preparar todos los artefactos offline; ejecutar en secuencia sin interrupciones |
| Créditos de laboratorio limitados | No se pueden ejecutar pruebas destructivas repetidas en AWS | Validar completamente en Bolt 1 antes de usar créditos; una sola ejecución de producción en Bolt 2 |
| `LabRole` sin creación de IAM Roles | El template CloudFormation no puede declarar `AWS::IAM::Role` | Parámetro `GlueRoleArn` recibe el ARN del `LabRole` preexistente |
| Sin acceso a consola IAM | No se puede verificar permisos del `LabRole` directamente | Usar `aws iam simulate-principal-policy` si el tiempo lo permite (R5) |

## Dependencias Fuera de Scope

- DynamoDB: fuera de scope (FR2 — resultados viven solo en S3)
- Amazon EMR: descartado (ADR-001 — AWS Glue es serverless y más económico)
- AWS Lambda: no requerido para batch job
- Servicios de streaming (Kinesis, MSK): fuera de scope (procesamiento exclusivamente por lotes)
