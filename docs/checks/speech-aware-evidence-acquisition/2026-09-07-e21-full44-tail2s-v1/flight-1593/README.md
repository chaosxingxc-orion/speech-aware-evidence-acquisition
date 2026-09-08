# The flight of `SAEA-E21-FULL44-TAIL2S-V1` — all 1,593 windows over all 44 calls

Exposure row `SAEA-E21-FULL44-TAIL2S-V1`, registered and committed at study commit `81f2b1e9`
**before the first contact**. Attempt **`attempt-20260907T231248Z-00f13c`**, manifest `COMPLETED`,
attempt `FINALIZED`, `study_repo_dirt` empty.

**This receipt reports the flight; the verdict is
`docs/readiness/2026-09-07-e21-full44-tail2s-v1-verdict.md`** and its machine form is
`../verdict/result-summary.json`.

**This is the first and only attempt of this flight.** No recovery re-registration was used, and the
one this flight was allowed remains unspent.

---

## The cell that flew

One contact per fixed 90-second window, 1,593 windows over the 44 `earnings21-original` discovery
calls, arm `bare-core`, policy `obs-agent-loop`, evidence source `none`, composed config hash
`3d28fb5abfe2ff6d05cbefac1384e9088504794d9859071a4e5fcc9f16047d22` — the value §6.3 of the
preregistration recorded before this row existed — protocol hash
`16e9dd6753592e37a21ab4b4136c0ac48df45a5b7cc859d608b9a1fac90bc660`, split identity
`fcc1b0bc…d69e`. Temperature 0, seed 20260803, `max_tokens` 1024, `obs_batch_slices` 8.

**ONE factor moves against the sealed comparator `SAEA-E21-FULL44-DIRECT-BASELINE-V2`**: the
baseline fragment's `obs_slice_tail_silence_seconds` 2.0, which appends exactly 32,000 zero samples
at 16 kHz to each buffered 90-second window AFTER the cut and before the request. The population,
split identity, dataset fragment, model fragment, serving geometry, server env, decoding params,
instruction, arm, policy, evidence source and every obs buffer/advance/snap/boundary-mode/VAD/
preprocess/tail-chars/retry/skip/batch setting are the comparator's, byte for byte. The baseline
fragment additionally declares the three agentic scorer ids the comparator scored post-hoc, so all
four §4.3 metrics come out of the verified scoring path rather than an out-of-band read.

## The §4.4 media falsifier, run before any score file was opened — 1,593 of 1,593

| check | result |
|---|---|
| windows checked | **1,593 of 1,593**, 44 of 44 calls |
| emitted slice SHA-256 equals the committed `@ts2` entry | **1,593** |
| delivered byte count equals the committed entry | **1,593** |
| delivered seconds = cut seconds + exactly 2.0 | **1,593** |
| byte count equals `44 + 2 × round(delivered × 16000)` | **1,593** |
| `preprocess` declares `tail-silence-2s` | **1,593** |
| `audio_seconds` still equals the CUT span (the tail moved no window) | **1,593** |
| `pre_sha256` equals the SEALED comparator's own cut for that window | **1,593** |
| window spans equal to the comparator's | **1,593** |
| **disagreeing rows** | **0** |

Delivered total **144,531.852688 s** and **4,625,089,378 bytes**, both exactly the committed
supplement's own `audio_seconds_total` and `total_bytes`. Cut total 141,345.852688 s, which is what
`SliceRecord.audio_seconds` meters and what the manifest charges.

**A defect was found on the first pass and it was in the checker, not the cell.** Eleven rows were
flagged on delivered seconds; all eleven were the same rounding artifact, the committed supplement
storing seconds to six decimals (22.914313) against the runtime's exact cut span (22.9143125) — a
5 × 10⁻⁷ gap at the receipt's own precision limit. The SHA-256 and byte-count checks passed on all
1,593 rows on that pass too, and those pin the delivered sample count exactly. The comparison is now
made at the receipt's own precision with the byte-count identity checked beside it. Recorded here
rather than quietly re-run.

**The wire agrees to the token.** Prompt tokens **1,977,383** against the comparator's **1,935,965**:
a difference of **41,418 = 1,593 × 26 exactly**, no residue. 26 tokens is 2.0 s at the encoder's 13
tokens per second. Per-window prompt tokens 101 / 1,258 / 1,258 (min / median / max), worst request
1,258 against the 6,144-token slot, margin factor **4.88**. Completion 435,392 against the
comparator's 439,532.

## Serving — attached, never started, never stopped

`saea-driver run --session-receipt` reached the coordinator's resident session
`e21-np6-c36864-20260907b` through `core.session.attach_session`; the flight started no server and
stopped none. Geometry `-c 36864 -np 6`, 6 slots of 6,144 tokens, port 8080, fragment
`q4km-e21-buf90-mmproj-gpu-04ccc72a-np6`, bf16 mmproj resident, raw audio, no feature cache.
`scripts/run_arm_sequence.sh` was deliberately not used: its pre-arm cleanup refuses while a serving
session is resident and its smoke step would have spawned a second llama-server.

Monitor summary over this attempt's own contact window (2026-09-07T23:12:50Z to 2026-09-08T00:45:19Z):

| wall | active | parked | requests | mean / peak power | mean util | host free min | VM avail min |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 5,544.30 s | 4,549.85 s (82.1 %) | 994.45 s (17.9 %) | 1,584 | 74.08 W / 99.51 W | 60.8 % | 12.96 GB | 24.89 GB |

