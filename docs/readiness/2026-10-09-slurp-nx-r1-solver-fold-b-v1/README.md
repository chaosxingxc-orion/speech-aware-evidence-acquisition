# Cell NX-R1-SOLVER: the first same-flight node-template column (Solver instruction template, TRAIN Fold B)

Registered before contact 2026-10-09 at study commit `e6345dd26e821624746f38b5f7d2627dce961418` (branch `fable/nx-r1-register`, base
master `d200fa8f2`) under the NX node-extreme programme (`docs/readiness/2026-10-09-slurp-nx-node-extreme-programme-v1.md`: C0, C1 E1/E2/E5,
C2 R1, C4, F2; owner decisions 228-234 as ruled in `docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md`, section "Decisions
228-236"). Both cells **HELD**. Nothing here authorises a flight, a flip, a receipt or an admission entry; the five ledger rows are DRAFTs
and none is countersigned. Development numbers only (owner decisions 28 and 86), never a test claim.

## 1. What it is

One flight on TRAIN Fold B (1,080 rows, the same roster the P-SV cells read: `docs/receipts/rosters/slurp-evo-fold-b-v2.json`, split
identity `4407794c...`) of the **review-off COMP-1b module graph** in which the Solver is contacted **seven times per row over the
same state and the same evidence**, once per instruction template:

| arm | template (pinned relpath, sha256) | role |
| --- | --- | --- |
| `r1-c1` | `configs/probes/nx/solver/r1/r1-c1.txt` `715e6bb1...` | value-in-supply extraction (declared +1.80 pp) |
| `r1-c2` | `.../r1-c2.txt` `45bb164d...` | copy suppression with a heard-span requirement (+0.63) |
| `r1-c3` | `.../r1-c3.txt` `89b81e97...` | explicit empty-entity decision, decision 199 (+0.89) |
| `r1-c4` | `.../r1-c4.txt` `d375f16d...` | the ChatGPT donor ported onto the locked template (+0.6, author prior) |
| `r1-c5` | `.../r1-c5.txt` `3b4cb0f1...` | contract tightening and TRAIN-side filler conventions (+0.28) |
| `aa` | none (`replicate_of lock`) | the in-chain twin: the within-flight null of this node column |
| `lock` | none: the locked template `configs/probes/slurp_native_role_solver_v2.txt` `18bff5c5...` | the **delivering** arm, untemplated, last |

Only the delivering arm's answer is carried forward; its request is the locked plan's request byte for byte (invariant I7). The five
templates are hand-written (author: Opus 5.5 from aggregate tables; `docs/readiness/2026-10-09-slurp-nx-r1-solver-candidates-v1/README.md`);
the harness accepted the `configs/probes/nx/solver/r1/` subdirectory, so **no file was moved** and the candidates README needs no edit.

**Base.** The COMP-1b composition as a consumption-module block on lock v2.1 (`native_episode.consumption_module`): `agree-vote-seed`
(w_agree 1.0, k 60, the Fold B vote table `SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-FOLD-B-V1`) and `centroid-boundary-key`
(`SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1`) ON, every other component OFF, with the Reviewer loop **OFF** (`review_loop: off`:
Perception then Solver; Reviewer and Planner `max_iterations` 0, `max_revisions` 0; `phase_tools` empty, so no role renders a tool schema,
the fix named by `docs/results/2026-10-09-slurp-nx-solver-parse-root-cause.md`). The compiler writes every policy block (it is the module's
review-off program at the ceiling the harness computes for the arm count: `phase-native-module-v1-c8`, ceiling 8 = 2 + (7 - 1)); the loader
refuses a fragment whose blocks differ from the compiled ones. Decoding, knowledge, supply, geometry (`slurp-np4`, 4 x 24,576, session
`serving-slurp-native-candidate-five-train-a-np4-v1`), `finite_completion_policy` `deliver-latest-or-abstain` and `react_exhaustion_policy`
`continue-without-answer` are the COMP-1b module cell's own (the Fold B pins are the P-SV-4 fragments'). The runtime delivery normaliser
is `saea-deliver-normalise-v3`, unchanged: **v4 and v4g are NOT wired into the cell** (section 7).

`stage3_algorithm`: `none` (decision 101; the P-SV precedent: an instrument cell, no operator, no credit, no update).

Derived by `scripts/flights/nx/derive_slurp_nx_r1_cells.py`; shared ids in `scripts/flights/nx/nx_r1_family.py`; package written by
`scripts/flights/nx/write_slurp_nx_r1_registration.py`.

## 2. Why, and the declared effect (decision 192: on file before flight)

