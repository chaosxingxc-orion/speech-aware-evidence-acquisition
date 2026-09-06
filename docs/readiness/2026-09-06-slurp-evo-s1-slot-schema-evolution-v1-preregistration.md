# EVO-S1: slot-schema evolution on SLURP — preregistration (DRAFT)

**Status: DRAFT.** This document is complete but unregistered. **The coordinator ruled on
2026-09-06** and those seven decisions are written into the sections below: the reward metric is
ratified (section 4), read Option B is taken (section 7), the folds are re-drawn at 60 utterances
per scenario (sections 2, 6, 10), the per-scenario harm bound replaces the background tolerance
(section 6), F2/F3/`K`/`M`/form are fixed (section 5), decontamination's DEV-1000 read is bounded
(section 8), and the budget is recomputed from the V2 sizes (section 10). What still closes the
document: **admitting the SLURP half of track E3c, which does not exist (section 12), and writing
the exposure rows.** One decision the ruling reopened and two engineering points remain open and
are named in section 16. Nothing here authorizes a contact.

Cell EVO-S1 of `docs/readiness/2026-09-05-three-dimension-experiment-program.md` (section 4c, loop
constants section 5), the **generality rung** of the system-evolution dimension: the same loop code
and the same selection rule as EVO-A1, hash-pinned, on a second carrier. Owner directive of
2026-09-06 makes EVO-S1 the PRIMARY demonstration of that dimension.

| prerequisite | receipt | state |
|---|---|---|
| MF-3, the per-intent TRAIN slot schema (`A_0`) | `docs/receipts/knowledge/slurp-intent-slot-schema-v1.json` | closed |
| KC-S1b, the mechanism this cell evolves | `docs/readiness/2026-09-05-slurp-slot-stage-kc-s1-v1-verdict.md` | **ADMITTED**, +8.55 SLU-F1 |
| construction capacity, `SAEA-SLURP-MF-EVO-CONSTRUCTION-CAPACITY-V1` | `docs/checks/speech-aware-evidence-acquisition/2026-09-06-slurp-evo-construction-capacity/` | closed, **no wall** |
| the three loop rosters, `SAEA-SN-MF-SLURP-EVO-FOLD-ROSTERS-V2` | `docs/receipts/rosters/slurp-evo-{fold-a,fold-b,exemplars}-v2.json` | frozen, **the V2 re-draw**; V1 kept as history, never contacted |
| the folds' flight products, `SAEA-SN-MF-SLURP-EVO-FOLD-SUPPLEMENTS-V2` | `docs/checks/speech-aware-evidence-acquisition/2026-09-06-slurp-evo-fold-supplements-v2/` | closed, **both folds hydratable** |
| the folds' featcache packets, `SAEA-SLURP-EVO-FOLD-PACKETS-V2` | — | **NOT DONE**, and the only prerequisite that needs a model contact (section 13.3) |
| stage-one power at the V2 fold size | `docs/checks/speech-aware-evidence-acquisition/2026-09-06-slurp-evo-stage-one-power/` | closed, **seven of eighteen** scenarios, not nine |
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

**The folds carry 60 utterances per scenario** (coordinator decision 1 of 2026-09-06, remedy (b)
of what was section 16 open point 1), so the loop's requirement per scenario is **144 utterances of
which 24 carry entities**, not the 84 the capacity census was computed against. The census
(`capacity.json`) still clears it everywhere: the thinnest scenario is `cooking` at 211 utterances
(+67 over the V2 need) and every one of the eighteen filled both folds at 60 without a single
shortfall.

One capacity edge appears at 60 and is recorded rather than absorbed. `audio` carries only 57
entity-bearing utterances in 290; after the two folds take 120 of its utterances, **22
entity-bearing utterances remain against an exemplar target of 24**. The folds keep their full
quota — they are the scientific population and have to carry their scenario's own entity density,
and reserving exemplars first would have stripped about a third of `audio`'s scorable fold rows —
so `audio`'s exemplar pool is 22. That is still 2.75 x `M` and above the floor of `2 * M = 16`, so
its three per-round draws still differ in membership as well as order. The cap is written into
`docs/receipts/rosters/slurp-evo-exemplars-v2.json` under `exemplar_quota_policy`.

