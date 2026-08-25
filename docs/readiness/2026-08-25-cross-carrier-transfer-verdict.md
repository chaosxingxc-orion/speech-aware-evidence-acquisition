# CROSS-CARRIER TRANSFER VERDICT — the mechanism transfers byte-identical; the magnitude
# does not, and the arithmetic says exactly why

Date: 2026-08-25. Status: **CONSOLIDATION VERDICT — computed, ZERO CONTACTS, fidelity gate
passed 104/104.** Row `SAEA-SN-MF-CROSS-CARRIER-CEILING-DECOMPOSITION` (registered `1db6b66a`,
**before any computation**). Module
`src/speech_aware_evidence_acquisition/analysis/cross_carrier_ceiling_decomposition.py`.
Receipt `docs/checks/speech-aware-evidence-acquisition/2026-08-25-cross-carrier-decomposition/decomposition-report.json`
(sha256 `9a1903b35f3eff42dc7bf4caee5ba95235af855e9e0fc087ba8d9d7c0d8be5a1`).

**Spend: 0 frozen-core contacts, 0 embedding-tool contacts, 0 tokenizer contacts, 0 audio
seconds, 0.0 GPU hours, 0 new dependencies.** The offline guard
(`analysis.dev100_reviewer_audit.arm_offline_guard`) was armed before the first input was opened
and recorded **0 outbound connection attempts against 0 targets**. The resident np2 A2T service
on port 8090 was never contacted, probed, reconfigured or stopped. Wall 270.5 s. No knob was
changed; `configs/`, `rails/` and `core/` were not written.

---

## 0. The verdict in one paragraph

The locked policy cell's **mechanism** transfers to Audio2Tool with the cell **byte-identical**:
the supply path fires, every mechanism invariant passes, two of them having moved from
VACUOUS/FALSIFIED to PASS/RESTORED, and every gain is method-attributable. Its **magnitude**
does not transfer, and the reason is not that the method is weaker on this carrier — it is that
its **reach is smaller and its within-reach conversion is lower, and the two multiply**. On
SLURP's unexposed 500 the policy can touch **32.00 %** of trajectories and converts within that
reach at **+59.38 pp**; on Audio2Tool it can touch **14.42 %** and converts at **+13.33 pp**.
2.22 × 4.45 ≈ 9.9, and the reach contributions stand at 19.00 pp against 1.92 pp — a ratio of
9.9. **The two factors account for the whole of the reachable-set contribution gap; nothing is
left over for "the method is weaker here".** The one remaining term, the retain-subgroup drift,
differs in sign (+1.60 pp on SLURP, −0.96 pp on A2T), and on A2T it is a single flip the landed
read attributes to decode variance rather than to the method (§3.4). That is an explanation, not
a defence: both ceilings are real and both are named below, one as a property of the POLICY FORM
and one as a property of KB COVERAGE.

---

## 1. What is ESTABLISHED

### 1.1 SLURP — the locked cell, its interval, and its out-of-sample evidence

Authority: `docs/readiness/2026-08-25-baseline-lock-verdict.md`; read artifact
`docs/checks/speech-aware-evidence-acquisition/2026-08-25-dev1000-lock-read/read-verdict.json`
(sha256 `2f8e295852e1c09d737467a62123586f097f938ec353dcbe58d258dadc1ea581`, blob-verified).

| | value | source |
|---|---|---|
| population | DEV-1000 minus DEV-500 = **500 UNEXPOSED** | `populations.unexposed_new500_n` |
| M0 | 278 / 500 = **55.60 %** | `primary.M0_correct` |
| BLEND | 379 / 500 = **75.80 %** | `primary.BLEND_correct` |
| paired delta | **+101 samples = +20.20 pp** | `primary.delta_samples`, `delta_pp` |
| 90 % CI | **[+17.20, +23.40]**, 0 of 10,000 replicates ≤ 0 | `primary.bootstrap` |
| 95 % CI | [+16.60, +24.00] | `primary.bootstrap` |
| McNemar exact | p = 1.035e-25; W→C 106 / C→W 5 | `primary.mcnemar` |
| lock condition (90 % CI low ≥ +10 pp) | **MET with +7.20 pp of margin** | `primary.ci90_lower_bound_margin_vs_threshold_pp` |

**Scale stability.** DEV-500's unexposed 400 read **+19.75 pp** [+16.50, +23.00]; DEV-1000's
unexposed 500 reads **+20.20 pp** [+17.20, +23.40]. Each point estimate lies inside the other's
90 % interval (lock verdict §2). The effect does not shrink as the population doubles on
disjoint held-out data.

**The locked cell is v1, not v2.** The δ ≥ 0.14 retain-override was falsified out of sample —
11/11 recovered on the previously-exposed half, **0 recovered and 3 damaged** on the unexposed
half — and was removed. With it removed the same population reads **382/500 = +20.80 pp** (lock
verdict §3; the exact per-sample counterfactual is the "v1 retain (counterfactual)" column of
the 14-fire table in `.../2026-08-25-dev1000-lock-read/README.md` §5.3, which reads 1, 1, 1 on
the three unexposed rows). This verdict re-derives that 382 arithmetically in §3.4.

