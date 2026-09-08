# SLURP slot knowledge views — the KV family, design note and preregistration v1 (2026-09-08)

**Owner Decision 11-A, 2026-09-08**: GO for the static slot-value cards, **and** the slot task's
local-optimisation space is widened from "the card" to the whole **knowledge-view space** — type
DESCRIPTIONS, FEW-SHOT exemplars, vocabulary CARDS, RETRIEVED knowledge — each admitted one module
at a time with its form twin.

This note turns that decision into four preregistered cells and their twins. **Status: REGISTERED,
NOT FLOWN. Zero model contacts were spent preparing it**; every number in it is model-free and
re-derivable from committed bytes (`SAEA-SLURP-MF-KV-VIEWS-PREP-V1`, receipt
`docs/checks/speech-aware-evidence-acquisition/2026-09-08-slurp-kv-views-prep/`).

Predecessors this note is built on and does not restate:
`docs/readiness/2026-09-05-slurp-slot-stage-kc-s1-v1-verdict.md` (KC-S1b, ADMITTED, official
SLU-F1 44.35), `docs/readiness/2026-09-08-mf9-slurp-slot-gap-audit-v1.md` (the loss decomposition
and the module ladder), `docs/readiness/2026-09-08-mf10-slot-vocabulary-cards-and-normalized-slu-v1.md`
(the slot classes, the cards, the containment finding, the normalized scorer and the admission
primary), `docs/readiness/2026-09-08-mf8-speech-to-knowledge-audit-v1.md` (exemplar availability),
`docs/readiness/2026-09-07-slurp-consumption-ku-s3-v1-preregistration.md` (KV-4, the retrieval
view) and `docs/readiness/2026-09-08-agent-system-episode-and-core-pressure-v1.md` (the episode
table, the core-pressure covariates and the module admission gate).

---

## 1. The family

| cell | run id | view | what it adds to KV-0 | twin |
|---|---|---|---|---|
| **KV-0** | `SAEA-SLURP-KV0-EXAMPLES-FREE-DEV1000-V1` | `examples-free` | nothing — it is KC-S1b's block with its five example fillers **removed** | none: KV-0 **is** the null view |
| **KV-2** | `SAEA-SLURP-KV2-CARDS-DEV1000-V1` | `cards` | the full TRAIN vocabulary card of every CLOSED type the block lists | `SAEA-SLURP-KV2-CARDS-TWIN-DEV1000-V1` |
| **KV-1** | `SAEA-SLURP-KV1-DESCRIPTIONS-DEV1000-V1` | `descriptions` | one TRAIN-derived description line per listed type, naming **no** value | `SAEA-SLURP-KV1-DESCRIPTIONS-TWIN-DEV1000-V1` |
| **KV-3** | `SAEA-SLURP-KV3-FEWSHOT-DEV1000-V1` | `fewshot` | k = 3 TRAIN exemplars of this intent as `transcript -> slots` pairs | `SAEA-SLURP-KV3-FEWSHOT-TWIN-DEV1000-V1` |
| **KV-4** | `SAEA-SLURP-KU-S3-FILLERS-*-DEV1000-V1` | retrieval | the top-5 speech-keyed TRAIN neighbours' fillers as traced typed content | already preregistered (KU-S3) |

Everything else is KC-S1b's, by construction and not by assertion: the roster, the contact count
(one per row), the system message, the directive template, the sealed predecessor manifest, the
packet promotion receipt, the decoding parameters and the serving geometry. Composed through
`configs/baseline/slurp-phase-slots-kv*.json` and `configs/experiment/slurp-kv*.json`.

### 1.1 The design decision MF-10 handed on, taken here

MF-10 section 5 left one open item: *whether the card replaces the schema block's five examples or
the two are merged into one supplied artefact — because section 2.3 shows they cannot both be
sent.* The family takes the first branch, and extends it to every view.

**Every KV block travels where KC-S1b's admitted block travels — the per-sample state-fill suffix
appended after the sealed state — and REPLACES that block's five example fillers.** Three reasons,
in the order they bind.

1. **One factor.** The comparator is KC-S1b, whose mechanism is an instruction-side knowledge
   block. A view that moved the same knowledge into the traced-supply channel would move **two**
   things — the content and the channel — and the study's strongest rule is that a cell moves one.
