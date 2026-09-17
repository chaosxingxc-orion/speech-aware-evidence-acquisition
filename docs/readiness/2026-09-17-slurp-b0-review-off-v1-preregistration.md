# Cell B0: the review-loop-off ablation, preregistration

Status: **PREREGISTERED BEFORE CONTACT.** Author: the B0 preparation agent, worktree
`/home/chao/saea-worktrees/fable-b0-prep`, branch `fable/b0-prep`, base commit `fe140d4f`.
Authority: `docs/superpowers/specs/2026-09-16-slurp-v2-base-program-design.md` section 4 (Phase B,
cell B0, module M0) and owner decision 4 of
`docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md`. This document grants no model
contact; both cells stay readiness `held` until the coordinator flips them.

Everything recorded here was produced with **zero model, tokenizer, encoder, ASR, scorer and
server contacts**. The resident service was never started, stopped or queried.

## 1. Question

Does removing the Reviewer/Planner review loop from the retained native dual-store agent change
task quality on TRAIN Fold A 1,080?

The loop costs 60 % of the anchor's contacts (5,417 for 1,080 rows), saves no intent, harms about
one row per thousand, and its Planner ACCEPTs 1,075 of 1,080 rows. If removing it is neutral, the
loop leaves the default plan and its budget is re-spent on sampling (M2) and exemplar grounding
(M1). If removing it is harmful, every later cell builds on the anchor instead.

## 2. Arms

| role | identity |
| --- | --- |
| treatment | `SAEA-SLURP-NATIVE-REVIEW-OFF-TRAIN-FOLD-A-V1` / `attempt-slurp-native-review-off-train-fold-a-generation-v1`, cell `slurp-native-review-off-train-fold-a-v1`, composed config `45fe779f75694774a5e8f313a6682da5f70531c6e810554b6cd1a06c734400d1`, protocol `c445394b3c5560e07d4b1bf22b520297514456f88ca50d7293bb265f6090a7e6` |
| comparator | sealed bytes of `SAEA-SLURP-NATIVE-DUAL-STORE-TRAIN-FOLD-A-ANCHOR-RECOVERY-V1` / `attempt-slurp-native-dual-store-train-fold-a-anchor-generation-recovery-v1`, score artifact SHA-256 `7360876322488e5fda689fcafda00e90da2ebf559e5a35e635c550f940202b47`, run manifest `049ac230e536bc6c8fe45bc847756ba486c4904e9c7602c698157f78d70c0152` |

The comparator is never re-flown and never re-scored. Its official aggregate on these same 1,080
rows is pooled SLU-F1 48.53, intent 77.96, scenario 84.81, action 79.26, pooled span F1 29.50.

Both arms share the roster `docs/receipts/rosters/slurp-evo-fold-a-v2.json`
(SHA-256 `1fe7908c31396774d7535fdf37bd791762215c324999d66ed7beb9e7b2f9033d`), split
`SLURP-EVO-FOLD-A-V2`, split identity
`61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6`, role `discovery`, and the
resident session `serving-slurp-native-candidate-five-train-a-np4-v1` (attach only).

## 3. The one factor, and what it is not

Moved: `native_episode.max_revisions` 1 to 0; `roles.reviewer.max_iterations` 3 to 0;
`roles.planner.max_iterations` 1 to 0; policy `phase-native-candidates-review-revise-v1` to
`phase-native-candidates-solve-v1` (same four declared phases, `max_contacts` 11 to 2);
`native_contact_fit` resized to the 2-contact ceiling with its own run and attempt id; the WAVE R7
speech-feature identity strings renamed onto this arm (provenance, never model-visible).

Held identical: the roster and split, the model fragment and resident geometry, the promoted
speech packets, both knowledge stores with their release and snapshot hashes, the candidate supply
contract, every instruction template, the `phase_tools` block, and the scorers.

Two request-level differences exist and both are the module's own channel:

1. **Rendered envelope, proven row for row.** On all 1,080 rows and all four declared phases the
   rendered request differs from the anchor's by exactly one substitution, the phase-program id
   inside the `[agent control <program>:<phase>:<sample>]` marker
   (`phase-native-candidates-review-revise-v1` to `phase-native-candidates-solve-v1`, 8 bytes).
   Applying that substitution to the anchor's envelope reproduces the review-off envelope byte for
   byte on 1080/1080 rows for every phase. The system message (8,956 bytes), the speech-feature
   part, the knowledge blocks and the entire instruction body are byte-identical. Receipt:
   `SPEECHRL_DATA_DIR/coordination/slurp-b0-review-off-v1/request-envelope-comparison-v1.json`.
2. **The episode-limits epilogue at dispatch.** The episode runner appends a `Native episode
   limits` block to the Solver's per-turn instruction whose `max_revisions` reads 0 instead of 1
   and whose `available_planner_actions` reads `[ACCEPT]` instead of `[ACCEPT, REVISE]`.
   Everything before that message, including the exposed Perception agent state, is byte-identical
   (`tests/unit/test_native_episode_runner.py::test_review_loop_off_solver_history_matches_the_review_loop_on_shape`).

