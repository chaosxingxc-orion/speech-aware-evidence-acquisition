# P-SLU verdict — UNRESOLVED (registered one-shot read, 2026-08-18)

Mechanical outcome per the registered branch rules
(`docs/readiness/2026-08-17-pslu-preregistration-REGISTERED.md` §4, verbatim), computed by the
pinned offline read suite (`9eccfff` implementation, `e5547ed` fixtures; 15/15 unit tests green
immediately before the read) over the single COMPLETED attempt
`attempt-20260818T010218Z-4c97cb` (363 rows = 6 arms x 60 + 3 silence-swap; flight archive
`docs/checks/speech-aware-evidence-acquisition/2026-08-17-pslu-flight/2026-08-18-attempt4-flight-execution.md`).
Read archive: `docs/checks/speech-aware-evidence-acquisition/2026-08-18-pslu-read/`
(`verdict.json`, `report.txt`, `MANIFEST.sha256`). The suite ran exactly once; the exposure row
`SAEA-PROBE-pslu-n60` flips to consumed in the same commit.

The suite's own module docstring carries nine numbered engineering-interpretation notes resolving
genuine underspecification in the pre-registration text; they were reviewed and approved before the
read and are cited here by number, never re-litigated.

## 1. Mechanical branch outcome (first, before any interpretation)

**OVERALL: UNRESOLVED — no branch rule fired.**

