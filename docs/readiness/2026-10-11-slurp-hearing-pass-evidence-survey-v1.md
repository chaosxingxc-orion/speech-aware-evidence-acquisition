# Hearing-pass evidence survey for owner decision 261 option B (SLURP entities)

Read-only survey, 2026-10-11. Study repo `D:\chao_workspace\exploring-l4-intelligence\studies\speech-aware-evidence-acquisition`
at master `1382c777e`. No model, server, GPU or WSL contact. Paths below are relative to the study root. Only counts,
rates, pp, type names and ids are quoted. No utterance text, transcript, gold value or model output is quoted.

**What is being designed** (decision 261-B, ruled 2026-10-11, `docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md:1039-1050,1081-1084`):
the core itself in a hearing-only role, asked by the Solver (model-initiated, decision 206) for the spoken words of one
entity span per candidate slot type, returning words only. The coordinator's estimate in the same entry: "0 engineering
reuse of E4 is possible; expected value unknown, ceiling bounded by the 106 hearing-type misses (~5 pp oracle)".

---

## 1. The E4 / E4-1 core-native "relisten" family: CLOSED, SHADOW HARM

### 1a. The exact contract that flew

| item | value | source |
| --- | --- | --- |
| who asked | **the system**: a post-accept stage after ACCEPT and the deliver normaliser, fired on up to 3 delivered entities per row in delivery order, with no type filter. Module design 2d names this "the default-applied pattern this section bars" | `src/speech_aware_evidence_acquisition/rails/relisten.py:1-50`; `docs/superpowers/specs/2026-09-29-slurp-consumption-module-design.md` sec 2d table |
| contact 1 (blind) | the same full speech packet (no cut, no derived media), the decided intent and the slot type. The delivered value `c` is never shown. Template `configs/probes/slurp_relisten_blind_v1.txt`: one value, "at most 8 English words, in the speaker's own words", `heard=false` if not stated. Strict json_schema `slurp-relisten-value-v1` `{"heard": bool, "value": string}` | `rails/relisten.py:137-175`; template file |
| contact 2 (forced choice) | fired when the blind value is not canonically equal to `c`, and also on blind `heard=false` or an unparsed blind. Options A/B are `c` against the blind value, or `c` against the sentinel `[no value heard]`, in an order fixed by sha256(sample_id, slot_type). Schema `{"choice": "A"/"B"/"neither"}` | `rails/relisten.py:14-35, 503-520`; `configs/probes/slurp_relisten_confirm_v1.txt` |
| equality | `canonical_value` = the pinned P2 filler normaliser plus a token-wise number-word fold | `rails/relisten.py:282-316` |
| consumption | SHADOW only. The delivered answer was never changed. Offline `bind()` rendered two columns: (a) replace `c` by `v` when the blind value differed AND the confirm chose it; (b) = (a) plus drop when both contacts voted unheard. Only value hashes were sealed (`saea-relisten-v1`, the "no transcript state" rule) | `rails/relisten.py:30-50, 931-981` |
| program / ceiling | `phase-native-candidates-review-revise-relisten-v1`, ceiling 17 contacts per row (6 of them relisten) | `docs/readiness/2026-09-29-slurp-stage3-e4-relisten-fold-a-v1-preregistration.md` |
| roster / design | TRAIN Fold A 1,080 rows; `same-flight-shadow-relisten`; expected 0.0 pp; provisional null 0.3163 pp | same |

### 1b. Outcome

| measure | replace-only | replace + drop-unheard | source |
| --- | --- | --- | --- |
| official SLU-F1 (delivered 64.02) | 59.91, **-4.11 [-5.41, -2.88]** | 60.42, **-3.59 [-5.08, -2.14]** | `docs/results/2026-09-29-slurp-e4-relisten-fold-a-column-read.md` sec 3 |
| equal-scenario weighting | -3.92 [-4.96, -2.77] | -3.13 [-4.51, -1.62] | same |
| span-F1 | -6.22 [-8.15, -4.40] | -5.57 [-7.62, -3.54] | same |
| row saves / harms / ties | 14 / 66 / 1,000 | 17 / 83 / 980 | same |
| intent | identical by construction (0 of 1,080 rows) | identical | same |
| pre-declared gate | net conversion of the 106 items >= 29 %: measured **2.83 %** (4 converted, 1 broken) | >= 49.5 net FP removed: measured **40** (48 SPURIOUS removed, 8 not-in-note EXACT lost) | same, sec 5 |
| verdict | SHADOW HARM, NOT NOMINATED. "Core-native replacement re-listen is CLOSED" | same | same, coordinator verdict |

### 1c. Per stratum (SLU-F1 delta pp, n = 60 per scenario)

| scenario | replace-only | replace + drop |
| --- | --- | --- |
| alarm | **-16.69 [-24.67, -8.66]** | -16.69 |
| iot | **-13.09 [-22.07, -3.48]** | -11.25 [-21.03, -0.45] |
| lists | -9.32 [-15.24, -3.12] | -8.16 |
| calendar | -7.02 [-11.73, -2.37] | -7.47 |
| datetime | -7.07 [-15.23, 0.00] | -6.26 |
| email | -5.87 [-11.83, -1.23] | -5.01 |
| transport / takeaway / music / weather / recommendation | -2.88 / -2.17 / -2.29 / -1.81 / -1.45 | -2.16 / -1.86 / +3.47 / -5.04 / -1.45 |
| social / qa / cooking / general | +1.16 / 0.00 / 0.00 / 0.00 | +2.35 / +2.58 / +0.24 / -0.25 |

By channel (row-SLU pp): replace-only far-field -1.89, headset -1.56; replace + drop -2.61 and -2.76. Source: E4 read sec 3.

### 1d. Why it harmed (the mechanism read)

