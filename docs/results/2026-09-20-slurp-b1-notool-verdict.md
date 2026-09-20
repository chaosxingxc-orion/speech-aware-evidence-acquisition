# NON-INFERIORITY NOT PROVEN -- cell B1-notool: the Reviewer's task-contract tool withdrawn on the B1 base (repair form 0-B), SLURP TRAIN Fold A, 1,080 rows

**The preregistered rule names ADMITTED / NEUTRAL / HARMFUL and this read reaches none of the
three, so it does not claim one.** Against the sealed B1 arm, official pooled SLU-F1 is
**+0.9901 pp, CI95 [-0.5924, +2.5038]** -- non-inferior at the registered -1.2350 margin, and not a
gain -- and intent is **-0.1852 pp, CI95 [-1.3334, +0.9076]**, whose lower bound crosses the
-1.2212 margin **by 0.1122 pp**. There is **no measured loss** on either guard (no point estimate
below -h, no CI95 upper bound below zero), so owner decision 25 excludes HARMFUL. Because the intent
lower bound does not clear its margin, the preregistration's NEUTRAL clause is not satisfied as
written, and this read will not write NEUTRAL on a cell that did not earn NEUTRAL's consequence --
admission into the SLURP default plan. **Section 11 states the decision the coordinator and the
owner now have to make, and the program precedent that bears on it.**

**The efficiency result, which is this cell's registered deliverable, is unambiguous and large.**
Withdrawing the Reviewer's toolkit takes **prefilled tokens per row from cell B1r's 26,072 to
8,020 (-69.2 %)**, **GPU hours per 1,080 rows from 3.8507 to 1.6108 (0.418x)**, **contacts per
minute from 23.10 to 42.91 (1.86x)** and the projected 13,078-row read **from 46.6 h to 19.5 h**. It
is cheaper than the other way of holding the per-slot prefix constant (cell EFF-1: 10,127 prefilled
tokens per row, 1.843 GPU-h, 45.94 contacts/min) and it carries none of EFF-1's delivery-shape
damage: **zero Solver completions come back tool-call-shaped**, against EFF-1's 145, and the
official scorer fails to parse **4 rows of 1,080**, exactly the sealed B1 arm's own count.

Date: 2026-09-20. Model-free read: **zero model, tokenizer, encoder, ASR, server and paid-API
contacts**. The one official score was produced by the flight's own campaign at finalize; this read
invoked only the model-free projection-v3 and TRAIN symmetric scorers, over **copies** of the sealed
outputs written under its own analysis directory. The resident llama-server was never started,
stopped or queried -- its `server.log` and `monitor.jsonl` were read as files. No sealed artefact and
no file under `SPEECHRL_DATA_DIR/runs` or `/attempts` was written, moved or modified; nothing was
committed by this read.

Authority, applied unchanged:
[`docs/readiness/2026-09-20-slurp-b1-notool-v1-preregistration.md`](../readiness/2026-09-20-slurp-b1-notool-v1-preregistration.md)
sections 3-5 and its package
[`docs/readiness/2026-09-20-slurp-b1-notool-v1/`](../readiness/2026-09-20-slurp-b1-notool-v1/README.md)
(`analysis-recipe-v1.json`, `protocol-registered-v1.json`); owner decisions 55, 56, 57, 58, 53, 38,
30, 28, 25, 23, 17, 14 and 7; the margins, the comparator's sealed numbers and the per-role cost
profile in
[`docs/results/2026-09-19-slurp-b1-replicate-verdict.md`](2026-09-19-slurp-b1-replicate-verdict.md);
the efficiency method and the constant-rendering reference in
[`docs/results/2026-09-19-slurp-eff1-tool-constant-verdict.md`](2026-09-19-slurp-eff1-tool-constant-verdict.md).

Analysis root (all outputs): `SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-B1-NOTOOL-PAIRED-ANALYSIS-V1`.

---

## 1. What flew, re-derived and not assumed

Run `SAEA-SLURP-NATIVE-EXEMPLARS-K20-NOTOOL-V1`, attempt
`attempt-slurp-native-exemplars-k20-notool-train-fold-a-generation-v1`, **FINALIZED**, manifest
**COMPLETED**.

| fact | verified value |
| --- | --- |
| study commit / `study_repo_dirt` | `23f011dddde358d21f840cfabb9952d72a33c2ec` / `[]` (empty) |
| run-manifest sha256 | `b4ae2458221910324ba7338b78523d757e46f791c355ca6ddbdb3ac991a3e2b7` |
| scores sha256 | `d45ed82222c75a26d45cdb672151b034eab3e556d78dc4fb2799b30b77409a5d` |
| outputs sha256 | `81b370bfceb49ff9213e06f4b1e315d563f56e072862d26f98f559a7abba82ca` |
| phases sha256 | `69973679cf2c380f2bf3c1d00a7c65d8e54b0619c85f3badfd5c825c150bb4a8` |
| trace sha256 | `2a21d235dd2d385f9b0769185346c83057719512c3a096ca11ca15aa1d271887` |
| flight-receipts sha256 (file / own `receipts_hash`) | `91c5ce507de6cb6c59d1d87637f77002a9f783ee40f7b3e0738ee3b3870b7fc1` / `559ab37f4c3e553ab7052f67f1b15a09e67a78c36568a1440130084474ed015f` |
| composed config hash | `abdf14e7df2cb1619c74f6328c96c31e78fc62843279846bbecdf31f71366382` -- the package's registered value |
| protocol hash | `743313686772b96d0e07603188b3437990660538706a3c4cd7a1e8c66029e8b8` -- the package's registered value |
| config fragments | baseline `slurp-native-anchor-exemplars-k20-notool-v1`, experiment `slurp-native-exemplars-k20-notool-v1`, dataset `slurp-speech-native-evo-fold-a-1080`, model `q4km-mmproj-free-slurp-native-bounded-perception-proof-np4-ctx24k-max512-v1` |
| execution profile / arm / role | `bounded-discovery-probe` / `speech-feature-query-native-tools` / `discovery` |
| split identity / rows | `61b0f062...5398b6` / **1,080 distinct sample ids** |
| phase artefact | one phase, policy and controller `phase-native-candidates-review-revise-v1`, executor `openjiuwen-workflow-v1`, knowledge snapshot `a43d8b93f93c4c6d294c8f23b7aa0dd5cc340d00d566bff88880d931ddf3ef80` -- **identical to B1's and B1r's snapshot digest** |
| cost | 4,432 contacts; 12,687.047750000034 repeated speech seconds; 35,728,582 prompt tokens; 266,131 completion tokens; **0 tool calls** |
| flight | wall 6,400.412614583969 s; slot occupancy 0.7873; **1.6108 GPU hours** (5,798.925 monitor active seconds); utilisation 77.72 %; parked 0.0921; mean power 84.75 W |
| fit | **4,432** `*.request-fit.json` receipts / 17,728 endpoints, `every_request_fits = true` |
| scoring | **one** official score job at finalize (152.39 s), scorer `slurp-official-8eb16545`, evaluator commit `8eb16545762be97ace75334109d73824217311f1`, port/official identity check passed, **no projection on the decision score** |
| campaign | the committed single-cell plan; status `scored`; the campaign log's 40 ERROR lines are five log events for each of the eight finite-completion rows of section 7 and nothing else |

