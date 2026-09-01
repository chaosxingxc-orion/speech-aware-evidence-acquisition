from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import runpy
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.analysis.a2t_contract_preserving_cohort import (
    CohortError,
    SELECTION_NAMESPACE,
    TIERS,
    build_receipt,
    query_block,
    select_block_disjoint,
)


@dataclass(frozen=True)
class Candidate:
    sample_id: str
    media_relpath: str
    audio_seconds: float = 1.0
    audio_sha256: str = "a" * 64


REPO = Path(__file__).resolve().parents[2]
LAUNCHER = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-01-a2t-contract-preserving-cascade-104-v2/launcher"
    / "materialize_cohort.py"
)


def _candidate(tier: str, item: int, query: int) -> Candidate:
    return Candidate(
        sample_id=f"{tier}:{item:06d}",
        media_relpath=f"datasets/audio2tool/{tier}_audios/query_{query:05d}/voice.wav",
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_materializer_launcher_imports_against_public_package_surface(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")
    monkeypatch.setenv("PYTHONPATH", str(REPO / "src"))

    namespace = runpy.run_path(str(LAUNCHER), run_name="_assembly_check")

    assert namespace["require_clean_study_repo"]
    assert namespace["main"]


def test_real_cpv2_receipt_and_configs_are_hash_bound() -> None:
    receipt_path = REPO / "docs/receipts/a2t/A2T-CPV2-104.json"
    excluded_path = REPO / "docs/receipts/a2t/A2T-G1-104.json"
    dataset_path = REPO / "configs/dataset/audio2tool-cpv2-104.json"
    experiment_path = (
        REPO
        / "configs/experiment"
        / "a2t-training-free-contract-preserving-cascade-104-v2.json"
    )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    excluded = json.loads(excluded_path.read_text(encoding="utf-8"))
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    experiment = json.loads(experiment_path.read_text(encoding="utf-8"))
    items = receipt["items"]
    blocks = {item["query_block"] for item in items}
    excluded_blocks = {
        query_block(item["tier"], item["media_relpath"])
        for item in excluded["items"]
    }

    assert receipt["count"] == len(items) == 104
    assert receipt["selection_namespace"] == SELECTION_NAMESPACE
    assert receipt["strata_counts"] == {tier: 13 for tier in TIERS}
    assert len(blocks) == 104
    assert blocks.isdisjoint(excluded_blocks)
    assert all(
        item["selection_rank_sha256"]
        == hashlib.sha256(
            f"{SELECTION_NAMESPACE}\0{item['sample_id']}".encode()
        ).hexdigest()
        for item in items
    )
    assert dataset["a2t_cpv2_subset_receipt_sha256"] == _sha256(receipt_path)
    assert dataset["a2t_cpv2_split_identity_hash"] == receipt["split_identity_hash"]
    assert dataset["a2t_cpv2_run_identity_hash"] == receipt["run_identity_hash"]
    assert dataset["a2t_cpv2_excluded_receipt_sha256"] == _sha256(excluded_path)
    assert dataset["a2t_cpv2_count"] == receipt["count"]
    assert dataset["a2t_cpv2_audio_seconds_total"] == receipt["audio_seconds_total"]
    population = experiment["population"]
    assert population["receipt_status"] == "MATERIALIZED_AND_HASH_PINNED"
    assert population["receipt_sha256"] == _sha256(receipt_path)
    assert population["split_identity_hash"] == receipt["split_identity_hash"]
    assert population["run_identity_hash"] == receipt["run_identity_hash"]


def test_query_block_is_tier_scoped_and_refuses_an_ambiguous_path() -> None:
    assert (
        query_block(
            "tier1_direct",
            "datasets/audio2tool/tier1_direct_audios/query_00037/voice.wav",
        )
        == "tier1_direct:query-00037"
    )
    with pytest.raises(CohortError, match="exactly one query block"):
        query_block("tier1_direct", "no-query-here.wav")
    with pytest.raises(CohortError, match="exactly one query block"):
        query_block("tier1_direct", "query_00001/query_00002/voice.wav")
    with pytest.raises(CohortError, match="tier must be non-empty"):
        query_block("", "query_00001/voice.wav")
    with pytest.raises(CohortError, match="media path must be non-empty"):
        query_block("tier1_direct", "")


@pytest.mark.parametrize(
    ("candidate", "message"),
    (
        (SimpleNamespace(sample_id="bad", media_relpath="query_00001/a.wav"), "tier:integer"),
        (SimpleNamespace(sample_id="tier:", media_relpath="query_00001/a.wav"), "tier:integer"),
        (
            SimpleNamespace(
                sample_id="tier:1",
                media_relpath="",
                audio_seconds=1.0,
                audio_sha256="a" * 64,
            ),
            "media path",
        ),
        (
            SimpleNamespace(
                sample_id="tier:1",
                media_relpath="query_00001/a.wav",
                audio_seconds=True,
                audio_sha256="a" * 64,
            ),
            "seconds must be numeric",
        ),
        (
            SimpleNamespace(
                sample_id="tier:1",
                media_relpath="query_00001/a.wav",
                audio_seconds=float("inf"),
                audio_sha256="a" * 64,
            ),
            "finite and positive",
        ),
        (
            SimpleNamespace(
                sample_id="tier:1",
                media_relpath="query_00001/a.wav",
                audio_seconds=1.0,
                audio_sha256="UPPER",
            ),
            "audio SHA-256",
        ),
    ),
)
def test_selection_rejects_malformed_runtime_identity_fields(
    candidate: object, message: str
) -> None:
    with pytest.raises(CohortError, match=message):
        select_block_disjoint(
            (candidate,), (), tiers=("tier",), per_tier=1, namespace="fixture"
        )


def test_selection_accepts_nested_audio_reference() -> None:
    candidate = SimpleNamespace(
        sample_id="tier:1",
        media_relpath="query_00001/a.wav",
        audio_seconds=1.0,
        audio_ref=SimpleNamespace(sha256="a" * 64),
    )

    selected = select_block_disjoint(
        (candidate,), (), tiers=("tier",), per_tier=1, namespace="fixture"
    )

    assert selected[0].audio_sha256 == "a" * 64


@pytest.mark.parametrize(
    ("kwargs", "message"),
    (
        ({"tiers": ()}, "tiers must be unique"),
        ({"tiers": ("tier", "tier")}, "tiers must be unique"),
        ({"per_tier": True}, "per_tier must be a positive integer"),
        ({"namespace": ""}, "namespace must be non-empty"),
    ),
)
def test_selection_rejects_invalid_selector_configuration(
    kwargs: dict[str, object], message: str
) -> None:
    with pytest.raises(CohortError, match=message):
        select_block_disjoint((), (), **kwargs)


def test_selection_is_block_disjoint_balanced_and_input_order_invariant() -> None:
    parent = tuple(
        _candidate(tier, tier_index * 100 + item, item // 2)
        for tier_index, tier in enumerate(("tier1", "tier2"), start=1)
        for item in range(10)
    )
    excluded = (
        _candidate("tier1", 999001, 0),
        _candidate("tier2", 999002, 1),
    )

    selected = select_block_disjoint(
        parent,
        excluded,
        tiers=("tier1", "tier2"),
        per_tier=3,
        namespace="fixture-v2",
    )
    reversed_selected = select_block_disjoint(
        tuple(reversed(parent)),
        tuple(reversed(excluded)),
        tiers=("tier1", "tier2"),
        per_tier=3,
        namespace="fixture-v2",
    )

    assert [item.sample_id for item in selected] == [
        item.sample_id for item in reversed_selected
    ]
    assert {item.tier for item in selected} == {"tier1", "tier2"}
    assert sum(item.tier == "tier1" for item in selected) == 3
    assert sum(item.tier == "tier2" for item in selected) == 3
    assert len({item.query_block for item in selected}) == 6
    assert not {item.query_block for item in selected} & {
        "tier1:query-00000",
        "tier2:query-00001",
    }


def test_selection_refuses_duplicate_id_and_insufficient_unique_blocks() -> None:
    duplicate = _candidate("tier1", 1, 1)
    with pytest.raises(CohortError, match="duplicate parent sample"):
        select_block_disjoint(
            (duplicate, duplicate),
            (),
            tiers=("tier1",),
            per_tier=1,
            namespace="fixture",
        )
    with pytest.raises(CohortError, match="needs 2 unique blocks"):
        select_block_disjoint(
            (_candidate("tier1", 1, 1), _candidate("tier1", 2, 1)),
            (),
            tiers=("tier1",),
            per_tier=2,
            namespace="fixture",
        )


def test_receipt_binds_both_identity_conventions_and_selection_proof() -> None:
    selected = select_block_disjoint(
        (
            _candidate("tier1", 11, 11),
            _candidate("tier1", 12, 12),
            _candidate("tier2", 21, 21),
            _candidate("tier2", 22, 22),
        ),
        (),
        tiers=("tier1", "tier2"),
        per_tier=1,
        namespace="fixture-v2",
    )
    receipt = build_receipt(
        selected,
        split_name="A2T-FIXTURE-2",
        namespace="fixture-v2",
        parent_receipt="parent.json",
        parent_receipt_sha256="b" * 64,
        parent_split_identity_hash="c" * 64,
        excluded_receipt="excluded.json",
        excluded_receipt_sha256="d" * 64,
        excluded_query_blocks=("tier1:query-00001",),
        expected_tiers=("tier1", "tier2"),
        per_tier=1,
    )

    assert receipt["count"] == 2
    assert receipt["audio_seconds_total"] == 2.0
    assert len(receipt["split_identity_hash"]) == 64
    assert len(receipt["run_identity_hash"]) == 64
    assert receipt["split_identity_hash"] != receipt["run_identity_hash"]
    assert receipt["selection_proof"]["excluded_query_block_count"] == 1
    assert receipt["selection_proof"]["selected_query_block_count"] == 2
    assert receipt["selection_proof"]["query_block_overlap_count"] == 0
    assert receipt["strata_counts"] == {"tier1": 1, "tier2": 1}
    assert all(len(item["selection_rank_sha256"]) == 64 for item in receipt["items"])


def test_receipt_rejects_allocation_duplicates_overlap_and_bad_hashes() -> None:
    selected = select_block_disjoint(
        (_candidate("tier1", 11, 11),),
        (),
        tiers=("tier1",),
        per_tier=1,
        namespace="fixture-v2",
    )
    base = {
        "split_name": "A2T-FIXTURE-1",
        "namespace": "fixture-v2",
        "parent_receipt": "parent.json",
        "parent_receipt_sha256": "b" * 64,
        "parent_split_identity_hash": "c" * 64,
        "excluded_receipt": "excluded.json",
        "excluded_receipt_sha256": "d" * 64,
        "excluded_query_blocks": (),
        "expected_tiers": ("tier1",),
        "per_tier": 1,
    }
    with pytest.raises(CohortError, match="frozen tier allocation"):
        build_receipt(selected, **(base | {"expected_tiers": ("tier1", "tier2")}))
    with pytest.raises(CohortError, match="unique by sample"):
        build_receipt(selected * 2, **(base | {"per_tier": 2}))
    with pytest.raises(CohortError, match="overlaps an excluded"):
        build_receipt(
            selected,
            **(base | {"excluded_query_blocks": (selected[0].query_block,)}),
        )
    with pytest.raises(CohortError, match="parent receipt SHA-256"):
        build_receipt(selected, **(base | {"parent_receipt_sha256": "BAD"}))
