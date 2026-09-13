"""Tests for governed SLURP semantic-authoring support preparation."""

from __future__ import annotations

import hashlib
import json

from speech_aware_evidence_acquisition.core.preparation import canonical_bytes
from speech_aware_evidence_acquisition.core.roster import (
    RosterItem,
    freeze_roster,
    write_roster,
)
from speech_aware_evidence_acquisition.core.semantic_authoring_support import (
    prepare_slurp_semantic_authoring_support,
    select_semantic_authoring_support,
)
from speech_aware_evidence_acquisition.rails.knowledge_build import (
    KbEntityMention,
    KbRow,
    KbSourceToken,
)


def _row(number: int, intent: str, entity_types=()) -> KbRow:
    utterance = str(number)
    sample_ids = (f"slurp:train:{number:06d}:recording-a", f"slurp:train:{number:06d}:recording-b")
    mentions = tuple(
        KbEntityMention(entity_type, (index,), f"filler-{index}")
        for index, entity_type in enumerate(entity_types, start=1)
    )
    return KbRow(
        utterance_id=utterance,
        content=f"English support sentence {number}.",
        scenario="scenario",
        action=intent,
        intent=intent,
        entity_types=tuple(sorted(set(entity_types))),
        entity_fillers={},
        sample_ids=sample_ids,
        speaker_by_sample_id={sample_id: "speaker" for sample_id in sample_ids},
        media_relpath_by_sample_id={sample_id: "unused.flac" for sample_id in sample_ids},
        source_tokens=(KbSourceToken(1, "English"), KbSourceToken(2, "support")),
        entity_mentions=mentions,
    )


def test_selection_is_hash_ordered_bounded_and_deduplicates_slot_rows():
    rows = tuple(
        _row(index, "intent-a", ("date", "time")) for index in range(1, 12)
    ) + (_row(20, "intent-b"),)

    result = select_semantic_authoring_support(
        rows, intent_limit=8, slot_pair_limit=3, policy_id="semantic-authoring-v1"
    )

    assert len(result.intent_rows) == 9
    assert len([row for row in result.intent_rows if row.intent == "intent-a"]) == 8
    assert len(result.slot_rows) == 3
    assert all(
        set(result.slot_pairs_by_utterance[row.utterance_id])
        == {"intent-a:date", "intent-a:time"}
        for row in result.slot_rows
    )
    assert result.intent_rows == select_semantic_authoring_support(
        tuple(reversed(rows)),
        intent_limit=8,
        slot_pair_limit=3,
        policy_id="semantic-authoring-v1",
    ).intent_rows


def test_selection_preserves_all_recordings_tokens_mentions_and_zero_slot_intent():
    zero = _row(1, "intent-zero")
    slotted = _row(2, "intent-slot", ("date",))

    result = select_semantic_authoring_support(
        (zero, slotted),
        intent_limit=8,
        slot_pair_limit=3,
        policy_id="semantic-authoring-v1",
    )
    rendered = result.render_row(zero)

    assert rendered["recording_ids"] == list(zero.sample_ids)
    assert rendered["tokens"] == [
        {"token_id": 1, "surface": "English"},
        {"token_id": 2, "surface": "support"},
    ]
    assert rendered["entities"] == []
    assert [row.utterance_id for row in result.slot_rows] == ["2"]


def test_excluded_utterance_removes_every_recording_before_selection():
    retained = _row(1, "intent-a", ("date",))
    excluded = _row(2, "intent-a", ("date",))

    result = select_semantic_authoring_support(
        (retained, excluded),
        intent_limit=8,
        slot_pair_limit=3,
        policy_id="semantic-authoring-v1",
        forbidden_sample_ids={excluded.sample_ids[1]},
    )

    assert result.eligible_rows == (retained,)
    assert set(result.eligible_sample_ids) == set(retained.sample_ids)
    assert not set(excluded.sample_ids) & set(result.eligible_sample_ids)


