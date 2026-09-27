# Cell W3: intent contrast cards + a per-intent exemplar cap

Registered before contact 2026-09-27 at study commit `9673e9e2` (owner decision 164,
knowledge-wave item W3); both cells **held**. Nothing here authorises a flight, a flip or an admission entry.

**Why.** [`docs/results/2026-09-27-slurp-knowledge-content-audit.md`](../../results/2026-09-27-slurp-knowledge-content-audit.md) K1: every intent card carries one
activation sentence and one confusable exclusion, and 57.7 % of it is boilerplate; on 75 of the AGREE arm's 153
intent-wrong rows both the right and the chosen card are delivered and neither names the other. K6: on 38 wrong rows
none of the 20 delivered exemplars carries the gold intent, and on 93 the exemplar majority is the chosen (wrong)
intent. The error-source read: the 20 exemplars outvote gold on 107 of 152. The mechanism synthesis: every gain so far
was row-matched CONTENT to the deciding node -- so W3 adds content and pays for it inside the tokens it removes.

**W3a -- contrast cards** (`scripts/build_slurp_intent_contrast_cards.py`, release `knowledge/slurp/semantic/intent-boundaries-contrast-v1`, content hash
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

**W3b -- per-intent exemplar cap** (`saea-fuse-supplyfilter-target-cap-v1` in `rails/kb_policy.py`; the pure rule `select_target_capped`).
The Solver's 20 exemplars are taken in cosine order with at most **N = 11** per intent, recall/admission depth
**300** so the block still fills 20. **Fold B tuning** (`scripts/analysis/slurp_w3_contrast_cap_offline.py`, gold offline; rule fixed before reading:
the smallest N whose GAIN -- unique wrong-intent pluralities removed -- is at least its HARM -- unique gold pluralities
removed):

| N | GAIN | HARM | net | gold presence gained | absolute gold majority broken | blocks changed | blocks filled |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 20 | 0 | 0 | 0 | 0 | 0 | 0 | 1080 |
| 19 | 0 | 0 | 0 | 0 | 0 | 146 | 1080 |
| 18 | 0 | 0 | 0 | 0 | 0 | 261 | 1080 |
| 17 | 0 | 0 | 0 | 0 | 0 | 360 | 1080 |
| 16 | 0 | 0 | 0 | 5 | 0 | 439 | 1080 |
| 15 | 0 | 0 | 0 | 5 | 0 | 506 | 1080 |
| 14 | 0 | 0 | 0 | 5 | 0 | 558 | 1080 |
| 13 | 0 | 0 | 0 | 6 | 0 | 618 | 1080 |
| 12 | 0 | 0 | 0 | 8 | 0 | 661 | 1080 |
| 11 | 0 | 0 | 0 | 9 | 0 | 710 | 1080 |
| 10 | 8 | 41 | -33 | 9 | 673 | 782 | 1080 |
| 9 | 27 | 140 | -113 | 10 | 673 | 832 | 1080 |
| 8 | 57 | 249 | -192 | 11 | 673 | 893 | 1080 |
| 7 | 87 | 363 | -276 | 14 | 673 | 948 | 1080 |

Every cap below 11 breaks more right-intent pluralities than wrong-intent ones on Fold B; N = 11 breaks none
of either and still lets other intents into blocks one intent used to fill. The Fold A top 20 re-derived offline equals
the AGREE arm's sealed Solver consumption on 1080 of 1080 rows and the Fold B top 20
reproduces the pinned Fold B agreement table on 1080 of 1080.

**Fold A offline table** (the AGREE arm's own chosen intents and delivered sets; counts only):

| quantity | value |
| --- | ---: |
| intent-wrong rows | 153 |
| pair named on a delivered card, before (authored exclusion alone) | 41 |
| pair named on a delivered card, after (plus the contrast lines) | 89 |
| of the 75 rows with both cards delivered and neither naming the other, named after | 41 |
| wrong rows with 0 gold exemplars in the 20 | 38 |
| ... of which the cap brings >= 1 gold exemplar in | 6 |
| wrong rows whose gold exemplar count rises | 28 |
| wrong rows whose wrong-intent plurality the cap removes | 0 |
| RISK: right rows whose unique gold plurality the cap breaks | 0 |
| RISK: right rows whose absolute gold majority (> 10 of 20) the cap breaks | 0 |
| right rows whose block the cap changes / whose gold count falls | 700 / 665 |

**The expectation, and its basis.** None is declared (`expected_effect_pp` 0.0, `claims_benefit` false): row 139
allows an expectation only from a measured conversion analogue, and the two this programme has (CONV 32 of 70 = 0.457,
KPROBE 24 of 55 = 0.436) are conversions of a NEWLY DELIVERED gold card at Perception. W3a delivers nothing new -- it
changes what an already-delivered card says -- and W3b changes a block delivered to the Solver, another node and
channel. So W3 is registered as a **no-harm read** and says so. For scale only (not declared, not gated): the
48 newly named rows plus the 6 rows given a gold exemplar, at the CONV rate, would be
2.286 pp.

**Fit.** not measured in this write (pass --check-arm)

**`stage3_measurement`.** The arm declares `admission` `no-harm`, `harm_margin_pp` 1.2485 (by metric intent 0.9943 /
SLU 1.2485), `claims_benefit` false, `expected_effect_pp` 0.0, `measurement_design`
`cross-flight-with-in-chain-replicate`, `replicate_run_id` **`SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1`** -- the shared wave-1 A/A the coordinator
registers (not this package). The READ is registered with the flight: `analysis-recipe-v1.json` declares
`run_ids.read` **`SAEA-SLURP-STAGE3-W3-FOLD-A-PAIRED-ANALYSIS-V1`** and its DRAFT ledger row exists.

**Split into W3a and W3b.** Affordable (about 1.8816 GPU hours each at the AGREE rate, read at the
same shared A/A) and NOT registered: the brief registers it only if the coordinator asks. Without it the read attributes
by exposure (step 6 of the recipe), not by ablation.

**Implementation identity.** `rails/kb_policy.py` gains the fuser, so every prepared supply's identity moves on the
merge: any READY-but-unflown cell of another family must be re-pinned at its flight commit.

**Mint, flip, queue.** Root countersigns the seven DRAFT rows, mints `coordination/slurp-stage3-w3-contrast-fold-a-v1/root-admission-v1.json` (id `slurp-stage3-w3-contrast-fold-a-admission-v1`) with
`scripts/flights/w3/w3_mint_receipt.py` (four eligible ids), flips with `scripts/flights/w3/w3_flip.sh` (smoke, then arm,
converging at one HEAD; `--allow-output-change` never passed; the minted supplies must carry the AGREE family's own
output digests), and queues the arm in the wave-1 chain beside `SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1` (decision 77).

| file | what it holds |
| --- | --- |
| `../2026-09-27-slurp-stage3-w3-contrast-fold-a-v1-preregistration.md` | the preregistration, including the `stage3_measurement` fence |
| `registered-facts-v1.json` | every model-free fact, the composed diff, the CANONICAL `stage3_measurement` |
| `protocol-registered-v1.json` | identities, hashes, the no-harm rule, the claim boundary |
| `generation-plan-registered-v1.json` / `fit-plan-registered-v1.json` | the arm's plans |
| `smoke-generation-plan-registered-v1.json` / `smoke-fit-plan-registered-v1.json` | the smoke's plans |
| `analysis-recipe-v1.json` | the paired read at the shared A/A, with `run_ids.read` |
| `offline-estimates-v1.json` | the Fold B tuning table and the Fold A counts (the membership sets' counts) |
| `root-admission-draft-v1.json` | the decision receipt root mints with `w3_mint_receipt.py` |

**Not authorised by this package.** No flight before the receipt is minted and the cells are flipped; no contact by this
registration; no re-flying of the comparator; no test-split or DEV read (Fold B was read offline, for tuning only); no
third factor; no report of a gain; no admission entry.
