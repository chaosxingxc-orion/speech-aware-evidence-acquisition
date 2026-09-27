# SLURP throughput baseline and levers: where ROLL-2's clock went, measured before anything changes (owner decision 140)

**The single largest lever is the empty slot, not the prompt: 27.3 % of ROLL-2's slot capacity (8,997 of
32,909 slot-seconds) sat empty waiting for the client between contacts -- 2.67 s before every first Solver
contact alone -- worth up to +37.6 % contacts per GPU-hour with no change to any byte a node sees; the prefix
cache the brief named as the largest lever is already realised (88.9 % of the 81.4 M sealed prompt tokens
were served from cache; only 9.0 M were prefilled), and across the whole of 2026-09-26 the card computed for
182 of 1,440 minutes (12.6 %) and waited for people for 1,206 (83.8 %).**

Date: 2026-09-27. Author: Fable 5.1, branch `fable/tput`. Receipt
`docs/receipts/slurp-throughput-baseline-and-levers-v1.json`, script
`scripts/analysis/slurp_throughput_baseline_and_levers.py` (byte-reproducible apart from `generated_at` and
the tokenizer-call count; run twice, receipts identical modulo those two fields). Zero model, server,
encoder, scorer and endpoint contacts: the resident llama-server on port 8080 was never queried; its own
`server.log` and `monitor.jsonl` were read, plus the sealed ROLL-2 trace, `/home/chao/batch-driver.out`
(read-only) and the three other 2026-09-26 sessions' monitors. Token counts for the constant classes come
from the vocab-only `llama-tokenize` binary the 2026-09-26 global-state audit used (380 distinct texts,
sha-keyed count cache); no utterance text, transcript, gold, knowledge body, model output or sample identifier is printed or
persisted. Gates: `bash scripts/flights/batch/main_gates_generic.sh` read-only on the main checkout, all
seven exit 0 (`finite_completion_policy`, `results_ledger`, `harness_admission`, `engineering_base`,
`tool_catalog`, `stage3_algorithm_label`, `stage3_effect_floor`).

## 0. What was measured, and the one premise it overturns

Run `SAEA-SLURP-STAGE3-ROLL-2-FOLD-A-V1` (1,080 rows x {Perception, 5 Solver samples, Reviewer, Planner} =
8,996 contacts, 81,435,827 sealed prompt tokens, 366,929 completion tokens) on the resident geometry `-np 4
-c 98304 -b 2048 -ub 512 -fa on -ctk/-ctv q8_0 --cache-prompt --cache-ram 0 --no-cache-idle-slots
--slot-prompt-similarity 0`, session started 2026-09-26T14:42:06Z. The server log is appended across
restarts with minute stamps that restart at each start (eight lifetimes in the file); only the last lifetime
was parsed, and its 8,996 tasks in the arm window match the 8,996 trace contacts one to one (join on
slot + order, verified by `prompt_tokens` and `completion_tokens`: 8,994 exact matches with the server's
constant -1 offset on the released prompt count, 2 contacts unmatched).

The premise "prefill owns the clock" assumed the 81.4 M prompt tokens were prefilled. They were not: the
per-slot KV prefix survives every hand-over the client makes, so **9,005,834 tokens (11.06 %) were
prefilled and 88.94 % came from cache**. What the clock is actually made of:

| contact window 16:01:48Z-18:18:56Z, 8,227.2 s (arm wall 8,558 s incl. smoke/seal) | seconds | share |
|---|---|---|
| at least one slot prefilling (1 slot: 2,700.7 s; 2: 958.3; 3: 273.1; 4: 41.3) | 3,973.3 | 48.3 % |
| decode only, no slot prefilling (1 slot: 301.1 s; 2: 559.7; 3: 1,046.4; 4: 1,280.0) | 3,193.3 | 38.8 % |
| every slot empty | 1,055.3 | 12.8 % |
| slot busy, no compute (speech-chunk decode, scheduling) | 5.2 | 0.1 % |

