# LP-2 — the label-token logprob judge — preregistration (2026-09-09)

Confirmation cell `SAEA-SLURP-DEV1000-CLOSED-LIST-LOGPROB-REPLICATE-V1`, profile
`bounded-discovery-probe`, with the eight-row smoke
`SAEA-SLURP-DEV1000-CLOSED-LIST-LOGPROB-REPLICATE-SMOKE-8-V1`.
Fragments: `configs/experiment/slurp-dev1000-closed-list-logprob-replicate-v1.json` and
`configs/experiment/slurp-dev1000-closed-list-logprob-replicate-smoke8-v1.json`, both reusing the
predecessor's own `configs/baseline/slurp-direct-closed-list.json`,
`configs/model/q4km-mmproj-free-speech-native-np8-base-speech-query-prefix-max64-logprobs5.json`
and `configs/dataset/slurp-speech-native-dev1000.json`.
Judge: `slurp-intent-token-logprob-flag-v1`, `core.judges.SlurpIntentTokenLogprobJudge` v1.0.0.
Design read: `docs/checks/speech-aware-evidence-acquisition/2026-09-09-lp2-label-token-logprob-design/`
(exposure row `SAEA-SLURP-MF-LP2-DESIGN-V1`, zero contacts).
Wire check: `scripts/slurp_label_token_logprob_wire_check.py`, receipt
`docs/checks/speech-aware-evidence-acquisition/2026-09-09-slurp-label-token-logprob-replicate-wire-check/`.

**Nothing in this note has been flown.** The cell is priced, wired and preregistered; it is not
authorized. Every threshold in it is fixed here, and the one thing that is *not* fixed here — where
those thresholds came from — is the first section, because it is the reason the note exists.

---

## 0. The honesty constraint, stated before anything else

The 2026-09-09 logprob-as-judge probe came back **NOT ADMITTED**
(`docs/readiness/2026-09-09-slurp-logprob-judge-probe-v1-verdict.md`). Its preregistered primary,
the minimum logprob over the whole answer, reached **AUROC 0.6935** [0.6660, 0.7202] and **51.16 %
precision at 86 flags** against a 72.09 % bar. The reason was measured, not guessed: **491 of that
arm's 1,000 rows put their least-confident token on JSON punctuation**, the single most common
minimum token being `" []"` — the empty entity list — on 208 rows. The statistic spent its ranking
budget on the model's hesitation about *how many entities to emit*, which is a formatting decision.

The same read computed intent-span statistics as diagnostics. They reached **AUROC 0.8497** and
**75.58 % precision at 86 flags**. That verdict recorded them under a field named
`successor_diagnostic_NOT_PREREGISTERED` and wrote, in full:

> They are **not** the primary, they were not the primary before the numbers existed, and swapping
> them in now is exactly the move the rule was written to forbid.

**This note does not swap them in. It buys a second observation.** The statistic and the threshold
below were chosen after the predecessor's data existed, so they are legitimate as a DESIGN and
illegitimate as a RESULT. The rule fixed in section 4 is therefore read on **a fresh replicate of
the same cell**, on rows the threshold was not fitted to, under a judge frozen in code and in
config before the first contact.

One consequence follows and is stated here rather than discovered later: **the predecessor's own
1,000 rows can never again decide this question.** They designed the rule. They are reported in
section 3 as a design read, labelled on every line, and they are not evidence for admission.

---

## 1. What the judge is

`core.judges.SlurpIntentTokenLogprobJudge`, registered through the `JUDGES` protocol in
`core/policies.py` like every other judge, `criticism_only=True`, checked at the registry door.

It reconstructs the answer from the row's own generated token stream, locates the `scenario` and
`action` JSON string **values in that reconstruction, by span** — never by gold, never by the
sealed text — and takes a mean or a minimum over exactly the tokens overlapping them. A brace, a
quote and an empty entity list cannot enter the statistic at all. A unit test drives the
punctuation to −9.0, far below either floor, and the row is still not flagged; that test is the
predecessor's failure mode made unreachable by construction.

**Criticism only, one degree stricter than the type demands.** The flag names the row and the field
whose label token is least confident — `intent.scenario` or `intent.action` — and never a
replacement label, never a nearest legal pair, and never one of the `top_logprobs` alternatives,
which are precisely what a repair would substitute. A test renders the whole verdict and asserts
the row's own label text and every alternative are absent from it. The score is `exp(statistic)`:
the geometric-mean probability of the label tokens for the mean, the least confident label token's
probability for the minimum — a real quantity in `[0, 1]`, not a calibration this study has not
earned.

