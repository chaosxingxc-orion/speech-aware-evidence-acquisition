# Audio2Tool Q8_0 quantization probe (Factor C), v1 preregistration (REGISTERED, owner GO 2026-09-04)

Status: drafted 2026-09-04 at the owner's request ("preregister the Q8 probe too; decide together once the
official-protocol verdict is in") and REGISTERED on the owner's 2026-09-04 GO, recorded verbatim in section 8.
The GO was given after the official-protocol replication verdict
(`docs/readiness/2026-09-04-a2t-official-protocol-replication-v1-verdict.md`) and the three official-population
verdicts had been read. Nothing outside this document's own cell, budget and decision rule is authorized by it.

## 1. Why this probe exists

Outcome of the official-protocol replication (verdict
`docs/readiness/2026-09-04-a2t-official-protocol-replication-v1-verdict.md`, 2026-09-04): FAIL on the
preregistered rule. Under the official scorer, seven tiers sit between -12.6 and +3.4 pp of the paper row
(tiers 3, 4, 6, 7, 8 with the paper value inside the Wilson CI90), while tier 1 sits at 60.0 against 92.4 and
moved the wrong way relative to the reconstruction (66.0 under the format-matched diagnostic). The published
protocol itself is worth +5.50 pp of pooled tool accuracy (paired, CI90 +1.75 to +9.25). Quantization is one of
three remaining suspects for tier 1, beside the roster (mixed speakers, 50 per tier, versus first successful
speaker of every query) and the whitespace variant of the system prompt. This probe is the bounded test of the
quantization suspect; it is decided together with the roster question.

The local server is an RTX 5090 Laptop GPU with 24,463 MiB of memory. The operating frozen core is
Qwen3-Omni-30B-A3B-Instruct as a Q4_K_M GGUF (decoder 18,557,053,952 bytes, 17.3 GiB) plus the bf16 mmproj
audio encoder (2,207,465,568 bytes, 2.1 GiB) on the pinned llama.cpp featcache build 04ccc72a. With the KV cache
and compute buffers that fills the card; the Q8_0 decoder in the umbrella lock (`qwen3-omni-30b-a3b-instruct-gguf`,
32,484,494,336 bytes, 30.3 GiB) cannot be resident. The paper (arXiv:2604.22821) ran the bf16 HF model.

Every Audio2Tool baseline this study has flown is therefore a Q4_K_M number, and the direct-baseline calibration
(SAEA-A2T-DIRECT-CALIBRATION-V1) plus the official-protocol replication (SAEA-A2T-OFFICIAL-PROTOCOL-REPLICATION-V1)
vary everything except the decoder quantization. This probe measures the quantization cost ONCE, on the same rows
and the same official protocol, so that (a) every later Audio2Tool table can carry the bound "Q8 minus Q4 per tier"
beside the paper's bf16 row, and (b) the residual gap to the paper is attributed to quantization or excluded from it.
It is a bounded calibration measurement. Q8_0 does not become the operating core by this document; that is a
separate owner decision informed by the throughput this probe records.

Owner ruling in force (2026-09-04): the Q4_K_M core is the study's frozen core, not a stopgap; the quantization is a
recorded property of the core, reported in every table; no downgrade to a smaller omni model.

## 2. Population

The frozen 400-row discovery split A2T-CALIBRATION-400 (8 tiers x 50; receipt
`docs/checks/speech-aware-evidence-acquisition/2026-09-04-a2t-calibration-400-roster/flight-roster-receipt.json`,
split identity hash e1d751e6c76e49d087620842ba17c34e432a4602169dc2b93ee7e0a529ca332c under the roster convention,
11091b38ae9d53530952af632636d7e79a614350213e10c6c26583c37f85846b under the FlightRuntime convention; 2,159.688
speech seconds per pass). Already exposed by A0, the calibration flight and the official-protocol replication. No
draw, no new population, no test or confirmatory surface.

## 3. The cell: C-q8-official-raw (Factor C only)

Identical to the official-protocol replication cell R-official-raw in every request byte and every scoring rule,
with exactly one difference: the decoder GGUF is the Q8_0 file from the umbrella lock instead of the Q4_K_M file.