### 1.2 SLURP — the gain is attributed to the RETRIEVAL SIGNAL, not to the supply structure

Source: `docs/readiness/2026-08-24-dev500-confirmatory-verdict.md` §2 (DEV-500 NEW400,
unexposed, four sealed arms).

| contrast | value | what it excludes |
|---|---|---|
| BLEND − ABL-RANDRET | **+15.75 pp** [+12.5, +19.0] | that the second contact / supply *structure* is doing the work |
| ABL-RANDRET − M0 | **+4.0 pp** | the structural residue, reported rather than absorbed |
| BLEND − ABL-RANDICL | **+25.25 pp** | — |
| ABL-RANDICL − M0 | **−5.5 pp** [−9.5, −1.5] | that "any exemplars help" |

Random exemplars actively hurt. **Retrieval specificity is the mechanism.** This is the single
strongest reason the Audio2Tool result below is worth reading at all: the thing being carried
across is a retrieval signal, not a prompt-shape trick.

### 1.3 Audio2Tool — the mechanism transfers with the cell BYTE-IDENTICAL

Source: `docs/checks/speech-aware-evidence-acquisition/2026-08-25-a2t-g1/arm2-blend-mechanical-report-attempt4.json`
(sha256 `641c4b5ae82cdda1b2d8508bb95e52035fe1b3d119ea170f10906779df459436`).

| | value |
|---|---|
| policy cell | `configs/policy/kb-policy-v1-dev100.json`, sha256 **`d68afd2cfb6e12d9cbd9d3fbcf0daf3f81f6ed8be9b2a75c4f8ffb234011a919`** |
| pre-lock bytes the DEV-1000 launcher pinned | `0d36273eb2a5f4411ba9ca378ad820392e97c8759222087cf562e7f19442e2b0` |
| what changed between the two | the lock commit `d9fef537` added exactly two ANNOTATION keys, `STATUS` and `locked_at`; **the `knobs` block is byte-unchanged** (verified here by `git log -p` on the file) |
| experiment config hash, BOTH arms | `df6bf4d4e5ac3ae5a3fe9d52dc8933b81bec70f7dbff05a2984635b8badc38f9` |
| `rails/kb_policy.py` pinned at flight | commit `1341c2db`, sha256 `2a1c3d75e747db10f723044b05c08d232e1edf47f125d0889c1d2565ba1019af` (re-measured by this row) |
| knobs | α 0.45, τ 0.65, k 5, m 5, c 2, top_l 3, rrf w_cos 0.5 / w_prior 0.3 / w_agree 0.2, TRAIN priors, boundary stage off, facet-side percept admission |
| δ retain-override | **NOT CARRIED** |

Serving geometry (`-np 2`, 32,768 tokens/slot, output ceiling 1,024) is the output of the
campaign plan's §8.1 rule applied to this carrier's measured task contract, applied identically
to every arm and fixed before any result was seen (owner Amendment 2). It is not a knob of the
method, and the M0-vs-BLEND comparison is unaffected by it.

The supply path fires: recall returned nothing on 0 of 104; best content cosine 0.7594–0.9572,
clearing τ = 0.65 on 104 of 104; a content facet sits inside the top-m = 5 admission window on
**104 of 104**, where the pre-repair attempt measured 0 of 104.

### 1.4 Audio2Tool — every gain is method-attributable

Source: `docs/checks/speech-aware-evidence-acquisition/2026-08-25-a2t-g1/g1-read-attempt4.json`
(sha256 `cb5e56584a6d572f7b41b39542201ddb1b361755042eac66c3a70c55fd086f89`),
`decode_variance_attribution.tool_accuracy_flip_attribution`, verified line by line here:

| sample | direction | dispatched | text divergent from M0 | attribution |
|---|---|---|---|---|
| `tier1_direct:004159` | W→C | yes | no | **method-attributable** |
| `tier4_implicit:003312` | W→C | yes | no | **method-attributable** |
| `tier5_needle:000061` | W→C | yes | no | **method-attributable** |
| `tier1_direct:001631` | C→W | yes | yes | **AMBIGUOUS** |
| `tier8_intent_blending:000441` | C→W | no | yes | **decode variance** |

**3 method-attributable gains, 1 ambiguous loss, 1 decode-variance loss.** Not one clean loss is
attributable to the method. 93 of 104 trajectories produced a direct text byte-identical to the
M0 arm's, so the decode-variance channel is bounded and visible rather than assumed away.

### 1.5 Audio2Tool — two invariants changed status

Source: the campaign README §11.6 (`.../2026-08-25-a2t-g1/README.md`), cross-checked against
the mechanical report's own counters.

| invariant | attempt 3 (pre-repair) | attempt 4 (post-repair) |
|---|---|---|
| branch-only replay (replayed supply = flown fusion decision) | **VACUOUS** — 0 trajectories branched | **PASS** — 15 replayed, 0 supply mismatches |
| `retain == direct-label-recovered` | **FALSIFIED** — 104 retained vs 89 recovered | **PASS / RESTORED** — 89 retained, 89 recovered, and the 15 dispatched are exactly the 15 label-free ids |