Three refusals, all loud: a missing `logprobs` in state and material; a malformed record (no
non-empty `content` list, a non-numeric logprob); a token stream that is **not a prefix of the
draft**, because a confidence statistic aligned to a different string is not a measurement of that
draft. A *proper* prefix is admitted and named: `send_final_response` drops trailing stop-word
tokens from `probs_output` on this build (`server-context.cpp:2340-2352`), and the label spans sit
before any such trim. The predecessor measured zero of either case on 1,000 rows.

### 1.1 What the judge is NOT, today

`rails.phase_review.default_state_for_review` derives a judge's per-row state from the
`AgentRuntimeContext` alone, and **it does not carry the row's logprobs**. There is therefore no
in-flight form of this judge: it cannot be declared in a `phase_review` block and run inside a
loop without a `state_for_review` extension that does not exist. This cell does not buy that
extension and does not need it. The judge is driven **offline**, over the fresh pass's own sealed
`MODEL_LOGPROBS` records, after the flight lands. Section 6 records what that costs at admission
time.

---

## 2. The frozen threshold, and the flag budget it comes from

`core.judges.SLURP_INTENT_LOGPROB_FLOORS`, frozen in code and mirrored into the confirmation
fragment's `frozen_judge` block:

| statistic | frozen floor | what it is |
|---|---:|---|
| `intent_mean_token_logprob` — **THE CHOSEN PRIMARY** | **−0.2675283079346116** | the value that flags exactly **86** of the predecessor arm's 1,000 rows |
| `intent_min_token_logprob` — reported, not the primary | −0.5693119168281555 | the same, for the minimum |

A row is flagged when its statistic is **at or below** the floor. Boundary ties are **included**,
because a threshold cannot split identical evidence — the same rule the predecessor's own flag
budget used.

**Why 86.** It is the predecessor probe's own flag budget, carried over unchanged, so the successor
is read at the operating point the failed rule was read at rather than at a budget chosen to
flatter it.

**Why the mean and not the minimum.** Named here, before the contact, with its price attached: on
the design read the mean reaches 75.58 % precision against the minimum's 72.09 % and AUROC 0.8497
against 0.8446 — and, unlike the minimum, it does not land on the predecessor bar's own value to
three decimals. The verdict called 72.093 % "the most seductive number in this note"; a successor
whose primary sits exactly there would inherit the seduction. The minimum is computed and reported
on the fresh pass beside the mean, and it decides nothing.

**The threshold is a NUMBER, not a budget.** On the fresh pass the frozen floor is applied as it
stands; the number of rows it flags is whatever that pass's own distribution gives, and it is
reported, never renormalized to 86. Re-fitting the threshold to the fresh pass would reproduce the
exact defect this note exists to avoid.

---

## 3. The design read — every number here is unquotable as a result

`docs/checks/speech-aware-evidence-acquisition/2026-09-09-lp2-label-token-logprob-design/`, zero
contacts, over the predecessor's own 1,000 sealed rows, 265 of which carry an intent error, in 124
speaker clusters; 10,000 replicates, seed 20260909, CI90.

| flag, against intent error | flagged | caught | precision % | CI90 | recall % |
|---|---:|---:|---:|---|---:|
| `intent_mean_token_logprob` at −0.26753 | 86 | 65 | **75.58** | [69.23, 83.53] | 24.53 |
| `intent_min_token_logprob` at −0.56931 | 86 | 62 | 72.09 | [62.50, 80.20] | 23.40 |
| legality judge, free, recomputed on this arm | 42 | 28 | **66.67** | [54.55, 77.78] | 10.57 |
| union: mean-statistic flag ∪ legality judge | 111 | 80 | 72.07 | [65.93, 78.26] | 30.19 |
| the predecessor's whole-answer minimum, 86 flags | 86 | 44 | 51.16 | — | 16.60 |

AUROC for intent error: `intent_mean_token_logprob` **0.8497** [0.8261, 0.8724];
`intent_min_token_logprob` 0.8446 [0.8210, 0.8676].

