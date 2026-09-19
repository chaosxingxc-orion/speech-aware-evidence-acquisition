# SLURP throughput root cause: measured cost model and ranked levers (owner decision 41)

Date: 2026-09-19. Author: Fable 5.1 (checker phase). Branch `fable/throughput`.
Companion receipt: `docs/receipts/slurp-throughput-root-cause-v1.json`.

Model-free. Zero model, tokenizer, encoder and server contacts. Everything below is read from
sealed run directories under `SPEECHRL_DATA_DIR`, from the serving session's own launch record,
`monitor.jsonl` and `server.log` on disk, and from committed configuration. No utterance text and
no gold appear here or in the receipt. The campaign
`SAEA-SLURP-NATIVE-NCP-L1-ANCHOR-TRAIN-FOLD-A-V2` was in flight and its run directory was not
opened.

---

## 0. Verdict in one paragraph

The SLURP flights are **PREFILL-BOUND**, and the bound is not the batch. Across four sealed native
runs the wall clock is predicted by one number -- the count of prompt tokens llama.cpp actually had
to evaluate -- at **488 to 536 seconds per million prefilled tokens** (a spread of about 5 %), while
the same wall clock predicted from contacts varies by 30 % and from generated tokens by 20 %. The
machine's aggregate prefill rate is **1,999 to 2,048 tokens per second** at `-np 4`, and a single
request already reaches 2,266 tokens per second at the median and 3,123 at the maximum, so the
server is running roughly one prefill at a time at close to its single-stream ceiling; adding slots
does not raise that ceiling (the np8 sessions of 2026-09-08..13 hit the same per-request maximum).
The reason the flights are slow is therefore **how many tokens the row presents for evaluation**,
and the dominant cause of that count is not prompt size but **prefix-cache breakage**: the
Reviewer is the only role that carries a native `tool_schemas` entry, the task instruction is
byte-identical for all four roles (one distinct hash over every request of every run), and the chat
template renders the tools block *inside the system message*. The five contacts of a row run on one
pinned slot in the order perception, solver, reviewer, reviewer, planner, so the tools block
toggles on at contact 3 and off at contact 5, and each toggle invalidates the whole KV prefix --
including the speech packet, which is re-decoded on 100 % of planner and first-reviewer contacts.
Character-level measurement says 82.2 % of the first Reviewer's rendered prompt and 84.9 % of the
Planner's is a literal prefix of its predecessor; llama.cpp realises 23.6 % and 19.8 %. Repairing
that one rendering fact removes about half of all prefill work.

---

## 1. What was measured, and how it was joined

### 1.1 Sources

| source | what it gave |
|---|---|
| `runs/<run>/<attempt>/<run>.trace.jsonl` | per contact: role (`USE` record `flight-NNNN/native-role-contact`, field `use_role_id`), `COST` (prompt/completion tokens, latency, audio seconds), `MODEL_REQUEST` payload (task instruction, tool schemas, supplied evidence, history, speech feature parts, `decoding_params.id_slot`); the run manifest beside it gave `cost`, `plan`, `split` (1,080 ids) and `status` |
| `runs/<run>/<attempt>/flight-receipts.json` | `run_phases` (wall seconds, contact count, slot occupancy, contacts per second), `preprocess`, `score`, `seal.serving_monitor_summary` |
| `serving/serving-slurp-native-candidate-five-train-a-np4-v1/session.json`, `session-receipt.json` | launch argv, props, geometry, binary and GGUF hashes |
| the same session's `server.log` (70.8 MB, 651,869 lines) | per request: `prompt eval time = X ms / N tokens`, `eval time`, `total time`, `slot release: ... n_tokens`, `process_mtmd` speech-chunk decodes, `launch_slot_` / `get_availabl` |
| the same session's `monitor.jsonl` (20,794 samples, 2026-09-16 to 2026-09-19) | GPU power, pstate, SM clock, VRAM, busy slots, host memory |
| other sessions' `session-receipt.json` + `monitor.jsonl` | the VRAM-versus-context curve and the np4/np8 comparison |

### 1.2 The join

`server.log` carries relative timestamps (`MM.SS.mmm.uuu`, minutes unbounded) and six process
segments. Segment 6 starts at the session's `started_at` (epoch 1789742596.612345) and contains
B5e, B2 v3 and the B4b replicate; segment 1 contains B1 and the direct baseline, and its epoch was
fixed as the offset that reproduces each run's exact contact count.