The census also orders the scenarios by how much a schema can possibly say, and the order matches
KC-S1b's own per-stratum gains almost exactly:

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
`configs/baseline/slurp-direct-closed-list.json` on the fold dataset fragments: 1,080 + 1,080 =
**2,160 contacts**, one per row, `baseline-reproduction`. Its two run manifests become the `sealed-manifest`
`predecessor_source` of every slot cell on that fold, for every round and every candidate. It is
**incumbent-independent** — nothing the loop does can change it — which is why it is flown once and
not per round, and it doubles as each fold's own one-contact direct comparator.

**Which per-row metrics exist.** `core.scoring_batch` with `--include-per-sample` writes, per row,
from `reproduction.slurp_official_eval.score_slurp_outputs_official`:
`scenario_action_exact`, `slot_f1_exact_{tp,fp,fn,precision,recall,f1}`,
`slu_f1_word_{tp,fp,fn,f1}`, `slu_f1_char_{tp,fp,fn,f1}`, `slu_f1_{precision,recall,f1}`, and
`parsed`.

**The reward is per-row `slot_f1_exact_f1` — strict entity F1, exact `{type, filler}` match.**
**Ratified by the coordinator on 2026-09-06 (decision 6), with `slu_f1_word_f1` reported beside it
in every round receipt.** Four reasons, in order:

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

**Coordinator decision 4 of 2026-09-06 fixes this section:** F2 is shares-only, F3 is the
token-matched form twin, `K_1 = 5` and `K = 4` thereafter, `M = 8` with uncovered intents keeping
the incumbent block, and form is a `+20 %` relative token budget that is reported and is never a
gate on the claim.

**The exemplar draw.** `M = 8` utterances from that scenario's pool in `SLURP-EVO-EXEMPLARS-V2` — 24
utterances in seventeen scenarios and 22 in `audio` (section 2) — drawn
and ORDERED by `random.Random(f"{round}:{scenario}:{k}")` over the id-sorted pool. Because the pool
is about three times `M`, three draws differ in membership as well as order — unlike EVO-A1, where
twelve tools have a pool of exactly `M`. Where a scenario has more intents than `M` (only `iot`, with 9),
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
   arm, whose plan's split identity is `SLURP-EVO-EXEMPLARS-V2`. Build F2 (and, in round 1, F3) with
   no contact. Validate every candidate; a candidate that fails a form or decontamination gate is
   dropped and its slot flies the incumbent's blocks for that scenario.
2. **Assemble.** `assemble_portfolio` merges candidate `k` of every scenario into one schema state;
   the fragment writer emits the artifact and its baseline fragment.
3. **Fold A.** Fly the incumbent plus the `K_r` portfolios over all 1,080 rows of
   `SLURP-EVO-FOLD-A-V2`, one slot contact per row against that fold's sealed intent manifest,
   greedy, everything else KC-S1b's. Score once per complete manifest with `slurp-slu-official`
   through `core.scoring_batch`, never sharded.
4. **Stage one, per scenario** (`select_per_target`, gates `saves >= 4, harms <= 1, net >= 3` on
   per-row `slot_f1_exact_f1`): slice each arm to that scenario's own 60 rows and count against the
   incumbent. Winner = largest net, ties by fewer harms, then fewer artifact bytes, then lowest `k`.
   A count rule, not an interval: on a metric this sparse a bootstrap over one scenario still says
   little, and a reviewer can recount a count rule by hand. **The V2 draw is the answer to the
   power problem this gate had at 30 rows, and the size of that answer is now measured rather than
   asserted:** scaling KC-S1b's measured per-stratum saves to a 60-row fold clears the gate in
   **seven of eighteen** scenarios against three of eighteen at 30
   (`docs/checks/speech-aware-evidence-acquisition/2026-09-06-slurp-evo-stage-one-power/power.json`,
   model-free, from the committed KC-S1b read). Five scenarios join — `alarm`, `calendar`,
   `cooking`, `iot` and `qa`, beside the incumbent `social` and `weather` — and **one leaves**:
   `transport` clears at 30 rows (6.00 saves, 1.00 harms) and is refused at 60 (12.00, 2.00),
   because the harms bound is an absolute row count that does not scale with the fold. The
   admissible set still more than doubles, so a rounds-1-and-2 null is a statement about the
   mechanism rather than about the sample size; but it is seven, not the nine an earlier draft of
   this document asserted, and `transport` is a scenario the loop can no longer claim at this fold
   size. Whether the harms bound should scale is open (section 16).
