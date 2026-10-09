"""Evidence-consumption module, migration steps 1-2 (owner decisions 195, 196,
199; design docs/superpowers/specs/2026-09-29-slurp-consumption-module-design.md,
coordinator rulings R1 and R2).

Step 1: the closed registry, the block parse (fail-closed), the loader key.
Step 2: the compiler and its equivalence proofs AT-M0 / AT-M1 / AT-M2, made
through ``scripts/analysis/module_equivalence_proof.py`` -- the same
``core.config.compose`` the runtime uses -- plus the program family (R1) and
the ``saea-consumption-module-v1`` header receipt. Model-free throughout.
"""

from __future__ import annotations

import ast
import copy
import json
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
for _extra in (_REPO / "scripts" / "analysis", _REPO / "scripts" / "checks"):
    if str(_extra) not in sys.path:
        sys.path.insert(0, str(_extra))

import engineering_base_check as ebc  # noqa: E402
import module_equivalence_proof as proof  # noqa: E402

from speech_aware_evidence_acquisition.core.base import (  # noqa: E402
    AGENT_CONTROLLERS, CONSUMPTION_MODULES, ConsumptionModuleError, CoreError,
    assert_consumption_module,
)
from speech_aware_evidence_acquisition.core.config import compose, read_fragment  # noqa: E402
from speech_aware_evidence_acquisition.rails import consumption_module as cm  # noqa: E402
from speech_aware_evidence_acquisition.rails import controllers as rc  # noqa: E402
from speech_aware_evidence_acquisition.rails.adapters.slurp_module_hooks import (  # noqa: E402
    carrier_module_hooks,
)
from speech_aware_evidence_acquisition.rails.native_episode_config import (  # noqa: E402
    load_native_episode_config,
)

LOCK_BASELINE = "slurp-native-default-plan-lock-baseline-v1"
LOCK_EXPERIMENT = "slurp-native-default-plan-lock-v1"


def _block(*armed: str) -> dict:
    return proof.module_block(tuple(armed))


def _entry(component_id: str) -> dict:
    return copy.deepcopy(proof.component_entries()[component_id])


# ---------------------------------------------------------------------------
# Step 1: registry.
# ---------------------------------------------------------------------------


def test_the_module_is_registered_under_its_id_and_is_not_a_controller():
    assert CONSUMPTION_MODULES.names() == [cm.CONSUMPTION_MODULE_ID]
    entry = CONSUMPTION_MODULES.resolve(cm.CONSUMPTION_MODULE_ID)
    assert isinstance(entry, cm.EvidenceConsumptionModule)
    assert entry.id == cm.CONSUMPTION_MODULE_ID and entry.version == cm.CONSUMPTION_MODULE_VERSION
    assert not hasattr(entry, "initial_contact") and not hasattr(entry, "advance")


def test_the_registry_refuses_a_duplicate_and_a_mislabelled_entry():
    with pytest.raises(CoreError):
        CONSUMPTION_MODULES.register(cm.CONSUMPTION_MODULE_ID, cm.EvidenceConsumptionModule())
    with pytest.raises(ConsumptionModuleError, match="one identity"):
        assert_consumption_module(cm.EvidenceConsumptionModule(), name="another-id")
    with pytest.raises(ConsumptionModuleError, match="callable"):
        assert_consumption_module(object(), name="x")


def test_the_module_file_names_no_carrier():
    text = (_REPO / "src/speech_aware_evidence_acquisition/rails/consumption_module.py").read_text(
        encoding="utf-8"
    ).lower()
    for token in ("slurp", "audio2tool", "a2t", "earnings", "intent-boundar", "conec"):
        assert token not in text, token


# ---------------------------------------------------------------------------
# Step 1: the block parse, fail-closed.
# ---------------------------------------------------------------------------


