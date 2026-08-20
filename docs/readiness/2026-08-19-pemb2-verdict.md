# P-EMB-2 verdict — EMB-CLOSED (registered one-shot read, 2026-08-19)

Mechanical outcome per the registered metrics and verdict rules
(`docs/readiness/2026-08-19-pemb-preregistration-REGISTERED.md` §3, Run B), computed by the pinned
offline read suite (`analysis.pemb_read run-b`, coordinator-reviewed before the read) over the
already-flown attempt `attempt-20260820T002031Z-e816e2` (`SAEA-PROBE-pemb2-552`, status
`COMPLETED`, error `None`, durable state `FINALIZED`, 552/552 embedding contacts = 400 audio +
152 tool registry rows) — zero model contact, zero GPU, no attempt-directory mutation.

Read archive: `docs/checks/speech-aware-evidence-acquisition/2026-08-19-pemb2-read/`
(`verdict.json`, `report.txt`, `README.md`, `MANIFEST.sha256`). The suite ran exactly once
(idempotence-guarded output dir), exit 0, at study HEAD `6ebcaba` with a clean tree. Exposure row
`SAEA-PROBE-pemb2-552` flips to consumed in the same commit. Scope: **descriptive, discovery-tier,
n = 400 Audio2Tool discovery split, 152 registry rows, single run, same-distribution**. Audio2Tool
CC BY-NC 4.0 carried on every number below.

Pre-read gates, all green before anything was opened: `test_pemb_read.py` **41 passed**; the flight
archive's `MANIFEST.sha256` verified **36/36 OK**; ledger row `consumed = no`; tree clean at
`6ebcaba`. `PYTHONDONTWRITEBYTECODE=1` throughout, zero `__pycache__`/`*.pyc` under the frozen
scoring package after the read. The read consumed only the derived vector manifest
(`derived/embeddings/SAEA-PROBE-pemb2-552/manifest.json`, 552 entries, all dim 2048, 552 distinct
vector sha256) plus the consumed A0 attempt it re-partitions; every attempt-dir and derived-root file
mtime is 20:23 and predates the 21:26 read, post-read attempt fingerprint `88bbdb86…b134`.

**Landing-integrity note.** The read CLI ran to completion (exit 0, bundle written 21:26), but the
supervising session was severed by a transient connection error while the CLI was still executing.
The landing was completed afterwards from the bundle the single execution had already written. **The
read still executed exactly once**: the output directory's idempotence guard was never re-armed, no
second invocation was issued, `verdict.json` (194,522 B) and `report.txt` carry the 21:26 mtimes of
that one execution, and the attempt directory's post-read fingerprint is recorded above. Nothing in
this document was recomputed by a second pass over the model artifacts.

---

## 1. THE 183 HEADLINE

The registration's primary axis is **recovery on the 183 tool-wrong ids** — the population where the
decode router selects the wrong tool and which, per the V4 whole-population read, **no supply form
reaches**: EM cannot regress there and no gold-free supply-row rule exists for them, so 183 of the
frozen 400 (45.75 %) sit outside the program's signed supply account entirely. P-EMB-2 was the
registered attempt to open that population by a non-supply route.

> ## OVERALL: **EMB-CLOSED**
> top-1 accuracy on the 183 tool-wrong ids = **0.0109** ≤ 0.10

| quantity | value |
|---|---|
| tool-wrong population | **183** ids |
| **top-1 recoveries** | **2** |
| **top-1 accuracy on the 183** | **2 / 183 = 0.0109** |
| **top-5 accuracy on the 183** (reported alongside, as registered) | **5 / 183 = 0.0273** |
| candidate set | **152** tool registry rows |

### Clause margins (every clause, in the registered order)

| clause | result | margin |
|---|---|---|
| **EMB-OPENS-183** (both conjuncts required): top-1 ≥ 0.30 **and** ≥ 55 recoveries | **not met, on both** | top-1 0.0109 vs floor 0.30 — short by **0.2891**; recoveries 2 vs floor 55 — short by **53 samples**, i.e. the observed recovery count is **3.6 %** of the registered floor |
| **EMB-CLOSED**: top-1 ≤ 0.10 | **MET** | 0.0109 vs ceiling 0.10 — clears by **0.0891**, a factor of **9.2** inside the ceiling |
| **INCONCLUSIVE-EMB2** (otherwise) | not reached | — |

