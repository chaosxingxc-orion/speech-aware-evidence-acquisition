#!/usr/bin/env python3
"""Write the registration package of the 266-E bare-core read (Thinking versus Instruct, direct-only, TRAIN Fold B).

Reads the four derived experiment fragments, recomposes every cell's own hashes through ``core.config.compose`` / ``protocol_hash``
exactly as ``core.flight.cli`` does, and writes the package documents, the preregistration note, the draft decision receipt, the
countersign row texts and -- with ``--append-ledger`` -- the DRAFT exposure rows. Config alone: no adapter, no split load, no
lock, no contact; it flips nothing and mints nothing.

    python -B scripts/flights/direct/direct_fb_write_registration.py \\
        --study-commit <40-hex> --registered-at 2026-10-11T18:00:00.000000+00:00 --append-ledger
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import direct_fb_family as fam  # noqa: E402
import direct_fb_pins as pins_mod  # noqa: E402

REPO_ROOT = fam.REPO_ROOT
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.core.config import compose, protocol_hash  # noqa: E402

LEDGER = "docs/exposure-ledger.md"
DECISIONS = "docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md"
INSTRUMENT = "docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md"
B6_READ = "docs/results/2026-09-22-slurp-b6-dev2000-added-direct-vs-plan-read.md"
SMOKE_ROSTER_ROW_ID = "SAEA-SN-MF-SLURP-DIRECT-FOLD-B-SMOKE-4-ROSTER-V1"
READER = "scripts/analysis/slurp_direct_fold_b_core_read.py"
PRIMARY_METRIC = ("official SLURP pooled SLU-F1 (micro; scorer slurp-slu-official-train, the pinned official evaluate.py), natural-mixture "
                  "weighting, with intent accuracy (scenario_action) beside it")
INHERITED = (
    "TRAIN Fold B discovery rows already exposed by SAEA-SLURP-EVO-FOLD-PACKETS-V2, SAEA-SLURP-EVO-S1-INTENT-FOLDS-V2, the EVO-S1 confirmation fold "
    "SAEA-SLURP-EVO-S1-FOLD-B-V2 (8,640 contacts, 2026-09-06), the encoder pass SAEA-SLURP-TFRL-FOLD-B-SPEECH-QUERY-ENCODING-V1, the P-SV-1..P-SV-4 "
    "Fold B cells, the NX R1 / R6 Fold B columns, the VER-1a pool and the TFRL tables registered on these rows; this cell opens no split. Prior "
    "exposure is inherited in full."
)

MMPROJ_FINDING = (
    "The audio-encoder tensors of the two mmproj files differ: 748 of 860 tensors are not byte-identical (name-for-name comparison of the "
    "GGUF tensor tables of mmproj-Qwen3-Omni-30B-A3B-Instruct-bf16.gguf and mmproj-Qwen3-Omni-30B-A3B-Thinking-bf16.gguf; the 112 identical tensors "
    "are the non-audio ones). The Instruct speech-feature packets (/home/chao/feat-cache/slurp-q4km-packets-04ccc72a) are decoder-ready projector "
    "outputs of the Instruct encoder and are therefore NOT valid input for the Thinking decoder. The Thinking core needs its OWN packet root "
    f"({fam.THINK_PACKET_ROOT}) prepared by a GPU encoder pass over TRAIN Fold B inside a serving-swap window (registered, held: ledger row "
    f"{fam.PACKETS_ROW_ID}, fragment {pins_mod.PREPROCESS_FRAGMENT}; it supersedes the CPU sidecar run {fam.CPU_PACKETS_ROW_ID}, stopped after 50 rows at "
    "16-19 s per row); the Thinking baselines pin its future promotion receipt with a zero sentinel the flip refuses."
)
REASONING_FINDING = (
    "Reasoning stays out of the delivered content by the server flag --reasoning-format deepseek (registered explicitly in the serving fragment's "
    "server_args). Evidence from the pinned featcache build 04ccc72a2 (read-only grep): tools/server/README.md line 220 documents the option "
    "(none leaves thoughts in message.content; deepseek puts thoughts in message.reasoning_content; deepseek-legacy keeps <think> in content AND "
    "fills reasoning_content); common/arg.cpp line 3130 defines it; common/common.h line 622 makes COMMON_REASONING_FORMAT_DEEPSEEK the build's "
    "own default; common/chat.cpp line 828 maps it. The transport (core/model/transport.py) reads ONLY choices[0].message.content (and tool_calls); "
    "it never reads reasoning_content. The cells set preserve_wire_responses false, so no raw wire bytes (which would carry reasoning_content) are "
    "persisted. Client-side guard: the fragment declares reasoning_content_guard refuse-think-marker-in-content, and the transport raises "
    "FrozenCoreError when a delivered content string carries <think>, </think>, <thinking> or </thinking> (case-insensitive), BEFORE anything is "
    "returned or persisted; the flight stops (a leak means the option is not effective). The reader counts leak markers in the sealed delivered text "
    "(count only) as a second check."
)
CAP_FINDING = (
    f"Completion cap {fam.THINK_MAX_TOKENS} tokens (amended from {fam.SUPERSEDED_THINK_MAX_TOKENS} at the decode-cost sign-off of 2026-10-11, the one re-registration this finding "
    "pre-authorised). Slot budget: -c 98304 / -np 4 = 24,576 tokens per slot. The direct-only prompt is about 2,300 tokens per row (the sealed Instruct "
    "direct form measured 2,262 to 2,280 prompt tokens per contact; 3,733 on the A2T registry). 2,300 + 8,192 = 10,492 tokens, 42.7 percent of a slot, so "
    "the cap is still bound by decode cost, not by the slot. The first cap, 2048, was proposed because a SLURP answer is a short structured object, so a "
    "thinking trace that needs more than 2,048 tokens is itself the signal the read must see (a truncated answer is an abstention, counted in the cap-hit "
    "table). The four-row decode-cost smoke then measured the real distribution (run SAEA-SLURP-DIRECT-ONLY-FOLD-B-THINKING-SMOKE-4-V1, attempt "
    "attempt-slurp-direct-only-fold-b-thinking-smoke-4-generation-v1, 2026-10-11T21:49Z, 4 calls, 9.9395 speech-seconds): completions of 363, 921 and 977 "
    "tokens delivered 99, 111 and 60 characters of content, and ONE of the four contacts spent all 2,048 completion tokens (prompt 2,285) and delivered "
    "content of length 0 (the whole budget went to reasoning, which the server routes to message.reasoning_content and the transport never reads), so 1 of 4 "
    "rows hit the cap; decode speed was 37 tokens per second per slot (58 with one slot busy) and prompt evaluation 0.9 to 1.7 ms per token. That empty "
    "content crashed the OpenJiuwen wave (the sealed state refused an empty string). The harness now seals an empty final content of a direct-only contact "
    "as the explicit empty marker and leaves a saea-empty-completion-v1 receipt (cap_hit, completion_tokens, finish_reason), so a cap hit is a row-level "
    "outcome counted in the cap-hit table, never a flight abort. A cap that truncates a quarter of the rows would make the read a read of the cap, so it is "
    f"raised to {fam.THINK_MAX_TOKENS} for the smoke (re-flown whole under rec1) and the Thinking arm. The Thinking arm's GPU-hour ceiling moves 3.0 -> "
    f"{fam.THINK_ARM_GPU_HOURS}: a bound, never a target; at the smoke's mean of 1,077 completion tokens per contact and 4 slots x 37 tokens per second "
    "the 1,080-row arm is about 2.2 GPU-h, and 4.5 GPU-h admits a mean of about 2,200 tokens per contact (the all-cap-hit worst case, about 16.6 GPU-h, is "
    "not what the ceiling covers). The cap lives in the model fragment's decoding_params and the flight attaches to a resident session by fragment name and "
    f"sha256, so the fragment ({fam.THINK_MODEL}) and the serving session ({fam.THINK_SESSION}) both carry the new cap; the flown "
    f"{fam.SUPERSEDED_THINK_MODEL} and {fam.SUPERSEDED_THINK_SESSION} stay on disk as the record of the first smoke attempt."
)
SEALED_COLUMN_FINDING = (
    "No sealed Instruct direct-only Fold B column exists. The sealed direct-only (phase-direct-only-v1, slurp-direct-max512) columns are "
    "SAEA-SLURP-DIRECT-MAX512-TRAIN-FOLD-A-V1 (Fold A), -DEV1000-V1 and -DEV2000-ADDED-V1 (devel rosters). Fold B carries only the older EVO-S1 "
    "confirmation flight of the 'fixed' closed-list arm (SAEA-SLURP-EVO-S1-FOLD-B-V2), a different form on a different code path, which is not a "
    "same-harness comparator. The Instruct arm and its replicate therefore fly in this chain: the comparison must be same-chain."
)
CHAIN_FINDING = (
    "Chain order. The brief's order smoke -> sign-off -> Instruct arm -> replicate -> Thinking arm would swap the serving geometry three times "
    "(Instruct resident now: swap to Thinking for the smoke, back to Instruct, to Thinking again, and back to restore). The registered order is "
    "smoke -> sign-off -> Thinking arm (Thinking session), then ONE swap back to the Instruct session (which is also the required restore) and the "
    "Instruct arm -> Instruct replicate: two swaps total. The Instruct segment has no dependency on the Thinking one, so the coordinator may fly "
    "it first on the resident session before the swap if GPU idle time during the sign-off is the concern; batch_chain_direct_fb.sh takes the "
    "segment as an argument (smoke | thinking | instruct), checks the resident session by id and refuses on a mismatch. All segments fly from "
    "ONE flight commit."
)

CHECKLIST = [
    "0. Preconditions: the four cells are flipped at one flight commit (scripts/flights/direct/direct_fb_flip.sh); the Thinking packet root is prepared and "
    "its promotion receipt pinned (the flip refuses while the zero sentinel remains); the decision receipt is minted; no generation flight, lease or driver "
    "is alive and no CPU sidecar runs (one experiment in flight).",
    "1. Tell the uptime guard: create /home/chao/saea-queue/watchdog.hold (the idle watchdog then exits at step 3 of every tick and cannot swap the "
    "geometry back, force an uptime restart, or launch another chain while the Thinking session is resident or the sign-off is pending). Confirm "
    "with scripts/flights/batch/idle_watchdog.sh --dry-run that it logs the hold. Do not edit ready_chains.json; leave the hold in place until step 9.",
    "2. Dry run: bash scripts/flights/batch/serving_swap.sh think-np4 --dry-run (prints every precondition verdict; starts, stops and registers nothing).",
    "3. Release Instruct and start Thinking: bash scripts/flights/batch/serving_swap.sh think-np4. The tool stops serving-slurp-native-candidate-five-train-a-np4-v1 "
    "cleanly and its tasks (SAEA-Serving, SAEA-Monitor), verifies port 8080 free, starts the Windows task SAEA-Serving-THINK "
    "(scripts/flights/direct/serving_task_entry_think.sh) and SAEA-Monitor-THINK 20 s later, then the strict readiness wait; on any failure it tears "
    "the Thinking session down and restores Instruct. The two task names are new: the first run registers them through saea_task.ps1 -Start with the entry script.",
    "4. Smoke: bash scripts/flights/direct/batch_chain_direct_fb.sh smoke (flies the four-row smoke through the batch driver on the Thinking session; "
    "the driver's structural inspector runs). Then python -B scripts/analysis/slurp_direct_fold_b_core_read.py --stage smoke prints tokens per answer "
    "p50/p99, seconds per contact and the 1,080-row GPU-hour projection.",
    "3b. Cap-amendment variant (2026-10-11, the Thinking session recorded resident is the SUPERSEDED max2048 one): serving_swap.sh refuses a resident session "
    "that is not in its geometry table, so first run bash scripts/flights/direct/serving_stop_think_superseded.sh --dry-run and then without --dry-run (a clean "
    f"stop of {fam.SUPERSEDED_THINK_SESSION}, its wrapper, port 8080 free, then SAEA-Serving-THINK and SAEA-Monitor-THINK stopped; it starts nothing), then "
    f"bash scripts/flights/batch/serving_swap.sh think-np4 --start-only (the card is empty) to start {fam.THINK_SESSION}.",
    f"5. Sign-off: when the decode cost is acceptable, create the marker {fam.SIGNOFF_MARKER} (a one-line file naming the approved completion cap). "
    "The thinking segment refuses to start without it. If the cost is not acceptable, close the line (restore, step 8) or amend the cap by one re-registration.",
    "6. Thinking arm: bash scripts/flights/direct/batch_chain_direct_fb.sh thinking.",
    "7. Release Thinking and restore Instruct: bash scripts/flights/batch/serving_swap.sh slurp-np4 (the restore; the Instruct task entry is the "
    "existing serving_task_entry.sh), then bash scripts/flights/direct/batch_chain_direct_fb.sh instruct (the Instruct arm, then its replicate).",
    "8. If the Thinking line closes before the arm: bash scripts/flights/batch/serving_swap.sh slurp-np4 alone restores the resident geometry; the "
    "Instruct segment may still be flown (it is a useful Fold B direct-only column on its own).",
    "9. After the Instruct session reports ready (SLURP SESSION READY from serving_wait_ready.sh slurp-np4) remove /home/chao/saea-queue/watchdog.hold; "
    "the watchdog resumes from the committed ready_chains.json. Stop SAEA-Serving-THINK and SAEA-Monitor-THINK (serving_swap does this on the stop) and "
    "leave them unregistered or disabled; remove the decode sign-off marker.",
    "10. Read: bash scripts/flights/direct/direct_fb_read.sh (countersign the READ row first).",
]


def rd(path: str) -> str:
    return io.open(REPO_ROOT / path, encoding="utf-8", newline="").read()


def wr(path: str, text: str) -> str:
    target = REPO_ROOT / path
    os.makedirs(target.parent, exist_ok=True)
    io.open(target, "w", encoding="utf-8", newline="").write(text)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def wjson(path: str, obj: object) -> str:
    return wr(path, json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + "\n")


def sha256_file(relpath: str) -> str:
    return hashlib.sha256((REPO_ROOT / relpath).read_bytes()).hexdigest()


def compose_cell(key: str) -> dict:
    spec = fam.CELLS[key]
    document = json.loads(rd(f"configs/experiment/{spec['cell']}.json"))
    cell = document["cells"][0]
    composed = compose(REPO_ROOT, cell["model_fragment"], cell["dataset_fragment"], cell["baseline_fragment"], spec["cell"])
    split = document["population"]["split_identity_hash"]
    phash = protocol_hash(composed.config_hash, composed.values["arm"], split)
    fit = composed.values["live_phase_fit"]
    if (fit["run_id"], fit["attempt_id"]) != (spec["fit_run"], spec["fit_attempt"]) or (cell["run_id"], cell["attempt_id"]) != (spec["run"], spec["attempt"]):
        raise SystemExit(f"{key}: the composed identities are not the registered ones")
    if fit["contact_cap"] != fam.fit_contact_cap(spec["rows"]):
        raise SystemExit(f"{key}: live fit contact_cap {fit['contact_cap']} is not 1 + 3 x {spec['rows']}")
    if composed.values.get("preserve_wire_responses") is not False:
        raise SystemExit(f"{key}: preserve_wire_responses must be false (decision 266-E constraint iii)")
    return {"key": key, "spec": spec, "document": document, "cell": cell, "composed": composed, "config_hash": composed.config_hash,
            "protocol_hash": phash, "split": split, "fit": fit, "rows": spec["rows"], "caps": document["family_budget"]}



#: The recovery keys persisted into plan and protocol documents. Text fields that only the writer prints (ledger title, agent, fix, unchanged,
#: swap note ...) are NOT persisted, so adding a recovery never moves the bytes of another cell's registered plan.
PERSISTED_RECOVERY_KEYS = (
    "amendment", "fit_cap_rule", "predecessor_attempt_id", "predecessor_fit_attempt_id", "predecessor_fit_run_id", "predecessor_state",
    "predecessors", "reason", "recovered_at", "recovery_index", "root_cause", "rule",
)


def persisted_recovery(key: str, recovery_at: str, recovery_base: str) -> dict:
    """The recovery block of a plan or protocol document: the persisted subset, its own registration stamp and base commit, the knowledge pin
    when the recovery is the one that moved it."""

    rec = fam.recovery(key)
    out = {name: rec[name] for name in PERSISTED_RECOVERY_KEYS}
    out["registered_at_utc"] = rec.get("registered_at_utc") or recovery_at
    out["base_commit"] = rec.get("base_commit") or recovery_base
    if rec.get("knowledge_pin"):
        out["knowledge_snapshot"] = {"relpath": fam.KNOWLEDGE_SNAPSHOT_RELPATH, "sha256": fam.KNOWLEDGE_SNAPSHOT_SHA256}
    return dict(sorted(out.items()))


def recovery_budget(key: str, caps: dict) -> dict:
    """A recovered cell's run-cumulative budget statement: the original plan, the failed attempts' recorded spend, their sum."""

    spent_calls, spent_audio = fam.predecessor_spend(key)
    cumulative_calls, cumulative_audio = int(caps["generation_calls_cap"]), int(caps["repeated_speech_audio_seconds_cap"])
    return {
        "original_plan": {"planned_model_calls": cumulative_calls - spent_calls,
                          "planned_speech_audio_seconds": cumulative_audio - int(spent_audio + 0.999999999)},
        "failed_attempt_spend": {"model_calls": spent_calls, "speech_audio_seconds": spent_audio,
                                 "attempt_ids": [p["attempt_id"] for p in fam.recovery(key)["predecessors"]]},
        "cumulative_plan": {"planned_model_calls": cumulative_calls, "planned_speech_audio_seconds": cumulative_audio},
        "rule": "The adapter budget is run-cumulative across the attempts of a run id; the FIT cap is structural and never scaled.",
    }


def recovery_section(key: str, spec: dict, caps: dict) -> str:
    """The rec1 text of the README and the preregistration: failed attempt, root cause, fix, rec1 ids, cumulative budget, untouched cells."""

    rec, budget = fam.recovery(key), recovery_budget(key, caps)
    receipt = rec.get("receipt_clause") or f"the generation run id `{spec['run']}` and the minted decision receipt are unchanged"
    swap = f"- Serving: {rec['swap_note']}\n" if rec.get("swap_note") else ""
    return (
        f"\n## Recovery rec1: the {spec['role']} (the cell's single recovery re-registration)\n\n"
        f"{rec['reason']}\n\n{rec['amendment']}\n\n"
        f"- Failed attempt: `{rec['predecessor_attempt_id']}` ({rec['predecessor_state']})\n"
        f"- Root cause: {rec['root_cause']}.\n"
        f"- Fix: {rec['fix']}\n"
        f"- Re-flown whole under generation attempt `{spec['attempt']}` and FIT run `{spec['fit_run']}` / attempt `{spec['fit_attempt']}`; "
        f"{receipt}.\n"
        f"- Run-cumulative plan budget: {budget['original_plan']['planned_model_calls']} + {budget['failed_attempt_spend']['model_calls']} = "
        f"{budget['cumulative_plan']['planned_model_calls']} calls; {budget['original_plan']['planned_speech_audio_seconds']} + "
        f"{budget['failed_attempt_spend']['speech_audio_seconds']:g} = {budget['cumulative_plan']['planned_speech_audio_seconds']} "
        "speech-seconds; the FIT cap stays structural.\n"
        f"- Plans: `{fam.plan_file_name(key, 'generation')}`, `{fam.plan_file_name(key, 'fit')}` (the first-attempt plan files are superseded and removed "
        "from the package; the git history keeps them, and the failed attempt stays on the data root).\n"
        f"- {rec['unchanged']}\n"
        f"{swap}"
        f"- {rec['rule']}\n")


LEDGER_COLUMN_NAMES = ["date", "run/experiment id", "execution profile", "scope", "model/tool", "speech carrier + split", "split role",
                       "split identity hash", "consumed", "calls", "speech audio seconds", "gpu hours", "inherited exposure", "artifacts", "notes"]
RECOVERY_LEDGER_MARK = "## Cell 266-E recovery rec1: "


def ledger_row(registered_at, run_id, profile, scope, model_tool, carrier, split_hash, calls, audio, gpu, artifact, notes, consumed="no") -> str:
    line = " | ".join(["", registered_at, run_id, profile, scope, model_tool, carrier, "discovery", split_hash, consumed, str(calls), str(audio), str(gpu),
                        INHERITED, artifact, notes, ""]).strip()
    if line.count("\n") or line.count("|") != 16:
        raise SystemExit(f"a ledger row is malformed ({line.count('|')} pipes)")
    return line


def recovery_ledger_block(key: str, entry: dict, registered_at: str, base_commit: str, worktree: str, branch: str, plan_shas: dict) -> str:
    """The two DRAFT rows of a recovered cell (generation, FIT) as one new ledger block; the first-attempt rows stay exactly as they are."""

    spec, caps, rec = entry["spec"], entry["caps"], fam.recovery(key)
    budget = recovery_budget(key, caps)
    registered_at = rec.get("registered_at_utc") or registered_at
    base_commit = rec.get("base_commit") or base_commit
    worktree, branch = rec.get("worktree") or worktree, rec.get("branch") or branch
    rows_text = f"{entry['rows']:,}"
    if spec["core"] == "thinking":
        tool = (f"Frozen Qwen3-Omni-30B-A3B-Thinking Q4_K_M ({pins_mod.LOCK_KEY}), decoder-only build 04ccc72a, c98304 np4 x 24,576 max{fam.THINK_MAX_TOKENS}, "
                f"q8_0 KV, --reasoning-format deepseek ({fam.THINK_MODEL}); its own promoted speech packets; direct-only phase program; no tool authority")
    else:
        tool = (f"Frozen Q4_K_M decoder-only build 04ccc72a, c98304 np4 x 24,576 max512 ({fam.INSTRUCT_MODEL}); promoted EVO-FOLDS-V2 speech packets; "
                "direct-only phase program; no tool authority")
    common = (f"RECOVERY RE-REGISTRATION (root-diagnosed, the cell's single one, {rec['recovered_at']}): this row SUPERSEDES the first-attempt row of the same run id "
              "(the coordinator folds the earlier row into this one when countersigning). ")
    tail = rec.get("ledger_scope_tail") or "re-flown whole under the fold-excluded knowledge pin"
    gen_notes = (
        f"REGISTERED (DRAFT, root countersignature pending) {registered_at[:10]} at base commit {base_commit} by {rec['agent']} "
        f"(worktree {worktree}, branch {branch}); owner decision 266-E. {common}Attempt {rec['predecessor_attempt_id']} {rec['predecessor_state']} "
        f"Root cause: {rec['root_cause']}. The cell is re-flown whole under generation attempt {spec['attempt']}, a (run_id, attempt_id) pair being a one-time key; "
        f"the plan budget is run-cumulative across the attempts of the run id: the original plan plus the failed attempt's recorded spend, "
        f"{budget['original_plan']['planned_model_calls']} + {budget['failed_attempt_spend']['model_calls']} = {budget['cumulative_plan']['planned_model_calls']} calls and "
        f"{budget['original_plan']['planned_speech_audio_seconds']} + {budget['failed_attempt_spend']['speech_audio_seconds']:g} = "
        f"{budget['cumulative_plan']['planned_speech_audio_seconds']} speech-seconds. Composed config {entry['config_hash']}, protocol {entry['protocol_hash']} "
        f"(the re-pin tool rewrites both at the flip). Expected session {spec['session']}. A second failure closes the cell. "
        f"HELD: this registration performs no contact and authorises none.")
    fit_notes = (
        f"REGISTERED (DRAFT, root countersignature pending) {registered_at[:10]} at base commit {base_commit} by {rec['agent']} "
        f"(worktree {worktree}, branch {branch}); owner decision 266-E. {common}The FIT row of {spec['run']} under the rec1 identities: FIT run {spec['fit_run']}, "
        f"FIT attempt {spec['fit_attempt']} (supersedes FIT run {rec['predecessor_fit_run_id']} / attempt {rec['predecessor_fit_attempt_id']}, {rec['fit_predecessor_phrase']}). "
        f"Root cause: {rec['root_cause']}. The FIT cap stays structural ({caps['fit_endpoint_calls_cap']}, not scaled); speech seconds and GPU hours are the "
        "generation row's ceilings, shared and not additive. HELD: this registration performs no contact and authorises none.")
    gen = ledger_row(registered_at, spec["run"], "bounded-discovery-probe",
                     f"Cell 266-E {spec['role']} -- RECOVERY rec1: the sealed direct-only form on TRAIN Fold B on the {spec['core']} core, {tail}; a capability read, no mechanism, no claim.",
                     tool, f"slurp TRAIN Fold B {rows_text}", entry["split"], caps["generation_calls_cap"], caps["repeated_speech_audio_seconds_cap"],
                     caps["gpu_hours_fit_inclusive"], fam.package_file(fam.plan_file_name(key, "generation")), gen_notes)
    fit = ledger_row(registered_at, spec["fit_run"], "bounded-discovery-probe",
                     f"Cell 266-E {spec['role']} -- RECOVERY rec1 live phase-fit spend identity, request envelopes only, no generation.",
                     tool, f"slurp TRAIN Fold B {rows_text}", entry["split"], caps["fit_endpoint_calls_cap"], caps["repeated_speech_audio_seconds_cap"],
                     caps["gpu_hours_fit_inclusive"], fam.package_file(fam.plan_file_name(key, "fit")), fit_notes)
    header = (f"\n{RECOVERY_LEDGER_MARK}{rec['ledger_title']} (DRAFT, root countersignature pending)\n\n"
              f"Two unconsumed rows -- the recovered generation row and its rec1 live-phase-fit identity -- for the single recovery re-registration of the {spec['role']} of "
              f"owner decision 266-E. Package {fam.PACKAGE}. Neither row is countersigned and neither authorises a contact; the first-attempt rows above are unchanged.\n\n"
              "| " + " | ".join(LEDGER_COLUMN_NAMES) + " |\n"
              "| " + " | ".join("---" for _ in LEDGER_COLUMN_NAMES) + " |\n")
    return header + gen + "\n" + fit + "\n"


PACKETS_RUNBOOK = '## Thinking speech packets: GPU window, command sequence, runtime and re-pin (the coordinator\'s; nothing here executes it)\n\n**Re-registration of 2026-10-11 (supersedes the CPU sidecar pass).** The first packet pass ran the Thinking encoder on a CPU sidecar (`q4km-thinking-preprocess-featcache-cpu-sidecar-np4-v1`, `-np 4 -ngl 0 --no-mmproj-offload`) at 16 to 19 s per row (4-row smoke 76.6 s; 50 of 1,076 Fold B rows in 799 s, about 4.7 h for Fold B). The owner ruled that rate unacceptable and the pass was STOPPED at 11:50Z after 50 rows (run id `SAEA-SLURP-DIRECT-ONLY-FOLD-B-THINKING-PACKETS-V1`, attempt `attempt-packets-thinking-fold-b-v1`; the flight\'s one recovery re-registration was already spent on the smoke). It stays in the record as SUPERSEDED: its fragment, run id, roots (`/home/chao/feat-cache/slurp-q4km-packets-thinking-afdaeff6`, `/home/chao/feat-cache/slurp-thinking-q4km`) and its chain (`direct_fb_packets.sh`, which now refuses without `--allow-cpu`) are unchanged. Root cause of the rate: every fast preprocess in this repository runs the encoder on the GPU (`q4km-e21-feature-preprocess-gpu-cddb000c-np1`: `-c 8192 -np 1 -ngl 999 -fa on -ctk q8_0 -ctv q8_0 -b 512 -ub 128`); the Thinking fragment had copied the CPU sidecar geometry instead. CPU- and GPU-made encoder outputs are not bit-identical, so the GPU pass has its OWN packet root and legacy cache and never mixes with the 50 CPU-made rows.\n\nDriver `scripts/slurp_fold_preprocess_thinking.py --geometry gpu` (the default; a sibling of `scripts/slurp_evo_fold_preprocess.py`, which is not modified: it loads that driver and reuses its\nhelpers, so the packet format, the promotion receipt shape and the roster logic are the Instruct ones) and chain `scripts/flights/direct/direct_fb_packets_gpu.sh`.\nTwo attempts of ONE run id (`SAEA-SLURP-DIRECT-ONLY-FOLD-B-THINKING-PACKETS-GPU-V1`, plan budget run-cumulative, row total 1,084 calls / 3,165 speech seconds = the 1,080-row total plus the 4-row smoke attempt):\n`thinking-smoke-4` (attempt `attempt-packets-thinking-gpu-smoke-4-v1`: the first four Fold B rows, encoded into the GPU legacy cache only: no packet, no promotion receipt, packet root stays empty; the proof of the fixed form) and `thinking-fold-b` (attempt `attempt-packets-thinking-gpu-fold-b-v1`: the 1,076 cold rows encoded, the smoke\'s four warm rows are not contacted again, then all 1,080 promoted into the empty root and the promotion receipt written). The GPU server is `q4km-thinking-feature-preprocess-gpu-np1-v1` (`-c 16384 -np 1 -ngl 999 -fa on -ctk q8_0 -ctv q8_0 -b 512 -ub 128`, `GGML_CUDA_DISABLE_GRAPHS=1`, decoder AND bf16 mmproj on the GPU) under `docs/receipts/runtime-q4km-thinking-preprocess-gpu.json` (the same pinned featcache build and Thinking GGUF pins as the CPU receipt; its llama-server binary hash was re-read on the host and equals the receipt). One worker: the server batches at its own `-np 1`.\n\nThe 24 GB card holds ONE core. The resident Instruct serving session (about 22.9 GB) must be stopped for the GPU encoder, and the Thinking serving session (`think-np4`) starts afterwards so the flight can follow. The chain owns that window end to end (`serving_swap.sh --stop-only`, the smoke, a rate gate, Fold B, `serving_swap.sh think-np4 --start-only`; on ANY failure `serving_swap.sh slurp-np4 --start-only` restores the Instruct geometry and the exit code names the failed step; exit 25 means the restore itself failed and the card may be empty). The driver refuses to start while any serving session is recorded resident, anything listens on port 8080 or GPU memory is in use.\n\nCommand sequence:\n\n1. Countersign the exposure row `SAEA-SLURP-DIRECT-ONLY-FOLD-B-THINKING-PACKETS-GPU-V1` (root\'s act; it is in the block "Cell 266-E packets re-registration" at the end of `docs/exposure-ledger.md`): replace its whole notes cell with the text in\n   "Countersign text" below. The chain refuses a row that still says DRAFT, lacks the words "root countersigned", is consumed, or whose numbers or split identity differ.\n2. `bash scripts/flights/direct/direct_fb_packets_gpu.sh --check` -- every guard, both driver dry-runs and `serving_swap.sh --stop-only --dry-run`, no side effects. Guards: clean tree; no generation flight, lease,\n   batch driver or `flight.lock`; no other llama-server and no packet driver; host-available memory at least 8 GB (`PACKETS_START_FLOOR_GB`) and 5 GB free disk; ledger row countersigned; the\n   dry-run of each roster (pins equal the umbrella lock and the committed runtime receipt, roots empty, smoke rows are the Fold B prefix; the dry-run reports the serving state as information and never refuses over the resident Instruct session); the Thinking serving entries exist.\n3. `bash scripts/flights/direct/direct_fb_packets_gpu.sh --task` (starts the Windows task `SAEA-Packets-THINK-GPU`, which survives the session) or `--run [--stage all|smoke|fold-b]`\n   in a foreground shell. The window: hold the idle watchdog (`/home/chao/saea-queue/watchdog.hold`, created if absent; it STAYS in place after a successful window and is removed only after the Instruct restore, README serving checklist step 9),\n   stop Instruct, smoke (4 rows), the rate gate (`--smoke-rate`: the projected Fold B encode must stay within `--max-fold-seconds`, default 3,000 s, else the window restores Instruct with exit 23), Fold B (encode, then promote), start Thinking and wait for strict readiness.\n   `--stage smoke` is a short window that ends on the Instruct geometry; `--stage fold-b` is the second window after it. Do not start a swap, a flight or another sidecar while it runs; use a recovery file `/home/chao/direct-fb-packets-gpu.recovery` (NOT the CPU run\'s `direct-fb-packets.recovery`).\n4. Read: the window summary with every event timestamp at `$SPEECHRL_DATA_DIR/prepared/slurp-direct-fb-thinking-packets-gpu-v1/window-summary.json` (also `window-events.tsv`, `swap-summaries.jsonl`, `encoder-report-<roster>.json`), the encoder receipts under\n   `$SPEECHRL_DATA_DIR/runs/SAEA-SLURP-DIRECT-ONLY-FOLD-B-THINKING-PACKETS-GPU-V1/attempt-packets-thinking-gpu-{smoke-4,fold-b}-v1/encoder-receipt.json` (device `gpu`, seconds per row, server arguments, llama.cpp build commit, decoder and\n   mmproj sha256, runtime receipt sha256, split identity, per-file sha256 -- packet and chunk feature hashes for Fold B, legacy cache file hashes for the smoke -- worker\n   counts, timings) and the promotion receipt `/home/chao/feat-cache/slurp-q4km-packets-thinking-gpu-afdaeff6/EVO-FOLD-B-V2-promotion.json`. After a failed Fold B attempt whose cache\n   is fully warm, `python -B scripts/slurp_fold_preprocess_thinking.py --roster thinking-fold-b --promote-only --attempt-id <new id>` promotes with zero contacts (model-free, no GPU needed); any other\n   failure is the flight\'s one recovery re-registration, not a retry.\n5. `python -B scripts/slurp_fold_preprocess_thinking.py --pin-receipt` -- model-free: validates the promotion receipt with the runtime\'s own loader, checks that it covers exactly\n   the 1,080 Fold B rows under the committed Thinking GPU runtime receipt and the lock-verified decoder and mmproj, re-verifies every packet on disk, and PRINTS the two baseline\n   substitutions. Add `--write` to substitute the receipt\'s sha256 for the zero sentinel in the two Thinking baselines (it refuses to overwrite a different real pin). Do not\n   re-run `direct_fb_derive_cells.py` afterwards: it would write the sentinel back.\n6. Close the packets ledger row by hand (`consumed = yes`, measured contacts and seconds at the front of the notes); `ledger_mark_consumed.py` has no evidence rule for a packets row.\n7. Commit the two baselines, then the usual order: countersign the eight flight rows, `direct_fb_mint_receipt.py`, `direct_fb_flip.sh` (refuses while a zero sentinel remains), then\n   `refresh_registered_plan_pins.py` and flip again if it says so. Never `--allow-output-change`. The window leaves the Thinking session resident, so serving checklist step 3 is then a readiness-checked no-op.\n\nExpected runtime. There is NO GPU record for a SLURP Fold preprocess in this repository: the Instruct Fold B record (`docs/checks/speech-aware-evidence-acquisition/2026-09-06-slurp-evo-s1/fold-packets/preprocess-fold-b.json`:\n1,080 contacts in 2,037.8 s at 4 workers = 0.53 rows per second) was itself a CPU sidecar pass (`-ngl 0`, the row\'s "2.0 gpu hours" is only the registered ceiling), and the Thinking CPU pass was about nine times slower than that for the same\ngeometry (cause not isolated). The GPU estimate is therefore a bound, not a measurement: per row the audio tower on the GPU plus a one-token decode of a short prompt is expected at 0.3 to 1.0 s at one worker, i.e. 5 to 18 minutes for the 1,076 cold rows (planning value 0.5 s per row, about 9 minutes),\npromotion about 11 s at 8 workers. Window total: Instruct stop about 1 minute, two Thinking GPU loads (smoke and Fold B; each includes the frozen-core GGUF hash and the model load, 1 to 3 minutes, the second likely page-cached), the encode above, the Thinking serving start and strict readiness wait 2 to 4 minutes: about 15 to 20 minutes typical, 30 minutes worst case, 0.25 to 0.5 GPU-h\n(registered ceiling 1.0). The 4-row smoke measures the real rate before Fold B is committed to; the rate gate stops the window if the projection exceeds 3,000 s.\n\nCountersign text for the packets row (replaces the whole notes cell; keep the words "root countersigned", and no draft marker):\n`REGISTERED BEFORE CONTACT (root countersigned <UTC timestamp> by root flight operations on the coordinator\'s brief: owner decision 266-E of 2026-10-11 and the owner ruling of 2026-10-11 that the CPU encode rate is unacceptable; label-free Thinking speech-packet preparation over TRAIN Fold B on the GPU encoder q4km-thinking-feature-preprocess-gpu-np1-v1 through scripts/slurp_fold_preprocess_thinking.py --geometry gpu via scripts/flights/direct/direct_fb_packets_gpu.sh inside a serving-swap window; the 4-row smoke attempt and the Fold B attempt share this row\'s 1,084 calls and 3,165 speech seconds; supersedes SAEA-SLURP-DIRECT-ONLY-FOLD-B-THINKING-PACKETS-V1, which was stopped after 50 rows; prior exposure inherited in full)`\n\nWhich registered files change hash:\n\n- By the pin step itself, exactly two: `configs/baseline/slurp-direct-only-fold-b-thinking-baseline-v1.json` and `configs/baseline/slurp-direct-only-fold-b-thinking-smoke-4-baseline-v1.json`\n  (one field each, `speech_packet_promotion_receipt_sha256`).\n- By THIS re-registration (already regenerated and committed with it by `direct_fb_write_registration.py`): the Thinking serving fragment and the two Thinking baselines name the GPU packet root, so the composed config hash and protocol hash of the\n  two Thinking cells (smoke and Thinking arm) changed once, and with them `protocol-registered-v1.json`, `registered-facts-v1.json`, `root-admission-draft-v1.json`, this README\'s cell table and all eight plan files (every plan pins the sha256 of `protocol-registered-v1.json`). The ledger rows of the eight flight cells still carry the plans\' earlier hashes in their draft text: the countersign step replaces that text and the re-pin below rewrites it.\n- By the flip\'s re-pin (`scripts/flights/repin_cell.py` through `direct_fb_flip.sh`, expected, to be confirmed from its diff): the pin step\'s sentinel substitution changes the baselines, so the composed config hash and protocol hash of the\n  two Thinking cells change again, and the registered files that carry them are re-pinned: `smoke-` and `thinking-` generation and fit plans, `protocol-registered-v1.json`,\n  `registered-facts-v1.json`, `root-admission-draft-v1.json`, this README\'s cell table, and the ledger rows of the four Thinking-side flight rows. Every one of the eight plans pins the sha256\n  of `protocol-registered-v1.json`, so all eight plan files re-pin once that file changes. The Instruct arm and replicate baselines, composed configs and protocol hashes do not change.\n- The smoke roster receipt `smoke-roster-receipt-v1.json` does NOT change: it holds roster ids, audio seconds and a parent pin, no packet or baseline field. Its sha256 is pinned by the plans, the\n  facts file and the ledger, so a change there would break those pins; none is expected or needed.\n- The packet root, the legacy cache and the encoder receipts live outside Git. The Instruct driver `scripts/slurp_evo_fold_preprocess.py` and the Instruct packet root do not change.\n\n'

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study-commit", required=True)
    parser.add_argument("--registered-at", required=True)
    parser.add_argument("--branch", default="sonnet/266e-thinking-bare-read")
    parser.add_argument("--worktree", default="/home/chao/saea-worktrees/sonnet-266e")
    parser.add_argument("--append-ledger", action="store_true")
    parser.add_argument("--append-recovery-ledger", action="store_true",
                        help="append ONLY the recovered cell's two DRAFT rows (rec1) as a new ledger block; idempotent on the rec1 attempt id")
    parser.add_argument("--recovery-registered-at", default=None,
                        help="UTC timestamp of the recovery re-registration (default: now); recorded in the recovery plan and ledger rows")
    parser.add_argument("--recovery-base-commit", default=None, help="the commit the recovery was registered on top of (default: --study-commit)")
    parser.add_argument("--recovery-branch", default="sonnet/direct-fb-knowledge-pin-rec1")
    parser.add_argument("--registered-hashes-ref", default=None,
                        help="git revision whose root-admission-draft-v1.json carries the REGISTERED (pre-change) composed-config and protocol hashes: they are "
                             "written into every registered document instead of the freshly composed ones, so the flip's re-pin (repin_cell.py, which rewrites "
                             "the plans' hashes to the fresh ones across the package AND the ledger rows that quote them) converges. Without it the fresh hashes are written.")
    parser.add_argument("--recovery-worktree", default="/home/chao/saea-worktrees/sonnet-dfb-kbfix")
    args = parser.parse_args(argv)

    cells = {key: compose_cell(key) for key in fam.ALL_KEYS}
    from datetime import datetime, timezone  # noqa: PLC0415
    import subprocess  # noqa: PLC0415

    if args.registered_hashes_ref:
        shown = subprocess.run(["git", "-C", str(REPO_ROOT), "show", f"{args.registered_hashes_ref}:{fam.package_file('root-admission-draft-v1.json')}"],
                               capture_output=True, text=True)
        if shown.returncode != 0:
            raise SystemExit(f"cannot read the registered hashes at {args.registered_hashes_ref}: {shown.stderr.strip()}")
        registered = json.loads(shown.stdout)["registered_hashes"]
        for key in fam.ALL_KEYS:
            cells[key]["config_hash"], cells[key]["protocol_hash"] = registered[key]["composed_config"], registered[key]["protocol"]

    recovery_at = args.recovery_registered_at or datetime.now(timezone.utc).isoformat()
    recovery_base = args.recovery_base_commit or args.study_commit
    pkg, pkg_name = fam.PACKAGE, fam.PKG_NAME
    run_ids = {key: cells[key]["spec"]["run"] for key in fam.ALL_KEYS}
    fit_ids = {key: cells[key]["spec"]["fit_run"] for key in fam.ALL_KEYS}
    eligible = fam.eligible_run_ids()
    source_tree = f"studies/speech-aware-evidence-acquisition, worktree {args.worktree}, branch {args.branch}"
    arm_roster, smoke_roster = fam.roster_doc("arm"), fam.roster_doc("smoke")

    # Request identity between the two Instruct passes: every composed key but the fit identity and prose is byte-equal.
    prose = {"live_phase_fit", "what_this_is", "cells", "purpose", "experiment_id", "generation_budget", "core_read_design"}
    i, r = cells["instruct"]["composed"].values, cells["replicate"]["composed"].values
    differing = sorted(name for name in set(i) | set(r) if name not in prose and i.get(name) != r.get(name))
    if differing:
        raise SystemExit(f"the Instruct arm and its replicate differ in composed keys {differing}: not request-identical")
    pins = None
    try:
        lock = pins_mod.UMBRELLA_LOCK_WSL if pins_mod.UMBRELLA_LOCK_WSL.exists() else pins_mod.UMBRELLA_LOCK_WIN
        pins = pins_mod.resolve_pins(lock_path=lock)
    except SystemExit as error:  # the registration is still written; the pin state is recorded as unverified
        pins = None
        pin_state = f"UNVERIFIED: {error}"
    else:
        pin_state = "VERIFIED against the umbrella lock entry (local hash receipts == lock revision text, sizes equal)"

    def block(key: str) -> dict:
        spec = cells[key]["spec"]
        if key == "smoke":
            return {"claims_benefit": False, "expected_effect_pp": 0.0, "measurement_design": "form-proof", "rows": 4,
                    "primary_metric": "none: a four-row decode-cost smoke reads no metric", "read_roster": fam.READ_ROSTER, "tuning_roster": fam.TUNING_ROSTER,
                    "note": "The four-row smoke seals and reports decode cost (tokens per answer, seconds per contact, GPU-hour projection) before the Thinking arm is queued; under instrument rule 5 four rows are a form proof by size and claim nothing."}
        base = {"claims_benefit": False, "measurement_design": "cross-flight-with-in-chain-replicate", "rows": fam.ROWS,
                "primary_metric": PRIMARY_METRIC, "replicate_run_id": run_ids[fam.REPLICATE_OF[key]],
                "read_roster": fam.READ_ROSTER, "tuning_roster": fam.TUNING_ROSTER}
        if key == "thinking":
            base.update(expected_effect_pp=fam.CROSS_FLIGHT_BAR_PP,
                        note=("Core capability, not a system claim: expected effect = the cross-flight bar (about 2.5 pp SLU-F1 at n = 1,080), the smallest delta "
                              "the cross-session design can resolve; the Thinking core is read against the mean of the two request-identical Instruct passes "
                              "of the same chain and is resolved only above that bar (owner decision 266-E: a stronger core is expected to show more than that or the line closes)."))
        else:
            base.update(expected_effect_pp=0.0,
                        note=("The Instruct arm and its request-identical replicate measure the same-core offset the Thinking delta is read against; "
                              "expected_effect_pp is 0.0 because a request-identical pair is registered to look for no effect and claims_benefit is false because the read is a capability measurement, not an admission."))
        return base

    measurement = {run_ids[key]: block(key) for key in fam.ALL_KEYS}

    def identity(entry: dict) -> dict:
        return {"cell": entry["spec"]["cell"], "role": entry["spec"]["role"], "run_id": entry["spec"]["run"], "attempt_id": entry["spec"]["attempt"],
                "fit_run_id": entry["spec"]["fit_run"], "fit_attempt_id": entry["spec"]["fit_attempt"], "fit_contact_cap": entry["fit"]["contact_cap"],
                "baseline_fragment": entry["cell"]["baseline_fragment"], "dataset_fragment": entry["cell"]["dataset_fragment"],
                "model_fragment": entry["cell"]["model_fragment"], "policy": entry["composed"].values["policy"],
                "composed_config_hash": entry["config_hash"], "protocol_hash": entry["protocol_hash"], "split_identity_hash": entry["split"],
                "rows": entry["rows"], "service_session": entry["spec"]["session"], "declares_prepared_phase_supply": "prepared_phase_supply" in entry["composed"].values}

    def arithmetic(entry: dict) -> dict:
        rows, caps = entry["rows"], entry["caps"]
        return {"expected_contacts": caps["generation_calls_cap"], "family_budget": caps,
                "derivation": [
                    f"generation_calls_cap = {rows} rows x 1 contact (phase-direct-only-v1: one phase, max_contacts 1) = {caps['generation_calls_cap']}, the exact maximum and the expectation at once",
                    f"fit_endpoint_calls_cap = 1 + (2 + 1) x {rows} = {caps['fit_endpoint_calls_cap']} (core.preparation_fit.complete_phase_endpoint_count with one phase and one media packet per row)",
                    f"repeated_speech_audio_seconds_cap = ceil({fam.roster_audio(entry['spec']['roster']):.6f} roster seconds x 1 contact) = {caps['repeated_speech_audio_seconds_cap']}",
                    f"gpu_hours_fit_inclusive = {caps['gpu_hours_fit_inclusive']}, a ceiling and never a target (Instruct direct realised 140 contacts per minute, 0.087 GPU-h per 1,000 rows; the Thinking ceiling is the all-cap-hit worst case)",
                    "native_task_contract_calls_cap = 0: the direct-only program grants no tool authority",
                    f"official_complete_scoring_jobs = {caps['official_complete_scoring_jobs']}"],
                "run_cumulative": "every cap binds across ALL attempts of this run id"}

    read_rule = {
        "kind": "PREREGISTERED; verdict words RESOLVED-ABOVE-BAR / NOT RESOLVED / HARM; development numbers only",
        "primary_metric": PRIMARY_METRIC,
        "estimand": "d = SLU-F1(Thinking) - mean(SLU-F1(Instruct), SLU-F1(Instruct replicate)), pooled micro over the resampled utterance clusters; twin offset o = SLU-F1(replicate) - SLU-F1(Instruct)",
        "bar_pp": fam.CROSS_FLIGHT_BAR_PP,
        "verdicts": {
            "RESOLVED-ABOVE-BAR": "d >= 2.5 pp AND the CI95 lower bound of d > |o| (the delta exceeds the measured same-core offset) AND the reasoning-leak count is 0",
            "HARM": "d <= -2.5 pp AND the CI95 upper bound of d < -|o|",
            "NOT RESOLVED": "every other outcome (including a Thinking arm whose cap-hit or parse-failure rate is the explanation: reported in the tables, never adjusted away)"},
        "interval": {"kind": "utterance-cluster bootstrap", "draws": fam.BOOTSTRAP_DRAWS, "seed": fam.BOOTSTRAP_SEED, "level": "CI95"},
        "tables": ["paired per-row official SLU-F1 and intent (scenario_action), Thinking vs the mean of the two Instruct passes, with saves/harms/ties",
                   "the twin offset (replicate minus Instruct) with CI95",
                   "per-scenario table (18 scenarios): n, SLU-F1 and intent for the three arms and the delta, natural-mixture and equal-scenario weightings",
                   "Thinking answer-length table (completion tokens p10/p50/p90/p99/max, cap-hit count at the cap) and parse-failure table (empty delivered content, no JSON object)",
                   "reasoning-leak guard count over the sealed delivered text of all three arms (count only; must be 0)",
                   "cost: contacts per minute, seconds per contact p50/p99, GPU hours per 1,000 rows, per arm"],
        "what_it_never_is": "a system-level claim, an admission, a superiority or generalisation claim, a test claim, or the serving core of any system cell",
    }

    facts = {
        "schema": "saea-registered-facts-v1",
        "_note": "Every model-free measured fact this registration rests on, and the CANONICAL stage3_measurement mapping (run id -> block, four cells, one package) that scripts/checks/stage3_effect_floor_check.py resolves.",
        "registered_at_utc": args.registered_at, "study_commit_at_registration": args.study_commit, "source_tree": source_tree,
        "rows": fam.ROWS, "stage3_measurement": measurement,
        "what_this_cell_is": ("The bare-core read of owner decision 266-E: the sealed direct-only form on TRAIN Fold B, Instruct (twice) and Thinking, "
                              "to test whether core capability is the binding constraint. A capability measurement: it claims no benefit and admits nothing."),
        "finite_completion_and_react_exhaustion": ("Not applicable by construction: the direct-only program carries no native_episode block, so neither "
                                                   "finite_completion_policy nor react_exhaustion_policy exists to declare (finite_completion_policy_check.py scopes native cells only). A completion "
                                                   "that reaches the cap yields a truncated or empty delivered content: a row-level outcome counted in the cap-hit and parse-failure tables, never a flight abort."),
        "roster": {"roster_id": arm_roster["roster_id"], "count": len(arm_roster["items"]), "receipt": {"relpath": fam.ROSTER["arm"], "sha256": sha256_file(fam.ROSTER["arm"])},
                   "smoke_receipt": {"relpath": fam.ROSTER["smoke"], "sha256": sha256_file(fam.ROSTER["smoke"]), "ids_are_first_four_of_arm_roster": [i["sample_id"] for i in arm_roster["items"][:4]] == [i["sample_id"] for i in smoke_roster["items"]]},
                   "split_identity_hash": arm_roster["split_identity_hash"], "smoke_split_identity_hash": smoke_roster["split_identity_hash"],
                   "audio_seconds_total": arm_roster["audio_seconds_total"], "exposure_row": SMOKE_ROSTER_ROW_ID},
        "pins": {"thinking_gguf_lock_key": pins_mod.LOCK_KEY, "state": pin_state, "serving_fragment": pins_mod.SERVING_FRAGMENT,
                 "serving_runtime_receipt": pins_mod.SERVING_RECEIPT, "preprocess_fragment": pins_mod.PREPROCESS_FRAGMENT, "preprocess_runtime_receipt": pins_mod.PREPROCESS_RECEIPT,
                 "preprocess_fragment_cpu_superseded": pins_mod.PREPROCESS_FRAGMENT_CPU, "preprocess_runtime_receipt_cpu_superseded": pins_mod.PREPROCESS_RECEIPT_CPU,
                 "packets_row_cpu_superseded": fam.CPU_PACKETS_ROW_ID, "thinking_packet_root_cpu_superseded": fam.CPU_THINK_PACKET_ROOT,
                 "note": "per-file hashes live in the umbrella lock entry and in the runtime receipts; they are not copied into prose"},
        "findings": {"mmproj_encoder_tensors_differ": MMPROJ_FINDING, "reasoning_format": REASONING_FINDING, "completion_cap": CAP_FINDING,
                     "sealed_instruct_fold_b_column": SEALED_COLUMN_FINDING, "chain_order": CHAIN_FINDING},
        "serving": {"instruct_session": fam.INSTRUCT_SESSION, "thinking_session": fam.THINK_SESSION, "thinking_serving_fragment": fam.THINK_MODEL,
                    "superseded_thinking_session": fam.SUPERSEDED_THINK_SESSION, "superseded_thinking_serving_fragment": fam.SUPERSEDED_THINK_MODEL,
                    "swap_target": "think-np4", "release_restore_checklist": CHECKLIST,
                    "thinking_packet_root": fam.THINK_PACKET_ROOT, "thinking_server_args": json.loads(rd(f"configs/model/{fam.THINK_MODEL}.json"))["server_args"]},
        "identity": {key: identity(cells[key]) for key in fam.ALL_KEYS},
        "knowledge_snapshot": {"relpath": fam.KNOWLEDGE_SNAPSHOT_RELPATH, "sha256": fam.KNOWLEDGE_SNAPSHOT_SHA256,
                               "note": "fold-excluded view (37,407 source rows; 0 Fold A and 0 Fold B ids); pinned by every 266-E baseline fragment"},
        "request_identity_proof_before_contact": {"instruct_vs_replicate_differing_composed_keys_outside_prose": differing, "none_of_them_enters_a_request": True},
        "budget_arithmetic": {key: arithmetic(cells[key]) for key in fam.ALL_KEYS},
        "read_rule": read_rule,
        "authority_relpaths": [DECISIONS, INSTRUMENT, B6_READ, "configs/baseline/slurp-direct-max512-train-fold-a-v1.json"],
        "prohibitions": [
            "No system-level, superiority, generalisation or admission claim from this read, ever; the Thinking model is admitted ONLY for this read, not as the serving core of any system cell.",
            "No reasoning text delivered, persisted (beyond hashes) or scored; preserve_wire_responses stays false on every arm.",
            "No Thinking arm before the four-row smoke has sealed and the coordinator's decode-cost sign-off marker exists.",
            "No flight on the wrong session: the Thinking cells attach only to " + fam.THINK_SESSION + ", the Instruct cells only to " + fam.INSTRUCT_SESSION + "; the chain never spawns or stops a session.",
            "No test-split contact, no confirmatory split, no paper-scale profile; no carrier outside SLURP (the carriers stay held, decision 242).",
            "No flight before root countersigns the DRAFT rows, mints the decision receipt and the cells are flipped at one commit; --allow-output-change is never passed.",
            "No number from the smoke is a task measurement."],
    }
    facts_sha = wjson(fam.package_file("registered-facts-v1.json"), facts)

    protocol = {
        "schema": "saea-registered-protocol-v1", "protocol_id": f"{pkg_name}-protocol", "registered_at_utc": args.registered_at,
        "study_commit_at_registration": args.study_commit, "source_tree": source_tree,
        "status": "REGISTERED_BEFORE_CONTACT_AWAITING_COORDINATOR_READINESS_FLIP",
        "the_question": ("With the system held out entirely, does the Thinking core move the official SLU-F1 on TRAIN Fold B by more than the cross-flight bar "
                         "(about 2.5 pp) over the Instruct core, read against a same-chain Instruct replicate? (owner decision 266-E)"),
        "one_factor": f"The core (model weights, its own speech-packet root, the completion cap {fam.THINK_MAX_TOKENS} and --reasoning-format deepseek). The request form, the direct-only program, the closed-list task instruction, the roster and its order are the same.",
        "cells": {key: identity(cells[key]) for key in fam.ALL_KEYS},
        "decision_rule_fixed_here": read_rule["verdicts"], "read_rule": read_rule,
        "findings": facts["findings"], "serving": facts["serving"],
        "failure_policy": cells["thinking"]["document"]["failure_policy"],
        "development_numbers_only": "Every number is a discovery-roster development number (owner decisions 28 and 86) and never a test claim.",
        "prohibitions": facts["prohibitions"],
        **({"recovery": {key: persisted_recovery(key, recovery_at, recovery_base)
                         for key in fam.ALL_KEYS if fam.recovery(key)}} if any(fam.recovery(k) for k in fam.ALL_KEYS) else {}),
        "authority": f"{DECISIONS} owner decision 266 (A + E, 2026-10-11) and decisions 261, 242, 28, 86; {INSTRUMENT} rules 3 and 6 and section 2d",
    }
    protocol_sha = wjson(fam.package_file("protocol-registered-v1.json"), protocol)

    def plan_document(entry: dict, kind: str) -> dict:
        generation = kind == "generation"
        spec, caps = entry["spec"], entry["caps"]
        document = {
            "schema": "saea-registered-" + kind + "-plan-v1", "plan_kind": kind, "cell": spec["cell"], "experiment": spec["cell"],
            "composed_config_hash": entry["config_hash"],
            "execution_plan": {
                "attempt_id": spec["attempt"] if generation else spec["fit_attempt"], "carrier_lock_key": "slurp", "execution_profile": "bounded-discovery-probe",
                "planned_gpu_hours": caps["gpu_hours_fit_inclusive"],
                "planned_model_calls": caps["generation_calls_cap"] if generation else caps["fit_endpoint_calls_cap"],
                "planned_speech_audio_seconds": caps["repeated_speech_audio_seconds_cap"], "protocol_hash": entry["protocol_hash"],
                "run_id": spec["run"] if generation else spec["fit_run"], "schema": "saea-execution-plan-v1", "split_identity_hash": entry["split"],
                "split_role": "discovery", "study": "speech-aware-evidence-acquisition"},
            "expected_session_id": spec["session"], "family_budget": caps, "one_factor": protocol["one_factor"],
            "preparation_base_commit": args.study_commit,
            "protocol_document": {"relpath": fam.package_file("protocol-registered-v1.json"), "sha256": protocol_sha},
            "registered_at_utc": args.registered_at, "source_tree": source_tree,
            "status": "REGISTERED_BEFORE_CONTACT_AWAITING_COORDINATOR_READINESS_FLIP", "unused_budget_is_not_attempt_authority": True}
        if fam.recovery(entry["key"]):
            document["recovery"] = persisted_recovery(entry["key"], recovery_at, recovery_base)
            if generation:
                document["recovery_budget"] = recovery_budget(entry["key"], caps)
        if generation:
            smoke = entry["key"] == "smoke"
            document["execution_route"] = (
                "The batch driver's smoke path (core.flight.lease_cli --stage worker plus core.flight.cli worker for this one cell on the resident Thinking session, "
                "then batch_inspect.py in smoke mode: 4 rows, ceiling 1 per row, notool)." if smoke else
                f"Shared core.flight.cli campaign over configs/campaign/{spec['cell']}.json on the resident {spec['core'].capitalize()} session; one official score over the complete manifest at finalize. "
                "Flown by scripts/flights/direct/batch_chain_direct_fb.sh.")
            document["purpose"] = f"{spec['run']}: the {spec['role']} of the 266-E bare-core read."
            document["quality_read_gate"] = ("None: a smoke is inspected for structure and decode cost and never read for a number." if smoke else
                                             "No read before ALL THREE arms' complete sealed manifests, exact ordered outputs and single complete official scores exist and every attempt is FINALIZED at the same flight commit. A partial manifest is never scored and never read.")
            document["scoring"] = "No score: a form smoke." if smoke else "One first complete official score after a successful seal; no partial score."
        else:
            document.update(attached_generation_run_id=spec["run"], contact_cap=entry["fit"]["contact_cap"], max_speech_packets=1,
                            execution_route="The shared live phase-fit path (core.preparation_fit.build_live_phase_fit_gate) under this cell's own live_phase_fit identity; it tokenizes request envelopes and produces no generation.",
                            purpose=f"{spec['fit_run']}: the live phase-fit spend identity of {spec['run']}.", scoring="No fit score.")
        return document

    plan_shas = {}
    for key in fam.ALL_KEYS:
        plan_shas[f"{key}-generation"] = wjson(fam.package_file(fam.plan_file_name(key, "generation")), plan_document(cells[key], "generation"))
        plan_shas[f"{key}-fit"] = wjson(fam.package_file(fam.plan_file_name(key, "fit")), plan_document(cells[key], "fit"))
        for stale in fam.superseded_plan_file_names(key):          # the failed first-attempt plans are superseded by the rec1 plans
            stale_path = REPO_ROOT / fam.package_file(stale)
            if stale_path.is_file():
                stale_path.unlink()

    recipe = {
        "schema": "saea-slurp-core-read-analysis-recipe-v1", "recipe_id": fam.RECIPE_ID,
        "title": "Cell 266-E -- the bare-core read on TRAIN Fold B, Thinking versus Instruct",
        "registered_at_utc": args.registered_at,
        "cell_kind": "cross-flight bare-core capability read with an in-chain Instruct replicate; PREREGISTERED verdict words; no admission.",
        "run_ids": {"instruct": run_ids["instruct"], "replicate": run_ids["replicate"], "thinking": run_ids["thinking"], "smoke": run_ids["smoke"], "read": fam.READ_RUN_ID},
        "roster": {"relpath": fam.ROSTER["arm"], "roster_id": arm_roster["roster_id"], "rows": fam.ROWS, "split_identity_hash": arm_roster["split_identity_hash"]},
        "arms": {key: {"run_id": run_ids[key], "attempt_id": cells[key]["spec"]["attempt"], "outputs_sha256": "PENDING_SEAL", "run_manifest_sha256": "PENDING_SEAL", "scores_sha256": "PENDING_SEAL"} for key in fam.ARM_KEYS},
        "reader": READER,
        "steps": [
            "1. Refuse unless all three arms' manifests are COMPLETED at 1,080 rows, every attempt FINALIZED, one score job each, the same study commit, and each id set equals the frozen roster's exactly.",
            "2. Request identity: Instruct vs replicate request_sha256 equal on 1,080 of 1,080 (a different count is the finding and the offset is not registered from it).",
            f"3. Paired contrast on the official per-sample counts: d = Thinking minus mean(Instruct, replicate) on pooled SLU-F1 and on intent accuracy; twin offset o = replicate minus Instruct; utterance-cluster bootstrap, {fam.BOOTSTRAP_DRAWS:,} draws, seed {fam.BOOTSTRAP_SEED}.",
            "4. Per-scenario table (scenario from the roster's stratum), natural-mixture and equal-scenario weightings.",
            "5. Thinking answer-length table (trace COST channel), cap-hit count, parse-failure table, and the reasoning-leak count over all three arms (count only).",
            "6. Cost: contacts per minute, seconds per contact p50/p99, GPU hours per 1,000 rows.",
            "7. Apply the preregistered verdict words; write the analysis root artifacts (ids, flags, scores, counts and hashes only)."],
        "interval": {"kind": "utterance-cluster bootstrap", "draws": fam.BOOTSTRAP_DRAWS, "seed": fam.BOOTSTRAP_SEED, "level": "CI95"},
        "decision_rule": read_rule["verdicts"], "bar_pp": fam.CROSS_FLIGHT_BAR_PP,
        "output": {"analysis_root": f"analysis/{fam.READ_RUN_ID}"},
        "privacy": "No utterance text, transcript, gold label, model output or reasoning text is printed or persisted; artifacts carry ids, scenario names, flags, scores, counts and hashes only.",
        "claim_boundary": "No system-level, superiority, generalisation, admission or confirmatory claim; a development-roster capability measurement of the bare core.",
        "contacts": {"model": 0, "server": 0, "encoder": 0, "tokenizer": 0, "scorer": 0, "asr": 0}}
    recipe_sha = wjson(fam.package_file("analysis-recipe-v1.json"), recipe)

    draft = {
        "_draft_note": "A DRAFT for root to mint on the data root with scripts/flights/direct/direct_fb_mint_receipt.py (status decided, recorded_at_utc stamped, antecedents re-hashed, never overwrites). It authorises nothing while its status is not 'decided'.",
        "antecedents": {name: {"path": path, "sha256": None} for name, path in (
            ("analysis_recipe", fam.package_file("analysis-recipe-v1.json")), ("derive_script", "scripts/flights/direct/direct_fb_derive_cells.py"),
            ("owner_decisions", DECISIONS), ("preregistration", fam.PREREG), ("protocol", fam.package_file("protocol-registered-v1.json")),
            ("readiness_readme", fam.package_file("README.md")), ("registered_facts", fam.package_file("registered-facts-v1.json")))},
        "authorization_basis": f"Owner decision 266-E (2026-10-11), 261, 242, 28/86; {INSTRUMENT}.",
        "budget": {key: cells[key]["caps"] for key in fam.ALL_KEYS},
        "cell_kind": "Stage-3 bare-core capability read: direct-only, TRAIN Fold B, Instruct arm + in-chain replicate + Thinking arm, and a four-row Thinking decode-cost smoke (claims_benefit false).",
        "claim_boundary": "No system-level, superiority, generalisation, held-out, confirmatory or paper-scale claim; a development-fold capability read.",
        "coordinator": "Fable5.1",
        "decision": "Fly the 266-E bare-core read: the sealed direct-only form on TRAIN Fold B on the Instruct core (twice, same chain) and on the Thinking core, after a four-row Thinking decode-cost smoke and the coordinator's sign-off.",
        "decision_id": fam.DECISION_ID, "eligible_run_ids": fam.eligible_run_ids(),
        **({"superseded_attempt_ids": [a for k in fam.ALL_KEYS if fam.recovery(k)
                                       for a in (fam.recovery(k)["predecessor_attempt_id"], fam.recovery(k)["predecessor_fit_attempt_id"])],
            "recovery_note": " ".join(f"[{fam.CELLS[k]['role']}] {fam.recovery(k)['reason']}" for k in fam.ALL_KEYS if fam.recovery(k))}
           if any(fam.recovery(k) for k in fam.ALL_KEYS) else {}),
        "failure_policy": "Stop and preserve on the first failure. AT MOST ONE root-diagnosed recovery re-registration per run id; a second failure closes the cell and the fix is proven on a four-row dry run. The budget is run-cumulative across attempts.",
        "not_authorized": ["any flight before the cells are flipped and the receipt is minted", "touching the serving geometry by anyone but the coordinator", "any ASR, transcript or paid-API contact",
                           "the Thinking packet-preparation encoder pass (its own row, lease and owner authorisation)", "persisting reasoning text or raw wire responses", "--allow-output-change on the re-pin tool",
                           "using the Thinking model as the serving core of any system cell"],
        "owner": "root",
        "population": {"count": fam.ROWS, "fold_a_contact_authorized": False, "split_identity_hash": arm_roster["split_identity_hash"], "split_role": "discovery", "test_contact_authorized": False},
        "recorded_at_utc": None,
        "registered_hashes": {key: {"composed_config": cells[key]["config_hash"], "protocol": cells[key]["protocol_hash"]} for key in fam.ALL_KEYS},
        "schema": "saea-campaign-decision-v1",
        "service": {"instruct_session": fam.INSTRUCT_SESSION, "thinking_session": fam.THINK_SESSION, "no_child_start_stop": True, "slot_tokens": 24576, "slots": 4},
        "status": "DRAFT-NOT-MINTED"}
    draft_sha = wjson(fam.package_file("root-admission-draft-v1.json"), draft)

    def spend_clause(recovered_key: str) -> str:
        calls, audio = fam.predecessor_spend(recovered_key)
        return "0 spent" if calls == 0 else f"{calls} calls and {audio:g} speech-seconds spent"

    def countersign_text(label: str, run_id: str) -> str:
        recovered = next((k for k in fam.ALL_KEYS if fam.recovery(k) and run_id in (cells[k]["spec"]["run"], cells[k]["spec"]["fit_run"])), None)
        if recovered:
            rec, spec = fam.recovery(recovered), cells[recovered]["spec"]
            return ("REGISTERED BEFORE CONTACT (root countersigned <UTC timestamp> by root flight operations on the coordinator's brief: owner decision 266-E of 2026-10-11 "
                    f"(bare-core read on TRAIN Fold B, Thinking versus Instruct); RECOVERY rec1 of the {spec['role']}, the cell's single root-diagnosed recovery re-registration: "
                    f"{label}; the predecessor attempt {rec['predecessor_attempt_id']} {rec['predecessor_state']} Root cause: {rec['root_cause']}. Re-flown whole under "
                    f"generation attempt {spec['attempt']} and FIT run {spec['fit_run']} / attempt {spec['fit_attempt']}; the plan budget is run-cumulative "
                    f"(original plan + {spend_clause(recovered)}); {rec.get('countersign_receipt_clause') or 'the decision receipt ' + fam.DECISION_RELPATH + ' is unchanged (it already lists the generation run id)'}; "
                    "the READ row stays a draft until the seal)")
        return ("REGISTERED BEFORE CONTACT (root countersigned <UTC timestamp> by root flight operations on the coordinator's brief: owner decision 266-E of 2026-10-11 "
                f"(bare-core read on TRAIN Fold B, Thinking versus Instruct); {label}; the decision receipt {fam.DECISION_RELPATH} is minted by "
                "scripts/flights/direct/direct_fb_mint_receipt.py after this countersignature; the READ row stays a draft until the seal)")

    countersign = {
        "schema": "saea-countersign-row-texts-v1",
        "_note": "Replace the leading 'REGISTERED (DRAFT, root countersignature pending)' of each row's notes with the text below (keep the rest of the row unchanged), then mint the receipt.",
        "decision_receipt": fam.DECISION_RELPATH, "decision_id": fam.DECISION_ID,
        "rows": {run_id: countersign_text(label, run_id) for run_id, label in (
            [(run_ids[k], cells[k]["spec"]["role"]) for k in fam.ALL_KEYS] + [(fit_ids[k], "live phase-fit identity of the " + cells[k]["spec"]["role"]) for k in fam.ALL_KEYS])},
        "rows_that_stay_draft": [fam.READ_RUN_ID, fam.SERVING_ROW_ID, fam.PACKETS_ROW_ID],
        "separate_authorisations": {fam.SERVING_ROW_ID: "countersign when the swap is scheduled (the first Thinking weight load)", fam.PACKETS_ROW_ID: "its own root lease, owner authorisation and driver variant"}}
    countersign_sha = wjson(fam.package_file("countersign-row-texts-v1.json"), countersign)

    # ---- README and preregistration ------------------------------------
    table_rows = "\n".join(
        f"| {cells[k]['spec']['role']} | `{run_ids[k]}` | `{cells[k]['spec']['attempt']}` | `{fit_ids[k]}` ({cells[k]['fit']['contact_cap']}) | {cells[k]['rows']} | `{cells[k]['config_hash']}` | `{cells[k]['protocol_hash']}` |"
        for k in fam.ALL_KEYS)
    checklist_md = "\n".join(f"{item}" for item in CHECKLIST)
    readme = f"""# Cell 266-E: the bare-core read on TRAIN Fold B, Thinking versus Instruct

