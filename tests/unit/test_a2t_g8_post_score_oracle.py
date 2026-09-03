"""Post-seal, model-free G8 branch-oracle construction."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.analysis.a2t_g8_post_score_oracle import (
    BRANCH_ORDER,
    G8OracleError,
    build_oracle_artifacts,
    select_oracle_rows,
)


IDS = tuple(f"tier{tier}:0000{tier:02d}" for tier in range(1, 17))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _branch_inputs(tmp_path: Path, ids=IDS):
    manifests = {
        branch: (tmp_path / f"{branch}.run-manifest.json").resolve()
        for branch in BRANCH_ORDER
    }
    sealed = {}
    payloads = {}
    for branch_index, branch in enumerate(BRANCH_ORDER):
        manifests[branch].write_text("{}\n", encoding="utf-8")
        rows = []
        detail = []
        for index, sample_id in enumerate(ids):
            text = f"{branch}:{sample_id}"
            rows.append(
                {
                    "sample_id": sample_id,
                    "text": text,
                    "response_text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                }
            )
            detail.append(
                {
                    "sample_id": sample_id,
                    "exact_match": 1.0 if branch_index == 0 else 0.0,
                    "slot_f1": float(branch_index) / 10,
                    "tool_accuracy": float(branch_index) / 10,
                }
            )
        outputs = tmp_path / f"{branch}.outputs.jsonl"
        outputs.write_text(
            "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
            encoding="utf-8",
        )
        sealed[branch] = {
            "manifest": str(manifests[branch]),
            "manifest_sha256": _sha256(manifests[branch]),
            "outputs": str(outputs),
            "outputs_sha256": _sha256(outputs),
        }
        payloads[branch] = {
            "manifest": str(manifests[branch]),
            "verified": True,
            "scores": {
                "a2t-toolcall": {
                    "aggregate": {"samples": len(ids), "exact_match": 0.0},
                    "per_sample": detail,
                }
            },
        }
    return manifests, sealed, payloads


def test_selects_each_sealed_response_by_exact_then_slot_then_tool_then_order(tmp_path: Path) -> None:
    manifests, sealed, payloads = _branch_inputs(tmp_path)
    # No exact result for sample 2: slot F1 decides.  For sample 3, tool
    # accuracy decides; sample 4 is a complete comparator tie.
    for branch in BRANCH_ORDER:
        payloads[branch]["scores"]["a2t-toolcall"]["per_sample"][1]["exact_match"] = 0.0
        payloads[branch]["scores"]["a2t-toolcall"]["per_sample"][2].update(
            exact_match=0.0, slot_f1=0.5
        )
        payloads[branch]["scores"]["a2t-toolcall"]["per_sample"][3].update(
            exact_match=0.0, slot_f1=0.5, tool_accuracy=0.5
        )
    payloads["DECOMPOSED_SELECT_BIND_RESOLVE"]["scores"]["a2t-toolcall"]["per_sample"][1]["slot_f1"] = 0.9
    payloads["SUPPORT_ONLY_RESOLVE"]["scores"]["a2t-toolcall"]["per_sample"][2]["tool_accuracy"] = 0.9

    selected, summary = select_oracle_rows(
        score_payloads=payloads,
        sealed_branches=sealed,
        sample_ids=IDS,
    )

    by_id = {row.sample_id: row for row in selected}
    assert by_id[IDS[0]].branch == "STOP_M0"
    assert by_id[IDS[1]].branch == "DECOMPOSED_SELECT_BIND_RESOLVE"
    assert by_id[IDS[2]].branch == "SUPPORT_ONLY_RESOLVE"
    assert by_id[IDS[3]].branch == "STOP_M0"
    assert by_id[IDS[1]].text == f"DECOMPOSED_SELECT_BIND_RESOLVE:{IDS[1]}"
    assert by_id[IDS[1]].source_manifest == manifests["DECOMPOSED_SELECT_BIND_RESOLVE"]
    assert len(by_id[IDS[1]].score_payload_sha256) == 64
    assert summary["selected_by_branch"]["STOP_M0"] == 14


@pytest.mark.parametrize(
    ("mutate", "match"),
    [
        (lambda _manifests, _sealed, payloads: payloads["STOP_M0"].update(verified=False), "verified"),
        (
            lambda manifests, _sealed, payloads: payloads["STOP_M0"].update(
                manifest=str(manifests["EXHAUSTIVE_G7"])
            ),
            "manifest identity",
        ),
        (
            lambda _manifests, _sealed, payloads: payloads["STOP_M0"]["scores"].pop("a2t-toolcall"),
            "a2t-toolcall",
        ),
        (
            lambda _manifests, _sealed, payloads: payloads["STOP_M0"]["scores"]["a2t-toolcall"]["per_sample"].pop(),
            "sample identities",
        ),
    ],
)
def test_refuses_unverified_or_identity_incomplete_score_payloads(tmp_path: Path, mutate, match: str) -> None:
    manifests, sealed, payloads = _branch_inputs(tmp_path)
    mutate(manifests, sealed, payloads)

    with pytest.raises(G8OracleError, match=match):
        select_oracle_rows(score_payloads=payloads, sealed_branches=sealed, sample_ids=IDS)


@pytest.mark.parametrize("artifact_key", ["manifest", "outputs"])
def test_refuses_sealed_artifact_hash_drift(tmp_path: Path, artifact_key: str) -> None:
    _manifests, sealed, payloads = _branch_inputs(tmp_path)
    artifact = Path(sealed["STOP_M0"][artifact_key])
    artifact.write_text(artifact.read_text(encoding="utf-8") + "drift\n", encoding="utf-8")

    expected = "manifest hash drift" if artifact_key == "manifest" else "output hash drift"
    with pytest.raises(G8OracleError, match=expected):
        select_oracle_rows(score_payloads=payloads, sealed_branches=sealed, sample_ids=IDS)


def test_builder_writes_oracle_outputs_and_tool_trace_with_zero_new_contacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _manifests, sealed, payloads = _branch_inputs(tmp_path)
    captured = {}

    def build_manifest(**kwargs):
        captured.update(kwargs)
        manifest = kwargs["run_dir"] / "PARENT.run-manifest.json"
        manifest.write_text("{}\n", encoding="utf-8")
        return manifest

    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.analysis.a2t_g8_post_score_oracle.build_manifest",
        build_manifest,
    )
    result = build_oracle_artifacts(
        score_payloads=payloads,
        sealed_branches=sealed,
        sample_ids=IDS,
        run_dir=tmp_path / "oracle",
        parent_composed=object(),
        parent_plan=type("Plan", (), {"run_id": "PARENT"})(),
        parent_verified_split=object(),
        data_root=tmp_path,
        session_receipt_path=tmp_path / "session.json",
    )

    assert Path(result["outputs"]).is_file()
    assert Path(result["trace_manifest"]).is_file()
    assert Path(result["manifest"]).is_file()
    assert result["new_model_contacts"] == 0
    assert captured["result"].cost["calls_used"] == 0
    assert captured["result"].cost["parent_physical_contacts_once"] == 544
    assert captured["result"].cost["logical_costs_are_nonadditive"] is True
    source = json.loads(Path(result["outputs"]).read_text(encoding="utf-8").splitlines()[0])["composite_source"]
    assert source["branch"] == "STOP_M0"
    assert source["selection_metrics"]["exact_match"] == 1.0

    with pytest.raises(G8OracleError, match="not empty"):
        build_oracle_artifacts(
            score_payloads=payloads,
            sealed_branches=sealed,
            sample_ids=IDS,
            run_dir=tmp_path / "oracle",
            parent_composed=object(),
            parent_plan=type("Plan", (), {"run_id": "PARENT"})(),
            parent_verified_split=object(),
            data_root=tmp_path,
            session_receipt_path=tmp_path / "session.json",
        )


def test_builder_accepts_fixed12_successor_and_records_actual_parent_contacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ids = IDS[:12]
    _manifests, sealed, payloads = _branch_inputs(tmp_path, ids)
    captured = {}

    def build_manifest(**kwargs):
        captured.update(kwargs)
        manifest = kwargs["run_dir"] / "PARENT.run-manifest.json"
        manifest.write_text("{}\n", encoding="utf-8")
        return manifest

    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.analysis.a2t_g8_post_score_oracle.build_manifest",
        build_manifest,
    )
    result = build_oracle_artifacts(
        score_payloads=payloads,
        sealed_branches=sealed,
        sample_ids=ids,
        expected_sample_count=12,
        parent_physical_contacts_once=405,
        run_dir=tmp_path / "oracle-fixed12",
        parent_composed=object(),
        parent_plan=type("Plan", (), {"run_id": "PARENT"})(),
        parent_verified_split=object(),
        data_root=tmp_path,
        session_receipt_path=tmp_path / "session.json",
    )

    assert result["selection_summary"]["samples"] == 12
    assert captured["result"].cost["parent_physical_contacts_once"] == 405


@pytest.mark.parametrize("value", [True, 0, -1])
def test_builder_refuses_invalid_parent_contact_count(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, value
) -> None:
    ids = IDS[:12]
    _manifests, sealed, payloads = _branch_inputs(tmp_path, ids)
    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.analysis.a2t_g8_post_score_oracle.build_manifest",
        lambda **_kwargs: None,
    )

    with pytest.raises(G8OracleError, match="parent_physical_contacts_once"):
        build_oracle_artifacts(
            score_payloads=payloads,
            sealed_branches=sealed,
            sample_ids=ids,
            expected_sample_count=12,
            parent_physical_contacts_once=value,
            run_dir=tmp_path / f"invalid-{value}",
            parent_composed=object(),
            parent_plan=type("Plan", (), {"run_id": "PARENT"})(),
            parent_verified_split=object(),
            data_root=tmp_path,
            session_receipt_path=tmp_path / "session.json",
        )