def test_an_all_off_block_parses_without_records():
    parsed = cm.parse_consumption_module_block(_block())
    assert parsed.armed() == ()
    assert len(parsed.block_sha256) == 64


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda b: b.update(extra=1), "keys must be"),
        (lambda b: b.update(module_id="not-a-module"), "not registered"),
        (lambda b: b.update(profile="Slurp!"), "profile must match"),
        (lambda b: b.update(columns=[{"column_id": "c"}]), "keys must be"),
        (lambda b: b["components"].append({"component_id": "made-up", "state": "off"}), "unknown"),
        (lambda b: b["components"].append({"component_id": "relisten", "state": "off"}), "repeated"),
        (lambda b: b["components"][0].update(state="maybe"), "state 'maybe' is unknown"),
    ],
)
def test_the_parse_refuses_a_malformed_block(mutate, message):
    block = _block()
    mutate(block)
    with pytest.raises(cm.ConsumptionModuleConfigError, match=message):
        cm.parse_consumption_module_block(block)


def _replace(block: dict, entry: dict) -> dict:
    block["components"] = [
        entry if c["component_id"] == entry["component_id"] else c for c in block["components"]
    ]
    return block


def test_an_armed_component_without_admitted_by_is_refused():
    entry = _entry(cm.AGREE_VOTE_SEED)
    del entry["admitted_by"]
    with pytest.raises(cm.ConsumptionModuleConfigError, match="admitted_by"):
        cm.parse_consumption_module_block(_replace(_block(), entry))


def test_an_armed_component_whose_record_does_not_resolve_is_refused():
    entry = _entry(cm.AGREE_VOTE_SEED)
    entry["record"] = "docs/results/no-such-record.md"
    with pytest.raises(cm.ConsumptionModuleConfigError, match="does not resolve"):
        cm.parse_consumption_module_block(_replace(_block(), entry))
    entry["record"] = "../outside.json"
    with pytest.raises(cm.ConsumptionModuleConfigError, match="repo-relative"):
        cm.parse_consumption_module_block(_replace(_block(), entry))


def test_params_must_carry_exactly_the_components_keys():
    entry = _entry(cm.AGREE_VOTE_SEED)
    entry["params"]["extra"] = 1
    with pytest.raises(cm.ConsumptionModuleConfigError, match="exactly"):
        cm.parse_consumption_module_block(_replace(_block(), entry))


@pytest.mark.parametrize(
    ("component_id", "state", "message"),
    [
        ("e3-progressive-slots", "on", "E3 build go"),
        ("top2-contrast", "shadow", "compiled states are"),
        ("supply-abstain", "on", "migration step 6a"),
        (cm.RELISTEN, "on", "compiled states are"),
        (cm.AGREE_VOTE_SEED, "shadow", "compiled states are"),
    ],
)
def test_a_state_the_component_does_not_compile_is_refused(component_id, state, message):
    entry = {"component_id": component_id, "state": state, "admitted_by": "registry row 195",
             "record": "CLAUDE.md", "params": {}}
    with pytest.raises(cm.ConsumptionModuleConfigError, match=message):
        cm.parse_consumption_module_block(_replace(_block(), entry))


# ---------------------------------------------------------------------------
# Step 2: equivalence proofs (AT-M0, AT-M1, AT-M2) through core.config.compose.
# ---------------------------------------------------------------------------


def _assert_case(at: str) -> dict:
    report = proof.run_case(at)
    for row in report["results"]:
        assert row["differing_policy_paths"] == [], row
        assert row["baseline_object_identical"], row
        assert row["composed_identical"], row
    assert report["ok"], report
    return report


