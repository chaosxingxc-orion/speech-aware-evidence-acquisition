"""The 266-E registration (bare-core read, Thinking versus Instruct, direct-only, TRAIN Fold B): model-free tests.

Covers the lock-verified pins, the Thinking model fragment (a byte-for-byte Instruct sibling except the registered substitutions), the four composed
cells, the serving geometry row, the chain order (smoke before the arm), the draft ledger block, the draft receipt, the registration gate's allowed
findings, the effect-floor / finite-completion / harness-admission gates, and the reasoning-content guard. Nothing starts a process other than the
repository's own offline checks; no server, GPU or network is touched.
"""

from __future__ import annotations

import copy
import importlib.util
import inspect
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
DIRECT = REPO / "scripts" / "flights" / "direct"
sys.path.insert(0, str(DIRECT))

import direct_fb_family as fam  # noqa: E402
import direct_fb_mint_receipt as mint_mod  # noqa: E402
import direct_fb_pins as pins_mod  # noqa: E402

from speech_aware_evidence_acquisition.core.config import compose  # noqa: E402
from speech_aware_evidence_acquisition.core.model import transport as transport_mod  # noqa: E402

LEDGER = REPO / "docs" / "exposure-ledger.md"
MAIN_SHA = "afdaeff6f23c740429aadb3fa180f9d53b78278fe0d331b594b0b71bd9bf4835"
MMPROJ_SHA = "57b7240fb3d8941f5969d760c694a754cbe74f7db428605d63e1dacceda98b38"
ALLOWED_FINDINGS = {"not-ready", "row-not-countersigned", "receipt-missing"}


def _json(rel: str) -> dict:
    return json.loads((REPO / rel).read_text(encoding="utf-8"))


def _experiment(key: str) -> dict:
    return _json(f"configs/experiment/{fam.CELLS[key]['cell']}.json")


def _compose(key: str):
    spec = fam.CELLS[key]
    cell = _experiment(key)["cells"][0]
    return compose(REPO, cell["model_fragment"], cell["dataset_fragment"], cell["baseline_fragment"], spec["cell"])


def _fake_lock(tmp_path: Path, *, main_sha: str = MAIN_SHA, size: int = pins_mod.MAIN_BYTES, status: str = "COMPLETE") -> Path:
    revision = (f"x; {pins_mod.MAIN_NAME} {main_sha} ({size} bytes); {pins_mod.MMPROJ_NAME} {MMPROJ_SHA} ({pins_mod.MMPROJ_BYTES} bytes)")
    lock = tmp_path / "lock.json"
    lock.write_text(json.dumps({"models": [{"name": pins_mod.LOCK_KEY, "status": status, "revision": revision}]}), encoding="utf-8")
    return lock


def _receipts(tmp_path: Path, main_sha: str = MAIN_SHA) -> tuple[Path, Path]:
    main, mm = tmp_path / "main.sha256", tmp_path / "mmproj.sha256"
    main.write_text(f"{main_sha}  /x/{pins_mod.MAIN_NAME}\n18557053248\n", encoding="utf-8")
    mm.write_text(f"{MMPROJ_SHA}  /x/{pins_mod.MMPROJ_NAME}\n", encoding="utf-8")
    return main, mm


# ----------------------------------------------------------------------------------------------- pins and fragments


def test_pins_resolve_only_when_the_local_hash_equals_the_lock_and_refuse_otherwise(tmp_path):
    main, mm = _receipts(tmp_path)
    pins = pins_mod.resolve_pins(lock_path=_fake_lock(tmp_path), main_receipt=main, mmproj_receipt=mm)
    assert pins["main"]["sha256"] == MAIN_SHA and pins["mmproj"]["sha256"] == MMPROJ_SHA
    wrong_main, _ = _receipts(tmp_path, main_sha="1" * 64)
    with pytest.raises(SystemExit, match="does not match the lock"):
        pins_mod.resolve_pins(lock_path=_fake_lock(tmp_path), main_receipt=wrong_main, mmproj_receipt=mm)          # mismatched sha
    with pytest.raises(SystemExit, match="does not match the lock"):
        pins_mod.resolve_pins(lock_path=_fake_lock(tmp_path, size=1), main_receipt=main, mmproj_receipt=mm)         # mismatched size
    with pytest.raises(SystemExit, match="unreadable"):
        pins_mod.resolve_pins(lock_path=_fake_lock(tmp_path), main_receipt=tmp_path / "absent.sha256", mmproj_receipt=mm)  # unpinned
    with pytest.raises(SystemExit, match="not COMPLETE"):
        pins_mod.resolve_pins(lock_path=_fake_lock(tmp_path, status="PARTIAL"), main_receipt=main, mmproj_receipt=mm)


def test_committed_fragment_and_receipts_are_exactly_what_the_pins_produce():
    receipt = _json(pins_mod.SERVING_RECEIPT)
    pre = _json(pins_mod.PREPROCESS_RECEIPT)
    pins = {"main": receipt["gguf_files"][0], "mmproj": pre["gguf_files"][1]}
    assert pins["main"]["sha256"] == MAIN_SHA and pins["mmproj"]["sha256"] == MMPROJ_SHA
    assert pre["gguf_files"][0] == pins["main"]
    for relpath, body in pins_mod.build_fragments(pins, REPO).items():
        assert (REPO / relpath).read_text(encoding="utf-8") == body
    for relpath, document in pins_mod.build_receipts(pins, REPO).items():
        assert json.loads((REPO / relpath).read_text(encoding="utf-8")) == document


def test_the_model_fragment_refuses_an_unpinned_or_mismatched_sha():
    fragment = _json(f"configs/model/{pins_mod.SERVING_FRAGMENT}.json")
    receipt = _json(pins_mod.SERVING_RECEIPT)
    pins = {"main": receipt["gguf_files"][0]}
    assert pins_mod.verify_fragment_pins(fragment, receipt, pins) == []
    unpinned = {**receipt, "gguf_files": []}
    assert "unpinned" in " ".join(pins_mod.verify_fragment_pins(fragment, unpinned, pins))
    mismatched = copy.deepcopy(receipt)
    mismatched["gguf_files"][0]["sha256"] = "2" * 64
    assert pins_mod.verify_fragment_pins(fragment, mismatched, pins)
    bad_env = copy.deepcopy(fragment)
    bad_env["server_env"]["LLAMA_SPEECH_DECODER_SHA256"] = "3" * 64
    assert any("DECODER_SHA256" in f for f in pins_mod.verify_fragment_pins(bad_env, receipt, pins))


def test_the_thinking_fragment_differs_from_the_instruct_one_only_in_the_registered_lines():
    instruct = (REPO / "configs/model" / f"{fam.INSTRUCT_MODEL}.json").read_text(encoding="utf-8").splitlines()
    thinking = (REPO / "configs/model" / f"{fam.THINK_MODEL}.json").read_text(encoding="utf-8").splitlines()
    changed = [line for line in thinking if line not in instruct]
    keys = {re.match(r'\s*"([A-Za-z_]+)"', line).group(1) for line in changed if re.match(r'\s*"([A-Za-z_]+)"', line)}
    assert keys <= {"model_lock_key", "runtime_receipt", "--cache-ram", "max_tokens", "speech_feature_root", "LLAMA_SPEECH_FEATURE_ROOT",
                    "LLAMA_SPEECH_DECODER_SHA256", "reasoning_content_guard", "geometry_basis", "--reasoning-format"}, keys
    a, b = _json(f"configs/model/{fam.INSTRUCT_MODEL}.json"), _json(f"configs/model/{fam.THINK_MODEL}.json")
    assert b["server_args"][: len(a["server_args"])] == a["server_args"]                       # same geometry family flag for flag
    assert b["server_args"][len(a["server_args"]):] == ["--reasoning-format", "deepseek"]
    assert {"-c": "98304", "-np": "4", "-ctk": "q8_0", "-ctv": "q8_0"}.items() <= {k: b["server_args"][b["server_args"].index(k) + 1] for k in ("-c", "-np", "-ctk", "-ctv")}.items()
    assert b["decoding_params"]["max_tokens"] == fam.THINK_MAX_TOKENS == 8192 and a["decoding_params"]["max_tokens"] == 512
    assert {k: v for k, v in b["decoding_params"].items() if k != "max_tokens"} == {k: v for k, v in a["decoding_params"].items() if k != "max_tokens"}
    assert b["reasoning_content_guard"] == "refuse-think-marker-in-content"
    assert b["server_env"]["LLAMA_SPEECH_FEATURE_ROOT"] == b["speech_feature_root"] == fam.THINK_PACKET_ROOT != a["speech_feature_root"]


