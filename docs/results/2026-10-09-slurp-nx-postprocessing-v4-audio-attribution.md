# R0.4 / E4 diagnostic: the Fold-A audio loss of v4 is ee10 firing on one under-sampled intent (audio_volume_mute, 4 of 45 TRAIN exemplars carry entities); the A2 losses are small-n scope and ti1 drops. A TRAIN-only guard is proposed; it changes the rule set, so v4 would need a fresh confirmation roster (DESCRIPTIVE)

Read 2026-10-09 by the analysis agent (Claude Opus 5.5) for the NX programme
(`docs/readiness/2026-10-09-slurp-nx-node-extreme-programme-v1.md`, round R0.4 / deliverable E4), as the
attribution the R0.4 read (`docs/results/2026-10-09-slurp-nx-postprocessing-v4-offline-read.md`, section 4)
says must be read before the owner locks. Worktree `/home/chao/saea-worktrees/fable-nx-postproc2`, branch
`fable/nx-postproc2`, based on master `3352ff480`.

The driver is `scripts/analysis/slurp_nx_postproc_v4_audio_attribution.py`. It imports the search driver
`scripts/analysis/slurp_nx_postproc_v4_search.py` unchanged and calls its `prepare_partA`, so every row of both
base columns is re-proved against the sealed official fields before anything is read. Reports are under
`$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-NX-POSTPROC-V4-AUDIO-ATTRIBUTION-V1/{a2,fold-a}/report.json`.

**What this is and is not.**

- It is a DIAGNOSTIC RE-READ of the two columns R0.4 already produced (A2 select, Fold-A confirm) under the
  same fixed five-rule list. Nothing is selected on Fold A.
- It is not a second confirmation. The search driver's write-once `confirm-fold-a/report.json` is untouched,
  and no guarded column is computed on Fold A.
- Guards are defined from TRAIN pool statistics (the R5 pool `size-pool-annotated-exemplars-minus-r01`,
  content `6eaa03ae...`) and the rule's own threshold, then read on A2 only.

**Contacts.** None: model, server, tokenizer, encoder, embedder, scorer, network, GPU and paid API are all 0.
Gold entered offline only, through the governed loader `data.slurp.load_slurp_split` (`devel`, `train`), via the
search driver's `load_gold`. The test split was not read. The reports hold rule ids, slot TYPE names, scenario
names, intent ids, counts and pp only. No utterance, transcript, filler, gold value or model output text is
printed or persisted.

**Status: DESCRIPTIVE.** These are development numbers (owner decisions 28 and 86). This note admits nothing.

## 0. Answer in five lines

1. **Fold-A audio (-17.47 pp, 60 rows) is entirely ee10.** ee10 emptied 5 audio rows. All 5 were harms, and they
   dropped 5 entities: device_type exact 2, time exact 2, time other 1. Its marginal on audio is **-26.36 pp**.
   The scope rule offsets **+8.89 pp** on 4 audio rows (4 saves; it dropped 3 spurious device_type and 1 spurious
   change_amount).
2. **One intent causes it.** Every ee10 drop in the audio scenario sits under the delivered intent
   `audio_volume_mute`. In the TRAIN pool only 4 of its 45 exemplars carry an entity: rate 8.9 %, Wilson 95 %
   upper bound 20.7 %. So the "< 10 %" statement is not resolved on 45 exemplars. Elsewhere on Fold A, ee10 fires
   only under `music_query`: 4 rows in the alarm and music scenarios, 3 saves and 1 harm. Pooled over Fold A,
   ee10's marginal is -0.27 pp; on A2 it is +0.06 pp.
3. **The other losses are spread and small.**
   - Fold-A social, cooking and takeaway: ti1 (-0.84, -3.05 and -0.94 marginal).
   - Fold-A email: scope (-0.45).
   - A2 iot: scope (-1.95 marginal; color_type exact 2).
   - A2 datetime: scope (-5.58; 2 of 9 rows, 2 partially matched date spans dropped).
   - A2 email: ti1 (-1.25; business_name exact 2), partly offset by scope (+1.38).
   - Each of these is 1 to 3 rows. Pooled, scope (+0.43 / +1.04) and ti1 (+0.26 / +0.32) stay positive on both
     pools.
4. **Proposed guard (TRAIN only): `ee-wilson` + `ti-expressible`.**
   - `ee-wilson`: ee10 fires only when the intent's pool entity rate is resolved below 10 %, meaning its Wilson
     95 % upper bound is < 0.10. In this pool that is `qa_maths` (0 of 66) only.
   - `ti-expressible`: ti1 fires only on an intent with >= 1 / 0.01 = 100 pool exemplars. Below that, "< 1 %"
     cannot differ from "never seen".
   - On A2: **+0.98 [+0.25, +1.71]**, equal-scenario **+0.23** (v4: +0.98 [+0.21, +1.74], equal-scenario +0.10).
     Against v4 it is -0.00 [-0.24, +0.26], with 9 rows scoring differently.
