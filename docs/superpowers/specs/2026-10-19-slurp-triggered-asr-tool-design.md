# Owner ruling 339: a triggered ASR tool at the Solver slot-value step of the SLURP v3.0 lock (model-free design)

Date 2026-10-18. Model-free designer note (Claude Opus 5.5, coordinator's brief). Read-only on the study and umbrella repos.
Zero model, server, ASR, GPU, network and scorer-subprocess contacts. Gold entered on the scoring side only through the
governed TRAIN loaders. The SLURP reference sentence (the perfect-ASR bound) was held in memory only. No devel or test
rows were opened. Only counts, rates, pp, AUCs and slot TYPE names are persisted.
**Development numbers on TRAIN Fold B (decisions 28 and 86). This note registers nothing and gates nothing.**

Authority: ruling 339 (registry section "Owner rulings 338 and 339"), directive 206 (tools are model-initiated),
decision 190 floors (1.49 SLU / 0.65 intent at n = 1,080), ruling 338 (the SLURP lock goes first; this design queues
behind R3/R4).

Files (this directory):
- `asr_trigger_bound.py` produces `bound339.json`. It holds the labels, ceilings, signal AUCs, the cross-fit trigger and the rules.
- `whisper_wer.py` produces `whisper_wer.json`.
- `exposure.py` produces `exposure.json`.
- `run.sh` reproduces all three: WSL, CPU, about 10 min.

Inputs:
- **Population:** the NX-T R2b delivering arm `budget-3072` (the v3.0 lock form), TRAIN Fold B, n = 1,080, SLU 72.74 / intent 85.37.
- **Transcripts:** the sealed E5-0 Whisper large-v3 Fold B catalog (`31462f9b...`), re-hashed against its receipt. Its roster equals the run's 1,080 ids.
- **Reproduction check:** the gap-decomposition checks reproduced 1,080 of 1,080 rows (re-score equals sealed, intent parse agrees).

## 1. The opportunity on the v3.0 lock (Fold B, 1,080 rows)

| item class (v3.0 delivered vs gold) | items | gold value in Whisper | gold value in reference (perfect ASR) |
| --- | ---: | ---: | ---: |
| MISSING (slot not delivered) | 112 | 70 (0.625) | 104 (0.929) |
| wrong value (FORMAT/BOUNDARY/NEAR/WRONG-VALUE) | 166 | 61 (0.367) | 139 (0.837) |
| of those 61: the delivered wrong value is ALSO in Whisper (the transcript cannot discriminate) | | 38 | |

- Whisper large-v3 canonical-token WER on SLURP is 0.152 (Fold B) and 0.144 (Fold A). Only 52.8 % of Fold B sentences are exact.
- The ASR miss concentrates on names. On business_name, 6 of 28 value-wrong items are in Whisper. On place_name it is 4 of 20 value / 2 of 7 missing, and on person 4 of 13 / 1 of 6.

**Perfect-conversion SLU ceilings.** Every addressable item is repaired to gold, on every row (pp over 72.74). The CI95 is an utterance-cluster bootstrap with 2,000 draws.

| label (row has at least one such item) | rows | ceiling, perfect conversion | ceiling, conversion 0.457 (CONV uptake, linear in counts) |
| --- | ---: | --- | ---: |
| `miss_W`: MISSING, gold in Whisper | 66 | +3.96 [+3.09, +4.94] | +1.84 |
| `valdisc_W`: wrong value, gold in Whisper and delivered NOT in Whisper | 23 | +1.09 | +0.49 |
| **`missval_disc_W`: the two above (the transcript-discriminable prize)** | **88** | **+5.07 [+4.09, +6.14]** | **+2.34** |
| `any_W`: also counting non-discriminable value items | 119 | +6.77 [+5.51, +8.04] | +3.09 |
| `any_R`: perfect ASR, any addressable item | 219 | +12.29 [+10.78, +13.75] | +5.52 |

Reading the ceilings:
- On the Thinking lock, the transcript-discriminable prize (+5.07 pp) is about three times the Instruct-era verify-only ceiling (+1.62 pp, E5-1). The reason is that MISSING items now dominate, and 62.5 % of them are in the Whisper transcript.
- The non-discriminable value items (38) are boundary choices. The transcript contains both the wrong value and the right one, so it adds no evidence for them. They are excluded from the design's prize.

## 2. The trigger: which model-visible signals tell the core a call helps (decision oracle)

AUC per signal for the `missval_disc_W` label (base rate b = 0.0815). The `miss_W` and `val_W` AUCs are in `bound339.json`.

| signal (visible to the core at its slot step) | AUC | note |
| --- | ---: | --- |
| Solver completion tokens (its own reasoning length) | **0.710** | 0.707 on `miss_W`, 0.728 on `val_W` |
| Solver forced close (reasoning hit the 3,072 budget) | 0.653 | 433 rows; precision 0.185 / recall 0.672 on `any_W` |
| expected-type gap: max TRAIN P(type present given predicted intent) over the types not delivered | 0.608 | 0.659 on `miss_W` (the MISSING-specific signal) |
| delivered entity count / delivered value tokens | 0.564 / 0.560 | 0.763 / 0.791 on `val_W` (long or many values carry value errors) |
| predicted-empty slots | 0.463 | points the wrong way: empty predictions are mostly correct empties |
| Perception forced close, Perception tokens, shortlist length | 0.45-0.54 | uninformative |

The TRAIN prior excludes the Fold A and Fold B utterances.

**Cross-fit trigger.** This is the best that these signals jointly allow: 5 utterance folds, an L2 logistic fit over all 12 signals plus the predicted scenario, scored out of fold.

| `missval_disc_W` (b = 0.0815, OOF AUC 0.682) | 10 % calls | 20 % | 30 % | 50 % | 100 % |
| --- | ---: | ---: | ---: | ---: | ---: |
| precision of the call | 0.222 | 0.167 | 0.139 | 0.122 | 0.082 |
| recall of helpful rows | 0.27 | 0.41 | 0.51 | 0.75 | 1.00 |
| yield, perfect conversion (pp) | +1.51 | +2.16 | +2.59 | +3.86 | +5.07 |
| yield at conversion 0.457 (pp) | +0.69 | +0.99 | +1.19 | +1.78 | +2.34 |
| conversion needed to reach the 1.49 floor (no harm) | 0.99 | 0.69 | 0.58 | 0.39 | 0.29 |

- Simple rules sit at the same level. The `solver_forced_close` rule makes 433 calls for +4.74 perfect / +2.16 at 0.457 on `any_W`.
- **Bound.** No combination of these signals reaches AUC 0.72. The trigger alone therefore cannot concentrate the prize: half of it needs about 30 % of rows called.
- The core may use what the signals miss, namely its own hearing of the audio. That is why the experiment measures the core's own call decision against this table instead of hard-coding a rule.
- Gating the offer on a signal would be a system-default step, which directive 206 rules out. The offer is therefore universal, and the core's call is its own decision.

**Harm budget.**
- One broken EXACT item costs 0.0576 pp (mean over 200 sampled rows).
- At 100 % calls and conversion 0.457, the margin over the floor is 0.85 pp. That allows at most about 15 broken items per 1,080 rows (1.4 per 100 calls).
- The precedents all show harm on precisely this kind of action:
  - E4-1, core-native re-listen value replacement: -4.11 pp;
  - E5 R-SWAP: 3 EXACT items lost per 9 swaps;
  - transcripts in the prompt: intent -0.90 on DEV-1000.
- **The design must therefore cap exposure structurally (section 3).**
- Under the cite-and-protect guard, the exposure is as follows:
  - Only 70 of the 627 delivered EXACT items, 11.2 %, have a value missing from Whisper. These are the only EXACT values a guarded revision could replace.
  - 112 of the 189 spurious items have a value that IS in Whisper. A transcript does not remove false fills, and it can create new ones.

## 3. The tool contract

**Offer.** One tool, `transcribe_utterance`, is offered only in the Solver contact of the v3.0 module graph (slot-value step), with `tool_choice` set to `auto`.
- Never Perception. Never a constant multi-role schema: that was EFF-1's failure, with `tool_choice` set to `none` and a 13.9k-token schema.
- The schema is about 200 tokens. Its description states when the tool helps: unsure of a slot value's exact words, or the chosen intent usually carries a slot type you did not fill.
- The expected types for the predicted intent come from the existing type-by-intent table (an ORG supply from TRAIN knowledge, no gold).
- At most one call per row.

**Arguments (required).**
- `committed_intent`: a closed-set enum that must equal the intent the Solver will deliver.
- `draft_entities`: the Solver's current slot list.
- `slot_types`: the types it wants checked or added.

**Intent lock.** The runtime records `committed_intent`. The delivered intent is then FORCED to `committed_intent` by a deterministic form normaliser (flagged class, as for decision 203).
- The transcript therefore never enters the intent decision.
- The receipt counts `intent_changed_after_call`. The expected value is 0, and any non-zero count is a defect.

**Return.** The full 1-best transcript (Whisper large-v3 pinned, decoding config `b90432b6...`, the E5-0 bytes contract). No targeted span list is returned.
- S2a.1 and the ranker study show that every ranker loses most of the contained values. The contract T is 0.086-0.37 against a containment of 0.47-0.87. The core is the selector.
- The transcript is about 15-30 tokens and is wrapped as `evidence:asr-transcript` with its hash.
- Transcription is LAZY. It runs only when the core calls, as a logged tool contact (class `speech-tool`, axis OBS) in the CPU Whisper venv (`saea-whisper-vad`, about 14.8 s per call while the core serves).
- Nothing is pre-transcribed in the runtime. The sealed E5-0 Fold B bytes serve only as an offline determinism check of the result hash.

**Use, cite-and-protect.** This deterministic FORM verifier never adds evidence and never calls a tool.
- Every entity added or changed after the call must cite a contiguous span of the returned transcript (`saea-solver-cited-answer-v1`, `source: asr`).
- A changed value is accepted only when the replaced draft value is NOT contained in the transcript.
- An entity that violates either rule reverts to its draft form. A violating addition is dropped.
- The verifier never applies a transcript value the core did not deliver.

**Receipt.** Per row: `tool_decision {offered, called, committed_intent, draft_entities_hash, slot_types, asr_model_id, weights_sha256 (e5b1a55b...), decoding_config_sha256, audio_sha256, result_sha256, result_tokens, asr_seconds, continuation_tokens, entities_added, entities_changed, reverted_by_verifier, used_in_answer}`.
- The draft carried in the call is the within-row control. Final against draft, scored offline, is the conversion and harm of the call itself.

## 4. ASR choice

| item | value |
| --- | --- |
| pinned now | Whisper large-v3 in two umbrella-lock entries: `whisper-large-v3-openai-pt` (`large-v3.pt`, sha256 `e5b1a55b...`, used by E5-0) and `whisper-large-v3` (HF safetensors, revision `06f233fe...`); runtimes `saea-whisper-gpu` / `saea-whisper-vad` |
| measured on SLURP | canonical WER 0.152 (Fold B). Gold-span containment 0.76 (all gold). On the v3.0 lock's errors: MISSING 0.625, value 0.367 |
| perfect-ASR upper bound | `any_R` ceiling +12.29 against Whisper's `any_W` +6.77, so at most **+5.53 pp more at perfect conversion and +2.43 at 0.457** (MISSING +34 items, value +78 items) |
| candidates needing an acquisition entry | NVIDIA Parakeet-TDT-0.6B-v2, Canary-1B-flash, Canary-Qwen-2.5B (CC-BY-4.0). They are reported above Whisper large-v3 on the Open ASR leaderboard average; that is not a SLURP number and must be verified at registration. The NeMo 3.0.0 runtime already exists in the isolated `~/.venvs/diar`. Also free: Whisper's beam-5 n-best union (pinned asset, a different decode output) |
| what a candidate can gain | **Bounded between 0 and +5.53 pp (perfect) / +2.43 (0.457).** It is not estimated, because SLURP WER does not transfer from leaderboard averages |
| admission gate (model-free reader = this driver) | one tool-contact pass over Fold B (0 core contacts, about 0.15 GPU-h in a serving gap) |

The candidate is kept only if both of these hold:
- its `missval_disc_W` ceiling exceeds Whisper's +5.07 by at least +1.0 pp at perfect conversion;
- its canonical WER is below 0.152.

## 5. Registrable bounded experiment

**Stage 0, model-free engineering.** It changes no default plan.
- A `transcribe_utterance` tool in the tool catalog plus a `core.base` evidence-source registration (`asr-transcript-tool`).
- The Solver offer fragment, the intent-lock normaliser, the cite-and-protect verifier and the `tool_decision` receipt.
- A read driver: decision-oracle labels from `asr_trigger_bound.py`, and a within-row draft-against-final scorer.
- The cell declares `finite_completion_policy` / `react_exhaustion_policy`, a `stage3_algorithm` label and a `stage3_measurement` block.
- FIT on the longest prompt plus continuation.
- Proof on a 4-row dry run.

**Stage 1, decision probe (339-P1).**
- **Arm:** a single tool arm (v3.0 lock plus the offer) on TRAIN Fold B, n = 1,080. Fold B is the bound roster, so every call meets its oracle label.
- **Cost:**
  - core contacts: 2,160, plus one continuation per call (at most 1,080);
  - ASR tool contacts: at most 1,080;
  - GPU time: about 9.2 GPU-h base, plus 1.4-4.8 for continuations and 0.3-1.1 of slot time blocked on CPU Whisper, so **11-15 GPU-h** at a 30-100 % call rate.
- **STOP unless all of these hold:**
  - call rate in [0.05, 0.60];
  - call precision against `missval_disc_W` at least b + 0.10 = 0.18, with CI95 lower bound above b;
  - within-row final against draft at least +1.49 pp whole-roster, with CI95 lower bound above 0;
  - `intent_changed_after_call` = 0;
  - uncalled rows show no loss beyond the A/A width |o| = 1.15 against the sealed R2b column. This comparison is descriptive, because it is cross-flight.

**Stage 2, effectiveness (339-E1), only after P1 passes.**
- **Arms:** lock against lock plus offer, in one chain (in-chain control; the stage3 effect-floor gate refuses a cross-flight contrast). Roster: TRAIN Fold A, n = 1,080, which the design never read.
- **Cost:** 4,320 core contacts, plus at most 1,080 continuations and at most 1,080 ASR contacts; about **20-25 GPU-h**, roughly 22 h wall.
- **Word:** GAIN if the SLU point is at least +1.49 with CI95 lower bound above 0, and intent shows no measured loss (CI95 lower bound above -0.65). HARMFUL if the SLU CI95 upper bound is below 0.

**Expected effect against the floors (Whisper, bound-derived, harm excluded).** The call model matters:
- **Core calls like the best signal model:** +0.7 to +1.8 at a 10-50 % call rate and conversion 0.457. That is **below 1.49 at any call rate under 50 %**.
- **Core calls on every helpful row:** +2.34.
- **Perfect conversion:** at most +5.07 [+4.09, +6.14].

## 6. Go / no-go

- **NO-GO for Stage 2 on the bounds alone.** The central Whisper expectation sits under the 1.49 floor unless the core's call decision beats every model-visible signal (AUC above 0.68) or converts at 0.58 or higher. The harm budget is under 1.5 broken EXACT items per 100 calls, and every precedent of value revision broke more.
- **GO, model-free, now:** Stage 0 engineering, plus the stronger-ASR acquisition entry and its 0-core-contact Fold B tool pass. The ASR moves the ceiling more (up to +5.5 pp) than any trigger can (the trigger caps at about 0.5 of the prize at 30 % calls).
- **Conditional GO for Stage 1 (11-15 GPU-h):** after R3/R4 (ruling 338), and preferably with the stronger ASR if it passes its gate. It is the only way to measure the core's own call precision and conversion, which this note can only bound. Its STOP rule bounds the loss to one flight.
- The intent lock, lazy transcription, cite-and-protect and the in-call draft keep the design inside ruling 339 and directive 206. The transcript never reaches the intent decision, nothing is transcribed by default, and the core keeps answer authority.
