"""Report generation + content-hash invariants."""

from __future__ import annotations

from cdxreport import report, vendors

FIX = "2026-05-28T00:00:00Z"


def _findings():
    return vendors.normalize("roche_like", [
        {"GENE": "EGFR", "alteration": "L858R", "result": "DETECTED", "allele_freq": 0.34},
        {"GENE": "TP53", "alteration": "R175H", "result": "DETECTED", "allele_freq": 0.41},
    ])


def test_report_is_deterministic_given_timestamp() -> None:
    a = report.build_report("S1", _findings(), issued_at=FIX)
    b = report.build_report("S1", _findings(), issued_at=FIX)
    assert a == b
    assert a["content_sha256"] == b["content_sha256"]


def test_content_hash_verifies_and_detects_tamper() -> None:
    rep = report.build_report("S1", _findings(), issued_at=FIX)
    assert report.verify_content_hash(rep)
    rep["sample_id"] = "S2"  # tamper
    assert not report.verify_content_hash(rep)


def test_therapy_implication_lookup() -> None:
    rep = report.build_report("S1", _findings(), issued_at=FIX)
    egfr = next(f for f in rep["findings"] if f["gene"] == "EGFR")
    assert egfr["evidence_tier"] == "tier-1"
    assert "EGFR-TKI" in egfr["therapy_implication"]


def test_markdown_renders_all_findings() -> None:
    rep = report.build_report("S1", _findings(), issued_at=FIX)
    md = report.render_markdown(rep)
    assert "EGFR" in md and "TP53" in md
    assert rep["content_sha256"] in md