# ----------------------------------------------------------------------------------------------- cells


@pytest.mark.parametrize("key", fam.ALL_KEYS)
def test_every_cell_composes_is_held_and_declares_the_shared_form(key):
    spec, document = fam.CELLS[key], _experiment(key)
    composed = _compose(key)
    values = composed.values
    assert values["policy"] == "phase-direct-only-v1" and values["scorers"][0] == "slurp-slu-official-train"
    assert values["preserve_wire_responses"] is False                                    # reasoning_content is never persisted
    assert values["live_phase_fit"]["contact_cap"] == 1 + 3 * spec["rows"] == document["family_budget"]["fit_endpoint_calls_cap"]
    assert document["cells"][0]["readiness"]["state"] == "held"
    assert document["stage3_algorithm"]["id"] == "none"
    assert document["execution_plan"]["split_role"] == "discovery" and document["execution_profile"] == "bounded-discovery-probe"
    assert document["service_session"] == spec["session"]
    assert document["population"]["count"] == spec["rows"]
    assert document["generation_budget"]["cap"] == spec["rows"]
    assert "native_episode" not in values                                               # a direct-only cell has no native episode to arm
    if spec["core"] == "thinking":
        assert values["reasoning_content_guard"] == "refuse-think-marker-in-content"
        assert values["speech_packet_promotion_receipt"] == fam.THINK_PROMOTION_RECEIPT
        # The zero sentinel (the flip refuses it) until scripts/slurp_fold_preprocess_thinking.py --pin-receipt --write substitutes the
        # sha256 of the real promotion receipt; afterwards the field must be a real 64-hex digest.
        assert values["speech_packet_promotion_receipt_sha256"] == fam.UNPINNED_SHA or re.fullmatch(
            r"[0-9a-f]{64}", values["speech_packet_promotion_receipt_sha256"])
    else:
        assert "reasoning_content_guard" not in values
        assert values["speech_packet_promotion_receipt_sha256"] != fam.UNPINNED_SHA


def test_the_smoke_is_the_first_four_fold_b_rows_and_the_instruct_pair_is_request_identical():
    arm, smoke = fam.roster_doc("arm"), fam.roster_doc("smoke")
    assert [i["sample_id"] for i in smoke["items"]] == [i["sample_id"] for i in arm["items"][:4]]
    assert _experiment("smoke")["populations"][0]["ids"] == [i["sample_id"] for i in smoke["items"]]
    assert _experiment("thinking")["populations"][0]["ids"] == [i["sample_id"] for i in arm["items"]]
    i, r = _compose("instruct").values, _compose("replicate").values
    prose = {"live_phase_fit", "what_this_is", "cells", "purpose", "experiment_id", "generation_budget", "core_read_design"}
    assert [k for k in set(i) | set(r) if k not in prose and i.get(k) != r.get(k)] == []
    assert i["live_phase_fit"]["run_id"] != r["live_phase_fit"]["run_id"]


def test_measurement_blocks_declare_cross_flight_with_the_in_chain_replicate():
    facts = _json(f"{fam.PACKAGE}/registered-facts-v1.json")
    blocks = facts["stage3_measurement"]
    for key in fam.ARM_KEYS:
        block = blocks[fam.CELLS[key]["run"]]
        assert block["measurement_design"] == "cross-flight-with-in-chain-replicate" and block["claims_benefit"] is False
        assert block["replicate_run_id"] == fam.CELLS[fam.REPLICATE_OF[key]]["run"] and block["rows"] == 1080
        assert block["read_roster"] == "SLURP-EVO-FOLD-B-V2" and block["tuning_roster"] == "none"
    assert blocks[fam.CELLS["thinking"]["run"]]["expected_effect_pp"] == fam.CROSS_FLIGHT_BAR_PP
    assert blocks[fam.CELLS["smoke"]["run"]]["measurement_design"] == "form-proof"


# ----------------------------------------------------------------------------------------------- knowledge pin and rec1 recovery

FOLD_EXCLUDED_RELPATH = "knowledge/slurp/saea-kb-distmodel-v1/size-full-content-slot-fillers-intent-slot-frame-tfrl-folds-v1/snapshot.json"
FOLD_EXCLUDED_SHA = "9c64e8ec48a0fce4f172bd190932f99c98c7efa18bbfb14526d54c62fdf7032b"
FULL_TRAIN_SHA = "609854e4211891614b621e6431ccf23706c2aa3a3bc9133dae9d9765628c88b8"


@pytest.mark.parametrize("key", fam.ALL_KEYS)
def test_every_baseline_pins_the_fold_excluded_knowledge_view(key):
    """The runner's roster guard compares the pinned snapshot's source roster with the query roster even when evidence_source is none; the
    full-TRAIN view contains every Fold B id and aborted the Instruct arm before any model contact (2026-10-11T20:07:46Z)."""

    baseline = _json(f"configs/baseline/{fam.CELLS[key]['baseline']}.json")
    assert baseline["knowledge_snapshot_relpath"] == FOLD_EXCLUDED_RELPATH == fam.KNOWLEDGE_SNAPSHOT_RELPATH
    assert baseline["knowledge_snapshot_sha256"] == FOLD_EXCLUDED_SHA == fam.KNOWLEDGE_SNAPSHOT_SHA256
    assert baseline["knowledge_snapshot_sha256"] != FULL_TRAIN_SHA == fam.FULL_TRAIN_KNOWLEDGE_SNAPSHOT_SHA256
    assert "tfrl-folds" in baseline["knowledge_snapshot_relpath"]
    assert _compose(key).values["knowledge_snapshot_sha256"] == FOLD_EXCLUDED_SHA


@pytest.mark.parametrize("key", fam.ALL_KEYS)
def test_the_pinned_knowledge_snapshot_is_disjoint_from_the_cells_roster(key):
    import os  # noqa: PLC0415

    data_root = os.environ.get("SPEECHRL_DATA_DIR")
    snapshot_path = Path(data_root) / fam.KNOWLEDGE_SNAPSHOT_RELPATH if data_root else None
    if snapshot_path is None or not snapshot_path.is_file():
        pytest.skip("SPEECHRL_DATA_DIR (or the fold-excluded snapshot) is absent")
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    assert snapshot["snapshot_sha256"] == fam.KNOWLEDGE_SNAPSHOT_SHA256               # the pin is the snapshot's own content hash
    roster = _json(_experiment(key)["population"]["roster_receipt"])
    roster_ids = {item["sample_id"] for item in roster["items"]}
    assert len(roster_ids) == fam.CELLS[key]["rows"]
    assert not (set(snapshot["source_sample_ids"]) & roster_ids)                       # the runner's guard would pass
    assert snapshot["source_split_identity_hash"] != roster["split_identity_hash"]