| fact | value | source |
| --- | --- | --- |
| gold-side state transitions, delivered -> replace-only | EXACT 528 -> 467; BOUNDARY 69 -> 127 | E4 read sec 4 |
| **EXACT -> BOUNDARY** among 122 accepted replacements | **63**; only 7 replacements repaired an item to EXACT | same |
| EXACT -> BOUNDARY by type | date 11, time 10, timeofday 9, house_place 5, list_name 5, color_type 4, food_type 4, relation 4, place_name 3, time_zone 3 | same |
| accepted replacements by type | time 22, date 13, timeofday 12, food_type 7, house_place 6, place_name 6, list_name 5, podcast_descriptor 5, 21 more types at 1-4 | same, sec 6 |
| blind dispositions over 1,015 triggered entities | value 336, **unheard 679** (67 %: the blind core said the speech does not state a value the Solver had delivered) | same, sec 6 |
| confirm votes (874 fired) | delivered 684, candidate 176, neither 14 | same |
| coordinator reading | "The loss is the blind contact's SPAN ... Hearing is not the source of the loss." "The core cannot verify its own hearing by blind + forced-choice re-listen" | same, sec 7 and verdict |
| independent check | Whisper large-v3 contained the delivered exact value on 59 / 63 (0.9365) of the E4-broken items, so those items were heard correctly the first time | `docs/results/2026-09-30-slurp-e5-transcript-consistency-oracle-read.md` sec 1 (Q3) |
| only positive part | drop-only: SPURIOUS 258 -> 208 for 8 correct items lost, about +0.8 pp offline (+0.51 pp between the two columns), under the 1.49 floor | E4 read sec 7 and verdict |

### 1e. Cost and the seal abort

| item | value | source |
| --- | --- | --- |
| relisten contacts | 1,889 = 1.749 per row = **29.96 %** of the flight's 6,304 contacts | E4 read sec 6 |
| relisten speech seconds | 6,096.6 s (32.55 % of the flight); about 3.2 s per contact (the full packet is re-sent) | same |
| relisten prompt tokens | 4,502,291 (about 2,380 per contact; 10.60 % of the flight) | same |
| relisten summed server compute / call latency | 0.497 h (8.14 %) / 2,179.9 s (9.14 %) | same |
| registered caps | generation 18,360 calls = 1,080 x 17; FIT 73,440 = 1,080 x 17 x (1 + 3) | `docs/readiness/2026-09-29-slurp-stage3-e4-relisten-fold-a-v1/{generation,fit}-plan-registered-v1.json` |
| seal abort | all 1,080 rows flew, then the seal ABORTED with `finite source is not the last actual sample contact`. Post-delivery shadow relisten contacts followed a finite-completion (deliver-latest-or-abstain) source on 8 of 10 finite rows (0.9 % row rate, which a 4-row smoke cannot show). Fixed at `b286d897`: the seal allows only the row's own relisten contacts after the source, and resume replay rebuilds the relisten receipt (it is never in the trace). Recovered seal-only, 0 GPU (decision 194) | memory `e4-seal-abort-finite-relisten.md`; E4 read sec 1-2 |
| read-path defects | the read script hard-coded the aborted attempt. AT1 refused because 976 of 1,080 delivered texts are the core's compact JSON. Relisten contacts had to be read from the predecessor trace | E4 read sec 2 |

---

## 2. E5 / E5-0 / E5-1 Whisper oracles, S2a.1, and retrieval-key recall

### 2a. E5-1 transcript-consistency oracle (verify-span route): CLOSED

| measure | value | source |
| --- | --- | --- |
| instrument | E5-0: one pinned Whisper large-v3 pass on Fold A and Fold B, 1,080 rows each, 0 core contacts | `docs/results/2026-09-30-slurp-e5-transcript-consistency-oracle-read.md` sec 0 |
| Q6 gold-span containment | Fold A **707 / 941 = 0.7513**; Fold B **718 / 944 = 0.7606**; stop floor 0.80 -> **FAIL** | sec 1 |
| containment by type (Fold A) | business_name 0.50, person 0.548, time 0.724, food_type 0.769, place_name 0.79, media_type 0.825, date 0.848, event_name 0.878 | sec 1 |
| Q3 exact preservation on E4's 63 broken items | 0.9365 (pass) | sec 1 |
| wrong delivered values the transcript still "supports" (AGREE) | BOUNDARY 0.680, FORMAT 0.545, NEAR 0.571, WRONG-VALUE 0.341, WRONG-TYPE 0.804, SPURIOUS 0.585 | sec 2 |
| system-applied rules (oracle bounds only) | R-DROP tuned **-2.31 [-3.65, -1.00]**; R-SWAP tuned -0.03 [-0.14, +0.07]; R-SWAP theta 0.6 -0.50; every point <= 0 on all four arms | sec 3 |
| decision oracle | 29 / 1,080 helpful rows (2.69 %); flag precision 0.1215; perfect-repair ceiling **+1.62 [+1.04, +2.28]** (comp1b +1.21) | sec 4 |
| best model-visible signal | AUC 0.6713 (E4 blind/confirm disagreement), 0.6642 (delivered entity count); cross-fit two-signal AUC 0.6707; precision **0.0727 at a 10 % call rate** | sec 4 |
| proposed 206 gate | call-rate band [0.0134, 0.1074]; precision bar b + 0.10 = 0.1269; met only at the 15-row low end (2 hits) | sec 5 |
| survivor | MISSING spans contained in the transcript: 113 items on 106 rows; repair + add oracle **+8.21 [+6.95, +9.57]** (comp1b +8.89); wider-label cross-fit precision 0.2455 at 10 % (bar 0.2231). This assumes perfect span and type selection | sec 4-5, verdict |

