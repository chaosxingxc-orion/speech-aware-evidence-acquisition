# THE PRIOR-SCORE SEMANTICS REPAIR — a ratio that was never a probability, in both builders
# (2026-08-25)

**Exposure row:** `SAEA-SN-MF-PRIOR-SCORE-SEMANTICS-REPAIR`, registered `1efe5c9c` BEFORE any
computation.
**Repair commit:** `b3a420d7`. **Pre-repair commit:** `3f131afd`.
**Modules:** repaired `src/speech_aware_evidence_acquisition/rails/knowledge_build.py` and
`.../rails/knowledge_build_a2t.py`; range contract in `.../rails/knowledge.py`; measurement in
`.../analysis/prior_score_semantics_repair.py`.
**Receipt:**
`docs/checks/speech-aware-evidence-acquisition/2026-08-25-prior-score-semantics-repair/repair-report.json`,
sha256 `041de6c0868ca4324545d2a423c098d5d96218ca9443fff2ca527aa053895c05`.
**Spend exactly as registered:** 0 frozen-core contacts, 0 embedding-tool contacts, 0 tokenizer
contacts, 0 HTTP or socket requests, 0 audio seconds, 0.0 GPU hours, 0 new dependencies.
`analysis.dev100_reviewer_audit.arm_offline_guard()` was armed before the first input was opened and
recorded **0 outbound connection attempts against zero targets**. The resident np2 llama-server
(pid 38623, port 8090) was not contacted, probed, reconfigured or stopped. Wall 277.9 s.
**No knob changed.** `configs/policy/kb-policy-v1-dev100.json` is byte-identical
(`d68afd2c…a919`, re-hashed in the receipt) and `rails/kb_policy.py` was not touched.

---

## 0. What this document is

A **correctness repair**. It fixes a computation; it does not tune anything, and it revises no
landed number. Everything below is measured by the module named above and reproduced in its
receipt.

> **NO PINNED ARTIFACT MOVED.** The pinned Audio2Tool snapshot
> `ec2f9ec454d3f16957ac08e4d7686a6f3941f22c600ff2b1b2b97ff43baf9fb2` and the pinned SLURP snapshot
> `e27b274516604ffc0e21319758aea99dc027f459d480a32a74a715b023a51b57` were re-hashed from disk and
> are unchanged. They remain the record of what actually flew. A corrected Audio2Tool snapshot was
> built as a **new artifact at a new path** (§5); nothing consumes it.

---

## 1. THE DEFECT, VERIFIED AT SOURCE — one expression shape, on both carriers

Both builders divided two counts taken over **different populations**. Neither restricted the
numerator to the conditioning event, so neither ratio was a conditional probability and neither had
any reason to be ≤ 1.

**Audio2Tool**, `rails/knowledge_build_a2t.py:1085-1087` at `3f131afd`:

```python
category_total = len(rows_by_category_full.get((row.domain, row.category), ()))
tool_total     = len(rows_by_tool_full.get(row.tool_name, ()))
prior_score    = tool_total / category_total if category_total else 0.0
```

`rows_by_tool_full` is accumulated at line 853 over the **whole** construction pool;
`rows_by_category_full` at line 854 over **one** `(domain, category)`. The numerator's row set is
not a subset of the denominator's.

**SLURP**, `rails/knowledge_build.py:696-698` at `3f131afd`:

```python
scenario_total           = len(rows_by_scenario_full.get(row.scenario, ()))
intent_total_in_scenario = len(rows_by_intent_full.get(row.intent, ()))
prior_score              = intent_total_in_scenario / scenario_total if scenario_total else 0.0
```

`rows_by_intent_full` is accumulated at line 504 over the **whole** row set — **not** over the
scenario. It is the identical expression shape. The local's **name asserted a restriction the code
never performed**.

**How the pre-repair source is evidenced here.** Those lines are no longer in the tree, and reading
them back would need a `git` subprocess whose network surface the in-process offline guard cannot
cover. So the module re-hashes the **landed** Stage-2A synthesis receipt — which machine-checked
each of those six lines against the tree at `3f131afd` and recorded `present: true` for each — and
reads its recorded result. All six are confirmed. The live tree is then checked directly: **9**
repaired expressions present, **3** defective expressions absent, fail-closed.

---