| slot capacity (4 slots x 8,227.2 s = 32,908.6 slot-seconds) | slot-s | share |
|---|---|---|
| prefill (sum of `prompt eval time`) | 5,601.5 | 17.0 % |
| decode (sum of `eval time`) | 16,530.6 | 50.2 % |
| in-slot overhead (busy minus compute) | 1,779.1 | 5.4 % |
| empty slot (release -> next launch on the same slot), of which client turnaround 7,287.3 | 8,997.4 | 27.3 % |

Some slot is prefilling half the time, but the prefill *work* is a sixth of slot capacity; decode is half of
it and the empty slot a quarter. Mean busy slots 2.906 of 4; all four slots decoded with none prefilling for
only 1,280 s (15.6 % of the window). Aggregate rates as flown: prefill 2,267 tok/s while any slot prefills;
decode 51.2 tok/s while the GPU computes (44.6 over the wall); **65.6 contacts/min = 3,936 contacts per
GPU-hour on the contact window, 3,783 on the arm wall**. The session monitor agrees (utilisation mean
75.4 %, parked 8.2 %, mean power 83.3 W under the 100 W enforced limit). The runtime records only end-to-end
client latency per contact (25,247 s summed, `COST.latency_seconds`), so the prefill/decode split is taken
from the server's own per-request `print_timing` lines, not derived from token counts.

## 1. Per role: prompt, prefill, decode, and what the cache already does

| role | n | prompt tok | prefilled | cached | cache share | prefill ms | decode ms | completion tok | first byte that differs from the previous prompt on the slot |
|---|---|---|---|---|---|---|---|---|---|
| Perception | 1,079 | 3,597 | 1,368 | 2,228 | 62.0 % | 637 | 4,478 | 117.9 | the speech packet (new row; only the 2,217-token contract carries over) |
| Solver #1 of 5 | 1,133 | 9,781 | 6,142 | 3,638 | 37.2 % | 3,402 | 2,146 | 24.4 | the first exemplar item (after the 8 boundary cards Perception already had); 53 second-pass Solvers differ at the Planner state |
| Solver #2-5 | 4,531 | 9,781 | 1 | 9,779 | 99.98 % | 78 | 1,090 | 24.4 | none: byte-identical prompt, seed differs |
| Reviewer | 1,133 | 9,767 | 247 | 9,518 | 97.5 % | 270 | 3,640 | 87.6 | the new Solver state |
| Planner | 1,118 | 9,907 | 256 | 9,650 | 97.4 % | 356 | 186 | 2.1 | the new Reviewer state |

Means per contact; prefilled/cached from `n_tokens` at release minus `eval` tokens minus `prompt eval`
tokens. Prefilled tokens by role: Solver#1 6,959,171 (77.3 % of all prefill work: the row's slot-contract
cards 5,359 tokens + exemplars 545 + the Perception state + its 208-token instruction), Perception 1,475,776
(16.4 %: its 8 boundary cards 1,124 + 188-token instruction + 50-token limits line), Reviewer 280,307 (3.1 %),
Planner 286,049 (3.2 %), Solver#2-5 4,531 (0.05 %). Slot-seconds by role (prefill / decode / client gap
before it): Perception 687 / 4,832 / 558; Solver#1 3,854 / 2,431 / **3,024**; Solver#2-5 355 / 4,937 / 2,167;
Reviewer 306 / 4,124 / 681; Planner 398 / 208 / 858.

