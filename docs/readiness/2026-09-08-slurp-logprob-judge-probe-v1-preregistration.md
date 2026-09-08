# The SLURP logprob-as-judge probe — preregistration (2026-09-08)

Row id `SAEA-SLURP-DEV1000-CLOSED-LIST-LOGPROB-V1`, profile `bounded-discovery-probe`.
Smoke `SAEA-SLURP-DEV1000-CLOSED-LIST-LOGPROB-SMOKE-4-V1`.
Config: `configs/experiment/slurp-dev1000-closed-list-logprob-v1.json`,
`configs/model/q4km-mmproj-free-speech-native-np8-base-speech-query-prefix-max64-logprobs5.json`,
and the comparator's own `configs/baseline/slurp-direct-closed-list.json`, reused byte for byte.
Read: `scripts/slurp_logprob_judge_read.py`. Wire check:
`scripts/slurp_logprob_wire_check.py`, receipt
`docs/checks/speech-aware-evidence-acquisition/2026-09-08-slurp-logprob-judge-probe-wire-check/`.

**Nothing in this note has been flown.** It is written before the first contact, and every
threshold in it is fixed here rather than chosen after the numbers exist.

## 0. The question, and why it is asked now

The owner, 2026-09-08: *analyse logprobs first; the proposal needs experimental evidence.*

The proposal is the Reviewer. The agent-system design note of the same day
(`docs/readiness/2026-09-08-agent-system-episode-and-core-pressure-v1.md`, section 2) makes the
Reviewer one of four agents and lists its judges in two columns: *built today* — legal-label
projection, schema conformance, substitution-only delivery, numeric-format checks — and *named,
not built* — the brief-name near-miss detector, the acoustic re-check, the core-as-critic phase,
and **"decode-confidence signals from the sealed trace"**. That last entry is the subject of this
probe, and its wording contains the problem: there are no decode-confidence signals in any sealed
trace. MF-8 measured it exactly — the string `logprob` occurs **zero** times in the sealed SLURP
comparator's 540 KB outputs file and zero times in its 10 MB trace, because no flight ever set
`decoding_params.logprobs`. Getting the signal is a **cost**, not an available asset.

So the question this probe answers is narrow and falsifiable:

> Does the frozen core's own token confidence predict its own errors well enough to be admitted as
> a Reviewer signal, measured against the sharpest deterministic judge the study already has?

The bar is not "is there any signal". It is the **schema judge**, which MF-9 section 5.1 measured
at **72.09 % precision on 86 flagged rows (8.6 % of the roster) at zero cost**, and which that
note's own recommendation named as the gate for a targeted re-ask. A confidence flag that does not
beat a free judge is not worth a decoding parameter, and this note says so in advance.

**What this probe is not.** It is not a mechanism. It adds no evidence, no retrieval, no second
contact, no post-processor and no knowledge. It makes no SLURP accuracy claim, no superiority
claim, no generalization claim and no Stage-3 claim. Its outputs are never reported as a
comparator.

## 1. The rule, fixed now

**ADMISSION.** The confidence flag is admitted as a Reviewer signal if **either**:

* **(A)** AUROC ≥ **0.75** for **intent error** on DEV-1000, with a cluster-bootstrap **CI90 lower
  bound ≥ 0.70** (clusters = speakers); **or**
* **(B)** its **precision at 86 flags exceeds the schema judge's 72.09 %**, with a CI90 lower bound
  **strictly above** 72.09.

Otherwise the result is recorded as **NOT ADMITTED**, and the re-ask module falls back to the
deterministic judges. A NOT ADMITTED verdict is a result, is written up with the same care as an
admission, and closes the question rather than motivating a knob change.

The rule is implemented as `admission_verdict` in the read script and is unit-tested against eight
cases including both boundaries — exactly on 0.75/0.70 admits; exactly on 72.09 does not, because
the rule says *exceeds*
(`tests/unit/test_slurp_logprob_judge_read.py::test_the_admission_rule_is_exactly_as_preregistered`).

**One honesty clause, stated before any number exists.** 72.09 % and 86 are **KC-S1b's** numbers,
measured on the two-stage slot arm, under MF-9's own definition of a re-askable row ("carries an
unmatched gold mention", type-matched). This probe flies the **direct closed-list arm**, which has
no per-intent schema block, and its own reading of an unmatched gold mention is stricter
(`slot_f1_exact_fn > 0`: a gold `(type, filler)` pair the row did not produce exactly). The 72.09
constant is therefore carried as an **owner-fixed external bar**, exactly as the rule states, and
the read **additionally recomputes the schema and legality judges on this arm's own rows under the
same definition** so the comparison can also be read like for like. Both are reported. Neither is
allowed to replace the other after the fact.