This row reproduces both independently: the offline replay in
`cross_carrier_ceiling_decomposition.fidelity_gate` reproduces the flight's own per-sample
supply on **104 of 104**, its dispatch decision on **104 of 104**, and its direct-label recovery
on **104 of 104** (receipt `fidelity_gate`). The restoration is not a claim about the carrier —
it is the strongest available evidence that the earlier zero-dispatch was the ranker scale
defect the owner ruling named, and not a property of Audio2Tool.

---

## 2. What is NOT established

1. **Exact match did not move at all.** BLEND 29 / 104 = 27.88 %, M0 29 / 104 = 27.88 %,
   delta **0.0 pp**, one W→C against one C→W, 90 % CI [−1.92, +1.92]
   (`g1-read-attempt4.json` `paired_exact_match`). The tool-accuracy reading below must never be
   reported without this line beside it — the campaign plan's §3.5 smuggling guard, carried
   verbatim.
2. **The +0.96 pp population delta is not separated from zero by its own interval.** Tool
   accuracy 62 → 63 of 104, **+1 sample = +0.9615 pp**, 90 % CI **[−2.88, +4.81]**, 95 % CI
   [−2.88, +4.81], σ̂ 2.15 pp, McNemar mid-p 0.6875, 41.56 % of replicates at or below zero
   (`paired_tool_accuracy`). *(The 90 % and 95 % bounds coincide because at n = 104 the
   bootstrap's support is 1/104 = 0.96 pp per sample and the interval is only a few atoms
   wide — a discreteness artifact, reported as it landed rather than smoothed.)* This is a
   **first signal on an EXPOSED tier**, below the campaign plan's own n ≥ 400 unexposed power
   floor. It is not a result.
3. **The empty-call collapse is a DIFFERENT metric and must not be substituted for an accuracy
   claim.** M0 14 / 104 = 13.46 % → BLEND 3 / 104 = 2.88 %, recomputed here through the frozen
   `analysis.a2t_read.is_empty_tool_call` (whose predicate is `len(predicted) == 0`, so it
   counts unparsed answers too: M0 = 10 literal empty + 4 unparsed). Converting "said nothing"
   into "said something" is a real and desirable property of the supply path, and it is **not**
   evidence that the answer is right — of the 15 dispatched trajectories, 12 ended as
   well-formed non-empty tool calls and **3** ended correct.
4. **No generality claim and no superiority claim.** The A2T population is EXPOSED, its numbers
   are secondary readings under the campaign plan §3.3, no ablation arm flew on this carrier
   (so nothing here attributes the A2T effect to retrieval rather than to the second contact —
   ABL-RANDRET answers that at G2), the corpus is synthetic with synthetic voice assignments,
   and the `a2t-gold-v1` scorer's semantics are interpretation rather than ground truth.
5. **Audio2Tool has no conversion anchors of its own that are worth calling anchors.** The four
   gold-bearing dispatched trajectories are four samples. §3.3 reports them as a mechanism
   reading and nothing else.

---

## 3. The decomposition — why the two carriers differ in magnitude

### 3.1 CEILING A — the α veto. A property of the POLICY FORM.

`rails/kb_policy._blend_scores` computes, for every label facet ℓ:

```
blend(ℓ) = α · fused(ℓ) + (1 − α) · [ℓ == direct_label]
```

so the recovered direct label `d` scores `α·f(d) + (1−α)` and every rival `r` scores `α·f(r)`.

**The range of `fused` is verified in the code, not assumed.**
`kb_policy._fused_label_scores` initialises each label's raw score to `best = 0.0` and only ever
takes `best = max(best, strength)`. So **raw ≥ 0 for every label whatever the ranker returns** —
a negative or unbounded candidate score cannot produce a negative raw label score. It then
divides by `total = sum(raw)` when `total > 0` and returns all-zeros otherwise. Therefore
`fused(ℓ) ∈ [0, 1]` and `Σ fused ∈ {0, 1}` **by construction**.

The worst case for the direct label is `f(d) = 0` with one rival at `f(r) = 1` — the only
configuration `Σ fused ≤ 1` permits. The margin is then

```
blend(d) − blend(r)  ≥  (1 − α) − α  =  1 − 2α
```

At the frozen **α = 0.45** this is **+0.10**, against `_argmax_labels`' tie tolerance of `1e-9`.
**A recovered direct label is therefore the strict, unique argmax for EVERY possible supply**,
and `KbAlphaBlendController._advance_after_direct` returns `_stop` — retain — whenever
`best_labels == (direct_label,)`. Hence:

> **`retain == direct-label-recovered` is a structural property of the policy form at α < 0.5,
> not an empirical observation.** Evidence can only ever reach trajectories from which no direct
> label was recovered. The reachable set IS the label-free set, exactly.

The condition is sharp: at α = 0.5 the worst case is an exact tie, which `_argmax_labels`
returns as a multi-label best set and the controller therefore **dispatches**; above 0.5 a
supply can outvote the direct label. There is one carve-out, and both carriers are checked
against it: a trajectory that never reaches the blend (empty recall, or the fuser selecting
nothing) retains without a blend being formed. On A2T that is **0 of 104** on each count
(receipt `fidelity_gate`); on SLURP DEV-1000 the flight's own decomposition closes exactly over
retain + dead-direct + override with no residual class.

