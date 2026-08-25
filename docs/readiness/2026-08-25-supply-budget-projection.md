# SUPPLY BUDGET (`fusion.c` / `fusion.top_l`) — model-free projection and registered prediction

Date: 2026-08-25. Status: **DESIGN INPUT — no verdict, no knob selected, no round authorized.**
Profile: `model-free-check`. Exposure row `SAEA-SN-MF-SUPPLY-BUDGET-PROJECTION` (registered before
any computation; **0** frozen-core contacts, **0** embedding-tool contacts, **0** tokenizer
contacts, **0** audio seconds, **0.0** GPU hours).

K-WIDEN round K1 measured the width lever inert and named the `c`/`top_l` supply budget as the
binding constraint (`2026-08-24-kwiden-and-next-experiments-queue.md` §2a). This note asks the
follow-on question — does raising that budget put gold INTO the supplied set where it is currently
absent, and at what cost — and answers it over the three sealed populations. It selects nothing.

**The short version.** At the frozen cell the supply budget is **not binding at all**: no flown
trajectory ever filled `c·top_l = 6`, and an *unlimited* budget at the frozen width puts gold into
the supply on **0 of 600** sealed trajectories. The constraint one level up — the
`recall_top_k_per_dimension` window — is what caps the supply, and §2a's "`c·top_l` binds first"
holds only at K1's widened `m = 8`, not at the frozen `k = m = 5`.

## 1. Authority, scope, and non-contact

- Owner discipline `2026-08-23-knowledge-plane-baseline-rulings.md` §7.2 (iterate on exposed data
  before concluding); the queue's §2a stopping note that hands the lever to `c`/`top_l`.
- Consumed, all already landed and already scored: the sealed DEV-100 **round-4** and **round-5**
  frozen-cell attempt stores, the sealed DEV-500 confirmatory **BLEND** arm restricted to the
  **NEW400**, the committed round/arm reports and split receipts, the two committed tokenizer-only
  prompt-fit receipts (as token anchors only), the pinned TRAIN snapshot `e27b2745…a51b57`, and its
  landed content-facet NPZ `0bcb955a…21c72`. TRAIN **value** vectors stay SEALED and were not opened.
- Devel gold is read scoring-side only, over samples whose gold was already lawfully opened.
- **Non-contact is proven by construction, not by a service log.** The module calls
  `analysis.dev100_reviewer_audit.arm_offline_guard()` before opening a single input; measured
  **0 outbound connection attempts**. A concurrent A4 retain-override flight holds the resident
  decoder unit, so this analysis makes **no** server-log byte-identity claim and touches no file
  belonging to another campaign.
- Tool: `src/speech_aware_evidence_acquisition/analysis/dev100_supply_budget_projection.py`, a new
  sibling module that imports `dev100_next_experiment_projections`, `contrast_fewshot_preanalysis`,
  `dev100_damage_channel_analysis` and `dev100_reviewer_audit` rather than reimplementing them.
  `rails/`, `core/`, and the launchers are untouched.

### 1.1 Fidelity, re-asserted and extended

| gate | DEV-100 r4 | DEV-100 r5 | NEW400 |
|---|---|---|---|
| inherited retain/dispatch replay vs the flown contact count | **100/100** | **100/100** | **400/400** |
| inherited supply replay vs the flown SUPPLY channel | **37/37** | **33/33** | **130/130** |
| baseline-variant supply re-checked against the flown channel | **37/37** | **33/33** | **130/130** |
| derived candidate structure reproduces the REAL fuser's selection | every sample × **15 variants** | idem | idem |

The last row is the gate that makes the counterfactual sweep readable: every variant is computed by
calling the registered `saea-fuse-supplyfilter-v1` implementation, and a separately derived
candidate grouping is required to reproduce its `selected_value_ids` exactly. The analysis refuses
to run otherwise.

## 2. The saturation profile — the budget was never the binding constraint

Supplied-value counts on dispatched trajectories, at the **frozen** cell (`k = m = 5`, `c = 2`,
`top_l = 3`, nominal cap 6):

