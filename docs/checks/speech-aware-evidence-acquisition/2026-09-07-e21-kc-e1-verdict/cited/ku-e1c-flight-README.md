# KU-E1c — the flight of `E21-ku-e1c-brief-placebo`, all 44 calls

The form-twin half of `docs/readiness/2026-09-06-e21-kc-e1-pre-meeting-brief-v2-preregistration.md`
§8 item 5. Exposure row `SAEA-E21-KU-E1C-PLACEBO-44-V1`. Study commit **`60fca960`**,
`study_repo_dirt` [] in the sealed manifest. Attempt
**`attempt-20260907T200859Z-251383`**, manifest `COMPLETED`.

**This receipt reports; it decides nothing.** No pairing, no interval, no verdict: the contrast
against KC-E1 and against the sealed comparator is a separate act under its own row. The four
numbers below are this cell's own, read once from its own complete manifest.

---

## The cell that flew

One contact per fixed 90-second window, 1,593 windows over the 44
`earnings21-original` discovery calls, arm `fixed-legal-context`, policy `obs-agent-loop`, evidence source
`conec-class-lists-placebo-token-matched` at `brief_max_entries_per_class` 12, composed config hash
`f1f63fce...`, protocol hash `d05b3a8d...`, split identity
`fcc1b0bc...d69e`. Temperature 0, seed 20260803, `max_tokens` 1024, `obs_batch_slices` 8.

The twin differs from KC-E1 in exactly two composed keys, `evidence_source` and the byte pin of its
own pad plan. Its text is derived from each call's OWN two ConEC files by
`DerivedEvidenceRegistry`, with the pad plan's per-line `" item"` repeats inside `params_hash`; no
line of it comes from another call's context, from the evaluation calls' context, or from any
reference transcript.

**This is the first and only attempt of this flight.** No recovery re-registration was used.

Spend against the registered ceilings:

| | realized | ceiling |
|---|---:|---:|
| model calls | **1,593** | 1,750 |
| speech-audio seconds | **141,345.8527** | 150,000 |
| GPU hours (manifest nvidia-smi sampler) | **1.0087** | 1.6 |
| paid API spend | 0 | 0 |

For comparison at the same geometry and the same convention: the sealed direct comparator realized
0.9734 GPU-h for one pass and KC-E1 realized 0.9948.

## Serving — attached, never started, never stopped

`saea-driver run --session-receipt` reached the coordinator's resident session
`e21-np6-c36864-20260907b` through `core.session.attach_session`; the flight started no server
and stopped none. Geometry `-c 36864 -np 6`, 6 slots of 6,144 tokens, port 8080, fragment
`q4km-e21-buf90-mmproj-gpu-04ccc72a-np6`, bf16 mmproj resident, raw audio, no feature cache.
`scripts/run_arm_sequence.sh` was deliberately not used: its pre-arm cleanup refuses while a session
is resident and its `smoke` step would have spawned a second llama-server.

Monitor summary over this attempt's own contact window (`serving_monitor.py summarize`):

| wall | active | parked | requests | mean / peak power | mean util | host free min | VM avail min |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 5,790.53 s | 4,681.07 s (80.8 %) | 1,109.47 s (19.2 %) | 1,584 | 71.82 W / 102.19 W | 59.7 % | 12.18 GB | 24.15 GB |

`requests_delta` is a lower bound at the 10-second sampling interval; the charged contact count is
1,593, from the manifest and the trace. The monitor's own `requests_total` read
**1,578** at 2026-09-07T20:01:02Z, before this flight's first contact, and **3,162** at
2026-09-07T21:47:51Z, after its last: a difference of **1,584**.

**`core.driver.run_experiment_bundled` writes no session-attach receipt** — that artifact belongs to
`core.flight.FlightRuntime`, which cannot express this carrier's 90-second OBS tiling. The summary
above therefore comes from the SAME in-tree instrument, `scripts/serving_monitor.py summarize`, over
this attempt's own run wall window (20:10:15Z to 21:46:54Z), which counts any head or tail idle as
parked against this flight rather than hiding it.

**Host memory, and the reason it is reported here rather than buried.** Windows free memory reached a
minimum of **12.18 GB** during this pass, against the 12 GB floor
`scripts/serving_session.sh start` refuses below and the incident that killed KC-E1's first attempt.
The VM's own working set on the host peaked at 40.08 GB against the
44 GB `.wslconfig` cap. A CPU-only sibling task was running throughout. The flight completed, but the
margin was thin and the next flight scheduled beside a heavy CPU job should know it.

## The prompt on the wire, against the token match

Per-window prompt tokens **548 / 1,862 / 2,047**
(min / median / max). The prompt-fit and token-match receipts predicted a twin text envelope of
461 /
680 /
862 against the arm's
454 /
673 /
855 — a constant
**+7-token** residual that is the
`[evidence <id>] ` header of the two blocks and not the brief.

**Per-call check: 0 of 44 calls are off the
`fit + 2` identity** (the two special tokens the fit counted separately).
Every one of the 44 calls realized the token match exactly.
The token match's per-line and per-call equality with the treatment's brief is asserted by that
receipt's own measurement over all 44 calls (`brief_tokens_equal_on_every_call: true`), and this
flight re-derives none of it: the flight carries no tokenizer.

Worst realized request **3,071** against the 6,144-token
slot — margin factor **2.001**, against the token match's predicted
3,058. Prompt tokens
**2,918,425**, completion **430,779**.