**Prefix-cache reality (brief item 2).** The wire order is [system: task contract][user: speech packet,
`[evidence]` bodies in supply order, `[agent state]` texts, this node's instruction + limits], so every
later node's prompt is a byte-prefix extension of the previous contact on its slot up to the first new
state, and llama.cpp reuses exactly that: the Reviewer re-renders the 7,240-token supply block and pays 247
tokens for it; the Planner pays 256. The server's 4,531 "need to evaluate at least 1 token" full hits are
exactly the Solver samples 2-5. An independent reconstruction of the byte prefix from the sealed payloads
(system exact, packet from the log, the rest by each request's own chars-per-token) predicts the server's
cached count with a mean bias of +29 tokens (p50 0, p90 88, max 184; full hits predicted at prompt-2, the
contract-only hits at 2,217 vs the server's 2,224 template frame). Against that error the shortfall between
"every byte-identical block cached" and "cached as flown" is 63 tokens per Reviewer contact, 72 per Planner,
103 per Solver#1 -- **inside the estimator's bias, i.e. nil**. The only structural miss is Perception's 362
tokens: boundary cards the previous row on the slot also carried, in a different position; a pure-prefix
cache cannot reach them across rows and `--cache-reuse` (KV shift) would change the arithmetic. What could
have been served from cache for Reviewer and Planner was 97.5 % and 97.4 % of their prompts, and it was.
The lever the brief named does not exist as flown; the Solver#1 supply block is new content per row and
must be prefilled once, which it is.

**Decode batch scaling, measured from the same intervals** (each request at its own `eval` rate, no slot
prefilling): 1 slot 47.2 tok/s; 2 slots 57.4 (28.7 per slot); 3 slots 77.6 (25.9); 4 slots 107.5 (26.9).
From two slots up the per-slot rate is flat, so aggregate decode grows almost linearly with occupied slots
-- which is why the empty slot is the lever. A concurrent prefill halves the others' decode: with one slot
prefilling the decoding slots run at 11.4 / 14.8 / 16.8 tok/s each (1 / 2 / 3 decoding).

## 2. Slot geometry ceiling (brief item 3)

This featcache build's `server.log` carries the server's own lines only (the llama library's KV-buffer
lines go to a startup stdout the session merely hashes), so the KV cost is read from nvidia-smi instead:
four 2026-09-26 sessions (np2 and np1 at 49,152 total context: 20,410 / 20,434 / 20,410 MiB after load; np4
at 98,304: 22,954) plus the three 2026-09-19 calibration points fit **53.1 KiB per token at q8_0 K+V with
flash attention, intercept 17,868 MiB**; the device reported 24,462 MiB with **23,119 MiB free at load**.
As flown the model sits at 22,744-22,976 MiB idle (estimate 22,966; margin +153 MiB); nvidia-smi's peak
over the day was 23,988 MiB because it counts every process on the card.

| geometry | total context | q8_0 KV: MiB est. / margin | q4_0 KV (28.11 KiB/token, derived, unflown): MiB est. / margin |
|---|---|---|---|
| np4 x 24,576 (as flown) | 98,304 | 22,966 / +153 | 20,567 / +2,552 |
| np5 x 24,576 | 122,880 | 24,241 / -1,122 | 21,242 / +1,877 |
| np6 x 24,576 | 147,456 | 25,515 / -2,396 | 21,917 / +1,202 |
| np8 x 24,576 | 196,608 | 28,064 / -4,945 | 23,266 / -147 |
| np4 x 32,768 | 131,072 | 24,666 / -1,547 | 21,467 / +1,652 |

At q8_0 nothing wider than np4 fits; np6 x 24,576 and np4 x 32,768 fit only with q4_0 KV, np8 fits with
neither. Given section 1's scaling curve, np6 would add decode capacity worth having -- but today four slots
are simultaneously decoding for 15.6 % of the window, so more slots buy nothing until the dispatcher keeps
the existing four loaded, and q4_0 KV is a change to the core's arithmetic (new serving identity, every
comparator re-anchored): owner ruling plus a no-harm read, and no number is claimed for it here.

## 3. Prompt-length levers that preserve information (brief item 4)

A prompt token costs prefill only when it is not cached, so every row below is weighted by each contact's
prefilled share (Solver#1 pays for the supply block; Reviewer/Planner pay only for their tail). Tokens are
exact for labels (60 + 54 distinct ids exact, 200 of 4,990 exemplar ids sampled at 15.3 each), cards,
instructions and limits lines; repeated lines use each request's own chars-per-token.

| lever | tokens on the wire per contact | prefill actually saved | est. gain | what a node loses | class |
|---|---|---|---|---|---|
| (c) slot-contract cards whose slot type **no Perception candidate intent** of the row can carry (schema `slurp-intent-slot-schema-v1`, train-derived, gold-free): 4.0 of 11.8 cards | 1,647 (later contacts) | 536.8 s | **+7.0 %** | cards about types the row's own candidates exclude; Reviewer/Planner still see every card the Solver saw | selection (form) -> no-harm cell; the owner's global-state ruling does not forbid it |
| (d) content lines repeated across evidence items within one contact (10 distinct lines, restated in card after card) | 1,139 | 507.7 s | +6.6 % | nothing factual; the same sentence once instead of twelve times | form -> no-harm cell |
| (a) `[evidence <id>] ` labels (14-15 tokens each; 529 per contact averaged over roles, 608 on later contacts) | 529 | 218.5 s | +2.7 % | the addressable id nodes cite in `evidence_refs` | form -> no-harm cell |
| (d) heading-like repeated lines (<= 40 chars or ending ":") | 239 | 102.2 s | +1.3 % | card structure | form -> no-harm cell |
| (b) `Native episode limits:` JSON (always in the prefilled tail) | 50 | 25.7 s | +0.3 % | remaining revisions / actions the Planner reads | form -> no-harm cell |
| whitespace runs inside evidence bodies | 0 | 0 | 0 | nothing | (none present) |
| node instructions: Perception 188, Solver 208, Reviewer 82, Planner 36 tokens, prefilled every contact = 1.51 M tokens, 16.8 % of all prefill | -- | -- | -- | information-bearing; not a lever, listed for completeness | -- |

The synth analysis's "90.6 % of card characters describe types not in play" needs gold to compute; the
gold-free part of that selection -- whole cards whose type no candidate can carry -- is the +7.0 % row. The
same measurement on the **output** side, from the sealed response texts: Perception's JSON is 20.7 %
whitespace and newlines by characters (compact JSON would cut up to 26,300 decode tokens, worth up to 514.8 s
= +6.7 % if whitespace tokenised one-for-one, an upper estimate); the Reviewer's tool-call JSON 8.7 %
(+2.1 %); Solver and Planner outputs are already compact; string values repeated across Perception's
candidates are 0.26 % of its characters (nil).

## 4. The day: where the card waited (brief item 5)

2026-09-26 UTC, minute by minute, busy = any monitor sample with utilisation >= 5 % or a busy slot (four
sessions' monitors merged); driver state from `batch-driver.out`.

| driver state | minutes | GPU busy | GPU idle | unmonitored |
|---|---|---|---|---|
| in flight (arm-start -> arm-exit; ROLL-2 143, conv 5, seventeen np1/np2 system cells 78) | 226 | 162 | 64 | 0 |
| between drivers, nothing registered | 785 | 17 | 745 | 23 |
| between drivers, stopped or killed, waiting on a human | 421 | 0 | 33 | 388 |
| prelaunch + smoke, inspect + seal, driver idle between steps | 8 | 3 | 5 | 0 |
| **day** | **1,440** | **182 (12.6 %)** | **847** | **411** |

The unmonitored minutes are 00:00-06:28Z, when no session monitor ran after the 2026-09-25 23:17Z STOP; a
server was resident for 1,285 minutes of the day. The three long gaps: 00:00-06:28Z after the STOP (6.5 h),
12:15-15:58Z with the 14:42Z session switch inside it (3.7 h), 18:23-23:55Z after ROLL-2 sealed (5.5 h). Of
the 64 idle in-flight minutes, ROLL-2 contributed 17.6 (its 12.8 % all-slots-empty time); the rest are the
np1/np2 system cells, whose pipelines are CPU-bound. The arm-level overhead around ROLL-2's contact window
(smoke, preflight, seal) was 331 s (3.9 %). In owner terms: flying, the card delivers 3,936 contacts per
hour; over the day it delivered roughly 9,400 contacts (ROLL-2's 8,996 plus the small cells) in 24 hours, a
tenth of that, and 83.8 % of the day it was waiting for a person to register, read or recover.

## 5. Ranked levers (each estimated alone against 3,936 contacts per GPU-hour)

Prefill savings are priced at the measured 2,267 tok/s, decode savings at 51.2 tok/s, wall savings directly.

| # | lever | contacts / GPU-h | gain | what it changes for the nodes | what it needs |
|---|---|---|---|---|---|
| 1 | **keep every slot loaded**: no empty slot-seconds (async dispatch across rows; the Solver#1 gap 3,024 slot-s, the sample-to-sample gaps 2,167, every other hand-over 2,097) | <= 5,416 | up to +37.6 % (upper bound: per-slot service unchanged; the measured 2->4-slot scaling says batching is near-linear, concurrent prefill contention says the bound is not reached) | nothing in the bytes; batch composition changes | runtime change + own-null read of batch-composition noise (the E21 dispatcher precedent) |
| 1a | ... of which: no all-slots-empty time (1,055 s) | 4,515 | +14.7 % | nothing | runtime change |
| 1b | ... of which: start the Solver#1 supply acquisition while Perception decodes (2.67 s x 1,133) | 4,334 | +10.1 % | nothing | runtime change |
| 2 | drop slot-contract cards no candidate intent of the row can carry | 4,210 | +7.0 % | removes cards about excluded types | form (selection) -> no-harm cell |
| 3 | compact Perception JSON output | <= 4,198 | <= +6.7 % | same parsed candidates; the core's sampling path changes | form (output) -> no-harm cell |
| 4 | state each repeated content line once per contact | 4,194 | +6.6 % | same facts once | form -> no-harm cell |
| 5 | prefix cache: every byte-identical block cached (the brief's hypothesis) | <= 4,079 | <= +3.7 %, inside the estimator's +29-token bias: nil | nothing | nothing -- already realised as flown |
| 6 | remove or shorten `[evidence <id>] ` labels | 4,043 | +2.7 % | the addressable ids | form -> no-harm cell |
| 7 | compact Reviewer tool-call JSON | 4,018 | +2.1 % | as 3 | form (output) -> no-harm cell |
| 8 | repeated heading-like lines | 3,985 | +1.3 % | card structure | form -> no-harm cell |
| 9 | `Native episode limits:` line | 3,948 | +0.3 % | Planner-read state | form -> no-harm cell |
| 10 | np6 x 24,576 with q4_0 KV (the only wider geometry that fits) | not estimable here | decode scaling 57 -> 108 tok/s from 2 to 4 slots suggests capacity; worthless until #1 | the core's KV arithmetic | flown session + owner ruling on serving identity + no-harm read |
| 11 | whitespace runs in evidence bodies | 3,936 | 0 | -- | (none present) |
| -- | the day: 1,206 of 1,440 minutes waiting on people | ~8x the day's realised rate (12.6 % -> 100 % busy) | -- | nothing | a queue that is never empty (decision 77's driver is the mechanism; the queue is the gap) |

Levers 1, 2, 3 and 4 are independent in mechanism (empty slots, prefill volume, decode volume) and would
compound; no combined figure is claimed because 1 changes the contention regime the others were priced in.
Nothing here was changed, registered or flown.

## 6. Method notes and limits

* Server-side times are llama.cpp's own `prompt eval time` / `eval time` per task; the union-of-intervals
  decomposition places each task's prefill at [release - eval - prompt, release - eval] and its decode after
  it, and the batch-scaling table assumes each request decodes at a constant rate over its own interval.
* Prefilled/cached tokens are exact from the server (`n_tokens` at release - `eval` tokens - `prompt eval`
  tokens; the server's release count is prompt_tokens - 1 on all 8,994 joined contacts). The byte-prefix
  reconstruction is used only to attribute *why* a prefix ended and to bound what a re-order could add; its
  bias against the server's exact count is +29 tokens mean, and every "shortfall" below 200 tokens is
  reported as nil for that reason.
* Prompt-length levers convert characters to tokens with each request's own ratio except where the class was
  tokenised exactly (labels, cards, instructions, limits, the contract); output compaction converts
  whitespace characters one-for-one into tokens and is therefore an upper estimate.
* The day table treats a minute with no monitor sample as unmonitored, not idle; 388 of the 411 unmonitored
  minutes fall inside a window in which the driver was stopped and no flight ran.
* Two of 8,996 contacts did not join (one Perception, one Planner: their server tasks fell outside the
  four-task lookahead); all totals above are over the 8,994 joined contacts except where the sealed manifest
  is quoted.
* Not measured, not claimed: the gain of raising the 100 W enforced power limit (host setting, byte-neutral;
  the 2026-09-19 geometry report's lever 2), and the real per-slot decode rate at np6.
