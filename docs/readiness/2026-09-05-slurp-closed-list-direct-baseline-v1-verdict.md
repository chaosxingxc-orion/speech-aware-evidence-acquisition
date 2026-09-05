# SLURP closed-list direct baseline — verdict (2026-09-05)

Run id: `SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1`, attempt
`attempt-20260905T060424Z-2c5596`, profile `baseline-reproduction`, study commit at
takeoff `aae0a90d`. Preregistration:
`docs/readiness/2026-09-05-slurp-closed-list-direct-baseline-v1-preregistration.md`.
Receipts: `docs/checks/speech-aware-evidence-acquisition/2026-09-05-slurp-closed-list-direct-baseline-v1/`.
One arm, one attempt, one seal, one read. Nothing was re-flown and no knob was changed.

## Verdict

**The closed-list arm is the study's SLURP direct baseline**, as preregistered, and it
moves the intent number a long way while leaving the slot number where it was.

* Intent (scen_act) **71.40** against the sealed M0 comparator's **53.60** — a paired
  **+17.80 pp** (CI90 [+15.70, +19.90], sign test p = 1.7e-38), holding at **+17.60 pp**
  on the 500 rows unexposed at the lock tier.
* SLU-F1 **35.80** against M0's **36.90**: **−1.10**. The paired per-sample slot-F1
  contrast is **−1.70 pp** (CI90 [−2.94, −0.48], sign test p = 0.078).
* Impossible (scenario, action) pairs fall from **32.20 %** to **4.20 %**.
* **80.5 % of the locked BLEND cell's SLURP intent margin over M0 is reproduced by a
  prompt-side label inventory** with zero retrieval, zero tool contacts and no second
  model contact. What survives is +4.30 pp pooled, and on the unexposed 500 it is
  +2.60 pp with a 90 % CI of [−0.20, +5.60] — it no longer excludes zero.

This is He & Garner's asymmetry, reproduced for the first time on audio input with the
official script: **intent classification survives prompting; slot filling does not.**

## 1. The official table

Official `evaluate.py` at pinned commit `8eb1654…311f1` in `~/.venvs/slurp-official-eval`
(used, never modified), `--average micro --errors --table-layout csv`, run **once over
the complete manifest** through `core.scoring_batch`. The port-vs-official identity check
passed on all three arms at an absolute difference of 0.0.

| arm | scenario | action | **intent (scen_act)** | entities strict | Word-F1 | Char-F1 | **SLU-F1** | n gold | n predicted | skipped | unparsed |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **CLOSED-LIST (this flight)** | **81.00** | **73.90** | **71.40** | 21.91 | 33.69 | 38.20 | **35.80** | 1000 | 1000 | 0 | 3 |
| DEV-1000 M0 (sealed comparator) | 70.00 | 61.50 | 53.60 | 21.94 | 34.66 | 39.46 | 36.90 | 1000 | 1000 | 0 | 5 |
| DEV-1000 BLEND (locked cell) | 83.90 | 77.60 | 75.70 | 27.27 | 39.41 | 44.24 | 41.69 | 1000 | 1000 | 0 | 2 |

The M0 and BLEND rows reproduce the 2026-09-04 alignment audit exactly, to the second
decimal, on all seven metrics — an identity anchor for this read.

**N-predicted.** Zero skipped rows on every arm, so the unanswered-counted-wrong variant
equals the official number throughout. An unparsed response is *scored and counted wrong*
here, not skipped: `evaluate.py` pairs on `if gold_id in pred_examples`, and every gold id
has a prediction row.

## 2. Paired contrast against the sealed M0 arm

Paired per-sample, `delta = closed-list − M0`, stratified bootstrap N = 10,000 seed
20260807, CI90, exact sign test. Strata are the gold scenario.