## 2. THE REPAIR

Each numerator is now restricted to its conditioning event, via a joint counter accumulated beside
the existing per-key ones (same loop, same style):

* **Audio2Tool** — `p(tool | domain, category) = count(rows with this tool AND this (domain,
  category)) / count(rows in this (domain, category))`.
* **SLURP** — `p(intent | scenario) = count(rows with this intent AND this scenario) /
  count(rows in this scenario)`.

The A2T local `tool_total` is renamed `tool_total_in_category`; the SLURP local
`intent_total_in_scenario` keeps its name because the name is now **true**.

---

## 3. THE SLURP REPAIR IS AN EXACT IDENTITY — argued, then measured

**The argument.** `slurp_kb_rows` builds `intent = f"{entry.scenario}_{entry.action}"`
(`knowledge_build.py`, the `KbRow` construction). An intent therefore **determines** its scenario:
every row carrying this intent necessarily carries this scenario. The restricted row set
`{r : r.intent = i ∧ r.scenario = s}` is then literally **the same SET** as the unrestricted
`{r : r.intent = i}` — not merely the same cardinality. The repair is an identity transform.

**The measurement, over the real TRAIN construction rows** (not a fixture):

| quantity | measured |
|---|---|
| TRAIN rows walked | **11,514** |
| intents | **60** (matching the pinned SLURP snapshot's 60 prior facets) |
| scenarios | **18** |
| rows violating `intent = f"{scenario}_{action}"` | **0** |
| intents whose RESTRICTED row set differs from the UNRESTRICTED one | **0 of 60** |
| rows whose prior changed (exact float comparison, pre vs post) | **0 of 11,514** |
| post-repair prior supremum / values above 1 | **1.0** / **0** |

**No intent violated the nesting.** Had even one appeared under two scenarios, the SLURP prior
would have been wrong in flight exactly as the Audio2Tool one was; the module raises in that case
rather than reporting it in passing.

**A second, independent place the nesting turned out to be structural**, found while writing the
tests rather than assumed: the SLURP builder emits **one label facet per intent**, parented by
`scenario → action`. An intent appearing under two scenarios produces a duplicate `facet_id` and
the snapshot refuses to validate — *before any prior is read*. So the nesting is not merely what
made the old prior accidentally correct; the whole SLURP KB shape depends on it. The corrected
prior expression does **not** depend on it: it conditions whether or not the labels nest. That is
the point of the repair — SLURP's old code was right by accident of the label vocabulary, never by
construction, and would have broken exactly as A2T's did under a non-nesting scheme.

---

## 4. THE AUDIO2TOOL CHANGE, QUANTIFIED

### 4.1 The fidelity gate came first

The construction pool and the selection were reconstructed from the same manifests, the same
partition seed (`20260807`) and the same build seed (`20260825`) the landed build script used
(pool 16,843 units, 16,838 usable; construction **12,601** units; 400 proposed eval sample ids).
Then the **pre-repair** ratio was recomputed and compared to the pinned snapshot's own
`prior_score` on every value:

**12,601 of 12,601 values reproduced exactly, 0 mismatches.** Only then was a post-repair number
read.

### 4.2 Before and after, over all 12,601 values

| statistic | pre-repair (as flown) | post-repair (corrected) |
|---|---|---|
| **max (supremum)** | **4.1** | **1.0** |
| values above 1 | **193** | **0** |
| values exactly 1 | 0 | 144 |
| min | 0.021978 | 0.003448 |
| p05 | 0.126549 | 0.019469 |
| p25 | 0.177033 | 0.142584 |
| median | 0.241026 | 0.186508 |
| p75 | 0.295694 | 0.249612 |
| p95 | 0.528205 | 0.343689 |
| mean | 0.270370 | 0.193762 |
| distinct values | 182 | 145 |

**Values that moved: 12,237 of 12,601 (97.11 %); unchanged: 364.** Every move is a **decrease**
(max delta −0.010309, median −0.032564, mean −0.078886, min −4.05), which is what conditioning must
do: the numerator can only shrink when it is restricted to the denominator's cell. The two largest
falls are `value:tier1_direct:001931` and `value:tier5_needle:001922`, both **4.1 → 0.05**.

**The defining property now holds.** Over the tools present in one `(domain, category)` cell the
post-repair priors sum to exactly 1, on all **30** cells, worst absolute error **0.0**. The
pre-repair ratios could not — that is the arithmetic form of the defect.

### 4.3 The supply on the 104 is unchanged — measured, not inherited

The landed gold-absence diagnosis bracketed the prior's influence at the supremum (all prior-mass
scores set to 1.0) and the infimum (dimension removed), finding the supply identical to as-flown
under both. **That bracket has a gap, and this row closed it rather than quoting past it.** Its
`_rescale_prior` rewrote scores *after* recall, so it kept the as-flown recalled set and could not
see the one thing a corrected prior really changes: **which** facets each prior-mass dimension
recalls, since `multidim_recall` truncates each dimension to its own top `k` **by score**.

