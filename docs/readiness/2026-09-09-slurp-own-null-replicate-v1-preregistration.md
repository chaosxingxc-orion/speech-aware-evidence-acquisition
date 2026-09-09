# Preregistration — SLURP's own greedy replicate null

**NOT YET FLOWN when this file was written.** One cell,
`SAEA-SLURP-DEV1000-NULL-REPLICATE-V1`: a second pass of the sealed DEV-1000 closed-list direct
comparator `SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1` under its exact configuration. Written before
the run id existed on the wire and before any number from it is read.

Owner Decision 10 of 2026-09-08 orders it. Section 3 of
`docs/readiness/2026-09-07-cross-carrier-silence-tail-v1-preregistration.md` named it in advance,
and the SLURP tail cell's closure
(`docs/readiness/2026-09-09-slurp-silence-tail-v1-verdict.md` §8.1 item 1) named it again as the
**blocking** next cell:

> **The SLURP same-request null**, and it is now the blocking one. §3 named it before this cell
> existed and this result is exactly the case it was named for: an effect whose direction is clear
> and whose size cannot be judged against a borrowed bar. Without it, clause 1's +0.60 will keep
> deciding SLURP cells on an Earnings-22 number.

The Earnings-21 precedent is `docs/readiness/2026-09-08-e21-own-null-replicate-v1-preregistration.md`
and its verdict; this note follows its structure deliberately, so the two carriers' nulls are read
the same way.

---

## 0. What is being asked

Greedy decoding on this runtime is **not bitwise reproducible**. `llama-server` at temperature 0
returns different bytes for the same request depending on how requests batch together across the
eight slots, so a cell that changed nothing at all still produces a non-zero delta.

**SLURP has never had that measurement.** Every SLURP margin in this study is borrowed:

* the silence-tail cell's admission rule used **±0.60 pp**, the Earnings-22 same-request null's
  half-width on the same scale, and its own verdict §5 says so where it uses it;
* the KV slot-knowledge-view family declares its non-inferiority margin **IMPORTED** in §6.4 of
  `docs/readiness/2026-09-08-slurp-slot-knowledge-views-kv-v1-preregistration.md`, from EVO-S1
  round 1's finding that **286 of 1,019 byte-identically prompted rows (28.1 %) returned different
  text anyway** (`docs/readiness/2026-09-06-slurp-evo-s1-round-1-verdict.md` §1);
* the logprob judge probe carries the same 28 % flip figure as its stated greedy null.

So the question is exactly: **fly the sealed comparator again, changing nothing, and see how far
the numbers move.**

The factor under test is therefore **batch composition under greedy decoding, and nothing else**.
Not the media, not the prompt, not the geometry, not the build, not the population, not the scorer.

---

## 1. The cell, and why it is identical by construction

This cell introduces **no new config fragment**. It composes the sealed comparator's own four:

| kind | fragment |
|---|---|
| model | `q4km-mmproj-free-speech-native-np8-base-speech-query-prefix-max64` |
| dataset | `slurp-speech-native-dev1000` |
| baseline | `slurp-direct-closed-list` |
| experiment | `slurp-dev1000-closed-list-direct-v1` |

`core.config.compose` over those four, plus `data.splits.split_identity_hash` over the roster and
`core.config.protocol_hash` over the pair, yields — **measured before this row existed, with zero
model, GPU, tool, embedding and network contacts**:

| | value |
|---|---|
| composed config hash | `6be064ba49d4b3b8b430aa063b4fef46a898ce5a0b3702fe35c4896d5d1b894f` |
| protocol hash | `7e83a70508068d1a1c2512cabbc91b8417821ae5796038c2bc6fa4950bb951b2` |
| split identity hash | `8580d199bffc95a51ad6d8c5b2a2e9e39faa2c551dd095f8afcd78174a1e3c84` |
| split id / rows | `DEV-1000`, 1,000 |
| runtime view sha256 | `e148dbbcbda5b5145de9d3270f8bf7d6fb83fd00c7533f5ffa0fea1735fa0e87` |

**These are the sealed comparator's own, to the digit.** Its sealed run manifest
(`f908ff4c7b0267322b34c7bf2ca9ad29d6db97ee8bb3cf18bf8824a057ebc94c`) carries protocol hash
`7e83a705…951b2`; the 2026-09-06 projection-v2 re-lock records the split identity as
`8580d199…1e3c84`; and the silence-tail cell's own exposure row records the comparator's config
hash as `6be064ba…`. The run id differs and **nothing else does**.