**The four-row smoke sealed first, as registered**, under attempt
`attempt-slurp-native-exemplars-k20-notool-smoke-4-generation-v1r` (COMPLETED at study commit
`0e4cdc05`, empty dirt): 4 rows, 15 contacts, **0 tool schemas and `tool_choice` `none` on all 15
requests**, 0 tool calls. The first smoke attempt id was **voided with zero contacts** after two
pre-contact harness refusals (`rails.core_client` refused a tool-free native arm; items E23 / E23b);
its receipt is `coordination/slurp-b1-notool-v1/attempt-void-emplars-k20-notool-smoke-4-generation-v1-20260920.json`
and the attempt store records `ABORTED` with `calls = 0`, `audio_seconds = 0.0`.

**Population.** TRAIN Fold A, 1,080 rows, 125 speaker clusters, 18 scenarios of 60, 523 headset and
557 far-field rows; roster `docs/receipts/rosters/slurp-evo-fold-a-v2.json`
(`1fe7908c...`), metadata `07f4cd83...`. Row accounting: **1,080 in, 1,080 out on every arm**, no row
dropped and no sample id invented.

## 2. The STOP condition, both halves

| clause | result |
| --- | --- |
| the gating comparator reproduces its registered 61.14 / 80.19 from its own sealed bytes | **YES** (61.1394 / 80.1852; scenario 86.3889, action 81.3889, span 48.4286 all reproduce) |
| cell B1r reproduces its registered 62.23 / 80.09 | **YES** (62.2324 / 80.0926; 86.8519 / 81.0185 / 49.9228) |
| the sealed dual-store anchor reproduces 48.53 / 77.96 | **YES** |
| `analysis.null_calibration.pooled_f1` reproduces every arm's own official aggregate | **YES**, to better than 1e-6 on all four arms and both micro metrics |
| **cell B1r's own null reproduces field by field** | **57 field checks, 0 failures** |
| **the margins, recomputed rather than quoted** | **h_SLU = 1.2350** and **h_intent = 1.2212**, both to within 1e-4 of the registered values |

The last two rows matter more than the others: the margins this cell is judged against are not
quoted from cell B1r's verdict, they are **recomputed here from the sealed score bytes with the same
estimator, seed and draw count**, and every published figure of that own null -- deltas, both
interval bounds, both half-widths, and all fifteen saves / harms / ties -- reproduces.

## 3. The official contrast and the registered guards

Estimator: paired whole-speaker cluster bootstrap over **125** speaker clusters, **10,000 draws,
seed 20260915**, CI95 for the clauses and CI90 beside; sensitivity the paired scenario-stratified row
bootstrap on the same draws and seed. Delta = B1-notool minus the left arm, in percentage points.

| Metric | B1 | B1-notool | Delta | Speaker CI95 | Speaker CI90 | Equal-scenario |
| --- | ---: | ---: | ---: | --- | --- | ---: |
| Official pooled SLU-F1 | 61.14 | 62.13 | +0.9901 | [-0.5924, +2.5038] | [-0.3207, +2.2427] | +0.73 |
| Intent (scenario+action) | 80.19 | 80.00 | -0.1852 | [-1.3334, +0.9076] | [-1.1591, +0.7435] | -0.19 |
| Scenario | 86.39 | 86.48 | +0.0926 | [-0.8065, +1.0903] | [-0.6686, +0.9193] | +0.09 |
| Action | 81.39 | 81.11 | -0.2778 | [-1.3994, +0.8159] | [-1.2122, +0.6524] | -0.28 |
| Pooled span F1 | 48.43 | 49.03 | +0.5990 | [-1.4916, +2.5805] | [-1.1541, +2.2520] | +0.56 |
| Exact slot F1 (row mean) | 31.35 | 31.53 | +0.1843 | [-1.1234, +1.4784] | [-0.9128, +1.2673] | +0.18 |
| SLU-F1 (row mean) | 40.15 | 40.69 | +0.5380 | [-0.6228, +1.6591] | [-0.4298, +1.4742] | +0.54 |

Saves / harms / ties on the gating contrast, with the exact two-sided McNemar p:

| Per-row metric | saves | harms | ties | exact two-sided McNemar p |
| --- | ---: | ---: | ---: | ---: |
| scenario_action_exact | 23 | 25 | 1032 | 0.8854 |
| scenario_exact | 17 | 16 | 1047 | 1 |
| action_exact | 22 | 25 | 1033 | 0.7709 |
| slot_f1_exact_f1 | 41 | 35 | 1004 | 0.5666 |
| slu_f1_f1 | 63 | 53 | 964 | 0.4035 |

Scenario-stratified sensitivity on the gating contrast: pooled SLU CI90 [-0.0333, +2.0289] and CI95
[-0.2372, +2.2569]; intent CI90 [-1.2037, +0.8333] and CI95 [-1.3889, +1.1111]. Neither changes
sign, and the intent clause fails on the sensitivity estimator too -- by 0.1677 pp instead of
0.1122.

### 3.1 The registered clauses, applied unchanged

| guard | delta pp | CI95 | margin -h | point below -h? | CI95 upper below 0? | CI95 lower above -h? | CI95 lower above 0? |
| --- | ---: | --- | ---: | --- | --- | --- | --- |
| official pooled SLU-F1 | **+0.9901** | [-0.5924, +2.5038] | -1.2350 | no | no | **yes** | no |
| intent (scenario+action) | **-0.1852** | [-1.3334, +0.9076] | -1.2212 | no | no | **NO (by 0.1122 pp)** | no |

* **HARMFUL is excluded.** Owner decision 25 requires a measured loss -- a point estimate below -h
  or a CI95 upper bound below zero. Neither happens on either guard: the SLU point is **positive**,
  the intent point is -0.19 pp against a -1.2212 margin, and both upper bounds are comfortably above
  zero (+2.50 and +0.91). Saves against harms on intent are **23 / 25** with an exact two-sided
  McNemar p of **0.885** -- a coin flip on 48 moved rows in 1,080.
* **ADMITTED is excluded.** The pooled SLU CI95 lower bound is -0.5924, not above zero.
* **NEUTRAL is not satisfied as written.** Its second conjunct fails by 0.1122 pp.

### 3.2 Why the intent guard misses, precisely

