"""E0 D4: ten-sample model-free loader/provenance/four-axis trace receipt.

Sample selection is not hand-picked: it is the upstream-curated Earnings22
``subset10`` (dev/calibration carrier per the umbrella lock research role), sorted.
For each sample the generator materializes provenance (media relpath, re-measured
bytes and SHA-256), builds one validated
:class:`~speech_aware_evidence_acquisition.contracts.TraceRecord` per research axis
(OBS/ORG/SUPPLY/USE) plus a COST record, and stores each record's canonical
serialization and content hash. No model is touched, no audio is decoded, and no
transcript/annotation content enters the artifact; every runtime view passes the
information boundary before it is recorded.
"""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from ..contracts import TraceRecord
from ..data.loader import (
    LoaderError,
    MaterializedSample,
    SampleRef,
    earnings22_subset10_ids,
    load_earnings22,
    materialize,
)
from ..data.lock import asset_dir, load_lock
from .artifacts import ArtifactError, today


def _conec_e22_context_counts(lock: Mapping[str, object], root: Path) -> dict[str, int]:
    """Per-sample count of ConEC Earnings22 context PDFs (names only, never content).

    Fail-closed: a missing pdfs directory is a materialization defect, not
    "no context" — receipting zeros for it would be a false statement."""

    pdf_dir = asset_dir(lock, "conec", root) / "earnings22" / "contexts" / "pdfs"
    if not pdf_dir.is_dir():
        raise ArtifactError(f"conec earnings22 context pdfs directory missing: {pdf_dir}")
    counts: dict[str, int] = {}
    for entry in sorted(pdf_dir.iterdir()):
        if not entry.is_file() or not entry.name.endswith(".pdf"):
            continue
        stem = entry.name[: -len(".pdf")]
        sample_id = stem.split("_", 1)[0]
        counts[sample_id] = counts.get(sample_id, 0) + 1
    return counts


def _trace_records(
    sample: MaterializedSample, context_files: int
) -> list[dict[str, object]]:
    ref: SampleRef = sample.ref
    base = f"SAEA-E0-D4/{ref.sample_id}"
    records = [
        TraceRecord(
            channel="OBS",
            record_id=f"{base}/OBS",
            payload={
                "obs_speech_ref": f"{ref.carrier_lock_key}/{ref.sample_id}",
                "obs_media_relpath": ref.media_relpath,
                "obs_audio_seconds": ref.audio_seconds,
                "obs_sample_rate_hz": ref.sample_rate_hz,
                "obs_decoded": False,
            },
        ),
        TraceRecord(
            channel="ORG",
            record_id=f"{base}/ORG",
            payload={
                "org_carrier_lock_key": ref.carrier_lock_key,
                "org_context_source": "conec/earnings22/contexts/pdfs",
                "org_context_files": context_files,
                "org_context_available": context_files > 0,
                "org_content_read": False,
            },
        ),
        TraceRecord(
            channel="SUPPLY",
            record_id=f"{base}/SUPPLY",
            payload={
                "supply_evidence_items": 0,
                "supply_evidence_bytes": 0,
                "supply_policy": "none:e0-model-free-closure",
            },
        ),
        TraceRecord(
            channel="USE",
            record_id=f"{base}/USE",
            payload={
                "use_admitted_items": 0,
                "use_final_answer_authority": "frozen-core",
                "use_policy": "none:e0-model-free-closure",
            },
        ),
        TraceRecord(
            channel="COST",
            record_id=f"{base}/COST",
            payload={
                "model_calls": 0,
                "tool_calls": 0,
                "speech_audio_seconds_decoded": 0,
                "evidence_bytes_supplied": 0,
            },
        ),
    ]
    receipted = []
    for record in records:
        record.validate()
        # Receipt metadata only: payload key names + content hash. The serialized
        # record itself is a trace and traces are never committed (study boundary);
        # the hash is reproducible because generation is deterministic.
        receipted.append(
            {
                "channel": record.channel,
                "record_id": record.record_id,
                "payload_keys": sorted(record.payload),
                "content_sha256": record.content_hash(),
            }
        )
    return receipted


def build_d4(lock_path: Path, data_root: Path) -> dict[str, object]:
    lock = load_lock(lock_path)
    all_samples = {sample.sample_id: sample for sample in load_earnings22(lock, data_root)}
    selected_ids = earnings22_subset10_ids(lock, data_root)
    missing = [sample_id for sample_id in selected_ids if sample_id not in all_samples]
    if missing:
        raise LoaderError(f"subset10 ids missing from the earnings22 identity set: {missing}")

    context_counts = _conec_e22_context_counts(lock, data_root)

    samples_report = []
    boundary_checks = 0
    for sample_id in selected_ids:
        materialized = materialize(all_samples[sample_id], data_root)
        runtime_view = materialized.ref.runtime_view()
        boundary_checks += 1
        samples_report.append(
            {
                "sample_id": sample_id,
                "carrier_lock_key": materialized.ref.carrier_lock_key,
                "provenance": {
                    "media_relpath": materialized.ref.media_relpath,
                    "media_bytes": materialized.media_bytes,
                    "media_sha256": materialized.media_sha256,
                },
                "runtime_view_fields": sorted(runtime_view),
                "trace_records": _trace_records(
                    materialized, context_counts.get(sample_id, 0)
                ),
            }
        )

    return {
        "artifact_kind": "saea-e0-d4-trace-v1",
        "generated": today(),
        "selection_rule": (
            "earnings22-original subset10 media stems (upstream-curated ten-call dev "
            "subset), sorted lexicographically — not hand-picked"
        ),
        "split_note": (
            "earnings22-original is the dev/calibration carrier per the umbrella lock "
            "research role; no confirmatory sample identity is defined or read here"
        ),
        "sample_count": len(samples_report),
        "samples": samples_report,
        "validations": {
            "runtime_boundary_checks_passed": boundary_checks,
            "trace_records_validated": sum(
                len(sample["trace_records"]) for sample in samples_report
            ),
            "model_calls": 0,
            "audio_decoded": False,
        },
    }
