# Contract Summary — 261109-aws-medical-batch

> Upstream: unit-of-work, unit-of-work-dependency, components, requirements

## Contracts Table

| # | Provider Unit | Consumer | Mechanism | Owner |
|---|---|---|---|---|
| C-01 | u1-batch-job | u2-infrastructure | Shared schema + deployment artifact reference | u1-batch-job |

There are no REST/HTTP, event-driven, or gRPC boundaries in this system. The single inter-unit boundary is a file/configuration coupling: U2 (the CloudFormation template) references artifacts and configuration parameters that U1 (the PySpark job) produces and consumes.

There are no public or external API boundaries — the system does not expose any endpoint consumed outside the project.

---

## C-01: u1-batch-job → u2-infrastructure

**Integration mechanism:** Deployment artifact reference + shared job parameter contract + shared output schema

**What crosses the boundary:**

1. **PySpark script artifact** — U1 produces `src/batch_pipeline.py`; U2 references it in the CloudFormation Glue job definition via `--ScriptLocation`.
2. **Glue job parameters** — U2 declares the parameters in the CloudFormation template; U1 reads them at runtime via `getResolvedOptions` (AWS Glue SDK) or `sys.argv`.
3. **Output Parquet schema** — U1 writes the ProcessedRecord Parquet; U2 reads and presents a sample as execution evidence. The column names and types are pinned here so both sides agree.

**Failure behaviour:**
- If the script path is wrong or the file is absent, the Glue job fails at startup with `FAILED` status visible in CloudWatch.
- If a required job parameter is missing, `getResolvedOptions` raises `awsglue.utils.GlueArgumentError`; the job fails immediately.
- If the output schema changes without updating U2's evidence template, the evidence will show wrong column names — this is a documentation defect, not a runtime failure.

---

### Spec 1: Glue Job Parameters (U2 → U1)

U2 passes these parameters to U1 via the CloudFormation `DefaultArguments` block of the Glue job resource. U1 reads them with `getResolvedOptions(sys.argv, [...])`.

```yaml
# shared-schema: Glue job parameters contract
parameters:
  - name: input_path
    type: string
    format: "s3://{bucket}/input/{file}.csv"
    required: true
    description: S3 URI of the input CSV containing the medical orders

  - name: catalog_services_path
    type: string
    format: "s3://{bucket}/catalogs/COIL_catalogo_servicios_cubiertos.csv"
    required: true
    description: S3 URI of the covered-services catalog CSV

  - name: catalog_profiles_path
    type: string
    format: "s3://{bucket}/catalogs/COIL_catalogo_perfiles_cobertura.csv"
    required: true
    description: S3 URI of the coverage-profiles catalog CSV

  - name: output_path
    type: string
    format: "s3://{bucket}/output/"
    required: true
    description: S3 URI prefix for the output Parquet (partitioned by fecha)

  - name: quarantine_path
    type: string
    format: "s3://{bucket}/quarantine/"
    required: true
    description: S3 URI prefix for quarantine records

constraints:
  - All paths must use the s3:// scheme; no s3a:// or local paths in production.
  - The input bucket and output bucket may be the same S3 bucket.
  - Credentials are NOT passed as parameters; the Glue job uses the IAM role
    specified via GlueRoleArn in the CloudFormation stack parameter.
```

---

### Spec 2: Script Deployment Contract (U1 → U2)

U1 must produce the PySpark entry-point script at a fixed relative path in the repository. U2 uploads it to S3 and references it in the CloudFormation template.

