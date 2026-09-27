"""Owner decision 160: COMP-1 and G5 fly in ONE campaign with ONE shared in-chain A/A.

Two groups of assertions. The pure helpers of
``scripts/flights/comp1/comp1_g5_shared_aa_proof.py`` (the tool that proves the decision's
condition model-free) are exercised on synthetic inputs, so a classification or comparison defect
cannot pass silently. Config only otherwise: no data root, no lock, no adapter, no contact.
"""

from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
PROOF_TOOL = REPO / "scripts/flights/comp1/comp1_g5_shared_aa_proof.py"
C1 = REPO / "docs/readiness/2026-09-27-slurp-stage3-comp-1-fold-a-v1"
G5 = REPO / "docs/readiness/2026-09-27-slurp-stage3-g5-fold-a-v1"
G5_PREREG = REPO / "docs/readiness/2026-09-27-slurp-stage3-g5-fold-a-v1-preregistration.md"
PROOF = C1 / "shared-aa-proof-v1.json"
PROOF_REL = "docs/readiness/2026-09-27-slurp-stage3-comp-1-fold-a-v1/shared-aa-proof-v1.json"
FLIGHTS = REPO / "scripts/flights"

SHARED_AA = "SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1"
COMP1_ARM = "SAEA-SLURP-STAGE3-COMP1-FOLD-A-V1"
G5_ARM = "SAEA-SLURP-STAGE3-G5-FOLD-A-V1"
G5_AA = "SAEA-SLURP-STAGE3-G5-AA-FOLD-A-V1"
G5_AA_FIT = "SAEA-SLURP-STAGE3-G5-AA-FOLD-A-FIT-V1"
PLAN_SUPPLY_OUTPUT_SHA = "ba5e1faab9550fcae700f649a0ec6674327ffefe97d7044bb7ea3887536fb54f"


def _load_tool():
    spec = importlib.util.spec_from_file_location("comp1_g5_shared_aa_proof", PROOF_TOOL)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def tool():
    return _load_tool()


# ---------------------------------------------------------------------------------------------
# the proof tool's pure helpers
# ---------------------------------------------------------------------------------------------


def test_flatten_keys_dicts_by_dot_and_lists_by_index(tool) -> None:
    flat = tool.flatten({"a": {"b": [1, {"c": 2}], "e": {}}, "f": []})
    assert flat == {"a.b[0]": 1, "a.b[1].c": 2, "a.e": {}, "f": []}


@pytest.mark.parametrize(
    ("leaf", "klass"),
    [
        ("cells[0].run_id", "bookkeeping"),
        ("cells[0].readiness.requirements[0].sha256", "bookkeeping"),
        ("cells[0].readiness.requirements", "bookkeeping"),
        ("experiment_id", "bookkeeping"),
        ("native_contact_fit.run_id", "bookkeeping"),
        ("generation_budget.target", "bookkeeping"),
        ("what_this_is", "bookkeeping"),
        ("knowledge_stores.intent-boundaries.phase_supply.perception.k", "supply-recall-width"),
        # anything that could reach a request is never waved through
        ("phase_material.reviewer.instruction_template", "unclassified"),
        ("native_contact_fit.budget_tokens", "unclassified"),
        ("knowledge_stores.intent-boundaries.phase_supply.perception.rank_weights.w_agree", "unclassified"),
        ("policy", "unclassified"),
        ("cellsX", "unclassified"),
    ],
)
def test_classify_leaf_names_bookkeeping_and_the_recall_width_and_nothing_else(tool, leaf, klass) -> None:
    assert tool.classify_leaf(leaf)[0] == klass


def test_config_diff_marks_only_unclassified_leaves_request_affecting(tool) -> None:
    left = {"experiment_id": "A", "policy": "p", "knowledge_stores": {"intent-boundaries": {
        "phase_supply": {"perception": {"k": 60}}}}}
    right = {"experiment_id": "B", "policy": "q", "knowledge_stores": {"intent-boundaries": {
        "phase_supply": {"perception": {"k": 8}}}}}
    rows = {row["leaf"]: row for row in tool.config_diff(left, right)}
    assert set(rows) == {"experiment_id", "policy",
                         "knowledge_stores.intent-boundaries.phase_supply.perception.k"}
    assert rows["policy"]["request_affecting"] is True
    assert rows["experiment_id"]["request_affecting"] is False
    assert rows["knowledge_stores.intent-boundaries.phase_supply.perception.k"]["class"] == "supply-recall-width"


