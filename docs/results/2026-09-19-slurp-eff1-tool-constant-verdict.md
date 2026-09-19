# HARMFUL -- efficiency cell EFF-1, constant native tool-schema rendering (item E17, lever L1), on the sealed dual-store anchor

**HARMFUL.** Holding the native tool-schema rendering constant across the five role contacts of a row
does exactly what it was built to do to cost -- **prefilled tokens per row fall from the 26,197 of the
B4b reference to 10,127, GPU hours per 1,080 rows fall from the sealed anchor's 3.388 to 1.843, and
the projected 13,078-row test read falls from 41.0 h to 22.3 h** -- and it breaks the delivered answer
on 137 rows. Both registered guards show a **measured loss**: official pooled SLU-F1
**-4.39 pp, CI95 [-6.69, -2.17]** and intent **-9.17 pp, CI95 [-11.64, -6.79]**, each with its point
estimate below its own-null margin *and* its CI95 upper bound below zero. Under owner decision 25 that
is HARMFUL on the first clause read.

The loss is root-caused to a named component. On the **938 rows where both arms delivered an answer the
official scorer could parse**, the paired deltas are **+0.030 pp SLU [-1.64, +1.63]** and **+0.213 pp
intent [-1.09, +1.47]** -- zero, to a fraction of a point. The whole measured loss is the **Solver's
delivery shape**: with the Reviewer's `tools` array rendered into its system message and its
`tool_choice` still `"none"` -- so llama.cpp installs neither the tool-call grammar nor the tool parser
for it -- the frozen core answered with a **tool-call-shaped string** on **145 of 1,092** Solver
contacts (the sealed anchor: **0**). That string is delivered verbatim as the row's answer, the
official scorer cannot parse it, and the row scores zero on every metric.

`native_episode.tool_schema_rendering: "constant"` therefore **enters no default plan**, the per-role
rendering stays the SLURP default, and **lever L2 (drop the Planner) must not now be credited with
L1's gain**. The measured prefill saving is real, is reported in full below, and is **not purchasable
at this delivery shape**.

**An efficiency cell does not count toward owner decision 30's headroom trigger.** This cell consumed a
flight slot and a share of the GPU budget; it did not consume a headroom attempt, and this result is
not evidence about the bar. **This was not a bar attempt**: the official pooled SLU-F1 the arm reaches,
44.14 / 68.80, is stated as a fact beside the sealed anchor's 48.53 / 77.96 and is claimed as nothing
else. Nothing here is replicated.

Date: 2026-09-19. Model-free read: **zero model, tokenizer, encoder, ASR, server and paid-API
contacts**. The one official score was produced by the flight's own campaign at finalize; this read
invoked only the model-free projection-v3 and TRAIN symmetric scorers, over **copies** of the sealed
outputs written under its own analysis directory. The resident llama-server was never started, stopped
or queried -- its `server.log` and `monitor.jsonl` were read as files. No sealed artefact and no
repository file under `SPEECHRL_DATA_DIR/runs` or `/attempts` was written, moved or modified.

Authority, applied unchanged:
[`docs/readiness/2026-09-19-slurp-eff1-tool-constant-v1-preregistration.md`](../readiness/2026-09-19-slurp-eff1-tool-constant-v1-preregistration.md)
and its package
[`docs/readiness/2026-09-19-slurp-eff1-tool-constant-v1/`](../readiness/2026-09-19-slurp-eff1-tool-constant-v1/README.md)
(`analysis-recipe-v1.json`, `protocol-registered-v1.json`); owner decisions 41, 38, 30, 28, 25, 23, 22,
17, 14 and 7 in
[`docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md`](../readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md);
the own-null margins of
[`docs/results/2026-09-17-slurp-b0-review-off-redecision-v2.md`](2026-09-17-slurp-b0-review-off-redecision-v2.md);
the mechanism and its receipt in
[`docs/superpowers/specs/2026-09-19-e17-constant-tool-rendering-design.md`](../superpowers/specs/2026-09-19-e17-constant-tool-rendering-design.md);
the cost model, the B4b per-position reference and the server-log join method in
[`docs/results/2026-09-19-slurp-throughput-root-cause-v1.md`](2026-09-19-slurp-throughput-root-cause-v1.md);
the 58-minute in-flight window this read reconciles against in
[`docs/results/2026-09-19-slurp-serving-geometry-and-degradation-v1.md`](2026-09-19-slurp-serving-geometry-and-degradation-v1.md).

---

## 1. What flew, and the STOP condition

Run `SAEA-SLURP-NATIVE-TOOL-CONSTANT-ANCHOR-TRAIN-FOLD-A-V1`, attempt
`attempt-slurp-native-tool-constant-anchor-train-fold-a-generation-v1`, cell
`slurp-native-tool-constant-anchor-train-fold-a-v1`. The four-row form smoke
`SAEA-SLURP-NATIVE-TOOL-CONSTANT-ANCHOR-SMOKE-4-V1` sealed first, as registered.

Every sealed fact was **re-derived**, not assumed:

| fact | verified value |
|---|---|
| manifest status / attempt state | `COMPLETED` / `FINALIZED` |
| study commit | `711bc6c4904a066b94f511a0181959d5042ae044` |
| `study_repo_dirt` | `[]` (empty) |
| run-manifest sha256 | `e78449249c8f7400c24f320f3908c955c550e713be196350dfab438d63f1f5e6` |
| scores sha256 | `fcccb476db1f1189989bb8f9dc0bb2abeb32504869f8bf623ef741328498b153` |
| outputs sha256 | `769af62edb82ceb040872ccfeb27f28c22af61d58bf1208275052d7c1897b9b9` |
| composed config hash | `02b13593d920d6dd93977cf608da8812cb86ddaae3a1222b0287fe50f7507602` (registered) |
| protocol hash | `dc357b14d608d1fd19ea1a879c3fde59809e0af01a0726c2131eabd513af54ab` (registered) |
| split identity / role / rows | `61b0f062...5398b6` / `discovery` / 1,080 distinct ids |
| execution profile | `bounded-discovery-probe` |
| cost | 5,293 contacts; 15,111.56606250007 repeated speech seconds; 44,100,253 prompt tokens; 233,956 completion tokens; 939 tool calls |
| flight | wall 6,913.586 s; slot occupancy 0.8911; 1.8433 GPU hours; utilisation 85.06 %; parked 0.0380 |
| fit | 5,293 `*.request-fit.json` receipts; prompt-budget decision `ALLOW` against the live 24,576-token slot |
| scoring | one official score job at finalize |

**STOP condition, all four clauses pass.**

1. The sealed anchor reproduces its registered aggregates from its own score artefact to better than a
   hundredth of a point: **48.5336** against the registered 48.53 and **77.9630** against 77.96. Its
   three artifact hashes were re-derived by hashing the files and match
   (`7360876322488e5fda689fcafda00e90da2ebf559e5a35e635c550f940202b47`,
   `049ac230e536bc6c8fe45bc847756ba486c4904e9c7602c698157f78d70c0152`,
   `d87d71e8fa0fe93b45d5c6817ba125b016d8d91f44a14309171dd0f3a64270d8`). As a cross-check its other
   official fields and the released direct anchor's five fields also reproduce the sealed B8b/B7a
   values exactly.
2. Row accounting: **1,080 in, 1,080 out on both sides**; the manifest split ids, the roster and the
   scored rows are the same 1,080 ids; no row dropped, no `sample_id` invented.
3. Roster, split identity and strata identical on both sides: 18 scenarios of 60, 125 speaker
   clusters, 523 headset and 557 far-field rows, roster
   `1fe7908c31396774d7535fdf37bd791762215c324999d66ed7beb9e7b2f9033d`.
4. The sealed tool-schema-rendering receipt reports `distinct_tool_schemas_sha256 == 1` on **every one
   of the 1,080 rows**.

**The comparator's honest gap, restated.** The sealed anchor attempt has **no `flight-receipts.json`**.
Its GPU hours come from its own **session-attach-receipt monitor summary** (12,196.6499 active
seconds = 3.3880 GPU-h), which re-derives the 3.388 the registration read from its exposure-ledger
row; its wall clock can only
be read as its attach contact window (12,473.54 s). It has **no slot occupancy, no `run_phases` wall
clock and no per-position prefill split on file**, so the per-position reference below is the **B4b
replicate** -- a different configuration on the same geometry -- and every B4b column is labelled a
REFERENCE, never an anchor measurement.

---

## 2. The efficiency read -- the deliverable, reported regardless of the verdict

**Join quality: 100.00 %.** `n_tokens - generated + 1` equals the client's `usage.prompt_tokens` on
**5,293 of 5,293** joined contacts, and the four per-slot client sequences match the four per-slot
server task sequences one for one (1,309 / 1,347 / 1,340 / 1,297). Every per-role and per-position
figure below is therefore a **measurement**, not an estimate. The window is the flight's own sealed
contact window, 2026-09-19T14:40:24.306Z to 16:35:37.892Z, inside segment 6 of the resident session's
`server.log`; throughput is counted from the server's own `slot release` records, never from
`monitor.jsonl`'s `requests_total`. The decision-45 report's warning about that counter is confirmed
again here: the flight's own monitor summary records `requests_delta` **2,287** where the server
completed **5,293** requests -- a 57 % undercount. The monitor is used only for what it samples
directly: GPU utilisation, power, busy slots and active seconds.

### 2.1 Headline

| quantity | EFF-1 (measured) | sealed anchor (its own) | B4b REFERENCE |
|---|---:|---:|---:|
| **prefilled tokens / row** | **10,127.2** | not on file | 26,197 |
| client prompt tokens / row | 40,833.6 | 42,591.0 | 45,911 |
| client prompt tokens / contact | 8,331.9 | 8,491.5 | -- |
| **GPU hours / 1,080 rows** | **1.8433** | **3.3880** | 3.837 |
| wall seconds / row | 6.40 | 11.55 (attach window) | 12.79 |
| contacts / row | 4.901 | 5.016 | 5.00 |
| **contacts / minute** | **45.94** | 26.06 (attach window) | -- |
| cache hit share | 75.20 % | not on file | 42.9 % |
| speech-packet decodes / row | 0.996 | not on file | ~3.0 |
| aggregate prefill tok/s | 1,582 | not on file | 2,048 |
| aggregate decode tok/s | 33.84 | not on file | 18.7 |
| seconds per million prefilled tokens | 632.1 | not on file | 488-536 (four sealed runs) |
| slot occupancy | 0.891 | not on file | 0.881 |
| mean utilisation | 85.06 % | 88.73 % | 90.1 % |
| parked fraction | 3.80 % | 2.19 % | 1.8 % |
| truncations | 0 | not on file (its fit receipts all pass) | 0 |

**Prefilled tokens per row: 26,197 -> 10,127.2, a 61.3 % reduction** -- larger than lever L1's
predicted 13,065 (-50.1 %), as the registration said the character-proxy bound was conservative.
**GPU hours per 1,080 rows: 3.388 -> 1.843, a 45.6 % reduction**, 0.544x the anchor. **Contacts per
minute: 26.06 -> 45.94, 1.76x.**

