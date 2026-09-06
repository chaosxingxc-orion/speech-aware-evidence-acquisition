# SLURP legal-label projection v2, promoting an action-named scenario — verdict (2026-09-06)

Row id `SAEA-SLURP-MF-LEGAL-LABEL-PROJECTION-V2-V1`, profile `model-free-check`, study commit
at the read `eaae5f9b`. Preregistration:
`docs/readiness/2026-09-06-slurp-legal-label-projection-v2-preregistration.md`.
Receipts: `docs/checks/speech-aware-evidence-acquisition/2026-09-06-slurp-legal-label-projection-v2/`.
**Zero model, GPU, tool, embedding and network contacts.** One registered read, fifteen scored
sets, one lock decision.

## Verdict

**RE-LOCKED, as preregistered.** The SLURP direct comparator is the sealed closed-list arm
**plus** `slurp-legal-label-projection-v2`, scored through the registered
`slurp-slu-official-projected-v2`.

* Intent **73.10**, against v1's locked **71.60** and the unprojected **71.40**.
  Paired **+1.50 pp** over the locked comparator (15 saves / **0 harms**, CI90 [+1.0, +2.1],
  p 6.1e-05) and **+1.70 pp** over the raw sealed labels (17 saves / **0 harms**,
  CI90 [+1.1, +2.3], p 1.5e-05). Non-negative on OLD500 *and* NEW500 in **both** contrasts,
  and **not one gold-scenario stratum harmed on intent anywhere, in either**.
* **Scenario 82.60 from 81.00** — the column v1 never moved at all.
* **Action 74.60**, up from v1's 73.30 and back **above** the unprojected 73.90: v2 does not
  merely stop paying v1's −0.60 pp, it turns it into +0.70.
* **SLU-F1 35.80, entities-strict 21.91, Word-F1 33.69 and Char-F1 38.20 unchanged to the last
  decimal** — on every arm, row by row, across all three views.
* **Impossible `(scenario, action)` pairs 3.90 % → 0.00 %**, as under v1.

**What earned it, exactly.** The promote branch touched **19 of the 39** rows the projection
changed and landed **15** of them on the gold intent. v1's edit distance touched all 39 and
landed **2**. The 20 rows v2 hands to the v1 fallback behave exactly as they did under v1,
because they *are* v1 — same function object, same answer.

**And the two things that keep this honest.**

1. **The whole intent gain is one stratum.** Against v1, `recommendation` moves 46.67 → 71.67
   on 60 rows (+25.00 pp, 15 saves, 0 harms) and **the other seventeen strata are flat**. This
   is a repair of one confusion — the model naming `recommendation`'s action as its scenario —
   not a broad improvement, and a mechanism that only helps `recommendation` would be judged
   the same way.
2. **The multi-owner half of the tie-break never fires on this roster.** All three promoted
   action names (`locations`, `events`, `movies`) have exactly one owner. The rule's
   `(-prior, scenario)` owner choice is exercised only by unit tests here; the three
   multi-owner action names in the ontology (`query` with 12 owners, `remove` with 3, `set`
   with 2) never reached the branch, because a row naming one of them in the scenario slot did
   not occur.

It is still a **repair of the baseline's own output**, not a mechanism: no evidence, no
retrieval, no second contact, no parameter. The points belong to the comparator, and every
pending SLURP cell now has to beat **73.10**, not 71.60 and not 71.40.

**MF-7's attribution, corrected in one sentence.** The 2026-09-06 retrieval-key audit priced
its winner's gain at "≈ +1.40 pp closed-list legalisation of out-of-ontology draft labels";
measured on the same sealed draft rows, **cheap legalisation is worth +0.10 pp (v1) and the
best legalisation rule we have is worth +0.90 pp (v2)** — so even the good rule does not reach
+1.40, and GLAP's fallback was selecting among legal labels rather than legalising.

## 1. The official table

Official `evaluate.py` at pinned commit `8eb1654…311f1` in `~/.venvs/slurp-official-eval`
(used, never modified), `--average micro --errors --table-layout csv`, over complete 1,000-row
manifests through `core.scoring_batch`, one job per manifest, `include_per_sample=True`, never
sharded. **The port-vs-official identity check passed on all fifteen scored sets** (absolute
difference ≤ 1.1e-16).

