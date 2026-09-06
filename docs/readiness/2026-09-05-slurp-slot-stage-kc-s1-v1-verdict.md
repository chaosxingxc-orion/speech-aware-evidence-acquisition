# SLURP slot stage, cells KC-S1a and KC-S1b — verdict (2026-09-05)

Run ids `SAEA-SLURP-KC-S1A-SLOTS-DEV1000-V1` (attempt `attempt-20260906T023017Z-38c20a`, study commit
`782c6ac8`) and `SAEA-SLURP-KC-S1B-SLOTS-SCHEMA-DEV1000-V1` (attempt `attempt-20260906T025102Z-af6b04`,
study commit `d737e354`), profile `bounded-discovery-probe`. Preregistration:
`docs/readiness/2026-09-05-slurp-use2-slot-stage-v1-preregistration.md`. Receipts:
`docs/checks/speech-aware-evidence-acquisition/2026-09-05-slurp-slot-stage-kc-s1-v1/`.
Two cells, one attempt each except KC-S1b, which took its one permitted recovery after a CUDA fault
killed the server mid-roster (section 9). One seal each, one read.

## Verdict

**KC-S1b is ADMITTED**, on both preregistered conditions and with a large margin, and it is the first
mechanism in this study to move SLURP's slot layer at all.

* **SLU-F1 44.35** against the sealed closed-list direct baseline's **35.80** — **+8.55** under the
  official `evaluate.py`, and **above the locked BLEND cell's 41.69** with zero retrieval and zero
  knowledge supply.
* Paired per-sample slot F1 on the **unexposed NEW500**: **+10.11 pp** (CI90 [+8.11, +12.19], sign
  test p = 8.5e-16, 60 saves / 2 harms). Lower bound above 0. **Condition 1 met.**
* Paired against **KC-S1a**, the equal-contact control, on NEW500: **+10.02 pp**
  (CI90 [+8.01, +12.10], p = 9.1e-15, 60 saves / 3 harms). Lower bound above 0. **Condition 2 met:
  the schema is the lever, not the contact.**
* **KC-S1a is null, exactly as it should be.** One extra contact that asks for slots alone, given the
  intent and the 55-type list the system message already carries, moves the slot layer by
  **+0.09 pp** on NEW500 (CI90 [−0.20, +0.38], 2 saves / 1 harm) and **−0.09 pp** pooled. SLU-F1
  35.75 vs 35.80. A second look at the same audio with the same information is worth nothing.
* Intent is **identical by construction and asserted row by row**: 71.40 on all three arms, every
  paired intent contrast exactly 0.00 with CI90 [0.00, 0.00].

The closed-list verdict's closing sentence was that slot filling "is not a prompt problem: a closed
type list is exactly the intervention that should have helped, and it did not". This cell corrects
that: it is not the *type list* that helps, it is **which types this intent uses, with the fillers
TRAIN heard for them**. The same 55 names, re-organized per intent and priced by frequency, recover
9.5 points of entity F1.

## 1. The official table

Official `evaluate.py` at pinned commit `8eb1654…311f1` in `~/.venvs/slurp-official-eval` (used,
never modified), `--average micro --errors --table-layout csv`, over complete 1,000-row roster files,
never sharded. The port-vs-official identity check passed on all five scored sets at an absolute
difference of 0.0.

| arm | scenario | action | **intent** | entities strict | Word-F1 | Char-F1 | **SLU-F1** | n gold | n predicted | skipped | unparsed |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **KC-S1b (joined)** | 81.00 | 73.90 | 71.40 | **31.37** | **41.58** | **47.51** | **44.35** | 1000 | 1000 | 0 | 0 |
| KC-S1a (joined) | 81.00 | 73.90 | 71.40 | 21.82 | 33.62 | 38.17 | 35.75 | 1000 | 1000 | 0 | 0 |
| CLOSED-LIST (comparator) | 81.00 | 73.90 | 71.40 | 21.91 | 33.69 | 38.20 | 35.80 | 1000 | 1000 | 0 | 3 |
| DEV-1000 BLEND (locked cell, reference) | 83.90 | 77.60 | 75.70 | 27.27 | 39.41 | 44.24 | 41.69 | 1000 | 1000 | 0 | 2 |
| DEV-1000 M0 (sealed 2026-08-25) | 70.00 | 61.50 | 53.60 | 21.94 | 34.66 | 39.46 | 36.90 | 1000 | 1000 | 0 | 5 |