def test_registered_preparation_publishes_source_bound_support_and_rosters(
    tmp_path, monkeypatch
):
    repo_root = tmp_path / "repo"
    data_root = tmp_path / "data"
    repo_root.mkdir()
    data_root.mkdir()
    retained = _row(1, "intent-a", ("date",))
    excluded = _row(2, "intent-b", ("time",))

    def write_pin(path, value):
        raw = value if isinstance(value, bytes) else canonical_bytes(value)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        return {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest()}

    lock_pin = write_pin(tmp_path / "datasets.lock.json", b"{}")
    loader_pin = write_pin(tmp_path / "loader.py", b"# synthetic loader\n")
    pool_receipt_pin = write_pin(tmp_path / "pool.json", {"registered": True})
    forbidden = freeze_roster(
        carrier_lock_key="slurp",
        candidates=(RosterItem(excluded.sample_ids[0], "intent-b"),),
        per_stratum={"intent-b": 1},
        seed=0,
        split_role="discovery",
        roster_id="fold-a",
        roster_role="construction",
    )
    forbidden_path = tmp_path / "fold-a.json"
    write_roster(forbidden, forbidden_path)
    forbidden_pin = {
        "path": str(forbidden_path),
        "sha256": hashlib.sha256(forbidden_path.read_bytes()).hexdigest(),
    }
    source_identity = hashlib.sha256(
        "\n".join(sorted(retained.sample_ids)).encode("utf-8")
    ).hexdigest()
    snapshot_content_sha = "c" * 64
    snapshot = {
        "source_partition_role": "train",
        "source_split_identity_hash": source_identity,
        "snapshot_sha256": snapshot_content_sha,
        "source_sample_ids": list(retained.sample_ids),
        "values": [
            {
                "value_id": "value:1",
                "source_sample_ids": list(retained.sample_ids),
                "task_target": retained.intent,
            }
        ],
    }
    snapshot_pin = write_pin(tmp_path / "snapshot.json", snapshot)
    snapshot_pin["content_sha256"] = snapshot_content_sha
    registration = {
        "schema": "saea-semantic-authoring-read-registration-v1",
        "registration_id": "SYNTHETIC-SUPPORT",
        "data_root": str(data_root),
        "lock": lock_pin,
        "loader_sources": [loader_pin],
        "pool_receipt": pool_receipt_pin,
        "pool_snapshot": snapshot_pin,
        "forbidden_rosters": [forbidden_pin],
        "expected_pool": {
            "utterances": 1,
            "recordings": 2,
            "intents": 1,
            "entity_types": 1,
            "source_split_identity_hash": source_identity,
        },
        "selection": {"registered": True},
        "outputs": {"namespace": "prepared/SYNTHETIC-SUPPORT"},
    }
    registration_path = repo_root / "registration.json"
    registration_path.write_bytes(canonical_bytes(registration))
    config = {
        "schema": "saea-slurp-semantic-authoring-support-config-v1",
        "registration": {
            "relpath": "registration.json",
            "sha256": hashlib.sha256(registration_path.read_bytes()).hexdigest(),
        },
        "selection_policy_id": "semantic-authoring-v1",
    }
    config_path = repo_root / "config.json"
    config_path.write_bytes(canonical_bytes(config))
    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.core.semantic_authoring_support.load_lock",
        lambda _path: {},
    )
    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.core.semantic_authoring_support.slurp_kb_rows",
        lambda _lock, _root: (retained, excluded),
    )
    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.core.semantic_authoring_support.governed_train_jsonl_relpath",
        lambda _lock, _root: "datasets/slurp/metadata/train.jsonl",
    )

    result = prepare_slurp_semantic_authoring_support(
        config_path, repo_root=repo_root, data_root=data_root
    )

    assert result["aggregate"]["pool"]["utterances"] == 1
    assert result["aggregate"]["excluded_utterances"] == 1
    assert result["aggregate"]["excluded_recordings"] == 2
    namespace = data_root / "prepared/SYNTHETIC-SUPPORT"
    support = json.loads((namespace / "support.json").read_text())
    assert support["output"]["intent_support"][0]["recording_ids"] == list(
        retained.sample_ids
    )
    assert (namespace / "outer-construction-roster.json").is_file()
    assert (namespace / "intent-support-construction-roster.json").is_file()
    assert (namespace / "slot-support-construction-roster.json").is_file()
