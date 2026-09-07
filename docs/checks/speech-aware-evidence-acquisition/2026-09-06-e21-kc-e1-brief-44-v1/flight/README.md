# KC-E1 — the flight of `E21-kc-e1-brief-whole-prompt`, all 44 calls

The flight half of `docs/readiness/2026-09-06-e21-kc-e1-pre-meeting-brief-v2-preregistration.md`
§8 item 5, for the treatment cell of the pre-meeting-brief pair. Exposure row
`SAEA-E21-KC-E1-BRIEF-44-V1`. Study commit **`bfab2b16`**, clean tree, `study_repo_dirt` empty in
the sealed manifest. Attempt **`attempt-20260907T171238Z-f02eef`**, state `FINALIZED`, manifest
`COMPLETED`.

**This receipt reports; it decides nothing.** No pairing, no interval, no verdict: the comparator
contrast, the form twin `KU-E1c` and the decision rule of §5 are separate acts under their own rows.
The four numbers below are this cell's own, read once from its own complete manifest.

---

## The cell that flew, and the two attempts behind it

One contact per fixed 90-second window, 1,593 windows over the 44 `earnings21-original` discovery
calls, arm `fixed-legal-context`, policy `obs-agent-loop`, evidence source `conec-class-lists` at
`brief_max_entries_per_class` 12, config hash `3ac6d436…`, protocol hash `da55a18d…`, split identity
`fcc1b0bc…d69e`. Temperature 0, seed 20260803, `max_tokens` 1024, `obs_batch_slices` 8.

This is the **second and last** attempt. The first, `attempt-20260907T142632Z-a388ef`, was killed at
42 of 44 calls with no seal when the host's low-memory watchdog took the coordinator's serving
wrapper down (`.wslconfig memory=56GB` on a 63.4 GB host; fixed the same day at `memory=44GB` with
gradual reclaim plus the E7c host-memory instrumentation). That spent the one permitted recovery
re-registration; the ledger's dated block carries the arithmetic. **No byte of it is read here** —
it never produced a manifest, and scoring runs once per complete manifest.

Cumulative durable spend across both attempts, against the raised ceilings:

| | attempt 1 (dead) | attempt 2 (this one) | cumulative | ceiling |
|---|---:|---:|---:|---:|
| model calls | 1,520 | 1,593 | **3,113** | 3,270 |
| speech-audio seconds | 134,821.4766875 | 141,345.8526875 | **276,167.329375** | 285,000 |
| GPU hours | 1.4993 (monitor wall) | 0.9948 (manifest sampler) | see below | 3.1 |

