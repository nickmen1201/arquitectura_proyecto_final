# Arquitectura — Clasificación batch de órdenes médicas en AWS

> Requisitos en [requisitos.md](requisitos.md). Parámetros y esquemas en [contratos.md](contratos.md).

## 1. Vista general

```mermaid
flowchart LR
    subgraph S3["Amazon S3 — bucket del data lake"]
        RAW["raw/<br/>órdenes CSV"]
        CAT["catalogs/<br/>servicios y perfiles"]
        SCR["scripts/<br/>job_cobertura.py"]
        CUR["curated/<br/>Parquet por fecha"]
        QUA["quarantine/<br/>Parquet de errores"]
        ATH["athena-results/"]
    end

    WF["Glue Workflows<br/>1 por escenario (bajo demanda)<br/>+ operación diaria (programado, desactivado)"] --> JOB
    JOB["Glue Job (Spark)<br/>parsear → validar → clasificar<br/>→ hash → escribir"]
    SM["AWS Secrets Manager<br/>clave de seudonimización<br/>(generada por CloudFormation)"] -.->|"se lee 1 vez por ejecución"| JOB
    RAW --> JOB
    CAT --> JOB
    SCR -.-> JOB
    JOB --> CUR
    JOB --> QUA
    JOB --> CW["CloudWatch Logs<br/>línea METRICAS"]
    CUR --> GDC["Glue Data Catalog<br/>tablas ordenes_clasificadas<br/>y ordenes_cuarentena"]
    QUA --> GDC
    GDC --> AT["Athena<br/>consultas de trazabilidad"]
    AT --> ATH
```

Texto equivalente: cada Workflow de Glue lanza el Job con los argumentos de su escenario. El Job lee una vez la clave de seudonimización desde Secrets Manager, las órdenes de `raw/` y los catálogos de `catalogs/`, procesa en paralelo en los workers de Spark y escribe las decisiones en `curated/` (Parquet particionado por escenario y fecha) y los errores en `quarantine/` (particionado por escenario). Al terminar deja sus métricas en CloudWatch. Las dos salidas están registradas como tablas en el Glue Data Catalog y se consultan con Athena.

Toda la infraestructura (bucket, secreto con la clave, job, workflow, disparadores, base de datos y tablas del catálogo, workgroup de Athena) la crea **una sola plantilla de CloudFormation**.

## 2. Flujo del enunciado → componentes

| Paso del enunciado | Dónde ocurre |
|---|---|
| 1. Recepción | Archivo CSV en `raw/` (S3) |
| 2. Extracción | `GlosaParser` |
| 3. Clasificación | `CoverageClassifier` con `CatalogRepository` |
| 4. Cobertura | `CoverageClassifier` (porcentaje y `valor_cubierto`) |
| 5. Decisión trazable | `BatchPipeline` escribe `curated/` / `quarantine/` con `run_id`; Athena la consulta |

## 3. Componentes

Todos viven en un único archivo, `src/job_cobertura.py`, para que el despliegue sea subir un solo script. Los cuatro primeros son **Python puro** (sin Spark ni AWS) y se prueban localmente; el quinto es el punto de entrada de Glue.

| Componente | Responsabilidad | Entrada → salida |
|---|---|---|
| **GlosaParser** | Extraer `DNO`, `SeguroSocial`, `PerfilCobertura`, `ServicioSolicitado` de la glosa con expresiones regulares tolerantes al orden y a espacios. Si falta alguno, o `valor_procedimiento` no es numérico → `ERROR_PARSEO`. | fila CSV → campos parseados o error |
| **CatalogRepository** | Cargar los dos catálogos una vez al inicio: conjunto de servicios con `cubre_sistema_publico = SI` (columna `servicio`) y diccionario perfil → porcentaje. Inmutable durante la ejecución. | CSV → `Catalogos` |
| **CoverageClassifier** | Aplicar la regla FR4: perfil desconocido → `ERROR_PERFIL`; servicio cubierto → `SI`/`RG-01`/porcentaje del perfil; si no → `NO`/`RG-00`/0. Calcular `valor_cubierto`. | campos parseados + catálogos → decisión |
| **PatientPrivacyService** | `HMAC-SHA-256(clave, upper(trim(DNO)) + "\|" + upper(trim(SeguroSocial)))`. Único punto donde se tocan datos personales; nada de PII sale de aquí. Recibe la clave como argumento (no la busca), lo que permite probarlo con una clave de prueba. Incluye la función que extrae la clave del JSON del secreto y valida que no esté vacía. | DNO, seguro social, clave → `paciente_hash` |
| **BatchPipeline** | Punto de entrada de Glue: leer parámetros, leer la clave desde Secrets Manager (una sola llamada; si falla, el job termina con error), leer CSV, replicar si `factor_replicacion > 1`, distribuir los catálogos a los workers (*broadcast*), aplicar los cuatro componentes por partición (`mapPartitions`), separar resultados y errores, escribir Parquet, emitir la línea `METRICAS`. | S3 → S3 + CloudWatch |

