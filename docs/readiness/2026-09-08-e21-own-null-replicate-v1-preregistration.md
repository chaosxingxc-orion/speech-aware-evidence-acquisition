# Preregistration — Earnings-21's own greedy replicate null

**NOT YET FLOWN when this file was written.** One cell, `SAEA-E21-FULL44-NULL-REPLICATE-V1`: a
second pass of the sealed full-44 direct baseline `SAEA-E21-FULL44-DIRECT-BASELINE-V2` under its
exact configuration. Written before the run id existed on the wire and before any number from it
is read.

Owner Decision 8 of 2026-09-08 orders it. Section 3 of
`docs/readiness/2026-09-07-cross-carrier-silence-tail-v1-preregistration.md` named it in advance,
and the tail-cell closure (`docs/readiness/2026-09-07-e21-full44-tail2s-v1-verdict.md` section 10
item 1) named it again as the step before any re-lock:

> **Measure this carrier's own same-request null.** Section 3 said it in advance and this cell is
> why it matters: two of the four agentic metrics failed non-inferiority against an *imported*
> margin narrower than their own noise, so the admission question is currently unanswerable rather
> than answered. This is the named next cell.

---

## 0. What is being asked

Greedy decoding on this runtime is **not bitwise reproducible**. `llama-server` at temperature 0
returns different bytes for the same request depending on how requests batch together across the
six slots, so a cell that changed nothing at all still produces a non-zero delta. Earnings-22
measured its own version of that on 1,432 rows whose request differed only by an inert integer:
-0.0844 corpus-WER points, CI90 [-0.2356, +0.0692], with 302 of 1,432 rows emitting different
bytes. **Earnings-21 has never had that measurement**, and until it does, every Earnings-21
non-inferiority clause borrows Earnings-22's half-width and reports a margin it did not measure.

So the question is exactly: **fly the sealed comparator again, changing nothing, and see how far
the numbers move.**

The factor under test is therefore **batch composition under greedy decoding, and nothing else**.
Not the media, not the prompt, not the geometry, not the build, not the population.

---

## 1. The cell, and why it is byte-identical by construction

This cell introduces **no new config fragment**. It composes the sealed comparator's own four:

| kind | fragment |
|---|---|
| model | `q4km-e21-buf90-mmproj-gpu-04ccc72a-np6` |
| dataset | `earnings21-discovery` |
| baseline | `e21-buf90-zero-locked-scored4` |
| experiment | `e21-full44-direct-baseline-v1` |

`core.config.compose` over those four yields, measured before this row existed:

| | value |
|---|---|
| composed config hash | `e4b133d1df5611b4e0676cf143de07f7b9b2831ffbd247daf20e6263dfc460ae` |
| protocol hash | `06f7f3080f62a065f9c4ec76c58133161ed000412f864595d29a5ed777330145` |
| split identity hash | `fcc1b0bc55432d02347dcdf730c6bcef561a9b0ad9605c45b367e1ed3da5d69e` |

**These are the sealed comparator's own three, to the digit** — its sealed plan file carries the
same protocol and split hashes, and the cross-carrier preregistration section 1.4 recorded the
config hash as `e4b133d1...` before this cell was conceived.

### 1.1 The identity anchor — a STOP condition, not a report line

Before the first contact, the composed hashes above are recomputed and compared. **If the config
hash, the protocol hash or the split identity hash differs from the comparator's by one character,
the flight STOPS and reports.** A replicate whose protocol hash moved is not a replicate.

This is also why the flight declares the comparator's **four** scorers rather than the seven the
tail cell declared. `scorers` is a baseline-fragment key, so it enters `config_hash` ->
`protocol_hash`; adding scorer ids would have changed the identity this cell exists to hold fixed.
The three remaining agentic metrics are produced exactly as the comparator's own were — post hoc,
through `core.scoring_batch` over a complete verified manifest (section 3.2).

### 1.2 What is deliberately NOT held fixed

Nothing is deliberately varied — but two things cannot be held fixed, and they are named here
rather than discovered later:

1. **Batch composition.** Six slots, 1,593 windows, `obs_batch_slices` 8: which windows share a
   decode batch depends on arrival timing. This is the factor.
2. **The serving session.** The comparator ran under its own spawned server; this cell attaches to
   the coordinator's resident session at the same geometry (section 7). The command line, the
   binary sha256, the two GGUF sha256s, `-c 36864 -np 6`, six slots of 6,144 tokens and
   `GGML_CUDA_DISABLE_GRAPHS=1` are all identity-checked by `core.session.attach_session` before
   the first contact, so the *server* is the same server; only the process instance differs.

---

## 2. The falsifier, before any score file is opened

**Every one of the 1,593 emitted slices must be byte-identical to the sealed comparator's own.**

The authoritative surface is each run's own `obs-derivation.<call>.json` `SliceRecord` dumps —
what `core.model.SliceRegistry` sealed. For every window id `<call>#w<NNNN>`:

* `sha256` equals the comparator's `sha256` for that window;
* `bytes` equals the comparator's;
* `audio_seconds`, `start_seconds` and `end_seconds` equal the comparator's;
* `preprocess` is empty on both sides — no tail, no VAD trim, no preprocessing.

and at the wire level:

* **`prompt_tokens_total` equals the comparator's `1935965` exactly.** The prompt text is the same
  bytes and the audio is the same bytes, so the encoder must emit the same token count. A
  difference here means something moved that this cell claims did not.

**Zero disagreeing rows, or the cell is void and no score is read.** 1,593 windows over 44 calls,
141,345.8526875 metered speech seconds — the comparator's own figures to the digit.

---

## 3. The statistics, fixed now

Signed throughout as **replicate minus comparator**, so on WER a negative delta means the
replicate scored better and on numeric accuracy a positive delta does. Under a true null both
signs are noise.

### 3.1 What is computed

| statistic | unit | basis |
|---|---|---|
| **per-window text-identity rate** | 1,593 windows | the fraction of windows whose accepted span text is byte-identical across the two arms, reported beside the raw `MODEL_RESPONSE` identity rate |
| **corpus-WER delta, per call** | 44 clusters | `analysis.paired.resampled_statistic` over the pooled ratio, cluster-bootstrap by call |
| **corpus-WER delta, per window** | 1,593 windows | the same statistic clustered by call, and stratified by call beside it as the optimistic bound |
| **PERSON entity WER, non-entity WER, numeric-value accuracy, ConEC overall, semantic high-impact rate** | 44 clusters | the same cluster bootstrap on each metric's own pooled ratio |

**10,000 replicates, seed 20260903, CI90** throughout — `analysis.e21_window_pairing`'s own frozen
draws (`E21_WINDOW_SEED`, `E21_WINDOW_REPLICATES`, `E21_WINDOW_CI_LEVEL`), the same ones every
Earnings-21 paired read has used.

**Per-window rows carry corpus WER only**, because the registered instrument's per-window row
(`analysis.e21_window_pairing` through `build_e21_tail2s_verdict.window_rows`) emits the ConEC
`__ALL__` bucket and the semantic-impact counts, not the per-entity buckets. PERSON, non-entity
and numeric accuracy are therefore **per call, at 44 clusters**, and this note says so in advance
rather than the verdict explaining it afterwards. No shared module is edited to change that.

### 3.2 How each arm's numbers are produced

* **Comparator**: its committed receipts, unchanged and never re-flown —
  `docs/checks/speech-aware-evidence-acquisition/2026-09-06-e21-agentic-metric-baseline/scoring/verified-score-read.json`
  for corpus WER, ConEC and numeric, and
  `docs/checks/speech-aware-evidence-acquisition/2026-09-06-e21-semantic-impact-baseline/verdict/result-summary.json`
  for the semantic metric. The identity gate re-pools them and requires the published anchors back
  to the digit before a single contrast is computed: corpus WER 8.1995, S/D/I 13,098 / 5,701 /
  10,700 over 359,765 reference words, ConEC overall 8.200 and non-entity 4.730, numeric accuracy
  90.7335, semantic high-impact 0.02780.
* **Replicate**: `saea-driver finalize` scores the four declared scorers over the complete
  manifest; then four re-scoring bundles — byte-identical artifact copies with a manifest
  differing only in artifact paths and a one-scorer list, the mechanism
  `analysis.e21_agentic_metric_baseline.build_rescore_bundle` already uses — run through
  `core.scoring_batch` with `--include-per-sample`, one complete verified manifest per process,
  **never sharded**. The `asr-wer-whisper` bundle is the replicate's own internal anchor: it must
  reproduce what finalize sealed.

### 3.3 The per-window pairing instrument

`analysis.e21_window_pairing`, the registered instrument of `SAEA-E21-MF-WINDOW-PAIRING-V1`, with
its own proof `assert_stitch_reproduces_outputs` rebuilding all 44 stitched hypotheses byte for
byte on **both** arms before a single per-window number is computed. Window ids are positions in
the stitch order, so every paired id must carry the same cut span in both arms; a span
misalignment refuses the read rather than being reported.

---

## 4. What the null is FOR, and the rule that will be applied

**This measurement replaces the imported Earnings-22 margin in every future Earnings-21 cell.**

Today section 4.3 of the cross-carrier preregistration sets Earnings-21's clause-1 threshold at
-0.2356 and its clause-2 non-inferiority margin at +/-0.1524, both **imported** from Earnings-22
and both labelled as such. The tail cell then failed clause 2 on two metrics whose own intervals
were wider than that imported margin — a statement about the margin, not a measured harm.

**The rule, fixed here before any number exists:**

> For each metric, the Earnings-21 non-inferiority margin becomes **the half-width of this null's
> own call-clustered CI90 on that metric**: `margin_m = (ci_high_m - ci_low_m) / 2`. A future
> Earnings-21 cell is non-inferior on metric *m* iff its own CI90 stays inside `+/-margin_m`
> (signed for direction), and demonstrates an effect iff its CI90 is disjoint from **this null's
> measured interval**, not merely from zero.

