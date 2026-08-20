# P-FEW verdict — INCONCLUSIVE-FEW (registered one-shot read, 2026-08-19)

Mechanical outcome per the registered metrics and verdict rules
(`docs/readiness/2026-08-19-pfew-preregistration-REGISTERED.md` §3), computed by the pinned
offline read suite (`analysis.pfew_read`, coordinator-reviewed before the read) over the
already-flown attempt `attempt-20260819T233312Z-480fed` (`SAEA-PROBE-pfew-180`, status
`COMPLETED`, error `None`, 180/180 rows across FS-NONE / FS-BAL / FS-SKEW) — zero model contact,
zero GPU, no attempt-directory mutation.

Read archive: `docs/checks/speech-aware-evidence-acquisition/2026-08-19-pfew-read/`
(`verdict.json`, `report.txt`, `README.md`, `MANIFEST.sha256`). The suite ran exactly once
(idempotence-guarded output dir), exit 0, at study HEAD `47eb2c1` with a clean tree. Exposure row
`SAEA-PROBE-pfew-180` flips to consumed in the same commit. Scope: **descriptive, discovery-tier,
n = 60 SLURP devel, single run, same-distribution**. SLURP audio CC BY-NC 4.0 carried on every
number below.

Pre-read gates, all green before anything was opened: `test_pfew_read.py` **27 passed**; the
flight archive's `MANIFEST.sha256` verified **27/27 OK**; ledger row `consumed = no`; tree clean
at `47eb2c1`. The attempt directory was not mutated — every file mtime in it (19:33–19:39)
predates the read (20:39), post-read fingerprint `8968b37b…1b27`.

---

## 1. REACHABILITY STATEMENT (mandatory §3 item; published BEFORE any verdict was evaluated)

The registration requires the pre-read reachability statement to be published first, computed from
FS-NONE's own measured accuracy, because a high zero-demo comparator can put the +0.10 FS-HELPS
floor above the arithmetic ceiling and make the affirmative branch unreachable.

| quantity | value |
|---|---|
| samples flown per arm | **60** (FS-NONE 60 / FS-BAL 60 / FS-SKEW 60) |
| **acc(FS-NONE)** — the in-session zero-demo comparator | **0.8167** (49/60) |
| best case for BAL−NONE (FS-BAL = 1.0) | **max attainable diff = +0.1833** |
| FS-HELPS floor | **+0.10** |
| **BAL−NONE branch** | **REACHABLE** — headroom **+0.0833** |
| best case for NONE−SKEW (FS-SKEW = 0.0) | **max attainable diff = +0.8167** |
| BIAS-SENSITIVE floor | **+0.15** |
| **NONE−SKEW branch** | **REACHABLE** — headroom **+0.6667** |

**The ceiling case did not fire, but it came close enough to be worth stating plainly.** With the
zero-demo router already at 0.8167 there were only 11 recoverable samples in the whole population,
and FS-HELPS demanded 6 of them. Had FS-NONE landed at 0.9167 or above — a further two samples —
the +0.10 gain would have been *arithmetically unreachable* and no amount of demo engineering could
have produced an affirmative FS-HELPS on this design. The affirmative branch survived by two
samples. Any successor probe on this task must treat the +0.10 floor as near-degenerate against a
0.82 baseline and either enlarge n, restrict to the hard stratum, or re-register the floor; that is
a design lesson this read purchases regardless of its verdict.

The equivalence branch (FS-INERT) was likewise legally available before the data was opened: with
60 paired samples a CI can in principle sit wholly inside ±0.05. It did not — see §2 — but it was
never suppressed by construction.

---

## 2. VERDICT

> ## OVERALL: **INCONCLUSIVE-FEW**
> (no registered branch fires; the point estimate on the primary contrast is an exact zero and the
> CI is wider than the equivalence band)

