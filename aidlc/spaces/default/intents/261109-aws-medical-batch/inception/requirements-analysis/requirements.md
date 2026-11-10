# Requirements — 261109-aws-medical-batch

## Sources

- [desc] Proyecto COIL (Big Data + Metodología). Mi parte: diseño técnico e implementación de una solución por lotes (Opción 1) en AWS para clasificar órdenes médicas: cubre o no cubre, y 100 %, 50 % o 25 % según el perfil. Meta: 12 millones de solicitudes en menos de 24 horas, con trazabilidad y costo razonable.
- [scope] classic
- Entrevista de prácticas (2026-11-09): 7 preguntas, respuestas en `practices-discovery/`
- Entrevista de requisitos (2026-11-09): 6 preguntas, respuestas en `requirements-analysis-questions.md`
- `TrabajoFinal.pdf` (document_id: 01a1be47-8488-795e-82cf-e5631d71c18c)
- `data/COIL_diccionario_datos.md` — esquema de datos y regla de clasificación
- `data/COIL_catalogo_perfiles_cobertura.csv` — 3 perfiles de cobertura
- `data/COIL_catalogo_servicios_cubiertos.csv` — 20 servicios cubiertos

---

## Functional Requirements

### FR1 — Ingesta de órdenes médicas desde S3
El sistema lee el archivo de glosas (CSV) desde un bucket S3 de entrada mediante un job AWS Glue (PySpark). El job acepta como parámetro la ruta S3 del archivo de entrada.

**Criterio de aceptación:** El job lee correctamente `COIL_dataset_glosas_salud_1_2M.csv` (1 200 000 registros) sin truncar ni perder registros; el conteo de entrada se registra en el log del job.

---

### FR2 — Parseo de glosas
Cada glosa tiene el formato:
`Paciente: <nombre>; DNO: <id>; SeguroSocial: <id>; Edad: <edad>; PerfilCobertura: <perfil>; ServicioSolicitado: <servicio>; Medicacion: <med1>|...`

El sistema extrae los campos `PerfilCobertura` y `ServicioSolicitado` mediante expresiones regulares. Los demás campos de la glosa se utilizan únicamente para calcular `paciente_hash`.

**Criterio de aceptación:** El parser extrae correctamente `PerfilCobertura` y `ServicioSolicitado` para el 100 % de los registros con formato válido; los registros con formato inválido se derivan a FR3.

---

### FR3 — Manejo de registros en cuarentena
Los registros que no pueden procesarse correctamente se escriben a un archivo de cuarentena separado en S3 (`s3://<bucket-output>/quarantine/`) y el job continúa. Los motivos de cuarentena son:

- `ERROR_PARSEO`: la glosa no puede parsearse (campo faltante o formato incorrecto)
- `ERROR_PERFIL`: el valor de `PerfilCobertura` no existe en el catálogo

Cada registro de cuarentena conserva su `id_solicitud` original y el motivo de error en el campo `cubre`. El campo `Medicacion` de la glosa usa `|` únicamente como separador interno de medicamentos; si el parser falla al extraer `Medicacion` pero extrae correctamente `PerfilCobertura` y `ServicioSolicitado`, el registro **no** va a cuarentena — se clasifica normalmente.

**Criterio de aceptación:** Ningún registro bloqueado detiene el job; todos los registros con `ERROR_PARSEO` o `ERROR_PERFIL` aparecen en el archivo de cuarentena con su `id_solicitud` y el motivo; el conteo de errores por tipo se registra en el log del job.

---

### FR4 — Clasificación de cobertura
La clasificación es una búsqueda determinista en dos catálogos:

1. **Cobertura del servicio:** Buscar `ServicioSolicitado` en `COIL_catalogo_servicios_cubiertos.csv` (campo `nombre_servicio`, filtrando `cubre_sistema_publico = SI`). Si no existe → `cubre = NO`, `porcentaje_cobertura = 0`.
2. **Porcentaje por perfil:** Si el servicio cubre, buscar `PerfilCobertura` en `COIL_catalogo_perfiles_cobertura.csv` (campo `perfil_cobertura`) y obtener `porcentaje_cobertura` (100, 50 o 25).
3. **Regla aplicada:** Registrar el identificador de la regla (`RG-01` si cubre, `RG-00` si no cubre).

**Criterio de aceptación:** Para cada combinación válida de (perfil, servicio), el resultado de cobertura coincide con la tabla de verdad derivada de los dos catálogos; los servicios no cubiertos devuelven 0 %; los perfiles desconocidos devuelven `ERROR_PERFIL` en cuarentena.

---