The CLOSED-LIST row is this read's **identity anchor**: it reproduces its own 2026-09-05 verdict to
the second decimal on all seven metrics, from the same sealed bytes.

**The primary metric needs no projection.** The slot contact answers `{"entities": [...]}`, which
`reproduction.slurp_scoring.parse_slu_response` accepts with scenario and action absent, and the
official script computes `entities`, both distance blocks and SLU-F1 from the entity lists alone
(`slu_f1` is fed only the two distance metrics). Scoring each arm's **sealed** rows as they stand
gives SLU-F1 44.35 / 35.75 and entities 31.37 / 21.82 — **the same numbers to every decimal** as the
joined view above, which is the read's own consistency check on the join. Those sealed-row scoring
jobs ran through `core.scoring_batch`, one job per manifest. What the projection adds is only the
scenario/action/intent columns.

**N-predicted.** Zero skipped rows anywhere, so the unanswered-counted-wrong variant equals the
official number throughout. The joined arms have zero unparsed rows by construction (the projection
always emits a well-formed object); as sealed, KC-S1a had 2 unparsed responses and KC-S1b 3.

## 2. Paired contrasts

`analysis.paired.paired_contrast`, delta = arm − comparator on per-sample official scores, stratified
bootstrap N = 10,000 seed 20260903, CI90, exact sign test. Strata are the gold scenario. The decision
population is the unexposed NEW500; pooled 1,000 and the prior-exposed DEV-500 are reported beside it.

**KC-S1b over the closed-list baseline**

| population | metric | closed-list | KC-S1b | delta | saves | harms | ties | p | CI90 |
|---|---|---|---|---|---|---|---|---|---|
| **unexposed 500** | **slot F1 (per sample)** | 14.49 | 24.60 | **+10.11** | 60 | 2 | 438 | 8.5e-16 | **[+8.11, +12.19]** |
| unexposed 500 | SLU-F1 (per sample) | 21.05 | 31.89 | +10.85 | — | — | — | 3.4e-15 | [+8.76, +12.94] |
| unexposed 500 | slot precision | 15.83 | 26.73 | +10.90 | — | — | — | 8.5e-16 | [+8.70, +13.10] |
| unexposed 500 | slot recall | 13.94 | 23.67 | +9.73 | — | — | — | 5.4e-17 | [+7.77, +11.70] |
| unexposed 500 | intent | 73.20 | 73.20 | **0.00** | 0 | 0 | 500 | 1 | [0.00, 0.00] |
| pooled 1000 | slot F1 (per sample) | 12.96 | 20.76 | **+7.80** | 97 | 7 | 896 | 2.3e-21 | [+6.48, +9.15] |
| pooled 1000 | SLU-F1 (per sample) | 19.75 | 28.45 | +8.71 | — | — | — | 2.4e-22 | [+7.33, +10.10] |
| prior-exposed 500 | slot F1 (per sample) | 10.90* | 16.20* | +5.30 | — | — | — | 4.4e-07 | [+3.70, +6.97] |

\* the prior-exposed half's recall row; its slot-F1 row is +6.57 CI90 [+4.82, +8.34].

**KC-S1b over KC-S1a — the schema, net of the contact**

