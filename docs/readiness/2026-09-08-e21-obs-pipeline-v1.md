# E21 obs pipeline — the GPU stops waiting out every call boundary

**Status (2026-09-08): ENGINEERING FIX LANDED, DEFAULT OFF, NO FRAGMENT FLIPPED.** This is a
throughput repair to the engineering base, not an experiment and not an authorization. The new
knob defaults to `0`, `0` is today's behaviour byte for byte, and **no committed config fragment
declares a non-zero depth** — the coordinator decides that per cell, and a cell that turns it on
gets a new `config_hash`, a new `protocol_hash` and its own exposure row like any other fragment
edit.

| | |
|---|---|
| defect source | owner observation 2026-09-08, confirmed on the live monitor |
| measured on | `SAEA-E21-FULL44-DIRECT-BASELINE-V2`, attempt `attempt-20260904T233816Z-bcd338` |
| receipt | `docs/checks/speech-aware-evidence-acquisition/2026-09-08-e21-obs-pipeline/` |
| dry run | `python scripts/obs_pipeline_dry_run.py` (model-free, zero contacts, zero GPU) |
| code | `reproduction/obs_loop.py`, `core/driver/run.py` |
| tests | `tests/unit/test_obs_pipeline.py` |
| owner rule this serves | study `CLAUDE.md` **Pipeline**: "CPU packet preprocessing runs in parallel and overlaps model load; ready flights are queued by geometry so the GPU never idles" |

---

## 1. The defect, with the numbers

The owner saw it on the live monitor: the Earnings-21 obs loop holds the GPU at **64.6 % mean
utilisation** inside a flight, with **13.6 % of 10-second samples at 0 %** (runs of 10–30 s) and
**22.7 % below 50 %**, delivering **19 windows/min** where the geometry allows ~25+.

The sealed comparator says the same thing from the other side of the wire. Replaying its own
server log (`slot launch_slot_` → `slot release`, llama.cpp's microsecond clock) over its 1,593
windows and 44 calls:

| measured on the sealed attempt | value |
|---|---|
| wall | 5,378.8 s (1.49 h) |
| windows per minute | **17.77** |
| mean busy slots | **4.664 of 6 (77.7 %)** |
| all six slots busy | 65.4 % of wall |
| **zero** slots busy | **15.40 % of wall = 829 s** |
| call boundaries (43 gaps) | mean **19.26 s**, median 17.90 s, min 5.12 s, max 36.32 s |
| gap total | **828.4 s = 100.0 % of all zero-busy time** |

That last line is the whole finding: **every idle second the GPU spent in that flight was a call
boundary.** Not one of them was a stall, a slow request, or a scheduling hiccup inside a call.

The cause is structural, in two places that compound:

1. `reproduction/obs_loop.py::_slice_parallel_pass` works per SAMPLE. It decodes the whole call
   (`librosa`), then cuts, encodes, writes and registers EVERY window before the first request
   leaves the process.
2. `core/driver/run.py` iterates samples strictly sequentially (`policy.run_sample(ctx)`), so the
   next call's CPU phase begins only after this call's pool has fully drained.

So the GPU idles for the whole CPU phase at every boundary, and the slots drain one by one at
every call's tail. 24 cores sit almost idle while a 24 GB card waits.

## 2. The fix

Two halves of one mechanism, gated by one new knob, `obs_prefetch_depth` (integer ≥ 0, default 0).

**PREFETCH.** `core.driver.run_experiment` gains a pipelined sequential branch: it keeps
`obs_prefetch_depth` samples of LOOKAHEAD in flight, each on its own worker with its own
`core.tracing.TraceBuffer`, flushed into the real sink strictly in split-id order. Sample N+1's
decode / cut / encode / register therefore runs while sample N's windows are still being answered.
The docstring promise that every window of a sample is cut *before that sample's first model
touch* is preserved exactly — prefetch moves WHEN a sample starts cutting, never the cut-then-send
order inside it.

**SLOT-SATURATING DISPATCH.** `reproduction.obs_loop.ObsDispatcher` is ONE pool of dispatch slots
for the whole run — a FIFO deque of `width` integers behind a condition variable, acquired per
request and released when it settles. Because it spans samples, sample N+1's first windows occupy
the slots sample N's tail is releasing, and the in-flight count never falls to zero at a boundary.
It is also the one place the `id_slot="per-sample"` sentinel resolves under the pipeline: two
samples drawing from two per-sample pools would hand the same integer to two live requests and pin
them to one server slot.

Width = `max(obs_batch_slices, serving_geometry.slots)`. Never narrower than the width the config
already declares (so no run gets slower, and the set of `id_slot` integers a run can send does not
move — for every fragment in this repository `obs_batch_slices` is the larger of the two), and
never narrower than the server's own slots (so a geometry with more slots than the config's slice
width can actually fill them). The dispatcher never invents concurrency above both numbers.

## 3. What changes and what does not