**The union is worth reading carefully, because it is not free.** Adding the legality judge takes
the flag set from 86 rows to 111 and recall from 24.53 % to 30.19 %, at a cost of 3.51 pp of
precision. The two overlap on only **17** rows: the confidence flag reaches 69 rows the legality
judge does not, and the legality judge reaches 25 the confidence flag does not. They are looking at
different failures, not at the same ones twice — which is the argument for keeping both, and it is
also the argument that neither subsumes the other.

**Two proofs the design read owes and pays.** The judge's label-token locator and
`scripts/slurp_logprob_judge_read.py::row_confidence` — the read written and unit-tested *before*
the probe flew — were computed on all 1,000 rows for both statistics and agree exactly, 0
disagreements, or the read refuses to report a number. Both frozen floors were re-derived from the
sealed rows as the 86-flag cutoff and asserted equal to the constants the judge ships, and the
registered judge's own flag set asserted equal to the set each cutoff selects.

---

## 4. The rule, fixed now

The confirmation cell is read **only** with the frozen judge, at the frozen threshold, on the fresh
pass's own rows and against the fresh pass's own official per-sample scores through the locked
`slurp-slu-official-projected-v2` scorer. Let

* **P_judge** = precision of `intent_mean_token_logprob` at floor −0.2675283079346116, over the
  rows it flags on the fresh pass, against `scenario_action_exact == 0`;
* **P_legality** = precision of `slurp-legal-label-flag-v1` over the rows *it* flags **on the same
  fresh pass**;
* **A** = AUROC of `intent_mean_token_logprob` for intent error on the fresh pass, speaker-cluster
  bootstrap, 10,000 replicates, seed 20260909, CI90.

**ADMITTED if and only if BOTH arms hold.**

* **Arm A — precision.** `P_judge > P_legality`, **and** the speaker-clustered CI90 lower bound of
  `P_judge` is strictly greater than `P_legality` (the point estimate on the same pass).
* **Arm B — separation.** `A ≥ 0.75` **and** the CI90 lower bound of `A` `≥ 0.70`.

Otherwise **NOT ADMITTED**, and the re-ask module keeps falling back to the deterministic judges.

**This is a conjunction where the predecessor's rule was a disjunction, deliberately.** The
predecessor could pass on either arm; this one must pass on both. A successor chosen after the fact
should face a stricter gate than the rule it succeeds, not a looser one.

**Why the bar is `P_legality` and not the imported 72.09.** 72.09 was KC-S1b's schema-judge number
on a different arm, and the predecessor's own honesty clause already recorded that the same judge
recomputed on the logprob arm reached 30.77 %, not 72.09. Importing a constant across arms is what
made that clause necessary. The legality judge is measured on the *same rows in the same pass* by
the same definition, so the comparison is paired by construction. Its cost is that the bar itself
moves: it flags only ~42 rows and its own CI90 on the design read spans [54.55, 77.78]. That is
accepted, named here, and is the reason arm A compares the judge's LOWER BOUND to the legality
judge's POINT rather than point to point.

**Reported beside the gate, and not part of it:** the paired difference `P_judge − P_legality`
bootstrapped over the same cluster draws, with its CI90; `intent_min_token_logprob` at its own
frozen floor; the union of the judge with the legality judge; both whole precision-recall curves;
and the predecessor's whole-answer minimum recomputed on the fresh rows. If the paired difference
and arm A disagree, **arm A as written decides and the disagreement is reported in the verdict's
first table**, not resolved after the fact.

**One touch.** No knob change, no re-fly on the strength of the number, at most one recovery
re-registration per the standing rule; a second failure stops the flight.

---

## 5. What the fresh pass's own flip rate implies, and how it is reported

The SLURP own-null replicate (`docs/readiness/2026-09-09-slurp-own-null-replicate-v1-verdict.md`,
`SAEA-SLURP-DEV1000-NULL-REPLICATE-V1`) flew the identical 1,000 requests twice and measured:
**17.90 %** of rows returned different completion bytes, **5.90 %** changed their raw
`(scenario, action)` label, **5.20 % (52 of 1,000)** changed their *projected* intent, and on the
intent metric the two passes differed by 18 saves, 13 harms and 969 ties. So of the 52 projected
flips, **31 changed correctness and 21 flipped the label without changing it**.

**This matters to a confidence flag more than to anything else this study measures, because the
rows that flip between two identical passes are, by hypothesis, exactly the low-confidence ones.**
A flag that selects them is at risk of measuring the sampler's own instability rather than the
speech. Three things follow, all fixed now.

