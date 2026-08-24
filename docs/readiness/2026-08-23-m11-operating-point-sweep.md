# M11 operating-point sweep on already-exposed E108/C108 trajectories (2026-08-23)

## 0. Frame — read this before citing any number below

**Iteration tier. Model-free. Zero service contacts.** This is the first execution of the owner's
iterate-before-concluding ruling
(`docs/readiness/2026-08-23-knowledge-plane-baseline-rulings.md` §7.2, which authorizes sweeping a
design's operating-point curves on ALREADY-EXPOSED discovery data as ITERATION and reserves
one-shot reads for confirmatory readings).

- Every number here is a **DESIGN INPUT for the DEV-100 campaign's starting knobs**. Nothing more.
- **No verdict clause attaches.** No admission, promotion, generalization, or superiority claim may
  be derived from this document. This is not a reader output and not a one-shot confirmatory read.
- Gold labels are used **scoring-side only**, on train discovery data already opened scoring-side by
  the registered `SAEA-SN-MF-EVIDENCE-E108-ZCOPY-READ` and the four EFFECT-C108 read rows
  (precedent: the registered A1b/A1d evaluators and the P-EMB-4R mean-centering re-analysis).
- **FINAL60, the DEV-100/500/1000 ladder, SLURP devel, and SLURP test were not touched.**
- Exposure row: `SAEA-SN-MF-M11-OPERATING-POINT-SWEEP` (calls 0 / audio 0 / gpu 0.0), registered and
  committed before the first number was computed.
- **Honesty rule enforced in code**: counterfactual firing conditions yield COUNTS ONLY. A query that
  would have fired an acquisition under a relaxed condition but never actually flew it has no
  recorded outcome. That outcome is reachable only by new model contacts and is never imputed.

