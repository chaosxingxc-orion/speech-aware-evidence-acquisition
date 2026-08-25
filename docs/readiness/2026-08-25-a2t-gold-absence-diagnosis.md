# A2T GOLD-ABSENCE DIAGNOSIS — the KB is not the defect and depth is not the fix;
# on the reachable subgroup the retrieval key is a CONSTANT

Date: 2026-08-25. Status: **DIAGNOSIS — computed, ZERO CONTACTS, fidelity gate passed 104/104.**
Row `SAEA-SN-MF-A2T-GOLD-ABSENCE-DIAGNOSIS` (registered `71397517`, **before any computation**).
Module `src/speech_aware_evidence_acquisition/analysis/a2t_gold_absence_diagnosis.py`.
Receipt `docs/checks/speech-aware-evidence-acquisition/2026-08-25-a2t-gold-absence/diagnosis-report.json`
(sha256 `64327e98ff9f91a4affdf75f25e98eb5500aa4ab2eeab8befa6d3978799a3e14`).

**Spend: 0 frozen-core contacts, 0 embedding-tool contacts, 0 tokenizer contacts, 0 audio seconds,
0.0 GPU hours, 0 new dependencies.** The offline guard
(`analysis.dev100_reviewer_audit.arm_offline_guard`) was armed before the first input was opened and
recorded **0 outbound connection attempts against 0 targets**. The resident np2 A2T service on port
8090 (pid 38623) was never contacted, probed, reconfigured or stopped. Wall 271.5 s. No knob was
changed; `configs/`, `rails/` and `core/` were not written.

Every number below carries the artifact it came from. Where a quantity could not be established from
landed bytes at zero contacts it is declared unverified in §9 rather than estimated.

---

## 0. The answer in one paragraph

