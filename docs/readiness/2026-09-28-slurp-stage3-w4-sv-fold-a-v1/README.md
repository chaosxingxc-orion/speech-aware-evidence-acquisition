# Cell W4-SV: the W4 slot conventions as a same-flight supply-variant column read (owner decision 172)

Registered before contact 2026-09-28 at study commit `190e178db`; both cells **held**; status
`REGISTERED_BEFORE_CONTACT_AWAITING_COORDINATOR_READINESS_FLIP`. Nothing here authorises a flight, a flip or an admission entry. Development numbers only (owner decisions
28 and 86).

## Proof re-run after the renderer fix (3f6688de), 2026-09-29

`w4sv_arm_a_proof.py` re-run at study commit `c24824a46` (which carries the release-swap renderer
fix `3f6688de`: a release-swap arm now renders from its own alternate snapshot) over the first 120 rows
reports **ARM-B-VARIES**: arm b-w4's first-visit POST body differs from arm a-agree's on
120 rows and equals it on 0. Arm A's verdict and
the twin are unchanged (below). The arm-B blocker is lifted; the cells stay held until root countersigns and mints.

**History (the registration's finding, superseded).** At registration the proof (study commit
`b5392755b`, sha256 `913c5487d5c7cb37e6c323433dc55976e614f7d86676efd370ee9f669e3ea55d`) read ARM-B-INERT over the first
120 rows -- arm b-w4's body equal to arm a-agree's on 120 rows, different on
0: every arm b-w4 first-visit POST body equalled its arm a-agree body: the release swap re-selected value ids through the alternate's router, but rails.runner rendered every arm's request from the FLIGHT's composite snapshot (base_messages over the row's snapshot, with only retrieved_value_ids replaced), and slot-contracts-w4-v1 carries the SAME 54 value ids as slot-contracts-v2 with new content on 19 of them -- so arm b-w4 rendered the v2 cards and read as a second twin. Where: rails/runner.py (the supply-variant binding rendered a non-delivering arm over the row's own composite snapshot) and core/flight/runtime.py::_supply_action_router (rebuilt only the arm's ROUTER over the alternate). The cell was registered held
with status `BLOCKED_ARM_B_INERT_REGISTERED_HELD` until the fix landed.

**What W4-SV is.** The retained AGREE arm (`SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1`) with a three-arm Solver supply-variant group fanned out at
the FIRST Solver visit only (`arm_visits: "first"`, program `phase-native-candidates-review-revise-variants3first-v1`, ceiling 13 = 11 + 2):

| arm | declaration | what its first Solver request carries |
| --- | --- | --- |
| `b-w4` | `release_swap: {store_id: slot-contracts, release: knowledge/slurp/semantic/slot-contracts-w4-v1/release.json}` | the W4 conventions release (19 of 54 cards extended), the declared ONE alternate of `slot-contracts` |
| `t-twin` | `replicate_of: a-agree` | the delivering arm's request, byte for byte (AT2) -- the in-flight null |
| `a-agree` | `deliver: true`, last, no overrides | the AGREE Solver supply (slot-contracts-v2) |

Only the delivering arm's answer reaches the Reviewer, the Planner and the delivered text; every revisit contacts
`a-agree` alone. The alternate is pinned exactly as cell W4 registered it (`docs/readiness/2026-09-27-slurp-stage3-w4-slot-conventions-fold-a-v1`): equal =
True.

