"""Evidence-consumption module, carrier transfer: the Audio2Tool and Earnings hook files.

Owner decision 196, direction 205; design ``docs/superpowers/specs/2026-09-29-slurp-consumption-
module-design.md`` sections 2b and 2d. The fake-carrier suite (``test_consumption_module_carrier_
hooks.py``) proves the module arms through a second carrier's hooks; this suite holds the two REAL
hook files to their member contracts: every member the design maps is implemented, every member
with no analogue is ``None``, and a component that needs a ``None`` member is refused on that
carrier. Neither carrier has a locked system, so each all-off block compiles to its DIRECT layer and
any armed component is refused there. Model-free.
"""

from __future__ import annotations

import copy
import dataclasses
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.base import CONSUMPTION_MODULE_PROFILES
from speech_aware_evidence_acquisition.rails import consumption_module as cm
from speech_aware_evidence_acquisition.rails import delivery_normalisers as dn
from speech_aware_evidence_acquisition.rails.a2t_perception_state import (
    Audio2ToolPerceptionAction, Audio2ToolPerceptionState,
)
from speech_aware_evidence_acquisition.rails.adapters import audio2tool_module_hooks as ah
from speech_aware_evidence_acquisition.rails.adapters import earnings_module_hooks as eh
from speech_aware_evidence_acquisition.rails.adapters import slurp_module_hooks as sh

_REPO = Path(__file__).resolve().parents[2]
_FIELDS = tuple(cm.CarrierHooks.__dataclass_fields__)

#: The hook tables (member -> implemented?) the design maps for each carrier.
NONE_MEMBERS = {
    "audio2tool": {
        "decision_supply_path", "default_deliver_normaliser", "deliver_stages", "perception_branch_frame",
        "flown_branch_programs", "delivered_path_admissions", "lock_versions", "current_lock",
        "template_variant_frame", "perception_template_variant_frame", "thinking_variant_frame", "supply_variant_frame", "decoding_variant_frame", "sampling_variant_frame", "lock_deliver_normalisers", "construction",
    },
    "earnings": {
        "decision_supply_path", "decision_candidates", "max_decision_candidates", "deliver_stages",
        "perception_branch_frame", "flown_branch_programs", "delivered_path_admissions", "lock_versions",
        "current_lock", "template_variant_frame", "perception_template_variant_frame", "thinking_variant_frame", "supply_variant_frame", "decoding_variant_frame", "sampling_variant_frame", "lock_deliver_normalisers", "construction",
    },
    "earnings22": {
        "decision_supply_path", "decision_candidates", "max_decision_candidates", "deliver_stages",
        "perception_branch_frame", "flown_branch_programs", "delivered_path_admissions", "lock_versions",
        "current_lock", "template_variant_frame", "perception_template_variant_frame", "thinking_variant_frame", "supply_variant_frame", "decoding_variant_frame", "sampling_variant_frame", "lock_deliver_normalisers", "construction",
    },
}


def _all_off(profile: str, **extra) -> dict:
    block = {
        "module_id": cm.CONSUMPTION_MODULE_ID, "profile": profile,
        "components": [{"component_id": s.component_id, "state": "off"} for s in cm.COMPONENT_CATALOGUE],
        "columns": [],
    }
    block.update(extra)
    return block


def _policy(fragment: str) -> dict:
    raw = json.loads((_REPO / "configs/baseline" / f"{fragment}.json").read_text(encoding="utf-8"))
    return cm.policy_owned_values(raw)


# ---------------------------------------------------------------------------
# Registration: profiles, lock keys, hook files.
# ---------------------------------------------------------------------------


def test_every_registered_profile_has_a_hooks_file_naming_itself():
    assert set(CONSUMPTION_MODULE_PROFILES) == {"slurp", "audio2tool", "earnings", "earnings22"}
    for profile, lock_keys in CONSUMPTION_MODULE_PROFILES.items():
        hooks = cm.resolve_carrier_hooks(profile)
        assert hooks.profile == profile
        for key in lock_keys:
            assert cm.carrier_hooks_for_lock_key(key).profile == profile
    assert cm.carrier_hooks_for_lock_key("unknown-carrier") is None
    with pytest.raises(cm.ConsumptionModuleConfigError, match="not a registered profile"):
        cm.resolve_carrier_hooks("unregistered")


@pytest.mark.parametrize("profile", sorted(NONE_MEMBERS))
def test_the_hook_table_is_exactly_the_design_mapping(profile):
    hooks = cm.resolve_carrier_hooks(profile)
    none = {name for name in _FIELDS if getattr(hooks, name) is None}
    assert none == NONE_MEMBERS[profile]


