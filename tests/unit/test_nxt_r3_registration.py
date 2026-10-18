"""NX-T R3 (the Solver instruction-template column on the Thinking core, TRAIN Fold B): package, cells, instrument seam, reader, chain, hook and launch spec.

Model-free: no model, server, tokenizer, GPU or network contact. The cells are the 268-B Thinking lock cell plus the Solver ``template_variants`` block the module
compiler writes; the proofs here are that (1) the arm templates are minimal hash-pinned deltas of the locked Solver template, (2) the compiled cells carry exactly
that block and nothing else moved, (3) a Solver template-arm contact carries the lock's thinking fields at the REQUEST level, (4) the package, the reader's words and
splits, the sign-off, the chain, the queue hook and the launch spec agree with the family.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import shutil
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
import nxt_r3_derive_cells as dc  # noqa: E402
import nxt_r3_family as fam  # noqa: E402
import slurp_nxt_r3_solver_template_column_read as reader  # noqa: E402
import smoke_signoff  # noqa: E402
import thinking_system_family as tsf  # noqa: E402

from speech_aware_evidence_acquisition.core import reasoning_knobs as rk  # noqa: E402
from speech_aware_evidence_acquisition.core.config import compose  # noqa: E402
from speech_aware_evidence_acquisition.rails.controllers import default_phase_program  # noqa: E402
from speech_aware_evidence_acquisition.rails.native_episode_config import load_native_episode_config  # noqa: E402

NX = REPO / "scripts" / "flights" / "nx"
PKG = REPO / fam.PACKAGE
LOCKED_PATH = REPO / fam.LOCKED_TEMPLATE
PARAGRAPHS = {
    "t1": "Reason briefly. Decide each entity slot once, and do not re-verify a decision you have already settled. As soon as every slot is decided, stop thinking and write the final JSON.",
    "t2": "Output an entity only when its value is heard in the speech. An empty entities array is a correct and complete answer when no specific value is heard; do not add an entity merely because the selected candidate or the knowledge suggests a slot type.",
    "t3": "First fix the one intent you will answer. Then consult only the supplied evidence items that belong to that intent, and ignore the cards and examples of the other candidate intents; do not walk through every supplied item.",
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
    return json.loads((NX / "nxt_r3_arms.json").read_text(encoding="utf-8"))


# ---- ids and shape -----------------------------------------------------------------------------------------------------------------


def test_ids_are_unique_and_follow_the_registered_pattern():
    runs = [fam.CELLS[k][f] for k in fam.ALL_KEYS for f in ("run", "fit_run")]
    assert len(set(runs)) == 4
    assert fam.RECOVERIES == {} and fam.RECOVERY_HISTORY == {} and fam.recovery("arm") is None and fam.rec_suffix("arm") == "" and fam.recovery_index("arm") == 0
    assert fam.eligible_run_ids() == [fam.CELLS["smoke"]["run"], fam.CELLS["smoke"]["fit_run"], fam.CELLS["arm"]["run"], fam.CELLS["arm"]["fit_run"]]
    assert fam.CELLS["arm"]["run"] == "SAEA-SLURP-STAGE3-NXT-R3-SOLVER-TEMPLATE-FOLD-B-V1"
    assert fam.CELLS["arm"]["fit_run"] == "SAEA-SLURP-STAGE3-NXT-R3-SOLVER-TEMPLATE-FOLD-B-FIT-V1"
    assert fam.CELLS["smoke"]["run"] == "SAEA-SLURP-STAGE3-NXT-R3-SOLVER-TEMPLATE-FOLD-B-SMOKE-4-V1"
    assert fam.CELLS["arm"]["cell"] == "slurp-native-stage3-nxt-r3-solver-template-fold-b-v1"
    assert fam.CELLS["arm"]["attempt"] == "attempt-slurp-native-stage3-nxt-r3-solver-template-fold-b-generation-v1"
    assert fam.PACKAGE == "docs/readiness/2026-10-18-slurp-nxt-r3-solver-template-fold-b-v1" and fam.SHORT == "nxt3" and fam.PKG_NAME == "slurp-nxt-r3-solver-template-fold-b-v1"
    assert fam.READ_RUN_ID == "SAEA-SLURP-NXT-R3-SOLVER-TEMPLATE-FOLD-B-READ-V1" and fam.SIGNOFF_CONDITIONS == f"{fam.PACKAGE}/signoff-conditions-v1.json"
    for key in fam.ALL_KEYS:
        assert experiment(key)["cells"][0]["run_id"] == fam.CELLS[key]["run"]
        assert experiment(key)["cells"][0]["attempt_id"] == fam.CELLS[key]["attempt"]
        assert baseline(key)["native_contact_fit"]["run_id"] == fam.CELLS[key]["fit_run"]
        assert experiment(key)["cells"][0]["baseline_fragment"] == fam.CELLS[key]["baseline"]
        assert experiment(key)["cells"][0]["model_fragment"] == tsf.THINK_MODEL and experiment(key)["service_session"] == tsf.THINK_SESSION   # the RESIDENT np4 session


def test_recovery_hooks_for_rec1_and_rec2_are_declared_and_empty_now():
    assert list(fam.PREDECESSOR_SNAPSHOTS) == ["arm"] == list(fam.RECOVERY_INPUTS)
    assert fam.PREDECESSOR_SNAPSHOTS["arm"][0].endswith("predecessor-snapshot-arm-rec1-v1.json") and fam.PREDECESSOR_SNAPSHOTS["arm"][1].endswith("predecessor-snapshot-arm-rec2-v1.json")
    assert fam.RECOVERY_INPUTS["arm"][0].endswith("recovery-input-arm-v1.json") and fam.RECOVERY_INPUTS["arm"][1].endswith("recovery-input-arm-rec2-v1.json")
    assert fam.RESUME_MODES == {"checkpoint": "B", "trace": "A"} and callable(fam.build_arm_rec2) and callable(fam.build_arm_recovery)
    for name in ("nxt_r3_rec2_mode.py", "nxt_r3_rec2_snapshot.py", "nxt_r3_rec2_replay_proof.py"):
        subprocess.run([sys.executable, "-B", "-c", "import ast,sys; ast.parse(open(sys.argv[1], encoding='utf-8').read())", str(NX / name)], check=True)


# ---- the templates: minimal, hash-pinned deltas of the locked Solver template ---------------------------------------------------------------


def test_the_locked_template_is_the_one_the_thinking_lock_renders():
    assert hashlib.sha256(LOCKED_PATH.read_bytes()).hexdigest() == fam.LOCKED_TEMPLATE_SHA
    assert baseline("arm")["phase_material"]["solver"]["instruction_template"] == "probes/slurp_native_role_solver_v2.txt"
    assert baseline("arm")["native_episode"]["consumption_module"]["lock"] == fam.LOCK


def test_each_candidate_is_the_locked_template_plus_exactly_the_registered_paragraphs():
    locked = LOCKED_PATH.read_bytes().decode("utf-8")
    marker = "On a revision, reconsider"
    head, tail = locked[:locked.index(marker)], locked[locked.index(marker):]
    expected = {"t1-decide-once": [PARAGRAPHS["t1"]], "t2-grounded-or-empty": [PARAGRAPHS["t2"]], "t3-supply-focus": [PARAGRAPHS["t3"]],
                "t4-decide-once-grounded": [PARAGRAPHS["t1"], PARAGRAPHS["t2"]]}
    assert list(fam.CANDIDATE_ARMS) == list(expected) and "t3-type-inventory" not in fam.CANDIDATE_ARMS
    for spec in fam.ARM_SPECS:
        data = (REPO / spec["relpath"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == spec["sha256"] and b"\r" not in data and data.isascii()
        assert data.decode("utf-8") == head + "\n\n".join(expected[spec["arm_id"]]) + "\n\n" + tail
        assert spec["added_paragraphs"] == expected[spec["arm_id"]]
    assert len({s["sha256"] for s in fam.ARM_SPECS} | {fam.LOCKED_TEMPLATE_SHA}) == 5


def test_t3_names_the_supply_focus_instruction():
    text = (REPO / "configs/probes/nx/solver/thinking/t3-supply-focus.txt").read_text(encoding="utf-8")
    assert "First fix the one intent you will answer" in text and "ignore the cards and examples of the other candidate intents" in text
    assert "do not walk through every supplied item" in text


def test_the_arm_table_is_refused_by_name(tmp_path):
    bad_sha = arm_doc()
    bad_sha["arms"][0]["sha256"] = "0" * 64
    bad_dup = arm_doc()
    bad_dup["arms"][1] = dict(bad_dup["arms"][0], arm_id="t2-grounded-or-empty")
    bad_id = arm_doc()
    bad_id["arms"][0]["arm_id"] = "lock"
    bad_twin = arm_doc()
    bad_twin["twin"] = "x"
    bad_dir = arm_doc()
    bad_dir["arms"][0]["relpath"] = "configs/probes/slurp_native_role_solver_v1.txt"
    bad_keys = arm_doc()
    bad_keys["knobs"] = {}
    too_many = arm_doc()
    too_many["arms"] = [dict(too_many["arms"][0], arm_id=f"x{i}") for i in range(7)]
    for doc, message in ((bad_sha, "hashes to"), (bad_dup, "share one template"), (bad_id, "distinct lower-case id"), (bad_twin, "the delivering arm is"),
                         (bad_dir, "must sit under"), (bad_keys, "must be exactly"), (too_many, "between 1 and")):
        with pytest.raises(fam.ArmTableError, match=message):
            fam.validate_arm_table(doc)
    # a candidate that changes anything but the inserted paragraph(s) is refused (copy the tree pieces and edit one byte of the shared head)
    root = tmp_path / "repo"
    (root / "configs/probes/nx/solver/thinking").mkdir(parents=True)
    shutil.copy(LOCKED_PATH, root / "configs/probes")
    for spec in fam.ARM_SPECS:
        shutil.copy(REPO / spec["relpath"], root / spec["relpath"])
    edited = root / fam.ARM_SPECS[0]["relpath"]
    edited.write_bytes(edited.read_bytes().replace(b"Resolve the source-bound", b"Resolve the source bound", 1))
    doc = arm_doc()
    doc["arms"][0]["sha256"] = hashlib.sha256(edited.read_bytes()).hexdigest()
    with pytest.raises(fam.ArmTableError, match="nothing else changed"):
        fam.validate_arm_table(doc, root)
    assert [a["arm_id"] for a in fam.validate_arm_table(arm_doc())] == list(fam.CANDIDATE_ARMS)


# ---- the cells ---------------------------------------------------------------------------------------------------------------------


def test_the_cells_carry_the_solver_template_block_the_twin_and_the_delivering_arm_last():
    for key in fam.ALL_KEYS:
        base = baseline(key)
        roles = base["native_episode"]["roles"]
        block = roles["solver"]["template_variants"]
        assert block["node"] == "solver" and set(roles["perception"]) == {"max_iterations", "phase_id"} and "thinking_variants" not in json.dumps(roles)
        ids = [a["arm_id"] for a in block["arms"]]
        assert ids == list(fam.ARM_ORDER) and ids[-1] == fam.DELIVERING and ids[-2] == fam.TWIN
        assert block["arms"][-1].get("deliver") is True and block["arms"][-2].get("replicate_of") == fam.DELIVERING
        pins = {a["arm_id"]: a["instruction_template"] for a in block["arms"] if "instruction_template" in a}
        assert pins == {s["arm_id"]: {"relpath": s["relpath"], "sha256": s["sha256"]} for s in fam.ARM_SPECS}
        assert {a["arm_id"]: a["template_tokens"] for a in block["arms"] if a["arm_id"] in fam.CANDIDATE_ARMS} == {s["arm_id"]: s["template_tokens"] for s in fam.ARM_SPECS}
        assert block["max_supplied_items"] == fam.MAX_SUPPLIED_ITEMS and block["fit_estimate"] == fam.FIT_ESTIMATE
        assert "thinking_policy" not in base and base["policy"] == fam.PROGRAM == "phase-native-module-v1-c7"
        assert base["native_contact_fit"]["contact_cap"] == fam.fit_contact_cap(fam.CELLS[key]["rows"])
        assert base["preflight_budget_mode"] == "defer-to-native-contact-fit"
        episode = base["native_episode"]
        assert (episode["review_loop"], episode["max_revisions"]) == ("off", 0)
        assert episode["finite_completion_policy"] == "deliver-latest-or-abstain" and episode["react_exhaustion_policy"] == "continue-without-answer"
        assert block.get("arm_visits", "first") == "first"


def test_the_composed_cell_loads_through_the_runtime_loader_and_verifies():
    for key in fam.ALL_KEYS:
        values = composed(key).values
        program = default_phase_program(values["policy"])
        config = load_native_episode_config(values, program)
        group = config.supply_variant_group
        assert group is not None and group.is_template and group.arm_visits == "first"
        assert group.arm_ids == fam.ARM_ORDER and group.delivered_arm.arm_id == fam.DELIVERING
        assert program.max_contacts == fam.CONTACTS_PER_ROW == 7


def test_the_derive_proves_that_only_the_solver_block_the_program_and_the_ids_moved():
    result = dc.derive(write=False)
    assert result["program"] == fam.PROGRAM and result["ceiling"] == fam.CONTACTS_PER_ROW
    for key in fam.ALL_KEYS:
        cell = result["cells"][key]
        assert cell["loader_verification"] == {"ok": True, "refusal": None}
        assert dc.classify_moved(cell["moved_leaves"])[1] == []
        assert cell["moved_by_rule"]["the Solver template_variants block"] and cell["moved_by_rule"]["its declaration in consumption_module"]
        assert cell["moved_by_rule"]["the program id and ceiling"] == ["policy"]
        assert not any(leaf.startswith("thinking_policy") for leaf in cell["moved_leaves"])
    # the committed files are exactly what the derive writes (reproducible)
    assert dc.same_json(f"configs/baseline/{fam.CELLS['arm']['baseline']}.json", baseline("arm"))
    for leaf in ("native_episode.roles.perception.thinking_variants", "thinking_policy"):
        assert leaf not in dv._leaves(baseline("arm"))


def test_experiments_swap_nothing_but_the_ids_and_name_the_resident_session():
    for key in fam.ALL_KEYS:
        text = json.dumps(experiment(key))
        assert fam.THINK_SESSION in text and fam.THINK_MODEL in text
        assert "thinking-system-fold-b" not in text.replace("thinking-system-fold-b-lock-fit", "")


# ---- the request-level proof: a Solver template-arm contact carries the lock's thinking fields -------------------------------------------


def test_every_solver_arm_contact_carries_the_lock_thinking_fields_through_the_real_request_composer(tmp_path):
    """The arm identity (``variant_arm_id``) never reaches the decoding composer: thinking fields are resolved per ROLE ID. Compose the Solver and Perception requests
    for every arm of the column with the real composer over a request fixture and compare field for field with the delivering (and the unarmed) request."""

    pytest.importorskip("openjiuwen", reason="OpenJiuwen unavailable")
    from types import MappingProxyType

    import test_thinking_policy_column as tpc  # noqa: PLC0415

    from speech_aware_evidence_acquisition.reproduction.ojw.native_roles import NativeRoleContactContext, NativeRoleModelRequest  # noqa: PLC0415

    world = tpc._World(tmp_path)
    feature_root, packet, bindings = tpc._speech_feature_world(world, tmp_path)
    client, _gate, _t = tpc._client(world, tmp_path, transport=tpc._ScriptedTransport([("a", "stop", 3)] * 8), arm="speech-feature-query-native-tools",
                                    tool_schemas=tpc._TOOLS, speech_feature_root=feature_root, speech_packet_bindings=bindings, plan=tpc._native_plan(planned_model_calls=50))
    adapter = tpc.MeteredNativeSpeechRequest(
        client=client, binding_provider=lambda r: tpc._native_binding(r.role_id, packet), render_request=lambda b: json.loads(b),
        completion_sink=lambda request, completion: None)           # the 268-B lock composition: no role policy, no branch policy

    def request(role_id, arm, contact):
        return NativeRoleModelRequest(
            role_id=role_id, context=NativeRoleContactContext(sample_id="s1", agent_contact_id=contact, variant_arm_id=arm),
            messages=({"role": "system", "content": "Choose exactly one opaque key id."}, {"role": "user", "content": "Inspect the speech."}),
            tool_schemas=(), visible_tool_names=(), decoding_controls=MappingProxyType({}))

    def decoding(role_id, arm, contact):
        return adapter.prepare(request(role_id, arm, contact)).rendered_body()["decoding_params"]

    on = {"thinking_budget_tokens": fam.DELIVERING_BUDGET, "chat_template_kwargs": {"enable_thinking": True}, "max_tokens": fam.COMPLETION_CAP}
    for role in ("solver", "perception"):
        reference = decoding(role, None, f"unarmed-{role}")
        assert {k: reference[k] for k in on} == on
        for n, arm in enumerate(fam.ARM_ORDER):
            armed = decoding(role, arm, f"arm-{role}-{n}")
            assert armed == reference, (role, arm)                       # every wire decoding field, thinking budget and cap included


def test_the_dry_run_reports_the_lock_thinking_fields_for_every_arm_of_a_thinking_template_group():
    """The dry-run walk resolves a per-arm ``node_decoding`` for a template group ONLY on a thinking fragment (the instrument change of this round)."""

    source = (REPO / "src/speech_aware_evidence_acquisition/analysis/native_episode_dry_run.py").read_text(encoding="utf-8")
    assert "elif template_group is not None:" in source and "fold_into_decoding(binding[\"values\"])" in source
    import nxt_r3_dry_run as dry  # noqa: PLC0415

    values = composed("smoke").values
    folded = rk.fold_into_decoding(values)
    assert folded and folded["decoding_params"]["thinking_budget_tokens"] == 3072 and folded["decoding_params"]["max_tokens"] == 4096
    expected = dry.lock_node_decoding()
    assert set(expected) == {"perception", "solver"}
    for node_decoding in expected.values():
        assert node_decoding == {"thinking_budget_tokens": 3072, "chat_template_kwargs": {"enable_thinking": True}, "max_tokens": 4096}
    # an Instruct template cell folds nothing, so its dry-run rows stay unchanged
    instruct = js("configs/baseline/slurp-native-stage3-nx-r1-solver-fold-b-baseline-v1.json")
    assert rk.fold_into_decoding({"decoding_params": {"max_tokens": 512}}) is None and instruct["native_episode"]["roles"]["solver"]["template_variants"]


# ---- fit, cost and budget ------------------------------------------------------------------------------------------------------------


def test_the_live_slot_holds_the_longest_template_prompt_plus_the_cap():
    fit = fam.fit_proof()
    assert fit["ok"] and fit["prompt_limit_tokens"] == 17406 == fam.PROMPT_LIMIT and fit["completion_cap"] == 4096
    assert fit["longest_template_tokens"] == max(fam.TEMPLATE_TOKENS.values()) and fit["estimate_at_bound_tokens"] <= fit["prompt_limit_tokens"]
    assert fam.TEMPLATE_TOKENS[fam.DELIVERING] == -(-LOCKED_PATH.stat().st_size * 2 // 7)
    for spec in fam.ARM_SPECS:
        assert spec["template_tokens"] == -(-(REPO / spec["relpath"]).stat().st_size * 2 // 7)             # ceil(bytes / 3.5)


def test_the_derive_refuses_when_the_slot_cannot_hold_the_prompt_plus_the_cap(monkeypatch):
    monkeypatch.setattr(fam, "OBSERVED_SOLVER_PROMPT_MAX", 17400)
    assert not fam.fit_proof()["ok"]
    with pytest.raises(SystemExit, match="does not hold"):
        dc.derive(write=False)


def test_the_registered_cost_and_ceiling_follow_the_measured_r2b_throughput():
    m = fam.M
    assert m["gpu_hours_per_1080_row_lock_flight"] == 9.23 and m["perception_seconds_per_contact_mean"] == 59.0 and abs(m["solver_seconds_per_contact_mean"] - 64.07) < 1e-9
    assert abs(m["seconds_per_row_lock"] - 9.23 * 4 * 3600 / 1080) < 0.01
    assert fam.K == 6 and fam.CONTACTS_PER_ROW == 7 and fam.PROGRAM == "phase-native-module-v1-c7"
    assert fam.ARM_MIX_ROWS == fam.ceil_hundredth((59.0 + 6 * 64.07) / (59.0 + 64.07)) == 3.61
    assert fam.ROWS_PER_MINUTE_FULL == 1.95
    expected = 1080 * 3.61 / 1.95 / 60
    assert abs(fam.expected_gpu_hours(1080) - expected) < 1e-9 and 30 <= expected <= 40
    assert fam.planned_gpu_hours(1080) == 43.4 == fam.CELLS["arm"]["gpu_hours"] and fam.CELLS["smoke"]["gpu_hours"] == 0.5
    assert fam.planned_gpu_hours(1080) >= fam.expected_gpu_hours(1080) * 1.3


def test_plan_ceilings_follow_the_program_and_the_fallback_contacts():
    assert fam.THINKING_CONTACTS_PER_ROW == 7 == fam.FALLBACK_CONTACTS_PER_ROW_CEILING
    assert fam.original_generation_calls("arm") == 1080 * 14 == 15120 and fam.original_generation_calls("smoke") == 4 * 14
    assert fam.program_calls("arm") == 1080 * 7 and fam.fit_contact_cap(1080) == 1080 * 7 * 4
    for key in fam.ALL_KEYS:
        family, plan = dc.budgets(key)
        assert plan["planned_model_calls"] == fam.generation_calls(key) and family["fit_endpoint_calls_cap"] == fam.fit_contact_cap(fam.CELLS[key]["rows"])
        assert plan["execution_profile"] == "bounded-discovery-probe" and plan["split_role"] == "discovery" and plan["planned_gpu_hours"] == fam.CELLS[key]["gpu_hours"]


# ---- the package -------------------------------------------------------------------------------------------------------------------------


def test_stage3_measurement_blocks():
    facts = json.loads((PKG / "registered-facts-v1.json").read_text(encoding="utf-8"))
    blocks = facts["stage3_measurement"]
    arm_run, smoke = fam.CELLS["arm"]["run"], fam.CELLS["smoke"]["run"]
    assert set(blocks) == {arm_run, smoke}
    b = blocks[arm_run]
    assert b["measurement_design"] == "same-flight-node-column" and b["claims_benefit"] is False and b["claim"] == "nominated" and b["aa_arm_id"] == "aa"
    assert b["primary_metric_key"] == "slu" and b["rows"] == 1080 and b["tuning_roster"] == "none" and b["read_roster"] == fam.READ_ROSTER
    assert b["template_variants"] == {"node": "solver", "candidate_arms": 4, "twin": True} and b["variant_kind"] == "solver-template"
    assert b["variant_cost"]["extra_contacts_per_row"] == 5 and b["variant_cost"]["extra_audio_seconds"] > 0
    assert blocks[smoke]["measurement_design"] == "form-proof" and blocks[smoke]["claims_benefit"] is False
    assert facts["blockers"] == [] and {f["id"] for f in facts["findings"]} >= {"why-the-use-node", "arm-contacts-carry-the-lock-thinking-fields", "in-flight-aa-twin",
                                                                                   "resident-session-no-new-fragment", "machine-signoff-with-a-veto-window"}
    ce = facts["accounting"]["cost_estimate"]
    assert ce["column_flight"]["planned_ceiling_gpu_hours"] == fam.CELLS["arm"]["gpu_hours"] and ce["arm_mix_rows"] == fam.ARM_MIX_ROWS
    assert [r["arm"] for r in ce["arm_table"]] == list(fam.ARM_ORDER) and ce["inputs"]["r2b_measured"]["slots"] == 4
    assert facts["read_rule"]["word_order"] == list(reader.WORDS) and facts["read_rule"]["twin"] == "aa" and facts["context_fit"]["ok"] is True
    assert facts["pins"]["signoff_conditions"]["sha256"] == hashlib.sha256((PKG / "signoff-conditions-v1.json").read_bytes()).hexdigest()
    assert "thinking_arms" not in facts and facts["template_arms"]["t3-supply-focus"]["sha256"] == fam.ARM_SPECS[2]["sha256"]


def test_the_effect_floor_gate_resolves_the_node_column(tmp_path):
    """The gate keys on the exposure ledger; the package's DRAFT rows are overlaid on a COPY (this repository's ledger is not touched)."""

    ledger = tmp_path / "ledger.md"
    ledger.write_text((REPO / "docs/exposure-ledger.md").read_text(encoding="utf-8") + "\n" + (PKG / "draft-ledger-rows.md").read_text(encoding="utf-8"), encoding="utf-8")
    out = subprocess.run([sys.executable, "-B", str(REPO / "scripts/checks/stage3_effect_floor_check.py"), "--ledger", str(ledger), "--json"],
                         capture_output=True, text=True, cwd=REPO)
    assert out.returncode == 0, out.stderr[-500:]
    report = json.loads(out.stdout[out.stdout.find("{"):])
    mine = [c for c in report["in_scope_cells"] if "nxt-r3-solver-template" in c["cell_id"]]
    assert {c["cell_id"] for c in mine} == {fam.CELLS[k]["cell"] for k in fam.ALL_KEYS}
    assert not [f for f in report["findings"] if "nxt-r3-solver-template" in json.dumps(f)]
    column = {c["cell_id"]: c["declaration"] for c in mine}[fam.CELLS["arm"]["cell"]]
    assert column["problems"] == [] and column["measurement_design"] == "same-flight-node-column" and column["claims_benefit"] is False


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
            assert plan["template_arms"]["lock"]["added_paragraphs"] == [] and plan["template_arms"]["t1-decide-once"]["added_paragraphs"] == [PARAGRAPHS["t1"]]
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
    assert recipe["verdict_words"] == list(reader.WORDS) and recipe["primary"]["draws"] == 10000 and recipe["efficiency"]["solver_seconds_per_contact_ratio_max"] == 0.85
    assert recipe["guard"]["nominated_point_floor_pp"] == -0.65 and "2-arm Fold A confirm" in recipe["next_step"]
    assert any("by_supplied_items_bin" in s for s in recipe["secondaries"]) and any("split_by_forced_status" in s for s in recipe["secondaries"])
    assert (REPO / fam.PREREG).is_file()
    for line in draft_rows.splitlines():
        if line.startswith("| 2026"):
            assert "DRAFT" in line and "root countersigned" not in line


def test_the_readme_names_the_ruling_the_arms_the_fit_the_cost_the_words_and_the_confirm():
    readme = (PKG / "README.md").read_text(encoding="utf-8")
    for needle in ("326 A", "t1-decide-once", "t2-grounded-or-empty", "t3-supply-focus", "t4-decide-once-grounded", "saea-supply-variant-arms-v4", "arm_visits", "first",
                   "think-budget-np4", "no-op", "drop-reasoning-v1", "ceil_0.1", "NOMINATED", "EFFICIENT-NO-LOSS", "HARM", "NEUTRAL", "2-arm Fold A confirm", "NOT built",
                   "flip_package_ext4.sh", "nxt_r3_arms.json", "nxt3-decode-signoff.marker", "NXT3_KINDS", "wait_or_machine_signoff", "close_rows_after_seal", "SAEA-Chain-NXT3",
                   "queue_nxt3_after_nxt2.sh", "CHAIN_NXT2_EXIT", "signoff-conditions-v1.json", "arm-only", "forced-close share", "supplied-item bin", "forced status",
                   "ceil(bytes / 3.5)", "no tokenizer contact", "24 GPU-h", str(fam.CELLS["arm"]["gpu_hours"]), str(fam.ARM_MIX_ROWS), "0.85", "-0.65",
                   "repin exit N (1 = its internal check refused the dirty tree, expected)"):
        assert needle in readme, needle
    assert "t3-type-inventory" not in readme
    for script in ("nxt_r3_flip.sh", "nxt_r3_read.sh", "nxt_r3_repin_cell.sh", "batch_chain_nxt_r3.sh"):
        assert subprocess.run(["bash", "-n", str(NX / script)], capture_output=True).returncode == 0


def test_the_text_of_the_package_is_english():
    for path in [PKG / n for n in ("README.md", "draft-ledger-rows.md", "countersign-row-texts-v1.json", "registered-facts-v1.json", "protocol-registered-v1.json",
                                     "signoff-conditions-v1.json", "analysis-recipe-v1.json")]:
        assert not re.search(r"[^\x00-\x7f]", path.read_text(encoding="utf-8")), path
    for name in ("nxt_r3_family.py", "nxt_r3_derive_cells.py", "nxt_r3_write_registration.py", "nxt_r3_mint_receipt.py", "nxt_r3_dry_run.py", "nxt_r3_flip.sh", "nxt_r3_repin_cell.sh",
                 "nxt_r3_read.sh", "batch_chain_nxt_r3.sh", "nxt_r3_arms.json", "nxt_r3_cost_inputs.json", "nxt_r3_launch_spec.json", "nxt_r3_rec2_mode.py",
                 "nxt_r3_rec2_snapshot.py", "nxt_r3_rec2_replay_proof.py"):
        assert (NX / name).read_text(encoding="utf-8").isascii(), name
    for rel in (fam.READER, fam.PREREG, "scripts/flights/batch/queue/queue_nxt3_after_nxt2.sh", "scripts/flights/batch/queue/chain_nxt3.sh",
                *[s["relpath"] for s in fam.ARM_SPECS]):
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


def _outputs_rows(n=4, supplied=(10, 45)):
    rows = []
    for i in range(n):
        sid = f"s{i}"
        count = supplied[i % len(supplied)]
        rows.append({"sample_id": sid, "perception": [f"{sid}:perception:00"],
                     "arms": [(arm, f"{sid}:{arm}", count) for arm in fam.ARM_ORDER]})
    return rows


def _contact(agent, role, tokens, seconds, *, forced=False, finish="stop", empty=False, reasoning=100, marker=False):
    return {"agent_contact_id": agent, "role": role, "prompt_tokens": 8000, "completion_tokens": tokens, "latency_seconds": seconds, "finish_reason": finish,
            "empty_content": empty, "no_json_object": False, "marker_in_content": marker, "reasoning_chars": reasoning, "forced_close": forced}


def _synthetic_contacts(rows, *, cap_hit=False, forced_ge40=True):
    out = []
    for row in rows:
        out.append(_contact(row["perception"][0], "perception", 1500, 59.0))
        for arm, contact, supplied in row["arms"]:
            forced = bool(forced_ge40 and supplied >= 40)
            out.append(_contact(contact, "solver", 4096 if (cap_hit and arm == "lock") else 3200, 64.0, forced=forced))
    return out


def _score_row(tp, fp, fn, intent):
    return {"slu_f1_word_tp": tp, "slu_f1_char_tp": tp, "slu_f1_word_fp": fp, "slu_f1_char_fp": fp, "slu_f1_word_fn": fn, "slu_f1_char_fn": fn, reader.INTENT_FIELD: intent}


def _arms_scores(ids, *, candidate_gain=0.0, candidate_intent=1.0):
    base = {i: _score_row(3.0, 1.0, 1.0, 1.0) for i in ids}
    better = {i: _score_row(3.0 + candidate_gain, 1.0, max(0.0, 1.0 - candidate_gain), candidate_intent) for i in ids}
    return {arm: (better if arm in fam.CANDIDATE_ARMS else base) for arm in fam.ARM_ORDER}


def _contrast(slu, intent, twin=0.0):
    """A contrast record with controlled CI95s for the word logic (pp)."""

    def iv(point, lo, hi):
        return {"point_pp": point, "ci95_lo_pp": lo, "ci95_hi_pp": hi}

    versus = {fam.TWIN: {"slu_f1": iv(twin, twin - 1, twin + 1), "intent": iv(0.0, -0.5, 0.5), "intent_saves_harms_ties_vs_delivering": {}}}
    for arm in fam.CANDIDATE_ARMS:
        versus[arm] = {"slu_f1": iv(*slu), "intent": iv(*intent), "intent_saves_harms_ties_vs_delivering": {}}
    return {"versus_delivering": versus}


def test_the_arm_words_follow_the_registered_order_and_thresholds():
    secs = {arm: 64.0 for arm in fam.ARM_ORDER}
    cheap = dict(secs, **{"t1-decide-once": 50.0})
    words = lambda c, s=secs: {a: w["word"] for a, w in reader.arm_words(c, s)["words"].items()}  # noqa: E731
    assert words(_contrast((2.0, 0.5, 3.5), (0.0, -0.5, 0.5), twin=0.4))["t2-grounded-or-empty"] == "NOMINATED"
    assert words(_contrast((2.0, -0.2, 3.5), (0.0, -0.5, 0.5), twin=0.4))["t2-grounded-or-empty"] == "NEUTRAL"                    # CI-LB not above zero, same speed
    assert words(_contrast((2.0, 0.5, 3.5), (-1.0, -1.5, 0.0), twin=0.4))["t2-grounded-or-empty"] != "NOMINATED"                  # intent point under the -0.65 guard
    assert words(_contrast((0.3, 0.1, 3.5), (0.0, -0.5, 0.5), twin=0.4))["t2-grounded-or-empty"] != "NOMINATED"                    # point below the twin bar |o| = 0.4
    assert words(_contrast((-3.0, -4.0, -2.0), (0.0, -0.5, 0.5), twin=0.4))["t2-grounded-or-empty"] == "HARM"
    assert words(_contrast((-0.1, -1.0, 0.8), (0.0, -0.5, 0.5), twin=0.4), cheap)["t1-decide-once"] == "EFFICIENT-NO-LOSS"       # no resolved loss and 0.78 x the lock
    assert words(_contrast((-0.1, -1.0, 0.8), (0.0, -0.5, 0.5), twin=0.4), secs)["t1-decide-once"] == "NEUTRAL"                  # same speed: efficiency not met
    efficient_but_harm = words(_contrast((-0.3, -1.0, -0.1), (0.0, -0.5, 0.5), twin=0.4), cheap)["t1-decide-once"]
    assert efficient_but_harm == "EFFICIENT-NO-LOSS"                                                                              # brief order: EFFICIENT before HARM
    resolved_loss = words(_contrast((-2.0, -3.0, -1.0), (0.0, -0.5, 0.5), twin=0.4), cheap)["t1-decide-once"]
    assert resolved_loss == "HARM"                                                                                                # CI-UB -1.0 < -|o|: a resolved loss is never efficient
    assert reader.arm_words(_contrast((2.0, 0.5, 3.5), (0.0, -0.5, 0.5)), secs)["words"]["t1-decide-once"]["next_step"] == "2-arm Fold A confirm"
    assert list(reader.WORDS) == ["NOMINATED", "EFFICIENT-NO-LOSS", "HARM", "NEUTRAL"]


def test_the_writer_words_are_the_readers_words_in_order():
    import nxt_r3_write_registration as writer  # noqa: PLC0415

    assert list(writer.WORD_RULES) == list(reader.WORDS)
    assert "-0.65" in writer.WORD_RULES["NOMINATED"] and "0.85" in writer.WORD_RULES["EFFICIENT-NO-LOSS"] and "< 0" in writer.WORD_RULES["HARM"]


def test_reader_paired_contrast_end_to_end_with_the_twin():
    ids = [f"s{i}" for i in range(40)]
    arms = _arms_scores(ids, candidate_gain=1.0, candidate_intent=1.0)
    rows = _outputs_rows(40)
    contacts = _synthetic_contacts(rows)
    by_arm = reader.npc.attribute(contacts, reader.arm_contact_map(rows))
    result = reader.read_stage(arms, ids, lambda sid: sid, lambda sid: "alarm" if int(sid[1:]) % 2 else "play", by_arm, reader.contact_rows(rows, contacts), draws=200)
    assert result["schema"] == reader.SCHEMA_READ and result["contrast"]["delivering"] == "lock" and set(result["contrast"]["versus_delivering"]) == set(fam.ARM_ORDER) - {"lock"}
    assert result["contrast"]["versus_delivering"]["aa"]["slu_f1"]["point_pp"] == 0.0
    assert result["contrast"]["versus_delivering"]["t1-decide-once"]["slu_f1"]["point_pp"] > 0
    assert result["arm_words"]["words"]["t1-decide-once"]["word"] == "NOMINATED"
    assert set(result["per_scenario"]["scenarios"]) == {"alarm", "play"} and "natural_mixture" in result["per_scenario"] and "equal_scenario" in result["per_scenario"]
    assert reader.render_markdown(result).startswith("# ")
    json.dumps(result)


def test_forced_close_share_is_split_by_supplied_item_bin_and_empty_gold_false_fill_by_forced_status():
    rows = _outputs_rows(8, supplied=(10, 45))
    contacts = _synthetic_contacts(rows, forced_ge40=True)
    joined = reader.contact_rows(rows, contacts)
    split = reader.forced_by_supply_bin(joined, "lock")
    assert split["lt40"]["contacts"] == 4 and split["lt40"]["forced"] == 0 and split["lt40"]["forced_share"] == 0.0
    assert split["ge40"]["contacts"] == 4 and split["ge40"]["forced"] == 4 and split["ge40"]["forced_share"] == 1.0
    assert reader.supply_bin(39) == "lt40" and reader.supply_bin(40) == "ge40" and reader.supply_bin(None) == "unknown"
    # empty-gold rows: s1,s3,s5,s7 are the >= 40 (forced) rows; false-fill on the forced ones only
    scores = {}
    for i in range(8):
        sid = f"s{i}"
        forced = i % 2 == 1
        scores[sid] = _score_row(0.0, 1.0 if forced else 0.0, 0.0, 1.0)                    # empty gold (tp = fn = 0); an entity emitted only on forced rows
    scores["s8"] = _score_row(2.0, 0.0, 0.0, 1.0)                                          # a non-empty gold row, exact
    fill = reader.empty_gold_false_fill(scores, {c["sample_id"]: c["forced_close"] for c in joined if c["arm"] == "lock"}.get)
    assert fill["empty_gold_rows"] == 8 and fill["false_fill_rows"] == 4
    assert fill["forced"] == {"rows": 4, "false_fill": 4, "false_fill_share": 1.0} and fill["natural"]["rows"] == 4 and fill["natural"]["false_fill"] == 0
    assert reader.nonempty_exact(scores) == {"nonempty_gold_rows": 1, "exact_rows": 1, "exact_share": 1.0}
    tables = reader.tables_by_arm(reader.npc.attribute(contacts, reader.arm_contact_map(rows)))
    sec = reader.arm_secondaries({"lock": scores}, joined, tables)["lock"]
    assert sec["solver_forced_close_share"] == 0.5 and sec["forced_close_by_supplied_items_bin"]["ge40"]["forced"] == 4 and sec["empty_gold_false_fill"]["forced"]["false_fill"] == 4


def test_reader_counts_cap_hits_and_tabulates_the_throughput():
    rows = _outputs_rows(4)
    mapping = reader.arm_contact_map(rows)
    good = reader.smoke_stage(reader.npc.attribute(_synthetic_contacts(rows), mapping), missing=reader.missing_columns(rows, _synthetic_contacts(rows)))
    assert set(good["arms"]) == set(fam.ARM_ORDER) | {"_perception"} and good["arms"]["lock"]["solver"]["contacts"] == 4 and good["arms"]["lock"]["solver"]["cap"] == 4096
    assert good["arms"]["_perception"]["perception"]["contacts"] == 4 and good["absent_columns"] == 0 and good["unattributed_contacts"] == 0
    tp = good["throughput"]
    assert tp["arm_mix_registered_rows"] == fam.ARM_MIX_ROWS and abs(tp["arm_mix_measured_rows"] - (59.0 + 6 * 64.0) / (59.0 + 64.0)) < 1e-9
    checks = smoke_signoff.evaluate(fam.signoff_conditions(), good)
    assert checks and all(c["ok"] for c in checks), [c for c in checks if not c["ok"]]
    capped = reader.smoke_stage(reader.npc.attribute(_synthetic_contacts(rows, cap_hit=True), mapping))
    assert good["arms"]["lock"]["solver"]["cap_hits"] == 0 and capped["arms"]["lock"]["solver"]["cap_hits"] == 4
    assert any(not c["ok"] for c in smoke_signoff.evaluate(fam.signoff_conditions(), capped))
    # a declared arm column whose Solver contact is missing from the trace is counted (absent_columns)
    short = _synthetic_contacts(rows)[:-1]
    missing = reader.missing_columns(rows, short)
    assert missing["total"] == 1 and missing["by_arm"]["lock"] == 1


def test_the_reader_loads_only_ids_from_the_sealed_outputs(tmp_path):
    path = tmp_path / "outputs.jsonl"
    secret = "A-SECRET-TRANSCRIPT"
    receipt = {"schema": "saea-supply-variant-arms-v4", "arms": [{"arm_id": a, "contact_id": f"c:{a}", "supplied_item_count": 12, "instruction_template": None} for a in fam.ARM_ORDER]}
    path.write_text(json.dumps({"sample_id": "s0", "delivered": secret, "supply_variants": receipt, "native_episode_receipt": {"role_visits": [
        {"stage": "perception", "execution_receipt": {"contacts": [{"agent_contact_id": "c:p"}]}}]}}) + "\n", encoding="utf-8")
    rows = reader.load_outputs_rows(path)
    assert secret not in json.dumps(rows) and rows[0]["perception"] == ["c:p"] and rows[0]["arms"][-1] == ("lock", "c:lock", 12)


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
        "recovered_at": "2026-10-25", "ledger_title": "the column flight re-registration", "agent": "the NX-T R3 recovery agent", "reason": "host restart",
        "root_cause": "infrastructure, not the cell", "fix": "none in the cell", "decision": "owner decision 309 A"}), encoding="utf-8")
    history = fam._load_history(root)
    assert set(history) == {"arm"} and len(history["arm"]) == 1 and history["arm"][0]["predecessors"][0]["contacts_spent"] == 700 and history["arm"][0]["recovery_index"] == 1
    fam.rcv.validate_recovery(history["arm"][0])
    assert fam._load_history(tmp_path) == {}
    with pytest.raises(ValueError, match="root_cause"):
        fam.build_arm_recovery({"recovered_at": "x"}, _snapshot())


def test_the_writer_recovery_text_and_flags_are_wired():
    import nxt_r3_write_registration as writer  # noqa: PLC0415

    ids = writer.identities(REPO)
    assert writer.recovery_blocks(REPO, ids, "x", "2026-10-25T00:00:00+00:00", "abc", "/wt", "br") == {}
    text = writer.recovery_sequence_text(ids)
    assert "recovery-input-arm-v1.json" in text and "predecessor-snapshot-arm-rec1-v1.json" in text and "NXT3_KINDS=arm" in text and "arm-only" in text
    out = subprocess.run([sys.executable, "-B", str(NX / "nxt_r3_write_registration.py"), "--help"], capture_output=True, text=True, cwd=REPO)
    assert out.returncode == 0
    for flag in ("--append-recovery-ledger", "--recovery-registered-at", "--recovery-base-commit", "--study-commit", "--append-ledger", "--registered-at"):
        assert flag in out.stdout


def test_the_mint_supersedes_only_a_strict_prefix_receipt(tmp_path, monkeypatch):
    from datetime import datetime, timezone

    import nxt_r3_mint_receipt as mint  # noqa: PLC0415

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
    chain = (NX / "batch_chain_nxt_r3.sh").read_text(encoding="utf-8")
    assert subprocess.run(["bash", "-n", str(NX / "batch_chain_nxt_r3.sh")], capture_output=True).returncode == 0
    assert '. "$SP/chain_lib.sh"' in chain
    assert 'wait_or_machine_signoff "bash scripts/flights/nx/nxt_r3_read.sh smoke" "$MAIN/$SIGNOFF_CONDITIONS" "$SIGNOFF_MARKER" 20' in chain
    assert "wait_signoff()" not in chain and "sleep 60" not in chain
    assert "SIGNOFF_MARKER=/home/chao/nxt3-decode-signoff.marker" in chain and "f.SIGNOFF_CONDITIONS" in chain
    assert "close_rows_after_seal" in chain and "close_rows $SMOKE_CLOSE_IDS" in chain and "close_rows $ALL_CLOSE_IDS" in chain
    for needle in ("smoke|arm|arm-only|all) export BATCH_SESSION=$THINK_SESSION", "arm-only) run_driver arm", "exit 9", '"$SMOKE_STATE" = sealed', "COMPLETED", "no sign-off marker",
                   "serving_swap.sh \"$SWAP_TARGET\"", "nxt_r3_family", "NXT3_SIGNOFF_WAIT_SECONDS", "is not resident; swapping to"):
        assert needle in chain, needle
    assert "SHORT=nxt3" in chain and "/home/chao/$SHORT-flight-commit.txt" in chain and 'spec["attempt"]' in chain and "nxt_r2b" not in chain and "7168" not in chain


def test_the_flip_read_and_repin_scripts_consume_the_family_record():
    flip, read, repin = [(NX / n).read_text(encoding="utf-8") for n in ("nxt_r3_flip.sh", "nxt_r3_read.sh", "nxt_r3_repin_cell.sh")]
    assert "PLAN_REC=" in flip and "rec_suffix" in flip and 'NXT3_KINDS:-"smoke arm"' in flip and "nxt_r3_family" in flip
    assert "SLUG=nxt-r3-solver-template-fold-b" in flip and "PKGN=slurp-nxt-r3-solver-template-fold-b-v1" in flip and "SHORT=nxt3" in flip
    assert "nxt_r3_family" in read and "SAEA-SLURP-NXT-R3-SOLVER-TEMPLATE-FOLD-B-READ-V1" in read and "slurp_nxt_r3_solver_template_column_read.py" in read
    assert "--mode supply-variants" in read and "perception-branches" not in read and re.search(r'STAGE=\$\{1:-read\}', read) and '"$STAGE" = "columns"' in read
    assert "NXT3_KIND" in repin and "nxt-r3-solver-template-fold-b" in repin and "2026-10-18" in repin


def _hook(tmp_path, chain_lines, *, stamp="2026-10-18T12:40:00Z", wait="3", poll="0.2", launch=None):
    out, chain = tmp_path / "queue.out", tmp_path / "chain.out"
    chain.write_text("\n".join(chain_lines) + ("\n" if chain_lines else ""), encoding="utf-8")
    ran = tmp_path / "ran.txt"
    launch = launch or f"echo launched-from $(pwd) > {ran}"
    env = dict(os.environ, NXT3_HOOK_CHAIN_OUT=str(chain), NXT3_HOOK_OUT=str(out), NXT3_HOOK_MAIN=str(tmp_path), NXT3_HOOK_POLL_SECONDS=poll,
               NXT3_HOOK_MAX_WAIT_SECONDS=wait, NXT3_HOOK_LAUNCH_CMD=launch, TMPDIR=str(tmp_path))
    done = subprocess.run(["bash", str(REPO / "scripts/flights/batch/queue/queue_nxt3_after_nxt2.sh"), *([stamp] if stamp else [])], capture_output=True, text=True, env=env, timeout=60)
    return done, out.read_text(encoding="utf-8") if out.exists() else "", ran


def test_the_queue_hook_launches_only_after_a_clean_r2_exit_later_than_the_stamp(tmp_path):
    script = REPO / "scripts/flights/batch/queue/queue_nxt3_after_nxt2.sh"
    assert subprocess.run(["bash", "-n", str(script)], capture_output=True).returncode == 0
    text = script.read_text(encoding="utf-8")
    assert "CHAIN_NXT2_EXIT" in text and "/home/chao/nxt2-chain.out" in text and "/home/chao/nxt3-queue.out" in text and "108000" in text and "POLL_SECONDS:-60" in text
    assert "package_launch.sh scripts/flights/nx/nxt_r3_launch_spec.json --from flip --until chain" in text and "exit 9" in text
    (tmp_path / "a").mkdir()
    done, log, ran = _hook(tmp_path / "a", ["CHAIN_NXT2_EXIT rc=0 2026-10-18T12:50:00Z"])
    assert done.returncode == 0 and ran.is_file() and "launching NX-T R3" in log and "launcher exit rc=0" in log
    (tmp_path / "b").mkdir()
    done, log, ran = _hook(tmp_path / "b", ["CHAIN_NXT2_EXIT rc=0 2026-10-18T09:00:00Z"])
    assert done.returncode == 8 and not ran.exists() and "TIMEOUT" in log                       # an older attempt's line is ignored
    (tmp_path / "c").mkdir()
    done, log, ran = _hook(tmp_path / "c", ["CHAIN_NXT2_EXIT rc=0 2026-10-18T09:00:00Z", "CHAIN_NXT2_EXIT rc=3 2026-10-18T13:00:00Z"])
    assert done.returncode == 9 and not ran.exists() and "rc=3" in log and "NOT launched" in log
    (tmp_path / "d").mkdir()
    done, log, ran = _hook(tmp_path / "d", ["CHAIN_NXT2_EXIT rc=0 2026-10-18T13:00:00Z"], launch="exit 4")
    assert done.returncode == 4 and "launcher exit rc=4" in log
    (tmp_path / "e").mkdir()
    done, _, _ = _hook(tmp_path / "e", [], stamp=None)
    assert done.returncode == 64


def test_the_queue_hook_ignores_the_informational_repin_line_but_not_a_real_refusal(tmp_path):
    info = "repin exit 1 (1 = its internal check refused the dirty tree, expected)"
    (tmp_path / "ok").mkdir()
    done, log, ran = _hook(tmp_path / "ok", ["CHAIN_NXT2_EXIT rc=0 2026-10-18T13:00:00Z"], launch=f"echo '{info}'; echo 'FLIP_CHAIN_DONE'")
    assert done.returncode == 0 and "real refusal" not in log and info in log                    # the false match that blocked the R2 rec2 hook
    (tmp_path / "bad").mkdir()
    done, log, _ = _hook(tmp_path / "bad", ["CHAIN_NXT2_EXIT rc=0 2026-10-18T13:00:00Z"], launch=f"echo '{info}'; echo 'check: FAIL cell x'")
    assert done.returncode == 10 and "real refusal" in log
    (tmp_path / "bad2").mkdir()
    done, log, _ = _hook(tmp_path / "bad2", ["CHAIN_NXT2_EXIT rc=0 2026-10-18T13:00:00Z"], launch="echo 'the gate refused the flip'")
    assert done.returncode == 10 and "real refusal" in log


def test_the_queue_hook_sees_a_line_that_appears_while_it_polls(tmp_path):
    chain = tmp_path / "chain.out"
    chain.write_text("chain start 2026-10-18T12:40:00Z\n", encoding="utf-8")
    ran = tmp_path / "ran.txt"
    env = dict(os.environ, NXT3_HOOK_CHAIN_OUT=str(chain), NXT3_HOOK_OUT=str(tmp_path / "q.out"), NXT3_HOOK_MAIN=str(tmp_path), NXT3_HOOK_POLL_SECONDS="0.2",
               NXT3_HOOK_MAX_WAIT_SECONDS="30", NXT3_HOOK_LAUNCH_CMD=f"echo ok > {ran}", TMPDIR=str(tmp_path))
    proc = subprocess.Popen(["bash", str(REPO / "scripts/flights/batch/queue/queue_nxt3_after_nxt2.sh"), "2026-10-18T12:40:00Z"], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    import time

    time.sleep(1.0)
    assert proc.poll() is None
    with chain.open("a", encoding="utf-8") as handle:
        handle.write("CHAIN_NXT2_EXIT rc=0 2026-10-18T14:00:00Z\n")
    assert proc.wait(timeout=30) == 0 and ran.is_file()


def test_the_launch_spec_is_the_r2b_form_with_the_r3_names():
    spec = js("scripts/flights/nx/nxt_r3_launch_spec.json")
    r2b = js("scripts/flights/nx/nxt_r2b_launch_spec.json")
    assert spec["schema"] == "saea-package-launch-spec-v1" == r2b["schema"] and list(spec["steps"]) == list(r2b["steps"]) == ["derive", "write", "countersign", "mint", "commit", "flip", "chain", "read"]
    assert (spec["short"], spec["package"], spec["readiness_dir"]) == ("nxt3", fam.PKG_NAME, fam.PACKAGE) and spec["launch_id"] == "nxt3-first-attempt"
    steps = spec["steps"]
    assert steps["derive"]["cmd"].endswith("nxt_r3_derive_cells.py") and "nxt_r3_write_registration.py --study-commit {head}" in steps["write"]["cmd"]
    assert "--registered-at {utc}" in steps["write"]["cmd"] and "--append-ledger" in steps["write"]["cmd"]
    assert steps["mint"]["cmd"].endswith("nxt_r3_mint_receipt.py") and steps["mint"]["done_if"]["contains"] == [fam.CELLS["arm"]["fit_run"]] and steps["mint"]["done_if"]["file"] == fam.DECISION_RELPATH
    assert steps["countersign"]["texts"] == "{readiness_dir}/countersign-row-texts-v1.json" and steps["countersign"]["skip_substrings"] == ["-READ-"]
    assert set(steps["commit"]["paths"]) == {"configs", "docs/exposure-ledger.md", "{readiness_dir}", "{readiness_dir}-preregistration.md"}
    flip = steps["flip"]
    assert flip["script"] == "scripts/flights/nx/nxt_r3_flip.sh" and flip["package"] == fam.PACKAGE and flip["env"] == {"NXT3_KINDS": "smoke arm"}
    assert flip["cells"] == [fam.CELLS["smoke"]["cell"], fam.CELLS["arm"]["cell"]] and flip["pins_commit_msg"] == "/home/chao/nxt3-pins-commit.txt"
    assert flip["flight_commit_file"] == "/home/chao/nxt3-flight-commit.txt" == steps["chain"]["flight_commit_file"]
    assert flip["pins_commit_text"].rstrip("\n").splitlines()[-1] == "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>" and flip["pins_commit_text"].startswith("NX-T R3")
    assert steps["chain"]["task"] == "SAEA-Chain-NXT3" and steps["chain"]["wrapper"] == "/home/chao/saea-queue/chain_nxt3.sh"
    assert steps["read"]["cmd"] == "bash scripts/flights/nx/nxt_r3_read.sh smoke"
    wrapper = (REPO / "scripts/flights/batch/queue/chain_nxt3.sh").read_text(encoding="utf-8")
    assert subprocess.run(["bash", "-n", str(REPO / "scripts/flights/batch/queue/chain_nxt3.sh")], capture_output=True).returncode == 0
    assert "batch_chain_nxt_r3.sh all" in wrapper and "CHAIN_NXT3_EXIT" in wrapper and "/home/chao/nxt3-flight-commit.txt" in wrapper
    import package_launch  # noqa: PLC0415

    launch = package_launch.Launch(spec, REPO, dry=True, root_countersign=False, redo=set())
    launch.head = lambda: "0" * 40                     # rendering needs no repository state here (a linked worktree is not readable from every shell)
    assert launch.log_path == Path("/home/chao/nxt3-launch.out") and launch.render("{readiness_dir}") == fam.PACKAGE


def test_every_script_the_spec_names_exists_and_parses():
    for rel in ("nxt_r3_derive_cells.py", "nxt_r3_write_registration.py", "nxt_r3_mint_receipt.py", "nxt_r3_dry_run.py", "nxt_r3_family.py"):
        subprocess.run([sys.executable, "-B", "-c", "import ast,sys; ast.parse(open(sys.argv[1], encoding='utf-8').read())", str(NX / rel)], check=True)
    assert (REPO / fam.READER).is_file()