**Empirical confirmation, and it is tight.** Over the 104 landed A2T trajectories the replayed
fused vectors have min 0.0, max 1.0 and sum ∈ [1 − 2e-16, 1 + 2e-16]; over the 89 trajectories
with a recovered direct label the **worst observed** `blend(direct) − max rival` is
**0.10000000000000003 on `tier2_parametric:003923`** — i.e. the structural floor `1 − 2α` is
attained, not merely respected.

**The reachable set on both carriers:**

| carrier | population | direct label recovered | reachable (label-free, dispatch) | reachable share |
|---|---|---|---|---|
| Audio2Tool `A2T-G1-104` | 104 | **89** | **15** | **14.42 %** |
| SLURP DEV-1000 unexposed | 500 | **340** | **160** | **32.00 %** |

A2T sources: `arm2-blend-mechanical.json` in the sealed attempt-4 run dir (sha256
`59458c491368a117721041e4ba1538549f3e1e28bdb342e4927703ad5892644e`), reproduced 104/104 by this
row's own replay. SLURP sources: `read-verdict.json`
`secondaries.dispatch_decomposition_unexposed500` (dead-direct n = 160; retain-primary n = 337;
override n = 3, and the 3 override fires are v2-only — under the locked v1 cell they retain, so
340 = 337 + 3 is the v1 direct-label-recovered count). Pooled cross-check at DEV-1000 scale:
674 recovered / 326 dead-direct / 660 retain / 14 override
(`mechanical_cross_checks.blend_dispatch_decomposition_exact`).

**The composition of the A2T reachable set**, recomputed here through the frozen parser: of the
15, **11 were literal empty calls, 3 were unparsed, and 1 parsed to a tool name outside the
151-entry label vocabulary**. The Audio2Tool direct decode produces a parseable in-vocabulary
tool name on 85.6 % of trajectories against SLURP's 68.0 % — the frozen core is simply *better*
at naming a tool on this carrier, and the α veto converts that competence directly into a
smaller surface for evidence.

### 3.2 CEILING B — gold coverage inside the admitted window. A property of KB COVERAGE.

Recomputed here from the **landed attempt-4 supply records**, not quoted. Method: recall → rank
→ fuse replayed through `kb_policy`'s own registered ranker and fuser at the locked knobs via
`dev100_damage_channel_analysis.replay_supply`; a supply "carries gold" when some selected
value's `task_target` equals the trajectory's gold PRIMARY tool; the fused target rank is the
gold target's position in `cf._fused_ranked_targets(fused_label_scores, label_targets)`. Gold is
read scoring-side only, from sealed records, after the seal.

**Fidelity gate first, as pre-registered:** replayed supply = flown supply on **104 / 104**,
replayed dispatch = flown dispatch on **104 / 104**, replayed direct-label recovery = flown on
**104 / 104**. No gold number would have been read otherwise.

| of the 15 dispatched | count |
|---|---|
| own contact-0 answer already correct | **0** — the supply path cannot disturb a single correct trajectory |
| gold tool's facet inside the admitted window | **4** |
| supply carried the gold tool's own value | **4** |
| … gold at fused target rank **1** | **2** (`tier1_direct:004159`, `tier3_multi_intent:000879`) |
| … gold at fused target rank **2** | **2** (`tier4_implicit:001513`, `tier5_needle:000061`) |
| … gold at fused target rank 3 | 0 |
| gold **absent** from the supply | **11** |

This reproduces the admission-scale sweep's pre-flight projection exactly (4 / 2 / 2 / 11,
`docs/readiness/2026-08-25-a2t-admission-scale-sweep.md` §5.2) — with one refinement: the
sweep's "rank 2–3" bucket is entirely rank 2. **The projection was made before the flight and
the flight matched it to the sample.**

**The two ceilings compound; neither dominates.** The α veto removes 89 of 104 (85.58 %); within
the 15 that survive it, the coverage ceiling removes a further 11 of 15 (73.33 %). Only **4 of
104 = 3.85 %** of trajectories are both reachable AND gold-supplied — the intersection is where
the method's best case actually lives on this carrier.

**And the α ceiling is not free money either.** If the α gate did not exist, **68 of 104**
trajectories would carry gold-bearing supply — 4 inside the dispatched set and **64** inside the
retained set. The retained 64 are not a missed opportunity in any simple sense (they are
retained because the direct answer already named a tool, and 60 of the 89 retained are already
correct, so a widened dispatch would be putting evidence in front of mostly-correct answers),
but the 68 does bound what any α change could possibly reach.

### 3.3 Conditional conversion — a MECHANISM reading, never an effect size

| stratum | n | BLEND correct | vs the M0 arm | vs its own contact-0 |
|---|---|---|---|---|
| A2T: dispatched, gold in supply | **4** | **2 (50 %)** | +2 | +2 |
| A2T: … gold at fused rank 1 | 2 | 1 (50 %) | +1 | +1 |
| A2T: … gold at fused rank 2 | 2 | 1 (50 %) | +1 | +1 |
| A2T: dispatched, gold absent | **11** | **1 (9.1 %)** | 0 | +1 |
| A2T: all dispatched | **15** | **3 (20 %)** | **+2** | **+3** |