| arm | view | scenario | action | **intent** | entities strict | Word-F1 | Char-F1 | **SLU-F1** | unparsed |
|---|---|---|---|---|---|---|---|---|---|
| **CLOSED-LIST** | unprojected | 81.00 | 73.90 | **71.40** | 21.91 | 33.69 | 38.20 | 35.80 | 3 |
| **CLOSED-LIST** | v1 (locked) | 81.00 | 73.30 | **71.60** | 21.91 | 33.69 | 38.20 | 35.80 | 3 |
| **CLOSED-LIST** | **v2** | **82.60** | **74.60** | **73.10** | 21.91 | 33.69 | 38.20 | 35.80 | 3 |
| KU-S1c (revise) | unprojected | 81.50 | 75.20 | 72.90 | 23.26 | 33.99 | 38.07 | 35.92 | 4 |
| KU-S1c (revise) | v1 | 81.50 | 74.70 | 73.10 | 23.26 | 33.99 | 38.07 | 35.92 | 4 |
| KU-S1c (revise) | **v2** | 82.40 | 75.40 | **74.00** | 23.26 | 33.99 | 38.07 | 35.92 | 4 |
| KU-S1c (draft) | unprojected | 81.40 | 74.90 | 72.60 | 22.50 | 33.62 | 37.62 | 35.51 | 2 |
| KU-S1c (draft) | v1 | 81.40 | 74.30 | 72.70 | 22.50 | 33.62 | 37.62 | 35.51 | 2 |
| KU-S1c (draft) | **v2** | 82.20 | 74.90 | **73.50** | 22.50 | 33.62 | 37.62 | 35.51 | 2 |
| KC-S1a (as sealed) | unprojected | 16.10 | 15.70 | 15.20 | 21.82 | 33.62 | 38.17 | 35.75 | 2 |
| KC-S1a (as sealed) | v1 | 16.10 | 15.50 | 15.30 | 21.82 | 33.62 | 38.17 | 35.75 | 2 |
| KC-S1a (as sealed) | **v2** | 16.20 | 15.50 | 15.40 | 21.82 | 33.62 | 38.17 | 35.75 | 2 |
| KC-S1b (as sealed) | unprojected | 36.00 | 33.30 | 32.10 | 31.37 | 41.58 | 47.51 | **44.35** | 3 |
| KC-S1b (as sealed) | v1 | 36.00 | 32.80 | 32.30 | 31.37 | 41.58 | 47.51 | **44.35** | 3 |
| KC-S1b (as sealed) | **v2** | 37.60 | 34.10 | 33.80 | 31.37 | 41.58 | 47.51 | **44.35** | 3 |

**Identity anchors, checked before any new number was trusted, and fail-closed.** Every one of
the ten published sets — seven metrics × five arms × two views — is hard-coded in the read
script, which raises rather than reports if the sealed bytes stop reproducing it. All ten
matched. That covers the closed-list verdict's own table *and* v1's, so the v2 column is the
only column in this document that has never been published before.

**Read the KC rows carefully.** KC-S1a and KC-S1b mostly answer `{"entities": [...]}`; their
scenario/action columns *as sealed* are meaningless by construction and were never reported by
their own verdict — their published intent column is the closed-list intent, copied in by the
model-free join their read registered. Those columns appear here only to prove the projection
touched nothing that matters: **entities strict, Word-F1, Char-F1 and SLU-F1 are identical
across all three views on both arms, row by row.** Under the re-lock their intent column
becomes the *v2* closed-list intent, **73.10**, by the same construction — arithmetic, not a
new measurement, and **KC-S1b's admission is untouched**.

## 2. Paired contrasts on the same sealed rows (CLOSED-LIST)

`analysis.paired.paired_contrast`, 10,000 stratified bootstrap replicates, seed 20260903,
strata = gold scenario, CI90, exact sign test. v1's settings unchanged, so the two reads are
comparable.

### 2.1 v2 − v1 — does the successor beat the locked comparator