| | DEV-100 r4 (37) | DEV-100 r5 (33) | NEW400 (130) |
|---|---|---|---|
| supplied-value distribution | 1×1, 2×20, 3×8, 4×6, **5×2** | 2×17, 3×8, 4×6, **5×2** | 2×56, 3×40, 4×28, **5×6** |
| maximum supplied | **5** | **5** | **5** |
| **saturated at `c·top_l` = 6** | **0** | **0** | **0** |
| structural ceiling (infinite budget) equals `k` = 5 | 36/37 | 33/33 | 130/130 |
| structural ceiling never exceeds `k` | **true** | **true** | **true** |
| supply already equals the structural ceiling | 3 | 2 | 6 |
| unsaturated because fewer than `top_l` candidate targets | 22 | 19 | 73 |
| unsaturated because a selected target held fewer than `c` values | 6 | 6 | 20 |
| unsaturated for both reasons | 9 | 8 | 37 |
| candidate-target count | 1×21, 2×10, 3×4, 4×2 | 1×17, 2×10, 3×4, 4×2 | 1×56, 2×54, 3×8, 4×11, 5×1 |

Read plainly: **the nominal budget of six was never reached, on any trajectory, of any population.**
The reason is one level up. A candidate value must be supported by a *percept-admitted* facet, and
the admitted facets are a subset of the `recall_top_k_per_dimension` window, so the real ceiling is
`min(c·top_l, k)`. This KB build associates essentially one value with each content facet — the
structural ceiling equals `k` exactly on 199 of the 200 dispatched trajectories at `k = 5` and on
196 of 200 at `k = 8`, and never exceeds it.

At K1's flown width the picture is the one §2a reported, and the replay reproduces its shape:

| | this replay at `k = m = 8`, `c = 2`, `top_l = 3` (r4) | K1 as flown (published §2a) |
|---|---|---|
| dispatched | 37 | 36 |
| supplied-value distribution | 1×1, 2×15, 3×8, 4×6, 5×4, **6×3** | 2×13, 3×6, 4×6, 5×8, **6×3** |
| saturated at 6 | 3 | 3 |