def test_the_instruct_arm_resolves_to_the_rec1_identities_and_the_other_cells_keep_theirs():
    spec = fam.CELLS["instruct"]
    assert spec["run"] == "SAEA-SLURP-DIRECT-ONLY-FOLD-B-INSTRUCT-V1"                  # the generation run id stays: the budget is run-cumulative
    assert spec["attempt"] == "attempt-slurp-direct-only-fold-b-instruct-generation-rec1-v1"
    assert spec["fit_run"] == "SAEA-SLURP-DIRECT-ONLY-FOLD-B-INSTRUCT-FIT-REC1-V1"
    assert spec["fit_attempt"] == "attempt-slurp-direct-only-fold-b-instruct-fit-rec1-v1"
    for key in ("replicate",):                                                          # its attempt never opened (the Thinking arm has its own rec1, below)
        assert fam.recovery(key) is None and fam.rec_suffix(key) == ""
        assert "rec1" not in json.dumps(fam.CELLS[key]) and fam.plan_file_name(key, "generation") == f"{key}-generation-plan-registered-v1.json"
    rec = fam.recovery("instruct")
    assert rec["predecessor_attempt_id"] == "attempt-slurp-direct-only-fold-b-instruct-generation-v1" != spec["attempt"]
    assert rec["predecessor_fit_run_id"] == "SAEA-SLURP-DIRECT-ONLY-FOLD-B-INSTRUCT-FIT-V1" != spec["fit_run"]
    assert rec["predecessors"][0]["contacts_spent"] == 0 and rec["predecessors"][0]["speech_seconds_spent"] == 0.0
    assert "20:07:46Z" in rec["predecessor_state"] and "77b2283e9" in rec["predecessor_state"]
    assert fam.predecessor_spend("instruct") == (0, 0.0) and fam.predecessor_spend("thinking") == (0, 0.0)
    assert fam.cumulative_budget("instruct", 1080, 3155) == (1080, 3155)               # run-cumulative budget = original plan + 0
    assert fam.plan_file_name("instruct", "generation") == "instruct-generation-plan-registered-rec1-v1.json"
    assert fam.plan_file_name("instruct", "fit") == "instruct-fit-plan-registered-rec1-v1.json"
    assert fam.superseded_plan_file_names("instruct") == ["instruct-generation-plan-registered-v1.json", "instruct-fit-plan-registered-v1.json"]
    assert fam.superseded_plan_file_names("replicate") == []
    # eight first-registration ids (what the minted receipt lists) plus the rec1 FIT run id of each recovered cell (smoke, Thinking arm, Instruct arm)
    eligible = fam.eligible_run_ids()
    assert len(eligible) == 11 == len(set(eligible)) and eligible[-1] == spec["fit_run"]
    assert eligible[-2] == fam.CELLS["thinking"]["fit_run"] and eligible[-3] == fam.CELLS["smoke"]["fit_run"]
    assert fam.CELLS["instruct"]["run"] in eligible and rec["predecessor_fit_run_id"] in eligible


def test_the_rec1_plans_are_in_the_package_and_the_first_attempt_instruct_plans_are_gone():
    package = REPO / fam.PACKAGE
    for kind in ("generation", "fit"):
        assert (package / fam.plan_file_name("instruct", kind)).is_file()
        assert not (package / f"instruct-{kind}-plan-registered-v1.json").exists()
    spec = fam.CELLS["instruct"]
    generation = _json(f"{fam.PACKAGE}/{fam.plan_file_name('instruct', 'generation')}")
    fit = _json(f"{fam.PACKAGE}/{fam.plan_file_name('instruct', 'fit')}")
    assert (generation["execution_plan"]["run_id"], generation["execution_plan"]["attempt_id"]) == (spec["run"], spec["attempt"])
    assert (fit["execution_plan"]["run_id"], fit["execution_plan"]["attempt_id"]) == (spec["fit_run"], spec["fit_attempt"])
    assert generation["recovery"]["predecessor_attempt_id"] == fam.recovery("instruct")["predecessor_attempt_id"]
    budget = generation["recovery_budget"]
    assert budget["original_plan"] == budget["cumulative_plan"] == {"planned_model_calls": 1080, "planned_speech_audio_seconds": 3155}
    assert generation["execution_plan"]["planned_model_calls"] == 1080 and fit["execution_plan"]["planned_model_calls"] == 3241
    for key in ("replicate",):
        for kind in ("generation", "fit"):
            assert "recovery" not in _json(f"{fam.PACKAGE}/{fam.plan_file_name(key, kind)}")
    protocol = _json(f"{fam.PACKAGE}/protocol-registered-v1.json")
    assert protocol["recovery"]["instruct"]["root_cause"] == fam.recovery("instruct")["root_cause"]
    readme = (package / "README.md").read_text(encoding="utf-8")
    assert "## Recovery rec1" in readme and spec["attempt"] in readme and spec["fit_run"] in readme and FOLD_EXCLUDED_SHA in readme


def test_the_rec1_ledger_block_has_two_draft_rows_and_the_first_attempt_rows_are_unchanged():
    text = LEDGER.read_text(encoding="utf-8")
    start = text.index("## Cell 266-E recovery rec1")
    end = text.find("\n## ", start + 1)
    block = text[start:] if end == -1 else text[start:end]
    rows = [line for line in block.splitlines() if line.startswith("| 2026-")]
    assert len(rows) == 2 and all(r.count("|") == 16 for r in rows)
    spec = fam.CELLS["instruct"]
    assert [r.split("|")[2].strip() for r in rows] == [spec["run"], spec["fit_run"]]
    for r in rows:
        assert "countersignature pending" in r and "root countersigned" not in r.lower() and r.split("|")[9].strip() == "no"
        assert spec["attempt"] in r or spec["fit_attempt"] in r
    assert [r.split("|")[10].strip() for r in rows] == ["1080", "3241"]
    # the first-attempt rows stay in the original block (append-only), with their original ids
    original = [r for r in _ledger_rows() if r.split("|")[2].strip() in ("SAEA-SLURP-DIRECT-ONLY-FOLD-B-INSTRUCT-V1", "SAEA-SLURP-DIRECT-ONLY-FOLD-B-INSTRUCT-FIT-V1")]
    assert len(original) == 2
    texts = _json(f"{fam.PACKAGE}/countersign-row-texts-v1.json")["rows"]
    for run_id in (spec["run"], spec["fit_run"]):
        assert "root countersigned" in texts[run_id] and "RECOVERY rec1" in texts[run_id] and "countersignature pending" not in texts[run_id]


def test_the_flip_script_passes_the_rec1_plan_marker_for_the_recovered_cell_only():
    text = (DIRECT / "direct_fb_flip.sh").read_text(encoding="utf-8")
    assert 'PLAN_REC="${PLAN_REC_OF[$KIND]}"' in text and "fam.rec_suffix" in text
    assert fam.rec_suffix("instruct") == "-rec1" and fam.rec_suffix("smoke") == "-rec1" and fam.rec_suffix("replicate") == "" and fam.rec_suffix("thinking") == "-rec1"


# ----------------------------------------------------------------------------------------------- serving and chain


