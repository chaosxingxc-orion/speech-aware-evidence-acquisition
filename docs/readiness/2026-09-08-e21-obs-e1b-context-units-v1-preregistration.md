# OBS-E1b: the speaker-turn unit, delivered with its context

**Preregistration. Not a GO, not a registered flight, and not an amendment.** `SAEA-E21-OBS-E1-SPEAKER-TURN-UNITS-V1`
stays REJECTED under its own preregistered rule. This document fixes, before any contact, what
OBS-E1b would send, what it would stitch, what it would be measured against and what would count as
a win — so that if the owner ever says GO, nothing below can be chosen after seeing a number.

| | |
|---|---|
| what asked for it | `docs/readiness/2026-09-08-e21-obs-e1-person-harm-decomposition-v1.md`, candidate (a) |
| coordinator decision | 2026-09-08, from that decomposition; the owner's OBS-E1 GO of 2026-09-07 covers its named successor |
| plan | `docs/receipts/obs/e21-speaker-turn-units-v3.json`, sha256 `b2cb3899…b75976` (row `SAEA-E21-MF-SPEAKER-TURN-UNITS-V3`) |
| twin plan | `docs/receipts/obs/e21-uniform-context-units-v3.json`, sha256 `10a7e5d7…64d1f8` |
| stitch | `saea-obs-context-ownership-v1` (`reproduction.obs_ownership`), proved in `docs/checks/speech-aware-evidence-acquisition/2026-09-08-e21-obs-e1b-stitch-proof/` |
| cells | `configs/experiment/e21-obs-e1b-context-units-v1.json` (arm) · `…-uniform-twin-v1.json` (form twin) |
| wire check | `docs/checks/speech-aware-evidence-acquisition/2026-09-08-e21-obs-e1b-seam/` — **PASS**, both cells, zero contacts |
| exposure rows | `SAEA-E21-MF-SPEAKER-TURN-UNITS-V3`, `SAEA-E21-MF-OBS-E1B-SEAM-V1` (both model-free, both closed). **The two FLIGHT rows do not exist and must be registered, with `consumed = no`, before the first contact.** |

---

## 1. The measurement this cell answers

OBS-E1 bought **+1.0487** points of corpus WER and sold **2.0912** points of ConEC-mirror PERSON
entity WER. The model-free decomposition named the sixty-one excess errors:

* **78.7 %** of them sit in units under **ten seconds**, which hold 23.3 % of the PERSON words;
* units of **sixty seconds or more were better** in the cell than in the comparator, by seven errors;
* **93.4 %** of the harm is within three seconds of a unit boundary, and the comparator's own PERSON
  rate over those same words is flat — the words are not intrinsically harder;
* the cut goes through a multi-word name **once in 656**, so the damage is *beside* the name, not
  *through* it;
* **both edges** are damaged and the end only 1.2 times worse than the start (0.0533 against 0.0435
  excess errors per word, against 0.0150 in the interior).

A truncate-at-the-tail failure produces an end-side effect. A **missing-context** failure produces
both. OBS-E1b is the one candidate that acts on that: **give the short unit back the conditioning its
shortness removed, and change nothing else.**

## 2. What is delivered, and what is stitched

Each plan-v3 unit is delivered as **`[left context | the turn | right context]`** audio. The
**stitched text is the turn's own transcription only.**

The context rule (`analysis.e21_speaker_turn_units.context_bounds`), fixed model-free:

1. a nominal **5.0 s** margin per side — the middle of the three the decomposition priced;
2. a floor of **10.0 s** of delivered cut, so a short turn gets *more* context, never less;
3. a ceiling of **90.0 s** of delivered cut — `MAX_UNIT_SECONDS`, so a long unit gets less or none;
4. the extra seconds split evenly, a side that runs out of call handing its remainder to the other.

**The ceiling carries the slot argument.** `reproduction.obs_loop._load_unit_plan` already refuses a
unit longer than `obs_buffer_seconds`, and the slot receipt certified the 90-second window at 2.72x
against the 6,144-token slot. Capping the *delivered* cut at the same 90 s means that refusal keeps
passing untouched and **no re-certification is needed**; the units it starves of context are exactly
the ≥ 60 s ones the measurement says need none.

### The plan, in numbers