Each run's server records were then aligned to its client contacts **per slot**: the config pins
`decoding_params.id_slot = "per-sample"`, so one row owns one slot for its whole trajectory, and
the per-slot request sequences match one for one. After alignment, `n_tokens - generated + 1`
equals the client's `usage.prompt_tokens` on **100.00 %** of contacts in all four native runs and
in the direct baseline (5,425 / 2,501 / 5,415 / 9,807 / 1,080). That exactness is what lets
per-role prefill, cache-hit and packet-decode figures be quoted as measurements rather than
estimates.

Derived quantities:

* prompt length = `n_tokens` at release minus generated tokens;
* **prefilled** = the `prompt eval time` token count, i.e. what the GPU actually evaluated;
* **cached** = prompt length minus prefilled, i.e. what the slot's KV prefix supplied for free.

---

## 2. Serving geometry as flown

```
llama-server -m Qwen3-Omni-30B-A3B-Instruct-Q4_K_M.gguf --no-mmproj
  -c 98304 -np 4 -b 2048 -ub 512 -fa on -ngl 999 -ctk q8_0 -ctv q8_0
  --cache-prompt --cache-ram 0 --no-cache-idle-slots --slot-prompt-similarity 0
```

* build `b8-04ccc72a2` (llama.cpp-featcache), binary sha256 `d0b42ace...`, GGUF sha256 `0751c279...`
  (18,557,053,952 bytes).
* 4 slots of 24,576 tokens each; `max_tokens` 512; fragment
  `q4km-mmproj-free-slurp-native-bounded-perception-proof-np4-ctx24k-max512-v1`;
  `prompt_order = speech-query-prefix-v2`.
* GPU: **RTX 5090 Laptop, 24,462 MiB**. Host: Core Ultra 9 275HX, 24 threads.
* `--cache-ram 0` means the server-level prompt cache is off; the log says so at startup
  (`prompt cache is disabled - use --cache-ram N to enable it`). Only the per-slot KV prefix is
  reused. `--slot-prompt-similarity 0` disables llama.cpp's own similarity routing, which is
  correct here because the **client** chooses the slot.

---

## 3. The cost model of one row

Reference system: **B4b slot-store v2, anchor, TRAIN Fold A, replicate v2, `resume2` attempt**
(the first admitted module; 500 rows, COMPLETED). The other three native runs agree within a few
per cent and are in the receipt.

### 3.1 Contacts, tokens, latency by role

| role | contacts / row | prompt tok (med / p90 / mean) | prefilled / contact | cached | generated (med / mean) | client latency s (med / p90) | prefilled / row | share of row prefill |
|---|---|---|---|---|---|---|---|---|
| perception | 1.00 | 3,597 / 3,661 / 3,598 | 1,374 | 61.8 % | 134 / 119.0 | 15.43 / 20.74 | 1,374 | **5.2 %** |
| solver | 1.00 | 9,963 / 11,379 / 9,622 | 6,235 | 35.2 % | 24 / 24.2 | 6.14 / 10.64 | 6,260 | **23.9 %** |
| reviewer | 1.99 | 10,729 / 12,712 / 10,603 | 4,655 | 56.1 % | 22 / 47.3 | 8.29 / 14.92 | 9,282 | **35.4 %** |
| planner | 1.00 | 11,799 / 13,234 / 11,463 | 9,244 | 19.4 % | **2 / 2.0** | 5.10 / 8.39 | 9,281 | **35.4 %** |
| **row** | **5.00** | 45,911 tok/row | -- | 42.9 % | 240 tok/row | -- | **26,197** | 100 % |

The Planner spends **35.4 % of the whole flight's prefill work to emit exactly two tokens**
(median 2, mean 2.0, over 502 contacts). This is the same node the 2026-09-17 node-context audit
flagged at "25 % of tokens for ACCEPT"; measured against *prefill* rather than prompt volume it is
larger still.

### 3.2 Wall, GPU hours, occupancy, utilisation

