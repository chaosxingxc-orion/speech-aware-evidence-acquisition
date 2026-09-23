# Item E39b four-row dry run (the one recovery, caps 640 / 640): the Reviewer cap is solved, the Perception node has no length bound

Read 2026-09-23 by the coordinator (Fable 5.1) through a model-free receipts read (`$SPEECHRL_DATA_DIR/analysis/SAEA-E21-NATIVE-WINDOW-E39B-FOUR-ROW-READ-V1/read.md`, sha256 `1edfde6a07756ee54c852fac93f1c6d2762aa5914babd6f2a20ffea75e5279ae`; read.json sha256 `2d8cb0dd7f3bd0dd9f768f20e23649248f405f1047861b809fcd5629a467efeb`); zero contacts; no text. Sealed run `SAEA-E21-NATIVE-WINDOW-SYSTEM-FOUR-ROW-E39B-V1` / `attempt-e21-native-window-system-four-row-e39b-v1` (25 contacts, 4 windows of call 4320211, FINALIZED at flight commit 48c4bd1e, 04:01-04:04 UTC, one attempt, no abort). Comparators: E39 (25 contacts, caps 320 / 384), the parent (13 contacts, episode scope, one window voided), the direct arm (4).

## 1. Verdict against the registered rule (unchanged from E39)

| assertion | realized | holds |
| --- | --- | --- |
| R1 no auxiliary node voids its window | 0 rows | yes |
| R2 4 / 4 non-empty deliveries | 4 / 4 (parent 3 / 4) | yes |
| R3 zero length-truncated Perception / Reviewer contacts | **2** (Perception at 640 on windows w2, w3; Reviewer 0 / 7) | **no** |

**Rule FAIL; named cause: the Perception node has no receipt-backed length bound on this carrier at any cap tried (320, 384, 640, 1,024).** The Reviewer cap is solved at 640 (longest note 343, 46 % headroom). The Perception notes ran 504 / 523 / 640 / 640: the two natural stops sit within 136 tokens of the cap, and the parent at 1,024 still lost one window to a runaway. A further cap value is a fourth draw from the same unbounded distribution; the preregistration's one-recovery budget is spent.

## 2. What is proven on receipts (both dry runs)

- The repair's object, `finite_completion_scope = answering-node`, works on every occasion: every truncated auxiliary note was kept (`truncated = true`, a `truncation_events` record), every window reached the Solver and delivered a Solver draft; zero terminal dispositions; the window the parent voided delivers 269-270 tokens (the direct arm's count).
- Per-role caps ride exactly on the wire (Perception / Reviewer only; Solver / Planner keep 1,024); the Solver never nears its cap (267-283 tokens on every arm).
- The E39b delivery on window w1 is byte-identical to the parent's (same 504-token Perception note, first-pass ACCEPT, same Solver bytes): the mechanism changes nothing where nothing truncates.
- The null-revision effect is now separable: E39b truncates no Reviewer and still returns 3 / 3 byte-identical second drafts (9 of 25 contacts for no change), so the Reviewer probe v2 / route, not the truncated note, drives the no-op revisions (the same pattern P1 / R-PRIM show on SLURP).
- Budgets: 25 of 44 calls, 2,250 of 3,960 repeated speech seconds; +807 completion tokens and +30 s summed latency against E39 (the price of the longer auxiliary notes).

## 3. Bookkeeping corrections carried forward

- The E39 / E39b preregistrations' comparator prose ("abstained on two of the four windows, REVISE / ACCEPT on the other two") is wrong: the sealed parent shows one abstention (w2) and three first-pass ACCEPTs, zero REVISE. Corrected here; the preregistrations stay as registered (immutable), this note supersedes the prose.
- The baseline fragments' advisory `readiness` block reads `held` at both flown commits while the experiment cell's block (the gate's authority, `core.flight.campaign.declared_readiness`) reads `ready`; the E39b baseline documents the convention. No ruling needed.

## 4. Consequence (coordinator, provisional decision 103, pending the owner)

Base lock **v3.1 (provisional)**: the base supports `native_episode.finite_completion_scope` (default `episode`, every sealed configuration byte-identical) and per-role `max_completion_tokens`; every future Earnings native cell declares `answering-node`, the Reviewer cap 640 and the tool-free Reviewer probe v2; the Perception cap stays 640 with its truncation rate reported on every read as a measured quantity (R3 is re-stated from "zero" to "reported"), because the four-row receipts show the assertion R1 / R2 that the repair exists for holds twice while a zero-truncation Perception is not achievable by a cap. A bounded Perception note (a structured / length-constrained instruction) is a separate engineering item (E41) with its own dry run before the sub10 re-read of the Earnings system form. No effectiveness claim; n = 4.