2. **A replacement occupies what it replaces.** The five examples live in the instruction. A block
   that is measured *against* them has to sit where they sat.
3. **The channel is already the right one for this kind of payload.**
   `data.slurp.render_slurp_intent_slot_schema`'s own docstring states it: this block is a
   **USE-side instruction** — which types to fill and how to write a filler — *not* a retrieved
   knowledge payload, and `rails.runner._assert_agent_control_excludes_knowledge_payloads` exists
   to stop control text **bypassing traced supply**, which a deterministic per-intent view has no
   traced supply to bypass. KV-4 is the one view that genuinely retrieves, so it keeps
   `phase_supply` and its values stay typed content.

**Deviation recorded.** The brief that commissioned this family asked for the containment check to
show *zero card or exemplar value inside any instruction*. Under the decision above that number is
**100 % by construction for KV-1/2/3** — the view *is* the instruction-side block — and it is
reported rather than hidden (section 5, fold C3). The two containment questions that can pass, and
do, are C1 and C2. Anyone who prefers the other branch of MF-10's open item is choosing a different
experiment, and it would need its own snapshot views, its own deterministic supply kind in
`rails.phase_supply`, and a two-factor contrast against KC-S1b.

### 1.2 KV-0 needed its own renderer, and that is a finding

MF-10 proposed `examples_per_type=0` through the admitted renderer. Measured on the real corpus,
that combination renders **every** type as
`- date (21.8 percent of slot mentions): no example filler recorded`, under a header that still
promises *"fillers heard with that type"* — a block that tells the model the corpus recorded no
filler for `date`, which is false, on all sixty intents. KV-0 is the base of a whole family and
cannot ship a false claim. `rails.slurp_knowledge_views.render_examples_free_block` renders the
types and their shares, and `KV0_SCHEMA_HEADER` stops promising what the block no longer carries.
Every other sentence of the admitted header is kept verbatim.

---

## 2. What each view says, and what it costs

Receipt: `docs/checks/speech-aware-evidence-acquisition/2026-09-08-slurp-kv-views-prep/`, which
re-derives MF-10's six published card figures from the same TRAIN bytes through the same library —
18 closed types, 842 surface forms, median 1,432 and worst 2,010 proxy tokens on `social_query`, 39
intents rotating in place, 14 that cannot — and reproduces **all six exactly**, plus the KC-S1b
fragment's own 11,863 protected snapshot payloads.

**Every token figure below is MF-10's STATED PROXY** (whitespace tokens × 1.3, rounded up). No
tokeniser was called. Each cell measures its own envelope through the serving `/apply-template` +
`/tokenize` seam before takeoff, as KC-S1b did.

| view | block min / median / max | the view's own share | fallback block | intents with no view block |
|---|---|---|---|---|
| KC-S1b (admitted, five examples) | 110 / 177 / 251 | — | 5,353 | — |
| **KV-0** | **102 / 138 / 175** | 0 | 3,158 | 60 (by definition) |
| **KV-1** | 231 / 436 / 650 | 129 / 298 / 476 | 5,585 | 0 |
| **KV-2** | 102 / 1,542 / 2,148 | 0 / **1,432** / **2,010** | 6,471 | **7** |
| **KV-3** | 192 / 250 / 328 | 90 / 117 / 181 | 3,308 | 0 |

**KV-0 is cheaper than the block it replaces**, because removing five fillers per type is a
subtraction — the family's first cell costs the core *less* prompt, which is the direction the
2026-09-08 core-pressure correction asks for.

### 2.1 KV-1 — descriptions, and why they are statistics rather than prose

A description line reads

> `- date: a closed vocabulary the corpus re-uses; 289 distinct TRAIN forms over 1823 mentions;`
> `typically 1 word (1 to 9); written without digits; its most frequent form carries 28.7 percent`
> `of them`

Its prose comes from exactly two places: MF-10's class (one of three **declared** glosses) and the
type's own TRAIN surface statistics. **A hand-written semantic gloss per type was rejected**, and
the rejection is a methodological choice, not a shortcut: an author's sentence about what `date`
"means" is the author's knowledge rather than the corpus's, it cannot be re-derived from committed
bytes, and its twin could not be token-matched by construction. What the corpus can say about a
type is how big its vocabulary is, how long its forms are, whether it writes digits and how
concentrated it is — and that is what the line says.

