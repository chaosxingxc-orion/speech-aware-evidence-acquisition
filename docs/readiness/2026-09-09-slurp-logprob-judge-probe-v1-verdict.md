# Verdict — the SLURP logprob-as-judge probe: **NOT ADMITTED**

Run `SAEA-SLURP-DEV1000-CLOSED-LIST-LOGPROB-V1`, attempt `attempt-20260909T052142Z-07ca9c`,
`COMPLETED` on study commit `7489a15d`, **1,000 of 1,000 rows**, one attempt, none aborted, **no
recovery re-registration used**, `study_repo_dirt` empty. The cell of
`docs/readiness/2026-09-08-slurp-logprob-judge-probe-v1-preregistration.md`, flown on the owner
directive of 2026-09-08 (*analyse logprobs first; the proposal needs experimental evidence*) and
registered in its own exposure row before the first contact.

Receipt: `docs/checks/speech-aware-evidence-acquisition/2026-09-09-slurp-logprob-judge-probe-v1/`.

---

## 0. The answer

**The frozen core's decode confidence does predict its own intent errors — but not the statistic
the rule turns on. The preregistered primary, the minimum logprob over the whole answer, reaches
AUROC 0.6935 [0.6660, 0.7202] and 51.16 % precision at 86 flags [42.53, 59.09] against a 72.09 %
bar. Both arms of the admission rule fail, and the verdict is NOT ADMITTED. The re-ask module falls
back to the deterministic judges.**

| | value |
|---|---:|
| rule arm A — `min_token_logprob` AUROC for intent error | **0.6935** [0.6660, 0.7202] |
| the bar | ≥ 0.75 point, CI90 lower bound ≥ 0.70 |
| clears arm A | **no**, on both halves |
| rule arm B — precision at 86 flags, intent error | **51.16 %** [42.53, 59.09] |
| the bar | > 72.09 %, CI90 lower bound strictly above |
| clears arm B | **no** — 20.93 pp below, whole interval under the bar |
| **verdict** | **NOT ADMITTED** |
| the cost the flight measured for the first time | **+5.30 % per-request latency, +8.33 % wall, +8.35 % GPU-h** |

**And the reason it fails is measurable, not mysterious.** The intent-span statistics, preregistered
in the same table and computed by the same read, reach **AUROC 0.8497 [0.8262, 0.8729]**. The
signal is in the answer; the primary statistic is not looking at it.

**Three findings carry, and the second is the one that costs something.**

1. **The 2026-08-14 prior held, in structured form.** The P1 ceiling verdict found every
   logprob-flagged Earnings span landing on function words, 0 of 17 real entity errors. Here
   **491 of 1,000 rows put their least-confident token on JSON punctuation** — 57.1 % of correct
   rows against 26.8 % of intent-error rows — and the single most common minimum token is `" []"`,
   the empty entity list, on 208 rows. The whole-answer minimum spends its ranking budget on the
   model's hesitation about *how many entities to emit*, which is a formatting decision.
2. **A confidence statistic predicts the thing its tokens are part of, and nothing else.** The
   whole-answer minimum is the WEAKEST of the five on intent (0.6935) and the STRONGEST on slots
   (0.6534); the intent-span statistics are the exact mirror, 0.8497 on intent and 0.4795 — chance
   — on slots. This is not a nuance in the table; it is the table's shape.
3. **The decoding parameter is not free, and now there is a number.** `n_probs > 0` disables
   backend sampling for the slot and forces a per-token full-vocabulary copy, partial sort and
   softmax. Nobody could derive its size from source. Measured against the greedy replicate null
   — the same 1,000 requests, same geometry, no parameter — it is **+0.0898 s per request (+5.30 %)**,
   248.47 s against 229.38 s of wall, 0.0690 against 0.0637 GPU-h, and 241.5 against 261.6 rows per
   minute. The sealed trace grew from ~10 MB to **23.3 MB**.

---

## 1. The hard precondition, met before 1,000 rows were spent

The preregistration made the four-row smoke a gate, not a formality: *if the smoke returns no
object, the cell does not fly.* `SAEA-SLURP-DEV1000-CLOSED-LIST-LOGPROB-SMOKE-4-V1`, attempt
`attempt-20260909T051251Z-1f2c58`, registered and committed in its own exposure row first.

| clause, fixed in the experiment fragment before the contact | result |
|---|---:|
| all four rows return a `choices[0].logprobs` object **on the speech-feature packet route** | **4 of 4** |
| every generated token carries exactly five `top_logprobs` alternatives | **4 of 4 rows, 162 of 162 tokens** |
| the first alternative is the sampled token | **every token** |
| four `MODEL_LOGPROBS` records land, `logprobs_sha256` recomputes, `requested_top_logprobs` is 5 | **4 of 4** |
| the answer reconstructed from the token stream equals the sealed text | **4 of 4** |