| arm | closed-set scenario accuracy vs gold (scoring-side) |
|---|---|
| **FS-NONE** — zero demos, in-session comparator | **49 / 60 = 0.8167** |
| **FS-BAL** — K=4 label-balanced TRAIN demos | **49 / 60 = 0.8167** |
| **FS-SKEW** — K=4 demos all labelled `audio` | **45 / 60 = 0.7500** |

| contrast | point | σ̂ (paired bootstrap) | 90 % CI (N = 10,000, seed 20260807) |
|---|---|---|---|
| **BAL − NONE** | **+0.0000** | 0.0411 | **[−0.0667, +0.0667]** |
| **NONE − SKEW** | **+0.0667** | 0.0323 | **[+0.0167, +0.1167]** |

### Clause margins (every clause, in the registered order)

| clause | result | margin |
|---|---|---|
| **FS-HELPS point** (§3): acc(FS-BAL) − acc(FS-NONE) ≥ +0.10 | **not met** | +0.0000 vs floor +0.10 — short by **0.1000** (6 samples) |
| **FS-HELPS CI-gated** (§3): point met **and** CI lower bound > 0 | **not met** | failed on the point estimate; CI low is **−0.0667**, i.e. **0.0667 below** the 0 gate |
| **FS-INERT point** (§3): \|acc(FS-BAL) − acc(FS-NONE)\| ≤ 0.05 | **MET** | \|+0.0000\| vs ceiling 0.05 — clears by **0.0500**, the maximum possible margin |
| **FS-INERT CI-gated** (§3, authoritative): the entire CI inside [−0.05, +0.05] | **not met** | CI **[−0.0667, +0.0667]** overhangs the band by **0.0167 at each edge** (one sample of resolution on either side) |
| **BIAS-SENSITIVE overlay** (§3): NONE−SKEW ≥ +0.15 **and** capture rate ≥ 0.25 | **not met** | degradation +0.0667 vs floor +0.15 — short by **0.0833** (5 samples); capture 0.0339 vs floor 0.25 — short by **0.2161** |
| **INCONCLUSIVE-FEW** (otherwise) | **REACHED** | — |

**The FS-INERT near-miss is the most informative line in the table and must not be narrated as an
equivalence result.** The point estimate is not merely inside the ±0.05 band, it is exactly zero —
49 correct against 49 correct. The registered CI gate nonetheless refuses the affirmative, and the
suite says so explicitly in its own output: *"a point estimate inside the band with a CI crossing it
is INCONCLUSIVE-FEW, never an affirmative FS-INERT."* The gap is **0.0167 per edge — one sample out
of sixty**. At n = 60 the paired bootstrap simply cannot resolve a ±0.05 equivalence band; the
instrument, not the phenomenon, is what falls short. The correct reading is **"no gain was detected,
and this design cannot certify the absence of one at ±0.05 resolution"**, and the successor
requirement is arithmetic: an equivalence claim at this band needs materially more than 60 paired
samples, or a narrower band, registered in advance.

**BIAS-SENSITIVE fails on both of its conjuncts, and for two different reasons.** The degradation
conjunct fails by 5 samples but is *directionally real and CI-separated from zero* — the NONE−SKEW
CI is **[+0.0167, +0.1167]**, entirely above 0. The capture conjunct fails by an order of magnitude
and, per §4, fails structurally rather than marginally: not one prediction moved to the skewed
label. A single overlay verdict conflating "the demos hurt" with "the demos hurt *by imposing their
label prior*" therefore obscures what happened. Both halves are reported separately below.

---

## 3. Mapping-outcome distributions and instrument integrity

| arm | mapping outcomes | non-fallback |
|---|---|---|
| **FS-NONE** | `{exact: 60}` | 60/60 |
| **FS-BAL** | `{exact: 60}` | 60/60 |
| **FS-SKEW** | `{exact: 60}` | 60/60 |