Programme R1: the Solver is the owner's focus node and the measured weak point (MISSING 188 and SPURIOUS 264 raw entities on Fold A; 161 of
414 empty-gold rows false-filled). The exchange rates (`docs/results/2026-10-09-slurp-nx-exchange-rates-offline.md` section 0): one extra
raw-exact Solver row buys **+0.056 pp** of official pooled SLU-F1; the 1.5 pp bar costs about 27 raw-exact rows.

**Declared round effect +1.80 pp**, carried by `r1-c1` alone: 117 MISSING entities whose value is in the Solver's view (Fold A; DEV 108) x
the measured M1 delivered-filler conversion **0.2471** (`docs/results/2026-09-28-slurp-w5-slot-exemplar-offline-estimate.md`) = 28.9
recovered entities x 0.0621 pp = **+1.80 pp** (~32 raw-exact row equivalents; DEV sensitivity +1.53 pp). Harm netting: the break-even
precision of the new emissions is 0.318; at the E5-1 precision 0.25 the arm is -0.72 pp, so the range is [-0.72, +1.80]. The other four
arms declare +0.63, +0.89, +0.6 (author prior, not a measured conversion) and +0.28 and are below the floor alone. `claims_benefit` is
true **for the round only**, carried by c1. Fold B has no sealed table; Fold A counts are its proxy.

## 3. Measurement (`registered-facts-v1.json`, canonical `stage3_measurement`, keyed by run id)

`measurement_design: same-flight-node-column`; primary metric key `slu` with the node-local primary named: **raw first-answer entity
exact-set per row** (E2 reader, per arm minus `lock`, paired per row), quoted on delivered SLU-F1 through the exchange rate; intent is the
guard (rows differing from `lock` <= 7, the 0.65 pp floor of 1,080). Expected effect **1.80 pp**, rows 1,080, in-chain A/A = the `aa` twin
(`aa_arm_id`), claim ceiling `nominated`, tuning roster `SLURP-EVO-FOLD-A-V2` (the contrast tables that shaped the candidates), read roster
`SLURP-EVO-FOLD-B-V2`. **Floors (provisional, borrowed):** SLU 1.49 pp and intent 0.65 pp at n = 1,080, borrowed from
`same-flight-supply-variant` per the instrument README until a node-column cell measures its own twin null; 1.80 sits at about 1.2 x the
floor, knowingly near it. The bar of the read is the `aa` twin null of this flight: `|aa - lock offset| + its CI95 half-width`.
`variant_cost`: +6 Solver contacts per row, +18,928.78 speech seconds per flight (6 x 3,154.797 s). The smoke is a `form-proof`
(no benefit claim, fewer than 200 rows). The full decision rule is fixed in `protocol-registered-v1.json` and the preregistration.

## 4. FIT numbers (model-free; `fit-measure-v1.json`, `scripts/flights/nx/nx_r1_fit_measure.py`)

Source: the first Solver visit of every row of the **sealed COMP-1b Fold A arm** `SAEA-SLURP-STAGE3-COMP1B-FOLD-A-V1` (1,080 visits; trace
sha256 `7b2d7cfd...`; the delivering arm renders the same request on the Fold B sibling roster). Realised first-Solver prompt 4,987 to 14,641
tokens (mean 10,486.3); 29 to 53 supplied items (mean 41.6). The template frame:

| quantity | value | how |
| --- | --- | --- |
| `slot_tokens` / `completion_ceiling` | 24,576 / 512 | live slot; Solver `max_tokens` |
| `max_supplied_items` | 55 | measured maximum 53 + registered headroom 2 |
| `base_prompt_tokens` | 2,000 | DECLARED structural floor (the least-squares intercept of this arm is negative: a few very wide slot cards drive long prompts) |
| `tokens_per_supplied_item` | 235 | max over rows of `(prompt - locked template tokens - base) / items`, so base + template + items x 235 bounds every realised prompt of the sealed arm |
| template tokens (ESTIMATED, 3.5 chars/token, no tokenizer) | lock 323; c1 430; c2 413; c3 434; c4 431; c5 413 | `ceil(bytes / 3.5)` |
| arm prompt estimates | 15,248 (lock) to 15,359 (c3) | vs the prompt limit 20,990 = 24,576 - 3,072 - 512 - 2 |