### 2b. Transcripts in the Omni prompt (fixed all-row supply, 2026-09-12; old base, SLU about 39)

| population | SLU-F1 micro pp | intent (scenario_action) pp | source |
| --- | --- | --- | --- |
| NEW500 (primary) | +0.83 [-1.10, +2.83] (CI90) | -0.80 [-2.11, +0.40] | `docs/readiness/2026-09-12-slurp-fixed-whisper-result-v1.md` |
| OLD500 | -0.83 [-2.50, +0.79] | -1.00; action -1.60 [-2.98, -0.19] | same |
| DEV1000 | +0.02 [-1.23, +1.24] | **-0.90 [-1.68, -0.09]** | same; cited as an engineering finding in registry row 201 |

### 2c. S2a.1 missing-slot proposal tool, recall ceiling (70 not-in-supply MISSING items, COMP-1b Fold A)

| setting | T (hits / 70) | source |
| --- | --- | --- |
| contract (top 3, <= 5 tokens, trigram-Jaccard >= theta, draft-filtered), primary lexicon | **6 / 70 = 0.086** | `docs/results/2026-09-30-slurp-s2a1-missing-slot-recall-ceiling-offline.md` sec 1 |
| full-TRAIN lexicon | 12 / 70 = 0.171 | same |
| perfect ranker over Whisper | 33 / 70 = 0.47 | same |
| containment on these 70 | 35 / 70 = 0.50 (against 0.75 over all gold) | same |
| bar for reading (a) at CONV uptake 0.457 | T >= 0.738 (52 / 70) | sec 3 |
| misses (contract) | 35 not in transcript, 27 below theta, 2 overlap the draft | sec 2 |
| per type | place_name 13 (7 not in transcript), business_name 7 (5), date 5, person 5 (3), media_type 4 | sec 2 |
| false candidates on rows with no MISSING item | 2.30 % of calls non-empty (primary), 3.18 % (full TRAIN), all false | sec 2 |
| perfect-ASR addendum | of the 35 not-in-Whisper items, 28 are in the reference (ASR misses: place_name 7, business_name 4, media titles 6) and 7 are in neither (5 spacing forms, 2 derived). Perfect ASR + perfect ranker 61 / 70 = 0.871; the contract tool on perfect text stays at 10-26 / 70 (0.14-0.37) | addendum A.1-A.4 |
| ranker study | best TRAIN logistic ranker: reference T 43-49 / 70 at 2.3-10 % false-candidate budget, Whisper T 23 / 70; gate 52 / 70 not cleared | memory `s2a1-recall-ceiling-closed-2026-09-30.md` (`docs/results/2026-09-30-slurp-s2a-ranker-study-offline.md`) |
| status | S2 line closed at this ASR. The Qwen3-ASR probe E6 and cascade question were withdrawn by the owner on 2026-10-09 ("Cancel the Qwen3-ASR exploration ...") | `docs/readiness/2026-10-09-slurp-nx-node-extreme-programme-v1.md` F3, closing paragraph |

### 2d. Retrieval-key recall (intent; relevant only as a closed evidence kind)

| fact | value | source |
| --- | --- | --- |
| best pinned-vector key presence gain | +0.1 / +0.4 pp over centroid+agreement (1,048 / 1,080 already in block) | memory `retrieval-key-recall-2026-09-30.md` (`docs/results/2026-09-30-slurp-retrieval-key-recall-offline.md`) |
| K6p (centred centroid) | gold to rank 1 on +22 / +26 rows; P-SV-4 read -0.19 [-0.56, +0.19] intent, NOT NOMINATED; "intent levers exhausted" | memory `psv4-read-2026-10-09.md` |

---

## 3. The hearing-type miss population

### 3a. AGREE arm, Fold A (consumption-headroom note)

Source: `docs/results/2026-09-29-slurp-slu-consumption-headroom-offline.md`. Sealed totals TP 1,434 / FP 846.821 / FN 686.821, SLU-F1 65.1575.

| set | items | exact oracle pp | conversion measured | notes |
| --- | ---: | ---: | --- | --- |
| delivered gold-side errors | 407 | -- | -- | node-gain ledger counts 407 / 107 / 103 / 55 / 71 / 229 / 253 / 74 / 35 / 142 |
| **hearing-visible** (note near / partial) | **71** (69 rows) | 3.47 | E4-1: about 0 | 47 of the 71 are E5 (audio-only) |
| **re-listen addressable** (BOUNDARY / NEAR / FORMAT with the gold contiguous in the note) | **35 of 142** (BOUNDARY 29) | 1.55 | E4-1 | -- |
| union | **106** (104 rows) | **5.13** | E4-1 net 2.83 % | 1.5 pp alone needs 0.29 of the oracle |
| consumption, gold span contiguous in the note | 103 (MISSING 44) | 6.29 | Reviewer analogue 1 repaired / 1 broken | -- |
| SPURIOUS not in the note / in the note | 179 / 74 | 5.76 / 2.27 | E4 drop: 40 net | harm channel: 273 delivered-exact items are not in the note |

The 229 "undetermined" items (sec 3):

| class | items | MISSING | not MISSING | oracle pp |
| --- | ---: | ---: | ---: | ---: |
| E1 exemplars print the gold (type, value) | 91 | 55 | 36 | 5.12 |
| E2 value printed under another type | 1 | 0 | 1 | 0.09 |
| E3 a delivered card names the value | 15 | 13 | 2 | 0.99 |
| E4 not supplied, but in TRAIN's value list | 40 | 25 | 15 | 2.33 |
| **E5 nowhere but the audio** | **82** | **20** | **62** | 3.89 |

So 107 / 229 are consumption, not hearing (consumption total 214 / 407), and 82 are audio-only. The note names the 62
non-MISSING E5 items "the natural target of a hearing mechanism".