**Section 3.6 of the preregistration was right, and it was right for the stated reason.** Logprobs
are computed in the token-generation loop from the target context's logits, downstream of every
prompt-construction path; the packet splice happens on the other side of the prompt/generation
boundary. The packet route and the raw mmproj route behave identically. That reading is now
measured rather than argued.

---

## 2. Identity: exactly the two declared keys, and nothing else

| | |
|---|---|
| config hash | `15670eaafa88c16b47cb33487d343b21394986017911eb62a1ead2727711e587` |
| protocol hash | `bf6e602d3b6e5609e28d27b26a0c2065be61b4f07c46bdae3a3e30a718b83c68` |
| split identity | `8580d199bffc95a51ad6d8c5b2a2e9e39faa2c551dd095f8afcd78174a1e3c84` — **the comparator's own** |
| rendered instruction | `4073f79ef25c4796…0d37db`, 7,583 chars — **the comparator's own** |
| runtime view | `e148dbbc…0e87` — **the comparator's own** |

**The wire check called the config hash in advance.** Its contact-free receipt of 2026-09-08
predicted `6be064ba → 15670eaa`, and the flight's own preflight derived
`15670eaa…711e587`. The protocol hash differs from that receipt's `bceed4f0` for the reason the
receipt itself names: it computed against a *fixed* split identity, and this cell carries the real
DEV-1000 one.

**And the request side did not move.** `prompt_tokens_total` is **2,190,161** — identical to the
digit to both the sealed comparator's and the greedy replicate null's, on the same 2,884.7936875
metered speech seconds. Completion tokens 26,530, against the comparator's 26,495 and the null's
26,570; that spread is the null's own measured territory. The parameter bought a trace record, not
a different prompt.

---

## 3. What the read measured

`scripts/slurp_logprob_judge_read.py`, one registered read, written and unit-tested on synthetic
traces (40 tests) **before** the flight. Zero contacts. Its five inputs are files:

| input | provenance | sha256 |
|---|---|---|
| trace | the arm's own sealed `*.trace.jsonl` | in `verdict/read-inputs-provenance.json` |
| outputs | the arm's own sealed `*.outputs.jsonl` | `44a9e5b6…9921` |
| per-sample official scores | this arm's own, `slurp-slu-official-projected-v2` | `936e0512…8cf6` |
| clusters | `{sample_id: speaker}`, `data.slurp`'s own speaker index over the governed `metadata.json` | `9d6ec916…f9c1` |
| label inventory | 55 entity types and 60 legal pairs, **TRAIN alone** | `faedea31…bc8d` |

**1,000 of 1,000 speakers resolved into 124 clusters**; the read fails closed on an unresolved
speaker rather than inventing a singleton, and none had to be. **Zero token-stream mismatches** —
every row's reconstruction from its own token stream equals its sealed text, so every span
statistic is aligned to the string it claims to be aligned to.

### 3.1 AUROC — every preregistered statistic, both targets

Speaker-cluster bootstrap, 10,000 replicates, seed 20260908, CI90, mid-rank ties. Full table:
`verdict/auroc-table.md`.

| statistic | intent error | CI90 | any-slot error | CI90 |
|---|---:|---|---:|---|
| `min_token_logprob` **(PRIMARY)** | **0.6935** | [0.6660, 0.7202] | 0.6534 | [0.6262, 0.6804] |
| `mean_token_logprob` | 0.7364 | [0.7104, 0.7629] | 0.6391 | [0.6118, 0.6659] |
| `intent_mean_token_logprob` | **0.8497** | [0.8262, 0.8729] | 0.4795 | [0.4497, 0.5097] |
| `intent_min_token_logprob` | 0.8446 | [0.8211, 0.8683] | 0.4739 | [0.4442, 0.5041] |
| `first_intent_token_margin` | 0.7869 | [0.7592, 0.8131] | 0.4768 | [0.4462, 0.5089] |

### 3.2 The 86-flag operating point

The flag landed on exactly 86 rows at `min_token_logprob <= -0.7921727`, ties at the boundary
included. The schema and legality judges are recomputed on this arm's own rows under this probe's
own stricter definition. Full table, all three targets: `verdict/operating-point-table.md`.