def test_contact_key_and_role_come_from_the_last_history_turn(tool) -> None:
    payload = {"sample_id": "s1", "history": [
        {"contact_id": "pol:perception:0:s1"}, {"contact_id": "pol:planner:1:s1"}]}
    key = tool.contact_key(payload)
    assert key == "s1|pol:planner:1:s1"
    assert tool.role_of(key.split("|", 1)[1]) == ("planner", 1)
    with pytest.raises(ValueError):
        tool.contact_key({"sample_id": "s1", "history": []})


def test_canned_answers_are_deterministic_and_role_shaped(tool) -> None:
    intents = tool.CANNED_INTENTS
    perception = json.loads(tool.canned_answer("perception", 0, "s", intents))
    assert [c["intent_id"] for c in perception["candidates"]] == list(intents)
    assert json.loads(tool.canned_answer("solver", 0, "s", intents)) == {
        "scenario": "weather", "action": "query", "entities": []}
    revising = next(f"s{i}" for i in range(64) if tool.revises_first(f"s{i}"))
    accepting = next(f"s{i}" for i in range(64) if not tool.revises_first(f"s{i}"))
    assert tool.canned_answer("planner", 0, revising, intents) == "REVISE"
    assert tool.canned_answer("planner", 1, revising, intents) == "ACCEPT"
    assert tool.canned_answer("planner", 0, accepting, intents) == "ACCEPT"
    with pytest.raises(ValueError):
        tool.canned_answer("summariser", 0, "s", intents)


def test_the_run_id_normalization_blanks_only_the_run_id_derived_field(tool) -> None:
    payload = {"history": [{"source_query_state_sha256": "x", "content": "c"}], "request_id": "r"}
    assert tool.run_id_normalized_payload(payload) == {
        "history": [{"source_query_state_sha256": "<run-id-derived>", "content": "c"}],
        "request_id": "r",
    }


def _row(payload: str, normalized: str, body: str) -> dict:
    return {"payload_sha256": payload, "normalized_payload_sha256": normalized, "body_sha256": body}


def test_compare_captures_reports_each_byte_level_separately(tool) -> None:
    same = tool.compare_captures({"k": _row("p", "n", "b")}, {"k": _row("p", "n", "b")})
    assert same["payload_bytes_identical"] and same["post_body_bytes_identical"]
    assert same["run_id_normalized_payload_bytes_identical"]
    run_id_only = tool.compare_captures({"k": _row("p1", "n", "b")}, {"k": _row("p2", "n", "b")})
    assert not run_id_only["payload_bytes_identical"]
    assert run_id_only["run_id_normalized_payload_bytes_identical"]
    assert run_id_only["post_body_bytes_identical"]
    body = tool.compare_captures({"k": _row("p", "n", "b1")}, {"k": _row("p", "n", "b2")})
    assert not body["post_body_bytes_identical"] and body["first_mismatches"] == ["k"]
    missing = tool.compare_captures({"k": _row("p", "n", "b"), "j": _row("p", "n", "b")},
                                    {"k": _row("p", "n", "b")})
    assert not missing["keys_equal"] and not missing["payload_bytes_identical"]
    assert missing["only_in_comp1_aa"] == ["j"]


def test_identity_hashes_are_quoted_by_prefix_and_output_digests_in_full(tool) -> None:
    full = "ab" * 32
    quoted = tool.quote_hashes_by_prefix({
        "composed_config_hash": full, "output_sha256": full, "sealed_plan_output_sha256": full,
        "rows": [{"sha256": full}], "note": "not a hash", "short": "abcd",
    })
    assert quoted["composed_config_hash"] == "sha256-prefix16:" + full[:16]
    assert quoted["rows"][0]["sha256"] == "sha256-prefix16:" + full[:16]
    assert quoted["output_sha256"] == full and quoted["sealed_plan_output_sha256"] == full
    assert quoted["note"] == "not a hash" and quoted["short"] == "abcd"


def test_the_self_control_counts_differing_fields_per_contact(tool) -> None:
    first = {"k": {"payload": json.dumps({"request_id": "a", "history": [{"x": 1}]}),
                   "body": json.dumps({"id_slot": 0, "messages": []})}}
    second = {"k": {"payload": json.dumps({"request_id": "b", "history": [{"x": 1}]}),
                    "body": json.dumps({"id_slot": 3, "messages": []})}}
    reading = tool.self_control_reading(first, second, 1)
    assert reading["payload_fields_differing"] == {"request_id": 1}
    assert reading["post_body_fields_differing"] == {"id_slot": 1}
    assert reading["keys_equal"] and reading["contacts"] == 1