The prepared first-phase Perception supply was rebuilt model-free for this cell and selects the
identical facets and values as the anchor preparation on every one of the 1,080 rows, so the
knowledge channel does not move either.

## 4. Metrics

Primary: **official pooled SLU micro F1** from `slurp-slu-official-train` (pinned official
`evaluate.py`, `slurp-official-8eb16545`), natural mixture, one complete score per manifest through
`core.scoring_batch`, never sharded.

Secondaries: intent (joint scenario+action) accuracy, scenario accuracy, action accuracy, official
pooled span F1. Reported beside them: per-row mean official SLU-F1 and per-row mean exact slot F1,
saves/harms/ties with the exact two-sided McNemar p.

`delta = review-off minus anchor`, in percentage points; a negative delta means the review-off arm
is worse.

## 5. Resampling and tables

Paired whole-speaker cluster bootstrap, **10,000 draws, seed 20260915**, CI95 for advancement and
CI90 for diagnostics, both as percentile pairs of the same retained replicate sequence.
Sensitivity: paired scenario-stratified row bootstrap, same draws and seed. Every verdict carries
the per-scenario table in both the natural-mixture and the equal-scenario weighting; the
equal-scenario delta is reported beside the natural-mixture point estimate and never replaces it.
Speaker clusters come from the released roster metadata (125 speakers, 18 scenarios of 60 rows,
523 headset and 557 far-field rows).

## 6. Decision rule (fixed here, copied from the spec)

Null half-widths from `docs/readiness/2026-09-09-slurp-own-null-replicate-v1-verdict.md`: intent
0.92, SLU micro 1.18, scenario 0.83, action 0.98 percentage points.

- **NEUTRAL** if both the pooled SLU delta and the intent delta are non-inferior within their own
  margins, that is the CI95 lower bound of the delta is greater than -1.18 pp for pooled SLU and
  greater than -0.92 pp for intent. The review loop then leaves the default plan and cells B1, B2,
  B4a and B4b build on B0.
- **HARMFUL** otherwise, that is either CI95 lower bound is at or below its margin. Later cells then
  build on the sealed anchor and the loop stays in the default plan.
- **ADMITTED as a gain** if the CI95 lower bound of the pooled SLU delta is greater than 0, with
  intent non-inferior at its own margin.

No repeat-to-pass: the verdict is read once, from the single official score of the complete
manifest. Scenario and action margins are diagnostics for the per-scenario table, not gates.

## 7. Cost reporting (mandatory in the verdict)

- actual generation contacts, expected exactly 2 per row and 2,160 in total;
- contacts per row, expected 2.000, against the anchor's 5.016 (5,417 / 1,080), a saving of 3,257
  contacts or 60.1 %;
- actual repeated speech seconds, expected 2 x 3,084.528 = 6,169.06;
- actual FIT endpoints, expected 4 per realized contact and 8,640 in total;
- GPU hours read from the serving monitor
  (`SPEECHRL_DATA_DIR/serving/serving-slurp-native-candidate-five-train-a-np4-v1/monitor.jsonl`)
  over the lease window, never a wall-clock guess;
- mean latency, slot occupancy and duty cycle from the same monitor;
- preprocess and scoring wall time.

Registered ceilings, which are bounds and not targets: 2,160 generation calls, 8,640 FIT
endpoints, 6,170 repeated speech seconds, 2.0 fit-inclusive GPU hours, one official complete
scoring job, zero ASR, encoder, task-contract and paid-API calls.

## 8. Prompt fit

Model-free estimate from `core.flight.cli check` over the widest request each phase renders across
the whole roster, against the 24,576-token serving slot: Perception 19,182 required window tokens
(margin 5,394), Solver 19,225 (margin 5,351); decision ALLOW for every phase. That estimate unions
every candidate envelope and is deliberately conservative.

The measured truth for exactly these two contacts comes from the anchor's own 5,417 sealed native
contact-fit receipts: `perception:0` required at most 4,270 tokens (minimum margin 20,306) and
`solver:0` at most 13,157 tokens (minimum margin 11,419), over 1,080 contacts each, all fitting.
Cell B0 renders the same envelope minus 8 bytes, so 13,157 tokens is an upper bound on its own
requirement. Receipt:
`SPEECHRL_DATA_DIR/coordination/slurp-b0-review-off-v1/anchor-fit-token-stats-v1.json`.

## 9. Failure rule

The first failure stops the cell and preserves everything. No automatic restart, replay, row
filtering, roster, role-graph, prompt, geometry or cap change, and no silent recovery. At most one
root-diagnosed recovery re-registration; a second failure closes the flight and the fix must be
proven on a four-row dry run before another mechanism is admitted. A failed four-row smoke stops
B0 until the fix is proven on that same four-row roster.