| Branch | Result | Deciding clause |
|---|---|---|
| VOID (checked first) | **not met** | 0 of 3 silence-swap answers persisted; 0 recheck mismatches; 0 harness defects |
| COPY-TRAP | **not met** | A4 gain +0.1346 vs threshold +0.1408 (half of A1' gain) — short by **0.0062** |
| SUPPLY-CONVERTS | **not met** | A1' gain +0.2816 >= +0.05 MET; A1' copy-rate 0.0255 < 0.50 MET; **A4 gain +0.1346 > +0.01 ceiling NOT MET** |
| DOSE-CONFIRM (secondary) | **not met** | A3 0.5961 does **not** underperform A2 0.4686 (A3 is +0.1275 higher) |
| INERT | **not met** | every arm gains >= +0.02 (min A4 +0.1346) |
| intent-drift guardrail (-5pp) | no flags | all six arms at intent accuracy 0.0000 (see §6) |

The probe landed in the gap the rule set left open: a **wrong-content control arm that gains a
lot**. SUPPLY-CONVERTS presumes the control gains <= +0.01; COPY-TRAP presumes a runaway control
gains >= half of the legal arm's gain. A4 delivered +0.1346 — 47.8% of A1's gain — which is far
too much for the first and 0.0062 too little for the second. The rules were written on the
assumption that A0's floor is a *knowledge* floor; §7 argues it is mostly a *format* floor, which
is why no branch fits.

## 2. Every ingredient number

Per-arm aggregates, exactly as the pinned suite wrote them (n=60 per arm, silence-swap rows
excluded from every aggregate per note 4):

| Arm | Supply | SLU-F1 | Δ vs A0 | P | R | slot_f1_exact | Δ | P | R | intent acc | copy-rate | induced subs |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A0 | none | 0.1741 | — | 0.1692 | 0.1793 | 0.0435 | — | 0.0421 | 0.0449 | 0.0000 | 0.0000 (0/0) | 0 |
| A1 | gold-scenario roster (**ceiling**) | 0.6340 | **+0.4599** | 0.6187 | 0.6501 | 0.5246 | +0.4811 | 0.5106 | 0.5393 | 0.0000 | 0.0000 (0/2224) | 1 |
| A1' | predicted-scenario roster (**legal**) | 0.4557 | +0.2816 | 0.4557 | 0.4557 | 0.2135 | +0.1700 | 0.2135 | 0.2135 | 0.0000 | 0.0255 (84/3300) | 0 |
| A2 | 55-type vocabulary (legal) | 0.4686 | +0.2946 | 0.4551 | 0.4830 | 0.2486 | +0.2051 | 0.2396 | 0.2584 | 0.0000 | 0.0288 (95/3300) | 0 |
| A3 | dose-capped-100 ontology (legal) | 0.5961 | **+0.4220** | 0.5602 | 0.6370 | 0.5000 | +0.4565 | 0.4660 | 0.5393 | 0.0000 | 0.0000 (0/6000) | 3 |
| A4 | deranged roster (**control**) | 0.3087 | +0.1346 | 0.3071 | 0.3102 | 0.1899 | +0.1464 | 0.1889 | 0.1910 | 0.0000 | 0.0000 (0/2201) | 1 |

### Per-sample TP/FP/FN totals (summed over the 60 samples of each arm)

Entity exact-match ledger (`slot_f1_exact`, integer counts; the unit note 6 scopes entity TP gain
to). TP+FN = **89** in every arm, reproducing the registered 89 gold slots exactly:

| Arm | TP | FP | FN | entity-TP gain vs A0 |
|---|---|---|---|---|
| A0 | 4 | 91 | 85 | — |
| A1 | 48 | 46 | 41 | +44 |
| A1' | 19 | 70 | 70 | +15 |
| A2 | 23 | 73 | 66 | +19 |
| A3 | 48 | 55 | 41 | +44 |
| A4 | 17 | 73 | 72 | +13 |

Official SLU-F1 ingredients (distance-weighted; the metric pools the word- and char-distance
ledgers, so pooled TP/FP/FN reproduce the P/R column above exactly):

| Arm | word TP/FP/FN | char TP/FP/FN | pooled TP/FP/FN |
|---|---|---|---|
| A0 | 18.00 / 91.30 / 85.30 | 18.00 / 85.50 / 79.50 | 36.00 / 176.80 / 164.80 |
| A1 | 64.00 / 40.73 / 35.73 | 64.00 / 38.16 / 33.16 | 128.00 / 78.89 / 68.89 |
| A1' | 52.00 / 70.30 / 70.30 | 52.00 / 53.93 / 53.93 | 104.00 / 124.23 / 124.23 |
| A2 | 55.00 / 75.30 / 68.30 | 55.00 / 56.42 / 49.42 | 110.00 / 131.72 / 117.72 |
| A3 | 65.00 / 53.53 / 39.53 | 65.00 / 48.54 / 34.54 | 130.00 / 102.07 / 74.07 |
| A4 | 31.00 / 72.43 / 71.43 | 31.00 / 67.42 / 66.42 | 62.00 / 139.85 / 137.85 |

### Integrity

- Flight status `COMPLETED`, error `None`.
- **Recheck: 0 mismatches** — every row's recomputed TP/FP/FN and parsed answer matched its
  embedded metrics exactly (VOID clause 3 not met).
- **Harness defects: none** — arm/sample completeness, no duplicate rows, silence-swap
  counterparts present, and every row's supplied prompt text agreed with what the frozen
  `pslu_supply_packet` reproduces for its (arm, scenario) pair (note 8).
- Supplied-item counts confirm the registered dose design: A1 mean 37.1 entries/call (range
  19–40), A4 mean 36.7 (19–40), A2 exactly 55/call, A3 exactly 100/call (the registered cap).

### Silence-swap (3 seeded A1' samples)

**0 of 3 persisted — unanimous non-persistence.** All three silence variants produced a different
parsed answer (scenario + action + entity set) from their real-audio counterpart:

| Sample | real-audio answer | silence answer | unchanged |
|---|---|---|---|
| `slurp:devel:005518:audio-1490203960` | Smart Home Control / Turn off / device_type=room light | Setting an alarm / Set an alarm / alarm_type=alarm, time=… | False |
| `slurp:devel:007852:audio-1494416109-headset` | Adding an event to a calendar / Add event / event_name=baseball practice, … | Setting a timer / Set a timer / time=10 minutes | False |
| `slurp:devel:011654:audio-1501692977-headset` | searching for restaurants / search / food_type=Chinese, place_name=… | Setting an alarm / Set an alarm / time=10:00, timeofday=… | False |

**The mandatory partial-persistence disclosure is not triggered** (persistence is 0 of 3, not 1 or
2 of 3). The gains are conditioned on the audio, not a text-only prior. One safety observation for
the record: under silence the core did not abstain — it emitted a confident, well-formed, entirely
invented command in all three cases.

## 3. MANDATORY DISCLOSURE — A1' did not fly as designed; it is a duplicate of A2

**The deployment-legal arm degenerated into A2 on 60 of 60 samples.** Machine-checked evidence
from the attempt's own `ConsumptionTrace`:

- every one of A1''s 60 calls carries supplied-item ids stemmed `A1p-fallback-A2` (0 non-fallback
  calls);
- A1' supplied exactly 55 items on every call — A2's global type vocabulary, not a scenario-scoped
  value roster;
- A1' and A2 supplied **identical item sets on 60/60 samples**;
- A1' and A2 phase-2 prompts are **byte-identical on 60/60 samples**.

Cause: the frozen core's phase-1 scenario predictions are free-form English phrases — 56 distinct
strings over 60 samples (`Music playback`, `Setting a reminder`, `Querying the weather`,
`Checking if a specific date is a Saturday`, …) — and none maps to a canonical SLURP scenario key,
so `pslu_supply_packet` took its designed fallback on every call. Note 8's harness-defect check
reuses that exact frozen function, so it correctly reports **no defect**: this is designed
behaviour, and VOID does not fire mechanically. Scientifically, however:

> **This read contains no test of self-supplied scenario-scoped rosters at all.** Every A1' number
> above is an A2 number under a different label, and the registered A1-vs-A1' ceiling-vs-legal
> contrast (§5) is void as flown.

The self-supplied scoping step failed at the *label-space* boundary, not at the scoping logic:
the core can name a scenario in English but cannot name it in the ontology's vocabulary, and
nothing in the A1' prompt constrained it to. Any re-flight must supply the scenario label set (or
force a closed-set choice) before A1' means anything.

