# SLURP legal-label projection, re-locking the closed-list baseline — verdict (2026-09-06)

Row id `SAEA-SLURP-MF-LEGAL-LABEL-PROJECTION-RELOCK-V1`, profile `model-free-check`, study
commit at the read `8f1532f9`. Preregistration:
`docs/readiness/2026-09-06-slurp-legal-label-projection-relock-v1-preregistration.md`.
Receipts: `docs/checks/speech-aware-evidence-acquisition/2026-09-06-slurp-legal-label-projection-relock/`.
**Zero model, GPU, tool, embedding and network contacts.** One registered read, ten scored
sets, one lock decision.

## Verdict

**RE-LOCKED, as preregistered.** The SLURP direct comparator is the sealed closed-list arm
**plus** the legal-label projection `slurp-legal-label-projection-v1`, scored through the
registered `slurp-slu-official-projected`.

* Intent **71.60** against the unprojected **71.40**: paired **+0.20 pp** pooled
  (CI90 [0.00, +0.50], 2 saves / **0 harms**), **+0.00** on OLD500 and **+0.40** on NEW500.
* **SLU-F1 35.80, unchanged to the last decimal**, and so are entities-strict, Word-F1 and
  Char-F1 — on every arm, row by row.
* **Impossible `(scenario, action)` pairs: 3.90 % → 0.00 %.** For the first time the arm's
  output is inside the 60-way label space the published protocol defines.
* Every preregistered lock condition is met, and **no gold-scenario stratum is harmed on
  intent anywhere** — not by one row, by none.

**And the honest headline underneath it: this is protocol alignment, not accuracy.** Only
**2 of the 39** legalised rows land on the gold intent, and the **action column loses 0.60 pp**
(73.90 → 73.30). A pending SLURP cell now has to beat 71.60 instead of 71.40, which is 2 rows.

**The finding that matters is the residual, and it is now named and priced.** **19 of the 39
illegal rows put a legal ACTION name in the SCENARIO slot** — `locations/query`,
`events/query`, `movies/query` — and promoting that name back to its owning scenario would
have recovered **15** of them, about **+1.5 pp intent**. Nearest-edit-distance cannot see
this: it sends `locations` to `lists`, because that is what `locations` is spelled like. **The
label's legality was never the problem; which legal label you pick is.**

That also corrects MF-7. The 2026-09-06 retrieval-key audit priced its winner's gain at
"+1.00 pp draft label + ~+1.40 pp closed-list legalisation of out-of-ontology draft labels
+ ~0 pp retrieved evidence", and called legalisation "a decoding-constraint repair available
far more cheaply than a retrieval plane". Measured here on **the same sealed draft rows**, the
cheap repair is worth **+0.10 pp**, not +1.40. GLAP's fallback was not doing legalisation; it
was doing *selection among legal labels*, and that is the part that carried the 1.4 points.

## 1. The official table

Official `evaluate.py` at pinned commit `8eb1654…311f1` in `~/.venvs/slurp-official-eval`
(used, never modified), `--average micro --errors --table-layout csv`, over complete 1,000-row
manifests through `core.scoring_batch`, one job per manifest, `include_per_sample=True`, never
sharded. **The port-vs-official identity check passed on all ten scored sets** (absolute
difference 0.0; KC-S1a 5.6e-17).

| arm | view | scenario | action | **intent** | entities strict | Word-F1 | Char-F1 | **SLU-F1** | unparsed |
|---|---|---|---|---|---|---|---|---|---|
| **CLOSED-LIST** | unprojected | 81.00 | 73.90 | **71.40** | 21.91 | 33.69 | 38.20 | 35.80 | 3 |
| **CLOSED-LIST** | **projected** | 81.00 | **73.30** | **71.60** | 21.91 | 33.69 | 38.20 | 35.80 | 3 |
| KU-S1c (revise) | unprojected | 81.50 | 75.20 | 72.90 | 23.26 | 33.99 | 38.07 | 35.92 | 4 |
| KU-S1c (revise) | projected | 81.50 | 74.70 | 73.10 | 23.26 | 33.99 | 38.07 | 35.92 | 4 |
| KU-S1c (draft) | unprojected | 81.40 | 74.90 | 72.60 | 22.50 | 33.62 | 37.62 | 35.51 | 2 |
| KU-S1c (draft) | projected | 81.40 | 74.30 | 72.70 | 22.50 | 33.62 | 37.62 | 35.51 | 2 |
| KC-S1a (as sealed) | unprojected | 16.10 | 15.70 | 15.20 | 21.82 | 33.62 | 38.17 | 35.75 | 2 |
| KC-S1a (as sealed) | projected | 16.10 | 15.50 | 15.30 | 21.82 | 33.62 | 38.17 | 35.75 | 2 |
| KC-S1b (as sealed) | unprojected | 36.00 | 33.30 | 32.10 | 31.37 | 41.58 | 47.51 | **44.35** | 3 |
| KC-S1b (as sealed) | projected | 36.00 | 32.80 | 32.30 | 31.37 | 41.58 | 47.51 | **44.35** | 3 |

