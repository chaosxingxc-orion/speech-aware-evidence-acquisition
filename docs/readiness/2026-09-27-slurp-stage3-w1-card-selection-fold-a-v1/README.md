# Cell W1: slot-card selection (knowledge wave item W1)

Registered before contact 2026-09-27 at study commit `88edc193272f9bdb11f5099124b03cbb39f7d5b0` (owner decision 164, a row-127
no-harm FORM item derived from the retained AGREE arm, decision 161); both cells **held**. Nothing here authorises a
flight, a flip or an admission entry.

**The deficit.** [`docs/results/2026-09-27-slurp-knowledge-content-audit.md`](../../results/2026-09-27-slurp-knowledge-content-audit.md) K8: 12.9 slot-contract cards reach the Solver per row and
91.1 % of their text serves neither the delivered nor the gold slot types, under a Solver envelope with 226 tokens of
headroom (21,278 of 21,504 usable).

**What was measured first** (`scripts/build_slurp_intent_slot_legality.py`, model-free). The flown card route already selects through the authored
`intent_bindings`, and those 402 bindings are EXACTLY the (intent, slot type) pairs the released 9,354-utterance
exemplar store carries at least once. So "legal under a candidate intent" by mere presence is what flies today; the
unused text comes from ANECDOTAL bindings -- 116 of the 402 pairs are witnessed by one pool utterance.

**The one change.** `knowledge_stores.slot-contracts.candidate_supply.solver.candidate_legality_source` = the pinned table `prepared/SAEA-SLURP-INTENT-SLOT-LEGALITY-POOL-V1/legality.json` (sha256
`59b507b4e36970d4328b3442a31c790c2be48e2e47f4247bd3764bf2fddd1bad`, receipt beside it): the route keeps the 286 pairs the store carries in
at least two distinct utterances (rule `pool-utterance-support-at-least-2-v1`). A table can only remove an authored
binding (the loader refuses one that adds). Caps (3 / 16 / 28), stores, roster, geometry, templates: the AGREE arm's.

**What it saves** (`scripts/analysis/slurp_w1_card_selection_measurement.py` -> [`card-selection-measurement-v1.json`](card-selection-measurement-v1.json); the
flown selection replayed identically on 1,080 / 1,080 rows first; exact tokens by the local vocab-only tokenizer,
54 invocations): cards per row 12.904 -> 9.869; Solver prompt tokens per contact
**-1185.83** on average (median 1070, p95 2483, max 3652);
**-3629.596** per row over the Solver, Reviewer and Planner contacts that render the block;
3,919,964 per 1,080-row flight. Pre-flight card envelope 57,846 -> 50,030 UTF-8 bytes.

**What it risks** (gold read offline, ids and type names only): **5 rows** lose a card for a gold slot type
(5 gold items; **1** of them the AGREE arm delivered exactly right); rows with every gold type carded
654 -> 649 of 666; 12 rows' delivered answer used a type whose card W1 drops;
1 row receives no card at all (disposition `no-mapping`; its exemplars still arrive).

| row | lost gold type | gold intent's shortlist position | pool support under the gold intent | AGREE right | error-source item |
| --- | --- | --- | --- | --- | --- |
| `slurp:train:003057:audio-1490201218` | general_frequency | not shortlisted | general_frequency: 1 | 0 of 1 | MISSING |
| `slurp:train:010065:audio-1501756518` | food_type | not shortlisted | food_type: 70 | 1 of 1 | -- |
| `slurp:train:012069:audio-1492780300` | business_name | 1 | business_name: 0 | 0 of 1 | NEAR |
| `slurp:train:012876:audio-1502309870-headset` | business_name | 1 | business_name: 1 | 0 of 1 | WRONG-TYPE |
| `slurp:train:016867:audio-1497438083` | relation | not shortlisted | relation: 79 | 0 of 1 | MISSING |

Sensitivity (computed on the same arm before the rule was fixed, disclosed): min support 3 -> 10 harmed rows, 5 -> 22.

**Fit.** Before (the sealed AGREE preflight): Solver rendered 21,278, `COMPACT_REQUIRED`, physical margin
2,755. After: Solver rendered 21,278 -> 19,272 tokens, required window 21,821 -> 19,815, physical margin 2,755 -> 4,761, operational margin -317 -> 1,689, decision COMPACT_REQUIRED -> ALLOW.

**`stage3_measurement`.** `admission` `no-harm`, `harm_margin_pp` 1.2485 (by metric intent 0.9943 / SLU 1.2485, the G5
precedent), `claims_benefit` false, `expected_effect_pp` 0.0, `cross-flight-with-in-chain-replicate`, `replicate_run_id`
`SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1` (the coordinator's shared A/A of the AGREE arm's own bytes), `declared_ceiling` the measured saving.

| file | what it holds |
| --- | --- |
| `../2026-09-27-slurp-stage3-w1-card-selection-fold-a-v1-preregistration.md` | the preregistration, including the `stage3_measurement` fence |
| `card-selection-measurement-v1.json` | the replay, the saving, the harm rows, the static bound, the sensitivity grid |
| `registered-facts-v1.json` | every model-free fact, the one-key diff, the CANONICAL `stage3_measurement` |
| `protocol-registered-v1.json` | identities, hashes, the no-harm rule, the registered risk |
| `generation-plan-registered-v1.json` / `fit-plan-registered-v1.json` | the arm's plans |
| `smoke-generation-plan-registered-v1.json` / `smoke-fit-plan-registered-v1.json` | the smoke's plans |
| `analysis-recipe-v1.json` | the paired read, READ run id `SAEA-SLURP-STAGE3-W1-CARDSEL-FOLD-A-PAIRED-ANALYSIS-V1` |
| `root-admission-draft-v1.json` | the receipt root mints with `scripts/flights/w1/w1_mint_receipt.py` |

**Mint, flip, queue.** Root countersigns the seven DRAFT rows (SAEA-SLURP-STAGE3-W1-CARDSEL-FOLD-A-V1, SAEA-SLURP-STAGE3-W1-CARDSEL-FOLD-A-FIT-V1, SAEA-SLURP-STAGE3-W1-CARDSEL-FOLD-A-SMOKE-4-V1,
SAEA-SLURP-STAGE3-W1-CARDSEL-FOLD-A-SMOKE-4-FIT-V1, `SAEA-SLURP-INTENT-SLOT-LEGALITY-POOL-V1`, `SAEA-SLURP-W1-CARD-SELECTION-MEASUREMENT-V1`, and the READ row `SAEA-SLURP-STAGE3-W1-CARDSEL-FOLD-A-PAIRED-ANALYSIS-V1`, which may stay DRAFT until the
seal), mints `coordination/slurp-stage3-w1-cardsel-fold-a-v1/root-admission-v1.json` (id `slurp-stage3-w1-cardsel-fold-a-admission-v1`, four eligible run ids) with `scripts/flights/w1/w1_mint_receipt.py`,
flips with `scripts/flights/w1/w1_flip.sh` (the generic re-pin loop over `w1_repin_smoke.sh` and `w1_repin_arm.sh`,
converged at one HEAD), and queues the arm in ONE chain with `SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1`. The minted supplies must carry the AGREE
output digests (arm `eab5c61e...`, smoke `308601c5...`).