**The Audio2Tool KB does not have a coverage hole, and widening the window would not have helped.**
Of the 11 gold-absent dispatched trajectories, **0 are a BUILD defect and 11 are a RANKING defect** —
every one of their gold tools sits in the pinned snapshot with 144–189 values and 144–189 vectored
content facets. But the ranking defect is not where the key-construction agenda expected it either.
**9 of the 11 are refused by the τ = 0.65 percept gate** (their best gold-bearing facet scores
0.5653–0.6356), which no window depth can lift, and the other **2 are refused by the `top_l` = 3
target budget**, which is not a window knob either: **0 of 11 are reached at ANY depth under the
locked cell.** The reason the cosines are low is the deliverable finding: on the reachable subgroup
**the retrieval key is a constant.** The 15 dead-direct trajectories carry only **5 distinct query
vectors**, and **11 of the 15 share ONE identical key** — the embedding of the empty tool call — and
therefore received **one identical supply**, the three targets `cancelNavigation` /
`setHapticStrength` / `setPowerState`, whatever the utterance was about. Gold reached exactly one of
those 11, by coincidence, and that one still scored wrong. The SLURP dead-direct retrieval deficit is
present on Audio2Tool and is **several times larger** (gold-in-top-5 26.67 % vs 71.91 %, a −45.24 pp
gap against SLURP's −4.0 to −7.9 pp, i.e. 5.7× to 11.3× and ≈ 7.6× at the midpoint; median
gold-facet cosine 0.6054 vs 0.8632, −0.2578 against SLURP's −0.053, i.e. 4.9×). The compounding story is not merely confirmed — the second ceiling is a *consequence*
of the first, because the α veto selects precisely the trajectories whose answer text is empty, and
the answer text IS the query. Finally, **K3 (field-role-constrained contact-0) is an off-switch in
disguise on this carrier and is refused on that ground**: projected dispatch falls from 15/104 to
between 13/104 and 3/104, i.e. **−1.92 pp to −11.54 pp, −13.3 % to −80.0 % relative** (§7).

---

## 1. Provenance and gates — nothing below was read until these passed

### 1.1 The fidelity gate (pre-registered as necessary, not decorative)

Recall → rank → admit → fuse → blend, replayed offline through `rails.kb_policy`'s own registered
ranker, registered fuser, `_fused_label_scores`, `_blend_scores` and `_argmax_labels` at the locked
knobs, against the sealed attempt-4 flight
(`docs/checks/.../2026-08-25-a2t-gold-absence/diagnosis-report.json` → `fidelity_gate`):

| gate | result |
|---|---|
| replayed supply = flown per-sample supply | **104 / 104**, 0 mismatch ids |
| replayed dispatch decision = flown decision | **104 / 104**, 0 mismatch ids |
| replayed direct-label recovery = flown | **104 / 104**, 0 mismatch ids |
| trajectories with empty recall / empty supply | **0 / 0** |

The registration fixed this as a hard precondition: no gold-coverage or gold-rank number is read
unless all three read 104. They do.

### 1.2 The retrieval geometry is pinned to `kb_policy`'s own arithmetic

The full-KB cosine sweep is not trusted on its own (`recall_fidelity`): `kb.multidim_recall` is
called for real on **8** probe samples and must admit the same facet set with the same scores to
1e-9; `kb_policy._cosine` is called for real on **72** individual (query, facet) pairs — the top-8
window plus each probe's gold facet — and must reproduce each vectorised cosine to 1e-9. Both pass.

### 1.3 The ranker's order IS the cosine order — verified, not assumed

`ranker_ordering_check`, over **all 104** trajectories at a recall depth of 128:

- every content facet's `agreement` is the constant **1/3** (`dims_total` = 3 on every trajectory);
- every content facet's `max_prior` is **0.0**;
- the ranker's content-facet ordering equals the raw cosine ordering on **104 of 104**, 0 disagreements.

This is §2.1 of the key-construction agenda plan's degeneracy, confirmed on this carrier. It is what
licenses every depth statement in §3 to be a statement about one single ordering.

### 1.4 Artifact hashes

| artifact | sha256 |
|---|---|
| A2T knowledge snapshot | `ec2f9ec454d3f16957ac08e4d7686a6f3941f22c600ff2b1b2b97ff43baf9fb2` |
| content-facet NPZ | `00a7ebe9b8325ffc2c7b8e45ac4f0c8475b2d3e76994cc0f539f7b5ad5740f45` |
| sealed Pass-A direct outputs | `73e28511f419cd67b1721d829438f8c102e725e01243c9a9f000e00d92aadc9c` |
| sealed attempt-4 BLEND answers | `24a7864263226f4918076571aee359d40ee76838f9cea1da2bbae38f6b6bdd18` |
| sealed attempt-4 mechanical record | `59458c491368a117721041e4ba1538549f3e1e28bdb342e4927703ad5892644e` |
| sealed attempt-4 query vectors | `2915aa0e4c690fc612777f28c88949956b2cfb108582c4e40eaca36e6a184be7` |
| sealed M0 answers | `dea60ff1e63fd2ef11c93edf8808217062fea3f0565ed5b60f136264bc6a9467` |
| `rails/kb_policy.py` as read | `2a1c3d75e747db10f723044b05c08d232e1edf47f125d0889c1d2565ba1019af` |
| A2T-G1-104 subset receipt | `b42f0953a0d168955ba5ddfc77f2c300aacb54e48dce902d1b3d4a109c1996db` |

**KB shape** (`kb_shape`): 12,601 values, 12,601 vectored content facets, 12,903 content facets
carrying a task target, **151** distinct value targets against a **151**-entry label vocabulary.

### 1.5 The 4 / 11 split this row diagnoses is the SAME 4 / 11 the verdict reports

`gold_coverage_dispatched` recomputes the cross-carrier verdict's §3.2 block on the same
fidelity-gated replay and reproduces it exactly: 15 dispatched, **4** gold-bearing (rank 1: 2,
rank 2: 2, rank 3: 0), **11** gold-absent, and **68 of 104** would carry gold-bearing supply with no
α gate. The diagnosis below is of that block and not of a differently-computed one.

---

## 2. Q1 — BUILD coverage versus RANKING. **The split is 0 / 11, and RANKING dominates outright.**

Source: `q1_build_versus_ranking`. A trajectory is a **BUILD** defect when its gold PRIMARY tool has
no value in the pinned snapshot, or none of that value's content facets carries a landed vector — in
which case no ranker, no width and no key representation could ever surface it. Otherwise it is a
**RANKING/recall** defect.

| | count | sample ids |
|---|---|---|
| **(a) BUILD coverage defect** | **0** | — |
| **(b) RANKING / recall defect** | **11** | `tier1_direct:000167`, `tier1_direct:001631`, `tier2_parametric:004826`, `tier4_implicit:000655`, `tier4_implicit:000900`, `tier4_implicit:001148`, `tier4_implicit:001389`, `tier4_implicit:001409`, `tier4_implicit:003312`, `tier7_multiturn:000214`, `tier7_multiturn:001516` |

**Dominating sub-cause: RANKING, 11 of 11.**

Every one of the 11 gold tools is present in force. Per-tool KB depth for the 11, read off
`case_b_ranking_recall_defect.rows`: **144–189 values**, **146–191 content facets** and **144–189 of
those facets vectored**, and all 11 gold tools are inside the 151-entry label vocabulary.

And the carrier has **no build hole at all**: over the whole 104,
`population_coverage_context` reads **0** trajectories whose gold tool has no KB value and **0**
whose gold tool has no vectored facet. The A2T KB covers every gold tool in the population.

> **This is the load-bearing negative.** A KB-construction lever (more values, more tools, deeper
> coverage) has nothing to fix on this population. The remaining ceiling is entirely on the
> retrieval side.

---

## 3. Q2 — the reachability curve, and why depth is refused twice over

Source: `q2_reachability_curve`. Positions are 1-based in `kb.multidim_recall`'s OWN recall ordering
(cosine descending, `facet_id` ascending), so "position p" means exactly "this facet enters the
window at `top_k ≥ p`".

### 3.1 The curve

| depth k | case (b), n = 11 | all dispatched, n = 15 | all retained, n = 89 | whole population, n = 104 |
|---|---|---|---|---|
| 5 (**the locked cell**) | **0 (0.000)** | 4 (0.267) | 64 (0.719) | **68 (0.654)** |
| 8 | 1 (0.091) | 5 (0.333) | 72 (0.809) | 77 (0.740) |
| 16 | 3 (0.273) | 7 (0.467) | 76 (0.854) | 83 (0.798) |
| 32 | 3 (0.273) | 7 (0.467) | 81 (0.910) | 88 (0.846) |
| 64 | 3 (0.273) | 7 (0.467) | 84 (0.944) | 91 (0.875) |
| 128 | 4 (0.364) | 8 (0.533) | 86 (0.966) | 94 (0.904) |
| 256 | 9 (0.818) | 13 (0.867) | 88 (0.989) | 101 (0.971) |
| 512 | 11 (1.000) | 15 (1.000) | 89 (1.000) | 104 (1.000) |
| 1024 / full KB | 11 (1.000) | 15 (1.000) | 89 (1.000) | 104 (1.000) |
| gold-facet position min / median / max | 8 / 178 / 430 | 1 / 83 / 430 | 1 / 1 / 466 | 1 / 1 / 466 |

The whole-population `recall_at_5` = **68 / 104** independently reproduces the cross-carrier
verdict's "68 of 104 would carry gold-bearing supply with no α gate" — two different computations
landing on the same integer.

### 3.2 Which stage actually binds — and it is not the window

A recall window is not an admitted window. Three stages sit between the recall ordering and the
supply, and each can independently keep the gold value out. `binding_stage`, with the widened supply
**actually replayed** through `kb_policy`'s own fuser at each depth rather than inferred from a rank:

| | count of the 11 |
|---|---|
| **blocked by the τ = 0.65 percept gate** (best gold-bearing facet cosine 0.5653–0.6356) | **9** |
| blocked by the `top_l` = 3 target budget only (gold facet passes τ, gold target ranks 8th) | **2** |
| **reached at SOME depth under the locked `top_l` = 3** | **0** |
| reached at some depth if `top_l` were lifted entirely | 2 (at depths 8 and 16) |

The two `top_l`-blocked trajectories are `tier2_parametric:004826` (gold `setGroupLightState`, facet
cosine 0.8548, facet position 10, gold target rank **8** among 65 τ-passing targets) and
`tier7_multiturn:001516` (gold `activateRoutine`, facet cosine 0.6768, facet position 8, gold target
rank **8** among 10 τ-passing targets).

### 3.3 Is any ADMISSIBLE depth a fix? **No — and it is refused twice over.**

1. **The locked cell.** `k`, `m`, `τ`, `c` and `top_l` are all cells of
   `configs/policy/kb-policy-v1-dev100.json`, which is LOCKED. **No depth in this curve is
   admissible without an owner knob decision**, and this document makes none.
2. **Even granting the knob change, depth does not reach.** Under the locked `top_l` = 3, **0 of 11**
   gold values enter the supply at any depth up to the full 12,601-facet KB. For 9 of the 11 the τ
   gate refuses the facet at every window size, so `k` and `m` are irrelevant to them by
   construction; for the other 2 the refusal is the `top_l` target budget, which is a *budget* knob,
   not a *window* knob. The reachability curve in §3.1 rises to 1.000 at k = 512 and **none of that
   rise converts into an admitted supply.**
3. **The K-WIDEN prior, attached as the registration requires.** K-WIDEN K1 flew on exactly the
   reachability argument this curve would license — *the gold facet exists deeper, so widen* — and
   returned: supply changed on **32 of 100** trajectories and **0 width-attributable flips**
   (71/100 at Δ−1) (`docs/readiness/2026-08-25-key-construction-agenda-plan.md` §1). A reachability
   curve is evidence about REACHABILITY only. It has never, on this program's own record, been
   evidence about conversion.

> **Depth is not the lever, and this row does not present it as one.** The 4/11 gold-absence is not
> a window that is too narrow; it is a query that is too weak (§4) and a percept gate the query
> cannot clear.

### 3.4 These are ranking statements, and they were computed under a DEFECTIVE prior — bounded here

`rails.knowledge_build_a2t` sets `prior_score = tool_total / category_total`, where `tool_total`
counts a tool's rows across EVERY domain while `category_total` counts one `(domain, category)`
only. The numerator is not a subset of the denominator, so the ratio is not a conditional probability
and has no reason to be ≤ 1; the intended quantity is
`p(tool | domain, category) = count(tool AND category) / count(category)`. The landed
`max(1.0, sup)` repair in `kb_policy._dimension_scales` is a **monotone rescale of a wrong ratio, not
a correction of it**. This is already recorded in that function's own docstring under the
2026-08-25 owner ruling.

§2's case-(b) membership and §3's curve are RANKING statements, so they are computed under that
defective prior and are the record of what actually happened. Rather than rebuild the snapshot under
the corrected quantity — which would need the source rows, a rebuild and a re-embed, none of which a
zero-contact row may do — this row **brackets every possible correction**
(`a2t_prior_dimension_sensitivity`). A corrected prior is a probability, so it lies in [0, 1]; the
supply is replayed at the SUPREMUM (every prior-mass score set to 1.0) and at the INFIMUM (the
prior-mass dimension removed entirely), and any correction lies weakly between them.

| | value |
|---|---|
| recalled prior-score supremum | **4.1** (10 recalled prior-mass facets, all > 1) |
| snapshot `prior_score` supremum / values above 1 | **4.1** / **193** — reproduces the `kb_policy` docstring exactly |
| prior-mass facets inside the locked top-`m` = 5 window | **0**, on 104 of 104 trajectories |
| supply changed by `prior_at_unity` vs as-flown | **0 of 104** |
| supply changed by `prior_dropped` vs as-flown | **0 of 104** |
| as-flown replay matches the flight on every dispatched trajectory | **yes** |

> **Every ranking statement in this document is invariant to the prior defect — measured, not
> assumed.** After the landed scale repair, no prior-mass facet reaches the top-`m` window on any of
> the 104, so the prior contributes nothing to admission on this population and no correction of it
> can move a number here. A semantically corrected-prior secondary column would therefore be a
> column of zeros; it is not reported because the bracket above already dominates it. The prior
> defect remains a real defect worth fixing on its own terms — it is simply not load-bearing for
> this diagnosis.

---

## 4. Q3 — the dead-direct query deficit is PRESENT, and it is several times larger than SLURP's

Source: `q3_dead_direct_contrast`. Both statistics were fixed in the registration before the module
ran: the gold-in-top-5 rate over the full-KB dense ordering, and the median best gold-bearing facet
cosine. The SLURP figures are QUOTED from
`docs/readiness/2026-08-25-key-construction-agenda-plan.md` §2.2 — this row opened no SLURP run
directory and recomputed no SLURP number.

| statistic | A2T dead-direct (n = 15) | A2T label-recovered (n = 89) | A2T gap | SLURP gap (quoted) |
|---|---|---|---|---|
| gold-in-top-5 | **4 / 15 = 26.67 %** | **64 / 89 = 71.91 %** | **−45.24 pp** | 66.2–67.6 % vs 71.6–74.1 % ⇒ **−4.0 to −7.9 pp**, midpoint −5.95 |
| median gold-facet cosine | **0.6054** | **0.8632** | **−0.2578** | 0.775 vs 0.828 ⇒ **−0.053** |
| mean gold-facet cosine | 0.6792 | 0.8522 | −0.1729 | — |
| median gold-facet position | **83** | **1** | — | — |
| median top-1 cosine (any facet) | 0.7740 | 0.8774 | −0.1034 | — |
| gold present in KB | 15 / 15 | 89 / 89 | — | — |

**The deficit is PRESENT on both statistics.** On the top-5 statistic it is **5.7× to 11.3×** the
SLURP deficit depending on which end of SLURP's quoted per-population range is used, and **≈ 7.6×**
at its midpoint; on the cosine statistic it is **4.9×**. SLURP's figures are ranges across three
populations rather than one paired number, so the ratio is reported as the interval those figures
actually permit and not as a point. The
compounding story in the cross-carrier verdict §3.2 is not merely intact; the mechanism is stronger
than it claimed.

### 4.1 Why. The retrieval key on the reachable subgroup is a CONSTANT.

`q3_dead_direct_contrast.query_key_degeneracy`. The content-dimension query vector IS the embedding
of the trajectory's OWN contact-0 answer text — verified in this row by re-hashing each landed
Pass-A text against the `text_sha256` its own landed query-vector record carries. So when the answer
is literally the same string, the key is the same vector.

| | dead-direct (n = 15) | label-recovered (n = 89) |
|---|---|---|
| distinct contact-0 texts | **5** | 84 |
| distinct query vectors | **5** | **84** |
| distinct keys per trajectory | **0.333** | **0.944** |
| largest identical-key cluster | **11 (73.3 %)** | 3 (3.4 %) |

And the consequence, measured on the flight's own landed supply
(`query_key_degeneracy.largest_cluster_supply`):

- the 11-trajectory cluster received **exactly ONE distinct flown supply**;
- its targets are **`cancelNavigation`, `setHapticStrength`, `setPowerState`** — the same three
  tools for all 11, whatever the utterance was about;
- **1 of the 11** had its own gold tool inside that constant set (`tier4_implicit:001513`, gold
  `setPowerState`) — a coincidence, not a retrieval — **and it still scored wrong.**

> **This is the mechanism that makes the two ceilings compound, and it is tighter than "correlated".
> The α veto is a filter on "the answer named no in-vocabulary tool"; on this carrier that is
> overwhelmingly "the answer was empty"; and the empty answer is the query. The α veto therefore
> selects, with near-certainty, exactly the trajectories whose retrieval key carries no information.
> Ceiling B is not merely correlated with ceiling A on Audio2Tool — it is largely CAUSED by it.**

That also explains §3.2's τ result without any further hypothesis: a constant key produces one fixed
neighbourhood of the embedding space, its best cosines top out at 0.7740, and an arbitrary
trajectory's gold facet lands at a median position of 83 with a cosine of 0.605 — below τ.

---

## 5. Q4 — the multiset requirement is binding on exactly ONE trajectory

Source: `q4_multiset_binding`. The frozen `a2t-scorer-v1` scores tool accuracy as equality of the
full tool-name MULTISET; the dispatch projection uses only the PRIMARY call's name, so on a
multi-tool item the projection is lossy by construction.

| | all 104 | the 15 dispatched | the 4 gold-bearing dispatched |
|---|---|---|---|
| multi-tool gold (≥ 2 distinct tools) | **26 (25.00 %)** | **1 (6.67 %)** | **1 (25.00 %)** |
| supply covered the WHOLE gold tool set | 60 | 3 | 3 |
| **supply covered only PART of a multi-tool gold** | **13** | **1** | **1** |
| multi-tool gold ending correct under BLEND | 9 / 26 (34.6 %) | 0 / 1 | 0 / 1 |
| single-tool gold ending correct under BLEND | 54 / 78 (69.2 %) | 3 / 14 | 2 / 3 |

The single partial-coverage case is **`tier3_multi_intent:000879`**: gold names
`{getCameraEvent, setColorTemperature, setLighting}`, the supply carried **`getCameraEvent` only**,
and it scored **wrong**. It is precisely the **rank-1 gold-bearing failure** — the reason A2T's
rank-1 conversion reads 1/2 against SLURP's 108/110.

**Reading, with the sample size in front of it.** The cross-carrier verdict §3.3 offered the
multiset requirement as the explanation for A2T's low rank-1 conversion. That explanation is
**confirmed, on n = 1, and cannot carry more weight than n = 1.** It is also *not* a general property
of the reachable set: the dispatched 15 are **14/15 single-tool gold (6.67 % multi-tool against
25.00 % in the population)**, so the α veto systematically routes multi-tool items AWAY from the
reachable set. The multiset requirement is a real ceiling on the population and a marginal one on the
subgroup evidence can reach.

---

## 6. Q5 — the FORM channel is wide and weak; the KNOWLEDGE channel is narrow and strong

Source: `q5_form_repair_channel`, recomputed through the frozen
`analysis.a2t_read.is_empty_tool_call` and `reproduction.toolcall_scoring.parse_tool_calls_text`.

| | count of 15 |
|---|---|
| contact-0 form: literal **empty** call | 11 |
| contact-0 form: **unparsed** | 3 |
| contact-0 form: **well-formed non-empty** (dispatched for out-of-vocabulary tool name) | 1 |
| BLEND final form: well-formed non-empty | **12** |
| BLEND final form: still empty | 3 |
| **FORM CHANGED** (empty/unparsed → well-formed non-empty) | **11** |
| form repaired **but still wrong** | **9** |
| converted against its own contact-0 | **3** |

Empty-call rate over the whole population, recomputed: M0 **14 / 104 = 13.46 %** → BLEND
**3 / 104 = 2.88 %**.

### The two channels, separated

| channel | fires on | converts | sample ids |
|---|---|---|---|
| **FORM repair alone** (no gold value in the supply) | 11 of 15 changed form | **1** | `tier4_implicit:003312` |
| **KNOWLEDGE** (supply carried the gold tool's value) | 4 of 15 | **2** | `tier1_direct:004159`, `tier5_needle:000061` |

**The correctness delta attributable to form repair alone is +1 of 11 = 9.1 %. The delta attributable
to gold-bearing supply is +2 of 4 = 50.0 %.** Form repair is the WIDE channel with a low conversion
rate; gold supply is the NARROW channel with a high one. The whole dispatched subgroup moves
**0 → 3 correct against its own contact-0** and **+2 against the M0 arm**, exactly as the
cross-carrier verdict records.

This is also the sharpest available statement of why the empty-call collapse must never be read as
an accuracy claim: the collapse is the FORM channel working on 11 of 15 trajectories, and 9 of those
11 are still wrong.

---

## 7. K3 — the two-sided falsifier, and the projected dispatch-rate change

### 7.1 The projection, from landed answers only

Source: `k3_dispatch_projection`. On this carrier the dispatch predicate fires exactly when
`a2t_label_normalizer` returns `None`: the answer did not parse, carried no calls, or its PRIMARY
tool name is outside the 151-entry vocabulary. A field-role constraint removes the first two causes.
The flown dispatch set decomposes as **11 empty + 3 unparsed + 1 well-formed-but-out-of-vocabulary**,
so K3's own carve-out — *"leaves out-of-vocabulary answers out-of-vocabulary, so dispatch is
preserved"* — preserves **1 of 15** on Audio2Tool.

The projection is bracketed by two landed measurements of the same trajectories rather than by an
assumption:

| arm | what it measures | recovers a label | projected dispatch | rate | change |
|---|---|---|---|---|---|
| **UPPER bound on repair** — the BLEND arm's own final answers (the same core, the same trajectory, producing a well-formed call, with evidence in context) | what a successful form constraint would achieve | **12 of 15** | **3 / 104** | 14.42 % → **2.88 %** | **−11.54 pp, −80.0 % relative** |
| **LOWER bound on repair** — the M0 arm's own answers on the same 15 ids (no evidence, no constraint) | decode variance alone | 2 of 15 | 13 / 104 | 14.42 % → 12.50 % | **−1.92 pp, −13.3 % relative** |

**Projected dispatch-rate change: −1.92 pp to −11.54 pp; −13.3 % to −80.0 % of the reachable set.**
K3's entire purpose is to achieve form repair, so its intended effect sits at the upper-bound arm.
Both arms are material drops. **By the key-construction plan §3's own K3 gate — "if projected
dispatch drops materially, the change is an off-switch in disguise and is rejected like E-C" — K3 is
REFUSED on Audio2Tool.** For scale: the rejected E-C variant projected 72 → 54–67 per 100, a −7 % to
−25 % relative drop. K3's upper-bound arm on this carrier is **−80 %**, worse than the variant the
program already rejected.

The refusal is carrier-specific and the reason is measurable: the plan's K3 premise assumes the
dead-direct set is substantially out-of-vocabulary answers, which the constraint would leave alone.
On Audio2Tool the dead-direct set is **14/15 empty-or-unparsed**, so the constraint eats almost the
whole reachable set. Whether the premise holds on SLURP is **not** established here — this row opened
no SLURP run directory (§9).

### 7.2 The falsifier, pre-registered here for any future K3 gate, TWO-SIDED as §6 of the plan requires

The K1 gate's falsifier was one-sided ("if hybrid ranking does not raise recall@5…") and would have
licensed a flight that loses: recall@5 rose while recall@1 fell 23/500. Every clause below is fixed
before any K3 gate runs, and a K3 gate may not re-parameterise the query construction after seeing
these quantities.

> **K3 GATE — MUST IMPROVE (all four, jointly; failing any one refuses the item):**
>
> **I1.** Gold-facet **recall@1** on the *dead-direct* subgroup rises by **≥ +5.0 pp** under the
> role-constrained query text, measured on the SLURP DEV-1000 unexposed-500 dead-direct subgroup
> (n = 160) — the only landed population with the power to see an effect this size. *Recall@1, not
> recall@5: this is the K1 correction, and it is stated first because it is the quantity K1's
> falsifier omitted.*
>
> **I2.** Median **gold-facet cosine** on the dead-direct subgroup rises by **≥ +0.03** toward the
> label-recovered subgroup's value.
>
> **I3.** **Distinct query vectors per dead-direct trajectory** rises to **≥ 0.90** — the
> label-recovered subgroup's measured value on this carrier is 0.944 and the dead-direct subgroup's
> is 0.333 (§4.1). A role constraint that produces typed-but-identical skeletons on every empty
> answer changes the text and not the key, and would pass I1/I2 by accident on a small sample while
> fixing nothing. *This clause exists because this row found the degeneracy; no earlier gate could
> have named it.*
>
> **I4.** At SUPPLY level, after the τ / top-`m` / `top_l` stages: **newly gold-supplied among
> currently-WRONG dispatched > gold-supply LOST among currently-CORRECT**. Rank-level improvement
> does not substitute; this is the account K1 failed (12 gained against 29–40 lost).
>
> **K3 GATE — MUST NOT DEGRADE (breaching any one refuses the item):**
>
> **D1.** **Projected dispatch count falls by no more than 10 % relative** on the gated population.
> *On Audio2Tool this row already measures −13.3 % on the most conservative arm and −80.0 % on the
> arm that measures actual form repair, so D1 is breached on this carrier before any gate is run,
> and K3 is refused here on that ground alone.*
>
> **D2.** Gold-facet **recall@1 on the label-recovered (retained) subgroup does not fall.** K3
> rewrites contact-0 on EVERY trajectory, not only on the dead-direct ones, so it moves the retained
> subgroup's queries too — and on A2T 60 of the 89 retained are already correct. A change that helps
> the reachable 14 % by disturbing the retained 86 % is a loss the reach × conversion arithmetic will
> not forgive.
>
> **D3.** **No currently-CORRECT retained trajectory moves into dispatch.** The α veto's structural
> guarantee (`retain == direct-label-recovered`) is what keeps evidence away from correct answers;
> a change to contact-0 that breaks a label recovery converts a correct retain into a dispatch, which
> the measured anchors price at a loss.
>
> **D4.** The conversion-weighted product **reach share × within-reach conversion**, projected with
> the measured rank anchors (98.2 % at fused top-1, 69.6 % at rank 2–3, 0 % absent — cited to
> `analysis.k1_hybrid_ranking_gate.ANCHOR_TOP1 / ANCHOR_RANK23 / ANCHOR_ABSENT`), **does not fall**.
> This is the plan §6's stated alternative to two-sidedness, and it is required *in addition*, because
> it is the only clause that prices a reach loss against a conversion gain on one scale.
>
> **Reporting rule.** A negative outcome is the finding and is reported as such. The query
> construction, the role schema and the constraint's prompt text are fixed in the gating module
> before it runs, and none may be re-tried after the answer is seen. Any K3 flight is NEW400-tier or
> larger, read once, per the plan's statistical-honesty clause.

**Verdict carried by this row: K3 as specified is REFUSED for Audio2Tool on D1.** Its status on
SLURP is untouched and unprojected here.

---

## 8. Corrections carried

Per repository discipline, a claim in an existing document that this row's computation contradicts or
bounds is corrected explicitly rather than quietly. None of these changes a headline number in any
landed artifact.

**C1 — `docs/readiness/2026-08-25-cross-carrier-transfer-verdict.md` §6 (correction C1), and the same
wording in §2.3.** The superseded sentence is:

> "On the final answers, **12 of the 15 became well-formed non-empty tool calls** (3 remained
> empty), not 15."

**12 of 15 ENDED well-formed non-empty; only 11 CHANGED form.** The twelfth,
`tier1_direct:004159`, was already a well-formed non-empty tool call at its own contact 0 and
dispatched because its PRIMARY tool name was outside the 151-entry vocabulary, not because it was
malformed. The verdict's own §3.1 already records that composition ("1 parsed to a tool name outside
the 151-entry label vocabulary"), so the two statements were in tension with each other; this row
resolves it in favour of §3.1. The word to strike is "became". Recomputed here through the frozen
parser: `contact0_form_classes` = {empty: 11, unparsed: 3, well-formed-non-empty: 1};
`blend_final_form_classes` = {well-formed-non-empty: 12, empty: 3}; `form_repaired_n` = **11**.

**C2 — `docs/readiness/2026-08-25-cross-carrier-transfer-verdict.md` §3.3, bounded rather than
contradicted.** The sentence is:

> "On A2T the answer is a JSON call list; naming the right tool is necessary but the scorer demands
> the full tool-name multiset, and 26 of the 104 gold call lists name at least two distinct tools."

The 26 is exact and reproduced here. What the passage leaves open is how much of the A2T rank-1
conversion shortfall it explains, and the answer is **n = 1**: the multiset requirement binds on
exactly **1 of the 15 dispatched** and **1 of the 4 gold-bearing** (`tier3_multi_intent:000879`),
which is precisely the rank-1 failure. It cannot carry more weight than one sample. The dispatched
set is **6.67 % multi-tool against the population's 25.00 %**, so the α veto routes multi-tool items
away from the reachable set — the ceiling is real on the population and marginal on the subgroup
evidence can reach.

**C3 — `docs/readiness/2026-08-25-key-construction-agenda-plan.md` §2.2 and §3/K3, premise falsified
for the Audio2Tool carrier.** The sentence is:

> "The role-constrained version leaves out-of-vocabulary answers out-of-vocabulary (so dispatch is
> preserved) while improving the query text that feeds retrieval."