def test_at_m0_all_off_compiles_byte_for_byte_to_the_v2_lock():
    """Migration step 6 (owner decision 204): the CURRENT lock v2.1 (``lock:
    v2.1`` -> cell G5's flown bytes) first, and the v2.0 case kept beside it
    (no ``lock`` key -> the v2.0 lock) so A2 and every queued cell stay provable."""

    report = _assert_case("m0")
    assert {r["program_id"] for r in report["results"]} == {"phase-native-candidates-review-revise-v1"}
    by = {r["experiment"]: r for r in report["results"]}
    lock = compose(_REPO, *_cell_fragments(LOCK_EXPERIMENT)).config_hash
    assert by[LOCK_EXPERIMENT]["module_composed_hash"] == lock and by[LOCK_EXPERIMENT]["lock"] is None
    g5 = compose(_REPO, *_cell_fragments("slurp-native-stage3-g5-fold-a-v1")).config_hash
    assert by["slurp-native-stage3-g5-fold-a-v1"]["module_composed_hash"] == g5
    assert by["slurp-native-stage3-g5-fold-a-v1"]["lock"] == "v2.1"


def test_at_m1_the_agree_component_alone_is_cell_agree():
    report = _assert_case("m1")
    binding = report["sealed_pool"]
    if binding["available"]:
        # The sealed pool's own run manifest: every request of that pool was
        # rendered from exactly this composed configuration.
        assert binding["identical"], binding


def test_at_m2_composed_sets_are_comp1_and_comp1b():
    report = _assert_case("m2")
    by = {(r["experiment"], r["rev"]): r for r in report["results"]}
    assert by[("slurp-native-stage3-comp1-fold-a-v1", "working-tree")]["program_id"] == (
        "phase-native-candidates-review-revise-cited-v1"
    )
    registered = [r for r in report["results"] if r["rev"] == proof.COMP1B_REGISTRATION_COMMIT]
    assert {r["module_composed_hash"] for r in registered} == set(proof.COMP1B_REGISTERED_HASHES.values())


def test_relisten_shadow_and_the_reviewer_repair_compile_to_their_flown_cells():
    report = _assert_case("extra")
    ceilings = {r["experiment"]: r["program_ceiling"] for r in report["results"]}
    assert ceilings["slurp-native-stage3-relisten-fold-a-v1"] == 17


def test_the_proof_detects_a_missing_component():
    """Negative control: AGREE alone is NOT cell COMP-1b (the centroid key is
    missing) and the proof names exactly the differing leaves."""

    composed = cm.compile_module(_block(cm.AGREE_VOTE_SEED), carrier_module_hooks())
    row = proof.rebuild_and_compose(composed, "slurp-native-stage3-comp1b-fold-a-v1")
    assert not row["composed_identical"]
    assert row["differing_policy_paths"] and all(
        ".facet_source." in path for path in row["differing_policy_paths"]
    )


def _cell_fragments(experiment: str) -> tuple[str, str, str, str]:
    cell = json.loads((_REPO / f"configs/experiment/{experiment}.json").read_text(encoding="utf-8"))["cells"][0]
    return cell["model_fragment"], cell["dataset_fragment"], cell["baseline_fragment"], experiment


# ---------------------------------------------------------------------------
# Step 2: compiler refusals and carrier hooks.
# ---------------------------------------------------------------------------


def test_a_component_whose_hook_is_none_refuses_to_arm():
    hooks = carrier_module_hooks()
    bare = cm.CarrierHooks(profile="slurp", lock_layer=hooks.lock_layer,
                           flown_programs=hooks.flown_programs)
    with pytest.raises(cm.ConsumptionModuleConfigError, match="decision_supply_path"):
        cm.compile_module(_block(cm.AGREE_VOTE_SEED), bare)
    # The all-off block needs no carrier fact beyond the lock layer.
    assert cm.compile_module(_block(), bare).program_id == "phase-native-candidates-review-revise-v1"


def test_the_profile_must_match_the_hooks():
    hooks = carrier_module_hooks()
    other = cm.CarrierHooks(profile="other", lock_layer=hooks.lock_layer)
    with pytest.raises(cm.ConsumptionModuleConfigError, match="does not match"):
        cm.compile_module(_block(), other)