5. **Assemble the winners** into one candidate state.
6. **Stage two, fold B.** Fly the incumbent and the assembly over all 1,080 rows of
   `SLURP-EVO-FOLD-B-V2`. **Coordinator decision 3 of 2026-09-06 replaces the background tolerance
   with a per-scenario harm bound**, because on SLURP every scenario is a target and there is no
   background population. Accept the assembly **whole** iff all three hold:
   * the **pooled TARGETED** paired CI90 lower bound on `slot_f1_exact_f1` — over the fold-B rows of
     the scenarios stage one admitted — is strictly above 0;
   * **every admitted scenario, on its own 60 fold-B rows, has `harms - saves <= 1` row**; and
   * the **non-admitted scenarios, pooled, are no worse than -1.0 pp.**

   The second condition is a row COUNT, not an interval, for the same reason stage one is: it says
   that a scenario the loop claims to have improved may not go backwards by more than a single row
   on the confirmation fold. The third keeps the tolerance the program wrote for a background
   population and applies it where a background population actually exists here — the scenarios the
   loop did NOT touch this round, whose blocks are the incumbent's and which should therefore move
   only by decoding noise. Each scenario's own CI90 is recorded regardless. 10,000 replicates,
   stratified by scenario, seed 20260903, `analysis.paired.paired_contrast`. Never partially
   accepted.
7. **Curve.** Under read Option B (section 7) the curve is **fold B**, already flown in step 6 at
   no extra contact: the round's accepted incumbent against `A_0` on the 1,080 confirmation rows.
   Curve only: it decides nothing.
8. **Stop rule** (`should_stop`): `R_max = 4`; stop after two consecutive rejects, or after an
   accepted round whose gain is under 0.5 pp.
9. **Receipt.** `write_round_receipt` under
   `docs/checks/speech-aware-evidence-acquisition/2026-09-06-slurp-evo-s1/`, carrying the selection
   record, the confirmation record, the decontamination record and the per-candidate token deltas;
   `replay_selection` must reproduce every stage-one decision from the sealed per-sample score files
   alone.

## 7. The reads — Option B, chosen by the coordinator on 2026-09-06

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

**Decision 2 of 2026-09-06: read Option B.**

| | **Option B — TAKEN** | Option A — not taken |
|---|---|---|
| curve, per round | **fold B, 0 extra contacts** — the round's accepted incumbent against `A_0` on the 1,080 rows already flown in step 6.6 | OLD500 (`DEV-500`), 500 contacts per round, 1,422.0817 s |
| final read, once | **DEV-1000, 1,000 contacts, 2,884.7937 s** | NEW500 (`DEV-1000-NEW500`), 500 contacts, 1,462.712 s |
| extra contacts over the loop | **1,000** | 2,000 curve + 500 final = 2,500 |
| extra GPU hours | **about 0.20** | about 0.51 |
| decision population | **NEW500 within the pooled 1,000, DEV-500 reported beside it** | NEW500 alone |

**Why B.** It buys the largest final `n` — both sealed comparators exist on all 1,000 DEV rows —
and the curve costs nothing, because fold B flies every round anyway. The V2 fold size makes that
curve worth more than it was at 540: a per-round read on 1,080 construction rows is a better
signal than a 500-row read on a population four other rows have already consumed. The cost B
accepts, stated plainly: curve and final read sit on different distributions, so the generalization
gap `G` conflates fold-to-DEV shift with overfitting — which is exactly what the transfer ratio
exists to separate, and both are reported.