**A description names no filler.** Verified in the unit tests and in the receipt: zero TRAIN filler
strings occur in any description block.

### 2.2 KV-2 — the cards, unchanged from MF-10

`analysis.slurp_slot_vocabulary` is reused, not re-implemented: the same `build_vocabulary_card`,
the same `CARD_HEADER`, the same ordering, the same `derange_card_mapping`. MF-10's oracle for this
view is **SLU-F1 61.81 vocabulary-limited (+17.46)** at zero retrieval contacts and zero seed GPU
hours, and **480 of the 565 mass units it repairs are MISSING** — it is a recall module, which is
why its gain survives the normalized metric (+18.64 official against +18.69 normalized) where MF-9's
value projection does not.

**Seven of sixty intents list no CLOSED type at all** and receive the KV-0 block alone. That is
reported as a covariate and as a stratum, not designed away.

### 2.3 KV-3 — exemplars, and the rule that picks them

`select_exemplars` sorts the intent's TRAIN utterances by id, shuffles that list once with
`random.Random(20260903)` — the seed's only entry point — and then greedily takes the utterance
covering the most listed types not yet covered, breaking ties by the most on-target types and then
by the fewest off-target ones. Reproducible from `(seed, sorted ids)` and from nothing else.

| quantity | arm | twin |
|---|---|---|
| share of the intent's listed types the k = 3 cover reaches, mean | **0.9648** | **0.6477** |
| intents whose listed types are fully covered | **51 of 60** | 19 of 60 |
| TRAIN utterances per intent, min / median / max | 4 / 130 / 810 | — |
| intents with fewer than k candidates | **0** | 0 |

**No DEV text enters anywhere.** The exemplars are TRAIN sentences about OTHER utterances; the
query's own transcript is never produced, never requested and never available — the owner's
2026-09-06 no-transcript ruling is satisfied by construction, because the core is given text about
the corpus and audio of the row.

