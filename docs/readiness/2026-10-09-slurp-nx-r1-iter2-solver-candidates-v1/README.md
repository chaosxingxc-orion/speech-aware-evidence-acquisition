# NX R1 iteration-2 Solver instruction-template candidates v1 (SLURP, Stage 3): five hand-written arms from the iteration-1 column read

**Status: CANDIDATES ONLY.** Nothing is registered, re-pinned, flown or admitted. Author: Claude Opus 5.5 (candidate
author), 2026-10-09, branch `fable/nx-r1-iter2-candidates` (base master `93e863031`). Every candidate is labelled
**`author: hand (Opus 5.5 from aggregate tables)`** (programme C0.5 / C3). The label lives here only, because a phase
template is sent to the model byte for byte (`rails.phase_material.render_static_instruction`).

**Contacts: zero.** No model, server, tokenizer, scorer, GPU or network contact. No utterance text, transcript, gold
value, filler or model output was read, printed or persisted. Inputs were aggregate tables only (owner directive
2026-10-09: template-based learning from statistics, never per-sample review):
`SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-NX-R1-SOLVER-FOLD-B-COLUMN-READ-V1/node-local/tables.md` and
`report.json` (marginal rates, paired discordant counts, per-slot-type counts per arm), plus the iteration-1 README
`docs/readiness/2026-10-09-slurp-nx-r1-solver-candidates-v1/README.md`, the exchange-rate note
`docs/results/2026-10-09-slurp-nx-exchange-rates-offline.md` and programme
`docs/readiness/2026-10-09-slurp-nx-node-extreme-programme-v1.md` (C0.4, C2 R1, C3, F1).

## 1. What iteration 1 showed (TRAIN Fold B, 1,080 rows: 392 empty-gold, 688 non-empty; paired vs `lock`)

| arm | exact_set pp [CI95] | b / c | empty-gold stratum net rows (fixed - broken) | non-empty stratum net rows (b - c) | screen |
| --- | --- | ---: | ---: | ---: | --- |
| r1-c5 contract + conventions | +2.50 [+1.02, +4.07] | 50 / 23 | +12 (24 - 12) | +15 (26 - 11) | PASS |
| r1-c3 empty decision | +4.63 [+2.87, +6.48] | 74 / 24 | +62 (64 - 2) | -12 (10 - 22) | FAIL (non-empty -1.74 [-3.34, -0.15]) |
| r1-c2 copy suppression | +1.11 [-0.28, +2.59] | 38 / 26 | +7 (18 - 11) | +5 (20 - 15) | unresolved |
| r1-c4 donor port | -0.19 [-1.76, +1.30] | 35 / 37 | -7 | +5 | no |
| r1-c1 value-in-supply | -1.85 [-3.43, -0.37] | 24 / 44 | -31 | +11 | HARM |
| aa twin | +0.00 [-0.74, +0.74] | 9 / 9 | -1 | +1 | null |

Stratum nets are derived from the table's discordant counts: on empty-gold rows a raw-exact row is exactly a row
without a false fill, so the arm-only exact rows equal the false-fill `c` column and vice versa; the two strata add up
to the exact_set `b - c` for every arm.

**Where c3 lost its non-empty rows (per-slot-type, c3 minus lock, gold items).** MISSING +49 in total, concentrated in
date +11 (exact -7), media_type +7 (exact -3), event_name +4, business_type +3, time +3, transport_type +3 (exact -3),
weather_descriptor +2 (exact -3), device_type +2, food_type +2, place_name +2. These are short, operation-adjacent
values: the arm's "decide first whether any value beyond the operation words was spoken" step, backed by the N1
prior, classified them as operation words. Its SPURIOUS reduction (-82 items) is broad: device_type -10, food_type
-7, list_name -6, media_type -5, place_name -5, date -4, house_place -4. So media_type and date sit on both sides,
and a type-blind gate cannot separate them; the gate has to act on whether the value was heard, at extraction time.

**Where c5 gained (c5 minus lock).** gold_wrong -36, gold_exact +22, MISSING +14, SPURIOUS -7: the gain is mainly
wrong-filler -> exact (person +5 exact / -6 wrong, place_name +5 / -6, food_type +4 / -5, event_name +2 / -3, time +2
/ -2, news_topic, relation, business_name +2 each). That is the surface form of the filler, i.e. the conventions
block, not the strict JSON contract (parse validity +3 rows only). The +14 MISSING (business_type +3, date +4,
media_type +3) is a small leak in the same operation-adjacent types that c3 lost.

