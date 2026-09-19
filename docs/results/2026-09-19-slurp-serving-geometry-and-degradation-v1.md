# SLURP serving geometry and graceful degradation: batch scaling after lever L1, and memory-borrowing options (owner decision 45)

Date: 2026-09-19. Author: Fable 5.1 (checker phase). Branch `fable/geometry`. Companion receipt:
`docs/receipts/slurp-serving-geometry-analysis-v1.json`. Predecessor:
`docs/results/2026-09-19-slurp-throughput-root-cause-v1.md` (owner decision 41). Model-free: zero
model, tokenizer, encoder and server contacts; zero GPU processes started, stopped, restarted or
queried; `nvidia-smi` read for host facts only. The in-flight campaign
`SAEA-SLURP-NATIVE-TOOL-CONSTANT-ANCHOR-TRAIN-FOLD-A-V1` (cell EFF-1) was running throughout and its
run directory was **not opened** -- every post-L1 number below is read from the **serving session's
own** `server.log` and `monitor.jsonl`, which the owner brief permits. No utterance text and no gold
appear here or in the receipt.

## 0. Verdict in one paragraph

**(a) No.** Increasing the batch does not bring a stable inference-throughput gain, and the reason
is that lever L1 did not remove the prefill bound -- it removed most of the prefill *work*. On the
measured post-L1 window the machine still turns prefill tokens into seconds at the same rate it
always did (per-request median 2,248 tok/s, unchanged from the pre-L1 2,051-2,286), but the row now
presents 9,906 prefilled tokens instead of 24,500-33,000, so the *aggregate* prefill rate fell from
2,024-2,108 tok/s to 1,646 -- **below** the machine ceiling rather than pinned to it. Decode rose
from 14.8-21.6 to 36.6 tok/s aggregate, 62 % of the measured np4 decode ceiling of 59.4. The flight
is therefore **co-bound**: prefill at roughly 80 % of its ceiling and decode at 62 % of its own,
contending for one GPU with a fitted overlap efficiency of 0.647. Adding slots raises only the
decode ceiling, which is the smaller of the two terms, so the model says np6 buys **+7.5 %** and np8
**+11.8 %** -- and at q8_0 KV neither geometry fits: np6's 16,384-token slot leaves 14,336 usable
after the gate's one-eighth reserve, against a measured post-L1 maximum prompt of 14,524, and np8's
12,288-token slot fails even the p90. **Keep `-np 4 -c 98304`.** The two levers that do move the
machine rate are not the batch: the enforced GPU power limit is **100.00 W against a 175.00 W
maximum** (now read directly, no longer an inference), and `-ub` has never been flown above
512. **(b) Yes, but not on the server.** WSL 2 forbids exactly the mechanism "memory borrowing"
     would need -- NVIDIA states that "Oversubscription of GPU memory is not allowed" under the
     limited unified-memory paradigm that Windows and WSL fall under, and llama.cpp's
     `GGML_CUDA_ENABLE_UNIFIED_MEMORY` does nothing but swap `cudaMalloc` for `cudaMallocManaged`,
     so on this host it would fail the allocation rather than spill to the 43 GB of WSL RAM.
     Graceful degradation must therefore be built in the harness, and today there is none: preflight
     raises `FlightRuntimeError` on anything but `ALLOW`, and at dispatch there is no budget check
     at all -- `_default_post` calls `urllib.request.urlopen` with no exception handling, so the
     server's HTTP 400 `exceed_context_size_error` propagates and kills the flight. The fix is a
     per-request **COMPACT disposition** modelled exactly on the E13 finite-completion row, plus
     `-ctk/-ctv q4_0` held in reserve as the only way to widen the slot without giving up
     parallelism.

## 1. What was measured, and how

### 1.1 Sources

| source | what it gave |
|---|---|
| `serving/serving-slurp-native-candidate-five-train-a-np4-v1/server.log` (736,304 lines, 80.3 MB) | per request: `prompt eval time = X ms / N tokens`, `eval time`, `slot release: ... n_tokens, truncated = 0`, `slot launch_slot_`, `slot process_mtmd` speech-packet decodes |
| the same session's `monitor.jsonl` (22,891 samples, 2026-09-16 -> 2026-09-19) | GPU utilisation, power, pstate, VRAM, busy slots, host memory |
| the same session's `session.json` / `session-receipt.json` | launch argv, props, `slot_n_ctx = 24576`, `total_slots = 4`, binary and GGUF hashes |
| every other session's `session.json` + `monitor.jsonl` under `SPEECHRL_DATA_DIR/serving/` | the measured VRAM-versus-total-context curve across 14 distinct geometries |
| `nvidia-smi -q -d MEMORY,POWER`, `/proc/meminfo`, `uname -a`, `/usr/local/cuda*/bin/nvcc` | host and device facts |
| the built fork `/home/chao/llama.cpp-featcache` at commit `04ccc72a2207347ca76161b93fd9d846dd0a8675` | which options and error paths the **running binary** actually has, read from source rather than from upstream docs |
| `docs/receipts/slurp-throughput-root-cause-v1.json` | the sealed per-role prompt distributions of the four native runs, and the np4/np8 decode ceilings, carried forward unchanged |

