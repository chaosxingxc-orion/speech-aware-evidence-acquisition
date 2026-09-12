import hashlib
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.bundle.artifacts import VerifiedBundle
from speech_aware_evidence_acquisition.core.roster import RosterItem, freeze_roster, write_roster
from speech_aware_evidence_acquisition.core.scoring_receipt import (
    capture_score_source,
    write_complete_score_receipt,
)
from speech_aware_evidence_acquisition.rails.reward_links import (
    RewardLinkError,
    RewardProjection,
    build_experience_sources,
    build_reward_links,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture(tmp_path: Path):
    samples = ("slurp:train:0001", "slurp:train:0002")
    roster = freeze_roster(
        carrier_lock_key="slurp",
        candidates=[RosterItem(sample, "slot") for sample in samples],
        per_stratum=2,
        seed=3,
        split_role="discovery",
        roster_id="synthetic-train",
        roster_role="construction",
    )
    roster_path = tmp_path / "roster.json"
    write_roster(roster, roster_path)

    outputs_path = tmp_path / "outputs.jsonl"
    output_rows = [
        {"sample_id": sample, "request_id": f"req-{index}", "text": f"answer-{index}",
         "response_text_sha256": hashlib.sha256(f"answer-{index}".encode()).hexdigest(),
         "response_sha256": hashlib.sha256(f"answer-{index}".encode()).hexdigest(),
         "request_sha256": "a" * 64, "carrier_lock_key": "slurp", "arm": "synthetic"}
        for index, sample in enumerate(samples, 1)
    ]
    outputs_path.write_text("\n".join(json.dumps(row) for row in output_rows) + "\n")
    trace_path = tmp_path / "trace.jsonl"
    trace_rows = []
    for index, sample in enumerate(samples, 1):
        trace_rows.extend([
            {"channel": "tool_action", "record_id": f"act-{index}-{sample}",
             "payload": {"sample_id": sample, "tool_manifest_sha256": "b" * 64}},
            {"channel": "response", "record_id": f"resp-{index}-{sample}",
             "payload": {"sample_id": sample, "text": f"answer-{index}"}},
        ])
    trace_path.write_text("\n".join(json.dumps(row) for row in trace_rows) + "\n")
    trace_manifest_path = tmp_path / "trace-manifest.json"
    trace_manifest_path.write_text(json.dumps({"records": {}}))
    manifest_path = tmp_path / "manifest.json"
    manifest = {
        "schema": "saea-run-manifest-v1", "status": "COMPLETED", "run_id": "SAEA-SYNTH-001",
        "config": {"config_hash": "c" * 64},
        "split": {"carrier_lock_key": "slurp", "ids": list(samples), "count": len(samples),
                  "identity_hash": "d" * 64},
        "scorers": ["slurp-slu-official"],
        "outputs": {"path": str(outputs_path), "sha256": _sha(outputs_path)},
        "raw_trace": {"path": str(trace_path), "sha256": _sha(trace_path)},
        "trace_manifest": {"path": str(trace_manifest_path), "sha256": _sha(trace_manifest_path)},
    }
    manifest_path.write_text(json.dumps(manifest))
    bundle = VerifiedBundle(
        manifest_path=manifest_path, manifest=manifest, outputs_path=outputs_path,
        outputs_rows=tuple(output_rows), trace_records={}, split_ids=frozenset(samples),
        attempt_state="FINALIZED",
    )
    result_path = tmp_path / "score-result.json"
    result = {
        "manifest": str(manifest_path), "verified": True,
        "scores": {"slurp-slu-official": {
            "aggregate": {"f1": 0.5, "tp": 3},
            "per_sample": [{"sample_id": samples[0], "f1": 0.4, "tp": 1},
                           {"sample_id": samples[1], "f1": 0.6, "tp": 2}],
        }},
    }
    result_path.write_text(json.dumps(result))
    receipt_path = tmp_path / "score-receipt.json"
    receipt = write_complete_score_receipt(
        receipt_path, job_id="synthetic-score", result_path=result_path,
        source=capture_score_source(bundle), verified_bundle=bundle,
    )
    return manifest_path, roster_path, receipt, bundle


def test_complete_synthetic_bundle_builds_sources(monkeypatch, tmp_path):
    manifest, roster, receipt, bundle = _fixture(tmp_path)
    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.rails.reward_links.verify_bundle",
        lambda path: bundle,
    )
    projection = RewardProjection("slurp-slu-official-v1", "slurp-slu-official", ("f1", "tp"), ("f1",))
    links = build_reward_links(manifest, receipt, roster, projection)
    sources = build_experience_sources(manifest, receipt, roster, projection)
    assert sorted(source.source_sample_id for source in sources) == ["slurp:train:0001", "slurp:train:0002"]
    assert links[0].source == sources[0]
    assert "answer-1" not in json.dumps(links[0].as_json())
    assert links[0].provenance["ordered_events"][0]["axis"] == "tool_action"


def test_projection_and_trace_refuse_mutations(monkeypatch, tmp_path):
    manifest, roster, receipt, bundle = _fixture(tmp_path)
    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.rails.reward_links.verify_bundle",
        lambda path: bundle,
    )
    projection = RewardProjection("rule", "slurp-slu-official", ("f1",), ("f1",))
    links = build_reward_links(manifest, receipt, roster, projection)
    links[0].provenance["ordered_actions"].reverse()
    with pytest.raises(RewardLinkError):
        links[0].validate()
    with pytest.raises(RewardLinkError):
        RewardProjection("cost-rule", "cost", ("mean",), ("mean",))