def test_classify_supply_input_names_the_recall_width_and_its_identity_hash(tool) -> None:
    assert tool.classify_supply_input("sources.supply_spec.k") == "supply-recall-width"
    assert tool.classify_supply_input("config_sha256").startswith("supply-config-identity-hash")
    assert tool.classify_supply_input("sources.supply_spec.rank_weights.w_agree") == "unclassified"


# ---------------------------------------------------------------------------------------------
# the proof as committed: decision 160's condition holds
# ---------------------------------------------------------------------------------------------


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def proof() -> dict:
    return _read(PROOF)


def test_the_committed_proof_finds_the_two_aa_cells_identical(proof: dict) -> None:
    assert proof["schema"] == "saea-comp1-g5-shared-aa-proof-v1" and proof["owner_decision"] == 160
    assert proof["verdict"] == "IDENTICAL"
    assert proof["contacts"] == {"model": 0, "server": 0, "tokenizer": 0, "encoder": 0, "scorer": 0}
    assert proof["cells"]["comp1_aa"]["run_id"] == SHARED_AA and proof["cells"]["g5_aa"]["run_id"] == G5_AA
    # 1. composed config: nothing request-affecting; the one non-bookkeeping leaf is the recall width
    diff = proof["composed_config_diff"]
    assert diff["request_affecting_leaves"] == []
    assert {row["class"] for row in diff["differing_leaves"]} == {"bookkeeping", "supply-recall-width"}
    assert diff["supply_recall_width"] == [{
        "leaf": "knowledge_stores.intent-boundaries.phase_supply.perception.k", "comp1_aa": 60, "g5_aa": 8}]
    # 2. prepared supply: both reproduce the sealed PLAN output digest on the whole roster
    supply = proof["prepared_supply"]
    for name in ("comp1_aa", "g5_aa"):
        assert supply[name]["output_sha256"] == PLAN_SUPPLY_OUTPUT_SHA
        assert supply[name]["rows_seeded"] == 1080 and supply[name]["selected_value_ids"] == 8624
    assert supply["output_digests_equal"] and supply["both_equal_sealed_plan"]
    # 3. request bytes: >= 50 rows, every contact, both modes
    request = proof["request_bytes"]
    common, own = request["common_run_id"], request["own_run_ids"]
    for mode in (common, own):
        assert mode["comp1_aa"]["rows_dispatched"] >= 50 and mode["g5_aa"]["rows_dispatched"] >= 50
        assert mode["comparison"]["keys_equal"] and mode["comparison"]["contacts_comp1_aa"] > 0
        assert mode["comparison"]["post_body_bytes_identical"]
        assert mode["comparison"]["run_id_normalized_payload_bytes_identical"]
        assert mode["comp1_aa"]["contacts_by_role"] == mode["g5_aa"]["contacts_by_role"]
        assert mode["comp1_aa"]["rows_revised_by_canned_planner"] > 0
    assert common["comparison"]["payload_bytes_identical"]
    assert set(request["scheduling_self_control"]["post_body_fields_differing"]) <= {"id_slot"}


def test_the_proof_quotes_no_identity_hash_the_flip_could_rewrite(proof: dict) -> None:
    """core.flight.repin rewrites every JSON file of the COMP-1 package from old identity hashes to new
    ones and refuses any residue under docs/: the proof may quote in full only the output digests."""

    full = set(re.findall(r"[0-9a-f]{64}", PROOF.read_text(encoding="utf-8")))
    assert full == {PLAN_SUPPLY_OUTPUT_SHA}
    for plan in C1.glob("*plan-registered-v1.json"):
        registered = _read(plan)
        for value in (registered["composed_config_hash"], registered["execution_plan"]["protocol_hash"]):
            assert value not in full


# ---------------------------------------------------------------------------------------------
# the wiring: G5 re-declared, its own A/A superseded unflown, the gate content
# ---------------------------------------------------------------------------------------------