| population | metric | KC-S1a | KC-S1b | delta | saves | harms | ties | p | CI90 |
|---|---|---|---|---|---|---|---|---|---|
| **unexposed 500** | **slot F1** | 14.59 | 24.60 | **+10.02** | 60 | 3 | 437 | 9.1e-15 | **[+8.01, +12.10]** |
| unexposed 500 | SLU-F1 | 20.98 | 31.89 | +10.91 | — | — | — | 5.3e-16 | [+8.83, +13.05] |
| pooled 1000 | slot F1 | 12.87 | 20.76 | +7.89 | 98 | 7 | 895 | 1.2e-21 | [+6.56, +9.23] |

**KC-S1a over the closed-list baseline — the contact alone**

| population | metric | closed-list | KC-S1a | delta | saves | harms | ties | p | CI90 |
|---|---|---|---|---|---|---|---|---|---|
| unexposed 500 | slot F1 | 14.49 | 14.59 | **+0.09** | 2 | 1 | 497 | 1 | [−0.20, +0.38] |
| pooled 1000 | slot F1 | 12.96 | 12.87 | −0.09 | 3 | 4 | 993 | 1 | [−0.35, +0.16] |
| pooled 1000 | SLU-F1 | 19.75 | 19.55 | −0.20 | — | — | — | 0.388 | [−0.53, +0.12] |

**Both weightings agree in sign** on every admitted contrast (per-sample slot F1):

| arm | pooled natural | pooled equal-stratum | NEW500 natural | NEW500 equal-stratum |
|---|---|---|---|---|
| closed-list | 12.96 | 12.62 | 14.49 | 13.50 |
| KC-S1a | 12.87 | 12.53 | 14.59 | 13.58 |
| **KC-S1b** | **20.76** | **20.17** | **24.60** | **23.91** |

**Gain per extra contact.** Both cells add exactly one contact per row over the one-contact direct
baseline (1,000 realized contacts each, no row took two). KC-S1a buys −0.05 SLU-F1 for that contact;
KC-S1b buys **+8.55 SLU-F1**. Net of the equal-contact control, the schema is worth +8.60 SLU-F1.

## 3. Per stratum (per-sample slot F1, pooled 1,000)

| scenario | n | closed-list | KC-S1a | KC-S1b | S1b − CL | saves | harms |
|---|---|---|---|---|---|---|---|
| alarm | 58 | 10.5 | 11.6 | 14.2 | +3.7 | 4 | 0 |
| audio | 30 | 0.0 | 0.0 | 3.3 | +3.3 | 1 | 0 |
| calendar | 61 | 5.9 | 6.4 | 14.8 | +8.9 | 7 | 0 |
| cooking | 37 | 18.0 | 16.2 | 28.8 | +10.8 | 4 | 0 |
| datetime | 61 | 14.4 | 14.4 | 21.0 | +6.6 | 4 | 0 |
| email | 61 | 13.4 | 13.4 | 16.9 | +3.6 | 3 | 0 |
| general | 61 | 1.6 | 1.6 | 6.0 | +4.4 | 3 | 0 |
| iot | 61 | 23.5 | 23.5 | 35.0 | +11.5 | 7 | 0 |
| lists | 60 | 6.7 | 6.7 | 11.7 | +5.0 | 3 | 0 |
| music | 51 | 7.8 | 7.8 | 7.8 | **0.0** | 0 | 0 |
| news | 60 | 11.9 | 11.1 | 13.9 | +1.9 | 2 | 1 |
| play | 60 | 28.6 | 27.5 | 30.9 | +2.3 | 3 | 1 |
| qa | 60 | 24.2 | 24.2 | 30.8 | +6.7 | 4 | 0 |
| recommendation | 60 | 28.8 | 27.7 | 33.3 | +4.4 | 3 | 1 |
| **social** | 60 | 5.3 | 5.3 | **36.2** | **+30.9** | 22 | 0 |
| takeaway | 39 | 10.4 | 12.1 | 12.1 | +1.7 | 3 | 2 |
| transport | 60 | 9.0 | 9.0 | 22.7 | +13.6 | 12 | 2 |
| weather | 60 | 6.9 | 6.9 | 23.6 | +16.7 | 12 | 0 |

