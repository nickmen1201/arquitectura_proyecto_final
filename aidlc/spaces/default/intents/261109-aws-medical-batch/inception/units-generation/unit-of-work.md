# Units of Work — 261109-aws-medical-batch

> Upstream: components, requirements

## Unit Summary

| Unit ID | Directory | Kind | Complexity | Description |
|---|---|---|---|---|
| U1 | `u1-batch-job` | service | L | All five Python components (GlosaParser, CatalogRepository, CoverageClassifier, PatientPrivacyService, BatchPipeline) plus the full test suite |
| U2 | `u2-infrastructure` | packaging | S | CloudFormation template, S3 configuration, Glue job definition, and AWS deployment evidence |

---

## U1 — u1-batch-job

**Kind:** service
**Complexity:** L
**Deployment model:** standalone — runs as a single AWS Glue PySpark job

### Responsibilities

- Implement GlosaParser: regex extraction of all classification fields from raw glosa text; raises ParseError (ERROR_PARSEO) on missing required fields; Medicacion failure alone does not quarantine.
- Implement CatalogRepository: load ServiceCatalog (filtered to `cubre_sistema_publico = SI`) and ProfileCatalog from S3 CSVs at job startup; expose `is_service_covered` and `get_profile_percentage`.
- Implement CoverageClassifier: deterministic lookup (RG-01/RG-00); raises ProfileError (ERROR_PERFIL) for unknown profiles; calculates `valor_cubierto`.
- Implement PatientPrivacyService: normalise DNO and SeguroSocial (strip + uppercase), then compute SHA-256 hash as `paciente_hash`; no PII propagated.
- Implement BatchPipeline: PySpark entry point; reads input CSV from S3; generates `run_id`; routes records to ProcessedRecord (Parquet, 14 fields) or QuarantineRecord (ERROR_PARSEO / ERROR_PERFIL); logs metrics to stdout for CloudWatch.
- Deliver pytest suite: unit tests (pure component logic with local PySpark DataFrames), integration tests (S3 accesses with moto), and a smoke E2E test on ~1 000 orders; ≥ 80% line coverage floor.

### Walking Skeleton

This unit IS the walking skeleton. It must be the first unit built and must demonstrate the full end-to-end flow — read from S3 → parse → classify → hash → write Parquet + quarantine — on a dataset of approximately 1 000 orders, before U2 deploys it to AWS at 12 M scale. The skeleton verification command will read a local or S3-hosted 1 000-row CSV and verify that records appear in the output Parquet (or quarantine) with the correct schema.

### Implementation Notes and Constraints

- Python 3.11+, PySpark (AWS Glue runtime compatible).
- Black formatter (`line-length = 88`), Ruff linter; configured in `pyproject.toml`.
- No hardcoded credentials, ARNs, or bucket names — all via environment variables or Glue job parameters.
- PySpark session is created by the Glue runtime in production; tests use a local `SparkSession`.
- moto used only for S3 and DynamoDB integration tests; Glue-specific Spark features (DynamicFrame) may need thin adapters to run locally.
- Covers: FR1, FR2, FR3, FR4, FR5, FR6, FR7, FR8, NFR1, NFR2, NFR3, NFR4, NFR5.

---

## U2 — u2-infrastructure

**Kind:** packaging
**Complexity:** S
**Deployment model:** standalone — CloudFormation stack (`aws cloudformation deploy`)

### Responsibilities

- Deliver the CloudFormation template: S3 input/output/catalog/quarantine bucket, AWS Glue job definition referencing the PySpark script from U1, parameter `GlueRoleArn` for the LabRole ARN (no IAM role created by the template).
- Document and validate that the template deploys with a single `aws cloudformation deploy` command.
- Capture and include AWS execution evidence: CloudWatch log excerpt showing the metrics line (`records_input`, `records_output`, `records_quarantined_parseo`, `records_quarantined_perfil`, `duration_seconds`, `run_id`), and S3 output verification (file count or sample row from Parquet).
- Produce the technical design deliverable (FR10 / US5.1): architecture diagram, service selection justification, classification logic summary, scaling argument for 12 M orders in < 24 h, and cost analysis (AWS Pricing Calculator figures or lab-console estimates).
- Support rollback: document the `aws cloudformation delete-stack` + redeploy procedure (US1.2).
- Covers: FR9, FR10, FR11, NFR5, NFR6.

### Implementation Notes and Constraints

- CloudFormation YAML; no CDK, no Terraform.
- `GlueRoleArn` is a mandatory parameter — no default; deploy command always passes `--parameter-overrides GlueRoleArn=<LabRole-ARN>`.
- No hardcoded ARNs or account IDs inside the template body.
- Cost analysis uses AWS Pricing Calculator data or console-observed lab credits; never invented figures.
