# S2a: a model-initiated missing-slot proposal tool and its conversion probe (design)

Date 2026-09-30. Round S2a of the Stage-3 slot-extraction programme (`docs/readiness/2026-09-30-slurp-stage3-replan-v6.md`
section 2). Carrier: SLURP (decision 187; decision 211 keeps the other carriers closed until the SLURP lock). Status:
**design only**. It registers nothing, grants no contact of any kind and authorises no flight. It was written
model-free (zero model, tool, encoder, GPU, scorer or network contacts) in worktree `fable/s2adesign`, from master
`263c4ec6a`. No utterance text, transcript, gold value or model output appears here: only counts, rates, pp, ids,
paths and hashes. Every number is a development number (decisions 28, 86), quoted from the file named beside it.

## S2a in one screen

S1 (`docs/results/2026-09-30-slurp-s1-slu-error-taxonomy-refresh.md` section 3) found 80 MISSING gold items on the A2
arm (COMP-1b on DEV-2000-ADDED) whose value no supply printed. Repairing all 80 is worth 4.43 pp (isolated oracle). At
the best measured slot conversion (M1, 0.2471) that is 1.09 pp, below the decision-192 bar of 1.5 pp. Clearing the bar
needs a **measured** conversion of about 0.33 (26.5 of 80).

S2a proposes the one tool that could add new information on exactly those items: `saea-tool-missing-slot-proposal-v1`.
It is a native tool that the **Solver may call** with one argument, a slot type. It returns either an empty result or
at most three short spans from the pinned Whisper large-v3 transcript (E5-0). The spans are ones the Solver's own draft
does not already cover, ranked by a frozen type lexicon built from TRAIN. The system never calls the tool (206). The
Solver may decline, and an empty result is legal (199).

S2a has three steps:

- **S2a.1 (zero contacts, can run now).** Build the tool deterministically and tune its abstain threshold on TRAIN
  Fold B. Then read its recall ceiling on the 70 not-in-supply items of COMP-1b Fold A, where transcripts already
  exist.
- **S2a.2 (needs an owner row).** One E5-0 Whisper pass over DEV-2000-ADDED: about 0.15 GPU-h, tool contacts only.
- **S2a.3 (the conversion probe).** CONV/KPROBE style, on about 160 DEV rows: the 80-item positive stratum plus an
  80-row seeded control stratum. An offer arm flies against a request-identical no-offer twin, for about 0.6-1.1 GPU-h
  (cap 2.0).

The probe measures the call, decline and empty rates and the net per-item conversion. At n = 80 items the Wilson
half-width is about +/-0.10.

**Reading.**

- A net conversion of at least 27 / 80, with no net harm on the control stratum, would predict >= 1.5 pp for S2c.
- A Wilson upper bound below 0.33 (net <= 18 / 80) would close the line on this source.

**Owner asks.** Before S2a.2 and S2a.3, the owner is asked three things:

- whether decision 201's transcript exception extends from verification to proposal;
- whether to run the DEV tool pass;
- the fold discipline of the probe roster.

## 1. The tool contract

### 1.1 Source: the pinned E5-0 transcript is primary; the TRAIN value lexicon only ranks

**Option 1: E5-0 Whisper large-v3 transcript span search. Verdict: primary.**

For:

- The target is the set of MISSING items whose value is **not in any supply**. In S1, "none" means the TRAIN value
  list (E4) plus audio-only (E5).
- Of the 188 A2 MISSING items, 103 have origin *undetermined* (the note is silent). Only a new hearing instrument
  reaches them (S1 section 4).
- E5-1 names "the transcript proposing slots that are missing entirely" as the one transcript direction its oracle
  does not rule out: 113 items on 106 Fold A rows, ceiling +8.21 [+6.95, +9.57] pp, cross-fit precision 0.2455 at a
  10 % call rate (`docs/results/2026-09-30-slurp-e5-transcript-consistency-oracle-read.md` sections 4 and 7).

Against:

- Containment is 0.7513 on Fold A (0.7606 on Fold B), and worst on `business_name` (0.50) and `person` (0.548).
- A transcript carries no types.

**Option 2: M1 exemplar / slot store v2 values. Verdict: ranking aid only.** The TRAIN value lexicon of each slot type
orders transcript spans; it never supplies a value.

For: the store is pinned, it is in the lock, and it needs no new contact class.