## 4. Decisiones de arquitectura

### ADR-000 — Procesamiento por lotes (Opción 1), no flujo continuo

- **Contexto:** el enunciado fija una ventana de 24 h para 12 M de órdenes y no exige respuesta inmediata por orden; plantea dos rutas: por lotes, o ingesta continua e híbrida.
- **Decisión:** una única capa de procesamiento por lotes.
- **Consecuencias:** un solo código y un solo sistema que operar; el costo se concentra en la ventana de ejecución. En contra: una orden no tiene decisión hasta que corre el lote del día.
- **Alternativas descartadas:**
  - *Arquitectura Lambda* (capa por lotes + capa de velocidad; Marz y Warren, 2015): responde a necesidades de baja latencia que el caso no tiene y obliga a mantener la lógica en dos sistemas.
  - *Arquitectura Kappa* (un único sistema de flujo continuo; Kreps, 2014): evita la duplicación, pero exige operar un sistema de streaming permanente para una carga que llega y se procesa por días.

### ADR-001 — AWS Glue (Spark serverless) como motor de procesamiento

- **Contexto:** 12 M de órdenes en < 24 h, laboratorio con sesiones de 4 h y créditos limitados; el curso evalúa procesamiento distribuido.
- **Decisión:** AWS Glue 5.1 (Spark 3.5.6, Python 3.11; versión predeterminada para trabajos nuevos), workers G.1X, número de workers como parámetro.
- **Consecuencias:** sin clúster que administrar ni apagar; se paga por segundo de ejecución (DPU-hora); integración directa con S3, Data Catalog y CloudWatch. En contra: hay un tiempo de arranque en cada ejecución y menos control sobre la configuración del entorno.
- **Alternativas descartadas:**
  - *Amazon EMR:* misma lógica Spark, pero hay que crear, dimensionar y apagar el clúster; más riesgo operativo en sesiones de 4 h. Sería el camino si la carga fuera continua y mucho mayor.
  - *AWS Lambda:* límite de 15 min por invocación; habría que trocear el archivo y coordinar miles de invocaciones a mano, que es reinventar un motor distribuido.
  - *Athena SQL (CTAS):* para este volumen sería probablemente lo más barato y simple: una consulta con `regexp_extract`, `sha256` y un `JOIN` con los catálogos. Se descarta como motor porque la lógica queda en SQL difícil de probar unitariamente, el manejo de cuarentena es más rígido y no demuestra procesamiento distribuido programable, que es el objetivo del curso. **Sí se usa Athena para consultar los resultados** (ADR-002).

### ADR-002 — S3 como data lake por zonas + Data Catalog + Athena para consultar

- **Contexto:** la Opción 1 exige "estrategia robusta de almacenamiento"; la trazabilidad debe poder verificarse orden por orden.
- **Decisión:** un bucket con zonas por prefijo (`raw/`, `catalogs/`, `scripts/`, `curated/`, `quarantine/`, `athena-results/`). Salidas en Parquet (columnar, comprimido con Snappy), `curated/` particionado por `ejecucion` (escenario) y `fecha`, y `quarantine/` por `ejecucion`, para que ningún escenario borre la evidencia de otro. Tablas definidas en la plantilla con *partition projection* (enumeración de escenarios y rango de fechas), sin necesidad de un crawler. Consultas con Athena.
- **Consecuencias:** un solo destino barato y durable; Parquet reduce lo que Athena escanea; consultar una decisión es una línea de SQL. Las tablas existen desde que se crea el stack.
- **Alternativas descartadas:** *DynamoDB* (escritura registro a registro de 12 M es más lenta y cara, y el uso es analítico, no transaccional); *CSV como salida* (más pesado y más caro de consultar); *Glue Crawler* (costo y un paso más, innecesario si el esquema es fijo y conocido); *varios buckets* (más recursos que administrar sin beneficio de seguridad real en un laboratorio con un único rol).