**KV-3s is named and NOT preregistered here.** MF-8 measured same-speaker same-intent TRAIN
availability per DEV row at **943 of 1,000 rows with ≥ 1 and 843 with ≥ 3** (the brief's 95.7 % /
84.9 % is a paraphrase; MF-8's committed numbers are 94.3 % / 84.3 %). A same-speaker exemplar
variant belongs to the KU-S4 line, where the speaker dimension is the factor; here it would confound
the view with the speaker.

### 2.4 KV-4 — how KU-S3 composes on this base

KU-S3 is preregistered unchanged as to mechanism, and **flies after KV-2**. Two things follow from
KV-0 becoming the base and are stated here so nobody has to infer them.

1. **Its blocks also replace the examples.** Before KU-S3 flies, its three baseline fragments swap
   `state_fill` from `slurp-intent-slot-schema-for-state` to
   `slurp-slot-knowledge-view-for-state` with `fill_params.view = "examples-free"`, so that the
   retrieved fillers are the one place a filler is written. Without that swap the retrieved values
   and the block's own five examples are two sources of the same kind of string and the contrast is
   not clean. This is a fragment edit, not a mechanism change; the vectors, the snapshot, the knobs,
   k, tau and the twin are untouched.
2. **Its containment stays measured at 0 and can only improve.** KU-S3's slot-filler snapshot
   already collides with **0 of 1,000** KC-S1b instructions *including* their five examples;
   removing the examples removes strings, never adds them.

KU-S3's own decision rule, comparator and budgets stay exactly as its preregistration states, with
one substitution: **its comparator becomes the sealed KV-0 rows** if KV-0 is admitted or neutral,
and stays the sealed KC-S1b rows only if the whole family is abandoned at KV-0.

---

## 3. The twins

| view | matched by | intents with a block | matching to the character | cannot rotate in place | max abs char delta, all / rotating |
|---|---|---|---|---|---|
| KV-1 | construction (per-intent rotation) | 60 | **55** | 5 | 46 / **0** |
| KV-2 | construction (MF-10's own derangement) | 53 | **39** | 14 | 4,891 / **0** |
| KV-3 | measurement (a donor intent's sentences are other sentences) | 60 | 0 | — | 327 / 327 |

**Every intent that can rotate its view in place matches its twin to the character.** The intents
that cannot are those listing exactly one carded or described type: any twin of a single vocabulary
is a different vocabulary of a different size. They are pooled and rotated among themselves — MF-10's
and KU-S3's own resolution for singleton buckets.

**The twin contrast is therefore read TWICE, and both reads are fixed here, before any flight.**

* **(a) Whole roster.** Every row, the honest "same mechanism, wrong vocabulary" control. This is
  the contrast the decision rule names.
* **(b) The rotating stratum.** Only the rows whose predicted intent rotates its view in place —
  a stratum defined by construction from the committed TRAIN schema and the committed derangement,
  computable before the flight and not after seeing a score. On this stratum the twin is
  volume-matched to the character, so a gain there cannot be a volume effect.

If (a) and (b) disagree in sign, the disagreement is the finding and the cell is not admitted on
either. Per the owner's 2026-09-06 ruling token counts are advisory: the twin is the lock, and the
block's character volume is a reported covariate beside every contrast.

KV-3's twin is the one matched by measurement rather than by construction — mean absolute character
delta **95.1** on a block whose median is about 800 characters. Its volume covariate is reported
beside every KV-3 number, and its type-coverage gap (0.9648 against 0.6477) is the factor stated as
a construction number.

---

## 4. Order, and why

**KV-0 → KV-2 → KV-1 → KV-3 → KV-4 (KU-S3).** One experiment in flight at a time; a view is
admitted only after its predecessor is replicated or root-caused to a named component (owner rule,
2026-09-03).

1. **KV-0 first, and it gates everything.** It is the base every other view is measured against, so
   nothing above it can be read until its rows are sealed. It is also the cheapest cell in the
   family and the one that answers a question nobody has asked yet: *what were the five examples
   worth?*
2. **KV-2 second** because it is the view the owner's decision names, because MF-10 has already
   priced it (+17.46 vocabulary-limited oracle) and shown it is a **recall** module, and because
   its twin is the strongest of the three.
3. **KV-1 third.** It is the cheap test of whether the core needs the *values* or only the *kind*:
   about a fifth of KV-2's token cost, and a direct read on how much of KV-2's effect (if any) is
   vocabulary rather than orientation.
4. **KV-3 fourth.** It is the only view that shows a whole worked answer, so it is the one most
   likely to move format as well as content — and MF-9 already located a format problem in `time`.
   It flies after the two views that isolate content.
5. **KV-4 last**, as its own preregistration and the 2026-09-06 hand-off already require, and only
   if KV-2 is not HARMFUL.

**No cell in this family is a knob sweep.** Nothing is re-flown on the strength of a number, k is
not tuned, the seed is not re-drawn, and a NULL result closes that view rather than opening a
search.

---

## 5. Containment, measured

| fold | what it asks | result |
|---|---|---|
| **C1** | does a view payload occur inside the arm's own DIRECTIVE? | **0** on all seven arms, 1,240 payloads checked |
| **C2** | does a protected payload of the BOUND TRAIN snapshot occur inside the instruction? — the fold `rails.runner._assert_agent_control_excludes_knowledge_payloads` runs at contact time, here through `rails.runner`'s own reducer | **0** on all seven arms over all 61 renderable blocks each; **0** on the admitted KC-S1b block through the identical fold |
| **C3** | do a view's own payloads occur inside the instruction that carries them? | **100 % by construction** for KV-1/2/3 (section 1.1), reported and not hidden. **0** is the number KV-4 must keep, because its values are traced supply, and it already measures 0 of 1,000 |

C2's remaining surface — the bound snapshot against the 1,000 **sealed** closed-list states — is
**cited, not recomputed**: KC-S1b's own committed 78 facet-representation hits and 0 value hits, on
a snapshot whose content dimension no KV cell binds. The preparation row opened no sealed DEV
output.

C1 is the property that makes this a single-factor family: **every KV arm ships the same directive
bytes**, and the view lives only in the per-sample block.

---

## 6. Analysis, decision rules and guards (frozen before any read)

`analysis.paired.paired_contrast`, delta = arm minus comparator on per-sample official scores,
stratified bootstrap **N = 10,000**, strata = the gold scenario, **seed 20260903**, **CI90**, exact
sign test. Both weightings reported: natural mixture and equal-stratum. Per-stratum table with
every verdict, without exception.

Scoring is the dataset's standard scorer: the real, unmodified official `evaluate.py` at pinned
commit `8eb16545762be97ace75334109d73824217311f1` in `~/.venvs/slurp-official-eval`,
`--average micro`, run **once over the complete manifest** through `core.scoring_batch`, never
sharded, with the official-vs-port identity check.

**The admission primary is MF-10's.** Official SLU-F1 is the **primary**;
`slurp-slu-f1-normalized-v1` is a **secondary that must AGREE IN SIGN**. A cell whose two columns
disagree in sign is not admitted on the strength of either, and the disagreement is reported with
the per-type table that produced it.

### 6.1 KV-0 — a subtraction, read under non-inferiority

KV-0 removes information. It is therefore **not** held to a gain rule against KC-S1b.

* **NEUTRAL** (and the family's base) iff the paired official SLU-F1 CI90 lower bound on the
  unexposed NEW500 is **above the non-inferiority margin** taken from the carrier's own null
  (section 6.4), with the normalized secondary agreeing in sign.
* **ADMITTED** if that lower bound is above 0 — the five examples were costing the arm, which is a
  result in its own right and one the core-pressure correction predicts is possible.
* **HARMFUL** if the upper bound is below the margin. The family is then re-designed around a block
  that keeps its examples, and **no KV cell above KV-0 flies** — because every one of them is
  defined as a replacement for those examples.

### 6.2 KV-1, KV-2, KV-3 — the module rule

**ADMITTED** iff, on the unexposed **NEW500**, the paired per-sample **official** SLU-F1 CI90 lower
bound is above 0 **against the sealed KV-0 rows** AND above 0 **against the form twin**, with the
normalized secondary agreeing in sign on both, AND the twin contrast holding in sign on the
rotating stratum of section 3(b).

**NULL** if any interval includes 0: that view closes on this carrier and the next one flies.
**HARMFUL** if an upper bound is below 0: the view closes and is recorded as a documented negative.

The twin condition is the whole point of the family. A card, a description or a worked example must
not be worth anything unless it is the **right** card, the **right** description or the **right**
example.

### 6.3 Guards, reported with every cell

* **Intent identical by construction** — the sealed closed-list prediction is the input on every
  arm — and asserted row by row. A non-zero intent delta is a defect, not a result.
* **Entity strict F1, Word-F1 and Char-F1** reported beside SLU-F1, official and normalized, per
  cell and per type.
* **Schema conformance** (MF-9: 914 of 1,000 on KC-S1b) reported per arm: a view that raises the
  score by making the output less parseable is not a win.
* **The fallback-row count** — how many rows took the full-schema block — per arm, as KC-S1b and
  EVO-S1 both report it.
* **The block's character volume** per row, arm and twin, as the token covariate.

### 6.4 The margin, and its provenance — declared as IMPORTED

The family rule of 2026-09-08 requires a non-inferiority margin from **the carrier's own null**.
SLURP's own null replicate is **queued and has not landed**. Until it does, this family declares
the margin as **IMPORTED**: EVO-S1 round 1 measured, on this carrier and this build, that **286 of
1,019 byte-identically prompted rows (28.1 %) returned different text anyway**, and 31 rows moved
their reward on an unchanged prompt against 4 on a changed one. That flip floor is the reference
any claim from a handful of moved rows is read against.

**It is declared imported, and it is not a substitute.** The moment the SLURP own-null replicate
lands, KV-0's non-inferiority margin is restated from it and this section is superseded — the same
discipline `SAEA-E21-FULL44-NULL-REPLICATE-V1` established for Earnings-21. A KV-0 verdict written
before the replicate lands says so in its first paragraph.

### 6.5 Populations

| population | n | receipt | role |
|---|---|---|---|
| DEV-1000-NEW500 | 500 | `docs/receipts/probe-samples/DEV-1000-NEW500.json` | **the decision population**; reported first |
| DEV-1000 pooled | 1,000 | `docs/receipts/probe-samples/DEV-1000.json` | reported; the **replication stratum** for a cell admitted on NEW500 |
| DEV-500 (prior-exposed) | 500 | `docs/receipts/probe-samples/DEV-500.json` | reported separately, never pooled into a decision |

Split identity hash `8580d199bffc95a51ad6d8c5b2a2e9e39faa2c551dd095f8afcd78174a1e3c84`. **No new
draw and no new exposure.** Gold never enters the flight process: samples are built label-free from
the runtime view and the adapter's `gold()` refuses outright. The held-out `test` split is never
named, loaded or scored.

**n = 1,000 rows per arm clears the program's n ≥ 400 paired-claim floor.** The decision is read on
NEW500 (n = 500), also above it.

---

## 7. Budgets and geometry

| run id | calls (ceiling) | speech seconds (ceiling) | GPU-h (ceiling) | tool | embedding | paid |
|---|---|---|---|---|---|---|
| `SAEA-SLURP-KV0-EXAMPLES-FREE-DEV1000-V1` | 1,000 + 8 canaries (**1,050**) | 2,884.7937 (**3,000**) | ~0.20 (**1.0**) | 0 | 0 | 0 |
| `SAEA-SLURP-KV2-CARDS-DEV1000-V1` | 1,000 + 8 (1,050) | 2,884.7937 (3,000) | ~0.20 (1.0) | 0 | 0 | 0 |
| `SAEA-SLURP-KV2-CARDS-TWIN-DEV1000-V1` | 1,000 + 8 (1,050) | 2,884.7937 (3,000) | ~0.20 (1.0) | 0 | 0 | 0 |
| `SAEA-SLURP-KV1-DESCRIPTIONS-DEV1000-V1` | 1,000 + 8 (1,050) | 2,884.7937 (3,000) | ~0.20 (1.0) | 0 | 0 | 0 |
| `SAEA-SLURP-KV1-DESCRIPTIONS-TWIN-DEV1000-V1` | 1,000 + 8 (1,050) | 2,884.7937 (3,000) | ~0.20 (1.0) | 0 | 0 | 0 |
| `SAEA-SLURP-KV3-FEWSHOT-DEV1000-V1` | 1,000 + 8 (1,050) | 2,884.7937 (3,000) | ~0.20 (1.0) | 0 | 0 | 0 |
| `SAEA-SLURP-KV3-FEWSHOT-TWIN-DEV1000-V1` | 1,000 + 8 (1,050) | 2,884.7937 (3,000) | ~0.20 (1.0) | 0 | 0 | 0 |

Run-cumulative across every attempt of a run id, enforced by `core.model.adapter`. At most **one**
recovery re-registration per run id; a second failure stops the flight and the fix is proven on a
4-row dry run. Each run id needs its own exposure-ledger row, written before its first contact.
Paid API spend 0.

**A KV view has NO pre-flight seed**, which is the whole operational difference from KV-4: KU-S3
pays 0.68–0.71 h of single-threaded CPU per arm scoring 11,514 facets, and a KV arm pays a single
TRAIN mining pass inside the state-fill factory before the first contact.

### 7.1 Geometry: `-np 4` at 16,384-token slots, and why `-np 8` is refused

The commissioning brief named `-c 65536 -np 8` (8,192-token slots) at ~0.12 GPU-h per arm. **That
geometry is refused for this family, on a committed measurement.** KC-S1b's own worst prompt
envelope is **10,006 real tokens** *before* any view is added, driven by the full-schema fallback
rows, and it does not fit an 8,192-token slot — which is precisely why KC-S1b flew `-np 4`
(`configs/baseline/slurp-phase-slots-given-intent-schema-v1.json`, `why_np4`). Two further reasons
agree:

* the comparator is KC-S1b's **sealed** rows and greedy decoding is not bitwise reproducible across
  batch shapes, so geometry-matching to it is a condition of the contrast, not a preference;
* KV-2's fallback block adds about 3,313 proxy tokens on top, which widens the gap rather than
  closing it.

Every fragment therefore declares `serving_slots 4` / `serving_slot_tokens 16384`, matching KC-S1b
byte for byte. **The prompt fit is still measured, not assumed**: before takeoff each arm runs the
zero-generated-token `/apply-template` + `/tokenize` pass over all 1,000 rows through the resident
session, reports its worst envelope against the 16,384-token slot, and pins
`prompt_fit_receipt` + `prompt_fit_receipt_sha256` into its fragment. A negative margin STOPS the
mission. `FlightRuntime`'s own pre-flight estimator is not evidence for a cell like this (KC-S1
deviation 3).

---

## 8. The episode, and the core-pressure covariates

Required by the 2026-09-08 design note, section 6.

| agent | what it does in a KV cell |
|---|---|
| **Planner** | fixed: one observe mode (the frozen DEV-1000 packet), one knowledge view (the cell's `fill_params.view`), a budget of one core call per row, stop after Solve. The view IS the planner's choice, and the family is the search over it |
| **Observer** | the sealed DEV-1000 speech packet, promotion receipt `2accbdc5…a8fe6`. Unchanged on every arm |
| **Solver** | the frozen core, one contact per row, given the sealed intent and the view's block |
| **Reviewer** | **off** in this family, deliberately. A judge would be a second factor; KV measures the view alone. The legal-label projection is likewise **off** (section 1, `predecessor_is_unprojected_and_that_is_deliberate`) |

Core-pressure covariates, reported by every KV verdict (design note section 3):

* core calls per row (1 by construction) and per task unit;
* core **prompt and completion tokens** per row, arm and twin — and this family is the first where
  a module is expected to *reduce* prompt tokens (KV-0);
* the system's decision share: for KV-2 and KV-1 the **narrowing ratio** (types offered by the
  block / 55 types in the ontology) per row; for KV-3 the type coverage of the supplied exemplars;
* the share of rows delivered without any view block (KV-2: 7 of 60 intents), and the fallback-row
  count.

These are covariates, never decision criteria.

---

## 9. The admission-table entries each cell will write

`docs/receipts/harness-admission.json`, one row per module per carrier, status ADMITTED / NEUTRAL /
HARMFUL (design note section 8). Each KV cell writes exactly one row on closure:

| module | carrier | status | evidence |
|---|---|---|---|
| `knowledge view: example-free slot schema (KV-0)` | SLURP | pending | `SAEA-SLURP-KV0-EXAMPLES-FREE-DEV1000-V1` vs sealed KC-S1b, NEW500, official + normalized |
| `knowledge view: TRAIN vocabulary cards, closed types (KV-2)` | SLURP | pending | `SAEA-SLURP-KV2-CARDS-DEV1000-V1` vs sealed KV-0 and vs `…-TWIN-…` |
| `knowledge view: TRAIN type descriptions (KV-1)` | SLURP | pending | `SAEA-SLURP-KV1-DESCRIPTIONS-DEV1000-V1` vs sealed KV-0 and vs `…-TWIN-…` |
| `knowledge view: k=3 TRAIN exemplars (KV-3)` | SLURP | pending | `SAEA-SLURP-KV3-FEWSHOT-DEV1000-V1` vs sealed KV-0 and vs `…-TWIN-…` |
| `knowledge view: speech-keyed retrieved fillers (KV-4 / KU-S3)` | SLURP | pending | its own preregistration, re-based on KV-0 per section 2.4 |

The existing row `TRAIN slot schema view + two-stage Solve | SLURP | ADMITTED | KC-S1b` is **not**
restated by this family: KV-0 measures what the five examples inside that view were worth, not
whether the view itself is admitted.

---

## 10. Wire check, and the state of the engineering

**Request half: PASS on all seven arms**, 4 DEV-1000 rows each, against `WireCheckGate` and
`WireCheckTransport` — **zero sockets, zero model contacts, zero GPU**. Receipts:
`docs/checks/speech-aware-evidence-acquisition/2026-09-08-slurp-kv-views-wire-check/`. It drove the
real path: composition, the label-free roster with every media file re-hashed, the knowledge
snapshot load and hash verification, the sealed-manifest predecessor binding, the KV state fill
reading TRAIN, the containment fold on every contact instruction, the request build and the
transport seam.

| assertion | result |
|---|---|
| model contacts | **0** on every arm (the receipt's 4 calls and 15.011 audio seconds are the FAKE transport's, metered because the meter cannot tell) |
| dispatch | `phase-program`, `program_id` `phase-slots-given-intent-v1` — KC-S1b's own program, no new policy id — one phase `slots`, rows 4, contacts 4, `contacts_per_sample` 1 |
| `supplied_phases` / `seeded_supply_phases` | **empty**, `phase_supply` `null`, on every arm |
| resolved system message | sha256 `4073f79ef25c4796b0a46cb2ac7f5d4982c83084982b87ddd8a70504090d37db` on **all seven** arms — byte-identical to KC-S1b's own |
| the arm's static DIRECTIVE | sha256 `221ed0d343b0a543eda98008312938da25bde204a131efe8427ea8e3934a5e1f`, 841 characters, on **all seven** arms — fold C1 stated as an identity |
| containment at contact time | `rails.runner._assert_agent_control_excludes_knowledge_payloads` raised on **none of the 28 contacts**, against 11,863 protected payloads |
| four distinct request bodies per arm | yes, each with its own speech packet re-verified; 18 payload keys, equal to the arm's visible fields |
| config and protocol hashes | **distinct per arm** — `fill_params` rides the config hash |
| typed knowledge blocks | **0** on every row — correct: a KV view is instruction-side, not traced supply. This is where KV-4 reads non-zero |
| seal and score | **OK** on every arm: 4 canonical output rows and all four declared scorers running to completion over the complete manifest. No score there is a measurement — the transport answers with a canned string |

**The pre-flight cost of a KV view, measured.** The state fill mines TRAIN once per run inside
`_resolved_state_fills`, before the first contact: 6.2 s of dispatch wall for KV-0, which skips the
mining, against 8.8–11.0 s for the six views that build cards, descriptions or exemplars — about
**3 to 5 seconds, once, for a whole flight**. That is the operational contrast with KV-4, whose
retrieval seed costs 0.68–0.71 h of single-threaded CPU per arm.

Engineering: `python scripts/checks/engineering_base_check.py` **PASS**; `ruff` clean; the family
adds **one** module (`rails/slurp_knowledge_views.py`, pure renderers) and **one** registered state
fill on the existing `rails.phase_material` base, and no new policy, provider, ranker, fuser,
controller, adapter or probe module. 30 new unit tests.

---

## 11. What a flight agent must do, in order

0. **Merge this branch and re-run the gates**: `python scripts/checks/engineering_base_check.py`
   and `pytest`.
1. **Write the exposure row** for KV-0 — its own run id, its own plan, `consumed = no` — before any
   contact.
2. **Dry run** (`--dry-run`): preflight only, no server, no contact.
3. **Wire check** (`--wire-check`) on a clean committed tree, **with the seal half**.
4. **Prompt fit**, zero generated tokens, all 1,000 rows, through the resident session's
   `/apply-template` + `/tokenize`. Worst envelope against the 16,384-token slot; a negative margin
   STOPS the mission. Pin the receipt into the fragment.
5. **4-row smoke** on the four rows the wire-check fragment already names.
6. **Fly KV-0**, one attempt, one seal, on a clean tree for the whole run.
7. **`core.scoring_batch`**, one job over the complete manifest, never sharded, official-vs-port
   identity check, both scorers.
8. **One registered read**, then the KV-0 verdict and its admission-table row. Only then does KV-2
   open.

Repeat 1–8 per cell, in the order of section 4, one experiment in flight at a time.

---

## 12. What this authorizes, and what it forbids

**Authorizes**: the seven arms above, on DEV-1000, at the budgets of section 7, under the rules of
section 6, in the order of section 4 — and nothing else today. It fixes the roster, the views, the
twins, the comparators, the analysis and the reporting obligations so that flying is execution
rather than design.

**Forbids**: any test-split contact; any superiority or generalization claim; any Stage-3 or
paper-scale activity; any knob, k or seed change on the strength of a number; flying a KV cell
above KV-0 before KV-0 has sealed and been read; flying KV-4 before KV-2; pooling any two KV cells
into one claim; restating KC-S1b's admitted verdict under the normalized scorer; and any claim
about what a knowledge view adds on SLURP drawn from a cell that has not flown.