### The two recoveries do not survive a chance baseline

| baseline on the 183 | value |
|---|---|
| uniform chance over 152 rows, with this population's mean gold-set size 1.49 | expected **1.79** hits |
| expectation under random re-pairing of the **same 183 predicted tools** to the same samples | expected **0.99** hits |
| **observed** | **2** hits |
| permutation test, shuffling only the prediction vector (N = 100,000, seed 20260807) | **P(hits ≥ 2) = 0.2562** |

**Two recoveries out of 183 is what this prediction vector produces by accident.** It is roughly
what uniform guessing over the registry would produce, it is statistically indistinguishable from a
random re-pairing of the router's own outputs, and the top-5 figure is worse than that: **0.0273
against a uniform top-5 chance rate of 5/152 = 0.0329** — the router's top-5 list is *less* likely
to contain the gold tool than five rows drawn at random. Both recoveries land on tools that are
collapse attractors (`tier2_parametric:004217` → `streamCamera`, cosine −0.1047;
`tier7_multiturn:000318` → `setHumidifierState`, cosine −0.0707), not on tools the router reached by
discrimination.

**The 183 are not opened. They stay exactly as V4 left them**: a population that no supply form
reaches, that EM cannot score for regression, and for which this program now has one measured,
failed rescue attempt rather than an open question.

---

## 2. Non-degradation on the 217 (reported, no clause attaches)

The registration reports this axis as informational: *"a router would only ever be composed as a
rescue/argmax-fallback, so degradation here is informational."*

| population | decode router (A0 zero-supply, cited) | embedding argmax-cosine router |
|---|---|---|
| the **217** tool-correct ids | **217 / 217 = 1.0000** by construction | **1 / 217 = 0.0046** |
| the **183** tool-wrong ids | 0 / 183 = 0.0000 by construction | 2 / 183 = 0.0109 |
| whole frozen **400** | **217 / 400 = 0.5425** | **3 / 400 = 0.0075** |

**Degradation on the 217 is total.** The embedding router retains 1 of the 217 selections the decode
router already had right, and that one (`tier2_parametric:001365` → `setHumidifierState`) is again an
attractor tool. At 0.0046 it sits **below** the uniform chance rate of 1/152 = 0.0066; the
permutation baseline expects 1.24 hits and gives **P(hits ≥ 1) = 0.7358**.

The composition arithmetic follows directly, and is recorded because it is the only form in which a
router of this kind could ever be deployed. As a **replacement** router it converts a 0.5425
whole-population tool accuracy into 0.0075 — a loss of **214 of 400 samples**. As a **rescue /
argmax-fallback** applied only where decode fails, it would add **2** recoveries; as a *confidence-
gated* fallback it would need a gate, and §4 shows this space provides none. No composition of this
router is net-positive on this carrier.

This paragraph is informational per the registration and **no clause attaches to any number in it**.

---

## 3. Confusion structure — the same collapse as Run A, on a 152-way problem

| quantity | value |
|---|---|
| distinct tools ever predicted (over all 400) | **15 of 152** |
| most-predicted tool | **`stopCharging` — 151 / 400 = 37.8 %** |
| top-2 predicted tools' share | `stopCharging` + `setHumidifierState` = **213 / 400 = 53.3 %** |
| top-5 predicted tools' share | **343 / 400 = 85.8 %** |
| distinct tools predicted on the 183 | **11**; `stopCharging` 62, `setHumidifierState` 33, `streamCamera` 25, `getNetworkHealth` 24, `setHvacMode` 15 |
| distinct tools predicted on the 217 | **13**; `stopCharging` 89, `getNetworkHealth` 33, `setHumidifierState` 29, `setHvacMode` 20, `setVoiceGuidance` 15 |

**137 of 152 registry rows were never the nearest neighbour of any audio clip in the run.** The
confusion table over the 183 (full version in `verdict.json` / `report.txt`) reads as a column
structure exactly as Run A's did — `setColor → stopCharging` 4, `getAirQuality → stopCharging` 3,
`getAirQuality_diag → streamCamera` 3, `setColor → setHumidifierState` 3,
`setGroupLightState → streamCamera` 3, `setLighting → stopCharging` 3 — with gold classes of every
kind funnelling into the same handful of attractors and no visible relation between the gold tool and
which attractor absorbs it.