| judge, against **intent error** | flagged | caught | precision % | recall % |
|---|---:|---:|---:|---:|
| confidence flag (the primary) | 86 | 44 | **51.16** | 16.60 |
| schema judge, recomputed here | 13 | 4 | 30.77 | 1.51 |
| legality judge, recomputed here | 42 | 28 | 66.67 | 10.57 |
| union: confidence + schema | 97 | 46 | 47.42 | 17.36 |
| union: all three | 123 | 62 | 50.41 | 23.40 |

Against **any-slot error** the same 86 rows reach 80.23 % precision, and against **unmatched gold**
65.12 % — but the rule's arm B is about intent error, fixed in advance, and that is the cell it is
read in.

**One union the registered read does not compute, measured here rather than inferred**
(`verdict/deterministic-pair.json`, zero contacts): the two deterministic judges ON THEIR OWN flag
**52 rows at 55.77 % precision and 10.94 % recall**. Adding the confidence flag takes that to 123
rows at 50.41 % and 23.40 % — **precision down 5.36 pp for recall up 12.45 pp**. So the flag does
buy reach on top of the free judges; what it does not do is buy it at their precision, and the
rule's bar was a precision bar. The same addition on **any-slot error** goes the other way, 67.31 %
→ 75.61 %, which is the section 3.1 mirror showing up again: the whole-answer minimum is a slot
signal being asked an intent question.

**The honesty clause fired exactly as written.** 72.09 % and 86 are KC-S1b's numbers on the
two-stage slot arm. On THIS arm, under the same definition, **the schema judge flags 13 rows at
30.77 % precision**, not 86 at 72.09 %. Both readings are reported and neither replaces the other:
the flag misses the owner-fixed external bar by 20.93 pp, and it also loses to this arm's own
legality judge, which flags 42 rows at 66.67 % for free.

### 3.3 The precision-recall curves

1,000 points per target, one per distinct threshold, in `verdict/read.json`. They are the shape a
Reviewer would actually be tuned on and they are reported whole rather than at one point.

---

## 4. Why the primary fails while the signal exists

`verdict/per-scenario-table.md` carries the measurement.

| region carrying the row's LOWEST-logprob token | all rows | scorer says CORRECT | scorer says INTENT ERROR |
|---|---:|---:|---:|
| JSON punctuation | **491** | 420 | 71 |
| `scenario` value | 120 | 56 | 64 |
| `action` value | 96 | 36 | 60 |
| `filler` value | 211 | 159 | 52 |
| other | 82 | 64 | 18 |

Top minimum tokens: `" []"` (208), `"{\""` (164), `" [{\""` (75). Then the first real label token,
`"query"`, at 29.

**On a correct row the model's least confident moment is usually a brace.** On an error row it is
usually the label. A statistic that takes the minimum over the whole answer therefore ranks
formatting hesitation against semantic hesitation and loses; a statistic restricted to the label
tokens does not. The preregistration built that separation in on purpose (section 8, finding 1's
consequence), and it is the reason this is a clean NOT ADMITTED rather than an ambiguity.

Per scenario (all 18, `verdict/per-scenario-table.md`), the primary spans 0.5023 (`general`, which
also carries the largest error mass at 37 of 61) to 0.9866 (`weather`). **It is blind exactly where
the errors are**: `general` 0.50, `transport` 0.53, `cooking` 0.59, `alarm` 0.60. Read with the
null replicate's warning attached — that null moved intent by −5.13 to +5.41 pp across these same
18 scenarios with nothing changed, so no per-stratum reading here is admissible without its own
replicate.

---

## 5. The cost of the decoding parameter, measured for the first time

The preregistration said this number could not be derived from source and would be a reported
number of the flight, never a precondition of it. It is:

| | logprob arm | greedy replicate null | delta |
|---|---:|---:|---:|
| contacts | 1,000 | 1,000 | — |
| wall (contact window) | **248.47 s** | 229.38 s | **+8.33 %** |
| GPU-hours | **0.0690** | 0.0637 | **+8.35 %** |
| mean per-request latency | **1.7848 s** | 1.6950 s | **+0.0898 s / +5.30 %** |
| throughput | **241.5 rows/min** | 261.6 rows/min | **−20.1 rows/min** |
| sealed trace | **23.3 MB** | ~10 MB | **+13 MB** |

The greedy replicate null is the honest reference: it flew the same 1,000 requests on the same
geometry with no parameter added, and its own verdict fixed **~5 %** as the floor below which a
SLURP wall-clock or GPU-hour comparison means nothing (byte-identical work spread 1.7 %). **The
measured cost is above that floor**, so it is a real cost and not scheduling noise — but it is
about a twelfth of the throughput, not a doubling. Against the sealed comparator's 225.5 s the
wall delta reads +10.19 %; the null is the number to quote.