Exchange rates on this arm: 1 FP removed about 0.03 pp; 1 FN recovered about 0.06 pp. 1.5 pp = 24.8 recovered misses,
49.5 removed FPs, or 16.5 of each (sec 1).

### 3b. COMP-1b, Fold A and DEV-2000-ADDED (NX exchange-rate note)

Source: `docs/results/2026-10-09-slurp-nx-exchange-rates-offline.md`. Pools: Fold A SLU 63.61 / intent 85.65; DEV 65.93 / 81.50.

| class at the Solver (s1) | Fold A total | E1 | E2 | E3 | none | DEV total | E1 | E2 | E3 | none |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| SPURIOUS | 264 | 100 | 5 | 27 | 132 | 245 | 86 | 9 | 23 | 127 |
| **MISSING** | **188** | 103 | 1 | 14 | **70** | 187 | 94 | 0 | 14 | 79 |
| WRONG-TYPE | 54 | 14 | 4 | 2 | 34 | 67 | 21 | 4 | 2 | 40 |
| **BOUNDARY** | **68** | 29 | 0 | 1 | 38 | 74 | 27 | 1 | 1 | 45 |
| NEAR | 57 | 19 | 0 | 0 | 38 | 36 | 7 | 0 | 0 | 29 |
| **WRONG-VALUE** | **42** | 8 | 1 | 0 | **33** | 47 | 10 | 0 | 0 | 37 |
| FORMAT | 40 (10 delivered) | 14 | 0 | 1 | 25 | 44 (10) | 15 | 0 | 0 | 29 |
| EMPTY-GOLD-FILL (rows) | 161 / 414 | | | | | 138 / 314 | | | | |

The brief's labels map as follows. The note's supply classes are E1 / E2 / E3 / none. "none" = value not in the
supply, which covers the headroom note's E4 + E5. The S2a.1 70 = the Fold A MISSING "none" cell.

| per type (sec 3.1, top by gold; exact s1 / d) | Fold A | DEV |
| --- | --- | --- |
| date | 138 gold, 63 / 66 exact | 177, 102 / 107 |
| place_name | 100, 57 / 63 | 83, 52 / 56 |
| time | 76, 38 / 48 | 68, 40 / 44 |
| business_name | 52, 18 / 19 | -- |
| person | 42, 19 / 22 | 84, 40 / 51 |
| event_name | 41, 19 / 21 | 115, 71 / 72 |
| largest MISSING type at s1 | date 46, place_name 17, order_type 15, transport_type 14 | date 43, event_name 25, media_type 17, player_setting 14 |

Rates: +1 recovered MISSING = +0.062 / +0.057 pp; +1 repaired wrong entity = +0.091 / +0.085; 1.5 pp = 24-27
recovered MISSING or about 16-18 repaired wrong entities. s1 -> d transfer: d exact | s1 exact 99.4 %, d exact | s1
wrong 4.2-4.8 %. Errors grow with prompt length (MISSING Q1 -> Q4 37 -> 57). Solver contact today: tool schemas 0,
response_format none, tool_choice none, max_tokens 512, 0 completions at the cap (sec 3, 6).

### 3c. PLAN bad-case bank (v2.0 plan, 2026-09-24)

Source: `docs/results/2026-09-24-slurp-plan-bad-case-bank.md`.

| fact | Fold A | DEV-2000-ADDED |
| --- | --- | --- |
| same-type filler-distance pairs (shape) | 168 (37.1 % of FP+FN mass); 164 have no surface repair rung; 77 are boundary containment | 159; 158 no rung; 77 containment |
| token-count delta, pred minus gold | -1: 47, 0: 60, +1: 42 | -1: 43, 0: 49, +1: 46 |
| top types in filler-distance pairs | business_name 24, date 19, time 18, place_name 16, food_type 14, person 13 | date 23, person 23, event_name 15 |
| omission share / over-emission share | 24.9 % / 33.6 % | 25.7 % / 31.6 % |
| FN by type | date 70, place_name 35, business_name 34, time 30 | date 74, event_name 56, person 35 |
| empty-gold rows emitting entities | 172 / 414 (41.5 %) | 152 / 314 (48.4 %) |
| PLAN vs PLANr entity-set flipping rows | 93 (8.6 %) | 77 (7.7 %) |
| ENTITY-MIXED / FN-ONLY STABLE-WRONG ceilings | +16.65 / +4.41 pp | +16.08 / +3.77 pp |

The bank defines "none rung" as "an observation or resolution defect that only a different OBS or SUPPLY construction
can reach" (sec 1c).

---

## 4. Decision 206 and the record of the core's tool-call behaviour

### 4a. Decision 206 and its derived rules

| rule | source |
| --- | --- |
| owner 2026-09-29: "tools should be invoked by the model on its own initiative, not called by the system by default; otherwise we fall into the self-proof trap -- why would the task not be done by an ASR + LLM combination" | registry row 206, `docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md:439` |
| the module OFFERS a tool at ONE node and never calls it; `shadow` is not a legal state for an offer; an offer is one tool with a short schema and a closed argument space, absent from every other role's request; each call is one more core contact inside the same ReAct episode, counted into the program ceiling | module design sec 2d, `docs/superpowers/specs/2026-09-29-slurp-consumption-module-design.md:467-510` |
| receipt per row and node: `tool_decision {offered, called, args_hash, result_hash, used_in_answer}`; `used_in_answer` is computed deterministically after delivery, never from the model's claim | same |
| read three measures separately (call rate; decision precision/recall vs an offline DECISION ORACLE; conversion net of breakage); credit the decision node before tool quality | same |
| gate template (proposed, never confirmed; numbers moot for verify-span but "the gate form stays the template"): call rate in [max(0.01, 0.5b), min(0.50, 4b)]; precision >= b + 0.10 and >= 2b with CI95-LB > b; conversion >= +1.49 pp on called rows with CI95-LB > 0, a whole-column SLU-F1 no-loss guard and 0 intent rows differing | registry row 206 |
| only deterministic FORM normalisers may be system-default; "anything that adds evidence the core did not choose to consult -- a transcript, an alignment, a retrieval result -- is an offer or it is nothing" | module design sec 2d |