**180/180 responses carried a canonical label verbatim.** No case-normalized tier, no substring
tier, no unmapped row, on any arm. This reproduces the A1′r phase-1 result (`{exact: 60}`, 60/60
non-fallback) that first established closed-set decode routing as viable, and it extends it: the
closed-set contract survives the insertion of a four-demo block ahead of the instruction, and
survives a maximally skewed one. **The demo block never degraded the output contract** — the whole
of the FS-SKEW loss is wrong-label choice, none of it is malformed output. That is a genuinely
useful robustness fact about the routing tier's *form* layer, orthogonal to the null on its
*content* layer.

`harness_defect_reasons` is empty. Flight status `COMPLETED`, error `None`, 60/60 rows per arm,
180 distinct (arm, sample_id) pairs. `runtime_prohibited = true` and the suite's own note —
*"gold-derived; scoring-side only; must never enter a runtime path"* — travel in `verdict.json`.

---

## 4. Skew-capture accounting — the seeded label, the excluded denominator, and the zero

### 4.1 What the registered number is

| quantity | value |
|---|---|
| seeded **global** skew label | **`audio`** |
| samples flown | 60 |
| **excluded** (gold == skew label; capture undefined) | **1** — `slurp:devel:000115:audio-1495375974` |
| **denominator** | **59** |
| capture count (FS-SKEW answer == `audio` on a sample where `audio` is wrong) | **2** |
| **capture rate** | **2 / 59 = 0.0339** (floor 0.25) |

The exclusion is the registration's own disclosed accounting, implemented in the suite's
`compute_skew_capture`, and this read is the first step in the chain that knew its size: the flight
deliberately did not look it up. It is **1 of 60**. The denominator loss is negligible and the
accounting is disclosed here in full, as the flight receipt promised.

**Why the skew label is global rather than per-sample.** A per-sample "wrong for *this* sample"
label requires that sample's own devel gold at binding time, which the research boundary forbids.
`build_demo_binding` therefore drew one label once, from the 18 canonical labels, with zero gold
input; it landed on `audio`. The cost of that legality is that the skew arm's prior is only
*mostly* wrong (59/60 here) and that the pull it exerts is toward one particular, and as it turns
out low-frequency, class.

### 4.2 What the number conceals — the incremental capture is exactly zero

The 0.0339 figure is not a small capture. It is **no capture at all**, inherited entirely from the
zero-demo baseline. FS-SKEW predicted `audio` on exactly three rows:

| sample_id | gold | FS-NONE | FS-BAL | FS-SKEW | counted as capture? |
|---|---|---|---|---|---|
| `slurp:devel:000115:audio-1495375974` | `audio` | `audio` | `audio` | `audio` | no — **excluded** (gold == skew label) |
| `slurp:devel:009340:audio-1497882818-headset` | `play` | **`audio`** | **`audio`** | `audio` | yes |
| `slurp:devel:011503:audio-1494514154` | `play` | **`audio`** | **`audio`** | `audio` | yes |

**Both counted captures are samples the zero-demo router already answered `audio` on, unprompted.**
So is the excluded one. Netting the baseline out:

> **Incremental skew capture attributable to the 240 skewed demo slots = 0 / 59 = 0.0000.**
> Not one sample was pulled to the demo label that was not already there.

The marginal distribution says the same thing without reference to any individual row: **`audio` is
predicted exactly 3 times under FS-NONE, exactly 3 times under FS-BAL, and exactly 3 times under
FS-SKEW.** Four demonstrations of a label, in every one of 60 prompts, moved that label's predicted
marginal by **zero**.

### 4.3 The degradation is real, and it is not prior-parroting

FS-SKEW does lose 4 samples relative to FS-NONE, and the loss is strictly one-directional:

| | count |
|---|---|
| FS-NONE right & FS-SKEW wrong | **4** |
| FS-SKEW right & FS-NONE wrong | **0** |

| sample_id | gold | FS-NONE | FS-SKEW |
|---|---|---|---|
| `slurp:devel:005359:audio-1497265137-headset` | `datetime` | `datetime` | `general` |
| `slurp:devel:008072:audio-1488986707` | `calendar` | `calendar` | `datetime` |
| `slurp:devel:009733:audio--1505407176` | `play` | `play` | `general` |
| `slurp:devel:011654:audio-1501692977-headset` | `recommendation` | `recommendation` | `transport` |