| | v2 (OBS-E1, as flown) | **v3 (OBS-E1b)** | twin (uniform 27.60 s) |
|---|---:|---:|---:|
| units = contacts | 5,122 | **5,122** | 5,144 |
| turn seconds cut | 141,345.853 | **141,345.853** | 141,345.853 |
| context seconds added | 0 | **49,968.499** | 51,440.000 |
| delivered cut | 141,345.853 | **191,314.352** | 192,785.853 |
| delivered with the 2.0 s tails | 151,589.853 | **201,558.352** | 203,073.853 |
| delivered cut min / median / max | 1.09 / 25.78 / 90.00 | **11.00 / 27.78 / 90.00** | 11.00 / 37.60 / 37.60 |
| mean delivered cut | 27.596 | **37.351** | 37.478 |

4,874 of the 5,122 units get the full 10.0 s; 248 are trimmed by the ceiling; 15 get none. Over the
5,078 boundaries the shared region is **10.0 s at the median** and **0.0 s on seven of them**.

**The turns do not move.** v3 is a derivation of the committed v2 plan and the builder asserts every
unit's span, speaker facts, cut kinds, flags, absorbed slivers and reference-word range field by
field, on all 5,122 units, before writing a byte.

## 3. The stitch decision, and why it is the one that can be preregistered

Two protocols were available. They were weighed on **which of them can be proved without a contact.**

|  | **(i) overlap alignment — CHOSEN** | (ii) boundary marker — rejected |
|---|---|---|
| delivered | context + turn + context; **instruction byte-identical to OBS-E1's** | 200 ms of digital silence between context and turn, **plus a new instruction line** |
| how the turn's text is found | the neighbours transcribe the overlap too; align and cut at one word both agree on | the core is asked to obey a partial-transcription instruction |
| factors against OBS-E1 | **one** — the delivered audio | **two** — the audio *and* the instruction |
| provable model-free? | **yes**, §4 | **no.** Its correctness is a claim about instruction compliance, which this repository has never measured on this core for a partial-transcription task. Proving it needs the contact it is meant to justify. |
| tool contacts | **zero** | zero |

The repository already delivers audio whose text is not stitched, twice — `reproduction.replay_loop`
discards its REPLAY window's context by an **MMS_FA forced alignment** (a tool contact, and 5,122 of
them here), and `reproduction.repair_loop`'s window hook plus `obs_delivered_text` is the *channel*
by which a policy declares what it contributed. OBS-E1b **reuses the channel** and replaces the
aligner with an overlap the neighbours already transcribe.

**The safety argument.** Inside a run of words two neighbours agree on, the texts are the same words
in the same order, so `left[:anchor] + right[anchor:]` covers that audio once and only once — for
*every* position in the run. A displaced anchor therefore moves a word between two neighbours; it
does not remove it. Four rules, recorded per boundary: `no-overlap`, `anchor` (≥ 3 agreeing words,
taking the run whose implied cut lands nearest the boundary, length only as a tie-break),
`anchor-short` (≥ 2, counted apart), `proportional` (no shared run — the only rule that can drop a
word, and therefore the one that is gated in §6).

## 4. The proof, on sealed bytes, before any GPU

`SAEA-E21-MF-OBS-E1B-SEAM-V1`, zero contacts of every kind including forced alignment.

| | result |
|---|---|
| **P1 identity** — zero margin must reproduce the sealed OBS-E1 hypothesis | **exact: 44/44 calls, 5,122/5,122 units, retention 1.0000000** |
| **P2 round trip** at plan v3's own 5.0 s margin, contexts spliced from the sealed texts | **42/44 calls byte for byte; 367,944 of 368,011 corpus words kept (99.982 %)**; rules anchor 5,065 · anchor-short 5 · proportional 1 · no-overlap 7; cut displacement median **0**, mean **1.87** words, p95 **5** |
| **P3 disagreement** — the sealed comparator against the sealed `SAEA-E21-FULL44-TAIL2S-V1`, the same 1,593 windows of the same audio | word agreement **98.289 %**, but only **88.443 %** in the first and last 13 words of a window, and **124 of 1,593** windows identical after normalization |
| **P4 adversarial** — contexts taken from the comparator's own independent decode | retention **97.110 %** (−11,073 words, −3.0 %); proportional **122**, clamped **25** |

Two things follow, and the preregistration is built on both. **The mechanism works**: at a same-arm
overlap the stitch loses 67 words in 368,011. **The risk is real**: greedy decoding here is not
bitwise reproducible, agreement at the edges — where every overlap lives — is 88 %, and under the
most adversarial pairing available the stitch loses 3.0 %. The truth sits between, and the flight's
own realized rule mix will say where. §6 gates on it rather than assuming.

