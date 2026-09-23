"""The R01-excluded ``train-exemplars`` store clears the BUILD/USE guard.

Cell ROLL-1 (Stage-3 S3-2) flies a TRAIN construction roster as its AgentLoop
QUERY population, and ``rails.runner.run_speech_native_agent_loop`` refuses
any run whose query samples intersect the bound snapshot's own
``source_sample_ids``. These tests pin the exclusion mechanism that removes
that intersection, on a synthetic corpus: model-free, filesystem-free except
for ``tmp_path``, zero contacts.

The property that matters most is UTTERANCE-level: a roster names ONE
recording, and the excluded snapshot must lose every recording of that
utterance (the ``-headset`` sibling included), because a facet is built per
utterance and carries all of its recordings as ``source_sample_ids``.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.rails.knowledge_build import (
    VIEW_ANNOTATED_EXEMPLARS,
    KbRow,
    KnowledgeBuildSpec,
    build_knowledge_snapshot,
)
from speech_aware_evidence_acquisition.rails.knowledge_stores import (
    load_knowledge_store_binding,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO_ROOT / "scripts" / "build_slurp_stage3_r01_excluded_exemplar_store.py"
_SPEC = importlib.util.spec_from_file_location("r01_excluded_store_under_test", _SCRIPT)
builder = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(builder)

#: The query roster: three recordings, one of them a sibling of a row whose
#: other recording is NOT named. Only ``utterance_id`` 3 is named twice.
QUERY_ROSTER = (
    "slurp:train:1:audio-1",
    "slurp:train:3:audio-3",
)


def _row(utterance_id: str, *, words: str, headset: bool = False) -> KbRow:
    sample_ids = [f"slurp:train:{utterance_id}:audio-{utterance_id}"]
    if headset:
        sample_ids.append(f"slurp:train:{utterance_id}:audio-{utterance_id}-headset")
    sample_ids = tuple(sample_ids)
    return KbRow(
        utterance_id=utterance_id,
        content=words,
        scenario="alarm",
        action="set",
        intent="alarm_set",
        entity_types=("time",),
        entity_fillers={"time": ("six",)},
        sample_ids=sample_ids,
        speaker_by_sample_id={sample_id: "FO-001" for sample_id in sample_ids},
        media_relpath_by_sample_id={
            sample_id: f"datasets/slurp/{sample_id.rsplit(':', 1)[-1]}.flac"
            for sample_id in sample_ids
        },
    )


def _rows() -> tuple[KbRow, ...]:
    return (
        # Named by the roster; carries a sibling recording the roster does NOT name.
        _row("1", words="wake me at six", headset=True),
        _row("2", words="wake me at seven"),
        # Named by the roster; single recording.
        _row("3", words="wake me at eight", headset=True),
        _row("4", words="wake me at nine"),
        _row("5", words="wake me at ten", headset=True),
    )


def _build(rows) -> object:
    return build_knowledge_snapshot(
        KnowledgeBuildSpec(
            carrier_lock_key="slurp",
            dimensions=("content",),
            view=VIEW_ANNOTATED_EXEMPLARS,
        ).validate(),
        rows=rows,
        forbidden_sample_ids=frozenset(),
    )


def _excluded_rows(rows, excluded_ids):
    """The CLI's own selection expression (pure, model-free, per utterance)."""

    return tuple(row for row in rows if not (set(row.sample_ids) & set(excluded_ids)))