Artifacts: `src/speech_aware_evidence_acquisition/analysis/m11_operating_point_sweep.py` (new,
standalone; imports the frozen reader's own parsers and edits no existing module) and
`docs/checks/speech-aware-evidence-acquisition/2026-08-23-m11-operating-point-sweep/sweep.json`
(sha256 `b9edfa34aa563d366d6de5c0a9374b5d41182c131c419b518fd5c9cbc5be05f8`).

Zero-contact proof: resident llama-server PID 607's log
`/home/chao/runs/services/SAEA-SN-Q4KM-NP16-HOT-PREFIX-ZCOPY-20260823T111700Z/server.log` measured
**1,117,739 bytes / sha256 `177b972d81bcf02cf26dbcacfc8cd9f6ca81b1ae695395022923da1faa557e02` before
and after**, with the process continuously resident across the whole sweep.

## 1. Inputs

| split | queries | source | primary | decisions sha256 |
|---|---|---|---|---|
| `EVIDENCE-E108` | 108 | `SAEA-SN-EVIDENCE-E108-K1M11-…-ZCOPY/attempt-20260823T175901Z-e108zc` (M11, k=3) | 92/108 | `4e9ebefc…6f99` |
| `EFFECT-C108` | 108 | `SAEA-SN-EFFECT-C108-K1M6-GROUNDED-SCHEMA-V3/attempt-20260822T141000Z-12i001` (M6, k=3) | 90/108 | `ce4d5822…4cc78` |

The two rosters are **disjoint** (zero shared sample ids); union split identity hash
`76e7435630070e2bd9f089033e5e2598f7fc4eb0aa111794e7a8b7e5a5320645`. E108 trajectories are
reconstructed by the frozen reader's own
`core.driver.speech_native._parse_m11_adaptive_evidence_gap_trajectory` against the hash-pinned
binding and decision graph. C108 rows are reduced through the reader's own inline M6 field contract
(`agent_vote_key_ids[0]` = speech-only primary, `agent_steps[1].top_key_ids` = speech-only retrieval,
`verifier_scores` = per-candidate compatibility) with the reader's deterministic
`key_id → value_label` mapping; no scorer is reimplemented.

**Prior source, stated exactly.** The label prior is the model-free KB-BUILD v1 **size-full**
snapshot (receipt `docs/receipts/knowledge/slurp-kb-size-full.json`, snapshot sha256
`e27b2745…a51b57`), specifically its eighteen `facet:label:scenario:<label>` facets, whose
representation text carries the TRAIN utterance count behind each scenario (11,514 total; `calendar`
1688 … `cooking` 211). This is the only landed ValueBundle-style prior that is TRAIN-built,
hash-pinned, and keyed by the exact eighteen value labels this task routes over. The per-intent
`facet:prior:*` facets in the same snapshot are **entity-type priors conditioned on an intent that is
not observable at decision time** on this surface, so they are not usable as a label prior here and
were not used.

**Structural limitation that shapes everything below.** The logged retrieval channel is a **RANK, not
a score**. The frozen core emits an ordered key-id list; no cosine, logit, or embedding similarity
was ever recorded on this surface (`verifier_scores` is `{}` on every E108 row). Every "rank weight"
in this sweep is therefore a synthetic decay over rank position, not a recovered continuous
retrieval score. A DEV-100 campaign that wants a real `cos`-driven α-blend must first land the
text-embedding pass; this sweep cannot stand in for it.

## 2. Boundary firing-rate curve (E108)

Termination histogram over the 108 logged trajectories: `complete-consistent-state` 94,
`pair-boundary-compared` **7**, `no-registered-pair-boundary` 7, mechanism failures 0.

| condition | legality | would-fire | rate | actually flown | reachable only by new contacts |
|---|---|---|---|---|---|
| **C0** registered (disagreement ∧ registered pair boundary) | runtime-legal (as flown) | **7** | 6.5% | 7 | 0 |
| **C1** drop the stable-edge-support floor (disagreement, boundary registration ignored) | legal, needs new graph edges | **14** | 13.0% | 7 | 7 |
| **C2** primary ≠ retrieval rank-1 (only 2 contacts needed) | runtime-legal | **14** | 13.0% | 7 | 7 |
| **C3** primary ≠ candidate-action state | runtime-legal | **11** | 10.2% | 7 | 4 |
| **C4** retrieval rank-1 ≠ candidate-action state | runtime-legal | **5** | 4.6% | 2 | 3 |
| **C5** any pairwise disagreement (C2 ∪ C3 ∪ C4) | legal, needs new graph edges | **14** | 13.0% | 7 | 7 |
| **C6** always fire | runtime-legal, maximal cost | **108** | 100% | 7 | 101 |
| *D1* gold not at rank 1 | **ORACLE-DIAGNOSTIC, not runtime-legal** | *20* | *18.5%* | 5 | 15 |
| *D2* gold ≠ primary | **ORACLE-DIAGNOSTIC, not runtime-legal** | *16* | *14.8%* | 3 | 13 |

### 2.1 The finding that matters most in this table

**No runtime-legal relaxation reaches the registered support floor.** The support gate demands
`adaptive_boundary_query_count ≥ 18`. The union of every disagreement-based condition (C5) tops out
at **14**. The loop's three votes are unanimous on **94/108** queries, so the only way to reach 18 on
a 108-query surface is to fire unconditionally (C6) or to have a gap detector strictly better than
any logged signal. The 18-query floor was never reachable on E108 by tuning the firing rule — it is a
**sample-size and vote-concordance** constraint, not a threshold-tuning one.

Corollary: the 7 `no-registered-pair-boundary` queries are the exact cost of the stable-edge-support
floor. The loop DID detect a candidate disagreement on 14 queries; the frozen decision graph carried
a boundary for only 7 of them. Doubling graph edge coverage would double firing to 14 — still 4 short
of 18, and with **no recorded outcome for the 7 new firings**.

### 2.2 Precision recap of the 7 that actually fired

The registered read reports 4 attributable transitions, **4 helpful / 0 harmful**, 3 unresolved.
Replaying the logged trajectories sharpens what that means:

| # | primary | rank-1 | action state | ab / ba | stable | gold | primary correct? |
|---|---|---|---|---|---|---|---|
| 1 | social | calendar | calendar | calendar / social | — (unstable) | **calendar** | no |
| 2 | news | calendar | calendar | calendar / news | — (unstable) | **calendar** | no |
| 3 | weather | qa | datetime | datetime / weather | — (unstable) | recommendation | no |
| 4 | social | alarm | alarm | social / social | social | social | yes |
| 5 | social | alarm | alarm | social / social | social | social | yes |
| 6 | social | datetime | datetime | social / social | social | social | yes |
| 7 | transport | calendar | alarm | transport / transport | transport | transport | yes |

The mechanism's observed value on E108 was **purely defensive**: all 4 helpful transitions are cases
where the acquisition **confirmed an already-correct primary** against a challenger. It **repaired
zero wrong primaries**. On all 3 queries where a repair was actually available, the pairwise
comparison came back **order-unstable** (ab ≠ ba) and was discarded — which is exactly the
"unresolved 3".

**And the two repairs it failed to make are precisely the two the free α-blend layer makes**
(§4.4). Fourteen extra contacts (7 firings × 2 calls) bought four confirmations of decisions that
were already right, and missed both repairs that a zero-extra-contact decision layer recovers.

## 3. Within-logged-k retrieval curves

| depth | E108 gold-reachable | E108 rate | C108 gold-reachable | C108 rate |
|---|---|---|---|---|
| top-1 | 88 / 108 | 81.5% | 92 / 108 | 85.2% |
| top-2 | 94 / 108 | 87.0% | 98 / 108 | 90.7% |
| top-3 (logged depth) | **96 / 108** | 88.9% | **99 / 108** | 91.7% |
| top-3 ∪ {primary} | **99 / 108** | 91.7% | **99 / 108** | 91.7% |

The registered E108 top-k reachability of **96/108 sits exactly at the end of the logged curve** — it
is the k=3 point, not a plateau. The curve is still climbing (+6 from k=1 to k=2, +2 from k=2 to
k=3), so **rerank depth is an unswept knob with visible headroom**: the sweep cannot say what k=5 or
k=10 would give, because those keys were never returned.

**Union reachability is the honest ceiling of any blend-layer-only controller: 99/108 on both
splits.** A decision layer that only re-ranks logged candidates can never exceed it.

Unreachable queries (gold outside top-3 ∪ {primary}): 9 on each split. Gold-label distribution only,
no deep dive:

- E108 (9): `general` 3, `recommendation` 2, `music` 1, `news` 1, `social` 1, `weather` 1.
- C108 (9): `general` 3, `calendar` 2, `iot` 1, `music` 1, `news` 1, `qa` 1.

`general` is the largest unreachable class on both splits — a cross-split-consistent retrieval blind
spot, and the only scenario-level signal in this section strong enough to act on.

(The E108 "12 unreachable" figure in the read verdict is `108 − 96`, i.e. the top-3-only measure;
folding the primary back in leaves 9.)

## 4. C3 α-blend offline replay — the headline

Decision layer replayed per the frozen baseline form: fused label score built from the **logged**
retrieval ranking × rank-weight variant × ValueBundle-style label prior × logged agreement evidence,
normalized over `top-3 ∪ {primary}`, then

```
final = argmax_label [ α · normalized_fused(label) + (1 − α) · 1[label == primary] ]
```

with an optional admission threshold τ (retain primary when `max normalized_fused < τ`).
Grid: α ∈ {0.0 … 1.0} × rank-weight ∈ {rrf, linear, exp} × evidence variant ∈ {rank-only,
rank+prior, rank+agreement, rank+prior+agreement} × τ ∈ {off, 0.5} = **264 cells, each scored on both
splits.**

Agreement is the second, evidence-conditioned endorsement of a retrieved candidate: on E108 the
candidate-action-state key (plus a stable boundary key where one was acquired); on C108 every
candidate the grounded verifier marked `compatible`. **These two channels differ in kind** — E108
endorses exactly one key, C108 may endorse several — so the agreement axis is only loosely
comparable across splits. That asymmetry is recorded in the JSON and is a real weakness of the
two-split design here.

### 4.1 α curves (correct counts, E108 / C108; primary is 92 / 90)

τ = off:

| rank weight | variant | α=0.0–0.5 | 0.6 | 0.7 | 0.8 | 0.9 | 1.0 |
|---|---|---|---|---|---|---|---|
| rrf | rank-only | 92/90 | 92/90 | 89/91 | 88/92 | 88/92 | 88/92 |
| rrf | rank+prior | 92/90 | **93/91** | 88/90 | 76/84 | 61/74 | 47/61 |
| rrf | rank+agreement | 92/90 | 89/91 | 91/92 | 91/92 | 91/92 | 91/92 |
| rrf | rank+prior+agreement | 92/90 | **94/91** | 91/91 | 90/89 | 83/82 | 79/76 |
| linear | rank-only | 92/90 | 92/90 | 89/91 | 89/91 | 88/92 | 88/92 |
| linear | rank+prior | 92/90 | **93/91** | 81/86 | 69/79 | 56/65 | 41/52 |
| linear | rank+agreement | 92/90 | 92/90 | 91/92 | 91/92 | 91/92 | 91/92 |
| linear | rank+prior+agreement | 92/90 | **94/91** | 91/89 | 83/83 | 80/76 | 74/69 |
| exp | rank-only | 92/90 | 92/90 | 89/91 | 88/92 | 88/92 | 88/92 |
| exp | rank+prior | 92/90 | **93/91** | 90/91 | 81/86 | 77/86 | 68/78 |
| exp | rank+agreement | 92/90 | 89/91 | 91/92 | 91/92 | 88/92 | 88/92 |
| exp | rank+prior+agreement | 92/90 | 92/91 | 90/91 | 90/89 | 90/90 | 82/83 |

τ = 0.5 reproduces the same α ≤ 0.6 column exactly and damps the far-α collapse (e.g. rrf
rank+prior at α=1.0 goes 47/61 → 68/78). It **never changes any best cell.**

Two structural facts: **(a) the blend is completely inert for α ≤ 0.5** — with three candidates and a
normalized fused score, the primary's `(1 − α)` term dominates until α crosses the switching
threshold; **(b) at α = 1.0 with rank-only weights the blend degenerates to retrieval rank-1**, which
is **88 on E108 (−4) and 92 on C108 (+2)** — opposite signs. A single-split reading of that cell
would have concluded the exact opposite of the truth, which is precisely why best-by-worst-split is
the selection rule.

### 4.2 Best cells

Selection is **best-cell-by-worst-split on per-split DELTA against that split's own primary**, never
best-by-single-split and never on raw accuracy (the two splits have different primaries, so raw
worst-accuracy silently rewards a cell that damages E108 while lifting C108).

| ranking | cell | E108 | C108 |
|---|---|---|---|
| best on E108 alone | `rrf \| rank+prior+agreement \| τ=off \| α=0.6` | **94** (+2) | 91 (+1) |
| best on C108 alone | `rrf \| rank+agreement \| τ=off \| α=0.7` | 91 (**−1**) | **92** (+2) |
| **best by worst split** | `linear \| rank+prior+agreement \| τ=0.5 \| α=0.6` | **94** (+2, 2 W→C, **0 C→W**) | **91** (+1, 1 W→C, **0 C→W**) |

The best-by-worst-split winner in the JSON is the `linear` variant only because the tie-break sorts
cell ids lexicographically. `rrf | rank+prior+agreement | τ=0.5 | α=0.6` and
`rrf | rank+prior+agreement | τ=off | α=0.6` produce the **identical** 94/91 with the identical six
changed decisions; §4.3 shows the `rrf` shape holds the wider plateau, which is why §6 recommends it.

**10 of 264 cells beat the primary on BOTH splits.** All ten sit at α = 0.6 and **all ten require the
prior**. `rank-only` and `rank+agreement` never produce a both-splits win at any α.

### 4.3 Is the win a plateau or a knife edge?

A starting knob read off a single 0.1-grid point is worthless. A supplementary 0.01-step scan of
α ∈ [0.50, 0.90] (same model-free replay) settles it:

| combination | contiguous both-splits-positive α interval | width |
|---|---|---|
| `rrf \| rank+prior+agreement` (τ off and τ=0.5) | **[0.54, 0.65]** | 0.11 |
| `exp \| rank+prior` | [0.55, 0.65] | 0.10 |
| `linear \| rank+prior+agreement` | [0.55, 0.65] | 0.10 |
| `rrf \| rank+prior` | [0.58, 0.66] | 0.08 |
| `exp \| rank+prior+agreement` | [0.53, 0.58] | 0.05 |
| `linear \| rank+prior` | [0.60, 0.63] | 0.03 |
| all 4 `rank-only` / `rank+agreement` combinations | **none** | 0 |

12 of 24 combinations have any both-splits-positive α; every one of them uses the prior.
`rrf | rank+prior+agreement` holds **+2/+1 flat across α ∈ [0.55, 0.65]** (eleven consecutive
0.01 steps) — a genuine, if narrow, operating plateau, not a knife edge. Outside it the cell falls to
+0/+1 at 0.66 and to −1/+1 at 0.70.

### 4.4 What the recommended cell actually changes (all 6 decisions)

| split | outcome | primary → chosen | gold | logged top-3 | endorsed |
|---|---|---|---|---|---|
| E108 | **wrong→correct** | social → calendar | calendar | calendar, social, alarm | calendar |
| E108 | **wrong→correct** | news → calendar | calendar | calendar, news, alarm | calendar |
| E108 | wrong→wrong | recommendation → qa | general | qa, recommendation, alarm | qa |
| E108 | wrong→wrong | alarm → qa | recommendation | qa, datetime, iot | qa |
| E108 | wrong→wrong | alarm → qa | weather | qa, datetime, general | qa |
| C108 | **wrong→correct** | recommendation → calendar | calendar | calendar, datetime, general | calendar |

**Zero correct-to-wrong on either split.** Every override fires only where the primary was already
wrong, rank-1 disagrees with it, the second opinion endorses rank-1, and rank-1 carries a high train
prior. The two E108 repairs are **exactly the two queries the pair-boundary acquisition failed to
resolve** (§2.2 rows 1–2) — recovered here for zero extra contacts.

**Read the mechanism honestly.** All three gains move to `calendar` (1688 TRAIN utterances, the
largest scenario); all three no-ops move to `qa` (1183, the third largest). The prior is functioning
as a *trust-the-large-classes* margin modifier. On these deliberately 6-per-scenario **balanced**
splits that is a hard test — a skewed prior on a balanced split should hurt on average, and it does
above α ≈ 0.66, collapsing to 47/61 at α=1.0. It helps in the plateau only because it modulates the
switching margin rather than the ranking. **On a naturally-distributed DEV-100 sample the prior's
behaviour will differ and must be re-fit, not carried over as a constant.**

## 5. Sensitivity — which knob moves accuracy at all

| knob | moves best worst-split accuracy? | spread across values |
|---|---|---|
| **α** | **yes** | 0.0093 (= 1 query); inert ≤ 0.5, best at 0.6, degrades above |
| **evidence variant** | **yes** | 0.0093; `rank-only` best-worst-split caps at 90/108, prior/agreement variants reach 91/108 |
| rank weight (rrf / linear / exp) | **no** | 0.0 — changes the plateau width and the far-α decay shape, never the best cell |
| admission τ (off / 0.5) | **no** | 0.0 — identical results throughout the plateau; only damps far-α collapse |

Answers to the three questions §7.2 asks of a sweep:

1. **Which knob moves accuracy at all?** Only α and the evidence composition. Rank-weight shape and
   the admission threshold are inert at the operating point. τ earns its place as a *safety rail*
   (it caps the damage if α drifts high), not as a tuning knob.
2. **Does ANY cell beat primary on BOTH splits?** **Yes — 10 of 264**, all at α = 0.6, all requiring
   the prior, best worst-split delta **+1** (E108 +2 / C108 +1) with **zero correct-to-wrong**.
3. **The honest ceiling of blend-layer-only improvement.** Union reachability is **99/108 on both
   splits**: +7 over the E108 primary, +9 over the C108 primary. The recommended cell captures
   **2 of the 7** available on E108 and **1 of the 9** on C108. Note that the recommended cell's
   E108 score of 94 exactly equals the registered diagnostic action-family oracle of 94 — the free
   blend layer already reaches what the whole M11 action family could reach at best, and 5 reachable
   queries remain untouched by either. **The gap to the ceiling is a retrieval-ranking problem, not
   a blend-weight problem**: the blend can only reorder what retrieval already returned.

## 6. Recommendation — DEV-100 starting knobs

This is the positive outcome, with its scope stated: the blend layer **does** beat the primary on
both exposed splits, on a plateau rather than a point, with zero observed harm. It does **not**
license a promotion claim, and these knobs are **starting values to be re-fit on DEV-100**, not
frozen constants.

| knob | starting value | why |
|---|---|---|
| **α (blend weight)** | **0.60** | centre of the widest both-splits-positive plateau [0.54, 0.65]; +2/+1 flat across [0.55, 0.65] |
| **rank weight** | **rrf**, `w(r) = 1/(1+r)` | widest plateau; the axis is provably inert for the best cell, so pick the most robust shape |
| **evidence composition** | **rank + prior + agreement** | the only family with a both-splits win; agreement adds +1 on E108 over rank+prior and widens the plateau |
| **label prior** | KB-BUILD **size-full** TRAIN scenario counts | the only landed TRAIN-built prior keyed to the 18 routed labels; **re-fit on DEV-100, do not carry the constant** |
| **admission τ** | **0.5, kept on** | inert at the operating point but caps the far-α collapse; a free safety rail |
| **top-k / rerank depth** | **raise above 3 — first knob to sweep** | the recall curve is still climbing at the logged depth; union reachability 99/108 is the blend ceiling and it is set by retrieval, not by α |
| **boundary firing condition** | **do not carry M11's pair-boundary stage into DEV-100 as flown** | 14 contacts bought 4 confirmations of already-correct primaries, repaired nothing, and missed both repairs the free blend recovers |

**Contact accounting for the recommendation.** The recommended layer needs contacts 1 (primary),
2 (retrieval) and 3 (candidate-action state, for the agreement term) — i.e. exactly the M11 base
loop, with **zero extra contacts**. Dropping the boundary stage takes E108 from 338 to 324 contacts.
Dropping the agreement term as well gives a 2-contact loop (216 contacts) at `rank+prior`, α ≈ 0.6,
scoring 93/91 (+1/+1). So **contact 3 buys +1 on E108 and +0 on C108 for a 50% contact increase** —
a real DEV-100 cost/benefit decision, and one this sweep can only pose, not settle. (The C108 side of
that trade is not comparable: its agreement channel is the M6 verifier, which costs four more
contacts of its own.)

## 7. What this sweep cannot tell us

- **Anything about the 101 queries that never fired an acquisition.** The relaxed firing conditions
  in §2 are counts. The model was never asked; the outcomes do not exist and are not imputed.
- **Anything about k > 3.** Keys beyond rank 3 were never returned. The rerank-depth recommendation
  is a direction, not a measured gain.
- **Anything about a real similarity-driven α-blend.** No retrieval score was ever logged. The
  text-embedding pass is a prerequisite before the α-blend can be driven by anything but rank
  position.
- **Anything confirmatory.** Both splits are TRAIN discovery surfaces that have been read before.
  The two-split agreement here is a consistency check between two already-exposed samples, not
  validation. The DEV-100 campaign remains the place where these knobs are actually tested, per
  §7.2's requirement of multi-round iteration to convergence, and §7.3's rule that no expansion
  happens without a stable gain from small-scale iteration.
- **Anything about the agreement axis across splits.** E108 and C108 carry structurally different
  endorsement channels; the axis is only loosely comparable and the +1 attributed to it rests on the
  E108 side alone.
