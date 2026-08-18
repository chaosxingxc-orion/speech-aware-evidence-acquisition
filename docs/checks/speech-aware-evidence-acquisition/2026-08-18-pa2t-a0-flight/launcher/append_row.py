"""Append the SAEA-BASE-a2t-a0-400 pre-registration row to the exposure ledger.

LF-only, UTF-8, appended to the single existing table. Refuses to run twice.
"""

from __future__ import annotations

import io
from pathlib import Path

LEDGER = Path(
    "/mnt/d/chao_workspace/exploring-l4-intelligence/studies/"
    "speech-aware-evidence-acquisition/docs/exposure-ledger.md"
)

CELLS = [
    "2026-08-17",
    "SAEA-BASE-a2t-a0-400",
    "baseline-reproduction",
    (
        "P-A2T STAGE-1 A0 BASELINE RE-FLY (the 2026-08-17 night restructure, "
        "docs/readiness/2026-08-17-pa2t-preregistration-draft.md section 8 item 4): ONE arm, "
        "zero-supply, over the frozen 400-item Audio2Tool discovery split (8 tiers x 50, seed "
        "20260807). Produces the A0 artifact pa2t-binding.json's own A0_reuse_verdict records as "
        "absent everywhere on this machine (no run directory, outputs.jsonl, scores.json, "
        "ExecutionPlan or ledger row for this split), measures the REAL tool-acc/EM gap -- the "
        "84.6 percent / 15.6 percent headroom premise was RETIRED as unsourced and contradicted "
        "by both recoverable archival reads (dev 67.5/65.0, test 86.7/85.0) -- and yields the "
        "Stage-2 headroom sample list, the set where tool_accuracy == 1.0 and exact_match == 0.0. "
        "Every request ships the identical full 152-tool registry as its system instruction "
        "(50413 chars, ~12.6k estimated prompt tokens before audio) and NO supplied evidence: "
        "rails.runner.run_rails_experiment with arms = zero-supply only, through the "
        "rails.core_client.FrozenCoreClient bridge on D2 arm fixed-legal-context. Flight config "
        "configs/probes/g0-binding/pa2t-a0-flight.json; binding table "
        "configs/probes/g0-binding/pa2t-binding.json. The flying agent reads no metric -- a "
        "separately registered one-shot read mission follows."
    ),
    (
        "llama.cpp llama-server, receipt-pinned build, frozen Qwen3-Omni-30B-A3B-Instruct Q4_K_M "
        "GGUF per configs/model/q4km-featcache.json and receipts/runtime-q4km-featcache.json, "
        "spawned by core.session per session receipt; campaign-own feature cache "
        "/home/chao/feat-cache/audio2tool-q4km (COLD at registration, never the legacy q4km or "
        "the slurp-q4km directory)"
    ),
    (
        "audio2tool, frozen 400-item discovery-split probe receipt "
        "docs/receipts/probe-samples/r1-audio2tool-sample.json, all 8 tiers x 50 at seed 20260807"
    ),
    "discovery",
    "e1d751e6c76e49d087620842ba17c34e432a4602169dc2b93ee7e0a529ca332c",
    "no",
    "450",
    "3000",
    "1.5",
    (
        "FIRST frozen-core exposure of this study on the Audio2Tool carrier: pa2t-binding.json's "
        "A0_reuse_verdict establishes that no prediction or score artifact for any Audio2Tool "
        "read on this split exists anywhere on this machine, and the only recoverable Audio2Tool "
        "reads (cold-backup dev n=40 / test n=60) are a different split, seed, quantization, "
        "sampling policy and prompt, so nothing is inherited from them beyond the fact of prior "
        "program-level Audio2Tool contact. Inherits every prior SAEA row -- the "
        "earnings21-original / earnings22-original / conec campaigns and the SLURP devel n=60 "
        "P-SLU probe consumed 2026-08-18 -- plus program-level W1 probe campaigns on other "
        "carriers. Monotonically non-decreasing: this row adds Audio2Tool discovery-split "
        "exposure to that set and removes none."
    ),
    (
        "$SPEECHRL_DATA_DIR/runs/SAEA-BASE-a2t-a0-400/<attempt_id>/ -- ExecutionPlan, "
        "config-values, session receipt, server log, ConsumptionTrace, responses.jsonl, "
        "outputs.jsonl, flight-receipt.json; launcher and health logs archived to "
        "docs/checks/speech-aware-evidence-acquisition/2026-08-18-pa2t-a0-flight/"
    ),
    (
        "REGISTRATION ONLY: no core contact has occurred at the time this row is written. "
        "BUDGETS -- calls 450 registered (400 items x 1 request, 50 headroom); the ExecutionPlan "
        "itself claims the flight config's own 420. Speech audio seconds 3000, REFINED UP from "
        "the flight config's 2400: that figure came from pa2t-binding.json's PARTIAL 1801.3 s "
        "over the 350 items carrying a top-level duration, while the shipped adapter resolves "
        "all 400 (the 50 tier7_multiturn items included) and the model-free pre-flight measures "
        "the real total at 2159.69 s -- worst case inside the call budget is 2159.69 plus 20 "
        "retries each bounded by the split's own longest item 35.714 s = 2874.0 s. GPU hours "
        "1.5, REFINED DOWN from the flight config's own 2.0 placeholder, which that config's "
        "cost_budget note explicitly invites the flying agent to refine; the launcher stops "
        "before issuing any request that would cross 450 requests or 1.5 h of wall clock. "
        "RUNTIME DELTA disclosed at registration: beyond the campaign feature-cache directory "
        "and dropping the batch-executor-only id_slot sentinel (both inherited from the archived "
        "P-SLU launcher), this flight changes ONE committed server arg -- -np 4 becomes -np 1. "
        "llama-server divides -c across parallel slots, so the committed -c 49152 -np 4 yields "
        "12288 tokens PER SLOT (the archived P-SLU attempt-2 log records exactly that: 4 slots "
        "at n_ctx 12288), which is BELOW this flight's own ~12.6k-token registry prefill before "
        "audio and output -- every one of the 400 requests would overflow and the flight could "
        "not fly. -np 1 gives the single sequence the whole 49152, is memory-neutral (total "
        "n_ctx unchanged) and costs no throughput because the rails FrozenCoreClient issues "
        "requests strictly sequentially. consumed STAYS no: this flight reads no result. "
        "Audio2Tool license cc-by-nc-4.0 carried on audio-derived results."
    ),
]


def main() -> int:
    text = LEDGER.read_text(encoding="utf-8")
    if "SAEA-BASE-a2t-a0-400" in text:
        print("REFUSED: a SAEA-BASE-a2t-a0-400 row already exists in the ledger")
        return 1
    if len(CELLS) != 15:
        print(f"REFUSED: {len(CELLS)} cells, the table header declares 15")
        return 1
    for index, cell in enumerate(CELLS):
        if "|" in cell:
            print(f"REFUSED: cell {index} contains a pipe character")
            return 1
    row = "| " + " | ".join(CELLS) + " |\n"
    if not text.endswith("\n"):
        row = "\n" + row
    with io.open(LEDGER, "a", encoding="utf-8", newline="") as handle:
        handle.write(row)
    print(f"appended {len(row)} chars")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