### 1.1 The identity anchor — a STOP condition, not a report line

Before the first contact, `FlightRuntime.preflight` recomputes all three. **If the config hash, the
protocol hash or the split identity hash differs from the comparator's by one character, the flight
STOPS and reports.** A replicate whose protocol hash moved is not a replicate.

This is also why the flight declares the comparator's **three** scorers —
`slurp-slu-official`, `slurp-slu`, `cost` — rather than the paper-facing projected-v2 scorer.
`scorers` is a baseline-fragment key, so it enters `config_hash` → `protocol_hash`; declaring the
projected scorer would have changed the identity this cell exists to hold fixed. The paper-facing
numbers are produced exactly as the comparator's own were and as the silence-tail cell's were —
post hoc, through `core.scoring_batch` over a complete verified manifest under one derived manifest
per arm that differs from the sealed one **only** in its `scorers` list (§3.2).

### 1.2 What is deliberately NOT held fixed

Nothing is deliberately varied — but two things cannot be held fixed, and they are named here
rather than discovered later:

1. **Batch composition.** Eight slots, 1,000 rows, `max_in_flight` 8: which requests share a decode
   batch depends on arrival timing. This is the factor.
2. **The serving session.** The comparator ran under its own spawned server; this cell attaches to
   the coordinator's resident session at the same geometry (§7). The command line, the binary
   sha256, the GGUF sha256, `-c 65536 -np 8`, eight slots of 8,192 tokens and the
   `LLAMA_SPEECH_FEATURE_ROOT` packet root are all identity-checked by `core.session.attach_session`
   before the first contact, so the *server* is the same server; only the process instance differs.

---

## 2. The falsifier, before any score file is opened

**The request side must be provably unchanged on every one of the 1,000 rows.**

| check | requirement |
|---|---|
| rows flown | exactly 1,000, zero missing and zero extra against the sealed comparator's roster |
| sample ids | the comparator's own 1,000 published ids, no variant suffix |
| speech packet handed to the decoder | equal to the comparator's promoted packet **by sha256**, from the pinned promotion receipt `/home/chao/feat-cache/slurp-q4km-packets-04ccc72a/DEV-1000-promotion.json` (`2accbdc5…8fe6`) |
| `mmproj_loaded` | false on both arms |
| rendered system instruction | sha256 equal to the comparator's, and the same 7,583 characters |
| metered speech seconds | **2,884.7936875**, the comparator's own figure to the digit |
| **prompt tokens total** | **2,190,161**, the comparator's own figure exactly |

**Zero disagreeing rows, or the cell is void and no score is read.** The prompt bytes and the audio
packets are the same bytes, so the encoder must emit the same token count; a difference in
`prompt_tokens_total` means something moved that this cell claims did not. The silence-tail cell
proved the same instrument works on this carrier at single-token resolution (+26 on every row, no
residue), so a *zero* difference here is a check with teeth rather than a formality.

---

## 3. The statistics, fixed now

Signed throughout as **replicate minus comparator**. Under a true null both signs are noise.

### 3.1 What is computed

| statistic | unit | basis |
|---|---|---|
| **raw completion identity rate** | 1,000 rows | fraction of rows whose sealed `text` is byte-identical across the two arms — the quantity EVO-S1's 28.1 % estimated |
| **parsed-prediction flip rate** | 1,000 rows | fraction whose parsed `(scenario, action)` differs, and separately whose parsed slot set differs, under `reproduction.slurp_scoring.parse_slu_response` |
| **projected-intent flip rate** | 1,000 rows | the same on the label the paper-facing scorer actually reads, after `slurp-legal-label-projection-v2` |
| **intent / scenario / action accuracy deltas** | 1,000 rows | `analysis.paired.paired_contrast`, mean of the per-row 0/1 |
| **entities strict F1, Word-F1, Char-F1, SLU-F1 — micro** | 1,000 rows | the paper-facing pooled ratio, `analysis.paired.resampled_statistic` over each metric's own summed TP/FP/FN |
| **the same four — per row** | 1,000 rows | `paired_contrast` over the per-row F1, reported beside the micro figure, as the silence-tail cell reports them |
| **per-scenario deltas** | 18 gold scenarios | intent and SLU-F1, with saves and harms |
| **per-cluster deltas** | 124 speaker clusters | intent and SLU-F1, and the count of clusters that moved |

