# Sealed-credit inner loop, run 3: C1 (the admitted COMP-1b) is the whole intent side; K6p is the only open same-flight nomination, and nothing open clears the DEV cross-flight bar (DESCRIPTIVE, model-free)

Run 2026-09-30 by Claude Fable 5.1 (analysis agent). Worktree `/home/chao/saea-worktrees/fable-innerloop3`, branch
`fable/innerloop3`, forked from master `a00b0327c`. The run implements the run-1 design
(`docs/superpowers/specs/2026-09-29-sealed-credit-inner-loop-run-1-design.md` and its coordinator rulings Q1-Q6)
with the run-3 inputs the coordinator's brief names. It is **not** a registered READ row and **not** a cell.

- **Contacts.** Zero model, server, encoder, embedder, tokenizer, scorer-subprocess, network or GPU contacts.
  `core.flight.cli` and `lease_cli` were not invoked.
- **Gold.** Read offline through the governed TRAIN loader (`data.slurp.load_slurp_split`) only, as in runs 1 and 2.
  No DEV gold was loaded: the DEV numbers below are cited from sealed READ outputs.
- **What appears here.** Counts, rates, pp, ids and hashes only. No utterance text, gold value, filler or model
  output was printed or persisted.

**DESCRIPTIVE.** The Fold A / Fold B / R01C numbers are TRAIN development numbers, and the A2 / COMP-2 numbers are
DEV-2000-ADDED development numbers (owner decisions 28 and 86). A nomination is input to the coordinator's
registration decision. It is never a claim of benefit.

## 1. Inputs

**Pools v3** (`configs/analysis/sealed-credit-pools-v3.json`, 28 pools) are run 2's 25 plus three:

- `psv3`: P-SV-3 (`SAEA-SLURP-STAGE3-PSV3-FOLD-B-V1`), TRAIN Fold B, tuning. Its delivered branch `a-agree` gives
  `d_ok` 899 / 1,080, and its Perception-rank conversion is 96.25 / 24.42 / 4.35 / 1.11 % (rank 1 / 2 / 3+ /
  absent; n 881 / 86 / 23 / 90).
- `a2` (`SAEA-SLURP-STAGE3-COMP1B-DEV2000-ADDED-V1`) and `a2-aa` (`SAEA-SLURP-STAGE3-COMP1-AA-DEV2000-ADDED-V1`):
  DEV-2000-ADDED, n = 1,000, `use: read`.
  - They are the read roster of both designs, so they are never extracted and never tune a parameter (decision 28,
    Q1). They therefore do not appear in the credit table's pool list.
  - They enter only through two cited sealed READ outputs, and only for lines the coordinator has already
    disposed of: the A2 gating contrast for the admitted C1 composite, and the COMP-2 stage column for the scope
    rule.

The split is unchanged from run 2: tune on R01C + TRAIN Fold A + TRAIN Fold B, and read on DEV-2000-ADDED. The four
advisory `tuning-roster-unverified` findings are the same as in run 2. No finding was blocking.

**Policy space v3** (`configs/analysis/sealed-credit-policy-space-v3.json`, 25 knobs, 29 values). A new optional
value-level `status` records the coordinator's disposition of each line:

- `admitted`: dev-admitted. The value is ranked and composable, but never re-nominated.
- `closed`: a closed line, kept as an observation and never nominated.
- `open`: the default.