**None of the four losses went to `audio`.** Two went to `general`, the catch-all class, whose
predicted marginal rises 1 → 2 → 3 across NONE → BAL → SKEW. The skewed demo block therefore
behaves as a **generic distractor that degrades routing confidence into the catch-all**, not as a
label prior that captures the decision. This is a mechanism distinction the registered overlay was
not designed to make, and it is the substantive skew finding of the probe:

> On this frozen core, at this tier, a maximally skewed four-shot label prior costs about
> 4 samples in 60 (CI [+0.0167, +0.1167], separated from zero) and buys the skewed label **nothing**.
> The classic ICL label-prior-bias failure mode did **not** reproduce; a smaller, unglamorous
> ICL-noise failure mode did.

That is consistent with, and independently supportive of, the 2026-08-19 discussion premise the
registration was built on: the word-level resonance law does not extend to the label level, because
class labels have no acoustic relation to the audio. P-TRAP measured 0/32 cross-sample capture on
the *content* side; P-FEW now measures 0/59 incremental capture on the *label* side. Two
independent probes, two exact zeros, on the same underlying claim.

---

## 5. Per-sample table and the structure of the residual error

The full 60-row three-arm table (sample_id, gold, FS-NONE / FS-BAL / FS-SKEW label and correctness)
is in **`docs/checks/speech-aware-evidence-acquisition/2026-08-19-pfew-read/verdict.json`** under
`per_sample`, and rendered verbatim in `report.txt`. It is not duplicated here. The structural
readings drawn from it follow.

### 5.1 The primary null is a wash, not an absence of movement

FS-BAL and FS-NONE tie at 49, but they are **not the same predictions**: the arms agree on 54 of 60
labels and differ on 6, splitting exactly **3 gains / 3 losses**.

| sample_id | gold | FS-NONE | FS-BAL | |
|---|---|---|---|---|
| `slurp:devel:005025:audio-1500900618` | `iot` | `music` | **`iot`** | gain |
| `slurp:devel:008047:audio-1498570919` | `calendar` | `lists` | **`calendar`** | gain |
| `slurp:devel:009518:audio-1495734594-headset` | `play` | `news` | **`play`** | gain |
| `slurp:devel:000943:audio-1434529860-headset` | `datetime` | **`datetime`** | `qa` | loss |
| `slurp:devel:009733:audio--1505407176` | `play` | **`play`** | `general` | loss |
| `slurp:devel:012478:audio-1498486426` | `transport` | **`transport`** | `takeaway` | loss |

Balanced demonstrations are **not inert at the decision level** — they move 10 % of the population.
They are inert *in expectation*, because what they move, they move in both directions with equal
frequency. The three gains are all genuine confusion repairs (music→iot, lists→calendar,
news→play); the three losses are all fresh confusions of the same kind. The honest summary is that
four balanced demos act as a **re-randomization of the router's borderline decisions**, not as
information about the label space. That is a different, and more useful, statement than "few-shot
does nothing."

All-three-arms-identical on **51 of 60** samples: the core of the routing decision is unmoved by any
demo condition tested.

### 5.2 The residual error is one confusable cluster, not diffuse noise

FS-NONE's 11 errors are heavily concentrated:

| gold class | n | FS-NONE | FS-BAL | FS-SKEW |
|---|---|---|---|---|
| **`play`** | **7** | **1** | **1** | **0** |
| `calendar` | 8 | 7 | 8 | 6 |
| `weather` | 4 | 3 | 3 | 3 |
| `transport` | 4 | 4 | 3 | 4 |
| `datetime` | 3 | 3 | 2 | 2 |
| `iot` | 3 | 2 | 3 | 2 |
| `recommendation` | 3 | 3 | 3 | 2 |
| `social` | 3 | 2 | 2 | 2 |
| `general` | 2 | 1 | 1 | 1 |
| `audio`, `music`, `news`, `takeaway`, `alarm`, `cooking`, `lists`, `qa`, `email` | 24 | perfect on all three arms | | |