```yaml
# shared-schema: script deployment contract
script:
  repository_path: "src/batch_pipeline.py"
  s3_key_convention: "scripts/batch_pipeline.py"
  s3_uri: "s3://{GlueScriptsBucket}/scripts/batch_pipeline.py"
  cloudformation_reference: "ScriptLocation: !Sub 's3://${GlueScriptsBucket}/scripts/batch_pipeline.py'"

upload_command: >
  aws s3 cp src/batch_pipeline.py
  s3://{GlueScriptsBucket}/scripts/batch_pipeline.py

constraints:
  - The script must import only packages available in the Glue runtime
    (Python 3.11, PySpark 3.3+) or listed in extra-py-files.
  - U2 must upload the script to S3 BEFORE running aws cloudformation deploy.
  - The S3 bucket name is provided by the CloudFormation stack output
    GlueScriptsBucket; U1's CI/CD step reads it from the stack outputs.
```

---

### Spec 3: Output Parquet Schema (U1 → U2 evidence)

U1 writes the ProcessedRecord Parquet partitioned by `fecha`. U2 reads a sample row for the execution evidence deliverable (FR11 / US5.2). The 14-field schema is pinned here (FR7).

```yaml
# shared-schema: ProcessedRecord Parquet output schema (FR7)
schema:
  format: Parquet
  partition_key: fecha
  columns:
    - name: id_solicitud
      type: string
      nullable: false
    - name: paciente_hash
      type: string
      nullable: false
      description: "SHA-256(strip+upper(dno) + '|' + strip+upper(seguro_social)), 64-char hex; no PII. The '|' separator prevents hash collisions between field-boundary variants."
    - name: cubre
      type: string
      nullable: false
      values: [SI, NO]
    - name: porcentaje_cobertura
      type: integer
      nullable: false
      values: [0, 25, 50, 100]
    - name: perfil_cobertura
      type: string
      nullable: false
    - name: servicio_solicitado
      type: string
      nullable: false
    - name: entidad_emisora
      type: string
      nullable: true
    - name: medio_emisor
      type: string
      nullable: true
    - name: valor_procedimiento
      type: double
      nullable: false
    - name: valor_cubierto
      type: double
      nullable: false
    - name: regla_aplicada
      type: string
      nullable: false
      values: [RG-01, RG-00]
    - name: run_id
      type: string
      nullable: false
      description: UUID generated once at job start; same value for all records in a run
    - name: fecha
      type: date
      nullable: false
      description: partition key; also the solicitud date from the parsed glosa
    - name: timestamp_proceso
      type: timestamp
      nullable: false
      description: UTC timestamp when the record was processed

quarantine_schema:
  format: Parquet
  columns:
    - name: id_solicitud
      type: string
      nullable: false
    - name: cubre
      type: string
      nullable: false
      values: [ERROR_PARSEO, ERROR_PERFIL]
    - name: run_id
      type: string
      nullable: false
    - name: timestamp_proceso
      type: timestamp
      nullable: false
```

---

## Contract Ownership Rules

1. **U1 owns C-01** — u1-batch-job owns the script artifact, the output schema spec (Spec 3), and the parameter-reading contract (Spec 1 consumer side). Any change to the Parquet schema or required parameters requires a U1 change.
2. **U2 must stay in sync** — u2-infrastructure owns the CloudFormation parameter declarations (Spec 1 provider side) and the script upload step (Spec 2). When U1 adds or renames a parameter, U2 must update the CloudFormation `DefaultArguments` block in the same commit.
3. **Breaking changes** — This is a single-developer project; no formal review process beyond the standard Git commit on `main`. A "breaking change" is any rename or removal of a parameter or output column; additive changes (new optional columns, new optional parameters with defaults) are safe.
4. **Consumer-side tolerance** — U2's evidence template references columns by name; it must be updated if column names change. U2 never parses the Parquet programmatically — it reads a sample with `pandas.read_parquet` or `aws s3 select` for evidence capture only.

---

## Open Questions

| Contract | Question | Blocks |
|---|---|---|
| C-01 Spec 2 | What is the final S3 bucket name for the Glue scripts? The CloudFormation template will export a `GlueScriptsBucket` stack output, but the actual name depends on the lab account. | u2-infrastructure deployment; can use a parameter with a generated default. |