| knob = value | run 3 source | intent / SLU pp | status |
| --- | --- | --- | --- |
| `perception_seed_agree_centroid` = agree + centroid (**C1**) | A2 vs in-chain A/A, DEV n = 1,000 (`...COMP1B-DEV2000-ADDED-PAIRED-ANALYSIS-V1/vs-aa/score-contrasts.json`); supersedes run 2's COMP-1 +4.26 / counterfactual +0.58 | **+4.60** [+2.58, +6.73] / +0.53 [-1.04, +2.09] | admitted |
| `key_source` = `k6p` (new) | retrieval-key note, implied +11.496 rows Fold A (+1.0644 pp, used) / +11.634 Fold B (+1.0772 pp); measured against `cent_agree`, so an increment on C1 | +1.0644 / n/a | open; **flag: selection used both folds** |
| `scope_rule` | COMP-2 stage column on A2, stage vs delivered (`...COMP2-STAGE-COLUMN-DEV2000-READ-V1/report.json`); supersedes AGREE R5 +1.18 and Fold A +1.35 | 0.00 / +0.49 [-0.01, +1.00] | closed as a standalone claim (FAILS Q2); composable |
| `none_hint` = N1 theta 0.6 | unchanged (M1 conversion on AGREE); A2 trigger coverage 51 / 1,000 rows, 17 with entities | 0.00 / +0.17 | open |
| `lock` = v2.1 (replaces run 2's `reviewer_repair_g5`; same bytes, same source) | G5 vs A/A, Fold A | +0.09 / -0.38 | admitted (decision 204, efficiency; never a gain) |
| `missing_slot_proposal_tool` (new) | unobserved; E5-1 ORACLE ceiling +8.21 [+6.95, +9.57] SLU (the brief's precision 0.25); no call precision or conversion measured | 0.0 / 0.0, flagged | open |
| `reviewer_revise` (new) = contrastive (REV-TFRL-1) | loop net, Fold A; precision 0.095, conversion 0.159 | -0.09 [-1.11, +0.93] / n/a | open |
| `reviewer_revise` = best cross-fit flag | upper bound, instrument note (pooled precision 0.122) | <= +0.43 / n/a | open |
| `asr_verify` = R-DROP tuned / R-SWAP tuned (new) | E5-1 ORACLE upper bounds, agree, Fold A | 0.00 / -2.31 [-3.65, -1.00]; 0.00 / -0.03 [-0.14, +0.07] | closed (verify-span) |
| `boundary_depth` = 12 | P-SV-3 branch column, Fold B; level-1 present -1.39 | 0.00 [-0.28, +0.28] / +0.01 | closed |
| `min_candidates` = 3 (forced list) | P-SV-2 branch column, Fold B; supersedes run 2's 6-row citation | 0.00 / +0.81 [+0.11, +1.66] | closed |
| `presentation_id` = top2-contrast / rank-visible | P-SV-1 pre-read / RANKVIS probe (unchanged) | -0.19 / +0.10; +0.29 / n/a | closed (Perception presentation forms) |
| `relisten_acceptance` replace-only / replace + drop | E4-1 shadow columns (unchanged) | 0.00 / -4.11; 0.00 / -3.59 | closed (relisten replace) |
| `citation_contract` | COMP-1 harm attribution (unchanged) | 0.00 / -2.83 | closed |

Every other knob is unchanged from run 2, with no status: `phase_supply.k`, `release_swap`, `relisten_drop_only`,
`reviewer_planner`, `deliver_normaliser`, the unobserved `fuse_coverage.*`, `candidate_supply.max_candidates`,
`boundary_phase_supply` and `rank_weights.w_agree`, and the excluded `commit_rule`.

**Compositions v3** (`configs/analysis/sealed-credit-compositions-v3.json`): C1, C1 + k6p, C1 + scope rule,
C1 + k6p + scope rule, and C1 + none hint.

## 2. What ran

```
PYTHONDONTWRITEBYTECODE=1 python -B scripts/analysis/sealed_credit_inner_loop.py \
    --pools configs/analysis/sealed-credit-pools-v3.json \
    --policy-space configs/analysis/sealed-credit-policy-space-v3.json \
    --compositions configs/analysis/sealed-credit-compositions-v3.json --run-label run-3 --top 8 \
    --read-design same-flight-supply-variant \
    --out "$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-SEALED-CREDIT-INNER-LOOP-RUN-3-V1"
#   and --read-design cross-flight-with-in-chain-replicate --rows 1000 \
#       --out "$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-SEALED-CREDIT-INNER-LOOP-RUN-3-CROSS-V1"
```

**Reproducibility.** `--check` re-derived both outputs, and each was IDENTICAL apart from `generated_at`.

**Code changes.** They are minimal, and 57 sealed-credit unit tests pass with `PYTHONPATH=src` (54 existing plus 3
new).

- `policy_space`: the optional value-level `status` is validated against `open` / `admitted` / `closed`.
- `estimate`: a declared `status` and `status_note` are copied onto the estimate. An absent status leaves no key.
- `accept.nominate`: only `open` candidates are nominated. The ones that would have cleared are listed under
  `cleared_but_not_open`.
- CLI:
  - the report shows a status column when any status is declared;
  - `same-flight-perception-variant` is added as a read design. It carries the same decision-190 anchors as the
    supply variant, intent 0.65 and SLU 1.49 at n = 1,080, so the same-flight output below serves both.

**Run 2 is unchanged.** With the v2 configs, `--check` against the sealed `...RUN-2-V1` and `...RUN-2-CROSS-V1`
outputs is IDENTICAL apart from `generated_at`.

**Content hashes** (`content-sha256.json`, with `generated_at` stripped):

| file | RUN-3-V1 (same-flight, n = 1,080) | RUN-3-CROSS-V1 (DEV cross-flight, n = 1,000) |
| --- | --- | --- |
| `credit.json` | `846742a6952dc1b313573e72d89f56317e28add8acd7bda7ba6d424a4a332b20` | same |
| `row-states.jsonl` | `9786848cbf4dfcbc4df838b0592abed19cd07d13ee7be2425463a8977569332c` | same |
| `candidates.json` | `2ce800b3f4c699ed54af4684db728adb873c05dc356cdfaf648e47943dd1b4b6` | `8f9787bd7bd997cd2a06725004ebcca776f96ac15a04b046ff13c6b181a25a42` |
| `compositions.json` | `fd5cfd9853272f4c46cac592a65663122ffce68d0850f3d11243a8b77fbfe7f9` | `0024fe7850179b15793f123fa093382fa386d67108e5b1dd7fcc32fc8695104b` |
| `nomination.json` | `479758f44bd8721e420a119ebbf10284a5927e00c52b9948f54ad494906d5f7f` | `5b1e0605602cd9277eacef10be32f4119afac89b0c373daf5eb05cd9d7ecc2c6` |
| `report.md` | `8bc04719e0a98cdea985284860f3c88b49853aaa7cc25138d7ddf4f42dfc9448` | `fcb0d49aff9cb56a9d1ee39849e17523794e6324637f4feece79770040be93f5` |

The `credit.json` `table_sha256` is `c72889d1c6e323d49eb9798136c09fede8cb06b5326cf3ef404d73ffb3afb485`.

## 3. Candidates: top 8 per design (29 values ranked by predicted intent)

The ranking is the same under both designs. Only the guard and the floor differ:

- **Same-flight** (supply or perception variant, n = 1,080): SLU guard 1.49, intent floor 0.65.
- **DEV cross-flight with in-chain replicate** (n = 1,000): guard 1.2525, bar 2.5981.

| rank | knob = value | intent pp | SLU pp | status | same-flight (0.65) | DEV cross-flight (2.5981) |
| ---: | --- | ---: | ---: | --- | --- | --- |
| 1 | perception_seed_agree_centroid = agree + centroid (C1) | +4.6000 | +0.5302 | admitted | clears | clears |
| 2 | key_source = k6p | +1.0644 | n/a | **open** | **clears** | below |
| 3 | phase_supply.k = 10 | +0.4800 | -0.2827 | open | below | below |
| 4 | reviewer_revise = best cross-fit flag (upper bound) | +0.4300 | n/a | open | below | below |
| 5 | phase_supply.k = 30 | +0.3704 | -0.4582 | open | below | below |
| 6 | presentation_id = rank-visible-v1 | +0.2870 | n/a | closed | below | below |
| 7 | release_swap = slot-contracts-w4-v1 | +0.1852 | -0.1519 | open | below | below |
| 8 | lock = v2.1 | +0.0926 | -0.3805 | admitted | below | below |

The remaining 21 values rank below these:

- **Intent 0.00:**
  - `asr_verify` R-SWAP (SLU -0.03, closed);
  - `boundary_depth` (+0.01, closed);
  - `min_candidates` 3 (+0.81, closed);
  - `none_hint` (+0.17);
  - `relisten_drop_only` (+0.8, approximate);
  - `scope_rule` (+0.49, closed);
  - the six unobserved knobs, including `missing_slot_proposal_tool`.
- **Negative intent:**
  - `reviewer_revise` contrastive -0.09;
  - top2-contrast -0.19 (closed);
  - `deliver_normaliser` off -1.94.
- **Guard-discarded under both designs:**
  - `asr_verify` R-DROP (SLU -2.31);
  - `citation_contract` (-2.83);
  - `relisten_acceptance` replace + drop (-3.59) and replace-only (-4.11);
  - `reviewer_planner` off (-1.85 / -3.39).

## 4. Nominations

- **Same-flight design (floor 0.65 intent, guard 1.49 SLU): `key_source = k6p` is nominated** (+1.0644 intent;
  SLU is not modelled, so the guard is not evaluated). Claim ceiling `nominated`.
  - C1 also clears (+4.60), but it is `admitted` and is listed as cleared-but-not-open.
  - Read-roster caveat: K6p was selected on Fold A and Fold B, so neither fold is an unexposed same-flight read
    roster for it. A same-flight read needs a new Perception-branch `key_source` axis (the brief's P-SV-4).
  - Its point sits at about 1.6 times the same-flight intent floor. Unlike the other nominations, it is an implied
    figure: today's sealed rank-conditional conversions are applied to new ranks.
- **DEV cross-flight design (bar 2.5981, guard 1.2525): nothing open is nominated.** The only candidate over the bar
  is C1, which is admitted, cleared-but-not-open. K6p's +1.06 is 41 % of the bar.

## 5. The composed-policy question (DEV cross-flight bar 2.5981 at n = 1,000, SLU guard 1.2525)

The compositions are additive sums of single-knob estimates. Rows two components both act on are not
de-duplicated.

| id | components | intent pp | SLU pp | same-flight (0.65 / 1.49) | DEV cross-flight (2.5981 / 1.2525) |
| --- | --- | ---: | ---: | --- | --- |
| C1 | agree + centroid (A2) | +4.6000 | +0.5302 | clears | clears |
| C1 + k6p | + key_source k6p | +5.6644 | +0.5302 | clears | clears |
| C1 + scope | + scope_rule | +4.6000 | +1.0201 | clears | clears |
| C1 + k6p + scope | both | +5.6644 | +1.0201 | clears | clears |
| C1 + none | + none_hint | +4.6000 | +0.6994 | clears | clears |

- **Every composition clears the DEV bar only through C1.** C1 alone carries +4.60 of the intent, and no other
  component except K6p has an intent term. Every composition's intent clears because C1's does.
- **Each extension would have to be read as its own increment over C1.**
  - K6p would add +1.06 to intent, an implied figure below the 2.5981 bar on its own.
  - The scope rule would add +0.49 to SLU.
  - The none hint would add +0.17 to SLU.
- **C1 + scope is not a prediction.** The scope term is measured on the A2 arm, so the sum, intent +4.60 / SLU
  +1.02, is the sealed COMP-2 composed contrast by construction: +4.60, +1.02 [-0.64, +2.68].
- **No composition's predicted SLU is negative.** Only the C1 term has a measured DEV interval, whose lower bound
  -1.04 lies inside -1.2525.

## 6. What this run does not claim

- No admission, superiority, generalisation, test claim, or claim about any carrier but SLURP. Every DEV number is a
  cited development READ, and no DEV row tuned anything.
- **The C1 and scope-rule numbers are DEV READ outputs.** They are cited here because the coordinator has already
  disposed of both lines: C1 is admitted, and the scope rule is closed as a standalone claim. They are not new
  inputs to a selection.
- **K6p's +1.0644 is implied, not measured.** It applies sealed rank-conditional conversions to new ranks, and its
  SLU effect is not modelled. It was selected on both TRAIN folds.
- **The compositions are additive sums over estimates from different rosters and arms.** The C1 term is DEV
  (n = 1,000). K6p is TRAIN Fold A, and the none hint is AGREE. None of the compositions is a measurement of a
  composed arm, except that C1 + scope reproduces the sealed COMP-2 contrast by construction.
- **Some sources are ceilings or approximations.** `missing_slot_proposal_tool` enters at 0.0: its +8.21 is an
  oracle ceiling with no measured call precision or conversion. `reviewer_revise` +0.43 is an upper bound.
  `relisten_drop_only` +0.8 remains the coordinator's approximate figure.
- The filler pools enter the credit surface only. Decision 179 still holds.

## 7. Recommendation to the coordinator

1. **Take C1 (AGREE + centroid = COMP-1b, A2-admitted) as the consumption module's first block, with the lock at
   v2.1 for cells registered after A2.**
   - Design: the module's composed cross-flight read with an in-chain A/A on DEV-2000-ADDED (n = 1,000, bar 2.5981,
     guard 1.2525).
   - Decision needed: none new. A2's coordinator verdict and decision 204 already carry it.
2. **P-SV-4 (`key_source = k6p`) is the only open same-flight nomination.**
   - Predicted +1.06 intent, implied; SLU is not modelled.
   - Design: a same-flight Perception-branch level-2 (Solver) column. This needs a new `key_source` branch axis
     (parser, refusals, tests) and two zero-contact `prepared/` artefacts: the centred key file and the centred
     query files. The column is read against the 0.65 intent floor and the 1.49 SLU guard.
   - Decision needed: owner decision 208. It covers authorising the axis and artefacts, and choosing the read
     roster, because both TRAIN folds were used in K6p's selection.
3. **Everything else is closed or below its floor.**
   - Closed lines: contrast presentation, forced list, boundary depth, relisten replace, verify-span, and the scope
     rule as a standalone claim. The scope rule stays a composable deliver stage.
   - Below the 0.65 floor: `phase_supply.k`, `release_swap` and `reviewer_revise`.
   - `missing_slot_proposal_tool` is unobserved.
   - Decision needed: none. The loop proposes no other cell.

## Coordinator reading (Fable 5.1, 2026-09-30)

Run 3 confirms the state of the loop: C1 (AGREE + centroid = COMP-1b) is admitted on DEV and is the
consumption module's first block on lock v2.1; `key_source = k6p` (+1.06 pp implied) is the only open
same-flight nomination and waits for owner decision 208 (P-SV-4, with the both-folds selection disclosure);
every other knob is closed or below its floor; no open candidate clears the DEV cross-flight bar 2.5981. The
`missing_slot_proposal_tool` knob (unobserved here) is routed to owner decision 209 option B per the E5 oracle
verdict. The loop's status moves from `base-loop` to `converged-under-current-evidence-kinds` pending 209.