### 4b. Every recorded tool-call behaviour of the core

| flight / read | role, tool, tool_choice | what happened | source |
| --- | --- | --- | --- |
| B1 (2026-09-17), B1-twin, B1r | Reviewer, `saea-tool-task-contract-v1`, auto (per-role rendering) | **1,084 / 1,082 native calls over 1,080 rows**, i.e. called on essentially every row. Consumed into Reviewer history, but the tool only replays the contract already in the system message | `docs/results/2026-09-17-slurp-b1-exemplars-k20-verdict.md:70`; memory `eff1-constant-tools-harmful-2026-09-19.md` |
| EFF-1 (2026-09-19), constant rendering to every role | Reviewer auto; Solver/Perception/Planner `none` | Reviewer 939 calls. **Solver 145 / 1,092 completions were `<tool_call>` strings** (136 naming the tool), delivered verbatim on 137 rows. SLU -4.39 [-6.69, -2.17], intent -9.17 [-11.64, -6.79]: HARMFUL | `docs/results/2026-09-19-slurp-eff1-tool-constant-verdict.md:264-354` |
| B1-notool (2026-09-20) | Reviewer tool withdrawn | SLU +0.99 [-0.59, +2.50], intent -0.19: NEUTRAL; toolkit RETIRED (switch class `phase_tools`) | memory `b1-notool-neutral-retired-2026-09-20.md` |
| Planner ACQUIRE -> E18 acquisition (B9a-rec) | Planner route, not a native tool | ACQUIRE on 18 / 1,080 rows, all 18 acquired 0 items | E4 design `docs/superpowers/specs/2026-09-28-e4-core-native-targeted-relisten-design.md:22-26` |
| pilot20 post-call audit (2026-10-03) | Planner, `saea-tool-knowledge-target-lookup-v1`, auto | **0 lookups in 289 Planner opportunities**; 24 textual tool-call markers among 27 non-strict Solver replies | `docs/results/2026-10-03-slurp-postcall-source-audit.md`; NX programme `docs/readiness/2026-10-09-slurp-nx-node-extreme-programme-v1.md:136,280` |
| N100 seed / seed A/A (2026-10-08) | Planner auto; Solver none, lookup schema rendered to all roles (+410 tokens per contact) | Planner 0 calls in 334 contacts. **Solver 13 / 100 and 10 / 100 first drafts were `<tool_call>` strings** (R0.3 root cause; 0 / 70 at revision visits). Grammar-constrained roles (json_schema) emitted 0 in 534 contacts with the same tool array | `docs/results/2026-10-09-slurp-nx-solver-parse-root-cause.md` sec 1-2 |
| N100 **solver-lookup** (2026-10-08) | **Solver, lookup tool, `tool_choice: auto`**, at most one call, at most two slot-type IDs (template `configs/probes/slurp_simple_consumption_solver_lookup_v1.txt`) | **16 / 100 first visits ended with `finish_reason tool_calls`**, server-parsed, 16 successful tool contacts, no rejected call; the visit then delivered a parsed answer (100 / 100 per visit, 84 / 100 per first contact). **SLU -5.13 [-9.49, -1.04] vs A/A**, -4.82 [-9.69, +0.04] vs parent; intent -2.00 [-5.00, 0.00]. "No pre-tool quality endpoint for causal tool benefit" | `docs/results/2026-10-08-simple-consumption-n100-complete-family.md:14,27-28,45`; R0.3 note sec 2 |
| Sept-12 native speech tool (`saea-tool-live-speech-observation-v1`, full-utterance Whisper transcript) | Solver/role on `native-answer-or-tool-v1` | 4-row engineering run: 8 internal ASR invocations, all 4 final outputs were escaped tool-call markup (final `tool_choice=none`), intent 0. The single recovery: 4 call/result/answer chains, 50 % intent, but "the acquisition instruction explicitly exercised the live ASR branch" (instructed, not a free decision) | `docs/readiness/2026-09-12-native-speech-tool-engineering-result-v1.md`; `...-recovery-result-v1.md` |
| candidate-refresh tools TRAIN A (2026-09-14) | Reviewer candidate lookup | stopped after 202 contacts: a Reviewer requested an unknown legal candidate ID -> source-bound rejection repair. Batch-call rejection (2026-09-16): a Reviewer emitted several tools in one completion despite `parallel_tool_calls=false` | `docs/readiness/2026-09-14-native-tool-rejection-observation.md`; `2026-09-16-native-tool-batch-rejection-repair-v1.md` |
| COMP-1b / lock v2.2 / NX rounds / VER-1 | none rendered | 0 tool calls (e.g. R6-P1: 10,800 contacts, 0 tool calls) | NX exchange note sec 3; R6-P1 read sec 1 |

**Has a model-initiated tool call ever been consumed?** Yes, twice in kind. (1) The Reviewer's task-contract replay,
called on about every row; it brought no new evidence and was retired. (2) N100 solver-lookup, 16 / 100 rows of
self-initiated Solver lookups whose results the same visit consumed; it read -5.13 [-9.49, -1.04] vs A/A at n = 100,
below the instrument's resolution. **No model-initiated tool call that returns speech-derived evidence has ever flown
at n >= 200.** The NX programme's summary ("the forced-lookup form harms (-5.13). The model-initiated tool (decision
206) is dead today") calls solver-lookup "forced". The family note and R0.3 record it as `tool_choice: auto`. The two
documents conflict on that word.