The `server.log` timestamps are `MM.SS.mmm.uuu` with unbounded minutes and restart at each server
launch. The final segment begins at line 411,069 and its epoch anchor is the session's own
`started_at`, 1789742596.612345 = 2026-09-18T14:43:16Z. The anchor is confirmed two ways: the last
parsed record lands at 2026-09-19T15:39:28Z against a last monitor sample of 15:38:58Z, and the B4a
v2 arm window it produces (16,983 s, 5,409 requests) reproduces that arm's sealed flight cost to
three digits -- 5,409/19.11 per minute = 4.72 GPU-hours, against the **4.721 GPU hours** its own
seal records at commit `682ee52d`.

### 1.2 Contacts per minute: two counters, one of them wrong

`monitor.jsonl` carries a cumulative `requests_total`. It **undercounts**: over the B4a v2 arm it
advances 4,466 where the server completed 5,409 requests and the seal records 5,412 contacts. Its
ratios are not safe either -- it reports the post-L1 gain as +32 % where the server log reports +102
%. **Every throughput number in this report is counted from `server.log` release records**, and
`monitor.jsonl` is used only for utilisation, power, busy slots and VRAM, which it samples directly.

## 2. Part A -- batch and slot scaling

### 2.1 The regime after L1, measured

Five windows of the same resident session, same model, same binary, same geometry. The first four
are pre-L1; the last is the EFF-1 constant-tool-rendering arm, in flight.

| window | dur s | reqs | **contacts/min** | prefilled/req | cached | agg prefill tok/s | agg decode tok/s | packet re-decode | lat p50 | lat p90 | lat p99 | prompt p50 | p99 | max | trunc |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B5e recovery (18th, 15:28-19:25Z) | 14,226 | 5,414 | 22.83 | 5,347 | 42.7 % | 2,035 | 17.86 | 60.1 % | 8.93 | 15.74 | 21.71 | 10,296 | 14,491 | 18,018 | 0 |
| B2 samples5 v3 (18th-19th, 20:38-00:21Z) | 13,358 | 9,802 | 44.03 | 2,615 | 69.7 % | 1,919 | 27.24 | 33.2 % | 3.92 | 11.02 | 18.03 | 9,115 | 13,007 | 14,644 | 0 |
| NCP-L1 anchor v2 (19th, 05:18-09:05Z) | 13,596 | 5,615 | 24.78 | 4,902 | 44.4 % | 2,024 | 21.58 | 59.5 % | 7.56 | 17.81 | 24.80 | 9,579 | 14,151 | 17,358 | 0 |
| B4a v2 (19th, 09:41-14:24Z) | 16,983 | 5,409 | 19.11 | 6,619 | 40.1 % | 2,108 | 14.80 | 60.0 % | 10.42 | 22.04 | 29.66 | 12,398 | 15,225 | 17,371 | 0 |
| **EFF-1 post-L1 (19th, 14:41-15:39Z)** | 3,481 | 2,912 | **50.20** | **1,972** | **75.3 %** | **1,650** | **36.62** | **20.4 %** | **3.54** | **9.31** | **12.97** | 8,573 | 12,816 | 14,524 | 0 |

Sub-windows of EFF-1: the first 15 minutes run at **53.34** contacts/min and the last 30 at
**48.14**. The owner brief's early sample of 53.5 against 23.5-24.2 is therefore corroborated to
within noise for the *rate* -- the honest comparator is the NCP-L1 anchor's 24.78, the arm the EFF-1
cell is the one-factor twin of, and the ratio is **2.03x**. The brief's "GPU utilisation 98 % -> 60
%" is **not** corroborated: over 307 monitor samples of the EFF-1 window the mean is **88.6 %**, the
median 94 %, the p10 69 %, and no five-minute bucket falls below 85 %. The pre-L1 comparator is 93.0
% (B4a) and 86.4 % (anchor, which had a 6.3 % zero-busy share). 60 % is a tail sample, not the
regime.

| monitor window | util mean | util median | util p10 | zero-busy | power mean W | power max W | busy slots | all-4 share | VRAM MiB |
|---|---|---|---|---|---|---|---|---|---|
| NCP-L1 anchor v2 | 86.4 | 97 | 65 | 6.34 % | 88.94 | 97.47 | 3.525 | 74.7 % | 22,976 |
| B4a v2 | 93.0 | 98 | 82 | 0.14 % | 94.58 | 97.33 | 3.752 | 79.3 % | 22,976 |
| **EFF-1 post-L1** | **88.6** | 94 | 69 | 0.65 % | **92.10** | 97.22 | 3.511 | 63.2 % | 22,976 |

### 2.2 Which bound now

L1 did not raise the machine's prefill rate and was never going to: the **per-request** prefill rate
is 2,248 tok/s median post-L1 against 2,051 (B4a) and 2,286 (anchor) -- the same number, with the
same 20-27 % spread. What changed is how many tokens the row presents: 9,906 prefilled per row
against 24,500-33,000, because the constant tools array stops toggling the system message and the
pinned slot's KV prefix survives the role handover (cached share 40-44 % -> 75.3 %, speech-packet
re-decode 60 % -> 20.4 %, which is one decode per row plus a fifth).

