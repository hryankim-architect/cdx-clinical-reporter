"""End-to-end pipeline: vendor results -> canonical findings -> signed report.

Keeps the house-style shape::

    audit_start -> tracking_start -> body -> tracking_end -> audit_end

The body ingests a synthetic multi-vendor CDx result batch, normalizes it
through the vendor-agnostic shim, builds a clinical report, collects the
required electronic sign-offs (authored + approved), verifies the signature
chain still binds to the report content, and writes a signed-record artifact.
Everything is deterministic given the injected timestamps.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import click

from cdxreport import audit, compliance, report, tracking, vendors


def _run_id(name: str) -> str:
    return f"{name}-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}"


def demo_batch() -> dict[str, list[dict[str, Any]]]:
    """A synthetic multi-vendor result batch (three differently-shaped schemas)."""
    return {
        "roche_like": [
            {"GENE": "EGFR", "alteration": "L858R", "result": "DETECTED", "allele_freq": 0.34},
            {"GENE": "TP53", "alteration": "R175H", "result": "DETECTED", "allele_freq": 0.41},
        ],
        "thermo_like": [
            {"gene_symbol": "KRAS", "hgvs_p": "p.G12C", "call": "POS", "vaf_percent": 28.0},
            {"gene_symbol": "EGFR", "hgvs_p": "p.T790M", "call": "NEG", "vaf_percent": 0.0},
        ],
        "guardant_like": [
            {"Gene": "BRAF", "Variant": "V600E", "Detected": True, "MAF": 0.03},
            {"Gene": "ERBB2", "Variant": "amplification", "Detected": True, "MAF": 0.22},
        ],
    }


def run_pipeline(
    run_name: str,
    out_dir: Path,
    *,
    sample_id: str = "SAMPLE-0001",
    issued_at: str = "2026-05-28T00:00:00Z",
) -> dict[str, Any]:
    """Normalize -> report -> sign -> verify -> artifact."""
    out_dir.mkdir(parents=True, exist_ok=True)
    job_id = _run_id(run_name)

    audit.emit(action="pipeline_start", job_id=job_id, fields={"sample_id": sample_id})

    with tracking.run(name=job_id, experiment="cdxreport"):
        findings = vendors.normalize_batch(demo_batch())
        rep = report.build_report(sample_id, findings, issued_at=issued_at)

        ledger: list[dict[str, Any]] = []
        compliance.sign(rep, signer="pipeline@cdxreport", role="system",
                        action="authored", ledger=ledger, signed_at=issued_at)
        compliance.sign(rep, signer="reviewer@example.org", role="molecular_pathologist",
                        action="approved", ledger=ledger, signed_at=issued_at)

        verification = compliance.verify_signatures(rep, ledger)
        signoffs_met = compliance.required_signoffs_met(ledger)

        tracking.log_metrics({
            "n_findings": float(len(findings)),
            "n_detected": float(rep["qc"]["n_detected"]),
            "signatures": float(len(ledger)),
            "verified_ok": 1.0 if verification["ok"] else 0.0,
        })

    artifact = {
        "job_id": job_id,
        "report": rep,
        "signatures": ledger,
        "verification": verification,
        "required_signoffs_met": signoffs_met,
        "report_markdown": report.render_markdown(rep),
    }
    artifact_path = out_dir / f"{run_name}.json"
    with artifact_path.open("w", encoding="utf-8") as fh:
        json.dump(artifact, fh, indent=2, sort_keys=True)

    audit.emit(action="pipeline_end", job_id=job_id, fields={
        "artifact_path": str(artifact_path),
        "verified_ok": verification["ok"],
        "content_sha256": rep["content_sha256"],
    })

    return {
        "job_id": job_id,
        "artifact_path": str(artifact_path),
        "verification": verification,
        "n_findings": len(findings),
    }


@click.group()
def cli() -> None:
    """cdxreport regulated CDx-reporting pipeline (synthetic-data POC)."""


@cli.command()
@click.option("--manifest", type=click.Path(path_type=Path), default=Path("data/manifest.yaml"))
@click.option("--out", type=click.Path(file_okay=False, path_type=Path), default=Path("data"))
def fetch(manifest: Path, out: Path) -> None:
    """No-op for the synthetic demo: vendor inputs are generated, not downloaded."""
    click.echo(json.dumps(
        {"status": "synthetic-demo", "note": "vendor results are synthetic; "
         "see data/manifest.yaml for the regulated patterns this models",
         "manifest": str(manifest), "out": str(out)}, indent=2))


@cli.command()
@click.option("--name", default="demo")
@click.option("--out", type=click.Path(file_okay=False, path_type=Path), default=Path("artifacts"))
@click.option("--sample", default="SAMPLE-0001")
def run(name: str, out: Path, sample: str) -> None:
    """Run the end-to-end signed-report pipeline."""
    result = run_pipeline(name, out, sample_id=sample)
    click.echo(json.dumps(result, indent=2))


if __name__ == "__main__":
    cli()