On Audio2Tool that carve-out preserves **1 of 15** dispatched trajectories, because this carrier's
dead-direct set is **11 empty + 3 unparsed + 1 out-of-vocabulary** rather than substantially
out-of-vocabulary. "Dispatch is preserved" is false here by −13.3 % to −80.0 % (§7.1). The plan's
§2.2 evidence for K3 (the swap-recoverable subset's 0.869 retrieval advantage) is a SLURP
measurement and is untouched by this row; the premise is falsified for A2T only. **This section is
that plan's English successor for the A2T carrier; the plan itself is NOT rewritten here.** Whoever
next opens the key-construction agenda should append this outcome in the same additive form its §6
used for the K1 gate outcome, and must carry the two-sided falsifier in §7.2 with it.

**C4 — no contradiction found elsewhere.** The cross-carrier verdict's §3.2 coverage block
(4 gold-bearing of 15, 2 at rank 1, 2 at rank 2, 11 absent, 68 of 104 with no α gate) is reproduced
here **exactly**, on the same fidelity-gated replay. §3.1's reachable-set composition (11 empty,
3 unparsed, 1 out-of-vocabulary) is reproduced exactly. §1.4's flip attribution is consistent with
the per-sample table in `gold_coverage_dispatched.per_sample`.

---

## 9. Not verified, and therefore not used

