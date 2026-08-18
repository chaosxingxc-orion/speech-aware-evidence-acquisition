# P-SLU Stage-2 verdict — Q-A: KNOWLEDGE-BEYOND-FORMAT; Q-B: SELF-SCOPING-WORKS (registered one-shot read, 2026-08-18)

Mechanical outcome per the registered independent verdicts
(`docs/readiness/2026-08-18-pslu-s2-preregistration-REGISTERED.md` §1, verbatim), computed by the
pinned offline read suite (`speech_aware_evidence_acquisition.analysis.pslu_s2_read` at study HEAD
`5699ab8`; 22/22 unit tests green immediately before the read, clean tree, flight-archive
MANIFEST sha256-verified) over the single COMPLETED attempt `attempt-20260818T200339Z-80119a`
(183 rows = F1 60 + A1r-phase1 60 + A1'r 60 + 3 silence-swap; flight archive
`docs/checks/speech-aware-evidence-acquisition/2026-08-18-pslu-s2-flight/`). Read archive:
`docs/checks/speech-aware-evidence-acquisition/2026-08-18-pslu-s2-read/` (`verdict.json`,
`report.txt`, `MANIFEST.sha256`). The suite ran exactly once; the exposure row
`SAEA-PROBE-pslu-s2-183` flips to consumed in the same commit. Parent: the consumed P-SLU read
(`d8b71a5`, `docs/readiness/2026-08-18-pslu-verdict.md`), whose §8.6 and §9 prescribed exactly
these two arms. A0 (0.1741), A2 gain (+0.2946), A3 (0.5961), and A4 gain (+0.1346) are **CITED**
from that consumed read throughout — never re-flown; the parent's §4 duplicate-condition floor
bounds re-fly drift at ~±0.013 and its separability bar is 0.03.

The suite's module docstring carries seven numbered engineering-interpretation notes; they were
reviewed and approved before the read and are cited here by number, never re-litigated. Note 1
documents that, given the registered thresholds and the literal cited comparators,
**INCONCLUSIVE-QA is mathematically unreachable** (FORMAT-FLOOR-CONFIRMED's met-boundary 0.2787
lies below KNOWLEDGE-BEYOND-FORMAT's not-met-boundary 0.4961, so every real F1 value fires at
least one clause) — a checked property of the registered thresholds, documented rather than
silently special-cased.

## 1. Mechanical outcome (VOID first, then both questions)

**Q-A: KNOWLEDGE-BEYOND-FORMAT** (alone — the clauses may co-fire; only one fired).
**Q-B: SELF-SCOPING-WORKS.**

| Gate / clause | Result | Deciding numbers (margin) |
|---|---|---|
| VOID (checked first, gates both) | **not met** | 0 of 3 silence-swap answers persisted; 0 recheck mismatches; 0 harness defects |
| Q-A FORMAT-FLOOR-CONFIRMED (F1 gain vs A0 >= +0.1046) | **not met** | gain **−0.0385** — short by **0.1431**; the filler roster did not reproduce any of A4's cited +0.1346 |
| Q-A KNOWLEDGE-BEYOND-FORMAT (A3 − F1 >= 0.10) | **MET** | gap **+0.4605** — clears the floor by **+0.3605** (>15x the separability bar) |
| Q-A FORMAT-IS-EVERYTHING (A3 − F1 <= 0.03) | **not met** | gap +0.4605 vs ceiling 0.03 — exceeded by 0.4305 |
| Q-B SELF-SCOPING-WORKS (non-fallback >= 50/60 AND gain >= +0.2646) | **MET** | non-fallback **60/60** (floor 50, margin +10); gain **+0.4352** (floor +0.2646, margin **+0.1706**) |
| Q-B SELF-SCOPING-FAILS (non-fallback < 30/60 OR gain < +0.1946) | **not met** | 60/60 vs <30; +0.4352 vs <+0.1946 (above by +0.2406) |

One registered-semantics note, stated plainly: KNOWLEDGE-BEYOND-FORMAT was written as "value
knowledge survives against the schema-primed floor", assuming F1 would land *above* A0 as that
floor. F1 instead landed marginally **below** the cited A0 (−0.0385), so no schema-primed floor
materialized at all — the clause fires with an even stronger reading: format-shape priming
contributes approximately nothing, and the entire legal-supply gain is content-borne (§5).

## 2. Every ingredient number

Per-arm aggregates, exactly as the pinned suite wrote them (n=60 per arm, silence-swap rows
excluded from every aggregate; Δ columns are against the **CITED** A0 SLU-F1 0.1741 /
slot_f1_exact 0.0435):

