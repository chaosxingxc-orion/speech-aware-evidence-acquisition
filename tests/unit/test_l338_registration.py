"""L338 (the decision-338 lever column on the Thinking core, TRAIN Fold B): package, cells, instrument seam, reader, chain, hook and launch spec.

Model-free: no model, server, tokenizer, GPU or network contact. The cells are the 268-B Thinking lock cell plus the Perception ``sampling_variants`` block the module
compiler writes; the proofs here are that (1) the arm table states only the registered sampling axes and the lock's own decoding, (2) the compiled cells carry exactly that
block and nothing else moved, (3) the compiled group parses through the runtime loader as a level-2 sampling group with the registered seeds, contacts and policies,
(4) the package, the reader's words, streams and discordance tables, the sign-off, the chain, the queue hook and the launch spec agree with the family.
The request-level proof of the fan-out (sample index, seed and override per contact, sample 0 the lock's request) is ``test_l338_sampling_live.py``; the sealed-row render is
``test_l338_sampling_score.py``.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
for _extra in (REPO / "scripts" / "flights" / "nx", REPO / "scripts" / "flights" / "direct", REPO / "scripts" / "flights" / "tfrl", REPO / "scripts" / "flights" / "lib",
               REPO / "scripts" / "flights" / "batch", REPO / "scripts" / "analysis", REPO / "scripts" / "checks", REPO / "src"):
    if str(_extra) not in sys.path:
        sys.path.insert(0, str(_extra))

import derive_tfrl_iteration_cells as dv  # noqa: E402
import l338_derive_cells as dc  # noqa: E402
import l338_family as fam  # noqa: E402
import slurp_l338_column_read as reader  # noqa: E402
import smoke_signoff  # noqa: E402
import thinking_system_family as tsf  # noqa: E402

from speech_aware_evidence_acquisition.core import reasoning_knobs as rk  # noqa: E402
from speech_aware_evidence_acquisition.core.config import compose  # noqa: E402
from speech_aware_evidence_acquisition.rails.controllers import default_phase_program  # noqa: E402
from speech_aware_evidence_acquisition.rails.native_episode_config import load_native_episode_config  # noqa: E402

NX = REPO / "scripts" / "flights" / "nx"
PKG = REPO / fam.PACKAGE
LOCKED_PATH = REPO / fam.LOCKED_TEMPLATE
DECODING = {"temperature": 0.6, "top_p": 0.95, "top_k": 20}
AXES = {
    "l1-support": {"solver_samples": {"n": 5, "decoding": DECODING, "commit": {
        "policy": "saea-commit-first-support-v1", "min_support": 2, "similarity_threshold": 0.8, "n1_min": 0.2, "empty_votes_min": 3}}},
    "l2-union": {"perception_samples": {"k": 4, "decoding": DECODING, "merge_policy": "saea-perception-candidate-union-v1", "cap": 3}},
}


def js(rel: str) -> dict:
    return json.loads((REPO / rel).read_text(encoding="utf-8"))


def baseline(key: str) -> dict:
    return js(f"configs/baseline/{fam.CELLS[key]['baseline']}.json")


def experiment(key: str) -> dict:
    return js(f"configs/experiment/{fam.CELLS[key]['cell']}.json")


def composed(key: str):
    spec = fam.CELLS[key]
    cell = experiment(key)["cells"][0]
    return compose(REPO, cell["model_fragment"], cell["dataset_fragment"], cell["baseline_fragment"], spec["cell"])


def arm_doc() -> dict:
    return json.loads((NX / "l338_arms.json").read_text(encoding="utf-8"))


# ---- ids and shape -----------------------------------------------------------------------------------------------------------------


def test_ids_are_unique_and_follow_the_registered_pattern():
    runs = [fam.CELLS[k][f] for k in fam.ALL_KEYS for f in ("run", "fit_run")]
    assert len(set(runs)) == 4
    assert fam.RECOVERIES == {} and fam.RECOVERY_HISTORY == {} and fam.recovery("arm") is None and fam.rec_suffix("arm") == "" and fam.recovery_index("arm") == 0
    assert fam.eligible_run_ids() == [fam.CELLS["smoke"]["run"], fam.CELLS["smoke"]["fit_run"], fam.CELLS["arm"]["run"], fam.CELLS["arm"]["fit_run"]]
    assert fam.CELLS["arm"]["run"] == "SAEA-SLURP-STAGE3-L338-LEVER-COLUMN-FOLD-B-V1"
    assert fam.CELLS["arm"]["fit_run"] == "SAEA-SLURP-STAGE3-L338-LEVER-COLUMN-FOLD-B-FIT-V1"
    assert fam.CELLS["smoke"]["run"] == "SAEA-SLURP-STAGE3-L338-LEVER-COLUMN-FOLD-B-SMOKE-4-V1"
    assert fam.CELLS["arm"]["cell"] == "slurp-native-stage3-l338-lever-column-fold-b-v1"
    assert fam.CELLS["arm"]["attempt"] == "attempt-slurp-native-stage3-l338-lever-column-fold-b-generation-v1"
    assert fam.PACKAGE == "docs/readiness/2026-10-19-slurp-l338-lever-column-fold-b-v1" and fam.SHORT == "l338" and fam.PKG_NAME == "slurp-l338-lever-column-fold-b-v1"
    assert fam.READ_RUN_ID == "SAEA-SLURP-L338-LEVER-COLUMN-FOLD-B-READ-V1" and fam.SIGNOFF_CONDITIONS == f"{fam.PACKAGE}/signoff-conditions-v1.json"
    for key in fam.ALL_KEYS:
        assert experiment(key)["cells"][0]["run_id"] == fam.CELLS[key]["run"]
        assert experiment(key)["cells"][0]["attempt_id"] == fam.CELLS[key]["attempt"]
        assert baseline(key)["native_contact_fit"]["run_id"] == fam.CELLS[key]["fit_run"]
        assert experiment(key)["cells"][0]["baseline_fragment"] == fam.CELLS[key]["baseline"]
        assert experiment(key)["cells"][0]["model_fragment"] == tsf.THINK_MODEL and experiment(key)["service_session"] == tsf.THINK_SESSION   # the RESIDENT np4 session


def test_recovery_hooks_for_rec1_are_declared_and_empty_now():
    assert list(fam.PREDECESSOR_SNAPSHOTS) == ["arm"] == list(fam.RECOVERY_INPUTS)
    assert fam.PREDECESSOR_SNAPSHOTS["arm"] == [fam.PREDECESSOR_SNAPSHOT["arm"]] and fam.PREDECESSOR_SNAPSHOTS["arm"][0].endswith("predecessor-snapshot-arm-rec1-v1.json")
    assert fam.RECOVERY_INPUTS["arm"] == [fam.RECOVERY_INPUT["arm"]] and fam.RECOVERY_INPUTS["arm"][0].endswith("recovery-input-arm-v1.json")
    assert callable(fam.build_arm_recovery) and not hasattr(fam, "build_arm_rec2") and not hasattr(fam, "RESUME_MODES")        # the rec2 resume tooling is not cloned
    assert not list(NX.glob("l338_rec2_*"))


# ---- the arm table: the closed sampling set and the lock's own decoding ----------------------------------------------------------------------


def test_the_locked_template_is_the_one_the_thinking_lock_renders():
    assert hashlib.sha256(LOCKED_PATH.read_bytes()).hexdigest() == fam.LOCKED_TEMPLATE_SHA
    assert baseline("arm")["phase_material"]["solver"]["instruction_template"] == "probes/slurp_native_role_solver_v2.txt"
    assert baseline("arm")["native_episode"]["consumption_module"]["lock"] == fam.LOCK


def test_the_registered_arms_are_the_two_levers_the_twin_and_the_lock():
    assert list(fam.CANDIDATE_ARMS) == ["l1-support", "l2-union"] and fam.ARM_ORDER == ("l1-support", "l2-union", "aa", "lock") and fam.K == 4
    assert fam.AXIS_OF == AXES and fam.ARM_LEVER == {"l1-support": "L1", "l2-union": "L2"}
    assert fam.PERCEPTION_CONTACTS_PER_ROW == 7 and fam.SOLVER_CONTACTS_PER_ROW == 8 and fam.CONTACTS_PER_ROW == 15 and fam.PROGRAM == "phase-native-module-v1-c15"
    assert fam.LOCKED_DECODING == {"seed": 20260913, "temperature": 0}
    # the sampling decoding is the closed Qwen thinking-mode setting; no arm sets a seed, a cap or a switch (seeds are derived: lock seed + offset)
    assert "seed" not in json.dumps(fam.AXIS_OF) and "max_tokens" not in json.dumps(fam.AXIS_OF)
    group = fam.SAMPLING_GROUP
    assert group.is_sampling and group.branch_ids == fam.ARM_ORDER and group.delivering_branch.branch_id == "lock" and group.twin_branch.branch_id == "aa"
    l1, l2 = group.branch("l1-support").solver_samples, group.branch("l2-union").perception_samples
    assert (l1.n, l1.seed_offsets, l1.min_support, l1.n1_min, l1.empty_votes_min) == (5, (1, 2, 3, 4), 2, 0.2, 3)
    assert (l2.k, l2.seed_offsets, l2.cap, l2.merge_policy) == (4, (1, 2, 3), 3, "saea-perception-candidate-union-v1")


def test_the_lock_decoding_in_the_arm_table_is_the_thinking_fragments_own():
    fragment = js(f"configs/model/{tsf.THINK_MODEL}.json")
    assert {k: v for k, v in fragment["decoding_params"].items() if k in fam.LOCKED_DECODING} == fam.LOCKED_DECODING
    for key in fam.ALL_KEYS:
        values = composed(key).values
        effective = {k: v for k, v in (values.get("decoding_params") or {}).items() if k in fam.LOCKED_DECODING}
        assert effective == fam.LOCKED_DECODING                                      # the request seed every arm inherits


def test_the_arm_table_is_refused_by_name():
    def mutate(fn):
        doc = arm_doc()
        fn(doc)
        return doc

    cases = (
        (mutate(lambda d: d["arms"][0].update(perception_samples=d["arms"][1]["perception_samples"])), "ONE of"),                      # two axes on one arm
        (mutate(lambda d: d["arms"][1].update(arm_id="lock")), "distinct lower-case id"),
        (mutate(lambda d: d["arms"][1].update(arm_id="l1-support")), "distinct lower-case id"),
        (mutate(lambda d: d["arms"][1].update(solver_samples=d["arms"][0]["solver_samples"])), "ONE of"),
        (mutate(lambda d: d["arms"][0].pop("solver_samples")), "ONE of"),                                                              # no axis
        (mutate(lambda d: d.update(twin="x")), "the delivering arm is"),
        (mutate(lambda d: d.update(knobs={})), "must be exactly"),
        (mutate(lambda d: d["arms"][0].update(extra=1)), "ONE of"),
        (mutate(lambda d: d["arms"][0].update(evidence="")), "non-empty string"),
        (mutate(lambda d: d.update(locked_decoding={"seed": 1, "temperature": 0})), "locked_decoding must state"),
        (mutate(lambda d: d.update(arms=[])), "between 1 and"),
        (mutate(lambda d: d["locked_template"].update(sha256="0" * 64)), "Solver template the Thinking lock renders"),
        (mutate(lambda d: d.update(schema="x")), "schema must be"),
    )
    for doc, message in cases:
        with pytest.raises(fam.ArmTableError, match=message):
            fam.validate_arm_table(doc)
    assert [a["arm_id"] for a in fam.validate_arm_table(arm_doc())] == list(fam.CANDIDATE_ARMS)


def test_the_rails_parser_refuses_a_bad_axis_by_name_when_the_group_is_parsed(monkeypatch):
    """The axis-level rules (counts, decoding bounds, registered policies, cap, seed offsets) are the rails' own, applied to the compiled block."""

    from speech_aware_evidence_acquisition.rails.supply_variants import PerceptionBranchError, parse_perception_sampling_variants  # noqa: PLC0415

    def parse(mutate):
        block = fam.sampling_block()
        mutate(block)
        return parse_perception_sampling_variants(block, phase_id="perception")

    assert parse(lambda b: None).is_sampling
    for mutate, message in (
        (lambda b: b["arms"][0]["solver_samples"].update(n=9), "n"),
        (lambda b: b["arms"][1]["perception_samples"].update(k=1), "k"),
        (lambda b: b["arms"][1]["perception_samples"].update(merge_policy="saea-nope-v1"), "merge"),
        (lambda b: b["arms"][0]["solver_samples"]["commit"].update(policy="saea-nope-v1"), "commit"),
        (lambda b: b["arms"][0]["solver_samples"]["decoding"].update(seed=5), "seed"),
        (lambda b: b["arms"].pop(-2), "twin"),
    ):
        with pytest.raises(PerceptionBranchError, match=message):
            parse(mutate)


