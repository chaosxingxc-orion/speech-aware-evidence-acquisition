# P-CORR-F verdict — CORRECTIVE-PERCEPT / DOSE-INSUFFICIENT (registered one-shot read, 2026-08-20)

Mechanical outcome per the registered metrics and verdict rules
(`docs/readiness/2026-08-20-pcorrf-preregistration-REGISTERED.md` §3), computed by the pinned
offline read suite (`analysis.pcorrf_read`, coordinator-reviewed before the read) over the
already-flown attempt `attempt-20260820T151845Z-88b2a5` (`SAEA-PROBE-pcorrf-240`, status
`COMPLETED`, error `None`, 240/240 rows across W1/W2/W3/W4) — zero model contact, zero GPU, no
attempt-directory mutation.

Read archive: `docs/checks/speech-aware-evidence-acquisition/2026-08-20-pcorrf-read/`
(`verdict.json`, `report.txt`, `README.md`, `MANIFEST.sha256`). The suite ran exactly once
(idempotence-guarded output dir), exit 0, at study HEAD `a407d03` with a clean tree. Exposure row
`SAEA-PROBE-pcorrf-240` flips to consumed in the same commit. Scope: **descriptive,
discovery-tier, n = 60 SLURP devel (40 mechanism-usable), single run, same-distribution**. SLURP
audio CC BY-NC 4.0 carried on every number below.

Pre-read gates, all green before anything was opened: `test_pcorrf_read.py` + `test_pcorrf_flight.py`
**110 passed**; the flight archive's `MANIFEST.sha256` verified **34/34 OK**; ledger row
`consumed = no`; tree clean at `a407d03`; the pcorrf modules byte-identical to their reviewed state
at `5c3e0fa` (`git log 5c3e0fa..HEAD` on both files is empty). The attempt directory was not
mutated: the pre-read and post-read file fingerprints are identical
(`35c64313fc0abe147132576292aecbd22bdab91d81a64970bbb477d2d95cdb20`).

---

## 1. REACHABILITY STATEMENT (mandatory §3 item; published BEFORE any verdict was evaluated)

### 1.1 The mechanism denominator is 40, not 60 — stated before Q-1

L1 TYPE-LOOKUP keys on the core's own A0 emitted slots. **20 of the 60 samples emitted nothing
lookup-able and fly at K = 0.** On those 20, W1 and W2 render the identical bare A3 roster, so
their prompts are **byte-identical — verified 20/20 in this read** (and 0/40 identical on the K > 0
samples, as required). Per-sample Δ₁ on that third is therefore not a measurement of the mechanism;
it is a resend. **The common denominator for any mechanism claim is 40.** Both the registered
full-60 clustering and the restricted-40 reading are reported below; the registered verdict is the
full-60 one.

