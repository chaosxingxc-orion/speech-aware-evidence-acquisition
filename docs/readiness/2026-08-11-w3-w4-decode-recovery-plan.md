# W3/W4 decode-recovery: survey and plan (2026-08-11)

Standing facts: decode p50 6.74 tok/s per slot at 4-way, 13.07 single-slot,
against a ~40–100 tok/s realistic band for a 3B-active MoE at Q4_K_M on this
RTX 5090 **Laptop** GPU (~0.9 TB/s). Config space exhausted (M1/M2 refuted);
upstream flat (9afff1b7 = fdbd6abee on this workload); HAGS already enabled.
W2's four-cell probe ({graphs on/off} × {np1/np4}) attributes what remains.

**W2 results (2026-08-11, four cells, identical single slice):** graphs-on/off
at np1 = 17.68 / 17.67 tok/s (ZERO difference — per-step submission latency is
NOT the bottleneck, weakening W4's paravirt hypothesis at its core); at np4
with ALIGNED concurrency, graphs-on 10.75 vs graphs-off **14.43 (+34% from
disabling graphs)** — under changing batch shapes the re-capture overhead
exceeds any launch savings. Deficit decomposition: 18.0 (np1) -> 14.4 (np4
aligned, graphs off) -> 10.75 (np4 aligned, graphs on) -> 6.74 (np4 real
staggered, graphs on). W3's action therefore pivots: not `-ub` pinning but
**GGML_CUDA_DISABLE_GRAPHS=1 as a config-hashed server_env field + a 30-min
re-lock bench** (predicted real-np4 aggregate 27 -> 40-55 tok/s). W4's
zero-integration probe stays worthwhile but with lowered expectations — the
residual np1 ceiling (18 vs the 40-100 band) now points at laptop
power/clock management and MoE kernel efficiency, both readable from the
same probe's dmon telemetry.


## W3 — batch-shape stability (graph thrash)

**Survey.** The pinned build's CUDA-graph engine skips graph execution
whenever graph "properties" change — `ggml-cuda.cu:4496`: *"properties
changed or first call — execute directly (use_cuda_graph stays false)"*.
Under `-np 4` the decode batch is the set of currently-decoding slots, and
its composition changes every time any slot starts prefill, finishes, or
joins — i.e. constantly under our rolling per-sample loop. Every such step
executes graph-less and pays raw per-kernel submission latency. Single-slot
serving has one stable shape, which is consistent with np1's 13.07 vs np4's
6.74 per slot.

**Actionable knobs found (pinned build):**
- No server flag forces graph use at changing shapes — the disqualifier is
  structural. `-ub` shapes PREFILL chunks only; decode batches are formed by
  the scheduler.
- Feasible mitigations, in cost order: (a) **slot-count sweet spot** — W2's
  np1-vs-np4 cells + the existing np2 datum (9.77/slot ≈ 19.5 aggregate)
  already measure the trade; if graphs are the np1 advantage, np2 may be the
  aggregate-per-stability optimum; (b) **wave-aligned batching** (executor
  holds requests to keep slot occupancy constant) — protocol-level change,
  moderate complexity, bounded gain (~40%); (c) upstream contribution to
  relax the property-change disqualifier for MoE decode — out of this
  study's scope.

**Plan:** decide from W2 cells. If graphs explain ≥40% of the np4 penalty →
register a np2-vs-np4 CAMPAIGN bench (full fast-split arm at np2, wall-clock
decision; np2 costs concurrency but may win aggregate under stable shapes).
Else close W3 as empty.

## W4 — native Windows llama-server (bypassing dxgkrnl paravirt)

**Survey.**
- WSL2 GPU path: CUDA → `/dev/dxg` → dxgkrnl paravirt → host WDDM → GPU.
  Native Windows keeps WDDM but removes the paravirt hop. Community numbers
  put WSL2 decode 5–15% behind native for DENSE models — our 6–10× anomaly
  is not explained by that alone, so W4's expected value hinges on whether
  paravirt interacts pathologically with MoE's many small kernels, and on a
  **second suspect the laptop platform adds: power/clock throttling under
  bursty small-kernel occupancy** (boost clocks sag when the GPU never
  sustains occupancy). Both are testable by the same probe.
- **Zero-integration probe first** (decisive, ~30 min, no study-repo
  changes): official llama.cpp Windows CUDA release binary, same GGUF
  (E:\ is Windows-readable; model files are regular files, no LX symlinks),
  same flags, same single-slice request matrix as W2, plus `nvidia-smi dmon`
  clock/power logging on BOTH the native run and a WSL rerun. Readout:
  native-vs-WSL decode rate AND clocks/power under decode. Outcomes:
  - native ≈ WSL → paravirt exonerated; the deficit is WDDM/laptop-power/
    model-side; W4 integration is DEAD (days saved); attribution moves to
    power management (Windows power plan, NVIDIA prefer-max-performance).
  - native ≫ WSL (≥2×) → integration project GO.
- **Integration design (only on GO):** session layer spawns the Windows
  binary via WSL interop (`/mnt/c/...\llama-server.exe` — WSL can exec
  Windows binaries and holds a real interop pid for liveness); receipt v2
  hashes the exe + DLLs via /mnt/c (regular files); loopback rail survives
  by switching WSL to **mirrored networking** (`networkingMode=mirrored` in
  .wslconfig — currently default NAT, where 127.0.0.1 does NOT cross the
  boundary; mirrored shares localhost both ways, so `require_loopback` and
  the session receipt's host:port binding hold unchanged). Estimated 1–2
  days including a full bench + re-lock. Risk register: interop pid
  semantics in `assert_session_alive`; Windows Defender scanning the 18 GB
  GGUF on first load; mirrored-mode side effects on the MLflow/sqlite paths
  (none expected — files, not sockets).

**Plan:** run the zero-integration probe in the next GPU-idle window AFTER
the R4 n=10 set (pre-registered as its own bench row); decide W4 GO/DEAD on
its numbers; only a GO spends integration effort.

## Sequencing

R4 n=10 (science, launches now) → W4 zero-integration probe (+ power
telemetry) → W3 campaign bench iff W2 indicts graphs → W4 integration iff
the native probe shows ≥2×.
