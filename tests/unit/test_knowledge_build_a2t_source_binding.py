"""Source-bound Audio2Tool construction selection over synthetic manifests."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Mapping

import pytest

from speech_aware_evidence_acquisition.rails import knowledge_build_a2t as builder
from speech_aware_evidence_acquisition.rails.errors import RailsError


def _entry(tier: str, item_id: int, query_idx: int) -> dict[str, object]:
    return {
        "id": item_id,
        "tier": tier,
        "query_idx": query_idx,
        "query": f"synthetic request {tier} {query_idx}",
        "user_request": f"synthetic final request {tier} {query_idx}",
        "domain": "smart_home",
        "category": "lighting",
        "tool_id": 2,
        "tool_name": "setLighting",
        "expected_tool_call": "setLighting(deviceId='light_1')",
        "extracted_params": {"deviceId": "light_1"},
        "additional_tool_calls": None,
        "path": f"{tier}_audios/query_{item_id:05d}/turn.wav",
        "duration": 0.5,
        "speaker_id": "synthetic_voice",
    }


def _tier_entries() -> dict[str, list[dict[str, object]]]:
    entries = {
        tier: [_entry(tier, 100 + index, 1000 + index)]
        for index, tier in enumerate(builder.TIERS)
    }
    entries[builder.TIERS[0]].append(_entry(builder.TIERS[0], 999, 1000))
    return entries


def _write_world(
    tmp_path: Path,
    entries_by_tier: Mapping[str, list[dict[str, object]]] | None = None,
) -> tuple[dict[str, object], Path, Path]:
    data_root = tmp_path / "data"
    carrier_dir = data_root / "datasets" / "audio2tool"
    public_dir = carrier_dir / "public"
    entries_by_tier = entries_by_tier or _tier_entries()
    for tier, entries in entries_by_tier.items():
        path = public_dir / f"{tier}_data" / f"{tier}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(entries), encoding="utf-8", newline="")
    carrier_dir.mkdir(parents=True, exist_ok=True)
    (carrier_dir / "tools_registry.csv").write_text(
        "tool_id,domain,category,tool_name,signature,description,"
        "argument_defaults,argument_constraints\n"
        "2,smart_home,lighting,setLighting,setLighting(deviceId),Turns a light on,,,\n",
        encoding="utf-8",
        newline="",
    )
    lock: dict[str, object] = {
        "datasets": [
            {
                "name": "audio2tool",
                "local_subdir": "datasets/audio2tool",
            }
        ]
    }
    return lock, data_root, public_dir


def _write_receipt(
    path: Path,
    inventory: Mapping[str, object],
    *,
    allowed_units: list[dict[str, object]],
    excluded_sample_ids: list[str],
    **overrides: object,
) -> str:
    document: dict[str, object] = {
        "schema": "saea-a2t-construction-selection-v1",
        "source_manifest_sha256_by_tier": inventory[
            "source_manifest_sha256_by_tier"
        ],
        "allowed_units": allowed_units,
        "excluded_sample_ids": excluded_sample_ids,
    }
    document.update(overrides)
    raw = json.dumps(document, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def _unit(inventory: Mapping[str, object], unit_id: str) -> dict[str, object]:
    return next(
        unit for unit in inventory["units"] if unit["unit_id"] == unit_id  # type: ignore[index]
    )


def test_metadata_inventory_is_deterministic_and_target_blind(tmp_path: Path) -> None:
    entries = _tier_entries()
    for tier_entries in entries.values():
        for entry in tier_entries:
            for field in (
                "query",
                "user_request",
                "tool_name",
                "expected_tool_call",
                "path",
                "speaker_id",
            ):
                entry[field] = {"poison": field}
    lock, data_root, _public_dir = _write_world(tmp_path, entries)
    (data_root / "datasets" / "audio2tool" / "tools_registry.csv").unlink()

    first = builder.a2t_metadata_inventory(lock, data_root)
    second = builder.a2t_metadata_inventory(lock, data_root)

    assert first == second
    assert first["item_count"] == 9
    assert first["unit_count"] == 8
    assert tuple(first["source_manifest_sha256_by_tier"]) == builder.TIERS
    assert _unit(first, "tier1_direct:001000") == {
        "unit_id": "tier1_direct:001000",
        "tier": "tier1_direct",
        "query_idx": 1000,
        "sample_ids": ["tier1_direct:000100", "tier1_direct:000999"],
    }
    serialized = json.dumps(first, sort_keys=True)
    assert "poison" not in serialized
    assert all(
        set(unit) == {"unit_id", "tier", "query_idx", "sample_ids"}
        for unit in first["units"]
    )


def test_default_pool_rows_and_report_keep_the_historical_shape(tmp_path: Path) -> None:
    lock, data_root, _public_dir = _write_world(tmp_path)
    rows, report = builder.a2t_pool_rows(lock, data_root)

    assert [row.unit_id for row in rows] == sorted(
        f"{tier}:{1000 + index:06d}" for index, tier in enumerate(builder.TIERS)
    )
    assert rows[0].sample_ids == (
        "tier1_direct:000100",
        "tier1_direct:000999",
    )
    assert report == {
        "pool_items": 9,
        "pool_items_by_tier": {
            tier: 2 if tier == "tier1_direct" else 1 for tier in builder.TIERS
        },
        "pool_units": 8,
        "usable_units": 8,
        "usable_items": 9,
        "quarantined_unit_count": 0,
        "quarantined_units_by_reason": {},
        "quarantined_units": [],
        "registry_tool_count": 1,
        "gold_primary_tool_count": 1,
        "registry_tools_never_gold": [],
    }


def test_selection_filters_poisoned_excluded_targets_before_helpers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    entries = _tier_entries()
    poison = entries[builder.TIERS[1]][0]
    poison.update(
        {
            "query": {"poison": "invocation"},
            "tool_name": {"poison": "gold"},
            "expected_tool_call": {"poison": "gold"},
            "path": {"poison": "media"},
            "duration": {"poison": "media"},
        }
    )
    lock, data_root, _public_dir = _write_world(tmp_path, entries)
    inventory = builder.a2t_metadata_inventory(lock, data_root)
    allowed = _unit(inventory, "tier1_direct:001000")
    receipt_path = tmp_path / "selection.json"
    receipt_sha = _write_receipt(
        receipt_path,
        inventory,
        allowed_units=[
            {"unit_id": allowed["unit_id"], "sample_ids": allowed["sample_ids"]}
        ],
        excluded_sample_ids=["tier2_parametric:000101"],
    )
    original_text = builder._unit_text
    original_gold = builder.expected_tool_calls_for_entry
    original_media = builder._entry_media

    def reject_poison_text(tier: str, entry: Mapping[str, object]) -> str:
        assert entry["id"] != 101
        return original_text(tier, entry)

    def reject_poison_gold(entry: Mapping[str, object]):
        assert entry["id"] != 101
        return original_gold(entry)

    def reject_poison_media(entry: Mapping[str, object], context: str):
        assert entry["id"] != 101
        return original_media(entry, context)

    monkeypatch.setattr(builder, "_unit_text", reject_poison_text)
    monkeypatch.setattr(builder, "expected_tool_calls_for_entry", reject_poison_gold)
    monkeypatch.setattr(builder, "_entry_media", reject_poison_media)

    rows, report = builder.a2t_pool_rows(
        lock,
        data_root,
        construction_receipt_path=receipt_path,
        construction_receipt_sha256=receipt_sha,
    )
    assert [row.unit_id for row in rows] == ["tier1_direct:001000"]
    assert report["construction_selection"]["allowed_unit_count"] == 1
    assert report["construction_selection"]["excluded_sample_count"] == 1
    assert report["pool_items"] == 2


def test_selection_rejects_an_allowed_cross_tier_sibling_before_target_helpers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    entries = _tier_entries()
    entries[builder.TIERS[1]][0]["query_idx"] = 1000
    lock, data_root, _public_dir = _write_world(tmp_path, entries)
    inventory = builder.a2t_metadata_inventory(lock, data_root)
    allowed = _unit(inventory, "tier2_parametric:001000")
    receipt_path = tmp_path / "selection.json"
    receipt_sha = _write_receipt(
        receipt_path,
        inventory,
        allowed_units=[
            {"unit_id": allowed["unit_id"], "sample_ids": allowed["sample_ids"]}
        ],
        excluded_sample_ids=["tier1_direct:000100"],
    )
    monkeypatch.setattr(
        builder,
        "_unit_text",
        lambda *_args, **_kwargs: pytest.fail("target text was inspected"),
    )
    monkeypatch.setattr(
        builder,
        "expected_tool_calls_for_entry",
        lambda *_args, **_kwargs: pytest.fail("gold was inspected"),
    )

    with pytest.raises(RailsError, match="query_idx 1000"):
        builder.a2t_pool_rows(
            lock,
            data_root,
            construction_receipt_path=receipt_path,
            construction_receipt_sha256=receipt_sha,
        )


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda allowed, excluded: allowed[0]["sample_ids"].pop(), "partial unit"),
        (
            lambda allowed, excluded: excluded.append("tier8_intent_blending:999999"),
            "unknown excluded_sample_id",
        ),
        (
            lambda allowed, excluded: allowed.append(copy.deepcopy(allowed[0])),
            "duplicate allowed unit",
        ),
        (
            lambda allowed, excluded: allowed[0]["sample_ids"].append(
                allowed[0]["sample_ids"][0]
            ),
            "duplicate sample",
        ),
        (
            lambda allowed, excluded: excluded.append(excluded[0]),
            "duplicate excluded_sample_id",
        ),
        (
            lambda allowed, excluded: allowed[0].update(
                {"unit_id": "tier8_intent_blending:999999"}
            ),
            "unknown allowed unit",
        ),
        (
            lambda allowed, excluded: allowed[0]["sample_ids"].__setitem__(
                0, "tier8_intent_blending:999999"
            ),
            "unknown sample",
        ),
    ],
)
def test_selection_refuses_invalid_identity_membership(
    tmp_path: Path, mutate, message: str
) -> None:
    lock, data_root, _public_dir = _write_world(tmp_path)
    inventory = builder.a2t_metadata_inventory(lock, data_root)
    selected = _unit(inventory, "tier1_direct:001000")
    allowed = [
        {"unit_id": selected["unit_id"], "sample_ids": list(selected["sample_ids"])}
    ]
    excluded = ["tier2_parametric:000101"]
    mutate(allowed, excluded)
    receipt_path = tmp_path / "selection.json"
    receipt_sha = _write_receipt(
        receipt_path,
        inventory,
        allowed_units=allowed,
        excluded_sample_ids=excluded,
    )

    with pytest.raises(RailsError, match=message):
        builder.a2t_pool_rows(
            lock,
            data_root,
            construction_receipt_path=receipt_path,
            construction_receipt_sha256=receipt_sha,
        )


def test_selection_refuses_empty_allowed_units(tmp_path: Path) -> None:
    lock, data_root, _public_dir = _write_world(tmp_path)
    inventory = builder.a2t_metadata_inventory(lock, data_root)
    receipt_path = tmp_path / "selection.json"
    receipt_sha = _write_receipt(
        receipt_path,
        inventory,
        allowed_units=[],
        excluded_sample_ids=["tier2_parametric:000101"],
    )
    with pytest.raises(RailsError, match="allowed_units must be non-empty"):
        builder.a2t_pool_rows(
            lock,
            data_root,
            construction_receipt_path=receipt_path,
            construction_receipt_sha256=receipt_sha,
        )


def test_selection_refuses_malformed_receipt_shapes(tmp_path: Path) -> None:
    lock, data_root, _public_dir = _write_world(tmp_path)
    inventory = builder.a2t_metadata_inventory(lock, data_root)
    selected = _unit(inventory, "tier1_direct:001000")
    allowed = [
        {"unit_id": selected["unit_id"], "sample_ids": selected["sample_ids"]}
    ]
    incomplete_hashes = dict(inventory["source_manifest_sha256_by_tier"])
    incomplete_hashes.pop(builder.TIERS[-1])
    cases = (
        ({"schema": "saea-a2t-construction-selection-v2"}, "schema"),
        ({"unexpected": True}, "contain exactly"),
        (
            {"source_manifest_sha256_by_tier": incomplete_hashes},
            "cover exactly",
        ),
        (
            {
                "allowed_units": [
                    {
                        **allowed[0],
                        "unexpected": True,
                    }
                ]
            },
            "contain exactly",
        ),
        ({"excluded_sample_ids": "tier2_parametric:000101"}, "must be a list"),
    )
    for index, (overrides, message) in enumerate(cases):
        receipt_path = tmp_path / f"malformed-{index}.json"
        receipt_overrides = dict(overrides)
        case_allowed = receipt_overrides.pop("allowed_units", allowed)
        case_excluded = receipt_overrides.pop(
            "excluded_sample_ids", ["tier2_parametric:000101"]
        )
        receipt_sha = _write_receipt(
            receipt_path,
            inventory,
            allowed_units=case_allowed,
            excluded_sample_ids=case_excluded,
            **receipt_overrides,
        )
        with pytest.raises(RailsError, match=message):
            builder.a2t_pool_rows(
                lock,
                data_root,
                construction_receipt_path=receipt_path,
                construction_receipt_sha256=receipt_sha,
            )


def test_receipt_hash_is_checked_before_any_tier_manifest_is_opened(
    tmp_path: Path,
) -> None:
    lock, data_root, public_dir = _write_world(tmp_path)
    receipt_path = tmp_path / "selection.json"
    receipt_path.write_text("{}\n", encoding="utf-8")
    for tier in builder.TIERS:
        (public_dir / f"{tier}_data" / f"{tier}.json").unlink()

    with pytest.raises(RailsError, match="receipt SHA-256"):
        builder.a2t_pool_rows(
            lock,
            data_root,
            construction_receipt_path=receipt_path,
            construction_receipt_sha256="0" * 64,
        )


def test_selection_refuses_source_manifest_drift(tmp_path: Path) -> None:
    lock, data_root, public_dir = _write_world(tmp_path)
    inventory = builder.a2t_metadata_inventory(lock, data_root)
    selected = _unit(inventory, "tier1_direct:001000")
    receipt_path = tmp_path / "selection.json"
    receipt_sha = _write_receipt(
        receipt_path,
        inventory,
        allowed_units=[
            {"unit_id": selected["unit_id"], "sample_ids": selected["sample_ids"]}
        ],
        excluded_sample_ids=["tier2_parametric:000101"],
    )
    source = public_dir / "tier8_intent_blending_data" / "tier8_intent_blending.json"
    source.write_bytes(source.read_bytes() + b"\n")

    with pytest.raises(RailsError, match="source manifest SHA-256"):
        builder.a2t_pool_rows(
            lock,
            data_root,
            construction_receipt_path=receipt_path,
            construction_receipt_sha256=receipt_sha,
        )


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda entries: entries[builder.TIERS[0]][0].update(id=True), "integer id"),
        (
            lambda entries: entries[builder.TIERS[0]][0].update(query_idx=True),
            "integer query_idx",
        ),
        (
            lambda entries: entries[builder.TIERS[0]][0].update(query_idx=-1),
            "query_idx must be non-negative",
        ),
        (
            lambda entries: entries[builder.TIERS[0]].append(
                copy.deepcopy(entries[builder.TIERS[0]][0])
            ),
            "repeated sample identity",
        ),
        (
            lambda entries: entries[builder.TIERS[0]][0].update(tier=builder.TIERS[1]),
            "tier mismatch",
        ),
    ],
)
def test_metadata_inventory_refuses_malformed_identity_fields(
    tmp_path: Path, change, message: str
) -> None:
    entries = _tier_entries()
    change(entries)
    lock, data_root, _public_dir = _write_world(tmp_path, entries)
    with pytest.raises(RailsError, match=message):
        builder.a2t_metadata_inventory(lock, data_root)


def test_metadata_inventory_refuses_a_missing_tier(tmp_path: Path) -> None:
    entries = _tier_entries()
    entries.pop(builder.TIERS[-1])
    lock, data_root, _public_dir = _write_world(tmp_path, entries)
    with pytest.raises(RailsError, match="tier manifest missing"):
        builder.a2t_metadata_inventory(lock, data_root)


def test_selection_arguments_must_be_provided_together(tmp_path: Path) -> None:
    lock, data_root, _public_dir = _write_world(tmp_path)
    with pytest.raises(RailsError, match="provided together"):
        builder.a2t_pool_rows(
            lock,
            data_root,
            construction_receipt_path=tmp_path / "selection.json",
        )
    with pytest.raises(RailsError, match="provided together"):
        builder.a2t_pool_rows(
            lock,
            data_root,
            construction_receipt_sha256="0" * 64,
        )