| run | rows | contacts/row | wall s | GPU-h / 1,080 rows | prefilled / row | prompt / row | generated / row | cache hit | agg prefill tok/s | agg decode tok/s | mean busy slots | slot occupancy (receipt) | mean util % | parked |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| direct baseline | 1,080 | 1.00 | 450.6 | **0.125** | 145 | 2,277 | 25 | 93.7 % | 347 | 59.4 | 3.55 | 0.658 | 55.7 | 28.1 % |
| B1 exemplars k20 | 1,080 | 5.02 | 13,894 | **3.860** | 25,933 | 45,725 | 237 | 43.3 % | 2,016 | 18.4 | 3.57 | 0.877 | 91.0 | 4.5 % |
| B4b replicate (resume2) | 500 | 5.00 | 6,395 | **3.837** | 26,197 | 45,911 | 240 | 42.9 % | 2,048 | 18.7 | 3.80 | 0.881 | 90.1 | 1.8 % |
| B5e combination | 1,080 | 5.01 | 14,483 | **4.023** | 26,807 | 46,791 | 235 | 42.7 % | 1,999 | 17.6 | 3.57 | 0.851 | 88.7 | 3.7 % |
| B2 v3 samples5 | 1,080 | 9.08 | 13,754 | **3.821** | 23,756 | 78,273 | 337 | 69.7 % | 1,865 | 26.5 | 3.70 | 0.863 | 87.5 | 2.7 % |
| dual-store anchor (exposure ledger) | 1,080 | 5.02 | -- | **3.388** | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- |

Aggregate prompt-token throughput including cached tokens is 3,489-3,590 tok/s on the 5-contact
runs and 6,146 tok/s on B2 v3; aggregate decode throughput is 17.6-26.5 tok/s.

### 3.3 Which bound

Three candidate bounds, each tested against the measurements.

**Dispatch (idle slots) -- not the bound.** Zero-busy time share is 0.02 % (B4b), 0.10 % (B2 v3),
3.57 % (B5e) and 3.76 % (B1). Mean busy slots 3.57-3.80 of 4. Monitor `parked_fraction`
1.8-4.5 %. Maximum recoverable: about 4 %.

**Decode -- not the bound today.** Summed per-slot decode windows are 57 % of the four-slot budget,
but those windows include time a generating slot spends waiting while another slot's prefill owns
the batch: per-slot decode rate falls 111.8 -> 56.4 -> 30.1 -> 9.2 tok/s as measured concurrency
goes 1 -> 2 -> 3 -> 4, i.e. aggregate decode *falls* with concurrency, which only happens when the
decoders are being starved. Independent evidence of the real ceiling: the np4 direct baseline,
which is decode-dominated (93.7 % cache hit, prefill only 11 % of the busy budget), sustains
**59.4 tok/s**; the np8 session `slurp-np8-base-c65536-20260909` (97 % cache hit, mean 7.38 busy
slots) sustains **115.9 tok/s**. At 240 generated tokens per row that is a decode floor of 4.0 s/row
at np4 and 2.1 s/row at np8 -- against a measured 12.79 s/row.

**Prefill -- the bound.** 26,197 prefilled tokens per row / 2,048 tok/s = **12.79 s/row**, which is
the whole measured row time. The same law holds across all four native runs:

| run | s per million prefilled tokens | s per contact | ms per generated token |
|---|---|---|---|
| B1 | 496.1 | 2.561 | 54.4 |
| B4b | 488.2 | 2.557 | 53.4 |
| B5e | 500.2 | 2.674 | 57.0 |
| B2 v3 | 536.1 | 1.402 | 37.8 |
| spread | **+/- 4.6 %** | +/- 30 % | +/- 20 % |

B2 v3 is the decisive case: it ran **1.81x the contacts of the dual-store anchor for 1.13x the
anchor's GPU hours** (9,807 vs 5,417 contacts; 3.821 vs 3.388 GPU-h). Its prompt volume was 1.71x
B1's, but its **prefilled** volume was 0.92x B1's, because grouped sampling puts five identical
solver prompts back to back on one slot and the last four are near-total cache hits: the B2 v3
solver caches **87.8 %** and costs 5,387 prefilled tokens per row across 5.05 contacts, *less* than
the single un-sampled solver contact of B4b (6,260). Contacts are not the cost. Prefilled tokens
are.

### 3.4 The prefill rate curve

Per-request prefill rate at np4 `-ub 512`, over the 17,577 requests of the three segment-6 runs:

| prefilled tokens | n | median tok/s | p90 | max |
|---|---|---|---|---|
| 1,000-2,000 | 5,362 | 2,297 | 2,757 | 3,074 |
| 4,000-5,000 | 539 | 2,452 | 2,795 | 3,001 |
| 8,000-9,000 | 1,343 | 2,192 | 2,655 | 2,900 |
| 10,000-11,000 | 569 | 2,151 | 2,572 | 2,784 |
| all >= 4,000 | 7,477 | 2,266 | 2,719 (p90) | 3,123 |

There is no small-batch penalty to recover -- the rate is flat to gently declining with prompt
size. The machine aggregate (2,048 tok/s) sits just below the single-request median (2,266),
confirming that prefill is essentially serialised and already near its ceiling.

