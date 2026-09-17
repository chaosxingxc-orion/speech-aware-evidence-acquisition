# Cell B0r: the same-roster own-null replicate of cell B0, preregistration

Status: **PREREGISTERED BEFORE CONTACT.** Author: the B0-replicate preparation agent, worktree
`/home/chao/saea-worktrees/fable-b0r-prep`, branch `fable/b0r-prep`, base commit `6c5c9ab7`.
Authority: `docs/superpowers/specs/2026-09-16-slurp-v2-base-program-design.md` section 4 (Phase B,
module M0), owner decision 4 of `docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md`,
and the family rule of owner Decision 9 of 2026-09-08 item 3: **every "not worse" guard is a
non-inferiority test with a margin fixed from the carrier's own null.** This document grants no
model contact; the cell stays readiness `held` until the coordinator adds the decision requirement
and flips it.

Everything recorded here was produced with **zero model, tokenizer, encoder, ASR, scorer and
server contacts**. The resident service was never started, stopped or queried, and no other
worktree was modified.

## 1. Why there is a B0r at all

Cell B0 (`SAEA-SLURP-NATIVE-REVIEW-OFF-TRAIN-FOLD-A-V1`, FINALIZED at study commit `5d0d694d`,
score artifact `51f37e6c5a78751f2d000ac370cff6f0fff18745cd18d1fc81a2cd145ce960ae`, run manifest
`8b6f3f783f1933c4009c46cdc01472e240c547a496f7553c07e5efe301cdfe32`) measured, against the sealed
dual-store anchor on the same 1,080 rows:

| metric | delta | CI95 (paired whole-speaker) | CI95 half-width | imported margin | clause |
| --- | --- | --- | --- | --- | --- |
| official pooled SLU micro F1 | +0.1318 pp | [-1.150048, +1.454120] | 1.3021 pp | 1.18 pp | passed, by 0.03 pp |
| intent (joint scenario+action) | -0.3704 pp | [-1.527335, +0.821699] | 1.1745 pp | 0.92 pp | **failed** |

The preregistered rule therefore returned **HARMFUL** on the intent clause. But read the two
right-hand columns: **the imported margins are narrower than the CI95 half-widths this roster
yields.** The 0.92 pp intent margin and the 1.18 pp SLU margin come from
`docs/readiness/2026-09-09-slurp-own-null-replicate-v1-verdict.md`, a **DEV-1000** null. A
non-inferiority clause whose margin is narrower than the measurement's own noise cannot certify a
null module. It can only reject, whatever the module does — and on the SLU clause it passed by
three hundredths of a point, which is not a measurement, it is a coin.

That is the same defect the Earnings-21 KC-E1f verdict named in its own section 13, and the study
already has its answer: measure the carrier's own null on the same roster, fix the rule before the
number is read, and let the first verdict stand beside the re-decision. The precedent pair is
`docs/readiness/2026-09-08-e21-own-null-replicate-v1-verdict.md` (the null) and
`docs/readiness/2026-09-08-e21-kc-e1f-repair-pass-v2-redecision.md` (the re-decision). **This cell
is the SLURP TRAIN Fold A version of the first of those two, and section 6 below is the second.**

## 2. The cell, and why it is a replicate by construction

