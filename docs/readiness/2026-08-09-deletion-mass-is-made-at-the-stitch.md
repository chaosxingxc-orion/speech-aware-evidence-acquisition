# Where the deletion mass actually comes from (2026-08-09)

First completed arm of SAEA-E-002 (`nocontext`, bare-core-ojw, ten Earnings-21
discovery samples, 614 slices, attempt `attempt-20260809T194151Z-ecdb38`,
study_commit `63d0f57`). Read after the arm completed; the other two arms were
already running under a frozen config, so nothing here could change them.

## The headline

| | |
|---|---|
| corpus WER | **26.61 %** |
| macro WER | 26.33 % |
| published E-21 systems, rescored with our frozen metric | 15.70–17.95 % |
| gap to the top of that band | **8.7 pp** |

**Carrier note:** this is **Earnings-21**. The 26.74 % recorded earlier in
`2026-08-08-e001-wiring-memo.md` is **Earnings-22**. The two land within
0.13 pp of each other even though E-22 is the harder, more diverse release —
which is the first hint that the binding constraint is not acoustic difficulty.

## Error composition: deletions dominate

| | substitutions | deletions | insertions |
|---|---|---|---|
| count | 4,745 | **12,433** | 3,353 |
| share of all errors | 23.1 % | **60.6 %** | 16.3 % |

Per-sample deletion share ranges 42–75 %. In a tuned ASR system substitutions
normally dominate; 60 % deletions says the system is **losing content**, not
mis-hearing it.

## The obvious hypotheses, and what the trace says

**"The model under-produces / the audio needs enhancement."** Not supported at
the recognition step. Joining every slice's request duration to its response
text across all 614 slices:

- raw slice production: **94,146 words over 36,588 s = 2.573 words/s**
- the corpus reference rate is **2.54 words/s**

The model emits *slightly more* than the reference rate, not less. Whatever is
deleting content is downstream of the decode.

**"Audio is being skipped between slices."** Also no. The loop advances at most
55 s through a 60 s buffer, so consecutive slices overlap; measured coverage is
36,588 s of slice audio over 30,408 s of real audio, an overlap factor of 1.20.
Nothing is skipped — the same seconds are transcribed more than once by design.

## What the trace does say: the stitch step

Per sample, comparing raw slice production against the final stitched
hypothesis, and separating out the removal that overlap dedup *should* account
for (`raw × (1 − 1/overlap)`):

| | words |
|---|---|
| raw slice production | 94,146 (122.0 % of reference) |
| final stitched hypothesis | 67,621 (87.7 % of reference) |
| removed at the stitch | 26,525 (28.2 % of raw) |
| explained by overlap dedup | 15,832 |
| **excess removal** | **10,693** |
| scored deletions | 12,433 |
| **excess removal / deletions** | **86.0 %** |

Per-sample, excess removal and deletions correlate at **r = 0.847 (n = 10)**.

So roughly **86 % of the deletions are created by the merge step**, and since
deletions are 60.6 % of all errors, the stitch alone owns on the order of
**half the total error mass**. The recognition is not the bottleneck; the
control plane's own reassembly is. That is squarely this study's subject matter
rather than a frozen-core capability limit.

Two readings remain open and the write-up must not collapse them: either the
dedup is too aggressive outright, or the model's transcripts of the overlapping
seconds disagree enough that alignment fails and content is dropped in the
confusion. They imply different fixes, and the per-slice texts needed to
separate them are already on disk.

## The left tail is real, and it is where enhancement belongs

Per-slice yield (words per second of slice audio, reference 2.54):

| p05 | p10 | p25 | p50 | p75 | p90 | p95 |
|---|---|---|---|---|---|---|
| 0.73 | 1.50 | 2.33 | 2.65 | 2.97 | 3.25 | 3.55 |

13.4 % of slices come in under 2.0 w/s, 6.7 % under 1.0, 1.3 % under 0.5. The
median slice is healthy; a minority of slices produce almost nothing. **That
minority is the legitimate target for signal enhancement** — and the point of
measuring the distribution first is that a *global* enhancement would pay for
all 614 slices to help roughly 80.

## Generation cap: vindicated and cheap

Exactly **1 of 614** slices reached the 1,024-token cap (p50 = 193,
p90 = 231, p99 = 304). The runaway that aborted two earlier arms is real,
rare, and now bounded at a cost of one truncated slice per arm.

## Consequences for the plan

1. **The stitcher is now the highest-value single target in the study**, and it
   is not currently an arm in the E-004 substrate ladder. Add one.
2. Evidence injection (W-B, the R4 contrast currently running) attacks
   substitutions, which are only 23 % of the error mass. Expect a small effect
   from the matched arm on aggregate WER **for this structural reason**, and do
   not read a small effect as "context does not help" — read it against
   entity-class errors instead.
3. Signal enhancement earns an arm, but a **selective** one gated on the
   low-yield tail, not a global tempo change.
