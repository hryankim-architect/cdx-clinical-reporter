# `cdx-clinical-reporter`

![ci](https://github.com/hryankim-architect/cdx-clinical-reporter/actions/workflows/ci.yml/badge.svg) ![english-only](https://github.com/hryankim-architect/cdx-clinical-reporter/actions/workflows/english-only.yml/badge.svg)

> All data is synthetic: no patient records, no real vendor assay formats, no clinical knowledge base, and no proprietary code or parameters. This repo demonstrates the regulated CDx reporting pattern on public conventions; it is not a validated system and not regulatory advice.

**What this shows**: the regulated-reporting axis of clinical bioinformatics,
(1) a **vendor-agnostic CDx integration shim** that normalizes differently-shaped
assay outputs into one canonical finding model; (2) a **clinical report
generator** with per-finding therapy implications and a stable content hash; and
(3) **21 CFR Part 11-style electronic-signature controls**, a hash-chained
signature ledger bound to the report's content hash, with tamper re-verification.

**Reproducibility**: `make run` produces a signed report artifact in under a second, no network and no GPU required. Everything is seeded.

**Substrate**: each run writes to a NDJSON journal where records are hash-linked back to front; MLflow logging is optional, and a deterministic canary is checked daily by the lab monitor.

**Background**: I led FDA/CLIA-validated clinical bioinformatics and CDx programs with multiple assay vendors in industry. This repo rebuilds the method and the engineering from public patterns on synthetic data — a clean-room implementation, not a copy of any specific company's system, vendor format, or knowledge base. See [`docs/what-is-out-of-scope.md`](docs/what-is-out-of-scope.md).

---

## The capability, in one flow

```
 multi-vendor CDx results (synthetic: Roche- / Thermo- / Guardant-shaped schemas)
        │
        ├── vendors.normalize_batch  → canonical Finding model
        │     (field-name, pos/neg-encoding, VAF fraction-vs-percent reconciled)
        │
        ├── report.build_report      → structured, versioned clinical report
        │     per-finding therapy implication + QC status + content SHA-256
        │
        └── compliance.sign / verify → 21 CFR Part 11-style e-records
              hash-chained signature ledger bound to the content hash;
              re-verify detects any post-signature edit (report or chain)
```

## Demo run (synthetic, deterministic)

`make run` ingests a 3-vendor batch (6 findings across EGFR / TP53 / KRAS / BRAF /
ERBB2), normalizes it, builds a report, collects the required **authored +
approved** electronic sign-offs, and verifies the signature chain still binds to
the report content. The artifact contains the report, the signature ledger, the
verification result, and a rendered markdown report. The canary additionally
tampers with a signed report and asserts verification then fails, the core
control demonstrated end to end.

## Quickstart

```bash
make install     # uv sync, or pip install -e ".[dev]"
make run         # -> artifacts/demo.json (signed report)
make test        # pytest
make lint        # ruff
make canary      # deterministic sign -> verify -> tamper-detect check
```

## Layout

```
.
├── README.md
├── LICENSE                      # MIT
├── Makefile                     # install | data | run | test | lint | canary
├── pyproject.toml
├── .github/workflows/           # ci.yml + english-only.yml
├── data/manifest.yaml           # the regulated patterns modeled (no data committed)
├── src/cdxreport/
│   ├── vendors.py               # vendor-agnostic CDx integration shim
│   ├── report.py                # clinical report + content hash
│   ├── compliance.py            # 21 CFR Part 11-style e-signatures + tamper detection
│   ├── pipeline.py              # CLI entry; audit + MLflow shape
│   ├── audit.py / tracking.py / canary.py   # shared substrate
└── docs/
    ├── architecture.md
    ├── what-is-out-of-scope.md
    └── release-notes/v0.1.md
```

## License

MIT. See [`LICENSE`](LICENSE).