Same shape, same maximum, same saturation count — a useful external check, though not the same
flight (K1's own direct decodes differ byte-wise, so its dispatch set and query vectors differ).
The correction to §2a is narrow but load-bearing: `c·top_l = 6` binds first **at m = 8**; at the
frozen `k = m = 5` the recall window binds first and the budget carries at least one unused slot on
every single trajectory.

## 3. Two structural facts, from the fuser's source and confirmed measurement-side

`rails.kb_policy._fuse_supply_filter` picks the `top_l` targets FIRST and only then keeps `c` values
inside each. Therefore:

1. **`c` can never put gold into the supplied set.** "Gold is in the supply" is a statement about
   *targets*; `c` only deepens targets that are already there. Confirmed on every population: every
   `c`-raising variant has exactly the same newly-gold-supplied count as its `c = 2` sibling at the
   same `top_l` — `(3,3)` = `(2,3)` and `(3,5)` = `(2,5)`, at both widths.
2. **The supply is a monotone superset in both knobs.** No trajectory *loses* a gold-bearing supply
   under any variant: **0** on all 15 variants × 3 populations.

## 4. Reachability — the briefed variants, measured

"NEW-GOLD" counts currently-**wrong dispatched** trajectories whose gold is **absent** from the
supply today and would be **present** under the variant. That absent set is **12 / 11 / 44** of the
**14 / 13 / 49** wrong dispatched trajectories (the rest are wrong despite gold being supplied).
"changed" counts dispatched trajectories whose supplied set changes at all; retained trajectories
also change but are structurally **inert** — no supply ever reaches their prompt — and are excluded.
"risk" counts currently-CORRECT dispatched trajectories whose supply changes.

| variant | nominal cap | real cap | NEW-GOLD r4 / r5 / N400 | changed (dispatched) | risk | max values |
|---|---|---|---|---|---|---|
| `(2,3)` k=5 — **frozen baseline** | 6 | 5 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 | 5 |
| `(3,3)` k=5 | 9 | 5 | **0 / 0 / 0** | 32 / 29 / 112 | 23 / 20 / 75 | 5 |
| `(2,5)` k=5 | 10 | 5 | **0 / 0 / 0** | 2 / 2 / 12 | 0 / 0 / 3 | 5 |
| `(3,5)` k=5 | 15 | 5 | **0 / 0 / 0** | 34 / 31 / 124 | 23 / 20 / 78 | 5 |
| `(4,4)` k=5 | 16 | 5 | **0 / 0 / 0** | 34 / 31 / 124 | 23 / 20 / 78 | 5 |
| **unlimited budget, k=5** | ∞ | 5 | **0 / 0 / 0** | 34 / 31 / 124 | 23 / 20 / 78 | 5 |
| `(2,3)` k=m=8 — K1 as flown | 6 | 6 | 0 / 0 / 1 | 15 / 12 / 58 | 9 / 6 / 24 | 6 |
| `(3,3)` k=m=8 | 9 | 8 | 0 / 0 / 1 | 35 / 32 / 127 | 23 / 20 / 79 | 8 |
| **`(2,5)` k=m=8** | 10 | 8 | **1 / 1 / 5** | 17 / 14 / 65 | 9 / 6 / 28 | 7 |
| `(3,5)` k=m=8 | 15 | 8 | 1 / 1 / 5 | 36 / 33 / 130 | 23 / 20 / 81 | 8 |
| `(4,4)` k=m=8 | 16 | 8 | 0 / 0 / 3 | 36 / 33 / 130 | 23 / 20 / 81 | 8 |
| **unlimited budget, k=8** | ∞ | 8 | **1 / 1 / 5** | 36 / 33 / 130 | 23 / 20 / 81 | 8 |
| `(2,5)` k=m=16 | 10 | 10 | 3 / 3 / 10 | 20 / 17 / 91 | 10 / 7 / 49 | 10 |
| **unlimited budget, k=16** | ∞ | 16 | **3 / 3 / 14** | 36 / 33 / 130 | 23 / 20 / 81 | 16 |
| **unlimited budget, k=32** | ∞ | 32 | **3 / 3 / 17** | 36 / 33 / 130 | 23 / 20 / 81 | 32 |

Three findings the coordinator should carry forward.

1. **Every briefed variant at the frozen width reaches exactly nothing.** `(3,3)`, `(2,5)`, `(3,5)`
   and `(4,4)` all return NEW-GOLD **0 / 0 / 0** — and so does an *unlimited* budget. On the 67
   gold-absent dispatched trajectories, gold's target is never among the percept-admitted candidate
   targets at `k = 5`, so no amount of budget can supply it. `top_l = 3` truncates a fourth or fifth
   candidate target on only 2 / 2 / 12 dispatched trajectories, and gold is in none of them.
2. **The budget lever only becomes live when coupled to a wider recall window**, and the ceiling
   curve is 0 → 1/1/5 → 3/3/14 → 3/3/17 at `k` = 5 / 8 / 16 / 32 with an unlimited budget. Even the
   `k = 32` ceiling reaches **3 of 12 (25%)** of DEV-100's gold-absent dispatched errors and
   **17 of 44 (39%)** of NEW400's. That is the honest upper bound of this whole axis at the present
   key construction.
3. **`(2,5)` at `k = m = 8` already saturates the reachable set at that width** — it returns the
   same 1 / 1 / 5 as an unlimited budget there — while touching less than half as many trajectories
   as any `c`-raising variant. If a supply-budget round is flown, this is the cell.

**Named members** (DEV-100 r4 and r5 share the same one). `(2,5)` at `k = m = 8`: DEV-100 `013465`
(gold `general_quirky`, arriving at fused rank 5); NEW400 `002834` (`iot_cleaning`, rank 4), `006522`
(`general_quirky`, rank 5), `008778` (`calendar_set`, rank 4), `008899` (`calendar_query`, rank 3 —
this one is bought by the *width*, not by `top_l`, since it also appears at `(2,3)` k=8), `013836`
(`general_quirky`, rank 5).

**An honesty flag on that list.** Eight of the fourteen samples the wider variants reach carry gold
`general_quirky`, SLURP's catch-all intent, and they arrive at fused rank 5 — outside every rank the
sealed record has a measured conversion for (§6).

## 5. The dilution question — measured, and mostly unanswerable

Conversion of a dispatched evidence contact, at a fixed gold rank, as a function of how much was
supplied (pooled over all three populations):

| gold rank | 2 values | 3 values | 4 values | 5 values |
|---|---|---|---|---|
| **fused top-1** | 83/83 = 1.000 | 17/18 = 0.944 | 8/8 = 1.000 | 0/1 = 0.000 |
| fused 2 or 3 | — | 6/8 = 0.750 | 7/12 = 0.583 | 3/3 = 1.000 |
| absent | 0/10 | 0/30 | 0/20 | 0/6 |

| gold rank | 1 target | 2 targets | 3 targets |
|---|---|---|---|
| **fused top-1** | 83/83 = 1.000 | 25/26 = 0.962 | 0/1 = 0.000 |

**There is no measurable dilution cost inside the measured range**, and the range is small: above
four values or two targets the sealed record holds one to three samples. So the cost side of a
wider budget is **unanchored, not proven safe** — that is the whole of what the offline record can
say, and it is why the pessimistic band in §7 is deliberately harsh.

## 6. The conversion anchors, and where they run out

Pooled over the three sealed populations (unchanged from
`2026-08-25-ec-and-retain-override-projections.md` §3, recomputed here):

| where gold sits | measured | rate |
|---|---|---|
| fused **top-1** | 108 / 110 | **98.2%** |
| fused rank **2 or 3** | 16 / 23 | **69.6%** |
| **absent** | 0 / 67 | **0.0%** |

The frozen cell's `top_l = 3` means **no flown trajectory ever supplied a fourth target**, so there
is **no measured anchor at fused rank 4 or deeper**. The projections price it at 0.493 — the
rank-2/3 rate carried one further step down the same measured slope (0.6957 × 0.6957/0.9818) — and
that number is an **extrapolation, labelled as one everywhere it is used**. It matters here more
than it did for A4: of the changed trajectories a wider variant produces, **1 / 1 / 4** (at `(2,5)`
k=8) and **3 / 3 / 7** (at `(2,5)` k=16) are priced at that unanchored rank, and they are exactly the
recoveries the whole projection rests on.

## 7. Projected accuracy bands

Construction. A trajectory whose supplied set is **unchanged** receives a byte-identical evidence
prompt, so its outcome is carried over **exactly** — arithmetic, not projection. A trajectory whose
supplied set **changes** is priced at the measured rate for wherever gold sits under the variant,
whether it is right or wrong today; a currently-correct disturbed sample therefore carries the same
rate as a currently-wrong one at the same rank, which is the symmetric reading. The **pessimistic**
edge prices every changed trajectory one rank-band worse; the **optimistic** edge assumes no
currently-correct trajectory is disturbed and every gold-supplied error converts at the top-1 rate.

Sealed baselines: DEV-100 r4 **72/100**, r5 **72/100**, NEW400 **289/400**.

| variant | DEV-100 r4 pess / central / opt | Δ/100 | DEV-100 r5 | Δ/100 | NEW400 | Δ pp |
|---|---|---|---|---|---|---|
| `(3,3)` k=5 | 65.6 / **72.4** / 74.0 | +0.40 | 66.7 / **72.7** / 74.0 | +0.74 | 266.4 / **288.0** / 291.9 | −0.25 |
| `(2,5)` k=5 | 72.0 / **72.0** / 72.0 | 0.00 | 72.0 / **72.0** / 72.0 | 0.00 | 288.0 / **288.8** / 290.0 | −0.05 |
| `(3,5)` k=5 | 65.6 / **72.4** / 74.0 | +0.40 | 66.7 / **72.7** / 74.0 | +0.74 | 265.4 / **287.8** / 292.9 | −0.30 |
| `(4,4)` k=5 | 65.6 / **72.4** / 74.0 | +0.40 | 66.7 / **72.7** / 74.0 | +0.74 | 265.4 / **287.8** / 292.9 | −0.30 |
| `(2,3)` k=8 (K1) | 69.3 / **72.0** / 73.0 | −0.04 | 70.5 / **72.3** / 73.0 | +0.30 | 282.9 / **290.2** / 292.9 | +0.30 |
| **`(2,5)` k=8** | 69.3 / **72.5** / 74.0 | **+0.45** | 70.5 / **72.8** / 74.0 | **+0.79** | 281.5 / **291.9** / 297.8 | **+0.73** |
| `(3,5)` k=8 | 65.6 / **72.9** / 75.0 | +0.89 | 66.7 / **73.2** / 75.0 | +1.23 | 265.1 / **290.5** / 298.8 | +0.38 |
| `(4,4)` k=8 | 65.6 / **72.4** / 74.0 | +0.40 | 66.7 / **72.7** / 74.0 | +0.74 | 265.1 / **289.5** / 296.9 | +0.13 |
| `(2,5)` k=16 | 69.5 / **74.1** / 76.9 | **+2.12** | 70.7 / **74.5** / 76.9 | **+2.46** | 275.5 / **293.6** / 302.8 | +1.14 |
| ∞ budget, k=32 | 65.6 / **73.9** / 76.9 | +1.88 | 66.7 / **74.2** / 76.9 | +2.22 | 266.1 / **296.9** / 310.6 | +1.96 |

**Against the ±2 per-100 byte-variance channel, plainly:**

- **Every variant at the frozen width is inside the channel, and four of the five are inside it
  because they change literally nothing about which targets are supplied.** `(2,5)` at `k = 5`
  projects an exact 0.00 on both DEV-100 rounds. None of the five is evaluable on DEV-100, and none
  is worth flying there.
- **`(2,5)` at `k = m = 8` is inside the channel too** (+0.45 / +0.79 per 100). It is **not
  evaluable on DEV-100** and would need the 400 tier, where its central projection is +0.73 pp —
  and even that is only +1.74 of 400 (+0.44 pp) measured against K1's own already-sealed `k = 8`
  cell rather than against the frozen cell.
- **The only variant whose DEV-100 central band clears the channel is `(2,5)` at `k = m = 16`**
  (+2.12 / +2.46). It is a **two-variable** move (width 5→16 *and* `top_l` 3→5) and it **breaks the
  prompt envelope** (§8), so it is not a single-variable round as it stands.
- Every pessimistic edge sits well below the sealed baseline. That is deliberate: the loss side of a
  wider budget is unanchored (§5), so the band is built to show it rather than to hide it. Unlike
  A4, whose loss side is **zero by construction**, this lever's loss side is a real unknown applied
  to 9–81 currently-correct trajectories.

## 8. Token cost — a measured rate, and the envelope it breaks

The naive estimator (differencing the two landed prompt-fit receipts) prices three facet
representations that happen to be dense numeric entity-prior tables at 1.93 characters per token,
and would mis-price exemplar prose by roughly 2×. A far better anchor is already inside the sealed
stores: every dispatched trajectory made two contacts on the **same** speech packet, and the
evidence contact is the direct contact plus a fixed instruction plus the supplied value block, so

```
prompt_tokens(evidence) − prompt_tokens(direct)  =  constant  +  the value block
```

with the speech features, task contract and system prompt cancelling **exactly**, per sample.
Regressed over **200 paired contacts**:

| quantity | value |
|---|---|
| tokens per character of value text | **0.41355** (2.418 characters per token) |
| R² | **0.9677** |
| maximum absolute residual | 155 tokens |
| supplied-value block character range observed | 801 – 3,449 |
| flown evidence prompt tokens (min / median / max) | 1,971 / 2,493 / **3,143** |

Applying that rate to the standing worst-case envelope (the longest snapshot value contents, the
same construction `scripts/dev100_c3_prompt_fit.py` and `scripts/dev100_kwiden_prompt_fit.py` use).
The slot is **8,192** and 64 tokens are reserved for completion, so the prompt must stay ≤ **8,128**:

| worst-case values | with 5 facet reps | with 8 facet reps | verdict |
|---|---|---|---|
| 5 | 5,579 | 6,261 | fits |
| **6** | **6,174** (measured) | **6,856** (measured) | fits — the standing envelopes |
| 7 | 6,753 | 7,435 | fits |
| 8 | 7,326 | **8,008** | fits centrally; **8,296 at the stressed rate — marginal** |
| 9 | 7,894 | 8,576 | **breaks** at 8 facets |
| 10 | 8,462 | 9,144 | **breaks** |
| 16 | 11,802 | 12,484 | **breaks by ~4,300** |
| 32 | — | 21,169 | **breaks by ~13,000** |

Per variant, priced at the **structural** cap `min(c·top_l, k)` — the nominal cap is not reachable
and pricing it would refuse variants for no reason:

| variant | structural cap | envelope | fits (central / stressed) |
|---|---|---|---|
| `(3,3)` / `(2,5)` / `(3,5)` / `(4,4)` at k=5 | 5 | 5,579 | yes / yes |
| `(2,3)` k=8 (K1) | 6 | 6,856 | yes / yes |
| **`(2,5)` k=8** | 8 | **8,008** | **yes / no (8,296)** — observed worst 7 → 7,435, fits both |
| `(3,5)` / `(4,4)` / `(3,3)` k=8 | 8 | 8,008 | yes / no |
| `(2,5)` k=16 | 10 | **9,144** | **NO / NO** |
| ∞ budget k=16 | 16 | 12,484 | NO / NO |
| ∞ budget k=32 | 32 | 21,169 | NO / NO |

Two disclosures. **First**, these are ESTIMATES: no tokenizer was contacted, and any variant above
six values must pass a **real** tokenizer-only prompt-fit row before it could fly. **Second**, the
standing envelope method is conservative to the point of being unrealizable — it renders the longest
value contents in the whole snapshot, which cannot all co-occur in one supply, and it renders facet
representations the flown runner never renders at all (the C3 controller carries `visible_facet_ids`
empty). The flown reality is 3,143 tokens at up to five values. So a variant this table refuses is
**not proven infeasible**; it fails the standing gate, which is a different and weaker statement.

## 9. Interaction with A4 (δ ≥ 0.14 retain-override), now flying

**The overlap is zero, on every variant and every population, and it is zero by construction rather
than by luck.** The frozen cell's dispatch predicate is the single test *"the direct answer named no
TRAIN intent"* (`2026-08-25-ec-and-retain-override-projections.md` §2). A4 acts only where it named
one (retained); the supply budget acts only where it did not (dispatched). Measured: the dispatch
set is **invariant** under every budget variant on all three populations, and the two recovery sets
are disjoint by sample id.

| | A4 at δ ≥ 0.14 | supply budget `(2,5)` k=8 | overlap |
|---|---|---|---|
| DEV-100 r4 | `002814`, `010037`, `011819` | `013465` | **0** |
| DEV-100 r5 | + `012045` | `013465` | **0** |
| NEW400 | `009926`, `009999`, `010017`, `010070`, `010242` | `002834`, `006522`, `008778`, `008899`, `013836` | **0** |

**The coordinator can add the two central projections without double-counting.** What is *not*
additive is the flight: if both knobs move in one arm, the wider budget would also change the supply
on **1 / 2 / 2** of A4's 3 / 4 / 6 triggered trajectories (and on **3 / 4 / 6** — all of them — under
any `c`-raising variant). A4's recoveries are exactly the trajectories where gold is the fused
top-1, and a wider budget adds lower-ranked distractor targets to those same prompts. So a combined
arm is not the sum of two independent effects, and attribution requires A4 flown alone first — which
is what is happening.