def _write_roster(path: Path, roster_id: str, ids, *, key: str = "sample_id") -> str:
    document = {
        "roster_id": roster_id,
        "split_identity_hash": hashlib.sha256(roster_id.encode()).hexdigest(),
        "items": [{key: sample_id} for sample_id in ids],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(document, sort_keys=True).encode("utf-8")
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def test_roster_receipts_of_both_item_shapes_union_into_one_exclusion(
    monkeypatch, tmp_path
) -> None:
    """``sample_id`` rosters and ``id``-only probe rosters both resolve, and the
    receipt records each one's NEW contribution, not just its size."""

    pool_sha = _write_roster(tmp_path / "pool.json", "POOL-V1", ("slurp:train:5:audio-5",))
    probe_sha = _write_roster(
        tmp_path / "probe.json", "PROBE-V1", ("slurp:devel:9:audio-9",), key="id"
    )
    query_sha = _write_roster(tmp_path / "query.json", "QUERY-R01", QUERY_ROSTER)
    monkeypatch.setattr(builder, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        builder, "EXCLUDE_ROSTER_RELPATHS", ("pool.json", "probe.json", "query.json")
    )
    monkeypatch.setattr(builder, "R01_ROSTER_RELPATH", "query.json")

    excluded, records = builder._excluded_sample_ids()
    assert excluded == {
        "slurp:train:5:audio-5",
        "slurp:devel:9:audio-9",
        *QUERY_ROSTER,
    }
    assert [record["relpath"] for record in records] == [
        "pool.json", "probe.json", "query.json",
    ]
    assert [record["new_exclusions"] for record in records] == [1, 1, len(QUERY_ROSTER)]
    assert [record["file_sha256"] for record in records] == [pool_sha, probe_sha, query_sha]
    assert builder._roster_sample_ids("query.json") == frozenset(QUERY_ROSTER)


def test_the_exclusion_drops_every_recording_of_a_named_utterance() -> None:
    rows = _rows()
    full = _build(rows)
    excluded = _build(_excluded_rows(rows, QUERY_ROSTER))

    # The refusal this exists to remove, reproduced on the un-excluded store.
    assert set(QUERY_ROSTER) & set(full.source_sample_ids) == set(QUERY_ROSTER)
    # ... and gone from the excluded one.
    assert set(QUERY_ROSTER) & set(excluded.source_sample_ids) == set()
    # Utterance level: the sibling recording the roster never named is gone too.
    assert "slurp:train:1:audio-1-headset" in set(full.source_sample_ids)
    assert "slurp:train:1:audio-1-headset" not in set(excluded.source_sample_ids)
    assert "slurp:train:3:audio-3-headset" not in set(excluded.source_sample_ids)
    # Nothing else moved: a strict subset, two whole utterances lighter.
    assert set(excluded.source_sample_ids) < set(full.source_sample_ids)
    assert len(excluded.facets) == len(full.facets) - 2
    assert len(excluded.values) == len(full.values) - 2


def test_the_excluded_snapshot_carries_a_different_split_identity() -> None:
    rows = _rows()
    full = _build(rows)
    excluded = _build(_excluded_rows(rows, QUERY_ROSTER))
    assert excluded.source_split_identity_hash != full.source_split_identity_hash
    assert excluded.content_hash() != full.content_hash()


def test_the_surviving_values_are_bit_identical_to_the_parent_store() -> None:
    """The rebuild is a pure SELECTION: no facet, value, prior score or
    provenance ref of a surviving utterance changes by a byte."""

    rows = _rows()
    full = _build(rows)
    excluded = _build(_excluded_rows(rows, QUERY_ROSTER))
    parent_facets = {facet.facet_id: facet for facet in full.facets}
    parent_values = {value.value_id: value for value in full.values}
    for facet in excluded.facets:
        assert facet == parent_facets[facet.facet_id]
    for value in excluded.values:
        assert value == parent_values[value.value_id]


def _publish_store(root: Path, store_id: str, snapshot) -> dict[str, object]:
    reldir = f"knowledge/{store_id}"
    source_relpath = f"{reldir}/source.jsonl"
    (root / reldir).mkdir(parents=True, exist_ok=True)
    source_raw = b'{"corpus": "synthetic"}\n'
    (root / source_relpath).write_bytes(source_raw)
    snapshot_relpath = f"{reldir}/snapshot.json"
    (root / snapshot_relpath).write_text(
        json.dumps(snapshot.frozen_json()), encoding="utf-8"
    )
    release = {
        "schema": "saea-knowledge-store-release-v1",
        "store_id": store_id,
        "store_role": store_id,
        "snapshot_sha256": snapshot.content_hash(),
        "source_split_identity_hash": snapshot.source_split_identity_hash,
        "builder_policy_id": snapshot.builder_policy_id,
        "source": {
            "relpath": source_relpath,
            "sha256": hashlib.sha256(source_raw).hexdigest(),
        },
    }
    release_relpath = f"{reldir}/release.json"
    release_raw = json.dumps(release, sort_keys=True).encode("utf-8")
    (root / release_relpath).write_bytes(release_raw)
    return {
        "store_role": store_id,
        "snapshot": {"relpath": snapshot_relpath, "sha256": snapshot.content_hash()},
        "release": {
            "relpath": release_relpath,
            "sha256": hashlib.sha256(release_raw).hexdigest(),
        },
    }


@pytest.mark.parametrize("excluded_store", [False, True])
def test_the_composite_binding_decides_the_runner_overlap(tmp_path, excluded_store) -> None:
    """The guard reads the COMPOSITE snapshot of
    ``load_knowledge_store_binding``, whose ``source_sample_ids`` is the union
    over the composed stores -- so one contaminated store refuses the run."""

    rows = _rows()
    snapshot = _build(_excluded_rows(rows, QUERY_ROSTER) if excluded_store else rows)
    config = {"knowledge_stores": {"train-exemplars": _publish_store(
        tmp_path, "train-exemplars", snapshot
    )}}
    binding = load_knowledge_store_binding(config, data_root=tmp_path)
    composite = binding.composite_snapshot.validate()
    overlap = set(QUERY_ROSTER) & set(composite.source_sample_ids)
    assert (overlap == set()) is excluded_store


def test_both_roll_1_baselines_pin_the_r01_excluded_release() -> None:
    """Wiring regression guard: the committed ROLL-1 fragments must name the
    R01-excluded release, never the whole-pool parent."""

    for name in (
        "slurp-native-stage3-rollout-baseline-v1",
        "slurp-native-stage3-rollout-smoke-4-baseline-v1",
    ):
        document = json.loads(
            (_REPO_ROOT / "configs" / "baseline" / f"{name}.json").read_text(
                encoding="utf-8"
            )
        )
        store = document["knowledge_stores"]["train-exemplars"]
        for pin in ("release", "snapshot"):
            assert store[pin]["relpath"].startswith(
                "knowledge/slurp/saea-kb-distmodel-v1/"
                "size-pool-annotated-exemplars-minus-r01/"
            )
        receipts = {item["relpath"] for item in document["preparation_source_receipts"]}
        assert (
            "docs/receipts/knowledge/"
            "slurp-kb-size-pool-annotated-exemplars-minus-r01.json"
        ) in receipts