**The one number that was expected to rise, and what actually happened.** The registration expected
client-visible prompt tokens per row to **rise**, because perception, solver and planner each gain the
tools block, and warned that quoting that rise as a regression would be reading the wrong number. At
the one position where a like-for-like comparison exists -- **Perception**, whose request is fully
determined by configuration -- the rise is exactly as expected: **median 3,593 -> 3,727 (+134 tokens)**
and **+144,720 tokens in total (+3.7 %)**. Flight-wide, however, prompt tokens per row **fell** (42,591
-> 40,834) for an unrelated reason: the flight made **124 fewer contacts** because 137 rows lost their
second Reviewer contact (section 4). Neither movement is the cost; the cost is prefill.

### 2.2 Per position

| position | role | rendered tools | prompt med | prefilled med | cached | generated med | packet re-decode | prefilled / row | share of row prefill | B4b REFERENCE prefilled/row | B4b REFERENCE cached |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | perception | 1 | 3,727 | 1,368 | 63.3 % | 98 | 99.6 % | 1,367.8 | 13.5 % | 1,374 | 61.8 % |
| 1 | solver | 1 | 8,898 | 5,420 | 40.2 % | 23 | 0.0 % | 5,200.4 | **51.4 %** | 6,258 | 36.1 % |
| 2 | reviewer #1 | 1 | 8,874 | **235** | **97.3 %** | 22 | **0.0 %** | **235.3** | **2.3 %** | 7,505 | 23.6 % |
| 3 | reviewer #2 (n=934) | 1 | 10,740 | 1,757 | 83.3 % | 69 | 0.0 % | 1,519.5 | 15.0 % | 1,859 | 83.5 % |
| 3 | planner (n=144) | 1 | 8,121 | 200 | 97.5 % | 2 | 0.0 % | 27.0 | 0.3 % | -- | -- |
| 4 | planner (n=934) | 1 | 10,853 | **2,023** | **81.0 %** | 2 | **0.0 %** | **1,751.8** | **17.3 %** | 9,109 | 19.8 % |

(Beyond the rows above, positions 4 to 8 carry the revision tail -- **41 contacts in all**, 12 solver,
17 reviewer and 12 planner, together **0.3 %** of row prefill. The table plus the tail accounts for all
5,293 contacts. The "packet re-decode" column is the share of contacts at that position
on which llama.cpp ran `process_mtmd` at all; at position 0 that is the row's **first and only**
decode, not a re-decode, which is the whole point.)

**The mechanism reached the server, exactly as designed.** The two transitions the throughput report
identified as the whole problem are repaired: the **first Reviewer contact falls from 7,505 to 235
prefilled tokens per row (-96.9 %)** and its cached share rises from 23.6 % to 97.3 %; the **Planner
falls from 9,109 to 1,752 (-80.8 %)** with cached rising from 19.8 % to 81.0 %. The speech packet is
now decoded **0.996 times per row** -- once, at Perception -- against roughly three times per row
before; the packet re-decode share over all contacts is **20.3 %**. Positions 2 and 4 carried 63.5 % of
all prefill before; they carry **19.6 %** now, and the **Solver is the new dominant line item at
51.4 %**, which is the natural next target and is *not* decided here.

**The flight is no longer prefill-bound.** Seconds per million prefilled tokens rose from the 488-536
measured across four sealed pre-L1 runs to **632.1**; aggregate prefill fell off its 2,048 tok/s
ceiling to **1,582** while aggregate decode rose from 18.7 to **33.84** tok/s. That is the signature of
two-resource contention, not of a single bound -- the same conclusion the decision-45 geometry report
reached from its own window.

### 2.3 Reconciliation with the decision-45 geometry report

The geometry report measured this arm **while it was in flight**, from the serving session's
`server.log`, over a **58-minute window**; its own scope note calls those numbers a provisional
observation. That window is the **first 3,481 seconds of a 6,914-second flight**. Reading the same
prefix from the sealed receipts reproduces it almost exactly, and the whole-flight numbers differ only
because the flight slowed as it ran:

| quantity | geometry report (58-min window, in flight) | this read, same 3,481 s prefix | this read, whole flight (sealed) |
|---|---:|---:|---:|
| duration s | 3,481 | 3,491 | 6,914 |
| contacts | 2,912 | **2,912** | 5,293 |
| contacts / minute | 50.20 | **50.04** | **45.94** |
| prefilled / contact | 1,972 | **1,971** | 2,066 |
| cached share | 75.3 % | **75.3 %** | 75.2 % |
| aggregate prefill tok/s | 1,650 | 1,644 | 1,582 |
| aggregate decode tok/s | 36.62 | 36.55 | 33.84 |
| packet re-decode share | 20.4 % | 20.4 % | 20.3 % |
| latency p50 / p90 / p99 s | 3.54 / 9.31 / 12.97 | 3.66 / 9.13 / 12.68 | 3.90 / 9.43 / 13.33 |
| prefilled / row | 9,906 | -- | **10,127** |
| GPU-h / 1,080 | 1.79 | -- | **1.8433** |
| 13,078-row read | 21.7 h | -- | **22.3 h** |

Denominators, stated so the columns are comparable: the two window columns divide by the measured
launch-to-release span; the whole-flight column divides by the flight receipt's own
`run_phases.wall_seconds` (6,913.586 s), which additionally carries 6.98 s of client initialisation
and the seal. On the span denominator (6,641.76 s) the whole flight reads 47.82 contacts/min, 1,647
aggregate prefill tok/s and 35.22 decode tok/s.

