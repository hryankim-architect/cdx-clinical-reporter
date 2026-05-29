"""Vendor-agnostic CDx integration shim.

Companion-diagnostic results arrive in different shapes from different assay
vendors. This module models three *synthetic* vendor schemas (loosely inspired
by the field conventions of Roche, Thermo Fisher, and Guardant assays — no real
vendor format or data is used) and normalizes all of them into one canonical
``Finding`` model so the downstream report generator sees a single shape.

The point is the integration *pattern*: a registry of per-vendor adapters, each
a pure function from a raw record to canonical findings, with explicit handling
of the things that differ in practice — field names, positive/negative encodings,
and VAF expressed as a fraction vs a percentage.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Finding:
    """Canonical biomarker finding (vendor-independent)."""

    gene: str
    variant: str
    detected: bool
    vaf: float | None  # allele fraction in [0, 1], or None if not reported
    vendor: str
    assay: str

    def as_dict(self) -> dict:
        return asdict(self)


def _to_fraction(value: float) -> float:
    """Normalize a VAF that may be a fraction (0.34) or a percent (34.0)."""
    v = float(value)
    return v / 100.0 if v > 1.0 else v


# --- per-vendor adapters: raw record -> Finding -------------------------------

def _adapt_roche(rec: dict) -> Finding:
    return Finding(
        gene=str(rec["GENE"]).upper(),
        variant=str(rec["alteration"]),
        detected=str(rec["result"]).upper() in {"DETECTED", "POSITIVE", "POS"},
        vaf=_to_fraction(rec["allele_freq"]) if rec.get("allele_freq") is not None else None,
        vendor="roche_like",
        assay=str(rec.get("assay", "roche_panel")),
    )


def _adapt_thermo(rec: dict) -> Finding:
    return Finding(
        gene=str(rec["gene_symbol"]).upper(),
        variant=str(rec["hgvs_p"]).replace("p.", ""),
        detected=str(rec["call"]).upper() in {"POS", "POSITIVE", "DETECTED"},
        vaf=_to_fraction(rec["vaf_percent"]) if rec.get("vaf_percent") is not None else None,
        vendor="thermo_like",
        assay=str(rec.get("panel", "thermo_panel")),
    )


def _adapt_guardant(rec: dict) -> Finding:
    return Finding(
        gene=str(rec["Gene"]).upper(),
        variant=str(rec["Variant"]),
        detected=bool(rec["Detected"]),
        vaf=_to_fraction(rec["MAF"]) if rec.get("MAF") is not None else None,
        vendor="guardant_like",
        assay=str(rec.get("Assay", "guardant_ldt")),
    )


ADAPTERS: dict[str, Callable[[dict], Finding]] = {
    "roche_like": _adapt_roche,
    "thermo_like": _adapt_thermo,
    "guardant_like": _adapt_guardant,
}


def normalize(vendor: str, records: list[dict]) -> list[Finding]:
    """Normalize a list of raw vendor records into canonical findings."""
    if vendor not in ADAPTERS:
        raise ValueError(f"unknown vendor {vendor!r}; known: {sorted(ADAPTERS)}")
    adapter = ADAPTERS[vendor]
    return [adapter(rec) for rec in records]


def normalize_batch(batch: dict[str, list[dict]]) -> list[Finding]:
    """Normalize a {vendor: [records]} batch into one merged, sorted finding list.

    Sorting by (gene, variant, vendor) makes the downstream report deterministic
    regardless of vendor input order.
    """
    out: list[Finding] = []
    for vendor, records in batch.items():
        out.extend(normalize(vendor, records))
    out.sort(key=lambda f: (f.gene, f.variant, f.vendor))
    return out