| item | value |
| --- | --- |
| cell / experiment fragment | `slurp-native-review-off-train-fold-a-replicate-v1` |
| generation run / attempt | `SAEA-SLURP-NATIVE-REVIEW-OFF-TRAIN-FOLD-A-REPLICATE-V1` / `attempt-slurp-native-review-off-train-fold-a-replicate-generation-v1` |
| native fit run / attempt | `SAEA-SLURP-NATIVE-REVIEW-OFF-TRAIN-FOLD-A-REPLICATE-FIT-V1` / `attempt-slurp-native-review-off-train-fold-a-replicate-fit-v1` |
| model fragment | `q4km-mmproj-free-slurp-native-bounded-perception-proof-np4-ctx24k-max512-v1` (temperature 0, **seed 20260913**, max_tokens 512) |
| dataset fragment | `slurp-speech-native-evo-fold-a-1080` |
| baseline fragment | `slurp-native-dual-store-train-fold-a-review-off-replicate-v1` |
| campaign plan | `configs/campaign/slurp-native-review-off-train-fold-a-replicate-v1.json` |
| composed config / protocol | `086b6387de1f5ef9afb4d86f7f90058c753f3fea78d9ed1ee3ea9ea960f3018a` / `6f1d8dc0120b5f87442ac0d48eb0ca63656603222326df13b159673fe05e7d48` |
| prepared phase supply | `prepared/SAEA-SLURP-NATIVE-REVIEW-OFF-TRAIN-FOLD-A-REPLICATE-V1/phase-supply-v3.json`, SHA-256 `052acd26f790a4e1af04a0c0a10dcc86bfaede1f208819b11ec53097edb1fccf` |
| session | `serving-slurp-native-candidate-five-train-a-np4-v1`, attach only, never spawn |
| readiness | `held`, carrying the preparation requirement only; the coordinator adds the decision requirement and flips |

The baseline fragment is cell B0's own bytes with exactly three substitutions: the native-fit run
id, the native-fit attempt id, and the prepared-supply pin. The experiment fragment is cell B0's
own bytes with the cell, run, attempt, experiment and fragment-kind identities changed, readiness
returned to `held`, and the prose fields (`purpose`, `what_this_is`, `decision_population`,
`failure_policy`, the budget `definition`) rewritten to describe a replicate. **The roster, the
1,080 ordered sample ids, the split identity hash, the budgets and every behavioural key are
copied, not retyped.**

Held identical: the arm `speech-feature-query-native-tools`, the policy
`phase-native-candidates-solve-v1`, the native episode role graph (`max_revisions` 0, Reviewer and
Planner `max_iterations` 0), the model fragment and resident geometry, the promoted speech packets
and their promotion-receipt hash, both knowledge stores with their release and snapshot hashes, the
candidate supply contract, every instruction template, the inert `phase_tools` block, the scorers,
and — deliberately — **the WAVE R7 speech-feature identity strings**
(`saea-slurp-task-agent-review-off-v1:query-speech` / `saea-slurp-task-agent-review-off-v1`). Cell
B2's fragment mints its own pair on purpose because B2 changes the arm; a replicate that renamed
them would not be a replicate. They are provenance only — `core.model.transport` validates and then
drops them, and they never enter the rendered `messages` — and native contact-fit receipts are
namespaced by the FIT run and attempt id, so holding them fixed cannot collide with B0's.

## 3. The one factor, and what it is not

**The factor is batch composition under greedy decoding, and nothing else.** `llama-server` at
temperature 0 does not return bytes independent of how requests batch across slots, so a cell that
changes nothing at all still produces a non-zero delta. Earnings-21 measured its own version of
that on 1,593 windows; SLURP measured a DEV-1000 version of it on 2026-09-09. **TRAIN Fold A has
never had that measurement**, and until it does, every TRAIN Fold A non-inferiority clause borrows
a half-width it did not measure.

Not the media, not the prompt, not the knowledge, not the role graph, not the geometry, not the
population.

### 3.1 Rendered request bytes — proven row for row, before contact

On all 1,080 rows and all four declared phases, cell B0r renders a request **byte-identical** to
cell B0's, **including** the `[agent control <program>:<phase>:<sample>]` marker, because the phase
program id does not move. Zero differing rows and a rendered byte delta of exactly 0 in every
phase. **Neither the run id nor the attempt id appears in any rendered byte.** The comparison was
run three ways through `core.flight.runtime.render_phase_prompt_envelopes`, the one authority the
pinned prompt-fit measurement and its verification both use:

| comparison | rows | differing rows | byte deltas |
| --- | --- | --- | --- |
| B0r versus cell B0 **as committed on this master** | 1,080 x 4 phases | 0 | {0} |
| B0r versus cell B0 **as flown**, rendered from the `5d0d694d` worktree with that commit's own code and config bytes | 1,080 x 4 phases | 0 | {0} |
| cell B0 as flown versus cell B0 on this master | 1,080 x 4 phases | 0 | {0} |