**No new identity is opened either way**: every row of DEV-1000 has been contacted by the
closed-list baseline, KC-S1a and KC-S1b.

**The final read of `A*` is flown once, on DEV-1000**, paired row for row against the sealed
KC-S1b manifest (the headline) and the sealed closed-list direct manifest, with KC-S1a reported
beside them.

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
  reported separately). **Coordinator decision 5 of 2026-09-06 bounds this row exactly**: it may read
  the DEV-1000 sentence text — rows this study has already consumed — as 6-gram SETS and nothing
  else; `SLURP-DEV-500-B-V1` and the test split are never opened by it or by any other row of this
  cell. **This is the only step in the whole study that opens SLURP devel sentence text** — `data.slurp.load_slurp_split` deliberately does not carry it — it opens it inside the gate
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

**Recomputed from the V2 fold sizes (coordinator decision 7 of 2026-09-06). The program's own
line for this cell — "about 10,000 contacts, under 1.0 GPU-h" — is SUPERSEDED and must not be cited
again.**

`rails.evolution.ledger_budget` reproduces the speech arithmetic:
`calls = R * (K + 1) * rows + R * proposer_calls`, `speech = R * (K + 1) * seconds_per_pass`.
Fold A carries **3,084.528438 s** of audio per pass and fold B **3,154.797375 s**, both measured
from the V2 receipts. Proposer text contacts are costed at **20 s** each (a scenario's blocks are up
to about 1,100 tokens; `max_tokens` 1,536) and send no audio at all.

**The slot-contact rate, and a discrepancy the coordinator should settle.** The rate used here is
**0.7359 s per contact**, taken from the KC-S1b flight's own receipt: 1,000 contacts in 735.9065 s
of `run_phases` wall at `-np 4`, attempt `attempt-20260906T025102Z-af6b04`
(`docs/checks/speech-aware-evidence-acquisition/2026-09-05-slurp-slot-stage-kc-s1-v1/`
`flight-receipt-kc-s1b.json`, `stages.run_phases.wall_seconds`; the ledger row states the same
"1,000 contacts in 735.9 s"). The 2026-09-06 direction cites that flight's realized throughput as
**1,008 contacts in 0.08 GPU-h** — 0.2857 s per contact, 2.6x faster — and **that figure does not
reconcile with any committed receipt**: 1,008 is the run id's smoke plus flight call count, but no
receipt records 288 s of wall for it (KC-S1a, the cheaper arm, took 531.3 s for 1,000). The table
below is therefore computed at the receipt-backed rate, with the cited rate carried beside it so
the coordinator can see both. If the cited rate is right the cell is 3.94 GPU-h; if the receipt is
right it is 8.25.

| round | fold A calls | fold B calls | proposer calls | curve calls | fold speech s |
|---|---:|---:|---:|---:|---:|
| 1 (`K_1 = 5`, 6 arms) | 6,480 | 2,160 | 54 | 0 | 24,816.8 |
| 2–4 each (`K_r = 4`, 5 arms) | 5,400 | 2,160 | 54 | 0 | 21,732.2 |
| loop total (`R_max = 4`) | 22,680 | 8,640 | 216 | 0 | 90,013.5 |
| one-time intent flight | 1,080 | 1,080 | — | — | 6,239.3 |

Under Option B the curve column is zero by construction: the curve IS fold B, already flown.

| | contacts | speech s | GPU h (receipt rate) | GPU h (cited rate) |
|---|---:|---:|---:|---:|
| loop, folds | 31,320 | 90,013.5 | 6.40 | 2.49 |
| loop, proposer | 216 | 0 | 1.20 | 1.20 |
| one-time intent flight | 2,160 | 6,239.3 | 0.44 | 0.17 |
| final read, DEV-1000 (Option B) | 1,000 | 2,884.8 | 0.20 | 0.08 |
| **whole cell** | **34,696** | **99,137.6** | **8.25** | **3.94** |

