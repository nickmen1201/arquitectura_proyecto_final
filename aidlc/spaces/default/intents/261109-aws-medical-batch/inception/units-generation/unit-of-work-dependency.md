# Unit Dependency DAG — 261109-aws-medical-batch

> Upstream: components, requirements

## Dependency Graph

```
u2-infrastructure
       │
       ▼
u1-batch-job
```

U1 (`u1-batch-job`) has no dependencies — it is the root of the DAG and can be built first from the existing project state.

U2 (`u2-infrastructure`) depends on U1: the CloudFormation template references the PySpark script produced in U1, and the deployment evidence requires U1's job to have run successfully.

## Edge Table

| From (depends on) | To (dependency) | Integration point |
|---|---|---|
| u2-infrastructure | u1-batch-job | CloudFormation Glue job definition references the `batch_pipeline.py` script path produced in U1 |

## Machine-Readable DAG

```yaml
units:
  - name: u1-batch-job
    kind: service
    depends_on: []
  - name: u2-infrastructure
    kind: packaging
    depends_on: [u1-batch-job]
```

## Parallelism Opportunities

There are only two units and one directed edge, so no parallel development is possible — U2 can only begin once U1 is verified. This is appropriate for a single-developer project.

## Walking Skeleton — First Unit

`u1-batch-job` is the first unit in topological order and is shaped as the walking skeleton: it must demonstrate the full end-to-end flow on ~1 000 orders before U2 is built. The skeleton is considered complete when:
1. The batch job reads a 1 000-row CSV from S3 (or a local path in the test environment).
2. Each row is routed to either the output Parquet (cubre = SI or NO) or the quarantine file (ERROR_PARSEO or ERROR_PERFIL).
3. The output Parquet contains all 14 required fields with valid non-null values for processed records.
4. CloudWatch (or stdout in local mode) emits the metrics line with `run_id`, record counts, and duration.

U2 is built after the skeleton is verified and human-approved.

## Notes on Topology

This DAG describes **what can depend on what**, not a recommended build order. Delivery Planning (the next stage) chooses the economic sequencing through this topology. The linear DAG here leaves no ambiguity: topological order is U1 → U2.