---

## 4. The batch question, answered directly

**Geometry as flown.** `-np 4`, `-c 98304` (24,576 tokens per slot), `-b 2048`, `-ub 512`,
`-fa on`, `-ctk/-ctv q8_0`, `-ngl 999`.

**Would more slots raise throughput? No, not today.** Mean busy slots is already 3.57-3.80 of 4
and the zero-busy share is under 4 %; aggregate prefill (2,048 tok/s) is already at the
single-request rate, so the slots are not waiting on each other, they are queueing behind one
GPU-bound prefill stream. The np8 sessions confirm the ceiling is geometry-independent: maximum
per-request prefill 2,833 tok/s at `serving-slurp-role-coverage-np8-v1`, 2,505 at
`slurp-g2-kus4n-aligned-np8-20260910-root`, 3,126 at `slurp-np4-base-c65536-20260909` -- the same
number at np4 and np8. Adding slots at today's prompt sizes would only divide the same prefill
stream into more, slower pieces, which is exactly what the np8 per-slot medians show
(390-1,065 tok/s).

**Do the prompts fit? Comfortably, with room to spare.** Prompt-length tails per run:

| run | p50 | p90 | p99 | p99.9 | max prompt | max context used | margin to the 24,576 slot |
|---|---|---|---|---|---|---|---|
| B5e | 10,296 | 13,105 | 14,486 | 15,756 | 18,018 | 18,110 | 6,466 |
| B4b | 10,184 | 12,524 | 13,872 | 15,045 | 15,279 | 15,350 | 9,226 |
| B1 | 10,028 | 12,660 | 13,936 | 15,097 | 15,461 | 15,523 | 9,053 |
| B2 v3 | 9,116 | 11,319 | 12,995 | 14,229 | 14,644 | 14,737 | 9,839 |

Zero truncations in any run. Note one latent inconsistency: the preflight `prompt_budget` receipts
reason against `slot_limit_tokens = 32768` while `props_identity.slot_n_ctx` is 24,576. No run came
near either, so nothing was harmed, but the gate is currently permissive by 33 %.

**VRAM budget.** Measured `memory_used_mib`, `--no-mmproj`, `-ub 512`: **22,976 MiB at c=98,304**
and **21,272 MiB at c=65,536**. The difference, 1,704 MiB per 32,768 tokens, gives
**53.2 KiB of KV per token** (q8_0 K and V, flash attention on) and a constant base of
**17,868 MiB** for model plus compute buffers -- consistent at both points, so the fit is linear.
Free VRAM at the current geometry: **1,486 MiB**.

**The largest geometry that fits**, keeping the 17,868 MiB base and leaving about 400 MiB of
headroom, is roughly **119,000 total context tokens** -- for example np6 x 19,456 or np5 x 23,552.
But the maximum context observed is 18,110 tokens, so np6 x 19,456 leaves a 1,346-token margin,
well under the preflight's own 8,192-token operational reserve. **np6 is therefore not admissible
until the prompt shrinks**, and while the flight is prefill-bound it would buy nothing anyway. This
changes after section 7, step 4.

---

## 5. Prefix reuse: what is available and what is realised

### 5.1 The rendered layout

`prompt_order = speech-query-prefix-v2` builds
`[system: task_instruction] [user: query speech packet][stable text][key packets][mutable evidence + agent state]`.
Two measured facts about the SLURP native runs:

1. **`task_instruction` is byte-identical across all four roles** -- one distinct SHA-256 over all
   2,501 (B4b) / 5,425 (B1) / 5,415 (B5e) / 9,807 (B2 v3) requests. The instruction is not the
   thing that changes.
2. **Every evidence item is typed `knowledge_role = "value"`** (46,605 of 46,605 items in B4b).
   The transport's cache-explicit key/value split therefore puts *nothing* in the stable prefix:
   `stable_text_parts` is empty and the entire knowledge block lands in the mutable suffix, after
   the query packet. Measured stable head (system message + query packet) = **14.2 %** of the
   rendered characters.

### 5.2 Character-level prefix overlap (proxy) versus tokens actually cached

Per-row transition, B4b (500 rows; B1 and B5e within 0.5 points):