**SLURP anchors, for comparison only** — `analysis.k1_hybrid_ranking_gate.ANCHOR_TOP1 /
ANCHOR_RANK23 / ANCHOR_ABSENT`, pooled over three sealed SLURP populations and published as the
table rows `108 / 110`, `16 / 23`, `0 / 67` in
`docs/readiness/2026-08-25-ec-and-retain-override-projections.md` §3 (recomputed identically in
`docs/readiness/2026-08-25-supply-budget-projection.md` §6):

| stratum | SLURP measured | A2T flown |
|---|---|---|
| gold at fused top-1 | **108 / 110 = 98.2 %** | 1 / 2 |
| gold at fused rank 2–3 | **16 / 23 = 69.6 %** | 1 / 2 |
| gold absent from supply | **0 / 67 = 0.0 %** | **1 / 11** |

**Read this as mechanism, not as effect size.** The A2T cells hold 2, 2 and 11 samples; SLURP's
hold 110, 23 and 67, on a different task with a different label space and a different answer
shape. No interval is computed across them and none should be. Two mechanism observations do
survive the sample sizes:

- **A2T conversion at rank 1 is visibly not SLURP's 98 %.** On SLURP, gold at the fused top-1
  almost always converts, because the answer is a single closed-set label and the supply names
  it. On A2T the answer is a JSON call list; naming the right tool is necessary but the scorer
  demands the full tool-name multiset, and 26 of the 104 gold call lists name at least two
  distinct tools (`g1-read-attempt4.json` `tool_name_multiset_mapping`). Supply that fixes the
  primary tool does not automatically fix the multiset.
- **The "gold absent ⇒ 0 conversion" anchor is not zero on this carrier.** One of the 11
  gold-absent dispatched trajectories (`tier4_implicit:003312`, gold `startWorkout`) ended
  correct — and it is one of the three method-attributable W→C flips. On A2T a supply can help
  by repairing the *form* of an answer the core already half-knew; on SLURP, where the direct
  answer is a label and the supply is a label, it cannot. **This is a genuine cross-carrier
  difference in how evidence acts, found by this decomposition and not predicted by it.**

### 3.4 Closing the arithmetic

```
population delta = Σ over subgroups of  (subgroup share) × (within-subgroup delta)
```

The subgroups partition the population, so closure is a **check on the read**, not a result. The
content is in the factors.

**Audio2Tool `A2T-G1-104`, tool accuracy, M0 62 → BLEND 63:**

| subgroup | n | share | M0 | BLEND | within-subgroup Δ | population contribution |
|---|---|---|---|---|---|---|
| reachable (dead-direct dispatch) | 15 | 14.42 % | 1 | 3 | **+13.33 pp** (W→C 3, C→W 1) | **+1.92 pp** |
| α-vetoed (retain-primary) | 89 | 85.58 % | 61 | 60 | −1.12 pp (W→C 0, C→W 1) | **−0.96 pp** |
| **total** | **104** | | **62** | **63** | | **+0.96 pp** |

Reconstructed +0.9615 pp against observed +0.9615 pp — **closes exactly**.

**SLURP DEV-1000 unexposed 500, intent accuracy, M0 278 → BLEND 379:**

| subgroup | n | share | M0 | BLEND | within-subgroup Δ | population contribution |
|---|---|---|---|---|---|---|
| reachable (dead-direct dispatch) | 160 | 32.00 % | 5 | 100 | **+59.38 pp** (W→C 97, C→W 2) | **+19.00 pp** |
| α-vetoed (retain-primary) | 337 | 67.40 % | 271 | 279 | +2.37 pp (W→C 9, C→W 1) | **+1.60 pp** |
| δ-override dispatch (**v2 only, removed from the lock**) | 3 | 0.60 % | 2 | 0 | −66.67 pp | **−0.40 pp** |
| **total as flown (v2)** | **500** | | **278** | **379** | | **+20.20 pp** |

Reconstructed +20.20 pp against observed +20.20 pp — **closes exactly**.

**And the locked v1 figure is re-derived rather than quoted.** Under v1 the 3 override
trajectories retain and answer with their own contact-0 direct decode; the lock-read README §5.3
records that counterfactual as 1, 1, 1. So v1 BLEND = 100 + 279 + 3 = **382 / 500**, and
382 − 278 = 104 → **+20.80 pp**, which is exactly what the lock verdict §3 states. *(A naive
subtraction that prices those three at the M0 ARM's decode instead gives +20.60 pp; the 0.20 pp
gap is the single sample `slurp:devel:002303` where the two arms' decodes of the same prompt
disagree. That is arm-level decode variance, not an arithmetic discrepancy, and it is recorded
here so nobody re-derives 20.6 and thinks the verdict is wrong.)*

**The cross-carrier table:**

