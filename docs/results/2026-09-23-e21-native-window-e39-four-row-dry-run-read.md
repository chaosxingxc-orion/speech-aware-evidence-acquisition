# Item E39 four-row dry run (receipts-only read): the tolerance path works, the cap sizing does not

Read 2026-09-23 by the coordinator (Fable 5.1) through a model-free receipts read (`$SPEECHRL_DATA_DIR/analysis/SAEA-E21-NATIVE-WINDOW-E39-FOUR-ROW-READ-V1/read.md`, read.json sha256 3698f653e627..., read.md
sha256 de449d36d9db...); zero contacts; no text. Sealed run `SAEA-E21-NATIVE-WINDOW-SYSTEM-FOUR-ROW-E39-V1` /
`attempt-e21-native-window-system-four-row-e39-v1` (25 contacts on the 4 windows of call 4320211, FINALIZED at flight commit d3d397b4,
E21 geometry), comparator = the sealed parent `SAEA-E21-NATIVE-WINDOW-SYSTEM-FOUR-ROW-V1` (13 contacts) and the direct arm (4).

## 1. Verdict against the registered rule

| assertion | realized | holds |
| --- | --- | --- |
| R1 no auxiliary node voids its window (terminal_disposition.role_id in {perception, reviewer} with an abstention) | 0 rows | yes |
| R2 4 / 4 non-empty deliveries | 4 / 4 (the parent delivered 3 / 4: window w0003 was voided by a 1,024-token Perception runaway) | yes |
| R3 zero length-truncated Perception / Reviewer contacts | **6** (Perception 4 / 4 at the 320 cap; Reviewer 2 / 7 at 384) | **no** |

**Rule FAIL, cause named: cap sizing.** Every truncation took the E39 tolerance path (visit marked `truncated`, note kept, the Solver
ran, delivery = the Solver draft; 0 terminal dispositions; 0 abstentions). The mechanism the repair exists for (scope =
answering-node) is proven on receipts: the window the parent voided delivered 269 tokens (the direct arm's count on that window).
The caps were sized on the E35 sub10 medians (324 / 381); on these four windows the parent's Perception ran 299 / 366 / 504 / 1,024 and
its Reviewer 299 / 531 / 539, so 320 / 384 are reached by construction and R3 could not hold.

## 2. Structural facts

- Wire caps: Perception `max_tokens` 320 x 4, Reviewer 384 x 7, Solver / Planner 1,024 (unchanged); Solver completions 267-283 on
  every arm (the answering node never nears its cap).
- Contacts 25 vs 13: the Reviewer probe v2 moved the Planner routing from 0 REVISE to 3 of 4 windows, and all three revisions returned a
  byte-identical Solver draft (9 of 25 contacts bought nothing); the two leaves (probe text, truncated Reviewer note) are not separable
  in these receipts.
- Delivered volume: E39 1,089 completion tokens over 4 windows vs parent 827 vs direct 1,094; deletions in the sealed structural score
  equal the direct arm's exactly (7,738; parent 7,969). Descriptive only, n = 4.
- Budgets: 25 of 44 calls, 2,250 of 3,960 repeated speech seconds; one attempt, no abort.
- Bookkeeping: the baseline fragment's advisory `readiness` block still reads `held` at the flown commit (the gate reads the experiment
  cell's block, which is `ready`); repaired in the E39b registration.

## 3. Consequence (the one recovery re-registration)

E39b: the same cell with `roles.perception.max_completion_tokens 640` and `roles.reviewer.max_completion_tokens 640` (the parent's
observed 75th percentiles plus headroom; the pathological 1,024 runaway is still cut), same rule R1-R3. No score claim; the sub10 re-read of
the E39 form is a separate registration after E39b passes. Base lock v3.1 waits for E39b.