| Arm | Supply | SLU-F1 | Δ vs A0 (cited) | P | R | slot_f1_exact | Δ | P | R | intent acc | copy-rate | induced subs |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| F1 | 100-entry synthetic filler roster (format-matched control) | 0.1356 | **−0.0385** | 0.1400 | 0.1315 | 0.0116 | −0.0319 | 0.0120 | 0.0112 | 0.0000 | 0.0000 (0/6000) | 0 |
| A1r-phase1 | 18 canonical scenario labels (closed-set choice; descriptive only) | 0.1287 | −0.0454 | 0.1447 | 0.1158 | 0.0503 | +0.0068 | 0.0571 | 0.0449 | 0.1167 | 0.0000 (0/0) | 0 |
| A1'r | self-scoped scenario roster via chosen canonical label (**legal**) | 0.6093 | **+0.4352** | 0.5919 | 0.6278 | 0.4891 | +0.4456 | 0.4737 | 0.5056 | 0.0000 | 0.0000 (0/2177) | 2 |

Cited comparators from the consumed parent read (same 60 samples, same decode config; drift bound
~±0.013): A0 0.1741 / 0.0435; A2 0.4686 (+0.2946) / 0.2486; A3 0.5961 (+0.4220) / 0.5000;
A4 0.3087 (+0.1346) / 0.1899; A1 ceiling 0.6340 (+0.4599) / 0.5246.

- The A1r-phase1 row is a scenario-choice response scored descriptively for completeness — it is
  not a claim-bearing SLU answer. Its intent accuracy 0.1167 (7/60 exact scenario+action) is the
  only non-zero intent cell this study has recorded on this vehicle, a direct consequence of
  phase-1 supplying canonical scenario labels; F1 and A1'r remain 0.0000 under the parent §8.5
  label-space degeneracy, and intent accuracy is reported-only (suite note 3, no guardrail
  registered).
- Copy-rate is **reported-only, no clause** (registration §2; suite note 2), and carries the
  parent's §8.3 shape caveat verbatim: the classifier marks `copy` only on a contiguous verbatim
  token subsequence, which `"{type}={value}"` items essentially never produce in a JSON response
  — the 0.0000 rates must not be read as "no copying". That said, F1's 0/6000 filler-item
  comparisons together with its 0 induced substitutions support the narrower safety observation
  that the core did not parrot synthetic filler content into answers.
- Induced substitutions: A1'r **2** against a **+41** entity-TP gain (cf. parent A3: 3 against
  +44); F1 0 (vacuous-adjacent: its filler values overlap no gold value by construction, but a
  filler value in an answer would have counted — none did).

### Per-sample TP/FP/FN totals (summed over the 60 samples of each arm)

Entity exact-match ledger; TP+FN = **89** in every arm, reproducing the registered 89 gold slots:

| Arm | TP | FP | FN | entity-TP gain vs A0 (cited TP 4) |
|---|---|---|---|---|
| F1 | 1 | 82 | 88 | −3 |
| A1r-phase1 | 4 | 66 | 85 | ±0 |
| A1'r | 45 | 50 | 44 | **+41** |

### Supplied-item audit (suite note 7)

- F1: exactly **100** items on every one of 60 calls (the registered filler dose).
- A1'r: mean **36.28**, range **19–40**, over 60 calls — scenario-scoped roster sizes matching the
  parent's gold-scoped A1 (mean 37.1, range 19–40), i.e. roughly **one third of A3's 100-entry
  dose**.

### Integrity

- Flight status `COMPLETED`, error `None`; 183/183 requests, 0 failures.
- **Recheck: 0 mismatches** — every row's recomputed TP/FP/FN and parsed answer matched its
  embedded metrics exactly.
- **Harness defects: none** — arm/sample completeness, no duplicate rows, silence-swap rows
  present on A1'r only, every F1 prompt byte-equal to the reconstructed fixed filler packet, and
  every A1'r phase-2 prompt byte-equal to `pslu_supply_packet("A1p", scenario=<mapping re-derived
  from the phase-1 sibling's own response text>)` (suite note 6 — this check also proves the
  embedded mappings agree with the responses they claim to summarize).

## 3. Silence-swap (3 seeded A1'r samples, parent unanimity bar)

**0 of 3 persisted — unanimous non-persistence.** All three silence variants produced a different
parsed answer (scenario + action + entity set) from their real-audio counterpart:

| Sample | real-audio answer | silence answer | unchanged |
|---|---|---|---|
| `slurp:devel:005518:audio-1490203960` | controlling a smart device / turn off / device_type=room light | coffee shop / order coffee / business_name=starbucks, coffee_type=… | False |
| `slurp:devel:007852:audio-1494416109-headset` | Adding an event to a calendar / Add event / event_name=baseball practice, time=5 pm, timeofday=tonight | Setting a reminder for a daily task / Set a reminder / general_frequency=daily, list_name=tasks | False |
| `slurp:devel:011654:audio-1501692977-headset` | searching for restaurants / search for / business_type=restaurants, food_type=chinese, place_name=nearby | finding a restaurant for dinner / search for a restaurant / food_type=pizza, meal_type=dinner, place_name=new york, time=tonight | False |