def test_g5_reads_its_arm_at_the_shared_aa_and_cites_the_proof(proof: dict) -> None:
    facts = _read(G5 / "registered-facts-v1.json")
    arm = facts["stage3_measurement"][G5_ARM]
    assert arm["replicate_run_id"] == SHARED_AA
    assert "decision 160" in arm["replicate_note"] and PROOF_REL in arm["replicate_note"]
    shared = facts["shared_in_chain_replicate"]
    assert shared["owner_decision"] == 160 and shared["replicate_run_id"] == SHARED_AA
    assert shared["superseded_unflown"] == [G5_AA, G5_AA_FIT]
    assert shared["condition_proof"]["relpath"] == PROOF_REL
    assert shared["condition_proof"]["sha256"] == hashlib.sha256(PROOF.read_bytes()).hexdigest()
    assert shared["condition_proof"]["verdict"] == proof["verdict"] == "IDENTICAL"
    assert facts["comparator"]["in_chain_replicate"]["run_id"] == SHARED_AA
    assert facts["comparator"]["in_chain_replicate"]["superseded_registration"]["run_ids"] == [G5_AA, G5_AA_FIT]
    assert facts["stage3_measurement"][G5_AA]["status"].startswith("superseded-unflown")
    text = G5_PREREG.read_text(encoding="utf-8")
    start = text.index("```json")
    fenced = json.loads(text[text.index("\n", start) + 1 : text.index("```", start + 7)])
    assert fenced["stage3_measurement"] == facts["stage3_measurement"]
    assert "## Owner decision 160: one shared in-chain A/A" in text
    recipe = _read(G5 / "analysis-recipe-v1.json")
    assert recipe["arms"]["in_chain_replicate"]["run_id"] == SHARED_AA
    assert recipe["arms"]["in_chain_replicate"]["attempt_id"] == "attempt-slurp-native-stage3-comp1-aa-fold-a-generation-v1"
    assert SHARED_AA in recipe["steps"][0]
    comp1 = _read(C1 / "registered-facts-v1.json")["shared_in_chain_replicate"]
    assert comp1["this_aa_serves"] == [COMP1_ARM, G5_ARM]
    assert comp1["condition_proof"]["sha256"] == shared["condition_proof"]["sha256"]


def test_the_two_campaign_plans_realise_one_chain_with_the_aa_first() -> None:
    comp1 = _read(REPO / "configs/campaign/slurp-native-stage3-comp1-fold-a-v1.json")
    g5 = _read(REPO / "configs/campaign/slurp-native-stage3-g5-fold-a-v1.json")
    assert [c["cell"] for c in comp1["cells"]] == [
        "slurp-native-stage3-comp1-aa-fold-a-v1", "slurp-native-stage3-comp1-fold-a-v1"]
    assert [c["cell"] for c in g5["cells"]] == ["slurp-native-stage3-g5-fold-a-v1"]
    # the superseded A/A is untouched: still registered, still held, never deleted
    fragment = _read(REPO / "configs/experiment/slurp-native-stage3-g5-aa-fold-a-v1.json")
    assert fragment["cells"][0]["run_id"] == G5_AA and fragment["cells"][0]["readiness"]["state"] == "held"


def _ledger_row(run: str) -> list[str]:
    lines = io.open(REPO / "docs/exposure-ledger.md", encoding="utf-8", newline="").read().split("\n")
    found = [line for line in lines if line.startswith("|") and ("| " + run + " |") in line]
    assert len(found) == 1, run
    parts = found[0].split("|")
    assert len(parts) == 17, run
    return [part.strip() for part in parts[1:-1]]


def test_the_superseded_rows_say_so_and_stay_unconsumed() -> None:
    for run in (G5_AA, G5_AA_FIT):
        cells = _ledger_row(run)
        assert cells[8] == "no"
        assert cells[3].endswith("[SUPERSEDED UNFLOWN by owner decision 160]")
        assert cells[14].startswith("SUPERSEDED UNFLOWN (owner decision 160")
        assert "Plan SHA256" in cells[14]
    assert "OWNER DECISION 160" in _ledger_row(G5_ARM)[14] and SHARED_AA in _ledger_row(G5_ARM)[14]
    assert "OWNER DECISION 160" in _ledger_row(SHARED_AA)[14] and G5_ARM in _ledger_row(SHARED_AA)[14]


def test_the_effect_floor_gate_reads_the_cross_package_replicate() -> None:
    spec = importlib.util.spec_from_file_location(
        "stage3_effect_floor_check", REPO / "scripts/checks/stage3_effect_floor_check.py")
    gate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gate)
    data = gate.evaluate(REPO)
    by_run = {row["run_id"]: row for row in data["in_scope_cells"]}
    arm = by_run[G5_ARM]["declaration"]
    assert arm["replicate_run_id"] == SHARED_AA
    assert arm["source"] == "docs/readiness/2026-09-27-slurp-stage3-g5-fold-a-v1/registered-facts-v1.json"
    shared = by_run[SHARED_AA]["declaration"]
    assert shared["source"] == "docs/readiness/2026-09-27-slurp-stage3-comp-1-fold-a-v1/registered-facts-v1.json"
    ours = [f for f in data["findings"] if f["run_id"] in (G5_ARM, G5_AA, SHARED_AA)]
    assert ours == [], ours


