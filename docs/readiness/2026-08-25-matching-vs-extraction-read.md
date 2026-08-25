# MATCHING versus EXTRACTION — the conditioned secondary reading (2026-08-25)

**Exposure row:** `SAEA-SN-MF-MATCHING-VS-EXTRACTION-READ`, registered `f11e6148` BEFORE any
computation.
**Module:** `src/speech_aware_evidence_acquisition/analysis/matching_vs_extraction_read.py`.
**Receipt:** `docs/checks/speech-aware-evidence-acquisition/2026-08-25-matching-vs-extraction/read-report.json`,
sha256 `378757b5bc3292395cbdc82a19c936912edaf61725cede012bfad6b77ffd6523`.
**Spend exactly as registered:** 0 frozen-core contacts, 0 embedding-tool contacts, 0 tokenizer
contacts, 0 HTTP or socket requests, 0 audio seconds, 0.0 GPU hours, 0 new dependencies.
`arm_offline_guard()` was armed before the first input was opened and recorded **0 outbound
connection attempts against zero targets**. The resident np2 llama-server (pid 38623, port 8090)
was not contacted, probed, reconfigured or stopped. No knob changed; no line under `rails/`
touched.

---

## 0. The question

Both scorers in this study compute two things, and every campaign so far has reported and
optimized only the first:

- **MATCHING** — pick the right intent (SLURP `scenario_action_exact`) or the right tool
  (Audio2Tool `tool_accuracy`);
- **EXTRACTION** — pull structured content out of the signal (SLURP `slot_f1_exact` and the
  official `slu_f1`; Audio2Tool `exact_match`, i.e. the full name-**plus-argument** multiset, with
  the slot-triple micro-F1 beside it).

The architectural claim is that the knowledge plane owns matching and *supplies enough information
for* extraction. **Nobody had measured whether the supply actually serves extraction.**

The confound: on SLURP the aggregate extraction score moved (+3.5438 slot-F1 points on the
unexposed half), but getting the intent right also constrains which slot types are plausible — so
the extraction gain may be entirely **downstream** of the matching gain. The only separation is to
**condition on matching**.

### Metric-naming discipline, carried at every citation

`slot_f1_exact` is the exact `{type, filler}` dict match (the official SLURP script's plain
`entities` row). `slu_f1` is the **official** combined word-distance + char-distance metric. They
are never interchanged and never relabelled as each other. `slot_f1_exact_mean` is the **macro**
mean of per-sample F1 — the exact quantity the landed `field_decomposition_*` profiles publish;
the P/R/F1 triples below are corpus-level **micro**, obtained by summing `SluScore` ingredients
into a synthetic `SluScore` and reading the frozen scorer's own properties.

---

## 1. FIDELITY GATE — **PASS**

Re-scored per sample through the same imported scoring path the flown reads used
(`reproduction.slurp_scoring.parse_slu_response` + `score_slu`; `Audio2ToolAdapter.score` behind
the frozen `a2t-scorer-v1`), and cross-checked sample by sample against
`dev500_confirmatory_read.score_arm` itself and against `toolcall_scoring.score_item`. Every
target reproduced **to the sample and to full float precision** (byte equality of the doubles).

| population | arm | metric | target | measured | result |
|---|---|---|---|---|---|
| unexposed500 | M0 | `scenario_action_exact` | 278 | 278 | PASS |
| unexposed500 | M0 | `slot_f1_exact_mean` | 0.17097619047619048 | 0.17097619047619048 | PASS |
| unexposed500 | BLEND | `scenario_action_exact` | 379 | 379 | PASS |
| unexposed500 | BLEND | `slot_f1_exact_mean` | 0.20641428571428572 | 0.20641428571428572 | PASS |
| exposed500 | M0 | `scenario_action_exact` | 258 | 258 | PASS |
| exposed500 | M0 | `slot_f1_exact_mean` | 0.12224761904761905 | 0.12224761904761905 | PASS |
| exposed500 | BLEND | `scenario_action_exact` | 378 | 378 | PASS |
| exposed500 | BLEND | `slot_f1_exact_mean` | 0.15097142857142856 | 0.15097142857142856 | PASS |
| A2T-G1-104 | M0 | tool accuracy / exact match / empty call | 62 / 29 / 14 | 62 / 29 / 14 | PASS |
| A2T-G1-104 | BLEND | tool accuracy / exact match / empty call | 63 / 29 / 3 | 63 / 29 / 3 | PASS |

