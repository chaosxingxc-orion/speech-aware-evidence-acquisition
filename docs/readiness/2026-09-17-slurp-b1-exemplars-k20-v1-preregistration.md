# Cell B1: speech-keyed exemplar supply to the Solver, preregistration

Status: **PREREGISTERED BEFORE CONTACT — AND BLOCKED.** Author: the B1 preparation agent, worktree
`/home/chao/saea-worktrees/fable-b1-prep`, branch `fable/b1-prep`, base commit `02f2f0af`.
Authority: `docs/superpowers/specs/2026-09-16-slurp-v2-base-program-design.md` section 3 (module M1)
and section 4 (Phase B, cell B1), and the A2 decision
`docs/results/2026-09-17-slurp-a2-exemplar-headroom-audit-v1.md`. This document grants no model
contact; all three cells stay readiness `held` until the coordinator flips them, and they cannot be
flown at all until the blocking gate in section 0 is closed.

Everything recorded here was produced with **zero model, tokenizer, encoder, ASR, scorer and server
contacts**. The resident service was never started, stopped or queried, and cell B0 — in flight from
its own pinned worktree while this was written — was never touched.

## 0. The blocking gate (read this first)

`rails.knowledge_stores.build_knowledge_store_supply` refuses this configuration outright:

```
candidate, explicit, and scoped supply cannot overlap on phase(s) ['solver']
```

The `slot-contracts` store already serves the Solver phase through `candidate_supply` (the anchor's
four-candidate contract, part of the base) while the new `train-exemplars` store serves the same
phase through `phase_supply` (module M1). A per-store collision guard in
`build_knowledge_store_supply` tests each store's explicit specs against the *global* candidate
specs and refuses the overlap, so the combination cannot be constructed.

This is **inherited, not introduced here**. The E3 commit `cfdf08fb` added the routing that composes
a later-phase plain `phase_supply` into `automatic_for_phase`, and its own module comment names this
exact pairing — *"this program's anchor: `slot-contracts` candidate_supply.solver plus the new
`train-exemplars` phase_supply.solver"* — as the case it fixes; but it left the older guard in place
and covered only the `context_supply` pairing with a test. A throwaway experiment fragment on the
**anchor** policy pointing at the committed
`configs/baseline/slurp-native-dual-store-train-fold-a-exemplars-k20-v1.json` raises the identical
refusal at the identical frame.

A second, smaller defect rides along: the committed E3 fragments pin the exemplar knowledge receipt
with `"root": "repo"`, and `core.preparation.verify_source_receipts` accepts only `repository` and
`data`. The three B1 fragments registered here use `repository`; the three committed E3 fragments
still need the same correction.

**Consequence for this registration.** `check`, `prepare-supply`, the four-row smoke and both
campaigns all refuse. `prepared_phase_supply` therefore cannot be pinned, and the three experiment
fragments carry `readiness.requirements: []` rather than a preparation pin. Everything else — the
configs, the plans, the protocol, the six exposure rows, the analysis recipe and the contact-free
evidence that does not need the router — is registered and final. Receipt:
`SPEECHRL_DATA_DIR/coordination/slurp-b1-exemplars-k20-v1/store-router-blocker-v1.json`, with the
raw refusals in `store-router-blocker-v1.log`.

A diagnosed one-line narrowing of the guard was verified **in a throwaway tree, never in this
repository**, and is sufficient for construction and for a model-free `prepare-supply` of all three
cells. It is not applied here: it is a production change that owes its own reviewed engineering item
and its own test, and `rails.knowledge_stores` is one of the five module files whose SHA-256 the
prepared phase-supply artifact identity pins — so an artifact prepared against an unreviewed patch
would be invalid the moment that patch is reshaped in review. Section 0 of the runbook
[`2026-09-17-slurp-b1-exemplars-k20-v1/README.md`](2026-09-17-slurp-b1-exemplars-k20-v1/README.md)
carries the unblocking sequence.

## 1. Question

Do speech-keyed annotated TRAIN exemplars, supplied to the Solver as typed content blocks, improve
official pooled SLU-F1 over the review-off base on TRAIN Fold A 1,080?