Two facts decide how to read the miss, and both are measurements of this read.

**First: the miss is arithmetic, not width.** The arm's own intent interval is **narrower** than the
margin -- half-width **1.1205 pp** against h_intent = 1.2212. The registered clause compares the
*lower bound* to -h, so it is passed only when the point estimate exceeds (half-width - 1.2212), here
**-0.1007 pp**. The arm's point estimate is **-0.1852 pp**. It misses by **0.0845 pp of point
estimate**, or eight hundredths of a percentage point -- one row in 1,080 is 0.0926 pp.

**Second: cell B1r fails the same clause.** The margin's own source -- the request-identical
replicate of the B1 base, in which *nothing* changed but batch composition -- has an intent delta of
-0.0926 pp with CI95 **[-1.3145, +1.1279]**. Its lower bound, -1.3145, **also crosses -1.2212**. So
the clause as written cannot be passed on intent by any arm whose intent point estimate sits below
about -0.10 pp, including a pure null. This is a property of the registered rule, not a property of
this cell; it is recorded here and is not a re-decision of anything.

**Third, and the substantive one: the clause turns on eight rows.** The registered diagnostic --
the primary metrics recomputed with the eight `finite_completion` rows of section 7 excluded,
reported **beside** the registered all-rows number, which stays the number the rule reads --

| population | rows | pooled SLU delta | CI95 | intent delta | CI95 |
| --- | ---: | ---: | --- | ---: | --- |
| **all rows (REGISTERED)** | 1,080 | +0.9901 | [-0.5924, +2.5038] | **-0.1852** | **[-1.3334, +0.9076]** |
| finite-completion rows excluded (diagnostic) | 1,072 | +0.9984 | [-0.5956, +2.5228] | **-0.0933** | **[-1.2174, +0.9709]** |

The eight rows account for **0.0919 pp of the intent delta -- one row in 1,080** -- and with them out
the intent lower bound is **-1.2174** and clears -1.2212. **No row was filtered from the scored
manifest**, and this table changes no verdict; it names the component that decides the clause.

## 4. The decision-56 clause

| metric | sealed B1 | B1-notool | relative difference | within 5 %? |
| --- | ---: | ---: | ---: | --- |
| official pooled SLU-F1 | 61.1394 | 62.1295 | **+1.619 %** | **YES** |
| official intent | 80.1852 | 80.0000 | **-0.231 %** | **YES** |

**Both lie within 5 % relative of the sealed B1 values, so under owner decision 56 the anchor-base
and plan-base withdrawal cells are NOT flown.** The clause is stated here; the coordinator records
it.

## 5. The efficiency read (mandatory, reported whatever the verdict)

The join is a **measurement, not an estimate**: `n_tokens` at release minus generated plus one equals
the client's `usage.prompt_tokens` on **4,432 of 4,432 contacts (100.00 %)**, and the 4,432 server
release records inside the flight's sealed contact window match the 4,432 client contacts exactly,
balanced across the four KV slots (1,093 / 1,146 / 1,129 / 1,064). `monitor.jsonl`'s
`requests_delta` for this window reads **2,181** against 4,432 realized contacts and is not used.

| quantity | **B1-notool (measured)** | B1r REFERENCE (tool present) | B1 base (sealed) | EFF-1 REFERENCE (constant rendering) |
| --- | ---: | ---: | ---: | ---: |
| **prefilled tokens / row** | **8,019.8** | 26,071.9 | not on file | 10,127 |
| client prompt tokens / row | 33,082.0 | 45,998.6 | 45,730.5 | -- |
| completion tokens / row | 246.4 | 238.4 | 236.6 | -- |
| **GPU hours / 1,080 rows** | **1.6108** | 3.8507 | 3.6819 | 1.843 |
| wall seconds | 6,400.4 | 14,437.7 | 13,894.2 | 6,913.6 |
| contacts / row | **4.104** | 5.040 | 5.023 | 4.901 |
| **contacts / minute** (server.log releases) | **42.91** | 23.10 | not on file | 45.94 |
| packet re-decodes / row | 0.996 | -- | -- | 0.996 |
| cache hit share | **75.76 %** | 43.32 % | not on file | 75.20 % |
| aggregate prefill tok/s | 1,353.3 | 1,950.3 | not on file | 1,582.0 |
| aggregate decode tok/s | 41.6 | not on file | not on file | 33.8 |
| slot occupancy | 0.787 | 0.868 | 0.877 | 0.891 |
| mean utilisation % | 77.72 | 87.09 | 91.01 | 85.06 |
| parked fraction | 9.21 % | 3.88 % | 4.52 % | 3.80 % |
| **projected 13,078-row read** | **19.5 h** | 46.6 h | 44.6 h | 22.3 h |

Both reference columns were **re-read from their own sealed analysis artefacts**, not quoted from
prose: B1r's `server-join.json` reproduces its published 26,071.9 prefilled tokens per row, 43.32 %
cache share, 1,950.3 prefill tok/s and 23.10 contacts per minute exactly.

### 5.1 Per position -- where the saving comes from

| position | role | tools | client prompt med | prefilled med | cached | generated med | latency p50 | latency p90 | prefilled/row | share of row prefill | B1r REFERENCE prefilled/row (per role) | B1r REFERENCE cached |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | perception | 0 | 3593 | 1368 | 61.97 % | 133 | 5.34 | 8.82 | 1367.8 | 17.06 % | 1367.8 | 61.97 % |
| 1 | solver | 0 | 9685 | 6342 | 35.41 % | 24 | 6.82 | 10.40 | 6120.1 | 76.31 % | 6164.4 | 36.05 % |
| 2 | reviewer | 0 | 9662 | 236 | 97.49 % | 89 | 3.61 | 8.76 | 237.1 | 2.96 % | 9275.6 | 56.36 % |
| 3 | planner | 0 | 9793 | 258 | 97.24 % | 2 | 0.39 | 4.02 | 262.0 | 3.27 % | 9264.1 | 19.49 % |
| 4 | solver | 0 | 9594 | 340 | 96.37 % | 24 | 1.71 | 4.65 | 12.7 | 0.16 % | 6164.4 | 36.05 % |
| 5 | reviewer | 0 | 9565 | 232 | 97.51 % | 138 | 7.11 | 11.44 | 8.7 | 0.11 % | 9275.6 | 56.36 % |
| 6 | planner | 0 | 9720 | 306 | 96.75 % | 2 | 0.64 | 4.51 | 11.5 | 0.14 % | 9264.1 | 19.49 % |