# ---------------------------------------------------------------------------------------------
# the flip and the chain
# ---------------------------------------------------------------------------------------------


def _script(relpath: str) -> str:
    return (FLIGHTS / relpath).read_text(encoding="utf-8")


@pytest.mark.parametrize("relpath", [
    "comp1/comp1_g5_flip.sh", "comp1/batch_chain_comp1_g5.sh", "comp1/batch_chain_comp1.sh",
    "g5/g5_flip.sh", "g5/batch_chain_g5.sh",
])
def test_the_scripts_parse(relpath: str) -> None:
    assert subprocess.run(["bash", "-n", str(FLIGHTS / relpath)], capture_output=True).returncode == 0


def test_the_combined_flip_runs_comp1_then_g5_without_its_aa_and_converges_at_one_head() -> None:
    flip = _script("comp1/comp1_g5_flip.sh")
    body = flip[flip.index('cd "$MAIN"'):]
    comp1 = body.index('bash "$CP/comp1_flip.sh"')
    g5_smoke = body.index("$G5/g5_repin_smoke.sh")
    g5_arm = body.index("$G5/g5_repin_arm.sh")
    convergence = body.index("CYCLES=(")
    assert comp1 < g5_smoke < g5_arm < convergence
    assert "g5_repin_aa.sh" not in flip and "g5_flip.sh" not in body
    assert "--allow-output-change" not in body
    cycles = body[convergence: body.index("\n)\n", convergence)]
    for script in ("comp1_repin_smoke.sh", "comp1_repin_aa.sh", "comp1_repin_arm.sh", "g5_repin_smoke.sh", "g5_repin_arm.sh"):
        assert script in cycles, script
    assert '[ "$BEFORE" = "$AFTER" ]' in body and "/home/chao/comp1g5-flight-commit.txt" in body
    for refusal in ('"IDENTICAL"', "not the arm alone", "--drop-aa"):
        assert refusal in flip, refusal


def test_the_chain_queues_two_steps_the_shared_aa_in_the_first(tmp_path: Path) -> None:
    chain = _script("comp1/batch_chain_comp1_g5.sh")
    writer = chain[chain.index("QUEUE=\"$QUEUE\" /home/chao/.venvs/speechrl/bin/python - <<'PY'"):]
    source = writer[writer.index("\n") + 1: writer.index("\nPY\n")]
    queue = tmp_path / "queue.json"
    subprocess.run(["python3", "-c", source], check=True, env=dict(os.environ, QUEUE=str(queue)))
    steps = json.loads(queue.read_text(encoding="utf-8"))
    assert [step["short"] for step in steps] == ["comp1", "g5"]
    assert [step["order"] for step in steps] == [1, 2]
    comp1, g5 = steps
    assert comp1["campaign_plan"] == "configs/campaign/slurp-native-stage3-comp1-fold-a-v1.json"
    assert comp1["smoke_cell"] == "slurp-native-stage3-comp1-fold-a-smoke-4-v1" and comp1["run_id"] == COMP1_ARM
    assert g5["campaign_plan"] == "configs/campaign/slurp-native-stage3-g5-fold-a-v1.json"
    assert g5["smoke_cell"] == "slurp-native-stage3-g5-fold-a-smoke-4-v1" and g5["run_id"] == G5_ARM
    for step in steps:
        assert step["expected_rows"] == 1080 and step["ceiling_per_row"] == 11 and step["notool"] is True
    assert chain.count("bash $SP/batch_driver.sh") == 1 and "/home/chao/comp1g5-flight-commit.txt" in chain
    assert "shared-A/A precondition refused" in chain


def test_the_standalone_g5_and_comp1_paths_refuse_in_the_shared_mode() -> None:
    for relpath in ("g5/g5_flip.sh", "g5/batch_chain_g5.sh"):
        text = _script(relpath)
        assert "refusing (owner decision 160)" in text and "slurp-native-stage3-g5-aa-fold-a-v1" in text
    comp1 = _script("comp1/batch_chain_comp1.sh")
    assert "refusing (owner decision 160)" in comp1 and "COMP1_ALONE" in comp1