## 4. Second consequence: an accidental duplicate-condition noise floor

Because A1' and A2 were byte-identical conditions, this probe accidentally produced the study's
first empirical read-noise estimate on this vehicle: **identical prompts, identical supply, same
frozen core, 0.4557 vs 0.4686 SLU-F1 — a gap of 0.0129** — with the core returning a **different
response text on 37 of 60 samples** (identical on 23/60).

Two implications, both load-bearing for how the rest of this table is read:

1. Deltas below roughly **±0.013** SLU-F1 at n=60 on this vehicle are indistinguishable from
   decoder nondeterminism; a safe separability bar is ~0.03.
2. The registered **INERT threshold of +0.02 sits barely above that floor** — it would have been
   nearly unusable had the effects been small. Future preregistrations on this vehicle should set
   thresholds against this measured floor rather than against intuition.

## 5. Ceiling-vs-legal contrast

The registered contrast (A1 vs A1') is **void as flown** per §3. The usable legal comparator is
**A3**, which is fully deployment-legal (train-split-mined ontology, no gold field anywhere in its
selection):

| Contrast | SLU-F1 | slot_f1_exact |
|---|---|---|
| A1 (ceiling, gold-scenario-scoped) | 0.6340 | 0.5246 |
| A3 (legal, undirected 100-entry) | 0.5961 | 0.5000 |
| **ceiling premium** | **+0.0379** | **+0.0246** |

A3 recovers **91.8% of the ceiling gain** (+0.4220 of +0.4599). Gold scenario selection — the
oracle advantage the ORG/SUPPLY layer would have to earn legally — is worth only ~0.038 SLU-F1
here, against ~0.42 for the supply itself. The selection problem is, on this vehicle at L3, a
small residual next to the supply effect.

## 6. Descriptive decomposition of the supply benefit

Taking A1's +0.4599 as 100% of the ceiling gain:

| Component | Contrast | Δ SLU-F1 | share of ceiling gain |
|---|---|---|---|
| schema/label-space grounding | A2 − A0 (types only, **zero values**) | +0.2946 | 64.1% |
| value knowledge | A3 − A2 | +0.1275 | 27.7% |
| gold scenario selection | A1 − A3 | +0.0379 | 8.2% |
| *(wrong-content reference)* | *A4 − A0 (deranged values)* | *+0.1346* | *29.3%* |

The single most informative row is A2: supplying **only 55 type names and no values at all** buys
nearly two-thirds of what the gold-scoped value roster buys, and **more than the deranged
value roster** (+0.2946 vs +0.1346). This decomposition is descriptive, not factorial: A2→A3
changes dose (55→100) and content kind (types → type=value) together, and A3→A1 changes scoping
and length together. It cannot be read as a clean causal partition.

### DOSE-CONFIRM (secondary answer)

**Not met, and directionally contradicted.** The registered prediction was A3 < A2 (dilution).
Observed: **A3 0.5961 vs A2 0.4686, i.e. A3 is +0.1275 higher** — the 100-entry roster beat the
55-type vocabulary decisively, and the gap is ten times the §4 noise floor. Two caveats keep this
from being a dose-law refutation: the contrast confounds dose with content kind (A3 carries values,
A2 does not), so it is not a clean dose manipulation; and both arms sit far below the uncapped
4,157-entry roster (~25k tokens) the cap was introduced to avoid. The honest statement is that
**no dilution was observed anywhere in the tested range**, and the dose law remains untested at
doses above 100.

## 7. What the numbers mean for the L3 point on the supply-benefit curve

At L3 the supply-benefit curve on this frozen core is **dominated by schema grounding, not by
knowledge conversion**. The A0 floor is the tell: 0.0435 exact-slot F1, just 4 of 89 gold slots
recovered, while the core simultaneously produces fluent, well-formed, semantically reasonable
JSON (`volume_level` / `low` for a volume command). The unsupplied core is not failing to
understand the speech — it is answering in a different label space than the metric scores. Roughly
64% of the entire ceiling gain is bought by simply showing it the ontology's type names, and even
a *wrong-scenario* value roster buys 29% because it still carries correct type names and the right
output shape. The genuine evidence-supply component — the part attributable to having the right
values available rather than the right schema — is the A3−A2 increment of **+0.1275**, real and
about ten times the measured noise floor, but a quarter of the headline number. For the study's
SUPPLY thesis this is a legitimate and quantitatively strong L3 anchor (**+0.4220 SLU-F1 from a
fully legal, prompt-only, zero-parameter roster, 91.8% of the gold-scoped ceiling**) and
simultaneously a warning: most of it is a one-time format-alignment payment that a well-specified
output contract or a fixed schema preamble could plausibly buy without any retrieval, ORG, or
SUPPLY machinery at all. Any claim that this probe demonstrates *knowledge* supply converting
speech-domain errors must be stated against the A2 baseline, not against A0 — and the copy-safety
evidence that would normally accompany such a claim is, per §8, largely uninformative as flown.

## 8. Limitations and honest disclosures

1. **n = 60, descriptive only.** No p-values, no confidence intervals, no significance claims.
   Every number is a point estimate on one seeded stratified sample (seed 20260807) from one
   split (`devel`, discovery). Effects near the §4 noise floor of ~±0.013 carry no weight.
2. **A1' is void as flown** (§3): the registered deployment-legal arm is a duplicate of A2, and
   the registered ceiling-vs-legal contrast could not be evaluated as designed.
3. **Copy-rate is largely uninformative as flown.** The `ConsumptionTrace` classifier marks
   `copy` only when a supplied item's tokens appear as a *contiguous verbatim subsequence* of the
   response. Value-bearing arms supply `"{type}={value}"` items, which the JSON response format
   splits with punctuation between type and filler — so they can essentially never register
   `copy`, and their reuse lands in `use` instead (A1 384 `use` records, A3 321, A4 228, **0
   `copy` on all three**). Type-only arms supply single-token items, which register `copy` whenever
   the response names that type at all — which is exactly the behaviour the task *wants*.
   Consequently the 0.0000 copy-rates on A1/A3/A4 must **not** be read as "no copying", and the
   0.0255/0.0288 on A1'/A2 must not be read as pathology. The clause the branch rules actually
   evaluated (note 5: A1''s own copy-rate) was well-defined and passed comfortably, but this
   probe yields weak copy-safety evidence overall.
4. **Induced substitutions are near-zero, and vacuous on two arms.** Totals: A1 1, A3 3, A4 1,
   A1' 0, A2 0. Per note 1 an arm supplying no values cannot induce a substitution, so A2's 0 is
   true by construction — and because A1' flew as A2 (§3), **A1''s 0 is also vacuous**. The
   informative counts are the value-bearing arms: 3 induced substitutions against a +44 entity-TP
   gain for A3, 1 against +44 for A1, 1 against +13 for A4. Harm from value supply is real but
   very small at this scale.
5. **The intent-accuracy guardrail is degenerate.** All six arms scored 0.0000, A0 included, so
   "no drift beyond −5 pp" is vacuously satisfied and carries no attention-tax evidence. Cause:
   intent = exact scenario+action match against SLURP's canonical labels, and the core emits
   free-form phrases ("Adjusting device settings" / "Set the volume"); across all 360 scored calls
   there were only 6 exact scenario hits (A1 2, A3 2, A4 2) and 2 exact action hits (A1 1, A4 1),
   and never both on the same sample. No arm supplied a scenario/action label vocabulary — only
   entity types and values — so this is a label-space mismatch, not an attention effect.
6. **The branch rules were mis-specified for this vehicle.** Both SUPPLY-CONVERTS' A4 ceiling
   (+0.01) and COPY-TRAP's A4 half-gain disjunct assume a wrong-content control that gains
   ~nothing. The measured format-induction effect (§7) makes that assumption false at L3, which is
   the direct cause of the UNRESOLVED outcome. A re-flight needs either a format-matched control
   (a syntactically identical roster of non-ontology filler types) or a redefinition of the A0
   baseline to a schema-primed floor, so that "gain" measures knowledge conversion rather than
   format alignment.
7. **Interpretation notes.** The nine notes in the read suite's module docstring were approved
   before the read and applied mechanically. Notes 5, 6 and 9 shaped the COPY-TRAP evaluation
   (arm scoping of copy-rate; entity TP unit; the strict-positivity requirement that stops the
   `>=` disjuncts from firing vacuously at 0 vs 0); note 7 set unanimity as the silence-swap VOID
   bar; notes 1 and 2 scope the induced-substitution count. Notes 1 and 4 are load-bearing for
   limitations 3 and 4 above.
8. **Scope.** Discovery tier, `bounded-discovery-probe`, one COMPLETED attempt, single read.
   SLURP audio is CC BY-NC 4.0; the non-commercial constraint is carried on every audio-derived
   number here. Rosters are train-split-mined only (`train_synthetic` refused at binding for
   64.8% verbatim devel overlap), so all legal-tier arms remain legal.

## 9. Consequences for the sequence

- **The L3 anchor stands, restated against the right baseline**: a legal, prompt-only, 100-entry
  roster buys +0.4220 SLU-F1 over an unsupplied frozen core and reaches 91.8% of the gold-scoped
  ceiling — but only **+0.1275** of that is attributable to value knowledge over a bare type
  vocabulary. Both numbers should travel together in any downstream claim.
- **A1' must be re-flown** with a closed-set scenario prediction (or a supplied scenario label
  vocabulary) before any self-supplied-scoping claim is made. Until then the study has no
  measurement of legal self-scoping at L3.
- **The measured noise floor (~±0.013 at n=60)** is now the calibration reference for every
  threshold in the next preregistration on this vehicle.
- **Copy-rate needs a shape-invariant definition** before it can serve as a safety control on
  value-bearing arms; induced-substitution count is the metric that actually worked here.
- No re-read of this attempt is permitted: the read is consumed and the suite is idempotence-
  guarded against the same output directory.
