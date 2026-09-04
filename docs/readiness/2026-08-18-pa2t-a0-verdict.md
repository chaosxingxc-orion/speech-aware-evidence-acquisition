# P-A2T Stage-1 A0 baseline verdict — the REAL tool-acc/EM gap (registered one-shot read, 2026-08-18)

Descriptive baseline outcome computed by the pinned offline read suite (`ae4d71d` — implementation,
CLI and fixtures in one commit; 18/18 unit tests green immediately before the read, clean tree) over
the single COMPLETED attempt `attempt-20260818T055500Z-res315` of the flown Stage-1 A0 zero-supply
baseline (400 rows over the frozen 400-item Audio2Tool discovery split, 8 tiers x 50, seed
20260807). Read archive:
`docs/checks/speech-aware-evidence-acquisition/2026-08-18-pa2t-a0-read/` (`verdict.json`,
`headroom.json`, `report.txt`, `MANIFEST.sha256`). The suite ran **exactly once**; the exposure row
`SAEA-BASE-a2t-a0-400` flips to consumed in the same commit.

This is Stage 1 of the P-A2T family — a **baseline read, not a probe**. It carries no branch rules,
so there is no mechanical branch outcome to report; its two registered deliverables are the real
tool-acc/EM gap and the Stage-2 headroom sample list.

The suite's module docstring carries six numbered engineering-interpretation notes resolving genuine
underspecification in the mission text. They were reviewed and approved before the read and are
cited here by number, never re-litigated.

## 1. Headline — the retired premise is replaced

**The 84.6% / 15.6% headroom premise (a claimed ~69pp gap) is RETIRED and is replaced by the
numbers below.** It was unsourced prose-only in five files and is recorded as
`cited_premise_unverified` in `configs/probes/g0-binding/pa2t-binding.json`. The measured baseline
on the frozen 400-item discovery split is:

| | value |
|---|---|
| n | **400** (8 tiers x 50, seed 20260807) |
| Tool accuracy | **0.5425** (217/400) |
| Exact match | **0.2425** (97/400) |
| **Gap (tool-acc − EM)** | **+0.3000** (120/400) |
| Empty tool-call rate | 0.1025 (41/400) |
| Stage-2 headroom list size | **120** |
| Recheck mismatches | **0** |
| Harness defects | **none** (the suite scored rather than refusing) |

Neither prior position survives. The retired figure claimed a ~69pp gap; the two recoverable
archival Audio2Tool reads pointed the other way, at tool-acc ≈ EM (dev n=40: 67.5 / 65.0, a 2.5pp
gap; test n=60: 86.7 / 85.0, a 1.7pp gap). The truth on this split is **+30.0pp** — less than half
the retired claim, but more than ten times the archival gap. There is a real, large, and now
machine-listed conversion target; it is not the near-total one the retired premise asserted.

The gap and the headroom count are the same quantity in different units, and that identity is
machine-checkable rather than asserted: exact match implies tool accuracy (equal multisets of
canonicalized name+argument calls imply equal multisets of names), so the tool-correct set
partitions exactly into the EM-correct set and the headroom set. 217 − 97 = 120, and 120/400 =
0.3000 = the gap. Every per-tier row below satisfies the same identity.

## 2. Full per-tier table (8 x 50)

Exactly as the pinned suite wrote them. `empty` is the registered note-1 definition — the predicted
call list is literally empty, regardless of the `parsed` flag. `headroom` is `tool_acc == 1.0 AND
exact_match == 0.0`.

| tier | n | tool_acc | EM | gap | empty | empty_rate | headroom |
|---|---|---|---|---|---|---|---|
| tier1_direct | 50 | 0.5800 | 0.1200 | +0.4600 | 1 | 0.0200 | 23 |
| tier2_parametric | 50 | **0.7200** | 0.3800 | +0.3400 | 0 | 0.0000 | 17 |
| tier3_multi_intent | 50 | 0.6200 | 0.0400 | **+0.5800** | 2 | 0.0400 | **29** |
| tier4_implicit | 50 | **0.3000** | 0.2400 | **+0.0600** | 11 | 0.2200 | **3** |
| tier5_needle | 50 | 0.5400 | 0.3000 | +0.2400 | **16** | **0.3200** | 12 |
| tier6_correction | 50 | 0.6400 | 0.4000 | +0.2400 | 4 | 0.0800 | 12 |
| tier7_multiturn | 50 | 0.6000 | **0.4400** | +0.1600 | 4 | 0.0800 | 8 |
| tier8_intent_blending | 50 | 0.3400 | **0.0200** | +0.3200 | 3 | 0.0600 | 16 |
| **overall** | **400** | **0.5425** | **0.2425** | **+0.3000** | **41** | **0.1025** | **120** |