Measured here: the corrected prior-mass recall is **a different facet set** — 8 of the 10 recalled
facets change (`controlPlayback`, `getLockState`, `setLockState`, `setVolume` out;
`getEnergyUsage`, `setClimate`, `setHapticStrength`, `setMirrorAngle` in), with the recalled
supremum falling **4.1 → 1.0** and values above 1 falling **10 → 0**. So the gap was real.

The prior-mass recall was therefore **redone** through `kb_policy.multidim_recall` on a snapshot
carrying the corrected values, and the supply replayed through `kb_policy`'s own ranker, admission
gate and fuser at the locked cell, with an anchor asserting that recomposing with the *as-flown*
prior recall reproduces the as-flown recall exactly (it did, on 104/104). Results:

| quantity | measured |
|---|---|
| landed fidelity gate (supply / dispatch / direct-label recovery) | **104 / 104 / 104**, 0 mismatch ids |
| as-flown replay reproduces the flight on dispatched | **true** |
| prior-mass facets inside the locked top-`m` = 5 window under the CORRECTED prior | **0**, on 104 of 104 |
| **supply changed vs as-flown** | **0 of 104** |

**No landed Audio2Tool ranking, supply, dispatch or correctness number is revised by this repair.**

---

## 5. THE REBUILT SNAPSHOT — a new artifact, never a displacement

The rebuilt snapshot was compared **field by field** against the pinned one:

| comparison | result |
|---|---|
| facet ids present on only one side | **0** |
| facets whose fields changed (representation, parents, sources) | **0** |
| value ids present on only one side | **0** |
| snapshot header fields that changed | **0** |
| value fields that changed | `prior_score` on **12,237** values, and nothing else |

**No facet representation and no value content string changed**, so **no embedding pass is
implied**: every landed vector remains the vector of the text it was computed from, and
`prior_score` is a numeric `ValueBundle` field that is never embedded. Had any text moved, the
module raises with the exact inventory instead of taking an embedding contact.

The rebuilt snapshot was written to a **new** path,
`knowledge/audio2tool/saea-kb-a2t-toolshaped-v1/size-full/snapshot-prior-repaired.json`
(`snapshot_sha256` **`ad4e0bbff31e46a66a9281fbc1deb893546c53d68debfe4b479c4658435c8e76`**, file
sha256 `4af3d41f17d4beca4e3c7fab2ede7e6cb56809b09edc9a6630f71547c6dc9b01`). The module refuses
outright if that path resolves to the pinned one. **Nothing consumes it** except this row's own
replay, and it is **not** promoted to any pin. Promoting a corrected snapshot into a flying
configuration is a separate, separately-registered decision this row does not make.

---

## 6. THE RANGE CONTRACT — and the design question it had to answer

`ValueBundle.prior_score` had **no declared range**. That absence is why two independent builders
wrote the same wrong ratio and nothing refused it for many rounds. The range is now declared —
`PRIOR_SCORE_MIN = 0.0`, `PRIOR_SCORE_MAX = 1.0` — as a contract, not a knob: not configurable, not
widened per carrier, not softened by a tolerance.

### 6.1 The hard part

A naive fail-closed check at load time would make the **already-pinned** Audio2Tool snapshot
unloadable. That snapshot reaches 4.1 on 193 of its 12,601 values, and **every landed replay reads
it**. Refusing it would break the audit of what actually flew — a worse failure than the defect
being audited. So the contract has to be **directional**: refuse on the way out, accept and label on
the way in.

### 6.2 The design

One pure classifier, two gates at the two ends of the data flow:

* **`prior_score_range_violation(x) -> float | None`** — pure, total, never raises, never mutates.
  Both sides are written in terms of it, so they cannot drift apart. Exposed as
  `ValueBundle.prior_score_range_violation()` and `KnowledgeSnapshot.prior_score_range_violations()`.
* **CONSTRUCTION, fail-closed:** `assert_prior_scores_are_probabilities(values, builder=…)` raises
  `RailsError` naming the offending value ids. It is called **(a)** by *both* builders immediately
  after `_build_facets_and_values` — the earliest point the values exist — and **(b)** by
  `KnowledgeSnapshot.frozen_json()`, which is the **only** point at which a snapshot becomes
  durable, content-addressed bytes: both build scripts write exactly what it returns, and *nothing*
  on the load path calls it.
* **LOAD, accept and record:** `KnowledgeSnapshot.from_frozen_json()` never raises on range.
  Violations are recorded on the loaded instance and are readable at
  `snapshot.historical_prior_score_range_violations`, and a `RuntimeWarning` naming the snapshot,
  its hash, the count and the supremum is emitted so acceptance is never silent. The record is a
  non-field instance attribute set with `object.__setattr__` — exactly the established `_validated`
  pattern — so it never enters `__eq__`/`__hash__`/`as_json`/`content_hash` and cannot perturb
  identity.

**The boundary in one sentence: bytes carrying a violation may come IN and be labelled; none may go
OUT.** A snapshot loaded from a historical document therefore cannot be re-frozen.

### 6.3 Verified on the real artifact, not only on a fixture

Loading the pinned Audio2Tool snapshot: succeeds; records **193** violations with supremum **4.1**
over 12,601 values; the recorded set equals the set recomputed from the loaded instance; and
`frozen_json()` on it refuses with

> `RailsError: KnowledgeSnapshot.frozen_json[a2t-kb-toolshaped-9eb5f4bf186a0285]: prior_score must
> be a probability in [0.0, 1.0] — 193 of 12601 values are outside it (…)`

Both sides are covered by unit tests (`tests/unit/test_prior_score_contract.py`), including that an
in-range load records nothing and does not warn, and that recording does not perturb snapshot
identity.

### 6.4 What was rejected, and why

* **A — enforce inside `ValueBundle.validate()`** (the obvious "fail-closed dataclass invariant").
  Rejected: `validate()` is on **both** paths. `as_json()` calls it, `content_hash()` calls
  `as_json()`, and `from_frozen_json()` calls `content_hash()` to verify the claimed hash. Enforcing
  there makes the pinned snapshot not merely unloadable but **un-hashable**. It would also break
  `tests/unit/test_kb_policy_v1.py`, which deliberately constructs an A2T-shaped snapshot with
  masses up to 4.1 to prove the landed ranker repair — reproducing the historical pathology in
  memory must stay possible.
* **B — thread a `strict=`/policy flag through `validate()`, `as_json()` and `content_hash()`.**
  Rejected: `content_hash()` is called from roughly twenty sites across `kb_policy`, `runner`,
  `pslu_flight`, the driver and four analysis modules, essentially all of them on **loaded**
  snapshots. Every one would need the flag, and any site that forgot it would fail in a way that
  looks like a hash mismatch. It also still needs instance-carried state for `as_json()` to remain
  callable — so it buys nothing over the instance record while adding a parameter to the
  most-called method in the rails layer.
* **C — refuse at load, and migrate the pin to a corrected rebuild.** Rejected: this is fixing the
  evidence. It displaces `ec2f9ec4…9fb2`, invalidates every landed receipt that pins it and
  destroys the record of what flew. (The corrected rebuild exists — §5 — precisely as a *separate*
  artifact.)
* **D — clamp at load (`min(1.0, x)`).** Rejected: silently falsifies historical evidence. A replay
  would stop reproducing the flight, and the document hash check would have to be relaxed to
  accommodate the clamp. Recording is honest; clamping is not.
* **E — a range assertion in a check script under `scripts/`.** Rejected: a gate that runs on demand
  cannot stop a builder that runs elsewhere, and the defect survived many rounds *precisely* because
  nothing in the construction path refused it. The gate belongs where the bytes are made.

---

## 7. THE LANDED RANKER REPAIR AFTER THIS — RECOMMENDATION: **KEEP IT**