| transition | roles | `tool_schemas` | char LCP share of the later prompt | tokens actually cached | speech packet re-decoded |
|---|---|---|---|---|---|
| 0 -> 1 | perception -> solver | 0 -> 0 | 0.254 | 36.1 % | 0 % |
| 1 -> 2 | solver -> reviewer #1 | **0 -> 1** | **0.822** | **23.6 %** | **100 %** |
| 2 -> 3 | reviewer #1 -> reviewer #2 | 1 -> 1 | 0.617 | **83.5 %** | 1.4 % |
| 3 -> 4 | reviewer #2 -> planner | **1 -> 0** | **0.849** | **19.8 %** | **100 %** |

The two transitions where realisation collapses are exactly the two where the native tool array
toggles. The Qwen3-Omni chat template renders `tools` *inside* the system message
(`<|im_start|>system\n` + content + `\n\n# Tools\n<tools>...`), so a toggle changes the token
stream about 2,220 tokens in -- and the measured cached count on those contacts is 2,219 tokens,
against 2,224 when no toggle occurred. The divergence is a handful of tokens at the end of the
system message, and it costs the whole remainder of the prompt, speech packet included.

### 5.3 Prefill per row by position -- where the money goes

| position | role | tools | prompt (med) | prefilled (med) | cached | generated (med) | packet re-decoded | prefilled / row | share |
|---|---|---|---|---|---|---|---|---|---|
| 0 | perception | 0 | 3,597 | 1,373 | 61.8 % | 134 | 100 % | 1,374 | 5.2 % |
| 1 | solver | 0 | 9,960 | 6,591 | 36.1 % | 24 | 0 % | 6,258 | 23.9 % |
| 2 | reviewer #1 | **1** | 10,062 | **7,843** | 23.6 % | 22 | 100 % | **7,505** | **28.7 %** |
| 3 | reviewer #2 | 1 | 11,813 | 1,757 | 83.5 % | 70 | 1.4 % | 1,859 | 7.1 % |
| 4 | planner | **0** | 11,805 | **9,586** | 19.8 % | 2 | 100 % | **9,109** | **34.8 %** |

Positions 2 and 4 carry **63.5 % of all prefill work**, and position 3 -- which is the *same role*
as position 2, with a *longer* prompt -- costs a quarter of it. Nothing about the Reviewer or the
Planner is intrinsically expensive; their neighbours' tools shape is.

### 5.4 Cross-row reuse

Character LCP between the first contacts of two different rows is **0.33** (system message plus a
common evidence head). The common prefix of all five contacts of one row is **0.258**. So cross-row
affinity has nothing to offer beyond what the per-row pin already gives, and pinning slots to
*roles* instead of rows would be strictly worse: it would leave only the 2,224-token system head.

---

## 6. Levers, ranked

Gains are quoted on **GPU hours per 1,080 rows** (today: 3.837 for the admitted system) and on the
**13,078-row test read** (today: 46.5 h at the admitted system's rate; 41.0 h at the dual-store
anchor's 3.388 GPU-h, which is where the owner's "41-42 hours" comes from). All conversions use the
measured 2,048 prefilled tokens per second unless stated.

### L1 -- Hold the native tool rendering constant across the five roles. MEASURED, largest.

*Mechanism.* Give every role the same `tool_schemas` array (either all four roles carry the
Reviewer's single schema, or the Reviewer's schema is withdrawn and its contract expressed in the
instruction). The system message then never changes inside a row, the KV prefix survives the role
handover, and the speech packet stops being re-decoded four times out of five.

*Gain.* Setting positions 2 and 4 to their measured available reuse
((1 - 0.822) x 10,062 = 1,791 and (1 - 0.849) x 11,805 = 1,783) gives
**26,197 -> 13,065 prefilled tokens per row, -50.1 %**. 3.837 -> **1.92 GPU-h / 1,080**;
test read 46.5 -> **23.2 h**. Position 3 is the existence proof: a same-tools handover realises
83.5 % where the character proxy says 61.7 % is available, so the bound is conservative.

*What changes.* Request bytes (one array field on four roles), hence `config_hash` and
`protocol_hash`. No change to knowledge, roster, split, geometry, scorers or contact count.

*Admission form.* A one-factor efficiency cell that must read **NEUTRAL** on the official number
at n >= 400, preceded by the model-free render proof of section 8.

*Risk.* Adding the tools block to perception/solver/planner also inserts the template's tool
instruction paragraph into their system message, which the model can react to; withdrawing the
Reviewer's tool authority changes the admitted B4b / M1 base. Medium. The first variant is
preferred because it leaves every role's *authority* unchanged and only adds a constant block.

### L2 -- Remove the Planner contact, or make it a non-contact. MEASURED.

*Mechanism.* The Planner consumes 11,463 prompt tokens to emit a two-token verdict
(`ACCEPT` / `REVISE`). Owner decision 39 on node primitives points the same way.

