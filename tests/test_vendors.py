"""Vendor-agnostic CDx shim invariants."""

from __future__ import annotations

import pytest

from cdxreport import vendors


def test_three_vendors_normalize_to_same_canonical_egfr() -> None:
    roche = vendors.normalize("roche_like",
        [{"GENE": "egfr", "alteration": "L858R", "result": "DETECTED", "allele_freq": 0.34}])[0]
    thermo = vendors.normalize("thermo_like",
        [{"gene_symbol": "EGFR", "hgvs_p": "p.L858R", "call": "POS", "vaf_percent": 34.0}])[0]
    guardant = vendors.normalize("guardant_like",
        [{"Gene": "EGFR", "Variant": "L858R", "Detected": True, "MAF": 0.34}])[0]

    for f in (roche, thermo, guardant):
        assert f.gene == "EGFR"
        assert f.variant == "L858R"
        assert f.detected is True
        assert abs(f.vaf - 0.34) < 1e-9  # percent and fraction both normalized


def test_negative_call_normalizes() -> None:
    f = vendors.normalize("thermo_like",
        [{"gene_symbol": "EGFR", "hgvs_p": "p.T790M", "call": "NEG", "vaf_percent": 0.0}])[0]
    assert f.detected is False


def test_unknown_vendor_raises() -> None:
    with pytest.raises(ValueError):
        vendors.normalize("acme_like", [{}])


def test_normalize_batch_is_sorted_and_merged() -> None:
    batch = {
        "guardant_like": [{"Gene": "TP53", "Variant": "R175H", "Detected": True, "MAF": 0.4}],
        "roche_like": [{"GENE": "EGFR", "alteration": "L858R", "result": "DETECTED", "allele_freq": 0.3}],
    }
    findings = vendors.normalize_batch(batch)
    assert [f.gene for f in findings] == ["EGFR", "TP53"]  # sorted by gene