The mandatory partial-persistence disclosure is not triggered (0 of 3, not 1 or 2 of 3). The
A1'r gain is conditioned on the audio, not on a text-only prior. The parent's safety observation
repeats exactly: under silence the core did not abstain — it emitted a confident, well-formed,
entirely invented command in all three cases (different inventions than the parent's, so the
confabulation is not even stable).

## 4. Phase-1 mapping detail (the repaired label-space boundary)

- **Non-fallback 60/60; fallback 0/60.** The parent's voiding defect (A1' fell back to A2 on
  60/60 because free-form scenario phrases never matched a canonical key) did not recur: with a
  closed-set choice over the 18 canonical labels, every phase-1 response mapped, and the
  mapping-outcome distribution is **`{exact: 60}`** — all 60 responses carried a canonical label
  verbatim (no fuzzy/normalized tier was needed).
- **Chosen label vs gold scenario (scoring-side only, reported, no clause): 0.7833 = 47/60.**
  The core's self-chosen scenario agrees with gold 78.3% of the time; the remaining 13 phase-2
  calls therefore carried a wrong-scenario roster, and the A1'r aggregate absorbs that cost while
  still reaching 0.6093 (§5).

## 5. What each verdict does to the L3 anchor's restatement (parent §9: +0.4220 / +0.1275)

