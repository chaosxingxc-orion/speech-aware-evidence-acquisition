# EVO-S1 round 1 — verdict addendum

Addendum to `docs/readiness/2026-09-06-slurp-evo-s1-slot-schema-evolution-v1-preregistration.md`
(REGISTERED). It reports round 1 of at most four. It admits nothing, promotes nothing, and makes no
superiority, generality or Stage-3 claim. The loop's terminal read — DEV-1000 — has not been taken,
and every exposure row involved stays `consumed = no`.

Flown 2026-09-06 and 2026-09-07 on study commits `4152ed7e` (propose, candidates, fold A, select,
fold-B incumbent) and `03400ec4` (fold-B assembly), profile `baseline-reproduction`, frozen
Qwen3-Omni-30B-A3B-Instruct Q4_K_M on llama.cpp featcache build `04ccc72a`, mmproj-free over the
fold packets, `-c 65536 -np 4`, greedy, `max_tokens` 64.

| step | run id | attempts | contacts | rows | products |
|---|---|---|---:|---:|---|
| prompt fit | `SAEA-SLURP-EVO-S1-PROMPT-FIT-V1` | 4 tokenizer sessions | 0 | — | `prompt-fit/prompt-fit.json`, the `/tokenize` binding |
| propose | `SAEA-SLURP-EVO-S1-PROPOSER-V2` | `attempt-r1-p`, `-p2` (both ABORTED), `-p3` | 56 | 54 draws | `round-01/propose.json`, `proposer-outputs.jsonl` |
| fold A | `SAEA-SLURP-EVO-S1-FOLD-A-V2` | `attempt-r1-i`, `attempt-r1-c1`…`c5` | 6,480 | 6 × 1,080 | `round-01/fold-a-*.json`, `fold-a-scores.json` |
| select | — | model-free | 0 | — | `round-01/selection.json` |
| fold B | `SAEA-SLURP-EVO-S1-FOLD-B-V2` | `attempt-r1-i`; `attempt-r1-a` (ABORTED, 0 contacts); `attempt-r1-a2` | 2,160 | 2 × 1,080 | `round-01/fold-b-*.json`, `fold-b-scores.json` |
| confirm | — | model-free | 0 | — | `round-01/confirmation.json`, `evolution-round-01.json` |

Sealed manifests: fold-B incumbent `2567d9eae40925fae4c790e5c9efe198b05f85859a891194b66cdcaef59bbf11`
(config hash `846c742b…`), fold-B assembly
`26a13ae72ae374d46b270f97bb030f7e6befa062c670345c2fed31bcd10be2d7` (config hash `54f1660c…`). Round
receipt `evolution-round-01.json`, SHA-256
`906634869ec1a95e10a796c54b5bd0410db7adff5196612a38833ea73939aff3`. Scorer:
`slurp-slu-official-train`, the SLURP official `evaluate.py` from the pinned local clone, run once
per complete manifest through `core.scoring_batch` and never sharded; both arms passed the
port/official identity check (SLU-F1 absolute difference 0.0 and 5.6e-17).

## Verdict: REJECT. Two of the three conditions hold; the pooled targeted interval fails at exactly zero.