The consequence is that **the aggregate prefill rate fell off its ceiling**. Pre-L1 it sat at
2,024-2,108 tok/s, i.e. pinned to the single-stream capability; post-L1 it is 1,646-1,655, about 80
% of it. Meanwhile aggregate decode rose to 36.6 tok/s, **62 %** of the np4 decode ceiling of 59.4
tok/s measured on the decode-dominated direct baseline. Neither resource is saturated and both are
heavily used, which is the signature of contention, not of a single bound.

A two-resource model fits it. With `P` = 2,100 tok/s (the measured aggregate prefill ceiling) and
`D` = 59.4 tok/s (the measured np4 decode ceiling), prefill alone would allow 2,100/9,906 x 60 =
**12.72 rows/min**, decode alone 59.4/219 x 60 = **16.24 rows/min**; fully serialised that is 7.13
rows/min and perfectly overlapped 12.72. Measured: **9.97 rows/min**, which places the overlap
efficiency at **0.647** -- llama.cpp does put decode tokens in the same micro-batch as a prefill
chunk, but only up to four of them, so about a third of the decode work still waits for a free
batch. **What more slots buy.** Slot count raises `D` and leaves `P` exactly where it is -- the np8
sessions in this study's history reach the same per-request prefill maximum as the np4 ones (2,833 /
2,505 / 3,126 tok/s; section 4 of the predecessor report). Holding the fitted overlap constant:

| geometry | decode ceiling tok/s | prefill-only rows/min | decode-only rows/min | modelled rows/min | modelled contacts/min | vs np4 | GPU-h / 1,080 rows | 13,078-row read |
|---|---|---|---|---|---|---|---|---|
| np4 (today) | 59.4 measured | 12.72 | 16.24 | **9.97 measured** | **50.2 measured** | -- | **1.79** | **21.7 h** |
| np6 | 87.7 interpolated | 12.72 | 23.98 | 10.71 | 53.6 | +7.5 % | 1.68 | 20.4 h |
| np8 | 115.9 measured | 12.72 | 31.69 | 11.14 | 55.7 | +11.8 % | 1.62 | 19.6 h |

A doubling of slots buys a ninth. That is the whole answer to question (a) on the throughput side,
and the fit gate answers it again on the memory side.

### 2.3 VRAM: a fully measured calibration

Fourteen distinct geometries have been served on this machine, all `-ngl 999`, and their resident
VRAM is a straight line in total context and **independent of slot count**:

| total context `-c` | np | mmproj | measured `memory_used_mib` |
|---|---|---|---|
| 36,864 | 4 | `--no-mmproj` | 19,776 |
| 36,864 | 6 | `--no-mmproj` | 19,752 - 19,774 |
| 65,536 | 4 | `--no-mmproj` | 21,250 - 21,299 |
| 65,536 | 8 | `--no-mmproj` | 21,264 |
| 98,304 | 3 | `--no-mmproj` | 22,962 - 22,984 |
| 98,304 | 4 | `--no-mmproj` | 22,976 |

Slope: 1,496 MiB over 28,672 tokens = 53.43 KiB/token; 1,704 MiB over 32,768 tokens = 53.25. Take
**53.30 KiB/token** at q8_0 K and V with flash attention on. Intercept, from all three points:
**17,857 / 17,861 / 17,859 MiB** -- call it 17,857 MiB of model plus compute buffers. `-np` moves
nothing, which is exactly what `n_ctx_seq = n_ctx / n_seq_max` predicts and what the fork's own
`src/llama-context.cpp:232` does.

The envelope is **not** the 24,463 MiB the card reports. llama.cpp's own `device_info` line at this
session's load says `NVIDIA GeForce RTX 5090 Laptop GPU (24462 MiB, 23119 MiB free)`: WDDM and the
desktop already hold 1,343 MiB. So the usable ceiling is **23,119 MiB**, and the largest total
context that fits is **101,094 tokens at q8_0** -- not the ~119,000 the predecessor report estimated
from the nameplate. The geometry flown since 2026-09-18 sits at 22,976 MiB, leaving 143 MiB. For
q4_0 the block is 18 bytes per 32 elements against q8_0's 34, so KV would cost **28.22 KiB/token**
and the ceiling would be **190,955 tokens** -- **derived, never flown**; no session in this study
has ever used a KV type other than q8_0.

### 2.4 The constraint table

The gate is `rails.context_budget`. Since E17 (2026-09-19) an undeclared budget is bound to the
**live** slot rather than to the 32,768-token module default, and its reserve is `min(8192, slot //
8)` below 32,768 (`serving_bound_reserve_tokens`). A request must fit `slot - reserve`, where the
required window is rendered text + speech packet + 2 special tokens + the 512-token completion
ceiling.

Holding the proven 98,304-token total (VRAM 22,974 MiB, unchanged):

