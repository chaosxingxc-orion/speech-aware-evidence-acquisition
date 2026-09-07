# EVO-S1: slot-schema evolution on SLURP — preregistration (REGISTERED)

**Status: REGISTERED, 2026-09-06.** The coordinator's seven decisions of 2026-09-06 are written
into the sections below — reward metric (section 4), read Option B (section 7), folds at 60
utterances per scenario (sections 2, 6, 10), the per-scenario harm bound (section 6), F2/F3/`K`/`M`/
form (section 5), the bounded decontamination read (section 8), and the recomputed budget
(section 10) — and the three things that stood between them and a registered document are now done:

* **the SLURP half of track E3c landed** on `wt/e3d` (section 12.5), so the loop code, the second
  artifact family, the scenario target kind, the per-scenario harm bound and the driver all exist;
* **the model-free pre-flight closed** (2026-09-06): the decontamination gate is BUILT as a
  committed 6-gram digest artifact and `A_0` passes it (section 8); `A_0` and, for the first time,
  the unfloored TRAIN table are pinned and re-derived, executably (section 3); and the projection
  the re-locked comparator introduced is decided, implemented and bounded (section 4);
* **the exposure rows exist** — seven of them, every one `consumed = no`, and
  `check_ledger_budget` accepts every one against the loop's own run-cumulative worst case, offline
  (section 10).