The honest planned figure is **8.25 GPU-h**, about 1.7x the 4.90 the V1 draw would have cost and
about 8x the program's superseded estimate. What the re-draw bought is now measured: **seven of
eighteen** scenarios can clear the stage-one gate instead of three (section 6 step 4;
`2026-09-06-slurp-evo-stage-one-power/power.json`). That is still the difference between a testable
loop and a preregistered null, and it is smaller than the nine this document previously claimed.
Paid API spend 0.

Registered ceilings are `R_max` times the largest per-round cost, per run id, because plan budgets are
cumulative across every attempt of a run id — with margin where the fragment registers one, which
is why the proposer row reads 288 against an arithmetic 216:

| run id | roster | attempts | calls ceiling | speech s ceiling | profile |
|---|---|---|---:|---:|---|
| `SAEA-SLURP-EVO-S1-INTENT-FOLDS-V2` | folds A and B | `attempt-intent-a`, `attempt-intent-b` | 2,300 | 6,500 | `baseline-reproduction` |
| `SAEA-SLURP-EVO-S1-FOLD-A-V2` | `SLURP-EVO-FOLD-A-V2` | `attempt-r{r}-i`, `attempt-r{r}-c{k}` | 25,920 | 74,100 | `baseline-reproduction` |
| `SAEA-SLURP-EVO-S1-FOLD-B-V2` | `SLURP-EVO-FOLD-B-V2` | `attempt-r{r}-i`, `attempt-r{r}-a` | 8,640 | 25,300 | `baseline-reproduction` |
| `SAEA-SLURP-EVO-S1-PROPOSER-V2` | `SLURP-EVO-EXEMPLARS-V2` | `attempt-r{r}-p-{scenario}-k{k}` | 288 | **0** | `bounded-discovery-probe` |
| `SAEA-SLURP-EVO-S1-FINAL-V2` | DEV-1000 | `attempt-<stamp>-evofinal` | 1,050 | 2,884.8 | `baseline-reproduction` |
| `SAEA-SLURP-MF-EVO-DECONTAMINATION-V1` | — | — | 0 | 0 | `model-free-check` |

There is no `CURVE-OLD500` run id: Option B spends nothing on the curve.

Every row is written `consumed = no` and stays so until the loop closes. Proposer contacts are counted
in `calls` and never in `speech_seconds`: the arm is text-only and sends no audio part at all.

## 11. Configuration

Two fragments, because a composed experiment fragment declares exactly one `execution_plan`
(`FlightRuntime._build_execution_plan` reads `values["execution_plan"]`) and therefore exactly one
`execution_profile` that `contracts.assert_execution_scope` validates:

* `configs/experiment/slurp-evo-s1-slot-schema-v1.json` — the reward flights, `baseline-reproduction`,
  round 1, modelled on `configs/experiment/slurp-slot-stage-kc-s1b-v1.json`. The loop re-emits it per
  round. It names the V2 rosters, the V2 sizes and the decision-3 stage-two bound, and declares
  6,480 planned calls / 18,508 speech seconds / 1.4 GPU-h for round 1 on fold A.
* `configs/experiment/slurp-evo-s1-proposer-v1.json` — the proposer contacts,
  `bounded-discovery-probe`, bound to `SLURP-EVO-EXEMPLARS-V2`. It configures a runner that does not
  exist (section 12).

**The two fold dataset fragments now exist** and are named by every reward cell:

| fold | dataset fragment | rows | speech s | probe-sample view | D1 media supplement |
|---|---|---:|---:|---|---|
| A | `configs/dataset/slurp-speech-native-evo-fold-a-1080.json` | 1,080 | 3,084.528438 | `docs/receipts/probe-samples/SLURP-EVO-FOLD-A-V2.json` | `docs/receipts/artifacts/d1-slurp-evo-fold-a-v2.json` |
| B | `configs/dataset/slurp-speech-native-evo-fold-b-1080.json` | 1,080 | 3,154.797375 | `docs/receipts/probe-samples/SLURP-EVO-FOLD-B-V2.json` | `docs/receipts/artifacts/d1-slurp-evo-fold-b-v2.json` |