Receipt: `SPEECHRL_DATA_DIR/coordination/slurp-b0-replicate-v1/request-envelope-comparison-v1.json`,
with the per-row, per-phase digests of all three renderings beside it. The third row is what proves
the second: rendering cell B0 from the `fable-b0-flight` worktree reproduces B0's registered
composed config hash `45fe779f75694774a5e8f313a6682da5f70531c6e810554b6cd1a06c734400d1` and its
protocol hash `c445394b3c5560e07d4b1bf22b520297514456f88ca50d7293bb265f6090a7e6` exactly, so the
bytes compared are the bytes B0 sent.

The episode-limits epilogue the episode runner appends at dispatch is also identical, because
`max_revisions` and the Reviewer/Planner iteration counts are identical.

### 3.2 The prepared Perception supply — rebuilt, and identical where it counts

`core.preparation.artifact_inputs` binds the composed values (run and attempt ids included) and the
SHA-256 of `rails.kb_policy`, `rails.knowledge_provider`, `rails.phase_supply`,
`rails.knowledge_stores` and `core.flight.runtime`. Both moved since B0 flew, so the artifact FILE
had to be rebuilt model-free for this cell. Its **output** — the thing that reaches a request — is
byte-equal to cell B0's and to the sealed anchor preparation's:

| artifact | file SHA-256 | output SHA-256 |
| --- | --- | --- |
| B0r | `052acd26f790a4e1af04a0c0a10dcc86bfaede1f208819b11ec53097edb1fccf` | `ba5e1faab9550fcae700f649a0ec6674327ffefe97d7044bb7ea3887536fb54f` |
| B0 | `7930b9df5fcc8b1bc956495ad303892985a4ebbb6495d936c47c826db1d31b2b` | `ba5e1faab9550fcae700f649a0ec6674327ffefe97d7044bb7ea3887536fb54f` |
| anchor | `c5b0b51c23ef22feb1284559cd9e37286922d4cefc2e3cfcf7feafb23e3b595e` | `ba5e1faab9550fcae700f649a0ec6674327ffefe97d7044bb7ea3887536fb54f` |

1,080 of 1,080 rows select the identical values in the identical order in every pairing. Receipt:
`SPEECHRL_DATA_DIR/coordination/slurp-b0-replicate-v1/phase-supply-vs-b0-and-anchor-v1.json`.

### 3.3 What cannot be held fixed, named here rather than discovered later

1. **Batch composition.** Four slots, 2,160 contacts, `id_slot` per sample: which requests share a
   decode batch depends on arrival timing. This is the factor.
2. **The serving process instance.** B0 ran under this same resident session;
   `core.session.attach_session` identity-checks the binary SHA-256, both GGUF SHA-256 values,
   `-c 98304 -np 4`, the four 24,576-token slots and the speech-feature root before the first
   contact, so the *server* is the same server and only the process instance may differ.

### 3.4 The identity anchor is a STOP condition, not a report line

The composed config hash of a replicate **necessarily** moves, because the run and attempt ids are
inside it. What must not move is the behaviour, and section 3.1 is what proves that. Before the
first contact the coordinator re-runs `core.flight.cli check` and confirms the runtime-derived
protocol hash equals `6f1d8dc0120b5f87442ac0d48eb0ca63656603222326df13b159673fe05e7d48`. If it
differs by one character, the flight stops and reports.

### 3.5 One honest discrepancy, isolated and named