### Every one of the 400 winning cosines is negative

| statistic over the 400 winning (audio, registry-row) pairs | value |
|---|---|
| max | **−0.0494** |
| mean | **−0.1253** |
| median | **−0.1177** |
| min | **−0.2541** |
| pairs with a positive cosine | **0 / 400** |

With L2-normalized vectors on both sides, **the best of 152 candidate tool rows is anti-aligned with
the audio on every single one of the 400 samples**. There is no sample in this run for which any
registry row is even weakly positively similar to the clip. Run A's near-orthogonality (mean +0.038)
becomes, on this carrier, uniform anti-alignment. The argmax is selecting the *least negative* of 152
negative similarities, which is a text-side geometry artifact and not a content match, and the
15-tool collapse is that same fact seen from the label side.

### This carrier removes Run A's strongest confound

Run A's negative carried three named confounds; **Run B kills one of them outright.** Run A's text
side was a bare one- or two-token canonical label, and "severe length and form asymmetry against a
multi-second clip" was a live explanation of the collapse. Run B's text side is the **full shipped
registry row** (`data.audio2tool.render_registry_row`, `strip_defaults=False` — tool name,
description, and parameter schema), an order of magnitude richer and longer, against clips averaging
5.4 s. **The result is not better; it is worse** — accuracy below chance, top-5 below chance, and
every cosine negative where Run A at least had positive ones.

Making the text side richer therefore does not help, and the remaining explanation is the one Run A
named first and could not isolate: **the frozen core has no contrastive objective, so its mean-pooled
audio states and mean-pooled text states do not occupy a shared space.** Two carriers, two label-set
sizes (18 vs 152), two text renderings (bare label vs full registry row), one conclusion.

---

## 4. What this does to the P-TARGET design gate

P-TARGET — *router confidence as the supply-targeting signal* — is item 3 of the scoreboard's design
queue and is registered as **needing the P-EMB reads** before it can be designed. Both reads are now
in, and the gate resolves **negatively for the embedding channel and positively for the problem's
importance**.

**1. The embedding channel cannot supply the confidence signal.** P-TARGET's implicit candidate was
cosine margin: rank samples by how decisively the router picked its top candidate, supply where the
margin is low. That signal does not exist here. On Run A the winning cosines are near-orthogonal
(mean +0.038) and the predictions collapse to 2 attractors; on Run B every winning cosine is negative
(mean −0.125) and the predictions collapse to 15 of 152 rows. **A margin computed over a collapsed,
anti-aligned similarity field ranks the attractor geometry, not the samples' routing difficulty.**
This is now measured on two carriers and is not a marginal call.

**2. The targeting problem it was designed to attack is unchanged and still the binding one.** V4
measured the gap between *targeted* supply (+8 to +10 EM conversions on the gold-identified 120-id
headroom set) and *blind* supply (−26 to −28 EM samples over the 217 ids where the rule is defined) at
**34 to 38 EM samples wide**, with the explicit finding that closing it is an ORG/SUPPLY-side
selection problem — deciding *where* to supply — and not a supply-form problem. P-EMB-2 was the one
registered instrument that could have changed the shape of that account by opening the excluded 183.
**It did not.** The 183 remain undefined for the signed account, the 45.75 % denominator disclosure
stays attached to every statement of it, and the targeting gap gains no new instrument from this arc.

**3. Where P-TARGET's signal must come from instead.** If P-TARGET is registered, its confidence
signal has to be drawn from the **decode path**, and this arc has already produced measured,
gold-free candidates:

- **label-token logprobs** under the closed-set prompt (available from the decode path at no extra
  call cost);
- **cross-prompt disagreement**, for which P-FEW happens to have supplied the statistics. Flagging the
  samples where FS-NONE and FS-BAL choose different labels marks **6 of 60** samples; on all 6 at
  least one arm is wrong, FS-NONE itself is wrong on **3 of the 6**, giving a flag precision of
  **0.50** against a base error rate of **11/60 = 0.1833** — a **2.73× lift** — at recall **3/11 =
  0.27**. Extending the flag to three-way disagreement across FS-NONE/FS-BAL/FS-SKEW marks 9 samples
  at precision 0.33 (1.82× lift) and the same recall, i.e. **two arms are the better flag than
  three**. These figures are **descriptive, unregistered, n = 6, and carry no clause**; they are
  recorded because they are the only measured gold-free targeting signal this program currently has,
  and because they cost nothing beyond a second decode pass the program already knows how to fly.