| population | metric | M0 | closed-list | delta | saves | harms | ties | p | CI90 |
|---|---|---|---|---|---|---|---|---|---|
| pooled 1000 | intent | 53.60 | 71.40 | **+17.80** | 197 | 19 | 784 | 1.7e-38 | [+15.70, +19.90] |
| prior-exposed 500 | intent | 51.60 | 69.60 | +18.00 | 98 | 8 | 394 | 8.1e-21 | [+15.20, +20.80] |
| **unexposed 500** | intent | 55.60 | 73.20 | **+17.60** | 99 | 11 | 390 | 7.4e-19 | [+14.80, +20.40] |
| pooled 1000 | scenario | 70.00 | 81.00 | +11.00 | 126 | 16 | 858 | 2.2e-22 | [+9.30, +12.70] |
| pooled 1000 | action | 61.50 | 73.90 | +12.40 | 158 | 34 | 808 | 2.6e-20 | [+10.40, +14.40] |
| pooled 1000 | slot-F1 (exact, per sample) | 14.66 | 12.96 | **−1.70** | 33 | 50 | 917 | 0.078 | [−2.94, −0.48] |

The exposed and unexposed halves agree to 0.4 pp, so the effect is not an artifact of the
half of the roster earlier iteration touched.

## 3. Per stratum (intent), and both weightings

| scenario | n | M0 | closed-list | delta | saves | harms |
|---|---|---|---|---|---|---|
| alarm | 58 | 86.2 | 87.9 | +1.7 | 3 | 2 |
| audio | 30 | 30.0 | 73.3 | **+43.3** | 13 | 0 |
| calendar | 61 | 42.6 | 65.6 | +23.0 | 14 | 0 |
| cooking | 37 | 8.1 | 59.5 | **+51.4** | 20 | 1 |
| datetime | 61 | 80.3 | 82.0 | +1.6 | 4 | 3 |
| email | 61 | 80.3 | 83.6 | +3.3 | 5 | 3 |
| general | 61 | 3.3 | 34.4 | +31.1 | 19 | 0 |
| iot | 61 | 57.4 | 85.2 | +27.9 | 17 | 0 |
| lists | 60 | 85.0 | 86.7 | +1.7 | 1 | 0 |
| music | 51 | 62.7 | 84.3 | +21.6 | 12 | 1 |
| news | 60 | 76.7 | 78.3 | +1.7 | 2 | 1 |
| play | 60 | **0.0** | 38.3 | +38.3 | 23 | 0 |
| qa | 60 | 20.0 | 58.3 | +38.3 | 23 | 0 |
| recommendation | 60 | **0.0** | 46.7 | **+46.7** | 28 | 0 |
| social | 60 | 78.3 | 80.0 | +1.7 | 3 | 2 |
| takeaway | 39 | 74.4 | 76.9 | +2.6 | 3 | 2 |
| transport | 60 | 66.7 | 71.7 | +5.0 | 7 | 4 |
| weather | 60 | 93.3 | 93.3 | 0.0 | 0 | 0 |

Natural (roster) weighting 53.60 → 71.40, +17.80; equal-stratum weighting 52.52 → 71.45,
+18.93. The DEV-1000 roster is itself scenario-stratified, so the two barely differ;
neither is the published natural mixture of the test split.

**Where the gain lives, and why.** The nine scenarios that gained more than 20 points are
exactly the ones whose correct action is unguessable from a flat 46-name list:
`recommendation` and `play` scored **0.0** under M0 because the model answered
`recommendation/query` and `music/play` — plausible English, and not SLURP labels.
Naming the legal actions per scenario fixes those by construction. The nine scenarios that
barely moved were already at or above 74 % and had an obvious action.

## 4. The prompt change did what it was designed to do

Measured against the same TRAIN-only inventory the prompt carries — no gold involved:

| arm | scenario outside the 18 | action outside the 46 | **(scenario, action) not in train** | entity type outside the 55 | unparsed |
|---|---|---|---|---|---|
| CLOSED-LIST | 2.40 % | 0.90 % | **4.20 %** | 0.00 % of 547 mentions | 3 |
| DEV-1000 M0 | 8.60 % | 6.90 % | **32.20 %** | 0.28 % of 718 | 5 |
| DEV-1000 BLEND | 0.20 % | 0.20 % | **2.10 %** | 0.00 % of 693 | 2 |

An 87 % reduction in impossible pairs, and the entity-type vocabulary is now perfectly
respected. What remains is genuine confusion, not invention: the largest residual classes
are `locations/query` (10) and `events/query` (8) — the model picking the *action* name as
the scenario for `recommendation_locations` / `recommendation_events`.