Registered before contact {args.registered_at[:10]} at study commit `{args.study_commit}`; all four cells are **held**. Nothing here authorises a
flight, a flip, a serving swap or an admission entry.

**The question (owner decision 266-E).** The 265 coverage pre-read left the supply side of SLURP SLU at its plateau; the remaining mass is values TRAIN
never shows and values already supplied and not used, both core-side. Is the CORE, not the system, the binding constraint? The system is core-agnostic
by design, so a stronger core transfers every locked component. This read holds the system out entirely: the sealed direct-only form
(`phase-direct-only-v1`, the shared controller, `FlightRuntime`, OpenJiuwen, the `slurp-direct-max512` task instruction) flies on TRAIN Fold B 1,080 on
the Instruct core and on the Thinking core. The Thinking model is admitted ONLY for this read, never as the serving core of a system cell.

**The cells.**

| cell | run id | attempt | fit run id (contact cap) | rows | composed config | protocol |
| --- | --- | --- | --- | ---: | --- | --- |
{table_rows}

**Cross-session by necessity.** The 24 GB card holds one core, so Thinking and Instruct cannot share a flight. The Instruct arm therefore flies twice
(arm and request-identical replicate, one chain, one session) and the Thinking delta is read against the mean of the two at the cross-flight bar (about 2.5 pp
at n = 1,080; instrument note section 2d); `stage3_measurement` is `cross-flight-with-in-chain-replicate` on every arm, `claims_benefit` false, `stage3_algorithm`
`none`. The smoke is `form-proof`. {SEALED_COLUMN_FINDING}

