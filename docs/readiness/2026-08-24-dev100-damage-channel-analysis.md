# DEV-100 damage-channel dissection — offline knob replay (iteration-tier design input)

Date: 2026-08-24. Status: **DESIGN INPUT — no verdict, no knob selected, no round-3 flight
authorized.** Profile: `model-free-check`. Exposure row
`SAEA-SN-MF-DEV100-DAMAGE-CHANNEL-ANALYSIS` (registered before any computation; **0** frozen-core
contacts, **0** embedding-tool contacts, **0** audio seconds, **0.0** GPU hours).

This document reports what the sealed rounds already contain. It selects nothing. The round-3
knob decision, and whether a round 3 flies at all, belong to the coordinator and the owner.

## 1. Authority and scope

- Owner discipline `2026-08-23-knowledge-plane-baseline-rulings.md` §7.2 (iterate on exposed
  data before concluding); the DEV-100 campaign preregistration
  `2026-08-23-dev100-campaign-preregistration.md` and its round discipline.
- Consumed: the three sealed round reports
  (`docs/checks/speech-aware-evidence-acquisition/2026-08-24-dev100-round{0,1,2}/round*-report.json`),
  the round-2 durable trace / outputs / query vectors / per-sample scores under
  `runs/SAEA-DEV100-KB-ALPHA-BLEND-CAMPAIGN/attempt-20260824T153842Z-dev100r2`, the pinned TRAIN
  snapshot `e27b2745…a51b57`, and its landed content-facet NPZ `0bcb955a…21c72`.
- TRAIN **value** vectors stay SEALED and were not opened. Devel gold is read scoring-side only,
  for the same 100 samples whose gold was lawfully opened at each round seal.
- The resident decoder unit `saea-np8-dev100-r6-base` was never contacted: its `server.log`
  measured **592,082 bytes / SHA-256 `0c3c0dd4b4fa2a9925d13f3a8224df50fcfd5ee55f1b4cd62e1b796dff69838b`**
  before the analysis and **byte- and hash-identical** after it, with the unit still `active`.
- Tool: `src/speech_aware_evidence_acquisition/analysis/dev100_damage_channel_analysis.py`,
  which imports and re-runs `rails.kb_policy`'s own pure functions. `rails/`, `core/`, and the
  round launchers are untouched.

## 2. Replay fidelity — the analysis is exact, not approximate

The flown supply decision is a deterministic function of (query vector, facet vectors, snapshot,
knobs), and all four are landed. Replaying `multidim_recall` → the registered ranker → the
registered fuser reproduces, for **100/100** samples:

- the round-2 SUPPLY channel's `selected_value_ids`, exactly; and
- the flown `winner_label` in `round2-outputs.jsonl`, exactly.

Both gates pass with zero mismatches, so every number below is arithmetic over the flown
trajectories rather than a model of them.

## 3. What the counterfactuals can and cannot say

Changing a knob changes what is SUPPLIED; the frozen core's answer to a *changed* evidence block
is not knowable without a model contact. Every counterfactual outcome is therefore bucketed:

| bucket | meaning | outcome |
|---|---|---|
| `revert_to_direct` | retain-primary fires; the logged direct-decode response becomes final | **known** offline |
| `dispatch_same_supply` | evidence dispatches with byte-identical values, so the evidence prompt is byte-identical and the logged evidence response stands | **known** offline |
| `dispatch_changed_supply` | evidence dispatches with a different evidence block | **unknown** offline — counted, never scored |

No counterfactual accuracy is asserted as a measured flight result.

## 4. Two structural facts that bound every registered knob

**4.1 The recall geometry makes the rank-weight family inert.** Every facet in this snapshot
carries exactly one dimension, so each recalled candidate is admitted under exactly one
dimension and the ranker's agreement term is the *same constant* `1/dims_total` (measured:
`dims_total = 3` on 100/100 samples, and `0` facets recalled under more than one dimension).
Content facets carry `max_prior_mass = 0.0`; label/prior facets carry no cosine at all and so
can never pass the fuser's percept-admission test — measured, `0` label/prior facets ever reach
the top-`m`. Consequently the ranker's content ordering **is identically the cosine ordering for
any weight vector with `w_cos > 0`** (verified on 100/100 samples). `w_cos`/`w_prior`/`w_agree`
cannot reorder a single candidate, cannot change a single admitted facet, and cannot move a
single supplied value on this split.