`kb_policy._dimension_scales` divides every dimension by `max(1.0, sup_d)` (landed `1341c2db`).
With genuine probabilities the prior dimensions' sup is ≤ 1 and cosine's is ≤ 1 by theorem, so the
divisor is 1 everywhere and the transform is an **identity** — measured here: the corrected A2T
prior-mass recall supremum is exactly **1.0** and SLURP's is exactly **1.0**.

**It should stay. This row does not remove it and recommends against removing it.** Four reasons,
in decreasing order of force:

1. **It is load-bearing for historical replay, not merely insurance.** The range contract keeps
   historical snapshots *loadable by design*, and the pinned A2T snapshot with its 4.1 is exactly
   what every landed A2T replay ranks. Remove the divisor and replaying the pinned snapshot gives
   the pre-repair behaviour back — prior-mass facets monopolising the top-`m` window, dispatch
   falling from 15 to 0. Every landed A2T replay and every future audit of attempt 4 would stop
   reproducing the flight.
2. **The contract's scope is narrower than the ranker's.** The range contract binds
   `ValueBundle.prior_score`. `multidim_recall` returns scores from *arbitrary* dimensions, and
   `PRIOR_MASS_DIMENSIONS` is a fixed `frozenset({"label", "prior"})`. A future non-cosine,
   non-prior dimension — a BM25 dimension, say, and `analysis.a2t_lexical_ceiling.Bm25Index`
   already exists in this repository — would be treated as a cosine dimension, would be unbounded,
   and would be range-checked nowhere. The divisor is the only thing that would catch it.
3. **Defence in depth with independent failure modes.** The contract catches a non-probability at
   BUILD; the divisor catches an out-of-scale dimension at RANK. They fail independently, which is
   the whole value of having both.
4. **The cost of keeping is exactly zero and the cost of removing is not.** Keeping costs an
   identity transform. Removing edits `rails/kb_policy.py`, whose sha256 `2a1c3d75…1019af` is pinned
   by the landed Stage-2A synthesis and asserted against the live tree, so removal is a change to
   the locked baseline's code path requiring a re-pin.

One honest caveat, recorded rather than acted on: because the divisor **rescales** instead of
refusing, an out-of-range dimension that somehow reached the ranker would be silently normalised. It
must rescale rather than refuse — historical snapshots have to stay rankable — but it could also
*record*, the way the load path now does. That is a separate, separately-registered change and this
row does not make it.

---

## 8. WHAT THIS ROW COULD NOT VERIFY

1. **Whether a corrected prior would change anything on a population other than A2T-G1-104.** The
   supply invariance is measured on those 104 trajectories only. SLURP needs no such measurement —
   its priors are bit-identical (§3) — but no other A2T population was replayed.
2. **What the corrected prior does to a flight rather than a replay.** No flight was run. The
   rebuilt snapshot is consumed by nothing, and promoting it is not proposed here.
3. **Whether the pre-repair A2T source lines held at any commit other than `3f131afd`.** The
   evidence is the landed synthesis receipt's check against that one tree.
4. **Whether any other `rails/` quantity carries the same unrestricted-ratio shape.** Only
   `prior_score` was audited. The two builders were the two the synthesis named; no systematic
   sweep of every ratio in the repository was performed.
5. **The 60-intent count against the SLURP builder's own docstring**, which says "SLURP train: 91
   intents". The measured 60 agrees exactly with the pinned SLURP snapshot's own **60 prior
   facets** (one per intent), so the measurement is anchored to a landed artifact and the docstring
   figure is the outlier — but *why* the docstring says 91 was not investigated here.

---

## 9. HARD STOP

**CORRECTNESS REPAIR ONLY.** This row changes no knob, writes nothing under `configs/`, does not
touch `rails/kb_policy.py`, displaces no pinned snapshot, opens no sealed run directory beyond the
already-broken A2T-G1-104 seal, and breaks no seal. `consumed` is `no`. It does **not** revise the
DEV-1000 LOCK, revise any landed number, authorise a flight, a re-flight, a rebuild-and-repin, a G2
opening, a test contact or any Stage-3 activity. FINAL60 stays reserved. The §7 recommendation
about `max(1.0, sup_d)` is a **recommendation**; the change is not made here.