## 2. The arm: the comparator plus exactly one declared key

The probe is the sealed closed-list direct comparator's configuration with
`decoding_params.logprobs: true` and `top_logprobs: 5` added, and nothing else.

* The **baseline fragment is the comparator's own file**, reused — not a sibling, not a copy. The
  arm, policy, evidence source, instruction template and fill, packet promotion receipt and its
  sha256, representation and matcher ids and declared scorers are literally the same bytes.
* The **dataset fragment is the comparator's own**, `slurp-speech-native-dev1000`.
* The **model fragment** adds two `decoding_params` keys to the comparator's own model fragment and
  changes nothing else — not the lock key, the materialization root, the transport, the base URL,
  the timeout, the runtime receipt, any of the fifteen `server_args`, `temperature 0`,
  `seed 20260803`, `max_tokens 64`, `id_slot per-sample`, `prompt_order speech-query-prefix-v2`,
  `profile_slot_count 8`, the feature root, or either `server_env` entry.

**Measured, not asserted** (wire-check receipt `df2f9ca5…`, three halves, zero contacts and zero
sockets):

| half | what ran | result |
|---|---|---|
| config | real `core.config.compose` on both full cells | shared keys moved: `decoding_params` + the five experiment-identity keys two runs cannot share. `decoding_params` added exactly `{logprobs: true, top_logprobs: 5}`, removed nothing, changed nothing. `config_hash` 6be064ba → 15670eaa; `protocol_hash`, against a fixed split identity, 159dc0ea → bceed4f0 |
| payload | real `FlightRuntime.wire_check` on both four-row smokes: real fragments, adapter, samples, payload binding, hash-verified packets, real client/adapter stack; only gate and transport faked | all four rows, paired by sample id: the only field that moved is `decoding_params`, the only decoding change is the two added keys, the rendered instruction is identical (`4073f79e`), and the four packet sha256 are identical in both arms |
| body | the four committed transport/adapter test targets | 19 tests, all passing |

Two facts the payload half established the hard way and that any future comparison of two flights
must respect: comparing by dispatch **position** reports six spurious differences, because two runs
of the same cell dispatch the same rows in different orders — pair by sample id; and two payload
values are **run-local by construction**, `request_id` (the dispatch counter) and
`decoding_params.id_slot` (the slot the executor allocated in that run). The receipt names both and
reports a `protocol_payload_sha256` with exactly those stripped.

**The profile is `bounded-discovery-probe`, not `baseline-reproduction`, and the reason is
load-bearing.** These outputs are a NEW arm's outputs: greedy decoding is not bitwise reproducible
across batch compositions on llama-server, and asking for logprobs additionally disables backend
sampling for the slot (section 3). So **every relation this read measures is measured WITHIN this
arm** — its own official scores against its own confidences — and the read never pairs a row
against the sealed comparator's row for the same sample. There is no accuracy comparison between
the two arms anywhere in this probe.

## 3. What the pinned server actually does, with file:line

Build: `/home/chao/llama.cpp-featcache` at `04ccc72a2207347ca76161b93fd9d846dd0a8675`, the featcache
checkout the study's runtime receipt pins.

**3.1 The endpoint decides the field names.** The study talks to
`/v1/chat/completions` — `core/model/transport.py:517` builds exactly
`base_url.rstrip("/") + "/v1/chat/completions"` and `:886` posts to it. So the request keys are the
OpenAI-compatible **`logprobs` / `top_logprobs`**, and the response key is
**`choices[0].logprobs`**. `n_probs` and `completion_probabilities` are the **native `/completion`**
endpoint's spellings (`server-task.cpp:384`) and never appear on this study's wire.

**3.2 The translation.** `server-common.cpp:1523-1531`:

* `:1525` — `if (json_value(body, "logprobs", false))`: the field is read as a **boolean**.
* `:1529` — `llama_params["n_probs"] = json_value(body, "top_logprobs", 20);`. A true `logprobs`
  with no `top_logprobs` therefore means **k = 20**, the server's own default, not k = 1.
* `:1531` — a `top_logprobs` without `logprobs: true` throws
  `"top_logprobs requires logprobs to be set to true"`. The adapter now refuses the same pair
  before the call is metered.
