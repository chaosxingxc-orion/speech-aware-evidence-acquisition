# Preregistration — the cross-call dispatcher's admission test on Earnings-21

**NOT YET FLOWN when this file was written.** One cell,
`SAEA-E21-FULL44-DISPATCH-ADMISSION-V1`: a third pass of the sealed full-44 direct baseline
`SAEA-E21-FULL44-DIRECT-BASELINE-V2` under its exact configuration **except one key**,
`obs_prefetch_depth: 1`. Written before the run id existed on the wire and before any number from
it is read.

The owner rule of 2026-09-08 orders it: *every harness module must show gain or no harm before
large-scale use.* Section 8 of
`docs/readiness/2026-09-08-agent-system-episode-and-core-pressure-v1.md` states the gate and lists
this module as the one entry still owed a receipt:

> | cross-call dispatcher (throughput) | Earnings-21 | must be NEUTRAL on score; checked against
> the null | `wt/obspipe` |

`docs/readiness/2026-09-08-e21-obs-pipeline-v1.md` is the module. This is its admission receipt.

---

## 0. What is being asked

The pipeline fix landed **default off**. `obs_prefetch_depth` is an integer ≥ 0, `0` is today's
behaviour byte for byte, and no committed fragment declared a non-zero depth. This cell is the
first fragment that does, and it exists to answer one question:

> **Does turning the dispatcher on change the score?**

It must not. The module is a *scheduler*: it moves WHEN a call's audio is cut and WHICH requests
share a decode batch. It does not move a single request byte. Section 3 of the pipeline note says
so and section 2 below is the falsifier that proves it on this cell's own bytes before any score
file is opened.

What it can move is decode-time batch composition, and this runtime is not bitwise reproducible
under greedy decoding across batch compositions. `SAEA-E21-FULL44-NULL-REPLICATE-V1` measured
exactly how much that costs on this carrier: the same request, flown twice, moves corpus WER by
−0.0200 points with a call-clustered CI90 half-width of 0.05793, and 66 % of the 1,593 windows
emit different bytes. **The dispatcher's score deltas are read against that band, not against
zero.**

The factor under test is therefore **one config key, `obs_prefetch_depth` 0 → 1**, and its two
measured consequences: batch composition (a nuisance, bounded by the null) and slot occupancy (the
gain the module exists for).

---

## 1. The composed identity, and the one key

| kind | fragment | relation to the comparator |
|---|---|---|
| model | `q4km-e21-buf90-mmproj-gpu-04ccc72a-np6` | **the comparator's own** |
| dataset | `earnings21-discovery` | **the comparator's own** |
| baseline | `e21-buf90-zero-locked-scored4-prefetch1` | **new**: a byte copy of `e21-buf90-zero-locked-scored4` plus one line, `"obs_prefetch_depth": 1` |
| experiment | `e21-full44-direct-baseline-v1` | **the comparator's own** |

`core.config.compose` over those four, measured before this row existed, and diffed key by key
against the comparator's own composition:

| | comparator | this cell |
|---|---|---|
| composed config hash | `e4b133d1df5611b4e0676cf143de07f7b9b2831ffbd247daf20e6263dfc460ae` | `94af86c3c807fc25a19fccfe64f164201bb07b397613ef733fa667cb3f0bf33e` |
| protocol hash | `06f7f3080f62a065f9c4ec76c58133161ed000412f864595d29a5ed777330145` | `5ebcb722693ad58b60ff66d6153471527acf4e0762c9078ea28f0a4c9269f6fc` |
| split identity hash | `fcc1b0bc55432d02347dcdf730c6bcef561a9b0ad9605c45b367e1ed3da5d69e` | **identical** |
| **keys on which the two composed configs differ** | — | **exactly one: `obs_prefetch_depth`, absent (= 0) vs `1`** |

**The key lands in the BASELINE fragment.** That is the placement section 5 of the pipeline note
requires, and it is deliberate: `obs_prefetch_depth` is a baseline key, so it enters `config_hash`
→ `protocol_hash` → the exposure row, and a depth change can never be mistaken for the same
protocol. The `scorers` list is the comparator's own four for the same reason as the null
replicate: `scorers` is a baseline key, so adding scorer ids would have moved a second key. The
three remaining agentic metrics are produced post hoc through `core.scoring_batch`, exactly as the
comparator's and the replicate's own were.

### 1.1 The identity anchor — a STOP condition

Before the first contact, the composed hashes are recomputed and compared against the three above,
**and the composed-values diff against the comparator is recomputed and required to name exactly
one key**. A second differing key, or a hash that is not the one written here, STOPS the flight
and reports. A one-key cell whose composition moved two keys is not a one-key cell.