## 10. RECOMMENDATION

**No supply-budget variant clears the ±2 per-100 variance channel on DEV-100 as a single variable
inside the prompt envelope.** That is the honest headline, and it is not a close call:

- the five briefed variants at the frozen width reach **zero** errors on **600** sealed trajectories,
  including at an unlimited budget — the budget is not the binding constraint at the frozen cell;
- the best variant that reaches anything, `(2,5)` at `k = m = 8`, projects **+0.45 / +0.79 per 100**
  on DEV-100 — comfortably inside the channel, and only **+0.44 pp** measured against K1's own
  already-sealed `k = 8` cell;
- the only variant whose DEV-100 band clears the channel, `(2,5)` at `k = m = 16`, is a two-variable
  move that breaks the standing prompt envelope by ~1,000 tokens.

**If a supply-budget round is flown anyway, the single best cell is `fusion.top_l` 3 → 5 layered on
K1's already-sealed `k = m = 8` width** (`c` unchanged at 2, everything else byte-equal to
`configs/policy/kb-policy-v1-dev100.json` plus the K1 width). Rationale: `c` is provably inert for
reachability (§3), `top_l = 5` already saturates the reachable set at that width (§4), it touches
less than half the trajectories any `c`-raise touches, its observed worst case (7 values, 7,435
tokens) fits the envelope on both the central and stressed rate, and against K1 it is a genuine
single variable on an already-paid width.