**Calibration of iteration-1 predictions.** Declared vs measured raw-exact rows: c1 +32 vs -20, c3 +35 gross vs +50,
c5 +5 vs +27, c2 +11 vs +12. Conversion-based author priors were badly calibrated. Iteration 2 therefore predicts from
the measured iteration-1 discordant counts (section 2), not from the exchange-note conversions.

## 2. Prediction method (applies to every candidate)

1. **Component nets.** Each candidate is composed of iteration-1 components; its predicted net raw-exact rows per
   stratum are built from that component's measured net (table above) times a stated retention factor, which is the
   author's prior, not a measured conversion.
2. **Winner's-curse shrink.** c3 and c5 were picked as the two best of five arms on the same roster, so each source
   net is shrunk by half its paired standard deviation, sqrt(b + c) / 2: c5 4.3 rows, c3 4.9, c2 4.0 (applied once
   per candidate as about 4-5 rows).
3. **Roster reuse.** These candidates were shaped on Fold B tables and are to be read on Fold B again; the shrink is a
   partial guard only. The once-per-lock Fold A two-arm confirmation (programme C0.6) is the real guard.
4. **Conversion to pp of official pooled SLU-F1.** Uniform node rate **+0.056 pp per raw-exact row** (the brief; the
   exchange note gives 0.0563 Fold A). Class-split sensitivity: an empty-gold row made exact is an emptied false-fill
   row, worth **0.0333 pp** (exchange note); a non-empty row **0.0563 pp**. Both are reported; the class-split figure
   is the conservative one.

## 3. The candidates

All files are complete replacements of the Solver instruction (no placeholder; the locked file has none), ASCII,
LF, one trailing newline, no word "tool", no example utterance and no slot value. Iteration-2 files keep the locked
P1 (intent resolution) byte-identical, as iteration 1 did. On the review-off NX base (programme F2) the Solver is
never revisited, so the revision paragraph is inert; it was dropped where the 230-word ceiling required it (i2-c1,
i2-c2, i2-c3, i2-c4) and kept in i2-c5 so that the ablation changes one component only.

### r1-i2-c1 -- c5 + empty decision gated on heard values (`configs/probes/nx/solver/r1/r1-i2-c1.txt`)

- **author:** hand (Opus 5.5 from aggregate tables).
- **Target class:** EMPTY-GOLD-FILL (c3's +62-row empty-stratum gain) without c3's non-empty MISSING loss (date,
  media_type, event_name, business_type, time, transport_type).
- **Mechanism hypothesis (one line):** making the empty answer the model's own decision taken AFTER extraction, and
  naming the short value kinds that c3 misread as operation words as values to keep, keeps most of c3's false-fill
  reduction while no heard value is dropped (decision 199: empty is legal, nothing is deleted by the system, the
  model decides).
- **Prediction (Fold B):** empty stratum: retention 0.5 of c3's +62 = +31 (floor c5's +12); non-empty: c5's +15 minus
  a residual quarter of c3's -12 = +12. Gross +43, shrink -5: **+38 raw-exact rows**, **+2.13 pp** at the uniform rate,
  **+1.51 pp** class-split. Range [+15, +61] rows (gate kills the empty effect and leaks c3's loss / gate keeps 0.75 of
  the empty effect with no loss). Expected to pass the mechanical screen; the non-empty secondary is the risk.
- **Words:** 221. **sha256:** `45b3d55aa125d42c0008a19314fe8a6be309575bc8b68ab3ef001ce7485cc9d3`
- **Diff vs iteration 1:** r1-c5 with (a) the revision paragraph removed, (b) the P3 sentence "Do not invent a missing
  value from knowledge, a slot name, or a candidate distinction." removed and replaced by "Never invent an unheard one."
  at the end of the new block, (c) the empty clause of P3 ("If no entity is expressed, entities is an empty array.")
  replaced by a new block: empty is legal and the model's own decision, made after extraction; operation words are
  not entities; a spoken day, date, time, place, name, event, condition, or kind of media, device or vehicle is a
  value to keep. Differs from c3: no "first decide" step, no N1 prior, decision ordered after extraction.

### r1-i2-c2 -- c5 + a softer empty rule (`r1-i2-c2.txt`)

