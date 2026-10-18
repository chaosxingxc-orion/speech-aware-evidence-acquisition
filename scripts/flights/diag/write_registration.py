#!/usr/bin/env python3
"""write_registration.py -- emit the registration files of the Solver reasoning diagnostic package from its roster (model-free, deterministic).

    python -B scripts/flights/diag/write_registration.py [--root DIR]

Reads ``<package>/roster-v1.json`` and writes, in dependency order, ``protocol-v1.json`` (pins the roster's sha256), ``execution-plan-v1.json`` (its ``protocol_hash`` is
the protocol file's sha256), ``draft-ledger-rows.md`` (two DRAFT exposure-ledger rows, root countersignature pending) and ``README.md``. Nothing is registered on master, no
ledger row is countersigned and no contact is authorised by running this.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import solver_reasoning_diag as diag  # noqa: E402

DATE = "2026-10-18"
ATTEMPT_ID = "attempt-slurp-solver-reasoning-diagnostic-v1"
OWNER_RULINGS = "owner rulings 329 A and 330 A (2026-10-18, the R2b READ section of docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md)"
MODEL = ("Frozen Qwen3-Omni-30B-A3B-Thinking Q4_K_M (qwen3-omni-30b-a3b-thinking-gguf-q4km), decoder-only build 04ccc72a, c98304 np4 x 24,576 geometry (resident session "
         "serving-slurp-thinking-module-fold-b-np4-budget3072-max4096-v1, swap target think-budget-np4: reasoning budget 3072, cap 4096), q8_0 KV, --reasoning-format deepseek; "
         "its own promoted speech packets; the sealed NX-T R2b budget-3072 Solver requests (and, for the forced-both rows, the sealed budget-6144 / max_tokens 7168 requests) "
         "re-sent unchanged; no tool authority")
INHERITED = "TRAIN Fold B discovery rows already exposed by prior SLURP cells; this probe opens no split. Prior exposure is inherited in full."
LEDGER_HEADER = ("| date | run/experiment id | execution profile | scope | model/tool | speech carrier + split | split role | split identity hash | consumed | calls | "
                 "speech audio seconds | gpu hours | inherited exposure | artifacts | notes |\n"
                 "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n")


def sha(path: Path) -> str:
    return diag.file_sha256(path)


def build(root: Path) -> dict[str, str]:
    package = root / diag.PACKAGE
    roster_path = package / diag.ROSTER_NAME
    roster = json.loads(roster_path.read_text(encoding="utf-8"))
    rows = roster["rows"]
    audio = sum(float(r["reissue"]["audio_seconds"]) for r in rows)
    worst = max(float(r["reissue"]["audio_seconds"]) for r in rows)
    audio_ceiling = int(math.ceil(diag.CALL_CEILING * worst / 10.0) * 10)
    counts = roster["selected_counts"]
    raised_n = counts["forced-both"]
    contacts_n = len(rows) + raised_n
    audio_raised = sum(float(r["raised_arm_request"]["audio_seconds"]) for r in rows if r["group"] == "forced-both")
    # Expected decode volume from the sealed completion tokens of the roster rows (both arms' sealed numbers) at the np4 aggregate rate measured in R2b.
    tokens_3072 = sum(int(r["sealed"][diag.ARM_DELIVERING]["completion_tokens"]) for r in rows)
    tokens_6144 = sum(int(r["sealed"][diag.ARM_RAISED]["completion_tokens"]) for r in rows if r["group"] == "forced-both")
    protocol = {
        "schema": "saea-solver-reasoning-diag-protocol-v1", "run_id": diag.RUN_ID, "read_run_id": diag.READ_RUN_ID, "registered_at_utc": f"{DATE}T00:00:00Z",
        "authority": {
            "owner_rulings": OWNER_RULINGS,
            "owner_words_english": "Decision 329: A. Decision 330: A. (Decision 330 A: a bounded diagnostic exception to ruling 286 -- one small registered probe re-issues the "
                                   "sealed Solver requests of about 40 R2b rows, forced and natural, both budgets, with the reasoning bytes RETAINED under the data root only, to "
                                   "classify the non-terminating reasoning as enumeration or a repetition loop; 286 stays in force for every other cell.)",
            "exception_to": "owner ruling 286 (reasoning bytes are projected out at the transport on every path; policy hash-and-stats-only-v1)",
        },
        "question": ("Is the Solver reasoning that fails to terminate at the 3,072-token budget an ENUMERATION (the model verifies every supplied item and candidate intent "
                     "once or twice, in supply order, with no stopping rule) or a REPETITION LOOP (a small block restated over and over)?"),
        "source": roster["source"],
        "roster": {"file": diag.ROSTER_NAME, "seed": roster["seed"], "rows": len(rows), "counts": counts, "selection_rule": roster["selection_rule"]},
        "roster_sha256": sha(roster_path),
        "reissue": {
            "arm": diag.ARM_DELIVERING,
            "what": ("the sealed Solver MODEL_REQUEST payload of each roster row's budget-3072 first-visit contact (40 contacts) and, for the forced-both rows, of the "
                     "solver-6144 contact (16 contacts), rebuilt from the sealed trace and sent through the registered llama-server transport unchanged (decoding: "
                     "temperature 0, seed 20260913, the sealed id_slot; thinking_budget_tokens 3072 / max_tokens 4096 for the first 40, 6144 / 7168 for the last 16)"),
            "reconstruction_proof": ("sha256 of the adapter's canonical serialisation of the sealed payload equals the sealed payload_sha256 and the first-visit request_sha256; "
                                     "verified offline for all 56 contacts by `solver_reasoning_diag.py verify` (and the exact wire body rendered by the transport's own renderer)"),
            "workers": ("one sequential worker per sealed id_slot, so every sent payload is the sealed payload byte for byte; within a slot the budget-3072 requests "
                        "come first and the budget-6144 requests after them"),
            "raised_arm_requests": ("RE-ISSUED (coordinator decision 2, ruling 330 A 'both budgets'): the solver-6144 requests of the 16 forced-both rows. The resident np4 "
                                    "server admits them (max_tokens is a request parameter; no -n cap in the server arguments). Retained as <sample>.b6144.txt."),
            "reproduction_caveat": "np4 batching is not deterministic: the re-issued reasoning may differ from the sealed one; the hash match or mismatch is recorded per row.",
        },
        "retention": {
            "policy": "retain-diagnostic-v1",
            "directory": f"<data root>/diagnostics/{diag.RUN_ID}/reasoning/<sample>.txt",
            "mechanism": ("core.reasoning_knobs.ReasoningRetention, buildable only from a plan whose run id is the diagnostic run id and whose profile is bounded-discovery-probe; "
                          "an explicit constructor argument of the transport, never a model-fragment key; the stored wire message, the envelope reasoning object and every trace "
                          "record remain the decision-286 projection"),
            "hash_check": "sha256 of the retained bytes versus the sealed reasoning_content_sha256: match or mismatch recorded per row (results.jsonl)",
            "text_policy": "reasoning text never enters a document, a note, a commit, a ledger row or a chat transcript; only counts and pattern statistics do",
        },
        "read": {"script": "scripts/analysis/solver_reasoning_diag_read.py", "prints": "statistics only (no sentence, no quote)", "groups": list(counts) + ["forced-both@6144"],
                 "pairs": "forced-both rows: the 3072 reasoning against the 6144 reasoning of the same row (common prefix up to the forced close, repeat onset offsets)"},
        "stop_rules": ["the first failure stops every worker; nothing is retried", "one attempt: an existing diagnostic directory refuses the launch",
                       "the call ceiling is a hard stop", "a flight lock, a flight process or a resident session other than think-budget-np4 refuses the launch"],
        "claims_benefit": False,
        "non_claims": "A diagnostic of reasoning shape on TRAIN Fold B development rows. It claims no score, no benefit and no change to the lock.",
    }
    protocol_text = json.dumps(protocol, indent=2, sort_keys=True) + "\n"
    (package / diag.PROTOCOL_NAME).write_bytes(protocol_text.encode("utf-8"))
    plan = {
        "schema": "saea-registered-diagnostic-plan-v1", "plan_kind": "generation", "registered_at_utc": f"{DATE}T00:00:00Z",
        "execution_plan": {
            "run_id": diag.RUN_ID, "execution_profile": "bounded-discovery-probe", "carrier_lock_key": "slurp", "split_role": "discovery",
            "split_identity_hash": diag.SPLIT_IDENTITY_HASH, "planned_model_calls": diag.CALL_CEILING, "planned_gpu_hours": diag.GPU_HOURS_CEILING,
            "planned_speech_audio_seconds": audio_ceiling, "protocol_hash": sha(package / diag.PROTOCOL_NAME), "attempt_id": ATTEMPT_ID,
            "schema": "saea-execution-plan-v1", "study": "speech-aware-evidence-acquisition",
        },
        "protocol_document": {"relpath": f"{diag.PACKAGE}/{diag.PROTOCOL_NAME}", "sha256": sha(package / diag.PROTOCOL_NAME)},
        "roster": {"relpath": f"{diag.PACKAGE}/{diag.ROSTER_NAME}", "sha256": sha(roster_path), "rows": len(rows)},
        "budget": {"re_issues": contacts_n, "re_issues_budget_3072": len(rows), "re_issues_budget_6144": raised_n, "call_ceiling": diag.CALL_CEILING,
                   "gpu_hours_ceiling": diag.GPU_HOURS_CEILING,
                   "gpu_hours_basis": (f"sealed completion tokens of the roster contacts: {tokens_3072} (40 x budget 3072) + {tokens_6144} (16 x budget 6144) = "
                                       f"{tokens_3072 + tokens_6144} tokens; at 100 tokens per second aggregate on np4 that is about "
                                       f"{round((tokens_3072 + tokens_6144) / 100 / 3600, 2)} h of decode, ceiling 0.9 h with a 40 percent allowance for prefill and tail imbalance"),
                   "roster_audio_seconds": round(audio + audio_raised, 3), "audio_ceiling_basis": f"{diag.CALL_CEILING} calls x the longest roster utterance ({worst} s), rounded up to 10",
                   "ceilings_are_not_targets": True},
        "expected_session_id": diag.EXPECTED_SESSION_ID, "launcher": "scripts/flights/diag/solver_reasoning_diag.sh",
        "needs": ["root countersignature of the two draft ledger rows (the gate refuses a model touch without the pre-registered row)",
                  "no flight lock and no flight process", "the resident serving session is think-budget-np4 (after the R2 rec2 flight seals)"],
    }
    (package / diag.PLAN_NAME).write_bytes((json.dumps(plan, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    probe_scope = (f"DRAFT -- REGISTERED. Solver reasoning diagnostic (owner ruling 330 A): {len(rows)} sealed budget-3072 Solver requests of the sealed NX-T R2b column plus the "
                   f"{raised_n} sealed budget-6144 requests of its forced-both rows ({contacts_n} contacts) re-sent "
                   f"to the resident Thinking server with the reasoning bytes RETAINED under the data root only ({counts['forced-both']} forced at both budgets, "
                   f"{counts['forced-3072-only']} forced at 3072 only, {counts['forced-6144-only']} forced at 6144 only, {counts['natural-both']} natural at both), to classify the "
                   f"non-terminating reasoning as enumeration or repetition loop. Bounded exception to ruling 286; bytes never leave the data root")
    probe = (f"| {DATE} | {diag.RUN_ID} | bounded-discovery-probe | {probe_scope} | {MODEL} | slurp TRAIN Fold B {len(rows)} of 1080 | discovery | "
             f"{diag.SPLIT_IDENTITY_HASH} | no | {diag.CALL_CEILING} | {audio_ceiling} | {diag.GPU_HOURS_CEILING} | {INHERITED} | "
             f"{diag.PACKAGE}/{diag.PLAN_NAME} | DRAFT. REGISTERED WITH THE PACKAGE (root countersignature pending). {contacts_n} re-issues ({len(rows)} + {raised_n}), ceiling {diag.CALL_CEILING}; one attempt; "
             f"launched by scripts/flights/diag/solver_reasoning_diag.sh after the R2 rec2 flight seals and before R3. Claims no benefit. |")
    read = (f"| {DATE} | {diag.READ_RUN_ID} | model-free-check | The offline read of the Solver reasoning diagnostic: per-row and per-group reasoning statistics (characters, "
            f"approximate tokens, compression ratio, repeated-sentence share, longest repeated block, first-repeat position, enumeration signal, answer-after-restatement) by "
            f"scripts/analysis/solver_reasoning_diag_read.py. Prints statistics only. Zero model, server, encoder, embedder, tokenizer and GPU contacts. | no model or tool contact; "
            f"read of the retained diagnostic bytes on the data root | slurp TRAIN Fold B {len(rows)} of 1080, the sealed diagnostic run (after the probe) | discovery | "
            f"{diag.SPLIT_IDENTITY_HASH} | no | 0 | 0 | 0 | {INHERITED} | {diag.PACKAGE}/{diag.PROTOCOL_NAME} | DRAFT. REGISTERED WITH THE PACKAGE (root countersignature pending; "
            f"countersigned after the probe is sealed and before any statistic is read). Claims no benefit. |")
    ledger = (f"## Cell SOLVER-REASONING-DIAGNOSTIC: the bounded reasoning-retention probe on the sealed NX-T R2b Solver requests (DRAFT, root countersignature pending)\n\n"
              f"2 unconsumed rows -- the probe and its READ row -- for the diagnostic of {OWNER_RULINGS}. Package {diag.PACKAGE}. No row is countersigned and no row "
              f"authorises a contact. No serving row: the probe attaches to the resident think-budget-np4 session and starts nothing.\n\n"
              f"{LEDGER_HEADER}{probe}\n{read}\n")
    (package / "draft-ledger-rows.md").write_bytes(ledger.encode("utf-8"))
    readme = f"""# Solver reasoning diagnostic (DRAFT / HELD)

