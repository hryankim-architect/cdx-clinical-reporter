"""cdxreport: a regulated clinical-reporting + CDx-integration clean-room demonstration.

A clean-room demonstration of the *pattern* behind companion-diagnostic (CDx)
reporting in a regulated environment:

- a **vendor-agnostic integration shim** that normalizes differently-shaped
  assay outputs (modeled on Roche / Thermo Fisher / Guardant-style schemas) into
  one canonical biomarker-finding model;
- a **clinical report generator** that turns canonical findings into a
  structured, versioned report with therapy implications from a knowledge table;
- **21 CFR Part 11-style controls**: a tamper-evident hash-chained audit trail,
  electronic-signature records bound to the report's content hash, and a
  re-verification path that detects any post-signature change.

Everything runs on synthetic data. No patient data, no proprietary vendor
formats, and no real knowledge base are present. See the README honest-scope
preamble and ``docs/what-is-out-of-scope.md``.
"""

__version__ = "0.1.0"
