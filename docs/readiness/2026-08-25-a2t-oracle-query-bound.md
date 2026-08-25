# A2T ORACLE-QUERY UPPER BOUND — the locked cell CAN deliver the gold value on all 11,
# but only to a query that already knows the answer; a merely BETTER query delivers ZERO

Date: 2026-08-25. Status: **BOUNDING RUNG — computed, ZERO CONTACTS, all gates passed.**
Row `SAEA-SN-MF-A2T-ORACLE-QUERY-BOUND` (registered `fed9a79c`, **before any computation**).
Module `src/speech_aware_evidence_acquisition/analysis/a2t_oracle_query_bound.py`.
Receipt `docs/checks/speech-aware-evidence-acquisition/2026-08-25-a2t-oracle-query-bound/oracle-query-bound-report.json`
(sha256 `b564362b64bb41df4d9055518bcd0cd88753e2796b3583ed0b95f626a2ece723`).

> **SELF-CORRECTION, landed in the same session as the first version of this document
> (`5020adce`), recorded here rather than hidden.** §2.1 originally asserted, from the builder's
> source alone, that "**no evaluation utterance is a KB entry, by construction and fail-closed**."
> That was an over-claim: the fail-closed check guarantees no evaluation **UNIT** is in the
> construction pool, and says nothing about two different `query_idx` blocks carrying the same
> invocation string. Measured (`utterance_leak_check`), **0 of 104** evaluation units are in the
> KB and **6 of 104** evaluation utterance TEXTS do appear verbatim as a KB content facet — all
> six in `tier8_intent_blending`, and **0 of them among the 15 dispatched trajectories this row
> measures**. No number in this document changes; the sentence is corrected below and the
> measurement now lands in the receipt instead of being inferred from source.

> ## THIS IS AN ORACLE. READ THIS BEFORE ANY NUMBER BELOW.
>
> Every query measured in this document is built from the trajectory's own **GOLD TOOL
> identity** — information no runtime query could legally have. Every count here therefore
> **BOUNDS THE DIRECTION FROM ABOVE**. Nothing here is a proposal, a method, a knob
> recommendation, or an achievable accuracy. The oracle exists for one purpose: to make a
> refutation cheap. It cannot make an endorsement.

**Spend: 0 frozen-core contacts, 0 embedding-tool contacts, 0 tokenizer contacts, 0 audio
seconds, 0.0 GPU hours, 0 new dependencies, 0 vectors constructed from text.** The offline
guard (`analysis.dev100_reviewer_audit.arm_offline_guard`) was armed before the first input was
opened and recorded **0 outbound connection attempts against 0 targets**. The resident np2 A2T
service on port 8090 (pid 38623) was never contacted, probed, reconfigured or stopped. Wall
285.8 s. No knob was changed; `configs/`, `rails/` and `core/` were not written; new code landed
only under `analysis/`.

**The A2T-G1-104 population is EXPOSED.** Every statistic in this document is a **secondary
reading** and must not be used to revise, re-tune or restate the LOCK. That caveat is repeated at
every citation below and is not weakened anywhere.

---

## 0. The answer in one paragraph

**Under the pre-registered oracle, all 11 gold-absent dispatched trajectories become
gold-supplied — 11 of 11 — and the decision rule therefore returns SURVIVES.** The locked cell's
retrieval machinery is not the ceiling: τ = 0.65, `top_l` = 3, `c` = 2 and `k` = `m` = 5 all pass
on every one of the 11 as soon as the query lands in the gold tool's own utterance neighbourhood,
and the result is not a duplicate artifact — with every query that owns an exact twin removed the
count is still **11 of 11**, and a *randomly chosen* same-tool sibling query delivers gold
**1,596 of 1,871 times, 85.30 %** (per trajectory 70.27 %–93.14 %, median 88.17 %). **But the
oracle's condition is nearly circular, and the cheap floor proves it.** The non-oracle,
runtime-legal TIER-PROTOTYPE query (N1) raises the gold facet's cosine from the landed below-τ
band of 0.565332–0.635625 to **0.7209–0.8587** and clears τ on **15 of 15** — and supplies gold to
**0 of 15**, blocked on all 15 by the recall window because the lift is not *discriminative*:
148–150 targets clear τ simultaneously and the gold target lands at rank 11–99. **Clearing τ is
not the lever.** The oracle converts only because it already encodes the tool identity, and the
substitution it makes — a *different* utterance that invokes the same tool, standing in for the
trajectory's own utterance, whose embedding is on disk for none of these 15 (measured, §2.1) — is most generous exactly
where the subgroup is hardest: **8 of the 11 are `tier4_implicit` or `tier7_multiturn`**, tiers
whose utterances are by construction *not* direct tool invocations. The honest reading is
therefore: the direction survives this rung on the registered quantity, and surviving
**authorizes nothing** — this row licenses no flight, no knob change and no contact.

