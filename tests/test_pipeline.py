"""End-to-end pipeline + audit-chain smoke tests."""

from __future__ import annotations

import json
from pathlib import Path

from cdxreport import audit, pipeline


def test_pipeline_produces_verified_signed_report(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("AUDIT_HOST", raising=False)
    monkeypatch.delenv("MLFLOW_TRACKING_URI", raising=False)

    result = pipeline.run_pipeline("smoke", tmp_path / "artifacts")
    assert result["verification"]["ok"]
    assert result["n_findings"] == 6

    payload = json.loads(Path(result["artifact_path"]).read_text())
    assert payload["required_signoffs_met"] is True
    assert len(payload["signatures"]) == 2
    assert payload["report"]["content_sha256"]


def test_pipeline_is_deterministic(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("AUDIT_HOST", raising=False)
    a = pipeline.run_pipeline("a", tmp_path / "a")
    b = pipeline.run_pipeline("b", tmp_path / "b")
    pa = json.loads(Path(a["artifact_path"]).read_text())
    pb = json.loads(Path(b["artifact_path"]).read_text())
    # same inputs + injected timestamps -> identical report content hash
    assert pa["report"]["content_sha256"] == pb["report"]["content_sha256"]


def test_audit_chain_valid_after_pipeline(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("AUDIT_HOST", raising=False)
    pipeline.run_pipeline("smoke", tmp_path / "artifacts")
    ok, n, first_bad = audit.verify()
    assert ok, f"audit chain invalid at {first_bad}"
    assert n >= 2