Three commitments that go with it:

1. **The margin is per metric.** Corpus WER, PERSON entity WER, non-entity WER, numeric accuracy
   and the semantic rate get five different margins, because they have five different noise
   levels. The tail cell's failure is precisely what one margin for all of them produces.
2. **The measured margin replaces the imported one only for Earnings-21**, and only from the date
   this cell closes. It is never carried to SLURP or Audio2Tool, which have their own unmeasured
   nulls.
3. **A single replicate measures the null with 44 clusters and no more.** The interval this cell
   produces is itself uncertain; it is a better margin than an imported one, not an exact one, and
   every verdict that uses it must say which cell measured it.

**This cell admits and refutes nothing.** It has no ADMITTED / NOT-ADMITTED verdict, no mechanism
and no claim about the tail, the brief, or any knob. Its whole output is a table of intervals.

---

## 5. The prediction, signed before the cell exists

* **Corpus WER moves, and by less than the tail cell's -0.93.** Earnings-22's own null moved
  -0.0844 points on 3-second utterances. Earnings-21's unit is a 90-second window with a
  1,024-token decode cap, so a single divergent window can cost or save a whole window's text.
  Predicted corpus-WER delta **-0.35 to +0.35 points**, with the CI90 half-width **wider** than
  Earnings-22's 0.1524 rather than narrower.
* **The text-identity rate is well below 1.0.** Earnings-22 saw 302 of 1,432 rows (21.1 %) differ
  on a 3-second utterance. A 90-second window has roughly 30x more tokens to diverge in, so the
  per-window identity rate is predicted **below 60 %** — possibly far below. A rate at or near
  100 % would say this runtime is more deterministic than the Earnings-22 measurement implies, and
  would be the more interesting result.
* **Saturation is arm-local and small.** The comparator saturated 0 windows of 1,593; the three
  post-comparator passes at this geometry saturated 1 to 2 each, on four different calls.
  Predicted **0 to 2** saturated windows, on calls that are not the comparator's, since it has
  none. Saturation is reported by window id whatever it is, because a saturated window is 90 s of
  audio contributing the empty string and is a named covariate of this family.
* **Both metrics that failed the tail cell's clause 2 have null half-widths above 0.1524.** That
  is the concrete prediction the tail closure implies, and it is what would make the imported
  margin demonstrably the wrong instrument rather than merely an unmeasured one.

---

## 6. Budgets, and the one recovery rule

| | registered | basis |
|---|---:|---|
| model calls | **1,750** | 1,593 windows plus 157 retry headroom at `obs_slice_retry_max` 1 — the comparator's own figure |
| speech-audio seconds | **150,000** | 141,345.8527 metered for one pass, rounded up with headroom |
| GPU hours | **1.2** | the family's realized band at this geometry: comparator **0.9734**, `SAEA-E21-KC-E1-BRIEF-44-V1` **0.9948**, `SAEA-E21-KU-E1C-PLACEBO-44-V1` **1.0087**, `SAEA-E21-FULL44-TAIL2S-V1` **0.9765** |
| paid API spend | **0** | unchanged and in force |

Budgets are cumulative across every attempt of this run id (`core/model/adapter.py` meters
`planned_model_calls` and `planned_speech_audio_seconds` against prior durable usage), so a
partially spent attempt cannot be re-run under this id.

**One experiment in flight. At most ONE recovery re-registration, and only on a CUDA fault.**
A host-memory kill is **not** a CUDA fault: if the resident session dies under this flight, the
flight STOPS and REPORTS rather than re-registering. The realized rate is re-measured during the
pass and the flight STOPS if it projects past 1.2 GPU-hours.

---

## 7. Serving

**Attach, never start, never stop.** Under
`docs/readiness/2026-09-07-always-on-serving-operating-note.md` this flight reaches the
coordinator's resident session `e21-np6-c36864-20260908` (fragment
`q4km-e21-buf90-mmproj-gpu-04ccc72a-np6`, `-c 36864 -np 6`, port 8080 on loopback) through
`core.session.attach_session`, which independently re-verifies loopback, the
runtime-receipt-pinned binary, both GGUF sha256s, the live pid, the pid's real process image and
socket ownership before the first contact. `scripts/run_arm_sequence.sh` is deliberately not used:
its pre-arm cleanup refuses while a serving session is resident, and its smoke step would spawn a
second llama-server. The monitor summary over this attempt's own contact window is reported in the
verdict.

**A mismatch, or no live session, is a STOP.**

---

## 8. Claim surface

Discovery data: the 44 frozen `earnings21-original` discovery calls, exposed many times over. **No
new speech exposure** — this is the same audio, the same prompt and the same protocol as
`SAEA-E21-FULL44-DIRECT-BASELINE-V2`. No superiority, generality, published-comparison or Stage-3
claim; no knob is tuned on it; no reference transcript, timestamp file, `wer_tags` sidecar or bias
list is opened at runtime — gold enters only through the registered scorers, after the outputs are
sealed. Earnings-22 is not contacted and no held-out surface is named, loaded or scored.