**Identity anchor.** Every unprojected row reproduces its own published verdict to the second
decimal from the same sealed bytes: the closed-list arm's seven metrics, KU-S1c's 72.90 /
35.92, its draft's 72.60 / 35.51, KC-S1b's 31.37 / 44.35 and KC-S1a's 21.82 / 35.75.

**Read the KC rows carefully.** KC-S1a and KC-S1b answer `{"entities": [...]}`; their
scenario/action columns *as sealed* are meaningless by construction and were never reported by
their own verdict — their published intent column is the closed-list intent, copied in by the
model-free join their read registered. Those as-sealed columns are shown here only to prove
the projection touched nothing that matters: **entities strict, Word-F1, Char-F1 and SLU-F1
are byte-identical projected and unprojected on both arms.** Under the re-lock their intent
column becomes the *projected* closed-list intent, **71.60**, by the same construction — it is
arithmetic, not a new measurement, and **KC-S1b's admission is untouched**.

## 2. Paired contrast, projected minus unprojected on the same sealed rows

`analysis.paired.paired_contrast`, 10,000 stratified bootstrap replicates, seed 20260903,
strata = gold scenario, CI90, exact sign test.

| population | metric | unprojected | projected | delta | saves | harms | p | CI90 |
|---|---|---|---|---|---|---|---|---|
| pooled 1000 | **intent** | 71.40 | **71.60** | **+0.20** | 2 | **0** | 0.50 | [0.00, +0.50] |
| pooled 1000 | scenario | 81.00 | 81.00 | 0.00 | 0 | 0 | 1 | [0.00, 0.00] |
| pooled 1000 | **action** | 73.90 | 73.30 | **−0.60** | 2 | 8 | 0.109 | [−1.10, −0.10] |
| pooled 1000 | slot F1 (per sample) | 12.96 | 12.96 | 0.00 | 0 | 0 | 1 | [0.00, 0.00] |
| pooled 1000 | SLU-F1 (per sample) | 19.75 | 19.75 | 0.00 | 0 | 0 | 1 | [0.00, 0.00] |
| prior-exposed 500 | intent | 69.60 | 69.60 | **+0.00** | 0 | 0 | 1 | [0.00, 0.00] |
| prior-exposed 500 | action | 72.20 | 71.20 | −1.00 | 0 | 5 | 0.063 | [−1.80, −0.40] |
| **unexposed 500** | **intent** | 73.20 | **73.60** | **+0.40** | 2 | **0** | 0.50 | [0.00, +1.00] |
| unexposed 500 | action | 75.60 | 75.40 | −0.20 | 2 | 3 | 1 | [−1.00, +0.60] |

Both weightings agree and barely differ, as they always do on this scenario-stratified roster:
natural 71.40 → 71.60, equal-stratum 71.45 → 71.63.

The other four arms move the same way and by the same tiny amounts: KU-S1c +0.20 intent /
−0.50 action, its draft +0.10 / −0.60, KC-S1b +0.20 / −0.50, KC-S1a +0.10 / −0.20. Every one
of them has **zero** intent harms and **zero** movement on every entity-side metric.

## 3. Per stratum (intent, pooled 1,000)

Sixteen of the eighteen strata are flat. The two that move, move up:

| scenario | n | unprojected | projected | delta | saves | harms |
|---|---|---|---|---|---|---|
| general | 61 | 34.4 | 36.1 | **+1.6** | 1 | 0 |
| play | 60 | 38.3 | 40.0 | **+1.7** | 1 | 0 |
| the other 16 | 879 | — | — | 0.0 | 0 | **0** |

The action column's 8 pooled harms are spread thinly — `news` 2, `play` 2, and one each in
`calendar`, `lists`, `music`, `transport` — and are exactly the structurally predicted case:
rule 4a rewrites an action that happened to be *right* while the scenario was wrong.

## 4. What the projection actually did