Cell B0's registered composed config hash `45fe779f` **cannot be reproduced from master's committed
bytes**, and the cause is exactly one key. Commit `ad04a26c` (merged as `dd83963e`), after B0 flew,
added `native_episode.review_loop: "off"` to B0's baseline fragment as part of the harness-admission
switch classes. Reverting only that one key to its `5d0d694d` bytes reproduces `45fe779f` and
`c445394b` exactly on this master; nothing else in B0's four fragments moved, and its experiment
fragment did not move at all. The marker is, in its own author's words, "a checked redundant
declaration": `rails.native_episode_config.load_native_episode_config` derives
`review_loop_enabled` from the three authoritative leaves and *refuses* a marker that disagrees with
them. Cell B0r inherits the marker from master. Section 3.1's third comparison is the proof that it
changes no rendered byte, and the episode it configures is the same episode.

## 4. Metrics

Primary: **official pooled SLU micro F1** from `slurp-slu-official-train` (pinned official
`evaluate.py`, `slurp-official-8eb16545`), natural mixture, one complete score per manifest through
`core.scoring_batch`, never sharded.

Secondaries: intent (joint scenario+action) accuracy, scenario accuracy, action accuracy, official
pooled span F1. Reported beside them: per-row mean official SLU-F1 and per-row mean exact slot F1,
saves/harms/ties with the exact two-sided McNemar p, and the count of rows whose delivered
(scenario, action) pair differs between the two passes.

Two signed contrasts: the **own null** is `delta = R minus B0`; the **clauses** use
`delta = arm minus anchor`, both in percentage points, negative meaning worse.

## 5. Resampling and tables

Paired whole-speaker cluster bootstrap, **10,000 draws, seed 20260915**, CI95 for the clauses and
CI90 for diagnostics, both as percentile pairs of the same retained replicate sequence — the first
pass's own estimator settings, unchanged. Sensitivity: paired scenario-stratified row bootstrap,
same draws and seed. Speaker clusters (125) come from the released roster metadata
(`analysis/SAEA-SLURP-TRAIN-A-DIRECT-ANCHOR-RELEASE-PAIRED-ANALYSIS-V1/roster-metadata.json`,
SHA-256 `07f4cd83b83d83d65500a328e0a38421ede575195c63ae118def0d1006c14e34`). Every verdict carries
the per-scenario table in both the natural-mixture and the equal-scenario weighting.

The recomputed `(B0 minus anchor)` contrast must reproduce the first pass's CI95 lower bounds
`-1.150048` (pooled SLU) and `-1.527335` (intent) to the digit. If it does not, the read stops: the
same sealed bytes under the same estimator and seed cannot give two answers.

## 6. Decision rule (fixed here, before the replicate is read)

> Re-decision of module M0 (review loop off) under the TRAIN A own null. Let R be the replicate and
> B0 the first pass, both against the sealed anchor A on the same 1,080 rows with the same paired
> whole-speaker bootstrap (10,000 draws, seed 20260915). Own-null half-widths h_SLU and h_intent
> are the CI95 half-widths of (R minus B0) for pooled SLU and intent respectively (same rows, same
> interval level as the clauses). Clause 1 (SLU): the CI95 lower bound of (B0 minus A) exceeds
> -h_SLU AND the CI95 lower bound of (R minus A) exceeds -h_SLU. Clause 2 (intent): the same with
> h_intent. NEUTRAL if both clauses hold on both passes; ADMITTED-as-gain if additionally the CI95
> lower bound of the pooled SLU delta exceeds zero on both passes; HARMFUL otherwise. Diagnostics
> reported beside the rule and never used for it: the (R minus B0) point estimates, saves/harms,
> per-scenario tables, contacts and GPU hours of R, and the anchor-vs-R comparison. This rule
> replaces the imported DEV1000 margin for this module only; the first-pass status HARMFUL-by-rule
> stays on record beside the re-decision, as the KC-E1f v1/v2 pair does.

Three properties of that rule are deliberate and are recorded here so no later reader has to infer
them:

1. **A margin is one-sided and applies only on the harmful side.** It never widens an interval,
   never moves a point estimate and never turns a harm into a benefit. It says how much movement
   this configuration's own noise can manufacture with nothing changed, and refuses to call a
   smaller movement a harm.
2. **Both passes must clear the same bar.** A rule that read only the replicate would be a second
   draw at the same question; requiring B0 and R to clear their own-null margin is why one
   replicate is enough and a third pass is not.