**Finding 1: the Instruct speech packets are not valid for the Thinking core.** {MMPROJ_FINDING}

**Finding 2: reasoning stays out of `content`.** {REASONING_FINDING}

**Finding 3: the completion cap.** {CAP_FINDING}

**Chain.** {CHAIN_FINDING}  The Thinking arm segment refuses until the coordinator's decode-cost sign-off marker `{fam.SIGNOFF_MARKER}` exists.

**Pins.** `{pin_state}`. Per-file hashes are carried by `{pins_mod.SERVING_RECEIPT}` (main GGUF, as the Instruct receipt does) and `{pins_mod.PREPROCESS_RECEIPT}`
(main + mmproj) and live in the umbrella lock entry `{pins_mod.LOCK_KEY}`; `scripts/flights/direct/direct_fb_pins.py` refuses to write a fragment if a local
hash is absent or differs from the lock.

## Serving release and restore checklist (the coordinator's; nothing here executes it)

{checklist_md}

{PACKETS_RUNBOOK}## Prerequisites still open

1. **Thinking speech packets (P0).** Prepare the Thinking packet root over TRAIN Fold B and pin its promotion receipt in the two Thinking baselines (zero sentinel today); the receipt's `feature_root` must equal the fragment's `speech_feature_root` (the runtime refuses a disagreement) and cover all 1,080 Fold B rows (the smoke's four are among them). The driver variant exists (`scripts/slurp_fold_preprocess_thinking.py`) and the chain `scripts/flights/direct/direct_fb_packets_gpu.sh` runs it inside a serving-swap window; ledger row `{fam.PACKETS_ROW_ID}` is still a DRAFT that needs its root countersignature and owner authorisation (the CPU sidecar row `{fam.CPU_PACKETS_ROW_ID}` is superseded). See the section above.
2. **Task registration.** `SAEA-Serving-THINK` / `SAEA-Monitor-THINK` are registered by the first `serving_swap.sh think-np4` through `saea_task.ps1`.
3. **Countersignatures and the receipt.** `countersign-row-texts-v1.json`; then `scripts/flights/direct/direct_fb_mint_receipt.py`, then `direct_fb_flip.sh`.

| file | what it holds |
| --- | --- |
| `../{fam.DATE}-{pkg_name}-preregistration.md` | the preregistration proper, with the `stage3_measurement` fence and the read rules |
| `registered-facts-v1.json` | every model-free fact, the findings, the checklist, the CANONICAL `stage3_measurement` |
| `protocol-registered-v1.json` | the protocol document every plan pins |
| `*-generation-plan-registered-v1.json`, `*-fit-plan-registered-v1.json` | the eight registered plans (smoke, thinking, instruct, replicate) |
| `analysis-recipe-v1.json` | the read recipe, declaring the READ run id `{fam.READ_RUN_ID}` |
| `root-admission-draft-v1.json` | the draft decision receipt (eight eligible run ids) |
| `countersign-row-texts-v1.json` | the row texts root writes when countersigning |
"""
    recovery_md = "".join(recovery_section(k, cells[k]["spec"], cells[k]["caps"]) for k in fam.ALL_KEYS if fam.recovery(k))
    readme_sha = wr(fam.package_file("README.md"), readme + recovery_md)

    prereg = f"""# Preregistration -- cell 266-E: the bare-core read on TRAIN Fold B, Thinking versus Instruct

Registered {args.registered_at[:10]} before any contact, at study commit `{args.study_commit}`. Owner decision 266-E. Package `{pkg}/`.

## 1. Question and design

Does the Thinking core move the official SLU-F1 on TRAIN Fold B (1,080 rows, discovery role) by more than the cross-flight bar (about 2.5 pp) over the
Instruct core, with the system held out entirely? Same form on both cores (direct-only program, closed-list instruction, same roster and order); the only
differences are the core, its own packet root, the completion cap {fam.THINK_MAX_TOKENS} and `--reasoning-format deepseek`. Cross-session by necessity, so the Instruct arm
flies twice in the chain and the Thinking delta is read against the mean of the two. All numbers are development numbers (owner decisions 28 and 86).

## 2. Measurement declaration

```json
{json.dumps({"stage3_measurement": measurement}, indent=2, sort_keys=True)}
```

## 3. Read rules (fixed here, before contact)

* **Estimand.** `d` = SLU-F1(Thinking) minus the mean of SLU-F1(Instruct) and SLU-F1(Instruct replicate), each pooled micro over the resampled utterance
  clusters (official evaluate.py per-sample counts, scorer `slurp-slu-official-train`); the same on intent accuracy (`scenario_action` exact, per-row mean). The
  twin offset `o` = replicate minus Instruct, with its CI95.
* **Interval.** Utterance-cluster bootstrap, {fam.BOOTSTRAP_DRAWS:,} draws, seed {fam.BOOTSTRAP_SEED}, CI95; saves / harms / ties on the per-row metrics.
* **Verdict words.**
  * `RESOLVED-ABOVE-BAR`: `d >= 2.5` pp AND the CI95 lower bound of `d` is greater than `|o|` AND the reasoning-leak count is 0.
  * `HARM`: `d <= -2.5` pp AND the CI95 upper bound of `d` is below `-|o|`.
  * `NOT RESOLVED`: every other outcome. A cap-hit or parse-failure explanation is reported in the tables and never adjusted away.
  If the verdict is `NOT RESOLVED` or `HARM`, the Thinking-core line closes (owner decision 266-E).
* **Tables.** Paired per-row official SLU-F1 and intent; the twin offset; the per-scenario table (18 scenarios from the roster's stratum; natural-mixture and
  equal-scenario weightings); the Thinking answer-length table (completion tokens p10/p50/p90/p99/max, cap-hit count) and parse-failure table (empty delivered
  content; no JSON object); the reasoning-leak guard count over all three arms (count only); cost (contacts per minute, seconds per contact p50/p99, GPU hours per 1,000 rows).
* **Privacy.** No utterance text, transcript, gold label, model output or reasoning text is printed or persisted.

## 4. Stop rules

A response whose delivered content carries a reasoning marker stops the flight (`reasoning_content_guard`). The Thinking arm does not open before the
smoke has sealed and `{fam.SIGNOFF_MARKER}` exists. At most one root-diagnosed recovery re-registration per run id; a second failure closes the cell.

## 5. Findings recorded before contact

{MMPROJ_FINDING}

{REASONING_FINDING}

{CAP_FINDING}

{SEALED_COLUMN_FINDING}

## 6. Claim boundary

No system-level, superiority, generalisation, component-causal, admission, held-out, confirmatory or paper-scale claim. The Thinking model is admitted for
this read only. Nothing here authorises a flight, a readiness flip or a serving swap.
"""
    prereg_sha = wr(fam.PREREG, prereg + recovery_md)

    # ---- ledger block -----------------------------------------------------
    ledger_state = "not appended"
    if args.append_ledger:
        text = rd(LEDGER)
        if fam.LEDGER_MARK in text:
            ledger_state = "already present"
        else:
            def notes_common(extra: str) -> str:
                return (f"REGISTERED (DRAFT, root countersignature pending) {args.registered_at[:10]} at study commit {args.study_commit} by the 266-E registration agent "
                        f"(worktree {args.worktree}, branch {args.branch}); owner decision 266-E. {extra} HELD: this registration performs no contact and authorises none.")

            def row(run_id, profile, scope, model_tool, carrier, split_hash, calls, audio, gpu, artifact, notes, consumed="no") -> str:
                return " | ".join(["", args.registered_at, run_id, profile, scope, model_tool, carrier, "discovery", split_hash, consumed, str(calls), str(audio), str(gpu),
                                   INHERITED, artifact, notes, ""]).strip()

            think_tool = (f"Frozen Qwen3-Omni-30B-A3B-Thinking Q4_K_M ({pins_mod.LOCK_KEY}), decoder-only build 04ccc72a, c98304 np4 x 24,576 max{fam.THINK_MAX_TOKENS}, q8_0 KV, "
                          f"--reasoning-format deepseek ({fam.THINK_MODEL}); its own promoted speech packets; direct-only phase program; no tool authority")
            inst_tool = (f"Frozen Q4_K_M decoder-only build 04ccc72a, c98304 np4 x 24,576 max512 ({fam.INSTRUCT_MODEL}); promoted EVO-FOLDS-V2 speech packets; "
                         "direct-only phase program; no tool authority")
            rows = [
                row(SMOKE_ROSTER_ROW_ID, "model-free-check", "Freeze the four-row decode-cost smoke roster of the 266-E read: the first four rows of SLURP-EVO-FOLD-B-V2 in roster order. Zero model, server, encoder, tokenizer, scorer, network, GPU and paid-API contacts.",
                    "no model or tool contact; roster items copied from the committed Fold B roster receipt", "slurp TRAIN Fold B 4", smoke_roster["split_identity_hash"], 0, 0, 0, fam.ROSTER["smoke"],
                    notes_common(f"Receipt {fam.ROSTER['smoke']} SHA256 {sha256_file(fam.ROSTER['smoke'])}; built by scripts/flights/direct/direct_fb_derive_cells.py. Admits nothing.")),
                row(fam.SERVING_ROW_ID, "bounded-discovery-probe", "The serving contact of the 266-E read: the Thinking session start (the first Thinking weight load) after the Instruct session is released under the serving-entry protocol (serving_swap.sh think-np4); no answering contact.",
                    think_tool, "slurp TRAIN Fold B (no rows)", arm_roster["split_identity_hash"], 0, 0, 0.3, fam.package_file("registered-facts-v1.json"),
                    notes_common("Session " + fam.THINK_SESSION + "; the release/restore checklist is in the package README; the uptime guard is told with watchdog.hold. Countersigned separately when the swap is scheduled.")),
                row(fam.CPU_PACKETS_ROW_ID, "bounded-discovery-probe", "The ENCODE preparation of the Thinking speech-packet root over TRAIN Fold B (1,080 rows): a CPU sidecar encoder pass at max_tokens 1 and the model-free promotion, because the Instruct packets are not valid for the Thinking decoder (748 of 860 mmproj tensors differ).",
                    f"Frozen Thinking Q4_K_M decoder and its own bf16 mmproj on a CPU sidecar (-ngl 0 --no-mmproj-offload) ({pins_mod.PREPROCESS_FRAGMENT_CPU}); no answer is read", "slurp TRAIN Fold B 1,080",
                    arm_roster["split_identity_hash"], fam.ROWS, fam.audio_cap("arm"), 0.0, fam.package_file("registered-facts-v1.json"),
                    notes_common("Needs its own driver variant (scripts/slurp_evo_fold_preprocess.py is wired to the Instruct root), root lease and owner authorisation; a placeholder row, not countersigned with the arms.")),
            ]
            for key in fam.ALL_KEYS:
                entry, spec, caps = cells[key], cells[key]["spec"], cells[key]["caps"]
                tool = think_tool if spec["core"] == "thinking" else inst_tool
                carrier = "slurp TRAIN Fold B " + ("4" if key == "smoke" else "1,080")
                scope = (f"Cell 266-E {spec['role']}: the sealed direct-only form on TRAIN Fold B on the {spec['core']} core; a capability read, no mechanism, no claim."
                         if key != "smoke" else "Cell 266-E four-row Thinking decode-cost smoke on the first four Fold B rows; no score, no read.")
                rows.append(row(spec["run"], "bounded-discovery-probe", scope, tool, carrier, entry["split"], caps["generation_calls_cap"], caps["repeated_speech_audio_seconds_cap"],
                                caps["gpu_hours_fit_inclusive"], fam.package_file(f"{key}-generation-plan-registered-v1.json"),
                                notes_common(f"Composed config {entry['config_hash']}, protocol {entry['protocol_hash']} (the re-pin tool rewrites both at the flip). Measurement declaration: "
                                             f"{measurement[spec['run']]['measurement_design']}, expected_effect_pp {measurement[spec['run']]['expected_effect_pp']}, claims_benefit false. Expected session {spec['session']}.")))
                rows.append(row(spec["fit_run"], "bounded-discovery-probe", f"Cell 266-E {spec['role']} -- live phase-fit spend identity, request envelopes only, no generation.", tool, carrier, entry["split"],
                                caps["fit_endpoint_calls_cap"], caps["repeated_speech_audio_seconds_cap"], caps["gpu_hours_fit_inclusive"], fam.package_file(f"{key}-fit-plan-registered-v1.json"),
                                notes_common(f"The FIT row of {spec['run']}; quotes no hash of its own so nothing here can go stale; speech seconds and GPU hours are the generation row's ceilings, shared and not additive.")))
            rows.append(row(fam.READ_RUN_ID, "model-free-check", "The preregistered model-free read of the 266-E bare-core read: paired contrasts, twin offset, per-scenario and Thinking answer-length / parse-failure / leak tables from the sealed outputs. Zero contacts.",
                            "no model or tool contact; sealed outputs, traces and scores read-only", "slurp TRAIN Fold B 1,080", arm_roster["split_identity_hash"], 0, 0, 0, fam.package_file("analysis-recipe-v1.json"),
                            notes_common(f"Reader {READER}; stays a draft until the seal and is countersigned before any number is read.")))
            for line in rows:
                if line.count("\n") or line.count("|") != 16:
                    raise SystemExit(f"a ledger row is malformed ({line.count('|')} pipes)")
            header = (f"\n{fam.LEDGER_MARK} (DRAFT, root countersignature pending)\n\n"
                      f"Twelve unconsumed rows -- the smoke roster, the Thinking serving contact, the Thinking packet preparation, four generation rows, their four live-phase-fit "
                      f"identities and the READ row -- for the bare-core read of owner decision 266-E. Package {pkg}. No row is countersigned and no row authorises a contact.\n\n"
                      "| date | run/experiment id | execution profile | scope | model/tool | speech carrier + split | split role | split identity hash | consumed | calls | speech audio seconds | gpu hours | inherited exposure | artifacts | notes |\n"
                      "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n")
            suffix = "" if text.endswith("\n") else "\n"
            wr(LEDGER, text + suffix + header + "\n".join(rows) + "\n")
            ledger_state = f"appended {len(rows)} rows"

    if args.append_recovery_ledger:
        text = rd(LEDGER)
        # idempotent PER recovered cell: a cell whose rec1 generation attempt id already appears in the ledger is skipped
        missing = [k for k in fam.ALL_KEYS if fam.recovery(k) and cells[k]["spec"]["attempt"] not in text]
        if not missing:
            ledger_state += "; recovery rows already present"
        else:
            blocks = "".join(recovery_ledger_block(k, cells[k], recovery_at, recovery_base, args.recovery_worktree, args.recovery_branch, plan_shas) for k in missing)
            wr(LEDGER, text + ("" if text.endswith("\n") else "\n") + blocks)
            ledger_state += f"; appended {2 * len(missing)} recovery rows ({', '.join(missing)})"

    print(json.dumps({"package": pkg, "ledger": ledger_state, "pin_state": pin_state, "written": {
        "README.md": readme_sha, "analysis-recipe-v1.json": recipe_sha, "protocol-registered-v1.json": protocol_sha, "registered-facts-v1.json": facts_sha,
        "root-admission-draft-v1.json": draft_sha, "countersign-row-texts-v1.json": countersign_sha, "preregistration": prereg_sha, **plan_shas},
        "identity": {key: {"config": cells[key]["config_hash"][:12], "protocol": cells[key]["protocol_hash"][:12]} for key in fam.ALL_KEYS}}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