**Where they differ and why.** (a) The report's contact count and rate are reproduced to within
0.3 %; the join method is the same and the small residue is window-edge alignment. (b) The whole-flight
rate is **45.94** against the window's 50.20 because throughput declines as the flight runs -- the
first 600 s measure **52.70** contacts/min, the first 3,481 s 50.04 and the whole flight 47.82 on the
same launch-to-release denominator. The report saw the same decline inside its own window (53.34 for
its first 15 minutes, 48.14 for its last 30). (c) The report's **9,906 prefilled per row** is its window's
prefilled-per-request times five contacts per row; the sealed whole-flight figure is **10,127.2**,
prefilled tokens summed over the flight divided by 1,080. (d) The report's **1.79 GPU-h** is a
projection from its window's rate; **1.8433** is the flight's own serving-monitor `active_seconds`
over its lease window, which is the registered basis ("read from the serving monitor, never a
wall-clock guess"). The report's **21.7 h** test read becomes **22.3 h** for the same reason. All four
differences are window scope, not disagreement.

The coordinator's ten-minute sample of **53.5 contacts/min against 23.5-24.2 on the per-role arms** is
**confirmed with a correction**: the arm's first 600 seconds measure **52.70** contacts/min, and the
honest per-role comparators are the NCP-L1 anchor's **24.78** (geometry report) and this cell's own
comparator, the sealed dual-store anchor, at **26.06** over its attach window. The whole-flight rate is
**45.94**, i.e. **1.76x** the comparator rather than 2.2x.

### 2.4 Projected test read (13,078 rows)

| basis | GPU-h / 1,080 | 13,078-row read |
|---|---:|---:|
| **EFF-1 measured (serving monitor)** | **1.8433** | **22.3 h** |
| EFF-1 wall-clock basis | -- | 23.3 h |
| geometry report's in-flight projection | 1.79 | 21.7 h |
| lever L1 prediction | 1.92 | 23.2 h |
| sealed dual-store anchor | 3.3880 | 41.0 h |
| throughput report baseline (admitted B4b system) | 3.837 | 46.5 h |

The measured saving **beats** lever L1's own prediction on both quantities -- 10,127 prefilled tokens
per row against a predicted 13,065, and 1.8433 GPU-h against a predicted 1.92 -- exactly as the
registration said the character-proxy bound would be conservative. The coordinator's **12 GPU-hour
target for the test read is not reached by L1 alone**, and on this verdict it is not reached by L1 at
all.

### 2.5 Cost against the registered ceilings

| item | realized | ceiling | anchor's realized |
|---|---:|---:|---:|
| generation contacts (run-cumulative, one attempt) | 5,293 | 11,880 | 5,417 |
| repeated speech seconds | 15,111.566 | 33,930 | 15,459.765 |
| FIT endpoints | 21,172 (5,293 receipts x 4) | 47,520 | 21,668 |
| native task-contract calls | 939 | 6,480 | 1,082 |
| GPU hours | 1.8433 | 12.0 | 3.3880 |
| official scoring jobs | 1 | 1 | 1 |
| paid API | 0 | 0 | 0 |

Every ceiling holds with wide headroom. **Prompt fit**: all 5,293 `*.request-fit.json` receipts report
`every_request_fits = true`, the minimum margin is **9,087 tokens** and the maximum required window is
**15,489 tokens** against the live 24,576-token slot (the anchor: 9,194 and 15,382). **Zero
truncations** on the server side. The flight ran under the repaired `_assess_prompt_budget` gate, which
reads the live per-slot limit -- the preflight records `slot_limit_tokens: 24576` and decision `ALLOW`
for every phase.

Ledger closure inputs for the coordinator (the ledger is **not** edited by this read): **5,293
contacts / 15,111.56606250007 repeated speech seconds / 5,293 request-fit receipts (21,172 endpoints) /
939 tool calls / 1.8433 GPU hours**, attempt `FINALIZED`, one official score job.

---

## 3. Constancy, authority and the wire check

**The constancy claim holds exactly.** All 1,080 rows carry a `saea-native-tool-schema-rendering-v1`
block with `mode: "constant"` and `rendered_tool_names: ["saea-tool-task-contract-v1"]`; the blocks
carry 5,293 contact rows, one per realized contact; **`distinct_tool_schemas_sha256 == 1` on every
row**, and there is exactly **one** distinct `tool_schemas` digest over the entire flight.

**Rendering moved; authority did not.**

| role | authority_tool_names (EFF-1) | rendered_tool_names (EFF-1) | `tool_choice` EFF-1 | `tool_choice` anchor | rendered arrays EFF-1 / anchor |
|---|---|---|---|---|---|
| perception | `[]` x 1,080 | `[task-contract]` x 1,080 | `none` x 1,080 | `none` x 1,080 | 1 / 0 |
| solver | `[]` x 1,092 | `[task-contract]` x 1,092 | `none` x 1,092 | `none` x 1,085 | 1 / 0 |
| reviewer | `[task-contract]` x 2,031 | `[task-contract]` x 2,031 | `auto` x 2,031 | `auto` x 2,167 | 1 / 1 |
| planner | `[]` x 1,090 | `[task-contract]` x 1,090 | `none` x 1,090 | `none` x 1,085 | 1 / 0 |

Every role's authority set and every role's `tool_choice` are identical to the anchor's. **939 native
task-contract calls, all from the Reviewer; zero tool calls from a role holding no authority; zero
`_RoleAuthorityRail` refusals anywhere in the sealed trace.** Showing three more roles the tool
definitions produced no illegal *call* at all -- the damage it did took a different route (section 4).

**Wire check.** The model-facing payload is the whole request minus exactly three bookkeeping fields:
`request_id` (the flight counter), every `evidence_provenance` `relpath` (`rails-message/flight-<n>/k`,
the same counter -- each entry's `lock_key` and `sha256` stay compared) and `decoding_params.id_slot`.
`history`, `task_instruction`, `supplied_evidence`, `tool_schemas`, `max_tokens`, `response_format`,
`parallel_tool_calls`, `seed`, `temperature`, `tool_choice`, `speech_feature_parts`,
`speech_packet_sha256`, `speech_ref`, `media_relpath`, `key_representation_id`, `matcher_policy_id`,
`query_source`, `mmproj_loaded`, `sample_rate_hz` and `audio_seconds` are all inside the compared
digest.

* **Claim (b) holds on every checkable contact.** On all **1,080 Perception requests** -- the only
  position whose request is fully determined by configuration -- the payload **minus the
  `tool_schemas` key is byte-identical to the anchor's**, and `tool_choice` is still `"none"`. Zero of
  the 1,080 are identical *including* the key, which is the factor doing precisely what it declares.
* **Claim (a), the Reviewer byte-identity claim, is NOT EVALUABLE on this flight, and that is
  structural rather than a failure.** Because the factor changes the Perception request, the Perception
  **response differs from the anchor's on all 1,080 rows**; every later request of a row inherits that
  difference. Measured unconditionally, **0 of 1,080** position-2 Reviewer requests are model-facing
  identical to the anchor's. The registration anticipated this when it said no `request-bytes-identical`
  falsifier can exist for an episode-class rendering key. **Zero violations were found**, because no
  in-sync Reviewer contact exists to violate it.
* **A note the coordinator should reconcile.** The same pattern holds on all four rows of the sealed
  four-row smoke: no request digest at any position matches the anchor's, and one of the four rows
  already shows the shortened four-contact trajectory of section 4. Smoke acceptance clause 3 as
  literally written ("each Reviewer `MODEL_REQUEST` is byte-identical to the sealed anchor's request at
  the same position of the same sample id") is **unsatisfiable by construction** once the Perception
  request changes, and its clause 6 -- the cache evidence -- is the clause that actually carried the
  smoke.

---

## 4. Root cause, named: the Solver's delivery shape

The registration asked what three more roles would do with the tool definitions and said the
neutrality guard existed to find out. This is the answer, and it is a count, not an interpretation.

| signal | EFF-1 | sealed anchor |
|---|---:|---:|
| Solver responses **tool-call-shaped as text** (`<tool_call>...`) | **145 of 1,092** | **0 of 1,085** |
| Solver responses that do not load as JSON | 146 of 1,092 | 7 of 1,085 |
| Perception responses that load as JSON | 1,080 of 1,080 | 1,080 of 1,080 |
| Reviewer responses tool-call-shaped as text | 0 of 2,031 | 0 of 2,167 |
| rows the official scorer could not parse | **137** | **7** |
| of those, carrying `<tool_call>` / `"name"` / `"arguments"` / `saea-tool-task-contract` | **136** | 0 |
| of those, whose Reviewer ran only once | **136** | -- |
| rows with a single Reviewer contact | **137** | 3 |
| contacts-per-row histogram | 3:2, **4:135**, 5:931, 7:7, 8:2, 9:3 | 4:3, 5:1,072, 9:5 |

**The chain.** The Solver holds no tool authority, so its `tool_choice` stays `"none"` and llama.cpp
installs for it neither the tool-call grammar nor the tool parser -- exactly as the E17 design records.
Under `"constant"` the Qwen3-Omni template nevertheless renders the Reviewer's `tools` array **inside
the Solver's system message**. On 145 of 1,092 Solver contacts the frozen core answered with a
tool-call-shaped **string** carrying `<tool_call>`, `"name"`, `"arguments"` and
`saea-tool-task-contract`. Nothing parses it into a `tool_calls` envelope, so it is simply the
Solver's draft. On those rows the Reviewer then made a **single** contact and emitted **no**
task-contract call (939 flight-wide against the anchor's 1,082), the episode went straight to the
Planner -- **135 rows ran four contacts instead of five, and 137 rows saw the Reviewer once** -- and
the tool-call string was **delivered verbatim as the row's answer** (the 137 unparseable deliveries
have a median length of 80 characters and only one of them even starts with `{`). The official scorer
cannot parse it, and **all 137 rows score zero on every metric** -- verified directly against the
sealed per-sample block.

**The arithmetic closes.** 137 unparseable rows out of 1,080 is 12.7 % of the roster scoring zero;
that alone accounts for the entire -9.17 pp of intent and -4.39 pp of pooled SLU-F1:

| population | rows | SLU anchor | SLU EFF-1 | SLU delta | CI95 | intent anchor | intent EFF-1 | intent delta | CI95 |
|---|---:|---:|---:|---:|---|---:|---:|---:|---|
| **all rows (the registered number)** | **1,080** | 48.534 | 44.141 | **-4.393** | [-6.689, -2.173] | 77.963 | 68.796 | **-9.167** | [-11.640, -6.789] |
| rows both sides parsed (**diagnostic**) | 938 | 47.529 | 47.559 | +0.030 | [-1.644, +1.632] | 78.465 | 78.678 | +0.213 | [-1.091, +1.467] |

The restricted row is a **diagnostic only**: restricting to rows both sides could parse conditions on
an outcome of the factor and is never a decision quantity. **No row is filtered from the verdict.** But
it is what licenses the root-cause statement: where delivery survived, constant rendering changed the
answer by nothing measurable. 135 rows became unparseable and 5 became parseable; 2 were unparseable on
both sides. The newly unparseable rows are spread across all 18 scenarios (worst: audio 23, play 15,
datetime 10, music 10).

---

## 5. The official contrast and the registered decision clauses

`delta = EFF-1 minus the sealed anchor`, percentage points; negative is worse. Paired whole-speaker
cluster bootstrap, **10,000 draws, seed 20260915**, percentile intervals from the same retained
replicate sequence; the scenario-stratified row bootstrap is the registered sensitivity.

| metric | anchor | EFF-1 | delta pp | speaker CI95 | speaker CI90 | scenario-strat CI95 | equal-scenario delta |
|---|---:|---:|---:|---|---|---|---:|
| **official pooled SLU-F1** | 48.53 | 44.14 | **-4.39** | **[-6.69, -2.17]** | [-6.31, -2.55] | [-6.33, -2.48] | -5.23 |
| **intent (scenario+action)** | 77.96 | 68.80 | **-9.17** | **[-11.64, -6.79]** | [-11.18, -7.14] | [-11.30, -7.04] | -9.17 |
| scenario accuracy | 84.81 | 74.26 | -10.56 | [-13.25, -7.92] | [-12.84, -8.33] | [-12.78, -8.52] | -10.56 |
| action accuracy | 79.26 | 70.00 | -9.26 | [-11.71, -7.02] | [-11.30, -7.34] | [-11.39, -7.22] | -9.26 |
| official pooled span F1 | 29.50 | 25.41 | -4.09 | [-6.77, -1.50] | [-6.28, -1.94] | [-6.36, -1.82] | -4.24 |
| per-row mean exact slot F1 | 19.02 | 14.93 | -4.09 | [-5.81, -2.50] | [-5.50, -2.74] | [-5.63, -2.59] | -4.09 |
| per-row mean official SLU-F1 | 30.29 | 24.69 | -5.61 | [-7.49, -3.80] | [-7.17, -4.08] | [-7.19, -4.07] | -5.61 |

| per-row metric | saves | harms | ties | exact two-sided McNemar p |
|---|---:|---:|---:|---:|
| intent (scenario+action) | 27 | 126 | 927 | 1.72e-16 |
| scenario accuracy | 21 | 135 | 924 | 1.41e-21 |
| action accuracy | 25 | 125 | 930 | 3.41e-17 |
| per-row exact slot F1 | 32 | 86 | 962 | 6.91e-07 |
| per-row official SLU-F1 | 67 | 152 | 861 | 9.06e-09 |

**The registered clauses, read in the registered order.**

| guard | delta pp | CI95 | margin -h | point below -h? | CI95 upper below 0? | CI95 lower above -h? |
|---|---:|---|---:|---|---|---|
| official pooled SLU-F1 | -4.3929 | [-6.6889, -2.1735] | -1.1218 | **YES** | **YES** | no |
| intent accuracy | -9.1667 | [-11.6404, -6.7887] | -1.0051 | **YES** | **YES** | no |

**HARMFUL is read first** (owner decision 25, Method B) and it fires on **all four** clauses: both point
estimates fall below their own-null margins, and both CI95 **upper** bounds fall below zero. This is a
measured loss, not a wide interval. Non-inferiority is not merely unproven; it is refuted. The margins
are cell B0r's own null on this exact roster and geometry -- **h_SLU 1.1218, h_intent 1.0051** at CI95
-- the registered decision-38 fallback, this cell having no replicate of its own.

**Per-scenario diagnostic (owner decision 17).** **Nine** scenarios lose intent beyond the null band
(CI95 upper below zero): audio, cooking, general, iot, lists, music, qa, takeaway, transport. **Twelve**
are flagged at five or more net harmed rows. **No scenario gains**; four (email, news, social,
weather) are exactly flat and every other one loses. The loss is uniform, which is what a
delivery-shape failure looks like and what a knowledge or reasoning effect would not.

| scenario | n | intent anchor | intent EFF-1 | delta | CI95 | net harmed | flag |
|---|---:|---:|---:|---:|---|---:|---|
| audio | 60 | 76.67 | 48.33 | -28.33 | [-48.94, -17.92] | 17 | D17 BAND |
| cooking | 60 | 85.00 | 70.00 | -15.00 | [-25.00, -6.67] | 9 | D17 BAND |
| iot | 60 | 86.67 | 73.33 | -13.33 | [-24.14, -3.33] | 8 | D17 BAND |
| transport | 60 | 86.67 | 73.33 | -13.33 | [-23.44, -4.08] | 8 | D17 BAND |
| qa | 60 | 75.00 | 61.67 | -13.33 | [-21.21, -5.56] | 8 | D17 BAND |
| lists | 60 | 83.33 | 71.67 | -11.67 | [-20.00, -3.77] | 7 | D17 BAND |
| takeaway | 60 | 85.00 | 73.33 | -11.67 | [-20.90, -3.17] | 7 | D17 BAND |
| general | 60 | 36.67 | 25.00 | -11.67 | [-23.08, -1.64] | 7 | D17 BAND |
| alarm | 60 | 83.33 | 73.33 | -10.00 | [-20.65, +4.55] | 6 | D17 |
| datetime | 60 | 83.33 | 73.33 | -10.00 | [-22.45, +1.67] | 6 | D17 |
| music | 60 | 76.67 | 66.67 | -10.00 | [-20.00, -1.59] | 6 | D17 BAND |
| play | 60 | 58.33 | 50.00 | -8.33 | [-19.73, +3.70] | 5 | D17 |
| recommendation | 60 | 90.00 | 85.00 | -5.00 | [-12.50, +1.72] | 3 | -- |
| calendar | 60 | 75.00 | 71.67 | -3.33 | [-9.52, +3.45] | 2 | -- |
| email | 60 | 85.00 | 85.00 | +0.00 | [-5.08, +5.00] | 0 | -- |
| news | 60 | 80.00 | 80.00 | +0.00 | [+0.00, +0.00] | 0 | -- |
| social | 60 | 66.67 | 66.67 | +0.00 | [-8.33, +7.81] | 0 | -- |
| weather | 60 | 90.00 | 90.00 | +0.00 | [-6.78, +6.67] | 0 | -- |

Full per-scenario pooled SLU-F1 in both weightings is in `per-scenario-tables.json`.

**Context, not a gate.** Against the released direct anchor, EFF-1 is **+10.26 pp** pooled SLU-F1
[+6.89, +13.68] and **-4.91 pp** intent [-7.52, -2.31]: the agent system still beats the direct
baseline on slot filling while now losing to it on intent.

### 5.1 Development companions (owner decisions 7 and 14; they decide nothing)

Projection v3 (`slurp-slu-official-projected-v3-train`) and the TRAIN symmetric sibling
(`slurp-slu-f1-normalized-v1-train`), both run model-free over **copies** of the sealed outputs. Owner
decision 23 keeps the official, unprojected number the one that decides; these are development views
and they **decide nothing**. Both reproduce the anchor's registered v3 aggregates exactly (51.99 /
79.35 / 85.46 / 80.65 / 40.30).

| view | metric | anchor | EFF-1 | delta pp | speaker CI95 |
|---|---|---:|---:|---:|---|
| projection v3 | pooled SLU-F1 | 51.99 | 47.06 | -4.94 | [-7.57, -2.44] |
| projection v3 | intent | 79.35 | 69.54 | -9.81 | [-12.13, -7.56] |
| projection v3 | pooled span F1 | 40.30 | 35.55 | -4.75 | [-7.67, -1.93] |
| projection v3 | scenario / action | 85.46 / 80.65 | 74.72 / 70.74 | -10.74 / -9.91 | -- |
| TRAIN symmetric | pooled SLU-F1 | 52.09 | 47.13 | -4.96 | [-7.61, -2.46] |
| TRAIN symmetric | pooled span F1 | 41.38 | 36.77 | -4.61 | [-7.71, -1.67] |

Both companions move the same way and by the same size as the official number, which is what a
delivery-shape failure predicts: neither a label projection nor a symmetric filler normalizer can
recover a row whose text does not parse. The symmetric normalizer is `saea-slurp-slot-normalizer-v1`
with 34 false merges on both sides. Under projection v3 the **137 EFF-1 rows are `ineligible`**
against the anchor's 7 -- the projection's own `unparsed` branch counts the same failure.

---

## 6. Mandatory diagnostics

1. **Finite completions: 2 rows**, `slurp:train:006712:audio-1500980407-headset` and
   `slurp:train:011205:audio-1490262560-headset`. Both `finish_reason` `"length"`, role `reviewer`,
   stage `review`, `planner_accepted` false, `revision_count` 0; both **delivered the latest Solver
   draft** (2 deliveries, 0 abstentions). Both rows are retained and are in every number above. The
   sealed anchor carries **0**, as its registered exposure receipt
   (`docs/receipts/slurp-finite-completion-exposure-v1.json`) proves, so the comparator side of the
   declaration's asymmetry is provably unaffected. **Recomputed with those two rows excluded** -- beside
   the registered all-rows number, which stays the number the rule reads -- pooled SLU-F1 is
   **-4.402 pp [-6.698, -2.191]** and intent **-9.091 pp [-11.566, -6.708]**: unchanged. No row is
   filtered.
2. **`planner_action_illegal`: 1 row**, `slurp:train:011394:audio-1502890109-headset`, `count: 1`,
   schema `saea-native-planner-action-illegal-v1`, offending action digest
   `1650b04f64c06fc84e99c6812f34138d13a18e86462f74dfc5a19d2712417fdb` (the action text is model output
   and is not printed here; the sealed receipt carries **no** character count, only the digest). The
   row is retained, delivers its committed draft and is in every metric above. The sealed anchor carries
   **0**.
3. **First-request byte identity**: section 3. Claim (b) holds on all 1,080 Perception requests; claim
   (a) is structurally not evaluable and recorded zero violations.
4. **The constancy table**: section 3. `distinct_tool_schemas_sha256 == 1` on every row;
   `authority_tool_names` unchanged beside `rendered_tool_names`.
5. **Native task-contract calls: 939** against the anchor's realized **1,082** and the 6,480 ceiling.
   **Tool calls emitted by a role holding no authority: 0** (perception 0, solver 0, planner 0). Zero
   rail refusals.
6. **Per-scenario tables in both weightings, plus net harmed rows per scenario**: section 5 and
   `per-scenario-tables.json`.
7. **Row accounting**: 1,080 in, 1,080 out on both sides; no row dropped, no `sample_id` invented.
8. **Cost**: section 2.5.

**Revisions.** The arm took **12** `REVISE` routes on 12 rows against the anchor's **6** on 5 rows
(planner routes 1,090 -- ACCEPT 1,077, REVISE 12, illegal 1 -- against the anchor's 1,085 -- ACCEPT
1,079, REVISE 6). The rise is small in absolute terms and sits alongside the 137 rows that saw the
Reviewer only once against the anchor's 3; it is reported, not interpreted.

**Per-role prompt tokens, beside the anchor's.**

| role | contacts EFF-1 / anchor | prompt median EFF-1 / anchor | median delta | prompt total EFF-1 / anchor |
|---|---|---|---:|---|
| perception | 1,080 / 1,080 | 3,727 / 3,593 | **+134** | 4,029,533 / 3,884,813 |
| solver | 1,092 / 1,085 | 8,898 / 8,964 | -66 | 9,489,690 / 9,492,410 |
| reviewer | 2,031 / 2,167 | 9,602 / 9,905 | -303 | 19,353,046 / 21,112,471 |
| planner | 1,090 / 1,085 | 10,536 / 10,804 | -269 | 11,227,984 / 11,508,573 |

Only the Perception row is a like-for-like comparison; the other three roles' prompts depend on
upstream model output that this factor changed, so their medians are descriptive, not attributable.

---

## 7. Harness-admission consequence

| field | value |
|---|---|
| class | `episode` |
| key | `native_episode.tool_schema_rendering` |
| OFF | the key's absence, or the explicit `"per-role"` (`rails.config_tables.is_episode_null_arm`) |
| ON | `"constant"` |
| module | constant native tool-schema rendering (lever L1) |
| carrier | `slurp` |
| **verdict** | **HARMFUL** |
| admitted | **no** |

**The key enters no default plan.** Per-role rendering remains the SLURP default, and every later cell
and the test read continue to register against it; section 4.1 of the preregistration -- the clause that
would have bound later cells to declare which side of the switch they sit on -- does not fire. The
coordinator writes the harness-admission receipt entry from this verdict, never from the
preregistration.

**Consequences the registration fixed in advance, now in force.**

* **Lever L2 (drop the Planner) must not be credited with L1's gain.** The registration's ordering note
  was written for exactly this case. L1 is measured and its prefill gain is quantified here
  (-61.3 % prefilled tokens per row); a future L2 cell measured on the *per-role* base will still be
  carrying the L1 toggle cost, and its gain must be reported against the per-role base it flies on.
* **The efficiency result survives the quality verdict.** Owner decision 41's throughput target is not
  abandoned by this verdict -- it is redirected. The measurement proves the prefix-cache diagnosis was
  right: constant rendering halves GPU hours and removes 96.9 % of the first Reviewer's prefill and
  80.8 % of the Planner's. What it also proves is that *this* way of holding the array constant --
  rendering the Reviewer's tools to roles that cannot call them -- is not free.
* **Candidate repairs exist and none is decided here.** The throughput report's own L1 paragraph names
  a second variant -- withdraw the Reviewer's tool schema and express the task contract in the
  instruction, so that **no** role renders a tool paragraph and the system message is constant because
  it is empty of tools. That variant would remove the input this failure needs, but it changes the
  admitted B4b / M1 base and E17's loader refuses `"constant"` when no role holds authority, so it is a
  **new cell with its own registration**. So is any variant that keeps the rendering constant while
  constraining the tool-free roles' output shape (for example a `response_format` on the Solver, which
  today carries none). **Nothing here authorizes either**, and neither is claimed to work.
* **One experiment in flight; no recovery re-registration is claimed.** This flight did not fail -- it
  completed, sealed clean and was read once. There is no root-diagnosed recovery to register under the
  registration's failure rule, because nothing failed operationally.

---

## 8. What is not claimed

* **No effectiveness claim of any kind.** This cell asserted nothing about quality except that it would
  not fall. It fell, and that is the finding.
* **No superiority, generalization, paper-scale or held-out claim.** TRAIN Fold A is an exposed
  discovery roster and every claim here stops at it. Fold B, DEV-1000 and the test split stay untouched
  and unread.
* **No cross-carrier claim.** The measurement is SLURP native, np4, ctx24k, `id_slot` per-sample.
  Earnings and Audio2Tool are not addressed, and neither the saving nor the failure measured here is
  claimed there.
* **No geometry claim.** np6 / np8 and `-ub` remain out of scope. The measurement that the row is no
  longer prefill-bound is reported and acted on by nothing here.
* **No claim that the delivery-shape failure is a property of the frozen core in general.** It is a
  property of *this* rendering, *this* template and *this* serving configuration, measured once.
* **No bar attempt, no replication claim, and no headroom attempt consumed.**

---

## 9. Reproduction

Analysis package (model-free, under `SPEECHRL_DATA_DIR`, nothing committed):
`analysis/SAEA-SLURP-EFF1-TOOL-CONSTANT-ANCHOR-V1-PAIRED-ANALYSIS-V1/` -- the recipe's own registered
analysis root.

| file | sha256 |
|---|---|
| `score-contrasts.json` | `cff4015d898e37a474d80670a2231adab409fa58ae8b312a774a9e4317aa6e3e` |
| `throughput-tables.json` (the brief's `efficiency.json`) | `3cf11ac66092f362b72a4f1160b654045d7794f0e246085e44c6b390878a408f` |
| `per-scenario-tables.json` | `56f44f16a1007cf61dcec543387eaa8bcdf370d428dcf26abeee60e060810d66` |
| `flight-diagnostics.json` | `983e254e42cfe5ed66d9bc47fe833a22ef8edf803e74c419f46c6989256658d3` |
| `delivery-shape-attribution.json` | `64f7b7ee020cc1a8244cc9e904aa11758a5c790696119837e451c7030a86bc96` |
| `README.md` | `bf56a82613ccb43373886bebcaa770d99d5a4753675a84aa84109789c3e709df` |
| `eff1_paired_read.py` (the driver) | `8bb31f12fbead0527b41f16d65e66c0774caa4f5b294976f2f07937e7fe301de` |

`README.md` in that directory carries the same tables; `score-contrasts.json` carries every input and
output path with its sha256, the authority documents with their digests, the estimator implementation
digests, and the full interval blocks. `throughput-tables.json` is the recipe's name for the efficiency
tables. Stages: `contrasts`, `band`, `diag`, `server`, `parse`, `v3`, `v3contrasts`, `sym`,
`symcontrasts`, `assemble`.