Against:

- By construction the row's supply did not print the 80 items.
- The only measured value-list conversion is W4's 0.0515 (5 of 97). On the 80 items that gives 0.23 pp (S1
  section 3).
- A store cannot hear.

**Consequence.** Every value the tool can return is a substring of the pinned transcript. The tool's ceiling is
therefore the transcript's containment on the target items, which S2a.1 measures before any core contact.

### 1.2 Signature, result and schema budget

- **Catalog id and native function name: `saea-tool-missing-slot-proposal-v1`.**
  - The function name equals the catalog id (`rails/phase_tools.py`, `_native_tool_schema`).
  - Axis `OBS`; cost class `cpu` (a catalog read, no live decode); `ledger_row_type` `tool-contact`.
  - The wrapper lives under `rails/tool_wrappers/`. It is registered through `build_tool_entry`, joins
    `phase_tools.ACTION_TOOLS`, and is pinned by `tool_catalog_check.py`: one function, one schema, rendered in the
    Solver request only (re-plan v6 section 5).
- **One argument: `slot_type`.** A string enum over the SLURP slot-type label set of the task contract. The set is
  closed, and the carrier hook of section 4 supplies it. The model chooses the type; the runtime never receives the
  gold type.
- **Result.** Either `{"slot_type": t, "candidates": [s1, s2, s3]}`, with at most three spans of at most five tokens
  each, or `{"slot_type": t, "candidates": []}`.
  - A span qualifies only if all three hold:
    1. It is a contiguous token run of the row's E5-0 transcript.
    2. Under the E5 canonicaliser (`rails/relisten.canonical_value`, `fold_number_words`), it overlaps no entity value
       in the Solver's own draft in the same episode.
    3. Its score under the frozen type lexicon of `t` clears the abstain threshold. The score is character n-gram
       similarity to the TRAIN values of `t`, taken from slot store v2's train-only build.
  - The threshold and the span and candidate caps are fitted on TRAIN Fold B only, and pinned before S2a.3.
  - Nothing pads the list (decision 199). The abstention is receipted as in module design section 2c.
  - The tool never returns the whole transcript, and never returns intent words as such. A row with no catalog entry
    returns nothing.
- **Description and rendering.**
  - The description is at most two sentences, with one parameter. This is the EFF-1 lesson: a 13.9k-token constant
    catalog was HARMFUL, SLU-F1 -4.39 [-6.69, -2.17] (module design section 2d).
  - The tool is rendered only in the Solver's request, with `tool_choice` `auto`.
  - At most one call per Solver visit. The ceiling rises by 2 contacts per row at `max_revisions` 1; the loader
    computes it.
- **Receipt.**
  - Per row and per offered node: `tool_decision {offered, called, args_hash, result_hash, used_in_answer}`.
  - Per call, a hash-only `saea-missing-slot-proposal-v1` sub-receipt: slot type, candidate count, the sha256 of each
    candidate value, the transcript artifact sha256, the abstain score and the threshold.
  - `used_in_answer` is computed deterministically after delivery, never read from the model's claim. It is true when
    a delivered entity of type `t` has a canonical value equal to a returned candidate, and that value was absent from
    the pre-call draft.
- **Pinned and logged.**
  - The catalog is an E5-0 `saea-prepared-speech-observation-catalog-v1`: checkpoint `.pt` sha256 `e5b1a55b...`,
    decoding config `b90432b6...`, no prompt field (E5 design sections 2.1 and 3).
  - The DEV catalog is produced under its own exposure-ledger row, written before contact.
  - The probe's plan declares each row's tool reads, and each call is receipted.

## 2. The probe (S2a.3), in the CONV / KPROBE style

**Question.** Take the A2 arm's not-in-supply MISSING items on DEV-2000-ADDED. What share does the Solver recover to
an EXACT delivered item when it is offered the tool, net of what a re-flight without the offer recovers?

**Roster.** It is derived offline, and the runtime sees ids only. A new `scripts/analysis/slurp_s2a_probe_roster.py`
imports the S1 driver's functions unchanged. As a stop check it reproduces S1's A2 counts: MISSING 188 items on 168
rows; not-in-supply 80 items, oracle 4.4287 pp. It then writes:

- **Stratum P:** the sample ids of the DEV-2000-ADDED rows that carry at least one of the 80 items. That is at most 80
  rows; about 71 are expected at S1's ratio of 188 items per 168 rows, and the script gives the exact count.
- **Stratum R:** 80 rows drawn from the remaining DEV-2000-ADDED ids in `sha256(seed, sample_id)` order. The seed is
  fixed in the derivation. The draw itself reads no gold; the exclusion of P does, and this is disclosed.
- **The committed `roster-derivation-v1.json`:** counts, the id-list sha256 and the split identity only.

The item-to-row map and each item's slot type stay on the scoring side, under `$SPEECHRL_DATA_DIR/analysis/`. **The
runtime receives the id list and nothing else**: no type, no hint, no per-row field.

As with CONV and KPROBE, THE P STRATUM IS SELECTED USING GOLD, OFFLINE. The cell is therefore constrained:

- It is `form-proof` by size (rule 5: under `MIN_BENEFIT_ROWS` of 200).
- `claims_benefit` is false, and it declares no admission mode.
- No pooled or roster-level number is ever read off it.

**Arms.** Both arms fly in one chain on the same roster, from the A2 fragment
(`configs/experiment/slurp-native-stage3-comp1b-dev2000-added-v1.json`, scorer `slurp-slu-official`). They differ in
one factor:

- **Offer:** the Solver renders the tool. This is the module component of section 4 in its offer state.
- **Twin:** no tool, request-identical to A2.

The twin replaces CONV's "sealed comparator, never re-flown". For slots, a re-flight recovers some MISSING items by
decode variance alone (A2 has 188 MISSING, its A/A 197). The conversion is therefore read **paired per item, offer
minus twin**, not against the sealed A2 column.

**Measured quantities.** The official scorer runs once per complete manifest, and gold is used only after delivery.

| quantity | stratum | definition |
| --- | --- | --- |
| call rate | P, R | Solver visits with a call / offered visits; also per row |
| decline rate | P, R | offered rows with no call; on R, a decline is the correct act |
| empty rate | P, R | calls returning `candidates: []` |
| type accuracy | P | calls whose `slot_type` equals the type of a missing item on that row |
| P(gold in candidates \| called with the item's type) | P | the tool's runtime recall |
| P(delivered EXACT \| gold in candidates) | P | the Solver's uptake (the CONV analogue measured 0.457) |
| **net conversion c** | P | (items EXACT in offer - items EXACT in twin) / 80, paired per item; Wilson CI95, with the exact Clopper-Pearson interval beside it |
| harm | P, R | offer minus twin: spurious entities added, EXACT items lost, intent rows differing (expected 0) |
| cost | both | contacts per row, `context_fit.compacted_contacts`, GPU-h |

**Size.** n = 80 items (stratum P). Wilson half-widths are:

- +/-0.093 at c = 0.25;
- +/-0.10 at c = 0.33 (27 / 80 gives [0.244, 0.446]);
- +/-0.107 at c = 0.50.

The paired offer-minus-twin difference adds about +/-0.01-0.02 at plausible discordance. On R (n = 80 rows) the call
rate is read to about +/-0.07-0.11.

**Declared expectation.** Decision 139: the probe declares its expectation, and dispositions are discussed on the
number.

- **Basis (S1 section 3).** 80 items, 4.4287 pp in total, so 0.0554 pp per item isolated; 1.5 pp = 26.5 converted
  items (S1).
- **Plausible band, by analogue only.**
  - M1 (0.2471) gives 1.09 pp.
  - Containment × M1 gives 0.82 pp.
  - Containment 0.7513 × CONV's uptake 0.457 bounds a well-typed call at about 0.34 per item, even at a 100 % call
    rate on P.

**Reading thresholds.**

- **(a) What would predict >= 1.5 pp for S2c.** Both must hold:
  - net conversion c >= 27 / 80 (0.3375);
  - the whole-roster prediction is >= 1.5 pp.

  The prediction is the exact in-process official re-score of A2's sealed column after two adjustments: the P-stratum
  offer-minus-twin entity deltas are applied as measured, and the R-stratum deltas are scaled by
  (1,000 - |P|) / 80. Control harm is therefore netted, not ignored.
- **(b) What would close the line on this source.** Either of these:
  - the Wilson CI95 upper bound of c is below 0.33 (c <= 18 / 80);
  - c is at or below M1's 0.2471 (<= 19 / 80), so the tool adds nothing a printed exemplar does not.
- **In between (19-26 / 80).** The number goes to the owner as read. Nothing is pre-committed.

**S2a.1 precondition (zero contacts, before S2a.2).**

- Run the tool deterministically over the existing Fold A catalog on the 70 not-in-supply MISSING items of COMP-1b
  Fold A (S1 table, arm c). The gold type is supplied offline, on the scoring side.
- Measure T, the share of those items whose gold value is among the returned candidates.
- Measure the tool's false-candidate rate on Fold A rows that have no MISSING item.
- Because c <= T × uptake, a T below about 0.72 (0.33 / 0.457) would make (a) unreachable at the CONV uptake. That
  number is read with the owner before the DEV tool pass is requested.

**GPU-h.**

- **Per-row basis.** DEV A2 flew 1,000 rows at 1.6955 GPU-h and 4.05 contacts per row
  (`docs/results/2026-09-30-slurp-a2-comp1b-dev2000-read.md` section 1). That is 0.0017 GPU-h per row at full-flight
  efficiency. Small probes run at about twice that (CONV: 0.24 GPU-h on 70 rows).
- **The probe (S2a.3).** Two arms × about 151-160 rows, plus at most two calls per offer row: **about 0.6-1.1 GPU-h,
  cap 2.0**.
  - The contact ceiling is (11 + 2) × rows on the offer arm plus 11 × rows on the twin: about 3,900.
  - About 1,400 contacts are expected.
- **The DEV tool pass (S2a.2).** E5-0 over all 1,000 DEV-2000-ADDED rows takes about 0.15 GPU-h in the
  serving-restart gap, or about 4 h on CPU. The GPU basis is Fold A's roughly 10 min wall per 1,080 rows (E5 design
  section 5). Covering all 1,000 rows, not only the ~160, is proposed because S2c's DEV read needs the same catalog.