### FR5 — Cálculo de valor cubierto
Para los registros que cubren (`cubre = SI`), calcular:
`valor_cubierto = valor_procedimiento × porcentaje_cobertura / 100`

El campo `valor_procedimiento` proviene del registro de entrada.

**Criterio de aceptación:** `valor_cubierto` es numéricamente correcto para todos los registros con `cubre = SI`; para `cubre = NO`, `valor_cubierto = 0`.

---

### FR6 — Generación de hash irreversible del paciente
Generar `paciente_hash` como SHA-256 de la cadena `strip+upper(DNO) + "|" + strip+upper(SeguroSocial)`. El separador `|` evita colisiones entre variantes de límite de campo. El nombre del paciente y el número de seguro social **no** aparecen en el archivo de salida.

**Criterio de aceptación:** El campo `paciente_hash` es un string hexadecimal de 64 caracteres; no hay campos `nombre_paciente` ni `seguro_social` en el output; el mismo paciente produce el mismo hash en ejecuciones distintas del mismo job independientemente de espacios o mayúsculas en el input.

---

### FR7 — Persistencia de resultados en S3 (trazabilidad completa)
El job escribe los resultados clasificados en S3 en formato Parquet, particionados por `fecha_solicitud`. Cada registro de salida contiene los siguientes campos:

| Campo | Descripción |
|---|---|
| `id_solicitud` | Identificador original de la solicitud |
| `paciente_hash` | SHA-256 de DNO+SeguroSocial (sin PII) |
| `cubre` | `SI` / `NO` / `ERROR_PARSEO` / `ERROR_PERFIL` |
| `porcentaje_cobertura` | 100, 50, 25 o 0 |
| `perfil_cobertura` | Valor parseado de la glosa |
| `servicio_solicitado` | Valor parseado de la glosa |
| `entidad_emisora` | Entidad que emitió la orden |
| `medio_emisor` | Canal de emisión (ej. digital, presencial) |
| `valor_procedimiento` | Valor monetario del procedimiento (campo de entrada) |
| `valor_cubierto` | `valor_procedimiento × porcentaje / 100` |
| `regla_aplicada` | `RG-01` (cubre) / `RG-00` (no cubre) |
| `run_id` | Identificador único de la ejecución del job |
| `fecha` | Fecha de la solicitud (campo de entrada) |
| `timestamp_proceso` | Timestamp UTC de cuando se clasificó el registro |

**Criterio de aceptación:** Todos los registros procesados correctamente aparecen en el Parquet de salida con los 14 campos; el recuento de registros de salida + registros de cuarentena = recuento de registros de entrada.

---

### FR8 — Escala y rendimiento
El job debe procesar **12 millones de órdenes en menos de 24 horas**. Para la defensa, se demuestra con los 1 200 000 registros del dataset disponible y se argumenta analíticamente el escalado (ej. throughput lineal con nodos adicionales de Glue DPU).

**Criterio de aceptación:** La ejecución con 1,2 M registros completa en un tiempo T documentado; el documento de arquitectura incluye el argumento analítico de escalado a 12 M (con el número de DPU requerido y el tiempo estimado resultante).

---

### FR9 — Orquestación y despliegue con CloudFormation
Toda la infraestructura (bucket S3 de entrada, bucket S3 de salida, bucket S3 de scripts, AWS Glue Job) se despliega mediante un CloudFormation template. El template **no crea ningún IAM Role**: recibe el ARN del rol preexistente del laboratorio (`LabRole`) como parámetro de CloudFormation y lo asigna al Glue Job. No se realizan cambios manuales en la consola AWS.

**Criterio de aceptación:** Un `aws cloudformation deploy --parameter-overrides GlueRoleArn=<LabRole-ARN>` desde cero crea todos los recursos sin intervención manual; el job puede ejecutarse inmediatamente después del despliegue.

---

### FR10 — Entregable: diseño técnico
El entregable de diseño técnico (25 % de la nota según el enunciado) incluye:
- Diagrama de arquitectura de la solución (servicios AWS y flujo de datos)
- Justificación de la elección de servicios (AWS Glue vs. alternativas)
- Descripción de la lógica de clasificación (regla determinista sobre los catálogos)
- Argumento analítico de escalado de 1,2 M a 12 M de órdenes (throughput real medido × factor de escala o DPU adicionales)
- Análisis de costo para el volumen de 12 M de órdenes, usando cifras del AWS Pricing Calculator o de la consola del laboratorio; si las cifras no están disponibles, los campos se dejan en blanco con la fuente indicada

**Criterio de aceptación:** El documento de arquitectura contiene las cinco secciones anteriores; los costos son cifras reales o estimaciones del Pricing Calculator explícitamente marcadas como tales.