**4.2 The direct-label term has never been live.** `KbAlphaBlendController` blends `(1 - alpha)`
onto the label facet `default_label_normalizer` recovers from the direct-decode text, and that
normalizer matches a label facet's **representation** as a substring. The snapshot's
representations are prose sentences (`"Intent 'alarm_query' (scenario='alarm', action='query');
130 TRAIN utterances in this snapshot."`) while the task contract's answers are compact JSON, so
the match can never fire. Measured over the round-2 flight: the flown normalizer recovered a
direct label on **0/100** samples (and an evidence label on 0/100).

The consequence is exact: with the direct term dead, the blend reduces to
`argmax(alpha * fused_label_scores)`, whose argmax is **invariant in `alpha`**; retain-primary
can never fire. This is precisely what all three sealed rounds recorded
(`retain_primary_samples = 0`, evidence dispatched 100/100) — and it means the round-2 α move
0.60 → 0.55 changed no trajectory at all. The observed +2 is attributable to the documented
8-slot direct-decode byte instability, not to the α mechanism.

For contrast, the answers' **own parsed** scenario/action names a snapshot label facet on
**64/100** direct answers and **99/100** evidence answers; a further **5** direct answers name a
real TRAIN intent only with the two fields exchanged, and **0** fail to parse.

## 5. The 11-sample damage list, dissected

All eleven share one anatomy: the direct answer is correct, the nearest content facet carries a
**confusable sibling intent**, the fused distribution therefore concentrates on that sibling, and
the correct label — having no admitted supporting facet — scores exactly `0` in the blend.

| sample (`slurp:devel:…`) | gold | direct | evidence (final) | top-1 facet target | top-1 cos | admitted | fused mass on winner | blend margin over the correct label at α .55 | gold facet's full-recall position | partition |
|---|---|---|---|---|---|---|---|---|---|---|
| `000090:audio-1498567209` | takeaway_query | takeaway_query ✔ | takeaway_order ✘ | cooking_recipe | 0.8412 | 5/5 | 0.5112 | 0.2812 | 7 | recall-limited |
| `001227:audio-1490104218` | datetime_query | datetime_query ✔ | recommendation_events ✘ | recommendation_events | 0.8359 | 5/5 | 0.5113 | 0.2812 | 82 | recall-limited |
| `001791:audio-1502195360` | music_query | music_query ✔ | play_music ✘ | play_music | 0.9014 | 5/5 | 1.0000 | 0.5500 | 19 | recall-limited |
| `003202:audio-1495733953-headset` | music_likeness | music_likeness ✔ | play_music ✘ | play_music | 0.8307 | 5/5 | 1.0000 | 0.5500 | 14 | recall-limited |
| `003443:audio-1501776590` | datetime_query | datetime_query ✔ | calendar_query ✘ | recommendation_events | 0.8359 | 5/5 | 0.5113 | 0.2812 | 82 | recall-limited |
| `003705:audio-1490194357` | datetime_query | datetime_query ✔ | calendar_query ✘ | recommendation_events | 0.8359 | 5/5 | 0.5113 | 0.2812 | 82 | recall-limited |
| `007738:audio-1489153308` | calendar_remove | calendar_remove ✔ | lists_remove ✘ | lists_remove | 0.8558 | 5/5 | 1.0000 | 0.5500 | 41 | recall-limited |
| `012185:audio-1499244805` | transport_query | transport_query ✔ | transport_traffic ✘ | transport_traffic | 0.8392 | 5/5 | 1.0000 | 0.5500 | 18 | recall-limited |
| `012625:audio-1494417974` | transport_query | transport_query ✔ | transport_traffic ✘ | transport_traffic | 0.6898 | 5/5 | 0.3373 | 0.1855 | 6 | recall-limited |
| `015630:audio-1490967842` | social_query | social_query ✔ | recommendation_events ✘ | social_post | 0.7956 | 5/5 | 0.3386 | 0.1862 | 4 | **reweight-addressable** |
| `016699:audio-1499688493-headset` | email_sendemail | email_sendemail ✔ | email_query ✘ | email_query | 0.8346 | 5/5 | 1.0000 | 0.5500 | 26 | recall-limited |

Reading the table: "blend margin over the correct label" is the fused winner's blended score
minus the correct label's, at the flown α = 0.55. The correct label's blended score is `0.0000`
on all eleven — it is not merely out-ranked, it is **absent from the blend**, because (a) no
admitted facet supports it and (b) the direct term that would have carried it is dead (§4.2).

**Gold evidence supply, damage group: 0/11.** On no damaged sample does the supplied evidence
carry the gold `task_target` at all.

