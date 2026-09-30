# Sealed-credit inner loop, run 2: the only candidate over its floor is AGREE + centroid (COMP-1b, already flying); the composed policy is predicted to clear 2.5 pp intent with SLU inside the guard (DESCRIPTIVE, model-free)

Run 2026-09-29 by Claude Fable 5.1 (analysis agent), worktree `/home/chao/saea-worktrees/fable-innerloop2`, branch
`fable/innerloop2`, forked from master `c2ae4404f`. The run implements the run-1 design
(`docs/superpowers/specs/2026-09-29-sealed-credit-inner-loop-run-1-design.md` and its coordinator rulings Q1-Q6)
with the run-2 inputs the coordinator's brief names. It is **not** a registered READ row and **not** a cell. There
was zero model, server, encoder, tokenizer, scorer-subprocess, network or GPU contact; `core.flight.cli` and
`lease_cli` were not invoked. Gold was read offline through the governed TRAIN loader
(`data.slurp.load_slurp_split`) only. Counts, rates, pp, ids and hashes appear below; no utterance text, gold
value, filler or model output was printed or persisted.

**DESCRIPTIVE.** Every number is a TRAIN development number (owner decisions 28 and 86). A nomination is input to
the coordinator's registration decision, never a claim of benefit.

## 1. Wait condition and inputs

- **P-SV-1 seal-only completion.** `SAEA-SLURP-STAGE3-PSV1-FOLD-B-V1` /
  `attempt-slurp-native-stage3-psv1-fold-b-generation-v1-seal-only`: attempt state FINALIZED, run manifest
  COMPLETED (created 2026-09-29T20:45:15Z, study commit `c6e98e6b`, `study_repo_dirt` empty; 1,080 rows kept, 0
  flown). Queue log: `P-SV-1 seal-only chain exit 0; done=2026-09-29T20:49:26Z`. The pool is included.
- **Pools v2** (`configs/analysis/sealed-credit-pools-v2.json`, 25 pools): run 1's twelve, plus `comp1-aa` (the
  shared in-chain A/A that COMP-1, COMP-1b and G5 read against), `comp1` (seal-only), `g5`, `e4-relisten`
  (seal-only), `wsv1`, `w4sv`, `filler-c01` .. `filler-c06` (grouped 5, Fold B), and `psv1` (seal-only; outputs
  and scores from the finalized attempt, node states from its predecessor's `phases.json` through the new
  `phases_attempt` key). All tuning.
- **Split.** Per the brief (the run-1 design's Q1 alternative): tune on R01C + TRAIN Fold A + TRAIN Fold B (filler,
  P-SV-1). Because Fold B now tunes, the manifest names DEV-2000-ADDED as the read roster for both designs (the
  loader refuses a tuning roster that is also a read roster). Per candidate: every source except
  `presentation_id = top2-contrast-v1` is Fold-A-only (or R01C), so those could still be read same-flight on Fold
  B; the top2-contrast source is Fold B and may not be (decision 186). The four roster findings are advisory
  `tuning-roster-unverified` (no receipt states Fold A / Fold B disjoint from DEV-2000-ADDED; they are different
  SLURP splits).
- **Policy space v2** (`configs/analysis/sealed-credit-policy-space-v2.json`, 21 knobs): run 1's fourteen with the
  new observations, plus seven (section 3).
- **Compositions** (`configs/analysis/sealed-credit-compositions-v2.json`, 8 named compositions).

## 2. What ran

```
scripts/analysis/sealed_credit_psv1_preread.py        # P-SV-1 B vs A, pre-read (section 4)
scripts/analysis/sealed_credit_inner_loop.py \
    --pools configs/analysis/sealed-credit-pools-v2.json \
    --policy-space configs/analysis/sealed-credit-policy-space-v2.json \
    --compositions configs/analysis/sealed-credit-compositions-v2.json --run-label run-2 --top 8 \
    --read-design same-flight-supply-variant \
    --out "$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-SEALED-CREDIT-INNER-LOOP-RUN-2-V1"
#   and --read-design cross-flight-with-in-chain-replicate --out ...-RUN-2-CROSS-V1
```

`--check` re-derives both outputs and the pre-read: IDENTICAL apart from `generated_at`. The code changes are
byte-neutral for run 1: with the v1 configs, master `c2ae4404f` and this branch produce identical
`credit.json`, `candidates.json`, `nomination.json`, `report.md` and `row-states.jsonl`. Both differ from the sealed
`...-RUN-1-V1` output in `candidates.json`, `nomination.json` and `report.md`. The cause is the metric-aware
`accept.py` already on master (decision 190), not this branch. Re-derived today, run 1 nominates nothing.