Each fragment carries the D1 supplement's relpath and artifact SHA-256 in the pair
`core.config.d1_media_supplement_relpath` / `d1_media_supplement_sha256` reads, so the composed run
config pins the supplement the gate then re-verifies. The exemplar roster needs none of these: the
proposer arm is text-only and its plan's split identity is that receipt.

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

1. ~~**Ratify the reward metric** (section 4) and the read option (section 7).~~ **DONE**,
   coordinator decisions 6 and 2 of 2026-09-06: the reward is per-row `slot_f1_exact_f1` with
   Word-F1 beside it, and the read is Option B.
2. ~~**Make the folds hydratable.**~~ **DONE**, `SAEA-SN-MF-SLURP-EVO-FOLD-SUPPLEMENTS-V2`, receipts
   under `docs/checks/speech-aware-evidence-acquisition/2026-09-06-slurp-evo-fold-supplements-v2/`.
   Three artifacts per fold, all from one measurement pass, following the `TRAIN90` precedent (the
   only TRAIN roster this study has ever flown): the speech-native runtime-view **dataset fragment**
   (`saea-speech-native-runtime-view-v1`, per item `audio_seconds`, `audio_sha256`, `media_relpath`,
   `packet_id`, `sample_rate_hz`), the **probe-sample view** the driver enumerates through, and the
   **D1 media supplement** — not optional, because `d1-identity.json` closes over the SLURP **devel**
   split only (8,690 recordings, zero `slurp:train:` ids).

   | | fold A | fold B |
   |---|---|---|
   | dataset fragment | `configs/dataset/slurp-speech-native-evo-fold-a-1080.json` | `configs/dataset/slurp-speech-native-evo-fold-b-1080.json` |
   | `runtime_view_sha256` | `f423fd59…7918` | `fdb6ccdc…e469d` |
   | probe-sample view | `docs/receipts/probe-samples/SLURP-EVO-FOLD-A-V2.json` | `docs/receipts/probe-samples/SLURP-EVO-FOLD-B-V2.json` |
   | D1 supplement | `docs/receipts/artifacts/d1-slurp-evo-fold-a-v2.json` | `docs/receipts/artifacts/d1-slurp-evo-fold-b-v2.json` |
   | supplement sha256 | `2b3d2299…8397` | `c543067e…bd32` |
   | media bytes | 58,339,950 | 59,382,544 |

   Verified offline through the production checks, not a re-implementation of them:
   `contracts.gate.FrozenCoreGate.verify_media_identity` re-hashed all 2,160 flac files against the
   supplements with D1 resolved through the E0 closure receipt exactly as a model touch resolves it,
   `reproduction.probe_split.load_verified_probe_split` derived the same run identity the fragments
   publish, and `core.roster.read_roster` recomputed both roster identities — PASS on both folds
   (`verify.json`). **The exemplar roster needs none of them**: the proposer arm is text-only and its
   plan's split identity is that receipt.
3. **Preprocess the fold packets — the only prerequisite that needs a model contact, and it is not
   yet done.** Promotion starts a llama.cpp sidecar with the decoder AND the mmproj encoder loaded
   and issues one contact per row at `max_tokens: 1`; that is a `bounded-discovery-probe` model
   contact (`SAEA-SN-DEV1000-PREPROCESS`, 2026-08-24, is the precedent to copy), so the model-free
   supplements row stopped before it. The scope is **measured, not assumed**
   (`products.json`, `packet_coverage`): **0 of 2,160 fold rows has a packet** — 0/1,080 per fold in
   `slurp-q4km-packets`, in the resident `slurp-q4km-packets-04ccc72a` and in
   `slurp-q4km-packets-x108-04ccc72a` — because every already-touched TRAIN utterance was excluded
   before the draw, and a touched utterance is exactly the kind that would already carry a packet.
   The whole of both fragments is therefore the scope: no set difference, and no derived "NEW"
   receipt to cut, unlike DEV-1000 where 500 of 1,000 packets already existed. Two preprocess
   sessions under `SAEA-SLURP-EVO-FOLD-PACKETS-V2`, composing
   `q4km-preprocess-featcache-cpu-sidecar` + `slurp-speech-native-evo-fold-{a,b}-1080` +
   `speech-native-preprocess` + a new `slurp-evo-fold-{a,b}-preprocess` experiment fragment on the
   `04ccc72a` preprocess runtime receipt, producing `EVO-FOLD-A-V2-promotion.json` and
   `EVO-FOLD-B-V2-promotion.json`. Budget 2,160 calls and 6,239.33 speech seconds; own GPU offload
   zero (`-ngl 0`), CPU-parallel, and it overlaps model load.
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