Sources: `docs/checks/.../2026-08-25-dev1000-lock-read/read-verdict.json` (`profiles.field_decomposition_*`)
and `docs/checks/.../2026-08-25-a2t-g1/g1-read-attempt4.json`. Every input was sha256-verified
before a single response text was parsed: the four sealed `*-outputs.jsonl` files, both arms'
committed mechanical reports, and the three SLURP split receipts plus the A2T-G1-104 receipt.

---

## 2. Method — and the two caveats that travel with every conditioned number

**The partition.** Each population is partitioned on the **joint** matching outcome of the two
arms into four cells: both matched / only BLEND matched / only M0 matched / neither matched.
Because the joint cells are the *same samples* for both arms, every cell delta is **paired** and
the aggregate extraction delta decomposes exactly as `sum_c w_c * delta_c` with one shared weight
vector and no reweighting residue. The reconstruction is asserted to close to 1e-9 and does.

**The (a)/(b) split then needs no modelling at all:**

- **(a) matching-attributable** = the two **discordant** cells (only-BLEND-matched,
  only-M0-matched), where the arms' matching outcomes differ, so extraction movement inside them is
  mechanically downstream of the matching movement;
- **(b) matching-independent** = the two **concordant** cells (both-matched, neither-matched),
  where both arms share a matching status, so no matching movement can explain any extraction
  movement inside them. Its **both-matched** half is the conditioned headline.

A marginal two-group Oaxaca decomposition is computed as a **cross-check** in both weighting
orders (section 6). It is never the attribution: its within-group term compares two *different*
sample sets.

**Uncertainty** is the campaign's own: `analysis.bootstrap.paired_cluster_bootstrap` through
`dev100_reviewer_audit.bootstrap_gain`, **N=10,000, seed 20260807**, 90% and 95% percentile CIs —
the identical primitive, seed and N as the DEV-500 and DEV-1000 reads. Micro-aggregated ratio
statistics use the same primitive with a local statistic closure. The imported wrapper hard-codes
a resampling string reading "over the 100 DEV-100 ids"; the module is not edited (it is pinned to
already-sealed reads), so every block carries its own `resampling_universe` and the erratum.

> **CAVEAT 1 — post-treatment conditioning.** Cell membership is a function of the OUTCOME of both
> arms. Every conditioned number is therefore conditioned on a post-treatment variable and can
> carry selection (collider) bias. The cells are **descriptive mechanism readings, never effect
> sizes**.
>
> **CAVEAT 2 — small n.** A small-n cell is a mechanism reading whatever its interval says. This
> rule was fixed in the ledger row before any cell's n was known.

---

## 3. SLURP — DEV-1000-NEW500 (500 UNEXPOSED)

> **SECONDARY READING on the LOCKED baseline's population.** The aggregates restated here were
> computed inside the one-shot lock read, so restating them is not a new read — but **every
> conditioned statistic in this section is a SECONDARY reading and MUST NOT be used to revise,
> re-tune or restate the LOCK.** It is descriptive.

**Aggregates.** Matching 278 → 379 (+20.20 pp, CI90 [+17.20, +23.40]) — the locked statistic,
restated. Extraction: `slot_f1_exact_mean` 0.1709762 → 0.2064143 (**+3.5438 pts**); micro
`slot_f1_exact` F1 0.247375 → 0.298122 (+5.0748 pts); official micro `slu_f1` F1 0.376674 →
0.430813 (+5.4139 pts).

### The four-cell table (SECONDARY)

| cell | n | w | `slot_f1_exact_mean` M0 → BLEND | Δ (pts) | CI90 | micro `slot_f1_exact` F1 M0 → BLEND (Δ) | official micro `slu_f1` F1 M0 → BLEND (Δ, CI90) | contribution to +3.5438 |
|---|---|---|---|---|---|---|---|---|
| **both matched** | **273** | .5460 | 0.160701 → 0.159480 | **−0.1221** | [−1.5873, +1.2210] | 0.223158 → 0.223158 (**+0.0000**) | 0.370265 → 0.371159 (+0.0894, [−0.9401, +1.1619]) | **−0.0667** |
| only BLEND matched | 106 | .2120 | 0.280975 → 0.391532 | +11.0557 | [+3.8230, +18.3962] | 0.372549 → 0.507317 (+13.4768) | 0.485193 → 0.613883 (+12.8690, [+6.8462, +19.1719]) | +2.3438 |
| only M0 matched | 5 | .0100 | 0.200000 → 0.400000 | +20.0000 | [0.0000, +60.0000] | 0.500000 → 0.800000 (+30.0000) | 0.500000 → 0.800000 (+30.0000, [0, +100]) | +0.2000 |
| neither matched | 116 | .2320 | 0.093391 → 0.139368 | **+4.5977** | **[+1.7241, +7.7586]** | 0.160920 → 0.239521 (+7.8601) | 0.253388 → 0.361759 (**+10.8371**, **[+6.3169, +15.7389]**) | +1.0667 |