# ---- the cells ---------------------------------------------------------------------------------------------------------------------


# ---- the cells ---------------------------------------------------------------------------------------------------------------------


def test_the_cells_carry_the_perception_sampling_block_the_twin_and_the_delivering_arm_last():
    for key in fam.ALL_KEYS:
        base = baseline(key)
        roles = base["native_episode"]["roles"]
        block = roles["perception"]["sampling_variants"]
        assert block["node"] == "perception" and set(roles["solver"]) <= {"max_iterations", "phase_id"} and "decoding_variants" not in json.dumps(roles)
        ids = [a["arm_id"] for a in block["arms"]]
        assert ids == list(fam.ARM_ORDER) and ids[-1] == fam.DELIVERING and ids[-2] == fam.TWIN
        assert {a["arm_id"]: {k: v for k, v in a.items() if k != "arm_id"} for a in block["arms"] if a["arm_id"] in fam.CANDIDATE_ARMS} == AXES
        assert block["arms"][-1] == {"arm_id": "lock", "deliver": True} and block["arms"][-2] == {"arm_id": "aa", "replicate_of": "lock"}
        assert "template_variants" not in json.dumps(roles) and "supply_variants" not in json.dumps(roles) and "thinking_variants" not in json.dumps(roles)
        assert block["max_supplied_items"] == fam.MAX_SUPPLIED_ITEMS and block["fit_estimate"] == fam.SAMPLING_FIT_ESTIMATE
        assert fam.SAMPLING_FIT_ESTIMATE["base_prompt_tokens"] == fam.FIT_ESTIMATE["base_prompt_tokens"] + fam.DELIVERING_TEMPLATE_TOKENS
        assert "thinking_policy" not in base and base["policy"] == fam.PROGRAM == "phase-native-module-v1-c15"
        assert base["native_contact_fit"]["contact_cap"] == fam.fit_contact_cap(fam.CELLS[key]["rows"])
        assert base["preflight_budget_mode"] == "defer-to-native-contact-fit"
        episode = base["native_episode"]
        assert (episode["review_loop"], episode["max_revisions"]) == ("off", 0)
        assert episode["finite_completion_policy"] == "deliver-latest-or-abstain" and episode["react_exhaustion_policy"] == "continue-without-answer"
        module = episode["consumption_module"]
        assert [c["column_id"] for c in module["columns"]] == list(fam.CANDIDATE_ARMS) and {c["kind"] for c in module["columns"]} == {"sampling"}
        assert module["sampling_frame"] == {"max_supplied_items": fam.MAX_SUPPLIED_ITEMS, "twin": True, "fit_estimate": fam.SAMPLING_FIT_ESTIMATE}
        assert episode["deliver_normaliser"] == {"normaliser": "saea-deliver-normalise-v4g"}                      # the lock's delivery rule is untouched
        assert block.get("arm_visits", "first") == "first"


def test_the_composed_cell_loads_through_the_runtime_loader_and_verifies():
    from speech_aware_evidence_acquisition.rails.native_episode_receipt import PERCEPTION_BRANCH_RECEIPT_SCHEMA_V6  # noqa: PLC0415
    from speech_aware_evidence_acquisition.rails.supply_variants import sampling_extra_contacts  # noqa: PLC0415

    for key in fam.ALL_KEYS:
        values = composed(key).values
        program = default_phase_program(values["policy"])
        config = load_native_episode_config(values, program)
        group = config.perception_branch_group
        assert group is not None and group.is_sampling and group.level == 2 and group.branch_ids == fam.ARM_ORDER and group.delivering_branch.branch_id == fam.DELIVERING
        assert group.twin_branch.branch_id == fam.TWIN and PERCEPTION_BRANCH_RECEIPT_SCHEMA_V6 == "saea-perception-branch-arms-v6"
        assert config.supply_variant_group is None
        assert program.max_contacts == fam.CONTACTS_PER_ROW == 15 == 2 + 2 * (fam.K - 1) + sampling_extra_contacts(group)
        assert [(b.branch_id, b.perception_samples is not None, b.solver_samples is not None) for b in group.branches] == [
            ("l1-support", False, True), ("l2-union", True, False), ("aa", False, False), ("lock", False, False)]


def test_the_derive_proves_that_only_the_perception_block_the_program_and_the_ids_moved():
    result = dc.derive(write=False)
    assert result["program"] == fam.PROGRAM and result["ceiling"] == fam.CONTACTS_PER_ROW
    for key in fam.ALL_KEYS:
        cell = result["cells"][key]
        assert cell["loader_verification"] == {"ok": True, "refusal": None}
        assert dc.classify_moved(cell["moved_leaves"])[1] == []
        assert cell["moved_by_rule"]["the Perception sampling_variants block"] and cell["moved_by_rule"]["its declaration in consumption_module"]
        assert cell["moved_by_rule"]["the program id and ceiling"] == ["policy"]
        assert not any(leaf.startswith("thinking_policy") or ".decoding_variants" in leaf or ".solver." in leaf for leaf in cell["moved_leaves"])
    # the committed files are exactly what the derive writes (reproducible)
    assert dc.same_json(f"configs/baseline/{fam.CELLS['arm']['baseline']}.json", baseline("arm"))
    for leaf in ("native_episode.roles.solver.decoding_variants", "thinking_policy"):
        assert leaf not in dv._leaves(baseline("arm"))
    # a leaf outside the registered diff is refused by name
    assert dc.classify_moved(["native_episode.roles.solver.max_iterations"])[1] == ["native_episode.roles.solver.max_iterations"]


def test_experiments_swap_nothing_but_the_ids_and_name_the_resident_session():
    for key in fam.ALL_KEYS:
        text = json.dumps(experiment(key))
        assert fam.THINK_SESSION in text and fam.THINK_MODEL in text
        assert "thinking-system-fold-b" not in text.replace("thinking-system-fold-b-lock-fit", "")


# ---- the sample plan of the compiled cell: seeds and decoding per sample come from the rails' own derivation -------------------------------------------


def test_the_compiled_cell_declares_the_registered_sample_plan_and_the_request_adapter_table_matches_it():
    from speech_aware_evidence_acquisition.rails.supply_variants import derive_sample_seeds, sampling_decoding_table  # noqa: PLC0415

    config = load_native_episode_config(composed("smoke").values, default_phase_program(composed("smoke").values["policy"]))
    group = config.perception_branch_group
    table = sampling_decoding_table(group, perception_phase_id="perception", solver_phase_id="solver")
    assert set(table) == set(fam.CANDIDATE_ARMS)
    assert table["l1-support"] == {"solver": {"decoding": DECODING, "seed_offsets": [1, 2, 3, 4]}}
    assert table["l2-union"] == {"perception": {"decoding": DECODING, "seed_offsets": [1, 2, 3]}}
    lock_seed = fam.LOCKED_DECODING["seed"]
    assert derive_sample_seeds(lock_seed, group.branch("l1-support").solver_samples.seed_offsets) == (lock_seed, lock_seed + 1, lock_seed + 2, lock_seed + 3, lock_seed + 4)
    assert derive_sample_seeds(lock_seed, group.branch("l2-union").perception_samples.seed_offsets) == (lock_seed, lock_seed + 1, lock_seed + 2, lock_seed + 3)
    # the delivering arm and the twin declare no axis, so their requests are the lock's own
    assert table.get("lock") is None and table.get("aa") is None


def test_the_dry_run_reports_the_lock_thinking_fields_for_every_arm_of_a_sampling_group():
    """The native dry-run walk resolves a per-arm ``node_decoding`` for a SAMPLING group (decision 338), like a thinking group's."""

    source = (REPO / "src/speech_aware_evidence_acquisition/analysis/native_episode_dry_run.py").read_text(encoding="utf-8")
    assert "episode_group.is_thinking or episode_group.is_sampling" in source
    import l338_dry_run as dry  # noqa: PLC0415

    values = composed("smoke").values
    folded = rk.fold_into_decoding(values)
    assert folded and folded["decoding_params"]["thinking_budget_tokens"] == 3072 and folded["decoding_params"]["max_tokens"] == 4096
    expected = dry.lock_node_decoding()
    assert set(expected) == {"perception", "solver"}
    for node_decoding in expected.values():
        assert node_decoding == {"thinking_budget_tokens": 3072, "chat_template_kwargs": {"enable_thinking": True}, "max_tokens": 4096}
    plan = None
    sys.path.insert(0, str(REPO / "src"))
    plan = dry.sample_plan()
    assert plan["l1-support"]["seeds"] == [20260913 + i for i in range(5)] and plan["l1-support"]["extra_contacts"] == 4
    assert plan["l2-union"]["seeds"] == [20260913 + i for i in range(4)] and plan["l2-union"]["extra_contacts"] == 3


# ---- fit, cost and budget ------------------------------------------------------------------------------------------------------------