Content hashes (`content-sha256.json`, `generated_at` stripped):

| file | RUN-2-V1 (same-flight) | RUN-2-CROSS-V1 |
| --- | --- | --- |
| `credit.json` | `8ec1f732...fc44af1f` | `8ec1f732...fc44af1f` |
| `candidates.json` | `dfd59ed1...e09b6021` | `cf85481c...74a7b9bf0` |
| `compositions.json` | `9947be72...16ec60bb27` | `92afb1bb...c68f4ea5` |
| `nomination.json` | `87b274c2...bfd83f9a` | `99955cdb...2383e747` |

`credit.json` `table_sha256` `61c7e4fc...6c0f04`. P-SV-1 pre-read `report.json` sha256 `9bc68223...d2f0ee`.

Code changes (minimal, tested; 54 sealed-credit unit tests pass): the `cited` estimator takes a literal intent or
SLU half when the artefact carries no such field (run 1's evidence shape unchanged); `accept.score_compositions`
scores named compositions through `estimate.compose`; the CLI adds the `cross-flight-with-in-chain-replicate`
design at n = 1,080, `--compositions`, `--run-label`, `--top`; a pool may name `phases_attempt` for a seal-only
completion. New model-free script `scripts/analysis/sealed_credit_psv1_preread.py`.

## 3. Credit table headline

Reference pool `agree` (Fold A, n = 1,080) reproduces run 1 exactly: `d_ok` 927, `s1_ok` 907, Perception-rank
conversion 97.57 / 26.98 / 12.00 / 2.35 % (rank 1 / 2 / 3+ / absent).

New pools (`d_ok` / rows): `comp1` 930 / 1,080, `comp1-aa` 884, `g5` 885, `e4-relisten` 926, `wsv1` 926, `w4sv`
929, `psv1` 904, filler c01-c06 143 / 146 / 151 / 141 / 145 / 153 of 180 each. On Fold B (`psv1`, branch A
delivered) Perception rank converts 97.54 % (893 rows) / 19.48 % (77) / 13.64 % (22) / 0.00 % (88).

Caveat: `comp1` and `e4-relisten` are seal-only completions whose backfilled `phases.json` carries no Solver or
Reviewer agent states (`s1_ok` 0, `reviewer_visited` 0 in the table). Their delivered state is valid; their node
states are not, and no knob reads them.

## 4. P-SV-1 top2-contrast column, pre-read (DESCRIPTIVE)

Computed by `scripts/analysis/sealed_credit_psv1_preread.py` with the perception-branch read primitives
(`paired_top1_read`, `paired_present_read`, 10,000 draws, seed 20260807) and, for the level-2 answer columns, each
branch's own first Solver answer recovered from the I7r-verified predecessor trace (0 unresolved), passed through
the row's own normaliser and scored in-process with the official SLURP arithmetic. **Pre-read, descriptive: the
P-SV-1 READ row is the coordinator's to countersign; this is not its verdict.** The ledger was not edited.

| contrast (n = 1,080, TRAIN Fold B) | B - A (top2-contrast) | T - A (twin null) |
| --- | --- | --- |
| level 1 top1 (gold ranked first on the note) | -1.67 [-2.96, -0.37] (54 discordant) | -0.56 [-1.11, -0.09] (8) |
| level 1 present (gold on the note) | -1.85 [-2.96, -0.83] | -0.56 [-1.11, -0.09] |
| level 2 intent (branch Solver answer) | **-0.19 [-0.56, +0.19]** (1 save / 3 harms) | -0.09 [-0.46, +0.19] |
| level 2 pooled SLU-F1 | +0.10 [-0.48, +0.68] | -0.03 [-0.41, +0.34] |

Gold rank on the note (A / B / T): rank 1 893 / 875 / 887; rank 2 77 / 82 / 77; 3+ 22 / 15 / 22; absent 88 / 108 /
94. Branch A's level-2 column differs from the sealed delivered intent on 8 rows (Reviewer revisions after the
first Solver visit; delivered intent 83.70 %, A column 83.52 %). The top2-contrast presentation moves gold off
first place on the note more often than onto it; the Solver's answers barely move. The knob becomes OBSERVED:
intent -0.19, SLU +0.10.

