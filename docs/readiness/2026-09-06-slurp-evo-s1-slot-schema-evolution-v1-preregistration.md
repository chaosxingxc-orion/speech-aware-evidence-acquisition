# EVO-S1: slot-schema evolution on SLURP — preregistration (DRAFT)

**Status: DRAFT.** This document is complete but unregistered. The coordinator closes it by (1)
ratifying the reward metric (section 4), (2) choosing the curve/final read option (section 7), (3)
ruling on the fold-quota power arithmetic (section 16, open point 1), (4) admitting the SLURP half of
track E3c, which does not exist (section 12), and (5) writing the exposure rows. Nothing here
authorizes a contact.

Cell EVO-S1 of `docs/readiness/2026-09-05-three-dimension-experiment-program.md` (section 4c, loop
constants section 5), the **generality rung** of the system-evolution dimension: the same loop code
and the same selection rule as EVO-A1, hash-pinned, on a second carrier. Owner directive of
2026-09-06 makes EVO-S1 the PRIMARY demonstration of that dimension.

| prerequisite | receipt | state |
|---|---|---|
| MF-3, the per-intent TRAIN slot schema (`A_0`) | `docs/receipts/knowledge/slurp-intent-slot-schema-v1.json` | closed |
| KC-S1b, the mechanism this cell evolves | `docs/readiness/2026-09-05-slurp-slot-stage-kc-s1-v1-verdict.md` | **ADMITTED**, +8.55 SLU-F1 |
| construction capacity, `SAEA-SLURP-MF-EVO-CONSTRUCTION-CAPACITY-V1` | `docs/checks/speech-aware-evidence-acquisition/2026-09-06-slurp-evo-construction-capacity/` | closed, **no wall** |
| the three loop rosters, `SAEA-SN-MF-SLURP-EVO-FOLD-ROSTERS-V1` | `docs/receipts/rosters/slurp-evo-{fold-a,fold-b,exemplars}-v1.json` | frozen |
| MF-5, the multi-phase seal path on SLURP | `docs/checks/speech-aware-evidence-acquisition/2026-09-05-slurp-phase-smoke-4-v1/` | closed |

---

## 1. Hypothesis

**H1.** The per-intent slot schema block that KC-S1b admitted — entity types above a 2 % share, their
shares, and up to five TRAIN fillers each — is not the best block a frozen core can be given. Shown
only its own incumbent block and eight construction utterances of that scenario with their gold
entities, the frozen core can rewrite the block so that per-row slot F1 rises on rows it has never
seen; a best-of-K selection over four rounds, scored by the official scorer on held-out construction
folds and never on evaluation data, produces a schema whose gain survives one read on DEV.

**H2 (the two controls that decide what H1 means).** The **shares-only** control — the incumbent
block with every filler list deleted, shares and types untouched — is the content floor: the KC-S1b
verdict attributes the whole +8.55 to "which types this intent uses, **with the fillers TRAIN heard
for them**", and a proposer that cannot beat a block with the fillers removed has learned nothing
about fillers. The **token-matched form twin** — the incumbent block with every filler replaced by a
neutral placeholder at equal token count — is the form floor: if it is indistinguishable from the
proposer's rewrite, the effect is prompt volume, not filler content. Both are built without a model
contact.

**The ceiling, stated before takeoff.** KC-S1b took NEW500 slot F1 from 14.49 to 24.60 and SLU-F1
from 35.80 to 44.35. The remaining distance to the weakest published trained pipeline is 19.67
SLU-F1 points, and the per-entity-type table says where it is not recoverable from a schema: the
types already at their ceiling (`definition_word` 64.3, `artist_name` 42.9) and the types whose
filler is an open proper noun no block can enumerate (`business_name` 13.9, `event_name` 4.8,
`person` 17.9 — 134 of 950 gold mentions). EVO-S1 is a test of whether the loop mechanism transfers
to a second carrier and a second artifact family; it is not a bid to close the pipeline gap.

## 2. Targets

**A target is a SLURP scenario, and there are eighteen.** They are disjoint by construction: every
utterance has exactly one gold scenario, every intent belongs to exactly one scenario, and the
schema is keyed by intent, so no two targets can write into the same block. This is the structural
difference from EVO-A1, where a target is a hand-picked set of confusable tools and nine of
twenty-three tools could not supply reward rows at all.

`A_r` is a mapping from **intent** to that intent's block content. A scenario owns 1 to 9 intents
(`iot` 9, `play` 5, `qa` 5, `audio`/`email`/`music`/`transport` 4, five scenarios 3, four 2,
`news` and `weather` 1), and a target's candidate rewrites every block its scenario owns.

The census (`capacity.json`) puts no scenario near the loop's requirement of 84 utterances of which
24 carry entities: the thinnest are `cooking` (211 utterances) and `audio` (57 entity-bearing). It
also orders the scenarios by how much a schema can possibly say, and the order matches KC-S1b's own
per-stratum gains almost exactly:

| scenario | zero-entity share of TRAIN | KC-S1b gain (pp, pooled 1,000) |
|---|---:|---:|
| weather | 11.9 % | +16.7 |
| takeaway | 12.5 % | +1.7 |
| social | 16.6 % | +30.9 |
| transport | 17.0 % | +13.6 |
| … | | |
| music | 71.7 % | **0.0** |
| general | 70.9 % | +4.4 |
| audio | 80.3 % | +3.3 |

`music` and `audio` are the two scenarios where the loop has the least to work with, and they are
named here so a null on them is not read afterwards as a loop failure.

## 3. State, and `A_0`

