# The ESB released arrays carry the published overlap — verdict

**RELEASED ARRAYS OVERLAP. The ESB release's own per-utterance `audio` arrays are cut at the
published `[start_ts, end_ts]` and at nothing else: 2,732 of 2,735 test utterances (99.89 %)
match `end_ts − start_ts` to within a millisecond, the median difference is +0.0000316 s — half
a sample frame — and the implied per-side pad is +0.0000158 s, which is zero. Place each
released array at its own published start and 1,959 of 2,729 adjacent pairs (71.8 %) overlap,
hard capped at −0.18045 s, median −0.13996 s, 274.3 s of test audio delivered twice.** The
2026-09-06 clip-boundary audit measured 77.7 % of dev pairs overlapping at a −0.18042 s cap with
a −0.140015 s median on this study's own cut. **Same wall, same median, same mechanism.** The
published 9.79 / 12.3 systems consume these arrays, so they heard the same onsets: the overlap is
**not** a difference between the two systems, and the boundary-exact cell's binding claim rule
stands, unconditionally. Section 1.6's conditional lifting clause is now dead, and section 7 of
`docs/readiness/2026-09-06-e22-dev-boundary-exact-v1-preregistration.md` carries the dated update.

Row `SAEA-E22-MF-ESB-ARRAY-DURATIONS-V1` (`model-free-check`), registered before the reading pass
under the owner decision of 2026-09-06. **Zero frozen-core, tokenizer, embedder, retriever,
scorer, network, GPU and paid-API contacts; zero audio seconds delivered to any service**, and the
offline guard recorded zero outbound connection attempts. Under nine seconds of wall time in one
process, and the pass is **byte-deterministic**: run twice back to back it reproduces the same
`MANIFEST.sha256`, which is why the wall time is printed and not stored. Receipts:
`docs/checks/speech-aware-evidence-acquisition/2026-09-06-e22-esb-array-durations/`
(`summary.json` sha256 `1316efed…`, `per-utterance-table.csv` `7b10e7b1…`). Module
`analysis/e22_esb_array_durations.py`, runner `scripts/run_e22_esb_array_durations.py`, tests
`tests/unit/test_e22_esb_array_durations.py` (35, on synthetic containers, a synthetic segment
table and a synthetic parquet shard).

**Population: the ESB TEST release's metadata, touched for durations only.** All 2,735 published
test utterances of the six calibration-exposed ESB test calls. **No text, no audio content, no
outputs.** The `sentence` column was never projected out of the parquet and the `sentence` field
of the pinned JSONL is discarded inside the loader's parse scope; of each `audio.bytes` blob only
its byte length and its RIFF/WAVE container header left the row group; no sample was decoded, no
blob was written, hashed or retained; no sealed output, hypothesis, score or reference layer was
opened. `text_columns_read`, `audio_samples_decoded`, `audio_blobs_written_or_hashed`,
`sealed_outputs_opened` and `reference_layers_opened` are all `0` in the receipt.

**The dev side cannot be checked and is not claimed.** The 55 train shards that hold the 6,038
dev10 rows were never downloaded — only column-projected over the network — so no released dev
array exists on disk. Every number below is the test release's, and the transfer to dev is an
inference from the fact that both splits come from one repartition at one revision, stated as one.

## 1. What was read, and how identity was established

| layer | artifact | identity |
|---|---|---|
| the release | `sanchit-gandhi/earnings22_split`, split `test`, revision `f9fb35f4134e32b9c8100199d949398fd6d08a5f` | four parquet shards materialized locally, **byte sizes re-checked** against the committed 2026-09-04 receipt |
| the shard digests | `derived/e22-esb-segment-table/parquet/*.parquet` | **INHERITED**, not recomputed: the receipt records `locally_rehashed: true` and `local_matches_lfs_oid: true` for all four, and this row may not hash the audio bytes |
| the boundaries | `derived/e22-esb-segment-table/segments-test.jsonl`, 2,735 rows | sha256 `7ef6911b…`, re-hashed on load against the receipt (`0c923a73…`) |
| the join | every shard row against the pinned table | `(id, source_id, segment_id, start_ts, end_ts)` must agree **exactly**, both directions, or the run refuses |