Readings, kept descriptive:

- **Best tool selection: tier2_parametric (0.7200)**; it also has the cleanest output behaviour
  (zero empty calls). **Best execution: tier7_multiturn (EM 0.4400)**, with the second-smallest gap.
- **Worst tool selection: tier4_implicit (0.3000)** and **tier8_intent_blending (0.3400)** — the two
  tiers where the tool to call is not stated but inferred.
- **Worst execution: tier8_intent_blending (EM 0.0200, 1/50)** and **tier3_multi_intent (EM 0.0400,
  2/50)**.
- **Largest gap: tier3_multi_intent (+0.5800)** — the core picks the right tool set on 31/50 but
  gets the full call right on 2/50. **tier1_direct (+0.4600)** is the same shape on the easiest
  tier: 29/50 tool-correct, 6/50 exact.
- **Smallest gap: tier4_implicit (+0.0600)**. This tier is not argument-limited; it is
  selection-limited. When it does select correctly it usually executes correctly.

The two extremes matter for Stage 2 more than the mean does: tier3_multi_intent alone supplies 29 of
the 120 headroom samples while tier4_implicit supplies 3.

## 3. Empty tool-call structure — the flight's observation confirmed, and widened

The flight's own behavioural note recorded "17/400 items return an empty tool-call list,
concentrated in tier4_implicit (10/50)". **Both halves of that statement are confirmed from the
scored data, under the flight's narrower definition.** The read's registered note-1 definition is
broader, so its headline number is larger; the two decompose exactly:

| | count | dominant tier |
|---|---|---|
| Well-formed empty call (valid JSON, zero calls — the flight's count) | **17** | tier4_implicit **10/50** |
| Parse failure (`parsed == False`, fail-closed to an empty prediction) | **24** | tier5_needle **16/50** |
| **Total empty predictions (note-1 definition)** | **41** | — |

Per-tier split (parse-fail / well-formed), summing to the `empty` column above: tier1_direct 0/1,
tier2_parametric 0/0, tier3_multi_intent 2/0, tier4_implicit 1/10, tier5_needle 16/0,
tier6_correction 2/2, tier7_multiturn 0/4, tier8_intent_blending 3/0. The well-formed column totals
17 and concentrates in tier4_implicit at 10/50 — the flight's figure reproduced exactly.

Provenance of this decomposition, disclosed because it is not itself in `verdict.json`: it uses the
**flight's own embedded `parsed` flags** from `outputs.jsonl` plus a blank-text check, not a second
scoring run. The suite's recheck found **0 mismatches** between embedded and recomputed metrics
across all 400 rows and all six recheck fields, so the embedded flags are validated against the
frozen scorer. No response text was blank (0/400): every parse failure is a non-empty response the
scorer could not read as a JSON tool-call array.

The consequence is that the raw 10.25% "empty" rate is two different failure modes wearing one
label, and the concentration claim depends on which is meant. **Deliberate abstention** (a
well-formed decision not to call a tool) is a tier4_implicit phenomenon: 10/50 there against 7
across all other tiers combined. **Format failure** is a tier5_needle phenomenon: 16/50 there, 8
across all other tiers combined, and it is a full third of that tier. tier5_needle's depressed
scores are therefore substantially a formatting floor, not only a knowledge floor — the same
distinction the P-SLU verdict drew on a different carrier.

## 4. Stage-2 headroom list

**Size: 120 samples.** Machine-readable at
`docs/checks/speech-aware-evidence-acquisition/2026-08-18-pa2t-a0-read/headroom.json`
(schema `saea-a2t-a0-headroom-v1`; also mirrored in `verdict.json` under `headroom.sample_ids`).
Selection rule as registered: `tool_accuracy == 1.0 AND exact_match == 0.0`.

Tier distribution: tier1_direct 23, tier2_parametric 17, tier3_multi_intent 29, tier4_implicit 3,
tier5_needle 12, tier6_correction 12, tier7_multiturn 8, tier8_intent_blending 16.

**Actionable for Stage-2 registration, not performed here:** the binding table's own
`proposed_selection_rule` says "if that set exceeds 40, take n = 40 by seeded tier-stratified draw
at seed 20260807". 120 > 40, so that draw is required. Selecting it is Stage-2 registration work and
is deliberately left undone by this read; note also that a *tier-stratified* draw over a set this
unevenly distributed cannot be uniform per tier (tier4_implicit offers only 3 candidates), so the
stratification scheme needs an explicit decision at registration rather than an assumed equal split.

## 5. Integrity

- Flight status `COMPLETED`, `error: None`, `request_failures: []`, `arms: ["zero-supply"]`,
  400 result rows, 400 unique sample ids.
- `split_identity_hash` `e1d751e6c76e49d087620842ba17c34e432a4602169dc2b93ee7e0a529ca332c` agrees
  across three independent places: the flight receipt, the frozen probe receipt
  (`docs/receipts/probe-samples/r1-audio2tool-sample.json`), and the exposure-ledger cell — verbatim,
  as note 5 requires.
- **Recheck: 0 mismatches** across 400 rows x 6 fields (`tool_accuracy`, `exact_match`,
  `slot_precision`, `slot_recall`, `slot_f1`, `parsed`). The flight-time scorer and this suite's
  scorer never disagreed. Per note 3 this signal is informational; it happens to be perfectly clean.
- **Harness defects: none.** Per note 2 every structural check is a fail-closed refusal raised
  before any scoring; the suite scored, so none fired — no malformed rows, no duplicate sample ids,
  no wrong-arm rows, no missing or extra ids against the frozen 400-item receipt.
- The read was model-free and read-only: no model session, no GPU, no installs, no mutation of the
  attempt directory. Zero core contact.
- Spend context (from the flight, not this read): 400 real core calls of the 450 registered; the
  resumed attempt itself flew 85 calls / 565.64 audio-seconds / 1894.99 s wall and replayed 315
  cached responses, inside the 1.5 GPU-h cap.

## 6. What this means for the L5 point on the supply-benefit curve

The Stage-1 question was whether a supply probe on this carrier would be aiming at anything real.
It is. The retired premise implied an enormous conversion target (~69pp) and the recoverable
archival reads implied essentially none (~2pp); the measured answer is +30.0pp, a target that is
both real and bounded, with 120 named samples where the frozen core already selects the right tool
and still fails the call. That is a genuine L5 point rather than a phantom: evidence supply has
somewhere to land, and the ceiling any supply arm can claim on this split is now a measured number
instead of a prose assertion. But the same table says the target is heterogeneous in a way that
should shape the Stage-2 arm design rather than be averaged away. The headroom concentrates where
the task is compositional and argument-limited — tier3_multi_intent (29), tier1_direct (23),
tier2_parametric (17), tier8_intent_blending (16) — and nearly vanishes where the bottleneck sits
upstream of arguments: tier4_implicit contributes 3 headroom samples because its floor is tool
*selection* (0.3000), not argument filling. A further slice is not a knowledge problem at all: 24
of 400 rows (6%) never produced parseable output, two-thirds of them in tier5_needle, and no
evidence supply will move a formatting floor. So the honest shape of the L5 point is a ~30pp ceiling
of which only the argument-conversion component is plausibly supply-addressable, with a
selection-limited tier and a format-limited tier that a single averaged supply arm would silently
blend together — exactly the confound that left P-SLU unresolved, and the reason Stage 2 should
report per-tier rather than pooled.

## 7. Limitations — read these with the numbers

- **Discovery split, n=400, descriptive only.** These are baseline observations on the frozen
  discovery split. No confirmatory claim, no superiority claim, no generalization beyond this split,
  this quantization, this sampling policy and this prompt.
- **Single arm, zero supply.** One condition flew. There is no comparator, so nothing here measures
  the effect of supply; it measures only the floor that a later supply arm would have to beat.
- **No read-noise floor exists for this carrier.** Nothing in this flight repeats a condition, so
  the run-to-run variability of these numbers is unknown. Small per-tier differences (n=50 per tier,
  so one sample is 2pp) must not be over-read; the P-SLU flight incidentally measured ~0.013 between
  byte-identical conditions on a different carrier, and no analogous figure exists here.
- **The 120-sample headroom list is a property of this one attempt.** It is a seed for Stage-2
  registration, not an established stable set; a re-fly would not reproduce it exactly.
- **The archival dev/test reads remain non-comparable.** They differ in split, seed, quantization,
  sampling policy and prompt, so the fact that this read lands between them is not a reconciliation
  of the three — it is one measurement on one split, and the only one bound to an execution on this
  machine.
- **Scorer semantics are interpretation, not ground truth.** `a2t-scorer-v1` reimplements the
  paper's three metrics because the official eval scripts were unreleased at survey time; its
  documented choices (order-insensitive multiset tool matching, case-sensitive tool names,
  canonicalized argument comparison, fail-closed parsing) are recorded in
  `reproduction/toolcall_scoring.py` and are load-bearing for every number above.
- **Empty-call accounting depends on the definition**, as §3 shows: 41 under the registered note-1
  definition, 17 under the flight's narrower one. Any downstream citation must say which.

## Correction under a2t-scorer-v2 (2026-09-03)

Zero-contact offline re-score of the same sealed `outputs.jsonl` (400/400 rows, v1 identity confirmed
to 4 decimals overall and per tier) under the registered `a2t-scorer-v2`
(`analysis.a2t_v2_rescore`, `docs/checks/speech-aware-evidence-acquisition/2026-09-03-a2t-scorer-v2-rescore/`).
This is a single, standalone arm (zero-supply direct baseline) with no paired treatment in this
flight; there is no saves/harms/ties contrast to report here.

| | v1 exact | v1 tool_acc | v2 exact | v2 tool_acc (ordered) | v2 tool_acc (multiset) | v2 slot F1 | v1 slot F1 | parse rate |
|---|---|---|---|---|---|---|---|---|
| overall (n=400) | 0.2425 | 0.5425 | 0.3125 | 0.5300 | 0.5425 | 0.4363 | 0.3434 | 0.9400 |

| tier | v1 exact | v1 tool_acc | v2 exact | v2 tool_acc (ordered) | v2 tool_acc (multiset) | paper tool_acc/EM |
|---|---|---|---|---|---|---|
| tier1_direct | 0.1200 | 0.5800 | 0.4000 | 0.5800 | 0.5800 | 0.924/0.924 |
| tier2_parametric | 0.3800 | 0.7200 | 0.4400 | 0.7200 | 0.7200 | 0.846/0.156 |
| tier3_multi_intent | 0.0400 | 0.6200 | 0.1400 | 0.5800 | 0.6200 | 0.747/0.286 |
| tier4_implicit | 0.2400 | 0.3000 | 0.2400 | 0.3000 | 0.3000 | 0.334/0.113 |
| tier5_needle | 0.3000 | 0.5400 | 0.3800 | 0.5400 | 0.5400 | 0.906/0.360 |
| tier6_correction | 0.4000 | 0.6400 | 0.4000 | 0.6400 | 0.6400 | 0.815/0.248 |
| tier7_multiturn | 0.4400 | 0.6000 | 0.4400 | 0.6000 | 0.6000 | 0.546/0.163 |
| tier8_intent_blending | 0.0200 | 0.3400 | 0.0600 | 0.2800 | 0.3400 | 0.417/0.124 |

This reproduces the slice-S1 zero-contact study's V2e numbers for A0 exactly (overall 53.00/31.25,
Tier-1 40.00 EM). This verdict carries no promotion/branch decision to re-open (§0 above: "a baseline
read, not a probe"); the only load-bearing correction is factual — the v1-vs-paper Tier-1 EM gap this
doc's headline reports (12.0 vs the paper's 92.4) narrows to 40.0 vs 92.4 under v2, still leaving a
large (~52pp) residual gap that scorer semantics alone do not close (see the slice-S1 study's own
reading: `TOOL_SET_WRONG` accounts for 46.9% of every A0 v1 failure and is untouched by any v2 rule).
