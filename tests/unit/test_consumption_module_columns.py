"""Evidence-consumption module, migration step 4: Perception columns and the delivered-path guard.

Design docs/superpowers/specs/2026-09-29-slurp-consumption-module-design.md sections 3.3 and 4
(step 4); coordinator rulings R1 and R3. AT-M4: a ``column`` component compiles to the flown P-SV
branch block, byte for byte. Model-free throughout.
"""

from __future__ import annotations

import copy
import dataclasses
import json
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
for _extra in (_REPO / "scripts" / "analysis",):
    if str(_extra) not in sys.path:
        sys.path.insert(0, str(_extra))

import module_equivalence_proof as proof  # noqa: E402

from speech_aware_evidence_acquisition.rails import consumption_module as cm  # noqa: E402
from speech_aware_evidence_acquisition.rails.adapters.slurp_module_hooks import (  # noqa: E402
    carrier_module_hooks,
)
from speech_aware_evidence_acquisition.rails.supply_variants import (  # noqa: E402
    PerceptionBranchError, parse_perception_branches,
)

PSV1 = "configs/baseline/slurp-native-stage3-psv1-fold-b-baseline-v1.json"
PSV2 = "configs/baseline/slurp-native-stage3-psv2-fold-b-baseline-v1.json"
PSV4 = "configs/baseline/slurp-native-stage3-psv4-fold-b-baseline-v1.json"


def _cell(relpath: str) -> dict:
    return json.loads((_REPO / relpath).read_text(encoding="utf-8"))


def _entry(block: dict, component_id: str) -> dict:
    return next(c for c in block["components"] if c["component_id"] == component_id)


# ---------------------------------------------------------------------------
# AT-M4.
# ---------------------------------------------------------------------------


def test_at_m4_columns_reproduce_the_flown_psv_branch_blocks():
    report = proof.run_case("m4")
    assert report["ok"], report
    by = {row["baseline"]: row for row in report["results"]}
    assert len(by) == 6
    for row in by.values():
        assert row["branch_block_identical"] and not row["non_roster_differing_paths"]
        assert (row["program_id"], row["program_ceiling"]) == (
            "phase-native-candidates-review-revise-pbranch3-l2-v1", 15,
        )
    assert by[PSV1]["component"] == cm.TOP2_CONTRAST
    assert by[PSV2]["component"] == cm.FORCED_CANDIDATE_LIST
    assert by[PSV4]["component"] == cm.KEY_SOURCE_K6P  # AT-M4 for P-SV-4: the b-k6p block reproduces from the module


def test_at_m4_the_compiled_block_parses_under_the_loaders_own_rules():
    composed = cm.compile_module(proof.psv_column_block(PSV1), carrier_module_hooks())
    block = composed.values()["native_episode"]["roles"]["perception"]["branches"]
    group = parse_perception_branches(block, first_phase_id="perception")
    assert group.branch_ids == ("b-top2contrast", "t-twin", "a-agree")
    assert group.delivering_branch.presentation_id is None  # A carries no axis in column state


def test_the_relisten_shadow_proof_still_holds_beside_columns():
    report = proof.run_case("extra")
    assert report["ok"]


# ---------------------------------------------------------------------------
# Column parse, fail-closed.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda b: b["columns"][0].update(to="off"), "must be 'on'"),
        (lambda b: b["columns"][0].update(level=3), "level must be 1 or 2"),
        (lambda b: b["columns"][0].update(extra=1), "keys must be"),
        (lambda b: b["columns"][0].update(toggle=cm.RELISTEN), "shadow"),
        (lambda b: b["columns"][0].update(toggle=cm.AGREE_VOTE_SEED), "'column' state"),
        (lambda b: b["columns"].append(copy.deepcopy(b["columns"][0])), "distinct"),
        (lambda b: b.update(columns=[]), "exactly one column"),
        (lambda b: b["columns"][0].update(prepared_seed={"relpath": "x", "sha256": "y"}), "64-hex"),
    ],
)
def test_the_column_parse_refuses_a_malformed_column(mutate, message):
    block = proof.psv_column_block(PSV1)
    mutate(block)
    with pytest.raises(cm.ConsumptionModuleConfigError, match=message):
        cm.parse_consumption_module_block(block)


def test_two_columns_must_share_one_level():
    block = proof.psv_column_block(PSV1)
    list3 = proof.psv_column_block(PSV2)
    block["components"] = [
        _entry(list3, c["component_id"]) if c["component_id"] == cm.FORCED_CANDIDATE_LIST else c
        for c in block["components"]
    ]
    block["columns"].append(dict(list3["columns"][0], level=1))
    with pytest.raises(cm.ConsumptionModuleConfigError, match="share one level"):
        cm.parse_consumption_module_block(block)


def test_prepared_seed_is_outside_the_block_identity():
    block = proof.psv_column_block(PSV1)
    other = copy.deepcopy(block)
    other["columns"][0]["prepared_seed"] = {"relpath": "prepared/x.json", "sha256": "0" * 64}
    a, b = cm.parse_consumption_module_block(block), cm.parse_consumption_module_block(other)
    assert a.block_sha256 == b.block_sha256 and a.block_json != b.block_json