**`play` accounts for 6 of the 11 zero-demo errors and collapses into its media neighbours:** three
to `music`, two to `audio`, one to `news`. Nine of the eighteen canonical classes are perfect on all
three arms. This is not a router that is uniformly noisy at 0.82; it is a router that is
**essentially correct outside one label neighbourhood and essentially blind inside it**.

**Balanced four-shot demonstrations did not touch it.** FS-BAL scores 1/7 on `play`, identical to
FS-NONE, having merely swapped which single `play` sample it gets right. Every FS-BAL prompt
contained four distinct labels drawn from all 18 canonical classes, so on most samples the
`play`/`music`/`audio` distinction was not demonstrated at all — and where it was, it did not
transfer. This is the concrete reason the +0.10 gain was never in reach: **more than half the
available headroom sits in a single systematic confusion that generic demonstrations cannot
address.**

The design implication is direct and belongs in the successor queue: the routing tier's open
problem is not *how much* supply to give the router, it is *targeting supply at the confusion the
router actually has*. That is the routing-tier twin of the filling tier's already-registered
supply-targeting problem (scoreboard §Filling tier, item 3), and it is what P-CORR's corrective
confusable-pair design would attack at this tier.

---

## 6. An in-session replication discrepancy against the cited A1′r comparator

The registration made FS-NONE an **in-session comparator** and pinned A1′r's 47/60 as cited context
that "is never a substitute." That precaution earned its keep.

| | phase-1 closed-set routing, same 60 SLURP devel samples | accuracy |
|---|---|---|
| cited **A1′r** phase-1 (consumed, 2026-08-18, `pslu_s2` flight) | 47/60 | **0.7833** |
| **FS-NONE** (this flight, 2026-08-19) | **49/60** | **0.8167** |

The two are supposed to be the same measurement. The pre-flight verified that FS-NONE's prompt block
is **byte-identical** to the reused A1′r phase-1 packet (`pslu-s2-a1r-phase1-closed-set-v1`,
432 chars); the decode configuration is the consumed flight's own, unchanged
(`-c 49152 -np 4 -fa on -ngl 999 -ctk q8_0 -ctv q8_0`; `temperature 0, seed 20260803,
max_tokens 1024`); the samples, the split identity hash, the runtime build and both GGUF hashes all
match. **The result differs by two samples.**

Candidate explanations, none of which this read can adjudicate, and no further model contact is
authorized to try:

1. **Continuous-batching nondeterminism.** Both flights ran `-np 4`; slot assignment and batch
   composition differ between a 183-row four-arm session and a 180-row three-arm session, which
   changes floating-point reduction order in the batched kernels. `temperature 0` fixes the sampling
   rule, not the logits.
2. **Session/context differences.** A1′r's phase-1 requests were interleaved with three other
   request families in one session; FS-NONE's were a contiguous 60-row block.

Neither is a defect and neither is under any clause. What matters is the **magnitude**: a nominally
deterministic configuration reproduced to **±2 samples = ±0.0333** across sessions. That figure is
the same order as — in fact *larger than* — the entire BAL−NONE contrast this probe was built to
measure (+0.0000), and it is two-thirds of the ±0.05 equivalence band FS-INERT was gated on.

**Consequences, stated once and carried forward:**

- The registration's decision to fly an in-session FS-NONE rather than cite 47/60 was correct, and
  every future routing-tier contrast on this carrier must do the same. Comparing an arm flown today
  against a number flown yesterday cannot resolve effects below ~0.03 on n = 60.
- The scoreboard's routing-tier entry should read A1′r's closed-set gold agreement as **0.78–0.82
  across two sessions**, not as the point value 0.7833.
- Any successor equivalence band at ±0.05 on n = 60 is now known to be *within* cross-session
  reproduction noise, independent of bootstrap width. This reinforces §2's successor requirement
  from a second, independent direction.