- **author:** hand (Opus 5.5 from aggregate tables).
- **Target class:** EMPTY-GOLD-FILL, with a stricter non-empty guard than i2-c1.
- **Mechanism hypothesis (one line):** a single-sentence empty rule inside the extraction paragraph (empty only when
  the speech names nothing beyond the operation words; never when a value of a type the supplied examples annotate was
  heard) moves fewer rows than c3 but cannot fire against a heard exemplar-typed value.
- **Prediction (Fold B):** empty stratum retention 0.35 of +62 = +22; non-empty +15 - 1 = +14. Gross +36, shrink -5:
  **+31 rows**, **+1.74 pp** uniform, **+1.31 pp** class-split. Range [+24, +46].
- **Words:** 230. **sha256:** `656a0aa579c7ca198621a1449a748e8ab9c2535f7c5f836f4dd3e1807d7a34ea`
- **Diff vs iteration 1:** r1-c5 with two sentences appended to P3 ("Words that only name the requested operation are
  not values: when the speech names nothing specific beyond them, entities is an empty array. Never return it empty
  when you heard a value of a type the supplied examples annotate.") and the revision paragraph removed. Contract and
  conventions byte-identical to c5.

### r1-i2-c3 -- c3 + c5's filler conventions (`r1-i2-c3.txt`)

- **author:** hand (Opus 5.5 from aggregate tables).
- **Target class:** the test of whether c3's non-empty loss is recoverable by surface conventions alone.
- **Mechanism hypothesis (one line):** c3's non-empty loss is MISSING (operation-adjacent values judged as operation
  words), not WRONG; conventions fix wrong fillers, so they should add c5-like wrong -> exact gains on the rows c3
  still fills but leave the MISSING loss in place (expected outcome: the non-empty secondary moves from -12 toward
  about -3 rows, not to zero or above).
- **Prediction (Fold B):** empty stratum 0.9 of +62 = +56 (conventions do not touch the empty decision; slight
  dilution by length); non-empty: -12 + 9 (two thirds of c5's +15 carried by conventions, scaled by c3's 87 % item
  volume) = -3. Gross +53, shrink -5: **+48 rows**, **+2.69 pp** uniform, **+1.54 pp** class-split. Range [+38, +65].
  Screen risk: the non-empty CI likely straddles zero; a repeat of -12 would fail it again.
- **Words:** 230. **sha256:** `bcfbc69f363215195a5a553fd542115461c88977c6b2464038e6fbca111dd3f8`
- **Diff vs iteration 1:** r1-c3 with (a) c5's conventions block added verbatim, (b) the revision paragraph and "Add
  nothing outside the task JSON." removed, (c) "preserving their spoken surface forms" removed from P3 (now covered by
  the conventions' "as spoken"), (d) the word "itself" removed from "the requested operation itself", (e) the
  "Knowledge associations ..." sentence already absent in c3. The c3 empty-decision paragraph is otherwise
  byte-identical (decision-first step and N1 prior kept on purpose).

### r1-i2-c4 -- c5 + c2's heard-span requirement (`r1-i2-c4.txt`)

- **author:** hand (Opus 5.5 from aggregate tables).
- **Target class:** the remaining copied-spurious mass under c5 (c5 SPURIOUS 7 items below lock only; c5 per-type
  spurious still high on list_name 13, media_type 16, business_name 13, person 14, place_name 15).
- **Mechanism hypothesis (one line):** printed knowledge values treated as unheard until confirmed, plus one
  contiguous heard stretch per entity, remove copy-transferred spurious entities on top of c5's surface-form gain;
  "keep a heard value no example shows" guards MISSING.
- **Prediction (Fold B):** c5 +27 plus half of c2's +12 (overlap with c5's own suppression): empty +15.5, non-empty
  +17.5, gross +33, shrink -5: **+28 rows**, **+1.57 pp** uniform, **+1.27 pp** class-split. Range [+20, +39] (c2's
  non-empty CI included a loss).
- **Words:** 229. **sha256:** `60e90ef34ac0207487da7339a75ee9ee2510d7185c17a6d20f5ac5306c686180`
- **Diff vs iteration 1:** r1-c5 with (a) the P3 "Do not invent ..." sentence replaced by the new block, (b) a new
  block between P3 and the conventions, compressed from c2: "Treat every printed knowledge value as unheard until the
  current speech confirms it; annotated examples belong to other speakers' requests. Every entity must rest on one
  contiguous stretch of this speech that says it. Keep a heard value no example shows; invent nothing.", (c) the
  revision paragraph removed.