# ---------------------------------------------------------------------------
# The all-off arm compiles to each carrier's direct layer, byte for byte.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("profile, fragments", [
    ("audio2tool", ("a2t-native-system-direct-v1", "a2t-native-role-direct-union4000-v1",
                    "a2t-stage3-aa-paired-400-a-baseline-v1")),
    ("earnings", ("e21-native-window-direct-full44-v1", "e21-native-window-direct-sub10-v1",
                  "e21-native-window-direct-four-row-v1")),
    ("earnings22", ("e22-native-window-direct-base-v1",)),
])
def test_the_all_off_block_compiles_to_the_carriers_direct_baseline(profile, fragments):
    hooks = cm.resolve_carrier_hooks(profile)
    composed = cm.compile_module(_all_off(profile), hooks)
    assert (composed.program_id, composed.program_ceiling, composed.written_paths) == (
        "phase-direct-only-v1", 1, ())
    for fragment in fragments:
        assert cm.differing_paths(composed.values(), _policy(fragment)) == [], fragment
    assert cm.is_module_off_block(_all_off(profile))


@pytest.mark.parametrize("profile", ["audio2tool", "earnings", "earnings22"])
def test_a_direct_layer_refuses_every_armed_component_and_every_lock(profile):
    hooks = cm.resolve_carrier_hooks(profile)
    block = _all_off(profile)
    block["components"] = [
        {"component_id": cm.REVIEWER_G5_REPAIR, "state": "on", "admitted_by": "registry row 204",
         "record": "README.md", "params": {"instruction_template": "probes/x.txt"}}
    ]
    with pytest.raises(cm.ConsumptionModuleConfigError, match="direct layer"):
        cm.compile_module(block, hooks)
    with pytest.raises(cm.ConsumptionModuleConfigError, match="lock_versions"):
        cm.compile_module(_all_off(profile, lock="v2.1"), hooks)


# ---------------------------------------------------------------------------
# A None member refuses its component even on a system layer.
# ---------------------------------------------------------------------------


def _on_slurp_layer(hooks: cm.CarrierHooks) -> cm.CarrierHooks:
    slurp = sh.carrier_module_hooks()
    return dataclasses.replace(
        hooks, lock_layer=slurp.lock_layer, flown_programs=slurp.flown_programs,
        default_deliver_normaliser=None,
    )


def _armed(profile: str, entry: dict, columns=()) -> dict:
    import module_equivalence_proof as proof  # noqa: PLC0415

    block = _all_off(profile)
    source = copy.deepcopy(proof.component_entries()[entry["component_id"]]) if "params" not in entry else entry
    block["components"] = [source if c["component_id"] == entry["component_id"] else c
                           for c in block["components"]]
    block["columns"] = list(columns)
    return block


@pytest.fixture(autouse=True)
def _proof_path():
    import sys

    extra = str(_REPO / "scripts" / "analysis")
    if extra not in sys.path:
        sys.path.insert(0, extra)


@pytest.mark.parametrize("profile, component, member", [
    ("audio2tool", cm.AGREE_VOTE_SEED, "decision_supply_path"),
    ("audio2tool", cm.SCOPE_RULE, "deliver_stages"),
    ("earnings", cm.AGREE_VOTE_SEED, "decision_supply_path"),
    ("earnings", cm.CENTROID_BOUNDARY_KEY, "decision_supply_path"),
    ("earnings", cm.SCOPE_RULE, "deliver_stages"),
    ("earnings22", cm.AGREE_VOTE_SEED, "decision_supply_path"),
    ("earnings22", cm.SCOPE_RULE, "deliver_stages"),
])
def test_a_none_member_refuses_its_component(profile, component, member):
    hooks = _on_slurp_layer(cm.resolve_carrier_hooks(profile))
    with pytest.raises(cm.ConsumptionModuleConfigError, match=member):
        cm.compile_module(_armed(profile, {"component_id": component}), hooks)


@pytest.mark.parametrize("profile", ["audio2tool", "earnings", "earnings22"])
def test_a_perception_column_is_refused_without_a_branch_frame(profile):
    import module_equivalence_proof as proof  # noqa: PLC0415

    block = proof.psv_column_block("configs/baseline/slurp-native-stage3-psv2-fold-b-baseline-v1.json")
    block["profile"] = profile
    block["components"] = [c for c in block["components"]
                           if c["component_id"] in (cm.FORCED_CANDIDATE_LIST,)]
    hooks = _on_slurp_layer(cm.resolve_carrier_hooks(profile))
    with pytest.raises(cm.ConsumptionModuleConfigError, match="perception_branch_frame"):
        cm.compile_module(block, hooks)