**Registered prediction for that round, read at the 400 tier** (baseline = the sealed BLEND NEW400,
289/400 = 72.25%; the K1-width reference is 290.2 projected):

| quantity | prediction |
|---|---|
| dispatch set vs K1 | **identical** — the dispatch predicate is supply-independent |
| trajectories whose supply changes | **65** of 130 dispatched (28 of them currently correct) |
| newly gold-supplied errors | **5**, named: `002834`, `006522`, `008778`, `008899`, `013836` |
| trajectories that LOSE a gold-bearing supply | **0** |
| maximum supplied values | **7** (structural cap 8) |
| extra frozen-core contacts | **0** — no new dispatch, only wider prompts |
| band vs the frozen cell | **281.5 / 291.9 / 297.8** of 400 = 70.4% / **73.0%** / 74.5% |
| central change | **+0.73 pp** vs the frozen cell, **+0.44 pp** vs K1 |
| DEV-100 | **NOT evaluable** — band 72.5 / 72.8 against sealed 72, inside the ±2 channel |

**What would falsify it.** A flown arm whose dispatch count differs from K1's falsifies the
supply-independence of the dispatch predicate and voids §9's zero-overlap claim. A flown arm in
which none of the five named samples converts falsifies the transfer of the rank-4/5 extrapolated
rate — and since four of the five arrive at rank 4 or 5, that is the single most likely way this
prediction fails. A flown arm materially **below** the K1 reference falsifies §5's "no measurable
dilution" reading and would be the first direct evidence that a wider supply block costs accuracy.

**Selection disclosure.** Every variant was scored on exposed data across all three sealed
populations. Under the owner's split-usage philosophy that is legitimate optimization, but the cell
is **fit, not validated**; its out-of-sample test would be the DEV-1000 baseline-lock read.

**And the design consequence, which is larger than the recommendation.** The ceiling curve in §4 —
0 → 1/1/5 → 3/3/14 → 3/3/17 as `k` goes 5 → 8 → 16 → 32 with an unlimited budget — says the supply
budget tops out at **25% (DEV-100) / 39% (NEW400)** of the gold-absent dispatched errors even with a
context that could hold 32 values, which the 8,192-token slot cannot. Combined with the E-A
pre-analysis's finding that the residual is 68–73% recall-limited with the gold facet at median
position 46–60, the offline record now points the same way three times: **the reachable lever is the
retrieval KEY, not the retrieval width and not the supply budget.**

## 11. What this document does not do

It registers no round, selects no knob, authorizes no flight, and reaches no verdict on the frozen
cell or on convergence. It adds one analysis module and this note. The queue decision — including
whether to spend the next round on key construction instead — remains with the coordinator and the
owner.