### r1-i2-c5 -- ablation of c5: contract tightening removed (`r1-i2-c5.txt`)

- **author:** hand (Opus 5.5 from aggregate tables).
- **Target class:** attribution of c5's +2.50 pp (FORMAT / surface form vs output contract).
- **Mechanism hypothesis (one line):** the per-slot table says c5's gain is wrong -> exact filler surface form, so the
  conventions block carries it and the strict-contract paragraph (one object, braces, no surrounding text, exact keys,
  label-spelling rule) is the weakest part; removing it should keep most of the gain.
- **Prediction (Fold B):** empty stratum +10 (c5's +12 is kept if it came from dropping the "Knowledge associations
  ..." sentence, which i2-c5 also lacks), non-empty +10 (two thirds of +15), gross +20, shrink -4: **+16 rows**,
  **+0.90 pp** uniform, **+0.72 pp** class-split. Range [0, +27]. Reading rule: >= about 20 rows means the
  conventions carry c5; near 0 means the contract did; parse validity is expected to fall back toward lock (c5 +3
  rows).
- **Words:** 181. **sha256:** `0463a4978021e595a1d3310751ad91f06d6716661103cb6e7dd6a01a7e10d0cf`
- **Diff vs iteration 1:** r1-c5 with P2 reverted to the locked "Return only:" plus the shape line (the two contract
  sentences removed), the first P3 sentence reverted to the locked "Use the scenario/action pair belonging to the
  selected candidate and entity types from the full legal inventory." Conventions block and revision paragraph
  byte-identical to c5. Single-component ablation.

## 4. Round summary and declared effect (decision 192 form, before any flight)

| arm | target class | predicted raw-exact rows (gross -> shrunk) | pp uniform 0.056 | pp class-split | range (rows) | words |
| --- | --- | ---: | ---: | ---: | --- | ---: |
| lock v2 (delivering) | -- | 0 | 0 | 0 | -- | 160 |
| r1-i2-c1 | empty-gold fill, gated | 43 -> **38** | +2.13 | +1.51 | [+15, +61] | 221 |
| r1-i2-c2 | empty-gold fill, soft | 36 -> **31** | +1.74 | +1.31 | [+24, +46] | 230 |
| r1-i2-c3 | c3 + conventions (loss test) | 53 -> **48** | **+2.69** | **+1.54** | [+38, +65] | 230 |
| r1-i2-c4 | copied spurious on c5 | 33 -> **28** | +1.57 | +1.27 | [+20, +39] | 229 |
| r1-i2-c5 | c5 ablation (contract out) | 20 -> **16** | +0.90 | +0.72 | [0, +27] | 181 |

**Round-2 declared effect: +2.69 pp official pooled SLU-F1 at the uniform node rate (+1.54 pp class-split), carried by
r1-i2-c3 alone (+48 raw-exact rows on Fold B).** The class-split figure is the conservative one and the one to compare
with the provisional floor 1.49 pp (it sits at about 1.03 x the floor). The author expects r1-i2-c1 (+38 rows,
+2.13 / +1.51 pp) to be the arm that clears the mechanical screen, because r1-i2-c3 keeps c3's decision-first step and
is predicted to leave a non-empty deficit (about -3 rows). Plateau rule (C0.4): R1 iteration 1 had a NOMINATION
candidate on the node screen (r1-c5), so the plateau counter depends on that arm's full nomination read (intent guard
and official SLU vs the twin bar), not on this file.

## 5. Notes for the cell author

- Same mechanics as iteration 1 (section 5 there): the arms change only the Solver instruction bytes; task context
  `slurp_native_role_context_v3.txt`, supply, decoding, `max_tokens` 512 and no `response_format` stay locked.
- Recommended column: these five arms + `aa` + `lock` on Fold B (K = 7, as in iteration 1). Including r1-c5 as an
  eighth reference arm would let i2-c1/i2-c2/i2-c4/i2-c5 be read against c5 directly; the programme caps candidates at
  K <= 6 per round, so that is a cell-author choice, not part of this declaration.
- Secondaries to tabulate: the per-slot-type MISSING delta on date, media_type, event_name, business_type, time,
  transport_type (i2-c1, i2-c2, i2-c3); per-type spurious on list_name, media_type, business_name, person, place_name
  (i2-c4); parse validity and gold_wrong (i2-c5).
