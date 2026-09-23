# E39b: the one recovery re-registration of the E39 four-row dry run (caps 640 / 640)

Derived 2026-09-23 by the coordinator from the E39 package by id substitution after the E39 read (`docs/results/2026-09-23-e21-native-window-e39-four-row-dry-run-read.md`): rule FAIL on R3 (6 length-truncated auxiliary contacts at 320 / 384), cause = cap sizing; the caps move to 640 / 640 (the parent's observed 75th percentiles plus headroom; the 1,024 runaway is still cut). Same roster, geometry, rule and read.

# Item E39 four-row dry run on the E21 native-window cell: launch runbook

Registered 2026-09-23, before any contact, in the git worktree
`/home/chao/saea-worktrees/fable-e39reg` (branch `fable/e39reg`, base commit
`321b64fe`). Authority: `docs/results/2026-09-22-e21-native-window-flightruntime-e35-read.md`
section 5 (the dry-run sketch this package registers),
`docs/results/2026-09-22-base-lock-v3.md` section 5a (the one open harness defect
at the lock), owner decisions 89 and 98.

**Question:** on the SAME four-row roster, the SAME six-node native episode and the
SAME resident E21 serving geometry the sealed E35 four-row system cell flew, does a
**length-truncated Perception or Reviewer contact still void its window?**

**It does not ask** -- and this package makes **no claim** about -- whether the repair
improves any score, whether the system arm beats the direct arm, or anything about
the sub10 or full-discovery E21 reads. This is a **Stage-2 base repair proof**, not a
Stage-3 cell: receipts only, zero scoring jobs, harness-admission label `NONE`.

## The one factor (three leaves, one repair)

Against the sealed `e21-native-window-system-four-row-v1`:

1. `native_episode.finite_completion_scope` `"episode"` -> `"answering-node"`. Item
   E13's `deliver-latest-or-abstain` rule stops ending the episode when a
   **non-answering** node is length-truncated; only a truncated Solver, or no Solver
   draft at the end, still triggers it.
2. Per-role completion caps `roles.perception.max_completion_tokens` 320 and
   `roles.reviewer.max_completion_tokens` 384 -- both inside the geometry's 1,024,
   sized on the E35 sub10 medians of 324 and 381, composed at request time like the
   E2 decoding overrides.
3. The tool-free Reviewer probe `probes/e21_native_window_system_reviewer_v2.txt` in
   place of v1, which orders a task-contract tool call this tool-free cell arms no
   tool for.

Nothing else moves. Every pinned artifact -- the execution-unit subset, the window
feature packets and the participant-roster knowledge snapshot -- is the parent's,
because those pins bind the four-row **roster batch**
`SAEA-E21-NATIVE-WINDOW-FOUR-ROW-V1`, not a run id.

`native_episode.finite_completion_policy` (`deliver-latest-or-abstain`, item E13) and
`native_episode.react_exhaustion_policy` (`continue-without-answer`, item E22) keep
the parent's values, as `scripts/checks/finite_completion_policy_check.py` requires of
every live unflown native cell. Neither moves; what moves is the **scope** the first
applies to.

## The cell

| item | value |
| --- | --- |
| cell | `e21-native-window-system-four-row-e39b-v1` |
| experiment | `configs/experiment/e21-native-window-four-row-e39b-dry-run-v1.json` |
| baseline | `configs/baseline/e21-native-window-system-four-row-e39b-v1.json` |
| dataset | `configs/dataset/e21-native-window-four-row-v1.json` (unchanged) |
| policy | `phase-native-review-revise-acquire-v1` (unchanged, ceiling 11) |
| campaign | `configs/campaign/e21-native-window-system-four-row-e39b-v1.json` |
| generation run | `SAEA-E21-NATIVE-WINDOW-SYSTEM-FOUR-ROW-E39B-V1` (44 calls) |
| fit run | `SAEA-E21-NATIVE-WINDOW-SYSTEM-FOUR-ROW-E39B-V1-FIT-V1` (176 endpoints) |
| roster | 4 native windows of call `4320211`, split identity `4d9ea907...` |
| session | `serving-e21-native-window-flightruntime-np4-max1024-v1` (np4, 1,024) |
| composed config | `615d7f227348e7c71ac0fd9bc266dfe3693d22c2d86381055c915802f2680630` |
| protocol | `a06b65a712a72b29a002131b2261ab6cdbf7baab1cf190a9a6b6fd7783986cec` |
| comparator | the sealed E35 four-row **system** arm, receipts only, never re-flown |

Comparator receipts (not re-scored): `SAEA-E21-NATIVE-WINDOW-SYSTEM-FOUR-ROW-V1`,
attempt `attempt-e21-native-window-system-four-row-recovery-v4`, flight commit
`1a9c78d2`, 13 contacts / 1,170 repeated speech seconds through all six nodes. On
those four windows the sealed arm **abstained on two** and completed REVISE/ACCEPT on
the other two -- the shape the E35 read's section 5 named for this dry run.

## Budgets (ceilings, not targets)

44 generation calls = 4 windows x the exact eleven-contact program maximum.
176 fit endpoints = 44 x (1 speech packet + 3 endpoints).
3,960 **repeated** speech seconds = 4 windows x 11 contacts x 90 s; every
native-episode contact re-sends the window audio, the convention whose absence aborted
E35's `recovery-v2` after four contacts. 0.5 GPU hours -- the sealed E35 four-row
**system** arm's own registered value (E35's experiment-level 0.6 is the *pair* total,
0.5 system + 0.1 direct); this experiment has one arm, so its experiment-level
`execution_plan` carries that single arm's 44 / 0.5 / 3,960 and the runtime enforces it
run-cumulatively per run id. Zero official scoring jobs, zero ASR, encoder and paid-API
calls, zero native task-contract calls.