| condition | value | rule | result |
|---|---|---|---|
| pooled targeted CI90 lower bound | **−0.000 pp** (`−9.25e-19`); point **+2.500 pp**, CI90 **[−0.000, +5.417]** | strictly above 0 | **FAILS** |
| every admitted scenario, `harms − saves` on its own 60 rows | `news` **−2**, `social` **−2** | ≤ 2 (the owner's 1-per-30 rate at n = 60) | passes |
| unadmitted scenarios pooled | **−0.264 pp**, CI90 [−1.024, +0.500] | ≥ −1.0 pp | passes |

`A_1 = A_0`: `incumbent_overrides` stays empty and the round's portfolio `58feaf936194c3d9…` is
recorded and dropped. The stop rule reads `continue` — `R_max` is 4 and stopping wants two
consecutive rejects — so the loop *may* open round 2. Nothing in this document authorizes it.

The interval failing *at* zero is not a near miss to be argued around. Over the 120 targeted rows
**six moved up and two moved down**; 112 tied. A bootstrap over eight moved rows of a 0/1-heavy
metric cannot separate itself from zero, and that is the honest reading of the number rather than a
complaint about it.

## 1. The finding: half the targeted movement happened on prompts that did not change

Both arms were flown over the same 1,080 rows through the same harness, so every row's request is
comparable. Two payload fields move between any two runs for scheduling reasons alone —
`request_id`, a dispatch-order index, and `decoding_params.id_slot`, the server slot the request
landed on — so the QUESTION is the rest: `history` (the task text and the rendered schema block),
the task instruction, the speech packet hash, the supplied evidence. Comparing that row by row
across the two sealed traces:

| | rows |
|---|---:|
| asked a **different** question | **61** of 1,080 |
| — of which `news` | 52 of 60 |
| — of which other scenarios whose sealed intent is `news_query` | 9 (`transport` 3, `email` 2, `social` 2, `recommendation` 1, `takeaway` 1) |
| asked a **byte-identical** question | **1,019** |
| — of which returned **different text anyway** | **286 (28.1 %)** |

Now split the rows whose *reward* moved by the same test:

| | saves | harms |
|---|---:|---:|
| moved on a changed question | 3 | 1 |
| moved on a **byte-identical** question | 15 | 16 |

**All four of `news`'s moved rows are of the first kind. All four of `social`'s are of the second.**
Of the eight rows that make up the pooled targeted contrast, four are the mechanism and four are the
decoder.

## 2. Why `social` moved nothing: its admitted candidate is the incumbent's own block

The assembly `configs/knowledge/slurp-evo-s1/evolved-schema-58feaf936194c3d9.json` carries two
intents. One of them is a no-op, and the candidates receipt says so in its own fields:

| winner | intent | rendered SHA-256 | tokens | vs incumbent |
|---|---|---|---:|---|
| `15b1425a…` (`news`, k = 3) | `news_query` | `182f2144c783d54c…` | 163 | incumbent 174, **`token_delta` −11** |
| `bb02b5f3…` (`social`, k = 2) | `social_post` | `f974f889f16a93f2…` | 72 | incumbent 72, **`token_delta` 0** |

`f974f889f16a93f2…` **is** the incumbent's `social_post` rendering. The proposer returned `A_0`'s
block verbatim — the same two types in the same order with the same five and five fillers. The
artifact is 221 bytes of JSON that renders to the state the arm already had.

This is the phenomenon the fold-A commit recorded for `takeaway`, a scenario that cleared the count
gate against blocks identical to the incumbent's — except that `takeaway` was *not* admitted,
because all three of its draws were refused and `select_per_target` requires a candidate artifact.
`social` was admitted because it *has* one. **The guard checks that a candidate exists, not that it
differs.** A candidate whose rendering is byte-identical to the incumbent's should be refused at the
form gate as a null rewrite; on this round it instead spent one of two admissions and diluted the
confirmation with 60 rows of pure noise. That is a concrete, cheap repair and it is this round's
clearest engineering finding.

What `news` changed, for the record — `A_0` on the left, the admitted candidate on the right:

* `news_topic`: `train wreck; fake news; trump 's ties; trump 's potential ties with russia; trending`
  → `politics; music; financial; storm; winning numbers of the powerball lottery`;
* `media_type`: `facebook; l. a. times; so clean; la times; truthdig`
  → `cnn; new york times; facebook; la times; truthdig` — it drops `so clean`, a mis-mined filler,
  and one of the two spellings of the LA Times;
* `date`: `today 's` → `today's`; `person`: reordered, `donald trump 's` → `trump 's ties`;
* the type order moves `date` above `place_name`; `place_name` itself is untouched.

It is a plausible rewrite, it is 11 tokens *shorter* than the block it replaced, and on 52 changed
rows of fold B it bought 3 saves against 1 harm.

## 3. Stage one on fold A, per scenario

`select_per_target` over each scenario's own 60 fold-A rows, paired against the incumbent arm of the
same flight on per-row `slot_f1_exact_f1`. Gate: `saves >= 4`, `harms <= 2` (the owner's 1-per-30
rate at n = 60, carried as `harms_per_rows` and stamped into every outcome as `harms_allowed`),
`net >= 3`. `k = 1..3` are proposer draws and the column below is each scenario's best of the three.

| scenario | best k | saves | harms | allowed | net | delta pp | artifact | admitted |
|---|---:|---:|---:|---:|---:|---:|---|---|
| `alarm` | 2 | 2 | 0 | 2 | +2 | +3.33 | `a4cb4ca5` | no |
| `audio` | 1 | 0 | 0 | 2 | 0 | +0.00 | `bcd68516` | no |
| `calendar` | 2 | 2 | 0 | 2 | +2 | +2.78 | `65cfaf3e` | no |
| `cooking` | 1 | 3 | 1 | 2 | +2 | +2.78 | `03198d1d` | no |
| `datetime` | 1 | 2 | 0 | 2 | +2 | +3.33 | none — all draws refused | no |
| `email` | 2 | 2 | 1 | 2 | +1 | +1.78 | none — all draws refused | no |
| `general` | 1 | 0 | 0 | 2 | 0 | +0.00 | none — all draws refused | no |
| `iot` | 1 | 0 | 0 | 2 | 0 | +0.00 | `86f1e1de` | no |
| `lists` | 2 | 0 | 1 | 2 | −1 | −1.11 | `8070badf` | no |
| `music` | 1 | 1 | 0 | 2 | +1 | +1.67 | `2df9ece1` | no |
| `news` | 3 | 6 | 0 | 2 | **+6** | **+9.44** | `15b1425a` | **yes** |
| `play` | 1 | 1 | 0 | 2 | +1 | +0.56 | none — all draws refused | no |
| `qa` | 1 | 3 | 0 | 2 | +3 | +3.83 | `7c9e964a` | no |
| `recommendation` | 1 | 3 | 1 | 2 | +2 | +3.06 | `5176c3a0` | no |
| `social` | 2 | 4 | 1 | 2 | **+3** | **+1.94** | `bb02b5f3` — renders to the incumbent | **yes** |
| `takeaway` | 2 | 4 | 0 | 2 | +4 | +4.17 | none — all draws refused | no |
| `transport` | 1 | 5 | 3 | 2 | +2 | +4.17 | none — all draws refused | no |
| `weather` | 2 | 7 | 4 | 2 | +3 | +1.11 | `7fecb2fe` | no |

Both controls are strongly harmful, which is what H2 asked:

| control | scenarios worse than the incumbent | worst four strata (pp) |
|---|---:|---|
| F2 shares-only (k = 4) | 16 of 18 | `social` −28.72, `recommendation` −23.44, `transport` −22.22, `datetime` −16.11 |
| F3 token-matched form twin (k = 5) | 14 of 18 | `social` −25.94, `recommendation` −22.33, `transport` −18.39, `datetime` −14.44 |

`replay_selection` reproduces every one of these decisions from the round receipt and the six sealed
`*.score.json` files alone: `matches = True`, zero mismatches, which is what preregistration section
6.9 asks of a round receipt.

## 4. Fold B, per scenario, all eighteen

Paired on `slot_f1_exact_f1` against the incumbent's own sealed pass of the same 1,080 rows.

| scenario | admitted | n | saves | harms | ties | net harm | delta pp |
|---|---|---:|---:|---:|---:|---:|---:|
| `alarm` | no | 60 | 1 | 2 | 57 | +1 | −1.56 |
| `audio` | no | 60 | 0 | 0 | 60 | 0 | +0.00 |
| `calendar` | no | 60 | 0 | 0 | 60 | 0 | +0.00 |
| `cooking` | no | 60 | 2 | 5 | 53 | +3 | **−5.00** |
| `datetime` | no | 60 | 0 | 0 | 60 | 0 | +0.00 |
| `email` | no | 60 | 0 | 0 | 60 | 0 | +0.00 |
| `general` | no | 60 | 0 | 0 | 60 | 0 | +0.00 |
| `iot` | no | 60 | 0 | 0 | 60 | 0 | +0.00 |
| `lists` | no | 60 | 0 | 0 | 60 | 0 | +0.00 |
| `music` | no | 60 | 0 | 0 | 60 | 0 | +0.00 |
| `news` | **yes** | 60 | 3 | 1 | 56 | −2 | **+3.89**, CI90 [−0.56, +8.89] |
| `play` | no | 60 | 2 | 1 | 57 | −1 | +0.83 |
| `qa` | no | 60 | 0 | 0 | 60 | 0 | +0.00 |
| `recommendation` | no | 60 | 0 | 4 | 56 | +4 | **−5.83** |
| `social` | **yes** | 60 | 3 | 1 | 56 | −2 | +1.11, CI90 [−0.56, +3.06] |
| `takeaway` | no | 60 | 3 | 0 | 57 | −3 | **+4.44** |
| `transport` | no | 60 | 2 | 1 | 57 | −1 | +1.78 |
| `weather` | no | 60 | 2 | 2 | 56 | 0 | +1.11 |
| **all 18** | — | **1,080** | **18** | **17** | **1,045** | −1 | **+0.04** |

**Read the two largest magnitudes in that column before the admitted ones.** `recommendation` loses
5.83 pp and `takeaway` gains 4.44 pp on rows whose prompt the assembly never touched — both larger
in magnitude than the `social` admission and comparable to the `news` one. That is the fold's noise
scale, measured on the fold itself.

Official aggregate, both arms over all 1,080 rows:

| metric | incumbent (`attempt-r1-i`) | assembly (`attempt-r1-a2`) |
|---|---:|---:|
| SLU-F1 | 0.46271 | 0.46231 |
| span-F1 (entities) | 0.34657 | 0.34673 |
| intent (scen_act) | 0.31667 | 0.30833 |
| scenario | 0.35463 | 0.34630 |
| action | 0.32315 | 0.31296 |
| mean per-row `slot_f1_exact_f1` | 0.223210 | 0.223642 |
| rows the official parser accepted | 1,074 | 1,073 |

## 5. The curve point on fold B

Under read Option B the curve is fold B at no extra contact: the round's **accepted** incumbent
against `A_0` on the 1,080 confirmation rows. Round 1 was rejected, so `A_1 = A_0` and

> **the curve point after round 1 is +0.00 pp, by construction.**

The rejected assembly's own whole-fold delta against `A_0` was **+0.043 pp** (18 saves, 17 harms,
1,045 ties). It is recorded so a later round's curve has something to be read against, and it
decides nothing: the curve is a report, not a gate. The DEV-1000 final read has not been taken and
must not be taken to settle this round.