def test_resolve_carrier_hooks_finds_the_adapter_file_and_refuses_an_unknown_profile():
    assert cm.resolve_carrier_hooks("slurp").profile == "slurp"
    with pytest.raises(cm.ConsumptionModuleConfigError, match="no carrier hooks"):
        cm.resolve_carrier_hooks("nocarrier")


def test_an_unflown_ceiling_compiles_to_the_program_family():
    entry = _entry(cm.RELISTEN)
    entry["params"]["max_slots_per_row"] = 1
    composed = cm.compile_module(_replace(_block(), entry), carrier_module_hooks())
    assert (composed.program_id, composed.program_ceiling) == ("phase-native-module-v1-c13", 13)
    assert composed.values()["policy"] == "phase-native-module-v1-c13"


def test_a_cited_contract_at_an_unflown_ceiling_is_refused():
    block = _block(cm.SOLVER_CITATION_CONTRACT, cm.RELISTEN)
    with pytest.raises(cm.ConsumptionModuleConfigError, match="no program carries"):
        cm.compile_module(block, carrier_module_hooks())


def test_compile_is_pure_and_deterministic():
    hooks = carrier_module_hooks()
    block = _block(cm.AGREE_VOTE_SEED, cm.CENTROID_BOUNDARY_KEY)
    before = copy.deepcopy(block)
    first, second = cm.compile_module(block, hooks), cm.compile_module(block, hooks)
    assert block == before
    assert first == second
    assert first.written_paths == (
        "knowledge_stores.intent-boundaries.phase_supply.perception.agreement_source",
        "knowledge_stores.intent-boundaries.phase_supply.perception.facet_source",
        "knowledge_stores.intent-boundaries.phase_supply.perception.k",
        "knowledge_stores.intent-boundaries.phase_supply.perception.rank_weights.w_agree",
    )


# ---------------------------------------------------------------------------
# Program family (ruling R1).
# ---------------------------------------------------------------------------


def test_the_program_family_registers_one_id_per_ceiling():
    lock = rc.default_phase_program(rc.MODULE_PROGRAM_FAMILY_BASE)
    assert rc.MODULE_PROGRAM_FAMILY_IDS == tuple(f"phase-native-module-v1-c{c}" for c in (2, *range(3, 25)))
    for program_id in rc.MODULE_PROGRAM_FAMILY_IDS:
        assert program_id in AGENT_CONTROLLERS.names()
        program = rc.default_phase_program(program_id)
        assert program.program_id == program_id
        assert program.max_contacts == int(program_id.rsplit("-c", 1)[1])
        assert program.phases == lock.phases and program.stop_rule == lock.stop_rule
    with pytest.raises(rc.RailsControllersError):
        rc.module_program_family_id(25)


def test_the_family_registration_is_idempotent():
    before = set(AGENT_CONTROLLERS.names())
    rc.register_module_program_family_v1()
    assert set(AGENT_CONTROLLERS.names()) == before


def test_the_engineering_check_reads_the_family_tuple_from_source():
    text = (
        "MODULE_PROGRAM_FAMILY_IDS = ('phase-native-module-v1-c11', 'phase-native-module-v1-c12')\n"
        "for program_id in MODULE_PROGRAM_FAMILY_IDS:\n"
        "    AGENT_CONTROLLERS.register(program_id, None)\n"
    )
    registered = {"AGENT_CONTROLLERS": set()}
    loop_vars = ebc._read_family_registrations(text, ebc.CONTROLLERS_MODULE, registered)
    assert registered["AGENT_CONTROLLERS"] == {
        "phase-native-module-v1-c11", "phase-native-module-v1-c12",
    }
    assert loop_vars == {("program_id", "AGENT_CONTROLLERS")}
    with pytest.raises(ebc.EngineeringBaseError, match="string literals"):
        ebc._read_family_registrations(
            "MODULE_PROGRAM_FAMILY_IDS = tuple(x for x in 'ab')\n",
            ebc.CONTROLLERS_MODULE, {"AGENT_CONTROLLERS": set()},
        )
    assert "module_id" in ebc.NESTED_ID_KEYS
    assert ebc.NESTED_ID_KEYS["module_id"] == "CONSUMPTION_MODULES"