| population | metric | v1 | v2 | delta | saves | harms | p | CI90 |
|---|---|---|---|---|---|---|---|---|
| pooled 1000 | **intent** | 71.60 | **73.10** | **+1.50** | 15 | **0** | 6.1e-05 | [+1.0, +2.1] |
| pooled 1000 | **scenario** | 81.00 | **82.60** | **+1.60** | 16 | **0** | 3.1e-05 | [+1.0, +2.2] |
| pooled 1000 | **action** | 73.30 | **74.60** | **+1.30** | 15 | 2 | 0.0024 | [+0.7, +1.9] |
| pooled 1000 | slot F1 (per sample) | 12.96 | 12.96 | 0.00 | 0 | 0 | 1 | [0.00, 0.00] |
| pooled 1000 | SLU-F1 (per sample) | 19.75 | 19.75 | 0.00 | 0 | 0 | 1 | [0.00, 0.00] |
| prior-exposed 500 | intent | 69.60 | **71.00** | **+1.40** | 7 | **0** | 0.016 | [+0.6, +2.2] |
| prior-exposed 500 | action | 71.20 | 72.60 | +1.40 | 7 | 0 | 0.016 | [+0.6, +2.2] |
| **unexposed 500** | **intent** | 73.60 | **75.20** | **+1.60** | 8 | **0** | 0.0078 | [+0.8, +2.4] |
| unexposed 500 | action | 75.40 | 76.60 | +1.20 | 8 | 2 | 0.109 | [+0.2, +2.2] |

### 2.2 v2 − unprojected — what the projection is worth in total

| population | metric | unprojected | v2 | delta | saves | harms | p | CI90 |
|---|---|---|---|---|---|---|---|---|
| pooled 1000 | **intent** | 71.40 | **73.10** | **+1.70** | 17 | **0** | 1.5e-05 | [+1.1, +2.3] |
| pooled 1000 | scenario | 81.00 | 82.60 | +1.60 | 16 | 0 | 3.1e-05 | [+1.0, +2.2] |
| pooled 1000 | **action** | 73.90 | **74.60** | **+0.70** | 17 | 10 | 0.248 | [−0.1, +1.5] |
| pooled 1000 | SLU-F1 (per sample) | 19.75 | 19.75 | 0.00 | 0 | 0 | 1 | [0.00, 0.00] |
| prior-exposed 500 | intent | 69.60 | 71.00 | **+1.40** | 7 | **0** | 0.016 | [+0.6, +2.2] |
| prior-exposed 500 | action | 72.20 | 72.60 | +0.40 | 7 | 5 | 0.774 | [−0.6, +1.4] |
| **unexposed 500** | **intent** | 73.20 | **75.20** | **+2.00** | 10 | **0** | 0.0020 | [+1.2, +3.0] |
| unexposed 500 | action | 75.60 | 76.60 | +1.00 | 10 | 5 | 0.302 | [−0.2, +2.2] |

### 2.3 v1 − unprojected — the anchor

Reproduces v1's published verdict exactly: intent +0.20 pooled (2 saves / 0 harms,
CI90 [0.00, +0.50]), +0.00 on OLD500, +0.40 on NEW500; scenario 0.00; action −0.60 (2 saves /
8 harms, CI90 [−1.1, −0.1]); every entity-side metric 0.00.

Both weightings agree, as they always do on this scenario-stratified roster: natural
71.40 → 71.60 → **73.10**, equal-stratum 71.45 → 71.63 → **73.02**.

**The other four arms move the same way.** v2 − v1 / v2 − unprojected on intent: KU-S1c revise
+0.90 / +1.10, its draft +0.80 / +0.90, KC-S1b +1.50 / +1.70, KC-S1a +0.10 / +0.20. Every one
of them has **zero** intent harms in both contrasts and **zero** movement on every entity-side
metric.

## 3. Per stratum (intent, pooled 1,000)

**Against v1, exactly one stratum moves.**

| scenario | n | v1 | v2 | delta | saves | harms |
|---|---|---|---|---|---|---|
| **recommendation** | 60 | 46.67 | **71.67** | **+25.00** | 15 | **0** |
| the other 17 | 940 | — | — | 0.00 | 0 | **0** |

Against the unprojected rows, three move and all three move up: `recommendation` +25.00
(15 saves), `play` +1.67 (1), `general` +1.64 (1) — the last two being v1's own two saves,
which v2 keeps.

**The action column's harms, named.** Against v1: 2 harms, both in `calendar` (−3.28 pp on
n=61) against 15 saves in `recommendation`. Against the unprojected rows: 10 harms —
`calendar` 3, `news` 2, `play` 2, and one each in `lists`, `music` and `transport` — which are
exactly v1's own 8 fallback harms plus the two `calendar` rows, and are outweighed by
`recommendation`'s 15 saves. No stratum is harmed on **intent** anywhere, which is what the
lock rule gates on.

## 4. What the projection actually did