A2 settled the availability side and nothing more: at plain k = 20 the twenty neighbours carry the
gold intent on 0.956 of rows, lift union coverage from the sealed 0.8676 to 0.9722, reach type
recall 0.960 and filler recall 0.566, and show no memorisation channel (exact-text-neighbour rate
0.0019, metrics identical to three decimals on the complement). A2 also recorded the open question
this cell answers: *union coverage is availability, not use* — whether the Solver actually escapes
to a neighbour intent is a B1 outcome, not an A2 result.

## 2. Arms

| role | identity |
| --- | --- |
| treatment | `SAEA-SLURP-NATIVE-EXEMPLARS-K20-TRAIN-FOLD-A-V1` / `attempt-slurp-native-exemplars-k20-train-fold-a-generation-v1`, cell `slurp-native-exemplars-k20-train-fold-a-v1`, composed config `39ce13ecae402b31bbd062acb459534b17bf2c57b0041f723304bdd720bdc7f7`, protocol `2ccd722e0319a2daf831bfc01a00aa2cf993ec97a5d7545e9493a97a54cd91c3` |
| twin | `SAEA-SLURP-NATIVE-EXEMPLARS-K20-TWIN-TRAIN-FOLD-A-V1` / `attempt-slurp-native-exemplars-k20-twin-train-fold-a-generation-v1`, cell `slurp-native-exemplars-k20-twin-train-fold-a-v1`, composed config `94df17ed9d6379f5f0152cad750182b7c95b7b07c9ee89f00c817a85567c7a32`, protocol `4735f4b7949c6b2e587d97e5d4df2050b43a1e0ee466689021bf2b435a84bb4d` |
| primary comparator | sealed bytes of `SAEA-SLURP-NATIVE-REVIEW-OFF-TRAIN-FOLD-A-V1` (cell B0), score artifact SHA-256 **PENDING — the coordinator fills it in after B0 finalizes**, run manifest SHA-256 likewise |
| secondary comparator | sealed bytes of `SAEA-SLURP-NATIVE-DUAL-STORE-TRAIN-FOLD-A-ANCHOR-RECOVERY-V1`, score artifact SHA-256 `7360876322488e5fda689fcafda00e90da2ebf559e5a35e635c550f940202b47`, run manifest `049ac230e536bc6c8fe45bc847756ba486c4904e9c7602c698157f78d70c0152`, official aggregate pooled SLU-F1 48.53, intent 77.96, scenario 84.81, action 79.26, pooled span F1 29.50 |

Neither comparator is ever re-flown or re-scored. **If cell B0 lands HARMFUL, the coordinator
re-bases both cells on the sealed anchor before launch**, exactly as the spec's Phase B table
directs; the arm and twin fragments then change their base and every hash in this package is
recomputed.

All arms share the roster `docs/receipts/rosters/slurp-evo-fold-a-v2.json` (SHA-256
`1fe7908c31396774d7535fdf37bd791762215c324999d66ed7beb9e7b2f9033d`), split `SLURP-EVO-FOLD-A-V2`,
split identity `61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6`, role `discovery`,
and the resident session `serving-slurp-native-candidate-five-train-a-np4-v1` (attach only).

## 3. The one factor, and what it is not

Moved against cell B0's own committed baseline: `knowledge_stores` gains **one** named store,
`train-exemplars`, taken verbatim from the E3 deliverable. Its Solver block is plain top-k with
k = 20, `saea-fuse-supplyfilter-v1` at m = c = top_l = 20, `saea-rank-wcos-prior-agree-v1` with
w_cos = 1 and w_prior = w_agree = 0, tau 0.0, keyed by the row's own sealed Fold A full-utterance
speech vector in the `content` dimension. The store's release and snapshot are pinned
(`171aa4a8…` / `4c498dc0…`) over a 9,354-utterance pool that excludes every utterance with a
recording in TRAIN Fold A, Fold B or DEV-1000. Alongside it move only bookkeeping: this cell's own
`native_contact_fit` run and attempt ids at the unchanged 2-contact ceiling, the two speech-feature
identity ids (provenance only — they ride the audited payload envelope and never the messages), the
exemplar store's own `preparation_source_receipts` row, and two free-English note blocks.