## 16. Decisions taken, and what is still open

**The coordinator ruled on 2026-09-06.** All seven decisions are written into the sections they
govern; this table is the index, not a second copy of the rule.

| # | decision | now lives in |
|---|---|---|
| 1 | Folds at **60 utterances per scenario** — 1,080 rows each — exemplars 24, V2 draw, seed 20260906, same exclusions, same proofs. The V1 receipts stay committed as history and were never contacted. | sections 2, 6, 10; `SAEA-SN-MF-SLURP-EVO-FOLD-ROSTERS-V2` |
| 2 | **Read Option B.** The curve is fold B per round, at no extra contact; the final read of `A*` is DEV-1000, once, paired against sealed KC-S1b (the headline) and the sealed closed-list direct, with KC-S1a beside. | section 7 |
| 3 | **A per-scenario harm bound replaces the background tolerance**, because every scenario is a target: each admitted scenario at `harms - saves <= 1` row on fold B, the non-admitted scenarios pooled at `>= -1.0 pp`, and the pooled targeted CI90 lower bound `> 0`. | section 6.6 |
| 4 | F2 = shares-only; F3 = token-matched form twin; `K_1 = 5`, `K = 4` thereafter; `M = 8` with uncovered intents keeping the incumbent block; form = `+20 %` relative token budget, reported, never a claim gate. | section 5 |
| 5 | Decontamination may read **DEV-1000 sentence text — rows already consumed — as 6-gram sets**, under its own model-free row. `SLURP-DEV-500-B-V1` and the test split never. | section 8 |
| 6 | Reward = per-row `slot_f1_exact_f1`, with Word-F1 reported beside it. | section 4 |
| 7 | **Budget recomputed from the V2 sizes.** The program's "about 10,000 contacts, under 1.0 GPU-h" for this cell is superseded, and this document says so. | section 10 |

Four consequences the ruling produced that the coordinator did not have in front of them. Three
change no decision; the fourth reopens one, and is carried into the still-open list below rather
than absorbed:

* **`audio`'s exemplar pool is 22, not 24.** At 60 per scenario the two folds take 120 of `audio`'s
  utterances and only 22 entity-bearing ones survive. The folds kept their full quota, because they
  are the scientific population and must carry their scenario's own entity density — reserving
  exemplars first would have stripped about a third of `audio`'s scorable fold rows. 22 is 2.75 x
  `M` and above the floor of `2 * M = 16`, so the three per-round draws still differ in membership.
  Recorded in the exemplar receipt's `exemplar_quota_policy` block (section 2).
* **The cell now plans at 8.25 GPU-h**, against 4.90 for the V1 draw under the same read option.
  That is the price of the re-draw and it is what decision 7 accepted; the measured return is
  **seven** of eighteen scenarios able to clear the stage-one gate instead of three, not the nine
  this document asserted when the decision was written up
  (`docs/checks/speech-aware-evidence-acquisition/2026-09-06-slurp-evo-stage-one-power/`,
  model-free, zero contacts, from the committed KC-S1b per-stratum table). Rounding the expected
  counts admits `datetime` and scaling the harms bound admits `transport`; taking both at once is
  how nine was reached, and neither is the gate this document preregisters.
