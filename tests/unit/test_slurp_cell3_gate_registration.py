"""Stage-3 S3-6 iteration 3 (cell CELL-3) registration proof obligations.

The claim this package makes is narrow and mechanical, so it is checked
mechanically:

* the four CELL-3 baselines differ from **cell B6's plan arm** -- the locked
  v2.0 default plan as it flew on DEV-2000-ADDED -- by exactly the ONE added
  ``knowledge_stores.stage3-deltas`` key plus the per-flight bookkeeping keys
  each cell re-prepares under its own run id;
* the PLANr-DEV2000 baseline differs from it by the bookkeeping keys ALONE --
  it is a request-identical replicate, and that is the whole reason it can
  measure the roster's own null;
* the gate is declared on exactly the three candidate-bound routes, over
  exactly the seven scenarios, and the Perception unconditional route CELL-2
  carried is REMOVED rather than gated;
* every cell is ``held``, no baseline carries a ``prepared_phase_supply`` pin
  (the cell-P0 form: ``core.flight.repin`` mints each cell's own at the flip),
  and the smoke population's declared split identity is the freshly recomputed
  hash of the four ids it names.

Zero model, tokenizer, encoder, scorer, server and network contacts; no
``SPEECHRL_DATA_DIR`` read.
"""

from __future__ import annotations

import json
from pathlib import Path

from speech_aware_evidence_acquisition.data.splits import prefixed, split_identity_hash

REPO_ROOT = Path(__file__).resolve().parents[2]
BASELINE = REPO_ROOT / "configs" / "baseline"
EXPERIMENT = REPO_ROOT / "configs" / "experiment"
CAMPAIGN = REPO_ROOT / "configs" / "campaign"

B6_PLAN = BASELINE / "slurp-native-default-plan-dev2000-added-baseline-v1.json"
ARM = BASELINE / "slurp-native-stage3-delta-cell-r03-gate-baseline-v1.json"
TWIN = BASELINE / "slurp-native-stage3-delta-cell-r03-gate-twin-baseline-v1.json"
SMOKE = BASELINE / "slurp-native-stage3-delta-cell-r03-gate-smoke-4-baseline-v1.json"
TWIN_SMOKE = BASELINE / "slurp-native-stage3-delta-cell-r03-gate-twin-smoke-4-baseline-v1.json"
PLANR = BASELINE / "slurp-native-default-plan-dev2000-added-replicate-baseline-v1.json"

GATED_SCENARIOS = ["general", "alarm", "music", "social", "iot", "play", "news"]
GATE_POLICY = "majority-candidate-scenario-not-in-v1"
SMOKE_IDS = [
    "slurp:devel:000017:audio-1501773854-headset",
    "slurp:devel:000024:audio-1490195864-headset",
    "slurp:devel:000099:audio-1501754782",
    "slurp:devel:000217:audio-1490367363",
]
ROSTER_SPLIT = "ee6c43cd4dd8fc2a583d2dd053e799c2d002efa3755fcd092ba7c7565431bf67"

_BOOKKEEPING_KEYS = {
    "native_contact_fit",
    "prepared_phase_supply",
    "preparation_source_receipts",
    "speech_feature_key_representation_id",
    "speech_feature_matcher_policy_id",
    "speech_packet_promotion_receipt",
    "speech_packet_promotion_receipt_sha256",
}
_DOC_KEYS = {
    "what_this_is",
    "what_the_train_exemplars_store_is",
    "what_the_stage3_deltas_store_is",
    "knowledge_stores_note",
    "smoke_note",
}
_EXCLUDED_KEYS = _BOOKKEEPING_KEYS | _DOC_KEYS


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _comparable(document: dict) -> dict:
    return {key: value for key, value in document.items() if key not in _EXCLUDED_KEYS}


def _cell_baselines() -> tuple[Path, ...]:
    return (ARM, TWIN, SMOKE, TWIN_SMOKE)