Status: DRAFT / HELD. No exposure-ledger row is countersigned, nothing is registered on master, flipped or flown, and no session is started. Generated by
`scripts/flights/diag/write_registration.py` from `roster-v1.json`.

## The question (owner rulings 329 A and 330 A)

NX-T R2b read the Solver `NEEDS-NO-MORE-BUDGET`: raising the Solver's reasoning budget from 3,072 to 6,144 tokens did not help, and 66 % of the rows forced to close at 3,072
are still forced at 6,144. The coordinator's root-cause reading is "exhaustive verification over every candidate intent and supplied item with no stopping rule". This probe
looks at the reasoning itself, once, to tell an ENUMERATION (each supplied item and candidate walked through, a few mentions each) from a REPETITION LOOP (a small block
restated over and over). Ruling 330 A is a bounded exception to decision 286 for exactly this probe; 286 stays in force for every other cell.

## What flies

{len(rows)} sealed budget-3072 Solver requests of the sealed R2b column (run `{diag.SOURCE_RUN_ID}`, attempt `{diag.SOURCE_ATTEMPT_ID}`), re-sent unchanged to the resident
`think-budget-np4` session (budget 3,072 / cap 4,096, temperature 0, seed 20260913), followed by the {raised_n} sealed solver-6144 requests (budget 6,144 / max_tokens 7,168) of the
forced-both rows: {contacts_n} contacts, ceiling {diag.CALL_CEILING}. The reasoning bytes are written under
`<data root>/diagnostics/{diag.RUN_ID}/reasoning/<sample>.txt` (`<sample>.b6144.txt` for the 6,144 requests) and nowhere else; the stored wire message and every trace record keep
the decision-286 projection.