## 10. What is NOT claimed

- No superiority, generalization, paper-scale or held-out claim. TRAIN Fold A is an exposed
  discovery roster.
- No component-causal attribution beyond the one moved channel: a neutral result says the loop
  does not pay for itself in this configuration, not that review is useless in general.
- Nothing about Fold B, DEV-1000 or the test split; they stay unread.
- The 3,257 saved contacts are a cost fact, not an effectiveness result.
- A structural smoke result is never a quality result.

## 11. Analysis recipe

`docs/readiness/2026-09-17-slurp-b0-review-off-v1/analysis-recipe-v1.json` pins the two score
artifacts, the roster metadata
(`analysis/SAEA-SLURP-TRAIN-A-DIRECT-ANCHOR-RELEASE-PAIRED-ANALYSIS-V1/roster-metadata.json`,
SHA-256 `07f4cd83b83d83d65500a328e0a38421ede575195c63ae118def0d1006c14e34`), the shared estimators
(`analysis.null_calibration_cli.rows_for`, `analysis.null_calibration.pooled_f1`,
`analysis.paired.resampled_statistic`, `analysis.paired.paired_contrast`), the seed, the draws, the
two interval levels and the metric list. It reuses the released paired-read tooling of the
2026-09-17 TRAIN A direct anchor release rather than a private reimplementation;
`analysis.score_compare_cli` is deliberately not the runner because it hard-codes CI90 and DEV
population names.

## 12. Branch base and the master merge

This registration is based on `fe140d4f`. Master has since moved to `93060eb6` (E5b, A1, E5a, E3).
The protocol and plan hashes survive that merge because they derive from the four config fragments
alone. The prepared phase-supply artifact does not: its identity digest pins the SHA-256 of
`rails.kb_policy`, `rails.knowledge_provider`, `rails.phase_supply`, `rails.knowledge_stores` and
`core.flight.runtime`, and the merge touches two of them. After merging, re-pin both supplies and
rewrite the dependent hashes exactly as
[`2026-09-17-slurp-b0-review-off-v1/README.md`](2026-09-17-slurp-b0-review-off-v1/README.md)
section 7 prescribes, before flipping readiness.

## 13. Pre-contact evidence on file

All under `SPEECHRL_DATA_DIR/coordination/slurp-b0-review-off-v1/`, outside the repository so no
receipt can dirty the tree the scoring gate reads:

| receipt | SHA-256 |
| --- | --- |
| `check-full-v1.json` | `b9865b75695a34f40674041e7116d1da399c4755eb15b597ab679ba9365d4308` |
| `check-smoke-v1.json` | `d23fe385702cbc4c41c61172fce0f7a4f284c563733fa41d16ed9841f788c332` |
| `request-envelope-comparison-v1.json` | `344200f727d0d112bf59bbb5aac80763df36bdd8e8de0cb8f52870c0a208bd14` |
| `request-envelope-digests-v1.json` | `74274883d45e91ea6dfa329866e937dd6b26587aa0740da804a34edb8d5362f8` |
| `phase-supply-vs-anchor-v1.json` | `aa7e2171b9a6aa75173ffe9ca3961ea0e528080f2722c089e3561b2b336ec288` |
| `anchor-fit-token-stats-v1.json` | `1eb2352b947942fe0414f124a7c4abc37a54daf36a309ef9e4fc23b309e44b67` |
| `composed-hashes-v1.json` | `ee8bcda4c110354151e672f04b37547543eeaa9d15774a8f0c44b2db56fac3d6` |
| `plan-hashes-v1.txt` | `64fba18d2cccee0122e3fed71d669ec955c438e07403a1be8ef64c4ee5ff2544` |
| `ledger-parse-v1.json` | `8d7b344a60a32b7a99a512a72ba7285d4e0338619a58f7075a07f4ab13dbb969` |
| `prepare-supply-full-v1.json` | `5b4abe41b51e866ee9684cddcec543ce267ca2aa247d27e23b64772e0b14bd77` |
| `prepare-supply-smoke-v1.json` | `14e7aafc00a5a56666b2e1101b5e984ddaa7b295ef64db7f13163a1fa2a3d5d8` |
| `wire-check-smoke-v2.stderr.txt` | `db3849fd2c87040e1130e6eaa42a79046625fba3aad02468d8776c46eaead0c9` |

Both `check` receipts were produced at commit `d04d389e`, the registration commit carrying every
config, plan and ledger row this cell flies; the documentation commit that follows it changes no
config, no plan and no ledger row.

The last row is the refusal that proves `wire-check` cannot serve this arm:
`FlightRuntime._dispatch_phase_program` raises *native episode requires the actual shared speech
renderer; a generic text wire-check transport cannot prove this path*, because `wire_check`
installs a transport double. Neither cell therefore declares that stage, exactly as the sealed
anchor cell does not. The row-for-row envelope comparison of section 3 is the contact-free
substitute and is stronger per row than a single wire-check receipt would have been.