## 6. The proposer: 54 draws, 29 candidates, 25 refusals

`SAEA-SLURP-EVO-S1-PROPOSER-V2` `attempt-r1-p3`, one text contact per scenario per proposer slot on
the `construction-proposer-text` arm: 54 draws, 167.682125 s of anchor audio, zero audio parts sent,
159.4 s of wall. **Twenty-five of the 54 draws were refused at the form gate; 29 became candidates.**
A refused slot is never repaired — it flies the incumbent's blocks for that scenario, which is why
several rows of section 3 carry no artifact.

| refusal reason | count |
|---|---:|
| a blank line inside a block (lines 4, 6, 7, 8, 9) | 22 |
| a line outside the block grammar | 1 |
| over the +20 % relative token budget (`general_joke` 154 tokens, `cooking_query` 65) | 2 |

Twenty-two of the twenty-five are one formatting habit: the model puts a blank line between blocks
(corrected 2026-09-07, track E3e: the receipt's 25 refusals are 22 blank lines, 1 line outside the
block grammar and 2 over budget; this table read 23 and the arithmetic did not close).
Per scenario the refusals fall on `play` 3, `takeaway` 3, `datetime` 3, `email` 3, `alarm` 2,
`music` 2, `transport` 2, and one each on `news`, `lists`, `recommendation`, `qa`, `social`,
`general` and `cooking`. **`takeaway` lost all three of its draws**, which is why its 4-saves,
0-harms count in section 3 stands against no artifact at all.