## 3. The row-206 gate, as the E5 design states it (addendum, "Pre-declared gate")

1. **The call rate lies within a band.** Calls per offered row must fall in [max(0.01, 0.5 b), min(0.50, 4 b)], where
   b is the oracle base rate, frozen before the flight. Below the band the offer is inert. Above it the model calls by
   reflex, "the system-default form by another name".
2. **Decision precision exceeds the base rate by a margin.** Precision must be >= b + 0.10 and >= 2 b. Its
   paired-cluster bootstrap CI95 (cluster `sample_id`, 10,000 draws, seed 20260807) must have a lower bound above b.
   Recall is reported but not gated.
3. **Conversion clears the floor, with no harm.**
   - The SLU-F1 delta carried by the called rows, over the whole roster, is >= +1.49 pp with CI95 lower bound > 0
     (same-flight; 2.5 pp cross-flight at n = 1,080).
   - The whole column shows no measured SLU-F1 loss.
   - 0 intent rows differ.

For the proposal tool, b = the rows carrying a contained not-in-supply MISSING item, over all rows.

The probe cannot read this gate, because P is gold-selected. What it does instead:

- It **predicts** parts 1 and 2 by reweighting the P and R call rates to the 1,000-row population.
- It predicts part 3 through section 2's prediction.
- The gate itself is read by S2c, on the full roster.

The E5-1 wider label on Fold A has b 0.1231 and a cross-fit precision of 0.2455 at 10 %. That meets b + 0.10 but not
2 b, which is why the 2 b clause is expected to bind.

## 4. Module component, and carrier transfer (decisions 195, 196)

**The component: `tool-offer:missing-slot-proposal`.**

- **Plane:** "OBS evidence offered to USE; Solver slot-value step".
- **Legal states:** `off`, `column` and `on`, never `shadow`. Module design section 2d: an offer the model cannot see
  is not an offer.
- **Catalogue entry:** added to `rails/consumption_module.py` `COMPONENT_CATALOGUE` with `pending` until it is built
  (the `supply-abstain` pattern).
- **Why the probe cannot be a column today:**
  - `column` compiles only to Perception branches;
  - Solver `supply_variants` cannot reach tool authority (`rails/supply_variants.py` docstring).
- **The probe's offer arm** is therefore one of two things:
  - a one-factor module cell, with the component `on` in a probe-scoped block that the delivered path refuses until
    admission;
  - or, if that build is not done, a derived fragment on the CONV precedent.