**10,000 replicates, seed 20260903, CI90** throughout — every SLURP paired read's own settings.

**Both resampling families, side by side.** Speaker clusters (`usrid`) and gold-scenario strata
cannot be crossed on this carrier — a SLURP speaker records across scenarios — so
`clustered_by_speaker` and `stratified_by_scenario` are reported side by side and the
**speaker-clustered one is read as the honest interval**, exactly as the silence-tail cell reads
it and as Earnings-21 reads its call-clustered one. Both weightings — natural mixture and
equal-stratum — are reported, as the family rule requires.

**Under both scorers.** Everything above is computed under the paper-facing
`slurp-slu-official-projected-v2` and, beside it, the secondary `slurp-slu-f1-normalized-v1`.

### 3.2 How each arm's numbers are produced

* **Comparator**: its sealed bytes, unchanged and never re-flown — attempt
  `attempt-20260905T060424Z-2c5596`, run manifest `f908ff4c…c94c`, outputs `34fda7fa…885d`.
* **Replicate**: `runtime.score` settles the attempt over the three declared scorers; then one
  derived manifest per arm — differing from the sealed one only in `scorers` — is scored through
  `core.scoring_batch` with `include_per_sample=True`, **one job per complete manifest, never
  sharded**, exactly the mechanism the silence-tail read used.
* **The identity gate, before any contrast is computed.** The sealed comparator must reproduce its
  nine published anchors from its own sealed bytes, to the digit: scenario **82.60**, action
  **74.60**, intent **73.10**, entities strict **21.91**, Word-F1 **33.69**, Char-F1 **38.20**,
  SLU-F1 **35.80**, unparsed **3**, and the port-vs-official identity check passed. A gate failure
  writes the failure and stops.

---

## 4. What the null is FOR, and the rule that will be applied

**This measurement replaces the imported margin in every future SLURP cell.**

**The rule, fixed here before any number exists:**

> For each metric, the SLURP non-inferiority margin becomes **the half-width of this null's own
> speaker-clustered CI90 on that metric**: `margin_m = (ci_high_m − ci_low_m) / 2`. A future SLURP
> cell is non-inferior on metric *m* iff its own CI90 stays inside `±margin_m` (signed for
> direction), and demonstrates an effect iff its CI90 is disjoint from **this null's measured
> interval**, not merely from zero.

Four commitments that go with it:

1. **The margin is per metric.** Intent, scenario, action, entities-strict F1, Word-F1, Char-F1 and
   SLU-F1 get seven different margins, because they have seven different noise levels. Earnings-21's
   null showed one margin for all metrics is precisely what produces uninterpretable clause
   failures.
2. **It replaces the imported figure for SLURP only**, and only from the date this cell closes. It
   is never carried to Earnings-21 (which has its own) or to Audio2Tool (which still has none).
   Concretely it supersedes: the silence-tail rule's ±0.60 pp; §6.4 of the KV preregistration, whose
   own text says "the moment the SLURP own-null replicate lands, KV-0's non-inferiority margin is
   restated from it and this section is superseded"; and the 28 % flip floor the logprob judge probe
   and KU-S3 / KU-S4 read against.
3. **These verdicts read against these margins**: the KV slot-knowledge-view family (KV-0 first,
   then KV-1/2/3), KU-S3, KU-S4, and the logprob judge probe. Every one of them must name this cell
   where it uses the number.
4. **A single replicate measures the null with 1,000 rows and 124 clusters and no more.** The
   interval this cell produces is itself uncertain; it is a better margin than an imported one, not
   an exact one.

### 4.1 The silence-tail re-read, preregistered

The verdict will carry a **dated paragraph** re-reading
`docs/readiness/2026-09-09-slurp-silence-tail-v1-verdict.md` §4 clause 1 — "the CI90 lower bound on
the intent delta is > +0.60 pp" — against the margin measured here, and clauses 2 and 3 beside it.
This is a **re-reading of already-sealed numbers against a new reference, not a new measurement**:
the tail cell is **not re-flown**, its sealed bytes are not re-scored, and its NOT ADMITTED status
is not reopened by this cell — only its *reason* can move, exactly as Earnings-21's null re-read its
own tail cell.

**This cell admits and refutes nothing.** It has no ADMITTED / NOT-ADMITTED verdict, no mechanism
and no claim about the tail, the media, or any knob. Its whole output is a table of intervals.

