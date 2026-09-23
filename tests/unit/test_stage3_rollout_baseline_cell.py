"""Cell ROLL-1 (S3-2): the Stage-3 rollout baseline against cell PLAN.

In the ``tests/unit/test_default_plan_lock_cells.py`` style: the two
fragments agree on every key except the per-flight bookkeeping AND the
enumerated S3-2 factor (the grouped-Solver role graph, the removed delivery
normaliser, the samples5 policy id, the roster-bound speech-packet
promotion pins and the placeholder documentation block itself) -- so "the
rollout differs from the plan only in the announced keys" is a property of
bytes, not of prose. The roster-side identity pins that cannot exist yet
(the construction roster's packets are not promoted) are PENDING
placeholders, and this file proves every one of them is both present and
documented, per the task's own "the proof test must accept them" rule.

Once a placeholder is filled its entry moves from ``stage3_pending_placeholders``
to ``stage3_placeholders_filled`` (both blocks are part of the same
documentation key set the fragment is allowed to move against cell PLAN). The
placeholder proof therefore has two halves: while an entry is open its
``PENDING_`` leaf must be documented, and once every entry is closed no
``PENDING_`` leaf may remain anywhere in the fragment.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
BASELINES = REPO_ROOT / "configs" / "baseline"
PLAN = BASELINES / "slurp-native-default-plan-lock-baseline-v1.json"
ROLLOUT = BASELINES / "slurp-native-stage3-rollout-baseline-v1.json"
ROLLOUT_SMOKE = BASELINES / "slurp-native-stage3-rollout-smoke-4-baseline-v1.json"

#: Per-flight bookkeeping (identical set to test_default_plan_lock_cells.py):
#: the fit receipt, the prepared supply and its provenance, the speech-feature
#: identity ids and the free-English descriptions.
BOOKKEEPING = frozenset({
    "native_contact_fit",
    "prepared_phase_supply",
    "preparation_source_receipts",
    "speech_feature_key_representation_id",
    "speech_feature_matcher_policy_id",
    "what_this_is",
    "what_the_train_exemplars_store_is",
})

#: The S3-2 factor: exactly what the rollout baseline is allowed to move
#: against cell PLAN outside bookkeeping.
ENUMERATED = frozenset({
    "native_episode",
    "knowledge_stores",
    "policy",
    "speech_packet_promotion_receipt",
    "speech_packet_promotion_receipt_sha256",
    "stage3_pending_placeholders",
    # the closed half of the same documentation block: an entry moves here the
    # moment its placeholder is filled (2026-09-23), so the two keys are one
    # allowance, not two.
    "stage3_placeholders_filled",
})

SOLVER_KEYS = frozenset({"samples", "decoding_overrides", "commit", "max_iterations", "phase_id"})


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _non_bookkeeping_diff(a: dict, b: dict) -> list[str]:
    return sorted(key for key in (set(a) | set(b)) - BOOKKEEPING if a.get(key) != b.get(key))


def _get(document: Any, path: str) -> Any:
    """Resolve a dotted / ``[index]`` path (the shape
    ``stage3_pending_placeholders[].path`` entries use) against a document."""

    node = document
    for part in re.findall(r"[^.\[\]]+|\[\d+\]", path):
        if part.startswith("["):
            node = node[int(part[1:-1])]
        else:
            node = node[part]
    return node


def _all_pending_strings(node: Any, path: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            found.extend(_all_pending_strings(value, f"{path}.{key}" if path else key))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            found.extend(_all_pending_strings(value, f"{path}[{index}]"))
    elif isinstance(node, str) and node.startswith("PENDING_"):
        found.append(path)
    return found


@pytest.mark.parametrize("path", [PLAN, ROLLOUT, ROLLOUT_SMOKE])
def test_the_fixture_files_exist(path: Path):
    assert path.is_file(), path


def test_rollout_baseline_differs_from_plan_only_in_the_enumerated_keys():
    plan, rollout = _load(PLAN), _load(ROLLOUT)
    assert set(_non_bookkeeping_diff(plan, rollout)) == ENUMERATED


def test_rollout_baseline_solver_carries_exactly_the_four_b2v3_keys():
    rollout = _load(ROLLOUT)
    solver = rollout["native_episode"]["roles"]["solver"]
    assert set(solver) == SOLVER_KEYS
    assert solver["samples"] == 5
    assert solver["decoding_overrides"] == {"temperature": 0.7, "seed_offset": 0}
    assert solver["commit"] == {
        "policy": "saea-commit-plurality-support-v1",
        "min_support": 3,
        "similarity_threshold": 0.8,
    }
    assert solver["max_iterations"] == 1
    assert solver["phase_id"] == "solver"


def test_rollout_baseline_solver_keys_are_exactly_the_b2v3_precedents_addition():
    """The B2 v3 sealed fragment (configs/baseline/slurp-native-anchor-
    samples5-train-fold-a-v3.json) is the form precedent this test pins
    against -- the same three added keys, same values."""

    b2v3_path = BASELINES / "slurp-native-anchor-samples5-train-fold-a-v3.json"
    b2v3 = _load(b2v3_path)
    b2v3_solver = b2v3["native_episode"]["roles"]["solver"]
    rollout_solver = _load(ROLLOUT)["native_episode"]["roles"]["solver"]
    for key in ("samples", "decoding_overrides", "commit"):
        assert rollout_solver[key] == b2v3_solver[key]


def test_rollout_baseline_removes_the_deliver_normaliser():
    plan, rollout = _load(PLAN), _load(ROLLOUT)
    assert plan["native_episode"]["deliver_normaliser"] == {"normaliser": "saea-deliver-normalise-v3"}
    assert "deliver_normaliser" not in rollout["native_episode"]
    assert "slurp_projection_v3_delivery" not in rollout


def test_rollout_baseline_policy_is_the_registered_samples5_program():
    rollout = _load(ROLLOUT)
    assert rollout["policy"] == "phase-native-candidates-review-revise-samples5-v1"
    # a registered program (B2 v3 flies it too), never a fresh registration this task owes.
    b2v3 = _load(BASELINES / "slurp-native-anchor-samples5-train-fold-a-v3.json")
    assert rollout["policy"] == b2v3["policy"]


def test_rollout_baseline_keeps_slot_contracts_geometry_and_scorers_byte_identical_to_plan():
    plan, rollout = _load(PLAN), _load(ROLLOUT)
    assert plan["knowledge_stores"]["slot-contracts"] == rollout["knowledge_stores"]["slot-contracts"]
    assert plan["serving_slot_tokens"] == rollout["serving_slot_tokens"]
    assert plan["serving_slots"] == rollout["serving_slots"]
    assert plan["scorers"] == rollout["scorers"]
    assert plan["phase_material"] == rollout["phase_material"]
    assert plan["task_instruction_template"] == rollout["task_instruction_template"]
    assert plan["task_instruction_fill"] == rollout["task_instruction_fill"]
    assert plan["arm"] == rollout["arm"]


def test_every_pending_leaf_value_is_documented_in_stage3_pending_placeholders():
    rollout = _load(ROLLOUT)
    placeholders = rollout["stage3_pending_placeholders"]
    filled = rollout["stage3_placeholders_filled"]
    assert placeholders or filled, "neither an open nor a closed placeholder record"
    documented_paths = {entry["path"] for entry in placeholders}
    assert len(documented_paths) == len(placeholders), "duplicate placeholder path documented"
    for entry in placeholders:
        assert entry["path"] and entry["note"], entry
        assert len(entry["note"]) > 20, f"placeholder note too short to be useful: {entry}"

    filled_paths = {entry["path"] for entry in filled}
    assert len(filled_paths) == len(filled), "duplicate filled path recorded"
    for entry in filled:
        # "by" may legitimately be a back-reference ("same") to the preceding
        # entry's provenance, as the sha256 sibling of a receipt path is; what
        # must never be empty is the triple itself.
        assert entry["path"] and entry["filled"] and entry["by"], entry
    assert not (documented_paths & filled_paths), "a path is both open and filled"

    pending_paths = _all_pending_strings(rollout)
    if not placeholders:
        # every placeholder is closed: the fragment must carry no PENDING_ leaf
        # at all, which is the other half of the same proof.
        assert not pending_paths, f"all placeholders filled but PENDING_ remains: {pending_paths}"
        return
    assert pending_paths, "the rollout baseline carries no PENDING_ value at all"

    undocumented = []
    for pending_path in pending_paths:
        if pending_path in documented_paths:
            continue
        # an array-item leaf (e.g. "preparation_source_receipts[7].relpath") may be
        # documented at its WHOLE-ITEM granularity ("preparation_source_receipts[7]").
        match = re.match(r"^(.*\[\d+\])(\..+)?$", pending_path)
        array_parent = match.group(1) if match else None
        dotted_parent = pending_path.rsplit(".", 1)[0] if "." in pending_path else None
        if (array_parent and array_parent in documented_paths) or (
            dotted_parent and dotted_parent in documented_paths
        ):
            continue
        undocumented.append(pending_path)
    assert not undocumented, f"undocumented PENDING_ paths: {undocumented}"


def test_every_documented_placeholder_path_resolves_to_something_pending_or_is_an_item_container():
    rollout = _load(ROLLOUT)
    for entry in rollout["stage3_pending_placeholders"]:
        path = entry["path"]
        # strip a trailing ".field" that documents one field of an array item
        # (see the module docstring: array items are documented whole).
        try:
            value = _get(rollout, path)
        except (KeyError, IndexError, TypeError):
            base = re.match(r"^(.*\[\d+\])", path)
            assert base, f"{path} does not resolve and is not an array-item form"
            value = _get(rollout, base.group(1))
        found = _all_pending_strings(value) if isinstance(value, (dict, list)) else (
            [""] if isinstance(value, str) and value.startswith("PENDING_") else []
        )
        assert found, f"documented placeholder {path!r} carries no PENDING_ value"


def test_smoke_carries_the_same_decided_keys_as_the_full_rollout():
    rollout, smoke = _load(ROLLOUT), _load(ROLLOUT_SMOKE)
    assert _non_bookkeeping_diff(rollout, smoke) == []


def test_rollout_baseline_is_not_byte_identical_to_the_b1notool_base_outside_plans_own_diff():
    """Sanity check on the derivation chain: the rollout differs from the
    tool-free B1 base in at least the plan's own decided keys PLUS the S3-2
    factor -- never accidentally collapses back to either endpoint."""

    base = _load(BASELINES / "slurp-native-anchor-exemplars-k20-notool-v1.json")
    rollout = _load(ROLLOUT)
    diff = set(_non_bookkeeping_diff(base, rollout))
    assert "native_episode" in diff
    assert "knowledge_stores" in diff