Decontamination: every candidate passed through the digest route
(`docs/receipts/knowledge/slurp-evo-decontamination-v1.json`, SHA-256 `ebfe26a9…`, 2,205 DEV-1000
6-gram digests, with `A_0`'s own 1,008 TRAIN fillers exempt). Exemplar overlap is measured and never
gated: the `news` winner carries 2 overlapping 6-grams
(`march fourth two thousand and seventeenth`, `winning numbers of the powerball lottery`), the
`social` winner 0.

## 7. Form-twin token accounting

F3 is built by `rails.proposer.slurp_form_twin_candidate` at `tolerance = 0`: it replaces every
filler with a neutral placeholder, pads one word at a time while the block is short, and **raises**
rather than approximating — a twin whose plain placeholders already exceed the incumbent is refused
outright, because a shorter twin would have to delete a filler and become a second shares-only
control. The `k = 5` portfolio exists for all 18 scenarios, so every F3 block is **exactly**
token-equal to the incumbent's on the flight's own tokenizer (`token_counter_id`
`llama-server:/tokenize`, the binding `SAEA-SLURP-EVO-S1-PROMPT-FIT-V1` published). No estimator
priced anything.

On the whole rendered prompt, from the fold-A arms' own preflight prompt budget on the same probe
row — the worst-case envelope, which renders the fallback block:

| arm | rendered text tokens | vs incumbent |
|---|---:|---:|
| incumbent (`A_0`) | 9,246 | — |
| F3 token-matched form twin | 9,211 | **−35 (−0.38 %)** |
| F2 shares-only | 8,239 | −1,007 (−10.9 %) |

The −35 is a tokenizer boundary effect and not slack in the construction: the twin is matched block
by block in isolation, and the fallback concatenates every block, so the joins retokenize. **F3 sits
within four tenths of one percent of the incumbent's prompt volume and still falls with F2 in 14 of
18 scenarios.** What the fillers buy is their content and not their volume — and the `news` winner
makes the same point from the other side, at 163 tokens against 174.

## 8. Deviations in force

1. **One recovery re-registration on `SAEA-SLURP-EVO-S1-FOLD-B-V2`, spent and now exhausted.**
   `attempt-r1-a` is terminal ABORTED at **zero** calls and zero audio seconds: the coordinator
   stopped the flight engineer's process while that cell's server was loaded and idle. The server
   log's last line is `all slots are idle` and the run directory holds only that log and the session
   receipt — no outputs, trace, manifest or stop receipt — so nothing was resumed and the assembly
   flew its full 1,080 rows once. It was an operator event and not a CUDA fault, so the
   preregistration's `-np`-reduction recipe was not applied and the serving geometry stayed exactly
   as registered; the incumbent arm of this same run had flown 1,080 contacts clean at `-np 4` forty
   minutes earlier, and changing the geometry would have made the two arms differ by more than the
   artifact under test. The successor `attempt-r1-a2` differs by its attempt id alone, carried as
   `--attempt-id` rather than written into `configs/experiment/slurp-evo-s1-fold-b-r01.json`,
   because `core.config.compose` merges the experiment fragment whole and editing the assembly cell
   would have moved config hash `846c742b…`, which the incumbent arm is already sealed under.
   Registered before the successor's first contact:
   `docs/checks/speech-aware-evidence-acquisition/2026-09-06-slurp-evo-s1/round-01/fold-b-recovery-re-registration.json`.
2. **Two failed attempts on `SAEA-SLURP-EVO-S1-PROPOSER-V2`, which is one more than the rule
   allows.** `attempt-r1-p` died on its first contact at the speech-feature query gate
   (`query_source` must be `speech_features`); `attempt-r1-p2` died on its first contact on the
   server's missing-mmproj HTTP 500. Each cost one call and 2.687625 audio seconds, and neither
   produced a candidate or a read result. The engineering-base rule allows one recovery per flight
   and requires the second failure to stop the flight for a four-row dry run; it was retried in
   place instead. Recorded here and in that row's own ledger note rather than left in the attempt
   store alone.
3. **The fold-A intent flight `attempt-intent-a` is terminal ABORTED with all 1,080 contacts
   landed**, its seal having died in the scoring step on a devel-bound scorer id. That was
   registered and resolved before round 1 (ledger row `SAEA-SLURP-EVO-S1-INTENT-FOLDS-V2`); the fold
   was not re-flown because `verify_bundle` passes on its sealed manifest and a re-fly would have
   put the run id over its ceiling. Restated here because its 1,080 calls are part of round 1's cost.
4. **The fold-B incumbent receipt was committed one session late.** Its flight, seal and scoring
   completed at 21:36 local on 2026-09-06 and were durable on the data root, but the engineer was
   stopped before the receipt reached the tree. It was landed unchanged, byte for byte, in commit
   `ebe2424e`; nothing was re-flown to recover it.

## 9. Cost

Contacts and speech audio are the durable per-attempt figures from `core.attempts`. GPU residency is
**measured** from each attempt's session receipt and stop receipt, not declared: this harness records
no `gpu_seconds` and every attempt file carries `0.0` there.

| step | attempts | contacts | speech audio (s) | GPU residency |
|---|---|---:|---:|---:|
| prompt fit | 4 | 0 | 0 | 55.6 s (0.015 h) |
| fold packets | 3 | 0 — CPU preprocess | — | 0 |
| intent folds, one-time | 2 | 2,160 | 6,239.325812 | 1,218.8 s (0.339 h) |
| four-row smoke | 2 | 8 | 18.302000 | 561.5 s (0.156 h) |
| propose | 3 | 56 | 173.057375 | 195.9 s (0.054 h) |
| fold A, six arms | 6 | 6,480 | 18,507.170625 | 6,262.7 s (1.740 h) |
| fold B incumbent | 1 | 1,080 | 3,154.797375 | 982.1 s (0.273 h) |
| **fold B aborted attempt** | 1 | **0** | **0** | **≤ 240 s (≤ 0.067 h) — bounded, not measured** |
| fold B assembly, the recovery | 1 | 1,080 | 3,154.797375 | 981.2 s (0.273 h) |
| wire checks and dry runs | 8 | 0 | 0 | 0 |
| **round 1 total** | | **10,864** | **31,247.450562 (8.680 h)** | **≈ 10,498 s (2.916 h)** |

The aborted attempt's GPU figure is a bound and is labelled as one: its session receipt is stamped
`01:40:13Z`, the stop landed about four minutes later, and no resource sampler ran to completion, so
no measured figure exists. It sent nothing, so it consumed no budget — the fold-B row's
run-cumulative durable spend is 2,160 calls and 6,309.594750 audio seconds against a registered
8,640 / 25,300, and the recovery fitted inside the plan with zero call headroom and 0.41 s of audio
headroom.

Throughput, for the pipeline record: fold-B `run_phases` 662.95 s (incumbent) and 672.88 s
(assembly) for 1,080 contacts each — 1.629 and 1.605 contacts per second at `-np 4`, average latency
1.350 s and 1.376 s, against the 0.7359 s per contact the budget was written at. Packet
preprocessing ran on 8 workers while the GPU served: 1,080 packets in 9.13 s and 11.59 s, 118.3 and
93.2 packets per second. Official scoring took 151.9 s and 141.2 s, one complete manifest per
process.

## 10. What this authorizes

Nothing beyond recording the round. It does **not** authorize round 2, the DEV-1000 final read, any
expansion of the fold set, any change to the gates, or any claim about the mechanism. Three items
are handed to whoever opens the next round, in the order they matter:

1. **Refuse a candidate that renders to the incumbent.** `select_per_target` requires an artifact but
   not a *different* artifact, and `social` was admitted on one that renders byte-identically. The
   form gate already computes `rendered_sha256` and `token_delta` per candidate, so comparing that
   hash against the incumbent's block is a one-line refusal. It would have cost this round nothing
   and would have kept 60 rows of noise out of the confirmation.
2. **The gate's noise floor is now measured, and it is large.** 286 of 1,019 byte-identically
   prompted rows returned different text, and 31 rows moved their reward on an unchanged prompt
   against 4 on a changed one. Any admission rule read on counts of 3 to 6 moved rows out of 60 is
   operating below that floor. A rule change, a paired re-fly of the same arm as an explicit null
   control, and a larger per-scenario `n` are the three ways out, and only the owner picks among
   them.
3. **Twenty-two of the 25 refusals are one blank line.** Saying so in the proposer instruction
   would roughly double the number of scenarios holding a real candidate, which is the cheapest
   available increase in this loop's search width.