| factor | Audio2Tool | SLURP unexposed 500 | ratio |
|---|---|---|---|
| reachable share | 14.42 % | 32.00 % | **2.22 ×** |
| within-reach conversion | +13.33 pp | +59.38 pp | **4.45 ×** |
| reach × conversion | **+1.92 pp** | **+19.00 pp** | **9.88 ×** |
| retain-subgroup drift | −0.96 pp | +1.60 pp | (sign differs) |
| population delta | **+0.96 pp** | **+20.20 pp** | |

**The arithmetic closes on both carriers, and the answer to the reviewer's question is: reach
and conversion, multiplied.** Nothing is left unexplained, so nothing supports "the method is
weaker on Audio2Tool" as a separate hypothesis. What *is* supported is that the retain-subgroup
drift differs in sign — +1.60 pp on SLURP against −0.96 pp on A2T — but on A2T that drift is one
sample (`tier8_intent_blending:000441`) whose flip the landed read attributes to **decode
variance**, not to the method. At n = 104 a single decode-variance sample is 0.96 pp, which is
the whole of the A2T retain drift and the whole of the A2T population delta. **That is the real
statistical reading: the A2T population number is one sample of signal against one sample of
noise, and the mechanism reading in §3.1–3.3 is the only part of this carrier's result worth
anything.**

### 3.5 Which ceiling is which

| ceiling | belongs to | changing it requires | out-of-sample risk |
|---|---|---|---|
| **A — the α veto** (reach: 14.42 % vs 32.00 %) | the **POLICY FORM**. It is arithmetic in `_blend_scores` at α < 0.5, identical on every carrier, and it interacts with a *carrier property*: how often the frozen core's direct decode names an in-vocabulary label at all | changing α, or changing the dispatch predicate, i.e. **changing the locked cell** | high — see §4 |
| **B — gold coverage in the admitted window** (4 of 15 on A2T; recall@5 = 0.744 on SLURP unexposed 500) | **KB COVERAGE and the key representation**. It is a property of what the knowledge base contains and how the ranker orders it | changing KB construction or the key plane — **the locked cell is not touched** | lower; each item is gated offline before any flight |

---

## 4. The next-lever ranking, with priors stated

### L1 — KB gold coverage and key construction for label-free trajectories. **Rank 1.**

**Why first: it does not touch the locked cell at all, and it is binding on both carriers.** Of
the 15 A2T trajectories that survive the α veto, 11 got no gold at all; on SLURP the residual is
68–73 % recall-limited with the gold facet sitting at rank 6–2,023. It is ranked above L2 not
because it is the bigger ceiling — §3.2 shows the two compound rather than one dominating — but
because it is the one that can be moved **without changing the locked cell**, and because every
item in it is gated offline before it costs a contact. This is the priority-2 key agenda's
territory (`docs/readiness/2026-08-25-key-construction-agenda-plan.md`).

**Honest prior: modest, and one item is already closed.** K1 (same-text lexical/BM25 fusion) ran
its offline gate and is **refused for flight**: RRF-60 raises gold recall@5 on the unexposed 500
from 0.744 to 0.762 (+9/500) but **lowers recall@1 from 0.636 to 0.590 (−23/500)**, and because
the measured anchors are steeply rank-dependent (98.2 % at top-1 vs 69.6 % at 2–3), 23 demotions
against 9 promotions does not close; central conversion projections are negative on all four
populations (−0.75 to −2.70 pp) (key plan §6). Two durable assets survive: multi-dimensional K
is now demonstrably realisable, and the lexical channel is effectively free. **Next in this
lane: K2 (v5 pair-boundary material as discriminative key text), then K3 (field-role-constrained
contact-0).** The plan's own stated prior is **single-digit pp, not another +20**: reachability
even at k = 32 is 0.866. Every item here inherits K1's methodological correction — **the
falsifier must be two-sided** (raise recall@5 AND not lower recall@1), or be stated directly on
the conversion-weighted objective.

**Answerable offline at zero contacts:** the gates, yes — every one of them is a replay over
sealed records. The flights are not.

### L2 — the α form / dispatch widening. **Rank 2, and it carries an adverse prior.**

**The adverse prior, recorded in full.** The δ ≥ 0.14 retain-override was the last attempt to
widen dispatch beyond the α veto. Its registered property was *zero loss by construction*; it
held on every exposed population (DEV-100 r4/r5, DEV-500 NEW400) and in the A4 flight (3/3
recovered, 0 disturbed). Out of sample it **recovered 0 of 3 and damaged 3 of 3** — net −3
samples, −0.60 pp — while the 11 fires in the previously-exposed half recovered 11/11. Two of
the three failures sat at δ = 0.140362, **0.000362 above the hand-fit bar**. It was removed from
the locked cell (lock verdict §3).

> **Any dispatch-widening proposal inherits that prior and must be gated OUT OF SAMPLE.** A rule
> fit on data the reader has already seen, whose loss side is "zero by construction", is exactly
> the shape that failed. In-sample perfection is not evidence.

**And the second, non-statistical cost.** Any **per-carrier α** breaks the byte-identical
transfer claim — which is itself a scientific asset, arguably the most valuable single sentence
this carrier has produced (§1.3). So this is an **OWNER decision framed as a trade**, never a
tuning step: buy reach on one carrier, sell the strongest generality statement the study has.
The campaign README §11.9 says the same in its own words, and no implementer may make that
trade.

