# Entities — u1-batch-job

> Upstream: requirements, components, contract-summary

```yaml
# source-of-truth: entity model for u1-batch-job
entities:

  - name: GlosaRecord
    description: >
      A raw input row from COIL_dataset_glosas_salud_1_2M.csv. Represents one
      medical order received by the system. Fields come from two sources: the CSV
      column values (id_solicitud, fecha_solicitud, medio_emisor, valor_procedimiento,
      entidad_emisora) and the unstructured glosa text field parsed by GlosaParser.
    attributes:
      - name: id_solicitud
        type: string
        required: true
        unique: true
        description: Unique identifier of the medical order (CSV column)
      - name: fecha_solicitud
        type: datetime
        required: true
        description: Date and time of receipt (CSV column; source of output `fecha`)
      - name: glosa
        type: string
        required: true
        description: >
          Semi-structured text with format:
          "Paciente: <name>; DNO: <id>; SeguroSocial: <id>; Edad: <age>;
          PerfilCobertura: <profile>; ServicioSolicitado: <service>; Medicacion: <m1>|..."
      - name: medio_emisor
        type: string
        required: false
        description: Submission channel (CSV column; e.g., digital, presencial)
      - name: valor_procedimiento
        type: decimal
        required: true
        description: Monetary value of the medical procedure (CSV column)
      - name: entidad_emisora
        type: string
        required: false
        description: Institution that submitted the order (CSV column)
    entity_constraints:
      - valor_procedimiento must be a non-negative number; absence or non-numeric value triggers ERROR_PARSEO quarantine

  - name: ParsedFields
    description: >
      Value object extracted from the glosa text field by GlosaParser. This is an
      intermediate representation — it is never persisted. PII fields (nombre_paciente,
      seguro_social) are used only within the classification pipeline and are discarded
      before any record is written to output or quarantine.
    attributes:
      - name: nombre_paciente
        type: string
        required: false
        pii: true
        description: Patient name; never written to output (PII)
      - name: dno
        type: string
        required: true
        description: Patient DNO identifier; normalised (strip + uppercase) before hashing; never written to output
      - name: seguro_social
        type: string
        required: true
        pii: true
        description: Social security number; normalised (strip + uppercase) before hashing; never written to output
      - name: edad
        type: integer
        required: false
        description: Patient age; not in output schema
      - name: perfil_cobertura
        type: string
        required: true
        description: Coverage profile code (e.g., PRIORITARIO, ESTANDAR, COPAGO)
      - name: servicio_solicitado
        type: string
        required: true
        description: Requested medical service name, matched against ServiceCatalog
      - name: medicacion
        type: string
        required: false
        description: >
          Pipe-separated medication list. Extraction failure alone does NOT trigger
          quarantine; the record classifies normally if perfil_cobertura and
          servicio_solicitado were extracted successfully.
    entity_constraints:
      - Absence of dno, seguro_social, perfil_cobertura, or servicio_solicitado → ERROR_PARSEO
      - Failure to extract medicacion with other fields present → no quarantine

  - name: ProcessedRecord
    description: >
      Output record for a successfully classified order. Written to the output Parquet
      file partitioned by fecha. Contains exactly the 14 fields defined in FR7.
      No PII fields are present.
    attributes:
      - name: id_solicitud
        type: string
        required: true
        unique: true
        description: Original order identifier (from GlosaRecord)
      - name: paciente_hash
        type: string
        required: true
        min_length: 64
        max_length: 64
        description: "SHA-256(strip+upper(DNO) + '|' + strip+upper(SeguroSocial)), lowercase hex"
      - name: cubre
        type: string
        required: true
        allowed_values: [SI, NO]
        description: Coverage decision
      - name: porcentaje_cobertura
        type: integer
        required: true
        allowed_values: [0, 25, 50, 100]
        description: Coverage percentage; 0 when cubre=NO
      - name: perfil_cobertura
        type: string
        required: true
        description: Coverage profile parsed from glosa
      - name: servicio_solicitado
        type: string
        required: true
        description: Requested service parsed from glosa
      - name: entidad_emisora
        type: string
        required: false
        description: Emitting institution (from CSV column)
      - name: medio_emisor
        type: string
        required: false
        description: Submission channel (from CSV column)
      - name: valor_procedimiento
        type: decimal
        required: true
        description: Procedure monetary value (from CSV column)
      - name: valor_cubierto
        type: decimal
        required: true
        description: "valor_procedimiento × porcentaje_cobertura / 100; 0 when cubre=NO"
      - name: regla_aplicada
        type: string
        required: true
        allowed_values: [RG-01, RG-00]
        description: "RG-01 when cubre=SI; RG-00 when cubre=NO"
      - name: run_id
        type: string
        required: true
        description: UUID generated once at job start; same for all records in a run
      - name: fecha
        type: date
        required: true
        description: "Solicitud date derived from fecha_solicitud (partition key)"
      - name: timestamp_proceso
        type: timestamp
        required: true
        description: UTC timestamp when the record was classified
    entity_constraints:
      - paciente_hash is exactly 64 lowercase hex characters
      - porcentaje_cobertura is 0 when and only when cubre=NO
      - valor_cubierto = valor_procedimiento × porcentaje_cobertura / 100

  - name: QuarantineRecord
    description: >
      Error record for an order that could not be classified. Written to the quarantine
      Parquet file. Contains the original id_solicitud, the error code in the cubre field,
      run_id, and timestamp_proceso. No PII fields.
    attributes:
      - name: id_solicitud
        type: string
        required: true
        description: Original order identifier (preserved for auditability)
      - name: cubre
        type: string
        required: true
        allowed_values: [ERROR_PARSEO, ERROR_PERFIL]
        description: Error code identifying the quarantine reason
      - name: run_id
        type: string
        required: true
        description: UUID of the job run
      - name: timestamp_proceso
        type: timestamp
        required: true
        description: UTC timestamp when the record was quarantined
    entity_constraints:
      - cubre must be exactly ERROR_PARSEO or ERROR_PERFIL

  - name: CoverageService
    description: >
      A catalog entry from COIL_catalogo_servicios_cubiertos.csv, loaded at job startup.
      Only rows with cubre_sistema_publico=SI are loaded (R-02 filter from components review).
    attributes:
      - name: nombre_servicio
        type: string
        required: true
        unique: true
        description: Service name used as the lookup key
      - name: cubre_sistema_publico
        type: string
        required: true
        allowed_values: [SI, NO]
        description: Whether the public health system covers this service; only SI rows are loaded
    entity_constraints:
      - CatalogRepository loads ONLY rows where cubre_sistema_publico=SI

  - name: CoverageProfile
    description: >
      A catalog entry from COIL_catalogo_perfiles_cobertura.csv, loaded at job startup.
    attributes:
      - name: perfil_cobertura
        type: string
        required: true
        unique: true
        description: Profile code used as the lookup key (e.g., PRIORITARIO, ESTANDAR, COPAGO)
      - name: porcentaje_cobertura
        type: integer
        required: true
        allowed_values: [100, 50, 25]
        description: Coverage percentage for this profile

  - name: JobMetrics
    description: >
      Aggregated metrics emitted to stdout at the end of a successful or failed job run.
      CloudWatch captures this line for observability (FR11, NFR4).
    attributes:
      - name: run_id
        type: string
        required: true
      - name: records_input
        type: integer
        required: true
        description: Total rows read from the input CSV
      - name: records_output
        type: integer
        required: true
        description: Rows written to the output Parquet
      - name: records_quarantined_parseo
        type: integer
        required: true
        description: Rows in quarantine with ERROR_PARSEO
      - name: records_quarantined_perfil
        type: integer
        required: true
        description: Rows in quarantine with ERROR_PERFIL
      - name: duration_seconds
        type: float
        required: true
        description: Wall-clock execution time in seconds
    entity_constraints:
      - records_input = records_output + records_quarantined_parseo + records_quarantined_perfil

relationships:
  - from: GlosaRecord
    to: ParsedFields
    cardinality: 1:1
    direction: GlosaRecord -> ParsedFields
    description: GlosaParser extracts ParsedFields from GlosaRecord.glosa
  - from: GlosaRecord
    to: ProcessedRecord
    cardinality: 0..1:1
    direction: GlosaRecord -> ProcessedRecord
    description: A GlosaRecord produces one ProcessedRecord if classification succeeds
  - from: GlosaRecord
    to: QuarantineRecord
    cardinality: 0..1:1
    direction: GlosaRecord -> QuarantineRecord
    description: A GlosaRecord produces one QuarantineRecord if parsing or profile lookup fails
  - from: ParsedFields
    to: CoverageService
    cardinality: N:1
    direction: ParsedFields.servicio_solicitado -> CoverageService.nombre_servicio
    description: CoverageClassifier looks up servicio_solicitado in CoverageService catalog
  - from: ParsedFields
    to: CoverageProfile
    cardinality: N:1
    direction: ParsedFields.perfil_cobertura -> CoverageProfile.perfil_cobertura
    description: CoverageClassifier looks up perfil_cobertura in CoverageProfile catalog (only when service is covered)
```

## Entity Summary

The model has seven entities across three layers:

**Input layer** — `GlosaRecord` is the raw CSV row with six columns. It drives the entire pipeline.

**Processing layer** — `ParsedFields` is the intermediate value object extracted from the glosa text. It is ephemeral and contains PII that must not leave the pipeline. `CoverageService` and `CoverageProfile` are the two in-memory catalog look-up tables loaded once at startup.

**Output layer** — Every GlosaRecord produces exactly one output: either a `ProcessedRecord` (14 fields, no PII) or a `QuarantineRecord` (4 fields, error code). This one-in one-out invariant is the foundation of NFR1.

**Observability** — `JobMetrics` aggregates the run counts and is emitted once at the end of the job. It is not stored as a Parquet record — it goes to stdout for CloudWatch capture.
