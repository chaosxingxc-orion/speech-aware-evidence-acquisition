# OBS-E1 PERSON harm decomposition — `SAEA-E21-MF-OBS-E1-HARM-DECOMPOSITION-V1`

**The sixty-one errors that rejected OBS-E1, located.** `SAEA-E21-OBS-E1-SPEAKER-TURN-UNITS-V1` moved
ConEC-mirror PERSON entity WER from **22.48886** to **24.58005** (−2.0912, CI90 [−3.1701, −1.0978])
and was REJECTED as HARM. This receipt decomposes that movement, model-free, into its operation kind,
its position relative to the transport unit's own boundaries, the properties of the unit it fell in,
and a priced design table for the successors it names.

**The verdict, its reasoning and its claim surface live in
`docs/readiness/2026-09-08-e21-obs-e1-person-harm-decomposition-v1.md`.** This directory is the
machine-readable half.

| | |
|---|---|
| exposure row | `SAEA-E21-MF-OBS-E1-HARM-DECOMPOSITION-V1` (`model-free-check`), registered and committed at study commit `0e4cbed2` BEFORE the first sealed artifact was opened |
| cell | `SAEA-E21-OBS-E1-SPEAKER-TURN-UNITS-V1`, attempt `attempt-20260908T150858Z-c597a8` (artifacts at the run ROOT) |
| comparator | `SAEA-E21-FULL44-DIRECT-BASELINE-V2`, attempt `attempt-20260904T233816Z-bcd338` |
| carrier / split | `earnings21-original`, `discovery`, all 44 calls, split identity `fcc1b0bc…d69e` |
| contacts | **zero** — no model, GPU, server, tokenizer, tool, embedder, network, audio-decode or paid-API contact, and no Earnings-22 read |
| code | `analysis.e21_person_harm`, `scripts/e21_obs_e1_person_harm_read.py`, `tests/unit/test_e21_person_harm.py` |

## The two anchors, both cleared before any table was built

**Anchor 1 — the per-word rows reproduce both sealed PERSON buckets exactly, and the rows stage
refuses to write if they do not.** Comparator **22.48886** from 573 S / 83 D over 2,917 reference
words; cell **24.58005** from 619 S / 98 D over the same 2,917.

**Anchor 2 — the paired statistic reproduces the OBS-E1 verdict's own.** Improvement
**−2.0911896**, CI90 **[−3.1701, −1.0978]**, saves / harms / ties **10 / 27 / 7**, all identical to
the verdict's, through the same instrument (`build_e21_tail2s_verdict.bootstrap_delta`,
`analysis.paired.resampled_statistic`, seed 20260903, 10,000 replicates, CI90, clustered by call).

## The four answers, in one line each

1. **Kind.** The 61 excess errors are **46 substitutions and 15 deletions** — misheard names, not
   dropped ones. Substitution rate −1.5770 [−2.5868, −0.6684]; deletion rate −0.5142
   [−1.0247, −0.0304].
2. **Position.** **93.4 %** of the excess is within three seconds of a unit boundary and beyond ten
   seconds there is none; the comparator's rate over the same words is flat, so those are not
   intrinsically hard words. Exactly **one** of 656 multi-word PERSON mentions is cut by a unit
   boundary.
3. **Unit properties.** **Duration**, monotone and with no exception: −14.545 under 3 s to **+0.861**
   at 60 s or more. Units under 10 s hold 23.3 % of the PERSON words and **78.7 %** of the harm.
   Speaker purity is **flat**, and both of the verdict's call-level readings invert or vanish at the
   unit grain.
4. **Tail versus boundary.** **Neither count.** The per-tail cost varies 2.8× across duration classes
   and changes sign; the 3,529 extra boundaries leave a +0.113-point residual. The short unit is the
   driver and both counts are proxies for it.

## Contents

| path | what it is |
|---|---|
| `person-harm.json` | the whole decomposition: the identity anchors, the S/D split with per-call rows and call-clustered intervals, the boundary-distance tables in seconds and in reference words, the mention-split test, the duration/purity/end-cut/sliver/speaker-change tables, the tail-versus-boundary block with the per-tail-by-duration column and the deletion-position counts, and the design-only successor pricing |
| `README.md` | this file |
| `MANIFEST.sha256` | the SHA-256 of every file above |

**The per-word rows are NOT here.** `person-rows.json` (2,917 rows, one per `(PERSON reference word,
entity ID)` pair, with both arms' operation kind, span identity, span reference block and boundary
distances) is a per-request derivative of sealed model outputs and lives at
`$SPEECHRL_DATA_DIR/runs/SAEA-E21-MF-OBS-E1-HARM-DECOMPOSITION-V1/person-rows.json`, where those
outputs live. It never enters Git. Rebuild it with
`scripts/e21_obs_e1_person_harm_read.py --stage rows` (about 19 minutes, both arms' alignments) and
re-render this receipt with `--stage tables --out-dir <this directory>` (under a second).

## Not authorized by this receipt

Discovery data at n = 44 clusters, below the program's `n >= 400` rule. **Nothing here is a decision,
a preregistration or a GO**: OBS-E1 stays REJECTED, no successor cell is registered, no knob is tuned,
and the successor pricing is a design with projections attached under the OBS-E1 verdict's own
audio-proportional cost model. No superiority, generality, published-comparison or Stage-3 claim; no
paper-facing effectiveness claim of any kind. No Earnings-22 contact, no fstalign install, no
diarizer re-run, no speaker naming.
