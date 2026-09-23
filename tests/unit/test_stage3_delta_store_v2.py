"""Stage-3 S3-4s (owner decision 106): the NODE-TARGETED delta store.

Three obligations:

1. ``build_stage3_delta_snapshot_v2`` compiles a ``node_target`` row and
   refuses one whose ``task_target`` does not begin with that node; it is
   registered BESIDE v1 and v1 is untouched.
2. The curation CLI's v2 path turns one multi-block advantage response into
   one row per legal block, with ``node_target``, the three-field
   ``task_target`` and the bare ``TARGET`` as the associated facet.
3. The six-token containment rule drops a statement that repeats a
   construction transcript span, counts it, and prints no text.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.core.base import KNOWLEDGE_BUILDERS  # noqa: E402
from speech_aware_evidence_acquisition.rails.errors import RailsError  # noqa: E402
from speech_aware_evidence_acquisition.rails import knowledge_build as _kb  # noqa: E402,F401
from speech_aware_evidence_acquisition.rails.semantic_knowledge_build import (  # noqa: E402
    STAGE3_DELTA_BUILD_POLICY_ID,
    STAGE3_DELTA_V2_BUILD_POLICY_ID,
    AuthoredSemanticKnowledgeSpec,
    build_stage3_delta_snapshot,
    build_stage3_delta_snapshot_v2,
)

_spec = importlib.util.spec_from_file_location(
    "build_slurp_stage3_delta_store_v2",
    REPO_ROOT / "scripts" / "build_slurp_stage3_delta_store.py",
)
cli = importlib.util.module_from_spec(_spec)
sys.modules.setdefault(_spec.name, cli)
_spec.loader.exec_module(cli)  # type: ignore[union-attr]


def _spec_obj():
    return AuthoredSemanticKnowledgeSpec(
        carrier_lock_key="slurp",
        source_split_identity_hash="a" * 64,
        permitted_source_sample_ids=("train-1", "train-2"),
    )


def _row(suffix="aaaaaaaaaaaa", *, node="solver", kind="slot-contract", target="alarm_set"):
    return {
        "value_id": f"delta:1:{suffix}",
        "content": "Keep the device slot only when the speech names a device.",
        "associated_facet_ids": [target],
        "node_target": node,
        "source_sample_ids": ["train-1"],
        "provenance_refs": ["advantage:SAEA-TEST-RUN:train-1:0:1:0"],
        "task_target": f"{node}:{kind}:{target}",
        "prior_score": 0.6,
    }


# ---------------------------------------------------------------------------
# 1. The builder
# ---------------------------------------------------------------------------


def test_the_v2_builder_is_registered_beside_v1() -> None:
    names = KNOWLEDGE_BUILDERS.names()
    assert STAGE3_DELTA_BUILD_POLICY_ID in names
    assert STAGE3_DELTA_V2_BUILD_POLICY_ID in names
    assert KNOWLEDGE_BUILDERS.resolve(STAGE3_DELTA_V2_BUILD_POLICY_ID) is (
        build_stage3_delta_snapshot_v2
    )


def test_a_node_targeted_row_compiles_and_keeps_its_node_in_task_target() -> None:
    snapshot = build_stage3_delta_snapshot_v2(_spec_obj(), rows=(_row(),))
    assert snapshot.builder_policy_id == STAGE3_DELTA_V2_BUILD_POLICY_ID
    value = snapshot.values[0]
    assert value.task_target == "solver:slot-contract:alarm_set"
    assert value.associated_facet_ids == ("alarm_set",)
    # The facet is minted in the store's own dimension, not in the target's.
    assert snapshot.facets[0].dimension == "stage3-delta-target"


@pytest.mark.parametrize(
    "mutation",
    [
        {"node_target": "reviewer"},  # disagrees with task_target's head
        {"node_target": "answering-node"},  # not a node at all
    ],
)
def test_a_row_whose_node_disagrees_with_its_task_target_is_refused(mutation) -> None:
    row = {**_row(), **mutation}
    with pytest.raises(RailsError):
        build_stage3_delta_snapshot_v2(_spec_obj(), rows=(row,))


def test_a_v1_row_is_refused_by_the_v2_builder_and_vice_versa() -> None:
    v1_row = {k: v for k, v in _row().items() if k != "node_target"}
    v1_row["task_target"] = "slot-contract:alarm_set"
    with pytest.raises(RailsError):
        build_stage3_delta_snapshot_v2(_spec_obj(), rows=(v1_row,))
    with pytest.raises(RailsError):
        build_stage3_delta_snapshot(_spec_obj(), rows=(_row(),))


def test_v1_still_compiles_a_v1_row_unchanged() -> None:
    v1_row = {k: v for k, v in _row().items() if k != "node_target"}
    v1_row["task_target"] = "slot-contract:alarm_set"
    snapshot = build_stage3_delta_snapshot(_spec_obj(), rows=(v1_row,))
    assert snapshot.builder_policy_id == STAGE3_DELTA_BUILD_POLICY_ID


# ---------------------------------------------------------------------------
# 2 and 3. The curation CLI's v2 path
# ---------------------------------------------------------------------------

TRANSCRIPT = "set an alarm for seven o clock tomorrow morning please"
BLOCKS = (
    "NODE: solver\n"
    "DELTA-KIND: slot-contract\n"
    "TARGET: alarm_set\n"
    "STATEMENT: Keep the time slot whenever the speech states a clock time.\n"
    "NODE: perception\n"
    "DELTA-KIND: perception-hint\n"
    "TARGET: alarm_query\n"
    "STATEMENT: Propose the query intent when the utterance asks about an alarm.\n"
)
# Six consecutive transcript tokens -> dropped by the containment rule.
CONTAINED_BLOCK = (
    "NODE: reviewer\n"
    "DELTA-KIND: reviewer-criterion\n"
    "TARGET: alarm_set\n"
    "STATEMENT: Reject drafts that miss set an alarm for seven o clock.\n"
)


def _fixture(tmp_path, response_text):
    pairs_path = tmp_path / "pairs.json"
    pairs_path.write_text(
        json.dumps({
            "rows": [{
                "sample_id": "train-1",
                "best": {"sample_index": 2, "response_text_sha256": "a" * 64},
                "worst": {"sample_index": 4, "response_text_sha256": "b" * 64},
            }]
        }),
        encoding="utf-8", newline="\n",
    )
    outputs_path = tmp_path / "outputs.jsonl"
    outputs_path.write_text(
        json.dumps({
            "sample_id": "train-1",
            "response_text": response_text,
            "disagreement": 0.6,
        }) + "\n",
        encoding="utf-8", newline="\n",
    )
    transcripts_path = tmp_path / "transcripts.jsonl"
    transcripts_path.write_text(
        json.dumps({"sample_id": "train-1", "text": TRANSCRIPT}) + "\n",
        encoding="utf-8", newline="\n",
    )
    return pairs_path, outputs_path, transcripts_path


def _run(tmp_path, response_text, *, with_transcripts=True):
    pairs_path, outputs_path, transcripts_path = _fixture(tmp_path, response_text)
    out_path = tmp_path / "authored.json"
    argv = [
        "--advantage-outputs", str(outputs_path),
        "--pairs", str(pairs_path),
        "--repo-root", str(tmp_path),
        "--predecessor", "none",
        "--iteration", "1",
        "--run-id", "SAEA-TEST-RUN",
        "--out-authored", str(out_path),
    ]
    if with_transcripts:
        argv += ["--construction-transcripts", str(transcripts_path)]
    assert cli.main(argv) == 0
    return json.loads(out_path.read_bytes()), out_path


def test_one_contact_yields_one_row_per_legal_block(tmp_path, capsys):
    document, _ = _run(tmp_path, BLOCKS)
    assert document["schema"] == "saea-stage3-authored-deltas-v2"
    assert len(document["rows"]) == 2
    by_node = {row["node_target"]: row for row in document["rows"]}
    assert set(by_node) == {"solver", "perception"}
    assert by_node["solver"]["task_target"] == "solver:slot-contract:alarm_set"
    assert by_node["solver"]["associated_facet_ids"] == ["alarm_set"]
    assert by_node["perception"]["task_target"] == (
        "perception:perception-hint:alarm_query"
    )
    # The block index is part of the provenance, so two blocks of one contact
    # never collapse into one provenance reference.
    refs = {row["provenance_refs"][0] for row in document["rows"]}
    assert refs == {
        "advantage:SAEA-TEST-RUN:train-1:2:4:0",
        "advantage:SAEA-TEST-RUN:train-1:2:4:1",
    }
    report = json.loads(capsys.readouterr().out)
    assert report["schema_version"] == 2
    assert report["parse"]["blocks_legal"] == 2
    assert report["survivors_by_node"] == {
        "perception": 1, "planner": 0, "reviewer": 0, "solver": 1,
    }


def test_the_containment_rule_drops_a_transcript_span_and_counts_it(tmp_path, capsys):
    document, _ = _run(tmp_path, BLOCKS + CONTAINED_BLOCK)
    assert len(document["rows"]) == 2  # the reviewer block is gone
    assert all(row["node_target"] != "reviewer" for row in document["rows"])
    stdout = capsys.readouterr().out
    report = json.loads(stdout)
    assert report["parse"]["blocks_contained"] == 1
    assert report["containment"] == {
        "enabled": True, "transcripts": 1, "spans": 5, "span_tokens": 6,
    }
    # The console never carries transcript or statement text.
    assert "alarm for seven" not in stdout
    assert "Reject drafts" not in stdout


def test_a_five_token_overlap_is_allowed(tmp_path):
    short_overlap = (
        "NODE: reviewer\n"
        "DELTA-KIND: reviewer-criterion\n"
        "TARGET: alarm_set\n"
        "STATEMENT: Reject drafts that miss set an alarm for seven.\n"
    )
    document, _ = _run(tmp_path, short_overlap)
    assert len(document["rows"]) == 1


def test_without_transcripts_the_rule_is_disabled_and_the_report_says_so(
    tmp_path, capsys
):
    _run(tmp_path, BLOCKS + CONTAINED_BLOCK, with_transcripts=False)
    report = json.loads(capsys.readouterr().out)
    assert report["containment"]["enabled"] is False
    assert report["parse"]["blocks_contained"] == 0


def test_the_curated_v2_rows_compile_through_the_v2_builder(tmp_path):
    document, _ = _run(tmp_path, BLOCKS)
    snapshot = build_stage3_delta_snapshot_v2(
        AuthoredSemanticKnowledgeSpec(
            carrier_lock_key="slurp",
            source_split_identity_hash="a" * 64,
            permitted_source_sample_ids=("train-1",),
        ),
        rows=document["rows"],
    )
    assert len(snapshot.values) == 2
    assert {value.task_target for value in snapshot.values} == {
        "solver:slot-contract:alarm_set",
        "perception:perception-hint:alarm_query",
    }


def test_an_illegal_block_is_dropped_and_counted_not_raised(tmp_path, capsys):
    document, _ = _run(
        tmp_path,
        BLOCKS + "NODE: oracle\nDELTA-KIND: telepathy\nTARGET: x\nSTATEMENT: y\n",
    )
    assert len(document["rows"]) == 2
    report = json.loads(capsys.readouterr().out)
    assert report["parse"]["blocks_illegal"] == 1