## What this package registers

1. `docs/readiness/2026-09-23-e21-native-window-four-row-e39b-v1/` -- this README, the
   protocol document, the receipts-only analysis recipe, and the generation and fit
   plans with their registered twins.
2. `docs/readiness/2026-09-23-e21-native-window-four-row-e39b-v1-preregistration.md`.
3. `configs/campaign/e21-native-window-system-four-row-e39b-v1.json` (new).
4. The experiment fragment's readiness reason, `service_session` and plan numbers.
5. Two fresh, **unconsumed** exposure-ledger rows, one generation and one fit.

The baseline fragment is untouched by this registration: its fit run id and cap
(`SAEA-E21-NATIVE-WINDOW-SYSTEM-FOUR-ROW-E39B-V1-FIT-V1`, 176) already agree with the
registered fit plan. Its own advisory `readiness` block still reads `held` with the
pre-registration wording; that block is **inert** -- flight readiness is decided by the
experiment cell's block alone (`core.flight.campaign.declared_readiness`) -- and root
may retire its wording in the same re-pin cycle, which recomputes the hashes anyway.

## Decision rule (receipts only)

PASS iff all three hold on the sealed manifest:

- **R1** zero retained rows whose `terminal_disposition.role_id` is `perception` or
  `reviewer` together with an abstention;
- **R2** 4 of 4 windows deliver non-empty text (one
  `saea-deliver-earnings-text-v1` receipt per window, zero blank deliveries);
- **R3** zero length-truncated Perception or Reviewer contacts at the 320 / 384 caps --
  reported with its exact count on every verdict; a non-zero count is a **named cause**,
  never a silent pass.

There is no score in this rule, no margin and no bar. On PASS the repair is proposed to
the owner as **base lock v3.1**. On FAIL it stops here and the named cause is registered
before anything else flies.

## Mint, re-pin, switch, fly

1. Mint the decision receipt
   `coordination/e21-native-window-four-row-e39b-v1/root-admission-v1.json`, decision id
   `e21-native-window-four-row-e39b-admission-v1`.
2. Re-pin and flip with `scripts/flights/repin_cell.py` over this package (experiment
   `e21-native-window-four-row-e39b-dry-run-v1`, cell
   `e21-native-window-system-four-row-e39b-v1`, readiness dir
   `docs/readiness/2026-09-23-e21-native-window-four-row-e39b-v1`, preregistration
   `docs/readiness/2026-09-23-e21-native-window-four-row-e39b-v1-preregistration.md`).
   The flip inserts the decision requirement into the cell and therefore **moves the
   composed and protocol hashes**; the tool rewrites them in the plans, the protocol
   document, this README, the preregistration and both ledger rows. There is no supply
   to prepare -- the program declares no supplied first phase (item E38), so no prepared
   artifact and no `preparation` requirement exist for this cell.
3. Switch the resident serving geometry to
   `serving-e21-native-window-flightruntime-np4-max1024-v1`.
4. Enqueue on the SAEA-Batch-Driver scheduled task (decision 77). The flight attaches
   to the resident session and never spawns or stops a server.

## Model-free proofs

`tests/unit/test_e39_finite_completion_scope.py`,
`tests/unit/test_e35_earnings_native_window_configs.py`,
`tests/unit/test_e35_earnings_native_episode_wire.py`,
`tests/unit/test_e35_native_review_revise_acquire_program.py`,
`tests/unit/test_e35_earnings_delivery_normaliser.py`; gates
`engineering_base_check.py`, `finite_completion_policy_check.py`,
`derived_media_confinement_check.py`, `harness_admission_check.py`,
`results_ledger_check.py`, `tool_catalog_check.py`. The composed and protocol hashes
above were computed directly through `core.config.compose` and
`core.config.protocol_hash`, and the baseline was loaded through
`rails.native_episode_config.load_native_episode_config` on the real
`phase-native-review-revise-acquire-v1` program.

## Not authorised by this package

No flight before the receipt is minted and the cell is flipped; no contact by this
registration; no scoring job of any kind; no re-flying, re-reading or re-scoring of the
sealed E35 four-row or sub10 cells; no roster, geometry, cap, probe, knowledge or graph
change inside this run id; no second recovery re-registration; no promotion of the
repair into a sealed cell before these receipts are read.