---

## 1. Provenance and gates — nothing below was read until these passed

### 1.1 The fidelity gate (pre-registered as necessary, not decorative)

Recall → rank → admit → fuse → blend, replayed offline through `rails.kb_policy`'s own registered
ranker, registered fuser, `_fused_label_scores`, `_blend_scores` and `_argmax_labels` at the
locked knobs, against the sealed attempt-4 flight (receipt → `fidelity_gate`):

| gate | result |
|---|---|
| replayed supply = flown per-sample supply | **104 / 104**, 0 mismatch ids |
| replayed dispatch decision = flown decision | **104 / 104**, 0 mismatch ids |
| replayed direct-label recovery = flown | **104 / 104**, 0 mismatch ids |
| trajectories with empty recall / empty supply | **0 / 0** |

### 1.2 The landed-reproduction gate (a second stop condition, also pre-registered)

An oracle bound computed on a population this row could not reproduce would not be a bound on the
landed finding. Every cell below was fixed in the registration and every one matches
(`landed_reproduction_gate`):

| quantity | recomputed | landed |
|---|---|---|
| dispatched trajectories | **15** | 15 |
| gold-bearing dispatched | **4** | 4 |
| gold-absent dispatched | **11** | 11 |
| gold facets below τ among the 11 | **9** | 9 |
| τ band minimum | **0.565332** | 0.565332 |
| τ band maximum | **0.635625** | 0.635625 |

### 1.3 The retrieval geometry is pinned to `kb_policy`'s own arithmetic

The vectorised full-KB cosine sweep is not trusted on its own: `kb.multidim_recall` is called for
real on **8** probe samples and must admit the same facet set with the same scores to 1e-9, and
`kb_policy._cosine` is called for real on **72** individual (query, facet) pairs and must
reproduce each vectorised cosine to 1e-9. Both pass (`recall_fidelity`). Ranking, admission and
fusion are `kb_policy`'s own registered functions throughout; **nothing about the pipeline was
reimplemented and no knob was moved.**

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
| locked policy config at flight | `d68afd2cfb6e12d9cbd9d3fbcf0daf3f81f6ed8be9b2a75c4f8ffb234011a919` |

**The locked cell, unchanged throughout:** α 0.45, τ 0.65, `k` = `m` = 5, `c` = 2, `top_l` = 3,
weights (w_cos 0.5, w_prior 0.3, w_agree 0.2). **KB shape:** 12,601 values, 12,601 vectored
content facets, 12,903 content facets carrying a task target, 151 distinct value targets against a
151-entry label vocabulary.

---

## 2. What the oracle IS, and the one substitution it was forced to make

### 2.1 The trajectory's own utterance is not embedded anywhere on disk

The natural oracle query is the embedding of the trajectory's **own invocation utterance**. That
vector does not exist and this row may take no embedding contact, for two reasons that are both
properties of the landed system rather than choices made here:

1. **The KB does not contain it — MEASURED, not inferred** (`utterance_leak_check`, over all
   16,838 pool units and all 104 evaluation samples):

   | | value |
   |---|---|
   | evaluation **UNITS** present in the KB | **0 of 104** — the block decontamination in `rails.knowledge_build_a2t.propose_partition` holds exactly |
   | evaluation **utterance TEXTS** matching a KB content facet verbatim | **6 of 104** |
   | …of those, in the **15 dispatched** trajectories this row measures | **0** |

   The second row is the correction: `propose_partition` reserves every evaluation item's whole
   `query_idx` **BLOCK** (and every block touched by the frozen exposed 400, out of *both* sides),
   which forbids unit overlap but not two different blocks carrying the same invocation string.
   Six `tier8_intent_blending` evaluation utterances do have a verbatim KB twin, so for those six
   the utterance embedding *is* on disk under another facet id. **None of the 15 dispatched
   trajectories is one of them** — the dispatched set is tier1/2/3/4/5/7 and contains no tier8
   sample — so nothing in this row's oracle framing is affected, and the fact is recorded rather
   than glossed.