This is the whole mechanism, in one column. The Reviewer's prefill per row falls from B1r's
**9,275.6 to 237.1** and the Planner's from **9,264.1 to 262.0**, and their cache-hit shares rise to
**97.5 %** and **97.2 %** from 56.4 % and 19.5 %. The tools array sat between the shared prefix and
the role content, so **every contact after the Solver had to re-prefill the row**; with the array
gone the Reviewer and Planner requests are extensions of a prefix the slot already holds. **The two
positions upstream of the Reviewer are untouched**: perception prefill is 1,367.8 per row on both
arms, to the token, and the Solver's is 6,120.1 against B1r's 6,164.4 (-0.7 %, the size of one
realisation's noise on 1,080 rows). That is what a factor confined to the Reviewer's toolkit should
look like.

Two costs are visible and are not hidden: **slot occupancy falls to 0.787 and the parked fraction
rises to 9.21 %** -- with the row four contacts long and the tail nearly free, the client cannot keep
four slots busy, so the flight leaves GPU idle. The arm still finishes the same 1,080 rows in
**0.44x the wall clock** (6,400 s against 14,438 s). Raising concurrency is a **geometry** question
and this cell makes no geometry claim.

### 5.2 Per role, client prompt volume

| Role | contacts (arm) | contacts (B1r) | prompt med (arm) | prompt med (B1r) | delta | prompt p90 (arm) | prompt p90 (B1r) | completion med (arm) | completion med (B1r) | completion p90 (arm) | completion p90 (B1r) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| perception | 1080 | 1080 | 3593 | 3593 | +0 | 3650.1 | 3650.1 | 133.0 | 133.0 | 144.0 | 144.0 |
| solver | 1120 | 1092 | 9663 | 9769 | -106 | 11544.3 | 11586.4 | 24.0 | 24.0 | 35.0 | 35.0 |
| reviewer | 1120 | 2180 | 9644 | 10672 | -1028 | 11519.0 | 12926.1 | 90.0 | 28.5 | 171.1 | 86.0 |
| planner | 1112 | 1091 | 9788 | 11649 | -1861 | 11643.8 | 13450.0 | 2.0 | 2.0 | 2.0 | 2.0 |

The Perception median, p90 **and flight total (3,884,813 tokens, identical to B1r's and B1's to the
token)** are unmoved, which is the arithmetic consequence of 1,080 byte-identical first requests. The
Reviewer's median prompt falls 1,028 tokens and the Planner's 1,861 -- the tools array and the tool
round trip it caused. The one figure that **rises** is the Reviewer's own answer: its completion
median goes **28.5 -> 90** and its p90 **86 -> 171.1**, because it now writes its review instead of
emitting a tool call. That rise is what section 7's eight finite completions are made of.

### 5.3 Prompt fit

`every_request_fits = true` on all **4,432** receipts. The minimum margin is **10,711 tokens** in the
`planner` phase against the 24,576-token slot and the widest realized request needed **13,865**
tokens -- against cell B1r's 8,254 margin and 16,322 widest. The withdrawal buys **2,457 tokens of
headroom** in the tightest phase. Per phase: perception 20,306 / 4,270; solver 10,746 / 13,830;
reviewer 10,782 / 13,794; planner 10,711 / 13,865.

## 6. Structure: no tools anywhere, and the request bytes are B1r's

| claim | B1-notool | B1 | B1r |
| --- | ---: | ---: | ---: |
| model requests | 4,432 | 5,425 | 5,443 |
| requests carrying a `tools` array | **0** | 2,171 | 2,180 |
| `tool_choice` values | `none` x 4,432 | `none` x 3,254, `auto` x 2,171 | `none` x 3,263, `auto` x 2,180 |
| native task-contract tool calls | **0** (registered ceiling 0) | 1,084 | 1,088 |

The recipe's inherited **constancy table does not apply** to this factor: `tool_schema_rendering`
(item E17) is the EFF-1 key and is not armed here, so no arm seals a
`saea-native-tool-schema-rendering-v1` block and there is no `distinct_tool_schemas_sha256` to count.
The stronger structural claim is measured instead and holds: **no request carries a tools array and
every `tool_choice` is `none`**.

### 6.1 Request identity against cell B1r

The comparison excludes exactly six named bookkeeping fields and nothing else: `request_id` (the
flight counter), every `evidence_provenance` entry's `relpath` (each entry's `lock_key` and `sha256`
stay compared), `decoding_params.id_slot`, and each `history` entry's three per-flight state
identifiers `state_id`, `source_query_state_sha256` and `source_response_sha256`. Every history
entry's `content` and `content_sha256` stay compared, as do `task_instruction`, `supplied_evidence`,
`tool_schemas`, `max_tokens`, `response_format`, `parallel_tool_calls`, `seed`, `temperature`,
`tool_choice`, `speech_feature_parts`, `speech_packet_sha256`, `speech_ref`, `media_relpath`,
`key_representation_id`, `matcher_policy_id`, `query_source`, `mmproj_loaded`, `sample_rate_hz` and
`audio_seconds`.

**The three history fields are a correction this read had to make, and it is reported rather than
buried.** `source_response_sha256` digests the upstream contact *receipt*, not the upstream answer:
it differs on **1,080 of 1,080** first contacts even between cell B1 and its own request-identical
replicate. While it is inside the digest, no downstream request of any two flights can ever be
byte-identical, and the registered claim would be unfalsifiable. The same applies to the contact
receipt's `response_sha256`, which is therefore **not** used to decide whether two flights are in
sync; a SHA-256 of the delivered response **text** is used instead.

| quantity | value |
| --- | ---: |
| first model-facing request byte-identical to B1r's, per row | **1,080 of 1,080** |
| ... whole payload identical including the bookkeeping fields | 1 |
| Perception responses identical to B1r's | 230 of 1,080 |
| tool-free contacts checked while in sync (perception + solver) | **1,310**, byte-identical **1,310** -- claim **HOLDS** |
| Reviewer contacts checked while in sync | **195**, identical once the toolkit is removed **195** -- claim **HOLDS** |
| Reviewer toolkit pair on every checked contact | arm `0 schemas / tool_choice none` vs B1r `1 schema / tool_choice auto` |
| total violations | **0** |
| Solver responses identical to B1r's (unconditional) | 811 of 1,080 |
| rows byte-identical over the whole trajectory | 0 |
| rows with different contact counts | 1,077 |

**One honest refinement of the registered claim.** Withdrawing the toolkit removes **two** things
from the Reviewer request, not one: the `tool_schemas` array **and** the `tool_choice` that goes with
it, which the harness renders as `auto` when the role holds a tool and `none` when it does not. On
all 1,080 rows the Reviewer request differs from B1r's in exactly those two places and in nothing
else; with `tool_schemas` alone removed it differs on all of them, by `tool_choice`. The package
README's wording ("differing by exactly the absent tools array") is therefore true of the array and
incomplete about the flag it controls; the measured claim is stated above.