The projection is `source_id, segment_id, start_ts, end_ts, id, audio.bytes` — a **leaf**
projection, so `audio.path` and `sentence` are never decompressed. Each row group is released
before the next is read, and the two values taken out of it are computed inside Arrow:
`binary_length` for the blob's size and a 4,096-byte `binary_slice` for its container header. The
header parser refuses rather than repairs: a non-RIFF container, a RIFF size that disagrees with
the blob, a format tag other than uncompressed PCM, a missing `data` chunk, a `data` chunk longer
than the blob, or a byte count that is not a whole number of frames all raise.

**The row-for-row agreement is what stands in for the shard digest this row could not recompute.**
2,735 shard rows, 2,735 pinned rows, zero disagreements on any of the five fields.

## 2. The arrays are the published spans

Difference = `array_seconds − published_seconds`, positive meaning the release carries **more**
audio than the two columns describe.

| statistic | seconds |
|---|---:|
| minimum | **−0.148054** |
| p1 / p5 | −0.000201 / −0.000168 |
| p25 / **median** / p75 | −0.0000918 / **+0.0000316** / +0.0000612 |
| p95 / p99 / maximum | +0.000110 / +0.000247 / **+0.000290** |
| mean / stdev | −0.000126 / 0.003826 |

| bucket (s) | utterances |
|---|---:|
| ≤ −0.09 | 2 |
| (−0.09, −0.01] | 1 |
| (−0.01, −0.001] | 0 |
| (−0.001, −0.0000625] | 801 |
| **(−0.0000625, +0.0000625] — within one 16 kHz frame** | **1,266** |
| (+0.0000625, +0.001] | 665 |
| > +0.001 | 0 |

**2,732 of 2,735 (99.89 %) are span-faithful within the 1 ms tolerance**, which was fixed in the
module before any shard was read and is itself generous: one frame at 16 kHz is 0.0000625 s and
the float32 ulp of a 4,000 s boundary is about 0.00049 s, while a symmetric pad able to explain
the measured overlap would have to be 0.09 s per side. **The measured pad is +0.0000158 s per side
at the median** — three and a half orders of magnitude too small. Whatever produced the overlap,
it was not padding at cut time.

Expressed in samples rather than seconds — `frames − round(published × rate)` — the residual is
sub-frame everywhere but the three clamped tails: 341 rows land exactly, 916 are one frame long,
463 two, 301 three short, 230 four short, and 93 sit beyond ±4 frames, which at 24 kHz is 0.17 ms.
This is resampling and rounding residue, not a boundary policy.

### The three exceptions, named

All three are **shorter** than their published span and all three are the **last shipped segment
of their call**: the release clamped a final `end_ts` that runs past the parent recording, exactly
as this study's own slicer clamped `4481952-631` on dev (−0.0799 s).

| sample | rate | published s | array s | difference s |
|---|---:|---:|---:|---:|
| `4470290-178` | 24,000 | 13.180054 | 13.032000 | **−0.148054** |
| `4483338-619` | 24,000 | 8.720215 | 8.612125 | −0.108090 |
| `4432298-351` | 16,000 | 19.140381 | 19.060125 | −0.080256 |

Those three account for 0.336 s of the release's 0.344 s total shortfall (19,494.512 s of array
against 19,494.857 s of published span).

## 3. The released arrays' own adjacent-pair geometry

Each released array anchored at its own published `start_ts` and extended by its measured
duration, so `gap = start_next − (start_previous + array_seconds_previous)`. 2,729 pairs.