The legality of the key itself is fail-closed in `core.driver.run` and
`reproduction.obs_loop.resolve_prefetch_depth`, and all four clauses hold for this fragment:
depth is an integer ≥ 0 (`1`); `obs_batch_slices > 1` (`8`); `obs_batch_samples == 1` (`1`); the
policy is `obs-agent-loop`. Nothing in this cell asks the harness to relax any of them.

### 1.2 What is deliberately NOT held fixed

1. **Batch composition**, more so than in a plain replicate. At depth 0 only windows of ONE call
   can share a decode batch; at depth 1 the tail of call N and the head of call N+1 can. This is
   the mechanism, and it is also the whole nuisance channel.
2. **The wall.** The point of the module.
3. **The serving session process instance.** This cell attaches to the coordinator's resident
   session `e21-np6-c36864-20260908` — the same session the null replicate attached to, which
   makes the throughput contrast against the replicate a same-server, same-geometry contrast.

---

## 2. The falsifier, before any score file is opened

**Every one of the 1,593 emitted slices must be byte-identical to the sealed comparator's own,
and the wire must carry the comparator's own token count.** This is the null replicate's own
section 2, unchanged, run by the same script against this cell's artifacts — because the claim it
tests is the same claim: *the request did not move.*

For every window id `<call>#w<NNNN>` in each run's own `obs-derivation.<call>.json` `SliceRecord`
dumps:

* `sha256`, `bytes`, `audio_seconds`, `start_seconds`, `end_seconds`, `sample_rate_hz` and
  `parent_sha256` equal the comparator's;
* `preprocess` is empty on both sides.

and at the wire:

* **`prompt_tokens_total` equals the comparator's `1935965` exactly**;
* metered speech seconds equal `141345.8526875` exactly.

`media_relpath` is not compared: it carries the run id and says nothing about the bytes.

**Zero disagreeing rows, or the cell is void and no score is read.** A dispatcher that changed a
request byte would not be a scheduling change, and no score contrast could repair that.

The decode-cap saturation covariate is counted beside it and reported by window id whatever it is.

---

## 3. The statistics, fixed now

Signed **cell minus comparator** throughout, so on WER a negative delta is an improvement and on
numeric accuracy a positive delta is. The same contrasts are computed a second time signed **cell
minus null replicate**.

### 3.1 The two pairings

| pairing | comparator arm | why both |
|---|---|---|
| **A — against the sealed comparator** | `SAEA-E21-FULL44-DIRECT-BASELINE-V2`, `attempt-20260904T233816Z-bcd338` | the arm every Earnings-21 margin is defined against; the admission rule below is stated on this pairing |
| **B — against the depth-0 own-null replicate** | `SAEA-E21-FULL44-NULL-REPLICATE-V1`, `attempt-20260908T113102Z-bdde07` | the replicate is a depth-0 re-fly of the same request on the same resident session. Pairing B isolates the dispatcher from everything the replicate already absorbed, and its throughput numbers are the like-for-like ones |

Both pairings use the same instrument and the same draws. Pairing A decides the status; pairing B
is reported beside it and a disagreement between them is itself a finding to be stated, never
smoothed.

### 3.2 What is computed

| statistic | unit | basis |
|---|---|---|
| corpus-WER delta and the six other pooled metrics | 44 clusters | `analysis.paired.resampled_statistic` over the pooled ratio, cluster-bootstrap by call |
| corpus-WER delta, per window | 1,593 windows | the same statistic clustered by call, and stratified by call beside it as the optimistic bound |
| per-window text identity | 1,593 windows | accepted-span and raw-completion byte identity against both arms |
| per-call and per-stratum tables | 44 calls / 9 sectors / 5 sample rates | natural mixture and equal-stratum weighting |

**10,000 replicates, seed 20260903, CI90** throughout — `analysis.e21_window_pairing`'s own frozen
draws, the ones every Earnings-21 paired read has used. Per-window rows carry corpus WER only, for
the reason the null replicate's section 3.1 states; PERSON, non-entity, ORG, numeric accuracy and
the semantic rate are per call at 44 clusters. No shared module is edited to change that.

The comparator's numbers are its committed receipts, unchanged and never re-flown. The identity
gate re-pools them and requires the published anchors back to the digit before a single contrast
is computed: corpus WER 8.1995, S/D/I 13,098 / 5,701 / 10,700 over 359,765 reference words, ConEC
overall 8.200 and non-entity 4.730, numeric accuracy 90.7335, semantic high-impact 0.02780. The
replicate's numbers are its own sealed `score-read.json`, and the same gate requires its published
corpus WER of 8.17951 back. **Both anchors must reproduce through the instrument, or no contrast
is read.**

---

## 4. The admission rule, fixed before any number exists

The margins are the null replicate's own measured call-clustered CI90 half-widths — the family
rule of 2026-09-08, for Earnings-21 only, naming the cell that measured them:

| metric | **margin** `margin_m` | **null interval** `null_m` | gating? |
|---|---:|---|---|
| corpus WER (`asr-wer-whisper`) | **0.05793** | [−0.08502, +0.03085] | **yes — primary** |
| ConEC overall | 0.05793 | [−0.08502, +0.03085] | yes |
| ConEC non-entity | 0.06475 | [−0.11375, +0.01575] | yes |
| ConEC PERSON | 0.25009 | [−0.24338, +0.25680] | yes |
| ConEC ORG | 0.35609 | [−0.44313, +0.26904] | yes |
| numeric-value accuracy | 0.15651 | [−0.18758, +0.12543] | yes |
| semantic high-impact rate | 0.00148 | [+0.00080, +0.00377] | **no — advisory** |

**The semantic high-impact rate is advisory and never gating on this carrier.** Its own
same-request null EXCLUDES zero (null verdict section 2.2: 100 vs 108 high-impact reference words
out of 359,765), and a metric whose null excludes zero cannot carry a "does not rise" clause. It
is reported in full beside every other row, and the status this cell would carry if it were gating
is reported too, so the exclusion is visible rather than convenient.

**The status, evaluated in this order on pairing A:**

1. **HARMFUL** — if any gating metric's CI90 lies entirely on the harmful side of zero **and** is
   disjoint from that metric's `null_m`; or if any gating metric's point delta exceeds `margin_m`
   on the harmful side.
2. **ADMITTED** — otherwise, if some gating metric's CI90 lies entirely on the improving side of
   zero **and** is disjoint from that metric's `null_m` (a demonstrated gain by the family rule),
   and no gating metric is harmful under clause 1.
3. **NEUTRAL** — otherwise: every gating metric's paired delta lies within `±margin_m` and no
   gating CI90 excludes zero on the harmful side. **This is the outcome the module needs and the
   one predicted below.** Section 8's gate admits NEUTRAL modules into the default plan.

`docs/receipts/harness-admission.json` receives the decided row whatever it says, with the module,
the carrier, the status, the row and the evidence pinned by run and attempt id.

### 4.1 The caveat that travels with the margin

The null replicate measures the noise of re-flying **at depth 0**, where a decode batch can only
mix windows of one call. Depth 1 mixes windows of two. It is therefore possible for this cell's
noise to be *larger* than the null's without the dispatcher having changed any semantics — and
the rule above would then read HARMFUL. That is the owner's rule and this note does not soften it:
a module whose scheduling perturbs the score beyond the carrier's measured replicate band has not
shown "no harm", whatever the mechanism. What the verdict will additionally report, if that
happens, is the diagnostic separating the two readings (per-call spread, text-identity rate,
error-structure channel), so the next decision is made on evidence rather than on this paragraph.

---

## 5. The throughput claim

Reported whatever the score says, and stated as a claim rather than a by-product, because it is
the module's whole purpose. Section 6 of the pipeline note made these three numbers mandatory for
every flight closure from this flight onward.

| number | source |
|---|---|
| **windows per minute** | the attempt's own realized rate (1,593 windows over the contact wall) and the server-log replay below |
| **mean slot utilisation and zero-slot share** | `scripts/obs_pipeline_dry_run.py`'s own measurement path (`slot launch_slot_` → `slot release` on llama.cpp's microsecond clock), applied to this attempt's own contact window carved out of the resident session's `server.log` |
| **mean GPU utilisation, parked share, requests, power, host memory** | `core.session.serving.summarize_monitor_file` over the session's `monitor.jsonl` between this attempt's first and last contact — the E7 reporting fields |

Compared against **both** depth-0 arms:

| arm | windows/min | mean slot use | zero-slot share | basis |
|---|---:|---:|---:|---|
| `SAEA-E21-FULL44-DIRECT-BASELINE-V2` (own server) | 17.770 | 77.73 % | 15.40 % | the dry-run receipt's measured block |
| `SAEA-E21-FULL44-NULL-REPLICATE-V1` (this session) | 17.089 realized | to be measured by the same replay | to be measured | its own verdict section 7 |
| **this cell, depth 1** | **predicted 21.0–22.7** | predicted ≥ 95 % | **predicted ≈ 0 %** | — |

The signed prediction: **+18 % to +23 % windows per minute against the depth-0 arms, and a
zero-slot share that falls to near zero with the residual, if any, no longer concentrated at the
43 call boundaries.** The lower bound is the purely measured ceiling (the comparator's own wall
minus its own idle seconds, 21.005 windows/min, +18.2 %); the upper is the simulator's 22.743,
which the receipt itself labels its own ceiling. **A realized rate below the depth-0 arms would
falsify the module's reason to exist** and is reported as such.

---