Micro P/R for the conditioned cell: M0 0.270408 / 0.189964, BLEND 0.270408 / 0.189964 — the two
arms have **identical** exact-slot TP/FP/FN (53 / 143 / 226) over those 273 samples, so the micro
`slot_f1_exact` delta is exactly `0.0000`, not a rounding to zero. `n=5` is a MECHANISM reading.

### The conditioned headline

**On the 273 samples (54.6% of the population) where BOTH arms got the intent right, extraction
does not move.** Macro slot-F1 −0.1221 pts with a CI90 straddling zero; micro slot-F1 exactly
zero; official SLU-F1 +0.0894 pts with a CI90 straddling zero.

### (a)/(b) decomposition — **(a) DOMINATES**

| term | cells | points | share of |total| |
|---|---|---|---|
| **(a) matching-attributable** | only-BLEND-matched + only-M0-matched | **+2.5438** | **71.78%** |
| **(b) matching-independent** | both-matched + neither-matched | **+1.0000** | 28.22% |
| — of which both-matched | | −0.0667 | |
| — of which neither-matched | | +1.0667 | |
| aggregate | | **+3.5438** | closes exactly |

**Nearly three-quarters of the aggregate extraction gain is mechanically the matching gain.** The
remaining +1.0000 point is *not* downstream of matching — but it does not live where the claim
needs it either: it comes almost entirely from the **neither-matched** cell, where both arms got
the intent wrong (+4.5977 macro pts, CI90 excludes zero; +10.8371 official SLU-F1 pts, CI90
excludes zero). In the cell where matching already succeeds, the supply contributes −0.0667.

---

## 4. SLURP — DEV-500 (500 PRIOR-EXPOSED)

> SECONDARY READING on the nested prior-exposed half; **never pooled into the lock claim.**

**Aggregates.** Matching 258 → 378 (+24.00 pp, CI90 [+20.80, +27.20]). Extraction:
`slot_f1_exact_mean` 0.1222476 → 0.1509714 (**+2.8724 pts**); micro `slot_f1_exact` F1 0.189889 →
0.245259 (+5.5370); official micro `slu_f1` F1 0.361130 → 0.402267 (+4.1137).

| cell | n | w | `slot_f1_exact_mean` M0 → BLEND | Δ (pts) | CI90 | official micro `slu_f1` F1 Δ (pts, CI90) | contribution to +2.8724 |
|---|---|---|---|---|---|---|---|
| **both matched** | **255** | .5100 | 0.094846 → 0.089617 | **−0.5229** | [−1.3072, 0.0000] | **−1.6351**, **[−3.2291, −0.1108]** | **−0.2667** |
| only BLEND matched | 123 | .2460 | 0.175106 → 0.289973 | +11.4866 | [+6.3376, +16.8293] | +16.3285, [+9.9419, +22.8961] | +2.8257 |
| only M0 matched | 3 | .0060 | 0.333333 → 0.333333 | 0.0000 | [0.0000, 0.0000] | −10.0000, [−50.0000, 0.0000] | 0.0000 |
| neither matched | 119 | .2380 | 0.121008 → 0.134174 | +1.3165 | [−1.8487, +4.5378] | +4.2595, [+0.2776, +8.4833] | +0.3133 |

| term | points | share of |total| |
|---|---|---|
| **(a) matching-attributable** | **+2.8257** | **98.38%** |
| (b) matching-independent | +0.0467 | 1.62% |
| aggregate | **+2.8724** | closes exactly |