def test_the_think_np4_geometry_row_matches_the_registered_session_and_fragment():
    out = subprocess.run(["bash", "-c", f'source {REPO}/scripts/flights/batch/serving_lib.sh; saea_geometry think-np4 && echo "$G_SID $G_FRAGMENT $G_SERVING_ENTRY $G_MONITOR_ENTRY"'],
                         capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    sid, fragment, entry, monitor = out.stdout.split()
    assert (sid, fragment) == (fam.THINK_SESSION, fam.THINK_MODEL)
    assert (REPO / entry).is_file() and (REPO / monitor).is_file()
    assert fam.THINK_SESSION in (REPO / entry).read_text(encoding="utf-8") and pins_mod.SERVING_FRAGMENT == fragment


@pytest.mark.parametrize("script", sorted(p.name for p in DIRECT.glob("*.sh")))
def test_every_shell_script_parses(script):
    assert subprocess.run(["bash", "-n", str(DIRECT / script)], capture_output=True).returncode == 0


def _chain_text() -> str:
    return (DIRECT / "batch_chain_direct_fb.sh").read_text(encoding="utf-8")


def test_the_smoke_precedes_the_arm_in_the_chain_and_the_arm_waits_for_the_signoff_marker():
    text = _chain_text()
    body = text[text.index('case "$SEGMENT" in\n  smoke) run_driver'):]
    all_line = next(line for line in body.splitlines() if line.strip().startswith("think-all)"))
    assert all_line.index("run_driver smoke") < all_line.index("wait_signoff") < all_line.index("run_driver thinking")
    thinking_line = next(line for line in body.splitlines() if line.strip().startswith("thinking)"))
    assert thinking_line.index("wait_signoff") < thinking_line.index("run_driver thinking")
    assert fam.SIGNOFF_MARKER in text and 'SEGMENT=${1:-think-all}' in text
    assert fam.ALL_KEYS.index("smoke") < fam.ALL_KEYS.index("thinking")
    assert text.index(fam.THINK_SESSION) < text.index("INSTRUCT_SESSION=")


@pytest.mark.parametrize("segment,expected", [("smoke", ["smoke"]), ("thinking", ["thinking"]), ("instruct", ["instruct", "replicate"])])
def test_the_chain_queue_per_segment(tmp_path, segment, expected):
    text = _chain_text()
    snippet = text.split("<<'PY'\n", 1)[1].split("\nPY\n", 1)[0].replace("/home/chao/batch-queue.json", str(tmp_path / "queue.json"))
    env = {"DFB_SEGMENT": segment, "DFB_MAIN": str(REPO), "PATH": "/usr/bin:/bin"}
    result = subprocess.run([sys.executable, "-B", "-c", snippet], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    steps = json.loads((tmp_path / "queue.json").read_text(encoding="utf-8"))
    assert [s["short"] for s in steps] == [f"direct-fb-{k}" for k in expected]
    if segment == "thinking":                      # the Thinking arm flies under its rec1 ids (the FIT row it is gated on carries 4.5 gpu hours)
        assert [(s["run_id"], s["gen_attempt_id"], s["fit_run_id"]) for s in steps] == [
            ("SAEA-SLURP-DIRECT-ONLY-FOLD-B-THINKING-V1", "attempt-slurp-direct-only-fold-b-thinking-generation-rec1-v1", "SAEA-SLURP-DIRECT-ONLY-FOLD-B-THINKING-FIT-REC1-V1")]
    if segment == "instruct":                      # the Instruct arm flies under the rec1 ids, then the replicate under its own (unchanged) ids
        assert [(s["run_id"], s["gen_attempt_id"], s["fit_run_id"]) for s in steps] == [
            ("SAEA-SLURP-DIRECT-ONLY-FOLD-B-INSTRUCT-V1", "attempt-slurp-direct-only-fold-b-instruct-generation-rec1-v1", "SAEA-SLURP-DIRECT-ONLY-FOLD-B-INSTRUCT-FIT-REC1-V1"),
            ("SAEA-SLURP-DIRECT-ONLY-FOLD-B-INSTRUCT-REPLICATE-V1", "attempt-slurp-direct-only-fold-b-instruct-replicate-generation-v1", "SAEA-SLURP-DIRECT-ONLY-FOLD-B-INSTRUCT-REPLICATE-FIT-V1")]
    for step in steps:
        spec = next(v for v in fam.CELLS.values() if v["cell"] == step["cell"])
        assert step["run_id"] == spec["run"] and step["gen_attempt_id"] == spec["attempt"] and step["experiment"] == spec["cell"]
        if step["kind"] == "engineering":          # the driver's engineering rule: one identical four-row smoke, no campaign plan
            assert step["expected_rows"] == 4 and step["campaign_plan"] is None
            assert (step["smoke_experiment"], step["smoke_cell"], step["smoke_run_id"], step["smoke_attempt_id"]) == (step["experiment"], step["cell"], step["run_id"], step["gen_attempt_id"])
        else:
            assert step["kind"] == "cell" and step["smoke_experiment"] is None and (REPO / step["campaign_plan"]).is_file()
            assert step["expected_rows"] == 1080


def test_the_flip_script_refuses_the_zero_sentinel_and_can_be_narrowed_to_the_instruct_pair():
    text = (DIRECT / "direct_fb_flip.sh").read_text(encoding="utf-8")
    assert "exit 7" in text and "speech_packet_promotion_receipt_sha256" in text and "DIRECT_FB_KINDS" in text
    assert "--allow-output-change" in text and "never be passed" in text and "ALLOW_OUTPUT_CHANGE" not in text.replace("allow-output-change", "")
    assert (DIRECT / "direct_fb_flip.sh").read_text(encoding="utf-8").index("exit 6") < text.index("exit 7")


# ----------------------------------------------------------------------------------------------- ledger, receipt, gates


def _ledger_rows() -> list[str]:
    text = LEDGER.read_text(encoding="utf-8")
    start = text.index(fam.LEDGER_MARK)
    end = text.find("\n## ", start + 1)
    block = text[start:] if end == -1 else text[start:end]
    return [line for line in block.splitlines() if line.startswith("| 2026-10-11")]


def test_the_ledger_block_has_twelve_unconsumed_rows_and_the_recipe_read_row_exists():
    rows = _ledger_rows()
    assert len(rows) == 12 and all(r.count("|") == 16 for r in rows)
    ids = {r.split("|")[2].strip() for r in rows}
    # The CPU packets row (SUPERSEDED, stopped after 50 rows) is countersigned; every other row is still a draft.
    for r in rows:
        if r.split("|")[2].strip() == fam.CPU_PACKETS_ROW_ID:
            assert "root countersigned" in r.lower()
        else:
            assert "DRAFT, root countersignature pending" in r and "root countersigned" not in r.lower()
    ids = {r.split("|")[2].strip() for r in rows}
    for key in fam.ALL_KEYS:
        assert fam.CELLS[key]["run"] in ids and fam.CELLS[key]["fit_run"] in ids
    recipe = _json(f"{fam.PACKAGE}/analysis-recipe-v1.json")
    assert recipe["run_ids"]["read"] == fam.READ_RUN_ID in ids
    assert {fam.SERVING_ROW_ID, fam.CPU_PACKETS_ROW_ID} <= ids and fam.PACKETS_ROW_ID not in ids       # the GPU row has its own block
    for r in rows:
        assert r.split("|")[9].strip() == "no"


def _gpu_block_rows() -> list[str]:
    text = LEDGER.read_text(encoding="utf-8")
    start = text.index(fam.GPU_PACKETS_LEDGER_MARK)
    end = text.find("\n## ", start + 1)
    block = text[start:] if end == -1 else text[start:end]
    return [line for line in block.splitlines() if line.startswith("| 2026-10-11")]


def test_the_gpu_packets_row_is_one_unconsumed_draft_with_the_registered_ceilings_in_its_own_block():
    (row,) = _gpu_block_rows()
    cells = [c.strip() for c in row.split("|")[1:-1]]
    assert len(cells) == 15 and cells[1] == fam.PACKETS_ROW_ID == "SAEA-SLURP-DIRECT-ONLY-FOLD-B-THINKING-PACKETS-GPU-V1"
    assert cells[2] == "bounded-discovery-probe" and cells[6] == "discovery" and cells[8] == "no"
    assert cells[7] == fam.roster_doc("arm")["split_identity_hash"]
    assert (cells[9], cells[10], cells[11]) == ("1084", "3165", "1.0")               # 4-row smoke + the 1,080 total; 3,154.797375 + 9.94 s; 1 gpu-h cap
    notes = cells[14]
    assert "DRAFT, root countersignature pending" in notes and "root countersigned" not in notes.lower()
    assert fam.CPU_PACKETS_ROW_ID in row and fam.THINK_PACKET_ROOT in notes and pins_mod.THINKING_LEGACY_CACHE in notes
    assert "q4km-thinking-feature-preprocess-gpu-np1-v1" in cells[4] and "direct_fb_packets_gpu.sh" in notes
    # the superseded CPU row is left exactly where it was, in the 266-E block, and is not renamed
    assert any(r.split("|")[2].strip() == fam.CPU_PACKETS_ROW_ID for r in _ledger_rows())


def test_the_gpu_ids_roots_and_fragments_are_separate_from_the_superseded_cpu_ones():
    assert fam.PACKETS_ROW_ID != fam.CPU_PACKETS_ROW_ID and fam.PACKETS_ROW_ID.endswith("-GPU-V1")
    assert fam.THINK_PACKET_ROOT != fam.CPU_THINK_PACKET_ROOT and not fam.THINK_PACKET_ROOT.startswith(fam.CPU_THINK_PACKET_ROOT)
    assert pins_mod.THINKING_LEGACY_CACHE != pins_mod.CPU_THINKING_LEGACY_CACHE
    assert pins_mod.PREPROCESS_FRAGMENT != pins_mod.PREPROCESS_FRAGMENT_CPU and pins_mod.PREPROCESS_RECEIPT != pins_mod.PREPROCESS_RECEIPT_CPU
    assert fam.THINK_PROMOTION_RECEIPT.startswith(fam.THINK_PACKET_ROOT) and fam.CPU_THINK_PROMOTION_RECEIPT.startswith(fam.CPU_THINK_PACKET_ROOT)
    assert (REPO / f"configs/model/{pins_mod.PREPROCESS_FRAGMENT_CPU}.json").is_file()                     # the old fragment stays in the record
    for relpath in ("configs/baseline/slurp-direct-only-fold-b-thinking-baseline-v1.json",
                    "configs/baseline/slurp-direct-only-fold-b-thinking-smoke-4-baseline-v1.json"):
        text = (REPO / relpath).read_text(encoding="utf-8")
        assert fam.THINK_PROMOTION_RECEIPT in text and fam.CPU_THINK_PACKET_ROOT not in text
        assert f'"speech_packet_promotion_receipt_sha256": "{fam.UNPINNED_SHA}"' in text            # left as the zero sentinel for the pin step


def test_the_gpu_fragment_mirrors_the_e21_gpu_geometry_with_the_instruct_fold_b_context():
    gpu = _json(f"configs/model/{pins_mod.PREPROCESS_FRAGMENT}.json")
    e21 = _json(f"configs/model/{pins_mod.E21_GPU_PREPROCESS_FRAGMENT}.json")
    strip = lambda args: [a for i, a in enumerate(args) if not (a == "-c" or (i and args[i - 1] == "-c"))]    # noqa: E731
    assert strip(gpu["server_args"]) == strip(e21["server_args"]) == ["-np", "1", "-ngl", "999", "-fa", "on", "-ctk", "q8_0", "-ctv", "q8_0", "-b", "512", "-ub", "128"]
    assert gpu["server_args"][:2] == ["-c", "16384"] and "--no-mmproj-offload" not in gpu["server_args"]       # the Instruct Fold B pass used -c 16384
    assert gpu["model_lock_key"] == pins_mod.LOCK_KEY and gpu["runtime_receipt"] == pins_mod.PREPROCESS_RECEIPT.removeprefix("docs/")
    assert gpu["server_env"] == {"LLAMA_MTMD_FEAT_CACHE_DIR": pins_mod.THINKING_LEGACY_CACHE, "GGML_CUDA_DISABLE_GRAPHS": "1"}
    assert gpu["decoding_params"]["max_tokens"] == 1 and gpu["serving_geometry"]["slots"] == 1
    receipt, cpu_receipt = _json(pins_mod.PREPROCESS_RECEIPT), _json(pins_mod.PREPROCESS_RECEIPT_CPU)
    assert receipt == cpu_receipt                                                                            # the same pinned build and GGUF pins
    assert receipt["gguf_files"][0]["sha256"] == MAIN_SHA and receipt["gguf_files"][1]["sha256"] == MMPROJ_SHA
    experiment = _json("configs/experiment/slurp-direct-fold-b-thinking-preprocess-gpu-v1.json")
    assert experiment["experiment_id"] == fam.PACKETS_ROW_ID and experiment["feature_root"] == fam.THINK_PACKET_ROOT
    assert experiment["promotion_receipt"] == fam.THINK_PROMOTION_RECEIPT and experiment["legacy_cache_dir"] == pins_mod.THINKING_LEGACY_CACHE


def test_the_package_documents_point_at_the_gpu_pass():
    facts = _json(f"{fam.PACKAGE}/registered-facts-v1.json")
    assert facts["pins"]["preprocess_fragment"] == pins_mod.PREPROCESS_FRAGMENT
    assert facts["pins"]["preprocess_fragment_cpu_superseded"] == pins_mod.PREPROCESS_FRAGMENT_CPU
    assert facts["serving"]["thinking_packet_root"] == fam.THINK_PACKET_ROOT
    readme = (REPO / fam.PACKAGE / "README.md").read_text(encoding="utf-8")
    assert fam.PACKETS_ROW_ID in readme and "direct_fb_packets_gpu.sh --check" in readme and fam.THINK_PACKET_ROOT in readme
    assert "SUPERSEDED" in readme and "--stop-only" in readme and "NO GPU record" in readme
    texts = _json(f"{fam.PACKAGE}/countersign-row-texts-v1.json")
    assert fam.PACKETS_ROW_ID in texts["rows_that_stay_draft"]


def test_the_countersign_texts_name_the_packages_own_receipt():
    texts = _json(f"{fam.PACKAGE}/countersign-row-texts-v1.json")
    assert texts["decision_receipt"] == fam.DECISION_RELPATH and len(texts["rows"]) == 8
    assert all(fam.DECISION_RELPATH in t and "root countersigned" in t for t in texts["rows"].values())
    assert set(texts["rows"]) == {fam.CELLS[k][f] for k in fam.ALL_KEYS for f in ("run", "fit_run")}


def test_the_draft_receipt_lists_the_eight_run_ids_plus_the_rec1_fit_runs_and_mints_once(tmp_path):
    draft = _json(f"{fam.PACKAGE}/root-admission-draft-v1.json")
    assert draft["eligible_run_ids"] == mint_mod.expected_eligible() and len(draft["eligible_run_ids"]) == 11
    for key in ("smoke", "thinking", "instruct"):
        assert fam.CELLS[key]["fit_run"] in draft["eligible_run_ids"]
    assert draft["superseded_attempt_ids"] == [
        fam.recovery(key)[name] for key in ("smoke", "thinking", "instruct") for name in ("predecessor_attempt_id", "predecessor_fit_attempt_id")]
    assert draft["service"]["thinking_session"] == fam.THINK_SESSION
    assert draft["budget"]["thinking"]["gpu_hours_fit_inclusive"] == 4.5 and draft["budget"]["smoke"]["generation_calls_cap"] == 8
    assert draft["status"] == "DRAFT-NOT-MINTED"
    summary = mint_mod.mint(str(REPO), str(tmp_path))
    receipt = json.loads((tmp_path / fam.DECISION_RELPATH).read_text(encoding="utf-8"))
    assert receipt["status"] == "decided" and receipt["decision_id"] == fam.DECISION_ID and summary["rehashed_paths"] >= 5
    with pytest.raises(SystemExit, match="refusing to overwrite"):
        mint_mod.mint(str(REPO), str(tmp_path))


def _run_check(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-B", *args], cwd=REPO, capture_output=True, text=True, env={"PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": str(REPO / "src")})


@pytest.mark.parametrize("key", fam.ALL_KEYS)
def test_the_registration_gate_returns_only_the_three_expected_findings(tmp_path, key):
    cell = fam.CELLS[key]["cell"]
    out = _run_check("scripts/checks/flight_registration_check.py", "--repo-root", str(REPO), "--data-root", str(tmp_path), "--cell", f"{cell}:{cell}")
    found = set(re.findall(r"^\s+\[([a-z\-]+)\]", out.stdout, flags=re.MULTILINE))
    assert found and found <= ALLOWED_FINDINGS, (found, out.stdout[-1500:])
    assert {"not-ready", "row-not-countersigned", "receipt-missing"} <= found


def test_the_effect_floor_finite_completion_and_harness_gates_pass_and_cover_the_cells():
    floor = _run_check("scripts/checks/stage3_effect_floor_check.py")
    assert "PASS" in floor.stdout.splitlines()[-1] and floor.returncode == 0, floor.stdout[-800:]
    for key in fam.ARM_KEYS:
        explained = _run_check("scripts/checks/stage3_effect_floor_check.py", "--explain", fam.CELLS[key]["cell"]).stdout
        assert "in scope because" in explained and "cross-flight-with-in-chain-replicate" in explained, explained[:600]
        if key == "thinking":                       # the only arm that registers an expected effect: it must clear the 2.5 pp bar
            assert "clears the floor" in explained, explained[:900]
    label = _run_check("scripts/checks/stage3_algorithm_label_check.py")
    assert "PASS" in label.stdout.splitlines()[-1]
    for gate in ("finite_completion_policy_check", "harness_admission_check", "engineering_base_check"):
        out = _run_check(f"scripts/checks/{gate}.py")
        assert out.returncode == 0 and "PASS" in out.stdout, (gate, out.stdout[-600:])


# ----------------------------------------------------------------------------------------------- reasoning guard


def test_the_reasoning_guard_refuses_a_think_marker_and_is_wired_through_the_factory():
    guard = transport_mod.reasoning_marker_in_content
    assert guard("<think>x</think>y") == "<think>" and guard("a</THINK>") == "</think>" and guard("final answer") is None and guard(None) is None
    assert "reasoning_content_guard" in inspect.signature(transport_mod.LlamaServerTransport.__init__).parameters
    source = inspect.getsource(transport_mod._llama_server_factory)
    assert 'values.get("reasoning_content_guard")' in source
    assert transport_mod.REASONING_CONTENT_GUARD_THINK_MARKER == _json(f"configs/model/{fam.THINK_MODEL}.json")["reasoning_content_guard"]


# ----------------------------------------------------------------------------------------------- cap amendment 2,048 -> 8,192 and the smoke rec1


def test_the_completion_cap_is_8192_in_both_thinking_baselines_and_the_flown_fragment_is_kept():
    """Owner decision 266-E, decode-cost sign-off: the smoke row that spent its whole 2,048 budget on reasoning delivered empty content."""

    assert fam.THINK_MAX_TOKENS == 8192 and fam.SUPERSEDED_THINK_MAX_TOKENS == 2048 and pins_mod.THINKING_MAX_TOKENS == 8192
    assert fam.THINK_MODEL.endswith("max8192-v1") and fam.SUPERSEDED_THINK_MODEL.endswith("max2048-v1") and fam.THINK_MODEL != fam.SUPERSEDED_THINK_MODEL
    assert fam.THINK_SESSION.endswith("max8192-v1") and fam.THINK_SESSION != fam.SUPERSEDED_THINK_SESSION
    for key in ("smoke", "thinking"):
        cell = _experiment(key)["cells"][0]
        assert cell["model_fragment"] == fam.THINK_MODEL == pins_mod.SERVING_FRAGMENT
        assert _compose(key).values["decoding_params"]["max_tokens"] == 8192
        assert _experiment(key)["service_session"] == fam.THINK_SESSION
    # the slot still holds the prompt and the completion: 2.3k + 8,192 is 42.7 percent of a 24,576-token slot
    assert (2300 + fam.THINK_MAX_TOKENS) / 24576 < 0.43
    # the flown max2048 fragment is a frozen record, never rewritten in place
    flown = _json(f"configs/model/{fam.SUPERSEDED_THINK_MODEL}.json")
    assert flown["decoding_params"]["max_tokens"] == 2048 and flown["reasoning_content_guard"] == "refuse-think-marker-in-content"
    assert f"configs/model/{fam.SUPERSEDED_THINK_MODEL}.json" not in pins_mod.build_fragments({"main": {"sha256": MAIN_SHA}}, REPO)


def test_the_instruct_cells_are_untouched_by_the_cap_amendment():
    """I7: the Instruct pair is flying; its model fragment, cap and request-relevant composed keys do not move."""

    for key in ("instruct", "replicate"):
        values = _compose(key).values
        assert values["decoding_params"]["max_tokens"] == 512
        assert _experiment(key)["cells"][0]["model_fragment"] == fam.INSTRUCT_MODEL
        assert _experiment(key)["service_session"] == fam.INSTRUCT_SESSION
        assert "reasoning_content_guard" not in values
    assert "rec1" in fam.CELLS["instruct"]["attempt"]                                   # the Instruct arm keeps its own rec1 identities


def test_the_thinking_arm_takes_the_amended_gpu_hour_ceiling_under_its_rec1_ids():
    thinking = fam.CELLS["thinking"]
    assert fam.recovery("thinking") is not None and "rec1" in json.dumps(thinking)
    assert thinking["gpu_hours"] == fam.THINK_ARM_GPU_HOURS == 4.5
    assert _experiment("thinking")["execution_plan"]["planned_gpu_hours"] == 4.5
    assert _experiment("thinking")["family_budget"]["gpu_hours_fit_inclusive"] == 4.5
    for kind in ("generation", "fit"):
        plan = _json(f"{fam.PACKAGE}/{fam.plan_file_name('thinking', kind)}")
        assert plan["execution_plan"]["planned_gpu_hours"] == 4.5 and plan["expected_session_id"] == fam.THINK_SESSION
    assert fam.CELLS["smoke"]["gpu_hours"] == 0.5 and fam.CELLS["instruct"]["gpu_hours"] == 0.5


def test_the_smoke_resolves_to_the_rec1_identities_and_the_run_cumulative_budget():
    spec, rec = fam.CELLS["smoke"], fam.recovery("smoke")
    assert spec["run"] == "SAEA-SLURP-DIRECT-ONLY-FOLD-B-THINKING-SMOKE-4-V1"            # the generation run id stays: the budget is run-cumulative
    assert spec["attempt"] == "attempt-slurp-direct-only-fold-b-thinking-smoke-4-generation-rec1-v1"
    assert spec["fit_run"] == "SAEA-SLURP-DIRECT-ONLY-FOLD-B-THINKING-SMOKE-4-FIT-REC1-V1"
    assert spec["fit_attempt"] == "attempt-slurp-direct-only-fold-b-thinking-smoke-4-fit-rec1-v1"
    assert rec["predecessor_attempt_id"] == "attempt-slurp-direct-only-fold-b-thinking-smoke-4-generation-v1" != spec["attempt"]
    assert rec["predecessor_fit_run_id"] == "SAEA-SLURP-DIRECT-ONLY-FOLD-B-THINKING-SMOKE-4-FIT-V1" != spec["fit_run"]
    assert rec["predecessors"] == [{"attempt_id": rec["predecessor_attempt_id"], "state": rec["predecessors"][0]["state"],
                                    "contacts_spent": 4, "speech_seconds_spent": 9.9395}]
    assert fam.predecessor_spend("smoke") == (4, 9.9395)
    assert fam.cumulative_budget("smoke", 4, 10) == (8, 20)                             # original plan + the failed attempt's recorded spend
    assert fam.plan_file_name("smoke", "generation") == "smoke-generation-plan-registered-rec1-v1.json"
    assert fam.superseded_plan_file_names("smoke") == ["smoke-generation-plan-registered-v1.json", "smoke-fit-plan-registered-v1.json"]
    baseline = _json(f"configs/baseline/{spec['baseline']}.json")
    assert baseline["live_phase_fit"] == {"attempt_id": spec["fit_attempt"], "contact_cap": 13, "run_id": spec["fit_run"]}
    package = REPO / fam.PACKAGE
    for kind in ("generation", "fit"):
        assert (package / fam.plan_file_name("smoke", kind)).is_file()
        assert not (package / f"smoke-{kind}-plan-registered-v1.json").exists()
    generation = _json(f"{fam.PACKAGE}/{fam.plan_file_name('smoke', 'generation')}")
    fit = _json(f"{fam.PACKAGE}/{fam.plan_file_name('smoke', 'fit')}")
    assert (generation["execution_plan"]["run_id"], generation["execution_plan"]["attempt_id"]) == (spec["run"], spec["attempt"])
    assert (fit["execution_plan"]["run_id"], fit["execution_plan"]["attempt_id"]) == (spec["fit_run"], spec["fit_attempt"])
    assert generation["execution_plan"]["planned_model_calls"] == 8 and generation["execution_plan"]["planned_speech_audio_seconds"] == 20
    assert fit["execution_plan"]["planned_model_calls"] == 13
    assert generation["recovery_budget"]["original_plan"] == {"planned_model_calls": 4, "planned_speech_audio_seconds": 10}
    assert generation["recovery_budget"]["failed_attempt_spend"]["model_calls"] == 4
    assert generation["recovery_budget"]["cumulative_plan"] == {"planned_model_calls": 8, "planned_speech_audio_seconds": 20}
    assert generation["expected_session_id"] == fam.THINK_SESSION == fit["expected_session_id"]
    # only the persisted recovery keys reach a plan; the Instruct recovery keeps its knowledge pin, the smoke's does not carry one
    assert "knowledge_snapshot" not in generation["recovery"] and "fix" not in generation["recovery"]
    assert "knowledge_snapshot" in _json(f"{fam.PACKAGE}/{fam.plan_file_name('instruct', 'generation')}")["recovery"]


def test_the_smoke_rec1_ledger_block_has_two_draft_rows_and_the_first_attempt_rows_stay():
    text = LEDGER.read_text(encoding="utf-8")
    start = text.index("## Cell 266-E recovery rec1: the Thinking smoke re-registration")
    end = text.find("\n## ", start + 1)
    block = text[start:] if end == -1 else text[start:end]
    rows = [line for line in block.splitlines() if line.startswith("| 2026-")]
    spec = fam.CELLS["smoke"]
    assert len(rows) == 2 and all(r.count("|") == 16 for r in rows)
    assert [r.split("|")[2].strip() for r in rows] == [spec["run"], spec["fit_run"]]
    for r in rows:
        assert "countersignature pending" in r and "root countersigned" not in r.lower() and r.split("|")[9].strip() == "no"
        assert "max8192" in r and "max2048" not in r and fam.THINK_MODEL in r
        assert spec["attempt"] in r or spec["fit_attempt"] in r
    assert [r.split("|")[10].strip() for r in rows] == ["8", "13"]                      # run-cumulative 4 + 4; the structural FIT cap
    assert [r.split("|")[11].strip() for r in rows] == ["20", "20"]
    assert [r.split("|")[12].strip() for r in rows] == ["0.5", "0.5"]
    assert "9.9395" in rows[0] and "4 + 4 = 8 calls" in rows[0]
    original = [r for r in _ledger_rows() if r.split("|")[2].strip() in ("SAEA-SLURP-DIRECT-ONLY-FOLD-B-THINKING-SMOKE-4-V1", "SAEA-SLURP-DIRECT-ONLY-FOLD-B-THINKING-SMOKE-4-FIT-V1")]
    assert len(original) == 2 and all("root countersigned" in r.lower() for r in original)   # append-only: the flown first rows are untouched


def test_the_serving_draft_row_names_the_amended_fragment_and_session_and_stays_a_draft():
    (row,) = [r for r in _ledger_rows() if r.split("|")[2].strip() == fam.SERVING_ROW_ID]
    assert "max8192" in row and "max2048" not in row and fam.THINK_MODEL in row and fam.THINK_SESSION in row
    assert fam.SUPERSEDED_THINK_SESSION + " " not in row and "DRAFT, root countersignature pending" in row and "root countersigned" not in row.lower()


def test_the_countersign_texts_carry_the_smoke_rec1_wording():
    texts = _json(f"{fam.PACKAGE}/countersign-row-texts-v1.json")["rows"]
    spec = fam.CELLS["smoke"]
    assert "SAEA-SLURP-DIRECT-ONLY-FOLD-B-THINKING-SMOKE-4-FIT-V1" not in texts and spec["fit_run"] in texts and spec["run"] in texts
    for run_id in (spec["run"], spec["fit_run"]):
        text = texts[run_id]
        assert "RECOVERY rec1" in text and "root countersigned" in text and "countersignature pending" not in text
        assert spec["attempt"] in text and spec["fit_run"] in text and "4 calls and 9.9395 speech-seconds spent" in text
        assert "eligible_run_ids" in text and "8,192" in text


def test_the_readme_finding_three_carries_the_measured_smoke_numbers_and_the_amended_cap():
    readme = (REPO / fam.PACKAGE / "README.md").read_text(encoding="utf-8")
    finding = readme[readme.index("**Finding 3"):readme.index("**Chain.**")]
    for needle in ("8192 tokens", "amended from 2048", "363, 921 and 977", "99, 111 and 60", "length 0", "37 tokens per second per slot", "58 with one slot busy",
                   "0.9 to 1.7 ms per token", "9.9395", "1 of 4", "saea-empty-completion-v1", "3.0 -> 4.5", "42.7 percent"):
        assert needle in finding, needle
    assert "## Recovery rec1: the four-row Thinking decode-cost smoke" in readme and "serving_stop_think_superseded.sh" in readme


def test_the_serving_entry_scripts_name_the_amended_fragment_and_session():
    entry = (DIRECT / "serving_task_entry_think.sh").read_text(encoding="utf-8")
    assert f"FRAGMENT={fam.THINK_MODEL}" in entry and f"SESSION={fam.THINK_SESSION}" in entry and fam.SUPERSEDED_THINK_MODEL not in entry
    assert fam.THINK_SESSION in (DIRECT / "serving_monitor_start_think.sh").read_text(encoding="utf-8")
    assert f"THINK_SESSION={fam.THINK_SESSION}" in _chain_text()
    assert fam.SUPERSEDED_THINK_SESSION + "\n" not in _chain_text()


def test_the_flip_can_be_narrowed_to_the_smoke_and_the_thinking_arm_and_passes_the_rec1_marker_for_the_smoke():
    text = (DIRECT / "direct_fb_flip.sh").read_text(encoding="utf-8")
    assert 'KINDS=${DIRECT_FB_KINDS:-"smoke thinking instruct replicate"}' in text
    assert "for KIND in $KINDS; do" in text                                              # every re-pin pass iterates ONLY the narrowed kinds
    assert 'case " $KINDS " in *" thinking "*|*" smoke "*) ;; *) break ;; esac' in text   # the sentinel check applies to the Thinking cells only
    code = ("import sys; sys.path.insert(0, %r); import direct_fb_family as fam; "
            "print(' '.join(f'{k}={fam.rec_suffix(k)}' for k in ('smoke', 'thinking')))" % str(DIRECT))
    out = subprocess.run([sys.executable, "-B", "-c", code], capture_output=True, text=True)
    assert out.stdout.split() == ["smoke=-rec1", "thinking=-rec1"], out.stderr
    # a narrowed pass never names an Instruct cell: the cell table is a lookup, not a loop
    assert "declare -A CELL=" in text and "for KIND in smoke thinking instruct replicate; do\n  PLAN_REC_OF" in text


def test_the_superseded_session_stop_helper_refuses_unsafe_states_and_stops_only_the_retired_session(tmp_path):
    from test_serving_swap import Host  # noqa: PLC0415

    host = Host(tmp_path)
    script = str(DIRECT / "serving_stop_think_superseded.sh")
    retired = fam.SUPERSEDED_THINK_SESSION
    sdir = host.data / "serving" / retired
    sdir.mkdir(parents=True, exist_ok=True)

    def run(*args):
        return host.run(["bash", script, *args])

    assert run("--dry-run").returncode == 0 and "no session is recorded resident" in run().stdout          # nothing resident: a no-op
    # a generation flight alive refuses (7)
    host.procs("9000401 python -B -m speech_aware_evidence_acquisition.core.flight.cli campaign --repo-root /r")
    assert run().returncode == 7
    host.procs()
    # a DIFFERENT session recorded resident is never touched (10)
    (host.state / "resident").write_text("serving-slurp-native-candidate-five-train-a-np4-v1", encoding="utf-8")
    refused = run()
    assert refused.returncode == 10 and "not the retired Thinking session" in refused.stdout
    assert not any(line.startswith("stop ") for line in host.log("ss.log"))
    # the retired session resident: the dry run stops nothing; the real run stops exactly it and the two THINK tasks, and starts nothing
    (host.state / "resident").write_text(retired, encoding="utf-8")
    (sdir / "session.json").write_text("{}", encoding="utf-8")
    dry = run("--dry-run")
    assert dry.returncode == 0 and "DRY RUN" in dry.stdout and not any(line.startswith("stop ") for line in host.log("ss.log"))
    real = run()
    assert real.returncode == 0, real.stdout + real.stderr
    assert f"stop {retired}" in host.log("ss.log")
    ps = host.log("ps.log")
    assert any(line.startswith("-Stop SAEA-Serving-THINK") for line in ps) and any(line.startswith("-Stop SAEA-Monitor-THINK") for line in ps)
    assert not any(line.startswith("-Start") for line in ps)
    assert (sdir / "session-stop.json").is_file()


# ----------------------------------------------------------------------------------------------- Thinking arm rec1 and the GPU pre-registration gate


def _registration_check_module():
    spec = importlib.util.spec_from_file_location("flight_registration_check_under_test", REPO / "scripts" / "checks" / "flight_registration_check.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_the_thinking_arm_resolves_to_the_rec1_identities_and_the_run_cumulative_budget():
    spec, rec = fam.CELLS["thinking"], fam.recovery("thinking")
    assert spec["run"] == "SAEA-SLURP-DIRECT-ONLY-FOLD-B-THINKING-V1"                    # the generation run id stays: the budget is run-cumulative
    assert spec["attempt"] == "attempt-slurp-direct-only-fold-b-thinking-generation-rec1-v1"
    assert spec["fit_run"] == "SAEA-SLURP-DIRECT-ONLY-FOLD-B-THINKING-FIT-REC1-V1"
    assert spec["fit_attempt"] == "attempt-slurp-direct-only-fold-b-thinking-fit-rec1-v1"
    assert rec["predecessor_attempt_id"] == "attempt-slurp-direct-only-fold-b-thinking-generation-v1" != spec["attempt"]
    assert rec["predecessor_fit_run_id"] == "SAEA-SLURP-DIRECT-ONLY-FOLD-B-THINKING-FIT-V1" != spec["fit_run"]
    assert "00:25:21Z" in rec["predecessor_state"] and "5daf057f8" in rec["predecessor_state"] and "before any model contact" in rec["predecessor_state"]
    assert fam.predecessor_spend("thinking") == (0, 0.0) and fam.cumulative_budget("thinking", 1080, 3155) == (1080, 3155)
    assert fam.plan_file_name("thinking", "generation") == "thinking-generation-plan-registered-rec1-v1.json"
    assert fam.superseded_plan_file_names("thinking") == ["thinking-generation-plan-registered-v1.json", "thinking-fit-plan-registered-v1.json"]
    baseline = _json(f"configs/baseline/{spec['baseline']}.json")
    assert baseline["live_phase_fit"] == {"attempt_id": spec["fit_attempt"], "contact_cap": 3241, "run_id": spec["fit_run"]}
    assert _experiment("thinking")["cells"][0]["attempt_id"] == spec["attempt"]
    package = REPO / fam.PACKAGE
    for kind in ("generation", "fit"):
        assert (package / fam.plan_file_name("thinking", kind)).is_file()
        assert not (package / f"thinking-{kind}-plan-registered-v1.json").exists()
    generation = _json(f"{fam.PACKAGE}/{fam.plan_file_name('thinking', 'generation')}")
    fit = _json(f"{fam.PACKAGE}/{fam.plan_file_name('thinking', 'fit')}")
    assert (generation["execution_plan"]["run_id"], generation["execution_plan"]["attempt_id"]) == (spec["run"], spec["attempt"])
    assert (fit["execution_plan"]["run_id"], fit["execution_plan"]["attempt_id"]) == (spec["fit_run"], spec["fit_attempt"])
    assert generation["recovery_budget"]["original_plan"] == generation["recovery_budget"]["cumulative_plan"] == {"planned_model_calls": 1080, "planned_speech_audio_seconds": 3155}
    assert generation["execution_plan"]["planned_gpu_hours"] == fit["execution_plan"]["planned_gpu_hours"] == 4.5
    assert generation["expected_session_id"] == fam.THINK_SESSION == fit["expected_session_id"]


def test_the_thinking_rec1_ledger_block_carries_4_5_gpu_hours_on_both_rows_and_the_first_attempt_rows_stay():
    text = LEDGER.read_text(encoding="utf-8")
    start = text.index("## Cell 266-E recovery rec1: the Thinking arm")
    end = text.find("\n## ", start + 1)
    block = text[start:] if end == -1 else text[start:end]
    rows = [line for line in block.splitlines() if line.startswith("| 2026-")]
    spec = fam.CELLS["thinking"]
    assert len(rows) == 2 and all(r.count("|") == 16 for r in rows)
    assert [r.split("|")[2].strip() for r in rows] == [spec["run"], spec["fit_run"]]
    for r in rows:
        cells = [c.strip() for c in r.split("|")]
        assert "countersignature pending" in r and "root countersigned" not in r.lower() and cells[9] == "no"
        assert cells[12] == "4.5"                                                       # the gpu cell, on the generation AND the FIT row
        assert f"max{fam.THINK_MAX_TOKENS}" in cells[5] and fam.THINK_MODEL in cells[5]
    assert fam.THINK_SESSION in rows[0]                                                 # the generation row names the expected max8192 session
    assert [r.split("|")[10].strip() for r in rows] == ["1080", "3241"]
    original = [r for r in _ledger_rows() if r.split("|")[2].strip() in ("SAEA-SLURP-DIRECT-ONLY-FOLD-B-THINKING-V1", "SAEA-SLURP-DIRECT-ONLY-FOLD-B-THINKING-FIT-V1")]
    assert len(original) == 2                                                           # the first-attempt generation + FIT rows stay in the original block
    texts = _json(f"{fam.PACKAGE}/countersign-row-texts-v1.json")["rows"]
    assert "SAEA-SLURP-DIRECT-ONLY-FOLD-B-THINKING-FIT-V1" not in texts
    for run_id in (spec["run"], spec["fit_run"]):
        assert "root countersigned" in texts[run_id] and "RECOVERY rec1" in texts[run_id] and "countersignature pending" not in texts[run_id]
    assert "re-minted by the coordinator" in texts[spec["run"]]


def test_the_flip_can_be_narrowed_to_the_thinking_arm_alone():
    text = (DIRECT / "direct_fb_flip.sh").read_text(encoding="utf-8")
    assert 'KINDS=${DIRECT_FB_KINDS:-"smoke thinking instruct replicate"}' in text and "for KIND in $KINDS; do" in text
    assert 'case " $KINDS " in *" thinking "*|*" smoke "*) ;; *) break ;; esac' in text
    assert fam.rec_suffix("thinking") == "-rec1" and fam.plan_file_name("thinking", "fit").endswith("-rec1-v1.json")


@pytest.mark.parametrize("key", fam.ALL_KEYS)
def test_every_live_266e_row_pre_registers_at_least_the_gpu_hours_its_plan_claims(key):
    """The class of the 2026-10-12 Thinking abort: the exposure gate reads the matched row's gpu cell against the plan, and the FIT run has a row
    of its own, so an amendment that raised only the generation row left the arm refused before any contact."""

    check = _registration_check_module()
    ledger = check.parse_ledger(REPO, Path("docs/exposure-ledger.md"))
    spec = fam.CELLS[key]
    for role, run_id in (("generation", spec["run"]), ("fit", spec["fit_run"])):
        plan = _json(f"{fam.PACKAGE}/{fam.plan_file_name(key, role)}")
        claim = max(plan["execution_plan"]["planned_gpu_hours"], plan["family_budget"]["gpu_hours_fit_inclusive"])
        rows = ledger.get(run_id, [])
        assert rows, f"{run_id} has no ledger row"
        live = [r for r in rows if not check.row_consumed(r) and not check.SUPERSEDED_ROW.search(check.row_text(r))]
        for row in live:
            assert float(row["gpu hours"]) >= claim, (run_id, row["gpu hours"], claim)
        assert check.gpu_row_findings(role, run_id, rows, claim) == []


def test_the_registration_gate_flags_a_live_row_below_the_plan_gpu_claim_and_skips_history():
    check = _registration_check_module()
    short = {"gpu hours": "3.0", "consumed": "no", "notes": "REGISTERED (DRAFT, root countersignature pending)"}
    (finding,) = check.gpu_row_findings("fit", "RUN-FIT", [short], 4.5)
    assert finding.kind == "row-gpu-under-plan" and finding.severity is None and "3 gpu hours" in finding.message and "4.5" in finding.message
    assert check.gpu_row_findings("fit", "RUN-FIT", [{**short, "gpu hours": "4.5"}], 4.5) == []
    assert check.gpu_row_findings("fit", "RUN-FIT", [{**short, "consumed": "yes"}], 4.5) == []
    assert check.gpu_row_findings("fit", "RUN-FIT", [{**short, "notes": "SUPERSEDED by the rec1 row"}], 4.5) == []
    assert check.gpu_row_findings("fit", "RUN-FIT", [short], None) == []
    assert check.planned_gpu_hours_of({"execution_plan": {"planned_gpu_hours": 4.5}}) == 4.5 and check.planned_gpu_hours_of({}) is None