def test_planr_is_request_identical_to_cell_b6_plan_arm() -> None:
    """The roster's own null only measures decode noise if the second pass asks
    the same question: the diff is the fit identities and one prose sentence."""

    plan = _load(B6_PLAN)
    planr = _load(PLANR)
    assert _comparable(plan) == _comparable(planr)
    assert planr["knowledge_stores"] == plan["knowledge_stores"]
    assert "stage3-deltas" not in planr["knowledge_stores"]
    fit = planr["native_contact_fit"]
    assert fit["run_id"] == "SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-REPLICATE-FIT-V1"
    assert fit["attempt_id"] == "attempt-slurp-native-default-plan-dev2000-added-replicate-fit-v1"
    assert fit["contact_cap"] == plan["native_contact_fit"]["contact_cap"] == 44000
    # The bookkeeping keys that do NOT move on a request-identical replicate.
    for key in ("preparation_source_receipts", "speech_feature_key_representation_id",
                "speech_feature_matcher_policy_id", "speech_packet_promotion_receipt",
                "speech_packet_promotion_receipt_sha256"):
        assert planr[key] == plan[key], key


def test_each_cell_baseline_adds_exactly_the_one_store_to_cell_b6_plan_arm() -> None:
    plan = _load(B6_PLAN)
    plan_ks = plan.pop("knowledge_stores")
    for path in _cell_baselines():
        cell = _load(path)
        cell_ks = cell.pop("knowledge_stores")
        assert _comparable(plan) == _comparable(cell), path.name
        assert set(cell_ks) == set(plan_ks) | {"stage3-deltas"}, path.name
        for store_id in plan_ks:
            assert cell_ks[store_id] == plan_ks[store_id], (path.name, store_id)
        assert cell_ks["stage3-deltas"]["store_role"] == "stage3-deltas"


def test_the_roster_bindings_are_dev2000_added_everywhere() -> None:
    """The six population keys cell B6 re-pointed, re-pointed the same way."""

    plan = _load(B6_PLAN)
    for path in _cell_baselines() + (PLANR,):
        cell = _load(path)
        boundaries = cell["knowledge_stores"]["intent-boundaries"]["phase_supply"]["perception"]
        exemplars = cell["knowledge_stores"]["train-exemplars"]["phase_supply"]["solver"]
        assert boundaries["query_source"] == (
            plan["knowledge_stores"]["intent-boundaries"]["phase_supply"]["perception"]["query_source"]
        ), path.name
        assert exemplars["query_source"] == (
            plan["knowledge_stores"]["train-exemplars"]["phase_supply"]["solver"]["query_source"]
        ), path.name
        assert "slurp-dev2000-added-v1" in boundaries["query_source"]["relpath"], path.name
        assert "slurp-dev2000-added-v1" in exemplars["query_source"]["relpath"], path.name
        assert cell["scorers"] == ["slurp-slu-official", "cost"], path.name
        assert cell["speech_packet_promotion_receipt"].endswith(
            "DEV-2000-ADDED-promotion.json"), path.name
        assert cell["preparation_source_receipts"] == plan["preparation_source_receipts"], path.name


def test_the_gate_is_declared_on_the_three_candidate_bound_routes_only() -> None:
    for path in _cell_baselines():
        routes = _load(path)["knowledge_stores"]["stage3-deltas"]["context_supply"]
        assert set(routes) == {"solver", "reviewer", "planner"}, path.name
        assert "perception" not in routes, path.name
        for phase, cap in (("solver", 8), ("reviewer", 4), ("planner", 4)):
            spec = routes[phase]
            assert spec["cap"] == cap, (path.name, phase)
            assert spec["rank_by"] == "prior_score"
            assert spec["provider"] == "stage3-delta-candidate-bound-v1"
            assert spec["candidate_state_phase"] == "perception"
            assert spec["node_target"] == phase
            assert spec["scenario_gate"] == {
                "policy": GATE_POLICY,
                "scenarios": GATED_SCENARIOS,
            }, (path.name, phase)