**The two GPU-hour conventions, stated rather than blended.** The published receipts price a pass by
the manifest's own `cost.gpu_seconds` — the nvidia-smi busy-time sampler — which for this attempt is
3,581.43 s = **0.9948 GPU-h** (the comparator's was 0.9734). The dead attempt has no manifest and so
no sampler figure; it was priced, conservatively, by the session monitor's wall clock over its
contact window, 1.4993 h, and that is the number the 3.1 ceiling was built from. Read the pair the
same conservative way — monitor wall for both — and they sum to 1.4993 + 1.6298 = **3.1291 GPU-h**,
**105 seconds past the declared 3.1**. Read them by the receipts' own convention and the pair is
comfortably inside. Neither reading is hidden, and the in-flight stop rule (which watches the
sampler figure, projecting 0.9948 against 3.1) correctly never fired.

## Serving — attached, never started, never stopped

`saea-driver run --session-receipt` reaches the coordinator's resident session
`e21-np6-c36864-20260907b` through `core.session.attach_session`; `scripts/run_arm_sequence.sh` was
not used, because its pre-arm cleanup refuses outright while a serving session is resident and its
`smoke` step would have spawned a second llama-server. Geometry `-c 36864 -np 6`, 6 slots of 6,144
tokens, port 8080, fragment `q4km-e21-buf90-mmproj-gpu-04ccc72a-np6`, bf16 mmproj resident, raw audio,
no feature cache.

Monitor summary over this attempt's own contact window (`serving_monitor.py summarize`):

| wall | active | parked | requests | mean / peak power | mean util | host free min | VM avail min |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 5,867.33 s | 4,634.32 s (79.0 %) | 1,233.01 s (21.0 %) | 1,578 | 72.19 W / 101.63 W | 59.2 % | 17.10 GB | 29.00 GB |

`requests_delta` is a lower bound at the 10-second sampling interval; the charged contact count is
1,593, from the manifest and the trace. **The host-memory fix held**: the Windows side never fell
below 17.10 GB free, against the 12 GB floor the incident produced.

## The prompt on the wire, against the fit

Per-window prompt tokens **541 / 1,855 / 2,040** (min / median / max). Stripping the speech tokens,
the brief's own text envelope reads **456 / 688 / 870**, against the prompt fit's 454 / 673 / 855 —
and the receipt's per-call check is exact: **every one of the 44 calls realized the fit's
`text_tokens` + 2**, the two special tokens the fit counted separately, with **zero** calls off that
identity. The per-window maxima run 13 above the per-call value on the tail window only, which is
the speech-token estimate's own block rounding (`13 × ceil(seconds)`), not a varying brief.

Worst realized request **2,040 + 1,024 = 3,064** against the 6,144-token slot — margin factor
**2.005**, against the fit's predicted 3,051 and factor 2.014. The cap-12 fit held on the wire.

Tokens against the comparator: prompt **2,907,274** vs 1,935,965 (**+50.2 %**), completion
**423,115** vs 439,532 (−3.7 %). The extra prompt cost **+2.2 %** of GPU time (0.9948 vs 0.9734 h) —
the prefill is cheap beside the 90 seconds of audio in every window.

## Throughput

1,593 windows in 5,884 s of run wall (98.07 min): **16.24 windows per minute**, realized realtime
factor **39.47×**, latency summed over 6 slots 32,667.30 s, CPU 339.49 s, peak VRAM 22,726 MiB,
gate setup 19.76 s. Finalize (verify, score, upload, settle) took a further 1,528 s.

## The four metrics, all 44 calls

Scored **once** over the complete manifest, never sharded, by `core.scoring_batch` with
`--include-per-sample` and one job (`batch-summary.json`: 1 job, 1 succeeded, 0 failed,
`no dataset sharding and no averaging of shard-level official metrics`, 1,441.29 s, empty stderr).
The batch read is `verified: true` and its aggregates are **byte-identical** to the ones finalize
sealed, on all four metrics.

| metric | KC-E1, all 44 |
|---|---:|
| corpus WER (`asr-wer-whisper`, Whisper normalizer) | **8.736 %** — S 13,022 / D 8,393 / I 10,014 over 359,765 reference words |
| ConEC-mirror **PERSON** entity WER | **18.341 %** — S 421 / D 114 over 2,917 reference words |
| ConEC-mirror ORG entity WER | 17.992 % — S 644 / D 141 over 4,363 |
| numeric-value accuracy (`numeric-value-accuracy-v1`) | **90.189 %** — 8,779 of 9,734 expected numeric words, 887 spurious |
| semantic high-impact error rate | **0.0334 %** — 43 HIGH insertions, 120 HIGH reference words, taxonomy `e22-semantic-scan-2026-09-06-content-impact-word-pair-v1` |

Every ConEC class with its reference-word count is in `flight-receipt.json`
(`scores_aggregates.conec-entity-wer-official.by_entity_type`) and in `score-read.json`; the
per-sample rows (44 per metric) are in `score-read.json`. Insertions are not attributed to entity
classes, by the mirror's own definition.

## Two windows saturated the decode cap, and the comparator's zero did not

`saturated_slice_count` is **2**; `skipped_slice_count` is 0. `reproduction.obs_loop` treats a slice
that reaches the 1,024-token cap as a truncated decode rather than a transcript end: it contributes
the empty string to the stitched hypothesis and is counted, never scored silently.

| call | window | raw response | accepted |
|---|---|---:|---:|
| `4360717` | 1,980–2,070 s | 5,426 chars | 0 |
| `4363614` | 2,340–2,430 s | 4,195 chars | 0 |

Both ran far past the ~1,550-char typical window before the cap stopped them, so this is
over-generation under the brief, not two windows lost at random. It costs the measurement 180 s of
141,345.85 — 0.127 % of the audio — and it lands in this cell's deletions. **The comparator saturated
none.** Reported, not repaired: the sealed hypothesis is what the OBS rule produced.

## The window re-aggregation check REFUSED, and the cause is the instrument

`scripts/e21_window_pairing_read.py` (§8 item 6, exposure row `SAEA-E21-MF-WINDOW-PAIRING-V1`) was
run over this attempt and **refused** at `assert_stitch_reproduces_outputs` on 2 of the 44 calls:
`4360717` rebuilds 67,235 chars against the sealed 61,808, `4363614` 81,113 against 76,917.

**The cause is named, and it is the instrument, not the flight.**
`analysis.e21_window_pairing.stitched_windows_from_trace` recovers each window's text from the
`MODEL_RESPONSE` record and never reads the `OBS` record's `obs_saturated` / `obs_accepted_chars`, so
it re-admits exactly the text the sealed stitch excluded. The two differences are **5,427** and
**4,196** chars — the two saturated windows' raw text plus the single joining space each, exact, with
no residue. The instrument was built and proven on `SAEA-E21-FULL44-DIRECT-BASELINE-V2`, whose
`saturated_slice_count` is 0, so the case never arose there.

The fix is one line — treat an `obs_saturated` or `obs_skipped` window as an empty span, exactly as
`reproduction.obs_loop` already does — and it belongs to the instrument's own registered row, before
the verdict's per-window decomposition, not to this flight. **None of the four sealed metrics depends
on it**: they are computed from the sealed outputs by `core.scoring_batch`. What is blocked is the
per-window pairing the verdict will want, and the verdict agent must clear it first.

## Carried rather than discovered

`fixed-legal-context` predates the 2026-08-15 legality doctrine's either-field rule, so this attempt
records provenance tier `UNVERIFIED` with a GRANDFATHERED declaration warning in the manifest's
`legality` block. That is a property of the arm, not of this cell, and closing it is not this
flight's business — the preregistration said to carry the warning rather than be surprised by it.

## Files

| file | what |
|---|---|
| `flight-receipt.json` | identity, plan, serving and monitor summary, windows, token distribution per call, cost, throughput, evidence provenance, saturation, the re-aggregation refusal, and every artifact's SHA-256 |
| `score-read.json` | the `core.scoring_batch --include-per-sample` verified read, aggregates and 44 per-sample rows per metric; per-sample mask arrays dropped for size, the unreduced file's SHA-256 recorded inside |
| `batch-summary.json` | the batch record: one complete-manifest job, no sharding |
| `jobs.jsonl` | the one job that was run |

Sealed run artifacts (plan, outputs, trace, manifest, scores, per-window rows, session-attach receipt)
live under `$SPEECHRL_DATA_DIR/runs/SAEA-E21-KC-E1-BRIEF-44-V1/` and never enter Git.