*Gain today:* -9,109 prefilled tokens/row = **-34.8 %** -> 2.50 GPU-h / 1,080, test read **30.3 h**.
*Gain after L1:* only -1,783 tokens/row; L1 + L2 together give 11,282 tokens/row (-56.9 %) ->
**1.65 GPU-h / 1,080**, test read **20.0 h**.

*Ranking note.* The Planner looks like the single biggest line item, but four fifths of its cost is
the tools toggle, not its existence. **L1 must be evaluated first**, or L2 will be credited with
L1's gain.

*What changes.* The phase program (a controller change), so this is an effectiveness-bearing cell,
not an efficiency cell. *Risk:* high -- it removes a decision node.

### L3 -- Shrink the supplied-evidence block. BOUNDED, not measured.

*Mechanism.* The evidence list grows from 8 items at perception to 22 items at solver
(41,753-41,798 characters at solver / reviewer / planner). After L1 the solver's first full render
of that block, 6,258 prefilled tokens per row, is the single largest remaining item (48 % of the
post-L1 row).

*Gain (modelled).* Halving the block to 11 items removes roughly 3,000 tokens from every contact's
prompt; carrying that through the post-L1 profile gives about **7,200 prefilled tokens per row**
-> 1.05 GPU-h / 1,080, test read **12.7 h**. Not measured; the natural one-factor cell is a k-sweep
twin of B1 (k = 20 exemplars today -> k = 10).

*What changes.* A config key on the knowledge provider. *Risk:* high -- it is the mechanism under
test.

### L4 -- Cell B7c, the tool-observation contract rewrite. MEASURED, already registered, free.

*Mechanism.* The replayed task contract inside tool-observation states is rendered as a reference
to the system message that already carries it verbatim.

*Gain.* The registered model-free proof over 5,417 sealed anchor requests: 1,102 of 2,184
tool-observation rows shortened by 6,033 characters each, 6,648,366 characters over a 1,080-row
run. At the run's own 6.87 characters per prompt token that is about 967,000 prompt tokens, sitting
in the Reviewer's history suffix, hence almost entirely prefilled: **-3.5 % of prefill**, about
**-0.13 GPU-h / 1,080**, **-1.6 h** on the test read.

*What changes.* Already a registered cell with a preregistration and a byte-level proof.
*Risk:* low. A NEUTRAL B7c enters the default plan by its own design rule because it lowers cost.

### L5 -- Raise the serving rate. BOUNDED, not measured.

*(a) GPU power.* Measured power is pinned at **96.1-97.4 W** (median 95.3-96.1, maximum 97.4 over
3,035 in-window samples), pstate P2/P4 with no sustained P0, on a 24 GB RTX 5090 Laptop part whose
stock TGP is 150 W or more. The reported SM clock (180/232 MHz) is a WSL artefact and is not
usable, but the power ceiling is flat and sharp, which is what an enforced cap looks like. This is
a host setting (`nvidia-smi` enforced power limit; the Legion fan/power mode), not a repository
change, and it is byte-neutral: a serving change with a receipt, no protocol hash movement.
*Bounded gain:* prefill scales sub-linearly with power; 1.15-1.4x is plausible and must be
measured. At 1.25x (2,560 tok/s) the test read goes 46.5 -> 37.2 h alone, and the post-L1+L3 budget
12.7 -> 10.2 h.

*(b) `-ub 512 -> 1024`.* No session has ever flown anything but 512 (or 128 on the single-slot
encoding sessions), so there is no measured comparison. The rate curve shows no fixed-overhead
recovery to be had, so any gain must come from GPU occupancy per micro-batch. It costs VRAM, and
with only 1,486 MiB free `-c` must drop from 98,304 to about 90,112 (4 x 22,528, which still leaves
a 4,418-token margin above the observed maximum) to pay for it.

*(c) Prefill / decode interleaving.* Aggregate prefill (2,048) is 90 % of the single-request median
(2,266) and 75 % of the p90 (2,719). The missing 10-25 % is decode steps sharing the batch. There
is no llama.cpp knob that separates them at this build.

### L6 -- Reviewer x2 -> x1. MEASURED, small.

The *second* Reviewer contact is the cheapest contact in the row: 1,859 prefilled tokens per row,
**7.1 %** of prefill, 83.5 % cached. Dropping it saves **-0.27 GPU-h / 1,080** and **-3.3 h** on
the test read, and removes 70 generated tokens per row. A Reviewer x3 -> x1 change would drop more
contacts but again mostly cheap ones. *What changes:* the phase program; effectiveness-bearing.
*Risk:* high for a small efficiency return -- this is the wrong lever.