"In sync" closes a row at the first response that differs, so the 1,310 and 195 are the contacts on
which the claim is *checkable* -- 1,080 Perception, then the 230 rows whose Perception answer was
identical, then the 195 of those whose Solver answer was identical too. Greedy decoding at
temperature 0 is not bitwise reproducible across batch compositions; 230 of 1,080 identical first
responses here sits beside the 244 of 1,080 cell B1r measured against cell B1 on the same bytes.

## 7. Trajectory, dispositions and the review loop

| signal | B1-notool | B1 | B1r |
| --- | ---: | ---: | ---: |
| contacts per row | **3: 8, 4: 1,032, 7: 40** | 4: 2, 5: 1,071, 8: 1, 9: 6 | 4: 3, 5: 1,065, 8: 2, 9: 10 |
| Reviewer contacts per row | **1: 1,040, 2: 40** | 1: 2, 2: 1,071, 3: 1, 4: 6 | 1: 2, 2: 1,066, 3: 2, 4: 10 |
| Planner routes / `REVISE` tokens | 1,112 / **43** | 1,087 / 8 | 1,091 / 12 |
| rows with at least one `REVISE` | **40** | 7 | 12 |
| `revision_limit` terminal dispositions | **3** | 1 | 0 |
| `finite_completion` rows (item E13) | **8** | 0 | 1 |
| `react_exhaustion` visits (item E22) | **0** | 0 | 0 |
| `planner_action_illegal` rows | **0** | 0 | 0 |
| aborts / recovery re-registrations | **0 / 0** | -- | -- |

**The contacts-per-row shape is exactly what the factor predicts.** A plain row costs four contacts
(perception, solver, reviewer, planner) instead of five, on **1,032 rows**; 40 rows take the revise
route and cost seven; and **8 rows cost three** because the Reviewer's completion was cut off before
the Planner ran. Nothing exceeded the ceiling of 11.

**The eight finite completions, and what they cost.** All eight are the same shape: role `reviewer`,
stage `review`, `finish_reason` `length`, `revision_count` 0, `planner_accepted` false. Item E13's
`deliver-latest-or-abstain` retained every one of them and delivered the latest Solver draft (87-141
characters); **none abstained**, and the official scorer parsed all eight. Without that declaration
the flight would have aborted eight times, which is exactly how cell B7a lost an arm on 2026-09-19 --
and here the campaign log's 40 ERROR lines (five log events per row, "metered completion is
non-authoritative because finish_reason is 'length'") are the harness catching them. The sample ids
are `slurp:train:000023`, `000036`, `000455`, `010043`, `011568`, `014548`, `015165` and `015196`
(with their audio suffixes, recorded in `structural.json`); by scenario they fall in `iot` (2),
`social` (2), `general`, `cooking`, `qa` and `recommendation` -- **none of them in `music`**, so
section 9's band breach and these eight rows are two separate findings. **They are what decides the
intent clause of section 3.2**, and they are a direct consequence of the factor: the tool-free
Reviewer writes its review as prose (completion median 28.5 -> 90, p90 86 -> 171.1) and on eight rows
in 1,080 that prose reached the 512-token cap.

**`react_exhaustion` is zero, as the registration expected**: with no tool in the system the Reviewer
cannot loop on one. The declaration was armed and fired on no row.

**The revise route opens up.** 40 rows take it against B1's 7 and B1r's 12, and 3 of them hit the
revision limit against B1's 1 and B1r's 0. This is a behavioural consequence of the withdrawal worth
naming: the Reviewer that answers in prose says `REVISE` more often than the Reviewer that answers
through a tool round trip. It costs 3 extra contacts per revised row and it is **not** a defect --
the role graph, the revision cap and the Planner instruction are byte-identical.

### 7.1 Delivery shape

| signal | B1-notool | B1 | B1r | EFF-1 (for scale) |
| --- | ---: | ---: | ---: | ---: |
| Solver completions **tool-call-shaped as text** | **0 of 1,120** | 0 of 1,087 | 0 of 1,092 | **145 of 1,092** |
| Solver completions that do not load as JSON | 3 of 1,120 | 4 of 1,087 | 2 of 1,092 | -- |
| Reviewer completions tool-call-shaped as text | **0 of 1,120** | 1 of 2,171 | 1 of 2,180 | -- |
| Perception completions that load as JSON | 1,080 of 1,080 | 1,080 of 1,080 | 1,080 of 1,080 | -- |
| rows the official scorer could not parse | **4** | 4 | 2 | **137** |
| delivered answers starting with `{` | 1,080 | 1,080 | 1,080 | -- |
| delivered answers carrying a tool-call marker | **0** | 0 | 0 | -- |

**The failure class EFF-1 discovered cannot occur here, and did not.** Two rows became unparseable
against the B1 arm (`slurp:train:001679`, `slurp:train:005507`) and two became parseable
(`slurp:train:002081`, `slurp:train:003499`), a net of zero; two rows are unparseable on both sides.
On the 1,074 rows both sides parsed, the deltas are +0.81 pp SLU [-0.77, +2.30] and -0.28 pp intent
[-1.42, +0.81] -- a diagnostic, never a decision quantity.

Half the Reviewer's single answers now load as JSON (540 of 1,120) and half do not (580); in cell
B1r the Reviewer's 2,180 responses split into 1,088 tool calls and 1,092 review findings. That is a
change in the Reviewer's answer *shape*, recorded here and not attributed.

## 8. Cost and ceilings

| figure | B1-notool | B1 (base) | B1r | registered ceiling |
| --- | ---: | ---: | ---: | ---: |
| generation contacts (per row) | **4,432 (4.104)** | 5,425 (5.023) | 5,443 (5.040) | 11,880 (11) |
| repeated speech seconds | **12,687.05** | 15,494.60 | 15,542.42 | 33,930 |
| prompt / completion tokens | **35,728,582 / 266,131** | 49,388,949 / 255,524 | 49,678,439 / 257,424 | -- |
| prompt tokens per contact | 8,061.5 | 9,104.0 | 9,127.0 | -- |
| native task-contract tool calls | **0** | 1,084 | 1,088 | **0** |
| FIT receipts / endpoints | **4,432 / 17,728** | 5,425 / 21,700 | 5,443 / 21,772 | -- / 47,520 |
| GPU hours | **1.6108** (5,798.93 s) | 3.6819 | 3.8507 | 12.0 |
| generation wall seconds | **6,400.4** | 13,894.2 | 14,437.7 | -- |
| slot occupancy; utilisation; parked | 0.787; 77.72 %; 0.092 | 0.877; 91.01 %; 0.045 | 0.868; 87.09 %; 0.039 | -- |
| mean latency (s) | **4.548** | 8.982 | 9.213 | -- |
| official scoring jobs (seconds) | 1 (152.39) | 1 (166.22) | 1 (167.70) | 1 |