**On the exposed half the confound is almost total: 98.4% of the aggregate extraction gain is the
matching gain.** And in the conditioned cell the official SLU-F1 is **worse** under BLEND by
−1.6351 points with a CI90 that **excludes zero** — the one interval in this whole reading that
separates from zero inside a conditioned cell, and it points the wrong way. The
matching-independent signal seen on the unexposed half's neither-matched cell (+4.5977 macro pts)
**does not replicate** here (+1.3165, CI90 straddles zero); only its official-SLU-F1 counterpart
survives weakly (+4.2595, CI90 lower bound +0.2776).

---

## 5. Audio2Tool — A2T-G1-104 (104 EXPOSED)

> **SECONDARY READING on an EXPOSED population** (campaign plan section 3.3): every number here is
> a secondary reading and can never be a campaign claim; the claim interval needs n ≥ 400 UNEXPOSED
> and belongs to G2. n = 104 is below the plan's own power floor.

**Structural fact, asserted per sample (not assumed):** `score_item` computes `exact_match` as
equality of the full name-**plus-argument** multiset and `tool_accuracy` as equality of the
tool-**name** multiset, so `exact_match == 1` structurally implies `tool_accuracy == 1`. Extraction
is therefore identically zero in every cell for the arm that failed matching.

**Aggregates.** Matching (tool accuracy) 62 → 63 (**+0.9615 pp**, CI90 [−2.8846, +4.8077];
McNemar 3 wrong→correct / 2 correct→wrong, exact p = 1.0). Extraction (exact match) 29 → 29
(**0.0000 pp**). Slot micro P/R/F1: M0 0.366337 / 0.544118 / 0.437870 (TP 74, expected 136,
predicted 202); BLEND 0.328947 / 0.551471 / 0.412088 (TP 75, expected 136, predicted 228) —
**ΔF1 −2.5781 pts**. Empty calls 14 → 3; unparsed 4 → 0.

### The four-cell table (SECONDARY, EXPOSED)

| cell | n | w | exact match M0 → BLEND | Δ (pp) | discordant pairs | slot micro-F1 M0 → BLEND (Δ pts, CI90) | contribution to 0.0000 |
|---|---|---|---|---|---|---|---|
| **both matched** | **60** | .5769 | 28/60 → 28/60 | **0.0000** | **0** | 0.583784 → 0.577540 (−0.6244, [−1.4369, 0.0000]) | **0.0000** |
| only BLEND matched | 3 | .0288 | 0/3 → 1/3 | +33.3333 | 1 | 0.000000 → 0.285714 (+28.5714) | +0.9615 |
| only M0 matched | 2 | .0192 | 1/2 → 0/2 | −50.0000 | 1 | 0.500000 → 0.000000 (−50.0000) | −0.9615 |
| neither matched | 39 | .3750 | 0/39 → 0/39 | 0.0000 | 0 | 0.260274 → 0.236686 (−2.3588, [−5.7884, +0.4621]) | 0.0000 |

`n = 3` and `n = 2` are MECHANISM readings and nothing else.

### (a)/(b) decomposition of the exact-match delta — **BOTH TERMS ARE EXACTLY ZERO**

| term | points | note |
|---|---|---|
| (a) matching-attributable | **+0.9615 − 0.9615 = 0.0000** | the two discordant singletons cancel exactly |
| (b) matching-independent | **0.0000 + 0.0000 = 0.0000** | the conditioned cell moves 0, the neither cell moves 0 |
| aggregate | **0.0000** | closes exactly |

**The A2T zero is a genuine zero, not a cancellation of a positive matching-driven term against a
negative within-cell term.** Inside the conditioned cell there are **zero discordant exact-match
pairs**: not one of the 60 doubly-matched samples changed its extraction outcome.

### Why the gap WIDENED (0.3173 → 0.3269), by the same decomposition

`gap = tool_accuracy − exact_match`, so `Δgap = Δtool_accuracy − Δexact_match = +0.9615 pp −
0.0000 pp = +0.9615 pp`, and `0.317308 + 0.009615 = 0.326923` exactly. **The gap widened by
precisely the matching gain, because extraction did not follow it at all.** Equivalently, the
conditional conversion `P(exact match | tool correct)` fell 0.467742 → 0.460317 — and inside the
conditioned cell it is **identical for both arms** (28/60 = 0.466667). The whole fall comes from
the margin: BLEND's 3 newly matched samples convert at 1/3 = 0.3333 (below the 0.4667 base rate),
while the sample M0 matched and BLEND lost was converting at 1/2.