## 5. Candidates (23 knob values; ranked by predicted intent)

Same ranking under both designs; only guard and floor differ. Same-flight at n = 1,080: SLU guard 1.49, intent
floor 0.65 (decision 190). Cross-flight with in-chain replicate at n = 1,080: guard 1.2485 (sampling half-width,
decision 127), floor 2.5 (rule-3 bar).

| rank | knob = value | intent pp [CI95] | SLU pp | source | same-flight | cross-flight |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | perception_seed_agree_centroid = agree-w1+centroid-key | **+4.26 [+2.41, +6.11]** | +0.58 | COMP-1 vs A/A; SLU = harm-attribution counterfactual | clears | clears |
| 2 | phase_supply.k = 10 | +0.48 [-1.12, +2.24] | -0.28 (row proxy) | VAR-1 EX-K10 vs PLANR, n = 625 | below 0.65 | below 2.5 |
| 3 | phase_supply.k = 30 | +0.37 [-0.09, +0.93] | -0.46 | W-SV-1 column | below | below |
| 4 | presentation_id = rank-visible-v1 | +0.29 | n/a | RANKVIS (probe-transfer caveat) | below | below |
| 5 | release_swap = slot-contracts-w4-v1 | +0.19 [-0.46, +0.83] | -0.15 | W4-SV column (supersedes run 1's W4 pool pair) | below | below |
| 6 | reviewer_repair_g5 | +0.09 [-1.02, +1.20] | -0.38 | G5 vs A/A | below | below |
| 7 | min_candidates = 3 | +0.05 | n/a | 6 rows cited (P-SV-2 ceiling) | below | below |
| 8 | boundary_depth = m / top_l 12 | 0.00 | 0.00 | UNOBSERVED (P-SV-3 unflown; ceiling 83 rows = 7.69 pp present) | -- | -- |

Further down: `none_hint` 0.00 / +0.17 (M1 conversion; oracle +0.68); `relisten_drop_only` 0.00 / +0.8
(approximate, coordinator E4-1 verdict); `scope_rule` 0.00 / **+1.18** [+0.67, +1.71] (R5 table, `fable/module2`
commit `17711e68c`; wave A/A +1.07); `presentation_id = top2-contrast-v1` -0.19 / +0.10 (section 4);
`deliver_normaliser = off` -1.94; `citation_contract` 0.00 / **-2.83** (guard-discarded both designs);
`relisten_acceptance` replace + drop 0.00 / -3.59 and replace-only 0.00 / -4.11 (guard-discarded);
`reviewer_planner = off` -1.85 / -3.39 (guard-discarded). Unobserved at 0.0: `fuse_coverage.{m,c,top_l}`,
`candidate_supply.max_candidates`, `boundary_phase_supply`, `rank_weights.w_agree = 0.0` (circular source),
`boundary_depth`.

2026-09-30 (coordinator, no loop rerun): `boundary_depth 8->12` observed: present -1.39, intent 0.00 → discarded (P-SV-3 same-flight read; the rank-8 row above is superseded by this line).

Run 1's nomination `phase_supply.k = 10` (+0.48) now sits under the decision-190 intent floor 0.65 and lapses.
Run 1 re-derived under decision 190 nominates nothing.

## 6. Nomination

- **Same-flight design (floor 0.65 intent, guard 1.49 SLU):** `perception_seed_agree_centroid` (+4.26 intent, SLU
  +0.58 inside the guard). Claim ceiling `nominated`.
- **Cross-flight design (bar 2.5 intent, guard 1.2485 SLU):** the same candidate. Its point clears 2.5 but its
  COMP-1 CI95 lower bound (+2.41) does not.
- **No other single knob clears either floor.** The nominated candidate is the cell already flying as COMP-1b
  (COMP-1 minus the citation contract, same roster, same A/A). COMP-1b's read is its test; the loop proposes no
  new cell.

## 7. The composed-policy question

Additive sums of single-knob estimates; rows two components both act on are not de-duplicated, so for
same-direction components each SLU sum is an upper bound. Every SLU source except G5 and top2-contrast is
measured on AGREE or COMP-1, not on the COMP-1b arm.

| id | components | intent pp | SLU pp | same-flight | cross-flight (2.5 / 1.2485) |
| --- | --- | ---: | ---: | --- | --- |
| C0 | agree+centroid + citation contract (= COMP-1) | +4.26 | -2.25 | guard-discarded | guard-discarded |
| C1 | agree+centroid (COMP-1b) | +4.26 | +0.58 | clears | clears |
| C2 | C1 + scope_rule | +4.26 | +1.76 | clears | clears |
| C3 | C2 + none_hint | +4.26 | +1.93 | clears | clears |
| C4 | C3 + relisten_drop_only | +4.26 | +2.73 | clears | clears |
| C5 | C4 + reviewer_repair_g5 | +4.35 | +2.35 | clears | clears |
| C6 | C1 + top2-contrast | +4.07 | +0.68 | clears | clears |
| C7 | C4 + top2-contrast | +4.07 | +2.83 | clears | clears |

- **Answer.** AGREE + centroid (C1) is the whole intent side: +4.26 predicted against 2.5, with SLU +0.58 inside
  the 1.2485 guard. No other observed component moves intent by more than 0.1 pp.
- **Adding scope_rule, none_hint or relisten_drop_only changes only the SLU side, and only upward:** +1.18, +0.17
  and about +0.8 at their measured conversions. None has an intent term, and each is a deterministic or gated
  entity removal. C2 is the smallest composition whose predicted SLU clears the same-flight SLU floor 1.49
  (+1.76). The three components overlap on zero-gold and spurious rows (the consumption headroom note, section 4, records
  explicit emptiness (B4 / F10) overlapping the scope rule on FP-only rows; N1 is that same none option restricted
  by a supply gate, per the abstention note, section 4), so C3 and C4 are upper bounds. C2 is the only one resting on an
  exact, replicated offline edit (+1.18 AGREE / +1.07 wave A/A).
- **Do not add G5 or top2-contrast for gain.** G5 costs 0.38 SLU for 0.09 intent. The top2-contrast column costs
  0.19 intent (level 1: -1.67 top1).
- **C0 is a consistency check, not a validation.** The C1 SLU term was derived from COMP-1's own read (-2.24 plus
  the +2.83 counterfactual), so reproducing -2.25 is expected by construction. COMP-1b's SLU read is the first
  independent test of the additive model.

