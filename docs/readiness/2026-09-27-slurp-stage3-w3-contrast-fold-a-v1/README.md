# Cell W3a: intent contrast cards (W3 re-registered as W3a alone)

Registered before contact 2026-09-28T00:25:55.000000+00:00 at study commit `e9b4a8ee` (owner decision 164,
knowledge-wave item W3). First registered 2026-09-27 at study commit `701bd63a` as W3a + W3b; **re-registered in place as W3a
alone** (see [Re-registration](#re-registration) below). Both cells are **held**. Nothing here authorises a flight, a
flip or an admission entry.

**Why.** [`docs/results/2026-09-27-slurp-knowledge-content-audit.md`](../../results/2026-09-27-slurp-knowledge-content-audit.md) K1: every intent card carries one
activation sentence and one confusable exclusion, and 57.7 % of it is boilerplate; on 75 of the AGREE arm's 153
intent-wrong rows both the right and the chosen card are delivered and neither names the other. The mechanism
synthesis: every gain so far was row-matched CONTENT to the deciding node -- so W3a adds content and pays for it
inside the tokens it removes.

**W3a -- contrast cards, the one change** (`scripts/build_slurp_intent_contrast_cards.py`, release `knowledge/slurp/semantic/intent-boundaries-contrast-v1`, content hash
`130e9e2e7942a70ec2c556fd6846b7c3a3bd19572222c1b32f11d41e4ff1c2fb`, receipt [`docs/receipts/knowledge/slurp-intent-contrast-cards-v1.json`](../../receipts/knowledge/slurp-intent-contrast-cards-v1.json)). Each card keeps its
header, activation boundary, authored exclusion and card-specific limitation bullets verbatim; the uncertainty sentence
(identical on all 60) and the shared limitation bullet are removed; a section
`Nearest rivals, typical TRAIN words (this intent | rival):` adds one line per nearest TRAIN-centroid rival (KPROBE's
centroid keys), `- <rival>: <word>, <word> [<slot type>] | <word>, <word> [<slot type>]` -- the two words most typical of
each side's TRAIN requests against the other (document-frequency gap, outside annotated slot spans, at least 3
utterances, function words and the wake word excluded) and the slot type one side carries and the other does not, from
the R01-excluded pool (8,554 utterances, disjoint from Fold A, Fold B and R01, checked). Rivals are added nearest-first
only while the card tokenises to no more tokens than the flown card (the G5 measurement's vocab-only tokenizer):
**7,389 -> 6,932 tokens over the 60 cards (-457), max per-card delta
+0**, rivals carried per card {"2": 11, "3": 38, "4": 11}. Facets, keys and value ids are
unchanged, so Perception's delivered set is the AGREE arm's own.

**Against the AGREE bytes** (composed configs, `registered-facts-v1.json` `composed_config_diff_against_the_agree_cell`,
re-proven by `tests/unit/test_w3_config.py`): only `knowledge_stores.intent-boundaries.{release,snapshot}.{relpath,sha256}`
move (intent-boundaries-v1 -> intent-boundaries-contrast-v1), plus the contrast release's two frozen source receipts and
per-flight bookkeeping. The Solver's `knowledge_stores.train-exemplars.phase_supply.solver` is the AGREE arm's, byte for
byte (`saea-fuse-supplyfilter-v1`, `k` 20, `c`/`m`/`top_l` 20) -- the condition
`scripts/flights/wave/wave_preconditions.py` checks before the wave flips or flies.

**Fold A offline table** (the AGREE arm's own chosen intents and delivered sets; counts only):

| quantity | value |
| --- | ---: |
| intent-wrong rows | 153 |
| pair named on a delivered card, before (authored exclusion alone) | 41 |
| pair named on a delivered card, after (plus the contrast lines) | 89 |
| of the 75 rows with both cards delivered and neither naming the other, named after | 41 |

**The expectation, and its basis.** None is declared (`expected_effect_pp` 0.0, `claims_benefit` false): row 139
allows an expectation only from a measured conversion analogue, and the two this programme has (CONV 32 of 70 = 0.457,
KPROBE 24 of 55 = 0.436) are conversions of a NEWLY DELIVERED gold card at Perception. W3a delivers nothing new -- it
changes what an already-delivered card says. So W3a is registered as a **no-harm read** and says so; the package
declares no separate W3a number from a measured basis, so the re-registration keeps 0.0. For scale only (not declared,
not gated): the 48 newly named rows at the CONV rate would be
2.032 pp.

**Fit.** The held `core.flight.cli check` (runtime placeholder counter, widest representative request) reads ALLOW on all four phases of the arm: perception 19,087, reviewer 18,951, planner 18,890, Solver 20,916 rendered tokens -- -362 on every phase against the AGREE arm's registered 19,449 / 19,313 / 19,252 / 21,278 (the eight longest cards are shorter; the bound counts the twenty longest exemplars either way) -- Solver operational margin 45 and physical margin 3,117 on the 24,576-token slot, no blockers. Realised requests: the sealed AGREE arm's largest contact prompt was 14,561 tokens over 4,385 contacts against the per-contact limit 20,990; W3a moves every later contact by the card delta alone, -60.494 tokens on average (min -106, max -3: no contact grows), because the Solver exemplar block is the AGREE arm's own. Nothing must be freed for W3. The first-phase supply minted to a scratch path at this implementation carries the AGREE family's own digests (arm eab5c61e, 8,624 ids on 1,080 rows; smoke 308601c5). Receipt: [`preflight-proofs-v1.json`](preflight-proofs-v1.json).

**`stage3_measurement`.** The arm declares `admission` `no-harm`, `harm_margin_pp` 1.2485 (by metric intent 0.9943 /
SLU 1.2485), `claims_benefit` false, `expected_effect_pp` 0.0, `measurement_design`
`cross-flight-with-in-chain-replicate`, `replicate_run_id` **`SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1`** -- the shared wave-1 A/A the coordinator
registers (not this package). The READ is registered with the flight: `analysis-recipe-v1.json` declares
`run_ids.read` **`SAEA-SLURP-STAGE3-W3-FOLD-A-PAIRED-ANALYSIS-V1`** and its DRAFT ledger row exists.

**Attribution.** W3a is one change against the AGREE arm, so the arm-minus-A/A delta is the contrast cards' by
construction; the recipe's row attribution (step 6) splits it over the rows whose pair the contrast lines newly name.

**Implementation identity.** `rails/kb_policy.py` carries the registered target-capped fuser (merged with the first
registration); W3a does not use it, and the flown default selection is unchanged. Every prepared supply's identity
hashes that module, so any READY-but-unflown cell of another family is re-pinned at its flight commit.

**Mint, flip, queue.** Root countersigns the seven DRAFT rows, mints `coordination/slurp-stage3-w3-contrast-fold-a-v1/root-admission-v1.json` (id `slurp-stage3-w3-contrast-fold-a-admission-v1`) with
`scripts/flights/w3/w3_mint_receipt.py` (four eligible ids), flips inside the wave with
`scripts/flights/wave/wave_flip.sh` (smoke, then arm, converging at one HEAD; `--allow-output-change` never passed; the
minted supplies must carry the AGREE family's own output digests), and the wave chain flies the arm as step 2 of
`scripts/flights/wave/batch_chain_wave.sh`, A/A -> W1 -> W3a -> W4 (decision 77).

| file | what it holds |
| --- | --- |
| `../2026-09-27-slurp-stage3-w3-contrast-fold-a-v1-preregistration.md` | the preregistration, including the `stage3_measurement` fence |
| `registered-facts-v1.json` | every model-free fact, the composed diff, the CANONICAL `stage3_measurement`, the ruling |
| `protocol-registered-v1.json` | identities, hashes, the no-harm rule, the claim boundary |
| `generation-plan-registered-v1.json` / `fit-plan-registered-v1.json` | the arm's plans |
| `smoke-generation-plan-registered-v1.json` / `smoke-fit-plan-registered-v1.json` | the smoke's plans |
| `analysis-recipe-v1.json` | the paired read at the shared A/A, with `run_ids.read` |
| `offline-estimates-v1.json` | the contrast membership counts, the request-size projection, and the dropped cap's Fold B tuning and Fold A counts |
| `preflight-proofs-v1.json` | the held check per phase (Fit), the scratch-minted first-phase supply digests, the realised AGREE request sizes |
| `root-admission-draft-v1.json` | the decision receipt root mints with `w3_mint_receipt.py` |

**Not authorised by this package.** No flight before the receipt is minted and the cells are flipped; no contact by this
registration; no re-flying of the comparator; no test-split or DEV read (Fold B was read offline, for tuning only); no
second or third factor; no report of a gain; no admission entry.

## Re-registration

**2026-09-27 -- coordinator ruling (Fable 5.1) under owner decision 164's one-change rule; re-registered
2026-09-28T00:25:55.000000+00:00.** The wave's W3 cell is
re-derived as **W3a alone**: the intent contrast cards with the Solver exemplar supply restored to exactly the AGREE
arm's (no per-intent exemplar cap). W3b is dropped because it is a second change with no measured upside. Each fact,
with the file and section it comes from ("the first README" is this file as committed at `94c88036`):

1. **On Fold A the cap removes no wrong-intent plurality**: 0 of the 153 intent-wrong
   rows (`offline-estimates-v1.json` `fold_a_estimates.exemplar_cap.wrong_rows.wrong_plurality_removed`; the first
   README's "Fold A offline table", row "wrong rows whose wrong-intent plurality the cap removes").
2. **On Fold B a cap of 11 scores GAIN 0 / HARM 0**
   (`offline-estimates-v1.json` `fold_b_tuning.table["11"]`; the first README's "W3b -- per-intent exemplar cap"
   section, Fold B tuning table, row N = 11). Every smaller cap scores HARM above GAIN on Fold B (same table, N <= 10).
3. **It changes 700 Solver blocks on the 927 rows the AGREE arm got right**, lowering the gold
   exemplar count on 665 of them (`offline-estimates-v1.json`
   `fold_a_estimates.exemplar_cap.right_rows.block_changed` and `gold_count_down`; the first README's "Fold A offline
   table", row "right rows whose block the cap changes / whose gold count falls").

**How it was derived.** Exactly `registered-facts-v1.json` `attribution_split.how_to_derive` for W3a alone ("this
baseline with the train-exemplars Solver supply restored to AGREE's (fuse_policy saea-fuse-supplyfilter-v1, k 20,
m/c/top_l 20)"), by `scripts/flights/w3/derive_slurp_w3_cells.py`, which now derives W3a alone. Same run ids, same
attempt ids, same package directory: a re-registration of unflown cells. The seven DRAFT exposure rows are rewritten in
place by run id (never duplicated), each carrying a RE-REGISTERED note.

**What moved.** The four config fragments (composed and protocol hashes: arm `3440eefb7d01` /
`b51a0a435f1f`, smoke `cb4b2b74df12` / `4ddc7b3f9fcc`), the plans, the
protocol, the facts, the recipe (steps 2 and 6), the draft receipt, the preregistration, the pre-flight proofs and the
ledger rows. The pre-flight proofs were re-run at `e9b4a8ee`: before (the first registration, `701bd63a`)
perception 19,087 / reviewer 18,951 / planner 18,890 / Solver 20,916 rendered tokens, Solver operational margin 45 and
physical margin 3,117; supply digests arm eab5c61e and smoke 308601c5. After: perception 19,087 / reviewer 18,951 / planner 18,890 / Solver 20,916 rendered tokens, Solver operational margin 45 and physical margin 3,117; first-phase supply digests arm eab5c61e and smoke 308601c5. The numbers are identical
because the pre-flight bound counts the twenty longest exemplars whether the cap is present or not.

**What did not move.** The contrast-card release, the offline read (kept as the record of the dropped cap and as the
source of the contrast membership set), `expected_effect_pp` 0.0 (the package declares no separate W3a number from a
measured basis), the harm margins, the READ run id, the four eligible run ids, the caps and the shared A/A.
