# Cell NX-R6-PERCEPTION: the first Perception node-template column (Perception instruction template, TRAIN Fold B), a measurement cell

Registered before contact 2026-10-10 at base commit `fc0c0fc14a3b080e04752618188d798628471a76` (worktree `/home/chao/saea-worktrees/sonnet-nx-r6`,
branch `sonnet/nx-r6-engineering`, base master `fc0c0fc14`) under owner decisions 245-248 (design of record
`docs/readiness/2026-10-10-slurp-nx-r6-node-local-then-cascade-design-v1.md` sections 2.2, 4 and 6; candidates
`docs/readiness/2026-10-10-slurp-nx-r6-perception-candidates-v1/README.md`; instrument
`docs/readiness/2026-10-10-slurp-nx-perception-template-column-instrument-v1/README.md`). Both cells **HELD**. Nothing here authorises a flight,
a flip, a receipt or an admission entry; the five ledger rows are DRAFTs and none is countersigned. Model-free: no model, server, tokenizer, GPU,
network or paid-API contact was made to write it. Development numbers only (owner decisions 28 and 86), never a test claim.

## 1. What it is

One flight on TRAIN Fold B (1,080 rows, 392 empty-gold; roster `docs/receipts/rosters/slurp-evo-fold-b-v2.json`, split identity `4407794c...`; the
roster ids are the NX R1 cells': tuning `SLURP-EVO-FOLD-A-V2`, read `SLURP-EVO-FOLD-B-V2`) of the **review-off COMP-1b module graph on lock v2.2**
(lock v2.1 with the v4g delivery normaliser, module step 7: the R5 arm's base) in which the **Perception node is contacted five times per row over
the same state and the same evidence**, once per instruction template, and **each non-delivering arm is followed by its own first-visit Solver
contact** (the locked Solver template) over that arm's own note (level 2, receipt `saea-perception-branch-arms-v4`):

| arm | template (pinned relpath, sha256) | words | tag set | role |
| --- | --- | ---: | --- | --- |
| `p1` | `configs/probes/nx/perception/r6/r6-p1.txt` `8cd15846...` | 187 | `none,some` | presence tag only: can the core judge "no entity value" at the Perception node |
| `p2` | `.../r6-p2.txt` `2a27d0d4...` | 243 | `none,some` | presence tag + up to three `M=` heard mentions (options to verify) |
| `p3` | `.../r6-p3.txt` `12ff7812...` | 264 | `none,some,unsure` | presence with an `unsure` hedge + mentions (raise the precision of `none`) |
| `aa` | none (`replicate_of lock`) | - | - | the in-chain twin: the within-flight null of this node column |
| `lock` | none: the locked template `configs/probes/slurp_native_role_perception_v3.txt` `76749780...` | 128 | - | the **delivering** arm, untemplated, last |

The channel is the `distinction` string of the registered `slurp-intent-hypotheses-v1` note, whose first characters carry the pinned tag grammar
(`configs/probes/nx/perception/r6/TAG-GRAMMAR-v1.md`; the reader parses exactly it). The note schema and response format are **unchanged** (a richer
channel is the conditional v2 contract of decision 248). Only the delivering arm's answer is carried forward; its requests are the locked plan's
requests byte for byte (invariant I7), so the delivered answer is unchanged: **this is a MEASUREMENT cell.**

**Base.** The COMP-1b composition as a consumption-module block on lock **v2.2** (`native_episode.consumption_module`): `agree-vote-seed` (w_agree
1.0, k 60, the Fold B vote table `SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-FOLD-B-V1`) and `centroid-boundary-key`
(`SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1`) ON, every other component OFF, Reviewer loop **OFF** (`review_loop: off`; Reviewer and Planner
`max_iterations` 0, `max_revisions` 0; `phase_tools` empty). The compiler writes every policy block; the program is `phase-native-module-v1-c10`
(ceiling 10 = 2 + 2 (5 - 1)); the loader refuses a fragment whose blocks differ from the compiled ones. `finite_completion_policy`
`deliver-latest-or-abstain` and `react_exhaustion_policy` `continue-without-answer` are declared (items E13 and E22). The Fold B pins are the
P-SV-4 fragments'; the base is the **R5 arm's base re-derived for Fold B** (`tests/unit/test_nx_r6_cell_registration.py` compares lock, review loop,
armed components, normaliser, policies and the Solver material against the R5 fragment). `stage3_algorithm` `none`.

Derived by `scripts/flights/nx/derive_slurp_nx_r6_cells.py`; shared ids in `scripts/flights/nx/nx_r6_family.py`; package written by
`scripts/flights/nx/write_slurp_nx_r6_registration.py`.

## 2. Why, and the declared expectation (decision 192 form, measurement cell)

Decision 239 moves the empty-entity decision to the preceding node; decision 245 makes node-local optimisation first and information gain the
object; decision 247 adopts the gain rule, and says the 1.5 pp registration bar binds the cascade cells (R7/R8), not this cell. The Perception node
carries NO entity information today (`unresolved_fields` / `evidence_refs` empty on 1,080 / 1,080 rows of both R1 flights, AUC 0.500). The best
pre-Solver signal is the supply's entity-free share N1 (AUC 0.856); a Solver-side presence verdict gated by N1 >= 0.2 is worth **+0.75 [+0.27,
+1.24]** (iteration 1) and **+0.98 [+0.50, +1.48]** (iteration 2) pp on the v4g base with 0 intent rows moved
(`docs/results/2026-10-10-slurp-nx-r6-upstream-empty-decision-offline.md` section 4).

**Declared expectation `expected_effect_pp` 0.75** (the gate estimate; range 0.75 .. 0.98), `claims_benefit` **false**: the cell is registered to
measure, so the effect-below-floor rule (which looks only at cells that claim a benefit) does not apply; 0.75 sits at about 0.5 x the borrowed 1.49 pp
same-flight floor and under the 1.5 pp bar. The number is conditional on the Perception verdict matching the Solver-side verdict's quality (recall
0.81-0.83, precision 0.74-0.76); if it only mirrors N1 the gain is about +0.13. Exchange rates: +0.033 pp per false fill removed, -0.070 pp per
non-empty exact row lost.