### ADR-003 — HMAC-SHA-256 con clave en Secrets Manager como identificador seudonimizado del paciente

- **Contexto:** según la AEPD y el EDPS (2019), un *hash* es seudonimización, no anonimización: con identificadores de formato conocido y poca entropía (como `DNO-` + 8 dígitos) un SHA-256 simple se revierte por fuerza bruta.
- **Decisión:** `HMAC-SHA-256(clave, upper(trim(DNO)) + "|" + upper(trim(SeguroSocial)))` (RFC 2104). La clave la genera CloudFormation al crear el stack (`AWS::SecretsManager::Secret` con `GenerateSecretString`, 64 caracteres alfanuméricos), así que nadie la escribe ni la conoce. El job la lee **una vez** por ejecución en el driver y la distribuye a los workers junto con los catálogos; nunca se registra en logs. El separador evita colisiones entre límites de campo; la normalización evita que espacios o mayúsculas cambien el hash.
- **Consecuencias:** sin la clave, el identificador no se puede recalcular a partir de los datos del paciente; se conserva la correlación entre órdenes del mismo paciente. Costo pequeño: un secreto al mes más una llamada por ejecución. El esquema de salida no cambia (sigue siendo un hexadecimal de 64 caracteres).
- **Riesgos y límites:** sigue siendo seudonimización: quien acceda a la clave puede recalcular identificadores. En el laboratorio, el `LabRole` único no permite restringir la lectura del secreto solo al job (en producción, sí). Si el stack se borra, el secreto se borra con él: un stack nuevo genera otra clave y los `paciente_hash` nuevos no coinciden con los anteriores. Si el job no puede leer el secreto, falla de inmediato; no hay respaldo con un hash sin clave, porque mezclaría identificadores incompatibles.
- **Alternativas descartadas:** *SHA-256 sin clave* (reidentificable por fuerza bruta); *clave como parámetro del job* (quedaría visible en la consola de Glue y en la plantilla); *cifrado simétrico* (es reversible); *tokenización con tabla de mapeo* (la tabla contendría PII); *no guardar identificador* (se pierde la correlación).

### ADR-004 — Clasificación determinista por catálogo, no aprendizaje automático

- **Decisión:** búsqueda exacta en los dos catálogos.
- **Consecuencias:** 100 % trazable (cada decisión indica su regla), reproducible y totalmente probable. El enunciado entrega los catálogos como fuente de verdad, así que el espacio de decisión es cerrado. Además, en decisiones públicas de elegibilidad la explicabilidad es una exigencia: el Reglamento (UE) 2024/1689 clasifica como de alto riesgo los sistemas de IA que usan las autoridades públicas para evaluar el derecho a prestaciones de asistencia sanitaria (anexo III, punto 5, letra a).
- **Alternativa descartada:** *ML/NLP*: en la literatura sobre reclamaciones médicas se usa para detectar fraude, es decir, patrones no explícitos (Herland et al., 2018); aquí las reglas son explícitas, y un modelo sería sobredimensionado y menos explicable para un espacio cerrado de 20 servicios × 3 perfiles.

### ADR-005 — CloudFormation como infraestructura como código

- **Decisión:** plantilla YAML ([infra/plantilla.yaml](../infra/plantilla.yaml)) con parámetro `NombreRol` (por defecto `LabRole`); el ARN se arma con la cuenta y la partición del propio stack, sin escribir ningún ARN. Sin recursos `AWS::IAM::Role`. Validada con `cfn-lint`.
- **Consecuencias:** reproducible y legible por el comité; se puede crear desde la consola sin instalar nada.
- **Alternativas descartadas:** *CDK* (agrega Node.js y genera CloudFormation de todos modos); *Terraform* (requiere estado externo y no está en el laboratorio).

### ADR-006 — Lógica en Python puro aplicada con `mapPartitions`

