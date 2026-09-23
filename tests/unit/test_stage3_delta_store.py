"""Stage-3 S3-5 proof obligations (docs/superpowers/specs/2026-09-22-stage3-
tfrl-base-loop-engineering.md section S3-5 and "Proof obligations"): the
append-only delta-store builder (``rails.semantic_knowledge_build.
build_stage3_delta_snapshot``) and the curation CLI
(``scripts/build_slurp_stage3_delta_store.py``), entirely on synthetic
fixtures under ``tmp_path``.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.base import KNOWLEDGE_BUILDERS
from speech_aware_evidence_acquisition.core.preparation import canonical_bytes
from speech_aware_evidence_acquisition.core.semantic_knowledge_preparation import (
    prepare_semantic_knowledge_store,
)
from speech_aware_evidence_acquisition.data.splits import prefixed, split_identity_hash
from speech_aware_evidence_acquisition.rails import knowledge_build as _registrations  # noqa: F401
from speech_aware_evidence_acquisition.rails.errors import RailsError
from speech_aware_evidence_acquisition.rails.knowledge_stores import load_knowledge_store_binding
from speech_aware_evidence_acquisition.rails.semantic_knowledge_build import (
    STAGE3_DELTA_BUILD_POLICY_ID,
    STAGE3_DELTA_DIMENSION,
    AuthoredSemanticKnowledgeSpec,
    build_stage3_delta_snapshot,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "build_slurp_stage3_delta_store.py"

_spec = importlib.util.spec_from_file_location("_build_slurp_stage3_delta_store", SCRIPT_PATH)
_module = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _module
_spec.loader.exec_module(_module)  # type: ignore[union-attr]

build_candidate_rows = _module.build_candidate_rows
curate = _module.curate
load_predecessor_rows = _module.load_predecessor_rows
write_authored_document = _module.write_authored_document
main = _module.main
Stage3DeltaStoreError = _module.Stage3DeltaStoreError

SHA = "1" * 64


# ---------------------------------------------------------------------------
# build_stage3_delta_snapshot
# ---------------------------------------------------------------------------


def _delta_row(
    *,
    statement: str = "Synthetic statement text.",
    target: str = "alarm_set",
    sample_id: str = "synthetic-row-1",
    iteration: int = 1,
    prior_score: float = 0.4,
) -> dict[str, object]:
    value_id = f"delta:{iteration}:{hashlib.sha256(statement.encode()).hexdigest()[:12]}"
    return {
        "value_id": value_id,
        "content": statement,
        "associated_facet_ids": [f"stage3-delta-target:{target}"],
        "source_sample_ids": [sample_id],
        "provenance_refs": [f"advantage:SAEA-TEST-RUN:{sample_id}:2:4"],
        "task_target": f"exemplar-note:{target}",
        "prior_score": prior_score,
    }


def _spec(**changes):
    from dataclasses import replace

    return replace(
        AuthoredSemanticKnowledgeSpec(
            carrier_lock_key="slurp",
            source_split_identity_hash=SHA,
            permitted_source_sample_ids=("synthetic-row-1", "synthetic-row-2", "synthetic-row-3"),
        ),
        **changes,
    )


def test_builder_is_registered_in_knowledge_builders() -> None:
    assert STAGE3_DELTA_BUILD_POLICY_ID in KNOWLEDGE_BUILDERS.names()
    assert KNOWLEDGE_BUILDERS.resolve(STAGE3_DELTA_BUILD_POLICY_ID) is build_stage3_delta_snapshot


def test_builder_accepts_a_strict_subset_of_the_permitted_roster() -> None:
    snapshot = build_stage3_delta_snapshot(_spec(), rows=(_delta_row(),))
    assert snapshot.builder_policy_id == STAGE3_DELTA_BUILD_POLICY_ID
    assert snapshot.source_sample_ids == ("synthetic-row-1",)
    assert len(snapshot.values) == 1
    value = snapshot.values[0]
    assert value.associated_facet_ids == ("stage3-delta-target:alarm_set",)
    assert value.task_target == "exemplar-note:alarm_set"
    assert value.prior_score == pytest.approx(0.4)
    facet = snapshot.facets[0]
    assert facet.dimension == STAGE3_DELTA_DIMENSION
    assert facet.facet_id == "stage3-delta-target:alarm_set"


def test_builder_refuses_a_source_outside_the_permitted_roster() -> None:
    with pytest.raises(RailsError, match="subset"):
        build_stage3_delta_snapshot(
            _spec(), rows=(_delta_row(sample_id="not-permitted"),)
        )


def test_builder_refuses_a_forbidden_sample_id() -> None:
    with pytest.raises(RailsError, match="forbidden"):
        build_stage3_delta_snapshot(
            _spec(),
            rows=(_delta_row(),),
            forbidden_sample_ids=frozenset({"synthetic-row-1"}),
        )


def test_builder_refuses_a_malformed_value_id() -> None:
    row = _delta_row()
    row["value_id"] = "not-a-delta-id"
    with pytest.raises(RailsError, match="delta:<iteration>"):
        build_stage3_delta_snapshot(_spec(), rows=(row,))


def test_builder_refuses_a_duplicate_value_id() -> None:
    row = _delta_row()
    with pytest.raises(RailsError, match="duplicate value_id"):
        build_stage3_delta_snapshot(_spec(), rows=(row, dict(row)))


def test_builder_mints_one_facet_per_distinct_target_across_rows() -> None:
    rows = (
        _delta_row(statement="First statement.", target="alarm_set", sample_id="synthetic-row-1"),
        _delta_row(statement="Second statement.", target="alarm_set", sample_id="synthetic-row-2"),
        _delta_row(statement="Third statement.", target="play_music", sample_id="synthetic-row-3"),
    )
    snapshot = build_stage3_delta_snapshot(_spec(), rows=rows)
    assert len(snapshot.values) == 3
    facet_ids = {facet.facet_id for facet in snapshot.facets}
    assert facet_ids == {"stage3-delta-target:alarm_set", "stage3-delta-target:play_music"}
    alarm_facet = next(f for f in snapshot.facets if f.facet_id == "stage3-delta-target:alarm_set")
    assert set(alarm_facet.source_sample_ids) == {"synthetic-row-1", "synthetic-row-2"}


# ---------------------------------------------------------------------------
# The curation CLI: parsing.
# ---------------------------------------------------------------------------


class _FakeSample:
    def __init__(self, sample_index: int) -> None:
        self.sample_index = sample_index


class _FakePair:
    def __init__(self, sample_id: str, best: int, worst: int) -> None:
        self.sample_id = sample_id
        self.best = _FakeSample(best)
        self.worst = _FakeSample(worst)


def test_build_candidate_rows_drops_illegal_statements_and_counts() -> None:
    outputs = [
        {
            "sample_id": "row-1",
            "response_text": "DELTA-KIND: exemplar-note\nTARGET: alarm_set\nSTATEMENT: A legal one.\n",
            "disagreement": 0.5,
        },
        {
            "sample_id": "row-2",
            "response_text": "DELTA-KIND: not-a-kind\nTARGET: t\nSTATEMENT: Illegal kind.\n",
            "disagreement": 0.2,
        },
        {"sample_id": "row-3", "response_text": "garbage, no keys at all", "disagreement": 0.1},
        {"sample_id": "row-unmatched", "response_text": "irrelevant", "disagreement": 0.1},
    ]
    pairs_by_sample = {
        "row-1": _FakePair("row-1", best=2, worst=4),
        "row-2": _FakePair("row-2", best=0, worst=1),
        "row-3": _FakePair("row-3", best=0, worst=3),
    }
    rows, counts = build_candidate_rows(
        advantage_outputs=outputs,
        pairs_by_sample=pairs_by_sample,
        run_id="SAEA-TEST-RUN",
        iteration=1,
    )
    assert counts == {"total": 4, "legal": 1, "illegal": 2, "unmatched_pair": 1}
    assert len(rows) == 1
    row = rows[0]
    assert row["value_id"].startswith("delta:1:")
    assert row["provenance_refs"] == ["advantage:SAEA-TEST-RUN:row-1:2:4"]
    assert row["source_sample_ids"] == ["row-1"]
    assert row["task_target"] == "exemplar-note:alarm_set"
    assert row["prior_score"] == pytest.approx(0.5)


def test_build_candidate_rows_requires_numeric_disagreement() -> None:
    outputs = [
        {
            "sample_id": "row-1",
            "response_text": "DELTA-KIND: exemplar-note\nTARGET: t\nSTATEMENT: ok.\n",
        }
    ]
    with pytest.raises(Stage3DeltaStoreError, match="disagreement"):
        build_candidate_rows(
            advantage_outputs=outputs,
            pairs_by_sample={"row-1": _FakePair("row-1", 0, 1)},
            run_id="SAEA-TEST-RUN",
            iteration=1,
        )


# ---------------------------------------------------------------------------
# curate(): append-only, dedup rule, provenance merge, predecessor verbatim.
# ---------------------------------------------------------------------------


def test_curate_keeps_predecessor_rows_verbatim_and_appends_new_ones() -> None:
    predecessor = [_delta_row(statement="Predecessor statement one.", sample_id="row-a", iteration=1)]
    new = [_delta_row(statement="Brand new statement two.", sample_id="row-b", iteration=2)]
    survivors, counts = curate(predecessor_rows=predecessor, candidate_rows=new)
    assert counts["predecessor"] == 1
    assert counts["new_accepted"] == 1
    assert len(survivors) == 2
    predecessor_survivor = next(row for row in survivors if row["value_id"] == predecessor[0]["value_id"])
    assert predecessor_survivor == predecessor[0]


def test_curate_drops_an_exact_duplicate_and_merges_provenance() -> None:
    predecessor = [_delta_row(statement="Repeated statement text.", sample_id="row-a", iteration=1)]
    duplicate = [_delta_row(statement="Repeated statement text.", sample_id="row-b", iteration=2)]
    survivors, counts = curate(predecessor_rows=predecessor, candidate_rows=duplicate)
    assert counts["exact_duplicate"] == 1
    assert len(survivors) == 1
    survivor = survivors[0]
    assert survivor["value_id"] == predecessor[0]["value_id"]  # predecessor id kept
    assert set(survivor["provenance_refs"]) == set(
        predecessor[0]["provenance_refs"]
    ) | set(duplicate[0]["provenance_refs"])
    assert set(survivor["source_sample_ids"]) == {"row-a", "row-b"}


def test_curate_drops_a_near_duplicate_by_token_jaccard() -> None:
    predecessor = [
        _delta_row(
            statement="the better answer used the correct slot value for time",
            sample_id="row-a",
            iteration=1,
        )
    ]
    near = [
        _delta_row(
            statement="the better answer used the correct slot value for date",
            sample_id="row-b",
            iteration=2,
        )
    ]
    survivors, counts = curate(predecessor_rows=predecessor, candidate_rows=near, jaccard_threshold=0.8)
    assert counts["near_duplicate"] == 1
    assert len(survivors) == 1


def test_curate_keeps_two_dissimilar_new_rows_separate() -> None:
    new = [
        _delta_row(statement="First distinct statement about alarms.", sample_id="row-a", target="alarm_set"),
        _delta_row(statement="Second distinct statement about music playback.", sample_id="row-b", target="play_music"),
    ]
    survivors, counts = curate(predecessor_rows=(), candidate_rows=new)
    assert counts["new_accepted"] == 2
    assert len(survivors) == 2


def test_load_predecessor_rows_accepts_the_literal_none() -> None:
    assert load_predecessor_rows("none") == []
    assert load_predecessor_rows(None) == []


def test_load_predecessor_rows_reads_an_authored_document(tmp_path) -> None:
    row = _delta_row()
    document = {"schema": "saea-stage3-authored-deltas-v1", "iteration": 1, "rows": [row]}
    path = tmp_path / "predecessor.json"
    path.write_text(json.dumps(document), encoding="utf-8", newline="\n")
    rows = load_predecessor_rows(str(path))
    assert rows == [row]


# ---------------------------------------------------------------------------
# End-to-end CLI: main() writes a valid authored document.
# ---------------------------------------------------------------------------


def test_main_writes_authored_document_and_reports_counts(tmp_path, capsys) -> None:
    """The pre-S3-4s (v1) curation path, still reachable and unchanged.

    S3-4s made ``--schema-version 2`` the DEFAULT (node-targeted rows, the
    multi-block parser, the containment rule), so this test now names the v1
    path explicitly. Everything it asserts is what it asserted before.
    """

    pairs_document = {
        "rows": [
            {
                "sample_id": "row-1",
                "best": {"sample_index": 2, "response_text_sha256": "a" * 64},
                "worst": {"sample_index": 4, "response_text_sha256": "b" * 64},
            }
        ]
    }
    pairs_path = tmp_path / "pairs.json"
    pairs_path.write_text(json.dumps(pairs_document), encoding="utf-8", newline="\n")

    outputs_path = tmp_path / "outputs.jsonl"
    outputs_path.write_text(
        json.dumps(
            {
                "sample_id": "row-1",
                "response_text": (
                    "DELTA-KIND: exemplar-note\nTARGET: alarm_set\n"
                    "STATEMENT: The better answer named the exact device.\n"
                ),
                "disagreement": 0.6,
            }
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    out_path = tmp_path / "authored.json"

    exit_code = main(
        [
            "--advantage-outputs", str(outputs_path),
            "--pairs", str(pairs_path),
            "--repo-root", str(tmp_path),
            "--predecessor", "none",
            "--iteration", "1",
            "--run-id", "SAEA-TEST-RUN",
            "--out-authored", str(out_path),
            "--schema-version", "1",
        ]
    )
    assert exit_code == 0
    document = json.loads(out_path.read_bytes())
    assert document["schema"] == "saea-stage3-authored-deltas-v1"
    assert len(document["rows"]) == 1
    stdout = capsys.readouterr().out
    report = json.loads(stdout)
    assert report["survivor_count"] == 1
    assert report["parse"]["legal"] == 1
    # Console output must never carry the statement text, only ids/counts/hashes.
    assert "device" not in stdout


# ---------------------------------------------------------------------------
# Release identity: prepare_semantic_knowledge_store end to end.
# ---------------------------------------------------------------------------


def _write(path: Path, document: object) -> dict[str, str]:
    raw = canonical_bytes(document)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return {"relpath": path.name, "sha256": hashlib.sha256(raw).hexdigest()}


def _synthetic_roster(ids: tuple[str, ...], *, roster_id: str, roster_role: str = "construction") -> dict[str, object]:
    identity = split_identity_hash(prefixed("slurp", ids))
    return {
        "schema": "saea-roster-receipt-v1",
        "roster_id": roster_id,
        "carrier_lock_key": "slurp",
        "split_role": "discovery",
        "roster_role": roster_role,
        "items": [{"sample_id": sample_id, "stratum": "synthetic"} for sample_id in ids],
        "split_identity_hash": identity,
    }


def test_release_through_prepare_semantic_knowledge_store(tmp_path) -> None:
    repo_root, data_root = tmp_path / "repo", tmp_path / "data"
    repo_root.mkdir()
    data_root.mkdir()
    support_identity = split_identity_hash(prefixed("slurp", ("row-a", "row-b", "row-c")))
    scope_pin = _write(
        repo_root / "scope.json", _synthetic_roster(("row-a", "row-b", "row-c"), roster_id="scope")
    )
    # The stage3-deltas store's own PERMITTED roster is the whole construction
    # roster (three ids); authored rows use only TWO of them -- proving the
    # builder's subset relaxation actually composes with the shared
    # preparation orchestrator, unlike the exact-match authored builders.
    permitted_pin = _write(
        repo_root / "permitted.json",
        _synthetic_roster(("row-a", "row-b", "row-c"), roster_id="permitted"),
    )
    forbidden_pin = _write(
        repo_root / "forbidden.json",
        _synthetic_roster(("forbidden-1",), roster_id="forbidden", roster_role="evaluation"),
    )
    rows = [
        _delta_row(statement="Alpha statement.", target="alarm_set", sample_id="row-a"),
        _delta_row(statement="Beta statement.", target="play_music", sample_id="row-b"),
    ]
    source = {
        "schema": "saea-authored-semantic-knowledge-source-v1",
        "builder_policy_id": STAGE3_DELTA_BUILD_POLICY_ID,
        "source_split_identity_hash": support_identity,
        "rows": rows,
    }
    source_pin = _write(data_root / "authored-stage3-deltas-v1.json", source)
    registration = {
        "schema": "saea-authored-semantic-knowledge-preparation-v1",
        "registration_id": "SYNTHETIC-STAGE3-DELTAS-V1",
        "carrier_lock_key": "slurp",
        "source_partition_role": "train",
        "source_split_identity_hash": support_identity,
        "builder_policy_id": STAGE3_DELTA_BUILD_POLICY_ID,
        "store_id": "stage3-deltas",
        "store_role": "stage3-deltas",
        "authored_source": {**source_pin, "root": "data"},
        "construction_scope": scope_pin,
        "permitted_roster": permitted_pin,
        "forbidden_rosters": [forbidden_pin],
        "output_namespace": "knowledge/slurp/semantic/stage3-deltas-v1",
    }
    registration_path = repo_root / "registration.json"
    registration_path.write_bytes(canonical_bytes(registration))

    result = prepare_semantic_knowledge_store(
        registration_path, repo_root=repo_root, data_root=data_root
    )

    assert result["cache"] == "cold"
    completion = result["completion"]
    assert completion["contacts"] == {"model": 0, "tool": 0, "scorer": 0}
    binding = load_knowledge_store_binding(
        {
            "knowledge_stores": {
                "stage3-deltas": {
                    "store_role": "stage3-deltas",
                    "snapshot": completion["snapshot"],
                    "release": completion["release"],
                }
            }
        },
        data_root=data_root,
    )
    assert binding.store_ids == ("stage3-deltas",)
    snapshot = binding.snapshot_for("stage3-deltas")
    assert snapshot.source_sample_ids == ("row-a", "row-b")
    assert snapshot.builder_policy_id == STAGE3_DELTA_BUILD_POLICY_ID
    assert len(snapshot.values) == 2
