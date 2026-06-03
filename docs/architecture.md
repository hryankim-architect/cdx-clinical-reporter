# Architecture

One Python process. Three domain modules. Three substrate hooks. The process is
thin by design — the regulatory pattern is the deliverable, not data volume or
service complexity.

## Pipeline sequence

`make run` calls `cdxreport.pipeline.run_pipeline`, which executes three domain
steps in order:

1. `vendors.normalize_batch` — converts a mixed-vendor assay batch into a list
   of canonical `Finding` objects.
2. `report.build_report` — assembles findings into a versioned clinical report
   and computes a SHA-256 over the canonical content.
3. `compliance.sign` (called per required role) then `compliance.verify_signatures`
   — attaches electronic-signature records and confirms the chain is intact.

The final artifact is written to `artifacts/<name>.json` and contains the report,
the signature ledger, and the verification result.

## Domain modules

| Module | Role |
|---|---|
| `vendors.py` | Per-vendor adapters, each a pure function from a raw assay record to a canonical `Finding`. Handles the three things that vary across vendor schemas in practice: field naming conventions, positive/negative encodings, and VAF as fraction vs percent. |
| `report.py` | Builds a structured, versioned report from normalized findings. Looks up per-finding therapy implications in a small synthetic knowledge table, assigns QC status, and computes a stable content SHA-256 that the compliance layer signs. |
| `compliance.py` | Implements the 21 CFR Part 11-style controls. Each signature record stores the content hash at signing time. Verification checks that the hash still matches the report, that every `prev_hash` link in the chain is unbroken, and that every signature's bound hash equals the current content hash. Any post-signature edit to the report or the ledger causes verification to fail. |

## Why the content hash is load-bearing

A signature attached to mutable content proves nothing. Binding each signature
record to the SHA-256 of the report at signing time makes the invariant
deterministic: recompute the hash, walk the chain, compare. No hash collision
means no silent edit. That is the core property this repo demonstrates.

## Substrate channels

The three substrate hooks run alongside the domain pipeline. Each degrades
gracefully when its environment variable is absent.

| Channel | Module | Env var | Behavior when unset |
|---|---|---|---|
| Audit | `audit` | `AUDIT_HOST` | Writes NDJSON locally only; each record's `prev_hash` is the SHA-256 of the preceding entry, so the journal is its own tamper-evident chain. |
| Tracking | `tracking` | `MLFLOW_TRACKING_URI` | Becomes a no-op; the domain pipeline runs identically with or without MLflow. |
| Canary | `canary` | `CDXREPORT_CANARY_FIXTURE` | Falls back to the bundled fixture; the fixture is enough for the daily probe to assert sign → verify-intact → tamper → verify-fails. |

The daily lab probe (`lab_semantic_check.py` in the shared substrate) calls the
canary as its entry point. The canary completes in well under a second — the
~6.19 µs/entry figure from chain-write benchmarks confirms there is no meaningful
overhead even at scale.

## Intentional omissions

No database. No web service. No real PKI or certificate authority — the signature
record is a content-bound chain entry, not an X.509 signature. No real vendor
SDKs. No clinical knowledge base. The goal is a self-contained demonstration of
the pattern and its invariant, runnable on a laptop without network access.