def test_the_gate_resolves_in_the_registered_policy_registry() -> None:
    # The registry is POPULATED from rails/knowledge_provider.py, one of the
    # engineering check's canonical registration files, so importing it is part
    # of the assertion rather than an accident of import order.
    from speech_aware_evidence_acquisition.core.base import STAGE3_SUPPLY_GATE_POLICIES
    from speech_aware_evidence_acquisition.rails import knowledge_provider

    assert GATE_POLICY in STAGE3_SUPPLY_GATE_POLICIES.names()
    assert STAGE3_SUPPLY_GATE_POLICIES.resolve(GATE_POLICY) is not None
    assert hasattr(knowledge_provider, "resolve_scenario_gate")


def test_the_twin_pins_the_derangement_and_moves_nothing_else() -> None:
    arm = _load(ARM)
    twin = _load(TWIN)
    arm_store = arm["knowledge_stores"].pop("stage3-deltas")
    twin_store = twin["knowledge_stores"].pop("stage3-deltas")
    assert _comparable(arm) == _comparable(twin)
    assert arm_store["context_supply"] == twin_store["context_supply"]
    assert twin_store["release"] == {
        "relpath": "knowledge/slurp/semantic/stage3-deltas-twin-v2/release.json",
        "sha256": "b18b141f67dae4b413391d22dd787a3b85480d2b4fab24db0848e547e7aa1a9a",
    }
    assert twin_store["snapshot"] == {
        "relpath": "knowledge/slurp/semantic/stage3-deltas-twin-v2/snapshot.json",
        "sha256": "131809122d23ccdaac86c9a9426c5e045a9544fc3059c1b46f80a3365151d614",
    }
    assert arm_store["release"]["sha256"] == (
        "b81df5c5175e45e68933d4875c110fd46bea933283631d2c428187c480fc31f0")
    assert arm_store["snapshot"]["sha256"] == (
        "44a804184cf83a08e85831d40bae942af1e71ed4365b485d833f9a03807ef150")


def test_the_smokes_carry_their_own_fit_and_feature_identities() -> None:
    for path, run_id, attempt in (
        (SMOKE, "SAEA-SLURP-STAGE3-DELTA-CELL-R03-GATE-SMOKE-4-FIT-V1",
         "attempt-slurp-native-stage3-delta-cell-r03-gate-smoke-4-v1-fit"),
        (TWIN_SMOKE, "SAEA-SLURP-STAGE3-DELTA-CELL-R03-GATE-SMOKE-4-TWIN-FIT-V1",
         "attempt-slurp-native-stage3-delta-cell-r03-gate-smoke-4-v1-twin-fit"),
    ):
        smoke = _load(path)
        assert smoke["native_contact_fit"]["run_id"] == run_id
        assert smoke["native_contact_fit"]["attempt_id"] == attempt
        assert smoke["native_contact_fit"]["contact_cap"] == 176
        assert smoke["speech_feature_matcher_policy_id"].endswith("-smoke-v1")
        assert "smoke_note" in smoke


#: The generation run each derived baseline serves; its minted supply lives under prepared/<run id>/.
_BASELINE_RUN_IDS = {
    ARM.name: "SAEA-SLURP-STAGE3-DELTA-CELL-R03-GATE-V1",
    TWIN.name: "SAEA-SLURP-STAGE3-DELTA-CELL-R03-GATE-TWIN-V1",
    SMOKE.name: "SAEA-SLURP-STAGE3-DELTA-CELL-R03-GATE-SMOKE-4-V1",
    TWIN_SMOKE.name: "SAEA-SLURP-STAGE3-DELTA-CELL-R03-GATE-SMOKE-4-TWIN-V1",
    PLANR.name: "SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-REPLICATE-V1",
}