## 5. Distance to the published brackets

Owner rule: aligned = within 3 points, or better. **Every published row is the official
TEST split and a natural mixture; this arm is a scenario-stratified DEV roster**, and no
published prompt-only SLU-F1 computed with this script exists for any audio LLM, so no
like-for-like target is available and none is claimed.

| metric | ours | published target (system, split) | delta | verdict |
|---|---|---|---|---|
| intent | 71.40 | Google/SF-ID 72.06 (weakest published pipeline, test) | −0.66 | **aligned**; degraded-model floor failed by 0.66 |
| intent | 71.40 | ChatGPT on Whisper ASR, 10-shot 72.89 | −1.49 | **aligned** |
| intent | 71.40 | Multi-SLURP/HerMiT 78.33 (strong pipeline, test) | −6.93 | not aligned |
| intent | 71.40 | ChatGPT on oracle transcripts, 0-shot, 60 intents listed 79.25 | −7.85 | not aligned |
| intent | 71.40 | Gold/HerMiT 84.84 (oracle transcripts, test) | −13.44 | not aligned |
| scenario | 81.00 | Google/SF-ID 78.87 | +2.13 | **aligned-better**; floor cleared |
| scenario | 81.00 | Gold/HerMiT 90.15 | −9.15 | not aligned |
| action | 73.90 | Google/SF-ID 74.31 | −0.41 | **aligned**; floor failed by 0.41 |
| action | 73.90 | Gold/HerMiT 86.99 | −13.09 | not aligned |
| SLU-F1 | 35.80 | Google/SF-ID 64.02 (degraded-model floor) | −28.22 | not aligned; **floor failed** |
| SLU-F1 | 35.80 | Multi-SLURP/HerMiT 70.84 (best in the paper, test) | −35.04 | not aligned |
| SLU-F1 | 35.80 | ChatGPT prompt-only slot F1 12.03–13.35 | +22.5 to +23.8 | better, but a **different metric definition** |

The single most informative comparison is the last prompt-only one: against ChatGPT's
79.25 on **oracle transcripts** with the same 60 intents in the prompt, a frozen speech
core reading the **audio directly** reaches 71.40 — 7.85 points behind a text cascade that
was handed a perfect transcript, on a harder input, with the same prompt protocol.

## 6. What this does to the knowledge plane's SLURP claim

| contrast (intent, pooled 1000) | delta | CI90 | sign test p |
|---|---|---|---|
| BLEND over sealed M0 | +22.10 | [+20.20, +24.00] | — |
| **BLEND over closed-list** | **+4.30** | [+2.30, +6.30] | 0.00117 |
| BLEND over closed-list, unexposed 500 | +2.60 | [−0.20, +5.60] | 0.193 |

**80.5 % of BLEND's SLURP intent margin was a label-inventory effect.** BLEND supplies
TRAIN-mined exemplars that happen to carry legal intent pairs; the same information costs
1,836 characters of prompt and nothing else. What the retrieval plane still buys, pooled,
is +4.30 pp — real but an order of magnitude smaller than the headline the 2026-08-25 lock
recorded, and on the rows unexposed at that tier its 90 % CI includes zero.

This does **not** void the lock: the lock statistic was BLEND-vs-M0 and that number is
unchanged. It re-scopes what the lock *means*. The honest restatement is that the locked
cell's SLURP gain is mostly prompt-recoverable, and the knowledge plane's claim on this
carrier must be re-established against the protocol-aligned baseline, not against M0.

## 7. The slot layer did not move, and that is the finding to attack

SLU-F1 35.80 vs 36.90, entities-strict 21.91 vs 21.94. Underneath, the arm became
**more conservative**: 547 entity mentions against M0's 718, with precision up
(29.98 vs 25.49) and recall down (17.26 vs 19.26). Naming the 55 legal types stopped the
model inventing types (0.28 % → 0.00 %) but also stopped it guessing, and on a
recall-limited metric that is a wash.

Slot filling is where the 28-point gap to the weakest published pipeline lives, and it is
not a prompt problem: a closed type list is exactly the intervention that should have
helped, and it did not. **That is the target an evidence-acquisition control plane exists
to attack**, and the finding is now measured on a protocol-aligned baseline rather than a
prompt-defective one.