**Recommendation input for a P-TARGET registration** (an input, not a design, and not an
authorization): register the confidence signal as a **decode-path disagreement or logprob statistic**,
pre-register its precision/recall against the *measured* base error rate rather than against an
assumed one, and scope the target population to the ids where an EM-signed rule is defined —
**explicitly excluding the 183**, which this read has now shown are not reachable by the embedding
route either. Any design that assumes an embedding-derived confidence score is refuted before it
starts.

---

## 5. Appendix — SYNTHESIS: the routing-tier scorecard

The second arc set out to test whether the **routing tier** (high-order semantics: intent, tool, QA
candidate) admits any lever besides the closed-set decode prompting already established. Three
schemes have now been measured on two carriers. This appendix consolidates them; it supersedes
nothing and each row's own verdict document remains the evidence of record.

### 5.1 Scoreboard

| # | scheme | carrier / task | candidates | headline number | comparator | verdict |
|---|---|---|---|---|---|---|
| 1 | **Closed-set decode routing** (cited; A1′r 2026-08-18 + P-FEW FS-NONE 2026-08-19) | SLURP scenario | 18 | **0.7833** (47/60) and **0.8167** (49/60) — a **0.78–0.82** range across two sessions | free-form decode ≈ 0.10 | ✅ **established** — `{exact: 60}` mapping and 60/60 non-fallback under three prompt constructions |
| 2 | **Few-shot demonstration supply on the decode router** (P-FEW) | SLURP scenario | 18 | FS-BAL **0.8167**; Δ vs FS-NONE **+0.0000**, 90 % CI **[−0.0667, +0.0667]** | FS-NONE 0.8167 | ❌ **INCONCLUSIVE-FEW** — no gain; equivalence **not** certified (CI wider than ±0.05) |
| 2b | *— the same probe's skew arm* | SLURP scenario | 18 | FS-SKEW **0.7500**; NONE−SKEW **+0.0667**, CI **[+0.0167, +0.1167]**; incremental label-prior capture **0/59** | — | ❌ **no BIAS-SENSITIVE** — a small real ICL-noise cost, **zero** prior capture |
| 3 | **Bare mean-pooled embedding matching** (P-EMB-1) | SLURP scenario | 18 | **0.0500** (3/60); 5 of 18 labels ever predicted; permutation **P = 0.8774** | uniform chance **0.0556** | ❌ **EMB-WEAK** — below chance; no content signal |
| 4 | **Registry-row mean-pooled embedding matching** (P-EMB-2) | Audio2Tool tool selection | 152 | top-1 on the 183 **0.0109** (2/183); top-5 **0.0273**; on the 217 **0.0046**; **400/400 cosines negative**; 15 of 152 tools ever predicted | uniform chance **0.0066**, top-5 chance **0.0329** | ❌ **EMB-CLOSED** — at chance on top-1, **below** chance on top-5 and on the 217 |

### 5.2 What the scorecard says

**One lever works, and after this arc it is still the only one.** Closed-set decode prompting routes
at 0.78–0.82 on SLURP and produces a canonical label on 100 % of calls under every prompt
construction tested. Nothing in the arc improved it and nothing replaced it.

**The two candidate improvements are both eliminated, and both cleanly rather than marginally.**
Few-shot supply moves 10 % of the population and moves it in both directions equally (3 gains,
3 losses, Δ exactly zero). Embedding matching does not route at all: it collapses onto a handful of
attractor candidates on both carriers, and the observed agreement with gold is fully explained by the
prediction marginal on both (permutation P = 0.8774 and P = 0.2562).

**The embedding negative is a property of the core, not of the construction.** Run A left three
confounds; Run B removes the strongest of them. Going from a one-token label to a full shipped
registry row — richer text, longer text, an order of magnitude more content on the matched side — made
the result *worse*, not better, and pushed every winning similarity negative. The surviving
explanation is that a generative decoder with no contrastive objective does not place mean-pooled
audio and mean-pooled text in a shared space. That is a statement about **this frozen core's
representation**, and it generalizes across the two carriers tested and the two candidate-set sizes.

