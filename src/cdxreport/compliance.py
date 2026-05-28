"""21 CFR Part 11-style controls: electronic signatures bound to report content.

This module models the part of a regulated reporting workflow that turns a
generated report into a *signed, defensible record*:

- **Electronic signature records** bound to the report's content hash. Each
  signature captures who signed, in what role, what action (e.g. authored /
  reviewed / approved), when, and the SHA-256 of the exact report content they
  signed.
- **A hash-chained signature ledger** — every signature's ``prev_hash`` is the
  SHA-256 of the previous signature's canonical JSON, so the *sequence* of
  signatures is tamper-evident (you cannot drop, reorder, or insert a signature
  without breaking the chain).
- **Tamper detection** — re-verification checks both that the chain is intact
  *and* that every signature's content hash still equals the report's current
  content hash. If the report is edited after signing, verification fails.

This is the public *pattern* behind Part 11 e-records / e-signatures, not a
validated implementation and not legal/regulatory advice. Synthetic data only.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

ZERO = "0" * 64
VALID_ACTIONS = {"authored", "reviewed", "approved", "amended"}


@dataclass(frozen=True)
class Signature:
    ts: str
    signer: str
    role: str
    action: str
    content_sha256: str
    prev_hash: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _canonical(d: dict[str, Any]) -> bytes:
    return json.dumps(d, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _chain_hash(sig: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical(sig)).hexdigest()


def sign(
    report: dict[str, Any],
    *,
    signer: str,
    role: str,
    action: str = "approved",
    ledger: list[dict[str, Any]] | None = None,
    signed_at: str | None = None,
) -> dict[str, Any]:
    """Append an electronic-signature record bound to the report's content hash.

    ``ledger`` is the running list of prior signatures (mutated in place and also
    returned via the record). ``signed_at`` is injectable for deterministic
    tests / canary.
    """
    if action not in VALID_ACTIONS:
        raise ValueError(f"invalid action {action!r}; allowed: {sorted(VALID_ACTIONS)}")
    content = report.get("content_sha256")
    if not content:
        raise ValueError("report has no content_sha256; build it via report.build_report")

    ledger = ledger if ledger is not None else []
    prev = _chain_hash(ledger[-1]) if ledger else ZERO
    ts = signed_at or datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    record = Signature(
        ts=ts, signer=signer, role=role, action=action,
        content_sha256=content, prev_hash=prev,
    ).as_dict()
    ledger.append(record)
    return record


def verify_signatures(report: dict[str, Any], ledger: list[dict[str, Any]]) -> dict[str, Any]:
    """Verify the signature chain and that it still binds to the report content.

    Returns ``{"ok", "n_signatures", "reason"}``. ``ok`` is True only if (1) the
    report's content still hashes to its stored ``content_sha256`` (no silent
    edit), (2) the signature hash chain is intact, and (3) every signature binds
    the report's current content hash. Any post-signature edit is caught.
    """
    from cdxreport import report as _report

    if not _report.verify_content_hash(report):
        return {"ok": False, "n_signatures": 0,
                "reason": "report content does not match its content_sha256 (report tampered)"}
    current = report.get("content_sha256", "")
    prev = ZERO
    for i, rec in enumerate(ledger):
        if rec.get("prev_hash") != prev:
            return {"ok": False, "n_signatures": i, "reason": f"chain break at index {i}"}
        if rec.get("content_sha256") != current:
            return {
                "ok": False,
                "n_signatures": i,
                "reason": f"signature {i} binds a different content hash (report tampered)",
            }
        prev = _chain_hash(rec)
    return {"ok": True, "n_signatures": len(ledger), "reason": None}


def required_signoffs_met(
    ledger: list[dict[str, Any]], *, required: tuple[str, ...] = ("authored", "approved")
) -> bool:
    """Has the report collected every required sign-off action?"""
    actions = {rec.get("action") for rec in ledger}
    return all(r in actions for r in required)