| np | slot | reserve | usable | VRAM MiB | post-L1 p99 12,816 | p99.9 13,930 | max 14,524 | pre-L1 max 17,371 |
|---|---|---|---|---|---|---|---|---|
| **4** | **24,576** | **3,072** | **21,504** | **22,974** | fits | fits | **fits** | fits |
| 5 | 19,456 | 2,432 | 17,024 | 22,920 | fits | fits | fits | refused |
| 6 | 16,384 | 2,048 | 14,336 | 22,974 | fits | fits | **refused (-188)** | refused |
| 8 | 12,288 | 1,536 | 10,752 | 22,974 | refused | refused | refused | refused |

Pushing the total to the 23,119 MiB envelope moves the needle by one 256-token step and changes no
verdict: np6 reaches a 16,640-token slot (14,560 usable, still 36 tokens short of the post-L1
maximum) and np8 a 12,544-token slot. With q4_0 KV the picture inverts -- np6 x 31,744 and np8 x
23,808 both fit inside 23,105 MiB -- but that is an unflown KV type on an unmeasured quality risk,
and it is listed in Part B as a degradation reserve, not as a throughput recommendation.

Note the asymmetry the table exposes: **np6 is refused by 188 tokens.** One over-long row in 2,912
is the whole objection -- precisely what Part B's COMPACT disposition is for, which is why the two
halves of decision 45 are one question.

### 2.5 Batched prefill: `-b` and `-ub`

The build is `b8-04ccc72a2`, running `-b 2048 -ub 512`. `-ub` is the physical micro-batch; llama.cpp
defaults it to 512 and every session in this study has used 512 (or 128 on the single-slot encoding
sessions). One committed fragment,
`configs/model/q4km-mmproj-free-speech-native-np16-b4096-ub1024-max64.json`, declares `-ub 1024`,
but no serving session in `SPEECHRL_DATA_DIR/serving/` records having flown it, so there is **no
measured comparison and no VRAM figure** for a larger compute buffer on this model. What the
measurements do say is that there is no fixed-overhead recovery available: the per-request prefill
rate is flat to gently declining with prompt size, and post-L1 it is 2,248 tok/s median and 2,835 at
maximum on prompts whose median prefill is 1,757 tokens -- several micro-batches already. A larger
`-ub` can only help by raising GPU occupancy within a micro-batch, and it costs VRAM out of a 143
MiB margin, so `-c` must drop to pay for it.

### 2.6 Stability

| arm | buckets | mean c/min | s.d. | **CV** | min | max | full re-prefill (cached <= 64) | prompts >= 12k | slot balance max/min | p99/p50 latency | per-request prefill-rate s.d./median |
|---|---|---|---|---|---|---|---|---|---|---|---|
| NCP-L1 anchor v2 | 45 | 24.79 | 2.60 | 0.105 | 20.6 | 29.6 | **0.0 %** | 13.8 % | 1.046 | 3.28 | 0.244 |
| B4a v2 | 56 | 19.11 | 0.57 | **0.030** | 17.4 | 20.4 | **0.0 %** | 59.1 % | 1.074 | 2.85 | 0.269 |
| EFF-1 post-L1 | 11 | 50.45 | 3.55 | 0.070 | 41.4 | 54.0 | **0.0 %** | 5.5 % | 1.048 | **3.67** | **0.206** |

* **Prefix-cache misses on slot reassignment are not a source of variance here.** Not one request in
  any arm lost its whole prefix: the client pins `id_slot` per sample and `--slot-prompt-similarity
  0` disables llama.cpp's own routing, so a row owns a slot for its whole trajectory, and slot
  balance is 1.046-1.074. **A geometry change would break this** -- with more slots than the
  dispatcher's in-flight depth, some slots idle and rows land on cold ones.
* **Long-tail prompts occupying a slot** are the visible term: EFF-1's p99/p50 latency ratio is the
  worst of the three (3.67) even though its absolute latencies are two to three times better,
  because a 14.5k-token row now sits beside 8.5k-token neighbours instead of 12.4k ones. At np6 that
  same tail is what pushes a row past the gate.
* **Variation within an arm is roster composition, not geometry.** EFF-1 declines 52.4 -> 41.4 over
  55 minutes and the anchor 27 -> 21 over four hours; B4a, whose prompts are nearly uniform, is flat
  at CV 0.030. Post-L1 the CV is 0.070, between the two pre-L1 arms -- **L1 did not destabilise
  throughput.**
* **Greedy decoding is not bitwise reproducible across batch compositions**, so a geometry change is
  a **serving-session change**: new session identity, new receipt, re-anchored comparator. It may
  never be introduced mid-cell and is never an effectiveness factor -- no arm may be compared across
  geometries.

### 2.7 Ranked recommendation