**Does not change.** The request bytes: same slice cutting, same encoder, same instruction, same
arm, same evidence, same decoding params, same payload field set — proven by comparing per-window
request `payload_sha256` sets between arms. The OBS records: same ids, same payloads, still emitted
per sample in slice order after that sample completes. The stitch chain, the request ids, the
retry classification, the skip bound and every outcome shape. The `window_hook` seam (KC-E1f) and
the `obs_unit_plan` seam (OBS-E1), both orthogonal and both still green on their own suites. The
budget: metering is still per request, at the moment it is sent; prefetch CUTS audio, and cutting
never touches the adapter, so no attempt spend is created before a request goes out.

**Does change.** Timing and batch composition. Two samples' requests can now be in flight at once,
so MODEL/COST records interleave across a wider window than before — within each sample's own
trace block, which is where they already interleaved by arrival order (the pass's own documented
contract since 2026-08-12). Rows and trace blocks still land in split-id order.

**Also changes, and must be said plainly.** A run that aborts on sample N has already sent some of
sample N+1…N+depth's requests, so a FAILED attempt's durable spend is up to `depth` samples larger
than the sequential path's. `planned_model_calls` is run-cumulative and sized for the whole roster,
so this changes what a dead attempt costs, never what a complete one does.

**Greedy nondeterminism.** `llama-server` at temperature 0 is not bitwise reproducible across batch
compositions — this repository has measured that. The pipeline changes batch composition by
construction, so a pipelined re-fly of a sealed cell will differ in text from that cell, and the
difference is decoding noise, not a mechanism effect. The magnitude of that noise is exactly what
`SAEA-E21-FULL44-NULL-REPLICATE-V1` (the Earnings-21 own-null replicate, registered 2026-09-08)
measures. **Any comparison that spans a depth change must be read against that replicate's band,
and a cell may not change depth mid-campaign.**

## 4. The predicted gain (model-free)

`scripts/obs_pipeline_dry_run.py` replays the sealed attempt's own timing — the measured
per-request service times from the server log, and the measured per-call CPU phases from the
boundary gaps — through a simulated 6-slot FIFO dispatcher at depth 0 and depth 1.

| arm | windows/min | mean slot use | zero-busy | wall |
|---|---|---|---|---|
| measured (sealed attempt) | 17.77 | 77.7 % | 15.40 % | 1.49 h |
| simulated, depth 0 | 18.52 | 81.3 % | 16.11 % | 1.43 h |
| simulated, depth 1 | **22.74** | 99.9 % | 0.00 % | 1.17 h |

**Model fidelity: the depth-0 arm predicts the measured wall to −4.04 %** — the simulator is
slightly optimistic, and the receipt says so rather than hiding it.

**Predicted gain, depth 1 vs depth 0: +22.8 % windows per minute, 16.0 minutes saved on this
1.43-hour arm (18.6 % of wall).**

The bound that survives every modelling assumption is purely measured: the sealed attempt's own
wall minus its own idle seconds is 4,550.3 s, i.e. **21.01 windows/min, +18.2 %**. Take that as the
honest headline; the simulator's 22.74 is its own ceiling.

Stated assumptions, all carried in the receipt: per-request service times are held fixed across
arms (measured with the server mostly saturated, which is the regime the pipelined arm runs in, but
a busier server can still decode marginally slower — so the scheduling gain is an upper bound);
the CPU phase is held fixed (prefetch moves it off the critical path, it does not make it cheaper);
requests are assigned greedily in sample order; and the depth-1 arm's ~100 % modelled occupancy is
the model's ceiling, not a promise.

## 5. How to enable it, per fragment

Add one key to the cell's **baseline** fragment:

```json
"obs_prefetch_depth": 1
```

That moves the fragment's hash, therefore the composed `config_hash` and `protocol_hash`, therefore
the cell's exposure row — deliberately, so a depth change can never be mistaken for the same
protocol. Legality is fail-closed and checked before the adapter opens an attempt:

* the depth is an integer ≥ 0;
* `obs_batch_slices > 1` — the pipeline drives the slice-parallel pass, whose windows are provably
  independent; the sequential cutter's cursor is not;
* `obs_batch_samples == 1` — the ojw sample-batch executor already owns sample-level concurrency
  and its own slot pool, and two schedulers would multiply the in-flight count;
* the policy is `obs-agent-loop`.

Start at depth 1. Depth ≥ 2 costs one decoded call's PCM in RAM per extra lookahead (~145 MB for a
75-minute call) and buys progressively less, since one boundary's CPU is already fully hidden by
one sample's body.

## 6. Reporting rule (new, from this flight onward)

**Every flight closure reports mean GPU/slot utilisation, zero-utilisation share, and windows per
minute**, beside the scores. All three come out of the same server-log replay this receipt uses, so
there is no new instrumentation to build and no excuse for a closure that reports only quality. A
closure that cannot state them says why.

## 7. Claim surface

Nothing here is a quality claim, a superiority claim, or a Stage-3 activity. It is an engineering
throughput repair with a measured defect, a fail-closed knob that is off by default, and a
model-free projection whose fidelity is stated. It authorizes no contact, no server, no scoring,
and no change to any committed fragment.