3. **The half-widths are outputs of this cell, not inputs.** No value of h_SLU or h_intent is
   written anywhere in this registration, and none may be chosen after the fact. The imported 1.18
   and 0.92 are quoted in section 1 only to explain why the first rule could not answer; they gate
   nothing here.

On **NEUTRAL** the coordinator adds the harness-admission entry for M0, drops the review loop from
the default plan, and cells B1, B2, B4a and B4b build on B0. On **HARMFUL** later cells build on
the sealed anchor and the loop stays. The verdict is read once, from the single official score of
the complete manifest.

## 7. Cost reporting (mandatory in the verdict)

- actual generation contacts, expected exactly 2 per row and 2,160 in total — cell B0's realized
  figure to the digit;
- contacts per row, expected 2.000, against the anchor's 5.016;
- actual repeated speech seconds, expected 2 x 3,084.528 = 6,169.06;
- actual FIT endpoints, expected 4 per realized contact and 8,640 in total;
- GPU hours read from the serving monitor
  (`SPEECHRL_DATA_DIR/serving/serving-slurp-native-candidate-five-train-a-np4-v1/monitor.jsonl`)
  over the lease window, never a wall-clock guess, reported beside B0's own 1.0540;
- mean latency, slot occupancy and duty cycle from the same monitor, beside B0's 6.608 s, 0.905 and
  86.35 % mean utilisation;
- preprocess and scoring wall time, beside B0's 13.47 s and 165.44 s.

Registered ceilings, which are bounds and not targets: **2,160 generation calls, 8,640 FIT
endpoints, 6,170 repeated speech seconds, 2.0 fit-inclusive GPU hours**, one official complete
scoring job, zero ASR, encoder, task-contract and paid-API calls. Expect roughly 1.0 to 1.1 GPU
hours and about 65 to 70 minutes of generation wall clock, from B0's measured 3,945.1 s.

## 8. Prompt fit

Model-free estimate from `core.flight.cli check` over the widest request each phase renders across
the whole roster, against the 24,576-token serving slot: Perception 19,182 required window tokens
(operational margin 5,394), Solver 19,225 (5,351), Reviewer 19,045 and Planner 18,985 — decision
**ALLOW** for every phase. These are cell B0's own numbers to the token, because the envelopes are
the same envelopes.

The measured truth for the two contacts that actually fly comes from the anchor's 5,417 sealed
native contact-fit receipts: `perception:0` required at most 4,270 tokens (minimum margin 20,306)
and `solver:0` at most 13,157 tokens (minimum margin 11,419), 1,080 contacts each, all fitting.

## 9. No smoke, and why

No four-row smoke is registered, and none is needed. The request bytes of this cell **are** cell
B0's, proved row for row in section 3.1 before any contact. B0's own smoke
`SAEA-SLURP-NATIVE-REVIEW-OFF-SMOKE-4-V1` (runbook
`docs/readiness/2026-09-17-slurp-b0-review-off-v1/README.md` section 3) already sealed the
structural form of this exact episode: 8 contacts, 2 per row, no Reviewer or Planner contact,
`review_loop_disposition = skipped_by_configuration` on every row, one `*.request-fit.json` per
realized contact with `every_request_fits = true`. Re-flying it would spend contacts to re-learn a
fact already on file, and — worse — would put four rows of this roster through a second batch
composition before the measurement that this cell exists to make.

## 10. Failure rule

The first failure stops the cell and preserves everything. No automatic restart, replay, row
filtering, roster, role-graph, prompt, geometry or cap change, and no silent recovery. At most one
root-diagnosed recovery re-registration; a second failure closes the flight and the fix must be
proven on a four-row dry run before another mechanism is admitted. A partial manifest is never
scored and never read.

## 11. What is NOT claimed

- **Nothing about the direct comparison claims.** The 2026-09-17 TRAIN A direct anchor release and
  every number in it are untouched; this cell re-decides module M0 and nothing else.
