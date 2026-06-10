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


def test_forgery_boundary_keyless_ledger_can_be_reforged() -> None:
    """HONEST BOUNDARY: the "signature" is a *keyless* hash chain, so anyone who can
    rewrite the ledger can forge a complete, clean-verifying one.

    The two tamper tests above only catch an attacker who edits the report (or one
    record) while leaving the *rest* of the ledger intact. They cannot catch an
    attacker who rebuilds the whole ledger from scratch, because `sign()` needs no
    secret key or identity proof. This test makes that limit explicit and CI-visible
    so the "tamper-evident / 21 CFR Part 11" framing is not over-trusted: tamper-
    evidence holds only if the ledger is stored somewhere the attacker cannot
    rewrite. Real non-repudiation needs PKI + an identity provider — see
    docs/what-is-out-of-scope.md ("Not cryptographic signing").
    """
    # A legitimately signed report (EGFR L858R), authored + approved.
    rep = _report()
    ledger: list = []
    compliance.sign(rep, signer="alice", role="pathologist", action="authored", ledger=ledger, signed_at=FIX)
    compliance.sign(rep, signer="bob", role="director", action="approved", ledger=ledger, signed_at=FIX)
    assert compliance.verify_signatures(rep, ledger)["ok"]

    # Attacker swaps the variant to a clinically different call (KRAS G12C) and,
    # using only the public sign() API, re-forges a full ledger impersonating the
    # same two signers — no key required.
    forged = report.build_report(
        "S1",
        vendors.normalize("roche_like",
            [{"GENE": "KRAS", "alteration": "G12C", "result": "DETECTED", "allele_freq": 0.34}]),
        issued_at=FIX,
    )
    forged_ledger: list = []
    compliance.sign(forged, signer="alice", role="pathologist", action="authored", ledger=forged_ledger, signed_at=FIX)
    compliance.sign(forged, signer="bob", role="director", action="approved", ledger=forged_ledger, signed_at=FIX)

    # The forged record verifies clean and meets the required sign-offs — that is
    # the boundary, asserted rather than hidden.
    res = compliance.verify_signatures(forged, forged_ledger)
    assert res["ok"] is True
    assert compliance.required_signoffs_met(forged_ledger)
    assert forged["content_sha256"] != rep["content_sha256"]