| rank | change | expected contacts/min | GPU-h / 1,080 | 13,078-row read | status | risk |
|---|---|---|---|---|---|---|
| 1 | **Keep `-np 4 -c 98304 -b 2048 -ub 512 -ctk/-ctv q8_0`** | 50.2 | 1.79 | 21.7 h | MEASURED | none; it is the flying geometry |
| 2 | Raise the enforced power limit 100 W -> 175 W (host setting, byte-neutral) | 58-70 modelled | 1.28-1.55 | 15.5-18.8 h | **limit VERIFIED, gain UNMEASURED** | medium: thermals, fan mode, and the 2026-09-08 P-state lesson; a serving change with a receipt |
| 3 | `-ub 512 -> 1024`, `-c` reduced to pay for it | unknown | unknown | unknown | UNMEASURED | low-medium; costs VRAM from a 143 MiB margin |
| 4 | np6 x 16,384 at q8_0 | 53.6 modelled (+7.5 %) | 1.68 | 20.4 h | MODELLED, **and refused by the fit gate** | high: 188 tokens short of the measured maximum prompt; needs COMPACT first |
| 5 | np8 x 12,288 at q8_0 | 55.7 modelled (+11.8 %) | 1.62 | 19.6 h | MODELLED, **fails at p90** | prohibitive |
| 6 | np6/np8 with `-ctk/-ctv q4_0` | as 4/5 | as 4/5 | as 4/5 | DERIVED only | high: unflown KV type, unmeasured effect on outputs |

The honest reading for the owner: **the batch is not where the remaining time is.** L1 already took
the read from 44 h to an expected 21.7 h. The next 20-30 % is in the power cap, which is a host
setting and not a repository change; the next factor after that is still L3 (shrink the supplied
evidence block), which is effectiveness-bearing and belongs to a cell, not to a geometry.

## 3. Part B -- graceful degradation

### 3.1 Server-side memory borrowing is not available on this host

The question is whether an over-long sequence can be made to *slow the service down* rather than
fail, by letting the GPU borrow host memory. On WSL 2 the answer is no, and NVIDIA says so directly.

NVIDIA, *CUDA on WSL User Guide* (last updated 2026-09-13; read 2026-09-19),
<https://docs.nvidia.com/cuda/wsl-user-guide/index.html>, section 5.1 "Known Limitations for Linux
CUDA Applications" -- verbatim table cells (two more in the receipt):
> "Unified Memory - Full Managed Memory Support is not available on Windows native and therefore
> WSL 2 will not support it for the foreseeable future."
> "If your application is using Managed Memory, your application could see reduced performance and
> high system memory usage."
> "Pinned system memory (example: System memory that an application makes resident for GPU
> accesses) availability for applications is limited."