## 5. The arms, the comparator and the twin

**Arm** `E21-obs-e1b-context-units`: `bare-core`, `obs-agent-loop`, evidence `none`, instruction and
geometry byte-identical to the sealed comparator's, `obs_batch_slices` 8, 2.0 s tail, plan v3.

**Comparator**: the sealed `SAEA-E21-FULL44-DIRECT-BASELINE-V2` (`attempt-20260904T233816Z-bcd338`),
corpus WER **8.19952**, ConEC PERSON **22.48886** over 2,917 tagged reference words. Every interval
in §6 is against this arm. **OBS-E1** (7.15078 / 24.58005) is reported beside every number as the
one-factor predecessor; it is REJECTED and is not a comparator.

**Form twin** `E21-obs-e1b-uniform-twin`: equal **27.60-second clock units** with the identical
context rule, the identical ownership stitch, the identical instruction, arm, geometry and harness.

**Why this twin.** The alternative — plain long windows of the arm's mean delivered length, no
context, no ownership stitch — moves *two* things at once (where the boundaries are, and whether a
boundary's neighbourhood is heard twice) and could not be stitched by the same rule, so its harness
would differ from the arm's, which the 2026-09-03 same-harness rule forbids. The uniform twin matches
contact count (5,144 against 5,122, +0.43 %), delivered seconds (+0.77 %), the context mechanism and
the stitch, leaving **boundary placement** as the only factor. And 27.60 s is not a new number: it is
the contact-matched control the OBS-E1 preregistration itself named as OBS-E1b and declined to
register while OBS-E1 was in flight.

**Sequence.** The arm flies first and is read first. The twin is a separate cell under its own
exposure row and its own GO. The two are never in flight at once.

## 6. The decision rule, fixed here

Delta convention: **comparator minus cell**, in points; positive means the cell is better. Paired at
the CALL (44 clusters), `analysis.paired.resampled_statistic` on the pooled ratio, seed 20260903,
10,000 replicates, CI90.

| verdict | condition |
|---|---|
| **ADMITTED** | `CI90 LB(Δ PERSON) > 0` **AND** `CI90 LB(Δ corpus WER) > 0` |
| **NON-INFERIOR AND KEPT** | `CI90 LB(Δ PERSON) > −0.25009` **AND** `CI90 LB(Δ corpus WER) > 0` |
| **NO EFFECT** | neither, and CI90 on both deltas contains 0 |
| **HARM** | `CI90 UB(Δ PERSON) < −0.25009` **or** `CI90 UB(Δ corpus WER) < 0` |

**The margin is this carrier's own measured noise floor**, not an imported number: the study's null
replicate (`SAEA-E21-FULL44-NULL-REPLICATE-V1`) measured PERSON Δ +0.00000, CI90 [−0.24338,
+0.25680], max |bound| **0.25009**. OBS-E1's harm was 8.4 half-widths outside it.

**Corpus WER gets no margin.** OBS-E1 *bought* +1.0487 corpus points; a successor that hands them
back is not a repair, so that leg is a strict improvement over the comparator.

### Stitch guards — reported always, and two of them stop the cell

Reported with every verdict: the boundary rule mix and clamp count (corpus-wide, per call, and by
unit id for every non-anchor boundary); the stitched corpus word count against OBS-E1's sealed
368,011; words delivered / kept / dropped per unit; `numeric-value-accuracy-v1` against 90.7335 %;
`semantic-high-impact-error-rate-v1` against 0.0278 % (direction only, a weak guard by its own note's
admission); the remaining seven ConEC classes and the non-entity rate.

**STOP-AND-REPORT** — the run is reported but **not scored as clean**, and the verdict names the
failing guard:

* `proportional + clamped` boundaries **> 5.0 %** of the 5,078. The proof measured **0.02 %** at a
  same-arm overlap and **2.9 %** under the most adversarial pairing available, so this fires only if
  reality is worse than that ceiling.
* stitched corpus word count outside **±15 %** of 368,011. A stitch that ate or duplicated the
  transcript shows here before any metric is read.

### The falsifier, before any score

For every call: cut each delivered slice back to its own **turn** sub-range at the offsets the plan
declares, drop the 2.0 s tail, concatenate — and the result must reproduce that call's committed
`saea-diarization-v1` `audio_sha256`. This holds **only if** the turns still tile *and* the context
bounds are exactly where the plan says. It PASSED on all four dry-run calls of both cells in the wire
check; a disagreement at flight time stops the cell before it is scored.

## 7. Budgets

| | arm | twin |
|---|---:|---:|
| `planned_model_calls` | **5,635** (5,122 × 1.10) | 5,659 (5,144 × 1.10) |
| `planned_speech_audio_seconds` | **222,000** (201,558.352 × 1.10) | 224,000 |
| `planned_gpu_hours` | **2.0** | 2.0 |
| projected wall | 132 min | 133 min |
| projected prompt tokens | ~3.00 M (OBS-E1: 2.26 M) | ~3.02 M |
| worst single request | **unchanged**: the 2,258-token 90-second window, 2.72x inside the 6,144-token slot | unchanged |

**The GPU figure is bracketed, not guessed.** The OBS-E1 verdict established for this carrier and
geometry that cost tracks **encoded seconds, not requests** — its realized 1.0657 GPU-h landed 2 %
above the audio-proportional floor while the contact-proportional ceiling over-predicted by 2.9×.
Audio-proportional here: `1.0657 × 201,558.352 / 151,589.853 = 1.417` GPU-h. Contact-proportional:
`1.0657 × 5,122 / 5,122 = 1.066` — the contact model predicts **no increase at all**, because the
contacts do not move, which is exactly why the audio model is the binding one. 2.0 planned is a 1.41×
margin on the audio bracket; the projection is re-measured on the smoke and the flight **stops and
reports** if the measured rate projects past the registered ceiling.

Paid API spend 0, still. Budgets are run-cumulative across all attempts of a run id
(`core/model/adapter.py`), so a partially spent attempt cannot be re-run under the same id.

## 8. The seam, and what it refuses

Two thin derivations on the registered `obs-agent-loop` policy — no module under `rails/probes`, no
`TaskAdapter` or controller subclass, no `launcher/` directory:

* the cutter cuts `PlannedUnit.cut_start_seconds` / `cut_end_seconds`, which **are** the turn's own
  bounds on a v1/v2 plan, so every plan written before v3 cuts the same samples;
* text ownership runs once per call between dispatch and the OBS emits — the only point where every
  answer is in hand and no record has been written. Each unit's OBS record then carries
  `obs_delivered_text` and its four ownership fields beside the raw response, which
  `analysis.e21_window_pairing` already prefers, so `assert_stitch_reproduces_outputs` still binds a
  v3 run.

Fail-closed, before a window is cut: **context outside the call**; **context that does not cover its
own turn**; **a delivered cut under the 10 s minimum**; **a delivered cut over `obs_buffer_seconds`**;
**context bounds on a non-v3 plan** (a plan cut one way and stitched another); and **a
context-bearing plan at `obs_batch_slices <= 1`** — the sequential loop emits as it goes and cannot
see both sides of a boundary. `assert_tiles` and `assert_context` are both re-run by the loader on
the bytes it actually read.

**One defect the wire check caught and the seam now refuses to repeat.** A context-bearing unit's cut
runs past its turn, so the cursor could reach the call's end while units remained — 49 contacts for
50 planned units on call 4387332, a last unit dropped silently, and a falsifier that failed only
afterwards. The plan's own length is the loop bound now, and a regression test holds it.

## 9. Preconditions

**Closed** (2026-09-08): plan v3 and its receipt; the stitch decision and its four-part proof on
sealed bytes; the seam, its refusals and its byte-identity tests; the contact-free wire check —
composition, coverage, request half, turn-restricted falsifier and payload-binding stage, **PASS on
both cells**, `config_hash` `c21563da…` / `6495c695…`, `protocol_hash` `fb0a3737…` / `e7111783…`.

**Open**: each cell's own exposure row, registered and committed with `consumed = no` before the
first contact; and **the owner's GO**. Neither is granted by this document.

## 10. What this preregistration cannot claim

* **Nothing about OBS-E1's status.** It stays REJECTED; this is a successor, not an amendment.
* **Nothing about whether context helps.** The decomposition's "≤ 93.4 % addressable" is a ceiling on
  what a mechanism could reach, never a prediction that it will.
* **Nothing paper-facing.** n = 44 clusters is below the program's n ≥ 400 rule; this cell reports an
  interval and a direction and makes no effectiveness claim.
* **No margin sweep.** The context rule's three numbers were fixed model-free before any score
  existed, and the margin ladder in the stitch proof was run for the STITCH's correctness, never
  against a metric. Re-running this cell at a different margin would be a new preregistration.
* **No second cell in flight.** The twin waits for the arm's verdict; a form twin for an effect
  nobody measured buys nothing.
