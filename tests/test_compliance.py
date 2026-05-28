"""21 CFR Part 11-style signature + tamper-detection invariants."""

from __future__ import annotations

import pytest

from cdxreport import compliance, report, vendors

FIX = "2026-05-28T00:00:00Z"


def _report():
    f = vendors.normalize("roche_like",
        [{"GENE": "EGFR", "alteration": "L858R", "result": "DETECTED", "allele_freq": 0.34}])
    return report.build_report("S1", f, issued_at=FIX)


def test_sign_binds_content_hash_and_chains() -> None:
    rep = _report()
    ledger: list = []
    compliance.sign(rep, signer="a", role="system", action="authored", ledger=ledger, signed_at=FIX)
    compliance.sign(rep, signer="b", role="pathologist", action="approved", ledger=ledger, signed_at=FIX)
    assert len(ledger) == 2
    assert ledger[0]["content_sha256"] == rep["content_sha256"]
    assert ledger[1]["prev_hash"] != "0" * 64  # chained to the first


def test_verify_ok_then_detects_report_tamper() -> None:
    rep = _report()
    ledger: list = []
    compliance.sign(rep, signer="a", role="system", action="authored", ledger=ledger, signed_at=FIX)
    assert compliance.verify_signatures(rep, ledger)["ok"]

    rep["sample_id"] = "S2"  # edit report after signing
    res = compliance.verify_signatures(rep, ledger)
    assert not res["ok"]
    assert "tampered" in res["reason"]


def test_verify_detects_signature_chain_tamper() -> None:
    rep = _report()
    ledger: list = []
    compliance.sign(rep, signer="a", role="system", action="authored", ledger=ledger, signed_at=FIX)
    compliance.sign(rep, signer="b", role="pathologist", action="approved", ledger=ledger, signed_at=FIX)
    ledger[0]["signer"] = "evil"  # mutate a signed record -> breaks the chain
    assert not compliance.verify_signatures(rep, ledger)["ok"]


def test_invalid_action_rejected() -> None:
    rep = _report()
    with pytest.raises(ValueError):
        compliance.sign(rep, signer="a", role="system", action="rubber-stamped", ledger=[])


def test_required_signoffs() -> None:
    rep = _report()
    ledger: list = []
    compliance.sign(rep, signer="a", role="system", action="authored", ledger=ledger, signed_at=FIX)
    assert not compliance.required_signoffs_met(ledger)
    compliance.sign(rep, signer="b", role="pathologist", action="approved", ledger=ledger, signed_at=FIX)
    assert compliance.required_signoffs_met(ledger)