- **Contexto:** se quiere que el código probado sea exactamente el código que corre en Glue, sin instalar Spark localmente.
- **Decisión:** los cuatro componentes de negocio son funciones de Python puro; Spark las aplica partición por partición, con los catálogos distribuidos por *broadcast*.
- **Consecuencias:** las pruebas cubren la misma lógica que procesa los 12 M; no hay dos implementaciones. En contra: Python por fila es más lento que las funciones nativas de Spark (`regexp_extract`, `sha2`, `join`). Para 12 M de órdenes se espera que alcance holgadamente; **se confirma con la ejecución real de 12 M** (FR8). Si no alcanzara, la alternativa es reescribir el job con funciones nativas de Spark.

### ADR-007 — Perfil desconocido va a cuarentena

- **Decisión:** un perfil fuera de catálogo es un error de datos (`ERROR_PERFIL`) y se valida antes de mirar el servicio; no se aplica un porcentaje por defecto.
- **Consecuencias:** ningún registro recibe una decisión equivocada en silencio; un catálogo incompleto se detecta en la cuarentena.
- **Alternativa descartada:** *asumir 0 %*, que ocultaría el error y negaría cobertura a alguien con un perfil legítimo no registrado.

### ADR-008 — Orquestación con Glue Workflows

- **Contexto:** la Opción 1 exige orquestación; en operación real el lote llega cada día.
- **Decisión:** un Glue Workflow por escenario de prueba, cada uno con su disparador bajo demanda y sus argumentos (Glue admite un único disparador de inicio por workflow), y un workflow de operación diaria con disparador programado (05:00 UTC), creado desactivado para no consumir créditos.
- **Consecuencias:** historial de ejecuciones por workflow; extensible a más pasos (por ejemplo, validar el archivo antes de procesarlo).
- **Alternativas descartadas:** *Step Functions* (más flexible pero más piezas para un flujo de un solo paso); *EventBridge + Lambda* (más código propio); *ejecutar el job a mano* (no es orquestación).

## 5. Escalabilidad

- Spark reparte las filas entre los workers; el procesamiento por fila no depende de las demás filas (salvo la lectura de los catálogos, que se distribuyen a todos). El costo crece de forma aproximadamente lineal con el volumen, y el tiempo baja al agregar workers.
- 12 M en 24 h equivale a unas 139 órdenes por segundo de rendimiento mínimo requerido.
- **Medición (11-11-2026), 4 workers G.1X (paralelismo de Spark 12, 24 particiones):** tiempo de procesamiento = `duration_seconds` de la línea `METRICAS` (desde que arranca el script hasta antes de escribir la métrica); tiempo total = fin − inicio en la consola de Glue (añade el aprovisionamiento de workers). El tiempo total es la medida conservadora para H1. Evidencia: `ss/metricas.txt` y la captura de **Runs**.

| Ejecución | Registros | Procesamiento (s) | Tiempo total en consola (s) | Órdenes/s (procesamiento) | Órdenes/s (tiempo total) |
|---|---|---|---|---|---|
| Esqueleto | 1 000 | 63,0 | 145 | — | — |
| Muestra dañada | 34 | 88,1 | 143 | — | — |
| 1,2 M | 1 200 000 | 80,3 | 153 | 14 944 | 7 843 |
| 12 M | 12 000 000 | 225,5 | 274 | 53 215 | 43 796 |

- **H1 se cumple con amplio margen:** 12 M tardaron 274 s en total, el 0,32 % de la ventana de 86 400 s; el rendimiento sobre el tiempo total (43 796 órdenes/s) es unas 315 veces el mínimo requerido (139 órdenes/s).
- **Los costos fijos dominan en volúmenes pequeños.** Cada ejecución paga dos costos fijos: el aprovisionamiento de Glue (total − procesamiento: entre 49 y 82 s) y el arranque del script (iniciar Spark, leer clave y catálogos, planificar y escribir): 1 000 órdenes ya tardan 63 s de procesamiento. Por eso 1,2 M tardan casi lo mismo que la muestra de 1 000.
- **Rendimiento marginal:** pasar de 1,2 M a 12 M añadió 145,2 s de procesamiento para 10,8 M órdenes más, unas 74 000 órdenes/s con 4 workers. Diez veces más datos costaron 2,8 veces más tiempo de procesamiento: el crecimiento es sublineal en este rango, porque los costos fijos se reparten entre más órdenes.
- **Holgura para crecer:** aun suponiendo crecimiento lineal desde aquí, la ventana de 24 h admite volúmenes muy superiores a 12 M con 4 workers; la restricción práctica es el costo por DPU-hora, no el tiempo.