## 8. What this run does not claim

- No admission, superiority, generalisation, test or DEV claim. No claim about any carrier but SLURP.
- The P-SV-1 numbers are pre-read and descriptive. The READ row and its verdict belong to the coordinator.
- Composed predictions are additive over cited single-knob estimates from different arms and folds. They are not
  measurements of a composed arm. The SLU terms for scope_rule, none_hint and relisten_drop_only come from AGREE
  or E4-1, not from COMP-1b.
- `relisten_drop_only` +0.8 is the coordinator's approximate figure. No sealed artefact computes the drop-only
  column exactly.
- The scope-rule number comes from branch `fable/module2` (commit `17711e68c`, not yet on master at run time) and
  its sealed report `analysis/SAEA-SLURP-SCOPE-RULE-STAGE-ESTIMATE-R5-V1/report.json`.
- The `agree+centroid` SLU half (+0.58) is a counterfactual row swap. The centroid key has no flown arm of its own.
- Filler pools enter the credit surface only. Decision 179 still holds: no rule is read over grouped pools.

## 9. Recommendation to the coordinator

1. **Read COMP-1b as the loop's nominated cell.** Design: cross-flight with in-chain replicate (the sealed
   COMP-1 A/A), n = 1,080, bar 2.5 intent, guard 1.2485 SLU. Decision needed: none new. COMP-1b's registration
   already carries this, and its read tests the C1 prediction (+4.26 / +0.58).
2. **Declare the COMP-2 composition as C2 (COMP-1b + scope_rule) before flight, with none_hint as the one optional
   addition.** Design: cross-flight with in-chain replicate on DEV-2000-ADDED (n = 1,000; the scope rule's own read
   stays inside the composed arm per decision 195 = B). Decision needed: the component list, and whether the N1
   gate (theta 0.6 fixed, not tuned) rides. Leave out relisten_drop_only (approximate source), G5 (SLU cost) and
   top2-contrast (intent cost).
3. **Countersign or decline the P-SV-1 READ row.** Its pre-read column is intent -0.19 [-0.56, +0.19] against a
   twin -0.09, and level-1 top1 -1.67. Design: same-flight-perception-variant on Fold B. Decision needed: the READ
   verdict on `top2-contrast-v1`. This run marks it OBSERVED and unhelpful for intent.
