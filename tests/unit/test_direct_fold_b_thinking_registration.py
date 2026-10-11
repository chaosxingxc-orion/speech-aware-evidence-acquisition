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
    assert b["decoding_params"]["max_tokens"] == 2048 and a["decoding_params"]["max_tokens"] == 512
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
    assert text.index("serving-slurp-thinking-direct-fold-b-np4-v1") < text.index("INSTRUCT_SESSION=")


@pytest.mark.parametrize("segment,expected", [("smoke", ["smoke"]), ("thinking", ["thinking"]), ("instruct", ["instruct", "replicate"])])
def test_the_chain_queue_per_segment(tmp_path, segment, expected):
    text = _chain_text()
    snippet = text.split("<<'PY'\n", 1)[1].split("\nPY\n", 1)[0].replace("/home/chao/batch-queue.json", str(tmp_path / "queue.json"))
    env = {"DFB_SEGMENT": segment, "DFB_MAIN": str(REPO), "PATH": "/usr/bin:/bin"}
    result = subprocess.run([sys.executable, "-B", "-c", snippet], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    steps = json.loads((tmp_path / "queue.json").read_text(encoding="utf-8"))
    assert [s["short"] for s in steps] == [f"direct-fb-{k}" for k in expected]
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


def test_the_draft_receipt_lists_the_eight_run_ids_and_mints_once(tmp_path):
    draft = _json(f"{fam.PACKAGE}/root-admission-draft-v1.json")
    assert draft["eligible_run_ids"] == mint_mod.expected_eligible() and len(draft["eligible_run_ids"]) == 8
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
