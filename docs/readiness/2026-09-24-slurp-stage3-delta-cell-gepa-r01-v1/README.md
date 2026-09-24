# Readiness package: SAEA-SLURP-STAGE3-DELTA-CELL-GEPA-R01-V1 (cell CELL-1-GEPA)

Status: **HELD**. This package registers the engineering for the **GEPA arm** of Stage-3 S3-6 -- the
locked v2.0 plan plus the released 448-value `stage3-deltas-gepa-v1` store -- and authorises no
flight, no readiness flip and no admission entry. Source specs:
`docs/superpowers/specs/2026-09-22-stage3-tfrl-base-loop-engineering.md` section S3-6 and
`docs/superpowers/specs/2026-09-24-slurp-stage3-gepa-arm-design.md`. Governing decisions: owner 101
(the three training-free RL families), 83 (the retention that produced 200 of the 448 rows), 99 (the
TRAIN lock) and 106 (the per-node routes). Design authority:
`docs/readiness/2026-09-24-slurp-stage3-gepa-r01-v1/cell-1-gepa-diff-plan-v1.md`. The registration
note is `docs/readiness/2026-09-24-slurp-stage3-delta-cell-gepa-r01-v1-preregistration.md`.

Stage-3 algorithm (owner decision 101): **`gepa-reflective-pareto-v1`**, operators `update` +
`selection` + `context_application` (the per-node supply is the context-application step; the
registry record gained that operator by the coordinator ruling of 2026-09-24, see section 2a of the
preregistration). Declared as `stage3_algorithm` in both experiment fragments and checked by
`scripts/checks/stage3_algorithm_label_check.py`.

## What this cell is