| arm | eligible | left alone | **changed** | via **promote** | via edit distance | landing on gold | ineligible |
|---|---|---|---|---|---|---|---|
| CLOSED-LIST (v1) | 997 | 958 | 39 | — | 39 | **2** | 3 |
| **CLOSED-LIST (v2)** | 997 | 958 | **39** | **19** | 20 | **17** | 3 |
| KU-S1c revise (v2) | 996 | 959 | 37 | 13 | 24 | 11 | 4 |
| KU-S1c draft (v2) | 998 | 963 | 35 | 11 | 24 | 9 | 2 |
| KC-S1a (v2) | 194 | 186 | 8 | 2 | 6 | 2 | 806 |
| KC-S1b (v2) | 456 | 418 | 38 | 19 | 19 | 17 | 544 |

The two rules change the **same** rows — a pair is illegal or it is not — and differ only in
where those rows land. The complete closed-list promote map:

| rows | promote branch | gold |
|---|---|---|
| **10** | `locations/query` → `recommendation_locations` | 9 |
| **8** | `events/query` → `recommendation_events` | 5 |
| 1 | `movies/query` → `recommendation_movies` | 1 |

against the same rows under v1: `locations_query → lists_query` (10), `events_query →
lists_query` (8), `movies_query → social_query` (1) — **zero** gold. The remaining twenty rows
take the v1 fallback and are byte-identical to v1's answer for them, `sport_query → iot_coffee`
included: with `sport` outside the 18 scenarios and not a legal action name either, edit
distance still picks `iot`, and inside `iot` it still picks `coffee`. v2 does not fix that row
and does not claim to.

## 5. The residual after v2

Descriptive only — no rule, no metric, no gate, no effect on the lock. Of the 39 rows v2
changed on the closed-list arm, **17 land on gold and 22 do not**. Of those 22, four were
touched by the promote branch (a promotion to the right scenario whose action name was not the
gold one), and two become a legal pair when their halves are exchanged — with both of those
two exchanges equalling gold. The rest are what v1's verdict already called the rule at its
worst: a label whose nearest legal neighbour by spelling is simply a different intent.

There is no obvious third rule in that residual. Two rows is not a class.

## 6. The KC-S1b fallback rows

KC-S1b selected its per-intent TRAIN slot-schema block from the sealed closed-list response;
**42 rows (4.2 %)** fell back to the full 60-intent schema — 3 that did not parse and 39 that
named an impossible pair. Under either projection **39 of the 42 become legal**; the 3 unparsed
rows stay unparsed and still fall back, as both rules require. What changes is *which* block
they would have received: under v1, **2** of the 39 would have got the **gold** intent's block;
under v2, **17**. So a successor cell would serve the right per-intent block on 17 of the rows
where KC-S1b served a 26,720-character full-schema fallback.

**Forward-looking only.** KC-S1b's own numbers are untouched and are not restated: it chose its
blocks from bytes sealed on 2026-09-06, and nothing here re-runs that choice.

## 7. The comparator identity, exactly

Every pending SLURP cell pairs against this from now on:

| field | value |
|---|---|
| run id | `SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1` |
| attempt | `attempt-20260905T060424Z-2c5596` |
| run manifest sha256 | `f908ff4c7b0267322b34c7bf2ca9ad29d6db97ee8bb3cf18bf8824a057ebc94c` |
| outputs sha256 | `34fda7fa51410e0f4f7e8ba7c35f867c32f53c244de63af5386860486fcb885b` |
| **scorer id** | **`slurp-slu-official-projected-v2`** (alias `slurp-slu-projected-v2`) |
| projection id | `slurp-legal-label-projection-v2` |
| split identity | `8580d199bffc95a51ad6d8c5b2a2e9e39faa2c551dd095f8afcd78174a1e3c84`, DEV-1000 |
| **numbers to beat** | **intent 73.10, SLU-F1 35.80** (scenario 82.60, action 74.60) |

The sealed bytes are unchanged; only the scorer the comparator is read through changes.
`slurp-slu-official-projected` (v1) stays registered and resolvable, and v1's own verdict
stands as published — it is superseded as the comparator, not withdrawn as a measurement. A
cell that reports against `slurp-slu-official` is comparing against 71.40 and against
`…-projected` against 71.60; the three differ by at most 1.70 pp on intent and by **nothing at
all** on SLU-F1, so **no admitted or reported result on this carrier moves**, and none is
restated.

## 8. Mechanics and provenance