* **`transport` leaves the admissible set on the way up.** The stage-one gate is not scale-free:
  doubling the fold doubles a scenario's expected harms while the harms bound stays at one absolute
  row. `transport` — 12 saves and 2 harms in 60 measured DEV rows, the second-largest measured
  effect in the corpus after `social` — prices at 6.00 / 1.00 on a 30-row fold and clears, and at
  12.00 / 2.00 on a 60-row fold and is refused on the harms bound alone. Recorded, not repaired:
  changing a preregistered gate is a coordinator decision (section 16, still open).
* **The slot-contact rate the direction cited does not reconcile with the receipts.** The figure
  given was "1,008 contacts in 0.08 GPU-h" (0.2857 s per contact); the KC-S1b flight receipt records
  1,000 contacts in 735.9065 s (0.7359 s per contact), and KC-S1a, the cheaper arm, took 531.3 s for
  1,000. Section 10 is computed at the receipt-backed rate and carries both columns. **The
  coordinator should settle which rate the registered ceilings are written against** — it is the
  difference between 8.25 and 3.94 planned GPU-h, not between two ways of describing the same run.

### Still open

One decision and two engineering points:

0. **Should the stage-one harms bound scale with the fold?** This is the one thing the V2 re-draw
   reopened. The gate is `saves >= 4, harms <= 1, net >= 3` in ABSOLUTE rows, so it is not
   scale-free: at 60 rows `transport` prices at 12.00 saves and 2.00 harms and is refused, while at
   30 it prices at 6.00 / 1.00 and clears. Two readings, and the coordinator picks one before
   round 1 because it changes which scenarios the loop may claim:
   * **keep the absolute bound** — the gate stays recountable by hand, seven scenarios are
     admissible, and the loop simply cannot claim `transport` at this fold size; or
   * **make the harms bound relative** (`harms <= 1 per 30 fold rows`, i.e. `<= 2` at 60) — eight
     scenarios become admissible, `transport` returns, and the gate stops being a plain count.
   Either way the choice is preregistered before takeoff, never after a round is read. The
   per-scenario arithmetic for both is in
   `docs/checks/speech-aware-evidence-acquisition/2026-09-06-slurp-evo-stage-one-power/power.json`.
1. **`A_0`'s hash re-verification at takeoff.** The loop's round 0 must start from the exact bytes
   KC-S1b flew. Before round 1 the flight agent re-mines the per-intent schema from TRAIN and
   reproduces the content hash `732e500a…7dcc` against the committed receipt
   (`docs/receipts/knowledge/slurp-intent-slot-schema-v1.json`, receipt sha256 `7e04da0e…e782`),
   exactly as the capacity run did before counting anything; a mismatch stops the cell. This is an
   engineering step that has not been performed against the current tree, not an open question.
2. **The token counter binding at prompt fit.** The `+20 %` relative budget is measured through the
   flight tokenizer and never an estimator (KC-A1 died four tokens over a forty-token cap because
   its builder injected a chars-per-token ratio as its counter). WHICH endpoint the validator's
   `token_counter` is injected with, and at which serving geometry, is fixed at the section-13
   prompt fit and is not yet written down anywhere.

**What blocks round 1 is none of those: it is track E3c**, the proposer runner, which does not
exist (section 12.4 D2) and which blocks round 1 of both EVO cells. Admitting the SLURP half of
that track, and writing the exposure rows, are what close this document.

**One routing note for whoever owns section 12.** That section is the SPEC handed to track E3c and
is not edited here; it was written against the V1 draw and three of its statements are now stale.
E2 says "pass `scenario -> that scenario's 30 fold-A sample ids`" — it is 60. E3 restates the
stage-two bound as "no scenario's own paired point estimate below `-1.0 pp`", which is not what
decision 3 says: the bound is `harms - saves <= 1` row per ADMITTED scenario on fold B, with the
`-1.0 pp` tolerance applying to the NON-admitted scenarios pooled (section 6.6 is authoritative).
E6 still calls the stage-one gate "thin at 30 rows" and defers it to the coordinator; the
coordinator has ruled, and the live question is the harms-bound scaling of open point 0 above. None
of these changes what the code must do except E3, which the code must implement as section 6.6
states it.