**Answerable offline at zero contacts:** yes, the *sizing* is. What the method could reach at
other α values, over the already-landed vectors, texts and supplies, costs nothing — §3.2 has
already produced its headline number (**68 of 104** would carry gold-bearing supply with no α
gate). A full α curve with projected conversion is a further offline row. **Changing α is a knob
change and requires owner authorisation regardless of what the curve says.**

### L3 — a powered confirmatory read on Audio2Tool (G2). **Rank 3, and it needs contacts.**

**Prior: as scoped it does not fit, and at the measured effect it may still be underpowered.**
79 core contacts remain against a G2 scope of four arms over 400 unexposed samples (§5). And the
power calculation must be done against **the decomposition, not the population**: a whole-
population effect the mechanism structurally cannot produce is the wrong thing to power against.
At a 14.4 % reachable share and 20 % within-reach conversion, the population-level signal is
small by construction. The plan's own power note (§3.5) records SLURP's held-out σ̂ at
**1.9–2.1 pp at n = 400–500** and states that A2T per-sample variance is *higher* because of
multi-call items — so a 90 % interval at n = 400 is wider than ±3 pp on this carrier, against a
population effect the mechanism caps near +2 pp. **The right G2 design is stratified on the
reachable set, or it is not worth flying.** This is an owner decision, and this document does
not make it.

### L4 — re-measure the A2T decode-variance channel. **Rank 4, cheap, needs contacts.**

The A2T variance channel is currently a single number inferred from 11 divergent texts at
n = 104. §3.4 shows the entire A2T population delta is one sample, which is the same size as one
decode-variance flip. **A repeated-decode replication at fixed config is already required by the
campaign plan §3.5 and is the cheapest thing that would make any A2T number interpretable.**

### Offline vs contacts, at a glance

| lever | answerable offline at zero contacts? |
|---|---|
| L1 gates (K2, K3 reachability replays) | **yes** — replays over sealed records |
| L1 flights | no |
| L2 α sizing / α curve | **yes** |
| L2 α change | no — and it is an owner knob decision, not a computation |
| L3 G2 | no |
| L4 replication | no |

---

## 5. Budget and operational state

**The AttemptStore is the spend authority**, not any summary. Read directly from
`$SPEECHRL_DATA_DIR/attempts/SAEA-A2T-G1/` (five attempt records):

| attempt | state | durable calls | durable audio s |
|---|---|---|---|
| `attempt-20260825T100735Z-a2tg1m0` | OPENED | 106 | 590.251 |
| `attempt-20260825T101057Z-a2tg1blend` | OPENED | 28 | 73.633 |
| `attempt-20260825T114856Z-a2tg1blend` | OPENED | 62 | 277.177 |
| `attempt-20260825T125051Z-a2tg1blend` | OPENED | 107 | 591.348 |
| `attempt-20260825T144405Z-a2tg1blend` | OPENED | 18 | 58.247 |
| **run-cumulative** | | **321** | **1,590.656** |

*(All five records read `state: OPENED` rather than a terminal state; the durable `actual`
block is what each launcher wrote at landing and is what every campaign artifact's
`campaign_cumulative_incl_prior_arms` figure is computed from. The 321 / 1,590.656 pair
reproduced here from the store matches the attempt-4 report's own
`spend_vs_ceilings.campaign_cumulative_incl_prior_arms` exactly.)*

Against the campaign cell (`configs/experiment/a2t-g1-v1.json` `a2t_g1_ceilings`): **321 / 400
core contacts**, **1,590.656 / 2,000 metered audio seconds**. **79 core contacts remain.**

**Tool contacts are 136 / 200, and their authority is weaker — disclosed rather than smoothed
over.** The AttemptStore's `actual` block records only `calls` and `audio_seconds`; it carries no
tool-contact field. The 136 figure is carried by the arm mechanical reports (attempt 3: 10 = 8
bridge + 2 jitter; attempt 4: 0) and the campaign README §11.3. It is consistent across those
artifacts but it is **not** AttemptStore-backed, and a future campaign should extend the store
rather than rely on report arithmetic.

**What 79 core contacts buys and does not buy.** It does not buy G2 as scoped (four arms × 400
unexposed ≈ 2,600–3,000 core contacts; plan §5). It does not buy a second full 104-item paired
arm at the single-pass shape. It **does** buy roughly one 15-dispatch evidence pass at the
two-pass replay shape (attempt 4 flew a complete 104-trajectory arm for 18 core contacts), or a
small repeated-decode replication on a stratified subset. **No implementer may raise that cell.**

**Operational debt, carried unchanged:** the SLURP np8 service `saea-np8-dev100-r6-base` remains
DOWN and must be respawned by a later mission before any SLURP arm flies. The A2T np2 service
(pid 38623, port 8090) was resident and idle throughout this row and was not touched.

---

## 6. Corrections carried

Per repository discipline, a claim in an existing document that this row's computation
contradicts is corrected explicitly rather than quietly.