* `:1527` — `logprobs` is refused with **tools + stream** together. This arm sends no `tools` and
  does not stream, so the clause is inert here; it would bind a native-tool-calling arm that wanted
  streaming logprobs.

**3.3 The alias cannot fire.** `server-schema.cpp:175-177` registers `n_probs` with
`add_alias("logprobs")`, and `server-schema.h:38` states the resolution rule: *"if 'name' is
present, use it, otherwise look for aliases"*. On the chat endpoint `n_probs` is always present by
the time the schema runs (`:1529` set it), so the boolean `logprobs` that the OAI layer's
copy-remaining loop also carries through is **never parsed as a number**. `n_probs` carries no
`set_hard_limits`, so the server imposes no ceiling of its own; the adapter's `[1, 20]` is this
study's rule, taken from the server's own default and OpenAI's contract.

**3.4 The response shape.** `server-task.cpp:456-460`: `choice["logprobs"] = {"content": [...]}`,
set **only** when `!stream && probs_output.size() > 0`. Each content entry
(`probs_vector_to_json`, `:306-326`) carries `id`, `token`, `bytes`, `logprob`, and
`top_logprobs`; each alternative (`to_json`, `:288-304`) carries `id`, `token`, `bytes`, `logprob`.
`logarithm` (`:328-331`) maps a zero probability to `std::numeric_limits<float>::lowest()` rather
than `-inf`, because nlohmann would serialize `-inf` as `null` — so a floor value in the data is a
zero probability, not a missing one, and the read must not treat it as absent.

**3.5 Generated tokens only.** `populate_token_probs` is called from the token-generation loop
(`server-context.cpp:3975-3977`) on the token just sampled, and its result is pushed onto
`slot.generated_token_probs` (`:430`). **The prompt's tokens never get probabilities on this
build**, and no request field asks for them. So "the logprob of the intent tokens" can only mean
generated intent tokens — which is what this arm's answer is — and a future prompt-side
confidence signal would need a server change, not a config key.

One trimming rule the read must know: on a stop-word stop, `send_final_response`
(`server-context.cpp:2340-2352`) drops the trailing tokens matching the stop word from
`probs_output`. The token stream can therefore be **shorter** than the sealed text's tokenization,
which is exactly why the read reconstructs the answer from the token stream itself and reports
every row where the reconstruction does not equal the sealed text rather than aligning blindly.

**3.6 The modality does not matter, so the packet route is fine.** The speech-feature packets are a
**prompt-construction** hook: `process_speech_feature_prompt` (`server-common.cpp:996-1066`),
called from `server-context.cpp:4269-4280`, splices packet chunks into the prompt before any
decoding. `populate_token_probs` reads only the target context's logits at the sampled index. The
two are on opposite sides of the prompt/generation boundary, so logprobs are **modality-agnostic**:
the packet route and the raw mmproj route behave identically. Nothing in this reading was verified
against a running server, which is why the four-row smoke exists (section 5).

**3.7 The cost, and why it is only measurable in flight.** `n_probs > 0` with
`post_sampling_probs` false sets `need_pre_sample_logits` (`server-context.cpp:1994`) which
**disables backend sampling for that slot** (`:2004`, `backend_sampling &= !need_pre_sample_logits`),
and every generated token then calls `get_token_probabilities` (`:2195`), which copies the full
logit vector, `partial_sort`s the top k, and applies a softmax over the whole vocabulary
(`server-common.cpp:1644-1690`). That is a per-token, full-vocabulary CPU cost **and** a change of
sampling path. Its size cannot be derived from source: it depends on vocabulary size, batch
composition and the concurrency of eight slots. **The added latency is a reported number of the
flight, never a precondition of it**, and the budget carries a margin for it (section 5).

The same fact is the second reason this arm is not a reproduction: a different sampling path is a
second reason its greedy answers need not equal the comparator's.

## 4. What is measured

All of it by `scripts/slurp_logprob_judge_read.py`, one registered read, over the arm's own trace,
its own sealed outputs and its own official per-sample scores.

**4.0 The labels**, from this arm's own `core.scoring_batch` per-sample entries:

* `intent_error` — `scenario_action_exact == 0`, the official intent column row by row, read
  through the locked `slurp-slu-official-projected-v2` scorer (the 2026-09-06 re-lock's rule,
  applied through a derived manifest over sealed bytes exactly as that verdict applied it, so the
  arm's `scorers` key stays the comparator's).
* `unmatched_gold` — `slot_f1_exact_fn > 0`.
* `slot_error` — `slot_f1_exact_fn > 0` or `slot_f1_exact_fp > 0` ("any slot error").