CELL-1 with `knowledge_stores.stage3-deltas` re-pointed from `stage3-deltas-v1r` (379 values) to
`stage3-deltas-gepa-v1` (448 values), and the twin arm to `stage3-deltas-gepa-twin-v1`. **Nothing
else moves**: the locked v2.0 PLAN fragment, the four routes and their caps (Perception unconditional
4, Solver 8, Reviewer 4, Planner 4), `finite_completion_policy` `deliver-latest-or-abstain`,
`react_exhaustion_policy` `continue-without-answer`, `context_fit_policy` `compact-or-abstain`, the
deliver normaliser `saea-deliver-normalise-v3`, the review loop, the population (TRAIN Fold A, 1,080
rows, split identity `61b0f062...`), the caps, the session and the comparator (the sealed PLAN arm at
the plan's own null, h_SLU 1.2485 / h_intent 0.9943).

That is owner decision 101's construction: three families, one base plan, one comparator, one own
null, and a different released delta store each.

## The store (2026-09-24, model-free)

Released by `scripts/flights/batch/gepa_to_deltas.sh` over the sealed outputs of the GEPA proposer
cell `SAEA-SLURP-STAGE3-GEPA-R01-V1`. The curator
`scripts/build_slurp_stage3_gepa_delta_rows.py` **imports** `build_slurp_stage3_delta_store.py`'s own
`curate`, dedup rule, facet rule, containment rule and document writers rather than restating them,
so the store's shape is the CELL-1 store's shape.

| | release.json (file digest) | snapshot CONTENT hash | snapshot.json file digest |
| --- | --- | --- | --- |
| `knowledge/slurp/semantic/stage3-deltas-gepa-v1/` | `53c1267169b5269bc850f75527b2c8086fd681126f9180ac4a0df9410b61fcfa` | `560d84e7e6364de5ce09635f586660d22b9a103734c51dbd64e6182599fb935c` | `9a849fffc47b3747...` |
| `knowledge/slurp/semantic/stage3-deltas-gepa-twin-v1/` | `fb2dad3082848f1ff794401f2ea1d9b0d53e33b0f7a459592b44364cce196fb3` | `f19671d381f82ffb07f7d186b93c45adfe129bcf934e62011abdec1744123ffe` | `094f952ce1f4ac0c...` |

**The snapshot pin is the CONTENT hash**, never the `snapshot.json` file digest; both were read out of
the released documents and the release-pins record, not typed. Release pins, including the per-node
reach block: `coordination/slurp-stage3-delta-cell-gepa-r01-v1/stage3-deltas-gepa-v1-release-pins.json`.
Release registrations (referenced, not copied):
`docs/readiness/2026-09-24-slurp-stage3-gepa-r01-v1/stage3-deltas-gepa-v1-release-registration.json`
(sha256 `cbcf18d4...`) and `...-twin-v1-release-registration.json` (sha256 `f4fa1332...`).

### The store, in counts (model-free, no statement text)

| | v1r (CELL-1 flew it) | v2 (CELL-2) | **gepa-v1 (CELL-1-GEPA)** |
| --- | ---: | ---: | ---: |
| values | 379 | 200 | **448** |
| perception / solver / reviewer / planner | 119 / 151 / 95 / 14 | 80 / 76 / 40 / 4 | **142 / 137 / 92 / 77** |
| of which GEPA-authored | -- | -- | 62 / 61 / 52 / 73 (248) |
| of which iteration-1 retained | -- | -- | 80 / 76 / 40 / 4 (200) |
| delta kinds | slot-contract 147, intent-boundary 117, reviewer-criterion 95, planner-rule 13, exemplar-note 5, perception-hint 2 | slot-contract 75, intent-boundary 79, reviewer-criterion 40, planner-rule 4, exemplar-note 2 | slot-contract 113, intent-boundary 111, reviewer-criterion 103, planner-rule 90, exemplar-note 27, perception-hint 4 |
| distinct facets / facet entries | 39 / 402 | 26 / 219 | **38 / 780** |
| facets per row | 357 x 1, 21 x 2, 1 x 3 | 182 x 1, 17 x 2, 1 x 3 | 251 x 1, 98 x 2, 80 x 3, 3 x 4, 15 x 5, 1 x 6 |
| source sample ids | 223 | 136 | **201** |
| statement characters | 31,840 | 16,743 | **39,839** (mean 88.9, longest 140) |
| authored token count (twin holds it) | 5,740 | 3,001 | **7,345** |
| twin value fixed points | 16 of 379 | 13 of 200 | **16 of 448** |
| worst-case supplied chars per node (P/S/R/Pl) | 485 / 938 / 423 / 381 | 476 / 850 / 416 / 269 | **528 / 1,035 / 471 / 479** |

**Provenance.** 448 = 248 rows the proposer cell authored (68 reflective contacts, one per (scenario,
node) group over the sealed ROLL-1 trajectories of the clean construction subset R01C; 17 scenarios x
4 nodes, `music` having no eligible row) + 200 rows the owner-decision-83 retention kept of v1r's 379
(179 retired and held as dedup tombstones, so the same statements cannot re-enter from the same ADV-1
advantage outputs). Retention record:
`prepared/SAEA-SLURP-STAGE3-DELTAS-GEPA-V1/retention-gepa-v1.md` (200 kept, 179 retired; 201 of 379
decided by the scenario rule, 178 by the frontier-slope tie rule).

**The permitted roster is the ADV-1 disagreeing receipt**,
`docs/receipts/rosters/slurp-stage3-advantage-r01c-disagreeing-v1.json`
(`SLURP-STAGE3-ADVANTAGE-R01C-DISAGREEING-V1`, 225 rows, split identity `7c603857...`) -- the same
receipt v1r and v2 pin, so this store shares their source identity rather than inventing a third
one. The GEPA package's own ruling of 2026-09-24 records why: the 448 rows cite 201 distinct sample
ids and 28 of them, cited by retained rows only, lie outside the 173 GEPA group rows, so the group
rows are the record of what a contact was SHOWN and not the store's permitted roster.

### Supply reach (model-free, release step R)

**448 of 448** values are reachable by a registered candidate intent on **every** node, arm and twin:
perception 142 (38 intents), solver 137 (36), reviewer 92 (33), planner 77 (33); the twin is identical
except reviewer 36 distinct intents. 38 of the 60 registered SLURP candidate intents
(`prepared/SAEA-SLURP-NATIVE-CANDIDATE-CONTRACTS-PREPARE-V1/catalog.json`) are covered. **No route is
inert by construction and none is removed from the fragment** -- the B9a-rec rule, which is exactly
what the diff plan's precondition 2 asked to be checked before the fragments were written.

**The Perception slice does not move.** The unconditional route takes the top 4 perception values by
`prior_score` descending, `value_id` ascending; measured over the released GEPA document, that top 4
is the SAME four value ids as v1r's and v2's (`delta:1:0098d11d2d55`, `delta:1:2705faddd09d`,
`delta:1:458b1eb85929`, `delta:1:4bc644592b9f`). CELL-1-GEPA therefore tests the three
candidate-bound routes and nothing else, exactly as CELL-2 did.

## The offline four-row dry run (zero contacts)

Full record: `dry-run-v1.md` in this directory. `scripts/flights/batch/gepacell_dry_run.py` composes
the registered smoke cells from the committed fragments over the REAL released GEPA stores and walks
them node by node with `analysis.native_episode_dry_run`: all four rows on the Perception candidate
ids the flight itself produced, a REVISE revisit, and a duplicate-candidate row. **Both forms PASS.**

| row | arm S / R / Pl | twin S / R / Pl |
| --- | --- | --- |
| `slurp:train:000007:audio--1504197557` | 8 / 4 / 4 | 8 / 4 / 4 |
| `slurp:train:000009:audio-1497557594-headset` | 1 / 4 / 4 | 4 / 3 / 2 |
| `slurp:train:000015:audio-1488524781` | 5 / 4 / 4 | 5 / 4 / 2 |
| `slurp:train:000023:audio-1490956038` | 0 / 0 / 0 | 0 / 0 / 0 |

Every walk completes the whole graph on every row and both forms and delivers from the Solver's
sealed draft; the duplicate-candidate row (n=3, distinct=1) walks with 3 candidate projections
receipted; each declined route is receipted with its reason.

Three findings this package registers before contact:

1. **The routes reach cap.** Where CELL-2's retained store selected almost nothing on this roster,
   the GEPA store fills the Reviewer and Planner caps on every row that matches at all. The risk to
   report is volume, not inertness -- which is why the Solver's prompt-fit bound and the E20
   compaction count are both mandatory diagnostics.
2. **Row `slurp:train:000023:audio-1490956038` declines all three candidate-bound routes** on both
   forms: its `iot_hue_lightdim` / `lighton` / `lightoff` candidates reach no value in the store. That
   is the registered expectation, reported and never failed; whether a route serves at population
   level is the arm's own delta-consumption table.
3. **A REVISE revisit acquires a SECOND, DISJOINT slice** (arm Solver 1 / Reviewer 4 / Planner 4 on
   the second visit; 25 distinct value ids over the episode; **zero** duplicate acquisitions). The
   registered invariant is DISJOINTNESS, not emptiness, and that is a deliberate correction of the
   rule CELL-2's driver carried -- at a 200-value store there was no second slice to find, so the two
   rules could not be told apart there. What matters is unchanged: `QueryState` refuses a duplicate
   `retrieved_value_id` and a re-acquisition kills the trajectory (the 2026-09-17 cell B1 abort).

**The arm and the twin are not expected to match per node.** The derangement moves each row's whole
attachment tuple, so a candidate-bound route selects a different slice; only the total authored token
count (7,345) is held. Arm items over the four rows: perception 0 (seeded) / solver 14 / reviewer 12
/ planner 12; twin 0 / 17 / 11 / 8.

## The proofs on the committed tree

- Offline gates, all exit 0: `engineering_base_check.py`, `harness_admission_check.py`,
  `results_ledger_check.py`, `tool_catalog_check.py`, `experiment_handoff_check.py`,
  `finite_completion_policy_check.py`, `stage3_algorithm_label_check.py` and
  `derived_media_confinement_check.py`.
- The composed config and protocol hashes of all eight cells, computed offline by
  `core.config.compose` and `core.config.protocol_hash`: preregistration section 8.
- The offline four-row native-episode dry run on both forms: `dry-run-v1.md`.

**`core.flight.cli check` was NOT run** and no prompt-fit bound is claimed as measured. That check
needs the coordinator's clean-tree cycle against the minted receipt, and it is where
`prepared_artifacts_ok`, the readiness state and `_assess_prompt_budget`'s per-phase bound are
established. What this package registers instead is the model-free worst case each node can render
(528 / 1,035 / 471 / 479 characters at the unchanged caps) and the EXPECTATION -- ALLOW on perception,
reviewer and planner, COMPACT_REQUIRED on the Solver, whose bound already sat 317 tokens over the
live slot's reserve at CELL-2's smaller store. Preregistration section 5 states the estimate and the
method so a surprise reads as a surprise.

## What is registered here

Eight plan documents (`{,twin-}{generation,fit}-plan-registered-v1.json` and their smoke siblings),
`protocol-registered-v1.json`, `registered-facts-v1.json`, `analysis-recipe-v1.json` and
`dry-run-v1.md` in this directory; outside it, the preregistration note, the six config fragments,
the two campaign plans, eight unconsumed DRAFT exposure rows and the runbooks
`gepacell_repin_{smoke,twin_smoke,arm,twin}.sh`, `gepacell_flip_all.sh`, `batch_chain_gepacell.sh`,
`gepacell_read.sh` and `gepacell_dry_run.py`.

## The decision receipt's name

`coordination/slurp-stage3-delta-cell-gepa-r01-v1/` already holds the GEPA PROPOSER cell's
`root-admission-v1.json` (decision id `slurp-stage3-gepa-r01-admission-v1`) and the release pins, so
this cell's receipt is **`cell-admission-v1.json`** (decision id
`slurp-stage3-delta-cell-gepa-r01-admission-v1`). Every fragment, plan, runbook and exposure row in
this package names that path. `mint_decision_receipt.py` hard-codes the output name
`root-admission-v1.json` and would overwrite the proposer's receipt; preregistration section 10 step
0 gives the back-up-and-rename recipe and names the durable fix (an `--out-name` flag), which is not
taken here because a shared tool is not edited during a live flight.

## The lessons this package carries forward

1. **A recovery needs two new identities.** CELL-1 lost two relaunches (zero contacts each) because
   the fit gate binds the BASELINE's `native_contact_fit.attempt_id` and refuses an identity that
   already carries evidence. Both fragments' `failure_policy` say a recovery re-registration needs a
   new generation attempt id AND a new fit attempt id.
2. **A sealed identity is never re-pointed.** The release runbook's fill stage rewrites store pins in
   place, which is right for a held cell and wrong for a consumed one; CELL-1-GEPA is a sibling
   fragment set and CELL-1's and CELL-2's fragments are untouched.
3. **`check` does not walk the episode.** Three CELL-1 launches died at node boundaries `check`
   cannot see. The four-row offline dry run over the real released stores, on the candidates the
   flight actually produced, with a REVISE revisit and a duplicate-candidate row, is a precondition
   of the smoke here.
4. **An inert route is what stopped B9a-rec.** The release's reach block is read BEFORE the fragments
   are written: 448 of 448 reachable on every node, so no route is removed.
5. **An aborted campaign leaves `locks/flight.lock`.** Clear it before the next launch.