def test_no_committed_baseline_carries_a_prepared_phase_supply_pin() -> None:
    """The cell-P0 form: core.flight.repin mints each cell's own at the flip.

    As registered (4b3779e5) no baseline carried a pin; the flips (19cc490d arm, ae8f6ca4 twin, a855b92e PLANr)
    pinned each baseline's OWN minted supply. Either state is recorded truth; a foreign pin never is."""

    for path in _cell_baselines() + (PLANR,):
        supply = _load(path).get("prepared_phase_supply")
        if supply is not None:
            assert supply["relpath"] == f"prepared/{_BASELINE_RUN_IDS[path.name]}/phase-supply-v1.json", path.name
        assert "readiness" not in _load(path), path.name


def test_every_registered_cell_is_held_and_names_its_own_identities() -> None:
    expected = {
        "slurp-native-default-plan-dev2000-added-replicate-v1": (
            "SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-REPLICATE-V1"),
        "slurp-native-default-plan-dev2000-added-replicate-fit-v1": (
            "SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-REPLICATE-FIT-V1"),
        "slurp-native-stage3-delta-cell-r03-gate-v1": "SAEA-SLURP-STAGE3-DELTA-CELL-R03-GATE-V1",
        "slurp-native-stage3-delta-cell-r03-gate-fit-v1": (
            "SAEA-SLURP-STAGE3-DELTA-CELL-R03-GATE-FIT-V1"),
        "slurp-native-stage3-delta-cell-r03-gate-twin-v1": (
            "SAEA-SLURP-STAGE3-DELTA-CELL-R03-GATE-TWIN-V1"),
        "slurp-native-stage3-delta-cell-r03-gate-twin-fit-v1": (
            "SAEA-SLURP-STAGE3-DELTA-CELL-R03-GATE-TWIN-FIT-V1"),
        "slurp-native-stage3-delta-cell-r03-gate-smoke-4-v1": (
            "SAEA-SLURP-STAGE3-DELTA-CELL-R03-GATE-SMOKE-4-V1"),
        "slurp-native-stage3-delta-cell-r03-gate-smoke-4-fit-v1": (
            "SAEA-SLURP-STAGE3-DELTA-CELL-R03-GATE-SMOKE-4-FIT-V1"),
        "slurp-native-stage3-delta-cell-r03-gate-smoke-4-twin-v1": (
            "SAEA-SLURP-STAGE3-DELTA-CELL-R03-GATE-SMOKE-4-TWIN-V1"),
        "slurp-native-stage3-delta-cell-r03-gate-smoke-4-twin-fit-v1": (
            "SAEA-SLURP-STAGE3-DELTA-CELL-R03-GATE-SMOKE-4-TWIN-FIT-V1"),
    }
    seen = {}
    for name in ("slurp-native-default-plan-dev2000-added-replicate-v1",
                 "slurp-native-stage3-delta-cell-r03-gate-v1",
                 "slurp-native-stage3-delta-cell-r03-gate-smoke-4-v1"):
        fragment = _load(EXPERIMENT / ("%s.json" % name))
        assert fragment["execution_plan"]["split_role"] == "dev", name
        assert fragment["split_id"] == "DEV-2000-ADDED", name
        assert fragment["execution_profile"] == "bounded-discovery-probe", name
        for cell in fragment["cells"]:
            # `held` as registered (4b3779e5); the generation cells were flipped to `ready` (19cc490d, ae8f6ca4,
            # a855b92e and their smoke siblings), which adds the family's decision receipt and this cell's OWN
            # minted supply. The fit cells stay held.
            state = cell["readiness"]["state"]
            assert state in ("held", "ready"), cell["cell_id"]
            if cell["cell_id"].endswith("-fit-v1"):
                assert state == "held", cell["cell_id"]
            assert cell["dataset_fragment"] == "slurp-speech-native-dev2000-added"
            assert cell["readiness"]["requirements"], cell["cell_id"]
            kinds = [item["kind"] for item in cell["readiness"]["requirements"]]
            if state == "held":
                assert set(kinds) == {"preparation"}, cell["cell_id"]
            else:
                assert set(kinds) == {"decision", "preparation"}, cell["cell_id"]
                own_supply = f"prepared/{cell['run_id']}/phase-supply-v1.json"
                assert any(item["kind"] == "preparation" and item["relpath"] == own_supply
                           for item in cell["readiness"]["requirements"]), cell["cell_id"]
            seen[cell["cell_id"]] = cell["run_id"]
    assert seen == expected


