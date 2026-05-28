"""Deterministic canary smoke test.

Probed daily by the Polish-Phase5 ``lab_semantic_check.py`` runner. Contract:
completes in well under 30 s, deterministic, exit 0 on success / non-zero on any
deviation, no external services required.

The check builds a tiny report, signs it, verifies the signature chain binds to
the content, then tampers with the report and asserts verification now fails —
i.e. it exercises the core 21 CFR Part 11-style invariant end to end.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from cdxreport import audit, compliance, report, tracking, vendors

DEFAULT_FIXTURE = Path("tests/fixtures/canary.json")
EXPECTED_KEYS = {"name", "tier", "sample_id"}


def _load_fixture(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"canary fixture not found: {path}")
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def check() -> dict[str, Any]:
    fixture_path = Path(os.environ.get("CDXREPORT_CANARY_FIXTURE", str(DEFAULT_FIXTURE)))
    fixture = _load_fixture(fixture_path)
    missing = EXPECTED_KEYS - set(fixture.keys())
    if missing:
        return {"ok": False, "reason": f"fixture missing keys: {sorted(missing)}"}

    job_id = f"canary-{fixture['name']}"
    audit.emit(action="canary_start", job_id=job_id, fields={"tier": fixture["tier"]})

    findings = vendors.normalize(
        "roche_like",
        [{"GENE": "EGFR", "alteration": "L858R", "result": "DETECTED", "allele_freq": 0.3}],
    )
    rep = report.build_report(fixture["sample_id"], findings, issued_at="2026-01-01T00:00:00Z")
    ledger: list[dict[str, Any]] = []
    compliance.sign(rep, signer="canary", role="system", action="authored",
                    ledger=ledger, signed_at="2026-01-01T00:00:00Z")
    intact = compliance.verify_signatures(rep, ledger)["ok"]

    # tamper: mutate report content; verification must now fail
    tampered = dict(rep)
    tampered["sample_id"] = "TAMPERED"
    tamper_detected = not compliance.verify_signatures(tampered, ledger)["ok"]

    ok = bool(intact and tamper_detected)

    with tracking.run(name=job_id, experiment="canary"):
        tracking.log_metric("verified_ok", 1.0 if intact else 0.0)
        tracking.log_metric("tamper_detected", 1.0 if tamper_detected else 0.0)

    audit.emit(action="canary_end", job_id=job_id,
               fields={"ok": ok, "intact": intact, "tamper_detected": tamper_detected})
    return {"ok": ok, "job_id": job_id, "intact": intact, "tamper_detected": tamper_detected}


def main() -> int:
    result = check()
    print(json.dumps(result, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