## 6. Partition of the 11: reweight-addressable vs recall-limited

- **reweight-addressable — 1**: `015630:audio-1490967842`. Its gold-bearing facet is at
  full-recall position **4**, is inside the logged top-5, and **is percept-admitted** — yet it is
  not supplied, because the fuser's coverage floor `l = 3` filled all three target slots with
  higher-scoring siblings. A *fusion* knob (`l`) reaches this one; a *rank-weight* knob cannot
  (§4.1).
- **recall-limited — 10**: gold-bearing facet at full-recall positions
  **6, 7, 14, 18, 19, 26, 41, 82, 82, 82**. None is inside the logged top-5. Only wider recall
  or better keys reach these.
- **absent from the KB — 0**: every gold intent is represented somewhere in the snapshot.

Because the exact cosine ordering over all 11,514 content facets is computable from the logged
query vectors, the `top_k 5 → 8` question is answered directly rather than by proxy: widening
recall to 8 would newly reach the gold facet on exactly **2** of the 11 (positions 6 and 7), and
even then only if the fuser's `top_m` widened with it — see §7.

## 7. Counterfactual knob replay

Damage group = the 11; repair group = the 28. "chg" = trajectories whose supply or dispatch
decision changes at all. "gold supplied" = the necessary (never sufficient) condition that the
supplied evidence carries the gold `task_target`.

| setting | chg | damage buckets | damage gold supplied | damage known-correct | repair buckets | repair known-correct | projected DEV-100 | unknown |
|---|---|---|---|---|---|---|---|---|
| baseline round 2 (control) | 0 | same-supply 11 | 0/11 | 0/11 | same-supply 28 | 28/28 | 65 (control) | 0 |
| `w_prior → 0` (.5/0/.2) | **0** | same-supply 11 | 0/11 | **0/11** | same-supply 28 | **28/28** | 65 | 0 |
| `w_agree ↑` (.5/.1/.4) | **0** | same-supply 11 | 0/11 | **0/11** | same-supply 28 | **28/28** | 65 | 0 |
| `w_agree ↑` (.4/.2/.4) | **0** | same-supply 11 | 0/11 | **0/11** | same-supply 28 | **28/28** | 65 | 0 |
| α .50 | **0** | same-supply 11 | 0/11 | **0/11** | same-supply 28 | **28/28** | 65 | 0 |
| α .45 | **0** | same-supply 11 | 0/11 | **0/11** | same-supply 28 | **28/28** | 65 | 0 |
| `top_k 8` | **0** | same-supply 11 | 0/11 | **0/11** | same-supply 28 | **28/28** | 65 | 0 |
| `top_k 8` + `m 8` † | 34 | changed 5, same 6 | 1/11 | — | changed 11, same 17 | — | not knowable | 34 |
| `l 3 → 4` † | 5 | changed 1, same 10 | 1/11 | — | same-supply 28 | 28/28 | not knowable | 5 |
| `top_k 8` + `m 8` + `l 4` † | 38 | changed 6, same 5 | 3/11 | — | changed 11, same 17 | — | not knowable | 38 |
| **label-identity repair, α .60/.55/.50** | 54 | revert 6, same 5 | 0/11 | **6/11** | revert 3, same 25 | **27/28** | **71** (exact) | **0** |
| **label-identity repair, α .45/.40/.30** | 64 | revert 11, same 0 | 0/11 | **11/11** | revert 6, same 22 | **24/28** | **74** (exact) | **0** |

† not a single registered knob — measured only to show what a recall-side or fusion-side move
would require. These settings change the evidence block, so their outcomes are not knowable
offline; only the *gold-supplied* precondition is reportable, and it stays at 1–3 of 11.

**Answering the brief's questions directly:**

- **(2a) `w_prior → 0`**: **0 of the 11 flip back correct; 0 of the 28 repairs lost.** Not a
  near-miss — zero trajectories change, because content facets carry zero prior mass (§4.1).
- **(2b) `w_agree ↑`**: **0 flip; 0 lost**, at both `.5/.1/.4` and `.4/.2/.4`, for the same
  structural reason — agreement is a constant added to every candidate.
- **(2c) `top_k 8`**: fully replayed on the supply side (the logged query vectors make recall at
  any `k` exact): **0 trajectories change**, because the fuser's `top_m = 5` re-truncates the
  wider candidate pool before admission. The reachability partition stands as §6: **1 of 11
  reweight-addressable, 10 recall-limited, 0 absent from the KB.**