Every ceiling held with room: **37.3 %** of the contact ceiling (headroom 7,448 calls), 37.4 % of the
speech ceiling, **13.4 %** of the GPU-hour ceiling, 37.3 % of the FIT-endpoint ceiling, and the
task-contract ceiling of zero was met exactly. Run-cumulative over the single attempt of this run id:
**4,432 calls and 12,687.047750000034 repeated speech seconds**. Against the sealed B1 arm the
withdrawal costs **-993 contacts, -2,807.55 speech seconds, -13,660,367 prompt tokens (-27.7 %),
-1,084 tool calls and -2.0711 GPU hours**; against cell B1r, **-1,011 contacts, -2,855.37 speech
seconds, -13,949,857 prompt tokens (-28.1 %), +8,707 completion tokens, -1,088 tool calls and
-2.2399 GPU hours (0.418x)**.

### 8.1 Ledger closure inputs (the coordinator edits the ledger; this read does not)

* contacts **4,432**; repeated speech seconds **12687.047750000034**; native task-contract tool
  calls **0**; request-fit receipts **4,432** / FIT endpoints **17,728**; GPU hours **1.6108126**
  (5,798.925324678421 monitor active seconds); prompt tokens **35,728,582**; completion tokens
  **266,131**; wall **6,400.412614583969 s**; slot occupancy **0.7873**; utilisation **77.72 %**;
  parked **0.0921**; one official scoring job, **152.39 s**.
* **eight** `finite_completion` terminal dispositions, all retained and scored; **three**
  `revision_limit` dispositions; **zero** `react_exhaustion` visits; **zero**
  `planner_action_illegal` rows; **zero** aborts; **zero** recovery re-registrations.
* the smoke run `SAEA-SLURP-NATIVE-EXEMPLARS-K20-NOTOOL-SMOKE-4-V1`: 15 contacts, 40.72 speech
  seconds, 0 tool calls, one voided zero-contact attempt.

## 9. Per scenario (diagnostic under owner decision 17, never a gate)

### 9.1 B1-notool minus the sealed B1 arm (the gating contrast)

| Scenario | n | intent left | intent right | intent delta | intent CI95 | net harmed | flag | SLU left | SLU right | SLU delta |
| --- | ---: | ---: | ---: | ---: | --- | ---: | --- | ---: | ---: | ---: |
| alarm | 60 | 81.67 | 86.67 | +5.00 | [+0.00, +10.45] | -3 | no | 65.28 | 72.90 | +7.62 |
| audio | 60 | 78.33 | 78.33 | +0.00 | [-2.63, +8.57] | +0 | no | 60.35 | 61.94 | +1.59 |
| calendar | 60 | 78.33 | 80.00 | +1.67 | [-3.45, +8.16] | -1 | no | 64.16 | 63.96 | -0.20 |
| cooking | 60 | 88.33 | 85.00 | -3.33 | [-8.33, +0.00] | +2 | no | 64.74 | 64.49 | -0.25 |
| datetime | 60 | 88.33 | 88.33 | +0.00 | [+0.00, +0.00] | +0 | no | 69.80 | 70.77 | +0.96 |
| email | 60 | 83.33 | 86.67 | +3.33 | [+0.00, +7.69] | -2 | no | 57.93 | 54.41 | -3.52 |
| general | 60 | 43.33 | 41.67 | -1.67 | [-7.58, +3.70] | +1 | no | 20.41 | 17.78 | -2.63 |
| iot | 60 | 88.33 | 88.33 | +0.00 | [+0.00, +0.00] | +0 | no | 64.30 | 68.18 | +3.88 |
| lists | 60 | 85.00 | 81.67 | -3.33 | [-8.33, +0.00] | +2 | no | 53.45 | 50.55 | -2.89 |
| music | 60 | 78.33 | 70.00 | -8.33 | [-15.72, -1.75] | +5 | D17 BAND | 48.87 | 47.10 | -1.77 |
| news | 60 | 83.33 | 81.67 | -1.67 | [-5.77, +0.00] | +1 | no | 60.85 | 64.86 | +4.01 |
| play | 60 | 60.00 | 63.33 | +3.33 | [-7.69, +12.96] | -2 | no | 49.94 | 52.33 | +2.40 |
| qa | 60 | 75.00 | 78.33 | +3.33 | [+0.00, +8.62] | -2 | no | 58.16 | 57.77 | -0.39 |
| recommendation | 60 | 90.00 | 90.00 | +0.00 | [+0.00, +0.00] | +0 | no | 68.67 | 67.48 | -1.19 |
| social | 60 | 75.00 | 75.00 | +0.00 | [-6.56, +6.78] | +0 | no | 57.33 | 56.79 | -0.54 |
| takeaway | 60 | 85.00 | 85.00 | +0.00 | [-4.48, +5.17] | +0 | no | 60.43 | 60.66 | +0.23 |
| transport | 60 | 90.00 | 86.67 | -3.33 | [-10.17, +3.08] | +2 | no | 62.79 | 66.77 | +3.98 |
| weather | 60 | 91.67 | 93.33 | +1.67 | [+0.00, +5.56] | -1 | no | 73.93 | 75.85 | +1.92 |
| **equal-scenario mean** | 18 | | | **-0.19** | | | | | | **+0.73** |

**One scenario loses intent beyond the band on the gating contrast: `music`**, -8.33 pp with a CI95
upper bound of **-1.75**, on **+5 net harmed rows**, which also fires owner decision 17's flag. It
repeats against cell B1r (**-10.00 pp [-18.18, -3.23]**, +6 net harmed), so it is not an artefact of
which comparator is chosen. On pooled SLU `music` moves only -1.77, and no other scenario breaches
the band or fires the flag on either contrast. A 60-row stratum is the size at which cell B1r's own
null fired this same flag on `play`; this is recorded as the cell's one concentrated intent cost and
is the natural first place to look if the withdrawal is taken further.

### 9.2 B1-notool minus cell B1r (diagnostic)