- **No default-plan entry until the re-decision.** Registering this replicate does not admit M0. A
  NEUTRAL re-decision does, and it does not exist yet.
- **No third pass.** The own null is one replicate. A third pass of this configuration would be
  repeat-to-pass and is neither registered nor authorized.
- **No superiority, generalization, paper-scale or held-out claim.** TRAIN Fold A is an exposed
  discovery roster.
- **No component-causal attribution.** A NEUTRAL re-decision says the review loop does not pay for
  itself in this configuration on this roster, not that review is useless in general.
- **Nothing about Fold B, DEV-1000 or the test split**; they stay unread.
- **The 3,257 contacts B0 saves are a cost fact, not an effectiveness result**, and this cell does
  not change that.
- **This cell measures its own noise, not a general one.** h_SLU and h_intent belong to this
  configuration, this roster and this serving geometry; they are not a SLURP-wide constant and must
  not be imported into another cell the way the DEV-1000 half-widths were imported into this one.

## 12. Analysis recipe

`docs/readiness/2026-09-17-slurp-b0-replicate-v1/analysis-recipe-v1.json` pins the three score
artifacts (two sealed, one to be filled in by the coordinator after the manifest seals), the roster
metadata, the shared estimators (`analysis.null_calibration_cli.rows_for`,
`analysis.null_calibration.pooled_f1`, `analysis.paired.resampled_statistic`,
`analysis.paired.paired_contrast`), the seed, the draws, the two interval levels, the three
contrasts and the required tables. It reuses the released paired-read tooling rather than a private
reimplementation; `analysis.score_compare_cli` is deliberately not the runner because it hard-codes
CI90 and DEV population names.

Outputs: `analysis/SAEA-SLURP-B0-REPLICATE-OWN-NULL-PAIRED-ANALYSIS-V1/{score-contrasts.json,README.md}`
and the verdict `docs/results/2026-09-17-slurp-b0-review-off-redecision-v2.md`. The first-pass
verdict stays on record beside it, as the KC-E1f v1/v2 pair does.

## 13. Pre-contact evidence on file

All under `SPEECHRL_DATA_DIR/coordination/slurp-b0-replicate-v1/`, outside the repository so no
receipt can dirty the tree the scoring gate reads at finalize. The SHA-256 of each is recorded in
[`2026-09-17-slurp-b0-replicate-v1/README.md`](2026-09-17-slurp-b0-replicate-v1/README.md)
section 6.

| receipt | what it proves |
| --- | --- |
| `prepare-supply-v1.json` | the model-free supply preparation receipt for this cell |
| `phase-supply-vs-b0-and-anchor-v1.json` | the rebuilt Perception supply selects what B0 and the anchor selected, on 1,080/1,080 rows |
| `composed-hashes-v1.json` | the composed and protocol hashes, the method verification against the anchor's registered `d1c61c09`, and the exact B0-versus-B0r composed-key diff |
| `request-envelope-comparison-v1.json` | byte-identical rendered requests on 1,080 rows x 4 phases, in all three pairings of section 3.1 |
| `request-envelope-digests-b0r-v1.json`, `request-envelope-digests-b0-master-v1.json`, `request-envelope-digests-b0-asflown-v1.json` | the per-row, per-phase envelope digests behind that claim |
| `plan-hashes-v1.txt` | the SHA-256 of every plan and protocol document in the readiness directory |
| `ledger-parse-v1.json` | `contracts._parse_ledger_tables` sees both rows exactly once, each `consumed = no` |
| `check-v1.json` | `core.flight.cli check` passes: gate, exposure row, clean tree, attempt free, prompt budget ALLOW for every phase |

`core.flight.cli wire-check` is unavailable for any native-episode cell:
`FlightRuntime._dispatch_phase_program` refuses a native episode whose transport is not the real
shared speech renderer, and `wire_check` installs a text transport double. Cell B0 and the sealed
anchor declare the same four stages for the same reason. The row-for-row envelope comparison of
section 3.1 is the contact-free substitute and is stronger per row.
