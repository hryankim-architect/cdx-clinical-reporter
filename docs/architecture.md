# Architecture

A deliberately small architecture: one Python process, three method modules, and
three substrate hooks. The regulated controls are the point, not the data volume.

## Control flow

```
                make run / scripts/run_lab.sh
                          │
                          ▼
              cdxreport.pipeline.run_pipeline
                          │
        ┌─────────────────┼──────────────────────────────┐
        ▼                 ▼                               ▼
  audit.emit         tracking.run                       body
 (NDJSON +         (MLflow active run,        vendors.normalize_batch
  optional POST)    no-op if unset)            → report.build_report
                                               → compliance.sign ×N
                                               → compliance.verify_signatures
                          │
                          ▼
              artifacts/<name>.json  (report + signatures + verification)
```

## Method modules

| Module | Responsibility |
|---|---|
| `vendors.py` | Vendor-agnostic CDx integration shim. A registry of per-vendor adapters, each a pure function from a raw assay record to a canonical `Finding`. Reconciles the things that differ in practice: field names, positive/negative encodings, and VAF expressed as a fraction vs a percentage. |
| `report.py` | Clinical report generation: per-finding therapy implications from a small synthetic knowledge table, a QC status, and a canonical content SHA-256 the compliance layer signs. |
| `compliance.py` | 21 CFR Part 11-style controls: electronic-signature records bound to the report content hash, a hash-chained signature ledger, and re-verification that detects post-signature edits to either the report or the chain. |

## Why bind signatures to a content hash

An electronic signature is only meaningful if it is bound to *exactly* what was
signed. Each signature record stores the SHA-256 of the report content at signing
time. Verification recomputes the report's content hash and checks (1) it still
matches the report's stored hash, (2) the signature chain's `prev_hash` links are
intact, and (3) every signature's bound hash equals the current content hash. Any
edit to the report after signing, or any attempt to drop, reorder, or alter a
signature, fails verification. That is the electronic-records / electronic-
signatures pattern reduced to its core, deterministic invariant.

## Substrate integration

| Channel | Module | Env var | Behaviour when unset |
|---|---|---|---|
| Audit | `audit` | `AUDIT_HOST` | local NDJSON only (source of truth) |
| MLflow | `tracking` | `MLFLOW_TRACKING_URI` | no-op |
| Canary | `canary` | `CDXREPORT_CANARY_FIXTURE` | uses the bundled fixture |

The canary asserts the central control (sign → verify intact → tamper → verify
fails) in well under a second, which is what the daily lab probe checks.

## What this architecture intentionally avoids

No database, no web service, no real PKI / certificate authority (the signature
is a content-bound hash-chain record, not a cryptographic X.509 signature), no
real vendor SDKs, and no clinical knowledge base. The point is the *pattern* and
its invariant, runnable on a laptop.
