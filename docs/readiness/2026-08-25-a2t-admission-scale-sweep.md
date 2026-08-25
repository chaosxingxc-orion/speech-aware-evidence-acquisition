# A2T ADMISSION-SCALE DEFECT — the offline audit and the FIX SPECIFICATION

Date: 2026-08-25. Status: **ITERATION-TIER DESIGN INPUT — computed, ZERO CONTACTS, every fidelity
gate passed.** Row `SAEA-SN-MF-A2T-ADMISSION-SCALE-SWEEP` (registered `e9656577`, **before any
computation**). Module `src/speech_aware_evidence_acquisition/analysis/a2t_admission_scale_sweep.py`.
Receipt `docs/checks/speech-aware-evidence-acquisition/2026-08-25-a2t-admission-scale-sweep/sweep-report.json`
(sha256 `88f606fe89eb42e675bdd4832a31b028638613eba71d712d3d4ee6cf7aa74d66`).

**Spend: 0 frozen-core contacts, 0 embedding-tool contacts, 0 tokenizer contacts, 0 audio seconds,
0.0 GPU hours, 0 new dependencies. The offline guard was armed before the first input was opened and
recorded 0 outbound connection attempts against 0 targets. The resident np2 A2T service on port 8090
was never contacted, probed, reconfigured or stopped. Wall 152.1 s.**

---

## 0. The correction this document carries, stated before anything else