---

### FR11 — Entregable: implementación
El entregable de implementación (25 % de la nota según el enunciado) incluye:
- Código PySpark funcional del job AWS Glue (clasificación + cuarentena + trazabilidad)
- CloudFormation template que despliega toda la infraestructura (S3 buckets, Glue Job; sin crear IAM Roles)
- Suite de pruebas: unitarias (lógica de clasificación con PySpark local), integración (S3 y DynamoDB simulados con moto), smoke test E2E
- Evidencia de ejecución exitosa en AWS: capturas de pantalla de la consola, logs de CloudWatch y/o métricas del job con el dataset de 1,2 M registros

**Criterio de aceptación:** El job ejecuta sin errores en AWS con el dataset de 1,2 M registros; los logs de CloudWatch muestran recuento de entrada, salida y cuarentena; los tests tienen ≥ 80 % de cobertura de líneas; el CloudFormation template despliega sin errores con `aws cloudformation deploy`.

---

## Non-Functional Requirements

### NFR1 — Trazabilidad completa por orden
Cada solicitud de entrada tiene exactamente un registro en el output (resultado) o en la cuarentena (error), con `run_id` y `timestamp_proceso` que permiten rastrear la decisión de clasificación.

### NFR2 — Privacidad de datos (PII)
Ningún dato de identificación personal (nombre del paciente, número de seguro social) aparece en los archivos de salida. Solo se usa `paciente_hash` (SHA-256 irreversible).

### NFR3 — Idempotencia
Ejecutar el job dos veces con el mismo input produce el mismo output (mismo Parquet de resultados, mismo Parquet de cuarentena); solo `run_id` y `timestamp_proceso` difieren entre ejecuciones.

### NFR4 — Observabilidad mínima
El job registra en CloudWatch Logs: recuento de registros procesados, recuento de errores de parseo, tiempo de ejecución y `run_id`. Estos logs son la evidencia de ejecución para la defensa.

### NFR5 — Seguridad de credenciales
Ninguna credencial, clave de API ni ARN se hardcodea en el código fuente ni en los templates CloudFormation. Se usan IAM Roles del laboratorio y variables de entorno / parámetros de CloudFormation.

### NFR6 — Costo razonable para laboratorio universitario
La solución usa AWS Glue (serverless) como procesador principal para minimizar costos de laboratorio; se evita mantener clústeres EMR corriendo cuando no hay trabajo.

---

## Out of Scope

- Procesamiento en tiempo real o streaming (la solución es exclusivamente por lotes — Opción 1)
- Persistencia en DynamoDB u otro servicio de consulta online; los resultados viven únicamente en S3
- Generación de datos sintéticos hasta 12 M de registros en el laboratorio; la demo usa el dataset de 1,2 M con argumento analítico
- Interfaz de usuario, dashboard o API de consulta sobre los resultados
- Creación de IAM Roles desde CloudFormation; se usa el `LabRole` preexistente del laboratorio
- Opciones 2 y 3 del enunciado (procesamiento en tiempo real y arquitectura mixta)

---

## Assumptions & Open Questions

- [assumption] Los catálogos `COIL_catalogo_servicios_cubiertos.csv` y `COIL_catalogo_perfiles_cobertura.csv` son estáticos para toda la ejecución del job; no cambian durante el procesamiento.
- [assumption] El campo `valor_procedimiento` siempre es un número válido en el dataset; si falta, el registro se envía a cuarentena.
- [assumption] El carácter `|` en el campo `Medicacion` de la glosa es únicamente un separador interno de medicamentos y no puede confundirse con el separador de campos de la glosa (`;`). Si el parser falla al extraer `Medicacion` pero extrae correctamente `PerfilCobertura` y `ServicioSolicitado`, el registro se clasifica normalmente (no va a cuarentena).
- [assumption] El entorno de laboratorio AWS Academy **no permite crear IAM Roles desde CloudFormation**. El template recibe el ARN del `LabRole` preexistente del laboratorio como parámetro y lo asigna al Glue Job; no se declara ningún recurso `AWS::IAM::Role` en el template.
- [assumption] El `LabRole` del laboratorio AWS Academy tiene los permisos necesarios para que un Glue Job lea y escriba en S3 (acceso a los buckets del proyecto).
- [assumption] El entorno de laboratorio AWS Academy tiene permisos suficientes para crear Glue Jobs y buckets S3 desde CloudFormation.
- [assumption] Las cifras de costo se obtendrán del AWS Pricing Calculator o de la consola del laboratorio durante la ejecución de prueba; no se inventan valores.