## 8. Mechanics, cost and provenance

| item | value |
|---|---|
| population | DEV-1000, 1,000 devel rows, identity `8580d199…3c84` recomputed from the runtime view and equal to the sealed M0 plan's |
| prompt | 7,583 chars, sha256 `4073f79e…37db` = the sealed M0 instruction (5,747 chars, `cef52789…86b8`) + 1,836-char suffix `46ee018e…0dda3` |
| model | frozen Qwen3-Omni-30B-A3B-Instruct GGUF Q4_K_M, featcache build `04ccc72a`, mmproj-free over the DEV-1000 packets |
| geometry / decoding | `-np 8 -c 65536`; greedy, temperature 0, seed 20260803, max_tokens 64 — the sealed M0 arm's own |
| contacts | 1,000 of 1,050 registered; 2,884.79 of 3,000 audio seconds; ~0.105 of 1.0 GPU-h; 0 tool, 0 embedding, 0 paid spend |
| throughput | 1,000 contacts in 225.5 s, 4.43 contacts/s, 283.8 tokens/s, slot occupancy 0.899, 1,000 packets promoted at 155 packets/s, 6 min 18 s takeoff to report |
| prompt fit | ALLOW at preflight: 2,140 rendered text + 50 speech + 2 special + 64 completion = 2,256 against an 8,192-token slot, margin +5,936 |
| seal | `SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1.run-manifest.json` sha256 `f908ff4c…c94c`, 1,000 canonical rows, outputs sha256 `34fda7fa…885b`, attempt FINALIZED |
| scoring | `core.scoring_batch`, 1 job, 0 failed, 47.3 s, no sharding |

**Defect 2 of the 2026-09-04 audit is discharged for this carrier.** This is the first
SLURP cell flown through `core.flight.FlightRuntime`; its seal writes a real
`*.run-manifest.json` and canonical rows keyed `text`, so `core.scoring_batch` applies
directly. The two sealed August arms still needed the 1:1 key-rename projection the audit
established (both source and projection sha256 recorded in `read.json`); nothing about
them was altered.

## 9. Deviations and limits

1. **The mission's premise was wrong and was corrected before the flight.** The directive
   and the audit's caveat 4 both said M0 offered no label inventory. It offered three
   (18 scenarios, 46 actions, 55 entity types); it never offered the pairing. The flown
   arm is therefore *M0's prompt plus the missing pairing*, a pure suffix, and the 263
   example fillers M0 already carried were deliberately left in place so the contrast is
   not confounded by also deleting them. Receipt:
   `docs/checks/speech-aware-evidence-acquisition/2026-09-05-slurp-closed-list-headroom/`.
2. **Harness changed with the prompt.** M0 flew through `rails.runner`'s agent loop;
   this arm flew through `FlightRuntime`'s fixed-policy speech-feature direct dispatch.
   The request bytes are the same shape (system instruction + one
   `input_speech_features` query part, one contact, no evidence) and the instruction is
   provably M0's plus a suffix, but the two were not byte-compared on the wire. The
   dispatcher's concurrency (8 pinned slots) is not a request-content variable.
3. **Devel, not test.** No test contact. The published brackets are test-split numbers.
4. **No like-for-like SLU-F1 target exists**, so the SLU-F1 rows compare across metric
   definitions or across trained systems, never like for like.
5. **`configs/probes/manifest.json` carries two probe entries the generator no longer
   holds** (`R1-audio2tool-official-tier258-population`,
   `…-tier3467-population`). Regenerating would have deleted them, so the new entry was
   added surgically. Reported, not repaired — the repair belongs to whoever owns those rows.

## 10. What this authorizes

The closed-list arm replaces M0 as **the SLURP direct baseline every later comparison on
this carrier cites**: config hash `6be064ba…b894f`, protocol hash `7e83a705…951b2`,
prompt sha256 `4073f79e…37db`, run manifest `f908ff4c…c94c`. Any mechanism claiming a
SLURP gain must beat 71.40 intent / 35.80 SLU-F1, not 53.60 / 36.90.

It authorizes nothing else: no test contact, no superiority claim, no generalization
claim, no Stage-3 activity.