| | released arrays | published timestamps | centered (symmetric-pad reading) |
|---|---:|---:|---:|
| overlapping | **1,959 (71.78 %)** | 1,944 (71.23 %) | 1,956 (71.67 %) |
| touching exactly | 0 | 19 | 0 |
| separated | 770 | 766 | 773 |
| largest overlap (s) | **−0.180452** | −0.180420 | −0.180463 |
| median gap (s) | **−0.139956** | −0.139893 | −0.139950 |
| duplicated audio (s) | **274.275** | 274.283 | 274.162 |

| gap bucket (s) | released pairs |
|---|---:|
| ≤ −0.18 | 137 |
| (−0.18, −0.16] | 555 |
| (−0.16, −0.12] | 954 |
| (−0.12, −0.08] | 196 |
| (−0.08, −0.04] | 59 |
| (−0.04, 0] | 58 |
| (0, 0.25] | 151 |
| (0.25, 1] | 316 |
| (1, 4] | 280 |
| > 4 | 23 |

**The three readings agree to within half a percentage point**, so the verdict does not depend on
where the array is assumed to sit inside its span. The 0.55-point difference between the released
and published shares is the arrays being a fraction of a frame longer than the columns: 15 pairs
that the timestamps leave touching or barely separated tip into overlap, and the 19 exactly
touching pairs become 0.

Every call is affected and none is an outlier:

| call | pairs | overlapping | share | duplicated s |
|---|---:|---:|---:|---:|
| 4432298 | 350 | 222 | 63.4 % | 30.372 |
| 4450488 | 507 | 386 | **76.1 %** | 52.774 |
| 4470290 | 177 | 134 | 75.7 % | 18.244 |
| 4479741 | 472 | 322 | 68.2 % | 43.473 |
| 4483338 | 618 | 434 | 70.2 % | 62.096 |
| 4485244 | 605 | 461 | **76.2 %** | 67.315 |

### Against the dev cut this study made

| | dev, this study's clips | test, the ESB release's arrays |
|---|---:|---:|
| adjacent pairs | 6,028 | 2,729 |
| overlapping | 4,681 (**77.7 %**) | 1,959 (**71.8 %**) |
| hard cap (s) | **−0.18042** | **−0.180452** |
| median gap (s) | −0.140015 | −0.139956 |
| duplicated audio (s) | 668.726 (1.70 % of 39,292.6) | 274.275 (1.41 % of 19,494.5) |

**The same wall at 0.18 s, the same 0.14 s median, the same dense-up-to-a-wall shape.** The
clip-boundary audit read that shape as a fixed symmetric pad of about 0.09 s per side in the
**upstream segmentation** and labelled the reading an inference from the cap. This check
strengthens it and narrows where it can live: the pad is not in this study's slicer (measured
zero) and it is not in the release's cutter (measured +0.0000158 s per side), so it is in the
**boundary table both of them consume**. Two independent cutters, two different splits, one
geometry.

## 4. What this settles, and what it does not

**Settled.** The published systems receive the overlap. They consume these arrays; these arrays
are the published spans; the published spans overlap. So the overlap is a property of the ESB
protocol, shared by every system on that column, and it is **not** a difference between this
study's reproduction and the published 9.79 / 12.3. The boundary-exact cell measures **our**
sensitivity to a trigger everyone was handed.

**Not settled, and not claimed.** This says nothing about whether the overlap costs the published
systems anything — no published system's outputs are readable here — and nothing about the dev
split's released arrays, which do not exist on disk. It also does not lift the clip-boundary
audit's own bound: 274.3 s of test overlap at that corpus's word rate is a small number of words,
and on dev the same reasoning put the delivered share of the boundary mass at about a quarter.

**A second, separate deviation surfaced and is recorded rather than acted on.** The release does
**not** store one audio geometry. It stores each call's native container:

| call | container |
|---|---|
| 4432298 | 16,000 Hz, 2 ch, 16-bit PCM (351 rows) |
| 4450488 | 22,050 Hz, 2 ch, 16-bit PCM (508 rows) |
| 4470290, 4479741, 4483338, 4485244 | 24,000 Hz, 1 ch, 16-bit PCM (1,876 rows) |