NVIDIA, *CUDA Programming Guide* (last updated 2026-09-10; read 2026-09-19), section 2.6.2.3
"Limited Unified Memory Support" and its decisive bullet
(<https://docs.nvidia.com/cuda/cuda-programming-guide/02-basics/understanding-memory.html>):
> "On Windows, including Windows Subsystem for Linux (WSL), and on some Tegra systems, a limited
> subset of unified memory functionality is available. On these systems, managed memory is
> available, but migration between CPU and GPUs behaves differently."
> "Oversubscription of GPU memory is not allowed"

-- against the contrasting bullet of 2.6.2.2 "Full Unified Memory Feature Support", the Linux HMM
case and not this one, and section 4.1.3 "Unified Memory on Windows, WSL, and Tegra"
(<https://docs.nvidia.com/cuda/cuda-programming-guide/04-special-topics/unified-memory.html>):
> "Oversubscription is allowed: an application may allocate more managed memory than is physically
> available on the GPU"
> "GPU Memory Oversubscription: They cannot allocate more managed memory than the physical size of
> GPU memory." (4.1.3 also states that on-demand migration is unsupported and that "Page faulting is
> only supported from the CPU side"; both are verbatim in the receipt.)

llama.cpp's own lever is exactly the mechanism those sentences forbid -- `docs/build.md`, CUDA ->
Unified Memory, and the code, verified in the **built fork** at
`/home/chao/llama.cpp-featcache/ggml/src/ggml-cuda/ggml-cuda.cu`, not only upstream:
> "The environment variable `GGML_CUDA_ENABLE_UNIFIED_MEMORY=1` can be used to enable unified memory
> in Linux. This allows swapping to system RAM instead of crashing when the GPU VRAM is exhausted.
> In Windows this setting is available in the NVIDIA control panel as `System Memory Fallback`."
> `if (getenv("GGML_CUDA_ENABLE_UNIFIED_MEMORY") != nullptr) { err = cudaMallocManaged(ptr, size);`

There is no `cudaMemPrefetchAsync` anywhere in that file and the only `cudaMemAdvise` is a HIP-only
coarse-grain hint, so on this host the variable would allocate managed memory that, per NVIDIA,
cannot exceed physical VRAM and cannot fault in on demand: the allocation fails instead of spilling.
**Do not set it.** Host facts for the record -- WSL kernel `6.6.87.2-microsoft-standard-WSL2`, VM
RAM 43.1 GiB with 16 GiB of swap, Windows host 63.4 GB, driver 592.01, `nvidia-smi` CUDA 13.1,
`nvcc` at `/usr/local/cuda-12.8` and `/usr/local/cuda-13.0`. The remaining server-side options are
**capacity**, not borrowing. `-nkvo` / `--no-kv-offload` ("whether to enable KV cache offloading
(default: enabled)", present in the fork) moves the KV cache off the GPU entirely; `-ngl` below all
layers gives "CPU+GPU hybrid inference to partially accelerate models larger than the total VRAM
capacity". Both degrade everything, all the time, by putting reads across PCIe, for an event that is
rare by construction. `--cache-reuse N` ("min chunk size to attempt reusing from the cache via KV
shifting") and `/slots/{id}?action=save|restore|erase` address prefix reuse and slot persistence,
not over-long requests; context shift is "disabled by default" and is a generation mechanism, not a
prompt-fit one. The one option that makes an over-long prompt *fit* rather than making the service
slower is `-ctk/-ctv q4_0` ("allowed values: f32, f16, bf16, q8_0, q4_0, q4_1, iq4_nl, q5_0, q5_1"),
which at 28.22 KiB/token buys a 1.89x wider slot at the same VRAM -- an unflown KV type whose effect
on outputs is unmeasured, so it belongs in reserve behind a measured cell, never as a silent
default.

### 3.2 What happens today to an over-long request

**At preflight.** `core/flight/runtime.py:_assess_prompt_budget` renders the widest request the
roster produces for each phase, asks `rails.context_budget.assess_context_budget` with the live
`slot_tokens`, and then raises `FlightRuntimeError` on anything but `ALLOW` -- its own comment says
"A pre-flight estimate has no live compaction mechanism to apply, so COMPACT_REQUIRED is just as
fail-closed here as REFUSE". So `COMPACT_REQUIRED`, the rail's own "this can be fixed by dropping
context" verdict, aborts the flight before a single contact. The rail supports
`MAX_COMPACTION_PASSES = 2` and knows which identifiers may be dropped (`agent-state:`, `facet:`,
`value:` prefixes, validated in `_validate_compaction`), but **nothing calls it a second time**.
**At dispatch.** There is no per-contact budget assessment at all: `assess_context_budget` is called
from exactly one place, the preflight above. The request goes to the server, and if `n_tokens >=
slot.n_ctx` the built fork answers (verified at
`/home/chao/llama.cpp-featcache/tools/server/server-context.cpp:3326`)

> "request (%d tokens) exceeds the available context size (%d tokens), try increasing it"

with `ERROR_TYPE_EXCEED_CONTEXT_SIZE`, which `server-common.cpp:59-62` maps to **HTTP 400**, after
which the slot is released. On the client side `core/model/transport.py:314-322` is a bare
`urllib.request.Request` passed to `urllib.request.urlopen(request, timeout=timeout_seconds)` inside
a `with`, returning `response.read()` -- **no `except` anywhere**. `urlopen` raises
`urllib.error.HTTPError` on a 400, it propagates through the adapter, and the flight dies. **Today
the answer to "degrade or crash" is: crash, at row N of 13,078, with everything after it unflown.**
No arm measured here hit it -- `truncated = 0` on all 29,152 requests and the widest prompt on
record is 18,018 tokens against a 24,576-token slot -- but the np4 margin is the only thing
preventing it, and Part A's whole gain proposal is to spend that margin.

### 3.3 The COMPACT disposition, designed

The repository already has the exact template, admitted for this very shape of problem.
`native_episode.finite_completion_policy` (E13, 2026-09-19, `rails/config_tables.py`) is described
there as "the only one of the six that is a FAILURE MODE rather than a factor": with `"raise"` the
flight aborts; with `"deliver-latest-or-abstain"` the row is **retained**, the latest
delivery-eligible Solver draft is delivered, and a `terminal_disposition` mapping with `reason =
"finite_completion"`, `finish_reason`, `role_id`, `stage` and `revision_count` records exactly what
was given up. `rails/native_episode_receipt.py:_finite_delivery` validates it, and the key "renders
NO request byte ... which makes its ON arm free to be the default of every new cell." A context-fit
disposition should be built to the same contract. **Name.** `native_episode.context_fit_policy`, a
tenth episode-level switch, values `"raise"` (today's behaviour, the default until a cell admits the
other) and `"compact-or-abstain"`.

**Where it runs.** Immediately before each contact, in the seam the module docstring of
`rails/context_budget.py` already reserves -- "Runtime integration must supply receipt-bound exact
counts for an already rendered payload immediately before each model contact" -- which exists in the
contract and has never been wired.

**The declared drop order**, deterministic and declared, never a heuristic, lowest authority first:
(1) `value:` exemplars beyond the first k/2, the largest and most redundant block; (2) the candidate
cap, trailing candidates below the retained top-n; (3) the scenario-hints block
(`native_episode.solver_hints`); (4) the Reviewer audit block (`native_episode.reviewer_audit`); (5)
`agent-state:` history entries, oldest first, never the current draft. The task instruction, the
speech packet, the current draft and the tool schemas are **never** droppable: they are the
request's identity. The rail already enforces that dropped identifiers carry an `agent-state:`,
`facet:` or `value:` prefix, so items 3 and 4 need to become addressable under one of those prefixes
-- that is the one piece of new plumbing. **The receipt.** Each pass emits the existing
`ContextBudgetDecisionReceipt` (`payload_sha256`, `breakdown`, `decision`, `physical_margin_tokens`,
`operational_margin_tokens`, `compaction_pass`, `dropped_identifiers`, `slot_limit_tokens`,
`operational_reserve_tokens`), and the episode carries a `terminal_disposition` of the
finite-completion shape:

```json
{"reason": "context_compaction", "compaction_pass": 1, "role_id": "solver", "stage": "draft",
 "dropped_identifiers": ["value:exemplar-11", "..."], "tokens_before": 21988,
 "tokens_after": 20431, "budget_receipt_sha256": "..."}
```

The row is **retained and scored**, exactly as an E13 finite row is, and the per-stratum table
carries the compacted-row count beside it. Two passes, then `REFUSE` -- and a `REFUSE` at
`compaction_pass == 2` becomes an **abstention row**, not an exception. Never a silent truncation:
`truncated` stays 0 on the wire and every dropped identifier is named. **What it costs:** nothing on
a row that fits -- the check is a token count against an already-rendered payload, and at
`compaction_pass 0` with `ALLOW` the receipt is byte-identical to the preflight one. Like
`finite_completion_policy` it renders no request byte on the happy path, so its ON arm is free to
become the default of every new cell once one cell has flown it.

### 3.4 Which combination guarantees "degrade, never crash" for the test read

The test split is 13,078 recordings, headset and far-field, no subsampling. Its own prompt-length
tail has **never been measured** -- every arm flown at this geometry is a TRAIN Fold A roster. The
guarantee has to be constructed, in this order. (1) **Bound the tail before the read**: a model-free
pass over the test split's rendered payloads, zero contacts, the machinery E17's render proof
already used, reporting p50/p90/p99/p99.9/max rendered tokens per role -- a prerequisite: no
geometry may be chosen for a split whose tail nobody has seen. (2) **Keep `-np 4 x 24,576` for the
read**: 21,504 usable against a TRAIN maximum of 14,524 post-L1 and 18,018 across every sealed run
is a 3.5k-7k margin; at np6 that margin is negative today. (3) **Land `context_fit_policy =
"compact-or-abstain"`** so a test row wider than anything TRAIN produced degrades into a compacted
row with a named receipt instead of a 400. (4) **Hold `-ctk/-ctv q4_0` in reserve** for the case
where step 1 shows a tail that does not fit 21,504 even after compaction -- behind its own NEUTRAL
cell, because it changes the numerics of every contact. (5) **Do not enable unified memory**: per
section 3.1 it cannot work on WSL 2, and its failure mode is an allocation error at load, i.e. the
whole session rather than one row.

With 2 + 3 in place the read cannot crash on context: every request either fits, or is compacted
with a receipt, or abstains with a receipt. Without 3, the guarantee rests entirely on the margin in
2 -- which is exactly the margin Part A would have spent.

## 4. Part C -- the probe plan for the next GPU gap

Three probes, none computing a score; all are serving measurements, not cells. Total GPU budget:
**under 45 minutes per geometry** and under two hours in all.

### Probe G0 -- power headroom (byte-neutral, no geometry change, 10 minutes)

The enforced power limit is **100.00 W**, default 95.00 W, maximum **175.00 W**; the gain is
unmeasured. Serving flags unchanged, no new session. Record `nvidia-smi --query-gpu=power.limit,
power.default_limit,power.max_limit,enforced.power.limit,clocks.sm,temperature.gpu` before and
after, raise the limit with `nvidia-smi -pl`, replay one fixed request ten times at each cap from
the existing roster's already-exposed rows, restore the limit. **Measure** median and p90 `prompt
eval` tok/s at each cap from `server.log`, plus power and temperature from the monitor. **Pass:**
>= +15 % median prefill tok/s, no thermal throttling, no P-state regression. **Hazards:** the
2026-09-08 rule -- on any slowdown check `enforced.power.limit` and the Legion fan mode first, and
never change power settings while a scheduled task runs; this goes in a gap, not under a campaign.
**Receipt:** a serving receipt carrying both limits and both rate distributions; byte-neutral, no
`config_hash` or `protocol_hash` movement.

### Probe G1 -- `-ub 1024` at np4 (one new serving session, ~30 minutes)

* **Flags:** `-c 90112 -np 4 -b 2048 -ub 1024 -fa on -ngl 999 -ctk q8_0 -ctv q8_0 --cache-prompt
  --cache-ram 0 --no-cache-idle-slots --slot-prompt-similarity 0 --no-mmproj`. `-c` drops from
  98,304 to 90,112 (4 x 22,528 = 20,608 usable after the one-eighth reserve, still 6,084 tokens
  above the post-L1 maximum) to pay for the larger compute buffer out of a 143 MiB margin.
* **Session identity:** a new session id `serving-slurp-geometry-ub1024-np4-v1` with its own
  `session.json` / `session-receipt.json` / `monitor.jsonl` / `server.log`, and a new fragment
  `q4km-mmproj-free-slurp-native-np4-c90112-ub1024-max512-v1`. A geometry change is a session
  change.
* **Roster:** the four engineering rows (the `...-SMOKE-4-...` roster every cell smokes on), then
  **the first 100 ids of the TRAIN Fold A roster in its canonical order** -- already exposed by the
  sealed anchor, so no new exposure surface. Register an `ExecutionPlan` under
  `bounded-discovery-probe` and an exposure-ledger row before the first contact.
* **Measurements, all from `server.log` and the monitor:** contacts per minute; per-request latency
  by position in the row; prefilled tokens per request and per row; aggregate prefill and decode
  tok/s; cached share; packet re-decode share; slot occupancy and balance; steady-state
  `memory_used_mib` and the `device_info` free-at-load line; any `truncated = 1` or
  `exceed_context_size_error`.
* **Pass:** >= **+30 % contacts per minute** against EFF-1's 50.2 on the same roster prefix, **p99
  per-request latency no worse than 1.5x** (EFF-1 p99 is 12.97 s, so <= 19.5 s), **zero refusals**,
  zero truncations, steady-state VRAM <= 23,000 MiB. **Fail-fast:** abort at the four-row smoke if
  VRAM exceeds 23,050 MiB or any request is refused.

### Probe G2 -- np6 at q8_0, **only after** `context_fit_policy` lands (~30 minutes)

np6 is refused today by 188 tokens on one row in 2,912. This probe is **not admissible** until the
COMPACT disposition of section 3.3 exists, because without it the first wide row aborts the arm.

* **Flags:** `-c 99840 -np 6 -b 2048 -ub 512 -fa on -ngl 999 -ctk q8_0 -ctv q8_0 --cache-prompt
  --cache-ram 0 --no-cache-idle-slots --slot-prompt-similarity 0 --no-mmproj` -- 6 x 16,640-token
  slots, 14,560 usable, estimated 23,054 MiB (65 MiB of headroom, which the four-row smoke must
  confirm before the 100-row arm). Session `serving-slurp-geometry-np6-c99840-v1`, fragment
  `q4km-mmproj-free-slurp-native-np6-c99840-max512-v1`.
* **Roster:** the same four engineering rows, then the same first-100 TRAIN Fold A prefix as G1, so
  G1, G2 and the EFF-1 window are comparable.
* **Extra measurements:** rows reaching `COMPACT_REQUIRED` and their dropped identifiers; slot
  balance across six slots (the dispatcher's in-flight depth must be >= 6 or two slots idle); full
  re-prefill share, which is 0.0 % at np4 and must stay there.
* **Pass:** >= +30 % contacts per minute over EFF-1's 50.2, p99 latency <= 1.5x, **zero refusals**,
  compacted-row share <= 1 %, full re-prefill share <= 1 %, VRAM <= 23,100 MiB. **Expected:** the
  model says +7.5 %, which is **below the bar**, so G2 is a falsification probe -- if it lands near
  +7 %, slot scaling closes as a lever and np4 is locked with a measurement rather than a model
  behind it.
### What is not claimed

No effectiveness number is produced by any of these probes, and no arm is compared across
geometries: greedy decoding is not bitwise reproducible across batch compositions, so a geometry
change is a serving-session change with its own receipt, and any cell that spans two geometries is
void. The EFF-1 arm's serving-side numbers in this report are a provisional observation of an
unsealed flight, made from the serving session's files only; its cell verdict is whatever its own
sealed read says, and nothing here anticipates it.

## 5. What could not be verified

1. **`-ub` 1024 or 2048 on this model.** Never flown; one committed fragment declares it, no session
   records it. No VRAM figure, no rate comparison. Probe G1 exists to fix this.
2. **q4_0 KV.** Never flown. 28.22 KiB/token is derived from the measured q8_0 slope by the block
   ratio 18/34, and the effect of a 4-bit KV cache on this model's outputs is entirely unmeasured.
3. **The prefill gain of raising the power cap.** The cap itself is verified (100.00 W current and
   requested, 95.00 W default, 175.00 W maximum, read 2026-09-19T15:36:41Z); the gain is not.
4. **np5/np6/np8 post-L1 throughput.** Modelled from a two-resource fit with one fitted constant
   (overlap 0.647) calibrated on a single np4 window; the np6 decode ceiling is interpolated.
5. **The EFF-1 cell result.** The arm was in flight and its run directory was not opened; everything
   post-L1 here is serving-side and provisional.
6. **The SLURP test split's prompt tail.** Unmeasured; only TRAIN Fold A rosters have been flown at
   this geometry. Section 3.4 step 1 is a prerequisite for any geometry decision about the read.
7. **BAR1 usage under WSL 2** (32,740 of 32,768 MiB used) is recorded, not interpreted. **The
   residual idle** -- post-L1 monitor p10 utilisation 69 %, all-four-busy share down from 79 % to 63
   % -- was not separated into dispatcher scheduling, host-side packet assembly or sampling
   artefact; it bounds any dispatch-side lever at roughly a tenth.
8. **Upstream-versus-fork drift.** Every option and error path quoted in Part B was re-verified in
   the built fork at `04ccc72a`, except the README wording for `-b`/`-ub`/`-ctk`/`--cache-reuse`/
   slot save-restore, which is upstream master's text for options the fork's `common/arg.cpp` does
   contain. `--kv-unified-per-slot` exists upstream and is **absent** from the fork.