### 4c. Tool schemas on the wire today

| fact | source |
| --- | --- |
| OpenAI function format `{"type": "function", "function": {"name", ...}}`; non-empty tuple for a tool arm; the explicit empty tuple = tool-free contract (E23b) | `src/speech_aware_evidence_acquisition/rails/core_client.py:506-560` |
| `tool_choice` is derived from the role's tool scope: `auto` if the role names tools, else `none`; `parallel_tool_calls` must be false | `src/speech_aware_evidence_acquisition/reproduction/ojw/native_request.py:391-414` |
| llama-server with `tool_choice: none` leaves the tools in the chat template but installs no grammar or parser, so a tool-call-shaped completion comes back as text | R0.3 note sec 1 |
| R0.3 fixes: F1 render tools only to the calling role; F2 json_schema for a non-calling Solver; F3 `logit_bias` ban of the `<tool_call>` token; if the Solver is the caller, use `tool_choice: auto` plus the within-visit tool loop (the solver-lookup form). Always add an unauthorised-role tool-call counter | R0.3 note sec 3 |
| existing OBS tool manifests: `saea-tool-live-speech-observation-v1` (full utterance, `representation=asr-transcript`, Whisper) and `saea-tool-live-speech-span-v1` ("Decode a bounded span ... only when selected by the frozen core"); both `cost_class` contact, axis OBS. The span tool was wired for E21 meeting Reviewer/Planner only ("Perception and Solver never receive the new analytical speech tool") | `rails/tools.py:1559-1625`; `configs/toolkit/task-toolkits-v3-bounded-speech-span-v1.json` |
| a full native tool catalog renders to 13,914 tokens | module design sec 2d |

---

## 5. Audio-path facts that bound a second hearing pass

| fact | value | source |
| --- | --- | --- |
| packet | SLURP sends one prepared speech-feature packet per contact (`max_speech_packets: 1` in the COMP-1b and E4 baselines). A re-listen re-sends the same packet, with no cut and no derived media | `configs/baseline/slurp-native-stage3-comp1b-fold-a-baseline-v1.json:137`; E4 design sec 0 |
| mean speech per contact | about 2.9 s (B9a-rec 12,642 s / 4,420 contacts); E4 relisten 3.23 s | E4 design sec 0; E4 read sec 6 |
| FIT cap arithmetic | `contact_cap` must equal `rows x program.max_contacts x (max_speech_packets + 3)`; a request with n packets spends n + 3 tokenizer endpoints. E4: 1,080 x 17 x 4 = 73,440 | `src/speech_aware_evidence_acquisition/core/preparation_fit.py:1124-1137`; `docs/readiness/2026-09-13-native-role-flight-bridge-v1.md:85-93` |
| run-cumulative budget | `planned_model_calls` / audio are enforced across recovery attempts | memory `plan-budget-is-run-cumulative.md`; handoff line 225 |
| prefix cache | 88.94 % of ROLL-2 prompt tokens came from the per-slot KV prefix. The Solver's first contact pays the supply block (about 6,142 tokens); later byte-identical contacts are full hits | memory `throughput-baseline-slots-not-prefill.md` (`docs/results/2026-09-27-slurp-throughput-baseline-and-levers.md`) |
| slot geometry | `-np 4 -c 98304`, q8_0 KV, **24,576 tokens per slot**; preflight reserve = 1/8 slot = 3,072; widest realised SLURP request 17,873 + 512 completion cap. np6 refused by 188 tokens; nothing wider than np4 fits at q8_0 | memories `fit-gate-live-slot-reserve.md`, `serving-geometry-findings-2026-09-19.md` |
| COMP-1b first Solver prompt | mean 10,486 tokens (Fold A), 11,038 (DEV); Q4 cut 11,948 / 12,090; max_tokens 512 | NX exchange note sec 6 |
| perception prompt | about 3,590 tokens | R6-P1 read sec 4.4 |
| per-contact throughput | 37.9-65.6 contacts/min on np4 SLURP flights (R6-P1 43.2; VER-1a about 59; B1-notool 42.9; EFF-1 50.2; ROLL-2 63.07; capacity baseline 3,936 contacts per GPU-h); direct-only 140/min | R6-P1 read sec 1; VER-1 read sec 1; throughput note; `docs/results/2026-09-22-slurp-b6-dev2000-added-direct-vs-plan-read.md` |
| decode / slot mix | decode 50.2 %, empty slot 27.3 %, prefill 17.0 %; mean 2.9 / 4 slots busy | throughput note |
| contacts per row today | lock v2.2 review-off: 2.0 per row (vs 4.05 full graph) | registry 262 table (`...owner-decisions-v1.md:1100-1110`) |
| encoding pad (E22) | llama.cpp `mtmd_audio_preprocessor_qwen3a` pads mel to whole 100-frame blocks with literal `0.0` in normalised mel space (0.72 above the floor, louder than 66.4 % of real bins); 13 tokens per block including padding; 42.2 % of tokens on sub-second clips. The probe found the harm is the abrupt stop ("the model completing an utterance whose signal stopped mid-speech"); `tail-silence-2s` removed 86.7 % of the boundary block (-7.99 WER) | `docs/readiness/2026-09-07-e22-short-clip-encoding-audit-v1.md`; `2026-09-07-e22-dev-encoding-probes-v1-verdict.md` |
| derived media | SLURP/A2T `derived/<...>` rows are refused at preparation (confinement gap); ffmpeg absence is pinned | memories `derived-media-confinement-gap.md`, `ffmpeg-absence-is-pinned.md` |
| VRAM | serving notes: envelope 23,119 MiB, about 53 KiB per KV token at q8_0. Owner 2026-10-11: "a portable card with only 24 GB of VRAM". The NX programme F3 says "22.9 GB used of 32 GB" | serving-geometry memory; registry 261 ruling; NX programme F3 |