**Measurement.** `same-flight-supply-variant`; primary official pooled SLU-F1 of the first-visit column b-w4 minus
a-agree, intent accuracy the guard; expected effect 0.79 pp (cell W4's cross-flight read); provisional
floor 0.3163 pp at n = 1,080 (0.735 x sqrt(200 / 1,080)); bar = the twin null;
claim `nominated`; `aa_arm_id` `t-twin`; variant cost +2 Solver contacts per row
(+2,160 per flight, +6,169.057 speech seconds); tuning roster
`size-pool-annotated-exemplars-minus-r01`, `slurp-slot-conventions-w4-support-v1`; read roster `SLURP-EVO-FOLD-A-V2`.

**Estimand.** ESTIMAND CAVEAT. The expectation is transferred from cell W4's CROSS-FLIGHT full-system read (docs/results/2026-09-28-slurp-w4-fold-a-read.md: official pooled SLU-F1 +0.79 pp CI95 [-0.56, +2.12] against the shared wave A/A). In that flight the W4 cards reached EVERY node whose request carries the slot-contract supply: the realised prompt tokens rose +1,207.8 per Solver, +1,207.4 per Reviewer and +1,201.9 per Planner contact (the registration had projected +724.5 per Solver contact). Here only arm b-w4's FIRST Solver request carries them: the Reviewer, the Planner and the Solver revisit see the AGREE v2 cards and never see an arm's output. B minus A is therefore the Solver-local first-visit effect of the W4 cards, a DIFFERENT estimand from the +0.79 pp system effect (which also includes the Reviewer and Planner reading the conventions and any revision they drive); 0.79 pp is declared only as the size to look for, not as the value this read should reproduce.

## Arm A against the AGREE arm (`arm-a-byte-identity-proof-v1.json`, the wave shared-A/A proof shape)

Verdict **IDENTICAL-MODULO-PROGRAM-FIELDS** over the first 120 rows. Strict POST-body comparison: 663
of 663 paired contacts differ; twin mismatches 0.
Normalised: 0 of 663 differ
(120 arm-A first Solver contacts included); twin mismatches
0. Prepared first-phase supply output `eab5c61e92a47c1723c478f2b7914abade6152b195f676d7d32251f3d18884ae` (equal to the
registered and committed AGREE digest: True).

Arm A is NOT byte-identical to the AGREE arm: every contact's POST body differs, and only in three program-derived prompt fields the arm group necessarily moves -- the program id inside agent-state labels, the Solver's global contact index in those labels (shifted by K - 1 = 2), and remaining_model_contacts in the role context (13 vs 11 before the Solver visit, equal after it). Unifying exactly those three, every paired contact is byte-identical (arm A's first Solver request included) and every twin body equals its arm A body. A, T and B share these fields, so the column contrasts are unaffected; the claim 'A = the AGREE arm's bytes' holds only modulo these fields.

## Fit

`supply_variants.fit_estimate` {"base_prompt_tokens": 1, "completion_ceiling": 512, "slot_tokens": 24576, "tokens_per_supplied_item": 325}, measured from the sealed wave A/A and W4
Solver requests (`analysis/SAEA-SLURP-STAGE3-W4SV-FIT-MEASURE-V1/fit-measure-v1.json`): per-item ratio envelope; estimate at `max_supplied_items` 56
(the structural sum of the supply caps; realised max 55) is
18,201 tokens against the 20,990-token limit
(headroom 2,789). Realised Solver prompt maxima: AGREE bytes
14,851, W4 16,696.

| cell | phase | decision | rendered (4 B/token) | operational margin | physical margin |
| --- | --- | --- | ---: | ---: | ---: |
| arm | perception | ALLOW | 19453 | 1508 | 4580 |
| arm | reviewer | ALLOW | 19316 | 1645 | 4717 |
| arm | planner | ALLOW | 19256 | 1705 | 4777 |
| arm | solver | COMPACT_REQUIRED | 21281 | -320 | 2752 |
| smoke | perception | ALLOW | 19452 | 1509 | 4581 |
| smoke | reviewer | ALLOW | 19316 | 1645 | 4717 |
| smoke | planner | ALLOW | 19255 | 1706 | 4778 |
| smoke | solver | COMPACT_REQUIRED | 21281 | -320 | 2752 |

The check composes the delivering path; arm b-w4's widest request is cell W4's first Solver request, whose preflight
physical margin at 24,576 was 826 tokens (`docs/readiness/2026-09-27-slurp-stage3-w4-slot-conventions-fold-a-v1/registered-facts-v1.json`, `fit`), COMPACT_REQUIRED under the
armed compact-or-abstain policy with a non-negative physical margin.

## Decision rule (fixed here)

Columns: the first-visit Solver answers of arm b-w4 (B), the twin t-twin (T) and the delivering arm a-agree (A), each rendered through the delivered row's deliver normaliser and projection (AT1 self-check) and scored ONCE as a complete column with slurp-slu-official-train (stage3_rollout_score.py --mode supply-variants), paired by row (sample_id), 10,000 draws, seed 20260928. THE NULL: T minus A on official pooled SLU-F1 and intent accuracy; its bar is |T - A delta| + the T - A CI95 half-width (the same law as the cross-flight in-chain A/A), never below the provisional floor 0.3163 pp SLU-F1 (the ROLL-AA anchor 0.735 pp at n = 200 scaled to n = 1,080, scripts/checks/stage3_effect_floor_check.py). INSTRUMENT FAULT (no verdict): the T - A CI95 excludes zero on either metric. NOMINATED (the claim ceiling; Q6 ruling): the B - A official pooled SLU-F1 delta exceeds the bar AND its CI95 lower bound is above zero AND the B - A intent CI95 upper bound is not below zero (the guard: no measured intent loss). HARMFUL: the B - A CI95 upper bound below zero on either metric. Otherwise NOT NOMINATED (width). A nomination only sends the composed policy to a full-system read against an in-chain A/A; it is never an admission and never a system-level claim. Every verdict carries the per-scenario table in both weightings and the per-type exact TP/FP/FN of the 19 revised types, B vs A and T vs A.

## Files

| file | what it holds |
| --- | --- |
| `../2026-09-28-slurp-stage3-w4-sv-fold-a-v1-preregistration.md` | the preregistration, with the `stage3_measurement` fence |
| `registered-facts-v1.json` | every model-free fact; the CANONICAL `stage3_measurement` |
| `arm-a-byte-identity-proof-v1.json` | the arm-A / twin / arm-B byte proof |
| `protocol-registered-v1.json` | identities, hashes, the rule |
| `generation-plan-registered-v1.json` / `fit-plan-registered-v1.json` | the arm's plans |
| `smoke-generation-plan-registered-v1.json` / `smoke-fit-plan-registered-v1.json` | the smoke's plans |
| `analysis-recipe-v1.json` | the column read; `read_run_id` = `SAEA-SLURP-STAGE3-W4SV-FOLD-A-COLUMN-READ-V1` |
| `root-admission-draft-v1.json` | the receipt root mints with `scripts/flights/w4sv/w4sv_mint_receipt.py` |

**Sequence.** (1) The arm-B blocker is fixed and `w4sv_arm_a_proof.py` re-run reports ARM-B-VARIES (the flip refuses
otherwise) -- DONE: ARM-B-VARIES at c24824a46. (2) Root countersigns the DRAFT rows (four flight rows and the two model-free rows; the READ row stays
draft until the seal) and mints `coordination/slurp-stage3-w4sv-fold-a-v1/root-admission-v1.json`. (3) `scripts/flights/w4sv/w4sv_flip.sh` (smoke, then arm; minted
supplies must reproduce the AGREE digests). (4) `scripts/flights/w4sv/batch_chain_w4sv.sh` on slurp-np4 through the
batch driver. (5) `scripts/flights/w4sv/w4sv_read.sh`.

**Budgets.** Arm 14,040 generation contacts, 56,160 FIT endpoints,
40,099 speech seconds, 12.0 GPU hours; smoke
52 / 208 / 138 / 1.0.