2. **The flight never embedded utterances.** The landed `query-vectors.jsonl` carries exactly one
   vector per sample and it is the embedding of the model's **contact-0 answer text** — which is
   the whole pathology the gold-absence diagnosis identified.

**The substitution.** The oracle therefore uses, in place of the trajectory's own utterance, the
landed content-facet vector of a **different utterance that invokes the same gold tool**. This is
stated wherever a number is cited because it is the single largest source of generosity in the
bound — see §7.2.

### 2.2 The four oracle queries

| id | query | self-match? | role |
|---|---|---|---|
| **O1 ORACLE-SELF** | the gold-bearing facet the diagnosis measured against the flown key, whole KB retrievable | **YES, cosine 1.0** | leaky ceiling, NOT the bound |
| **O2 ORACLE-LOO** | the same facet, **withheld** from the retrievable pool | no | one fixed, narrow oracle |
| **O3 ORACLE-BEST-LOO** | **every** vectored content facet targeting the gold tool, each withheld in turn; delivers if **any** does | no | **THE PRE-REGISTERED HEADLINE** |
| **O4 ORACLE-CENTROID** | normalized mean of all the gold tool's vectored content facets | not a KB entry | cross-check |

O1's query *is* a KB entry, so it retrieves itself at cosine 1.0 and reaches recall position 1 and
target rank 1 on all 11 — a mechanical identity, reported once and then set aside. **The
self-excluded constructions are O2, O3 and O4, and O3 is the registered bound.**

### 2.3 The identity leak survives self-exclusion as DUPLICATION, and was measured

O3's maximum lands at a best-other-gold cosine of exactly `1.0000000000` on **6 of the 11** — the
withheld facet has an **exact twin** elsewhere in the KB, so withholding the facet does not
withhold the identity. This was not anticipated in the registration, so a **post-registration
robustness stratification** was added and is labelled as such everywhere: the same O3 loop is
re-read with every query whose best other gold-bearing cosine is ≥ 0.99 removed
(`NEAR_DUPLICATE_COSINE`, chosen after the numbers were seen; it can only make the headline weaker
or equal, and it does not replace the registered count).

| | value |
|---|---|
| O3 maxima sitting at an exact twin (≥ 0.99) | **6 of 11** |
| O3 queries owning a twin, pooled | **34 of 1,871 (1.82 %)** |
| **twin-free gold-supplied, of the 11** | **11 of 11** |
| twin-free pooled delivery | **1,562 / 1,837 = 85.03 %** |

**The headline does not depend on duplication.** The duplicate structure is real and worth a
KB-hygiene note, but it moves nothing here.

---

## 3. The per-trajectory table

All 15 dispatched trajectories; `*` marks the 11 **gold-absent** ones this row is about. `cos` is
the best gold-bearing content-facet cosine, `pos` its position in `multidim_recall`'s own recall
ordering, `adm` whether a gold-bearing facet entered the admitted top-`m` window, `trk` the gold
TARGET's rank among τ-passing targets (`top_l` = 3 gates this), `sup` whether the gold VALUE was
supplied. **Exposed-tier secondary reading.**