| fact | R-official-raw (flown) | C-q8-official-raw (this probe) |
|---|---|---|
| decoder | Q4_K_M, lock key `qwen3-omni-30b-a3b-instruct-gguf-q4km` | Q8_0, lock key `qwen3-omni-30b-a3b-instruct-gguf` |
| audio encoder | bf16 mmproj | the same bf16 mmproj file; the runtime receipt must show SHA-256 equality with the Q4 kit's mmproj |
| build | llama.cpp featcache 04ccc72a | 04ccc72a, no rebuild |
| prompt, tool lines, user text | official HF adapter strings (see the replication prereg) | byte-identical; prompt-fit receipt asserts the rendered text hash equals R-official-raw's |
| decoding | greedy (temperature 0), max_tokens 256, seed 20260803 | identical |
| audio path | raw audio, featcache dir `/home/chao/feat-cache/audio2tool-q4km-04ccc72a` | the same cache dir: entries are encoder outputs of the same mmproj bytes, so cache hits (zero "encoding" lines, untouched cache dir) are the proof that the audio side did not move |
| serving geometry | the -c / -np the replication settled on | identical -c / -np (KV cache and slots unchanged) |
| weight placement | all layers on GPU (`-ngl 999`) | `-ngl 999` plus `--n-cpu-moe N`: expert tensors of the first N layers live in host RAM (54 GB), attention, norms, embeddings, shared parts and the remaining experts on the GPU. Both flags exist on build 04ccc72a (`llama-server --help`: `-cmoe, --cpu-moe` and `-ncmoe, --n-cpu-moe N`) |
| scorers | `a2t-toolcall-official` (paper-facing), `a2t-toolcall-v2`, `a2t-toolcall`, `cost` | identical |

N is fixed model-free before takeoff by a VRAM fit rule, not tuned on outputs: start from `--cpu-moe` (all expert
layers on CPU), then lower N in steps of 4 while a zero-token server start (`/props` only, then stop) leaves at least
1,536 MiB free on the card at the declared geometry; the largest GPU-resident share that satisfies the rule is the
value, recorded with the measured free memory in the placement receipt. Placement is a numerical-implementation
detail: CPU and CUDA kernels accumulate in different orders, so rare greedy ties can flip; this is recorded as a
caveat, never treated as a protocol factor.

The packet path is not flown: Factor D was null on the calibration flight, and the Factor C question is decoder
quantization under the audio front-end the official adapter uses.

## 4. Pre-contact prerequisites (each a model-free receipt, in this order)

1. Materialize the Q8 kit on ext4: copy `models/qwen3-omni-30b-a3b-instruct-gguf/` (Q8_0 decoder + mmproj) from
   `SPEECHRL_DATA_DIR` to `/home/chao/models/qwen3-omni-30b-a3b-instruct-gguf/` (725 GB free), the same
   materialization root the Q4 kit uses. Hashes are computed by the receipt generator, never copied out of the lock.
2. Runtime receipt `docs/receipts/runtime-q8-featcache-04ccc72a.json` from
   `python -m speech_aware_evidence_acquisition.e0.generate` with the Q8 lock key (`--model-lock-key`) and
   `--llama-dir-name llama.cpp-featcache`; it must carry build 04ccc72a, per-file SHA-256 of both GGUFs, and the
   assertion that the mmproj SHA-256 equals the one in `docs/receipts/runtime-q4km-featcache-04ccc72a.json`.
3. Model fragment `configs/model/q8-featcache-a2t-official-04ccc72a.json`: a copy of the Q4 official-protocol
   fragment with the Q8 lock key, the Q8 receipt, the same `-c`/`-np`/`-fa`/`-ctk`/`-ctv`, and `--n-cpu-moe N` from
   step 4; `serving_geometry_basis` states the placement rule and the measured numbers.
4. Placement receipt (zero generated tokens): the fit search of section 3, recorded under
   `docs/checks/speech-aware-evidence-acquisition/2026-09-04-a2t-q8-quantization-probe-400-v1/placement/`, with its
   own ledger row (server started, `/props` read, stopped; no completion endpoint).
5. Prompt-fit receipt (zero generated tokens) under `.../prompt-fit/`: `/apply-template` + `/tokenize` on the Q8
   server; the rendered system text hash must equal the R-official-raw prompt-fit hash (the chat template is GGUF
   metadata; both files were converted from the same HF checkpoint, and this receipt proves it rather than assumes it).
6. Experiment fragment `configs/experiment/a2t-q8-quantization-probe-400-v1.json`, experiment_id
   `SAEA-A2T-Q8-QUANTIZATION-PROBE-V1`, profile `baseline-reproduction`, one cell, the section 5 plan.
7. `FlightRuntime.wire_check` on a clean committed tree, then a 4-row smoke (the same four rows as the calibration
   smoke: tier1_direct:000045, tier2_parametric:000045, tier5_needle:000060, tier6_correction:000008) under its own
   ledger row. The smoke records seconds per call and projects the 400-row wall time; if the projection exceeds the
   registered GPU-hour ceiling the flight does not take off and the owner is asked, rather than shrinking the roster.
8. Ledger row for the flight, written before the first contact; one-shot attempt semantics; at most one recovery
   re-registration.

## 5. Budget (ExecutionPlan)

| field | planned | registered ceiling | basis |
|---|---:|---:|---|
| model calls | 408 | 450 | 400 items + 8 canaries |
| speech audio seconds | 2,160 | 2,300 | one pass of the frozen 400 |
| GPU hours | 3.0 | 4.0 | the naive partial-offload measurement of August was 4.17x slower than resident Q4_K_M; expert offload keeps attention on the GPU and the official prompt is far shorter than the 13k-token registry, so 3.0 h is a conservative plan; the smoke's projection is the binding check |
| paid API spend | 0 | 0 | |