## 6. Costo

Mismo modelo que la propuesta (entregable 01): `C = C_Glue + C_S3 + C_Athena + C_CloudWatch + C_Secrets`, con `C_Glue = workers × DPU por worker (1 en G.1X) × horas facturadas × precio DPU-hora`. Las cifras salen de los precios oficiales de AWS para us-east-1 (región del laboratorio) y del consumo medido. **No se inventan.**

Precios unitarios (us-east-1; páginas de precios consultadas el 10-11-2026 y lista oficial de precios de AWS, *Price List API*, publicada el 09-11-2026 para S3 y el 04-11-2026 para CloudWatch, consultada el 11-11-2026):

| Componente | Unidad | Precio (USD) | Fuente |
|---|---|---|---|
| Glue, trabajo de Spark | DPU-hora, cobro por segundo | 0,44 | [AWS Glue pricing](https://aws.amazon.com/glue/pricing/) |
| Athena | TB escaneado | 5,00 | [Amazon Athena pricing](https://aws.amazon.com/athena/pricing/) |
| Glue Data Catalog | objetos y accesos | gratis hasta 1 millón de cada uno | [AWS Glue pricing](https://aws.amazon.com/glue/pricing/) |
| Secrets Manager | secreto al mes; 10 000 llamadas | 0,40; 0,05 | [AWS Secrets Manager pricing](https://aws.amazon.com/secrets-manager/pricing/) |
| S3 Standard, almacenamiento | GB-mes (primeros 50 TB) | 0,023 | [AWS Price List API, AmazonS3](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonS3/current/us-east-1/index.json) |
| S3, solicitudes | 1 000 PUT/COPY/POST/LIST; 1 000 GET | 0,005; 0,0004 | [AWS Price List API, AmazonS3](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonS3/current/us-east-1/index.json) |
| CloudWatch Logs (clase estándar) | GB ingerido; GB-mes almacenado | 0,50; 0,03 | [AWS Price List API, AmazonCloudWatch](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonCloudWatch/current/us-east-1/index.json) |

Consumo medido el 11-11-2026 (CloudShell: `aws s3 ls --summarize` y la métrica `IncomingBytes` de CloudWatch por minuto):

| Medida | 1,2 M | 12 M |
|---|---|---|
| Tiempo total facturable (s) | 153 | 274 |
| Resultados en S3 (Parquet, 72 archivos) | 0,104 GiB | 1,021 GiB |
| Entrada CSV | 0,336 GiB | 3,36 GiB (en el laboratorio se replica en memoria; en producción sería un archivo real) |
| Registros ingeridos en CloudWatch | 0,74 MB | 0,78 MB |

Parquet ocupa el 30 % del CSV equivalente (1,02 frente a 3,36 GiB para 12 M).

Costo (USD, us-east-1):

| Concepto | 1,2 M | 12 M | Mes (30 ejecuciones de 12 M) |
|---|---|---|---|
| DPU-hora (workers × horas facturadas) | 0,170 (4 × 153 s) | 0,304 (4 × 274 s) | 9,13 |
| Costo Glue (× 0,44 USD) | 0,075 | 0,134 | 4,02 |
| S3, almacenamiento de entrada y resultados durante un mes | 0,010 | 0,101 | 3,02 |
| S3, solicitudes (estimado) | 0,003 | 0,003 | 0,09 |
| Athena (cota: una consulta que lee toda la partición) | 0,001 | 0,005 | 0,15 |
| CloudWatch Logs | 0,0003 | 0,0004 | 0,01 |
| Secrets Manager (0,40 al mes; por ejecución, prorrateado entre 30) | 0,013 | 0,013 | 0,40 |
| Costo S3 + Athena + CloudWatch + Secrets Manager | 0,027 | 0,122 | 3,67 |
| **Costo total** | **0,10** | **0,26** | **7,69** |
| **Costo por millón de órdenes** | 0,085 | 0,021 | 0,021 |

Supuestos y lecturas:

- **Glue** se calcula con el tiempo total de la consola, que incluye el aprovisionamiento; Glue factura solo el tiempo de ejecución, así que es una cota superior. Es el 52 % del costo mensual.
- **S3 almacenamiento** supone que cada día se conservan la entrada y los resultados durante 30 días (131 GiB en régimen). Es el segundo componente (39 %). Una regla de ciclo de vida que borre o archive el CSV una vez procesado lo reduce a 0,70 USD al mes (solo resultados, 31 GiB).
- **S3 solicitudes** es una estimación (se midieron 72 archivos de salida; se suponen unas 500 escrituras y hasta 1 000 lecturas por ejecución); las métricas de solicitudes de S3 no vienen activadas.
- **Athena** cobra por datos escaneados; la cota supone una consulta diaria que lee toda la partición. Con Parquet, una consulta como la de exactitud lee solo la columna `cubre`, así que el costo real es menor.
- **Costo por orden:** 12 M cuestan unos 0,26 USD, unos 2 centavos de dólar por millón de órdenes. El costo por orden de 1,2 M es cuatro veces mayor porque los costos fijos (arranque y secreto) se reparten entre menos órdenes.

Más workers reducen el tiempo pero no necesariamente el costo (depende de workers × tiempo); las dos ejecuciones medidas permiten elegir la configuración más barata que cumple la ventana de 24 h.

## 7. Seguridad y privacidad

- Sin datos personales en salidas, cuarentena ni logs (FR6, NFR2).
- Seudonimización con HMAC y clave aleatoria en Secrets Manager, generada por la plantilla; la clave no está en el código, la plantilla ni los logs (ADR-003).
- Bucket con cifrado SSE-S3 y bloqueo de acceso público.
- Sin credenciales en el código; el job usa el `LabRole`.
- Limitación del laboratorio: un único rol con permisos amplios. En producción se separarían roles por servicio con mínimo privilegio.

## 8. Ajustes respecto al diseño inicial

El primer diseño se hizo con el marco AI-DLC. Al consolidarlo se corrigieron estos puntos:

| # | Antes | Ahora | Motivo |
|---|---|---|---|
| 1 | Glue 4.0 con Python 3.11 | Glue 5.1 (Python 3.11, Spark 3.5.6) | Glue 4.0 usa Python 3.10; la combinación anterior no existe. La 5.1 es la versión predeterminada vigente (la 6.0 usa Python 3.13 y Spark 4.1). |
| 2 | Columna `nombre_servicio` del catálogo | Columna `servicio` | Es el nombre real en el CSV. |
| 3 | Subir el script antes de crear el stack | Crear el stack → subir archivos → ejecutar | El bucket lo crea el propio stack. |
| 4 | Particionar por `fecha_solicitud` (fecha y hora) | Particionar por `fecha` (solo fecha) | Por fecha y hora habría una partición casi por registro. |
| 5 | 12 M "argumentados" (tiempo de 1,2 M × 10) | Ejecución real de 12 M replicando el dataset | Extrapolar ignora el arranque fijo y el paralelismo; medir es defendible. |
| 6 | Sin orquestación | Glue Workflow con disparadores (ADR-008) | La Opción 1 la exige explícitamente. |
| 7 | Resultados solo en Parquet, sin consulta | Data Catalog + Athena (ADR-002) | Permite demostrar la trazabilidad orden por orden. |
| 8 | Perfil desconocido solo se validaba si el servicio estaba cubierto | Se valida siempre, antes del servicio (ADR-007) | Coherencia con el criterio de aceptación de FR4. |
| 9 | Pruebas con DynamoDB simulado | Eliminado | DynamoDB está fuera de alcance. |
| 10 | Hash sin separador en ADR-003 | Con separador y normalización | Unificado con FR6. |
| 11 | Athena no figuraba como alternativa | Añadida en ADR-001 | Es la alternativa más barata; el comité puede preguntarla. |
| 12 | Cuarentena sin forma de demostrarse | Muestra con glosas dañadas | El dataset real no tiene errores. |
| 13 | SHA-256 sin clave | HMAC-SHA-256 con clave en Secrets Manager (ADR-003) | Con identificadores de formato fijo, el hash simple se revierte por fuerza bruta (AEPD y EDPS, 2019). |