**4.1 The confidence statistics**, five, each oriented so that lower means less confident:

| statistic | definition |
|---|---|
| `min_token_logprob` | minimum logprob over the generated tokens (the primary; the operating point and the verdict use it) |
| `mean_token_logprob` | mean over the generated tokens |
| `intent_mean_token_logprob` | mean over the tokens overlapping the `scenario` and `action` VALUE spans |
| `intent_min_token_logprob` | minimum over the same tokens |
| `first_intent_token_margin` | top-1 minus top-2 logprob at the first token of the `scenario` value (needs k ≥ 2; `top_logprobs: 5` supplies it) |

The intent spans are located in the answer **reconstructed from the token stream**, never in the
sealed text, because only the reconstruction shares the stream's offsets; every row whose
reconstruction differs from its sealed text is listed in the receipt. A statistic no row carries
(for instance the margin, if a future arm asks for k = 1) is reported `UNAVAILABLE`, never dropped
silently.

**4.2 AUROC** of each statistic against `intent_error` and against `slot_error`, with a
**cluster bootstrap over speakers** — `analysis.paired.resampled_statistic`, which resamples whole
clusters, 10,000 replicates, seed 20260908, CI90. Ties are handled by mid-rank, because a
confidence flag has many of them; a constant statistic scores 0.5, not 1.0. Speakers are resolved
from the governed release's `metadata.json` through `data.slurp`'s own speaker index
(`data/slurp.py:399-428`, `recordings[...]["usrid"]`), and a row whose speaker cannot be resolved
**fails the read closed** rather than being dropped into a singleton cluster.

**4.3 The 86-flag operating point.** The flag is set at whatever threshold flags the schema judge's
86 rows. Ties at the boundary are **included** — a threshold cannot split identical evidence — so
the actual flagged count is reported, never the requested one. At that point the read reports
precision and recall of:

* the confidence flag alone;
* the **schema judge** recomputed on this arm (unparsed, or an entity type outside the 55-type
  vocabulary, or a repeated type);
* the **legality judge** recomputed on this arm (the `(scenario, action)` pair is not one of the 60
  legal TRAIN pairs, i.e. `slurp-legal-label-projection-v2` fires);
* the **union** confidence ∪ schema, and the union of all three.

Against all three targets: `intent_error`, `slot_error`, `unmatched_gold`.

**4.4 The precision-recall curve** of a confidence-gated re-ask: one point per distinct threshold,
rows flagged against errors caught, for each target. This is the shape the Reviewer would actually
be tuned on, and it is reported whole rather than at one point.

**4.5 The verdict**, applied mechanically by `admission_verdict`, with the precision arm's CI90
from a cluster bootstrap whose flag budget is rescaled to each replicate's own size.

**4.6 Core-pressure covariates**, per the 2026-09-08 template addition: contacts per row (1),
prompt and completion tokens per row, wall-clock and GPU-hours against the comparator's own
`~0.105 GPU-h / 225.5 s` for the same 1,000 contacts, and the **added latency of `n_probs > 0`**,
which is the one number in this note nobody can predict.

## 5. Sequence, budget and geometry

| | |
|---|---|
| geometry | the comparator's: featcache packets, mmproj-free, `-c 65536 -np 8`, build `04ccc72a` |
| population | DEV-1000, identity `8580d199…3c84`, split role `dev` |
| contacts | 4 (smoke) + 1,000 (cell) |
| planned model calls | 12 (smoke) + 1,050 (cell), run-cumulative across every attempt of each run id |
| speech audio | 14.28 s (smoke) + 2,884.79 s (cell); metered ceilings 60 and 3,000 |
| GPU hours | expected ≈ **0.12** for the cell (the comparator spent ~0.105 on the same 1,000 contacts, `docs/readiness/2026-09-05-slurp-closed-list-direct-baseline-v1-verdict.md` section 8); **planned 0.5**, the margin covering the per-token full-vocabulary sort of section 3.7 |
| paid API spend | 0 |

**Order.** (1) The wire check, already run and committed. (2) The **four-row smoke**, which proves
the one thing a contact-free check cannot: that the server actually returns a
`choices[0].logprobs` object **on the packet route**, with five alternatives per generated token,
and that four `MODEL_LOGPROBS` records land with recomputable `logprobs_sha256` and
`requested_top_logprobs: 5`. The source reading says it must (3.6), but the 2026-08-13 policy note
already records llama-server sometimes omitting usable logprobs, and the transport treats an absent
object as *unavailable* rather than crashing — so it is checked on four rows before 1,000 are
spent. **If the smoke returns no object, the cell does not fly** and the note is closed with that
finding. (3) The cell, one attempt, one seal, one registered read. (4) The read.