Serving: **attached, never started, never stopped.** `session_reused` true,
`session_source` `attached-serving-session`, `stop_serving` null. Monitor over the attempt's own
contact window (22 samples at 10 s): wall 235.01 s, active 235.01 s, **parked fraction 0.0**, 168
requests (a 10 s-interval lower bound on the charged 1,000), mean **82.85 W**, peak 85.79 W, mean
utilization **71.91 %**, host free memory bottoming at **23.90 GB** against the 12 GB floor, VM
working set peaking at 24.24 GB.

Spend: **1,000 model calls of 1,050 registered**; **2,884.7937 of 3,000** metered speech seconds;
**0.0690 of 0.5** GPU-hours; paid API spend **0**. The smoke spent 4 of its own 12. Preprocess
promoted 1,000 packets in 10.25 s at 97.6 packets/s on 8 workers, every packet a cache hit from the
comparator's own base root.

---

## 6. This arm's own official numbers, which are not a comparator

Scored **once** over its one complete 1,000-row manifest through `core.scoring_batch`,
`include_per_sample=True`, one job, never sharded, verified. The paper-facing scorer is
`slurp-slu-official-projected-v2` with `slurp-slu-f1-normalized-v1` beside it; neither is declared
by the sealed manifest (`scorers` is a baseline-fragment key that enters `config_hash`), so one
derived manifest was written beside the sealed one differing from it only in the `scorers` list.
The sealed manifest was not touched and its sha256 is in the receipt.

| | this arm |
|---|---:|
| scenario | 82.90 |
| action | 75.00 |
| intent | 73.50 |
| entities strict | 23.32 |
| SLU-F1 | 36.67 |
| intent-error rows | 265 of 1,000 |

**These are this arm's OWN numbers and they are used for one thing only: as the labels the
confidences are read against.** They are not a comparator, they are not read against the locked
73.10 / 35.80, and this probe makes no SLURP accuracy claim. Greedy is not bitwise reproducible
across batch compositions and `n_probs > 0` additionally changes the sampling path, so these are a
new arm's answers by construction — which is precisely why every relation above is measured WITHIN
the arm.

---

## 7. What follows, and what does not

**The consequence fires as registered.** The confidence flag is NOT ADMITTED as a Reviewer signal
on this carrier; it never enters a default plan; the re-ask module falls back to the deterministic
judges — on this arm, the legality judge, which reaches 66.67 % precision on 42 rows at zero cost
and zero latency. The harness-admission receipt carries the row as `HARMFUL` for `replay-logprob-flag-v1`
on `slurp`, which is the status this table gives a module whose gate failed and which therefore
never enters a plan; the entry states plainly that the failure is of the probe's own admission bar
and not a measured harm to any metric, because this module never changed an answer.

**What this verdict does NOT do.** It says nothing about the `test` split, which is never named,
loaded, hashed or scored. It makes no SLURP accuracy, superiority, generalization or Stage-3 claim.
It says nothing about whether a re-ask helps — MF-9's rung 6 is a ceiling that assumes every
re-asked row then answers perfectly, and this probe measured only which rows a flag would select.
It does not buy the section 7 noise floor, which stays priced and unregistered. It does not
authorize the section 10 Earnings-21 follow-up, which needs its own preregistration and its own
owner decision.

**And one thing it deliberately does not do.** The intent-span statistics clear arm A's bar. They
are **not** the primary, they were not the primary before the numbers existed, and swapping them in
now is exactly the move the rule was written to forbid. `verdict/result-summary.json` records their
86-flag operating points under a field named `successor_diagnostic_NOT_PREREGISTERED`, labelled as
outside the verdict, so a successor preregistration can name its primary in advance **with a price
already attached**: 75.58 % precision at 86 flags for `intent_mean_token_logprob`, and — a
coincidence worth naming out loud rather than quoting — **exactly 72.093 % for
`intent_min_token_logprob`**, which is the 72.09 bar to three decimals and would be the most
seductive number in this note to report as a pass. It is not a pass. It is a post-hoc statistic on
a razor's edge, and the rule's whole purpose was to make that unquotable.

**One prediction of the preregistration held and one failed.** Section 8 predicted the prior was
against admission, and it was. It also predicted that a flag useless at *pointing at the wrong
word* could still be a good *row-level triage* signal — that is the claim this cell was bought to
test, and at the primary statistic it is **false**: 51.16 % precision is worse than a free judge.
The row-level reframing did not rescue the statistic; restricting it to the label tokens did.