| item | value |
|---|---|
| `A_0` | `docs/receipts/knowledge/slurp-intent-slot-schema-v1.json` |
| receipt file sha256 | `7e04da0ec29d0e9d6c473697d2b84bd1e0fc1d9ba28880ef2cf8b6f908bbe782` |
| schema content hash | `732e500af3870216c7b311369f6f190ffdb0365e497d84cf211f478036757dcc` |
| TRAIN source identity | `545847bb95a9423005c71bdcc3fa74af55a3a1b6ae91409ba4070fd35bf92fef` (11,514 utterances) |
| shape | 60 intents, 261 listed type rows over 52 distinct types, 1,008 example fillers |
| per-intent block | 494 to 1,224 characters |
| full rendering (the fallback) | 26,720 characters, 322 lines, sha256 `4e573a65e14c57598cc39ed1aa71cf0ac59018be162dbea3e0bfbf038203a5b9`, about 7,500 tokens |

**`A_0` is byte-identical to the artifact KC-S1b flew**, which is what makes round 0 of the curve the
admitted mechanism rather than a re-derivation of it. The capacity run re-mined it from TRAIN and
reproduced the content hash exactly before counting anything.

**The rendering rule is KC-S1b's, unchanged.** `data.slurp.render_slurp_intent_slot_schema` emits one
shared header sentence, then per intent

```
== {intent} == {n} TRAIN utterances, {m} slot mentions
- {entity_type} ({share*100:.1f} percent of slot mentions): {filler}; {filler}; ...
```

and `render_slurp_slot_schema_for_state_detail` selects the block by parsing the intent out of the
**sealed** closed-list prediction for that row, falling back to the full 60-intent schema when the
sealed response does not parse or names a (scenario, action) pair TRAIN never carries. **Both stay
exactly as they are.** On DEV-1000 the fallback fired on 42 of 1,000 rows (4.2 %); it will fire on
the folds too, and the count is reported per read.

**A candidate never writes a number.** The header line and the per-type share are re-rendered from
the unfloored TRAIN table (`load_slurp_intent_slot_schema(..., min_share=0.0)`) by the renderer, so a
candidate cannot misstate what TRAIN contains. A candidate chooses, per intent, only:

* **which entity types to list, and in what order** — each must have at least one TRAIN mention for
  that intent, or the candidate is refused;
* **up to five fillers per listed type** — free ASCII lower-case text, gated by section 8.

That is the whole state. It cannot change the block's grammar, its header, its selection rule, the
fallback, the system message, the contact count, or the roster.

## 4. The intent phase, and the reward

**The loop's slot contact conditions on a SEALED intent prediction, exactly as KC-S1b did.** The
schema block is chosen by the intent, so the intent must be fixed before the loop starts or every
round would be measuring two changes at once.

**One closed-list direct flight over fold A and fold B, flown once, before round 1.**
`configs/baseline/slurp-direct-closed-list.json` on the fold dataset fragments: 540 + 540 = **1,080
contacts**, one per row, `baseline-reproduction`. Its two run manifests become the `sealed-manifest`
`predecessor_source` of every slot cell on that fold, for every round and every candidate. It is
**incumbent-independent** — nothing the loop does can change it — which is why it is flown once and
not per round, and it doubles as each fold's own one-contact direct comparator.

**Which per-row metrics exist.** `core.scoring_batch` with `--include-per-sample` writes, per row,
from `reproduction.slurp_official_eval.score_slurp_outputs_official`:
`scenario_action_exact`, `slot_f1_exact_{tp,fp,fn,precision,recall,f1}`,
`slu_f1_word_{tp,fp,fn,f1}`, `slu_f1_char_{tp,fp,fn,f1}`, `slu_f1_{precision,recall,f1}`, and
`parsed`.

**The reward is per-row `slot_f1_exact_f1` — strict entity F1, exact `{type, filler}` match.** Four
reasons, in order:

1. **It is the metric KC-S1b was admitted on.** Its NEW500 admission (+10.11 pp, CI90 [+8.11,
   +12.19]) and its whole per-stratum table are stated in this metric, so round 0 of the curve has a
   measured comparator on the same scale rather than a re-derived one.
2. **It is the least gameable.** `slu_f1_word_f1` is distance-based and gives partial credit for a
   filler that is merely close, so a block that pushes the model toward longer, more coverable
   guesses can raise it without producing one correct slot. Under strict F1 a save is a slot that is
   exactly right.
3. **It is not a term in the read metric.** The official SLU-F1 is computed from the word- and
   char-distance TP/FP/FN alone; rewarding Word-F1 would optimize one of the two ingredients of the
   number the loop is then read on, so the selection rule and the claim would share arithmetic.
   Strict F1 moves with SLU-F1 (KC-S1b: +7.80 against +8.71 pooled) without being inside it.
4. **The density cost is measured and small.** On the largest slot effect this study has produced,
   pooled over 1,000 rows, strict F1 moved 104 rows (97 saves, 7 harms) and Word-F1 moved 131 (118
   saves, 13 harms) — a 21 % reduction in moving rows, not a difference of kind.

`slu_f1_word_f1` and `slu_f1_f1` are recorded beside the reward in every round receipt, so a reviewer
can see whether a count gate was starved by the metric. **The official corpus SLU-F1 is the READ
metric and is never the reward.**

## 5. Action space per scenario and round

`K` candidates per scenario, assembled across scenarios into one portfolio per slot `k`
(`rails.evolution.assemble_portfolio`), so a round flies the incumbent plus `K` portfolios rather
than `K x 18` arms.