# ---------------------------------------------------------------------------
# The header receipt (design 2.5).
# ---------------------------------------------------------------------------


def test_the_header_receipt_carries_the_schema_fields_and_no_content():
    composed = cm.compile_module(_block(cm.AGREE_VOTE_SEED), carrier_module_hooks())
    receipt = cm.module_header_receipt(
        composed, node_receipts=[{"schema": "saea-deliver-normaliser-v1", "pointer": "row:0"}],
    )
    assert set(receipt) == cm.MODULE_HEADER_RECEIPT_KEYS
    assert receipt["schema"] == "saea-consumption-module-v1"
    assert receipt["profile"] == "slurp" and receipt["program_ceiling"] == 11
    armed = [c for c in receipt["components"] if c["state"] != "off"]
    assert armed == [{
        "component_id": cm.AGREE_VOTE_SEED, "state": "on",
        "admitted_by": "registry row 161", "record": proof.AGREE_BASELINE,
    }]
    assert cm.validate_module_header_receipt(receipt) is receipt
    with pytest.raises(cm.ConsumptionModuleConfigError, match="node-action"):
        cm.module_header_receipt(composed, node_receipts=[{"schema": "made-up", "pointer": "x"}])
    broken = dict(receipt, config_block_sha256="xyz")
    with pytest.raises(cm.ConsumptionModuleConfigError, match="64-hex"):
        cm.validate_module_header_receipt(broken)


# ---------------------------------------------------------------------------
# Step 1: the loader key (rails.native_episode_config).
# ---------------------------------------------------------------------------


def _lock_values() -> dict:
    return copy.deepcopy(dict(compose(_REPO, *_cell_fragments(LOCK_EXPERIMENT)).values))


def test_a_config_without_the_key_loads_with_no_module():
    values = _lock_values()
    parsed = load_native_episode_config(values, rc.default_phase_program(values["policy"]))
    assert parsed.consumption_module_json is None


def test_a_declared_block_that_matches_its_blocks_loads():
    values = _lock_values()
    without = load_native_episode_config(values, rc.default_phase_program(values["policy"]))
    values["native_episode"]["consumption_module"] = _block()
    parsed = load_native_episode_config(values, rc.default_phase_program(values["policy"]))
    assert json.loads(parsed.consumption_module_json)["module_id"] == cm.CONSUMPTION_MODULE_ID
    assert parsed.max_contacts == without.max_contacts == 11
    assert parsed.roles == without.roles


def test_a_declared_block_whose_components_are_not_in_the_config_is_refused():
    values = _lock_values()
    values["native_episode"]["consumption_module"] = _block(cm.AGREE_VOTE_SEED)
    with pytest.raises(ValueError, match="consumption_module is invalid.*differ"):
        load_native_episode_config({**values, "carrier_lock_key": "slurp"}, rc.default_phase_program(values["policy"]))


def test_a_declared_block_with_an_unknown_component_is_refused_by_the_loader():
    values = _lock_values()
    block = _block()
    block["components"].append({"component_id": "made-up", "state": "off"})
    values["native_episode"]["consumption_module"] = block
    with pytest.raises(ValueError, match="consumption_module is invalid"):
        load_native_episode_config({**values, "carrier_lock_key": "slurp"}, rc.default_phase_program(values["policy"]))


def test_lock_layer_hook_reads_the_lock_fragment():
    layer = carrier_module_hooks().lock_layer()
    fragment = read_fragment(_REPO, "baseline", LOCK_BASELINE)
    assert set(layer) == set(cm.POLICY_OWNED_KEYS)
    assert all(layer[key] == fragment[key] for key in cm.POLICY_OWNED_KEYS)


