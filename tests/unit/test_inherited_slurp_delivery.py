import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.core.bundle import BundleError, RUN_MANIFEST_SCHEMA
from speech_aware_evidence_acquisition.core.bundle import delivery as delivery_mod
from speech_aware_evidence_acquisition.core.bundle.artifacts import VerifiedBundle


def _bundle(path, run_id, rows, split_ids):
    return VerifiedBundle(
        manifest_path=path,
        manifest={
            "schema": RUN_MANIFEST_SCHEMA,
            "status": "COMPLETED",
            "run_id": run_id,
            "config": {"fragments": {"model": "m", "dataset": "d", "baseline": "b", "experiment": "e"}, "config_hash": "cfg"},
            "outputs": {"sha256": "unused"},
        },
        outputs_path=path.with_suffix(".outputs.jsonl"),
        outputs_rows=tuple(rows),
        trace_records={},
        split_ids=frozenset(split_ids),
        attempt_state="FINALIZED",
    )


def _world(tmp_path, monkeypatch, *, source_ids=("a", "b")):
    parent_path = tmp_path / "parent.json"
    source_path = tmp_path / "runs" / "direct.json"
    source_path.parent.mkdir(parents=True)
    parent_path.write_text(json.dumps({"schema": RUN_MANIFEST_SCHEMA}))
    parent_rows = [
        {"request_id": "slot-a", "sample_id": "a", "carrier_lock_key": "slurp", "arm": "slots", "text": '{"entities": []}', "admitted": True},
        {"request_id": "slot-b", "sample_id": "b", "carrier_lock_key": "slurp", "arm": "slots", "text": '{"entities": []}', "admitted": True},
    ]
    direct_rows = [
        {"request_id": "direct-a", "sample_id": "a", "carrier_lock_key": "slurp", "arm": "direct", "text": '{"scenario": "music", "action": "play"}', "admitted": True},
        {"request_id": "direct-b", "sample_id": "b", "carrier_lock_key": "slurp", "arm": "direct", "text": '{"scenario": "calendar", "action": "set"}', "admitted": True},
    ]
    if source_ids != ("a", "b"):
        direct_rows = [direct_rows[0]]
    output_path = source_path.with_suffix(".outputs.jsonl")
    output_raw = b"".join(json.dumps(row, sort_keys=True).encode() + b"\n" for row in direct_rows)
    output_path.write_bytes(output_raw)
    source_raw = json.dumps({"schema": RUN_MANIFEST_SCHEMA}).encode()
    source_path.write_bytes(source_raw)
    source_hash = hashlib.sha256(source_raw).hexdigest()
    output_hash = hashlib.sha256(output_raw).hexdigest()
    parent = _bundle(parent_path, "slots-run", parent_rows, ("a", "b"))
    predecessor = _bundle(source_path, "direct-run", direct_rows, source_ids)
    predecessor.manifest["outputs"] = {"sha256": output_hash}
    fake_compose = SimpleNamespace(
        config_hash="cfg",
        values={
            "carrier_lock_key": "slurp",
            "policy": "phase-slots-given-intent-v1",
            "phase_material": {"slots": {"predecessor_binding": "sealed-manifest", "predecessor_source": {
                "manifest_relpath": "runs/direct.json", "manifest_sha256": source_hash, "producer_policy_id": "phase-direct-only-v1"
            }}},
        },
    )
    monkeypatch.setattr(delivery_mod, "compose", lambda *args, **kwargs: fake_compose)
    import speech_aware_evidence_acquisition.core.bundle.verify as verify_mod
    monkeypatch.setattr(verify_mod, "verify_bundle", lambda path: parent if Path(path).resolve() == parent_path.resolve() else predecessor)
    return parent_path, source_path, parent, predecessor, fake_compose


def test_inherited_slurp_join_is_sorted_and_preserves_parent(monkeypatch, tmp_path):
    parent_path, _, parent, _, _ = _world(tmp_path, monkeypatch)
    before = tuple(dict(row) for row in parent.outputs_rows)
    loaded, declaration, receipt, rows, windows = delivery_mod._inherited_slurp_inputs(
        parent_path, tmp_path / "repo", tmp_path / "repo" / "configs/experiment/e.json", tmp_path
    )
    assert loaded is parent
    assert receipt is None
    assert declaration["cell_id"] == "inherited-intent-slots-v1"
    assert declaration["source_selector"]["schema"] == "saea-sealed-predecessor-response-pair-v1"
    assert [row["sample_id"] for row in rows] == ["a", "b"]
    assert json.loads(rows[0]["text"]) == {"action": "play", "entities": [], "scenario": "music"}
    assert tuple(dict(row) for row in parent.outputs_rows) == before
    assert windows["join_diagnostics"]["rows"] == 2


def test_inherited_slurp_refuses_roster_mismatch(monkeypatch, tmp_path):
    parent_path, _, _, _, _ = _world(tmp_path, monkeypatch, source_ids=("a",))
    with pytest.raises(BundleError, match="roster"):
        delivery_mod._inherited_slurp_inputs(
            parent_path, tmp_path / "repo", tmp_path / "repo" / "configs/experiment/e.json", tmp_path
        )


def test_inherited_slurp_refuses_source_manifest_or_outputs_tamper(monkeypatch, tmp_path):
    parent_path, source_path, _, _, _ = _world(tmp_path, monkeypatch)
    source_path.write_bytes(b'{"schema":"tampered"}')
    with pytest.raises(BundleError, match="manifest hash"):
        delivery_mod._inherited_slurp_inputs(
            parent_path, tmp_path / "repo", tmp_path / "repo" / "configs/experiment/e.json", tmp_path
        )
    parent_path, source_path, _, _, _ = _world(tmp_path / "second", monkeypatch)
    output_path = source_path.with_suffix(".outputs.jsonl")
    output_path.write_bytes(output_path.read_bytes() + b"tamper")
    with pytest.raises(BundleError, match="outputs hash"):
        delivery_mod._inherited_slurp_inputs(
            parent_path, tmp_path / "second" / "repo", tmp_path / "second" / "repo" / "configs/experiment/e.json", tmp_path / "second"
        )


def test_inherited_slurp_accepts_historical_run_identity_and_refuses_mismatch(monkeypatch, tmp_path):
    parent_path, _, _, _, config = _world(tmp_path, monkeypatch)
    source = config.values["phase_material"]["slots"]["predecessor_source"]
    source["producer_policy_id"] = "direct-run"
    delivery_mod._inherited_slurp_inputs(
        parent_path, tmp_path / "repo", tmp_path / "repo/configs/experiment/e.json", tmp_path
    )
    source["producer_policy_id"] = "different-run"
    with pytest.raises(BundleError, match="producer identity"):
        delivery_mod._inherited_slurp_inputs(
            parent_path, tmp_path / "repo", tmp_path / "repo/configs/experiment/e.json", tmp_path
        )