| family | k | rounds | contacts | what it is |
|---|---:|---|---:|---|
| **F1 proposer** | 1, 2, 3 | every round | 1 text contact per scenario per k | the incumbent blocks of that scenario's intents, plus `M = 8` exemplar utterances of the scenario with their gold entities, rendered as English text. Returns the scenario's rewritten blocks |
| **F2 shares-only control** | 4 | every round | **none** | the incumbent blocks with every filler list deleted, types, order and shares untouched. Zero model contact |
| **F3 token-matched form twin** | 5 | **round 1 only** | **none** | the incumbent blocks with every filler replaced by a neutral placeholder at equal token count under the flight tokenizer. Zero model contact |

So `K_1 = 5` and `K_r = 4` for `r >= 2`; the program's `K = 4` is the steady state and the round-1
form twin is an extra slot, not a replaced proposer draw. **Both controls are deterministic**, which
is a real difference from EVO-A1, where the placebo costs a contact: 54 proposer contacts per round,
not 72, and neither control can be confounded by its own decoding.

**Why shares-only rather than "counts refreshed".** The program's F2 phrasing offers either. "Counts
refreshed" is a no-op here: `A_0`'s counts *are* the current TRAIN counts, so that control would be
byte-identical to the incumbent and worth nothing. Shares-only is the control the KC-S1b verdict
actually calls for.

**The exemplar draw.** `M = 8` utterances from that scenario's 24 in `SLURP-EVO-EXEMPLARS-V1`, drawn
and ORDERED by `random.Random(f"{round}:{scenario}:{k}")` over the id-sorted pool. Because the pool
is three times `M`, three draws differ in membership as well as order — unlike EVO-A1, where twelve
tools have a pool of exactly `M`. Where a scenario has more intents than `M` (only `iot`, with 9),
the draw covers intents in descending TRAIN mention mass and **any intent the draw did not cover
keeps its incumbent block unchanged**: a candidate never rewrites a block it saw no evidence for.
Exemplars never come from either fold.

**Candidate id** = `rails.proposer.candidate_id_for` — sha256 over the canonical JSON of the
candidate text, `proposer_prompt_sha256`, `exemplar_ids`, `round`, `target` (the scenario), `k` and
`family`. All seven fields are inside the hash, so a candidate cannot be relabelled into another slot
without changing its id.

### The proposer instruction, verbatim

Rendered offline; the exact bytes are reproducible from the committed schema receipt and the exemplar
ids, and `prompt_sha256` pins them. `{scenario}`, `{r}`, `{k}`, `{intent}`, `{n}`, `{m}`, `{L}` and
the two rendered blocks are the only substitutions.

```
# scenario {scenario} | round {r} | variant {k}

You are rewriting the slot-schema blocks a speech assistant is given before it extracts the
entities of a spoken command. The assistant hears the command; it does not see any text.

A block describes one intent: which entity types that intent draws its slots from, how much of
the intent's slot mentions each type carries, and fillers heard with that type.

## The blocks you are rewriting
{the incumbent block of every intent of this scenario, verbatim in the rendered grammar}

## Entity type names you may use
{the closed list of entity type names, comma separated}

## Example commands of this scenario, and the entities they carry
1. intent: {intent}
   said: {construction utterance text}
   entities: {entity type} = {filler}; {entity type} = {filler}
   (eight examples, grouped by intent, in the drawn order)

## Task
First decide what a reader who has only these blocks would still get wrong on the examples
above: a type the block never lists, a type it lists that this intent barely uses, or a filler
written in a form nobody would say out loud.
Then rewrite each block so that a reader who has only your block, and hears one of these
commands, writes the entities the examples show.

## Output
Reply with the rewritten blocks and nothing else -- no prose before or after them, no code
fence, no explanation. One block per intent, in the order the blocks were given, each in
exactly this grammar:
== {intent} == {n} TRAIN utterances, {m} slot mentions
- {entity type} ({p} percent of slot mentions): {filler}; {filler}; {filler}
Rules:
- reproduce each header line exactly as it was given to you
- every entity type name comes from the list above, and must be one this intent actually uses
- at most {L} type lines per block, the most used type first
- at most five fillers per type, lower case, written as they would be spoken
- ASCII only; one line per type; no blank lines; no numbering
- never write anything that is not an entity type name or a filler
- never write an identifier, a file name or a number that is not part of a filler
```

**No sample id ever reaches the rendered instruction** — exemplar ids are used only to group, to
order and to seed the candidate id. No devel row, no test row, no evaluation gold and no score enters
it. The construction utterance text and the construction gold entities that do appear are TRAIN, the
legality class the 2026-09-05 owner decision opened for this arm alone. The share value `{p}` in the
output grammar is **overwritten** by the renderer from the unfloored TRAIN table, so a hallucinated
percentage cannot reach a flight.

### Form: reported, bounded by a relative search budget, never a gate on the claim

Owner ruling of 2026-09-06: token caps are advisory and every content artifact carries a token-matched
form twin. Accordingly:

* the **token delta of each candidate block against the incumbent block** is measured on the flight
  tokenizer (the resident server's `/tokenize`) and REPORTED per candidate and per round;
* the **search budget** is `+20 %` tokens over the incumbent block, per intent, measured the same
  way. A candidate over budget is dropped and its slot flies the incumbent's block for that intent.
  This is a budget on the search, not a claim gate: it exists so a round cannot buy its gain with
  prompt volume alone;
* the **form twin** (F3) prices whatever volume does buy, at equal token count;
* `A_0`'s worst envelope is the 26,720-character full-schema fallback, about 7,500 tokens, which is
  what forced `-np 4` at `-c 65536` for KC-S1b. At +20 % it is about 9,000 tokens; the prompt fit
  re-derives the geometry and a candidate that only an estimator admits is refused. KC-A1 died four
  tokens over a forty-token cap because its builder injected a chars-per-token ratio as its counter;
  the tokenizer is the authority here.

Other form caps, all enforced before a candidate flies: ASCII only; at most five fillers per type;
at most `L` type lines per intent, where `L` is that intent's unfloored TRAIN type count; every
listed type has at least one TRAIN mention for that intent; the header line byte-identical to
`A_0`'s; the block parses under the renderer's own grammar.

## 6. The rounds

Per round `r`, in order:

1. **Propose.** One text contact per scenario per proposer slot on the `construction-proposer-text`
   arm, whose plan's split identity is `SLURP-EVO-EXEMPLARS-V1`. Build F2 (and, in round 1, F3) with
   no contact. Validate every candidate; a candidate that fails a form or decontamination gate is
   dropped and its slot flies the incumbent's blocks for that scenario.
2. **Assemble.** `assemble_portfolio` merges candidate `k` of every scenario into one schema state;
   the fragment writer emits the artifact and its baseline fragment.
3. **Fold A.** Fly the incumbent plus the `K_r` portfolios over all 540 rows of
   `SLURP-EVO-FOLD-A-V1`, one slot contact per row against that fold's sealed intent manifest,
   greedy, everything else KC-S1b's. Score once per complete manifest with `slurp-slu-official`
   through `core.scoring_batch`, never sharded.
4. **Stage one, per scenario** (`select_per_target`, gates `saves >= 4, harms <= 1, net >= 3` on
   per-row `slot_f1_exact_f1`): slice each arm to that scenario's own 30 rows and count against the
   incumbent. Winner = largest net, ties by fewer harms, then fewer artifact bytes, then lowest `k`.
   A count rule, not an interval: at 30 rows a bootstrap says nothing, and a reviewer can recount it
   by hand. **See section 16 open point 1: at 30 rows this gate is thin, and the arithmetic is
   stated there rather than discovered afterwards.**
5. **Assemble the winners** into one candidate state.
6. **Stage two, fold B.** Fly the incumbent and the assembly over all 540 rows of
   `SLURP-EVO-FOLD-B-V1`. Accept the assembly **whole** iff
   * the **pooled 540-row** paired CI90 lower bound on `slot_f1_exact_f1` is strictly above 0, and
   * **no scenario's own 30-row paired point estimate is below -1.0 pp.**

   The second condition is the program's -1.0 pp background tolerance transposed: on SLURP every
   scenario is a target, so there is no background population, and the tolerance becomes a
   per-scenario harm bound. It is stated on the **point estimate** rather than a CI90 lower bound
   because a CI90 over 30 rows of a sparse metric is uninformative and would accept everything; each
   scenario's CI90 is nevertheless recorded. 10,000 replicates, stratified by scenario, seed
   20260903, `analysis.paired.paired_contrast`. Never partially accepted.
7. **Curve.** Read the round's incumbent (post-decision) once on the curve population of section 7.
   Curve only: it decides nothing.
8. **Stop rule** (`should_stop`): `R_max = 4`; stop after two consecutive rejects, or after an
   accepted round whose gain is under 0.5 pp.
9. **Receipt.** `write_round_receipt` under
   `docs/checks/speech-aware-evidence-acquisition/2026-09-06-slurp-evo-s1/`, carrying the selection
   record, the confirmation record, the decontamination record and the per-candidate token deltas;
   `replay_selection` must reproduce every stage-one decision from the sealed per-sample score files
   alone.

## 7. The reads — an open decision, both options priced

Every read is a **one-slot-contact** arm over the read roster, conditioned on the already-sealed
closed-list intent manifest for that roster, and is paired **row for row against two sealed
manifests**:

* `SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1`, attempt `attempt-20260905T060424Z-2c5596`, manifest
  sha256 `f908ff4c7b0267322b34c7bf2ca9ad29d6db97ee8bb3cf18bf8824a057ebc94c` — the one-contact direct
  comparator, and the intent predecessor;
* `SAEA-SLURP-KC-S1B-SLOTS-SCHEMA-DEV1000-V1`, attempt `attempt-20260906T025102Z-af6b04`, manifest
  sha256 `088c9307a39f38db124a5204793806e9a8589d942259b15e7826ad2685fe8d08` — **the incumbent's own
  sealed rows**, i.e. `A_0` measured on DEV. This is the contrast that says whether the loop beat the
  hand-mined schema, and it is the headline.

`SAEA-SLURP-KC-S1A-SLOTS-DEV1000-V1` (the equal-contact control) is reported beside them. On the
FOLDS there are no sealed KC-S1b rows — the incumbent arm re-flown each round is `A_0` there — so the
two sealed comparators exist only on the DEV side; the folds carry their own one-time closed-list
direct arm instead.

| | **Option A** | **Option B** |
|---|---|---|
| curve, per round | OLD500 (`DEV-500`, the prior-exposed half of DEV-1000), 500 contacts, 1,422.0817 s | fold B only, **0 extra contacts** |
| final read, once | NEW500 (`DEV-1000-NEW500`), 500 contacts, 1,462.712 s | DEV-1000, 1,000 contacts, 2,884.7937 s |
| extra contacts over the loop | 2,000 curve + 500 final = **2,500** | **1,000** |
| extra GPU hours | about 0.52 | about 0.21 |
| virtue | the curve is **in distribution** with the final read: two disjoint halves of one roster, so a curve gain that does not transfer is visibly overfitting to OLD500 rather than a population change | the largest final `n`, both sealed comparators present on all 1,000 rows, and the curve costs nothing because fold B flies anyway |
| cost | 1,500 more contacts; OLD500 has already been read by the DEV ladder, the closed-list baseline, KC-S1a and KC-S1b, so its numbers are the most re-used in the study | curve and final read sit on different distributions, so the generalization gap conflates fold-to-DEV shift with overfitting — which is exactly what the transfer ratio is for |
| decision population | NEW500 (unexposed at the lock tier) | NEW500 within the pooled 1,000, DEV-500 reported beside it |

**Neither option opens a new identity**: every row of DEV-1000 has been contacted by the closed-list
baseline, KC-S1a and KC-S1b. **The coordinator chooses.** The budget table below is given for both.

**Headline evidence**, in this order: (1) the curve — round versus fold-A gain, fold-B gain and curve
gain; (2) the final paired delta against sealed KC-S1b and against the sealed closed-list direct, with
the per-scenario table and the published brackets beside it; (3) the generalization gap
`G = delta_foldB - delta_read`; (4) the transfer ratio `delta_read / delta_foldB`; (5) both weightings,
natural-mixture and equal-stratum; (6) the fallback-row count per read.

**Decision.** **ADMITTED** if the read's CI90 lower bound over sealed KC-S1b is above 0 on the
decision population, both weightings agree in sign, and `G <= 0.5 * delta_foldB`. **NULL** if the curve
rose but the read's CI includes 0 — reported as overfitting with the selection rule named — or if the
curve never rose. **HARMFUL** if the read's upper bound is below 0, and the schema branch ends with
its form/content attribution recorded.

## 8. Decontamination, per candidate, under its own model-free row

Register **`SAEA-SLURP-MF-EVO-DECONTAMINATION-V1`** (`model-free-check`, zero contacts) before the
first candidate is validated. Under it, each candidate is checked with:

* **`evaluation_sentence_texts`** = the `sentence` field of every DEV-1000 row (and of NEW500 alone,
  reported separately). **This is the only step in the whole study that opens SLURP devel sentence
  text** — `data.slurp.load_slurp_split` deliberately does not carry it — it opens it inside the gate
  alone, and it never renders, logs or echoes it. Refuse any candidate whose **fillers** share a word
  6-gram with a devel sentence, unless that 6-gram already occurs in `A_0`'s own 1,008 fillers. `A_0`'s
  fillers are exempt because they are TRAIN and were already sent by KC-S1b.
* **`exemplar_texts`** = the eight construction utterances the proposer was shown. Overlap here is
  **measured and reported, never gated**: construction rows are legally visible to the proposer, so
  the count is the memorization signal a reviewer reads beside the round's gain.
* the identifier refusals, always on: no `slurp:(train|devel|test):NNNNNN` string, no bare six-digit
  number, no media file name.
* the test split is never named, loaded or opened by this row or any other in the cell.

Per candidate the round receipt records: `candidate_id`, family, round, scenario, `k`, the exemplar
ids shown, the six-gram verdict, the exemplar overlap count, the per-intent token delta against the
incumbent, and the per-intent line and character counts.

## 9. Preregistered kill results (program section 5, transposed to scenarios)

The loop is declared to have failed, and is stopped and reported as such, if any of these holds:

1. **no scenario is admitted in rounds 1 and 2**;
2. a construction gain of at least 2 pp whose read CI90 includes 0, or a transfer ratio below 0.25;
3. the **shares-only control** lands within 0.5 pp of the proposer;
4. the **token-matched form twin** is indistinguishable from the proposer candidate;
5. **every candidate fails the per-scenario harm bound** of section 6.6.

## 10. Budget

`rails.evolution.ledger_budget` reproduces the speech arithmetic:
`calls = R * (K + 1) * rows + R * proposer_calls`, `speech = R * (K + 1) * seconds_per_pass`.
Fold A carries **1,542.8954 s** of audio per pass and fold B **1,608.2934 s**. Slot contacts are costed at
**0.75 s per call**, the rate KC-S1b measured at `-np 4` (1,000 contacts in 735.9 s); proposer text
contacts at **20 s** each (a scenario's blocks are up to about 1,100 tokens; `max_tokens` 1,536).

| round | fold A calls | fold B calls | proposer calls | curve calls (A) | fold speech s |
|---|---:|---:|---:|---:|---:|
| 1 (`K_1 = 5`, 6 arms) | 3,240 | 1,080 | 54 | 500 | 12,474.0 |
| 2–4 each (`K_r = 4`, 5 arms) | 2,700 | 1,080 | 54 | 500 | 10,931.1 |
| loop total (`R_max = 4`) | 11,340 | 4,320 | 216 | 2,000 | 45,267.2 |
| one-time intent flight | 540 | 540 | — | — | 3,151.2 |

| | contacts | speech s | GPU h |
|---|---:|---:|---:|
| loop (folds + proposer) | 15,876 | 45,267.2 | 4.46 |
| one-time intent flight | 1,080 | 3,151.2 | 0.23 |
| **Option A** curve 4 x 500 + final NEW500 | 2,500 | 7,151.0 | 0.52 |
| **Option B** curve 0 + final DEV-1000 | 1,000 | 2,884.8 | 0.21 |
| **whole cell, Option A** | **19,456** | 55,569.4 | **5.21** |
| **whole cell, Option B** | **17,956** | 51,303.1 | **4.90** |

**This is about twice the program's own estimate for EVO-S1** ("about 10,000, under 1.0" GPU-h,
section 4c), and the difference is not a surprise but an arithmetic consequence of fixing the folds at
540 rows each: the program's line was written before the fold size was chosen. The honest planned
figure is **4.90 GPU-h (Option B)** or **5.21 (Option A)**, and the coordinator should
either accept it or shrink the loop (section 16, open point 2). Paid API spend 0.

Registered ceilings are `R_max` times the largest per-round cost, per run id, because plan budgets are
cumulative across every attempt of a run id:

| run id | roster | attempts | calls ceiling | speech s ceiling | profile |
|---|---|---|---:|---:|---|
| `SAEA-SLURP-EVO-S1-INTENT-FOLDS-V1` | folds A and B | `attempt-intent-a`, `attempt-intent-b` | 1,200 | 3,200 | `baseline-reproduction` |
| `SAEA-SLURP-EVO-S1-FOLD-A-V1` | `SLURP-EVO-FOLD-A-V1` | `attempt-r{r}-i`, `attempt-r{r}-c{k}` | 12,960 | 37,100 | `baseline-reproduction` |
| `SAEA-SLURP-EVO-S1-FOLD-B-V1` | `SLURP-EVO-FOLD-B-V1` | `attempt-r{r}-i`, `attempt-r{r}-a` | 4,320 | 12,900 | `baseline-reproduction` |
| `SAEA-SLURP-EVO-S1-PROPOSER-V1` | `SLURP-EVO-EXEMPLARS-V1` | `attempt-r{r}-p-{scenario}-k{k}` | 288 | **0** | `bounded-discovery-probe` |
| `SAEA-SLURP-EVO-S1-CURVE-OLD500-V1` (Option A only) | `DEV-500` | `attempt-r{r}-curve` | 2,000 | 5,688.4 | `baseline-reproduction` |
| `SAEA-SLURP-EVO-S1-FINAL-V1` | NEW500 (A) or DEV-1000 (B) | `attempt-<stamp>-evofinal` | 500 / 1,050 | 1,462.8 / 2,884.8 | `baseline-reproduction` |
| `SAEA-SLURP-MF-EVO-DECONTAMINATION-V1` | — | — | 0 | 0 | `model-free-check` |

Every row is written `consumed = no` and stays so until the loop closes. Proposer contacts are counted
in `calls` and never in `speech_seconds`: the arm is text-only and sends no audio part at all.

## 11. Configuration

Two fragments, because a composed experiment fragment declares exactly one `execution_plan`
(`FlightRuntime._build_execution_plan` reads `values["execution_plan"]`) and therefore exactly one
`execution_profile` that `contracts.assert_execution_scope` validates:

* `configs/experiment/slurp-evo-s1-slot-schema-v1.json` — the reward flights, `baseline-reproduction`,
  round 1, modelled on `configs/experiment/slurp-slot-stage-kc-s1b-v1.json`. The loop re-emits it per
  round.
* `configs/experiment/slurp-evo-s1-proposer-v1.json` — the proposer contacts,
  `bounded-discovery-probe`. It configures a runner that does not exist (section 12).

Both compose `model + dataset + baseline + experiment` through the same `core.flight.FlightRuntime`
and the same OpenJiuwen executor every SLURP cell has flown. Model fragment
`q4km-mmproj-free-speech-native-np4-base-speech-query-prefix-max64` unless the prompt fit re-derives
the geometry. Policy `phase-slots-given-intent-v1`, one phase, `knowledge: "none"`, snapshot bound with
the `content` dimension excluded exactly as KC-S1b bound it (the SLURP leakage-rule blocker of the
KC-S1 verdict, deviation 1).

## 12. SPEC for the loop code — what `rails.proposer`, `rails.evolution` and the driver need

**Not implemented here.** `rails/evolution.py`, `rails/proposer.py` and `core/flight/runtime.py` are
owned by track `wt/e3c` this wave. This section is the specification that track needs; every item was
checked against the code as it stands at master `35193cb1`.

### 12.1 `rails.proposer` — a second artifact family

| # | what it assumes today | what SLURP needs |
|---|---|---|
| P1 | `CandidateArtifact.descriptions` is `{tool: description}` rendered by `data.audio2tool_tools.render_registry_compact_rows` | a family-parameterized artifact. SLURP's is `{intent: {"types": [{"entity_type": str, "fillers": [str, ...]}, ...]}}`, rendered through `data.slurp.render_slurp_intent_slot_schema` with shares re-derived from the unfloored TRAIN table. `candidate_text`, `candidate_id_for` and `CandidateArtifact.validate` must not assume a tool vocabulary |
| P2 | `_checked_descriptions` enforces `MAX_DESCRIPTION_CHARS = 200` and one line per description | SLURP blocks are 494 to 1,224 characters and multi-line by construction (one header line plus one line per listed type). The form validator must be per family: a per-intent LINE cap (`1 + L`, `L` = that intent's unfloored TRAIN type count), ASCII, a per-line grammar regex matching the two shapes `render_slurp_intent_slot_schema` emits, at most five fillers per type, and every listed type with at least one TRAIN mention for that intent |
| P3 | `validate_candidate_artifact` hardcodes `REGISTRY_LINE_COUNT = 152` and `TOKEN_HEADROOM = 40` against a compact-registry baseline | line count must be computed from the artifact, and the token budget must be RELATIVE: `+20 %` over the incumbent block per intent, measured through the injected `token_counter` (the serving geometry's own tokenizer, never an estimator) |
| P4 | `_SAMPLE_ID_RE = re.compile(r"tier\d_[a-z_]+:\d{6}")` | add `slurp:(train\|devel\|test):\d{6}(:[A-Za-z0-9-]+)?`; keep the bare-six-digit refusal |
| P5 | `_render_exemplar_block` / `_tool_of_gold_call` render gold CALL strings grouped by tool | SLURP exemplars are `(intent, utterance text, [(entity type, filler), ...])` triples grouped by intent. A family renderer, with the verbatim instruction of section 5 |
| P6 | `deterministic_candidate` appends the registry's `domain` and `category` | SLURP's F2 is **shares-only**: the incumbent blocks with every filler list deleted. Zero contacts |
| P7 | `placebo_candidate` / `render_placebo_instruction` spend one contact per target | SLURP's F3 is **deterministic**: every filler replaced by a neutral placeholder chosen so the block's token count matches the incumbent's under the injected counter. Zero contacts. Round 1 only |
| P8 | `parse_proposer_response` expects strict JSON `{"cue": ..., "descriptions": {...}}` | SLURP's output contract is the rendered block grammar itself, not JSON, because the block must be reproducible byte for byte by the renderer. The parser reads the blocks back into the artifact shape of P1 and refuses anything that does not parse |

### 12.2 `rails.evolution` — scenario targets and no background population

| # | what it assumes today | what SLURP needs |
|---|---|---|
| E1 | `Target.validate` refuses a target of fewer than two tools ("a target of one tool has nothing to separate it from") | a SLURP target is ONE scenario. Either relax the two-member rule per family, or give `Target` a `kind` (`"contrast"` vs `"stratum"`) whose stratum form admits a single member. `news` and `weather` own one intent each, so keying on intents does not rescue it |
| E2 | `select_per_target(rows_of_target=...)` takes `target_id -> row ids` | works unchanged: pass `scenario -> that scenario's 30 fold-A sample ids`. **No change** |
| E3 | `confirm_assembly` requires a NON-EMPTY `background_rows` and refuses any overlap with `targeted_rows` | with every scenario a target there is no background population. Allow `background_rows=()` and replace the background bound with the **per-scenario harm bound** of section 6.6: no scenario's own paired point estimate below `-1.0 pp`, every scenario's CI90 recorded |
| E4 | `write_candidate_fragments` emits a baseline fragment with `task_instruction_fill = evolved-artifact-v1` | SLURP consumes its artifact through `phase_material.slots.state_fill`, not `task_instruction_fill`. The writer must be family-aware: emit `configs/knowledge/slurp-evo-s1/evolved-schema-<sha16>.json` and a copy of `configs/baseline/slurp-phase-slots-given-intent-schema-v1.json` whose `phase_material.slots.state_fill` is `"slurp-evolved-slot-schema-for-state"` and which names the artifact relpath and its sha256 |
| E5 | `ledger_budget` | works unchanged. **No change** |
| E6 | `AdmissionGates(saves=4, harms=1, net=3)` | unchanged as a constant, but see section 16 open point 1: at 30 rows per scenario this gate is thin, and whether it stays is a coordinator decision, not a code one |

### 12.3 `rails.phase_material` — one new registered fill

**`PHASE_STATE_FILLS.register("slurp-evolved-slot-schema-for-state", ...)`**, a sibling of the
existing `slurp-intent-slot-schema-for-state`. Its factory loads the candidate artifact named by the
fragment (relpath plus sha256, refusing a mismatch), and its returned `(state_content) -> str` fill:

1. parses the intent out of the sealed closed-list response with
   `data.slurp.slurp_intent_from_state_content` — unchanged;
2. renders THAT intent's evolved block through `data.slurp.render_slurp_intent_slot_schema`'s
   grammar, with the header line and the shares re-derived from the unfloored TRAIN table;
3. falls back to the FULL evolved schema (all 60 blocks under the one shared header) when the sealed
   response does not parse or names a (scenario, action) pair TRAIN never carries — the same
   behaviour and the same reported count as `render_slurp_slot_schema_for_state_detail`.

Config alone; no `core/flight/runtime.py` change is needed, exactly as KC-S1b needed none.

### 12.4 The driver

| # | need |
|---|---|
| D1 | **The sealed-intent predecessor binding per fold.** Each fold's slot cells set `phase_material.slots.predecessor_binding = "sealed-manifest"` with `predecessor_source.manifest_relpath` = that fold's one-time closed-list intent manifest. Two folds, two manifests, two fragment variants; the binding never changes across rounds or candidates |
| D2 | **The proposer runner (track E3c), which does not exist.** `FlightRuntime.wire_check` issues one contact per roster sample through `_dispatch_fixed_policy`, which never supplies the `construction_targets` field, and the proposer makes at most three contacts per scenario per round rather than one per row. The bridge itself is already proven contact-free by `tests/unit/test_rails_core_client_construction_proposer.py`. This is the same blocker EVO-A1 records, and it blocks round 1 of both cells |
| D3 | **A per-round fragment emitter** that writes the round's fragments and hashes them before any contact, so a cell can never fly against an artifact edited afterwards |

## 13. What the flight agent must do before the first contact

1. **Ratify the reward metric** (section 4) and the read option (section 7).
2. **Make the folds hydratable** — three model-free artifacts per speech-bearing roster, none of which
   exists today, following the `TRAIN90` precedent exactly (it is the only TRAIN roster this study has
   ever flown): a speech-native runtime-view **dataset fragment**
   (`configs/dataset/slurp-speech-native-evo-fold-{a,b}-540.json`, schema
   `saea-speech-native-runtime-view-v1`, per item `audio_seconds`, `audio_sha256`, `media_relpath`,
   `packet_id`, `sample_rate_hz`); a **probe-sample view** under `docs/receipts/probe-samples/`; and a
   **D1 media supplement** `docs/receipts/artifacts/d1-speech-native-evo-fold-{a,b}.json`
   (`saea-d1-media-supplement-v1`). The D1 supplement is not optional: `d1-identity.json` closes over
   the SLURP **devel** split only (8,690 recordings) and explicitly does not close over `train`. **The
   exemplar roster needs none of them**: the proposer arm is text-only and its plan's split identity is
   that receipt.
3. **Preprocess the fold packets.** `~/feat-cache/slurp-q4km-packets-04ccc72a/` holds 1,000 devel
   packets and 451 train packet directories (TRAIN90 plus the knowledge-63 sets) with per-roster
   promotion receipts; **none of the 1,080 fold rows has a packet**, because every touched TRAIN
   utterance was excluded from the draw. Two preprocess sessions are needed, producing
   `EVO-FOLD-A-promotion.json` and `EVO-FOLD-B-promotion.json` on the same `04ccc72a` runtime receipt
   (`e80c635d…d808b`). CPU work, parallelizable, and it overlaps model load.
4. **Fly the one-time closed-list intent flight** on both folds and seal it (section 4).
5. **Register `SAEA-SLURP-MF-EVO-DECONTAMINATION-V1`** before validating any candidate (section 8).
6. **Prompt fit** under a `bounded-discovery-probe` row, zero generated tokens: `/apply-template` and
   `/tokenize` every round-1 portfolio's worst envelope (the full-schema fallback at +20 %) on the
   resident server, re-derive `-np`, and confirm the relative token budget against the measured
   incumbent. A candidate that only an estimator admits is refused.
7. **Wire check** the reward cells — they are ordinary one-phase `phase-slots-given-intent-v1` cells,
   so `FlightRuntime.wire_check` applies unchanged.
8. **MF-5 dry run**: four rows of fold A end to end through `run_program`, sealed and scored.
9. **Confirm the tree is clean** for the whole run: a COMPLETED manifest reads `study_commit` at
   finalize and refuses a dirty checkout.

## 14. Analysis

`rails.evolution.select_per_target` (stage one), `confirm_assembly` (stage two),
`analysis.paired.paired_contrast` (every interval; 10,000 replicates, scenario strata, seed 20260903,
CI90, exact sign test), `analysis.paired.per_sample_scores_from_score_file` (the per-sample reader),
`write_round_receipt` per round, `replay_selection` to recompute every stage-one decision from the
sealed per-sample score files, and `analysis.paired.render_markdown` for the tables. `ledger_budget`
reproduces section 10's arithmetic. Official scoring is `slurp-slu-official` — the unmodified official
`evaluate.py` at pinned commit `8eb1654…311f1` — run once per complete manifest through
`core.scoring_batch`, never sharded. No new analysis module is admitted for this cell.

## 15. Claim surface

Nothing here is a superiority, generality or Stage-3 claim. The folds are construction-role discovery
rows drawn from TRAIN and disjoint from every identity this study has ever contacted; the read rows are
DEV identities already contacted three times. Under the claim ladder an admitted EVO-S1 is **rung 1
only**. No test contact, no fresh roster, no `DEV-500-B` opening, no Q8_0, no second answering model,
no parameter update, no edit to an artifact after its fragment was emitted. At most one recovery
re-registration per run id.

## 16. Open points for the coordinator

1. **The per-scenario count gate is under-powered at 30 rows, and this is the cell's biggest design
   risk.** The gate is `saves >= 4, harms <= 1, net >= 3` on a scenario's own fold-A rows. Scale
   KC-S1b's measured per-stratum saves — the largest slot effect this study has produced — down to 30
   rows and only **three of eighteen** scenarios clear it: `social` 11.0 expected saves, `transport`
   6.0, `weather` 6.0; `calendar` and `iot` 3.4, `cooking` 3.2, `alarm` 2.1, `music` 0.0. A
   round-to-round refinement is far smaller than KC-S1b's step, so kill result 1 ("no scenario admitted
   in rounds 1 and 2") is likely to fire for a statistical reason rather than a mechanism reason. Four
   remedies, priced: **(a)** accept it and read kill result 1 as underpowered rather than negative;
   **(b)** draw the folds at **60 per scenario** (1,080 rows each) — the capacity is there (`cooking`
   still has 170 eligible utterances against a need of 144) and nine of eighteen scenarios then clear
   the gate, at exactly double the fold cost, about +3.7 GPU-h; **(c)** keep 30 and lower the gate to
   `saves >= 2, harms = 0, net >= 2`, which is a count rule close to noise; **(d)** demote the
   per-scenario count gate to a diagnostic and select portfolios on the pooled 540-row interval, which
   changes the program's selection rule. **(b) is the honest fix and it needs a fresh draw** — the
   generator takes `--fold-quota`, and a V2 roster id would be required because the receipts refuse to
   be overwritten.
2. **The budget is about twice the program's estimate for this cell** (section 10): 17,956 to 19,456
   contacts and 4.9 to 5.2 GPU-h against "about 10,000, under 1.0". Accept, or shrink `R_max`, or take
   Option B, or take remedy 1(a) rather than 1(b).
3. **The read option** (section 7): an in-distribution curve for 1,500 extra contacts, or the largest
   final `n` for nothing.
4. **`M = 8` versus `iot`'s nine intents.** Every other scenario has at most five. The stated rule is
   that uncovered intents keep their incumbent block; the alternative is `M = max(8, intents)` for that
   one scenario, which breaks the constant.
5. **The shares-only control as F2** rather than "counts refreshed" (section 5). "Counts refreshed" is
   byte-identical to the incumbent here and would be a wasted slot.
6. **Both controls are deterministic**, so `K_1 = 5` costs 54 proposer contacts, not 90. Confirm that
   reading rather than spending a contact on the form twin.
7. **The per-scenario harm bound on the point estimate** rather than a CI90 lower bound (section 6.6),
   because at 30 rows a CI90 accepts everything.
8. **Opening SLURP devel sentence text** for decontamination (section 8) is a first for this study.
   Confirm the row before it is written.
9. **Track E3c**, the proposer runner, is unwritten and blocks round 1 of both EVO cells (section
   12.4 D2).