def test_the_module_file_defines_no_controller_or_adapter_class():
    tree = ast.parse(
        (_REPO / "src/speech_aware_evidence_acquisition/rails/consumption_module.py").read_text(
            encoding="utf-8"
        )
    )
    assert ebc._classes_with_methods(tree, {"initial_contact", "advance"}) == []
    assert ebc._classes_with_base(tree, "TaskAdapter") == []


def test_knowledge_opportunity_compiles_shared_tools_and_preserves_off_bytes():
    block = _block()
    before = cm.compile_module(block, carrier_module_hooks()).values()
    block["components"] = [c for c in block["components"] if c["component_id"] != "knowledge-consumption-opportunity"]
    block["components"].append({"component_id": "knowledge-consumption-opportunity", "state": "on",
        "admitted_by": "bounded capability exploration; no effectiveness admission",
        "record": "docs/handoff/2026-10-01-chatgpt-review-and-next-family-v1.md",
        "params": {"mode": "targeted", "store_id": "slot-contracts",
            "reviewer_template": "probes/slurp_native_role_reviewer_slot_issues_v1.txt",
            "planner_template": "probes/slurp_native_role_planner_slot_lookup_v1.txt"}})
    compiled = cm.compile_module(block, carrier_module_hooks())
    values = compiled.values()
    assert values["knowledge_stores"] == before["knowledge_stores"]
    assert values["phase_material"]["perception"] == before["phase_material"]["perception"]
    assert values["phase_material"]["solver"] == before["phase_material"]["solver"]
    assert values["native_episode"]["review_handoff"] == "slot-issues-v1"
    assert values["phase_tools"]["planner"]["max_calls_per_sample"] == 1
    assert values["phase_tools"]["planner"]["knowledge_selection_mode"] == "targeted"
    assert compiled.program_ceiling == 13
    load_native_episode_config({**values, "carrier_lock_key": "slurp"}, rc.default_phase_program(values["policy"]))
    values["phase_tools"]["planner"]["knowledge_selection_mode"] = "reread"
    with pytest.raises(cm.ConsumptionModuleConfigError, match="differ"):
        cm.verify_declared_module(block, values)


def test_prepared_opportunity_configs_are_matched_and_compiler_verified():
    directory = _REPO / "configs/baseline"
    values = {a: json.loads((directory / f"slurp-native-stage3-knowledge-opportunity-{a}-v1.json").read_text()) for a in ("a", "b", "c")}
    for arm, value in values.items():
        block = value["native_episode"]["consumption_module"]
        cm.verify_declared_module(block, value)
        parsed = load_native_episode_config({**value, "carrier_lock_key": "slurp"}, rc.default_phase_program(value["policy"]))
        assert parsed.max_contacts == (11 if arm == "a" else 13)
    assert values["a"]["knowledge_stores"] == values["b"]["knowledge_stores"] == values["c"]["knowledge_stores"]
    assert values["a"]["phase_material"]["solver"] == values["c"]["phase_material"]["solver"]
    assert values["a"]["phase_material"]["perception"] == values["c"]["phase_material"]["perception"]
    assert values["b"]["phase_material"] == values["c"]["phase_material"]
    assert values["b"]["phase_tools"]["planner"]["knowledge_selection_mode"] == "reread"
    assert values["c"]["phase_tools"]["planner"]["knowledge_selection_mode"] == "targeted"
    experiment = json.loads((_REPO / "configs/experiment/slurp-native-stage3-knowledge-opportunity-v1.json").read_text())
    cells = experiment["cells"]
    assert cells[0]["baseline_fragment"] != cells[1]["baseline_fragment"]
    twin = json.loads((directory / (cells[1]["baseline_fragment"] + ".json")).read_text())
    assert {k:v for k,v in values["a"].items() if k != "prepared_phase_supply"} == {k:v for k,v in twin.items() if k != "prepared_phase_supply"}
    assert all(c["readiness"]["state"] == "held" for c in cells)
    assert all("campaign" not in c["allowed_execution_stages"] for c in cells)