**C1 — `docs/checks/speech-aware-evidence-acquisition/2026-08-25-a2t-g1/README.md` §11.7.**
The superseded sentences are:

> "Whatever the evidence is worth, it can only be applied where the direct answer parsed to
> nothing — 14 empty calls plus 4 unparsed answers on this population."

and

> "Within that subgroup the evidence contact does most of what it can: **11 of the 14 empty
> calls and all 4 unparsed answers become well-formed tool calls**, but only 2 of them become
> correct."

Two defects, both recomputed here through the frozen `analysis.a2t_read.is_empty_tool_call` and
`reproduction.toolcall_scoring.parse_tool_calls_text` over the sealed answer files:

1. **The 14 and the 4 are the same answers counted twice.** `is_empty_tool_call` is
   `len(predicted) == 0` and `parse_tool_calls_text` fails closed to `([], False)`, so the M0
   arm's 14 "empty calls" already *contain* its 4 unparsed answers (10 literal empty + 4
   unparsed = 14). "14 empty calls plus 4 unparsed" double-counts; the correct statement is
   "14 answers with an empty predicted call list, of which 4 failed to parse".
2. **They are the M0 arm's counters, and the dispatch set is decided by the BLEND arm's own
   contact-0.** The BLEND arm's Pass-A texts (byte-identical to attempt 3's, sha256
   `73e28511f419cd67b1721d829438f8c102e725e01243c9a9f000e00d92aadc9c`) classify as **11 literal
   empty calls + 3 unparsed + 1 parsed-but-out-of-vocabulary = the 15 dispatched**, not 18 and
   not 14 + 4. On the final answers, **12 of the 15 became well-formed non-empty tool calls**
   (3 remained empty), not 15.

The corrected reading of the subgroup, all of it recomputed in this row's receipt: 15 dispatched,
own contact-0 correct **0 / 15**, BLEND correct **3 / 15**, and **+2** against the M0 arm (the
difference being `tier1_direct:001631`, correct in the M0 arm and wrong under BLEND — the
AMBIGUOUS flip of §1.4). **The README's "only 2 of them become correct" is right against the M0
arm and wrong against the subgroup's own pre-evidence answers, where the figure is 3.** No
headline number in any landed artifact changes: the read's `subgroups.dead-direct-dispatch`
block already carries `m0_tool_accuracy 1/15`, `blend_tool_accuracy 3/15`,
`tool_accuracy_delta_samples 2`, all of which this row reproduces.

The README is an immutable landed check record and is **not** rewritten in place; this section is
its English successor.

**C2 — no contradiction found elsewhere.** The admission-scale sweep's §5.2 projection
(4 gold-bearing of 15, 2 at rank 1, 2 at rank 2–3, 11 absent) is reproduced here **exactly** on
the landed post-flight supply, with the refinement that the "rank 2–3" bucket is entirely rank 2.
Its §5.3 central projection of **63.35 / 104** correct is met by the flown **63 / 104** — while
being wrong in both directions internally (it priced the 4 gold-bearing trajectories at 3.36
expected conversions and got 2; it priced the 11 gold-absent at 0 and got 1). The band was
right for partly compensating reasons, and it said so itself: it labelled every anchor
CROSS-CARRIER and declared that Audio2Tool has no anchors of its own. **That disclaimer is
vindicated, not dispensed with.**

**Not verified, and therefore not used.** Two quantities I wanted and could not establish from
landed artifacts at zero contacts, listed so their absence is visible: (a) the SLURP
gold-fused-rank distribution restricted to the unexposed-500 *dead-direct* subgroup — the
anchors in §3.3 are pooled over three sealed populations and are not re-derivable per subgroup
from the committed artifacts alone; and (b) any Audio2Tool variance estimate independent of the
n = 104 read's own bootstrap. Both would need their own registered rows.

---

## 7. HARD STOP — what this document does NOT authorize

This is a **consolidation read over landed evidence at zero contacts**. It authorizes:

- **nothing to fly.** No model contact, no tool contact, no flight, no re-flight, no G2 opening.
- **no knob change.** `configs/policy/kb-policy-v1-dev100.json` is read and hash-checked, never
  written. `rails/` and `core/` are untouched. Any α change, dispatch-predicate change or
  per-carrier cell is an **owner decision**, framed as the trade in §4/L2.
- **no generality claim.** The Audio2Tool mechanism transfers; the magnitude is one sample on an
  EXPOSED tier below the campaign's own power floor. "The locked cell generalizes" is not
  established here and is not implied here.
- **no superiority claim**, no test contact, **FINAL60 stays reserved**, and no Stage-3 activity.
  Stage-3 requires `OWNER_GO_AND_PAPER_EXECUTION_CONTRACT` into a `papers/<slug>` repository and
  this repository never accepts it.
- **no budget increase.** 79 core contacts remain on `SAEA-A2T-G1`; no implementer may raise
  that cell.

`consumed` stays **no**: no seal is broken by this row. Gold was opened scoring-side only, over
the EXPOSED A2T-G1-104 whose seal the landed G1 read had already broken, and the SLURP
populations were read from their own landed verdicts.