| group | rows | meaning |
| --- | ---: | --- |
| `forced-both` | {counts['forced-both']} | forced close at 3,072 and at 6,144 |
| `forced-3072-only` | {counts['forced-3072-only']} | forced at 3,072, natural at 6,144 |
| `forced-6144-only` | {counts['forced-6144-only']} | natural at 3,072, forced at 6,144 |
| `natural-both` | {counts['natural-both']} | natural at both budgets |

Each group is stratified by supplied-item bin (< 40 / >= 40 items) and empty versus non-empty gold, with the fixed seed {roster['seed']} (rank = sha256(seed|group|sample)).
The read compares, on the forced-both rows, the 3,072 reasoning with the 6,144 reasoning of the same row (identical prefix up to the forced close? where does the repeat begin?).

## Request reconstruction

The sealed trace holds each request payload and its `payload_sha256`; the adapter's own canonical serialisation of the payload hashes to it. `solver_reasoning_diag.py verify`
re-reads the trace for the {contacts_n} contacts, proves every rebuilt request hashes to the sealed `payload_sha256` and to the first-visit `request_sha256`, and (with
`--render`) renders the exact wire body through the transport's own `render_request` over the sealed session receipt (composed config hash equals the sealed one). All rows pass.

## Files

| file | role |
| --- | --- |
| `roster-v1.json` | the preregistered roster (sample ids, groups, strata, sealed request and reasoning hashes; no text) |
| `protocol-v1.json` | the protocol; pins the roster sha256 |
| `execution-plan-v1.json` | the structured ExecutionPlan (bounded-discovery-probe, {diag.CALL_CEILING} calls, < 1 GPU-h); `protocol_hash` is the protocol file's sha256 |
| `draft-ledger-rows.md` | the probe row and the model-free READ row, DRAFT, root countersignature pending |

Code: `scripts/flights/diag/solver_reasoning_diag.py` (select / verify / run), `scripts/flights/diag/solver_reasoning_diag.sh` (the one-command launcher),
`scripts/analysis/solver_reasoning_diag_read.py` (statistics-only read), `core/reasoning_knobs.py` `ReasoningRetention` and the transport's `reasoning_bytes_policy` argument.

## Decisions for the coordinator

1. Countersign the two ledger rows (`draft-ledger-rows.md`) before the launch; the gate refuses a model touch without the pre-registered row.
2. (Settled by coordinator decision 2: the {raised_n} solver-6144 requests are in the plan, ceiling {diag.CALL_CEILING}.)
3. Launch window: after the R2 rec2 flight seals (expected 2026-10-19 14:00Z) and before R3, with the resident session still `think-budget-np4`.
"""
    (package / "README.md").write_bytes(readme.encode("utf-8"))
    return {"protocol_sha256": sha(package / diag.PROTOCOL_NAME), "plan_sha256": sha(package / diag.PLAN_NAME), "audio_ceiling": str(audio_ceiling)}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--root", type=Path, default=diag.REPO)
    print(json.dumps(build(parser.parse_args(argv).root), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