5. **The guard changes the rule set.** Under it, `audio_volume_mute` no longer fires ee10, and 32 of 59 pool
   intents no longer fire ti1. **Fold A cannot confirm it.** Fold A located the failure, so a guarded column needs
   a fresh confirmation read on a roster that has not seen this question. That read was not run.

## 1. Inputs and identities

| item | value |
| --- | --- |
| A2 | `SAEA-SLURP-STAGE3-COMP1B-DEV2000-ADDED-V1`, 1,000 rows / 913 utterance clusters, `slurp-slu-official`; base official SLU-F1 65.9327 (reproduced row by row) |
| Fold A | `SAEA-SLURP-STAGE3-COMP1B-FOLD-A-V1`, 1,080 rows / 1,080 clusters, `slurp-slu-official-train`; base official SLU-F1 63.6095 (reproduced row by row) |
| rule list | v4 = fx-article, fx-oclock, scope, ti1, ee10, in that order, after the sealed v3 column |
| reproduction of R0.4 | full v4 column: A2 **+0.9771 [+0.2116, +1.7443]**, Fold A **+1.6699 [+0.8143, +2.5003]**, equal-scenario +0.1044 / +0.9316; identical to the R0.4 reports |
| estimator | the search driver's paired whole-utterance cluster bootstrap (10,000 draws, seed 20260915) |
| per-scenario columns | "marginal" = delta(v4) - delta(v4 without the rule). "step" = the rule's increment in the fixed order; steps telescope to the v4 delta. "alone" = the rule by itself |
| entity classes | per edit, at the step the rule made it, against gold: exact (exactly matched), spurious (no gold counterpart), other (matched, not exact) |

## 2. Attribution: each loss scenario, by rule

### 2a. TRAIN Fold A (60 rows per scenario)

| scenario | v4 delta pp | rows edited | rule: marginal pp (step pp) | edits by rule, slot type and class | row effect |
| --- | ---: | ---: | --- | --- | --- |
| **audio** | **-17.47** | 9 | **ee10 -26.36 (-26.36)**; scope +3.70 (+8.89); fx/ti1 0 | ee10 drop: device_type exact 2, time exact 2, time other 1 (5 rows). Scope drop: device_type spurious 3, change_amount spurious 1 (4 rows) | ee10 5 harms; scope 4 saves |
| social | -0.84 | 8 | ti1 -0.84 (-0.84) | ti1 drop: business_type spurious 2, business_name spurious 1, food_type spurious 1, event_name exact 2 / other 1, date exact 1, relation other 1. fx-article rewrite: event_name other->other 1 | ti1 4 saves / 4 harms |
| cooking | -0.61 | 8 | ti1 -3.05 (-3.05); scope +2.38 (+2.44) | ti1 drop: meal_type exact 2, food_type exact 1. Scope drop: food_type spurious 5 | ti1 3 harms; scope 5 saves |
| takeaway | -0.60 | 6 | ti1 -0.94 (-0.94); scope 0.00 (+0.34) | ti1 drop: drink_type exact 1 / spurious 2, event_name exact 1, meal_type spurious 1, order_type other 1. Scope drop: time spurious 1 | ti1 1 save / 3 harms / 1 neutral; scope 1 save |
| email | -0.48 | 7 | scope -0.45 (-0.43); ti1 -0.05 (-0.05) | Scope drop: person exact 1 / spurious 2, event_name other 1, time other 1. ti1 drop: definition_word spurious 1, general_frequency exact 1, timeofday other 1 | scope 2 saves / 2 harms; ti1 1 / 1; scope+ti1 1 harm |

**Fold-A pooled marginals.** scope +1.04, ti1 +0.32, fx-article +0.17, fx-oclock +0.11, **ee10 -0.27**. ee10 is
the only member with a negative pooled marginal on Fold A.

**Where ee10 fires on Fold A.**

- **Audio:** 5 rows under `audio_volume_mute`, all harms.
- **Music:** 3 rows under `music_query` (2 saves, 1 harm), marginal -0.95. The drops are artist_name spurious 1,
  music_genre spurious 1 and music_genre exact 1.
- **Alarm:** 1 row under `music_query` (1 save), marginal +0.64. The drop is artist_name spurious 1.

### 2b. A2, the selection pool