# ---------------------------------------------------------------------------
# Audio2Tool member contracts.
# ---------------------------------------------------------------------------


def test_a2t_decision_candidates_read_the_perception_state_and_the_card_ids():
    state = Audio2ToolPerceptionState(
        actions=(
            Audio2ToolPerceptionAction("a1", ("set_temp", "get_temp"), "", ()),
            Audio2ToolPerceptionAction("a2", ("set_temp", "open_door"), "", ()),
        ),
        global_constraints=(), unique_tool_names=("set_temp", "get_temp", "open_door"),
    )
    assert ah.a2t_decision_candidates(state) == ("set_temp", "get_temp")
    ids = ["cards::a2t-native-card:open_door:value", "a2t-native-card:open_door:content",
           "cards::a2t-native-card:open_door:value", "a2t-native-card:lock_door:value",
           "cards::a2t-native-card:x:value"]
    assert ah.a2t_decision_candidates(ids) == ("open_door", "lock_door")
    assert ah.a2t_decision_candidates(()) == () == ah.a2t_decision_candidates("not a sequence")


def test_a2t_candidate_ceiling_is_every_registered_native_role_configs_value():
    values = set()
    for path in sorted((_REPO / "configs").rglob("a2t-*.json")):
        text = path.read_text(encoding="utf-8")
        if "max_candidates_per_action" in text:
            def walk(node):
                if isinstance(node, dict):
                    for key, value in node.items():
                        if key == "max_candidates_per_action":
                            values.add(value)
                        walk(value)
                elif isinstance(node, list):
                    for item in node:
                        walk(item)
            walk(json.loads(text))
    assert values == {ah.MAX_CANDIDATES_PER_ACTION} == {cm.resolve_carrier_hooks("audio2tool").max_decision_candidates()}


def test_a2t_delivered_units_are_parameter_values_per_action():
    text = json.dumps([
        {"name": "set_temp", "arguments": {"room": "kitchen", "value": 21}},
        {"name": "open_door", "arguments": {"door": "front", "force": False}},
    ])
    label, units, parsed = ah.a2t_delivered_units(text)
    assert parsed and label == "set_temp|open_door"
    assert [(u.type, u.filler, u.index, u.kind) for u in units] == [
        ("0:set_temp.room", "kitchen", 0, "string"), ("0:set_temp.value", "21", 1, "number"),
        ("1:open_door.door", "front", 2, "string"), ("1:open_door.force", "false", 3, "boolean"),
    ]
    assert ah.a2t_delivered_units("no call here") == (None, (), False)
    _label, offer, _parsed = ah.a2t_tool_offer_units(text)
    assert [(u.filler, u.index) for u in offer] == [("kitchen", 0), ("front", 1)]


def test_a2t_registers_no_deliver_normaliser():
    hooks = cm.resolve_carrier_hooks("audio2tool")
    assert hooks.default_deliver_normaliser is None
    for normaliser_id in dn.DELIVERY_NORMALISERS.names():
        entry = dn.DELIVERY_NORMALISERS.resolve(normaliser_id)
        assert getattr(entry, "carrier_lock_key", None) != "audio2tool", normaliser_id


# ---------------------------------------------------------------------------
# Earnings member contracts.
# ---------------------------------------------------------------------------


def test_earnings_delivered_units_are_numeric_and_entity_values_with_no_label():
    label, units, parsed = eh.earnings_delivered_units(
        "Revenue rose five percent at Acme Corp, then Acme Corp said twenty two.",
        entity_terms=["Acme Corp", "", "Nobody"],
    )
    assert parsed and label is None
    assert [(u.type, u.filler, u.kind) for u in units] == [
        ("numeric", "5%", "percent"), ("entity", "acme corp", "entity"),
        ("entity", "acme corp", "entity"), ("numeric", "22", "integer"),
    ]
    assert [u.index for u in units] == [0, 1, 2, 3]
    assert eh.earnings_delivered_units("   ") == (None, (), False)
    _label, offer, _parsed = eh.earnings_tool_offer_units("five percent at Acme Corp")
    assert [(u.type, u.filler) for u in offer] == [("numeric", "5%")]


def test_earnings_default_normaliser_is_the_registered_form_step():
    hooks = cm.resolve_carrier_hooks("earnings")
    assert hooks.default_deliver_normaliser() == dn.DELIVER_NORMALISE_EARNINGS_TEXT_V1
    entry = dn.DELIVERY_NORMALISERS.resolve(dn.DELIVER_NORMALISE_EARNINGS_TEXT_V1)
    assert entry.carrier_lock_key == "earnings21-original"
    assert "whisper" not in " ".join(dn.DELIVERY_NORMALISERS.names()).lower()