**What remains is GPU work, and only GPU work**, listed in order in section 16: the prompt fit
(which is also where the round-1 form twin's token counter is bound), the fold packet promotion, the
one-time intent flight whose two sealed manifests the loop config still carries as `PENDING`, then
the wire check and the four-row dry run.

**Registering this document authorizes nothing on its own.** Every contact still needs its own
registered row, a structured `contracts.ExecutionPlan`, and the gates the sections below describe.

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
| the folds' featcache packets, `SAEA-SLURP-EVO-FOLD-PACKETS-V2` | exposure row registered 2026-09-06, `consumed = no` | **NOT DONE**, 0 of 2,160 present, and one of the four prerequisites that need the GPU (sections 13.3, 16) |
| the decontamination gate, `SAEA-SLURP-MF-EVO-DECONTAMINATION-V1` | `docs/receipts/knowledge/slurp-evo-decontamination-v1.json`; `docs/checks/speech-aware-evidence-acquisition/2026-09-06-slurp-evo-decontamination/` | closed, **built**, `A_0` PASSES |
| `A_0`'s closure and the unfloored pin | `docs/checks/speech-aware-evidence-acquisition/2026-09-06-slurp-evo-a0-closure/` | closed, all eleven quantities re-derived |
| the exposure rows and their budget proof | `docs/exposure-ledger.md`; `docs/checks/speech-aware-evidence-acquisition/2026-09-06-slurp-evo-ledger-budget/` | closed, seven rows, `check_ledger_budget` accepts every one |
| stage-one power at the V2 fold size | `docs/checks/speech-aware-evidence-acquisition/2026-09-06-slurp-evo-stage-one-power/` | closed, **eight of eighteen** scenarios under the owner's harm rate |
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
| **unfloored table** (`min_share = 0.0`) | content hash `72fa23f70bfbe640d2ff84bb0035e1216dfc4f67bf1a31f7f8b8f64ebdc2e575`, same TRAIN source identity, 60 intents, **432** listed type rows over **55** distinct types, 1,281 fillers |

**`A_0` is byte-identical to the artifact KC-S1b flew**, which is what makes round 0 of the curve the
admitted mechanism rather than a re-derivation of it. The capacity run re-mined it from TRAIN and
reproduced the content hash exactly before counting anything.

**CLOSED, 2026-09-06 — and the closure is executed, not transcribed.** What was section 16 open
point 1 has been performed against the current tree: `scripts/verify_slurp_evo_a0.py` re-mines the
schema from `train.jsonl`, re-hashes the committed receipt file, and raises rather than reports if
any of the eleven published quantities above fails to reproduce. All eleven reproduced
(`docs/checks/speech-aware-evidence-acquisition/2026-09-06-slurp-evo-a0-closure/a0-closure.json`).
The **unfloored table is now pinned too, and it was pinned nowhere before**: it is the sole
authority for every type's TRAIN count, every share and every intent's `1 + L` line cap — that is,
for everything a candidate *cannot* write — so a loop that validated candidates against an
unpinned table would be enforcing an unstated contract. Both hashes live in
`configs/knowledge/slurp-evo-s1/loop-v1.json` under `a_0`, and `LoopConfig.assert_a_0` checks them
against the freshly mined tables **every time `rails.evolution_carrier` loads carrier material**;
a mismatch stops the cell before a candidate is built.

The same closure proves the third thing round 1 needs and which no other receipt stated: all **430**
rows of `SLURP-EVO-EXEMPLARS-V2` resolve through the construction-role gate — the roster receipt
verified fail-closed by `core.roster.verify_roster`, then
`data.slurp.load_slurp_train_construction_rows`, the TRAIN-locked reader that is the one caller
licensed to carry sentence text beside gold — and **all 430 carry at least one gold entity**, in the
eighteen scenario strata at 24 each and 22 in `audio`, every one at or above the `2 * M = 16` floor.

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
not per round, and it doubles as each fold's own one-contact direct comparator. Registered as
`SAEA-SLURP-EVO-S1-INTENT-FOLDS-V2`, attempts `attempt-intent-a` and `attempt-intent-b`.

### How the projection enters the predecessor binding — decided 2026-09-06

The re-lock of 2026-09-06 (`docs/readiness/2026-09-06-slurp-legal-label-projection-v2-verdict.md`)
made `slurp-slu-official-projected-v2` the scorer every pending SLURP cell reads through: the
comparator is intent **73.10** / SLU-F1 **35.80**, not 71.40. That rule has a second application in
this cell, one step earlier than scoring, and it is stated here because it is not free.

**What it does.** The block a row is shown is chosen by parsing the intent out of that row's SEALED
closed-list response. On DEV-1000 that response names a `(scenario, action)` pair TRAIN never
carries on **39 of 1,000** rows and fails to parse on 3, so 42 rows (4.2 %) are served the
26,720-character full-schema fallback instead of a per-intent block. Under
`slurp-legal-label-projection-v2`, 39 of those 42 become legal and **17 land on the gold intent**
(v2 verdict section 6). Projecting the sealed label *before* the block is selected therefore hands
about 1.7 % of rows a materially better instruction — an effect the same size as the one the loop is
trying to demonstrate.

**Where it is on, and where it is off.**

| population | projects? | why |
|---|---|---|
| **fold A and fold B**, every round, every arm | **yes**, `slurp-legal-label-projection-v2` | the fold intent manifests are this cell's OWN (`SAEA-SLURP-EVO-S1-INTENT-FOLDS-V2`), the incumbent arm and every candidate arm read them through the same projection, and the projection is declared ONCE — on the fold base fragment — so a round stays a single-factor contrast and the loop selects on the best labels available to it |
| **DEV-1000 final read** of `A*` | **no** | the headline comparator is KC-S1b's SEALED rows, which chose their blocks from UNPROJECTED bytes and cannot be re-flown. An `A*` arm that projected would beat them partly by better block selection rather than by the evolved schema, and the claim would no longer be about the artifact |

**The seam.** `data.slurp.render_slurp_slot_schema_for_state_detail` (and
`slurp_intent_from_state_content` beneath it) take an optional `projection=`, a rule already bound to
its TRAIN-mined legal inventory. Both SLURP state fills —
`slurp-intent-slot-schema-for-state` and EVO-S1's `slurp-evolved-slot-schema-for-state` — accept a
`projection` **`fill_params` key**, resolved through
`rails.phase_material.SLURP_STATE_INTENT_PROJECTIONS` against the same two ids `core.scorers`
registers the scoring side under; an unregistered id is refused. **Absent by default**, so every
already-flown cell keeps its own block selection byte for byte, KC-S1b's fragment included.

The declaration lives on the fold base fragment
`configs/baseline/slurp-phase-slots-given-intent-schema-projected-v2.json` — KC-S1b's arm plus that
one key — and `rails.evolution.write_candidate_fragments` now MERGES a base's own `fill_params` under
the artifact keys it owns (refusing a collision) instead of refusing any, so the incumbent arm and
every candidate copy of it carry the identical projection. The final read flies
`configs/baseline/slurp-phase-slots-given-intent-schema-v1.json`, unchanged.

**The cost, stated before takeoff.** Fold and read now differ in one path detail as well as in
population, so the generalization gap `G` carries a block-selection term. Its direction is
**conservative for the claim**: the loop optimizes in a world where ~1.7 % of rows get a better
block and is read in a world where they do not, which can only shrink the measured read gain
relative to the fold gain. The fallback-row count is reported per read either way (section 7,
headline evidence item 6), so a reviewer can price the term rather than infer it.

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
- leave no blank line between one block and the next: the next block's == header line comes immediately after the previous block's last type line
- never write anything that is not an entity type name or a filler
- never write an identifier, a file name or a number that is not part of a filler
```

**`proposer-instruction-v2`, from round 2 onward — dated 2026-09-07 (track E3e).** The rule line
"leave no blank line between one block and the next…" above is NEW, and it is the whole of the
change. Round 1 lost **22 of its 54 draws** to one formatting habit: the model separated its blocks
with a blank line, which v1 covered only as the general "no blank lines" in a rule whose other two
clauses are about type lines. `takeaway` lost all three of its draws that way, so its 4-saves,
0-harms stage-one count stood against no artifact at all. The parser is deliberately unchanged and
stays fail-closed — repairing a proposer answer here would be a second, unlogged policy deciding what
the frozen core meant — so the repair belongs in the instruction, where it costs nothing and is
visible. Because the instruction bytes are inside every candidate id (through
`proposer_prompt_sha256`) and are the preregistered prompt, the revision is versioned rather than
edited quietly: `rails.proposer.PROPOSER_INSTRUCTION_VERSIONS` names
`slurp-slot-schema -> proposer-instruction-v2`, and every PROPOSE receipt from round 2 on records
`proposer_instruction_version`. **Round 1's sealed prompts are untouched**: they were flown under v1,
their digests stand, and round 1 remains replayable exactly as it landed. The `a2t-descriptions`
instruction stays `proposer-instruction-v1` — its output contract is strict JSON, whose parser treats
a blank line as the insignificant whitespace it is, so the same habit cannot cost EVO-A1 a draw.

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

**Null rewrites, added 2026-09-07 (track E3e), after round 1.** A candidate whose RENDERED artifact
is byte-identical to the incumbent's rendering over exactly the intents it rewrote is refused at the
candidates step with the reason `null-rewrite`: it is never admitted, never flown, and its slot flies
the incumbent's blocks like any other refusal. Round 1 needed this. `social` was admitted on a block
set that renders to `A_0`'s own `social_post` block — the old guard checked that a candidate EXISTED,
not that it DIFFERED — which spent one of two admissions and put 60 rows of pure decoder noise into
the confirmation. Replaying round 1's `candidates.json` through the gate refuses five of its 29
candidates: `social` k = 2 (the admitted winner `bb02b5f3`), `calendar` k = 1 and k = 2, `iot` k = 1
and `general` k = 3. The gate needs no tokenizer — whether a rewrite is a rewrite is not a question
about tokens — so it runs on every round, before the relative token budget, and it is enforced for
both artifact families (`rails.proposer.null_rewrite_check`).

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
4. **Stage one, per scenario** (`select_per_target`, gates `saves >= 4, harms <= 2, net >= 3` on
   per-row `slot_f1_exact_f1`): slice each arm to that scenario's own 60 rows and count against the
   incumbent. Winner = largest net, ties by fewer harms, then fewer artifact bytes, then lowest `k`.
   A count rule, not an interval: on a metric this sparse a bootstrap over one scenario still says
   little, and a reviewer can recount a count rule by hand. **`saves` and `net` are absolute counts;
   the harm half is a RATE** — the owner's `harms <= 1 per 30 of that candidate's own paired rows`,
   floored at 1 (section 12.2 E6), which is `<= 2` at the V2 draw's 60 rows and stays `<= 1` on
   EVO-A1's 20-row tool quotas. It is one loop-config field, `harms_per_rows` (30), stamped onto both
   harm rules, and every stage-one outcome records `harms_allowed` beside `n` and `harms` so the
   admission is recountable from the receipt alone.

   **The V2 draw is the answer to the power problem this gate had at 30 rows, and the size of that
   answer is measured rather than asserted:** scaling KC-S1b's measured per-stratum saves to a 60-row
   fold clears the gate in **eight of eighteen** scenarios against three of eighteen at 30
   (`docs/checks/speech-aware-evidence-acquisition/2026-09-06-slurp-evo-stage-one-power/power.json`,
   model-free, from the committed KC-S1b read). Five scenarios join — `alarm`, `calendar`, `cooking`,
   `iot` and `qa`, beside the incumbent `social` and `weather` — and `transport` **stays**, at 12.00
   saves and 2.00 harms on 60 rows, which is exactly what the relative bound is for: the absolute
   reading of this gate would have dropped the second-largest measured effect in the corpus purely
   because doubling the fold doubles a scenario's expected harms. What was section 16 open point 0 is
   therefore CLOSED by the owner's own harm-rate ruling rather than left to be decided after a round,
   and it is closed in the direction that keeps the gate's arithmetic scale-free. The admissible set
   nearly triples, so a rounds-1-and-2 null is a statement about the mechanism rather than about the
   sample size.
5. **Assemble the winners** into one candidate state.
6. **Stage two, fold B.** Fly the incumbent and the assembly over all 1,080 rows of
   `SLURP-EVO-FOLD-B-V2`. **Coordinator decision 3 of 2026-09-06 replaces the background tolerance
   with a per-scenario harm bound**, because on SLURP every scenario is a target and there is no
   background population. Accept the assembly **whole** iff all three hold:
   * the **pooled TARGETED** paired CI90 lower bound on `slot_f1_exact_f1` — over the fold-B rows of
     the scenarios stage one admitted — is strictly above 0;
   * **every admitted scenario, on its own 60 fold-B rows, has `harms - saves <= 2` rows** — the same
     `1 per 30 rows` rate stage one uses, floored at 1, from the same `harms_per_rows` field, so the
     two stages can never report two different definitions of one word; and
   * the **non-admitted scenarios, pooled, are no worse than -1.0 pp.**

   The second condition is a row COUNT, not an interval, for the same reason stage one is: it says
   that a scenario the loop claims to have improved may not go backwards, on the confirmation fold,
   by more than one row per thirty it was measured on. The third keeps the tolerance the program wrote for a background
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
about 8x the program's superseded estimate. What the re-draw bought is now measured: under the
owner's relative harm bound, **eight of eighteen** scenarios can clear the stage-one gate instead of
three (section 6 step 4; `2026-09-06-slurp-evo-stage-one-power/power.json`, recomputed at
`harms <= 2` on 60 rows). That is the difference between a testable loop and a preregistered null.
Paid API spend 0.

Registered ceilings are `R_max` times the largest per-round cost, per run id, because plan budgets are
cumulative across every attempt of a run id — with margin where the fragment registers one, which
is why the proposer row reads 288 against an arithmetic 216. **All seven rows are REGISTERED as of
2026-09-06, `consumed = no`**, and `rails.evolution.check_ledger_budget` accepts every one of them
against the loop's own worst case, offline, in
`docs/checks/speech-aware-evidence-acquisition/2026-09-06-slurp-evo-ledger-budget/ledger-budget.json`:

| run id | roster | attempts | calls ceiling | speech s ceiling | GPU h | profile |
|---|---|---|---:|---:|---:|---|
| `SAEA-SLURP-EVO-FOLD-PACKETS-V2` | folds A and B | two preprocess sessions | 2,200 | 6,300 | 2.0 | `bounded-discovery-probe` |
| `SAEA-SLURP-EVO-S1-INTENT-FOLDS-V2` | folds A and B | `attempt-intent-a`, `attempt-intent-b` | 2,300 | 6,500 | 0.6 | `baseline-reproduction` |
| `SAEA-SLURP-EVO-S1-FOLD-A-V2` | `SLURP-EVO-FOLD-A-V2` | `attempt-r{r}-i`, `attempt-r{r}-c{k}` | 25,920 | 74,100 | 6.5 | `baseline-reproduction` |
| `SAEA-SLURP-EVO-S1-FOLD-B-V2` | `SLURP-EVO-FOLD-B-V2` | `attempt-r{r}-i`, `attempt-r{r}-a` | 8,640 | 25,300 | 2.2 | `baseline-reproduction` |
| `SAEA-SLURP-EVO-S1-PROPOSER-V2` | `SLURP-EVO-EXEMPLARS-V2` | `attempt-r{r}-p-{scenario}-k{k}` | 288 | **700** | 1.6 | `bounded-discovery-probe` |
| `SAEA-SLURP-EVO-S1-FINAL-V2` | DEV-1000 | `attempt-<stamp>-evofinal` | 1,050 | 2,900 | 0.3 | `baseline-reproduction` |
| `SAEA-SLURP-MF-EVO-DECONTAMINATION-V1` | — | — | 0 | 0 | 0 | `model-free-check` |

There is no `CURVE-OLD500` run id: Option B spends nothing on the curve.

**The proposer row's speech ceiling is 700, not 0, and the arm still sends no audio.** An earlier
draft of this table wrote 0, which the loop's own budget check would have refused:
`core.model.FrozenCoreAdapter` charges a payload's own `audio_seconds` against the plan even for a
text-only request and `contracts.ExecutionPlan` refuses a non-positive value outright, so
`run_propose_step` charges each draw's ANCHOR construction row. Measured on the real V2 exemplar
roster over all four rounds' actual draws: the worst round is 167.682125 s and the run-cumulative
charge is `worst round x R_max` = **670.7285 s** (the four rounds themselves sum to 662.111437 s).
Registered at 700. It is a harness fact about how a plan is priced, not a claim that the arm sends
audio; every proposer contact is text-only.

Every row is written `consumed = no` and stays so until the loop closes.

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

**The fold base fragment**, which is both the incumbent arm and the base every candidate fragment is
copied from, is `configs/baseline/slurp-phase-slots-given-intent-schema-projected-v2.json`: KC-S1b's
own arm plus exactly one key, `phase_material.slots.fill_params.projection =
"slurp-legal-label-projection-v2"` (section 4). Declaring it on the BASE is what makes a round
single-factor — the incumbent and every candidate select their block from the same sealed label — and
`write_candidate_fragments` merges the base's `fill_params` under the artifact keys it owns, refusing
a collision. KC-S1b's own `configs/baseline/slurp-phase-slots-given-intent-schema-v1.json` is
untouched and is what the DEV-1000 final read flies.

**The loop config declares its own fold sizes.** `configs/knowledge/slurp-evo-s1/loop-v1.json` carries
`fold_a_rows` / `fold_b_rows` 1,080 and `fold_a_speech_seconds` 3,084.528438 /
`fold_b_speech_seconds` 3,154.797375, because every emitted fragment's `execution_plan` is written
from those numbers and charged against the registered ceiling. They were function defaults set to
EVO-A1's 404-row folds until 2026-09-06; a SLURP round costed at 404 would have declared a plan its
own flight exceeds. EVO-A1 declares none of the four and keeps those defaults, so its committed
config and its behaviour are byte for byte unchanged.

**`A_0`'s pins are config too**, under `a_0`, and `LoopConfig.assert_a_0` checks them against the
freshly mined TRAIN tables every time `rails.evolution_carrier` loads carrier material (section 3).

## 12. SPEC for the loop code — what `rails.proposer`, `rails.evolution` and the driver need

**Not implemented here.** `rails/evolution.py`, `rails/proposer.py` and `core/flight/runtime.py` are
owned by track `wt/e3c` this wave. This section is the specification that track needs; every item was
checked against the code as it stands at master `35193cb1`.

**Status, 2026-09-06:** every item below is implemented — see 12.5 for the commits, and for the two
things still owed before round 1 can fly.

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
| E2 | `select_per_target(rows_of_target=...)` takes `target_id -> row ids` | works unchanged: pass `scenario -> that scenario's **60** fold-A sample ids` (the V2 draw of section 16 open point 1 remedy (b), 1,080 rows per fold). **No change** |
| E3 | `confirm_assembly` requires a NON-EMPTY `background_rows` and refuses any overlap with `targeted_rows` | with every scenario a target there is no background population. Allow `background_rows=()` and replace the background bound with the **per-scenario harm bound**, which the owner fixed on 2026-09-06 as a RELATIVE rule in three parts, all measured on fold B: (a) for every scenario whose candidate was ADMITTED at stage one, `harms - saves <= 1 per 30 of that scenario's own rows`, floored at 1 — so **2 at the V2 draw's 60 rows**, and 1 on a 20-row fold; (b) for the scenarios NOT admitted, whose blocks the assembly leaves at the incumbent, the POOLED paired point estimate at or above `-1.0 pp`; (c) unchanged from EVO-A1, the pooled TARGETED CI90 lower bound strictly above 0, pooled over the admitted scenarios' rows. Every scenario's own counts, allowance and CI90 are recorded whichever way the verdict goes |
| E4 | `write_candidate_fragments` emits a baseline fragment with `task_instruction_fill = evolved-artifact-v1` | SLURP consumes its artifact through `phase_material.slots.state_fill`, not `task_instruction_fill`. The writer must be family-aware: emit `configs/knowledge/slurp-evo-s1/evolved-schema-<sha16>.json` and a copy of `configs/baseline/slurp-phase-slots-given-intent-schema-v1.json` whose `phase_material.slots.state_fill` is `"slurp-evolved-slot-schema-for-state"` and which names the artifact relpath and its sha256 |
| E5 | `ledger_budget` | works unchanged. **No change** |
| E6 | `AdmissionGates(saves=4, harms=1, net=3)` | **CLOSED by the owner decision of 2026-09-06.** `saves` and `net` stay absolute counts; the harm half becomes the same RATE as E3, `harms <= 1 per 30 of that candidate's own paired rows`, floored at 1. On the V2 draw's 60 rows per scenario the gate reads `saves >= 4, harms <= 2, net >= 3`; EVO-A1's 20-row tool quotas keep reading `harms <= 1` and its loop config is unchanged byte for byte. The rate is one loop-config field, `harms_per_rows` (default 30), stamped onto both `gates` and `harm_bound`; a second spelling hidden inside either object is refused. Every stage-one outcome records `harms_allowed` beside `n` and `harms`, so the admission is recountable from the receipt alone |

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

### 12.5 E3d landed (2026-09-06)

Track `wt/e3d` implemented this SPEC against the base, with zero model contacts. The commits, in
order:

| commit | what |
|---|---|
| `74aed99f` | `rails/proposer.py`: the second artifact family `slurp-slot-schema` — the block-grammar parser (P8), the per-family form validator (P2, P3), the SLURP sample-id regex (P4), the exemplar renderer and the verbatim instruction (P5), and the two deterministic controls F2 and F3 (P6, P7). A2T behaviour byte-identical |
| `042bfbe2` | `rails/evolution.py`, `rails/evolution_carrier.py`, `rails/phase_material.py`, `data/slurp.py`: `target_kind: scenario` and the single-member relaxation (E1), the per-scenario harm bound in `confirm_assembly` (E3), the family-aware `write_candidate_fragments` targeting `phase_material.slots.state_fill` (E4), the `PHASE_STATE_FILLS` registration `slurp-evolved-slot-schema-for-state` (12.3), the SLURP carrier branch, the TRAIN-locked construction-row loader, and the sealed per-fold predecessor binding (D1). `ledger_budget` and `select_per_target` unchanged (E2, E5) |
| `e3677749` | the driver: `scripts/run_a2t_evolution_round.py` renamed to `scripts/run_evolution_round.py`, carrier-agnostic through the loop config rather than forked (D3), plus `configs/knowledge/slurp-evo-s1/loop-v1.json`, this cell as data |
| `8e0a2703` | `tests/unit/test_slurp_evolution_round_driver.py`: one whole round offline on a synthetic world, byte-identical across two runs, `replay_selection` reproducing stage one, and the harm bound rejecting a constructed breach |
| `0cf8e617` | the owner's relative harm bound (E3, E6) at both stages, with `harms_per_rows` as the one loop-config field and `tests/unit/test_evolution_harm_rate.py` covering both carriers |
| `6926d51b` | `tests/unit/test_slurp_proposer_family.py`: the parser's refusals, the validator's gates and the two controls, one function at a time |

`engineering_base_check.py` PASS; `tests/contract` green; no new module under `rails/probes/`, no
`TaskAdapter` or controller subclass, and the driver is 148 lines against its 150-line cap.

The round is driven exactly as EVO-A1's is, four resumable steps against one config:

```
python scripts/run_evolution_round.py --config configs/knowledge/slurp-evo-s1/loop-v1.json \
    --round 1 --plan-only
python scripts/run_evolution_round.py --config configs/knowledge/slurp-evo-s1/loop-v1.json --round 1
```

**Still owed before round 1 can fly**, and neither is code this track could write:

1. `fold_predecessors` in the loop config carries `manifest_sha256: PENDING` until the one-time
   closed-list intent flight seals on both folds (section 4). The three roster relpaths now name the
   V2 draw, which `wt/evos2` finished. **Still owed.**
2. **The round-1 form twin needs a live tokenizer.** F3's padding search prices each padded variant,
   so no precomputed table can serve it. `run_candidates_step` exposes the `token_counter` seam and
   refuses an estimator, but `scripts/run_evolution_round.py` is model-free and binds nothing, so a
   small prompt-fit entry point under a registered `bounded-discovery-probe` row — the repo's own
   convention for token measurement — is owed before round 1. Rounds 2 and later have no F3 and do
   not need it. **Still owed**, and section 13 item 6 now specifies it.

**Three things the 2026-09-06 model-free pre-flight added to this track's own surface**, none of
which section 12 anticipated:

3. **The fold sizes were function defaults.** `run_candidates_step`/`run_select_step` carried
   EVO-A1's `fold_a_rows = 404` and its two pass durations as defaults the driver never overrode, so
   every SLURP fragment would have declared an `execution_plan` its own 1,080-row flight exceeds.
   They are loop-config fields now, defaulting to EVO-A1's own measured folds so that cell is
   unchanged byte for byte (section 11).
4. **The incumbent had one fragment for two folds.** Both incumbent cells named
   `config.base_fragment`, which for a cell with a per-fold sealed predecessor means the fold-B
   incumbent would be bound to fold A's intent manifest. `LoopConfig.incumbent_fragment` now names
   `<base_fragment>-<fold>` when `fold_predecessors` is declared, both variants are committed, and
   EVO-A1 — whose arm is fold-independent — still flies one fragment on both folds.
5. **`write_candidate_fragments` refused any base `fill_params`.** It now MERGES the base's own
   under the artifact keys it owns and refuses only a collision, which is what lets the projection
   of section 4 be declared once, on the base, for the incumbent and every candidate alike.

## 13. What the flight agent must do before the first contact

**Order, and the first contact.** Everything model-free below is DONE as of 2026-09-06 and marked so.
What remains needs the GPU, and it starts with item 6, the **prompt fit**: it is non-generative,
costs minutes, settles the serving geometry the packet promotion and every reward flight then use,
and is the only thing that can price the round-1 form twin — `run_candidates_step` refuses to build
F3 without a `token_counter`, by design, and refuses an estimator. Running it first also means a
geometry surprise is found before 2,160 packet contacts are spent, not after. So: **6, then 3, then
4, then 7, 8, 9, then round 1.**

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
3. **Preprocess the fold packets — REGISTERED 2026-09-06 as `SAEA-SLURP-EVO-FOLD-PACKETS-V2`
   (2,200 calls / 6,300 s / 2.0 GPU-h, `consumed = no`), and still owed because it needs the GPU.** Promotion starts a llama.cpp sidecar with the decoder AND the mmproj encoder loaded
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
5. ~~**Register `SAEA-SLURP-MF-EVO-DECONTAMINATION-V1`** before validating any candidate.~~
   **DONE**, and the gate is BUILT: 2,205 DEV-1000 sentence 6-gram digests in
   `docs/receipts/knowledge/slurp-evo-decontamination-v1.json` (NEW500 contributes 1,133, a strict
   subset), `A_0`'s 1,008 fillers carrying 8 digests of which 1 is exempt, and `A_0` itself PASSING
   its own gate. Receipt
   `docs/checks/speech-aware-evidence-acquisition/2026-09-06-slurp-evo-decontamination/`. Every
   candidate is validated against that committed artifact through
   `rails.proposer.load_evaluation_ngram_digests`; **no later row re-opens devel sentence text**, and
   the artifact carries digests rather than grams so it cannot itself become the leak (section 8).
6. **Prompt fit, and the F3 token counter — the flight agent's FIRST contact.** A new entry point
   `scripts/slurp_evo_s1_prompt_fit.py`, modelled line for line on `scripts/slurp_kc_s1_prompt_fit.py`
   (which already spawns the server under a gate-checked `contracts.ExecutionPlan`, calls only
   `/props`, `/apply-template` and `/tokenize`, and stops with its own stop receipt), under its own
   `bounded-discovery-probe` row `SAEA-SLURP-EVO-S1-PROMPT-FIT-V1`, registered before the server is
   spawned. **Zero generated tokens.** It owes four things:
   * the worst envelope measured, not estimated: the full-schema fallback at the `+20 %` search
     budget, about 9,000 tokens against KC-S1b's 7,500, on top of the 7,583-character system message;
   * `-np` re-derived from that envelope against the folds' own longest packet, and the model
     fragment changed if it moves;
   * the **`token_counter` binding written down** — which endpoint, at which serving geometry —
     because section 16 open point 2 says it is fixed here and is recorded nowhere else. It is
     `SERVING_TOKENIZER_ID = "llama-server:/tokenize"` on the resident server at the flight's own
     geometry, and `validate_slurp_candidate_artifact` refuses any other `token_counter_id` unless
     `allow_estimator=True`, which a flight never passes;
   * that counter handed to `run_candidates_step(..., token_counter=...)` so round 1's **form twin
     F3** can be built. `_slurp_control_candidates` raises rather than pricing it with a ratio, and
     that refusal is the design: KC-A1 died four tokens over a forty-token cap because its builder
     injected a chars-per-token estimator as its counter.
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

**The prompt noise floor, added 2026-09-07 (track E3e). Reported, never gated.** Every round receipt
from now on carries `extra.noise_floor`: per target and pooled, the rows whose rendered prompt was
byte-identical across the two fold-B arms, of those the ones that answered differently anyway
(`unchanged_prompt_flips`), and the round's saves and harms split by the same test. It is computed by
`rails.evolution.prompt_noise_floor` from the sealed traces the confirm step's own two score files
already name (score file → run manifest → `raw_trace` for the question and `outputs.jsonl` for the
answer's digest, both hash-checked; neither prompt nor response text leaves the function). "The same
question" is `question_sha256`: the whole sealed request payload MINUS `request_id` and
`decoding_params.id_slot`, which are an ordinal and a server slot rather than anything the core was
asked — on round 1, 820 of 1,080 rows differ in `id_slot` alone and 62 in `request_id`, so comparing
whole request digests would have reported 842 changed questions against the 61 there are. Rebuilt
over round 1's own sealed traces the block reproduces the verdict's independently computed numbers
exactly: 61 changed, 1,019 unchanged, 286 flips, 3/1 saves and harms on changed questions against
15/16 on unchanged ones. It exists because that quantity is large: 286 of 1,019 byte-identically
asked rows returned different text, and 31 of the 35 rows whose reward moved were of that kind.
**The admission rule is unchanged** — nothing in `select_per_target`, `confirm_assembly` or
`advance_round` reads any of these counts, and whether the rule should change is the owner's open
question. A trace this driver cannot resolve leaves the block `measured: false` with the reason
recorded; a diagnostic never stops a round.

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
| 3 | **A per-scenario harm bound replaces the background tolerance**, because every scenario is a target: each admitted scenario at `harms - saves <= 1 row per 30 of its own` on fold B (so `<= 2` at the V2 draw), the non-admitted scenarios pooled at `>= -1.0 pp`, and the pooled targeted CI90 lower bound `> 0`. | section 6.6 |
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
  **eight** of eighteen scenarios able to clear the stage-one gate instead of three
  (`docs/checks/speech-aware-evidence-acquisition/2026-09-06-slurp-evo-stage-one-power/`,
  model-free, zero contacts, from the committed KC-S1b per-stratum table, recomputed at the owner's
  `harms <= 2` on 60 rows). It is eight and not the nine an earlier draft asserted: rounding the
  expected counts would additionally admit `datetime`, and the counts are not rounded.
* **`transport` stays, because the harm bound is a RATE.** Read absolutely, the stage-one gate is
  not scale-free: doubling the fold doubles a scenario's expected harms while an absolute bound
  stays at one row, and `transport` — 12 saves and 2 harms in 60 measured DEV rows, the
  second-largest measured effect in the corpus after `social` — would be refused at 60 having
  cleared at 30 (6.00 / 1.00). The owner's own ruling of 2026-09-06 (section 12.2, E3 and E6) makes
  the harm half of BOTH stages `1 per 30 rows`, floored at 1, from one `harms_per_rows` field, so
  the gate reads `harms <= 2` at the V2 draw's 60 rows and `transport` clears. **Eight of eighteen**
  scenarios are admissible, not seven, and the arithmetic for both readings is in
  `2026-09-06-slurp-evo-stage-one-power/power.json`. This closes what an earlier draft carried as
  section 16 open point 0: the question was answered by the ruling that was already in force, not by
  a fresh decision, and it is answered before takeoff rather than after a round is read.
* **The slot-contact rate the direction cited does not reconcile with the receipts.** The figure
  given was "1,008 contacts in 0.08 GPU-h" (0.2857 s per contact); the KC-S1b flight receipt records
  1,000 contacts in 735.9065 s (0.7359 s per contact), and KC-S1a, the cheaper arm, took 531.3 s for
  1,000. Section 10 is computed at the receipt-backed rate and carries both columns. **The
  coordinator should settle which rate the registered ceilings are written against** — it is the
  difference between 8.25 and 3.94 planned GPU-h, not between two ways of describing the same run.

### Still open

**Nothing model-free is open. Every remaining item needs the GPU**, and the three that were open on
2026-09-05 are closed:

0. ~~Should the stage-one harms bound scale with the fold?~~ **CLOSED by the owner's own harm-rate
   ruling** (section 12.2 E3/E6), which was already in force when the question was written down:
   both harm rules are `1 per 30 rows`, floored at 1, from the single `harms_per_rows` field, so
   the gate is `harms <= 2` at 60 rows, `transport` clears, and eight of eighteen scenarios are
   admissible. Sections 6 step 4 and 6.6 now state the gate that way. Preregistered before takeoff.
1. ~~`A_0`'s hash re-verification at takeoff.~~ **CLOSED, 2026-09-06.** `scripts/verify_slurp_evo_a0.py`
   re-mined the schema from TRAIN and reproduced all eleven published quantities, the unfloored table
   is pinned for the first time, and `LoopConfig.assert_a_0` re-checks both hashes at every carrier
   load rather than leaving the pin as prose (section 3).
2. ~~The token counter binding at prompt fit.~~ **WRITTEN DOWN** in section 13 item 6 — the resident
   server's `/tokenize` at the flight's own serving geometry, `SERVING_TOKENIZER_ID`, refused for any
   other id unless `allow_estimator=True` — and it still has to be MEASURED, which needs the GPU.

**What round 1 waits on, all of it GPU work, in order:**

| # | owed | row |
|---|---|---|
| 1 | the **prompt fit**, `scripts/slurp_evo_s1_prompt_fit.py`, non-generative: the `+20 %` worst envelope, `-np` re-derived, and the `token_counter` bound so the round-1 form twin F3 can be priced | `SAEA-SLURP-EVO-S1-PROMPT-FIT-V1`, still to be registered by the flight agent |
| 2 | the **fold packets**, 0 of 2,160 present | `SAEA-SLURP-EVO-FOLD-PACKETS-V2`, **registered** |
| 3 | the **one-time intent flight** on both folds, and its two `manifest_sha256` values written into `configs/knowledge/slurp-evo-s1/loop-v1.json` and into the two per-fold incumbent fragments, which carry `PENDING` until it seals | `SAEA-SLURP-EVO-S1-INTENT-FOLDS-V2`, **registered** |
| 4 | the wire check, the four-row MF-5 dry run, and a clean tree for the whole run | — |

**Track E3c is no longer the blocker.** Section 12.5 records the SLURP half landing on `wt/e3d`,
and this pre-flight closed the three things that were owed beside it: the decontamination gate is
built, `A_0` is closed, and the exposure rows exist and are proved to admit the loop's worst case.
The proposer RUNNER that turns a planned contact into a flown one is what item 1's row will exercise
first.

**One routing note for whoever owns section 12.** That section is the SPEC handed to track E3c and
is preserved as it was handed over rather than rewritten. Where it and the live sections disagree,
**sections 6.4 and 6.6 are authoritative**: E2's "30 fold-A sample ids" is 60, and the stage-two
bound is `harms - saves <= 1 row per 30 of that scenario's own` for each ADMITTED scenario, with the
`-1.0 pp` tolerance applying to the NON-admitted scenarios pooled. E3 and E6 already state the
owner's harm RATE correctly, and the code implements it; what is stale is only the prose around
them, and items 3 to 5 above record what the SPEC did not anticipate.
