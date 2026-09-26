# Cell AGREE: the agreement term on the intent-boundary retrieval channel

Registered before contact 2026-09-26 at study commit `c452c048`; all three cells **held**.
Nothing here authorises a flight, a flip or an admission entry.

**The one factor.** The intent-boundary Perception channel reads its own registered w_agree term over a pre-computed, self-excluded exemplar-intent vote: w_agree 1.0, k unchanged at 8, w_cos unchanged at 1.0, w_prior unchanged at 0.0. Nothing else moves.

**Why.** [`docs/results/2026-09-26-slurp-intent-retrieval-rank-diagnostic.md`](results/2026-09-26-slurp-intent-retrieval-rank-diagnostic.md) measured where the gold intent
actually ranks in the flown Perception boundary retrieval: median rank 10-14 on intent-wrong rows
against 1 on correct rows, spread down the whole tail, so widening `k` is not the fix -- `k` 16
leaves over two thirds still missing, and `k` 30 buys the same delivery as this change for +3,262.3
tokens a row instead of +1.4. The exemplar channel already ranks the gold intent first on 76.1 % of
rows against the boundary cosine's 65.6 %, so this change lets the boundary ranker borrow a signal
the system already computes. Selected from 27 candidates by a rule fixed before the numbers were
read; measured delivery on intent-wrong rows 45.0 % -> 81.7 % on the fit roster, with a +30.4-point
floor on the two rosters the weight was not fitted on.

| file | what it holds |
| --- | --- |
| `../2026-09-26-slurp-stage3-agree-w1-fold-a-v1-preregistration.md` | the preregistration proper, including the `stage3_measurement` fence |
| `registered-facts-v1.json` | every model-free measured fact, and the CANONICAL `stage3_measurement` |
| `protocol-registered-v1.json` | identities, hashes, budgets, the decision rule, the claim boundary |
| `generation-plan-registered-v1.json` / `fit-plan-registered-v1.json` | the AGREE arm's plans |
| `aa-generation-plan-registered-v1.json` / `aa-fit-plan-registered-v1.json` | the in-chain A/A replicate's plans |
| `smoke-generation-plan-registered-v1.json` / `smoke-fit-plan-registered-v1.json` | the four-row form smoke's plans |
| `analysis-recipe-v1.json` | how the sealed output is read offline, under its own later-registered read id |
| `identity-proof-v1.json` | the byte-identity proof: the default's selection is unchanged |
| `production-replication-v1.json` | the production path reproducing the read's own delivery numbers |

**Three cells, one chain.** The campaign plan `configs/campaign/slurp-native-stage3-agree-w1-fold-a-v1.json`
carries the A/A replicate **and** the AGREE arm, because a cross-flight contrast against a sealed
comparator with no in-chain replicate is refused outright ([`docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md`](readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md) rule 4:
a pure A/A pair at n = 625 read +1.87 pp with a CI95 excluding zero). The smoke is outside the plan
and is never scored.

**The expected effect, stated as what it is.** Declared `expected_effect_pp`
**1.363** pp official pooled SLU-F1, derived as the measured
newly-delivered rows per bad-case class times that class's measured perfect-repair headroom, times a
**stated, unmeasured** conversion of 0.467895. The ceiling at a perfect conversion is
2.9131 pp. The design's admission bar at n = 1,080
is 2.5 pp, so the declaration **DOES NOT CLEAR** it. That is reported, not engineered
around: delivery is not correctness, the conversion is this cell's primary unknown, and inflating the
declaration to clear a bar is the one move this registration refuses. A NEUTRAL read would mean the
conversion is below what this design can see -- mode (iv) of the read, and the programme's next
question.

**Byte identity of the default.** The A/A cell's own prepared first-phase supply, minted at the
changed implementation, carries output SHA-256 `ba5e1faab9550fcae700f649a0ec6674327ffefe97d7044bb7ea3887536fb54f` -- the sealed comparator's
own digest, on all 1,080 rows. The treatment's differs, so the change is not inert.

**Mint, flip, queue.** Root mints `coordination/slurp-stage3-agree-w1-fold-a-v1/root-admission-v1.json`
(id `slurp-stage3-agree-w1-fold-a-admission-v1`) with the six eligible run ids and this family's
caps, countersigns the exposure rows, then re-pins all three cells with
`scripts/flights/repin_cell.py --set-ready`. `--allow-output-change` must never be passed: no cell
here carries a committed `prepared_phase_supply` and the flip mints each cell's own.

**Not authorised by this package.** No flight before the receipt is minted and all three cells are
flipped; no contact by this registration; no re-flying of the comparator; no test-split, Fold B or DEV
read; no second factor; no `w_prior` change; no store rebuild.