### The one A2T extraction effect that is measurable is NEGATIVE

On the finer slot micro-F1, the supply moves the aggregate **−2.5781 points**. The mechanism is
visible in the raw counts: BLEND emits **26 more predicted argument triples** (202 → 228) and gains
exactly **one** more true positive (74 → 75), so precision falls 3.74 points while recall rises
0.74. This is the empty-call repair working as designed on the matching axis (14 empty → 3, 4
unparsed → 0) and paying for it on the extraction axis. The (a)/(b) split of the slot-F1 mean is
(a) −0.4808 / (b) +0.1923 of an aggregate −0.2885 — (a) dominates there too, at 71.4%.

---

## 6. Cross-check: the marginal Oaxaca decomposition, and why it disagrees

| population | ordering | (a) reweighting | (b) within-group | verdict |
|---|---|---|---|---|
| SLURP unexposed500 | primary | −0.4353 | +3.9791 | (b) |
| SLURP unexposed500 | mirror | +1.4997 | +2.0441 | (b) |
| SLURP exposed500 | primary | −1.2213 | +4.0936 | (b) |
| SLURP exposed500 | mirror | +0.3778 | +2.4946 | (b) |
| A2T exact match | primary | +0.4498 | −0.4498 | (b) |
| A2T exact match | mirror | +0.4426 | −0.4426 | (b) |

The marginal view names (b), the joint view names (a). Both close exactly; they are not in
arithmetic conflict, they are answering different questions, and the disagreement is itself
informative:

1. **The marginal (b) is not a paired within-cell effect.** It compares M0's matched group
   (n = 278) against BLEND's matched group (n = 379). Those are different sample sets, so the term
   absorbs the composition change of the matched group itself. The joint view is paired over
   identical samples and is therefore the attribution.
2. **On SLURP, matching success and extraction score are NEGATIVELY associated at sample level.**
   M0's matched-group mean slot-F1 is 0.161408 against 0.182958 for its unmatched group (exposed
   half: 0.097619 against 0.148505). Easy intents carry few or no gold entities, and the exact-slot
   `_prf` scores an empty-gold/empty-prediction sample 0.0, so the naive "the extraction gain is
   just the matching gain" story is not even directionally right in the marginal frame — which is
   exactly why the marginal reweighting term comes out negative and the residual term swallows
   everything.
3. **On A2T the two orderings are near-identical and sum to zero**, consistent with the joint view's
   flat zero.

Both orderings are published because a two-term Oaxaca decomposition is path dependent; the joint
concordant/discordant split has no such freedom.

---

## 7. TWO-AXIS SCOREBOARD — `matching | extraction`, one row per landed cell

This table replaces the matching-only scoreboard. A matching gain must never again be reported
without the extraction number that belongs beside it.

| carrier | population | arm | **matching** | **extraction** | n |
|---|---|---|---|---|---|
| SLURP (slot-SLU) | DEV-1000-NEW500 (UNEXPOSED) | M0 | `scenario_action_exact` **0.5560** (278) | `slot_f1_exact_mean` **0.170976** · micro `slot_f1_exact` 0.247375 · official `slu_f1` 0.376674 | 500 |
| SLURP (slot-SLU) | DEV-1000-NEW500 (UNEXPOSED) | BLEND | `scenario_action_exact` **0.7580** (379) | `slot_f1_exact_mean` **0.206414** · micro `slot_f1_exact` 0.298122 · official `slu_f1` 0.430813 | 500 |
| SLURP (slot-SLU) | DEV-500 (PRIOR-EXPOSED) | M0 | `scenario_action_exact` **0.5160** (258) | `slot_f1_exact_mean` **0.122248** · micro `slot_f1_exact` 0.189889 · official `slu_f1` 0.361130 | 500 |
| SLURP (slot-SLU) | DEV-500 (PRIOR-EXPOSED) | BLEND | `scenario_action_exact` **0.7560** (378) | `slot_f1_exact_mean` **0.150971** · micro `slot_f1_exact` 0.245259 · official `slu_f1` 0.402267 | 500 |
| Audio2Tool | A2T-G1-104 (EXPOSED) | M0 | `tool_accuracy` **0.596154** (62) | `exact_match` **0.278846** (29) · slot micro-F1 0.437870 · P(EM \| tool correct) 0.467742 | 104 |
| Audio2Tool | A2T-G1-104 (EXPOSED) | BLEND | `tool_accuracy` **0.605769** (63) | `exact_match` **0.278846** (29) · slot micro-F1 0.412088 · P(EM \| tool correct) 0.460317 | 104 |