**Every one of the eighteen scenarios is flat or better; none is harmed.** The gain concentrates
where the intent narrows the type space hardest: `social` (+30.9 — the schema tells the model that a
social post carries `media_type`), `weather` (+16.7), `transport` (+13.6), `iot` (+11.5). `music` is
the one scenario that does not move at all.

## 4. Per entity type (strict, exact type+filler, pooled 1,000)

Top twenty of 51 gold types by gold mention count; 950 gold mentions in total.

| entity type | gold | closed-list tp | KC-S1a tp | KC-S1b tp | CL recall | KC-S1b recall |
|---|---|---|---|---|---|---|
| date | 159 | 11 | 12 | 33 | 6.9 | **20.8** |
| place_name | 118 | 27 | 26 | 37 | 22.9 | 31.4 |
| media_type | 70 | 2 | 1 | 26 | 2.9 | **37.1** |
| time | 67 | 3 | 3 | 7 | 4.5 | 10.4 |
| person | 56 | 8 | 8 | 10 | 14.3 | 17.9 |
| food_type | 42 | 9 | 10 | 13 | 21.4 | 30.9 |
| event_name | 42 | 1 | 1 | 2 | 2.4 | 4.8 |
| business_name | 36 | 5 | 5 | 5 | 13.9 | 13.9 |
| transport_type | 31 | 1 | 1 | 9 | 3.2 | **29.0** |
| business_type | 28 | 8 | 8 | 9 | 28.6 | 32.1 |
| weather_descriptor | 27 | 1 | 1 | 4 | 3.7 | 14.8 |
| news_topic | 27 | 7 | 6 | 7 | 25.9 | 25.9 |
| timeofday | 22 | 2 | 2 | 4 | 9.1 | 18.2 |
| device_type | 22 | 4 | 4 | 12 | 18.2 | **54.5** |
| list_name | 19 | 4 | 4 | 6 | 21.1 | 31.6 |
| order_type | 18 | 3 | 3 | 4 | 16.7 | 22.2 |
| artist_name | 14 | 6 | 6 | 6 | 42.9 | 42.9 |
| relation | 14 | 3 | 3 | 3 | 21.4 | 21.4 |
| definition_word | 14 | 9 | 9 | 9 | 64.3 | 64.3 |
| music_genre | 13 | 4 | 4 | 4 | 30.8 | 30.8 |

Totals: 173 true positives for the closed-list baseline, 172 for KC-S1a, **263 for KC-S1b**; false
positives 370 → 415. **The types that do not move are the ones already at their ceiling**
(`definition_word` 64.3, `artist_name` 42.9, `music_genre` 30.8) or the ones whose filler is an open
proper noun the schema cannot enumerate (`business_name`, `event_name`, `person`). The types that
move most are the ones whose surface form TRAIN can actually exhibit: `device_type` 18.2 → 54.5,
`media_type` 2.9 → 37.1, `transport_type` 3.2 → 29.0, `date` 6.9 → 20.8.

## 5. Where the slot layer actually moved

| arm | predicted entity mentions | rows with no entity | strict precision | strict recall | strict F1 |
|---|---|---|---|---|---|
| closed-list | 547 | 514 (51.4 %) | 29.98 | 17.26 | 21.91 |
| KC-S1a | 544 | 519 (51.9 %) | 29.96 | 17.16 | 21.82 |
| **KC-S1b** | **682** | **397 (39.7 %)** | **37.54** | **26.95** | **31.37** |

The closed-list verdict diagnosed the slot layer as **recall-limited and over-conservative**: naming
the 55 legal types stopped the model inventing types "but also stopped it guessing". The schema
un-sticks exactly that. KC-S1b answers on 117 more rows and produces 135 more mentions than the
baseline, and **precision rises with recall** (29.98 → 37.54) rather than trading against it — the
extra mentions are mostly right. Both directions of the paired contrast confirm it: precision
+10.90 pp and recall +9.73 pp on NEW500, each with a CI90 well clear of zero.