This observation is descriptive, unregistered, and carries no clause. It is recorded because it
bounds the resolution of every small-n routing number in the program, including this probe's own.

---

## 7. What this adds to the routing-tier hypothesis

The scheme scoreboard's routing tier (`docs/readiness/2026-08-19-scheme-scoreboard.md`, "Current
best-scheme statement v1") lists closed-set decode routing as the one established positive
(A1′r 60/60 non-fallback, 47/60 gold agreement) and marks few-shot routing gain/bias as under test.
P-FEW resolves the *bias* half and returns a hard null on the *gain* half.

**What is now established at the routing tier.**

- **The form layer is robust.** Closed-set decode routing produced `{exact: 60}` mapping under three
  different prompt constructions, including a maximally skewed one. 180/180 responses were canonical
  labels. Whatever else varies, the router's output contract holds. (Second independent
  confirmation, after A1′r.)
- **Demonstration supply does not raise routing accuracy on this carrier.** BAL−NONE = +0.0000 with
  a CI of [−0.0667, +0.0667]. The affirmative branch was reachable by +0.0833 and was not
  approached. Under the scoreboard's own consistency bar this is a **negative** for the "few-shot
  routing gain" mechanism at 1/1, not an equivalence: the CI is too wide to certify inertness.
- **Label-prior capture does not occur at this tier.** 0/59 incremental capture; the skewed label's
  predicted marginal is 3 → 3 → 3 across all arms. This is the label-level companion to P-TRAP's
  0/32 cross-sample content-level control, and together they make the registration's founding
  premise — *no acoustic resonance channel exists at the label level, so label-level supply behaves
  classically and weakly* — an evidenced statement rather than an assumption.
- **A small ICL-noise cost is real.** NONE−SKEW = +0.0667, CI [+0.0167, +0.1167], entirely above
  zero; 4 losses, 0 gains, damage landing in the catch-all class. Badly-chosen demonstrations cost
  something even when they capture nothing.
- **The headroom is structurally concentrated.** 6 of 11 residual errors are one class (`play`)
  collapsing into its media neighbours; 9 of 18 classes are perfect on every arm. Generic supply
  cannot reach this; targeted corrective supply might.

**What this does to the two-tier architecture statement.** The routing tier's positive result
remains exactly what it was — closed-set decode prompting — and P-FEW removes one candidate way of
improving it. The tier's improvement path is now narrowed to (a) a *different representation*
(embedding matching, P-EMB-1/2, read next) rather than more prompt context, or (b) *targeted*
corrective supply aimed at the measured confusion neighbourhood. "More demonstrations" is
eliminated as a lever at n = 4 on this carrier.

**Scoreboard deltas this read licenses** (to be applied when the arc's reads are consolidated):

| consistency-ledger row | before | after this read |
|---|---|---|
| Few-shot routing gain | ⏳ under test | **❌ 0/1 — no gain (BAL−NONE +0.0000, CI [−0.0667, +0.0667]); equivalence NOT certified (CI wider than ±0.05)** |
| Few-shot routing bias / label-prior capture | ⏳ under test | **❌ does not occur — 0/59 incremental capture, skew-label marginal unchanged 3→3→3; small non-capture ICL cost +0.0667, CI above zero** |
| Closed-set decode routing viable | ✅ 1/1 (A1′r) | **✅ 2/2 — `{exact: 60}` reproduced under three prompt constructions; but gold agreement is 0.78–0.82 across sessions, not a point value** |
| Label-level supply has no resonance channel | (premise) | **✅ 2/2 — P-TRAP 0/32 cross-sample content, P-FEW 0/59 label-prior** |

**Bounds on every sentence above.** n = 60 SLURP devel, one run per arm, same-distribution, one
carrier, one core, K = 4 only, one seeded skew label, discovery tier. Cross-session reproduction on
this instrument is ±2 samples (§6). No superiority, generalization, deployment, or paper-scale claim
attaches to any number in this document. Gold labels were used scoring-side only and never entered
a runtime path.