| quantity | value |
|---|---|
| samples flown | **60** (W1/W2/W3/W4 = 60/60/60/60) |
| L1 K distribution (W1 = W2 = W3) | `{0: 20, 1: 25, 2: 10, 3: 4, 4: 1}`, mean 1.0167, max 4 |
| **K = 0 (untouched by construction)** | **20/60** → **mechanism denominator 40** |
| W4 K distribution | `{0: 14, 1: 11, 2: 10, 3: 14, 4: 10, 7: 1}`, mean 2.0000, max 7 |
| W4 K = 0 | 14/60 |
| **max attainable recovery** (gold slots present in each arm's own supplied set) | **W1 37/89, W2 0/89, W3 37/89, W4 39/89** |

The registration's design analysis predicted 36/89 for W1/W3; the read measures **37/89** on exact
`(type, normalized filler)` pair matching. The affirmative branch was reachable with margin, and the
equivalence branch was equally live (a 40-sample paired CI can sit wholly inside ±0.03). Nothing
below is reported under a suppression clause.

> **Denominator display defect in the shipped suite (disclosed, non-gating).** `verdict.json`
> renders these fractions as `37/8352` rather than `37/89`. Root cause:
> `analysis.pslu_read.load_gold_by_sample_id(lock, root, sample_ids)` ignores its `sample_ids`
> filter and returns the **entire** SLURP devel gold map (8690 keys), so the suite's
> `total_gold_slots = sum(len(record.entities) for record in gold_by_sample_id.values())` sums the
> whole devel split (8352 slots) instead of the frozen 60 (**89 slots**, mean 1.483/sample). The
> **numerators are correct** — `max_attainable` iterates `rows_by_arm`, which holds only the 60
> flown rows. This is the only place in the read that aggregates over the gold map; every other use
> (`_score_row`, `gold_values_by_sample`, dual measurement) is keyed per sample and therefore
> unaffected, so **no verdict, bootstrap, recovery or contamination number moves.** The suite was
> run exactly as shipped and was not patched; the corrected fraction is stated above and the defect
> is carried forward as a machinery fix.

### 1.2 Positive control — zero supply reproduces the bare core

W3's 20 K = 0 samples flew **true zero-supply** (`supply=None`). Their SLU-F1 is **0.1609**, against
the cited bare-core A0 **0.1741** — a difference of −0.0132, at the ±0.013 cross-session drift bound.
The harness reproduces the no-supply floor on the nose.

---

## 2. VERDICTS

> ### Q-1 mechanism: **CORRECTIVE-PERCEPT**
> ### Q-2 dose efficiency: **DOSE-INSUFFICIENT**
> ### W4: descriptive, no clause

| | Δ | 90% CI (N=10,000, seed 20260807) | σ̂ | outcome |
|---|---|---|---|---|
| **Q-1 full-60 (registered)** | **+0.0508** | **[+0.0098, +0.0968]** | 0.0265 | **CORRECTIVE-PERCEPT** (Δ₁ ≥ +0.03 ✔, CI low > 0 ✔) |
| **Q-1 restricted-40 (K > 0)** | **+0.0753** | **[+0.0179, +0.1411]** | 0.0375 | **CORRECTIVE-PERCEPT** (same branch, larger effect) |
| **Q-2 full-60 (registered, point-gated)** | **−0.1625** | [−0.2403, −0.0861] | 0.0468 | **DOSE-INSUFFICIENT** (Δ₂ ≤ −0.10 ✔) |
| Q-2 restricted-40 (K > 0) | −0.0380 | [−0.1272, +0.0494] | — | (descriptive; see §2.2) |

CORRECTIVE-INERT was **not met** on either denominator (the CI clears +0.03 at the top and 0 at the
bottom). Both Q-1 readings select the same branch, and the effect is **larger** where the mechanism
can actually act — the signature a real mechanism should produce.

### 2.1 Per-arm SLU-F1, split by denominator

| arm | construction | full 60 | **K > 0 (40)** | K = 0 (20) | slot_f1_exact (60) |
|---|---|---|---|---|---|
| **W1 CORR-SELF** | A3 roster + own L1 | **0.6588** | **0.7286** | 0.5262 | 0.6032 |
| **W2 CORR-CROSS** (control) | A3 roster + cross-sample L1 | 0.6080 | 0.6533 | 0.5190 | 0.5208 |
| **W3 CORR-ONLY** | L1 alone, no roster | 0.4336 | 0.5581 | 0.1609 | 0.3483 |
| **W4 CORR-WIDE** | A3 roster + L1 ∪ L2b | 0.6366 | 0.6998 | 0.5090 | 0.5445 |

Cited comparators (consumed, never re-flown): A0 0.1741 / A2 0.4686 / **A3 0.5961** /
A1 gold-ceiling 0.6340 / A4 0.3087 / A1'r 0.6093 / V1 trap 0.5003 / V2 cross 0.5907.

**Named observation (not a claim):** W1 at **0.6588** sits **+0.0248 above the cited A1 gold-ceiling
0.6340**, and W4 at 0.6366 is also above it. That is ~1.9× the ±0.013 cross-session drift bound.
Discovery-tier, n = 60, single run, cross-session — it is recorded as an observation to be re-tested,
not as a superiority claim.

### 2.2 Reading Q-2 honestly

The registered verdict is **DOSE-INSUFFICIENT** on the full-60 point gate, and that stands. But the
deficit is **not** evidence that ~1 entry/sample is a weak dose. It is almost entirely the
zero-supply third: W3's K = 0 slice scores 0.1609 (bare core), dragging the aggregate down. On the
40 samples that actually received supply, W3 reaches **0.5581 against A3's 0.5961 — Δ₂ = −0.0380**,
just outside the DOSE-EFFICIENT floor of −0.03 and far inside the DOSE-INSUFFICIENT ceiling of −0.10.

So: **1.5 entries/sample buys ~94% of a 100-entry roster's SLU-F1 on the samples it touches, and
0% on the third it cannot reach.** The A3 roster's value is **coverage**, not per-sample strength.
Cross-session comparison; the ±0.013 drift bound travels with both figures.

---

## 3. THE PERCEPT GATE — the headline mechanism

Capture rate = fraction of supplied corrective entries the core actually emitted, measured with
P-TRAP's own detector (`analysis.ptrap_read.response_captures_trap`), per entry.

| supplied set | keyed to | entries | captured | **rate** |
|---|---|---|---|---|
| **W1 corrective** | this sample's own percept | 61 | 59 | **96.7%** |
| **W2 corrective** (control) | another sample's percept | 61 | **0** | **0.0%** |
| **W3 corrective** (no roster) | this sample's own percept | 61 | 61 | **100.0%** |
| W4 · L1 subset | this sample's own percept | 61 | 58 | **95.1%** |
| W4 · L2b subset | retrieval widening (**not** percept-keyed) | 59 | 7 | **11.9%** |

This is the cleanest separation in the study to date, and it is **P-TRAP with the sign flipped
exactly as pre-declared** (P-TRAP: V1 self 0.9062, V2 cross 0.0000, harm; P-CORR-F: W1 self 96.7%,
W2 cross 0.0%, benefit). Three independent contrasts isolate the same gate:

1. **Self vs cross** (96.7% vs 0.0%) — identical construction, identical dose, identical roster
   base; only the key differs. The gate is percept-keying, not roster presence, not plausibility.
2. **Percept-keyed vs retrieval-widened inside one prompt** (95.1% vs 11.9%, W4) — same request,
   same response, same rendering. The core discriminates by key, not by supply position.
3. **Roster present vs absent** (W1 96.7% vs W3 100.0%) — the base roster does not gate the
   corrective layer.

**The gate is binary and near-total, and it does not inspect correctness.**

---

## 4. MANDATORY DUAL MEASUREMENT — recovery vs contamination

Recovery = gold slots newly matched versus the consumed A0 baseline. Contamination = non-gold
corrective entries the response emitted.

| arm | recovery (60) | contamination (60) | recovery (own K>0) | contamination (own K>0) |
|---|---|---|---|---|
| **W1** | **53** | **12** | 41 | 12 |
| **W2** (control) | 46 | **0** | 34 | 0 |
| **W3** | 27 | 14 | 27 | 14 |
| **W4** | 48 | 18 | 42 | 18 |

### The balance sheet, stated against the dose-matched control

On the 40 mechanism-usable samples, W1 versus its dose-matched control W2:

| | W1 | W2 | **marginal** |
|---|---|---|---|
| gold slots recovered | 41 | 34 | **+7** |
| non-gold values emitted | 12 | 0 | **+12** |

**The corrective layer emits more junk than gold on raw slot counts — 7 gold recovered against 12
spurious — and still gains +0.0753 SLU-F1.** Both halves are real and both must be carried:

- **Why it still wins.** A type-correction converts a slot the core already had right in *value* but
  wrong in *type* from a simultaneous false-positive *and* false-negative into a true positive. Each
  repair is a double swing in F1, which is why `slot_f1_exact` moves +0.0824 (0.5208 → 0.6032) on a
  net of only +7 recovered slots. The 12 contaminating emissions are single-count false positives.
- **Why the cost is structural, not incidental.** W1's supplied set contains **47 gold-valued and 14
  non-gold-valued entries** (77% value precision). **12 of those 14 non-gold entries were emitted —
  85.7%.** The core swallows wrong percept-keyed supply at essentially the same rate it swallows
  right percept-keyed supply. There is no model-side validation whatsoever.

**W4 prices the precision directly.** Widening to L2b takes the supplied set from 77% to 41% value
precision (49 gold-valued of 120), and SLU-F1 falls from 0.6588 to 0.6366 while contamination rises
12 → 18. The widened entries are only captured at 11.9% precisely because they are not
percept-keyed — which is the only reason the damage is as small as it is. The registration's
prediction that widening beyond L1 collapses precision is confirmed.

---

## 5. THE RESEND FLOOR IS NOT 0.0000 ON THIS STACK (adversarial disclosure)

The registration keeps its equivalence branch reachable by citing "the P-KEY byte-identical-resend
|ΔF1| floor of exactly 0.0000". **That floor does not reproduce on this flight.**

The 20 K = 0 samples give a free, in-flight measurement of it: byte-identical W1/W2 prompts
(verified 20/20), decoded at **temperature 0, seed 20260803**.

| quantity | measured |
|---|---|
| responses byte-identical across the pair | **14/20** |
| **responses divergent** | **6/20 (30%)** |
| samples whose per-sample SLU-F1 changed | 2/20 |
| **aggregate \|W1 − W2\| on the K = 0 slice** | **0.0072** (premise said exactly 0.0000) |

The divergences are not whitespace: they include different scenario strings
(`"querying calendar"` vs `"querying for upcoming event details"`), different entity sets
(one sample emitted `transport_type` + `transport_name`, its twin emitted `[]`), different slot types
(`change_amount:"to low"` vs `volume_level:"low"`), and different output framing (fenced vs bare
JSON). Four of the six happened to score identically, which is why only 2/20 moved F1.

Most likely cause: the server ran `-np 4` continuous batching, whose kernel reduction order depends
on batch composition; greedy decoding does not make that bit-reproducible.

**Does this threaten the verdict? No, but it must be carried.** The measured same-prompt noise on a
20-sample slice is 0.0072 aggregate, while restricted-40 Δ₁ is +0.0753 with CI low +0.0179 — roughly
an order of magnitude of headroom, and the percept-gate contrast (96.7% vs 0.0%) is far too large to
be jitter. What must change is the **premise**: successor registrations must not cite 0.0000 as this
stack's floor, and any probe whose bar sits near ±0.013 needs its own measured resend floor at its
own `-np` setting.

---

## 6. GUARDRAILS (descriptive, never verdict-gating)

| arm | parse rate | empty rate | copy rate | induced substitutions |
|---|---|---|---|---|
| W1 | 1.0000 | 0.0000 | 0.0000 (0/6061) | 3 |
| W2 | 1.0000 | 0.0000 | 0.0000 (0/6061) | 2 |
| W3 | 1.0000 | 0.0000 | 0.0000 (0/61) | 2 |
| W4 | 1.0000 | 0.0000 | 0.0000 (0/6120) | 3 |

No harness defects (`harness_defect_reasons` empty). Parse rate is perfect on all four arms, no
empty responses, and **copy rate is exactly 0.0000 everywhere** — the core never dumped the supplied
roster back wholesale, so nothing here is roster echo. Induced substitutions stay in the 2–3 band
across arms (W1 3 vs W2 2), so the mechanism is not buying its gain by trading one error class for
another at scale.

**Per-scenario (W1 − W2), 18 scenarios:** 8 positive, 7 exactly flat, 3 negative. Largest positives
`audio` +1.0000 (n=1), `news` +0.3333 (n=3), `play` +0.1667 (n=7), `cooking` +0.1632 (n=2),
`social` +0.1481 (n=3). Negatives: `lists` −0.1766 (n=2), `general` −0.1667 (n=2),
`datetime` −0.0701 (n=3). The gain is broad rather than one-scenario-driven, but per-scenario cells
are 1–8 samples and carry no weight individually.

---

## 7. WHAT THIS DECIDES FOR THE FILLING TIER

The scoreboard's standing open problem is: *"blind replacing supply on already-correct samples
regresses 36/97 — **supply targeting is the open problem**."* The question this probe was built to
answer is whether percept-keyed type-correction is the supply law's **targeting-free** answer,
given that it needs no confidence gate because it keys on the model's own output.

**Answer: yes for targeting, no for safety. The targeting problem moves; it does not close.**

**Targeting is solved, and solved structurally.** The construction never decides *which* samples to
correct. It keys every emitted slot, gold-free, with no confidence estimate, no wrong-only oracle,
and no gold-keyed accept/reject anywhere in the path. The consequences are mechanical rather than
statistical:

- Samples with no lookup-able percept receive **nothing** — prompts provably byte-identical to
  control on 20/20. Blind replacement's failure mode (perturbing already-correct samples) is not
  mitigated here, it is **structurally unreachable**: there is no un-keyed supply to do the damage.
- Where the key does fire, the core accepts it at **96.7%**, and accepts the cross-keyed control at
  **0.0%**. The targeting signal is the model's own percept, and it is essentially a perfect switch.
- The result is +0.0753 SLU-F1 on the 40 samples it touches, and a 100-entry-roster-competitive
  0.5581 from 1.5 entries/sample.

**Safety is now the binding constraint, and it is quantified.** The same gate that admits corrections
admits errors at **85.7%**. The core is not a filter — it is an open pipe for anything keyed to its
own percept. Therefore:

> **Supply precision is the entire safety margin.** L1's 77% value precision buys +0.0508 full-60;
> W4's 41% gives back 0.0222 of it. The supply law's targeting duty has been discharged by
> percept-keying; the **filtering duty named by P-TRAP is now the whole problem**, and it must be
> discharged **outside** the frozen core, because the core demonstrably will not do it.

**Two hard limits to carry.**

1. **Coverage ceiling.** 20/60 samples (33%) are unreachable by percept-keying by construction, and
   they are exactly the samples where the core emitted nothing to key on — plausibly the hardest
   ones. A percept-keyed layer can never be the whole filling tier; it needs a coverage layer beside
   it. This is precisely what W3-vs-A3 measures: keyed supply wins per-sample, the roster wins on
   reach, and the right architecture is **both**, not either.
2. **Marginal precision is poor even when it wins.** +7 gold against +12 spurious is a 37% marginal
   precision. The F1 gain survives only because type repairs swing twice. A metric more sensitive to
   false positives would price this differently, and Stage-3 must not assume the sign carries.

Scoreboard consequence: the filling tier gains its **first targeting-free positive lever with a
dose-matched control**, and the speech-as-knowledge line item "(b) percept-aware supply filtering"
is promoted from *designable* to *required and specified* — the filter must reject wrong
percept-keyed entries before they are supplied, since the core passes 85.7% of them through.

---

## 8. P-CORR-R DESIGN IMPLICATIONS

P-CORR-R is the registered routing twin (confusable-neighbourhood re-ask, disagreement-complementary).
Four constraints follow directly from the numbers above, and they change its design:

1. **The core cannot arbitrate among supplied candidates — do not ask it to.** At 96.7% capture with
   no correctness inspection, supplying N percept-keyed candidates will not produce a choice; it will
   produce emissions. A re-ask that presents a confusable neighbourhood as a menu is measuring the
   gate, not the core's judgement. **P-CORR-R must arbitrate outside the core, or supply exactly one
   candidate per slot.**
2. **Percept-keying is a usable ON/OFF switch.** 96.7% keyed versus 11.9% unkeyed, measured inside a
   single prompt (W4), means keying can be used deliberately as an admission control: key what should
   land, leave unkeyed what is offered only as context. This is a design primitive the study did not
   previously have.
3. **Pair the keyed layer with a coverage layer; do not replace the roster.** W3 (keyed only) is
   DOSE-INSUFFICIENT overall purely through its 33% blind spot, while matching the roster to within
   0.038 where it acts. P-CORR-R should assume a keyed layer + coverage layer composition and should
   report its own K = 0 population before any verdict.
4. **Measure the resend floor at flight time.** 0.0000 is not this stack's floor at `-np 4`; the
   measured value here is 0.0072 aggregate with a 30% response-divergence rate at temperature 0.
   P-CORR-R's disagreement signal is a **difference between two responses**, so it is directly
   exposed to this: a 30% same-prompt divergence rate could masquerade as disagreement. **P-CORR-R
   must fly an explicit byte-identical-resend control arm** and subtract its own measured floor,
   otherwise its central quantity is confounded. This is the single most important carry-forward from
   this read into that design.

---

## 9. ACCOUNTING AND SCOPE

Spend is unchanged by this read (model-free): 240 of 260 calls, 729.04 of 1000 metered audio-seconds.
**The GPU-hour column overshoots the registered 0.35 ceiling on the server-alive wall measure
(0.3628 h, +0.0128 h)** and is carried forward here rather than restated as clean. Per the §8 pre-read
adjudication (written before any result value was consulted), the registration's own stated basis is
the per-call measured-equivalent (**0.1416 h**) and GPU-active occupancy (**0.0967 h**), both inside
the ceiling, so the flight is **not in breach**; the wall figure stays on the record. The cause was a
959 s cold-cache sha256 of 20.76 GB of GGUF running after server spawn while the GPU sat at 0–1%
utilization. Forward rule for every successor flight: build transport and payload binding **before**
spawning the server.

**Scope limits on everything above.** Discovery-tier, n = 60 SLURP devel (40 mechanism-usable),
single run, same-distribution, one frozen q4km core, cross-session comparisons against pinned
constants with a ±0.013 drift bound. No superiority claim, no generalization claim, no test split.
Gold was used scoring-side only and never entered a runtime path. SLURP audio CC BY-NC 4.0; textual
annotation layer CC BY 4.0.

**Items flagged for adversarial re-check:**

1. The **30% same-prompt response-divergence rate at temperature 0** (§5) — it falsifies a premise
   several registrations cite, and it should be re-measured deliberately at `-np 1` versus `-np 4`.
2. The **reachability denominator defect** in `analysis.pcorrf_read` / `load_gold_by_sample_id`
   (§1.1) — cosmetic here and verdict-neutral, but the same ignored-filter bug could bite a suite
   that aggregates over that map for a gating quantity.
3. **W1 above the A1 gold-ceiling** (§2.1, +0.0248) — a corrective layer beating the gold-derived
   ceiling comparator deserves a check that the two are commensurable constructions.
4. The **+7 gold / +12 spurious marginal balance** (§4) — the verdict rests on an F1 metric that
   rewards type repairs twice; the sign should be re-derived under a false-positive-sensitive metric
   before any Stage-3 promotion.