### L7 -- Dispatch and prefetch. MEASURED, negligible.

Zero-busy time share 0.02-3.76 %; monitor `parked_fraction` 1.8-4.5 %; mean busy slots 3.57-3.80.
The ceiling on any dispatch fix, including an `obs_prefetch_depth`-style lookahead, is about **4 %**
(<= 0.15 GPU-h / 1,080, <= 1.9 h on the test read). The native policy's contacts are strictly
sequential within a row, so prefetch has nothing to overlap except the next row's packet, which is
already cheap: speech packets are 26-52 tokens, and CPU packet preprocessing is 10-15 s for the
whole 1,080-row roster at 8 workers (71-108 packets per second).

### L8 -- More slots or a bigger batch. MEASURED, zero today; the right answer later.

See section 4. Zero gain while prefill-bound, and np6 does not fit the current prompt tails with
the declared reserve. **But** once L1 and L3 land, the row's prefill falls to about 3.5 s while its
240 generated tokens need 68 tok/s aggregate, above the measured np4 decode ceiling of 59.4 tok/s
-- the flight becomes decode-bound, and the np8 measurement (115.9 tok/s aggregate) says slot count
is then the correct lever. By that point the prompts are about 7k tokens, so np6 x 19,456 or
np8 x 14,336 fits inside the 119,000-token VRAM envelope with the reserve intact.

### L9 -- The test read itself. FIXED.

The SLURP test split is 13,078 recordings, headset and far-field both mandatory, no subsampling
(`docs/checks/speech-aware-evidence-acquisition/2026-09-04-scoring-alignment-slurp/README.md`).
There is no legitimate lever here. Scoring is not a lever either: one complete manifest through
`core.scoring_batch` took 156-327 s for 1,080 rows, so about 30-65 minutes for the test read, and
it overlaps the next flight by design.

---

## 7. Projected budget for the 13,078-row test read

Assumptions, stated: (i) the test rows carry the same knowledge store and therefore the same
evidence-block size as TRAIN Fold A; (ii) prompt length follows the same distribution (utterance
length differs, but the speech packet is 26-52 tokens of a roughly 10,000-token prompt); (iii) the
machine prefill rate stays 2,048 tok/s unless L5 is applied; (iv) generated tokens per row stay at
240 unless a node is removed; (v) the np4 aggregate decode ceiling is the measured 59.4 tok/s and
the np8 ceiling the measured 115.9 tok/s.

| step | change | prefilled tok/row | prefill s/row | decode s/row (floor) | binding | GPU-h / 1,080 | test read (h) |
|---|---|---|---|---|---|---|---|
| 0 | as flown (B4b admitted system) | 26,197 | 12.79 | 4.04 | prefill | 3.84 | **46.5** |
| 0' | as flown (dual-store anchor) | -- | -- | -- | prefill | 3.39 | **41.0** |
| 1 | + L1 constant tools rendering | 13,065 | 6.38 | 4.04 | prefill | 1.92 | **23.2** |
| 2 | + L4 B7c tool-observation rewrite | 12,170 | 5.94 | 4.04 | prefill | 1.78 | **21.6** |
| 3 | + L3 evidence block halved | ~7,200 | 3.52 | 4.04 | **decode (np4)** | 1.21 | **14.7** |
| 4 | + L8 np6/np8 (now fits; decode ceiling 115.9) | ~7,200 | 3.52 | 2.07 | prefill | 1.06 | **12.8** |
| 5 | + L5(a) power cap lifted, 1.25x prefill | ~7,200 | 2.81 | 2.07 | prefill | 0.85 | **10.2** |

**The top three levers combined (L1 + L4 + L3) reach 14.7 h**; adding the geometry flip that those
levers themselves enable (L8) reaches **12.8 h**, and any part of L5 clears the 12-hour target. L2
(drop the Planner) is not in the table because after L1 it is worth only about 1.8 h and it changes
the system's behaviour; it should be decided on its merits as a node, not as an efficiency measure.

The honest reading for the owner: **efficiency-only changes (L1 + L4 + L5 + L8) land at roughly
16-18 h, not 12.** Reaching 12 h requires at least one change to how much knowledge the row carries
(L3), which is effectiveness-bearing and must be admitted on the official number first.

---

## 8. What to measure first

The biggest lever is L1 and it can be confirmed in two steps, neither of which makes an
effectiveness claim.