## Throughput

1,593 windows in 5,799 s of run wall
(96.65 min, 2026-09-07T20:10:15Z to 2026-09-07T21:46:54Z):
**16.48 windows per minute**, realized realtime factor
**38.92x**, 3,631.40 GPU-seconds, latency summed
over 6 slots 33,398.59 s, CPU 348.21 s, peak VRAM
22,726 MiB, gate setup 17.88 s. Finalize took a
further 1,637 s and the whole-manifest score batch
1,528 s. KC-E1 ran 5,884 s at
16.24 windows per minute and 39.47x.

## The four metrics, all 44 calls

Scored **once** over the complete manifest, never sharded, by `core.scoring_batch` with
`--include-per-sample` and one job (`batch-summary.json`: 1 job,
1 succeeded, 0 failed,
`no dataset sharding and no averaging of shard-level official metrics`, 1,414.21 s, result sha256
`5d323555bf0139fee8305bdc9ebf1de80b6e47432301b7bc20215375cd6f11c3`). The batch read is `verified: true` and its four metric aggregates are **byte-identical** to the ones finalize sealed (`batch_read_vs_sealed.byte_identical`), against sealed scores sha256 `3ed09669a723ddf0f519e7b03138545dab37caf1de8d92769c0bb399e0fedb63`.

| metric | KU-E1c, all 44 |
|---|---:|
| corpus WER (`asr-wer-whisper`, Whisper normalizer) | **8.354 %** — S 13,254 / D 6,460 / I 10,340 over 359,765 reference words |
| ConEC-mirror **PERSON** entity WER | **23.723 %** — S 597 / D 95 over 2,917 reference words |
| ConEC-mirror ORG entity WER | 18.244 % — S 692 / D 104 over 4,363 |
| numeric-value accuracy (`numeric-value-accuracy-v1`) | **90.939 %** — 8,852 of 9,734 expected numeric words, 889 spurious |
| semantic high-impact error rate | **0.0303 %** — 44 HIGH insertions, 109 HIGH reference words, taxonomy `e22-semantic-scan-2026-09-06-content-impact-word-pair-v1` |

Every ConEC class with its reference-word count is in `flight-receipt.json`
(`scores_aggregates`) and in `score-read.json`; the per-sample rows are in `score-read.json`.

## Decode-cap saturation — the named covariate of this pair

`saturated_slice_count` is **2**; `skipped_slice_count` is
0. KC-E1 saturated 2 and the sealed
comparator 0.

| call | window | raw response | accepted |
|---|---|---:|---:|
| `4384683` | 1,260-1,350 s | 2,425 chars | 0 |
| `4397829` | 360-450 s | 6,040 chars | 0 |

`reproduction.obs_loop` treats a slice that reaches the 1,024-token cap as a truncated decode rather
than a transcript end: it contributes the empty string to the stitched hypothesis and is counted,
never scored silently. Reported, not repaired.

**The count matches KC-E1's; the calls do not.** KC-E1 saturated `4360717` and `4363614`; this cell
saturated `4384683` and `4397829` — two disjoint pairs. So the pair's saturation is not a property of
particular windows that both arms would blow through, and the covariate is balanced in COUNT while
being carried by different calls in each arm. A verdict pairing these two cells window by window must
treat all four of these windows as this-arm-only deletions, not as a shared exclusion.

The trace and the manifest agree on both the count and the sample ids
(`saturation.trace_and_manifest_agree`).

## Carried rather than discovered

`fixed-legal-context` predates the 2026-08-15 legality doctrine's either-field rule, so this attempt
records provenance tier `UNVERIFIED` with a GRANDFATHERED declaration warning in the manifest's
`legality` block. That is a property of the arm, not of this cell.

**One placement deviation, recorded rather than hidden.** `saea-driver run --run-dir` writes straight
into the directory it is given, and this flight passed the run ROOT where KC-E1 passed an
attempt-named subdirectory, so this attempt's sealed artifacts sit at
`$SPEECHRL_DATA_DIR/runs/SAEA-E21-KU-E1C-PLACEBO-44-V1/` rather than one level deeper. Placement
only: the manifest, outputs and trace are named by run id and hashed below, the attempt record lives
under `$SPEECHRL_DATA_DIR/attempts/<run id>/` either way, and no protocol, metric or datum moves.

## Files

| file | what |
|---|---|
| `flight-receipt.json` | identity, plan, serving and monitor summary, windows, per-call token distribution against the token match, cost, throughput, evidence provenance, saturation, and every artifact's SHA-256 |
| `score-read.json` | the `core.scoring_batch --include-per-sample` verified read, aggregates and per-sample rows |
| `batch-summary.json` | the batch record: one complete-manifest job, no sharding |
| `jobs.jsonl` | the one job that was run |

Sealed run artifacts live under `$SPEECHRL_DATA_DIR/runs/SAEA-E21-KU-E1C-PLACEBO-44-V1/` and never
enter Git: manifest sha256 `437da898c7a80633665daf1ae305707e2db16d98a06e83c0bb46120e11f8000f`, outputs
`dc1af253e03a790e7f1a0578b057629621ab19f1c3ff4a89841cbb7a9db9fd9a`, trace `a9c8f95cfb77116a425054e5c981c585c7bd76a508d0023d3842af4bf7a2cfae`, plan
`cbb707750c6c6b8eb5258461e69a856f45a205d24607fa6a3770e0a8844ba4cc`.
