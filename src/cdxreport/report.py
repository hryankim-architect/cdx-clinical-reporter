"""Clinical report generation from canonical CDx findings.

Turns a list of canonical :class:`~cdxreport.vendors.Finding` objects into a
structured, versioned clinical report: per-finding therapy implications drawn
from a small *synthetic* knowledge table, an overall QC status, and a stable
content hash for the compliance layer to sign.

The knowledge table is illustrative only — a handful of well-known
gene/variant → therapy associations encoded as synthetic rows. It is not a
clinical knowledge base and must not be used for care.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from cdxreport.vendors import Finding

REPORT_SCHEMA_VERSION = "1.0"

# Synthetic biomarker -> therapy-implication knowledge table.
# (gene, variant-prefix) -> (implication, evidence_tier)
KNOWLEDGE: dict[tuple[str, str], tuple[str, str]] = {
    ("EGFR", "L858R"): ("EGFR-TKI sensitivity (illustrative)", "tier-1"),
    ("EGFR", "T790M"): ("EGFR-TKI resistance; later-generation TKI", "tier-1"),
    ("KRAS", "G12C"): ("KRAS-G12C inhibitor candidate (illustrative)", "tier-1"),
    ("BRAF", "V600E"): ("BRAF/MEK inhibitor candidate (illustrative)", "tier-1"),
    ("ERBB2", "amp"): ("HER2-targeted therapy candidate (illustrative)", "tier-2"),
    ("TP53", ""): ("Prognostic association only (illustrative)", "tier-3"),
}


def _lookup(gene: str, variant: str) -> tuple[str, str]:
    # exact (gene, variant-prefix) first, then gene-wildcard
    for (g, vprefix), val in KNOWLEDGE.items():
        if g == gene and vprefix and variant.startswith(vprefix):
            return val
    if (gene, "") in KNOWLEDGE:
        return KNOWLEDGE[(gene, "")]
    return ("No curated therapy implication (illustrative table)", "none")


def _qc_status(findings: list[Finding]) -> dict[str, Any]:
    detected = [f for f in findings if f.detected]
    low_vaf = [f for f in detected if f.vaf is not None and f.vaf < 0.05]
    status = "review" if low_vaf else "pass"
    return {
        "status": status,
        "n_findings": len(findings),
        "n_detected": len(detected),
        "n_low_vaf_flagged": len(low_vaf),
    }


def _content_hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def build_report(
    sample_id: str,
    findings: list[Finding],
    *,
    issued_at: str | None = None,
) -> dict[str, Any]:
    """Build a structured, content-hashed clinical report.

    ``issued_at`` is injectable so tests and the canary can pin a timestamp and
    get a byte-stable report (and therefore a stable content hash).
    """
    issued = issued_at or datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    interpreted = []
    for f in findings:
        implication, tier = _lookup(f.gene, f.variant)
        interpreted.append(
            {
                "gene": f.gene,
                "variant": f.variant,
                "detected": f.detected,
                "vaf": f.vaf,
                "vendor": f.vendor,
                "assay": f.assay,
                "therapy_implication": implication,
                "evidence_tier": tier,
            }
        )

    # content excludes the hash itself; issued_at IS part of the signed content
    content = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "sample_id": sample_id,
        "issued_at": issued,
        "findings": interpreted,
        "qc": _qc_status(findings),
    }
    return {**content, "content_sha256": _content_hash(content)}


def verify_content_hash(report: dict[str, Any]) -> bool:
    """Recompute the content hash and compare to the stored one (tamper check)."""
    stored = report.get("content_sha256")
    content = {k: v for k, v in report.items() if k != "content_sha256"}
    return stored == _content_hash(content)


def render_markdown(report: dict[str, Any]) -> str:
    """Deterministic human-readable rendering (for the demo artifact)."""
    lines = [
        f"# Clinical CDx Report — sample {report['sample_id']}",
        "",
        f"- Schema version: {report['schema_version']}",
        f"- Issued: {report['issued_at']}",
        f"- QC: {report['qc']['status']} "
        f"({report['qc']['n_detected']}/{report['qc']['n_findings']} detected)",
        f"- Content SHA-256: `{report['content_sha256']}`",
        "",
        "| Gene | Variant | Detected | VAF | Implication (illustrative) | Tier |",
        "|---|---|---|---|---|---|",
    ]
    for f in report["findings"]:
        vaf = "-" if f["vaf"] is None else f"{f['vaf']:.2f}"
        det = "yes" if f["detected"] else "no"
        lines.append(
            f"| {f['gene']} | {f['variant']} | {det} | {vaf} | "
            f"{f['therapy_implication']} | {f['evidence_tier']} |"
        )
    return "\n".join(lines)