**Probe A -- model-free render proof, 4 rows, zero contacts.** Re-render the 20 contacts of four
sealed B4b rows through the production transport with `tool_schemas` held constant across the five
roles, and emit a receipt carrying, per contact: the rendered system message SHA-256 (must be one
value for all five roles of a row), the rendered prompt SHA-256, and the predicted prefilled-token
count under llama.cpp's common-prefix rule given the pinned per-row slot. Predicted outcome:
positions 2 and 4 fall from 7,843 and 9,586 to about 1,800 each, and the row's predicted prefill
falls from 26,197 to about 13,100. This is the same proof form cell B7c already executed over 5,417
requests, so the machinery exists. Cost: zero GPU, zero model contacts, minutes of CPU.

**Probe B -- 100-row live efficiency cell.** One arm on 100 TRAIN Fold A rows already exposed by
the sealed anchor, same session, same knowledge stores, same roster ordering, one factor: constant
tools rendering. Register an `ExecutionPlan` under `bounded-discovery-probe` and an exposure-ledger
row as usual. Deliverables, all read from the server log and the flight receipt: prefilled tokens
per row, wall seconds per row, aggregate prefill tok/s, per-position cache shares, speech-packet
re-decode share. **No score is computed and no quality read is taken.** Pass criterion: prefilled
tokens per row <= 15,000 (the predicted 13,065 plus a 15 % margin) and packet re-decode share
<= 25 % (today 80 %). Expected cost at today's rate: about 21 minutes for a control-equivalent pass
and about 11 minutes for the treated arm, so well under half a GPU-hour including load.

Only after Probe B passes does the change go to a one-factor cell at n >= 400 that must read
NEUTRAL on the official SLU micro F1 with intent non-inferior, against the sealed B4b bytes, under
the existing own-null margins. If that cell reads NEUTRAL, the study's paper-facing cost halves and
the test read becomes affordable at 23 h before any further work.

A cheap companion measurement, worth doing in the same window: **Probe C**, a byte-neutral serving
receipt that records `nvidia-smi --query-gpu=power.limit,power.default_limit,power.max_limit` and
one fixed 10,000-token prefill repeated ten times at the current cap and again at the stock cap.
That is the only way to turn L5(a) from a bounded claim into a measured one, and it touches no
request bytes.

---

## 9. What could not be measured

1. **The realised token-level gain of L1.** The 82.2 % and 84.9 % figures are character-level
   longest-common-prefix proxies over a faithful reconstruction of the rendered content order.
   Token-level realisation can only be confirmed by Probe A (predicted) and Probe B (measured);
   re-tokenising here would have been a tokenizer contact.
2. **`-ub` 1024 or 2048.** No session in the study has ever used anything other than 512 (or 128 on
   the single-slot encoding sessions), so there is no measured comparison and no VRAM figure for a
   larger compute buffer.
3. **The GPU power cap.** The monitor stores `power_watts` but not `enforced.power.limit`, and the
   SM-clock field is a WSL artefact. The 96.1-97.4 W ceiling is a strong inference from 3,035
   samples across three runs, not a read of the limit itself.
4. **L3's gain.** Modelled from the measured post-L1 profile, not measured. A k-sweep twin is
   required.
5. **Queue wait versus server busy time.** The client `COST` records carry `latency_seconds` but no
   absolute timestamps, so client-side queueing was bounded only indirectly: summed
   launch-to-release windows are 87.6-93.3 % of the four-slot budget against the server's own
   77.1-83.7 % of busy time, and the 6-10 point difference is the per-request HTTP and scheduling
   gap.
6. **The in-flight campaign.** `SAEA-SLURP-NATIVE-NCP-L1-ANCHOR-TRAIN-FOLD-A-V2` was running; its
   run directory was not opened, so the NCP-L1 base's own prefill profile is unmeasured. Its
   registered proof says it adds +0.76 % of wire text and at most +165 tokens on any one contact,
   so it should not move the cost model materially.
7. **The test split's own prompt-length distribution.** Only the TRAIN Fold A 1,080-row roster was
   flown at this geometry; the 13,078-row test read's prompt tail is assumed, not measured.
8. **Why the dual-store anchor costs 3.388 GPU-h and the admitted system 3.837.** The anchor
   carries a smaller supplied-evidence block (36,095 vs 41,798 characters at the solver), which is
   consistent with the cost law, but the anchor's attempt has no `flight-receipts.json` and its
   serving session differs, so its prefill split was not reconstructed from a log.