def test_the_live_slot_holds_the_locks_prompt_plus_the_cap():
    fit = fam.fit_proof()
    assert fit["ok"] and fit["prompt_limit_tokens"] == 17406 == fam.PROMPT_LIMIT and fit["completion_cap"] == 4096
    assert fit["longest_added_tokens_over_lock"] == 0 and fit["template_tokens"] == fam.DELIVERING_TEMPLATE_TOKENS == -(-LOCKED_PATH.stat().st_size * 2 // 7)
    assert fit["estimate_at_bound_tokens"] == 2000 + fam.DELIVERING_TEMPLATE_TOKENS + 55 * 235 <= fit["prompt_limit_tokens"]
    assert fit["observed_solver_prompt_tokens_max"] + fit["completion_cap"] <= fit["slot_tokens"]


def test_the_derive_refuses_when_the_slot_cannot_hold_the_prompt_plus_the_cap(monkeypatch):
    monkeypatch.setattr(fam, "OBSERVED_SOLVER_PROMPT_MAX", 21000)
    assert not fam.fit_proof()["ok"]
    with pytest.raises(SystemExit, match="does not hold"):
        dc.derive(write=False)


def test_the_registered_cost_and_ceiling_follow_the_measured_r2b_throughput():
    m = fam.M
    assert m["gpu_hours_per_1080_row_lock_flight"] == 9.23 and m["perception_seconds_per_contact_mean"] == 59.0 and abs(m["solver_seconds_per_contact_mean"] - 64.07) < 1e-9
    assert abs(m["seconds_per_row_lock"] - 9.23 * 4 * 3600 / 1080) < 0.01
    assert fam.K == 4 and fam.CONTACTS_PER_ROW == 15 and fam.PROGRAM == "phase-native-module-v1-c15"
    exact = (7 * 59.0 + 8 * 64.07) / (59.0 + 64.07)
    assert 7.52 <= exact < 7.525 and fam.ARM_MIX_ROWS == fam.round_hundredth(exact) == 7.52          # the design spec's mix (nearest 0.01; ceil would read 7.53)
    assert fam.ROWS_PER_MINUTE_FULL == 1.95
    expected = 1080 * 7.52 / 1.95 / 60
    assert abs(fam.expected_gpu_hours(1080) - expected) < 1e-9 and round(expected, 1) == 69.4
    assert fam.planned_gpu_hours(1080) == 90.3 == fam.CELLS["arm"]["gpu_hours"] and fam.CELLS["smoke"]["gpu_hours"] == 0.5
    assert fam.planned_gpu_hours(1080) >= fam.expected_gpu_hours(1080) * 1.3 and fam.planned_gpu_hours(1080) < fam.expected_gpu_hours(1080) * 1.3 + 0.1
    # the per-branch shares of the design spec: lock 1.00, aa 1.00, l1 3.08, l2 2.44 lock-row equivalents
    assert abs((59.0 + 5 * 64.07) / 123.07 - 3.08) < 0.005 and abs((4 * 59.0 + 64.07) / 123.07 - 2.44) < 0.005


def test_plan_ceilings_follow_the_program_and_the_fallback_contacts():
    assert fam.THINKING_CONTACTS_PER_ROW == 15 == fam.FALLBACK_CONTACTS_PER_ROW_CEILING
    assert fam.original_generation_calls("arm") == 1080 * 30 == 32400 and fam.original_generation_calls("smoke") == 4 * 30
    assert fam.program_calls("arm") == 1080 * 15 == 16200 and fam.fit_contact_cap(1080) == 1080 * 15 * 4
    for key in fam.ALL_KEYS:
        family, plan = dc.budgets(key)
        assert plan["planned_model_calls"] == fam.generation_calls(key) and family["fit_endpoint_calls_cap"] == fam.fit_contact_cap(fam.CELLS[key]["rows"])
        assert plan["execution_profile"] == "bounded-discovery-probe" and plan["split_role"] == "discovery" and plan["planned_gpu_hours"] == fam.CELLS[key]["gpu_hours"]
    # repeated speech audio: every contact re-sends the row's speech packet (15 program contacts + 15 fallback re-asks per row)
    assert abs(fam.audio_cap("arm") - fam.roster_audio("arm") * 30) <= 1 and fam.extra_audio_seconds("arm") == fam.roster_audio("arm") * 13


# ---- the package -------------------------------------------------------------------------------------------------------------------------


def test_stage3_measurement_blocks():
    facts = json.loads((PKG / "registered-facts-v1.json").read_text(encoding="utf-8"))
    blocks = facts["stage3_measurement"]
    arm_run, smoke = fam.CELLS["arm"]["run"], fam.CELLS["smoke"]["run"]
    assert set(blocks) == {arm_run, smoke}
    b = blocks[arm_run]
    assert b["measurement_design"] == "same-flight-node-column" and b["claims_benefit"] is False and b["claim"] == "nominated" and b["aa_arm_id"] == "aa"
    assert b["primary_metric_key"] == "slu" and b["rows"] == 1080 and b["tuning_roster"] == "none" and b["read_roster"] == fam.READ_ROSTER and b["expected_effect_pp"] == 0.0
    assert b["template_variants"] == {"node": "perception", "candidate_arms": 2, "twin": True}
    assert b["variant_kind"] == "solver-sampling" and b["variant_kind_by_arm"] == {"l1-support": "solver-sampling", "l2-union": "perception-sampling"}
    assert b["primary_metric_key_by_arm"] == {"l1-support": "slu", "l2-union": "intent"}
    assert b["variant_cost"]["extra_contacts_per_row"] == 13 and b["variant_cost"]["extra_audio_seconds"] > 0
    assert blocks[smoke]["measurement_design"] == "form-proof" and blocks[smoke]["claims_benefit"] is False
    assert facts["blockers"] == [] and {f["id"] for f in facts["findings"]} >= {
        "why-the-lever-column", "free-check-over-r4-before-the-countersign", "sample-contacts-carry-the-lock-thinking-fields", "in-flight-aa-twin",
        "stochastic-streams-and-the-fixed-seeds", "n1-is-unavailable-in-flight", "l2-longer-lists-and-forced-close", "resident-session-no-new-fragment",
        "machine-signoff-with-a-veto-window"}
    ce = facts["accounting"]["cost_estimate"]
    assert ce["column_flight"]["planned_ceiling_gpu_hours"] == fam.CELLS["arm"]["gpu_hours"] and ce["arm_mix_rows"] == fam.ARM_MIX_ROWS
    assert [r["arm"] for r in ce["arm_table"]] == list(fam.ARM_ORDER) and ce["inputs"]["r2b_measured"]["slots"] == 4
    assert facts["read_rule"]["word_order"] == {"L1": ["NOMINATED", "HARM", "NEUTRAL"], "L2": ["NOMINATED", "HARM", "NEUTRAL"]}
    assert facts["read_rule"]["twin"] == "aa" and facts["context_fit"]["ok"] is True and facts["read_rule"]["levers"] == {"l1-support": "L1", "l2-union": "L2"}
    assert facts["pins"]["signoff_conditions"]["sha256"] == hashlib.sha256((PKG / "signoff-conditions-v1.json").read_bytes()).hexdigest()
    assert "thinking_arms" not in facts and "decoding_arms" not in facts and facts["locked_decoding"] == fam.LOCKED_DECODING
    assert facts["sampling_arms"]["lock"] is None and facts["sampling_arms"]["aa"] is None and facts["sampling_arms"]["l1-support"] == AXES["l1-support"]
    assert facts["sampling_arms"]["l2-union"] == AXES["l2-union"]


def test_the_effect_floor_gate_resolves_the_node_column(tmp_path):
    """The gate keys on the exposure ledger; the package's DRAFT rows are overlaid on a COPY (this repository's ledger is not touched)."""

    ledger = tmp_path / "ledger.md"
    ledger.write_text((REPO / "docs/exposure-ledger.md").read_text(encoding="utf-8") + "\n" + (PKG / "draft-ledger-rows.md").read_text(encoding="utf-8"), encoding="utf-8")
    out = subprocess.run([sys.executable, "-B", str(REPO / "scripts/checks/stage3_effect_floor_check.py"), "--ledger", str(ledger), "--json"],
                         capture_output=True, text=True, cwd=REPO)
    assert out.returncode == 0, out.stderr[-500:]
    report = json.loads(out.stdout[out.stdout.find("{"):])
    mine = [c for c in report["in_scope_cells"] if "l338-lever-column" in c["cell_id"]]
    assert {c["cell_id"] for c in mine} == {fam.CELLS[k]["cell"] for k in fam.ALL_KEYS}
    assert not [f for f in report["findings"] if "l338-lever-column" in json.dumps(f)]
    column = {c["cell_id"]: c["declaration"] for c in mine}[fam.CELLS["arm"]["cell"]]
    assert column["problems"] == [] and column["measurement_design"] == "same-flight-node-column" and column["claims_benefit"] is False
    assert column["variant_kind"] == "solver-sampling" and column["template_variants"] == {"node": "perception", "candidate_arms": 2, "twin": True}


def test_plans_protocol_receipt_and_ledger_agree():
    protocol_sha = hashlib.sha256((PKG / "protocol-registered-v1.json").read_bytes()).hexdigest()
    draft_rows = (PKG / "draft-ledger-rows.md").read_text(encoding="utf-8")
    for key in fam.ALL_KEYS:
        for kind in ("generation", "fit"):
            assert fam.plan_file_name(key, kind) == f"{fam.CELLS[key]['prefix']}{kind}-plan-registered-v1.json"
            plan = json.loads((PKG / fam.plan_file_name(key, kind)).read_text(encoding="utf-8"))
            assert plan["expected_session_id"] == fam.THINK_SESSION and plan["protocol_document"]["sha256"] == protocol_sha
            assert plan["thinking_knobs"]["thinking_budget_tokens"] == 3072 and plan["execution_plan"]["split_role"] == "discovery"
            assert plan["arm_order"] == list(fam.ARM_ORDER) and plan["arm_visits"] == "first" and "recovery" not in plan and "cell_thinking_policy" not in plan
            assert plan["sampling_arms"]["lock"]["axes"] is None and plan["sampling_arms"]["l1-support"]["axes"] == AXES["l1-support"]
            assert plan["sampling_arms"]["l2-union"]["axes"] == AXES["l2-union"] and "template_arms" not in plan and "decoding_arms" not in plan
            run = fam.CELLS[key]["run" if kind == "generation" else "fit_run"]
            assert plan["execution_plan"]["run_id"] == run and plan["execution_plan"]["planned_gpu_hours"] == fam.CELLS[key]["gpu_hours"]
            assert plan["execution_plan"]["planned_model_calls"] == (fam.generation_calls(key) if kind == "generation" else fam.fit_contact_cap(fam.CELLS[key]["rows"]))
            if kind == "fit":
                assert plan["context_fit"]["ok"] is True and plan["context_fit"]["prompt_limit_tokens"] == fam.PROMPT_LIMIT
            assert draft_rows.count(f"| {run} |") == 1
    draft = json.loads((PKG / "root-admission-draft-v1.json").read_text(encoding="utf-8"))
    assert draft["eligible_run_ids"] == fam.eligible_run_ids() and draft["eligible_attempt_ids"] == fam.eligible_attempt_ids()
    assert draft["decision_id"] == fam.DECISION_ID and draft["status"] == "DRAFT-NOT-MINTED" and draft["service"]["expected_session_id"] == fam.THINK_SESSION
    assert "recovery" not in draft and draft["budget"]["generation_calls_cap"] == fam.generation_calls("arm")
    texts = json.loads((PKG / "countersign-row-texts-v1.json").read_text(encoding="utf-8"))
    current = {fam.CELLS[k][f] for k in fam.ALL_KEYS for f in ("run", "fit_run")}
    assert set(texts["rows"]) == current | {fam.READ_RUN_ID} and draft_rows.count(f"| {fam.READ_RUN_ID} |") == 1
    assert len([ln for ln in draft_rows.splitlines() if ln.startswith("| 2026")]) == 5
    recipe = json.loads((PKG / "analysis-recipe-v1.json").read_text(encoding="utf-8"))
    assert recipe["read_run_id"] == fam.READ_RUN_ID and recipe["arms"] == list(fam.ARM_ORDER) and recipe["twin"] == "aa" and recipe["delivering"] == "lock"
    assert recipe["verdict_words"] == sorted(reader.WORDS) and recipe["primary"]["draws"] == 10000 and "efficiency" not in recipe
    assert recipe["guard"]["floors_pp"] == {"slu": 1.49, "intent": 0.65} and "NO-RESOLVED-LOSS" not in json.dumps(recipe) and "335 B Fold A column" in recipe["next_step"]
    assert recipe["levers"] == {"l1-support": "L1", "l2-union": "L2"} and recipe["primary_by_lever"] == {"L1": "slu", "L2": "intent"}
    assert recipe["word_order"] == {"L1": ["NOMINATED", "HARM", "NEUTRAL"], "L2": ["NOMINATED", "HARM", "NEUTRAL"]}
    assert "discordance_of_every_sampled_stream_against_the_twin" in recipe["secondaries"] and recipe["sampling_arms"]["l2-union"] == AXES["l2-union"]
    assert {"support_count_table", "union_size_table", "l1_pure_filter_delta", "forced_close_share_by_list_size"} <= set(recipe["secondaries"])
    assert (REPO / fam.PREREG).is_file()
    for line in draft_rows.splitlines():
        if line.startswith("| 2026"):
            assert "DRAFT" in line and "root countersigned" not in line


def test_the_readme_names_the_ruling_the_arms_the_fit_the_cost_the_words_and_the_next_step():
    readme = (PKG / "README.md").read_text(encoding="utf-8")
    for needle in ("338", "341 A", "l1-support", "l2-union", "saea-perception-branch-arms-v6", "arm_visits", "first", "solver_samples", "perception_samples",
                   "saea-commit-first-support-v1", "saea-perception-candidate-union-v1", "n1-unavailable", "parse_perception_sampling_variants", "lock seed", "discordance",
                   "stochastic", "think-budget-np4", "no-op", "drop-reasoning-v1", "ceil_0.1", "NOMINATED", "NO-RESOLVED-LOSS", "HARM", "NEUTRAL", "335 B Fold A column", "NOT built",
                   "flip_package_ext4.sh", "l338_arms.json", "l338-decode-signoff.marker", "L338_KINDS", "wait_or_machine_signoff", "close_rows_after_seal", "SAEA-Chain-L338",
                   "queue_l338_after_chain.sh", "exit token", "signoff-conditions-v1.json", "arm-only", "forced-close share", "list size",
                   "ceil(bytes / 3.5)", "no tokenizer contact", "24 GPU-h", str(fam.CELLS["arm"]["gpu_hours"]), str(fam.ARM_MIX_ROWS), "69.4", "-0.65", "1.49", "0.65",
                   "perception-branches", "l1-support-sample0", "CHAIN_L338_EXIT", "/home/chao/l338-chain.out", "CHAIN_NXT4_EXIT",
                   "repin exit N (1 = its internal check refused the dirty tree, expected)"):
        assert needle in readme, needle
    assert "d1-qwen-sampling" not in readme and "EFFICIENT-NO-LOSS" not in readme and "decoding_variants" not in readme.replace("DECODING_VARIANT_KNOBS", "")
    for script in ("l338_flip.sh", "l338_read.sh", "l338_repin_cell.sh", "batch_chain_l338.sh"):
        assert subprocess.run(["bash", "-n", str(NX / script)], capture_output=True).returncode == 0


def test_the_text_of_the_package_is_english():
    for path in [PKG / n for n in ("README.md", "draft-ledger-rows.md", "countersign-row-texts-v1.json", "registered-facts-v1.json", "protocol-registered-v1.json",
                                     "signoff-conditions-v1.json", "analysis-recipe-v1.json")]:
        assert not re.search(r"[^\x00-\x7f]", path.read_text(encoding="utf-8")), path
    for name in ("l338_family.py", "l338_derive_cells.py", "l338_write_registration.py", "l338_mint_receipt.py", "l338_dry_run.py", "l338_flip.sh", "l338_repin_cell.sh",
                 "l338_read.sh", "batch_chain_l338.sh", "l338_arms.json", "l338_cost_inputs.json", "l338_launch_spec.json"):
        assert (NX / name).read_text(encoding="utf-8").isascii(), name
    for rel in (fam.READER, fam.PREREG, "scripts/flights/batch/queue/queue_l338_after_chain.sh", "scripts/flights/batch/queue/chain_l338.sh"):
        assert (REPO / rel).read_text(encoding="utf-8").isascii(), rel


# ---- the sign-off conditions (emitted by the derive, inside the package) -----------------------------------------------------------------


def test_signoff_conditions_are_emitted_inside_the_package_from_the_arm_table(tmp_path):
    committed = json.loads((PKG / "signoff-conditions-v1.json").read_text(encoding="utf-8"))
    assert committed == fam.signoff_conditions() and (PKG / "signoff-conditions-v1.json").read_text(encoding="utf-8") == dc.signoff_conditions_text()
    smoke_signoff.validate_conditions(committed)
    assert committed["package"] == fam.PKG_NAME and committed["table_schema"] == fam.SMOKE_SCHEMA == reader.SCHEMA_SMOKE
    assert committed["table_relpath"] == f"{fam.ANALYSIS_ROOT}/smoke-decode-cost.json" and committed["expected_arms"] == sorted(fam.ARM_ORDER)
    assert committed["no_think_nodes"] == {} and committed["every_node_max"] == {"cap_hits": 0, "empty_content": 0, "no_json_object": 0, "finish_reason_length": 0}
    assert committed["arm_mix"] == {"max_ratio": 1.3, "measured_key": "arm_mix_measured_rows", "registered_key": "arm_mix_registered_rows"}
    first = dc.write_signoff_conditions(repo_root=tmp_path)
    assert json.loads((tmp_path / first).read_text(encoding="utf-8")) == fam.signoff_conditions() and dc.write_signoff_conditions(repo_root=tmp_path) == first


# ---- the reader ---------------------------------------------------------------------------------------------------------------------------


def _answer(*fillers, scenario="s", action="a"):
    return json.dumps({"scenario": scenario, "action": action, "entities": [{"type": "place_name", "filler": f} for f in fillers]}, sort_keys=True)


def _outputs_rows(n=4, lists=(2, 3)):
    """Sealed-row views as ``load_outputs_rows`` returns them: per row the four branches, the l1 five-sample custody, the l2 four-sample merge and the request ids."""

    rows = []
    for i in range(n):
        sid = f"s{i}"
        size = lists[i % len(lists)]
        merged = [f"i:{k}" for k in range(size)]
        branches = []
        requests = {}
        for arm in fam.ARM_ORDER:
            p, s = f"{sid}:{arm}:p0", f"{sid}:{arm}:s0"
            requests[s] = f"req-{s}"
            branch = {"branch_id": arm, "contact_id": p, "solver_contact_id": s, "solver_absent": False, "candidate_ids": merged[:2], "perception_samples": None,
                      "solver_samples": None}
            if arm == "l1-support":
                samples = [{"contact_id": f"{sid}:{arm}:s{j}", "parse_status": "ok"} for j in range(5)]
                for sample in samples:
                    requests[sample["contact_id"]] = f"req-{sample['contact_id']}"
                branch["solver_samples"] = {"samples": samples, "outcome": {"delivered_entity_count": 1}}
            if arm == "l2-union":
                samples = [{"contact_id": f"{sid}:{arm}:p{j}", "candidate_ids": merged[:2] if j == 0 else merged[j % size:], "note_parse_status": "ok"} for j in range(4)]
                branch["perception_samples"] = {"merged_ids": merged, "appended_ids": merged[2:], "samples": samples}
            branches.append(branch)
        rows.append({"sample_id": sid, "branches": branches, "requests": requests})
    return rows


def _contact(agent, role, tokens, seconds, *, forced=False, finish="stop", empty=False, reasoning=100, marker=False):
    return {"agent_contact_id": agent, "role": role, "prompt_tokens": 8000, "completion_tokens": tokens, "latency_seconds": seconds, "finish_reason": finish,
            "empty_content": empty, "no_json_object": False, "marker_in_content": marker, "reasoning_chars": reasoning, "forced_close": forced}


def _synthetic_contacts(rows, *, cap_hit=False, forced_size3=True):
    out = []
    for row in rows:
        mapping = reader.arm_contact_map([row])
        sizes = {b["branch_id"]: reader.list_size(b) for b in row["branches"]}
        for contact, (arm, node) in mapping.items():
            if node == "perception":
                out.append(_contact(contact, "perception", 1500, 59.0))
            else:
                forced = bool(forced_size3 and sizes[arm] >= 3)
                out.append(_contact(contact, "solver", 4096 if (cap_hit and arm == "lock") else 3200, 64.0, forced=forced))
    return out


def _score_row(tp, fp, fn, intent):
    return {"slu_f1_word_tp": tp, "slu_f1_char_tp": tp, "slu_f1_word_fp": fp, "slu_f1_char_fp": fp, "slu_f1_word_fn": fn, "slu_f1_char_fn": fn, reader.INTENT_FIELD: intent}


def _arms_scores(ids, *, gain=0.0, intent=1.0):
    base = {i: _score_row(3.0, 1.0, 1.0, 1.0) for i in ids}
    better = {i: _score_row(3.0 + gain, 1.0, max(0.0, 1.0 - gain), intent) for i in ids}
    arms = {arm: (better if arm in fam.CANDIDATE_ARMS else base) for arm in fam.ARM_ORDER}
    arms["l1-support-sample0"] = dict(base)
    return arms


def _contrast(l1, l2, twin=(0.0, 0.0)):
    """A contrast record with controlled CI95s (pp): ``l1`` / ``l2`` are ``((slu point, lo, hi), (intent point, lo, hi))``; ``twin`` is (SLU point, intent point)."""

    def iv(point, lo, hi):
        return {"point_pp": point, "ci95_lo_pp": lo, "ci95_hi_pp": hi}

    versus = {fam.TWIN: {"slu_f1": iv(twin[0], twin[0] - 1, twin[0] + 1), "intent": iv(twin[1], twin[1] - 0.5, twin[1] + 0.5), "intent_saves_harms_ties_vs_delivering": {}}}
    for arm, (slu, intent) in (("l1-support", l1), ("l2-union", l2)):
        versus[arm] = {"slu_f1": iv(*slu), "intent": iv(*intent), "intent_saves_harms_ties_vs_delivering": {}}
    return {"versus_delivering": versus}


NEUTRAL_SIDE = ((0.0, -0.5, 0.5), (0.0, -0.5, 0.5))


def _words(contrast):
    return {a: w["word"] for a, w in reader.arm_words(contrast)["words"].items()}


def test_the_l1_words_are_nominated_harm_neutral_against_the_floors():
    w = lambda slu, intent, twin=(0.4, 0.0): _words(_contrast((slu, intent), NEUTRAL_SIDE, twin))["l1-support"]  # noqa: E731
    assert w((2.5, 1.6, 3.4), (0.0, -0.5, 0.5)) == "NOMINATED"
    assert w((1.49, 1.49, 3.0), (0.0, -0.5, 0.5)) == "NOMINATED"                    # CI-LB exactly at the 1.49 floor clears it
    assert w((2.5, 1.6, 3.4), (-0.4, -1.5, -0.65)) == "NOMINATED"                   # intent CI-UB exactly at -0.65: no resolved intent loss
    assert w((2.5, 1.6, 3.4), (-3.0, -4.0, -1.0)) == "HARM"                         # the SLU gain does not rescue a resolved intent loss
    assert w((1.0, 0.2, 1.8), (0.0, -0.5, 0.5)) == "NEUTRAL"                        # positive but short of the floor
    assert w((1.48, 1.48, 3.0), (0.0, -0.5, 0.5)) == "NEUTRAL"                      # CI-LB just under the floor
    assert w((0.0, -0.5, 0.5), (0.0, -0.5, 0.5)) == "NEUTRAL"
    assert w((-1.0, -2.0, -1.4), (0.0, -0.5, 0.5)) == "NEUTRAL"                     # SLU CI-UB -1.4 >= -1.49: a loss that is not resolved
    assert w((-3.0, -4.0, -2.0), (0.0, -0.5, 0.5)) == "HARM"                        # SLU CI-UB below -1.49
    assert w((0.0, -0.5, 0.5), (-1.5, -2.0, -0.7)) == "HARM"                        # intent CI-UB below -0.65
    assert w((0.0, -0.5, 0.5), (-1.5, -2.0, -0.65)) == "NEUTRAL"                    # intent CI-UB exactly -0.65 is not below the floor
    # the twin is the noise bar only: it never moves a word
    assert w((2.5, 1.6, 3.4), (0.0, -0.5, 0.5), twin=(5.0, 5.0)) == "NOMINATED"
    assert w((1.0, 0.2, 1.8), (0.0, -0.5, 0.5), twin=(0.0, 0.0)) == "NEUTRAL"
    assert reader.arm_words(_contrast(((2.5, 1.6, 3.4), (0.0, -0.5, 0.5)), NEUTRAL_SIDE))["words"]["l1-support"]["next_step"] == "335 B Fold A column"


def test_the_l2_words_are_nominated_harm_neutral_against_the_floors():
    w = lambda intent, slu, twin=(0.0, 0.2): _words(_contrast(NEUTRAL_SIDE, (slu, intent), twin))["l2-union"]  # noqa: E731
    assert w((1.0, 0.7, 1.3), (0.0, -0.5, 0.5)) == "NOMINATED"
    assert w((0.65, 0.65, 1.2), (0.0, -0.5, 0.5)) == "NOMINATED"                    # CI-LB exactly at the 0.65 floor clears it
    assert w((1.0, 0.7, 1.3), (-1.0, -2.0, -1.49)) == "NOMINATED"                   # SLU CI-UB exactly at -1.49: no resolved SLU loss
    assert w((1.0, 0.7, 1.3), (-3.0, -4.0, -2.0)) == "HARM"                         # the intent gain does not rescue a resolved SLU loss
    assert w((0.5, 0.1, 0.9), (0.0, -0.5, 0.5)) == "NEUTRAL"                        # previously unreachable: positive but short of the floor
    assert w((0.0, -0.5, 0.5), (0.0, -0.5, 0.5)) == "NEUTRAL"
    assert w((0.64, 0.64, 1.2), (0.0, -0.5, 0.5)) == "NEUTRAL"                      # CI-LB just under the floor
    assert w((-0.3, -1.0, -0.2), (0.0, -0.5, 0.5)) == "NEUTRAL"                     # intent CI-UB -0.2 >= -0.65: a loss that is not resolved
    assert w((-1.5, -2.0, -0.7), (0.0, -0.5, 0.5)) == "HARM"                        # intent CI-UB below -0.65
    assert w((0.0, -0.5, 0.5), (-3.0, -4.0, -2.0)) == "HARM"                        # SLU CI-UB below -1.49
    assert w((0.0, -0.5, 0.5), (-1.0, -2.0, -1.4)) == "NEUTRAL"
    # the twin is the noise bar only: it never moves a word
    assert w((0.5, 0.1, 0.9), (0.0, -0.5, 0.5), twin=(0.0, 0.0)) == "NEUTRAL"
    assert w((1.0, 0.7, 1.3), (0.0, -0.5, 0.5), twin=(5.0, 5.0)) == "NOMINATED"
    assert reader.arm_words(_contrast(NEUTRAL_SIDE, ((0.0, -0.5, 0.5), (1.0, 0.7, 1.3))))["words"]["l2-union"]["next_step"] == "335 B Fold A column"
    # every word of the three-word vocabulary is reachable for BOTH arms (NOMINATED and HARM are disjoint), and NO-RESOLVED-LOSS exists for neither
    grid = (-4.0, -2.0, -1.4, -0.7, -0.5, 0.0, 0.5, 0.9, 1.3, 1.6, 3.0)
    seen = {"l1-support": set(), "l2-union": set()}
    for lo in grid:
        for hi in grid:
            if lo > hi:
                continue
            for other_lo, other_hi in ((-0.5, 0.5), (-4.0, -2.0), (0.7, 1.7)):
                iv_ = ((lo + hi) / 2, lo, hi)
                guard = ((other_lo + other_hi) / 2, other_lo, other_hi)
                seen["l1-support"].add(_words(_contrast((iv_, guard), NEUTRAL_SIDE))["l1-support"])
                seen["l2-union"].add(_words(_contrast(NEUTRAL_SIDE, (guard, iv_)))["l2-union"])
    assert seen == {"l1-support": {"NOMINATED", "HARM", "NEUTRAL"}, "l2-union": {"NOMINATED", "HARM", "NEUTRAL"}}
    assert list(reader.WORDS) == ["NOMINATED", "HARM", "NEUTRAL"] and "NO-RESOLVED-LOSS" not in reader.WORDS


def test_the_discordance_table_reports_every_arm_against_the_lock_beside_the_twin():
    ids = [f"s{i}" for i in range(20)]
    base = {i: _score_row(3.0, 1.0, 1.0, 1.0) for i in ids}
    twin = {i: (_score_row(3.0, 2.0, 1.0, 1.0) if n < 2 else dict(base[i])) for n, i in enumerate(ids)}                        # 2 / 20 rows differ (SLU side)
    sampled = {i: (_score_row(3.0, 2.0, 1.0, 1.0) if n < 8 else dict(base[i])) for n, i in enumerate(ids)}                     # 8 / 20 rows differ
    sampled_intent = {i: (dict(base[i], **{reader.INTENT_FIELD: 0.0}) if n < 4 else dict(base[i])) for n, i in enumerate(ids)}   # 4 / 20 differ, intent side only
    arms = {"lock": base, "aa": twin, "l1-support": sampled, "l2-union": sampled_intent}
    table = reader.discordance_table(arms, ids)
    assert table["delivering"] == "lock" and table["twin"] == "aa" and "lock" not in table["arms"] and table["twin_slu_discordant_share"] == 0.1
    assert table["arms"]["aa"]["slu_discordant_rows"] == 2 and table["arms"]["aa"]["is_twin"] is True and table["arms"]["aa"]["slu_discordant_share_over_twin"] == 1.0
    d1 = table["arms"]["l1-support"]
    assert d1["slu_discordant_rows"] == 8 and d1["slu_discordant_share"] == 0.4 and d1["slu_discordant_share_over_twin"] == 4.0 and d1["intent_discordant_rows"] == 0
    d2 = table["arms"]["l2-union"]
    assert d2["slu_discordant_rows"] == 0 and d2["intent_discordant_rows"] == 4 and d2["any_discordant_rows"] == 4
    zero = reader.discordance_table({"lock": base, "aa": dict(base), "l1-support": sampled}, ids)
    assert zero["arms"]["aa"]["slu_discordant_rows"] == 0 and zero["arms"]["l1-support"]["slu_discordant_share_over_twin"] != zero["arms"]["l1-support"]["slu_discordant_share_over_twin"]


def test_the_writer_words_are_the_readers_words_in_order():
    import l338_write_registration as writer  # noqa: PLC0415

    assert list(writer.WORD_RULES) == ["L1", "L2"] and writer.WORD_ORDER == {"L1": ["NOMINATED", "HARM", "NEUTRAL"], "L2": ["NOMINATED", "HARM", "NEUTRAL"]}
    assert sorted(reader.WORDS) == sorted(writer.WORD_ORDER["L1"]) == sorted(writer.WORD_ORDER["L2"])
    for lever in ("L1", "L2"):
        assert set(writer.WORD_RULES[lever]) == {"primary", "guard", "NOMINATED", "HARM", "NEUTRAL"}
    assert writer.WORD_RULES["L1"]["primary"] == "slu" and writer.WORD_RULES["L2"]["primary"] == "intent"
    assert "SLU delta CI95 lower bound >= 1.49" in writer.WORD_RULES["L1"]["NOMINATED"] and "intent delta CI95 upper bound >= -0.65" in writer.WORD_RULES["L1"]["NOMINATED"]
    assert "< -1.49" in writer.WORD_RULES["L1"]["HARM"] and "< -0.65" in writer.WORD_RULES["L1"]["HARM"]
    assert "intent delta CI95 lower bound >= 0.65" in writer.WORD_RULES["L2"]["NOMINATED"] and "SLU delta CI95 upper bound >= -1.49" in writer.WORD_RULES["L2"]["NOMINATED"]
    assert "< -0.65" in writer.WORD_RULES["L2"]["HARM"] and "< -1.49" in writer.WORD_RULES["L2"]["HARM"]
    for arm, lever in fam.ARM_LEVER.items():
        assert reader.LEVER_OF[arm] == lever


def test_reader_paired_contrast_end_to_end_with_the_twin():
    ids = [f"s{i}" for i in range(40)]
    arms = _arms_scores(ids, gain=1.0, intent=1.0)
    rows = _outputs_rows(40)
    contacts = _synthetic_contacts(rows)
    by_arm = reader.npc.attribute(contacts, reader.arm_contact_map(rows))
    result = reader.read_stage(arms, ids, lambda sid: sid, lambda sid: "alarm" if int(sid[1:]) % 2 else "play", by_arm, reader.contact_rows(rows, contacts), draws=200)
    assert result["schema"] == reader.SCHEMA_READ and result["contrast"]["delivering"] == "lock"
    assert set(result["contrast"]["versus_delivering"]) == set(fam.ARM_ORDER) - {"lock"} | {"l1-support-sample0"}
    assert result["contrast"]["versus_delivering"]["aa"]["slu_f1"]["point_pp"] == 0.0 and result["contrast"]["versus_delivering"]["l1-support"]["slu_f1"]["point_pp"] > 0
    assert result["arm_words"]["words"]["l1-support"]["word"] == "NOMINATED" and result["arm_words"]["words"]["l1-support"]["lever"] == "L1"
    assert set(result["arm_words"]["words"]) == set(fam.CANDIDATE_ARMS)
    assert set(result["per_scenario"]["scenarios"]) == {"alarm", "play"} and "natural_mixture" in result["per_scenario"] and "equal_scenario" in result["per_scenario"]
    assert "l1-support-sample0" not in result["per_scenario"]["natural_mixture"].__repr__().replace("slu_d_l1-support-sample0_pp", "")
    pure = result["l1_pure_filter"]
    assert pure["delta_vs_own_sample0"]["slu_f1"]["point_pp"] > 0 and pure["filter_effect"]["rows"] == 40 and "second A/A" in pure["note"]
    assert result["l2_gold_tables"]["status"].startswith("not computed")
    text = reader.render_markdown(result)
    assert text.startswith("# ") and "Discordance" not in text and "L1 pure filter" in text
    assert result["discordance"]["arms"]["aa"]["slu_discordant_rows"] == 0 and result["discordance"]["arms"]["l1-support"]["slu_discordant_rows"] == 40
    json.dumps(result)


def test_forced_close_share_is_split_by_list_size_and_empty_gold_false_fill_by_forced_status():
    rows = _outputs_rows(8, lists=(2, 3))
    contacts = _synthetic_contacts(rows, forced_size3=True)
    joined = reader.contact_rows(rows, contacts)
    split = reader.forced_by_list_size(joined, "l2-union")
    assert split["2"]["contacts"] == 4 and split["2"]["forced"] == 0 and split["2"]["forced_share"] == 0.0
    assert split["3"]["contacts"] == 4 and split["3"]["forced"] == 4 and split["3"]["forced_share"] == 1.0
    assert reader.list_size_bin(2) == "2" and reader.list_size_bin(3) == "3" and reader.list_size_bin(5) == "other" and reader.list_size_bin(0) == "other"
    # l1 and lock see their own note's two candidates, so their contacts are all in the size-2 bin and none is forced
    assert reader.forced_by_list_size(joined, "lock")["2"] == {"contacts": 8, "forced": 0, "no_wire": 0, "forced_share": 0.0}
    scores = {}
    for i in range(8):
        sid = f"s{i}"
        forced = i % 2 == 1
        scores[sid] = _score_row(0.0, 1.0 if forced else 0.0, 0.0, 1.0)                    # empty gold (tp = fn = 0); an entity emitted only on the forced rows
    scores["s8"] = _score_row(2.0, 0.0, 0.0, 1.0)                                          # a non-empty gold row, exact
    fill = reader.empty_gold_false_fill(scores, {c["sample_id"]: c["forced_close"] for c in joined if c["arm"] == "l2-union"}.get)
    assert fill["empty_gold_rows"] == 8 and fill["false_fill_rows"] == 4
    assert fill["forced"] == {"rows": 4, "false_fill": 4, "false_fill_share": 1.0} and fill["natural"]["rows"] == 4 and fill["natural"]["false_fill"] == 0
    assert reader.nonempty_exact(scores) == {"nonempty_gold_rows": 1, "exact_rows": 1, "exact_share": 1.0}
    tables = reader.tables_by_arm(reader.npc.attribute(contacts, reader.arm_contact_map(rows)))
    sec = reader.arm_secondaries({"l2-union": scores, "l1-support-sample0": scores}, joined, tables)
    assert set(sec) == {"l2-union"}                                                         # the stream column has no Solver contact of its own
    assert sec["l2-union"]["solver_forced_close_share"] == 0.5 and sec["l2-union"]["forced_close_by_list_size"]["3"]["forced"] == 4


def test_the_l1_filter_effect_counts_false_fills_removed_and_exact_rows_lost_or_gained():
    ids = ["a", "b", "c", "d", "e"]
    sample0 = {"a": _score_row(0, 1, 0, 1), "b": _score_row(0, 1, 0, 1), "c": _score_row(2, 0, 0, 1), "d": _score_row(1, 1, 1, 1), "e": _score_row(0, 0, 0, 1)}
    committed = {"a": _score_row(0, 0, 0, 1), "b": _score_row(0, 1, 0, 1), "c": _score_row(1, 0, 1, 1), "d": _score_row(2, 0, 0, 1), "e": _score_row(0, 1, 0, 1)}
    effect = reader.l1_filter_effect(committed, sample0, ids)
    assert effect["empty_gold_false_fills_removed"] == 1 and effect["empty_gold_false_fills_added"] == 1
    assert effect["nonempty_exact_lost"] == 1 and effect["nonempty_exact_gained"] == 1 and effect["rows"] == 5


def test_reader_counts_cap_hits_and_tabulates_the_throughput():
    rows = _outputs_rows(4)
    mapping = reader.arm_contact_map(rows)
    contacts = _synthetic_contacts(rows)
    good = reader.smoke_stage(reader.npc.attribute(contacts, mapping), missing=reader.missing_columns(rows, contacts))
    assert set(good["arms"]) == set(fam.ARM_ORDER) and good["arms"]["lock"]["solver"]["contacts"] == 4 and good["arms"]["lock"]["solver"]["cap"] == 4096
    assert good["arms"]["l1-support"]["solver"]["contacts"] == 20 and good["arms"]["l1-support"]["perception"]["contacts"] == 4          # five Solver samples per row
    assert good["arms"]["l2-union"]["perception"]["contacts"] == 16 and good["arms"]["l2-union"]["solver"]["contacts"] == 4             # four Perception samples per row
    assert good["absent_columns"] == 0 and good["unattributed_contacts"] == 0
    tp = good["throughput"]
    assert tp["arm_mix_registered_rows"] == fam.ARM_MIX_ROWS and abs(tp["arm_mix_measured_rows"] - (7 * 59.0 + 8 * 64.0) / (59.0 + 64.0)) < 1e-9
    assert tp["contacts_per_row_by_arm"]["l1-support"] == {"perception": 1.0, "solver": 5.0} and tp["contacts_per_row_by_arm"]["l2-union"] == {"perception": 4.0, "solver": 1.0}
    checks = smoke_signoff.evaluate(fam.signoff_conditions(), good)
    assert checks and all(c["ok"] for c in checks), [c for c in checks if not c["ok"]]
    capped = reader.smoke_stage(reader.npc.attribute(_synthetic_contacts(rows, cap_hit=True), mapping))
    assert good["arms"]["lock"]["solver"]["cap_hits"] == 0 and capped["arms"]["lock"]["solver"]["cap_hits"] == 4
    assert any(not c["ok"] for c in smoke_signoff.evaluate(fam.signoff_conditions(), capped))
    # a declared arm column whose Solver contact is missing from the trace is counted (absent_columns)
    short = [c for c in contacts if c["agent_contact_id"] != "s3:lock:s0"]
    missing = reader.missing_columns(rows, short)
    assert missing["total"] == 1 and missing["by_arm"]["lock"] == 1


def test_the_reader_loads_only_ids_from_the_sealed_outputs(tmp_path):
    path = tmp_path / "outputs.jsonl"
    secret = "A-SECRET-TRANSCRIPT"
    branch = {"branch_id": "l1-support", "contact_id": "c:p", "solver_contact_id": "c:s0", "candidate_intent_ids": ["i:a"], "note_text": secret,
              "sampling": {"solver_samples": {"samples": [{"contact_id": "c:s0", "parse_status": "ok", "response_text": secret}, {"contact_id": "c:s1", "parse_status": "ok"}],
                                              "outcome": {"delivered_entity_count": 1, "entity_supports": [{"type": "place_name", "support": 2}]}}, "perception_samples": None}}
    path.write_text(json.dumps({"sample_id": "s0", "delivered": secret, "native_episode_receipt": {
        "perception_branches": {"branches": [branch]},
        "role_visits": [{"stage": "solver", "execution_receipt": {"contacts": [{"agent_contact_id": "c:s0", "request_id": "rails-1"}, {"agent_contact_id": "c:s1", "request_id": "rails-2"}]}}]}}) + "\n",
        encoding="utf-8")
    rows = reader.load_outputs_rows(path)
    assert secret not in json.dumps(rows) and rows[0]["requests"] == {"c:s0": "rails-1", "c:s1": "rails-2"}
    assert rows[0]["branches"][0]["solver_samples"]["samples"] == [{"contact_id": "c:s0", "parse_status": "ok"}, {"contact_id": "c:s1", "parse_status": "ok"}]
    assert reader.arm_contact_map(rows) == {"c:p": ("l1-support", "perception"), "c:s0": ("l1-support", "solver"), "c:s1": ("l1-support", "solver")}


def test_answer_keys_and_stream_discordance_compare_parsed_answers_not_text():
    assert reader.answer_key(_answer("paris")) == reader.answer_key(json.dumps(json.loads(_answer("paris")), indent=2)) == ("s", "a", (("place_name", "paris"),))
    assert reader.answer_key("not json") == ("malformed",) and reader.answer_key(None) == ("absent",)
    ids = [f"s{i}" for i in range(10)]
    lock = {i: reader.answer_key(_answer("paris")) for i in ids}
    twin = {i: (reader.answer_key(_answer("rome")) if n < 1 else lock[i]) for n, i in enumerate(ids)}                          # 1 / 10 differ
    sample = {i: (reader.answer_key(_answer("paris", "rome")) if n < 4 else lock[i]) for n, i in enumerate(ids)}               # 4 / 10 differ
    table = reader.stream_discordance({"lock": lock, "aa": twin, "l1-support.s2": sample}, ids)
    assert table["twin_discordant_share"] == 0.1 and table["streams"]["aa"]["is_twin"] and table["streams"]["l1-support.s2"]["discordant_rows"] == 4
    assert table["streams"]["l1-support.s2"]["share_over_twin"] == 4.0 and "lock" not in table["streams"]
    rows = _outputs_rows(3)
    notes = reader.perception_stream_keys(rows)
    assert {"lock", "aa", "l1-support", "l2-union", "l2-union.s0", "l2-union.s3", "l2-union.merged"} <= set(notes)
    assert notes["l2-union.merged"]["s1"] == ("i:0", "i:1", "i:2") and notes["l2-union"]["s0"] == notes["l2-union.s0"]["s0"]
    response_keys = {f"req-{r['branches'][0]['solver_contact_id']}": reader.answer_key(_answer("paris")) for r in rows}
    streams = reader.solver_stream_keys(rows, response_keys)
    assert set(streams) >= {"lock", "aa", "l2-union", "l1-support", "l1-support.s0", "l1-support.s4"} and streams["l1-support"]["s0"] == reader.answer_key(_answer("paris"))
    assert streams["lock"]["s0"] == ("absent",)


def test_the_sampling_tables_come_from_the_render_custody():
    rows = [{"sample_id": f"s{i}", "branches": {
        "l1-support": {"n": 5, "entity_supports": [{"type": "place_name", "support": 2 + i % 2}], "delivered_entity_count": 1, "base_entity_count": 2 if i < 2 else 1,
                       "gate": {"status": "n1-unavailable"}, "parse_status": ["ok"] * 4 + ["malformed"]},
        "l2-union": {"perception_samples": {"merged_candidate_ids": ["a", "b", "c"][: 2 + i % 2], "appended_candidate_ids": ["c"][: i % 2],
                                            "sample_lists": [{"candidate_intent_ids": ["a", "b"]}, {"candidate_intent_ids": ["c"]}]}}}} for i in range(4)]
    support = reader.support_count_table(rows)
    assert support["rows"] == 4 and support["delivered_entities_by_support"] == {"2": 2, "3": 2} and support["base_entities_total"] == 6 and support["delivered_entities_total"] == 4
    assert support["dropped_entities_total"] == 2 and support["rows_with_a_drop"] == 2 and support["rows_emptied"] == 0
    assert support["gate_status_counts"] == {"n1-unavailable": 4} and support["sample_parse_status_counts"] == {"ok": 16, "malformed": 4}
    union = reader.union_size_table(rows)
    assert union["rows"] == 4 and union["merged_list_size"] == {"2": 2, "3": 2} and union["appended_count"] == {"0": 2, "1": 2} and union["rows_where_the_merge_changed_sample0"] == 2
    assert union["per_sample_list_size"] == {"1": 4, "2": 4}


def _raw_row(view):
    """A sealed outputs row (receipts only; a secret delivered text) from a ``load_outputs_rows``-shaped view."""

    branches = []
    for b in view["branches"]:
        sampling = {"perception_samples": None, "solver_samples": None}
        if b["perception_samples"]:
            sampling["perception_samples"] = {"merged_candidate_ids": b["perception_samples"]["merged_ids"], "appended_candidate_ids": b["perception_samples"]["appended_ids"],
                                              "samples": [{"contact_id": s["contact_id"], "candidate_intent_ids": s["candidate_ids"], "note_parse_status": "ok"}
                                                          for s in b["perception_samples"]["samples"]]}
        if b["solver_samples"]:
            sampling["solver_samples"] = {"samples": b["solver_samples"]["samples"], "outcome": b["solver_samples"]["outcome"]}
        branches.append({"branch_id": b["branch_id"], "contact_id": b["contact_id"], "solver_contact_id": b["solver_contact_id"], "candidate_intent_ids": b["candidate_ids"],
                         "sampling": sampling})
    contacts = [{"agent_contact_id": c, "request_id": r} for c, r in view["requests"].items()]
    return {"sample_id": view["sample_id"], "text": "A-SECRET-TRANSCRIPT", "native_episode_receipt": {
        "perception_branches": {"branches": branches}, "role_visits": [{"stage": "solver", "execution_receipt": {"contacts": contacts}}]}}


def _write_sealed(tmp_path, rows, run, attempt, *, answers=None):
    run_dir = tmp_path / "runs" / run / attempt
    run_dir.mkdir(parents=True)
    (run_dir / f"{run}.outputs.jsonl").write_text("".join(json.dumps(_raw_row(r)) + "\n" for r in rows), encoding="utf-8")
    lines = []
    for row in rows:
        mapping = reader.arm_contact_map([row])
        requests = {v: k for k, v in row["requests"].items()}
        for contact, (arm, node) in mapping.items():
            request = row["requests"].get(contact) or f"req-{contact}"
            lines.append({"channel": "COST", "record_id": f"{request}/cost", "payload": {"prompt_tokens": 8000, "completion_tokens": 1500 if node == "perception" else 3200,
                                                                                         "latency_seconds": 59.0 if node == "perception" else 64.0}})
            lines.append({"channel": "USE", "record_id": f"{request}/native-role-contact", "payload": {"use_agent_contact_id": contact, "use_role_id": node}})
            if answers is not None and node == "solver":
                lines.append({"channel": "MODEL_RESPONSE", "record_id": f"{request}/response", "payload": {"text": answers(row["sample_id"], contact)}})
        del requests
    (run_dir / f"{run}.trace.jsonl").write_text("".join(json.dumps(line) + "\n" for line in lines), encoding="utf-8")
    return run_dir


def test_the_smoke_stage_runs_end_to_end_over_a_sealed_smoke_and_keeps_no_text(tmp_path):
    rows = _outputs_rows(4)
    cell = fam.CELLS["smoke"]
    # the l1 and l2 branches own extra contacts; give every contact of the view a request id so the trace joins by id
    for row in rows:
        for b in row["branches"]:
            for sample in (b["solver_samples"] or {}).get("samples", []) + (b["perception_samples"] or {}).get("samples", []):
                row["requests"].setdefault(sample["contact_id"], f"req-{sample['contact_id']}")
    _write_sealed(tmp_path, rows, cell["run"], cell["attempt"])
    out = tmp_path / "analysis"
    assert reader.main(["--stage", "smoke", "--data-root", str(tmp_path), "--analysis-root", str(out)]) == 0
    result = json.loads((out / "smoke-decode-cost.json").read_text(encoding="utf-8"))
    assert result["schema"] == fam.SMOKE_SCHEMA and set(result["arms"]) == set(fam.ARM_ORDER) and result["absent_columns"] == 0 and result["unattributed_contacts"] == 0
    assert abs(result["throughput"]["arm_mix_measured_rows"] - (7 * 59.0 + 8 * 64.0) / (59.0 + 64.0)) < 1e-9
    assert "A-SECRET-TRANSCRIPT" not in (out / "smoke-decode-cost.json").read_text(encoding="utf-8")
    assert reader.main(["--stage", "smoke", "--data-root", str(tmp_path), "--analysis-root", str(out)]) == 6          # write-once
    checks = smoke_signoff.evaluate(fam.signoff_conditions(), result)
    assert checks and [c for c in checks if not c["ok"]] == [], [c for c in checks if not c["ok"]]


def test_the_trace_reads_reduce_response_texts_to_keys_and_feed_the_l1_forms(tmp_path):
    rows = _outputs_rows(2)
    for row in rows:
        for b in row["branches"]:
            for sample in (b["solver_samples"] or {}).get("samples", []) + (b["perception_samples"] or {}).get("samples", []):
                row["requests"].setdefault(sample["contact_id"], f"req-{sample['contact_id']}")

    def answers(sid, contact):
        j = contact.rsplit(":s", 1)[-1]
        if "l1-support" in contact:
            return _answer("paris", "rome") if j == "0" else _answer("paris") if j in ("1", "2") else _answer()
        return _answer("paris")

    run_dir = _write_sealed(tmp_path, rows, "RUN", "ATT", answers=answers)
    trace = run_dir / "RUN.trace.jsonl"
    wanted = {r for row in rows for r in row["requests"].values()}
    keys = reader.trace_response_keys(trace, wanted)
    assert keys["req-s0:l1-support:s0"] == ("s", "a", (("place_name", "paris"), ("place_name", "rome"))) and keys["req-s0:lock:s0"] == ("s", "a", (("place_name", "paris"),))
    assert "A-SECRET" not in json.dumps(keys)
    streams = reader.solver_stream_keys(rows, keys)
    assert streams["l1-support.s3"]["s0"] == ("s", "a", ()) and streams["lock"]["s1"] == streams["aa"]["s1"]
    forms = reader.l1_forms_from_trace(rows, trace, None)
    assert forms["s2_filter_only"]["rows"] == 2 and forms["s2_filter_only"]["entities_dropped"] == 2 and forms["s2_filter_only"]["rows_emptied"] == 0     # rome lacks support
    assert forms["s3_gated"]["entities_dropped"] >= 2 and forms["s2_gated"]["gate_n1_unavailable_rows"] == 2


def test_the_l2_gold_tables_need_a_gold_join_and_count_recall_and_conversion_by_position():
    rows = _outputs_rows(4, lists=(3,))
    ids = [r["sample_id"] for r in rows]
    gold = {"s0": "i:0", "s1": "i:2", "s2": "i:1", "s3": "i:9"}
    l2 = {i: _score_row(1, 0, 0, 1.0 if i in ("s0", "s2") else 0.0) for i in ids}
    lock = {i: _score_row(1, 0, 0, 1.0 if i == "s0" else 0.0) for i in ids}
    table = reader.l2_gold_tables(rows, gold, l2, lock, ids)
    assert table["rows"] == 4 and table["recall_merged_list"] == 0.75 and table["recall_sample0_list"] == 0.5 and table["recall_lock_note"] == 0.5
    assert table["gold_newly_listed_rows"] == 1 and table["gold_lost_rows"] == 0
    pos = table["conversion_by_gold_position_in_merged_list"]
    assert pos["1"] == {"rows": 1, "l2_intent_correct": 1, "lock_intent_correct": 1} and pos["2"] == {"rows": 1, "l2_intent_correct": 1, "lock_intent_correct": 0}
    assert pos["3"]["rows"] == 1 and pos["absent"]["rows"] == 1 and pos["absent"]["l2_intent_correct"] == 0


def test_the_l1_forms_report_counts_and_the_n1_gate_is_unavailable_without_a_join():
    rows = _outputs_rows(2)
    texts = {"s0": [_answer("paris", "rome"), _answer("paris"), _answer("paris"), _answer(), _answer("paris")],
             "s1": [_answer("paris"), _answer(), _answer(), _answer(), _answer()]}
    forms = reader.l1_forms(rows, texts, None)
    assert forms["s2_filter_only"] == {"rows": 2, "rows_with_a_changed_entity_list": 1, "entities_dropped": 1, "rows_emptied": 1, "gate_n1_unavailable_rows": 0} or \
        forms["s2_filter_only"]["entities_dropped"] == 2
    assert forms["s2_gated"]["gate_n1_unavailable_rows"] == 2 and forms["s3_gated"]["gate_n1_unavailable_rows"] == 2
    assert forms["s3_gated"]["entities_dropped"] >= forms["s2_filter_only"]["entities_dropped"]
    fired = reader.l1_forms(rows, texts, {"s0": 0.0, "s1": 0.9})
    assert fired["s2_gated"]["gate_n1_unavailable_rows"] == 0 and fired["s2_gated"]["rows_emptied"] >= forms["s2_filter_only"]["rows_emptied"]
    assert fired["gate_only"]["entities_dropped"] >= 1                                       # s1: N1 0.9 and four empty samples empty the row's single entity


# ---- recovery: the generic lib is wired, EMPTY now -------------------------------------------------------------------------------------------


def _snapshot() -> dict:
    return {"schema": "saea-recovery-predecessor-snapshot-v1", "run_id": fam.CELLS["arm"]["run"], "attempt_id": fam.CELLS["arm"]["attempt"], "state": "OPENED",
            "actual_calls": 700, "actual_audio_seconds": 1900.5, "reserved_calls": fam.generation_calls("arm"), "reserved_audio_seconds": float(fam.audio_cap("arm")),
            "fit": {"run_id": fam.CELLS["arm"]["fit_run"], "attempt_id": fam.CELLS["arm"]["fit_attempt"], "attempt_record_present": False, "prepared_dir_present": True,
                    "prepared_request_fit_envelopes": 700}}


def test_recovery_is_empty_now_and_the_rec1_path_is_data_driven(tmp_path):
    assert fam.plan_file_name("arm", "generation") == "generation-plan-registered-v1.json" and fam.superseded_plan_file_names("arm") == []
    assert fam.predecessor_spend("arm") == (0, 0.0) and fam.cumulative_budget("arm", 100, 50.0) == (100, 50)
    root = tmp_path / "repo"
    (root / fam.PACKAGE).mkdir(parents=True)
    (root / fam.PREDECESSOR_SNAPSHOTS["arm"][0]).write_text(json.dumps(_snapshot()), encoding="utf-8")
    (root / fam.RECOVERY_INPUTS["arm"][0]).write_text(json.dumps({
        "recovered_at": "2026-10-25", "ledger_title": "the column flight re-registration", "agent": "the L338 recovery agent", "reason": "host restart",
        "root_cause": "infrastructure, not the cell", "fix": "none in the cell", "decision": "owner decision 309 A"}), encoding="utf-8")
    history = fam._load_history(root)
    assert set(history) == {"arm"} and len(history["arm"]) == 1 and history["arm"][0]["predecessors"][0]["contacts_spent"] == 700 and history["arm"][0]["recovery_index"] == 1
    fam.rcv.validate_recovery(history["arm"][0])
    assert fam._load_history(tmp_path) == {}
    with pytest.raises(ValueError, match="root_cause"):
        fam.build_arm_recovery({"recovered_at": "x"}, _snapshot())


def test_the_writer_recovery_text_and_flags_are_wired():
    import l338_write_registration as writer  # noqa: PLC0415

    ids = writer.identities(REPO)
    assert writer.recovery_blocks(REPO, ids, "x", "2026-10-25T00:00:00+00:00", "abc", "/wt", "br") == {}
    text = writer.recovery_sequence_text(ids)
    assert "recovery-input-arm-v1.json" in text and "predecessor-snapshot-arm-rec1-v1.json" in text and "L338_KINDS=arm" in text and "arm-only" in text
    out = subprocess.run([sys.executable, "-B", str(NX / "l338_write_registration.py"), "--help"], capture_output=True, text=True, cwd=REPO)
    assert out.returncode == 0
    for flag in ("--append-recovery-ledger", "--recovery-registered-at", "--recovery-base-commit", "--study-commit", "--append-ledger", "--registered-at"):
        assert flag in out.stdout


def test_the_mint_supersedes_only_a_strict_prefix_receipt(tmp_path, monkeypatch):
    from datetime import datetime, timezone

    import l338_mint_receipt as mint  # noqa: PLC0415

    first = fam.eligible_run_ids()
    longer = first + [fam.CELLS["arm"]["fit_run"].replace("-FIT-", "-FIT-REC1-")]
    path = tmp_path / "root-admission-v1.json"
    path.write_text(json.dumps({"decision_id": fam.DECISION_ID, "eligible_run_ids": first}), encoding="utf-8")
    monkeypatch.setattr(fam, "eligible_run_ids", lambda: longer)
    assert mint.check_supersedable(str(path)) == first
    for bad in ({"decision_id": "other", "eligible_run_ids": first}, {"decision_id": fam.DECISION_ID, "eligible_run_ids": longer},
                {"decision_id": fam.DECISION_ID, "eligible_run_ids": list(reversed(first))}, {"decision_id": fam.DECISION_ID, "eligible_run_ids": []}):
        path.write_text(json.dumps(bad), encoding="utf-8")
        with pytest.raises(SystemExit):
            mint.check_supersedable(str(path))
    assert mint.backup_name("/d/root-admission-v1.json", datetime(2026, 10, 25, 17, 0, 5, tzinfo=timezone.utc)) == "/d/root-admission-v1.json.superseded-20261025T170005Z-by-rec1.bak"


# ---- the chain, the flip, the read, the queue hook and the launch spec -----------------------------------------------------------------------


def test_the_chain_uses_the_machine_signoff_and_closes_the_rows():
    chain = (NX / "batch_chain_l338.sh").read_text(encoding="utf-8")
    assert subprocess.run(["bash", "-n", str(NX / "batch_chain_l338.sh")], capture_output=True).returncode == 0
    assert '. "$SP/chain_lib.sh"' in chain
    assert 'wait_or_machine_signoff "bash scripts/flights/nx/l338_read.sh smoke" "$MAIN/$SIGNOFF_CONDITIONS" "$SIGNOFF_MARKER" 20' in chain
    assert "wait_signoff()" not in chain and "sleep 60" not in chain
    assert "SIGNOFF_MARKER=/home/chao/l338-decode-signoff.marker" in chain and "f.SIGNOFF_CONDITIONS" in chain
    assert "close_rows_after_seal" in chain and "close_rows $SMOKE_CLOSE_IDS" in chain and "close_rows $ALL_CLOSE_IDS" in chain
    for needle in ("smoke|arm|arm-only|all) export BATCH_SESSION=$THINK_SESSION", "arm-only) run_driver arm", "exit 9", '"$SMOKE_STATE" = sealed', "COMPLETED", "no sign-off marker",
                   "serving_swap.sh \"$SWAP_TARGET\"", "l338_family", "L338_SIGNOFF_WAIT_SECONDS", "is not resident; swapping to"):
        assert needle in chain, needle
    assert "SHORT=l338" in chain and "/home/chao/$SHORT-flight-commit.txt" in chain and 'spec["attempt"]' in chain and "nxt_r2b" not in chain and "7168" not in chain


def test_the_flip_read_and_repin_scripts_consume_the_family_record():
    flip, read, repin = [(NX / n).read_text(encoding="utf-8") for n in ("l338_flip.sh", "l338_read.sh", "l338_repin_cell.sh")]
    assert "PLAN_REC=" in flip and "rec_suffix" in flip and 'L338_KINDS:-"smoke arm"' in flip and "l338_family" in flip
    assert "SLUG=l338-lever-column-fold-b" in flip and "PKGN=slurp-l338-lever-column-fold-b-v1" in flip and "SHORT=l338" in flip
    assert "l338_family" in read and "SAEA-SLURP-L338-LEVER-COLUMN-FOLD-B-READ-V1" in read and "slurp_l338_column_read.py" in read
    assert "--mode perception-branches" in read and "supply-variants" not in read and re.search(r'STAGE=\$\{1:-read\}', read)
    assert '"$STAGE" = "columns"' in read
    assert "L338_KIND" in repin and "l338-lever-column-fold-b" in repin and "2026-10-19" in repin and "2026-10-18" not in repin
    assert f"RD={fam.PACKAGE}".replace("slurp-l338-lever-column-fold-b-v1", "$PKGN") in flip, "the flip's readiness directory must be the package's own (date included)"


TOKEN = "CHAIN_CARRIERTHINK_EXIT"


def _hook(tmp_path, chain_lines, *, stamp="2026-10-18T12:40:00Z", wait="3", poll="0.2", launch=None, token=TOKEN, args=True):
    out, chain = tmp_path / "queue.out", tmp_path / "chain.out"
    chain.write_text("\n".join(chain_lines) + ("\n" if chain_lines else ""), encoding="utf-8")
    ran = tmp_path / "ran.txt"
    launch = launch or f"echo launched-from $(pwd) > {ran}"
    env = dict(os.environ, L338_HOOK_OUT=str(out), L338_HOOK_MAIN=str(tmp_path), L338_HOOK_POLL_SECONDS=poll,
               L338_HOOK_MAX_WAIT_SECONDS=wait, L338_HOOK_LAUNCH_CMD=launch, TMPDIR=str(tmp_path))
    argv = [str(chain), token, stamp] if args else []
    done = subprocess.run(["bash", str(REPO / "scripts/flights/batch/queue/queue_l338_after_chain.sh"), *argv], capture_output=True, text=True, env=env, timeout=60)
    return done, out.read_text(encoding="utf-8") if out.exists() else "", ran


def test_the_queue_hook_launches_only_after_a_clean_predecessor_exit_later_than_the_stamp(tmp_path):
    script = REPO / "scripts/flights/batch/queue/queue_l338_after_chain.sh"
    assert subprocess.run(["bash", "-n", str(script)], capture_output=True).returncode == 0
    text = script.read_text(encoding="utf-8")
    assert "/home/chao/l338-queue.out" in text and "108000" in text and "POLL_SECONDS:-60" in text and "CHAIN_NXT2_EXIT" in text         # only in the usage example
    assert "package_launch.sh scripts/flights/nx/l338_launch_spec.json --from flip --until chain" in text and "exit 9" in text
    (tmp_path / "a").mkdir()
    done, log, ran = _hook(tmp_path / "a", [f"{TOKEN} rc=0 2026-10-18T12:50:00Z"])
    assert done.returncode == 0 and ran.is_file() and "launching L338" in log and "launcher exit rc=0" in log
    (tmp_path / "b").mkdir()
    done, log, ran = _hook(tmp_path / "b", [f"{TOKEN} rc=0 2026-10-18T09:00:00Z"])
    assert done.returncode == 8 and not ran.exists() and "TIMEOUT" in log                       # an older attempt's line is ignored
    (tmp_path / "c").mkdir()
    done, log, ran = _hook(tmp_path / "c", [f"{TOKEN} rc=0 2026-10-18T09:00:00Z", f"{TOKEN} rc=3 2026-10-18T13:00:00Z"])
    assert done.returncode == 9 and not ran.exists() and "rc=3" in log and "NOT launched" in log
    (tmp_path / "d").mkdir()
    done, log, ran = _hook(tmp_path / "d", [f"{TOKEN} rc=0 2026-10-18T13:00:00Z"], launch="exit 4")
    assert done.returncode == 4 and "launcher exit rc=4" in log
    (tmp_path / "e").mkdir()
    done, _, _ = _hook(tmp_path / "e", [], args=False)
    assert done.returncode == 64
    # the predecessor is an ARGUMENT: another chain's exit token does not release it, and the named one does
    (tmp_path / "f").mkdir()
    done, log, ran = _hook(tmp_path / "f", ["CHAIN_NXT2_EXIT rc=0 2026-10-18T13:00:00Z"])
    assert done.returncode == 8 and not ran.exists()
    (tmp_path / "g").mkdir()
    done, log, ran = _hook(tmp_path / "g", ["CHAIN_NXT2_EXIT rc=0 2026-10-18T13:00:00Z"], token="CHAIN_NXT2_EXIT")
    assert done.returncode == 0 and ran.is_file()


def test_the_queue_hook_ignores_the_informational_repin_line_but_not_a_real_refusal(tmp_path):
    info = "repin exit 1 (1 = its internal check refused the dirty tree, expected)"
    (tmp_path / "ok").mkdir()
    done, log, ran = _hook(tmp_path / "ok", [f"{TOKEN} rc=0 2026-10-18T13:00:00Z"], launch=f"echo '{info}'; echo 'FLIP_CHAIN_DONE'")
    assert done.returncode == 0 and "real refusal" not in log and info in log                    # the false match that blocked the R2 rec2 hook
    (tmp_path / "bad").mkdir()
    done, log, _ = _hook(tmp_path / "bad", [f"{TOKEN} rc=0 2026-10-18T13:00:00Z"], launch=f"echo '{info}'; echo 'check: FAIL cell x'")
    assert done.returncode == 10 and "real refusal" in log
    (tmp_path / "bad2").mkdir()
    done, log, _ = _hook(tmp_path / "bad2", [f"{TOKEN} rc=0 2026-10-18T13:00:00Z"], launch="echo 'the gate refused the flip'")
    assert done.returncode == 10 and "real refusal" in log


def test_the_queue_hook_sees_a_line_that_appears_while_it_polls(tmp_path):
    chain = tmp_path / "chain.out"
    chain.write_text("chain start 2026-10-18T12:40:00Z\n", encoding="utf-8")
    ran = tmp_path / "ran.txt"
    env = dict(os.environ, L338_HOOK_OUT=str(tmp_path / "q.out"), L338_HOOK_MAIN=str(tmp_path), L338_HOOK_POLL_SECONDS="0.2",
               L338_HOOK_MAX_WAIT_SECONDS="30", L338_HOOK_LAUNCH_CMD=f"echo ok > {ran}", TMPDIR=str(tmp_path))
    proc = subprocess.Popen(["bash", str(REPO / "scripts/flights/batch/queue/queue_l338_after_chain.sh"), str(chain), TOKEN, "2026-10-18T12:40:00Z"], env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    import time

    time.sleep(1.0)
    assert proc.poll() is None
    with chain.open("a", encoding="utf-8") as handle:
        handle.write(f"{TOKEN} rc=0 2026-10-18T14:00:00Z\n")
    assert proc.wait(timeout=30) == 0 and ran.is_file()


def test_the_launch_spec_is_the_r2b_form_with_the_r4_names():
    spec = js("scripts/flights/nx/l338_launch_spec.json")
    r2b = js("scripts/flights/nx/nxt_r2b_launch_spec.json")
    assert spec["schema"] == "saea-package-launch-spec-v1" == r2b["schema"] and list(spec["steps"]) == list(r2b["steps"]) == ["derive", "write", "countersign", "mint", "commit", "flip", "chain", "read"]
    assert (spec["short"], spec["package"], spec["readiness_dir"]) == ("l338", fam.PKG_NAME, fam.PACKAGE) and spec["launch_id"] == "l338-first-attempt"
    steps = spec["steps"]
    assert steps["derive"]["cmd"].endswith("l338_derive_cells.py") and "l338_write_registration.py --study-commit {head}" in steps["write"]["cmd"]
    assert "--registered-at {utc}" in steps["write"]["cmd"] and "--append-ledger" in steps["write"]["cmd"]
    assert "queue_l338_after_chain.sh" in spec["_note"] and "<chain-out> <exit-token> <start-stamp>" in spec["_note"]
    assert steps["mint"]["cmd"].endswith("l338_mint_receipt.py") and steps["mint"]["done_if"]["contains"] == [fam.CELLS["arm"]["fit_run"]] and steps["mint"]["done_if"]["file"] == fam.DECISION_RELPATH
    assert steps["countersign"]["texts"] == "{readiness_dir}/countersign-row-texts-v1.json" and steps["countersign"]["skip_substrings"] == ["-READ-"]
    assert set(steps["commit"]["paths"]) == {"configs", "docs/exposure-ledger.md", "{readiness_dir}", "{readiness_dir}-preregistration.md"}
    flip = steps["flip"]
    assert flip["script"] == "scripts/flights/nx/l338_flip.sh" and flip["package"] == fam.PACKAGE and flip["env"] == {"L338_KINDS": "smoke arm"}
    assert flip["cells"] == [fam.CELLS["smoke"]["cell"], fam.CELLS["arm"]["cell"]] and flip["pins_commit_msg"] == "/home/chao/l338-pins-commit.txt"
    assert flip["flight_commit_file"] == "/home/chao/l338-flight-commit.txt" == steps["chain"]["flight_commit_file"]
    assert flip["pins_commit_text"].rstrip("\n").splitlines()[-1] == "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>" and flip["pins_commit_text"].startswith("L338")
    assert steps["chain"]["task"] == "SAEA-Chain-L338" and steps["chain"]["wrapper"] == "/home/chao/saea-queue/chain_l338.sh"
    assert steps["read"]["cmd"] == "bash scripts/flights/nx/l338_read.sh smoke"
    wrapper = (REPO / "scripts/flights/batch/queue/chain_l338.sh").read_text(encoding="utf-8")
    assert subprocess.run(["bash", "-n", str(REPO / "scripts/flights/batch/queue/chain_l338.sh")], capture_output=True).returncode == 0
    assert "batch_chain_l338.sh all" in wrapper and "CHAIN_L338_EXIT" in wrapper and "/home/chao/l338-flight-commit.txt" in wrapper
    import package_launch  # noqa: PLC0415

    launch = package_launch.Launch(spec, REPO, dry=True, root_countersign=False, redo=set())
    launch.head = lambda: "0" * 40                     # rendering needs no repository state here (a linked worktree is not readable from every shell)
    assert launch.log_path == Path("/home/chao/l338-launch.out") and launch.render("{readiness_dir}") == fam.PACKAGE


def test_every_script_the_spec_names_exists_and_parses():
    for rel in ("l338_derive_cells.py", "l338_write_registration.py", "l338_mint_receipt.py", "l338_dry_run.py", "l338_family.py"):
        subprocess.run([sys.executable, "-B", "-c", "import ast,sys; ast.parse(open(sys.argv[1], encoding='utf-8').read())", str(NX / rel)], check=True)
    assert (REPO / fam.READER).is_file()