| | sample id | gold tool | KB facets | flown cos | flown pos | O2 cos | O2 τ | O2 pos | O2 adm | O2 trk | O2 sup | O3 cos | O3 sup | O3 delivery rate | O4 sup |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `*` | `tier1_direct:000167` | `setColor` | 165 | 0.5873 | 178 | 0.6883 | yes | 14 | no | 8 | **no** | 0.9430 | **yes** | 130/165 = 78.8 % | yes |
| `*` | `tier1_direct:001631` | `setWaterValve` | 175 | 0.5653 | 430 | 0.9592 | yes | 1 | yes | 1 | **yes** | 1.0000 | **yes** | 163/175 = 93.1 % | yes |
| | `tier1_direct:004159` | `getLockState` | 202 | 0.9121 | 1 | 0.9252 | yes | 1 | yes | 1 | yes | 1.0000 | yes | 196/202 = 97.0 % | yes |
| `*` | `tier2_parametric:004826` | `setGroupLightState` | 185 | 0.8548 | 10 | 0.9736 | yes | 1 | yes | 1 | **yes** | 1.0000 | **yes** | 130/185 = 70.3 % | yes |
| | `tier3_multi_intent:000879` | `getCameraEvent` | 193 | 0.8565 | 1 | 0.8585 | yes | 1 | yes | 1 | yes | 0.9329 | yes | 165/193 = 85.5 % | yes |
| `*` | `tier4_implicit:000655` | `setLockState` | 164 | 0.5942 | 130 | 0.6993 | yes | 4 | yes | 2 | **yes** | 1.0000 | **yes** | 131/164 = 79.9 % | yes |
| `*` | `tier4_implicit:000900` | `setGarageDoor` | 150 | 0.5828 | 216 | 0.7702 | yes | 4 | yes | 3 | **yes** | 0.9769 | **yes** | 139/150 = 92.7 % | yes |
| `*` | `tier4_implicit:001148` | `castContent` | 183 | 0.6054 | 83 | 0.7851 | yes | 1 | yes | 1 | **yes** | 1.0000 | **yes** | 149/183 = 81.4 % | yes |
| `*` | `tier4_implicit:001389` | `setApplianceMode` | 144 | 0.5842 | 203 | 0.6566 | yes | 23 | no | 13 | **no** | 0.9638 | **yes** | 131/144 = 91.0 % | yes |
| `*` | `tier4_implicit:001409` | `setApplianceMode` | 144 | 0.5842 | 203 | 0.6566 | yes | 23 | no | 13 | **no** | 0.9638 | **yes** | 131/144 = 91.0 % | yes |
| | `tier4_implicit:001513` | `setPowerState` | 153 | 0.7088 | 2 | 0.6900 | yes | 35 | no | 19 | no | 0.9501 | yes | 107/153 = 69.9 % | yes |
| `*` | `tier4_implicit:003312` | `startWorkout` | 186 | 0.5712 | 339 | 0.8855 | yes | 1 | yes | 1 | **yes** | 1.0000 | **yes** | 166/186 = 89.2 % | yes |
| | `tier5_needle:000061` | `setBrightness` | 153 | 0.8691 | 2 | 0.9064 | yes | 1 | yes | 1 | yes | 0.9718 | yes | 118/153 = 77.1 % | yes |
| `*` | `tier7_multiturn:000214` | `setTargetTemperature` | 189 | 0.6356 | 16 | 0.5847 | **no** | 194 | no | — | **no** | 0.9408 | **yes** | 162/189 = 85.7 % | yes |
| `*` | `tier7_multiturn:001516` | `activateRoutine` | 186 | 0.6768 | 8 | 0.6183 | **no** | 24 | no | — | **no** | 1.0000 | **yes** | 164/186 = 88.0 % | yes |

Three properties of this table are worth naming.