**Label-level supply has no resonance channel — now at 2/2.** The arc's founding premise was that the
word-level acoustic resonance law (P-TRAP: the core re-emits its own mishearings at 29/32, and 0/32
for cross-sample controls) should *not* extend to class labels, which bear no acoustic relation to
the audio. P-FEW measured **0/59 incremental capture** of a skewed label prior with its marginal
unmoved at 3 → 3 → 3, and P-EMB-1/2 found no audio-to-label matching signal at all. Two independent
probes, two exact zeros; the premise is now evidenced rather than assumed.

**Two limits on the tier's numbers, both discovered inside the arc.** First, cross-session
reproduction on the 60-sample SLURP routing instrument is **±2 samples (±0.0333)** — the in-session
FS-NONE arm read 49/60 where the cited A1′r read 47/60 on the same samples with a byte-identical
prompt and unchanged decode config. Any routing contrast below ~0.03 on n = 60 is inside that noise,
and the ±0.05 equivalence band FS-INERT was gated on is only two-thirds of it. Second, the residual
routing error is **structurally concentrated, not diffuse**: 6 of the decode router's 11 SLURP errors
are the single class `play` collapsing into `music`/`audio`/`news`, while 9 of 18 classes are perfect
on every arm. Generic supply cannot reach a concentrated confusion; that is the mechanical reason
few-shot never had the headroom the +0.10 floor demanded.

### 5.3 The recommendation input for P-TARGET registration

P-TARGET's registered prerequisite ("needs P-EMB") is **discharged**, negatively for the mechanism it
implicitly assumed. Consolidated input, offered as input to a registration decision and authorizing
nothing:

1. **Do not build P-TARGET on an embedding-derived confidence score.** Refuted on two carriers:
   collapsed predictions and anti-aligned similarities make cosine margin a measure of the attractor
   geometry, not of routing difficulty.
2. **Draw the signal from the decode path.** The measured, gold-free candidate already in hand is
   cross-prompt disagreement: FS-NONE vs FS-BAL disagreement flags 6/60 samples at precision 0.50
   against a 0.1833 base error rate (**2.73× lift**, recall 0.27); three-way disagreement is worse
   (precision 0.33, 1.82× lift). Label-token logprobs under the closed-set prompt are the second
   candidate and cost nothing extra. *(n = 6; descriptive; no clause.)*
3. **Scope the target population to the ids where an EM-signed rule is defined, and exclude the 183.**
   P-EMB-2 was the registered attempt to open them and returned EMB-CLOSED at 3.6 % of its own
   recovery floor. The V4 account's 45.75 %-undefined denominator stands, and the 34-to-38-EM-sample
   targeting gap between targeted and blind supply is still the binding open problem — it simply has
   one fewer candidate instrument than it did before this arc.
4. **The routing tier's remaining untested idea is corrective, targeted supply**, aimed at the
   measured confusion neighbourhood rather than at the router in general — the routing-tier twin of
   the filling tier's supply-targeting problem, and the natural object of a P-CORR-style design.

### 5.4 Bounds carried by every statement in this appendix

n = 60 SLURP devel (18 labels, one run per arm) and n = 400 Audio2Tool discovery (152 registry rows,
one run); **single run, same-distribution, two carriers, one frozen core**; K = 4 and one seeded skew
label for P-FEW; one pooling mode (mean), no instruct prefix, and one text rendering per carrier for
P-EMB. σ̂ and CIs are measured on exactly one flight each; the conversion terms and the A1′r
comparator are **cited**, not co-measured. Cross-session reproduction on the SLURP routing instrument
is ±2 samples. The permutation checks and the disagreement-flag statistics are **descriptive and
unregistered** and carry no clause. The 183/217 partition is a property of one consumed A0 attempt
(V4 bound 3), not an established stable set. NC carried: SLURP audio CC BY-NC 4.0 and Audio2Tool
CC BY-NC 4.0 on every audio-derived number. Gold scenarios and gold tools were used scoring-side only
and never entered a runtime path. **No test split was touched. No superiority, generalization,
deployment, or paper-scale claim attaches to any number in this document.**