- **(2d) α .50 / .45**: **0 flip; 0 lost.** α is mathematically inert while the direct term is
  dead (§4.2); there is no damage/repair tradeoff curve to plot because the curve is flat.

## 8. The repair group's anatomy — what actually makes the 28 work

- The supplied evidence carries the gold `task_target` on **28/28**.
- The gold-bearing facet is the **#1** cosine hit on **25/28**; the remaining three sit at
  positions 2, 3, 4. (Damage group, for contrast: **0/11** at #1; positions 4–82.)
- The direct answer was wrong on **26/28** — evidence is doing real work, not riding luck.

So the win mechanism is nearest-neighbour retrieval success, and the damage mechanism is
nearest-neighbour retrieval *failure onto a confusable sibling intent*. They are the same
mechanism with opposite outcomes. Any candidate change must be checked against this: a knob that
suppresses evidence to protect the direct answer necessarily risks the 26 repairs that depend on
evidence overriding a wrong direct answer.

## 9. Design input for round 3

**Among the four registered dev-legal knobs, none can address the 11.** This is not a weak
result — it is proved twice over: (a) directly, by exact replay (0 changed trajectories on every
setting in the first block of §7), and (b) structurally, by the recall geometry (§4.1) and the
dead direct term (§4.2). Declaring the damage channel "structural and untouchable" would
therefore be *half* right: it is untouchable **by those knobs**, but the analysis also locates a
specific, mechanism-bearing cause with a fully-replayable projection.

**The single change the evidence points at is the label-identity binding**: recover the
direct-decode label from the answer's OWN parsed `scenario`/`action` (the model's own output;
gold is never consulted) instead of matching a prose facet representation as a substring. This
restores the `(1 - alpha)` protect-direct term the baseline form was designed around and has
never actually had.

Its projection is **exact, with zero unknowns**, because the repair changes no supplied value —
recall/rank/fuse are untouched — so every trajectory ends on a response already in the round-2
trace:

| projected ledger, repair at the flown α = 0.55 | |
|---|---|
| DEV-100 `scenario_action_exact` | **71/100** (round 2: 65) |
| damage list healed | **6 of 11** — `000090`, `001227`, `003443`, `003705`, `012625`, `015630` |
| damage list still damaged | 5 of 11 — `001791`, `003202`, `007738`, `012185`, `016699` (fused mass 1.000 on the sibling, so `α·1.0 = .55 > 1−α = .45`) |
| repairs retained | **27 of 28** |
| repairs lost | 1 — `011819:audio--1505404383-headset` |
| additional W→C outside both groups | 1 — `015265:audio-1499689293-headset` |
| trajectories changed (retain-primary fires) | **54/100** |
| outcomes unknown offline | **0** |

Operational side effect worth pricing: retain-primary firing on 54/100 means the
`evidence-decode` contact is **not dispatched** on those samples — a round-3 BLEND arm would
cost roughly **146 frozen-core contacts instead of 200**, and the retain-primary counter would
be non-zero for the first time in the campaign.

At α .45 the same repair heals **11/11** (a fully-concentrated fused mass no longer out-scores
the direct term) at the cost of **4** repairs, projecting **74/100** (W→C 13, C→W 4). That is a
*second* variable, so it belongs to a later round, not to round 3 — but it is worth
pre-registering as the round-4 α re-sweep, because α only becomes a live knob once the repair
lands. Note the repair is flat across α ∈ [0.50, 0.60] and again across [0.30, 0.45]: the
mechanism is the repair, not the α position.

**Residual the repair does not reach.** The direct answer names a snapshot label facet on only
64/100 samples; 5 more name a real TRAIN intent with `scenario`/`action` exchanged, and 31 name a
pair that is not a TRAIN intent in either order. On those the direct term stays dead even after
the repair. Whether to widen the label vocabulary, tolerate the field swap, or tighten the answer
format is a separate design question and is **not** proposed here.

**Honest caveat on the projection.** "Exact" means exact *given the logged responses*. The
campaign has documented 8-slot direct-decode byte instability (cross-attempt direct agreement
75–79/100 across the three rounds), and the repair makes the direct-decode response final on 54
samples — so a flown round-3 arm re-decodes those directs under a different slot-concurrency
pattern and will carry that variance. The projection is a design input, not a predicted seal.

## 10. What this document does not do

It registers no round, selects no knob, authorizes no flight, and reaches no verdict on the
baseline form or on convergence. It adds one analysis module and this note. The round-3 decision
— including the option of declaring the campaign converged on gains alone and flying nothing —
remains with the coordinator and the owner.