| scenario | rows | v4 delta pp | rows edited | rule: marginal pp (step pp) | edits by rule, slot type and class | row effect |
| --- | ---: | ---: | ---: | --- | --- | --- |
| iot | 57 | -1.84 | 5 | **scope -1.95 (-1.14)**; ti1 0.00 (-0.70) | Scope drop: color_type exact 2, device_type spurious 1, house_place spurious 1. ti1 drop: change_amount other 1 | scope 2 saves / 2 harms; ti1 1 harm |
| datetime | 9 | -5.58 | 2 | **scope -5.58 (-5.58)** | Scope drop: date other 2 | scope 2 harms |
| email | 96 | -0.62 | 11 | **ti1 -1.25 (-1.25)**; scope +1.38 (+0.63) | ti1 drop: business_name exact 2, none spurious 1. Scope drop: person spurious 4 / exact 1 / other 1, email_address spurious 1, list_name exact 1 | ti1 2 harms / 1 neutral; scope 5 saves / 2 harms / 1 neutral |
| news | 20 | -0.16 | 2 | ti1 -2.29 (-2.29); scope +2.16 (+2.13) | ti1 drop: time other 1. Scope drop: news_topic spurious 1 | 1 harm / 1 save |

**A2 pooled marginals.** scope +0.43, ti1 +0.26, fx-article +0.11, ee10 +0.06, fx-oclock +0.04. On A2, ee10
fires only under `music_query`: 2 rows (play, qa), 2 spurious artist_name drops, 2 saves. It never fires in audio.

**Reading.**

- **Only one loss is a mechanism failure: Fold-A audio.** ee10 is a whole-row deletion, so one wrong firing costs
  every entity on the row. On a 60-row stratum, 5 such rows cost 26 pp.
- **The rest is 1 to 3 rows per scenario.** The A2 iot, datetime and email losses and the Fold-A social, cooking,
  takeaway and email losses come from ordinary per-entity drops (scope, ti1). Each rule is net positive pooled.
- **fx-article and fx-oclock** cause no loss in any of these scenarios.

## 3. Why ee10 misfires: the TRAIN statistic is unresolved

| intent (TRAIN pool) | pool exemplars | with entities | rate | Wilson 95 % upper | ee10 (v4) | ee-np5 (n x 0.10 >= 5) | **ee-wilson (upper < 0.10)** |
| --- | ---: | ---: | ---: | ---: | --- | --- | --- |
| audio_volume_mute | 45 | 4 | 0.0889 | 0.2073 | fires | no | **no** |
| audio_volume_other | 8 | 0 | 0.0000 | 0.3244 | fires | no | **no** |
| music_query | 71 | 4 | 0.0563 | 0.1361 | fires | fires | **no** |
| qa_maths | 66 | 0 | 0.0000 | 0.0550 | fires | fires | **fires** |

ee10's threshold is a point estimate on 8 to 71 exemplars. For `audio_volume_mute`, the 10 % cut sits inside the
sampling interval of its rate, so the rule is right about these rows only by chance. The Fold-A rows confirm
this: under that delivered intent, 4 of the 5 entities ee10 deleted were gold-exact.

The ti1 drops on Fold A that hit intents with fewer than 100 pool exemplars are listed below. These are the
existing column's events, not a guarded read:

- cooking_recipe (n = 46): exact 2
- takeaway_order (46): exact 1, spurious 2
- takeaway_query (47): exact 1, spurious 1
- music_query (71): exact 1, other 1, spurious 1
- music_likeness (64): spurious 1
- social_query (61): spurious 1
- transport_ticket (91): other 1

In total that is 5 exact, 6 spurious and 2 other. On such intents a type share of 0 means "not seen in < 100
exemplars". That says nothing about a 1 % rate.

## 4. The proposed guard (TRAIN statistics only) and its A2 effect

**The two guards.** Each is defined from the pool counts and the rule's own threshold, not from any Fold-A count:

- **ee-wilson.** ee10 fires on an intent only when the Wilson 95 % upper bound of its pool entity rate is below
  0.10. The criterion is that the rate is resolved below the threshold. It has no free parameter beyond the
  conventional 95 % level.
- **ti-expressible.** ti1 fires on an intent only when it has >= 1 / 0.01 = 100 pool exemplars. That is the
  smallest pool on which "< 1 %" is a different statement from "count 0". This removes 32 of 59 intents (1,691
  pool exemplars) from ti1.

**What was read on A2.** A2 only, against the sealed v3 column, plus the contrast with v4:

| variant | dSLU pp | CI95 | equal-scenario pp | vs v4 pp [CI95] | rows scoring differently from v4 |
| --- | ---: | --- | ---: | --- | ---: |
| v4 (no guard) | +0.98 | [+0.21, +1.74] | +0.10 | -- | 0 |
| v4 minus ee10 | +0.92 | [+0.16, +1.68] | +0.08 | -0.06 [-0.16, 0.00] | 2 |
| ee-wilson | +0.92 | [+0.16, +1.68] | +0.08 | -0.06 [-0.16, 0.00] | 2 |
| ee-np5 | +0.98 | [+0.21, +1.74] | +0.10 | 0.00 | 0 |
| ti-expressible | +1.10 | [+0.36, +1.84] | +0.32 | +0.12 [-0.09, +0.37] | 5 |
| **ti-expressible + ee-wilson (proposed)** | **+0.98** | **[+0.25, +1.71]** | **+0.23** | **-0.00 [-0.24, +0.26]** | **9** |
| ti-expressible + ee-np5 | +1.10 | [+0.36, +1.84] | +0.32 | +0.12 [-0.09, +0.37] | 5 |
| sensitivity: ti1 and ee10 need n >= 50 | +1.07 | [+0.32, +1.83] | +0.12 | +0.09 | 3 |
| sensitivity: ti1 and ee10 need n >= 100 | +1.01 | [+0.29, +1.74] | +0.29 | +0.03 | 10 |
| sensitivity: ti1 and ee10 need n >= 200 | +0.68 | [-0.01, +1.38] | -0.24 | -0.30 | 20 |

**Reading.**

- **Pooled.** The proposed guard leaves the A2 pooled point unchanged (+0.98) and narrows the lower bound
  upwards (+0.25).
- **Equal-scenario.** It raises the equal-scenario delta from +0.10 to +0.23.
- **What the guard does not touch.** The A2 per-scenario losses (iot -1.84, datetime -5.58, email -0.62,
  news -0.16) are unchanged under every guard. They are scope or ti1 drops on intents with >= 100 exemplars,
  which neither guard targets.
- **Why ee-wilson rather than ee-np5.** ee-np5 is A2-neutral and keeps ee10 on `music_query`. That rate (5.6 %,
  upper bound 13.6 %) is not resolved below 10 %. ee-wilson applies the same "resolved" standard as everywhere else
  in this programme, at a cost of -0.06 pp (2 rows) on A2. Choosing between the two by the A2 point would be
  selection on A2 again, so the criterion decides, not the number.
- **The n sweep is not a guard.** It is reported only to show that the result is not knife-edge at 100. At
  n >= 200, ti1 loses most of its value.
- **No scope guard is proposed.** The scope table records no slot type, and its thresholds (>= 5 occurrences,
  >= 80 % untagged) are the registered stage's own. Its losses are 2-row events inside a rule that is positive
  on both pools.

**Consequences for the lock.**

- **The rule set changes.** The guarded list is no longer the rule list Fold A confirmed:
  - `audio_volume_mute`, `audio_volume_other` and `music_query` no longer fire ee10;
  - 32 intents no longer fire ti1.
- **A fresh confirmation read is needed.** It must be on a roster that has not been used to look at this question.
  Fold A cannot serve: it located the audio failure, so its guarded number would not be a confirmation. That read
  was **not** run.
- **The owner's options.**
  - **(a) Lock v4 unchanged.** The pooled Fold-A gain is resolved, and the audio loss is a known, attributed
    5-row ee10 failure.
  - **(b) Lock v4 minus ee10.** The rule list becomes a subset of the confirmed one. On Fold A the ee10 removal is
    already read as a marginal: -0.27 pp pooled, so v4 minus ee10 would read about +1.94 on Fold A. This is still
    a post-hoc subset and needs the same caveat.
  - **(c) Adopt the guard.** This needs a fresh confirmation roster.
- **What the pinned tables support.** They carry the full intent and type counts, so all three options are
  implementable by the registered normaliser without new TRAIN reads.

## 5. Reproduce (WSL, from the worktree; zero model contacts)

```bash
cd /home/chao/saea-worktrees/fable-nx-postproc2 && source ~/.venvs/speechrl/bin/activate
export SPEECHRL_DATA_DIR=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data
PYTHONDONTWRITEBYTECODE=1 python -B scripts/analysis/slurp_nx_postproc_v4_audio_attribution.py --guards
```

| report (`analysis/SAEA-SLURP-NX-POSTPROC-V4-AUDIO-ATTRIBUTION-V1/...`) | sha256 |
| --- | --- |
| `a2/report.json` | `f5e486a814a33398bce8969fac653b0488dae5bcc25e35f9ae9ba24411d950c0` |
| `fold-a/report.json` | `7a6ca3eb7582be5aeb712a3f3d00e13405c909cdebc664b536dd639097c9d22e` |

The reports carry a `generated_at` stamp, so a re-run differs in that field only.