Read across, not down: on both carriers the matching column moves and the extraction column
either does not move (A2T exact match: 29 → 29) or moves mostly because the matching column did
(SLURP). The A2T slot micro-F1 and the SLURP conditioned cells move the **wrong way**.

---

## 8. VERDICT — does the supply serve extraction, on either carrier?

**NO — not where it matters, on either carrier.**

1. **Conditional on matching, extraction does not move.** SLURP unexposed, both arms matched
   (n = 273, 54.6% of the population): macro slot-F1 **−0.1221 pts** (CI90 straddles zero), micro
   slot-F1 **exactly 0.0000** (identical TP/FP/FN), official SLU-F1 **+0.0894 pts** (CI90 straddles
   zero). A2T, both arms matched (n = 60, 57.7%): exact match **0.0000 pp** with **zero discordant
   pairs**, and slot micro-F1 **−0.6244 pts**. SLURP exposed, both arms matched (n = 255): official
   SLU-F1 **−1.6351 pts, CI90 [−3.2291, −0.1108], excluding zero** — the only conditioned interval
   in this reading that separates from zero, and it is negative.
2. **The SLURP aggregate extraction gain is mostly the matching gain.** (a) accounts for **71.8%**
   of +3.5438 pts on the unexposed half and **98.4%** of +2.8724 pts on the exposed half. The
   original suspicion is confirmed on the exposed half almost completely, and on the unexposed half
   substantially.
3. **The residual matching-independent signal is real but does not support the claim.** On the
   unexposed half it is +1.0000 point, and +1.0667 of that sits in the **neither-matched** cell —
   samples where *both* arms got the intent wrong (+4.5977 macro pts, CI90 [+1.7241, +7.7586];
   +10.8371 official SLU-F1 pts, CI90 [+6.3169, +15.7389]). So the supply *does* put usable slot
   content in front of the core — but only where the direct answer's intent was already wrong, and
   it adds nothing on top of an already-correct intent. It does **not** replicate on the exposed
   half at the macro level (+1.3165, CI90 straddles zero).
4. **On A2T the answer is flatly no, and the finer measure is negative.** The zero exact-match
   delta is a genuine zero in every cell, not a cancellation; the widening gap is arithmetically
   just the matching gain with no extraction following it; and the supply's only measurable
   extraction effect is **−2.5781 slot micro-F1 points**, produced by 26 extra predicted argument
   triples carrying exactly one extra true positive.

**What this means for the architectural claim.** The knowledge plane demonstrably owns *matching*.
The measured evidence does **not** support the second half — "supplies enough information for
extraction" — as a property that operates once matching is correct. What the evidence supports is
narrower and should be stated that way: *the supply repairs whole answers whose intent was wrong,
and the extraction score follows the repaired intent.* Any future claim about extraction needs its
own conditioned statistic on an **unexposed** population with adequate n, not the aggregate.

---

## 9. HARD STOP — what this document does NOT authorize

- **It does NOT revise, re-tune or restate the DEV-1000 LOCK.** The SLURP unexposed-500 conditioned
  statistics are a SECONDARY reading on the locked baseline's population and are descriptive only.
  The lock stands exactly as landed at `d9fef537`.
- **No knob change, no re-tune, no re-flight, no new arm, no threshold move.** In particular the
  neither-matched-cell signal is NOT a licence to re-fit the alpha gate, the retain-override bar,
  the ranker, the fuser or the supply budget.
- **No claim.** No generality claim, no superiority claim, no cross-carrier transfer claim, no
  conclusion about the method's extraction capability beyond these two already-read populations.
- **No test contact, no FINAL60 contact, no new population**, and no G2 opening. The A2T numbers
  are a secondary reading on an EXPOSED n = 104 that sits below the campaign plan's own power
  floor; the `blend_only` (n = 3), `m0_only` (n = 2 and n = 5, n = 3) cells are MECHANISM readings
  and can never be cited as effect sizes.
- **No Stage-3 activity of any kind**, no manuscript, no paper-scale profile, no promotion.
- **Nothing here puts gold on a runtime path.** Gold was opened strictly scoring-side over
  populations whose seal the landed lock read and the landed G1 read had already broken.