Listed so their absence is visible rather than inferred.

1. **The K3 projection for SLURP.** This row opened no SLURP run directory and touched no SLURP seal;
   every SLURP number here is quoted from a landed committed document. Whether K3's carve-out
   preserves dispatch on SLURP — where the dead-direct set has a substantial out-of-vocabulary
   partition — is **not** established here and would need its own registered row. The refusal in §7
   is Audio2Tool-only.
2. **Any conversion estimate for the widened-`top_l` cases.** Two of the 11 would reach gold if
   `top_l` were lifted (§3.2). What that would convert to is unknown: the K-WIDEN precedent says a
   changed supply need not produce a flip, and n = 2 could not measure it either way.
3. **A corrected-prior rebuild.** The bracket in §3.4 shows no correction can move any number here,
   which is strictly stronger than a single corrected-prior column would be — but the actual
   `p(tool | domain, category)` snapshot was not built. Building it needs the source rows, a KB
   rebuild and a re-embed; the re-embed alone is an embedding-tool contact this row may not take.
   The defect itself remains open and belongs to whoever owns `rails/knowledge_build_a2t.py`.
4. **Any Audio2Tool variance estimate independent of the n = 104 read's own bootstrap.** Carried
   forward unchanged from the cross-carrier verdict §6; still absent.