---

## 6. Span-level and word-level prompting of the Omni core

| item | value | source |
| --- | --- | --- |
| Solver contract wording (v2 and its descendants) | "Extract all and only entity mentions supported by the current speech, preserving their spoken surface forms. Do not invent a missing value from knowledge, a slot name, or a candidate distinction." | `configs/probes/slurp_native_role_solver_v2.txt:6`; same in `r1-c1`, `r1-c3`, the lookup template |
| E4 blind template | "at most 8 English words, in the speaker's own words"; the result was 336 values / 679 unheard over 1,015 delivered entities; replacements were mis-spanned (63 EXACT -> BOUNDARY, mostly date / time / timeofday) | sec 1 above |
| R6-P1 p2 / p3 heard-mention tags (Perception, 128-char distinction channel, Fold B) | rank-1 tag parse **13.3 % / 19.7 %**; containment of the 944 gold entities **7.20 % (68) / 11.76 % (111)**; option precision 32.7 % / 35.0 % (predicted >= 0.70 / 0.60); date containment 0.77 % / 7.69 %; false fill +6.38 [+1.79, +10.71] (p2). "FORM FAILURES of the mention channel ... the channel binds, not the information" | `docs/results/2026-10-10-slurp-nx-r6-perception-fold-b-column-read.md` sec 0, 4.3 |
| R6-P1 p1 presence tag (`E=`) | parses 1,078 / 1,080; `E=none` AUC 0.671, precision 0.572, recall 0.599; cross-fit AUC increment +0.022; gate +0.44 [-0.29, +1.17] | same |
| ROLL-2 (Fold A, 5 samples at T 0.7) | one entity set across all 5 samples on 575 / 1,077 rows (53.4 %); pairwise entity-set flip 29.49 %; intent flip 3.37 % | `docs/results/2026-09-28-slurp-roll-2-fold-a-pool-read.md` sec 5 |
| ROLL-3 (DEV-2000-ADDED) | one entity set on 496 / 990 (50.1 %); pairwise entity-set flip 31.41 % | `docs/results/2026-09-27-slurp-roll-3-dev2000-added-pool-read.md` sec 5 |
| oracle best-of-n | Fold B best of 5 +8.77; Fold A best of 3 +5.34; every verifier tried extracts <= about 1 pp | `docs/results/2026-10-11-slurp-ver1-verification-layer-fold-b-fold-a-read.md` sec 0 |
| PLAN vs PLANr (temperature 0, identical requests) | entity-axis flipping 8.6 % / 7.7 % | bad-case bank sec 2 |
| official scorer (what counts as a match) | **SLU-F1 is not exact-match.** Word-distance and char-distance span F1 are summed. A predicted entity whose TYPE is in the remaining gold list is matched to the lowest-distance same-type gold: TP + 1, FP + d, FN + d. A wrong type gives FP + 1. Unmatched gold gives FN + 1. Gold fillers are lowercased at load; **predicted fillers are not lowercased** (official asymmetry). `slot_f1_exact` is the separate exact `{type, filler}` measure | `src/speech_aware_evidence_acquisition/reproduction/slurp_scoring.py:40-52, 152-240` |
| v4g | a DELIVERY normaliser, not part of the scorer: stages `fx-article`, `fx-oclock`, `scope`, `ti1`, `ee10` with TRAIN-built pinned tables; locked; Fold B +1.55 [+0.81, +2.33]; v2.2 on the test sample +1.67 [+0.53, +2.83] | `src/speech_aware_evidence_acquisition/rails/delivery_normalisers.py:740-800`; memory `v4g-lock-2026-10-09.md`; registry 262 table |
| canonicaliser used by E4/E5/S2a | `rails.relisten.canonical_value` (P2 normaliser + number-word fold) | `rails/relisten.py:297-316` |

---

## Constraints any option-B design must satisfy (from the record)

1. **Model-initiated, one node, real offer (206).** The Solver (or the named delivery-step role) must decide to call.
   A per-entity system-fired stage is the closed E4 form. `shadow` is illegal for an offer. One tool, a short schema
   with a closed argument space (for example slot-type enum plus an index), rendered only to the calling role.
   `tool_choice: auto` there, `parallel_tool_calls: false`, at most one call. Receipt `tool_decision {offered, called,
   args_hash, result_hash, used_in_answer}` with `used_in_answer` computed after delivery.
2. **No tool-string leakage.** Every non-calling role gets no tool array (R0.3 F1) or a decode constraint (F2/F3).
   EFF-1 (145 / 1,092) and N100 seed (13 / 100) show a rendered tool under `tool_choice: none` turns 10-13 % of Solver
   drafts into undeliverable `<tool_call>` text. The calling Solver needs the within-visit loop and must return task
   JSON after the result. Add the unauthorised-role tool-call counter.
3. **The hearing pass returns words only.** No label, no decision, and no value bytes persisted in clear (E4's
   "no transcript state": hashes only). It must not become a transcript path into intent: transcripts in the prompt
   cost intent -0.90 [-1.68, -0.09] on DEV1000. The owner's 2026-09-06 "no transcript tokens" ruling is superseded
   only in scope, for pinned, logged tool contacts (row 201).
4. **Do not repeat E4's failure surface.**
   - (a) Replacement of delivered values from a blind hearing contact broke 63 EXACT -> BOUNDARY (date / time /
     timeofday) and repaired 7.
   - (b) A forced-choice confirm did not filter that breakage.
   - (c) The blind core claimed "unheard" for 67 % of delivered entities, so an "unheard" signal is not
     discriminative by itself.

   The span convention (SLURP annotation extent) is the binding problem, not the hearing.