**One touch.** No knob change and no re-fly on the strength of the number. At most one recovery
re-registration, per the standing rule; a second failure stops the flight.

## 6. The read script, written and tested before the flight

`scripts/slurp_logprob_judge_read.py`, unit-tested on **synthetic traces** in
`tests/unit/test_slurp_logprob_judge_read.py` (40 tests): the token-stream alignment (the intent
statistics point at the scenario/action value characters and no others), the margin (top-1 minus
top-2, and `None` when k < 2), AUROC (perfect, inverted, all-ties, one tie straddling the boundary
at 0.875, an empty class), the flag budget (the least-confident rows, boundary ties included, a
budget above the population, a refused non-positive budget), the bootstrap's resampling
multiplicity (a row drawn twice counts twice, which a set-based statistic would silently lose and
which would narrow the CI the rule's second arm turns on), precision and recall denominators, the
curve's monotone recall, both judges on clean/unparsed/out-of-vocabulary/repeated-type/illegal-pair
rows, the three-way join and its four refusals, the union's monotonicity, and the admission rule on
eight cases including both boundaries.

The point of testing it now is not tidiness. An analysis script written after the numbers exist is
a script whose thresholds were chosen by the numbers.

Its five inputs are files, so the read carries no dataset access of its own: the trace, the sealed
outputs, the per-sample official scores, `{sample_id: speaker}`, and
`{entity_types, legal_pairs}` mined from **TRAIN alone**. The flight read produces the last two and
records their provenance and sha256.

## 7. The noise floor — priced, NOT preregistered

The statistic's own noise floor is only measurable by flying the probe **twice** on the same roster
and asking whether confidence separates the rows that flip from the rows that do not. SLURP's
greedy null is a **28 % flip rate on identical prompts** (the agent-system note, section 4), so the
question is real: a confidence signal that merely tracks the sampler's own instability is not a
Reviewer signal.

**Price:** a second 1,000-contact attempt under its own run id, ≈ 0.12 GPU-h, ≈ 2,885 audio
seconds, one more exposure row. It would add: AUROC of each statistic for *"this row flips"*, and
the flip rate within the flagged 86 against the flip rate outside it.

**It is an option, offered and not taken.** It is not registered here, it is not authorized by this
note, and the first flight does not reserve budget for it. If the primary result is ADMITTED, the
noise floor becomes the first thing worth buying, because an admitted flag whose AUROC for *flips*
is as high as its AUROC for *errors* is measuring the sampler, not the speech.

## 8. What is already known, and it is not encouraging

The study has measured a logprob-based flag once before, on Earnings-21 ASR spans:
`docs/readiness/2026-08-14-p1-ceiling-verdict.md`, finding 1 — **"Flag targeting misses entities
17/17. Every logprob-flagged span on the clean samples is function-word/boundary text ('with a',
'for the', 'increase by', 'final regulatory'); zero overlap with the real entity errors the oracle
candidates answer."** That result is why `core.flag_sources` exists at all: the roster-band flag
source was built as the config-selectable alternative, and it was offline-validated at proper-name
P@1 = 0.252 against the logprob flags' 0/17.

Two things follow, and both are stated before the flight rather than after it.

1. **The prior is against admission.** A statistic that found function words on Earnings spans may
   well find JSON punctuation on SLURP rows. The probe is designed so that this outcome is a clean,
   reportable NOT ADMITTED rather than an ambiguity: the intent-span statistics exist precisely so
   that "the confidence is low on the braces and quotes" and "the confidence is low on the label"
   are separated by construction.
2. **The two are not the same measurement, and the difference is the reason to spend the contacts.**
   The 2026-08-14 result was a **span-targeting** claim on a long free-text transcript, scored by
   whether the flagged span overlapped an entity error. This is a **row-level** claim on a short
   structured answer, scored by whether the flagged row carries an error at all. A flag can be
   useless at pointing at the wrong word and still be a good triage signal for which of 1,000 rows
   to ask again — that is exactly the shape the re-ask module needs, and it has never been measured.

## 9. The exposure ledger row

Registered **before** the first contact, one row per run id. Text for the cell (the smoke gets its
own row, naming the smoke's own run id, its 4 contacts, its 60-second ceiling and its 0.3 GPU-h,
and authorizing no metric and no verdict):

> `| 2026-09-08 | SAEA-SLURP-DEV1000-CLOSED-LIST-LOGPROB-V1 | bounded-discovery-probe | THE FLIGHT
> OF THE SLURP LOGPROB-AS-JUDGE PROBE — cell `closed-list-logprob` of
> `configs/experiment/slurp-dev1000-closed-list-logprob-v1.json`, preregistered in
> `docs/readiness/2026-09-08-slurp-logprob-judge-probe-v1-preregistration.md` on the owner
> directive of 2026-09-08 ("analyse logprobs first; the proposal needs experimental evidence").
> ONE FACTOR MOVES, and it is a DECLARED DECODING PARAMETER: `decoding_params.logprobs: true` and
> `top_logprobs: 5`, so the frozen core's own per-token distribution is recorded beside every
> answer in a new `MODEL_LOGPROBS` trace record instead of being discarded. Everything else —
> population, split identity, dataset fragment, baseline fragment (the comparator's OWN file,
> reused byte for byte), arm, policy, evidence source, instruction, packets, promotion receipt,
> build, serving geometry, server env, temperature, seed, max_tokens and slot policy — is the
> sealed comparator `SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1`'s. The contact-free wire check
> `docs/checks/speech-aware-evidence-acquisition/2026-09-08-slurp-logprob-judge-probe-wire-check/`
> (receipt sha256 `df2f9ca5…`) proves the composed configs and the bound payloads differ by exactly
> those two keys. What it measures: whether row-level decode confidence predicts this arm's OWN
> intent and slot errors well enough to be admitted as a Reviewer signal, against the schema
> judge's 72.09 % precision at 86 flags. What it does NOT do, stated before any number exists: it
> is NOT a reproduction of the comparator and NOT a comparator itself — greedy is not bitwise
> reproducible across batch compositions and `n_probs > 0` additionally disables backend sampling
> for the slot, so these are a new arm's answers and every relation is measured WITHIN the arm.
> It makes no accuracy, superiority, generalization or Stage-3 claim, and admits no mechanism.
> One contact per sample, 1,000 rows, one pass, one seal, one registered read. | Qwen3-Omni-30B-A3B-Instruct
> GGUF Q4_K_M, llama.cpp-featcache 04ccc72a, mmproj-free packets | SLURP devel, DEV-1000 | dev |
> 8580d199…3c84 | 1,000 devel rows already contacted by the sealed comparator; no new speech
> identity opens | 1,000 of 1,050 | 2,884.79 of 3,000 | ≈0.12 of 0.5 | inherits the DEV-1000
> exposure of `SAEA-DEV1000-BASELINE-LOCK` and `SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1` | run
> manifest, outputs, trace, `read.json` | 0 tool, 0 embedding, 0 paid spend |`

## 10. The Earnings-21 follow-up — named, NOT registered

If the flag is admitted on SLURP, the obvious next carrier is Earnings-21, where the Reviewer's
selective-re-listen loop is the cell after KC-E1f and where a flag has a span to point at rather
than only a row to triage. It would measure two things SLURP cannot:

* **window-level confidence** — does a 90-second window's own decode confidence predict its WER, its
  deletion count, or its boundary-bleed share;
* **PERSON-span-level confidence** — does the confidence over the tokens of a predicted PERSON span
  predict whether that span is an entity error, which is the 2026-08-14 measurement redone with the
  distribution actually recorded instead of reconstructed.

Approximate price: 1,593 windows on the buf90 roster, **≈ 1 GPU-h**, one exposure row.

**It is named here so the sequence is visible, and it is not registered.** It needs its own
preregistration, its own owner decision, and — per the standing rule of one experiment in flight —
the SLURP probe to have landed first.

## 11. What this probe cannot conclude

* Nothing about the **test** split, which is never named, loaded, hashed or scored.
* Nothing about SLURP accuracy: the arm's official numbers are reported as this arm's own, never as
  a comparator and never against the locked 73.10 / 35.80.
* Nothing about whether a **re-ask actually helps**. MF-9's rung 6 is a ceiling that assumes every
  re-asked row then answers perfectly; this probe measures only which rows a confidence flag would
  select, not what a second contact would do with them. Admission here authorizes a re-ask cell to
  be *preregistered*, not flown.
* Nothing about the **core-as-critic** reading of the boundary, which is a separate question still
  awaiting owner confirmation.
* Nothing about **generalization to another carrier or another core**. Section 10 is a proposal,
  not an inference.