5. **Whether the query-key degeneracy reproduces on an unexposed A2T population.** The 104 here are
   EXPOSED and below the campaign's own n ≥ 400 power floor. The degeneracy is a mechanical property
   of "the empty answer is the query" and is very unlikely to be population-specific, but it has been
   measured on one population only.

---

## 10. HARD STOP — what this document does NOT authorize

This is a **diagnosis over landed evidence at zero contacts**. It authorizes:

- **nothing to fly.** No model contact, no tool contact, no embedding contact, no flight, no
  re-flight, no G2 opening. The 79 remaining core contacts on `SAEA-A2T-G1` are untouched and no
  implementer may raise that cell.
- **no knob change.** `configs/policy/kb-policy-v1-dev100.json` is read and hash-checked, never
  written. `rails/` and `core/` are untouched. Every depth in §3 — `k`, `m`, `τ`, `c`, `top_l` — is a
  cell of the locked file, and §3.3 states plainly that none of them is admissible without an owner
  decision. §3.2's finding that lifting `top_l` would reach 2 of 11 is a **measurement, not a
  proposal**.
- **no `rails/` repair.** The prior-dimension defect named in §3.4 is real and is already on record in
  `kb_policy._dimension_scales`'s docstring. Fixing `rails/knowledge_build_a2t.py` is a separate
  authorized change and is not this row's; this row only bounds its effect on this row's numbers.
- **no K3 flight, and no K3 gate either.** §7 REFUSES K3 for Audio2Tool on D1 and pre-registers the
  two-sided falsifier any future gate must use. It does not open that gate, on this carrier or on
  SLURP.
- **no new query-construction item.** The obvious reading of §4.1 — that a retrieval key which is a
  constant should be built from something other than an empty answer — is a design observation, not
  an agenda item. Any such item needs its own registration, its own two-sided falsifier under the
  plan §6 rule, and an owner decision, and this document opens none of them.
- **no generality claim and no superiority claim.** The A2T-G1-104 population is EXPOSED, its
  numbers are secondary readings under the campaign plan §3.3, and its exact-match delta is 0.0 pp.
  Nothing here is a result about Audio2Tool as a task.
- **no test contact.** **FINAL60 stays reserved.** No Stage-3 activity: Stage-3 requires
  `OWNER_GO_AND_PAPER_EXECUTION_CONTRACT` into a `papers/<slug>` repository and this repository
  never accepts it.

`consumed` stays **no**: no seal is broken by this row. Gold was opened scoring-side only, over the
EXPOSED A2T-G1-104 whose seal the landed G1 read had already broken, and never on a runtime path.