def test_the_solver_repair_analogue_is_listed_admitted_and_not_armable():
    hooks = cm.resolve_carrier_hooks("earnings")
    entry = hooks.carrier_components["kc-e1f-repair-supply"]
    assert entry["status"] == "admitted on E21 (replicated PERSON +3.634)"
    assert entry["armable"] is False and (_REPO / entry["record"]).is_file()
    assert entry["plane"].startswith("SUPPLY")
    block = _all_off("earnings")
    block["components"].append({"component_id": "kc-e1f-repair-supply", "state": "off"})
    with pytest.raises(cm.ConsumptionModuleConfigError, match="unknown"):
        cm.parse_consumption_module_block(block)
    for profile in ("audio2tool", "earnings"):
        for name, item in cm.resolve_carrier_hooks(profile).carrier_components.items():
            assert name not in {s.component_id for s in cm.COMPONENT_CATALOGUE}
            assert item["armable"] is False and (_REPO / item["record"]).is_file(), name


# ---------------------------------------------------------------------------
# The per-carrier all-off arms (design 2b.3 admission gate): HELD form proofs, byte-identical to the direct baselines.
# ---------------------------------------------------------------------------

ALLOFF_CELLS = {
    "audio2tool": ("a2t-native-stage3-module-alloff-v1", "a2t-native-stage3-module-alloff-smoke-4-v1"),
    "earnings": ("earnings21-native-stage3-module-alloff-v1", "earnings21-native-stage3-module-alloff-smoke-4-v1"),
}


@pytest.mark.parametrize("at", ["a2t0", "e210"])
def test_the_all_off_byte_proof_holds(at):
    import module_equivalence_proof as proof  # noqa: PLC0415

    report = proof.run_case(at)
    assert report["ok"], report
    cells = [r for r in report["results"] if "cell" in r]
    assert {r["cell"] for r in cells} == {"arm", "smoke"}
    for row in cells:
        assert row["composed_identical"] and row["differing_policy_paths"] == []
        assert row["canonical_alloff_policy_differences"] == []
        # Old immutable declarations may omit components introduced later;
        # their absence must compile to OFF, not invalidate a byte proof.
        assert row["omitted_components_default_off"]
        assert row["composed_config_diff_vs_parent"]["policy"] == []
        assert row["composed_config_diff_vs_parent"]["anything_else"] == []


@pytest.mark.parametrize("profile", sorted(ALLOFF_CELLS))
def test_the_all_off_cells_are_held_form_proofs_declaring_the_all_off_block(profile):
    import module_equivalence_proof as proof  # noqa: PLC0415

    for cell in ALLOFF_CELLS[profile]:
        document = json.loads((_REPO / "configs/experiment" / f"{cell}.json").read_text(encoding="utf-8"))
        assert document["cells"][0]["readiness"]["state"] == "held"
        assert document["stage3_measurement"]["measurement_design"] == "form-proof"
        assert document["stage3_measurement"]["claims_benefit"] is False
        assert document["stage3_algorithm"]["id"] == "none"
        block = document[proof.DECLARATION_KEY]["block"]
        assert cm.is_module_off_block(block)
        hooks = cm.resolve_carrier_hooks(profile)
        assert cm.compile_module(block, hooks).values() == cm.compile_module(proof.alloff_block(profile), hooks).values()


@pytest.mark.parametrize("profile", sorted(ALLOFF_CELLS))
def test_omitted_off_components_preserve_direct_policy(profile):
    hooks = cm.resolve_carrier_hooks(profile)
    canonical = _all_off(profile)
    expected = cm.compile_module(canonical, hooks).values()
    for declarations in ([], canonical["components"][:1], list(reversed(canonical["components"]))):
        block = {**canonical, "components": declarations}
        assert cm.is_module_off_block(block)
        assert cm.compile_module(block, hooks).values() == expected


def test_no_component_on_cell_is_registered_for_audio2tool_or_earnings():
    for path in sorted((_REPO / "configs").rglob("*.json")):
        text = path.read_text(encoding="utf-8")
        if not any(f'"profile": "{profile}"' in text for profile in ("audio2tool", "earnings", "earnings22")):
            continue
        document = json.loads(text)
        blocks = []

        def walk(node):
            if isinstance(node, dict):
                if node.get("module_id") == cm.CONSUMPTION_MODULE_ID:
                    blocks.append(node)
                for value in node.values():
                    walk(value)
            elif isinstance(node, list):
                for item in node:
                    walk(item)

        walk(document)
        for block in blocks:
            if block.get("profile") in ("audio2tool", "earnings", "earnings22"):
                assert cm.is_module_off_block(block), path