## 6. The schema, and the rows it could not serve

The block sent per row is that row's predicted intent's TRAIN profile: entity types holding at least
2 % of the intent's TRAIN slot mentions, each with its share and up to five lower-case example
fillers (`data.slurp.render_slurp_slot_schema_for_state_detail`; schema content hash
`732e500a…7dcc`, source split `train`, 60 intents).

* **958 of 1,000 rows** received a per-intent block, drawing on **58 distinct intents** — 494 to 1,224
  characters each.
* **42 rows (4.2 %)** fell back to the full 60-intent schema, because the sealed closed-list response
  for that row does not parse (3 rows) or names a (scenario, action) pair TRAIN never carries
  (39 rows). That is exactly the closed-list arm's own 4.20 % impossible-pair rate, arriving here as
  a schema-selection miss. Their ids are listed in the prompt-fit receipt. This is the cell's one
  soft edge, and it is what cell USE-2c (top-2 union schema) was reserved for.
* The fallback block is what forced the serving geometry: 26,720 characters, about 7,500 tokens.

## 7. Distance to the published brackets

Owner rule: aligned = within 3 points, or better. Every published row is the official TEST split and
a natural mixture; this is a scenario-stratified DEV roster, and **no published prompt-only SLU-F1
computed with this script exists for any audio LLM**, so no like-for-like target is available and
none is claimed.