Host RAM: the Q8 expert tensors (about 28 GiB) are memory-mapped from ext4; 54 GB total, 53 GB free at drafting time.
No other GPU work may run during the flight (one resident server, ready-first scheduling suspended for its duration).

## 6. Analysis and decision (fixed before takeoff)

Paired on the same 400 rows: C-q8-official-raw minus R-official-raw, per tier and pooled, under the official scorer
(tool accuracy, exact match, param F1 macro and micro) and under `a2t-toolcall-v2` (ordered tool accuracy, exact
match, slot F1). `analysis.paired`: saves / harms / ties, exact sign test, 10,000 stratified bootstrap replicates,
seed 20260903, CI90. C-q8 versus the paper row per tier with Wilson CI90 (n = 50). Parse rate, rows with more than
one emitted call, seconds per call, calls per second at the declared slots, GPU memory and host RAM in use.

Decision, read on the four acceptance tiers (1, 2, 5, 6) pooled unless stated:

- QUANTIZATION-DOMINANT: the pooled Q8 minus Q4 tool-accuracy CI90 lower bound is above 0 AND C-q8 is PASS or
  CONSISTENT-WITHIN-NOISE against the paper on those tiers (the replication prereg's definitions). Consequence: the
  Q4 core is quantization-limited on this task; every Audio2Tool table carries the per-tier Q8 bound; the owner
  decides, on the recorded throughput, whether Q8 with expert offload becomes the Audio2Tool operating core.
- QUANTIZATION-EXCLUDED: the pooled CI90 includes 0. Consequence: the residual gap is not the decoder quantization;
  the remaining suspects are the GGUF chat template versus the HF processor template, the llama.cpp audio front-end
  versus the HF processor, and the roster (mixed speakers, 50 per tier) versus first-speaker-per-query over every
  query. Which of them to test next is an owner decision.
- PARTIAL: otherwise; report the fraction of each tier's gap closed by Q8 and stop.

No outcome changes the operating core by itself, tunes any knob, or opens any test data.

## 7. What this preregistration does not authorize

No model contact before the owner's written GO in section 8; no test split; no mechanism arm; no fresh roster;
no Q5_K_M / Q6_K / IQ variants; no rebuild or checkout of the llama.cpp tree; no edit to the chat template; no
packet-path cell; no second attempt beyond the one recovery re-registration; no superiority, generality or Stage-3
claim.

## 8. Owner decision and execution log

**Owner decision 2026-09-04: GO as the closing model-usage check; no author query.**

The owner's reasoning, recorded as given: the alignment axes that matter are the prompt, the way the model is
used, and the scoring script; the Audio2Tool authors will NOT be asked; quantization (Q4_K_M against the paper's
bf16) is the last controllable "model usage" suspect, and this probe closes it. Everything else in this
preregistration stands unchanged -- the cell, the population, the budget, the prerequisite order and the
three-outcome decision rule of section 6 are exactly as drafted, and section 7 remains in force.

Execution log:

| step | artifact | status |
|---|---|---|
| owner GO recorded | this section | 2026-09-04 |
| 1. Q8 kit materialized on ext4 | `/home/chao/models/qwen3-omni-30b-a3b-instruct-gguf/` | 2026-09-05 |
| 2. runtime receipt | `docs/receipts/runtime-q8-featcache-04ccc72a.json` | 2026-09-05 |
| 3. model fragment | `configs/model/q8-featcache-a2t-official-04ccc72a.json` | 2026-09-05 |
| 4. placement receipt | `.../2026-09-04-a2t-q8-quantization-probe-400-v1/placement/` | 2026-09-05 |
| 5. prompt-fit receipt | `.../2026-09-04-a2t-q8-quantization-probe-400-v1/prompt-fit/` | 2026-09-05 |
| 6. experiment fragment | `configs/experiment/a2t-q8-quantization-probe-400-v1.json` | 2026-09-05 |
| 7. wire check + 4-row smoke | `.../wire-check/`, smoke run | 2026-09-05 |
| 8. flight | `SAEA-A2T-Q8-QUANTIZATION-PROBE-V1` | 2026-09-05 |
| verdict | `docs/readiness/2026-09-04-a2t-q8-quantization-probe-v1-verdict.md` | 2026-09-05 |

Outcome, 2026-09-05: **QUANTIZATION-EXCLUDED**. Pooled over the four acceptance tiers the paired
Q8-minus-Q4 tool accuracy is +0.50 pp with a CI90 of [-1.50, +2.50] pp, which contains zero. Tier 1 is 60.0 %
on both decoders with zero discordant rows, and the `wearables` domain is 72.63 % on both across 95 rows.
Over all eight tiers there is a small real lift (+2.25 pp, CI90 [+0.25, +4.25]) concentrated in tier 8.
Cost: 7.85x the per-call latency of the resident Q4_K_M core. The flight spent 400 of 450 registered calls,
2,159.688 of 2,300 registered speech-audio seconds and about 0.29 of 4.0 registered GPU hours, on one
attempt with no recovery re-registration.