1. **The arithmetic of the expected overlap.** If the flag were independent of flipping, the
   expected number of flipped rows inside a flag set of size *F* is `0.052 × F` — about **4.5 rows
   at F = 86**, against a maximum possible overlap of `min(F, 52)`. Anything materially above 4.5
   is evidence the flag is tracking instability; anything near 52 would mean the flag is *mostly*
   an instability detector.
2. **What the confirmation reports, in the verdict body and not in an appendix.** The observed
   overlap between the flagged set and the flip set; the flip rate inside the flag set against the
   flip rate outside it; and `P_judge` computed **separately on flipped and on non-flipped rows**.
   A flag whose precision comes overwhelmingly from flipped rows is a flag whose usefulness is
   confined to a re-ask that would have changed the answer anyway, and the verdict says so in those
   words if that is what the numbers show.
3. **It is reported, not gated.** Arms A and B are measured entirely **within** the fresh pass,
   against that pass's own scores, exactly as the predecessor's were. The flip reading is a
   property of the PAIR and cannot enter a within-pass gate without turning the predecessor's rows
   back into evidence.

**And one honest caveat about the 5.20 % itself.** It was measured on the closed-list DIRECT
comparator and its null, neither of which set `logprobs`. This cell's predecessor does, and
`n_probs > 0` disables backend sampling for the slot on this build
(`server-context.cpp:1994-2004`), so the logprob configuration's own flip rate **has never been
measured**. 5.20 % is imported here as the closest available prior and is labelled as one. The
confirmation measures the real number for free — predecessor against replicate is, by construction,
a null replicate of the logprob configuration — and reports the full flip ladder beside the
imported figure. That measurement is a by-product; it is never an accuracy comparison between the
two arms, and no metric of the replicate is read against the predecessor's.

---

## 6. The harness-admission entry the confirmation would write

`docs/receipts/harness-admission.json`, schema `saea-harness-admission-v2`, enforced by
`scripts/checks/harness_admission_check.py`. On **ADMITTED** the entry is:

```
module:        "label-token decode confidence from the sealed trace (the judge
                slurp-intent-token-logprob-flag-v1 at intent_mean_token_logprob <= -0.2675283079346116,
                fed by decoding_params.logprobs / top_logprobs)"
carrier:       "slurp"
row:           "SAEA-SLURP-DEV1000-CLOSED-LIST-LOGPROB-REPLICATE-V1"
status:        "ADMITTED"
date:          <the verdict's date>
comparator:    {run_id: "SAEA-SLURP-DEV1000-CLOSED-LIST-LOGPROB-V1", attempt_id: <the predecessor's>}
switch:        {table: "judges", key: "judges.<phase>.judges",
                on: ["slurp-intent-token-logprob-flag-v1"], off: null,
                proof: <a test in tests/unit/test_config_table_module_switches.py that composes
                        both arms and diffs exactly that one key>,
                added_by: <this cell's verdict note>,
                what_flew: "THE JUDGE DID NOT FLY INSIDE ANY LOOP. It was read OFFLINE over this
                            cell's own sealed MODEL_LOGPROBS records; the cell is byte-identical to
                            one with no judge at all."}
evidence:      {arm: {run_id, attempt_id}, smoke: <the eight-row smoke's row>,
                primary: <arms A and B, with both intervals>,
                secondary: <the union, the minimum statistic, both PR curves>,
                cost: <the flip ladder and the measured latency of n_probs > 0>,
                receipt: <the confirmation receipt dir>, verdict_note: <the verdict path>}
provisional:   {state: "UNMET",
                reason: "rails.phase_review.default_state_for_review does not carry a row's
                         logprobs, so the switch form this entry records has never been composed
                         or flown",
                requirement: "COMPOSE AND FLY THE SWITCH FORM: extend state_for_review to supply
                              the row's sealed logprobs, declare the judge in a phase_review block,
                              and fly the ON/OFF twin on this carrier"}
not_admitted_for: ["any carrier other than slurp", "any statistic other than
                   intent_mean_token_logprob", "any threshold other than the frozen floor",
                   "in-loop use before the provisional requirement is met"]
```

**`provisional.state` is `UNMET` on an ADMITTED verdict, and that is not a formality.** The check
bars a module whose `provisional.state` is `UNMET` from every `default_plans` entry, which is
exactly right here: what this cell can admit is a **read-time Reviewer signal whose in-flight form
does not exist yet**. On **NOT ADMITTED** the entry is written with `status: "HARMFUL"` and a
`status_basis` saying, as the predecessor's does, that the failure is of this note's own admission
bar and not a measured harm to any metric, because the module never changed an answer.