| metric | KC-S1b | published target (system, split) | delta | verdict |
|---|---|---|---|---|
| SLU-F1 | 44.35 | Google/SF-ID 64.02 (weakest published pipeline, test) | −19.67 | not aligned; **floor still failed, by 19.67 instead of 28.22** |
| SLU-F1 | 44.35 | Multi-SLURP/HerMiT 70.84 (best in the paper, test) | −26.49 | not aligned |
| SLU-F1 | 44.35 | this study's locked BLEND cell 41.69 (DEV-1000) | **+2.66** | **better**, with no retrieval |
| SLU-F1 | 44.35 | ChatGPT prompt-only slot F1 12.03–13.35 | +31.0 to +32.3 | better, but a **different metric definition** |
| intent | 71.40 | Google/SF-ID 72.06 | −0.66 | **aligned** (unchanged: intent is the baseline's) |

**30 % of the 28.22-point gap to the weakest trained pipeline closes on prompt-side knowledge
organization alone.** The remaining 19.67 points are the honest distance left to a system trained on
SLURP.

## 8. What this does to the knowledge plane's SLURP claim

The 2026-09-05 closed-list verdict showed 80.5 % of the locked BLEND cell's SLURP **intent** margin
was a label-inventory effect. This cell is the counterpart on the slot side: **KC-S1b beats BLEND's
SLU-F1 (44.35 vs 41.69) with zero retrieval, zero embedding contacts and zero knowledge supply** —
one extra prompt-side block per row, mined model-free from TRAIN. What retrieval still has to justify
on this carrier is what it adds *over* an organized per-intent schema, not what it adds over a
prompt-defective baseline.

It also, for the first time on this carrier, separates **construction** from **consumption**
empirically: KC-S1a is the consumption change alone (one more contact, same information) and is worth
nothing; KC-S1b adds the constructed artifact and is worth ten points. Under the program's three
dimensions, that is a clean attribution to knowledge construction.

## 9. Mechanics, cost and provenance

| item | KC-S1a | KC-S1b |
|---|---|---|
| run id | `SAEA-SLURP-KC-S1A-SLOTS-DEV1000-V1` | `SAEA-SLURP-KC-S1B-SLOTS-SCHEMA-DEV1000-V1` |
| attempt | `attempt-20260906T023017Z-38c20a` | `attempt-20260906T025102Z-af6b04` |
| study commit at takeoff | `782c6ac8` | `d737e354` |
| config hash | `212b35ff…9194` | `b0edd683…3802` |
| sealed manifest sha256 | `80f49ac029e4a8b41c22cb0ccb82ff2323f600b2c16502a78c99324fb9cfd617` | `088c9307a39f38db124a5204793806e9a8589d942259b15e7826ad2685fe8d08` |
| phases file sha256 | `8677f8f5…` | `ff2657e2…` |
| contacts | 1,000 in 531.3 s | 1,000 in 735.9 s |
| prompt / completion tokens | 2,443,616 / 16,395 | 2,965,694 / 21,607 |
| spend | 1,000 calls, 2,884.7937 audio s, ~0.15 GPU-h | 1,000 calls, 2,884.7937 audio s, ~0.20 GPU-h (plus the aborted attempt's 206 calls / 552.9527 s) |
| attempt state | FINALIZED | FINALIZED |
| scoring | `core.scoring_batch`, 1 job, 53.5 s | 1 job, 52.2 s |

Common to both: frozen Qwen3-Omni-30B-A3B-Instruct GGUF Q4_K_M, llama.cpp featcache build `04ccc72a`,
mmproj-free over the DEV-1000 promotion receipt's packets; greedy, temperature 0, seed 20260803,
max_tokens 64; geometry `-np 4 -c 65536`; system message byte-identical to the sealed closed-list
baseline's (7,583 chars, sha256 `4073f79e…37db`); knowledge snapshot `07f94807…fa65` bound with empty
bootstrap ids; policy `phase-slots-given-intent-v1` through `rails.phase_runner.run_program`, phase
material from the baseline fragment alone; gold never enters the flight process (the adapter's
`gold()` refuses outright); the held-out test split is never named, loaded or scored.

**Prompt fit, before either flight** (`prompt-fit.json`, zero generated tokens, 2,000 envelopes
measured through the resident server's `/apply-template` + `/tokenize`):

| cell | text tokens min / p50 / p95 / max | worst envelope | margin at 16,384/slot |
|---|---|---|---|
| KC-S1a | 2,390 / 2,394 / 2,418 / 2,439 | 2,563 | +13,757 |
| KC-S1b | 2,504 / 2,624 / 2,713 / **9,900** | **10,006** | **+6,314** |

The worst KC-S1b envelope would **not** have fitted an 8,192-token slot, which is why both cells fly
at `-np 4`. The same pass asserted, on all 1,000 rows, that every KC-S1b contact instruction is the
KC-S1a one plus a per-sample suffix (496 to 26,722 characters, median 900) and that the two cells'
system messages are byte-identical.

## 10. Deviations, defects and fixes

1. **A program-level blocker found before takeoff: the leakage rule versus SLURP's own vocabulary.**
   Every phase program binds a knowledge snapshot even when all its phases declare
   `knowledge: "none"`, because `rails.runner.run_speech_native_agent_loop` requires one, and
   `_assert_agent_control_excludes_knowledge_payloads` is enforced against it. The default
   `size-full` SLURP snapshot's `content` dimension carries one facet per TRAIN utterance whose
   representation is the utterance text, and SLURP has one- and two-word utterances. Measured: with
   that snapshot bound, the rule refuses **78 of the 1,000 sealed closed-list responses** (58 of them
   for the word `calendar`) and **all 60 per-intent schema blocks** (for `how much`, which the schema
   header contains). **This blocks every SLURP phase cell, not just these two** — KU-S1c and KU-S3
   would have died the same way, and so would any cell whose prompt says `calendar`. Resolution, the
   one `data.slurp.render_slurp_intent_slot_schema` itself prescribes: exclude the content dimension
   from the bound snapshot (`KnowledgeBuildSpec.validate` explicitly allows any set containing
   `content` **or** `label`). `scripts/build_knowledge_snapshot.py` gained `--dimensions`; the
   resulting snapshot keeps every one of the 11,514 exemplar values and every label, speaker and prior
   facet — 11,863 protected payloads, the strictest snapshot these cells can send at all — and
   measures **zero** collisions against the full schema, all sixty blocks and all 1,000 sealed
   responses. **For the owner:** KU-S1 actually consumes facets and cannot take this way out; it needs
   its own ruling.
2. **Serving geometry `-np 4` instead of the baseline's `-np 8`.** Per-slot context, not throughput
   (section 9). Both cells share it, so their contrast is geometry-matched; the comparator is a sealed
   manifest, as the program requires precisely because greedy decoding is not bitwise reproducible
   across batch shapes.
3. **`FlightRuntime`'s pre-flight prompt budget cannot see these prompts.**
   `_phase_prompt_payloads` renders one representative request per phase with a fixed 256-character
   pad in place of the predecessor state and applies no `state_fill`, and `rails.context_budget`'s
   registered `PER_SLOT_LIMIT_TOKENS` is 32,768 rather than the physical `-c / -np`. Its ALLOW is not
   evidence for a cell like this. Reported, not patched: `core/flight/runtime.py` is owned by another
   track this wave. `scripts/slurp_kc_s1_prompt_fit.py` measures the real envelopes instead.
4. **One new seam, config-native.** `rails/phase_material.py` gained a `state_fill` key: a phase may
   name a registered per-sample fill and `build_material_for_phase` appends its text after the
   predecessor state. Resolution goes through the new `PHASE_STATE_FILLS` registry from config alone,
   so `core/flight/runtime.py` needed no change at all. Twelve unit tests pin the append order, the
   pure-suffix property, the registry resolution and every refusal.
5. **KC-S1b took its one permitted recovery.** Attempt `attempt-20260906T024148Z-af6b04` was ABORTED
   after 206 of 1,000 contacts when the llama.cpp featcache server died with a CUDA illegal memory
   access (`ggml-cuda.cu:104`, in `ggml_backend_cuda_synchronize`, at task 1446); the agent loop saw
   `Remote end closed connection without response` and the flight aborted itself, leaving 206 calls
   and 552.9527 audio seconds durably spent. Nothing about the cell changed on the re-fly — same
   fragments, geometry, roster and prompt bytes; only the plan cells grew, because calls and audio are
   metered cumulatively across every attempt of a run id (1,300 calls, 3,600 audio seconds, GPU
   ceiling 2.0). This was a GPU fault, not a contract or budget failure, and it is the fifth CUDA-side
   abort this program has seen on this build; the recovery flight passed the same point (206) without
   incident. A second failure would have stopped the flight.
6. **194 KC-S1a and 456 KC-S1b responses volunteered a `scenario`/`action` despite being told not to.**
   The projection overwrites both from the sealed closed-list row regardless, so intent is identical by
   construction; the counts are recorded because they are the honest measure of how well the "do not
   repeat it" instruction held.
7. **Two run ids, one per cell**, each with its own experiment fragment, plan, exposure row and single
   recovery allowance — `core.attempts` keys on `(run_id, attempt_id)` and a shared run id would have
   metered both cells against one budget and spent the recovery on whichever failed first. The 4-row
   smoke used one run id for both cells because its numbers are never read.

## 11. What this authorizes

KC-S1b becomes **the SLURP slot mechanism the next cells build on**: USE-2b (the model's own
transcript as the extraction source), USE-2c (the top-2 union schema, aimed squarely at the 42
fallback rows), KU-S3 (`phase-intent-then-slots-v1`, which now has a real slot stage to fold in), and
EVO-S1, whose evolution loop was always going to evolve this artifact. Under the claim ladder this is
**rung 1 only**: admission on n = 500 unexposed dev rows. Rung 2 is a same-roster replication at a
different serving geometry, and rung 3 the reserved `DEV-500-B`.

It authorizes nothing else: no test contact, no superiority claim, no generalization claim, no
Stage-3 activity. The number that leaves this cell is 44.35 SLU-F1 on a scenario-stratified DEV
roster — 19.67 points below the weakest published trained pipeline, and not yet compared to anything
like for like.