> **THE ZERO-DISPATCH ON AUDIO2TOOL IS AN IMPLEMENTATION DEFECT IN THE RANKER.** Owner ruling,
> adopted here as settled and not re-argued: summing an *unbounded* prior mass with a cosine that is
> *bounded by 1* inside one weighted score compares incommensurable quantities. It is a bug, not a
> design trade-off and not a paradigm boundary.
>
> **THE STAGE-G1 "PAIRED FIRST SIGNAL" THEREFORE MEASURED A BROKEN CONFIGURATION.** The BLEND arm
> flew a supply path that could not fire on this carrier for reasons that have nothing to do with
> Audio2Tool. **No paradigm-level conclusion about Audio2Tool follows from it** — not that the cell
> fails to transfer, not that the carrier is unreachable, not that the method is inert here.
>
> The mechanical half of G1 stands: the arm landed 104/104, the derived `-np 2` geometry serves the
> carrier, and the −1.92 pp paired delta is still fully attributed to the frozen core's multi-slot
> decode-variance channel (0 trajectories dispatched, so the two arms could differ only where the
> core's own decode of the same prompt differed). What is void is the arm's standing as a *test of
> the paradigm*.

This document is the **specification and verification material for the fix**. A separate agent
implements it; §6 is written to be acted on directly, and §7 lists the regression obligations that
prove the implementation correct.

---

## 1. Provenance — which ranker these numbers audit

An audit of a defect must run against the code that carries the defect. While this analysis was
running, a concurrent agent began implementing the repair in the same checkout. Rather than race it,
the audit was re-run against a **read-only export** of the pre-fix module; the main checkout was
never modified.

| | value |
|---|---|
| `rails/kb_policy.py` git blob | `6abb55d8f807c99f60318ae946aee748fb845110` (commit `401418cd`) |
| source sha256 as imported | `eed40ee51608b76817cf3ec9387305cbd05fe459117723828c06bc4fb55324d4` |
| carries a dimension normalization | **no** (`_dimension_scales` absent) — asserted at start-up |
| recorded state | `pre-fix` (the run refuses to proceed if it imports the other state) |

**The semantic half of the same check is stronger than the hash.** The `V0-FROZEN` fidelity gate
requires the baseline replay to reproduce the **flown** decision and supply on every trajectory —
which only the ranker that flew can do:

| gate | result |
|---|---|
| A2T V0-FROZEN reproduces the flown retain/dispatch decision | **104 / 104** |
| A2T V0-FROZEN reproduces the flown supply | **104 / 104** |
| SLURP flight replay (via `cf.replay_population`, its own gate) | 497/500 decisions, **163/163 supply** |
| the 3 SLURP decision deviations | **all three are exactly the v2 δ-override fires**, 0 unexplained |
| vectorised recall vs a real `kb.multidim_recall` call | 8 probes per carrier, exact to 1e-9 |
| A2T query texts re-hash to their own landed query-vector digests | **104 / 104** |
| locked cell `kb-policy-v1-dev100.json` proved key-for-key | PASS (`d68afd2c…a919`) |

**Reuse, never reimplementation.** Recall runs through `contrast_fewshot_preanalysis.vectorised_recall`;
ranking, admission, fusion and the blend head through
`dev100_damage_channel_analysis.replay_supply` / `replay_blend`, which call `kb_policy`'s registered
ranker, registered fuser, `_fused_label_scores`, `_blend_scores` and `_argmax_labels` directly.
Audio2Tool answers are scored by the frozen `a2t-scorer-v1` via `Audio2ToolAdapter.score`. Conversion
anchors are imported from `k1_hybrid_ranking_gate`. **Exactly two functions wrap rather than call,
and each says so in its own docstring**: `_per_dimension_supply` (hands the registered fuser a
`RankResult` restricted to the cosine-family facets, so its own `candidates[:m]` slice *is* a
per-dimension window) and `_split_scale_supply` (splits the mapping the ranker scores from the
mapping the fuser admits on, which a rank-based combiner forces — see §5).

---

## 2. The scale audit — the specification material

### 2.1 The ranker, and the term that quietly disappears

`saea-rank-wcos-prior-agree-v1` forms

```
score(f) = w_cos · max_cosine(f) + w_prior · max_prior(f) + w_agree · agreement(f)
         = 0.5  · max_cosine(f) + 0.3    · max_prior(f) + 0.2    · agreement(f)
```

**The agreement term is degenerate on both carriers and cancels exactly.** Measured, not assumed:
`dims_total = 3` on every trajectory, and **every recalled facet carries exactly one dimension** —
1,560 of 1,560 recalled facets across the 104 A2T trajectories, 7,500 of 7,500 across the 500 SLURP
trajectories. So `agreement = 1/3` for every candidate, contributing a constant 0.0667 to all of
them. **Ranking is decided by `0.5 · max_cosine` against `0.3 · max_prior`, and by nothing else.**

A second measured fact that matters for the fix: **no content facet ever carries prior mass, on
either carrier.** Prior-mass recall reads the `label` and `prior` dimensions only. So the comparison
that decides the window is *always* a content COSINE against a prior MASS — two different scales
inside one sum, on both carriers, always. SLURP did not avoid the mixed comparison; it merely
survived it.

### 2.2 The cosine dimension

| best content cosine per trajectory | A2T (n=104) | SLURP DEV-1000 NEW500 (n=500) |
|---|---|---|
| min | **0.7594** | 0.6182 |
| p10 | 0.7740 | 0.7512 |
| median | **0.8736** | 0.8399 |
| mean | 0.8654 | 0.8341 |
| p90 | 0.9176 | 0.9015 |
| max | **0.9572** | 0.9439 |
| clears τ = 0.65 | **104 / 104** | 498 / 500 |
| `w_cos · max` | 0.4786 | 0.4720 |
| `w_cos · τ` (the weakest *admissible* content facet) | **0.3250** | 0.3250 |

Content-facet recall on Audio2Tool is not merely adequate, it is **stronger than SLURP's** on every
quantile. Retrieval was never the problem.

### 2.3 The prior-mass dimensions

Prior-mass recall reads no vector, so its candidate set and its scores are **identical for every
trajectory** on a given snapshot. Both carriers recall 10 facets (top-5 of `label` plus top-5 of
`prior`, which are the same five tools/intents seen through two dimensions).

| recalled prior masses, descending | A2T | SLURP |
|---|---|---|
| 1–2 | **4.1000, 4.1000** | 1.0000, 1.0000 |
| 3–4 | **2.4938, 2.4938** | 1.0000, 1.0000 |
| 5–6 | **1.9560, 1.9560** | 0.9810, 0.9810 |
| 7–8 | **1.5275, 1.5275** | 0.8706, 0.8706 |
| 9–10 | **1.1908, 1.1908** | 0.8512, 0.8512 |
| snapshot sup | **4.1000** | **1.0000** |
| `w_prior · sup` | **1.2300** | **0.3000** |

**All ten recalled A2T prior-mass facets are outside the declared `[0, 1]` range.** Facet inventory:
A2T 12,601 content / 184 label / 151 prior; SLURP 11,514 content / 151 speaker / 138 label / 60 prior
(the speaker dimension recalls nothing — no speaker query vector is supplied).

### 2.4 The invariant the locked cell silently relied on

Because the agreement term cancels, a content facet outranks a prior-mass facet exactly when
`w_cos · cos > w_prior · prior`. The weakest content facet that percept admission can ever accept has
`cos = τ`. Therefore:

> **COMMENSURABILITY INVARIANT.** Every *admissible* content facet outranks every prior-mass facet
> **if and only if**
>
> `w_prior · sup(prior_score) < w_cos · τ`,
>
> i.e. **`sup(prior_score) < w_cos · τ / w_prior = 0.5 × 0.65 / 0.3 = 1.08333`**.

| | sup(prior) | required bound | inside? | margin |
|---|---|---|---|---|
| SLURP | **1.0000** | 1.08333 | **yes** | **+0.0833** (7.7 % of the bound) |
| Audio2Tool | **4.1000** | 1.08333 | **no** | **−3.0167**, a **3.78×** violation |

**Why SLURP was inside the bound, and why nothing enforced it.** `rails/knowledge_build.py` sets
`prior_score = intent_total_in_scenario / scenario_total`, and an intent is nested strictly inside its
scenario, so the numerator's row set is *contained* in the denominator's and the ratio is a genuine
conditional probability — it cannot exceed 1. The cell was inside the bound **by construction**, so
no code had to check it. `rails/knowledge_build_a2t.py:1087` sets
`prior_score = tool_total / category_total`, where `rows_by_tool_full` counts a tool name across
*every* `(domain, category)` while `rows_by_category_full` counts *one*. Tool → (domain, category) is
not a function on this corpus — the G0 report's own §1.1 finding that `tool_id` is not a join key and
that ten tool ids carry a different `tool_name` in the manifests than in the registry. **The
containment that made the SLURP ratio a probability does not hold on Audio2Tool**, so the same
defective ranker produced a correct-looking ordering on one carrier and a fully inverted one on the
other.

The SLURP margin is **0.0833**. That is how much slack the locked baseline was running on, and
nobody knew.

### 2.5 The eviction, measured

| | A2T (n=104) | SLURP (n=500) |
|---|---|---|
| content facets in the top-`m`=5 window (min / median / max) | **0 / 0 / 0** | 1 / 5 / 5 |
| trajectories with ZERO content facets in the window | **104 / 104** | **0 / 500** |
| admissible content facets per trajectory (min / mean) | 5 / 5.0 | 0 / 4.946 |
| prior facets ranked above the BEST content facet (min / median / max) | **6 / 8 / 8** | **0 / 0 / 0** |
| prior facets above the WEAKEST admissible content facet (min / median / max) | **6 / 8 / 10** | **0 / 0 / 0** |
| trajectories where any prior facet outranks an admissible content facet | **104 / 104** | **0 / 500** |
| `m` needed to admit every admissible content facet | **15** | **5** |

Read the last row twice. **On SLURP the frozen `m = 5` is exactly sufficient and not one more** — the
invariant guarantees the admissible content facets occupy the head of the ordering, and the recall
cap `top_k_per_dimension = 5` bounds how many there can be. The cell is internally consistent, but
only *conditionally* on an invariant it never states. On Audio2Tool you would need `m = 15`, which is
`|PRIOR_MASS_DIMENSIONS| × top_k + top_k`.

---

## 3. What a correct implementation should choose

Every variant below is a single change to the ranker/fuser scale handling, replayed through
`kb_policy`'s own pure functions over the 104 landed Pass-A trajectories. **The verdicts are driven by
a property table fixed independently of the Audio2Tool numbers** — the question is which form is
*principled*, never which form scores best on one carrier.

### 3.1 The A2T variant table

Token figures are **ESTIMATES** against the derived 32,768-token slot (§4).

| variant | the single change | dispatch | gold-bearing supply (of 104) | content in top-`m` | supply ≠ frozen | supplied values | est. tokens/slot | est. margin |
|---|---|---|---|---|---|---|---|---|
| **V0-FROZEN** | none — the cell as flown | **0** | 0 | 0 | 0 | 0 on all 104 | 14,678 | +18,090 |
| **A1-CLIP1** | `min(mass, 1.0)` | 15 | 68 | 5 on all 104 | 104 | 2:35 3:28 4:36 5:5 | 16,457 | +16,311 |
| **A2-GLOBALMAX** | ÷ snapshot sup | 15 | 68 | 5 on all 104 | 104 | 2:35 3:28 4:36 5:5 | 16,457 | +16,311 |
| **A6-DIMSUP-FLOOR1** | ÷ `max(1, sup over recalled)` — **the landed repair** | 15 | 68 | 5 on all 104 | 104 | 2:35 3:28 4:36 5:5 | 16,457 | +16,311 |
| A3-MINMAX-Q | per-query min-max | 15 | 68 | 5 on all 104 | 104 | 2:35 3:28 4:36 5:5 | 16,457 | +16,311 |
| A4-Z-Q | per-query z-score | 15 | 67 | **3** on all 104 | 104 | 2:45 3:59 | 15,958 | +16,810 |
| A5-RRF-DIM | `1/(60+rank)` per dimension | 15 | 68 | 5 on all 104 | 104 | 2:35 3:28 4:36 5:5 | 16,457 | +16,311 |
| B1-M8 | `m` 5 → 8, scale untouched | **0** | 12 | 13 trajectories only | 13 | 0:91 1:7 2:6 | 15,240 | +17,528 |
| B2-M16 | `m` 5 → 16, scale untouched | 15 | 68 | 5 on all 104 | 104 | 2:35 3:28 4:36 5:5 | 16,457 | +16,311 |
| B3-M32 | `m` 5 → 32, scale untouched | 15 | 68 | 5 on all 104 | 104 | 2:35 3:28 4:36 5:5 | 16,457 | +16,311 |
| C1-PERDIM | per-dimension top-`m` | 15 | 68 | 5 on all 104 | 104 | 2:35 3:28 4:36 5:5 | 16,457 | +16,311 |
| D1-CLIP1-M8 / D2-CLIP1-M16 / D3-CLIP1-PERDIM / D4-MINMAXQ-PERDIM | combinations | 15 | 68 | 5 on all 104 | 104 | 2:35 3:28 4:36 5:5 | 16,457 | +16,311 |

### 3.2 The SLURP identity proof — the binding obligation, discharged by measurement

Every variant, including every rejected one, was replayed over the sealed DEV-1000 NEW500 flight
through the identical code path:

> **All 15 variants: admitted set differs on 0 / 500, supply differs on 0 / 500, dispatch differs on
> 0 / 500. Every candidate form is an EXACT IDENTITY on the locked SLURP cell.**

The proof is structural, not lucky. (a) No content facet carries prior mass, so no rescaling of prior
mass touches a content facet's score. (b) SLURP's invariant holds, so every admissible content facet
already outranks every prior-mass facet; a transform of the prior-mass scores therefore only reorders
facets that can never be percept-admitted and can never be the maximum `facet_score` of any candidate
value (`w_cos · τ = 0.325 > w_prior · 1.0 = 0.300`). The locked cell's behaviour is provably
unchanged.

### 3.3 The verdicts

| variant | verdict |
|---|---|
| **A2-GLOBALMAX** | **PRINCIPLED FIX** — bounded, order-preserving, query-independent, one change |
| **A6-DIMSUP-FLOOR1** (landed) | **PRINCIPLED FIX** — bounded, order-preserving, query-independent, one change |
| A1-CLIP1 | ACCEPTABLE GUARD — bounded, auditable and SLURP-identical, but **not order-preserving**: it flattens every mass above 1 into a tie, so it guards against an out-of-contract prior rather than normalizing one |
| A3-MINMAX-Q | **REJECTED** — the same facet scores differently depending on what else a query recalled; also forces the weakest recalled prior to exactly 0 whatever its true mass, and is undefined when a dimension recalls one candidate |
| A4-Z-Q | **REJECTED** — a z-score is not bounded at all, so it does not restore commensurability. Measured: at `m = 5` it still leaves the **two heaviest prior facets above every content facet**, admitting 3 content facets instead of 5 |
| A5-RRF-DIM | **REJECTED** — forces a SECOND change, to the admission path, because `τ` lives on the cosine scale; and it discards the magnitudes the fuser uses to rank task targets and order values within a target |
| B1-M8 / B2-M16 / B3-M32 | **NOT A FIX** — moves the window while leaving the incommensurable scale in place |
| C1-PERDIM | **NOT A FIX** — same objection: it moves the window's *scope* rather than the scale, and leaves the ranker's own `facet_score` still mixing scales for `_fused_label_scores` |
| D1–D4 | carry a correct normalization but bundle an unnecessary window change with it |

**Why raising `m` is not the lever, in one line each.** `m = 8` fixes *nothing* — 0 dispatch, and a
content facet reaches the window on only 13 of 104 trajectories. `m = 16` works, but only because the
recalled prior-mass pool happens to be exactly `|PRIOR_MASS_DIMENSIONS| × top_k = 10`; `m` would have
to track that product forever, and the coupling breaks silently the moment a dimension is added or
`top_k` moves. A fix whose correctness depends on an arithmetic coincidence between two unrelated
knobs is not a fix.

### 3.4 The landed repair, machine-checked against the audit's own recommendation

The audit derived **A2-GLOBALMAX** (divide a prior-mass dimension by the snapshot's supremum) from
the property table alone. The landed `_dimension_scales` divides every dimension by
`max(1.0, sup over the recalled set)`. These are the same rule in practice, and the receipt proves it
rather than asserting it:

| | trajectories | where the two rules differ |
|---|---|---|
| Audio2Tool | 104 | **0** |
| SLURP DEV-1000 NEW500 | 500 | **0** |

Two lemmas make the landed form deterministic despite reading the recalled set, and both are worth
keeping in the implementation's docstring:

1. **On a cosine-family dimension the sup cannot exceed 1**, so the divisor is exactly `1.0` and the
   transform is the identity — which is precisely why `τ` keeps its meaning.
2. **On a prior-mass dimension the recalled sup IS the snapshot sup**, because `multidim_recall`
   truncates each dimension by *descending* score and therefore always retains that dimension's
   maximum. The apparent query-dependence is provably inert for exactly the dimensions that need
   fixing.

---

## 4. The evidence prompt still fits, comfortably

The token model is calibrated against the **already-landed** `prompt-fit-np2.json` receipt, whose two
envelopes were measured by the resident tokenizer at a registered contact: 13,236 text tokens direct
vs 19,047 worst-case evidence, a difference of exactly **5,811** tokens for the evidence block.
Reconstructing that block locally gives 19,109 characters, hence **3.2884 characters per token**.
Nothing is tokenized here.

The constant is deliberately conservative: the landed worst case also counted five key facets, which
`rails.runner._agent_messages` never renders for this controller because the controller leaves
`visible_facet_ids` empty — the real evidence block carries **values only**.

| | est. required per slot | derived slot | est. margin |
|---|---|---|---|
| V0-FROZEN (no supply) | 14,678 | 32,768 | +18,090 |
| every repaired variant (worst trajectory, 5 values) | **16,457** | 32,768 | **+16,311** |

**The derived `-np 2` geometry serves the repaired supply path with roughly half the slot unused.**
Serving geometry is not a blocker and does not need re-deriving.

---

## 5. Forward-looking material for the post-fix re-flight

### 5.1 The α gate — a SECOND ceiling that the admission fix does not touch

This is the most important thing in this document after the defect itself, and it was found by the
sweep rather than looked for.

`kb._blend_scores` gives the direct label `α · f + (1 − α)` and every rival `α · f`, while
`kb._fused_label_scores` normalizes the fused scores to sum to 1, so no `f` can exceed 1. At the
frozen `α = 0.45`:

```
blended[direct] ≥ 1 − α = 0.55        blended[rival] ≤ α = 0.45
```

**Whenever a direct label is recovered at all, it wins uniquely, for EVERY possible supply.** This is
arithmetic, not an empirical regularity, and it holds for any `α < 0.5`. Admission repair cannot
change it.

| | A2T (104) | SLURP NEW500 (500) |
|---|---|---|
| direct label recovered | 89 | 340 |
| **label-free — the entire reachable set** | **15 (14.4 %)** | **160 (32.0 %)** |

Two consequences:

- **The repaired supply path can act on at most 15 of the 104 A2T trajectories.** Audio2Tool's direct
  decode produces a parseable in-vocabulary tool name more than twice as often as SLURP's produces a
  recoverable intent, which *halves* the surface evidence can reach. That is a property of the
  carrier, and it is a real finding — unlike the zero-dispatch, which was a bug.
- **`retain == direct-label-recovered` is RESTORED by the fix.** G1 reported that invariant as
  FALSIFIED on this carrier. Under every repaired variant the dispatch set equals the label-free set
  exactly (0 dispatched outside it, 0 label-free left undispatched). The "falsification" was the bug
  talking.

The 15 label-free ids are enumerated in the receipt
(`audio2tool.alpha_gate.label_free_sample_ids`) — 6 of them in `tier4_implicit`, which is the tier
whose A0 bottleneck was already known to sit upstream of arguments.

### 5.2 The decisive quantity

Scored by the frozen `a2t-scorer-v1` over the landed answers: **60 of 104 correct today (0.5769
tool accuracy), 44 wrong.** Under the repaired ranker:

| | value |
|---|---|
| would dispatch | **15** |
| of those, currently WRONG | **15** |
| of those, currently CORRECT | **0** — the supply path cannot disturb a single correct trajectory |
| wrong-today **with the gold tool's facet inside the admitted window** | **4** |
| wrong-today with gold-bearing supply | **4** |
| … with gold at fused target rank 1 | **2** |
| … with gold at fused target rank 2–3 | **2** |
| … with gold absent from supply | **11** |
| trajectories retaining and carrying their own score exactly | 89 |

**The ceiling if the α gate did not exist**, for sizing a future α question and nothing else: 68 of
104 trajectories would carry gold-bearing supply — **13 of the 44 wrong-today** and 55 of the 60
correct-today.

### 5.3 The projected band — CROSS-CARRIER, and labelled as such everywhere

> **AUDIO2TOOL HAS NO MEASURED CONVERSION ANCHORS OF ITS OWN.** The band below prices an Audio2Tool
> trajectory at a rate measured on SLURP spoken-SLU intent recovery — a different task, a different
> label space, a different answer shape and a different frozen-core failure profile. It is a DESIGN
> INPUT for sizing a flight, never a result. **The first dispatching Audio2Tool flight is what would
> establish this carrier's own anchors.**

Anchors imported from `k1_hybrid_ranking_gate`: gold at fused top-1 converts at 108/110 = 0.9818;
at fused rank 2–3 at 16/23 = 0.6957; absent at 0/67 = 0.0.

| | correct of 104 | Δ vs the landed 60 |
|---|---|---|
| pessimistic (every changed trajectory priced one rank-band worse) | 62.78 | **+2.68 pp** |
| **central** | **63.35** | **+3.23 pp** |
| optimistic | 63.93 | **+3.78 pp** |

**Read this against the noise floor before reading it as a gain.** At n = 104 one sample is 0.96 pp,
so the central projection is ≈3.4 samples. G1 measured this carrier's own multi-slot decode-variance
channel at **1.9 pp of score noise and 11 of 104 divergent texts**. A projected central effect of
+3.2 pp is under 2× that noise floor: **a repeat of the 104-item exposed subset cannot resolve it**,
whatever the fix does. Any post-fix flight that wants a first signal needs either a materially larger
n or a paired design that removes the decode-variance channel.

---

## 6. THE FIX SPECIFICATION

### FIX-1 — normalize every ranker dimension onto one bounded scale (REQUIRED, `rails/kb_policy.py`)

Before the weighted sum, divide dimension `d`'s recalled scores by `max(1.0, sup_d)`, where `sup_d`
is that dimension's largest score over the recalled candidate set. Apply it **uniformly** — prior-mass
dimensions are not special-cased. This is the rule `_dimension_scales` implements, and §3.4 confirms
it is behaviourally identical to the audit's independently derived recommendation on 104/104 A2T and
500/500 SLURP trajectories.

The properties the implementation must preserve, each of which a reviewer will check:

1. **Bounded output.** Every dimension lands in `[0, 1]`, the range `w_cos`/`w_prior`/`w_agree` were
   chosen against.
2. **Order-preserving** within a dimension. (This is what rules out `clip1` as the primary form.)
3. **Effectively query-independent**, by the two lemmas in §3.4 — state both in the docstring, they
   are what makes the rule auditable.
4. **One change, confined to the ranker.** `τ` must keep reading raw cosines; percept admission must
   not move. (This is what rules out a rank-based combiner.)
5. **Divisor ≥ 1 by construction**, so the rule can neither divide by zero nor amplify a score.
6. **Parameter-free.** The only constant is the bound `1.0`, which is the theoretical range of
   cosine and agreement, not a tuned value. It must not become a knob.

### FIX-2 — assert the invariant fail-closed (RECOMMENDED)

Add a fail-closed check at policy-load / snapshot-bind time: every dimension's `sup` must be inside
`_DIMENSION_SCORE_BOUND`, or equivalently `w_prior · sup(prior) < w_cos · τ`. **Refuse rather than
silently rank.** SLURP passes with margin 0.0833; Audio2Tool fails by 3.78×. A silent violation of
this bound cost this program three BLEND flights and one void first signal. FIX-1 makes the ranker
robust; FIX-2 makes the *next* violation visible instead of silent.

### FIX-3 — the root cause, upstream (SEPARATE AUTHORIZATION)

`rails/knowledge_build_a2t.py:1087` computes `prior_score = tool_total / category_total` with a
numerator counted across every `(domain, category)` and a denominator counted within one. That is not
`p(tool | category)`, which is what the G0 report and `kb_policy`'s own docstring declare it to be.
Either restrict the numerator to the same `(domain, category)` or rename the field to what it
actually measures. Separately, `ValueBundle.validate` in `rails/knowledge.py` should refuse a
`prior_score` outside `[0, 1]`, so this class of defect becomes a build-time refusal.

**This is deliberately NOT bundled with FIX-1.** `rails/knowledge.py` and `rails/knowledge_build.py`
are byte-frozen and cited by the baseline lock; touching them re-hashes snapshots and carries its own
authorization cost. FIX-1 makes the ranker correct regardless of what a builder emits, which is the
right layering: **the ranker should not trust its inputs' scale.**

### FIX-4 — what NOT to bundle

Do **not** change `m`, `τ` or `α` as part of this repair. §3.3 shows `m` is not the lever; `τ` is
defined on the cosine scale FIX-1 deliberately leaves untouched; `α` is the second ceiling of §5.1 and
moving it is a knob change with its own preregistration and its own effect on the locked SLURP
baseline. One defect, one change.

---

## 7. Regression obligations — how to prove the fix correct

| # | obligation | expected result |
|---|---|---|
| **R1** | Replay the sealed SLURP DEV-1000 NEW500 flight under the fixed ranker | admitted set, supply and dispatch **identical to the frozen cell on 500 / 500** (already measured here for every candidate form) |
| **R2** | Replay the sealed DEV-100 rounds 4/5 and DEV-500 NEW400 supply | reproduced exactly, as `cf.replay_population`'s own gate requires |
| **R3** | Re-run `analysis.a2t_admission_scale_sweep --expect-state post-fix` | **the A2T `V0-FROZEN` gate MUST FAIL** (it reproduces the *defective* flown behaviour by design) while the SLURP flight-replay gate still reports 497/500 decisions with 3 explained v2 override fires and 163/163 supply. That pair is the regression test. |
| **R4** | A2T dispatch count under the fixed ranker | **0 → 15**, and the dispatch set must equal the 15 label-free ids exactly (`audio2tool.alpha_gate.label_free_sample_ids` in the receipt) |
| **R5** | A2T admitted content facets under the fixed ranker | 5 on all 104 trajectories; supplied-value distribution 2:35 3:28 4:36 5:5 |
| **R6** | Prompt fit | unchanged — est. 16,457 of 32,768 per slot, no re-derivation of serving geometry needed |

R3 deserves emphasis: this audit module is written so that **its own baseline gate becomes the
regression test**. It refuses to run against the wrong ranker state (`--expect-state`), it records
the imported `kb_policy` source sha256 in every receipt, and its `V0-FROZEN` verdict is the semantic
proof of which ranker produced the numbers.

---

### 7.1 The obligations, RUN against the landed fix

The repair landed at commit `1341c2db` while this audit was being written
(`rails/kb_policy.py` source sha256 `2a1c3d75e747db10f723044b05c08d232e1edf47f125d0889c1d2565ba1019af`,
`_dimension_scales` present). The obligations above were then executed against it — offline, zero
contacts, offline guard armed, nothing written into the repository. **Every one passes, and every
predicted number matches exactly:**

| # | obligation | required | measured against the landed fix |
|---|---|---|---|
| R3 | A2T `V0-FROZEN` gate | **must FAIL** | **False** — it no longer reproduces the flown zero-dispatch |
| R4 | A2T dispatch count | 0 → **15** | **15** |
| R4 | A2T dispatch set == the 15 label-free ids | exact | **exact** — 0 dispatched outside it, 0 label-free left undispatched |
| R5 | trajectories with an admitted content facet | 104 | **104 / 104** |
| R5 | supplied-value distribution | 2:35 3:28 4:36 5:5 | **2:35 3:28 4:36 5:5** |
| R5 | gold-bearing supply | 68 | **68** |
| R1 | SLURP flight-replay decisions | 497/500, the 3 being v2 override fires | **497 / 500**, all three explained |
| R1 | SLURP flown SUPPLY reproduced | 163/163 | **163 / 163** |
| R1 | SLURP `V0-FROZEN` gate | **must still PASS** | **True** |
| R1 | SLURP dispatch under the fix | 160 (the label-free set) | **160** |

**The locked SLURP baseline is byte-unchanged by the repair, and Audio2Tool's supply path now fires
on exactly the trajectories the arithmetic says it can reach.** FIX-2 (the fail-closed invariant
assertion) and FIX-3 (the upstream `prior_score` repair and the `ValueBundle` range refusal) remain
open; neither blocks the ranker, and FIX-3 carries its own authorization cost against the byte-frozen
builder modules.

---

## 8. What this document does NOT license

No flight, no contact, no G2 opening, no knob change beyond the specified defect repair, no test
contact, no generality or superiority claim, and no Stage-3 activity. Gold was opened only over the
EXPOSED A2T-G1-104, whose seal the landed G1 read had already broken; the SLURP populations were read
at their own registered seals. `consumed` stays `no`. The operational debt from G1 stands: **the SLURP
np8 service remains DOWN and must be respawned by a later mission before any SLURP arm flies.**

And the correction, once more, because it is the reason this document exists: **the A2T stage-G1
BLEND arm measured a broken configuration. Its mechanics stand; its standing as a test of the
paradigm does not.**