Held identical: the review-off role graph (reviewer and planner `max_iterations` 0, `max_revisions`
0, `review_loop` off, policy `phase-native-candidates-solve-v1`, two contacts per row), the roster
and split, the model fragment and resident geometry, the promoted speech packets, the
`intent-boundaries` and `slot-contracts` stores with their release and snapshot hashes and the
four-candidate supply contract, **every instruction template** — the exemplars reach the model as
typed content blocks on the acquire transition, never as instruction text — the inert `phase_tools`
block, and the scorers.

The prepared first-phase Perception supply does not move either. `prepare_phase_supply` prepares the
program's **first** phase only; the Solver supply is resolved live at dispatch. In the throwaway
diagnostic tree the rebuilt Perception artifacts for all three B1 cells reproduced the sealed cell B0
artifact `output` and the sealed anchor artifact `output` **exactly, on all 1,080 rows** (and the
smoke against B0's own smoke artifact on its 4 rows). The same equality must be re-established
against this repository once the blocking gate closes, before anything flies.

## 4. The twin

Every row receives another Fold A recording's sealed full-utterance speech vector, drawn by a seeded
within-delivered-scenario derangement (`scripts/build_slurp_exemplar_twin_vectors.py`, seed
20260917). Buckets come from the sealed anchor's **delivered** scenario, never gold. Independently
recomputed here from the two sealed vector files alone
(`coordination/slurp-b1-exemplars-k20-v1/twin-derangement-proof-v1.json`):

- 1,080 rows, ids identical and in the same order as the parent file;
- 1,080 distinct parent vectors, so the source of every twin row is unambiguous;
- **0 fixed points** — no row receives its own vector;
- it is **not a strict bijection**: exactly one source vector is delivered to two rows and exactly
  one is never delivered. That is the arithmetic consequence of the provenance's own declared
  `cross_group_rows: 1`, which merges the two singleton buckets (`recommendation_locations` and the
  residual). The property the twin needs — every row keyed by a real, foreign Fold A speech vector,
  token-matched by construction — holds on 1,080 of 1,080 rows; the strict-permutation property does
  not, and is recorded rather than glossed.

Because the store, k, fuse policy, rendering and contact count are identical, the twin's exemplar
block is token-matched to the arm's by construction, and `arm minus twin` isolates the retrieval key.

## 5. Metrics

Primary: **official pooled SLU micro F1** from `slurp-slu-official-train` (pinned official
`evaluate.py`, `slurp-official-8eb16545`), natural mixture, one complete score per manifest through
`core.scoring_batch`, never sharded.

Secondaries: intent (joint scenario+action) accuracy, scenario accuracy, action accuracy, official
pooled span F1. Reported beside them: per-row mean official SLU-F1 and per-row mean exact slot F1,
saves/harms/ties with the exact two-sided McNemar p.

Diagnostics, mandatory in the verdict and never gates:

- **candidate-union coverage realized in the delivered answer**, against A2's availability number
  0.9722 — the direct answer to A2's own open question;
- **Solver escape-to-neighbour-intent rate**: the share of rows whose delivered intent is absent from
  the sealed Perception candidates but present among the supplied exemplar intents;
- **exemplar token volume actually rendered per row**, against the 1,083-token estimated maximum.

`delta = arm minus comparator`, in percentage points; negative means the arm is worse.

## 6. Resampling and tables

Paired whole-speaker cluster bootstrap, **10,000 draws, seed 20260915**, CI95 for advancement and
CI90 for diagnostics, both as percentile pairs of the same retained replicate sequence. Sensitivity:
paired scenario-stratified row bootstrap, same draws and seed. Every verdict carries the per-scenario
table in both the natural-mixture and the equal-scenario weighting; the equal-scenario delta is
reported beside the natural-mixture point estimate and never replaces it. Speaker clusters come from
the released roster metadata (125 speakers, 18 scenarios of 60 rows, 523 headset and 557 far-field
rows).

## 7. Decision rule (fixed here, copied from the spec)

Null half-widths from `docs/readiness/2026-09-09-slurp-own-null-replicate-v1-verdict.md`: intent
0.92, SLU micro 1.18, scenario 0.83, action 0.98 percentage points.

- **ADMITTED** if the CI95 lower bound of the pooled SLU delta is greater than 0 **versus the primary
  base AND versus the twin**, intent is non-inferior within 0.92 pp, the normalised scorer agrees in
  sign, and no scenario loses intent beyond the null band.
- **NEUTRAL** otherwise; it enters the default plan only if it lowers cost.
- **HARMFUL** otherwise, when a guard fails on the losing side.

No repeat-to-pass: the verdict is read once, from the single official score of each complete
manifest. Scenario and action margins are diagnostics for the per-scenario table, not gates.

## 8. Cost reporting (mandatory in the verdict)

Per arm: actual generation contacts (expected exactly 2 per row, 2,160 in total); contacts per row
(expected 2.000); actual repeated speech seconds (expected 2 × 3,084.528 = 6,169.06); actual FIT
endpoints (expected 4 per realized contact, 8,640 in total); GPU hours read from the serving monitor
(`SPEECHRL_DATA_DIR/serving/serving-slurp-native-candidate-five-train-a-np4-v1/monitor.jsonl`) over
each lease window, never a wall-clock guess; mean latency, slot occupancy and duty cycle from the
same monitor; exemplar token volume actually rendered; preprocess and scoring wall time.

Registered ceilings per full cell, which are bounds and not targets: 2,160 generation calls, 8,640
FIT endpoints, 6,170 repeated speech seconds, 2.0 fit-inclusive GPU hours, one official complete
scoring job, zero ASR, encoder, task-contract and paid-API calls. Smoke: 8 / 32 / 25 s / 0.2 GPU-h
and zero scoring jobs.

## 9. Prompt fit

The 24,576-token serving slot. Measured base, from the anchor's own 5,417 sealed native contact-fit
receipts: `solver:0` required at most **13,157** tokens (minimum margin 11,419) and `perception:0` at
most 4,270 (minimum margin 20,306), over 1,080 contacts each, all fitting. Cell B0 renders the same
Solver envelope minus 8 bytes.

The exemplar block, from `scripts/estimate_slurp_exemplar_prompt_fit.py` over the real sealed
snapshot and the real sealed vectors, cross-checked byte-for-byte against the real
`KbFacetProvider`/rank/fuse pipeline on 5 random rows at both k values
(`coordination/slurp-b1-exemplars-k20-v1/exemplar-prompt-fit-v1.json`): at k = 20, mean 2,974.4
chars, p50 2,907, p95 3,796, **max 4,332** — a chars/4 proxy of mean 743.6, p95 949.0, **max
1,083.0** tokens. At the k = 12 fallback, max 2,730 chars / 682.5 proxy tokens.

Upper bound for the B1 Solver request: **13,157 + 1,083 = 14,240** required tokens, a margin of at
least **10,336** against the slot. The two maxima are taken over different rows, so the sum is a
strict upper bound and not a realized worst case. k = 12 is not needed. The runtime `check` receipt,
which is the authority, is blocked with the cell.

## 10. Containment

`scripts/check_slurp_exemplar_containment.py` reproduces
`rails.runner._assert_agent_control_excludes_knowledge_payloads`'s exact rule (casefolded substring
test, 8-character protected-payload floor) over the 9,354 rendered `annotated-exemplars` values
against the composed instruction text of every phase: **0 collisions** across all six composed
instruction texts (context 35,011 chars of label inventory, perception 960, planner 193, reviewer
435, solver 1,129, perception `fill_params.source_catalog` 35,011). No no-example task-contract
projection is needed. Receipt: `coordination/slurp-b1-exemplars-k20-v1/containment-v1.json`.