def test_two_columns_compile_to_one_block_and_the_ceiling_follows_the_branch_count():
    block = proof.psv_column_block(PSV1)
    list3 = proof.psv_column_block(PSV2)
    block["components"] = [
        _entry(list3, c["component_id"]) if c["component_id"] == cm.FORCED_CANDIDATE_LIST else c
        for c in block["components"]
    ]
    block["columns"].append(list3["columns"][0])
    composed = cm.compile_module(block, carrier_module_hooks())
    rows = composed.values()["native_episode"]["roles"]["perception"]["branches"]["branches"]
    assert [r["branch_id"] for r in rows] == ["b-top2contrast", "b-list3", "t-twin", "a-agree"]
    # level 2, K = 4: 11 + 2 * 3 = 17, no flown branched program -> the family id
    assert (composed.program_id, composed.program_ceiling) == ("phase-native-module-v1-c17", 17)


def test_a_column_beside_relisten_adds_both_ceiling_terms():
    block = proof.psv_column_block(PSV1)
    relisten = proof.component_entries()[cm.RELISTEN]
    block["components"] = [relisten if c["component_id"] == cm.RELISTEN else c for c in block["components"]]
    composed = cm.compile_module(block, carrier_module_hooks())
    assert (composed.program_id, composed.program_ceiling) == ("phase-native-module-v1-c21", 21)


# ---------------------------------------------------------------------------
# The delivered path (ruling R3): 'on' refuses today; an admitted carrier arms A.
# ---------------------------------------------------------------------------


def _on_block() -> dict:
    """top2-contrast ON (delivered path) with a forced-candidate-list column."""
    block = proof.psv_column_block(PSV2)
    top2 = copy.deepcopy(_entry(proof.psv_column_block(PSV1), cm.TOP2_CONTRAST))
    top2["state"] = "on"
    block["components"] = [top2 if c["component_id"] == cm.TOP2_CONTRAST else c for c in block["components"]]
    return block


@pytest.mark.parametrize("component_id", [cm.TOP2_CONTRAST, cm.FORCED_CANDIDATE_LIST])
def test_on_refuses_today_for_want_of_an_admitting_record(component_id):
    block = proof.psv_column_block(PSV1 if component_id == cm.TOP2_CONTRAST else PSV2)
    _entry(block, component_id)["state"] = "on"
    block["columns"] = []
    with pytest.raises(cm.ConsumptionModuleConfigError, match="no admitting record"):
        cm.compile_module(block, carrier_module_hooks())
    assert carrier_module_hooks().delivered_path_admissions == {}


def test_an_admitted_component_sets_the_delivering_branch_and_only_the_module_may():
    hooks = carrier_module_hooks()
    admitted = dataclasses.replace(hooks, delivered_path_admissions={cm.TOP2_CONTRAST: PSV1})
    block = _on_block()
    composed = cm.compile_module(block, admitted)
    branches = composed.values()["native_episode"]["roles"]["perception"]["branches"]
    a_row = branches["branches"][-1]
    assert a_row["deliver"] is True and a_row["presentation_id"] == "top2-contrast-v1"
    assert "contrast_pairs" in a_row
    assert cm.delivered_perception_axes(block) == ("presentation_id",)
    # the loader's parse: refused as a hand-written block (refusal 6) ...
    with pytest.raises(PerceptionBranchError, match="must declare no axis"):
        parse_perception_branches(branches, first_phase_id="perception")
    # ... accepted only with the module's admitted axes; T still resolves A's request
    group = parse_perception_branches(
        branches, first_phase_id="perception", delivering_axes_admitted=("presentation_id",),
    )
    assert group.delivering_branch.presentation_id == "top2-contrast-v1"
    assert group.twin_branch.presentation_id is None
    # a delivering column with no columns at all is refused
    block["columns"] = []
    _entry(block, cm.FORCED_CANDIDATE_LIST)["state"] = "off"
    with pytest.raises(cm.ConsumptionModuleConfigError, match="at least one column"):
        cm.compile_module(block, admitted)


def test_the_parse_lift_is_limited_to_the_named_axes_on_a():
    hooks = carrier_module_hooks()
    admitted = dataclasses.replace(hooks, delivered_path_admissions={cm.TOP2_CONTRAST: PSV1})
    branches = cm.compile_module(_on_block(), admitted).values()["native_episode"]["roles"]["perception"]["branches"]
    with pytest.raises(PerceptionBranchError, match="must declare no axis"):
        parse_perception_branches(branches, first_phase_id="perception",
                                  delivering_axes_admitted=("min_candidates",))
    with pytest.raises(PerceptionBranchError, match="not a subset"):
        parse_perception_branches(branches, first_phase_id="perception",
                                  delivering_axes_admitted=("overrides",))
    knobbed = copy.deepcopy(branches)
    knobbed["branches"][-1]["overrides"] = {
        "knowledge_stores.intent-boundaries.phase_supply.perception.k": 12,
    }
    with pytest.raises(PerceptionBranchError):
        parse_perception_branches(knobbed, first_phase_id="perception",
                                  delivering_axes_admitted=("presentation_id",))
