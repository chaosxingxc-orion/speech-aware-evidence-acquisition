"""NX-T R1 SEAL-ONLY completion of the stopped column flight: the derived cell, the package, the scripts and the seal-only read.

Model-free and synthetic where it must be; the committed package is checked against itself, against the parent registration and against the family. No contact, no ledger
write, no flip, no mint. The checks that need the data root (the stopped attempt's trace, the cell's pins) are the derive's and the flip's own preconditions.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
for _extra in (REPO / "scripts" / "flights" / "nx", REPO / "scripts" / "flights" / "direct", REPO / "scripts" / "flights" / "tfrl", REPO / "scripts" / "flights" / "lib",
               REPO / "scripts" / "analysis", REPO / "scripts" / "checks", REPO / "src"):
    if str(_extra) not in sys.path:
        sys.path.insert(0, str(_extra))

import nxt_r1_family as fam  # noqa: E402
import nxt_r1_sealonly_derive_cell as derive  # noqa: E402
import nxt_r1_sealonly_mint_receipt as mint  # noqa: E402
import slurp_nxt_thinking_policy_column_read as reader  # noqa: E402

from speech_aware_evidence_acquisition.core.config import compose  # noqa: E402
from speech_aware_evidence_acquisition.core.flight.campaign import load_campaign_cells  # noqa: E402
from speech_aware_evidence_acquisition.data.splits import prefixed, split_identity_hash  # noqa: E402
from speech_aware_evidence_acquisition.rails.hashing import content_hash  # noqa: E402

SPEC = fam.sealonly_spec()
PKG = REPO / SPEC["package"]
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def js(rel: str) -> dict:
    return json.loads((REPO / rel).read_text(encoding="utf-8"))


ROWS = js(SPEC["complete_rows"])
EXP = js(f"configs/experiment/{SPEC['experiment']}.json")
CELL = EXP["cells"][0]
N = ROWS["count"]


# ---- the identities ---------------------------------------------------------------------------------------------------------------


def test_the_identities_derive_from_the_rec1_arm_cell():
    # The seal-only package (decision 320 A, now UNUSED: owner ruling 320 B chose the rec2 mode-A resume) is pinned to the rec1 identities; the family's arm cell has
    # moved on to rec2, so the seal-only spec derives the rec1 ids from the family's recovery history, not from the live arm cell.
    arm, rec1 = fam.CELLS["arm"], fam.RECOVERY_HISTORY["arm"][0]
    stopped_attempt, stopped_fit_run = fam.recovery("arm")["predecessor_attempt_id"], fam.recovery("arm")["predecessor_fit_run_id"]
    stopped_fit_attempt = fam.recovery("arm")["predecessor_fit_attempt_id"]
    assert rec1["recovery_index"] == 1 and arm["attempt"].endswith("-rec2-v1")
    assert SPEC["run"] == arm["run"] and SPEC["fit_run"] == stopped_fit_run and SPEC["predecessor_attempt"] == stopped_attempt
    assert SPEC["attempt"] == stopped_attempt.replace("-rec1-v1", "-rec1-sealonly-v1") and SPEC["attempt"] != stopped_attempt
    assert SPEC["fit_attempt"] == stopped_fit_attempt.replace("-rec1-v1", "-rec1-sealonly-v1")
    assert SPEC["package"] == f"docs/readiness/{fam.DATE}-slurp-nxt-r1-thinking-policy-fold-b-v1-sealonly-v1"
    assert SPEC["cell"] == SPEC["experiment"] and SPEC["cell"].endswith("-v1-sealonly")
    assert SPEC["decision_relpath"].startswith("coordination/slurp-nxt-r1-thinking-policy-fold-b-v1/") and SPEC["decision_relpath"].endswith("root-admission-sealonly-v1.json")
    assert SPEC["decision_relpath"] != fam.DECISION_RELPATH                                 # the column's own receipt is never touched


# ---- the cell -------------------------------------------------------------------------------------------------------------------


def test_the_cell_is_a_held_mode_a_seal_only_resume_of_the_stopped_attempt():
    assert CELL["run_id"] == SPEC["run"] and CELL["cell_id"] == SPEC["cell"] and CELL["attempt_id"] == SPEC["attempt"]
    assert CELL["baseline_fragment"] == SPEC["baseline"]
    resume = CELL["resume_from"]
    assert set(resume) == {"attempt_id", "trace_sha256"} and resume["attempt_id"] == SPEC["predecessor_attempt"] and HEX64.match(resume["trace_sha256"])
    assert CELL["allowed_execution_stages"] == ["check", "prepare-supply", "seal-only"]
    assert CELL["readiness"]["state"] == "held"
    assert [r["kind"] for r in CELL["readiness"]["requirements"]] == ["preparation", "preparation"]       # the flip adds the decision requirement
    assert EXP["split_id"].endswith(f"-NXT1-COMPLETE-{N}")
    assert EXP["fragment_kind"] == f"saea-{SPEC['experiment']}"
    base = js(f"configs/baseline/{SPEC['baseline']}.json")
    parent = js(f"configs/baseline/{SPEC['parent_baseline']}.json")
    assert base["native_contact_fit"]["attempt_id"] == SPEC["fit_attempt"] and base["native_contact_fit"]["run_id"] == SPEC["fit_run"]
    differing = sorted(k for k in set(base) | set(parent) if base.get(k) != parent.get(k))
    assert differing == ["native_contact_fit", "what_this_is"]                              # the parent's bytes except the FIT attempt id and the note
    # the parent arm cell is on rec2 now: the seal-only baseline keeps the rec1 FIT identity, so only the FIT run / attempt ids may differ
    assert {k: v for k, v in base["native_contact_fit"].items() if k not in ("attempt_id", "run_id")} == {k: v for k, v in parent["native_contact_fit"].items() if k not in ("attempt_id", "run_id")}


def test_the_cell_composes_and_the_planned_config_hash_is_the_composed_one():
    composed = compose(REPO, CELL["model_fragment"], CELL["dataset_fragment"], CELL["baseline_fragment"], SPEC["experiment"])
    plan = js(f"{SPEC['package']}/generation-plan-registered-v1.json")
    fit = js(f"{SPEC['package']}/fit-plan-registered-v1.json")
    assert plan["composed_config_hash"] == fit["composed_config_hash"] == composed.config_hash
    assert composed.values["split_id"] == EXP["split_id"] and composed.values["native_episode"]["finite_completion_policy"] == "deliver-latest-or-abstain"
    cells = [c for c in load_campaign_cells(REPO, SPEC["experiment"]) if c.document["cell_id"] == SPEC["cell"]]
    assert len(cells) == 1 and cells[0].run_id == SPEC["run"]


# ---- the roster ---------------------------------------------------------------------------------------------------------------------


def test_the_complete_rows_are_a_strict_subset_of_the_fold_b_roster_and_account_for_every_row():
    parent = js(fam.ROSTER["arm"])
    parent_ids = [i["sample_id"] for i in parent["items"]]
    ids = [i["sample_id"] for i in ROWS["items"]]
    failed, never = ROWS["failed_rows"]["sample_ids"], ROWS["never_started_rows"]["sample_ids"]
    assert len(ids) == N == len(set(ids)) and set(ids) < set(parent_ids)
    assert ids == [sid for sid in parent_ids if sid in set(ids)]                              # the parent's order
    assert len(failed) == ROWS["failed_rows"]["count"] and len(never) == ROWS["never_started_rows"]["count"]
    assert set(ids) | set(failed) | set(never) == set(parent_ids) and not (set(ids) & set(failed)) and not (set(ids) & set(never)) and not (set(failed) & set(never))
    assert N + len(failed) + len(never) == ROWS["parent_rows"] == 1080
    assert ROWS["split_identity_hash"] == split_identity_hash(prefixed("slurp", ids)) != parent["split_identity_hash"]
    assert ROWS["ids_sha256"] == hashlib.sha256("\n".join(ids).encode()).hexdigest()
    assert ROWS["subset_of"]["sha256"] == hashlib.sha256((REPO / fam.ROSTER["arm"]).read_bytes()).hexdigest()
    assert "derived_from" not in ROWS and ROWS["schema"] == "saea-nxt-r1-sealonly-roster-v1"   # not a partition declaration, not in the exposure gate's roster registry
    for item, original in zip(ROWS["items"], [i for i in parent["items"] if i["sample_id"] in set(ids)]):
        assert item == original and item["stratum"] and item["utterance_id"]
    assert not str(PKG.relative_to(REPO)).startswith("docs/receipts/rosters")


def test_the_dataset_fragment_is_the_parent_view_restricted_to_the_complete_rows():
    fragment = js(f"configs/dataset/{CELL['dataset_fragment']}.json")
    parent = js("configs/dataset/slurp-speech-native-evo-fold-b-1080.json")
    ids = [i["sample_id"] for i in ROWS["items"]]
    assert [i["sample_id"] for i in fragment["items"]] == ids and fragment["count"] == N
    assert fragment["items"] == [i for i in parent["items"] if i["sample_id"] in set(ids)]    # byte-identical items
    unsigned = {k: v for k, v in fragment.items() if k != "runtime_view_sha256"}
    assert fragment["runtime_view_sha256"] == content_hash(unsigned)
    assert fragment["split_identity_hash"] == ROWS["split_identity_hash"] and fragment["split_name"] == EXP["split_id"] != parent["split_name"]
    assert fragment["audio_seconds_total"] == round(sum(i["audio_seconds"] for i in fragment["items"]), 9) == pytest.approx(ROWS["audio_seconds_total"])
    for key in ("d1_manifest_sha256", "d1_media_supplement", "d1_media_supplement_sha256", "carrier_lock_key", "split_role", "schema", "seed"):
        assert fragment[key] == parent[key]
    assert EXP["population"]["count"] == N and EXP["population"]["split_identity_hash"] == ROWS["split_identity_hash"]
    assert EXP["populations"] == [{"dataset_fragment": CELL["dataset_fragment"], "ids": ids}]


def test_subset_runtime_view_is_deterministic_and_refuses_a_tampered_parent():
    items = [{"sample_id": f"slurp:train:{i:06d}:a", "audio_seconds": 1.5, "audio_sha256": "a" * 64, "media_relpath": f"m/{i}.flac", "packet_id": f"slurp/train/{i:06d}/a",
              "sample_rate_hz": 16000} for i in range(6)]
    parent = {"audio_seconds_total": 9.0, "carrier_lock_key": "slurp", "count": 6, "items": items, "seed": 1, "split_identity_hash": "0" * 64, "split_name": "P", "split_role": "discovery",
              "source_binding_sha256": "1" * 64}
    parent["runtime_view_sha256"] = content_hash({k: v for k, v in parent.items()})
    rows = {"items": [items[1], items[4]], "count": 2}
    view, receipt = derive.subset_runtime_view(parent, rows, "P-SUB")
    assert [i["sample_id"] for i in view["items"]] == [items[1]["sample_id"], items[4]["sample_id"]] and view["count"] == 2 and view["split_name"] == "P-SUB"
    assert view["audio_seconds_total"] == 3.0 and view["split_identity_hash"] == split_identity_hash(prefixed("slurp", receipt["sample_ids"]))
    assert view["runtime_view_sha256"] == content_hash({k: v for k, v in view.items() if k != "runtime_view_sha256"})
    assert derive.subset_runtime_view(parent, rows, "P-SUB")[0] == view
    bad = copy.deepcopy(parent)
    bad["items"][0]["audio_seconds"] = 9.9
    with pytest.raises(SystemExit, match="hash differs"):
        derive.subset_runtime_view(bad, rows, "P-SUB")


# ---- the package --------------------------------------------------------------------------------------------------------------------


def test_the_plans_protocol_and_facts_agree_with_the_cell_and_each_other():
    gen = js(f"{SPEC['package']}/generation-plan-registered-v1.json")
    fit = js(f"{SPEC['package']}/fit-plan-registered-v1.json")
    protocol = js(f"{SPEC['package']}/protocol-registered-v1.json")
    facts = js(f"{SPEC['package']}/registered-facts-v1.json")
    for plan, run, attempt in ((gen, SPEC["run"], SPEC["attempt"]), (fit, SPEC["fit_run"], SPEC["fit_attempt"])):
        assert plan["cell"] == plan["experiment"] == SPEC["cell"] and plan["status"] == derive.STATUS
        ep = plan["execution_plan"]
        assert (ep["run_id"], ep["attempt_id"], ep["split_identity_hash"]) == (run, attempt, ROWS["split_identity_hash"])
        assert ep["split_role"] == "discovery" and plan["rows"] == N and plan["roster"]["rows"] == N
        assert plan["protocol_document"] == {"relpath": f"{SPEC['package']}/protocol-registered-v1.json", "sha256": hashlib.sha256((PKG / "protocol-registered-v1.json").read_bytes()).hexdigest()}
        assert plan["seal_only_registration"]["decision_id"] == SPEC["decision_id"]
    assert gen["resume_from"] == CELL["resume_from"] and "resume_from" not in fit
    proof = gen["resume_replay_proof"]
    assert (proof["rows_checked"], proof["rows_failing"], proof["sealed_twice"], proof["union_complete_rows"]) == (N, 0, 0, N) and proof["model_contacts"] == 0
    assert gen["resume_budget"]["flown_rows"] == 0 and gen["resume_budget"]["kept_rows"] == N and gen["resume_budget"]["seal_only"] is True
    assert gen["resume_budget"]["run_cumulative_actual_calls"] <= gen["resume_budget"]["cap_calls"] == gen["execution_plan"]["planned_model_calls"]
    cell = protocol["cells"]["seal-only"]
    assert (cell["attempt_id"], cell["fit_attempt_id"], cell["resume_from"]) == (SPEC["attempt"], SPEC["fit_attempt"], CELL["resume_from"])
    assert cell["composed_config_hash"] == gen["composed_config_hash"] and cell["protocol_hash"] == gen["execution_plan"]["protocol_hash"]
    assert protocol["abort"]["error"] == "RailsRunnerError: perception branch 'both-off' sealed no level-2 Solver column"
    assert (protocol["abort"]["complete_rows"], protocol["abort"]["failed_rows"], protocol["abort"]["never_started_rows"]) == (N, 1, 50)
    assert protocol["abort"]["contacts_of_the_failing_row"] == 8 and protocol["abort"]["calls"] == 10298
    measurement = facts["stage3_measurement"][SPEC["run"]]
    assert measurement["rows"] == N and measurement["claims_benefit"] is False and measurement["read_roster"] == ROWS["roster_id"]
    assert measurement["measurement_design"] == "same-flight-node-column" and facts["seal_only"]["resume_from"] == CELL["resume_from"]


def test_the_root_admission_draft_names_only_the_seal_only_run_and_attempt():
    draft = js(f"{SPEC['package']}/root-admission-sealonly-draft-v1.json")
    assert draft["status"] == "DRAFT-NOT-MINTED" and draft["recorded_at_utc"] is None and draft["decision_id"] == SPEC["decision_id"]
    assert draft["eligible_run_ids"] == [SPEC["run"], SPEC["fit_run"]] and draft["eligible_attempt_ids"] == [SPEC["attempt"]]
    assert draft["fit_attempt_ids"] == {SPEC["fit_run"]: SPEC["fit_attempt"]} and draft["resume_from"] == CELL["resume_from"]
    assert draft["population"]["count"] == N and draft["population"]["split_identity_hash"] == ROWS["split_identity_hash"]
    assert any("flying any row" in item for item in draft["not_authorized"])
    for key in ("sealonly_protocol", "sealonly_analysis_recipe", "sealonly_registered_facts", "sealonly_generation_plan", "sealonly_fit_plan", "sealonly_complete_rows"):
        record = draft["antecedents"][key]
        assert record["sha256"] == hashlib.sha256((REPO / record["path"]).read_bytes()).hexdigest()


def test_the_draft_ledger_rows_and_countersign_texts_are_complete():
    texts = js(f"{SPEC['package']}/countersign-row-texts-v1.json")
    assert texts["decision_id"] == SPEC["decision_id"] and set(texts["rows"]) == {SPEC["run"], SPEC["fit_run"], SPEC["proof_run"], SPEC["read_run"]}
    assert "<UTC timestamp>" in texts["rows"][SPEC["run"]] and "SEAL-ONLY COMPLETION REGISTERED" in texts["rows"][SPEC["run"]]
    assert "countersignature pending" not in texts["rows"][SPEC["run"]].split("SEAL-ONLY COMPLETION REGISTERED", 1)[1][:200]     # the flip's own DRAFT test
    assert ROWS["split_identity_hash"] in texts["rows"][SPEC["run"]] and SPEC["attempt"] in texts["rows"][SPEC["fit_run"]]
    draft = (PKG / "draft-ledger-rows.md").read_text(encoding="utf-8")
    assert "countersignature pending" in draft and SPEC["proof_run"] in draft and SPEC["read_run"] in draft
    proof_line = next(line for line in draft.splitlines() if line.startswith("|") and f"| {SPEC['proof_run']} |" in line)
    cells = [c.strip() for c in proof_line.strip().strip("|").split(" | ")]
    assert len(cells) == 15 and cells[2] == "model-free-check" and cells[8] == "no" and cells[9:12] == ["0", "0", "0.0"]
    # the shared exposure ledger itself is NOT touched by this registration
    ledger = (REPO / "docs" / "exposure-ledger.md").read_text(encoding="utf-8")
    assert SPEC["proof_run"] not in ledger and SPEC["attempt"] not in ledger


def test_the_readme_and_preregistration_state_the_corrected_counts_and_the_decisions():
    readme = (PKG / "README.md").read_text(encoding="utf-8")
    prereg = (REPO / SPEC["preregistration"]).read_text(encoding="utf-8")
    assert f"{N:,} rows are complete" in readme and "the 1,030th row is the FAILING one" in readme and "1,030 complete rows and 49 never flown" in readme
    assert "the delivering arm was NOT fine on that row" in readme
    for needle in ("Decisions this registration needs", "--allow-output-change", "Mode A, not mode B", "Not verified here", "Sequence"):
        assert needle in readme
    assert "PENDING" in readme and "PENDING" in prereg.upper() and f"n = {N:,}" in prereg
    for text in (readme, prereg):
        assert text.isascii(), "English-only, ASCII-clean documents"


def test_every_generated_document_is_english_ascii_text_with_lf_endings():
    files = [p for p in PKG.rglob("*") if p.is_file()] + [REPO / SPEC["preregistration"]] + [
        REPO / f"configs/experiment/{SPEC['experiment']}.json", REPO / f"configs/baseline/{SPEC['baseline']}.json", REPO / f"configs/dataset/{CELL['dataset_fragment']}.json"]
    for path in files:
        raw = path.read_bytes()
        assert b"\r" not in raw, path
        assert raw.decode("utf-8").isascii(), path


# ---- the scripts --------------------------------------------------------------------------------------------------------------------


def _text(rel: str) -> str:
    return (REPO / rel).read_text(encoding="utf-8")


def test_the_chain_refuses_while_batch_stop_exists_and_never_moves_it_aside():
    chain = _text("scripts/flights/nx/batch_chain_nxt_r1_sealonly.sh")
    lines = chain.splitlines()
    stop_check = next(i for i, ln in enumerate(lines) if ln.startswith('if [ -e "$STOP" ]'))
    checkout = next(i for i, ln in enumerate(lines) if "checkout -q --detach" in ln)
    assert stop_check < checkout and "exit 8" in lines[stop_check]
    move = next(ln for ln in lines if ln.startswith("for f in /home/chao/batch-status.jsonl"))
    assert "batch-STOP" not in move and "batch-done" in move
    assert chain.count('kind": "seal-only"') == 1 and '"smoke_cell": None' in chain and '"campaign_plan": None' in chain
    assert "resume_prelaunch_gate.sh" in chain and "batch_driver.sh" in chain and "nxt1seal-flight-commit.txt" in chain
    assert "git" in chain and "mv " in chain


def test_the_flip_is_loop_form_and_passes_allow_output_change_only_for_the_roster_narrowing():
    flip = _text("scripts/flights/nx/nxt_r1_sealonly_flip.sh")
    assert "for pass in 1 2 3 4" in flip and 'git status --short' in flip and "repin_loop_generic.sh" in flip and "repin_cell_generic.sh" in flip
    assert "export ALLOW_OUTPUT_CHANGE=1" in flip and "roll1_repin_arm.sh" in flip
    assert "export TAG=nxt1seal ARM=1" in flip and 'echo "$CONVERGED" > "$FLIGHT_FILE"' in flip
    for other in ("nxt_r1_flip.sh", "nxt_r2_flip.sh", "successor3_thinking_flip.sh"):
        assert "ALLOW_OUTPUT_CHANGE=1" not in _text(f"scripts/flights/nx/{other}")


def test_the_mint_script_checks_the_draft_the_cell_and_the_proof_and_refuses_a_bad_proof(tmp_path):
    draft, plan, resume_from = mint.check(str(REPO), str(tmp_path / "no-data-root"))
    assert draft["decision_id"] == SPEC["decision_id"] and resume_from == CELL["resume_from"] and plan["resume_replay_proof"]["rows_checked"] == N
    # a scratch tree with a failing proof is refused
    scratch = tmp_path / "tree"
    (scratch / SPEC["package"]).mkdir(parents=True)
    (scratch / "configs" / "experiment").mkdir(parents=True)
    shutil.copy(REPO / f"configs/experiment/{SPEC['experiment']}.json", scratch / "configs" / "experiment")
    for name in ("root-admission-sealonly-draft-v1.json", "generation-plan-registered-v1.json"):
        shutil.copy(PKG / name, scratch / SPEC["package"] / name)
    mint.check(str(scratch), str(tmp_path / "no-data-root"))
    bad = json.loads((scratch / SPEC["package"] / "generation-plan-registered-v1.json").read_text(encoding="utf-8"))
    bad["resume_replay_proof"]["rows_failing"] = 3
    (scratch / SPEC["package"] / "generation-plan-registered-v1.json").write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(SystemExit, match="resume_replay_proof"):
        mint.check(str(scratch), str(tmp_path / "no-data-root"))
    # a fresh data root whose stopped trace does not hash to the registered pin is refused
    data = tmp_path / "data"
    trace = data / "runs" / SPEC["run"] / SPEC["predecessor_attempt"] / f"{SPEC['run']}.trace.jsonl"
    trace.parent.mkdir(parents=True)
    trace.write_text("moved\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="no longer hashes"):
        mint.check(str(REPO), str(data))


def test_the_mint_script_writes_nothing_in_dry_mode(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(mint, "DATA", str(tmp_path / "data"))
    monkeypatch.setattr(sys, "argv", ["nxt_r1_sealonly_mint_receipt.py", "--dry"])
    assert mint.main() == 0
    out = capsys.readouterr().out
    assert '"status": "decided"' in out and SPEC["decision_id"] in out and "(dry) would write" in out
    assert not (tmp_path / "data").exists()


# ---- the seal-only read -------------------------------------------------------------------------------------------------------------


def test_the_reader_accounts_for_every_parent_row_by_count_and_checks_the_sealed_predecessor():
    registered = CELL["resume_from"]
    block = reader.sealonly_block(ROWS, registered)
    assert (block["rows"], block["parent_rows"], block["failed_rows"], block["never_started_rows"]) == (N, 1080, 1, 50)
    assert "ids" not in json.dumps(block) and ROWS["failed_rows"]["sample_ids"][0] not in json.dumps(block)        # counts only
    assert reader.sealonly_block(ROWS, registered, {"predecessor_attempt": {"trace_sha256": registered["trace_sha256"]}})["rows"] == N
    with pytest.raises(reader.ReadError, match="predecessor_attempt names trace"):
        reader.sealonly_block(ROWS, registered, {"predecessor_attempt": {"trace_sha256": "0" * 64}})
    with pytest.raises(reader.ReadError, match="predecessor_attempt names trace"):
        reader.sealonly_block(ROWS, registered, {})
    short = copy.deepcopy(ROWS)
    short["never_started_rows"]["count"] -= 1
    with pytest.raises(reader.ReadError, match="does not account for every parent row"):
        reader.sealonly_block(short, registered)
    text = reader.render_markdown({"sealonly": block})
    assert f"n = {N:,}" in text and "never scored" in text


def test_the_reader_refuses_a_sealonly_smoke_and_the_roster_loads_for_the_pairing(tmp_path, capsys):
    assert reader.main(["--stage", "smoke", "--sealonly", "--data-root", str(tmp_path), "--analysis-root", str(tmp_path / "a")]) == 2
    assert "smoke was sealed by the first attempt" in capsys.readouterr().err
    import slurp_direct_fold_b_core_read as base

    ids, cluster_of, scenario_of = base.roster_maps(REPO / SPEC["complete_rows"])
    assert len(ids) == N and cluster_of(ids[0]) and scenario_of(ids[0])


def test_the_read_script_has_the_two_seal_only_stages_that_use_the_complete_rows_roster():
    read = _text("scripts/flights/nx/nxt_r1_read.sh")
    assert "sealonly-columns|sealonly-read" in read and "--sealonly" in read and 'STAGE=${STAGE#sealonly-}' in read
    assert '--roster "$ROSTER"' in read and "complete_rows" in read and "read_require_countersigned" in read
    assert "docs/receipts/rosters/slurp-evo-fold-b-v2.json" in read                                       # the first-attempt roster is still the default