Plan budget (the harness FIT rule `planned_model_calls >= rows x ceiling`, run-cumulative): arm **8,640** generation contacts (1,080 x 8),
**34,560** FIT endpoints (x 4), **25,239** speech seconds (ceil(3,154.797 x 8)), **3.5** planned GPU hours (the ceiling, not a target: at the
P-SV-3 flight's 57 contacts per minute the 8,640 contacts take about 2.5 h); smoke 32 / 128 / 82 / 1.0. The realised fit of every arm request
is measured again at dispatch by `native_contact_fit`; the template tokens are the one estimated input.

## 5. The read (`analysis-recipe-v1.json`, `scripts/analysis/nx_r1_read.sh`, READ row `SAEA-SLURP-STAGE3-NX-R1-SOLVER-FOLD-B-COLUMN-READ-V1`)

`bash scripts/analysis/nx_r1_read.sh [--dry-run] [--rescore] [--skip-offline]`, after the seal and after the READ row is countersigned.
Model-free. In order: (1) the E2 reader `scripts/analysis/slurp_nx_solver_column_read.py` per arm vs `lock` (parse validity, exact-set =
primary, empty-gold false fill, non-empty exact, per-slot-type counts; whole-utterance cluster bootstrap CI95, 10,000 draws, seed 20260915,
paired Wilson share); (2) **one official column scoring per arm** (`stage3_rollout_score.py --mode supply-variants`, `slurp-slu-official-train`,
seven jobs, never sharded), then the twin null `aa-vs-lock` and `<candidate>-vs-lock` through `stage3_paired_read.py` (the column-arm
tool requires cluster key `sample_id`, so these are paired ROW bootstraps with 10,000 draws and seed 20260915; the whole-utterance number is
the E2 reader's and the offline step's); (3) the offline v4 / v4g columns (section 7). Rule: a candidate is NOMINATED iff the node-local
exact-set CI95 lower bound > 0, no secondary loss, the intent guard holds, and the official SLU-F1 point delta exceeds the twin bar; plateau
rule: two evaluated rounds without a NOMINATED arm lock the delivering template; a nomination is confirmed once on TRAIN Fold A as a two-arm
column before any lock.

## 6. Review-off vs full graph

The delivering `lock` arm of this flight is review-off on Fold B. It will be compared **cross-flight** to the P-SV-3 `a-agree` **delivered**
column on the same Fold B (`docs/results/2026-09-30-slurp-psv3-fold-b-branch-read.md`; official SLU-F1 columns exist, the A column at
61.78 % first-visit, the flight's own complete official TRAIN score on file), with the **P-SV-3 `t-twin` offset as the flight-offset bound**
(SLU +0.43 [-0.11, +1.01], bar 0.99 pp; the cross-flight bar of the instrument note is **2.5 pp**,
`docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md`). **No extra flight.** If review-off is within the bar, review-off is
locked (decision 232 / programme F2); if the full graph wins by more than 1.49 pp SLU with CI95 lower bound > 0 the drop is revisited. Two
caveats the comparison must carry: the P-SV-3 A arm is the AGREE graph without the centroid key (COMP-1b's second component, DEV SLU +0.53
[-1.04, +2.09] over the A/A, so up to about half a point of the gap is not the Reviewer loop), and the P-SV-3 twin is a same-flight
first-visit column twin, not a request-identical second flight; the cross-flight bar, not the twin, is the binding number.

## 7. Offline post-processing columns v4 and v4g (0 GPU)

The recipe declares two OFFLINE columns over **every arm's delivered column**: **v4** (`saea-deliver-normalise-v4`: the five-rule set
fx-article, fx-oclock, scope, ti1, ee10 of `docs/results/2026-10-09-slurp-nx-postprocessing-v4-offline-read.md` section 6) and **v4g** (v4 with the
two TRAIN-only guards `ee-wilson` and `ti-expressible` of `docs/results/2026-10-09-slurp-nx-postprocessing-v4-audio-attribution.md` section 4),
with the pinned TRAIN statistics `SAEA-SLURP-V4-TRAIN-STATISTICS-V1` (sha256 `01e6a019...`). Contrasts: `v4(X) - X`, `v4g(X) - X`,
`v4g(X) - lock`. The rule definitions live in `scripts/analysis/slurp_nx_postproc_v4_search.py`; the application of the registered normalisers to a sealed column is `scripts/analysis/slurp_nx_postproc_v4_apply.py --apply v4|v4g --pool <run>/<attempt> --column <arm id>` (on master since merge `7bfc09b3b`, after this branch's base), which `nx_r1_read.sh` calls and which the package does not implement. **Known blocker:** that driver refuses any run whose roster intersects TRAIN Fold B ("Fold B is not read by this script"); the R1 run is Fold B, so the refusal must be lifted for this one recipe before the offline step runs (the read driver exits 10 and names it; `--skip-offline` defers the step). **The R1 delivering-arm
(`lock`) column on Fold B is the fresh confirmation roster for v4g** (Fold A located the failure the guards address, so it cannot confirm
them): the lock rule is `v4g(lock) - lock` with CI95 lower bound > 0 here. The cell's runtime delivery normaliser stays v3.

## 8. What the coordinator does next (nothing was done here)

1. Merge this branch (a docs/scripts/config merge; the instrument merge `c474b79af` is already on master). Re-read the five DRAFT rows.
2. **Countersign** the four flight rows (arm, arm FIT, smoke, smoke FIT) in `docs/exposure-ledger.md` (section "NX round R1"); the READ row
   stays a draft until the seal.
3. **Mint the receipt:** `python scripts/flights/nx/nx_r1_mint_receipt.py` (writes `coordination/slurp-nx-r1-solver-fold-b-v1/root-admission-v1.json`,
   decision id `slurp-nx-r1-solver-fold-b-admission-v1`, four eligible run ids; refuses to overwrite; `--dry` first).
4. **Flip loop at the flight commit:** `bash scripts/flights/nx/nx_r1_flip.sh` (smoke then arm through `repin_loop_generic.sh` /
   `scripts/flights/nx/nx_r1_repin_cell.sh`; converges at one HEAD, writes `/home/chao/nxr1-flight-commit.txt`; mints each cell's own first-phase
   supply, item E16; never `--allow-output-change`). The instrument merge changed hashed sources, so every pinned cell needs this pass; run
   no concurrent merge.
5. **Queue** through the batch driver: `bash scripts/flights/nx/batch_chain_nx_r1.sh` (smoke first, then the one-cell campaign on `slurp-np4`).
6. After the seal: countersign the READ row, then `bash scripts/analysis/nx_r1_read.sh` (`--dry-run` first).
7. After the read: the v4g lock check (section 7), the review-off comparison (section 6) and, for a NOMINATED arm, the Fold A two-arm
   confirmation registration.

**Recovery 1 (smoke), 2026-10-09 -- the cell's single root-diagnosed recovery re-registration.** The four-row smoke attempt
`attempt-slurp-native-stage3-nx-r1-solver-fold-b-smoke-4-generation-v1` (run `SAEA-SLURP-STAGE3-NX-R1-SOLVER-FOLD-B-SMOKE-4-V1`) was OPENED,
spent 32 contacts / 81.453 speech-seconds and failed at `runtime.seal()` on the template-variant delivery validator (fixed on master in
`6633c9251`; tests `tests/unit/test_template_variants_delivery.py`). A (run_id, attempt_id) pair is a one-time key, so the smoke is re-flown
WHOLE under the new attempt ids `...-smoke-4-generation-rec1-v1` and `...-smoke-4-fit-rec1-v1` (`nx_r1_family.SMOKE_RECOVERY`); the failed
attempt stays preserved and unread. The arm never started and keeps its attempt id and its rows. The re-fly also proves the fixed seal path on
the GPU, which is what the smoke is for. Rule: a second failure closes the cell; the fix is proven on a four-row dry run. Steps 4 and 5 above
run unchanged (the flip loop rewrites the smoke plan hash and composed config hash; the minted supply pin and admission receipt stay valid, the
receipt being keyed by run id).

**Recovery 1 amended (smoke), 2026-10-09 -- rec1 -> rec2, run-cumulative budget.** The recovery attempt
`attempt-slurp-native-stage3-nx-r1-solver-fold-b-smoke-4-generation-rec1-v1` was registered with the same plan budget as the failed first
attempt (32 calls / 82 speech-seconds), but `core/model/adapter.py` enforces `planned_model_calls` and `planned_speech_audio_seconds` of the
registered plan run-cumulatively across all attempts of a run id (it counts what other attempts already spent). The first attempt had spent 32
calls / 81.453 speech-seconds, so rec1 was refused PRE-CONTACT ("call budget exhausted: ... allows 32 calls (32 already spent by other
attempts on this run)"); its attempt record is OPENED with 0 contacts and, a (run_id, attempt_id) pair being a one-time key, it cannot be
reused. Coordinator ruling (Fable 5.1, 2026-10-09): the rec1 refusal is a pre-contact registration defect of the recovery itself, not a second
flight failure; the single recovery re-registration is AMENDED to attempt ids `...-smoke-4-generation-rec2-v1` and `...-smoke-4-fit-rec2-v1`
with a run-cumulative budget over the attempts (`nx_r1_family.SMOKE_ATTEMPTS_BUDGETED = 2`): `planned_model_calls` 64 (32 spent by attempt 1 +
32 for rec2; rec1 spent 0), `planned_speech_audio_seconds` 164, family caps generation 64 / native 64 / FIT 256 / audio 164, GPU-hours 1.0
unchanged. The arm's numbers (8,640 / 25,239 / 34,560) are untouched. The minted `prepared_phase_supply` pin is preserved byte for byte; the
rest of Recovery 1 stands.

**Recovery 1 amended again (smoke), 2026-10-09 -- rec2 -> rec3, structural FIT cap.** The rec2 attempt
`...-smoke-4-generation-rec2-v1` (reserved 64 calls) was refused PRE-CONTACT (0 contacts; no FIT attempt records exist) at
`core/preparation_fit.py` `build_native_contact_fit_gate`: the FIT `contact_cap` must equal `rows x program.max_contacts x
endpoints_per_contact` = 4 x 8 x (max_speech_packets + 3 = 4) = 128 exactly, and the rec2 amendment had scaled it by the attempts multiplier
to 256. The FIT cap is a structural per-attempt number, never run-cumulative. Coordinator ruling: a second pre-contact registration defect of
the recovery itself, not a flight failure; the single recovery re-registration is AMENDED to `...-generation-rec3-v1` / `...-fit-rec3-v1`.
Numbers: FIT `contact_cap` and family `fit_endpoint_calls_cap` 128 (`nx_r1_family.fit_contact_cap`); the generation budget stays
run-cumulative (`planned_model_calls` 64, audio 164, generation/native caps 64); the FIT plan's `planned_model_calls` is 128. The arm is
unchanged. `tests/unit/test_nx_r1_cell_registration.py::test_pre_contact_preflight_*` now asserts every model-free gate the worker applies
before its first contact, for both cells. The minted `prepared_phase_supply` pin is preserved byte for byte.

## 9. Offline verification (2026-10-09, WSL, worktree; zero model, server, GPU or tokenizer contact)

* Dry run on the four-row smoke (`scripts/flights/nx/nx_r1_dry_run.py`, the harness's `analysis/native_episode_dry_run` walk, canned Perception and
  Solver answers only): 4/4 rows walk `perception -> solver`, the Solver node carries the seven arms in declared order
  `r1-c1 r1-c2 r1-c3 r1-c4 r1-c5 aa lock` with `lock` delivering and last, the twin and `lock` render the locked instruction
  (`18bff5c5...`, 1,129 characters), the five candidates render their own distinct instructions (1,505 / 1,443 / 1,517 / 1,508 / 1,444 characters),
  every arm is supplied the same 39 evidence items, program `phase-native-module-v1-c8`, max contacts 8.
* `core.flight.cli check` (report-only preflight) on both cells: composed config hashes equal the registered ones (arm `5be18a36...`,
  smoke `e657fc79...`), 1,080 / 4 samples, geometry 4 x 24,576, `blockers` none. Its synthetic worst-case Solver render reads `COMPACT_REQUIRED`
  (operational margin -330 arm / -305 smoke), the same profile as the flown COMP-1b cell's own ready check (-317); realised prompts are far
  lower (section 4).
* Gates and tests: see the hand-off report; `flight_registration_check.py` launch mode on the two held cells reports exactly the expected
  pre-countersignature findings (`not-ready`, `row-not-countersigned`, `receipt-missing`, `registered-supply-binding` until the flip) and
  none of the node-column findings added with this package (`aa-arm-missing`, `variant-cost-mismatch`, `variant-claim-not-nominated`,
  `template-summary-mismatch`).

## 10. Files

`README.md` (this), `registered-facts-v1.json`, `protocol-registered-v1.json`, `generation-plan-registered-v1.json`, `fit-plan-registered-v1.json`,
`smoke-generation-plan-registered-v1.json`, `smoke-fit-plan-registered-v1.json`, `analysis-recipe-v1.json`, `root-admission-draft-v1.json`,
`fit-measure-v1.json`; beside the package `docs/readiness/2026-10-09-slurp-nx-r1-solver-fold-b-v1-preregistration.md`. Fragments:
`configs/baseline/slurp-native-stage3-nx-r1-solver-fold-b{,-smoke-4}-baseline-v1.json`, `configs/experiment/slurp-native-stage3-nx-r1-solver-fold-b{,-smoke-4}-v1.json`,
`configs/campaign/slurp-native-stage3-nx-r1-solver-fold-b-v1.json`. Scripts: `scripts/flights/nx/*`, `scripts/analysis/nx_r1_read.sh`.
Run ids: `SAEA-SLURP-STAGE3-NX-R1-SOLVER-FOLD-B-V1` / `-FIT-V1`, `-SMOKE-4-V1` / `-SMOKE-4-FIT-V1`, read `SAEA-SLURP-STAGE3-NX-R1-SOLVER-FOLD-B-COLUMN-READ-V1`.