---

## 7. The cell, and what the wire check already proved

The confirmation cell is the predecessor's configuration, flown again. Contact-free proof,
`docs/checks/speech-aware-evidence-acquisition/2026-09-09-slurp-label-token-logprob-replicate-wire-check/`,
**three stages, all PASS**, zero model contacts, zero servers, zero sockets:

| stage | what it established |
|---|---|
| `request` | The two cells share one baseline fragment, one dataset fragment, one model fragment and one arm. **Zero keys outside the experiment fragments differ**, and the composed configs with every experiment-fragment key stripped hash to the **same** sha256 `014d052a…8055a5b`. `decoding_params` is identical on both sides, `logprobs` and `top_logprobs: 5` included. `config_hash` moves `15670eaa…` → `6ecd015d…` — it must, two runs cannot share an experiment identity. On the four rows the two smokes share, driven through the real `FlightRuntime.wire_check`: no payload field moved, no decoding key moved, the canonical boundary payloads are **byte-identical between the arms**, and the rendered instruction is the predecessor flight's own `4073f79e…0d37db`. |
| `payload_binding` | `rails.core_client.payload_binding_stage` through the real carrier root: **every one of the eight** smoke rows bound, plus the first and last of the 1,000-row cell, zero failures. |
| `media_identity` | Both arms verified the same speech-feature packets — identical sha256 on every shared row — off the same root `/home/chao/feat-cache/slurp-q4km-packets-04ccc72a` under the same pinned `LLAMA_SPEECH_DECODER_SHA256` `0751c279…8066d`. A replicate that read different bytes would be a different observation wearing the same config. |

### 7.1 Sequence and budget

| | |
|---|---|
| geometry | the predecessor's: featcache packets, mmproj-free, `-c 65536 -np 8`, build `04ccc72a`, attached to serving, never started or stopped |
| population | DEV-1000, split identity `8580d199…3c84`, split role `dev` |
| contacts | **8 (smoke) + 1,000 (cell) = 1,008** |
| planned model calls | 12 (smoke) + 1,050 (cell), run-cumulative across every attempt of each run id |
| speech audio | under 30 s (smoke, ceiling 60) + 2,884.7937 s (cell, ceiling 3,000) |
| GPU hours | **≈ 0.07 expected**, against the predecessor's measured 0.0690 on the identical 1,000 contacts; planned ceilings 0.05 (smoke) and 0.10 (cell) |
| paid API spend | 0 |

**Order.** (1) The wire check — already run, PASS, committed. (2) The **eight-row smoke**: eight,
not four, because the geometry is `-np 8` with `id_slot: per-sample`, so eight rows touch every
slot of the resident server exactly once. It re-proves on *this* pass that the pinned llama-server
returns a `choices[0].logprobs` object on the packet route with five alternatives per generated
token, that eight `MODEL_LOGPROBS` records land with recomputable `logprobs_sha256`, and that every
row's reconstruction is a prefix of its sealed text — the one alignment the frozen judge depends
on. **If the smoke fails, the 1,000-row cell does not fly.** (3) The cell, one attempt, one seal.
(4) One scoring pass through `core.scoring_batch` over the one complete manifest, never sharded.
(5) The read, under the frozen judge alone.

---

## 8. What this cell cannot conclude

* Nothing about the **`test` split**, which is never named, loaded, hashed or scored.
* Nothing about **SLURP accuracy**. The replicate's official numbers are its own, reported as this
  arm's own, never as a comparator and never against the locked 73.10 / 35.80. No metric of the
  replicate is read against the predecessor's.
* Nothing about whether a **re-ask helps**. This cell measures which rows a flag would select, not
  what a second contact would do with them. Admission authorizes a re-ask cell to be
  *preregistered*, not flown.
* Nothing about **in-loop behaviour**, for the reason section 1.1 names: the state the judge needs
  does not reach a judge today.
* Nothing about **any other carrier**. Earnings-21 span-level confidence remains the named,
  unregistered follow-up of the predecessor's section 10 and needs its own preregistration and its
  own owner decision.
* And nothing at all until the owner authorizes the flight. This note is a price, a wiring proof
  and a rule. It is not a GO.