5. **Deterministic verifier.** It may only change FORM or select among values the core produced (row 206 / module 2d
   flag). Its span acceptance must be judged against the official distance scorer. Partial credit means a
   BOUNDARY-wrong replacement of an EXACT value costs, while an extra correct MISSING recovery is worth about
   0.057-0.062 pp. Predictions are case-sensitive against lowercased gold.
6. **Slot and contact budget.**
   - The calling Solver re-sends the packet. Prompt growth must fit the 24,576-token slot minus the 3,072 reserve
     (Solver Q4 already about 12k).
   - Each call is one contact counted into `program.max_contacts`. The FIT cap must equal
     `rows x max_contacts x (max_speech_packets + 3)` and is run-cumulative across recoveries.
   - Expect about 1 s of server compute and about 2.4k prompt tokens per hearing contact (E4: 0.497 h and 4.50 M
     tokens over 1,889 contacts). Throughput is 38-66 contacts/min on np4.
   - Contacts after delivery must be declared to the seal. The E4 abort was a finite-completion row followed by
     shadow contacts. Smoke rosters must include finite-completion and revision-limit rows.
7. **No audio cut** unless the E22 abrupt-stop artefact is handled (`tail-silence-2s`). SLURP derived media is refused
   at preparation today, and ffmpeg absence is pinned. Re-sending the same packet is the precedent.
8. **Measurement floors.**
   - Rosters: n >= 1,080 (Fold B select, Fold A confirm, then DEV / test). Below 200 rows is a form proof only.
   - Same-flight SLU contrast floor 1.49 pp (decision 190) and intent 0.65. The same-flight shadow / twin provisional
     null is 0.3163 at n = 1,080, and twins have read up to +0.72 [+0.12, +1.37].
   - Cross-flight DEV bar 2.5-2.6 pp with an in-chain A/A. Offline pool floor 0.67. Decision 192 requires a
     model-free information-gain prediction >= 1.5 pp before registration.
   - The 206 gate form applies: call-rate band; decision precision >= b + 0.10 and 2b vs a decision oracle;
     conversion >= +1.49 with a no-loss SLU guard and 0 intent rows differing.
   - Every verdict carries per-scenario and per-type tables. One experiment in flight; at most one recovery.
9. **Ceiling arithmetic to beat.**
   - The 106 hearing-visible + re-listen items are worth 5.13 pp oracle. 1.5 pp needs 29 % net conversion, or about
     25 recovered MISSING / 17 repaired wrong entities.
   - E4 reached 2.83 %. The verify-form perfect-repair ceiling was only +1.62. The missing-slot proposal oracle is
     +8.21 but assumes perfect span and type.
10. **Knowledge boundary.** No gold, reference transcript or test annotation at runtime. Any query must contain speech
    (2026-09-06 rule). Decision 199 makes "no entities" and empty results legal, receipted outcomes.

## What the files do not answer

- **Whether the core will call a hearing tool at all.** The only self-initiated Solver tool record is solver-lookup at
  16 / 100 rows (a knowledge tool, n = 100, harmful point estimate). The Planner made 0 / 289 and 0 / 334 calls. No
  call-rate or decision-precision measurement exists for any speech-returning tool offered to the Solver at n >= 200.
- **Whether a hearing-only answer to a type-targeted question has the right SLURP span.** E4 says a blind 8-word answer
  mis-spans dates and times. No record tests a contract that asks for the exact spoken words of a span the Solver
  itself names (for example by quoting its draft or naming a type with a candidate count). R6-P1's mention channel
  failed on FORM (13-20 % parse) before hearing could be measured.
- **The hearing pass's containment of the gold spans.** The core's analogue of Whisper's 0.7513 has never been
  measured. The E4 receipts hold value hashes only (no value bytes), and the read did not compute gold containment
  of the 336 blind values. The headroom note's requested cross-tabulation of the blind hearing state against the
  E1 / E5 split was not reported in the E4 read.
- **The decision oracle for option B specifically.** E5-1's oracle is for verify-span (29 rows) and for a
  transcript-proposes-missing form (106 rows). Neither is an oracle of "Solver asks for type t, hearing returns
  words". The model-visible signals for when such a call helps are unmeasured beyond AUC <= 0.72 for the verify form.
- **How the deterministic verifier should consume the words.** Options include accept on containment in the draft,
  replace, add a missing entity, or a lexicon or type check. No record defines or measures this. S2a.1 shows a
  trigram-lexicon ranker loses 27 of 33 eligible values even on Whisper text.
- **Cost under the review-off lock** (2 contacts per row) at a realistic call rate. All measured relisten costs are
  on the 17-ceiling E4 graph.
- **Whether `saea-tool-live-speech-span-v1` ever flew with a live model.** Its manifest exists and it was wired for E21
  meeting roles. No SLURP record shows a call, and its argument schema was not located in this survey.
- **VRAM on the card.** Records say 23,119 MiB envelope (np4 at 24,576 per slot), "of 32 GB" (NX F3), and the owner
  says 24 GB. Which figure binds a heavier prompt or an extra contact type is not reconciled.
- **The "forced" vs `auto` label of solver-lookup.** The NX programme calls it forced; the family note and R0.3 record
  `tool_choice: auto` with 16 / 100 calls. No file resolves the wording.
- **"0 engineering reuse of E4".** The briefing asserts it, but E4's blind response format, canonicaliser, seal
  allowance for post-delivery contacts (`b286d897`) and replay code exist. The files do not say which parts the
  coordinator considers unusable. Presumably the system-fired post-accept stage and the shadow binding are the
  unusable parts.