| Scenario | n | intent left | intent right | intent delta | intent CI95 | net harmed | flag | SLU left | SLU right | SLU delta |
| --- | ---: | ---: | ---: | ---: | --- | ---: | --- | ---: | ---: | ---: |
| alarm | 60 | 86.67 | 86.67 | +0.00 | [+0.00, +0.00] | +0 | no | 68.67 | 72.90 | +4.23 |
| audio | 60 | 81.67 | 78.33 | -3.33 | [-8.57, +0.00] | +2 | no | 63.05 | 61.94 | -1.11 |
| calendar | 60 | 80.00 | 80.00 | +0.00 | [-4.69, +5.17] | +0 | no | 65.06 | 63.96 | -1.10 |
| cooking | 60 | 88.33 | 85.00 | -3.33 | [-8.47, +0.00] | +2 | no | 65.44 | 64.49 | -0.96 |
| datetime | 60 | 91.67 | 88.33 | -3.33 | [-7.94, +0.00] | +2 | no | 69.75 | 70.77 | +1.02 |
| email | 60 | 86.67 | 86.67 | +0.00 | [-5.08, +4.62] | +0 | no | 56.53 | 54.41 | -2.12 |
| general | 60 | 36.67 | 41.67 | +5.00 | [-3.51, +13.73] | -3 | no | 31.37 | 17.78 | -13.59 |
| iot | 60 | 86.67 | 88.33 | +1.67 | [+0.00, +5.36] | -1 | no | 68.76 | 68.18 | -0.57 |
| lists | 60 | 83.33 | 81.67 | -1.67 | [-5.36, +0.00] | +1 | no | 53.79 | 50.55 | -3.24 |
| music | 60 | 80.00 | 70.00 | -10.00 | [-18.18, -3.23] | +6 | D17 BAND | 47.67 | 47.10 | -0.58 |
| news | 60 | 80.00 | 81.67 | +1.67 | [+0.00, +5.77] | -1 | no | 62.57 | 64.86 | +2.29 |
| play | 60 | 51.67 | 63.33 | +11.67 | [+3.12, +21.82] | -7 | no | 52.94 | 52.33 | -0.60 |
| qa | 60 | 80.00 | 78.33 | -1.67 | [-7.70, +3.57] | +1 | no | 60.98 | 57.77 | -3.21 |
| recommendation | 60 | 91.67 | 90.00 | -1.67 | [-7.27, +3.70] | +1 | no | 67.78 | 67.48 | -0.30 |
| social | 60 | 75.00 | 75.00 | +0.00 | [-4.92, +5.00] | +0 | no | 58.89 | 56.79 | -2.10 |
| takeaway | 60 | 81.67 | 85.00 | +3.33 | [+0.00, +8.33] | -2 | no | 56.12 | 60.66 | +4.54 |
| transport | 60 | 86.67 | 86.67 | +0.00 | [-7.14, +6.10] | +0 | no | 62.75 | 66.77 | +4.02 |
| weather | 60 | 93.33 | 93.33 | +0.00 | [-4.84, +5.00] | +0 | no | 77.01 | 75.85 | -1.16 |
| **equal-scenario mean** | 18 | | | **-0.09** | | | | | | **-0.81** |

## 10. Companions (owner decisions 7 and 14; they decide nothing)

| view | B1 | **B1-notool** | B1r | anchor | delta (arm minus B1) | CI95 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| projection v3, pooled SLU | 62.6672 | **63.5973** | 63.9696 | 51.9946 | **+0.9301** | [-0.6843, +2.4785] |
| projection v3, intent | 81.7593 | **81.8519** | 82.3148 | 79.3519 | **+0.0926** | [-1.0223, +1.1988] |
| projection v3, span F1 | 52.6533 | **53.3265** | 54.2460 | 40.3025 | -- | -- |
| TRAIN symmetric, pooled SLU | 62.9742 | **63.9741** | 64.3497 | 52.0887 | **+0.9999** | [-0.6129, +2.5533] |
| TRAIN symmetric, pooled span F1 | 54.5080 | **55.3736** | 55.9959 | 41.3830 | **+0.8656** | -- |

Every registered comparator reproduces its published v3 and symmetric aggregates exactly, which is
what licenses reading the arm's beside them. Note, and do not act on it: under the fixed v3
post-processing the intent lower bound is **-1.0223** and would clear -1.2212. Owner decision 23
keeps the decision number **official and unprojected**, so this changes nothing; it is reported
because the registration requires v3 beside every official number.

## 11. The harness-admission consequence, and the decision that is not this read's to make

The entry this cell proposes, in the form `docs/receipts/harness-admission.json` records:

* **carrier** `slurp`; **row** `SAEA-SLURP-NATIVE-EXEMPLARS-K20-NOTOOL-V1`
  (`attempt-slurp-native-exemplars-k20-notool-train-fold-a-generation-v1`); **date** 2026-09-20.
* **module**: the Reviewer's toolkit `saea-tool-task-contract-v1` withdrawn (repair form 0-B): the
  `phase_tools` mapping is absent, so no role renders a tools array, the per-slot prefix is constant
  by construction and the Reviewer answers on its first contact.
* **switch**: table / class **`toolkits`**, key **`phase_tools`**; **off** = the B1 fragment's
  reviewer toolkit, present (`tool_schemas` one schema, `tool_choice` `auto` on the Reviewer);
  **on** = absent (no tools array anywhere, `tool_choice` `none` on every contact).
* **comparator**: the sealed B1 arm
  `SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-TRAIN-FOLD-A-RECOVERY-V2`, never re-flown or re-scored;
  both arms node-free; margins from cell B1r's own null, **1.2350 / 1.2212**, reproduced in this
  read; the arm carries the E13 and E22 declarations (8 finite-completion rows retained, 0
  react-exhaustion visits; B1 0 / 0).
* **status**: **not ADMITTED and not HARMFUL.** Primary official pooled SLU-F1 61.1394 -> 62.1295,
  **+0.9901 pp CI95 [-0.5924, +2.5038]**, non-inferior at -1.2350, equal-scenario +0.73; guard intent
  80.1852 -> 80.0000, **-0.1852 pp CI95 [-1.3334, +0.9076]**, lower bound 0.1122 pp short of -1.2212;
  saves / harms 23 / 25, McNemar p 0.885; one scenario (`music`) breaches the intent band.
* **cost**: 4,432 contacts (4.104 per row), 12,687.05 repeated speech seconds, **0** task-contract
  tool calls, **1.6108 GPU hours**, wall 6,400.4 s, slot occupancy 0.787, utilisation 77.72 %, parked
  0.092, 8 finite-completion rows retained.
* **not_admitted_for**: any test-split, Fold B or DEV-1000 claim; any claim that the withdrawal is
  score-neutral beyond this roster, geometry and session; any geometry or concurrency claim; any
  claim about the Reviewer's completion budget, which this cell did not move.

**The decision.** Owner decision 55 asks for 0-B to be judged on effect, and decision 53 makes a
NEUTRAL-or-better withdrawal the base of the knowledge-index cell. This read cannot supply NEUTRAL
under the rule as written. Three facts belong in front of whoever decides:

1. **There is no measured loss anywhere.** Point estimates: SLU **+0.99**, intent **-0.19**, scenario
   +0.09, action -0.28, span F1 +0.60, row-mean SLU +0.54. Against cell B1r the withdrawal reads
   **-0.10 SLU [-1.64, +1.33]** and **-0.09 intent [-1.39, +1.23]** -- indistinguishable from the
   null it was measured inside.
2. **The clause as written is not passable on intent by a pure null.** Cell B1r's own null, on the
   same roster and geometry, has an intent CI95 lower bound of -1.3145 and would also fail it
   (section 3.2).
