# Cell B7a v1 is CLOSED: two failures, no measurement, and the named fix that opens v2

Status: **CLOSED WITHOUT A RESULT.** This record closes the v1 flight of cell B7a (Node Context
Policy at level L1 on the sealed dual-store anchor, TRAIN Fold A 1,080). It reports **no score, no
delta and no verdict**. Author: the B7a v2 registration agent, worktree
`/home/chao/saea-worktrees/fable-b7a2`, branch `fable/b7a2`, base commit `25a7f325`. Everything here
was produced with **zero model, tokenizer, encoder, ASR, scorer and server contacts**.

## 1. The two failures

| | first | second |
| --- | --- | --- |
| run id | `SAEA-SLURP-NATIVE-NCP-L1-ANCHOR-TRAIN-FOLD-A-V1` | `SAEA-SLURP-NATIVE-NCP-L1-ANCHOR-TRAIN-FOLD-A-RECOVERY-V1` |
| attempt | `attempt-...-generation-v1` | `attempt-...-generation-recovery-v1` |
| when | 2026-09-17, about 21:00Z | 2026-09-19, about 03:35Z |
| flight commit | `00483f61` | `2f039fa6` |
| state | `ABORTED` | `ABORTED` |
| calls | 3,278 | 1,451 |
| repeated speech seconds | 8,973.150063 | 3,830.12 |
| rows | 618 contacted, 616 sealed | roughly 290 complete |
| request-fit receipts | 3,278 | 1,451 |
| official scoring jobs | 0 | 0 |
| task-quality reads | 0 | 0 |

**First failure.** `NativeEpisodeError: Planner output names no registered action`. Two of the
attempt's 665 Planner responses named no registered action and
`reproduction.ojw.native_episode._planner_action` raised. Engineering item E8c (commit `2af5955a`,
merged `5bbd54a2`) made an illegal Planner action a **row disposition** instead: the row is retained,
delivers its committed draft and records `planner_action_illegal`. The one recovery the
preregistration allows was registered
(`docs/readiness/2026-09-17-slurp-b7a-ncp-l1-anchor-v1-recovery-v1.md`) and its four-row smoke
`SAEA-SLURP-NATIVE-NCP-L1-ANCHOR-SMOKE-4-RECOVERY-V1` sealed on 2026-09-18 with a structural PASS.

**Second failure.** The recovery arm aborted with, verbatim:

```
NativeEpisodeError: native episode node failed: [100054] component 'reviewer_1_role' execute
'invoke' error, reason='metered completion is non-authoritative because finish_reason is 'length''
```

Exactly **one** contact in the trace reached **512** completion tokens -- the `max512` cap of the
serving geometry. Every other contact stayed below 400. The runner recorded the attempt `ABORTED`;
`flight.lock` was preserved and then reconciled, receipts
`flight-lock-preserved-20260919T034122Z.json` and
`flight-lock-reconciliation-20260919T034122Z.json` under
`SPEECHRL_DATA_DIR/coordination/slurp-b7a-ncp-l1-anchor-v1/`.

## 2. Root cause

The SLURP native baselines -- the sealed anchor
`configs/baseline/slurp-native-dual-store-train-fold-a-anchor-v1.json` and **every** B cell derived
from it -- omit `native_episode.finite_completion_policy`. The parser defaults it to `"raise"`:
`src/speech_aware_evidence_acquisition/rails/native_episode_config.py`,
`raw.get("finite_completion_policy", "raise")`. One truncated completion therefore propagates out of
the episode and kills the campaign.

The alternative is **already implemented and tested** in this repository and needs no new code:

* `reproduction/ojw/native_episode.py`, `_finite_terminal_outcome` -- retains the row with
  `terminal_disposition.reason == "finite_completion"`, records the truncated contact under
  `interrupted_role`, and delivers the latest delivery-eligible Solver draft, or abstains with empty
  output when no Solver had completed;
* `rails/native_episode_receipt.py` -- `_finite_delivery` and
  `validate_native_episode_terminal_policy` refuse that delivery unless the configured policy is
  exactly `deliver-latest-or-abstain`;
* `rails/runner.py` (around lines 2660-2720) -- refuses a disposition that differs from its actual
  quarantined completion;
* `core/flight/runtime.py` (around line 7993) -- passes the key through.

The A2T and E21 native baselines set the key explicitly, and cell B8b's fragments already carry it
(pinned by name in `tests/unit/test_config_table_module_switches.py::
test_the_two_b8b_fragments_arm_the_block_and_nothing_else`). **The key renders into no model
request**, so request bytes are unchanged by it.

## 3. What is NOT claimed

* **No score, no delta, no verdict.** Cell B7a has measured nothing. The 618 rows the v1 arm
  contacted and the roughly 290 rows the recovery completed were **never scored and never read**, in
  whole or in part, and no partial read is permitted now or later.
* **No reuse of any aborted row.** Neither attempt's rows are replayed, filtered, kept or merged into
  anything. Their spend is charged to their own closed run ids.
* **Nothing about whether the Node Context Policy at level L1 helps.** That is what v2 measures.
* **No claim about why a Reviewer completion reached the cap**, nor that v2 will meet none. The
  finite-completion count is a diagnostic v2 must report, not a hypothesis it tests.
* **No claim that the recovery's realized requests equalled the v1 arm's.** Greedy decoding at
  `temperature 0` is not bitwise reproducible across batch compositions.

## 4. Why this closes v1, and what opens

Section 8 of the recovery note and the owner iteration rule of the study `CLAUDE.md` -- *at most one
recovery re-registration per flight; a second failure stops the flight and the fix is proven on a
4-row dry run before another mechanism is admitted* -- close the v1 flight. There is **no third
registration under v1**, no replay and no row filtering. Both v1 packages
(`docs/readiness/2026-09-17-slurp-b7a-ncp-l1-anchor-v1/` and
`...-v1-recovery-v1/`) and both run ids are closed; their exposure rows stay as they are.

**v2 is a new registration** with new run ids, carrying the named fix and a four-row dry run of it
before the arm flies:

* preregistration: `docs/readiness/2026-09-19-slurp-b7a-ncp-l1-anchor-v2-preregistration.md`;
* package: `docs/readiness/2026-09-19-slurp-b7a-ncp-l1-anchor-v2/`;
* runs `SAEA-SLURP-NATIVE-NCP-L1-ANCHOR-SMOKE-4-V2`, `...-SMOKE-4-FIT-V2`,
  `...-TRAIN-FOLD-A-V2`, `...-TRAIN-FOLD-A-FIT-V2`;
* the question, the arms, the metrics, the resampling and the decision rule are the v1
  preregistration's, **unchanged**; the only model-facing configuration difference from the closed v1
  recovery is the episode key, which renders no request byte.