`requests_delta` is a lower bound at the 10-second sampling interval; the charged count is 1,593.
`core.driver.run_experiment_bundled` writes no session-attach receipt — that artifact belongs to
`core.flight.FlightRuntime`, which cannot express this carrier's 90-second OBS tiling — so the
summary comes from the same in-tree instrument over the attempt's own run wall window, which counts
head and tail idle as parked against this flight rather than hiding it.

**Host memory.** Windows free memory bottomed at **12.96 GB**, above the 12 GB floor
`scripts/serving_session.sh start` refuses below and above KU-E1c's 12.18 GB, with the VM's working
set peaking at 38.93 GB of its 44 GB cap. A CPU-only sibling task ran for part of the pass.

## Cost, well inside the untouched ceilings

| | realized | ceiling |
|---|---:|---:|
| model calls | **1,593** | 1,750 |
| speech-audio seconds (metered cut span) | **141,345.8527** | 150,000 |
| delivered speech-audio seconds | 144,531.8527 | — |
| GPU hours (manifest nvidia-smi sampler) | **0.9765** | 1.2 |
| paid API spend | 0 | 0 |

At the same geometry and the same convention: the sealed comparator realized 0.9734 GPU-h, KC-E1
0.9948 and KU-E1c 1.0087. **This is the cheapest of the three post-comparator passes**, despite
carrying 2.3 % more audio per request.

## Throughput

1,593 windows in **5,549 s of run wall (92.48 min**, 23:12:50Z to 00:45:19Z): **17.225 windows per
minute**, realized realtime factor **40.21×** (metered cut audio seconds over the manifest's own
nvidia-smi busy seconds, the convention the KC-E1 and KU-E1c receipts use), 3,515.49 GPU-seconds,
latency summed over 6 slots 31,999.2 s, CPU 346.2 s, peak VRAM 22,726 MiB, gate setup 9.9 s. The
fastest pass of the family: comparator 16.38, KC-E1 16.244, KU-E1c 16.482 windows per minute.
Finalize took a further 2,807 s and the whole-manifest score read 2,702 s.

## The four metrics, all 44 calls

Scored **once** over the complete manifest, never sharded. `saea-driver finalize` verified the
bundle, scored all seven declared scorers, wrote `scores.json` and settled the attempt `FINALIZED`
(MLflow run `37dbaa7004d547cf9bda1e85fcd58b7c`); a `core.scoring_batch` read with
`--include-per-sample` over the SAME complete manifest (`batch-summary.json`: 1 job, 1 succeeded, 0
failed, 2,501.8 s, *no dataset sharding and no averaging of shard-level official metrics*) came back
`verified: true` with **all seven scorers' aggregates byte-identical** to what finalize sealed.
Sealed scores sha256 `c5f195a43cd97b65526429228bb1bf27d0432713c6fe9a249af1a2c56d136ad7`; read result
sha256 `9b770e6c64dc6f9d68cf06ebfa189b9e2dde2c995b4669b031144308a8370eb4`.

| metric | this cell, all 44 |
|---|---:|
| corpus WER (`asr-wer-whisper`, Whisper normalizer) | **7.27141 %** — S 12,931 / D 6,192 / I 7,037 over 359,765 reference words |
| ConEC-mirror overall | 7.27141 % |
| ConEC-mirror non-entity | 4.83355 % |
| ConEC-mirror **PERSON** | **23.17449 %** — S 564 / D 112 over 2,917 |
| ConEC-mirror ORG | 16.86913 % — S 654 / D 82 over 4,363 |
| numeric-value accuracy | **90.77460 %** — 8,836 of 9,734 expected numeric words, 826 spurious |
| semantic high-impact error rate | **0.02696 %** — 97 HIGH reference words, 34 HIGH insertions, taxonomy `e22-semantic-scan-2026-09-06-content-impact-word-pair-v1` |

Every entity class with its reference-word count is in `flight-receipt.json` and in
`../verdict/result-summary.json`.

## Decode-cap saturation — one window, on a call no sibling saturated

`saturated_slice_count` **1**; `skipped_slice_count` **0**.

| call | window | window seconds | raw response | accepted |
|---|---|---|---:|---:|
| `4346818` | `#w0035` | 3,060–3,150 s | 3,135 chars | 0 |

The comparator saturated **0**; `SAEA-E21-KC-E1-BRIEF-44-V1` saturated 2 (`4360717`, `4363614`) and
`SAEA-E21-KU-E1C-PLACEBO-44-V1` saturated 2 (`4384683`, `4397829`). **All five saturated windows in
this family lie on five different calls**, so the covariate is arm-local everywhere and no window is
a shared exclusion. `reproduction.obs_loop` treats a slice that reaches the 1,024-token cap as a
truncated decode rather than a transcript end: it contributes the empty string and is counted, never
scored silently. It costs this measurement 90 s of 141,345.85 — 0.064 % of the audio. Reported, not
repaired; the verdict's §5 bounds its effect.

## Files

| file | what |
|---|---|
| `falsifier.json` | every one of the 1,593 windows: emitted SHA-256, byte count, delivered seconds, `pre_sha256` chain, span, saturation |
| `flight-receipt.json` | identity, plan, serving and monitor summary, per-call window counts, token distribution, cost, throughput, saturation and every artifact's SHA-256 |
| `window-section.json` | the per-window intervals and the §4.3 clause-3 mechanism slices |
| `batch-summary.json` | the verified score-batch record: one complete-manifest job, no sharding |
| `jobs.jsonl` | the one job that was run |