3. **The miss has a named, fixable component.** Eight rows of 1,080 in which the tool-free Reviewer's
   prose review hit the 512-token completion cap decide the clause: they account for 0.0919 pp of the
   intent delta, and excluding them the lower bound is -1.2174 and clears. Raising the Reviewer's
   completion budget, or shortening its review contract, is a **new one-factor cell with its own
   registration** -- not an edit of this one, and not something this read is authorised to fly.

The program precedent that bears on the label is **cell B5e**, as owner decision 25 and the
2026-09-18 addendum left it: an intent point estimate of **-0.09 pp** whose CI95 lower bound
(**-1.5136**) crossed the margin -- and still crosses cell B1r's own **-1.2212** -- with no measured
loss, recorded as **NEUTRAL, non-inferiority not proven at the request-identical margin**. This
cell's crossing is smaller: **-1.3334 against -1.2212**, by 0.1122 pp, where B5e's was 0.2924. If the
coordinator and the owner apply that precedent here, the status word is NEUTRAL and the consequences
of decisions 53 and 56 follow; if they apply the preregistration's "iff" literally, the withdrawal
does not enter the plan on this evidence and the fallback path of decision 55 (repair form 0-A) or a
Reviewer-budget cell is the next move. **This read records the numbers and refuses to choose for
them.** No receipt is written, no default plan is edited, and no harness-admission row is added by
this document.

**An efficiency cell does not count toward owner decision 30's headroom trigger** and does not extend
the NEUTRAL/HARMFUL streak recorded in `docs/results/2026-09-20-slurp-v2-provisional-lock-v1.md`;
this result is not evidence about the development bar, and **no bar claim is made**: the arm's
62.13 / 80.00 is stated as a fact beside the sealed B1 arm's 61.14 / 80.19 and as nothing else.

## 12. Where this read departs from the inherited recipe text

The recipe `analysis-recipe-v1.json` was generated from the EFF-1 package and carries clauses that
describe the *opposite* factor. The preregistration governs, and each departure is recorded in
`recipe_inheritance_notes` of `score-contrasts.json`:

1. **"THE CONSTANCY TABLE ... `distinct_tool_schemas_sha256 == 1`"** -- `tool_schema_rendering` is
   item E17 and is not armed here, so no arm seals that block. Reported instead: zero tool schemas
   and `tool_choice` `none` on every one of the arm's 4,432 requests (section 6).
2. **"the tools array is added to the Perception request"** -- the direction is reversed. Reported
   instead: the perception, solver and planner requests are byte-identical to B1r's and the
   **Reviewer** request is the one that differs, by the absent toolkit (section 6.1).
3. **"NATIVE TASK-CONTRACT CALL COUNT against the anchor's realized 1,082"** -- the registered
   ceiling for this cell is **zero**. Reported instead: 0 calls against B1's 1,084 and B1r's 1,088.
4. **`output.files: throughput-tables.json`** -- the spawn brief names the same file
   `efficiency.json`. Both names are written with identical bytes.
5. **`arms.arm.*_sha256: PENDING_SEAL`** -- the recipe was registered before the flight sealed; the
   three sealed digests are carried in section 1 and every one was re-derived by hashing the files.

One further departure is this read's own and is not inherited: the registered wire claim is
unfalsifiable as written, because `history[*].source_response_sha256` and the contact receipt's
`response_sha256` are per-flight bookkeeping. Section 6.1 names the six excluded fields, proves why,
and states the claim that is checkable.

## 13. What is not claimed

* **No superiority, generalization, paper-scale or held-out claim.** TRAIN Fold A is an exposed
  discovery roster and these are **development numbers** (owner decision 28); they are never compared
  with a published TEST baseline. Fold B, DEV-1000 and the test split stay untouched and unread. The
  13,078-row projection is a projection of *this flight's rate*, not an authorisation to read any
  split.
* **No claim that the withdrawal is score-neutral in general** -- only that on this roster, this
  geometry and this session it shows no measured loss and a 0.08 pp shortfall of point estimate
  against a rule its own null would also fail.
* **No geometry or concurrency claim**, although slot occupancy and the parked fraction both moved;
  and no claim about the Reviewer's completion budget, the revision cap or the review contract, none
  of which this cell touched.
* **Nothing is re-decided about cell B1, cell B1r, cell B5e or cell EFF-1.** The comparators were
  never re-flown and never re-scored; EFF-1 and B4b appear only as efficiency references.
* **No anchor-base or plan-base withdrawal cell is registered here** -- section 4 states the
  decision-56 clause and the coordinator records it.

## 14. Files

All under `SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-B1-NOTOOL-PAIRED-ANALYSIS-V1`:

| file | sha256 | what it carries |
| --- | --- | --- |
| `score-contrasts.json` | `7a7bbae7d354e99d88cba3827ce79e45e98e6d5442505abb37b4d553ab57fd9e` | population, STOP condition, the own-null reproduction, every contrast, the band, the decision block, the v3 and symmetric views, every input and authority digest |
| `efficiency.json` | `94c3431be004966a51ab7d1d320732aa40c60a41c20f67a913ea0651983fe8a7` | the server-log join, per position, per role, the cost block, the two references and the projected read (the recipe's `throughput-tables.json`) |
| `throughput-tables.json` | `94c3431be004966a51ab7d1d320732aa40c60a41c20f67a913ea0651983fe8a7` | the recipe's name for the same bytes |
| `per-scenario-tables.json` | `bef05a81dcf85687a68978fdd5c417e5d1376adbd9f8a5a13b0ad66a83768d7f` | all 18 scenarios in both weightings, on all four contrasts, plus the intent band |
| `structural.json` | `1347a772601ccb027ed25aa850cdb1d4df9fa572cac7125a3d1210acebeb0303` | the tool surface, request identity, trajectory, dispositions and delivery shape |
| `flight-diagnostics.json` | `e48ae010a416119f0f62e58245aa11cd19758a9ede319a32c23024a99c7178dd` | the same diagnostics as emitted by the driver |
| `README.md` | `413e5c7a477cfedb28ce7ffdac8934d844021547285810e5af2b50bb0cd6a03f` | the read's own summary, generated by the driver |
| `b1nt_paired_read.py` | `b41f747a4ed39ad3cdd590e8888ed9810774f22290078267fee3a04f94f54a44` | the driver, a copy of which is sealed beside its outputs |
| `v3/`, `symmetric/`, `outputs-copies/` | -- | the copies of each arm's sealed outputs and the two model-free companion scorings over them |

Every input the read opened, with its digest, and every authority document with its digest, are
listed in `score-contrasts.json` under `inputs`, `authority` and `implementation`. The serving
session's `server.log` is deliberately **not** pinned by digest: it is still being appended by later
flights, and only the release records inside this flight's own sealed contact window were selected.