## 11. Failure rule

The first failure stops the cell and preserves everything. No automatic restart, replay, row
filtering, roster, role-graph, prompt, geometry or cap change, and no silent recovery. At most one
root-diagnosed recovery re-registration per run; a second failure closes that flight and the fix must
be proven on a four-row dry run before another mechanism is admitted. A failed four-row smoke stops
B1 until the fix is proven on that same four-row roster.

## 12. What is NOT claimed

- No superiority, generalization, paper-scale or held-out claim. TRAIN Fold A is an exposed discovery
  roster.
- No component-causal attribution beyond the one added store. An admitted result says exemplars
  supplied this way pay for themselves in this configuration, not that exemplar grounding is
  generally good.
- A2's availability numbers are not predictions of the delivered answer. Union coverage 0.9722 is
  what is *available*; B1 measures what is *used*.
- Nothing about Fold B, DEV-1000 or the test split; they stay unread.
- The twin is a token-matched retrieval-key control, not an information-free control: twenty real
  annotated exemplars still reach the Solver in the twin arm.
- A structural smoke result is never a quality result.
- The diagnostic run in the throwaway tree is evidence about the *blocker*, not about this cell's
  quality; no number in it is registered.

## 13. Analysis recipe

`docs/readiness/2026-09-17-slurp-b1-exemplars-k20-v1/analysis-recipe-v1.json` pins the four score
artifacts, the roster metadata
(`analysis/SAEA-SLURP-TRAIN-A-DIRECT-ANCHOR-RELEASE-PAIRED-ANALYSIS-V1/roster-metadata.json`, SHA-256
`07f4cd83b83d83d65500a328e0a38421ede575195c63ae118def0d1006c14e34`), the shared estimators
(`analysis.null_calibration_cli.rows_for`, `analysis.null_calibration.pooled_f1`,
`analysis.paired.resampled_statistic`, `analysis.paired.paired_contrast`), the seed, the draws, the
two interval levels, the four contrasts and the metric list. It mirrors cell B0's recipe and reuses
the released paired-read tooling of the 2026-09-17 TRAIN A direct anchor release;
`analysis.score_compare_cli` is deliberately not the runner because it hard-codes CI90 and DEV
population names.