## 3. Measurement (`registered-facts-v1.json`, canonical `stage3_measurement`, keyed by run id)

`measurement_design: same-flight-node-column`, `template_variants {node: perception, candidate_arms: 3, twin: true}`, primary metric key `slu`
with the node-local primary named (rank-1 `E=none` against empty gold, reader E2b; the information gain over {N1, intent prior}; the gate
estimate), in-chain A/A = the `aa` twin (`aa_arm_id`), claim ceiling `nominated`, rows 1,080, tuning roster `SLURP-EVO-FOLD-A-V2`, read roster
`SLURP-EVO-FOLD-B-V2`. **Tuning disclosure (read it):** the candidates' hypotheses and the N1 >= 0.2 gate were derived from *aggregate* tables of the
R6 offline note, which were computed on Fold B (the NX R1 flights' columns), this cell's read roster; no utterance text, gold value or note body was
read to author them. Fold B is the design's *selection* roster (section 2.3: Fold B selects, Fold A confirms), so this is a selection read and every
number is descriptive until the Fold A confirmation (R6-A) fixes the rule. `variant_cost`: +4 Perception and +4 level-2 Solver contacts per row
(`extra_contacts_per_row` 4 is the gate's K - 1 count), 8 x 3,154.797 s of extra speech per flight. The smoke is a `form-proof`.

**Acceptance** (`analysis-recipe-v1.json`, `acceptance`): node-local = rank-1 `E=none` recall >= 0.80 and precision >= 0.75 on empty-gold rows with a
rank-1 tag parse rate >= 0.90 (below that: a FORM FAILURE, not a verdict) and no intent guard moving by more than the twin's own movement plus
0.65 pp; information gain = CI95 lower bound of the cross-fitted AUC increment over {N1, intent prior} above zero (2,000 draws, seed 20261010);
the delivered-metric estimate is reported through the exchange rates (10,000 draws, seed 20260915), intent rows moved must be 0. Nothing is
locked here; two evaluated Perception-entity rounds without an acceptance close the node.

## 4. FIT numbers

| quantity | value | how |
| --- | --- | --- |
| `slot_tokens` / `completion_ceiling` | 24,576 / 512 | live slot; Perception `max_tokens` |
| `base_prompt_tokens` | 2,577 | **measured** on the P-SV-4 AGREE arm's 1,080 Perception contacts (`scripts/flights/psv/psv_fit_measure.py`), excluding the template |
| `tokens_per_supplied_item` | 149 | measured, same source |
| `max_supplied_items` | 10 | the P-SV-4 branch bound (boundary block, 8 items observed) |
| `template_tokens` | lock 256; p1 374; p2 486; p3 528 | **ESTIMATE** (below) |
| arm prompt estimates | 4,323 (lock) to 4,595 (p3) | base + template + 10 x 149 against the prompt limit 20,990 |

Plan budget (the harness FIT rule `planned_model_calls >= rows x ceiling`, run-cumulative): arm **10,800** generation contacts (1,080 x 10),
**43,200** FIT endpoints (rows x ceiling x 4, structural, never run-cumulative), **31,548** speech seconds (`ceil(3,154.797 x 10)`), **4.1** planned
GPU hours (the ceiling, not a target: 10,800 contacts at the measured 44 requests per minute on np4); smoke 40 / 160 / 102 / 1.0 as a first attempt
and, after the smoke recovery below, **60 / 160 / 153 / 1.0** (run-cumulative: the original plan plus the failed attempt's realised 20 contacts /
50.908 speech seconds; the FIT cap is structural and unchanged). The realised fit of every arm request is measured again at dispatch by `native_contact_fit`; the level-2 Solver contacts are bounded by
the realised gate, not the estimate.

### Template tokens: ESTIMATE

`template_tokens` are **word-count estimates** (`ceil(2.0 x whitespace-separated words)` of the pinned file; `fit-measure-v1.json` is labelled
`ESTIMATE`), **not** a tokenizer measurement. A tokenizer pass needs the frozen core's tokenizer endpoint, which is a server-side contact, and none
was made. The fit margin is more than 15,000 tokens, so the estimate cannot change an admission decision; it enters the registered hashes, so the
measured values must replace it **before the flip**.

**TODO (root, with the resident np4 session attached and a lease):** run the cell's registered FIT identity (the harness's `prompt-fit` mode, the
shared `core.flight.cli` FIT path under `SAEA-SLURP-STAGE3-NX-R6-PERCEPTION-FOLD-B-FIT-V1`, structural cap 43,200), which measures request tokens
through the server's tokenizer endpoint; the command pattern, assembled from `core/flight/cli.py`'s argument list and NOT run:

```
python -B -m speech_aware_evidence_acquisition.core.flight.cli prompt-fit \
  --repo-root <flight worktree> --data-root "$SPEECHRL_DATA_DIR" --runtime-root <runtime root> --lock-path <datasets.lock.json> \
  --experiment slurp-native-stage3-nx-r6-perception-fold-b-v1 --owner root-slurp-native-stage3-nx-r6-perception-fold-b-v1 \
  --expected-session-id serving-slurp-native-candidate-five-train-a-np4-v1 --lease-token-file <lease token file> \
  --contact-cap 43200 --output "$SPEECHRL_DATA_DIR/<new, unused output path>"
```

Then put the measured per-template counts into `nx_r6_family.template_tokens()` (or a `fit-measure` input), re-run `derive_slurp_nx_r6_cells.py` and
`write_slurp_nx_r6_registration.py`, and adjust `test_template_tokens_are_the_labelled_word_count_estimate` in
`tests/unit/test_nx_r6_cell_registration.py` (it pins the estimate on purpose).

## 5. The read (`analysis-recipe-v1.json`, `scripts/analysis/nx_r6_read.sh`, READ row `SAEA-SLURP-STAGE3-NX-R6-PERCEPTION-FOLD-B-COLUMN-READ-V1`)

`bash scripts/analysis/nx_r6_read.sh [--dry-run] [--rescore] [--skip-official] [--skip-gain]`, after the seal and after the READ row is countersigned.
Model-free. (1) Reader E2b `scripts/analysis/slurp_nx_perception_column_read.py` (p3 with `--tag-set p3=none,some,unsure`): parse classes, the
rank-1 and list-majority presence verdict metrics, the heard-mention containment and option precision (normalised on the registered filler
normalisation), the paired intent guards and the level-2 Solver column's exact-set read. (2) `scripts/analysis/slurp_nx_r6_upstream_empty.py
--verdict-source perception-arm:<arm> --gain-baseline {n1,n1+prior,n1+prior+lock}` per candidate and baseline: the information-gain increment and
the gate estimate on the lock Solver column of the v4g base. (3) The official columns: each arm's level-2 Solver column scored once and read paired
(`stage3_rollout_score.py --mode perception-branches`, `stage3_paired_read.py`) -- **unexercised on a v4 template run**, non-gating.

## 6. Where the brief and the code did not agree (open items)

1. **Mention format.** The design (section 2.2) writes `M=<type>:<spoken surface>`; the pinned grammar and the templates write `M=<heard words>`
   (type-free). The reader follows the grammar, so containment is by surface and the per-slot-type split attributes a matched option to the type
   of the gold entity it matches.
2. **Roster tuning exposure.** See the tuning disclosure (section 3); the registered roster ids are the R1 cells'.
3. **`flight_registration_check` node-column findings** read only the Solver path (`NODE_COLUMN_PATH`); for this Perception cell they are a no-op.
   The preflight test asserts the same registration facts (twin, `aa_arm_id`, variant cost, summary, claim) instead.
4. **Template tokens** are an estimate (section 4).
5. **Re-pin.** The instrument merge changed hashed sources; every pinned cell needs the loop-form pass, including this one, after the merge point.
6. The dry run (`scripts/flights/nx/nx_r6_dry_run.py`) needs the data root and is root's to run after the flip.

## 6b. Smoke recovery (rec1, 2026-10-10; the cell's single recovery re-registration)

The first smoke attempt (`attempt-slurp-native-stage3-nx-r6-perception-fold-b-smoke-4-generation-v1`) stopped 2026-10-10T08:11:08Z at flight
commit 58c546b54 after 20 model contacts (4 rows x 5 Perception arms; 50.908 speech seconds, read from the attempt record's `actual`) on
`SlurpIntentHypothesisError: hypothesis content does not match its source response SHA-256` in the first level-2 Solver input. Root cause: the
level-2 branch view in `rails/runner.py` swapped the Perception state's content for the branch's note without rebinding
`source_response_sha256`; the fix is the level-2 note source-hash binding fix (`rails/runner.py`; fix commit 45c3b3633 on branch sonnet/level2-note-sha-fix, merged into master as 6030c3149; helper `perception_note_view_state` in rails/runner.py; regression test tests/unit/test_perception_note_view_binding.py). The smoke is re-flown
whole under `...-smoke-4-generation-rec1-v1` and `...-smoke-4-fit-rec1-v1` (a (run_id, attempt_id) pair is a one-time key); its plan budget is
run-cumulative, 40 + 20 = 60 calls and ceil(102 + 50.908) = 153 speech seconds; the FIT cap stays 160 (structural); the arm cell, its attempt
ids, caps and pins are untouched (only the registered plan copies' protocol-document pin moves, because the protocol document now records the
recovery). The recovery record lives in `nx_r6_family.SMOKE_RECOVERY`, the protocol document and the smoke generation plan; the two smoke ledger
rows were amended in place (R1 precedent). A second failure closes the cell; the fix is then proven on a four-row dry run.

## 7. What the coordinator does next (nothing was done here)

1. Merge this branch (docs, scripts, tests and configs); the R5 flight must have sealed (one experiment in flight). Re-read the five DRAFT rows.
2. Replace the template-token estimate (section 4) and regenerate the package.
3. **Countersign** the four flight rows (arm, arm FIT, smoke, smoke FIT); the READ row stays a draft until the seal.
4. **Mint the receipt:** `python scripts/flights/nx/nx_r6_mint_receipt.py` (`--dry` first).
5. **Flip loop:** `bash scripts/flights/nx/nx_r6_flip.sh` (then the registered plan-pin refresh and a second flip); run no concurrent merge.
6. **Queue:** `bash scripts/flights/nx/batch_chain_nx_r6.sh` (smoke first, then the one-cell campaign on `slurp-np4`).
7. After the seal: countersign the READ row, then `bash scripts/analysis/nx_r6_read.sh` (`--dry-run` first).