## 6. The prediction, signed before the cell exists

* **Status NEUTRAL.** The request bytes are identical, so every score movement should be replicate
  noise. Predicted corpus-WER delta within ±0.10 points of the comparator on pairing A, and every
  gating metric inside its own `margin_m`.
* **Throughput +18 % to +23 % windows per minute**, zero-slot share below 3 %.
* **The falsifier passes on 1,593 of 1,593 windows**, `prompt_tokens_total` = 1,935,965 exactly.
  A failure here is the interesting result: it would mean the dispatcher touched the request.
* **Per-window text identity below 60 %**, and plausibly below the replicate's own 33.90 %, since
  the depth-1 arm perturbs batch composition more than a depth-0 re-fly does.
* **Saturation 0 to 2 windows** — the comparator saturated 0, the replicate 0.
* **GPU hours at or below the family band**, i.e. ≤ 1.01, since the requests are the same and the
  wall is shorter.

---

## 7. Budgets, and the one recovery rule

| | registered | basis |
|---|---:|---|
| model calls | **1,750** | 1,593 windows plus 157 retry headroom at `obs_slice_retry_max` 1 — the comparator's own figure |
| speech-audio seconds | **150,000** | 141,345.8527 metered for one pass, rounded up with headroom |
| GPU hours | **1.2** | the family's realized band at this geometry: comparator 0.9734, replicate 1.0085, `SAEA-E21-KC-E1-BRIEF-44-V1` 0.9948, `SAEA-E21-KU-E1C-PLACEBO-44-V1` 1.0087, `SAEA-E21-FULL44-TAIL2S-V1` 0.9765 |
| paid API spend | **0** | unchanged and in force |

Budgets are cumulative across every attempt of this run id (`core/model/adapter.py` meters
`planned_model_calls` and `planned_speech_audio_seconds` against prior durable usage), so a
partially spent attempt cannot be re-run under this id.

**The abort caveat, stated because this cell is the first to carry it.** At depth 1 the driver
keeps one sample of lookahead in flight, so an attempt that dies on call N has already sent some
of call N+1's requests. **A FAILED attempt's durable spend is therefore up to one Earnings call
larger than the sequential path's — at most 64 windows, the roster's largest call
(`4341191`).** Metering is unchanged: it is per request at the moment the request is sent, and
prefetch only CUTS audio, so no spend is created before a request goes out. This changes what a
dead attempt costs, never what a complete one does.

**One experiment in flight. At most ONE recovery re-registration, and only on a CUDA fault.** A
host-memory kill is not a CUDA fault: if the resident session dies under this flight, the flight
STOPS and REPORTS rather than re-registering. The realized rate is re-measured during the pass and
the flight STOPS if it projects past 1.2 GPU-hours.

---

## 8. Serving

**Attach, never start, never stop.** Under
`docs/readiness/2026-09-07-always-on-serving-operating-note.md` this flight reaches the
coordinator's resident session `e21-np6-c36864-20260908` (fragment
`q4km-e21-buf90-mmproj-gpu-04ccc72a-np6`, `-c 36864 -np 6`, six slots of 6,144 tokens, port 8080
on loopback) through `core.session.attach_session`, which independently re-verifies loopback, the
runtime-receipt-pinned binary, both GGUF sha256s, the live pid, the pid's real process image and
socket ownership before the first contact. `scripts/run_arm_sequence.sh` is deliberately not used:
its pre-arm cleanup refuses while a serving session is resident, and its smoke step would spawn a
second llama-server.

**A mismatch, or no live session, is a STOP.**

The dispatcher's width is `max(obs_batch_slices, serving_geometry.slots)` = `max(8, 6)` = **8**,
which is the width this configuration already declared. The dispatcher does not raise the
in-flight ceiling; it stops the count from falling to zero at a boundary.

---

## 9. Claim surface

Discovery data: the 44 frozen `earnings21-original` discovery calls, exposed many times over.
**No new speech exposure** — the same audio, the same prompt and the same protocol as
`SAEA-E21-FULL44-DIRECT-BASELINE-V2`; the falsifier proves it on the bytes. No superiority,
generality, published-comparison or Stage-3 claim; no knob is tuned on it; no reference
transcript, timestamp file, `wer_tags` sidecar or bias list is opened at runtime — gold enters
only through the registered scorers, after the outputs are sealed. Earnings-22 is not contacted
and no held-out surface is named, loaded or scored.

**What this cell cannot conclude.** Nothing about any other carrier: SLURP and Audio2Tool have no
measured null, so this margin never travels to them and the dispatcher's admission there is a
separate receipt. Nothing about depth ≥ 2. Nothing about any mechanism: the dispatcher is a
scheduler and a NEUTRAL result is a licence to use it, never evidence about knowledge, evidence
supply or the agent layer.