This study's clips are all 16 kHz mono, decoded by `librosa` from the locked `earnings22-original`
MP3s. The published evaluations resample these WAV arrays to their model's rate in process. So the
two paths agree on the **span** and differ on the **decode**: different source container, different
resampler, different channel-fold. That is a real residual difference between our reproduction and
the published one, its sign is unknown, and nothing here measures it. It is named as a candidate
alongside D2 (Q4_K_M against an unstated published precision), not as a finding.

## 5. The 2,735-versus-2,741 gap, explained in shape

The 2026-09-04 segment-table receipt records the six-row gap between this study's pinned 2,735
rows and the 2,741 the leaderboard config and the NeMo AutoModel post both state as **UNEXPLAINED**
and refuses to reconcile it. The shipped segment ids decide its size at no extra cost:

| call | rows | index range | index not shipped |
|---|---:|---|---:|
| 4432298 | 351 | 0–351 | **23** |
| 4450488 | 508 | 0–508 | **467** |
| 4470290 | 178 | 0–178 | **23** |
| 4479741 | 473 | 0–473 | **467** |
| 4483338 | 619 | 0–619 | **467** |
| 4485244 | 606 | 0–606 | **467** |

**Every call ships a contiguous index range with exactly one hole, and 2,735 + 6 = 2,741.** The
published N counts the segments the release's own ids enumerate; the release ships six fewer. The
shards' parquet metadata declares 684 + 684 + 684 + 683 = 2,735 rows, so the six are missing
**upstream** — this study's extraction dropped nothing.

**The cause is not established and is not guessed at.** Two distinct indices across six calls (23
twice, 467 four times) is not what an independent per-row filter looks like, and determining what
produced it would mean reading the upstream build, which is a network read this row does not make.
Recorded as: the gap's *size* is explained, its *cause* is not. Its consequence is bounded either
way — six rows are 0.22 % of the population and cannot move the 6.15-point alignment gap the
2026-09-04 verdict reported over 2,735 rows.

## 6. Limits

* **Durations, not audio.** Every number comes from container headers. If a released blob's
  `data` chunk disagreed with its own samples the parser would not know; it checks the declared
  sizes against the blob's length and against a whole number of frames, and nothing more.
* **Shard digests are inherited.** They were re-hashed on 2026-09-04 against the published
  git-LFS oids; this row re-checks byte sizes and the full row-for-row agreement with the pinned
  table, and does not recompute the digests because it may not hash the audio bytes.
* **The dev release is unreadable offline** and the transfer to dev is an inference from shared
  provenance, not a measurement.
* **The anchoring is an assumption, tested three ways.** Anchoring at `start_ts`, anchoring on
  the published span with a symmetric pad, and the published timestamps themselves all give the
  same verdict; no reading in which the arrays are tight exists.
* **The 0.09 s pad remains an inference from a cap.** This check moves it upstream of both
  cutters; it does not open the builder that produced the boundary table.

## 7. What this licenses

**Nothing new.** It closes one comparability question and makes the boundary-exact cell's claim
rule unconditional. The boundary-exact dev cell and the `whisper-large-v3` anchor still need their
own owner decisions and their own exposure rows; no clip was re-cut, no population was scored, and
the six ESB test calls stay exactly as calibration-exposed as the 2026-09-04 allowance left them.

## 8. Defect, disclosed

Two exploratory probes of shard `test-00000-of-00004-d1f708ede2712e90.parquet` were run **before**
this row's ledger entry existed: the parquet footer metadata, then one row-group read from which
three blob lengths, the first 48 header bytes of three blobs, two `id` values and one
`(start_ts, end_ts)` pair were printed. That is a touch of a calibration-exposed population made
before its row was registered, and it breaks the register-before-you-read rule. No `sentence`
value, no audio sample, no output and no score was read by either probe, and every figure they
produced is re-derived by the registered pass above. The defect is carried in the ledger row's
inherited-exposure field and is repeated here rather than left in one place.