---

## 5. The prediction, signed before the cell exists

* **Intent accuracy moves, and by less than the tail cell's +1.30 pp.** Predicted intent delta
  **−0.8 to +0.8 pp**, with the speaker-clustered CI90 half-width **below** the imported 0.60 pp —
  because a 64-token completion on a 2.9-second utterance has far less room to diverge than
  Earnings-21's 1,024-token, 90-second window, whose corpus half-width came out at 0.058 on a much
  larger denominator.
* **The raw-text identity rate is well below 1.0, and near EVO-S1's figure.** EVO-S1 measured
  28.1 % of byte-identically prompted rows returning different text on this carrier and build.
  Predicted **15 % to 40 %** of rows differing here. A rate near 0 % would say this geometry is far
  more deterministic than the EVO-S1 number implies and would be the more interesting result.
* **The projected-intent flip rate is a small fraction of the text flip rate.** Most divergence on a
  closed-list task should be in slot filler text, not in the label. Predicted **under 5 %** of rows
  changing their projected intent.
* **The entity-side metrics are noisier than the label metrics.** SLU-F1's half-width is predicted
  **above** intent's, because entity fillers are free text and the label is one of 60 choices.
* **Unparsed count moves by at most 2** from the comparator's 3.

---

## 6. Budgets, and the one recovery rule

**The plan cell is the comparator's own, unchanged**, because `execution_plan` is an
experiment-fragment key and therefore enters `config_hash`: tightening it would move the identity
anchor this cell exists to hold fixed.

| | machine cap (enforced) | this cell's own operating budget |
|---|---:|---:|
| model calls | **1,050** | **1,008** = 1,000 rows + 8 contacts of canary/retry headroom, one per serving slot |
| speech-audio seconds | **3,000** | **2,884.7937**, the comparator's own metered figure |
| GPU hours | **1.0** | **0.30** — a STOP threshold, against the silence-tail cell's realized 0.0687 GPU-h for 1,000 rows at this geometry (242.6 rows/min) and the comparator's own ~0.105 |
| paid API spend | **0** | 0, unchanged and in force |

Budgets are cumulative across every attempt of this run id (`core/model/adapter.py` meters
`planned_model_calls` and `planned_speech_audio_seconds` against prior durable usage), so a
partially spent attempt cannot be re-run under this id. This run id has no prior spend.

**One experiment in flight. At most ONE recovery re-registration, and only on a CUDA fault.**
A host-memory kill is **not** a CUDA fault: if the resident session dies under this flight, the
flight STOPS and REPORTS rather than re-registering. The realized rate is re-measured during the
pass and the flight STOPS if it projects past 0.30 GPU-hours.

---

## 7. Serving

**Attach, never start, never stop.** Under
`docs/readiness/2026-09-07-always-on-serving-operating-note.md` this flight reaches the
coordinator's resident session `slurp-np8-base-c65536-20260909` (fragment
`q4km-mmproj-free-speech-native-np8-base-speech-query-prefix-max64`, `-c 65536 -np 8`, eight slots
of 8,192 tokens, port 8080 on loopback, `LLAMA_SPEECH_FEATURE_ROOT` on the **base** packet root
`/home/chao/feat-cache/slurp-q4km-packets-04ccc72a` — the comparator's own) through
`core.session.attach_session`, which independently re-verifies loopback, the runtime-receipt-pinned
binary, the GGUF sha256, the live pid, the pid's real process image and socket ownership before the
first contact. The monitor summary over this attempt's own contact window is reported in the
verdict.

**A mismatch, or no live session, is a STOP.**

---

## 8. Claim surface

Dev-tier optimization data: the 1,000 frozen `slurp` devel rows of `DEV-1000`, exposed many times
over. **No new speech exposure** — this is the same audio, the same packets, the same prompt and the
same protocol as `SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1`. No superiority, generality,
published-comparison or Stage-3 claim; no knob is tuned on it; no SLURP gold label, devel sentence
text or annotation is opened at runtime — the flight adapter is label-free by construction and its
`gold()` refuses outright, so gold enters only through the registered scorers after the outputs are
sealed, plus the gold *scenario* used as a bootstrap stratum label, which is the same device every
SLURP verdict on this carrier uses. The SLURP `test` split and FINAL60 are not named, loaded or
scored; Earnings and Audio2Tool are not contacted.