- **After a NOMINATED S2c,** the state becomes `on`, with `admitted_by` naming the S2c read.
- **All-off arms** render no tool, so the AT-M0 bytes are unchanged.

**The carrier hook.** A new `CarrierHooks.tool_offer_slot_types`, a sibling of `tool_offer_units`. Per carrier it gives
the closed argument enum and the "not covered by the draft" test.

**Audio2Tool.**

- `slot_type` = the string-typed parameters of the draft call's selected function that the draft left absent. Enums
  and numerics stay with `a2t-toolcall` grading.
- Source: the A2T clip transcript, from the same E5-0 producer.
- Lexicon: train-side parameter values.

**Earnings-21 / -22.**

- `slot_type` is one of the ConEC entity categories, or numeric.
- "Missing" means a value in the window transcript that the core's delivered text lacks.
- The 90-s windows exceed Whisper's 30-s limit. Spans therefore come from MMS_FA-timed recuts through
  `saea-tool-slice-encode-v1`, under a declared derived root (E5 design section 4).

Per carrier, only the adapter hook, the catalog producer, the lexicon and the config fragments change. No GPU runs on
either carrier before the SLURP lock (decision 211).

## 5. What is NOT decided here (owner items)

1. **The scope of decision 201's transcript exception.** 201 (coordinator ruling Q1) admits transcripts only for
   post-delivery entity-value checks, never into the Solver prompt. The E5 addendum then offered a span at the
   Solver's slot-value step. A proposal tool goes further: it puts transcript spans into the Solver's context as
   **candidate values**. This needs an explicit owner row, and nothing in S2a.2 or S2a.3 proceeds without it.
2. **The DEV-2000-ADDED E5-0 pass.** It needs a new `speech-tool` ledger row, because 201 opened Fold A and Fold B
   only.
3. **A second, stronger ASR tool.** This is v6's decision 212 (S2b). S2a uses only the pinned Whisper large-v3.
4. **The fold discipline of the probe roster.** P and R are DEV-2000-ADDED rows, the roster of A2 and of the proposed
   S2c read, so the probe's rows would be re-flown inside S2c. The alternatives are:
   - fly the probe on COMP-1b Fold A (70 items, transcripts on file, no DEV pass needed) and keep DEV for S2c;
   - or exclude the probe's P and R ids from S2c's read.
5. **The build choice for the offer arm:** a Solver-node module column, a probe-scoped `on` block, or a derived
   fragment.

## 6. Risks

- **The self-proof trap (206).** If the gain appears only when the Solver calls on nearly every row, the system is
  "ASR + LLM" by another name. The guards are:
  - an offer only, at one Solver node;
  - decline and empty are both legal;
  - the call-rate band's upper edge, min(0.50, 4 b);
  - the R stratum, which measures reflexive calls on rows with nothing missing;
  - `used_in_answer`, computed from bytes, never from the model's claim.
- **Gold leakage paths.**
  1. The roster: only ids reach runtime; types and item maps stay on the scoring side.
  2. The type lexicon: built from the TRAIN split only, asserted to hold no devel or test record, and never built from
     S1's 80 values.
  3. The abstain threshold: fitted on Fold B only, never on Fold A or DEV.
  4. The transcript: the E5-0 decode config has no prompt, and the wrapper imports no `data.slurp` label function (an
     AST check in `tool_catalog_check.py`; E5 design section 3). SLURP's reference transcript is never a catalog.
  5. The S2a.1 recall read and the S2c prediction use gold offline only.
  6. The test split stays closed.
- **Intent leakage.** Spans can carry intent-bearing words; the 2026-09-12 fixed-transcript supply cost intent -0.90
  [-1.68, -0.09]. The mitigations are bounded spans, the draft-overlap filter, and "intent rows differing" read on both
  strata. S2c's gate requires 0.
- **Contact budget.**
  - Paid API spend is 0.
  - Each call is one more core contact inside the Solver's ReAct episode, counted in the run-cumulative plan budget.
    The loader computes the ceilings.
  - At most one recovery re-registration. A second failure closes the cell, and the fix is proven on a four-row dry
    run.
- **Containment.** At 0.75 the tool cannot reach a quarter of the targets, and `business_name` and `person` are worst.
  That is the S2b (212) question, not a reason to widen this tool.