def test_the_smoke_population_hash_matches_the_four_ids_it_names() -> None:
    fragment = _load(EXPERIMENT / "slurp-native-stage3-delta-cell-r03-gate-smoke-4-v1.json")
    assert fragment["population"]["count"] == 4
    assert [entry["ids"] for entry in fragment["populations"]] == [SMOKE_IDS]
    declared = fragment["population"]["split_identity_hash"]
    assert declared == split_identity_hash(prefixed("slurp", SMOKE_IDS))
    assert declared != ROSTER_SPLIT


def test_the_arm_fragments_bind_the_full_roster_identity_and_its_ceiling() -> None:
    for name in ("slurp-native-default-plan-dev2000-added-replicate-v1",
                 "slurp-native-stage3-delta-cell-r03-gate-v1"):
        fragment = _load(EXPERIMENT / ("%s.json" % name))
        assert fragment["population"]["count"] == 1000, name
        assert fragment["population"]["split_identity_hash"] == ROSTER_SPLIT, name
        assert "populations" not in fragment, name
        budget = fragment["family_budget"]
        assert budget["generation_calls_cap"] == 11000, name
        assert budget["fit_endpoint_calls_cap"] == 44000, name
        assert budget["repeated_speech_audio_seconds_cap"] == 32819, name
        assert budget["official_complete_scoring_jobs"] == 1, name
        assert fragment["generation_budget"]["cap"] == 11000, name


def test_the_stage3_algorithm_label_is_the_training_free_grpo_record() -> None:
    from speech_aware_evidence_acquisition.core.stage3_algorithms import (
        validate_stage3_algorithm_label,
    )

    for name in ("slurp-native-stage3-delta-cell-r03-gate-v1",
                 "slurp-native-stage3-delta-cell-r03-gate-smoke-4-v1"):
        label = _load(EXPERIMENT / ("%s.json" % name))["stage3_algorithm"]
        assert label["id"] == "tfgrpo-semantic-advantage-v1", name
        assert label["operators_used"] == ["update", "context_application"], name
        validate_stage3_algorithm_label(label)
    planr = _load(EXPERIMENT / "slurp-native-default-plan-dev2000-added-replicate-v1.json")
    assert planr["stage3_algorithm"]["id"] == "none"
    assert planr["stage3_algorithm"]["operators_used"] == []
    validate_stage3_algorithm_label(planr["stage3_algorithm"])


def test_the_three_campaign_plans_name_the_three_flown_arms() -> None:
    expected = {
        "slurp-native-default-plan-dev2000-added-replicate-v1": (
            "slurp-native-default-plan-dev2000-added-replicate-v1",
            "slurp-native-default-plan-dev2000-added-replicate-v1"),
        "slurp-native-stage3-delta-cell-r03-gate-v1": (
            "slurp-native-stage3-delta-cell-r03-gate-v1",
            "slurp-native-stage3-delta-cell-r03-gate-v1"),
        "slurp-native-stage3-delta-cell-r03-gate-twin-v1": (
            "slurp-native-stage3-delta-cell-r03-gate-twin-v1",
            "slurp-native-stage3-delta-cell-r03-gate-v1"),
    }
    for name, (cell_id, experiment) in expected.items():
        plan = _load(CAMPAIGN / ("%s.json" % name))
        assert plan["schema"] == "saea-campaign-plan-v1"
        assert plan["cells"] == [{"cell": cell_id, "experiment": experiment}], name