## 14. Pre-contact evidence on file

All under `SPEECHRL_DATA_DIR/coordination/slurp-b1-exemplars-k20-v1/`, outside the repository so no
receipt can dirty the tree the scoring gate reads.

| receipt | SHA-256 | what it proves |
| --- | --- | --- |
| `store-router-blocker-v1.json` | `a4a215493b5a43a7dd869b10b2cd38de390d43ce11f87ba34889a0c361e9a27e` | the blocking gate, its inheritance from E3, the diagnosed sufficient change and what is still unproven |
| `store-router-blocker-v1.log` | — | the raw refusals for all three B1 cells |
| `composed-hashes-v1.json` | `86b7e9637bc6f3b634c3c52f1b869d359cdbe380e303ba4b2d32bbd90b48f236` | the composed and protocol hashes, the anchor method check, and the cell B0 hash drift on master |
| `containment-v1.json` | — | 0 collisions between the 9,354 exemplar values and every composed instruction text |
| `exemplar-prompt-fit-v1.json` | — | the k = 20 and k = 12 block size distributions, provider-verified |
| `twin-derangement-proof-v1.json` | — | 0 fixed points on 1,080 rows, and the bijection shortfall recorded honestly |
| `plan-hashes-v1.txt` | — | the SHA-256 of every plan document in the readiness directory |
| `ledger-parse-v1.json` | — | `contracts._parse_ledger_tables` sees all six rows exactly once, each `consumed = no` |

Blocked and therefore absent: `check` receipts for the three cells, `prepare-supply` receipts against
this repository, and the request-envelope comparison against the cell B0 rendered requests.
`core.flight.cli wire-check` is unavailable for any native-episode cell for the same reason it was
for B0 and for the anchor: `FlightRuntime._dispatch_phase_program` refuses a native episode whose
transport is not the real shared speech renderer, and `wire_check` installs a text transport double.
