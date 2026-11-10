# Unit of Work Story Map — 261109-aws-medical-batch

> Upstream: components, requirements, stories

Each row maps one upstream User Story to the Unit(s) that implement it.

| Story | Unit ID | Directory | Notes |
|---|---|---|---|
| US1.1 | U2 | u2-infrastructure | CloudFormation one-command deploy |
| US1.2 | U2 | u2-infrastructure | CloudFormation stack rollback and redeploy |
| US2.1 | U1 | u1-batch-job | Trigger batch job; read input CSV from S3 |
| US2.2 | U1 | u1-batch-job | Produce ProcessedRecord with all 14 output fields (FR7 schema) |
| US2.3 | U1 | u1-batch-job | CoverageClassifier lookup (RG-01 / RG-00); valor_cubierto calculation |
| US3.1 | U1 | u1-batch-job | Quarantine routing for ERROR_PARSEO and ERROR_PERFIL |
| US3.2 | U1 | u1-batch-job | BatchPipeline emits CloudWatch metrics line with run_id |
| US4.1 | U1; U2 | u1-batch-job; u2-infrastructure | U1 delivers the measurable execution (actual runtime in seconds); U2 delivers the written analytical scaling argument (FR10) |
| US5.1 | U2 | u2-infrastructure | Technical design deliverable: architecture diagram, justification, logic, scaling, cost |
| US5.2 | U1; U2 | u1-batch-job; u2-infrastructure | **Cross-cutting** — U1 delivers code + tests (≥ 80% coverage); U2 delivers AWS execution evidence (logs, screenshots, S3 output sample). `traceability.json` records U1 as primary target (engine requires a single value); this note is the authoritative cross-unit assignment. |

## Coverage Verification

All 10 upstream User Story IDs are assigned to at least one unit. No unassigned story and no unit without at least one story.

**U1 stories:** US2.1, US2.2, US2.3, US3.1, US3.2, US4.1, US5.2 (code and tests portion)
**U2 stories:** US1.1, US1.2, US5.1, US5.2 (AWS evidence portion)

## Cross-Cutting Concern

**US5.2** spans both units: the implementation deliverable requires the working code and test results from U1 AND the AWS execution evidence (logs, screenshots, S3 output sample) from U2. It is fully satisfied only when both units are complete.