**Q-A (KNOWLEDGE-BEYOND-FORMAT; FORMAT-FLOOR refuted).** The parent's §7 explanation of its own
UNRESOLVED outcome was that A0's floor is mostly a *format* floor — that most of the +0.4220 was
"a one-time format-alignment payment that a well-specified output contract or a fixed schema
preamble could plausibly buy without any retrieval, ORG, or SUPPLY machinery at all". The
format-matched control measures that payment directly and finds it **absent**: a roster
byte-compatible with A3's item shape and prompt framing, carrying 100 entries of machine-checked
zero-overlap filler, moves SLU-F1 by **−0.0385** (slot exact-match to 0.0116, entity TP from 4 to
1). Consequences: (a) the +0.4220 anchor sheds its format discount — none of it is bought by
shape; (b) the parent's schema-grounding component (A2 − A0 = +0.2946) is re-attributed from
"format alignment" to **real label-space content** (the 55 true type names), since shape-with-
fake-names buys nothing; (c) A4's anomalous +0.1346 — the gain that broke the parent's branch
lattice — is now content-borne too (a deranged roster still carries true type names and real
ontology values), which explains the UNRESOLVED outcome without the format hypothesis; and (d)
the +0.1275 value-over-types increment survives untouched as the value-knowledge component. The
anchor's two travelling numbers stand, and the follow-up hardens them: gain over the strongest
format-matched control is **A3 − F1 = +0.4605** (and A1'r − F1 = +0.4737).

**Q-B (SELF-SCOPING-WORKS).** The parent's §9 recorded "the study has no measurement of legal
self-scoping at L3" — it now has one: **+0.4352 SLU-F1** over the cited A0, at **60/60
non-fallback**, i.e. **94.6% of the gold-scoped ceiling gain** (+0.4352 of +0.4599) from a fully
legal two-phase self-scoped supply at a mean dose of **36.3 items/call — about one third of
A3's 100**. Against the comparators: +0.1406 above A2's vocabulary-parity bar (4.7x the
separability bar); +0.0132 above A3 (inside the 0.03 bar — parity with the undirected 100-entry
roster, not superiority); **−0.0247 below the A1 gold-scoped ceiling — inside the separability
bar**, so the parent's §5 ceiling premium (+0.0379) is now essentially closed by a legal
mechanism (slot_f1_exact premium remaining: 0.5246 − 0.4891 = +0.0355). The restated L3 anchor
therefore gains a third travelling number: legal supply at L3 buys +0.4220 (undirected, 100
items) or +0.4352 (self-scoped, ~36 items), of which +0.1275 is value knowledge over bare types —
and self-scoping's contribution is dose-efficiency plus the closing of the oracle-selection
premium, not a higher plateau.

## 6. Synthesis — what the parent read and this follow-up jointly establish about L3

Jointly, the two reads settle the three questions the parent left open. **The control-arm anomaly
is not format**: A4's +0.1346 cannot be reproduced by shape — a byte-compatible filler roster
scores −0.0385 — so the anomaly was ontology content in a deranged wrapper, and the parent's
branch lattice failed because its "wrong-content control" was in fact half-right-content, not
because gain is cheap to fake. **Value knowledge survives, and so does everything else in the
anchor**: with the format explanation eliminated, the entire legal-supply gain (+0.4220 A3,
+0.4352 A1'r, +0.4605/+0.4737 over the format-matched control) is content-borne, decomposing into
label-space knowledge (~+0.2946) plus value knowledge (~+0.1275), with 2–3 induced substitutions
against +41 to +44 entity-TP gains as the measured harm. **Legal self-scoping now has a
measurement**: the closed-set repair took non-fallback from 0/60 to 60/60, the core self-selects
the gold scenario 47/60 times, and the resulting scoped supply sits at ceiling-parity (−0.0247,
inside the bar) at one third of A3's dose. For the supply-benefit curve this places the L3 point
on a content plateau near 0.60 SLU-F1 reachable by at least two legal mechanisms, with the
schema-primed floor hypothesis retired: there is no floor between A0 and the plateau that format
alone can buy. Citation licenses: this row plus the parent license citing +0.4220 and +0.4352 as
legal prompt-only L3 gains with the +0.1275 value component and the −0.0385 format-control result
attached; A1'r-vs-A3 differences may not be cited as superiority (inside the noise bar); every
number is **n=60, discovery-tier, single-attempt, descriptive** — no confirmatory, superiority,
or generalization claim is licensed, and SLURP audio's CC BY-NC 4.0 non-commercial constraint is
carried on all audio-derived numbers.

## 7. Limitations and honest disclosures

1. **n = 60, descriptive only.** Point estimates on one seeded stratified sample (seed 20260807)
   from one split (`devel`, discovery), one COMPLETED attempt, single read. No p-values, no CIs.
2. **All four comparators are cited, not co-flown.** A0/A2/A3/A4 come from the consumed parent
   read; the parent's own measured duplicate-condition drift (~±0.013) bounds the re-fly risk,
   and every verdict margin here (smallest: 0.1431) is an order of magnitude above it. F1's
   −0.0385 is the one number close enough to that floor to deserve caution: it is safely a
   "no gain" result, but "format slightly hurts" is only ~1.3x the separability bar against a
   non-co-flown baseline.
3. **KNOWLEDGE-BEYOND-FORMAT fired without a schema-primed floor** (§1): the registered clause
   semantics assumed F1 >= A0; as flown, the clause's gap is measured from a control at/below A0.
   The verdict label is mechanically correct and its reading is *stronger* than registered, but
   any citation should say "vs a format-matched control that itself gained nothing", not "vs a
   schema-primed floor".
4. **INCONCLUSIVE-QA was unreachable as registered** (suite note 1) — a property of the
   registered thresholds given the cited comparators, checked and documented before the read; the
   suite implements the branch literally anyway. No equivalent defect exists on Q-B (its
   INCONCLUSIVE band 30–49 non-fallback, or gain in [+0.1946, +0.2646), was reachable).
5. **Copy-rate remains shape-blind** (parent §8.3, suite note 2): reported at 0.0000 everywhere,
   no clause anywhere, and not evidence of copy-safety on value-bearing arms. Induced
   substitutions (2 on A1'r) remain the working harm metric.
6. **Intent accuracy is degenerate on the answer arms** (parent §8.5): 0.0000 on F1 and A1'r,
   reported-only. Phase-1's 0.1167 shows the degeneracy is label-supply-driven, consistent with
   the parent's diagnosis.
7. **Phase-1 gold-agreement is scoring-side only** (registration §1): the 47/60 figure uses gold
   scenarios and never entered any runtime path; runtime saw only the core's own chosen labels.
8. **Scope.** Discovery tier, `bounded-discovery-probe`, 183 calls of 220 registered. SLURP audio
   is CC BY-NC 4.0; the non-commercial constraint travels with every audio-derived number here.
   Rosters are train-split-mined only; the filler lexicon is synthetic with a fail-closed
   zero-overlap binding check — all legal-tier arms remain legal.

## 8. Consequences for the sequence

- **The L3 anchor is now three numbers travelling together**: +0.4220 (undirected legal, 100
  items) / +0.4352 (self-scoped legal, ~36 items) / +0.1275 (value-over-types component), with
  the format-control result (−0.0385) as their standing defense against the "any schema preamble
  would do it" objection.
- **The parent's §9 re-fly mandate is discharged**: legal self-scoping is measured, works, and
  closes the oracle-selection premium to inside the noise bar. The remaining open dose question
  (behavior above 100 items) is untouched by this probe.
- **No re-read of this attempt is permitted**: the read is consumed and the suite is
  idempotence-guarded against the same output directory.