1. **`tier4_implicit:001389` and `:001409` are numerically identical on every flown column.** That
   is a direct consequence of the landed constant-key finding: they carry the *same* flown query
   vector (the empty tool call's embedding) and the *same* gold tool, so their whole flown geometry
   coincides. It is not a copy-paste error.
2. **O2's anchor is selected adversarially and its 6/11 must be read that way.** O2's query is the
   gold-tool facet closest to the *flown* key — that is, closest to the embedding of an empty tool
   call. On `tier7_multiturn:000214` and `:001516` that anchor's own cosine to the rest of its
   tool's manifold (0.5847, 0.6183) is *lower than the flown key's* gold cosine (0.6356, 0.6768):
   the anchor is an outlier inside its own tool. O2 is a narrow, unfavourably-chosen oracle, not a
   stricter version of O3.
3. **The O3 delivery rate is the "typical sibling" statistic, and it is high everywhere.** The
   headline is a supremum, so the rate column is what stops it from being a cherry-pick: a
   *randomly chosen* same-tool sibling query delivers gold on 70.3 %–93.1 % of attempts.

---

## 4. The headline count, and the self-excluded bound

| construction | self-excluded? | gold-supplied of the 11 | of all 15 dispatched |
|---|---|---|---|
| as flown (the landed baseline) | — | **0** | 4 |
| **O1 ORACLE-SELF** (leaky, cosine 1.0) | no | 11 | 15 |
| **O2 ORACLE-LOO** (one narrow anchor) | yes | **6** | 9 |
| **O3 ORACLE-BEST-LOO** — **PRE-REGISTERED HEADLINE** | yes | **11** | 15 |
| **O3 TWIN-FREE** (post-registration robustness) | yes, plus duplicates removed | **11** | — |
| **O4 ORACLE-CENTROID** | not a KB entry | 11 | 15 |

> ### THE HEADLINE: **of the 11 gold-absent trajectories, 11 become gold-supplied under the ORACLE query.**
> ### THE SELF-MATCH-EXCLUDED BOUND IS THE SAME NUMBER: **11 of 11**, and it holds with near-duplicate queries removed as well (**11 of 11**, pooled twin-free delivery 85.03 %).

Best gold-bearing facet cosine, **over the same 11 trajectories** in every row, for scale against
the landed 0.565332–0.635625 below-τ band:

| | min | median | max | clears τ = 0.65 |
|---|---|---|---|---|
| as flown (landed) | 0.5653 | 0.5873 | 0.8548 | **2 of 11** |
| **O2** | 0.5847 | 0.6993 | 0.9736 | **9 of 11** |
| **O3** | 0.9408 | 1.0000 | 1.0000 | **11 of 11** |
| N1 tier prototype (**non-oracle**) | 0.7209 | 0.7898 | 0.8251 | **11 of 11** |

(Over all 15 dispatched trajectories the N1 band is 0.7209 / 0.7898 / 0.8587 and clears τ on
15 of 15; §6.1 reports that population.)

---

## 5. Which stage binds — and under the oracle, none of them does

`binding_stage` names the **first** stage that keeps the gold value out, in pipeline order: KB
coverage (**data**), the τ percept gate (**data measured against a knob** — the bar is a knob of
the locked cell, the cosine is a property of the data), the recall/ranker window `k` = `m`
(**knob**), and the `top_l` target budget (**knob**).

| construction | supplied | τ gate | recall depth `k` | `top_l` |
|---|---|---|---|---|
| **O3 (headline)** | **11** | 0 | 0 | 0 |
| O2 (narrow anchor) | 6 | 2 | 3 | 0 |
| **N1 tier prototype (non-oracle)** | **0 of 15** | 0 | **15** | 0 |

**`c` = 2 cannot bind at all, and that is structural rather than empirical.** On this carrier each
content facet is associated with exactly one value, so once the gold TARGET is inside `top_l`, at
least one of its values is always selected whatever `c` is. The classification says so explicitly
rather than leaving `c` as a silent possibility.

**Under the pre-registered oracle no stage binds on any of the 11.** τ = 0.65, `k` = `m` = 5,
`top_l` = 3 and `c` = 2 are all *sufficient* for this population once the query is right. That is
the load-bearing negative of this row and it points the same way the gold-absence diagnosis did:
**the ceiling is the query, not the cell.**

**Under the realistic floor the binding stage is the recall window, on 15 of 15** — and it binds
even though τ is cleared on 15 of 15. §6.1 is where that matters.

---

## 6. The lower constructions

### 6.1 N1 — the TIER-PROTOTYPE floor (non-oracle, runtime-legal), and the sharpest result in this document

N1 uses **no gold whatsoever**: the query is the L2-normalized mean of the vectored content facets
of the KB units in the trajectory's own tier, and the tier is determined by the sample id alone.
It is constructible at runtime today.

| | value |
|---|---|
| gold facet cosine (min / median / max) | **0.7209 / 0.7898 / 0.8587** |
| clears τ = 0.65 | **15 of 15** |
| gold facet enters the admitted top-`m` window | **0 of 15** |
| τ-passing targets competing | **148–150** |
| gold TARGET rank among them | **11–99** |
| **gold supplied** | **0 of 15** |
| binding stage | recall depth `k`, **15 of 15** |

Its supplied targets are constant per tier — `getAirQuality` / `getEnergyUsage` /
`getThermostatState` for every `tier1_direct` and `tier7_multiturn` trajectory,
`getAirQuality` / `getCameraEvent` / `setFanMode` for every `tier4_implicit` one. **It is the
constant-key pathology again, at a higher cosine.**

> **THE LESSON, STATED AS A NEGATIVE BECAUSE THAT IS WHAT IT IS.** A query that lifts the gold
> facet's cosine from 0.5653–0.6356 to 0.7209–0.8587 — clearing τ on every single trajectory —
> converts **nothing**, because the same lift raises 148–150 competing targets past τ at the same
> time. **The τ gate is a threshold on similarity, and similarity is not the scarce resource;
> DISCRIMINATION is.** Any future item that argues from "the gold cosine is only 0.014–0.085 below
> τ" to "a small improvement converts" is refuted by this row, at zero cost, on this carrier.

### 6.2 N2 — the mixing sensitivity (a sensitivity, explicitly NOT a bound)

Query at mixing weight λ is the normalized mixture of the flown key's direction and the O2 oracle
direction, with the oracle anchor facet withheld throughout, on the fixed grid
λ ∈ {0.0, 0.1, …, 1.0}.

| | value |
|---|---|
| λ = 0 reproduces the as-flown supply | **13 of 15** |
| the 2 that do not | `tier4_implicit:001513`, `tier5_needle:000061` — **exactly** the two whose withheld anchor supported the flown supply |
| gold-absent trajectories reaching gold at some λ ≤ 1 | **6 of 11** (λ = 1 is O2 by construction) |
| smallest λ that supplies gold (min / median / max) | **0.3 / 0.5 / 0.8** |

The λ = 0 cell is a self-check and it behaves exactly as predicted, which is the reason to trust
the rest of the ladder. The reading: where the O2 direction converts at all, **roughly half the
distance** from the degenerate key to a same-tool utterance vector is needed. This is a
sensitivity on one narrow oracle direction and generalises to nothing.

---

## 7. The decision-rule outcome, in the row's own words

The bands were fixed in the registration (`fed9a79c`) before any number was seen, keyed on the
self-excluded O3 count over the 11 gold-absent trajectories: **≤ 1 refutes; ≥ 8 survives; 2–7 is
inconclusive.**

### 7.1 The registered outcome

> **SURVIVES.** 11 of 11 gold-absent trajectories become gold-supplied under the oracle query.
> **The query-improvement direction is NOT refuted by this rung.**
>
> **SURVIVING AUTHORIZES NOTHING BY ITSELF.** It is an upper bound and nothing else. It licenses
> no flight, no knob change, no G2 opening, no contact and no Stage-3 activity. Two standing
> obstacles are untouched by it:
>
> * **The K3 trap.** Any fix that improves the query by making the **ANSWER** better recovers a
>   direct label, and the α veto then suppresses dispatch: the landed gold-absence diagnosis
>   projects 15/104 → 3/104, **−11.54 pp, −80.0 % relative**, worse than the already-rejected E-C
>   variant. A bound on what a better query could retrieve says nothing about whether the
>   trajectories would still be dispatched to retrieve for.
> * **Conversion.** Gold-bearing supply is not correctness. On the landed evidence the
>   dispatched-with-gold conversion rate is **2 of 4**; that is n = 4 and this row does not
>   multiply it by 11.

For transparency the same bands read against two other constructions — **these are secondary
readings and neither revises the registered outcome**: O2 (the narrow, adversarially-anchored
oracle) gives **6 of 11 → INCONCLUSIVE**; the twin-free O3 stratification gives **11 of 11 →
SURVIVES**.

### 7.2 The honest limit of the bound, stated plainly

The oracle's condition is close to circular and the reader should hold both facts at once:

1. The oracle query is *an utterance that invokes the gold tool*. Supplying it is very nearly
   supplying the answer. What the bound proves is a statement about the **cell**: τ, `k`, `m`,
   `c` and `top_l` are not the obstruction. It is not a statement about any reachable query.
2. **The substitution is most generous exactly where the subgroup is hardest.** Of the 11,
   **6 are `tier4_implicit`, 2 are `tier7_multiturn`**, 2 are `tier1_direct` and 1 is
   `tier2_parametric` — i.e. **8 of 11** come from tiers whose utterances are, by the corpus's own
   construction, *not* direct tool invocations. Replacing such an utterance with a same-tool
   exemplar is precisely where the replacement flatters the query most.
3. **N1 shows the gap between "better" and "sufficient" is enormous.** The only runtime-legal
   query this row could build converts 0 of 15 while clearing τ on 15 of 15.

**The direction that survives is therefore narrow: a query that IDENTIFIES the tool converts; a
query that is merely closer to the tool's neighbourhood does not.** Whether any legal contact-0
construction can produce the former is exactly what this row cannot answer (§9).

---

## 8. Relationship to the landed documents — one clarification, no contradictions

No number in this row contradicts a landed document. One landed framing invites a reading this row
refutes, and it is corrected here as an English successor rather than by rewriting anything.

**(C1) The τ-distance framing must not be read as "a small nudge converts."**
`docs/readiness/2026-08-25-query-key-degeneracy-cross-carrier.md` reports, correctly, that the
nine below-τ A2T gold facets sit in the band 0.565332–0.635625 with "gap to tau min 0.014375 /
median 0.065795 / max 0.084668, all nine within 0.10". Every one of those figures is reproduced by
this row. The **sentence is right and the natural inference from it is wrong**: N1 (§6.1) lifts
those same gold cosines to 0.7209–0.8587, clears τ on 15 of 15, and supplies gold to 0 of 15. A
gap-to-τ of 0.08 is not a measure of how much improvement is needed, because closing it for the
gold facet closes it for 148–150 competitors simultaneously. Readers of that section should carry
this clarification with it.

**(C2) A KB-hygiene note, not a defect claim.** 6 of the 11 gold tools carry at least one pair of
content facets at cosine 1.0000000000 (34 of 1,871 O3 queries own such a twin, 1.82 %). This row
measured it only to prove the headline does not rest on it (§2.3). Whether the A2T KB build should
deduplicate is a question for a KB-construction item and is **not decided here**.

**(D1) The degeneracy row's clause (4) still stands and is not overturned.** That row registered
"NO COUNTERFACTUAL IS MEASURED … whether a differently-constructed query would clear tau cannot be
established without an embedding contact". That remains exactly true for a query built from **new
text**, which is what that clause was about. This row measures a different and narrower class: a
counterfactual whose query vector was **already landed on disk**, so no text was embedded and no
contact was taken. The two statements are compatible and neither is weakened.

---

## 9. Declared unverified rather than estimated

1. **Whether the trajectory's OWN utterance embedding would land inside its gold tool's
   neighbourhood.** For all 15 dispatched trajectories that vector is not on disk — measured, not
   inferred (§2.1) — and producing it is an embedding contact this row may not take. This is the
   single quantity that would turn the oracle into a projection, and it is **not** estimated here.
   (The six `tier8_intent_blending` samples whose utterance text *does* have a verbatim KB twin
   would permit the question to be asked of them at zero contacts; none of them is dispatched, so
   none is in this row's population, and no such measurement is made or estimated here.)
2. **Whether any legal contact-0 construction can produce a tool-identifying query.** That needs a
   model contact.
3. **The correctness consequence.** Gold-bearing supply is not a correct answer; the landed
   conversion evidence is 2 of 4 and this row does not extrapolate it.
4. **Transfer to SLURP.** No SLURP run directory was opened and no SLURP number was recomputed
   here.
5. **Dispatch preservation under any query fix.** Only projected, in the landed gold-absence row,
   from landed answers; nothing new is measured here.
6. **Whether the KB duplicate structure affects any other landed statistic.** Measured only inside
   this row's own O3 loop.

---

## HARD STOP

**BOUNDING RUNG ONLY.** This document changes no knob, writes nothing under `configs/`, `rails/`
or `core/`, opens no unexposed tier, and authorizes **no flight, no re-flight, no G2 opening, no
test contact, no `rails/` edit, no Stage-3 activity and no contact of any kind**. The A2T-G1-104
population is EXPOSED and every statistic here is a secondary reading that must not be used to
revise, re-tune or restate the LOCK. A ceiling on a direction is never a measurement of a method,
and an oracle that uses the gold tool identity is never evidence that a runtime system could do
the same thing. The next decision on the query-construction agenda belongs to the owner.