| arm | eligible rows | left alone | **projected** | landing on gold | ineligible (no label) |
|---|---|---|---|---|---|
| CLOSED-LIST | 997 | 958 | **39** | **2** | 3 (unparsed) |
| KU-S1c revise | 996 | 959 | 37 | 2 | 4 |
| KU-S1c draft | 998 | 963 | 35 | 1 | 2 |
| KC-S1a | 194 | 186 | 8 | 1 | 806 |
| KC-S1b | 456 | 418 | 38 | 2 | 544 |

The complete closed-list map, every changed label:

| rows | from → to |
|---|---|
| **10** | `locations_query` → `lists_query` |
| **8** | `events_query` → `lists_query` |
| 2 | `audio_audiobook` → `audio_volume_up` |
| 2 | `audio_play` → `audio_volume_up` |
| 2 | `calendar_createoradd` → `calendar_remove` |
| 2 | `general_query` → `general_quirky` |
| 2 | `music_play` → `music_query` |
| 1 each | `datetime_set`→`datetime_query`, `iot_hue_lightdown`→`iot_hue_lighton`, `movies_query`→`social_query`, `music_remove`→`music_query`, `music_volume_other`→`music_query`, `play_player_setting`→`play_podcasts`, `play_query`→`play_music`, `qa_convert`→`qa_currency`, `sport_query`→`iot_coffee`, `sports_query`→`iot_coffee`, `takeaway_ticket`→`takeaway_order` |

`sport_query → iot_coffee` is the rule at its worst and is shown rather than hidden: with
`sport` outside the 18 scenarios, edit distance picks `iot`, and inside `iot` it picks
`coffee`. The row was wrong before and is wrong after; nothing is lost, but nothing is gained
either, and no amount of tie-breaking fixes a rule that is measuring spelling.

## 5. The residual, named and priced

Descriptive only — no rule, no metric, no gate, and no effect on the lock. Among the 39 rows
the registered projection changed:

| description | closed-list | KU-S1c revise | KU-S1c draft | KC-S1b |
|---|---|---|---|---|
| rows changed | 39 | 37 | 35 | 38 |
| landed on gold under the registered rule | **2** | 2 | 1 | 2 |
| parsed pair becomes legal when its halves are EXCHANGED | 2 | 3 | 3 | 2 |
| **scenario half is a legal ACTION name** | **19** | 13 | 11 | 19 |
| **…and promoting it lands on gold** | **15** | 9 | 8 | 15 |

The closed-list promotion map: `locations/query → recommendation_locations` 10 rows, 9 gold;
`events/query → recommendation_events` 8 rows, 5 gold; `movies/query → recommendation_movies`
1 row, 1 gold.

This is the class the 2026-09-05 closed-list verdict spotted by eye and did not price. It is
now priced: **a projection that promotes an action-named scenario back to its owning scenario
is worth about +1.5 pp intent on this arm, roughly eight times the registered rule.** It is
`slurp-legal-label-projection-v2`, it is a *different rule*, and it was found by looking at
this read's output — so it **cannot be locked here**. It needs its own preregistration, and
this verdict recommends exactly that as the next model-free step on this carrier.

## 6. The KC-S1b fallback rows

KC-S1b selected its per-intent TRAIN slot-schema block from the sealed closed-list response;
**42 rows (4.2 %)** fell back to the full 60-intent schema — 3 that did not parse and 39 that
named an impossible pair.

Under the projection, **39 of the 42 become legal** and would have received a per-intent
block; the 3 unparsed rows stay unparsed and still fall back, as the rule requires. Of the 39,
**2** would have received the *gold* intent's block. So the projection converts KC-S1b's
schema-selection miss from a 4.2 % gap into a 0.3 % gap, but almost all of the newly served
blocks would be the *wrong* intent's block — a strictly better place to be than the 26,720-
character full-schema fallback, and not the same thing as being right.

**Forward-looking only.** KC-S1b's own numbers are untouched and are not restated: it chose
its blocks from bytes sealed on 2026-09-06, and nothing here re-runs that choice.

## 7. The comparator identity, exactly

Every pending SLURP cell pairs against this from now on:

| field | value |
|---|---|
| run id | `SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1` |
| attempt | `attempt-20260905T060424Z-2c5596` |
| run manifest sha256 | `f908ff4c7b0267322b34c7bf2ca9ad29d6db97ee8bb3cf18bf8824a057ebc94c` |
| outputs sha256 | `34fda7fa51410e0f4f7e8ba7c35f867c32f53c244de63af5386860486fcb885b` |
| **scorer id** | **`slurp-slu-official-projected`** (alias `slurp-slu-projected`) |
| projection id | `slurp-legal-label-projection-v1` |
| split identity | `8580d199bffc95a51ad6d8c5b2a2e9e39faa2c551dd095f8afcd78174a1e3c84`, DEV-1000 |
| **numbers to beat** | **intent 71.60, SLU-F1 35.80** (scenario 81.00, action 73.30) |

The sealed bytes are unchanged; only the scorer the comparator is read through changes. A cell
that reports against `slurp-slu-official` is not wrong, it is comparing against 71.40 — the
two differ by 0.20 pp on intent and by nothing at all on SLU-F1, so **no admitted or reported
result on this carrier moves**, and none is restated.

## 8. Mechanics and provenance

| item | value |
|---|---|
| scoring | `core.scoring_batch`, **8 jobs, 0 failed, 165.3 s**, `include_per_sample=True`, one job per manifest, never sharded |
| derived manifests | one per arm, differing from the sealed manifest **only in `scorers`**, written beside the artifacts they name; sha256 in `read.json` under `manifests` |
| sealed manifests | `f908ff4c…c94c` (closed-list), `1b5143aa…1a74d` (KU-S1c), `80f49ac0…fd617` (KC-S1a), `088c9307…5fe8d08` (KC-S1b) — re-verified from their own bytes by the unprojected job |
| KU-S1c draft | phases file `f6ed3c14…4e63`, outputs projection `65830fae…2ed69`, scored through the registered scorer functions (registered deviation) |
| legal inventory | 60 intents, 18 scenarios, from `data.slurp.load_slurp_ontology` (`train.jsonl` only) |
| TRAIN prior | `data.slurp.load_slurp_intent_slot_schema(...).intents[*].n` |
| statistics | `analysis.paired.paired_contrast`, 10,000 replicates, seed 20260903, CI90, strata = gold scenario |
| cost | 0 model calls, 0 audio seconds, 0 GPU hours, 0 tool contacts, 0 embedding contacts, 0 paid spend |

## 9. Deviations and limits

1. **One preregistered expectation was wrong and is corrected here.** The preregistration said
   the entity-only arms' sealed rows would be *untouched* because they carry no
   `scenario_action`. They are not label-free: KC-S1a volunteers a scenario and an action on
   194 of 1,000 rows and KC-S1b on 456, so the projection changed 8 and 38 of those rows. The
   claim that actually mattered — **that every entity-side metric is unchanged** — holds
   exactly, row by row, on both arms and on all five. The wrong half of the expectation is
   reported rather than quietly dropped.
2. **The lock rule gates on intent alone, and the action column regressed.** That was
   preregistered as a possible outcome ("a negative action delta is a finding, not a defect")
   and it happened: −0.60 pp pooled. Intent and SLU-F1 are the two numbers this carrier's
   verdicts report; action is a component beside them. The lock stands because the rule that
   was registered says it stands, not because the action number is comfortable.
3. **The re-lock is worth 2 rows.** Its case is protocol alignment — an arm that emits a label
   outside the 60 is not performing the published 60-way task — plus the removal of a free
   gain from every future mechanism's reach. It is not an accuracy result and is not reported
   as one.
4. **The v2 rule was found by looking at this read's output and is therefore not lockable
   here.** It is described, counted and recommended; it is not applied to any number in this
   verdict.
5. **Devel, not test.** No test contact. No published bracket is re-examined: the closed-list
   verdict's bracket table moves by 0.20 pp on intent, which changes no verdict in it
   (Google/SF-ID 72.06 stays −0.46 instead of −0.66, still aligned, still failing the
   degraded-model floor).
6. **No SLURP devel sentence text was read**, and no gold entered anything but the registered
   official scorer and the gold *scenario* used as the bootstrap stratum label — the same
   device every SLURP verdict on this carrier uses.

## 10. What this authorizes

The comparator identity of section 7, and nothing else. No admission, no promotion, no
superiority claim, no generalization claim, no test contact, no Stage-3 activity. No published
verdict is reopened, restated or re-scored: KC-S1b stays admitted on its own sealed numbers,
KU-S1c stays reported on its own, and the closed-list verdict's own table is unchanged. The
carrier set stays Earnings-21+ConEC, SLURP and Audio2Tool.

The named next step is a preregistration for `slurp-legal-label-projection-v2` — promote an
action-named scenario back to its owning scenario before falling back to edit distance —
measured the same way, on the same sealed rows, at zero contacts.
