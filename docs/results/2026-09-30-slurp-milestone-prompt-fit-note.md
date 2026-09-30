# SLURP milestone prompt fit: is the Solver COMPACT_REQUIRED new? (2026-09-30)

DESCRIPTIVE, model-free. Zero model, server, tokenizer or GPU contacts. The two milestone checks were re-run
from a detached verify worktree at master `6598ab9e`, which was removed afterwards. `cli check` is preflight only
(`generation_authorized: false`). No config was changed.

## Answer

This is the same state A2 and the DEV plan arm were in, and the sample is 10 tokens less tight. The preflight
Solver estimate is a fixed worst-case bound. It reads COMPACT_REQUIRED on every recent COMP-1 cell. At flight
time A2 compacted 0 of 1,000 rows. The DEV plan arm also compacted 0 of 1,000 rows.

| | A2 arm (DEV-2000-ADDED) | DEV plan arm | MILESTONE-01 and MILESTONE-00-PLAN (sample) |
|---|---|---|---|
| Solver rendered-text estimate (tokens) | 21,278 | 21,278 | 21,277 |
| Speech term (representative `samples[0]`) | 28 (1.92 s) | 28 | 19 (1.344 s) |
| Required window (text + speech + 2 + 512) | 21,820 | 21,820 | 21,810 |
| Physical / operational margin (slot 24,576, reserve 3,072) | +2,756 / **−316** | +2,756 / **−316** | +2,766 / **−306** |
| Check decision, Solver (Perception, Reviewer, Planner ALLOW) | COMPACT_REQUIRED | COMPACT_REQUIRED | COMPACT_REQUIRED (both cells) |
| Rows compacted at flight (`context_fit.compacted_contacts > 0`) | **0 / 1,000** | **0 / 1,000** | not flown |
| FIT receipts / all fit / Solver max exact prompt (min margin) | 4,050 / yes / 14,125 (9,937) | 4,071 / yes / 13,713 (10,349) | not flown |

Sources:
- `$DATA/coordination/slurp-stage3-comp1b-dev2000-added-v1/check-slurp-native-stage3-comp1b-dev2000-added-v1-ready-v1.json`
- `$DATA/coordination/slurp-b6-dev2000-added-v1/check-b6-plan-ready-v1.json`
- the re-run checks of `slurp-native-stage3-comp1b-testsample-v1` and `slurp-native-stage3-plan-testsample-milestone00-v1`
- `$DATA/runs/SAEA-SLURP-STAGE3-COMP1B-DEV2000-ADDED-V1/.../*.outputs.jsonl`, `native_episode_receipt.context_fit`, with `prompt_limit_tokens` 20,990
- `$DATA/runs/SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-V1/...`
- `$DATA/prepared/SAEA-SLURP-STAGE3-COMP1B-DEV2000-ADDED-FIT-V1/` and `...-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-FIT-V1/`, the `*.request-fit.json` exact tokenizer receipts

## Why −306 (and not a new condition)

`FlightRuntime._assess_prompt_budget` works as follows:
- It takes the widest serialized payload per phase over the whole roster.
- It pads the not-yet-existing predecessor state with 512 tokens' worth of ASCII.
- It counts tokens at 4 bytes per token.
- It adds the speech term of the first roster row only (14.4 tokens/s).

The Solver text bound is therefore near-constant across rosters: 21,278 on DEV and 21,277 on the sample. The
10-token difference is 9 speech tokens (the first sample row is 0.58 s shorter) plus 1 rendered token. It is
not longer utterances, more exemplar text, or roster-scaled budgets. The arm-vs-A2 config diff has
`composition_factor: []` and `anything_else: []` (package `registered-facts-v1.json`, `composed_config_diffs`),
so the supply sizes are unchanged.

Roster budgets do not enter the fit arithmetic. Real exact Solver prompts on DEV were 12,043 at the median and
14,125 at the maximum. The rail's 21,820 figure is 7,695 tokens above the maximum real prompt.

Sample speech (dataset fragments): mean 2.726 s vs 2.984 s on DEV, median 2.432 s vs 2.816 s, and p99 7.039 s on
both. The maximum is 21.629 s vs 10.368 s, and 6 sample rows exceed 10 s vs 1 on DEV. At DEV's observed rate
(143 exact speech tokens at 10.368 s, about 13.8 tokens/s), the longest sample row carries about 298 speech
tokens. That is about 155 more than any DEV row. It is small against A2's Solver minimum physical margin of 9,937
and the compaction headroom of 20,990 − 14,125 = 6,865. This is an estimate, not a measurement.

## Consequences for the milestone read

(a) Compaction is per realised request, at dispatch (`rails/runner.py::fit_contact_to_slot`). The limit is slot −
reserve − 512 − 2 = 20,990 prompt tokens, measured with the runtime's default counter, the same one A2 used.
Drops follow `rails/context_fit.py::DROP_ORDER`, lowest authority first:
1. `exemplar-supply` (the Solver's TRAIN exemplar values, from the tail)
2. `candidate-cards` (the intent-boundary cards, which are the COMP-1b module's channel, from the tail)
3. `scenario-hints`
4. `reviewer-audit`
5. `agent-states` (oldest first)

The instruction, task contract, speech reference, current draft and tools array are never dropped. A compacted
request has different bytes from the uncompacted one and carries a `context_compaction` record. If two passes do
not fit, the row takes the retained `context_compaction` terminal disposition. MILESTONE-00-PLAN carries the same
`compact-or-abstain` policy and the same limit. Its requests differ, though, so it would not necessarily compact
on the same rows. On any compacted row the paired delta would include a compaction difference. On DEV neither arm
compacted, so the question never arose.

(b) The FIT run ids (`native_contact_fit`) are an exact-tokenizer gate on each realised contact after
compaction and immediately before dispatch. The gate measures against the physical slot (fit multiple 1.0). It
is not a whole-roster pre-pass: its docstring says "not a whole-roster static capacity guarantee". If a request
does not fit, `build_native_contact_fit_gate` raises `PreparationError("native contact request exceeds the
registered capacity")`. The runner does not catch it, so the arm stops (fail-closed, not silent). Compaction is
recorded per row, never silent.

## Recommendation

Fly as registered. Change nothing before the flip. Both milestone cells already carry the exact
`context_fit_policy: compact-or-abstain` and `native_contact_fit` form that A2 and the DEV plan arm flew. The
check reading matches theirs to within 10 tokens, in the safe direction.

For the read, report `context_fit.compacted_contacts` counts for both arms. The expectation is 0, as on DEV. If
it is not 0, add the paired delta with the compacted rows excluded beside the registered one.