| item | value |
|---|---|
| scoring | `core.scoring_batch`, **12 jobs, 0 failed, 99.0 s**, `include_per_sample=True`, one job per manifest, never sharded |
| derived manifests | two per arm (v1, v2), differing from the sealed manifest **only in `scorers`**, written beside the artifacts they name; sha256 in `read.json` under `manifests` |
| sealed manifests | `f908ff4c…c94c` (closed-list), `1b5143aa…1a74d` (KU-S1c), `80f49ac0…fd617` (KC-S1a), `088c9307…5fe8d08` (KC-S1b) — re-verified from their own bytes by the unprojected job |
| KU-S1c draft | phases file `f6ed3c14…4e63`, scored through the registered scorer functions (registered deviation) |
| legal inventory | 60 intents, 18 scenarios, from `data.slurp.load_slurp_ontology` (`train.jsonl` only); 3 action names have more than one owner (`query` 12, `remove` 3, `set` 2) |
| TRAIN prior | `data.slurp.load_slurp_intent_slot_schema(...).intents[*].n` |
| statistics | `analysis.paired.paired_contrast`, 10,000 replicates, seed 20260903, CI90, strata = gold scenario |
| cost | 0 model calls, 0 audio seconds, 0 GPU hours, 0 tool contacts, 0 embedding contacts, 0 paid spend |

## 9. Preregistered expectations, scored

Every direction section 1.1 committed to before the read, and how it came out:

| expectation | outcome |
|---|---|
| intent harms structurally zero | **held** — 0 harms in every contrast, population and stratum; 0 devel gold intents lie outside the 60 TRAIN pairs, re-derived |
| scenario harms structurally zero | **held** — 0 |
| scenario delta **up, for the first time** | **held** — +1.60 against both baselines (v1: 0.00) |
| intent **up** against both baselines, ≈ +1.5 pp on closed-list | **held** — +1.50 / +1.70 |
| action vs v1 **up or flat** | **held** — +1.30, with the 2 predicted harms |
| action vs unprojected **better than −0.60, sign not predicted** | **held**, and the sign came out **positive**: +0.70 |
| entity-side deltas structurally zero | **held** — row by row on 15,000 arm-rows, not one moved |

## 10. Deviations and limits

1. **The multi-owner tie-break is untested on real data.** No promoted row named a
   multi-owner action in its scenario slot, so `(-prior, scenario)` was never called on to
   choose. It is exercised only by unit tests. If a later roster produces such a row, this
   verdict is not evidence about how that choice behaves.
2. **The gain is one confusion, not a broad improvement.** Seventeen of eighteen strata are
   flat against v1. `recommendation` carries all of it.
3. **The action column still has harms** — 2 against v1, 10 against the unprojected rows —
   and the lock rule gates on intent alone, exactly as v1's did. Preregistered as a possible
   outcome; reported rather than gated away.
4. **The entity-only arms are not label-free.** Carried forward from v1's own correction
   rather than rediscovered: KC-S1a volunteers a pair on 194 of 1,000 rows and KC-S1b on 456,
   so 8 and 38 of their meaningless as-sealed label rows moved. Every entity-side metric is
   unchanged, which is the claim that matters.
5. **Section 0.1 of the preregistration applies.** v1's verdict had already published the
   19-row / 15-gold count for the closed-list arm, so that headline was not a blind
   prediction. The lock turned on what was unread — both contrasts, both populations, the
   per-stratum harm table and the other four arms — and it is stated that way.
6. **Devel, not test.** No test contact. No published bracket is re-examined: the closed-list
   verdict's bracket table moves by 1.70 pp on intent, which changes no verdict in it
   (Google/SF-ID 72.06 becomes +1.04 instead of −0.66 — the arm now clears that pipeline
   rather than trailing it, and still fails the degraded-model floor the same way).
7. **No SLURP devel sentence text was read**, and no gold entered anything but the registered
   official scorer and the gold *scenario* used as the bootstrap stratum label — the same
   device every SLURP verdict on this carrier uses.

## 11. What this authorizes

The comparator identity of section 7, and nothing else. No admission, no promotion, no
superiority claim, no generalization claim, no test contact, no Stage-3 activity. No published
verdict is reopened, restated or re-scored: KC-S1b stays admitted on its own sealed numbers,
KU-S1c stays reported on its own, and neither the closed-list verdict's table nor v1's is
changed. The carrier set stays Earnings-21+ConEC, SLURP and Audio2Tool.

No third projection rule is proposed. The residual after v2 has no class in it worth
registering, and the next SLURP step is a mechanism measured against 73.10.
