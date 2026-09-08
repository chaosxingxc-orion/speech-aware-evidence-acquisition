# KU-E1fc — the flight of `E21-ku-e1fc-placebo-repair`, the form twin, all 44 calls

The second half of `docs/readiness/2026-09-07-e21-kc-e1f-brief-repair-pass-v1-preregistration.md`
§8 item 5: the token-matched placebo twin of the second-pass entity-repair pair, under the same
owner GO of 2026-09-07 (umbrella owner record Decision 7) that authorized the treatment cell.
Exposure row `SAEA-E21-KU-E1FC-PLACEBO-REPAIR-44-V1`. Study commit **`5988e7c2`**, clean tree,
`study_repo_dirt` empty in the sealed manifest. Attempt **`attempt-20260908T072231Z-ec8a5b`**, state
`FINALIZED`, manifest `COMPLETED`.

**This receipt reports; it decides nothing.** The content effect KC-E1f − KU-E1fc, the comparator
contrast and the decision rule of §5 are the verdict's own act, under its own row. Nothing here is
paired and no interval is computed.

The treatment cell's own receipt is the sibling directory `../flight/`.

---

## The cell that flew

One charged contact per fixed 90-second window, 1,593 windows over the 44 `earnings21-original`
discovery calls, arm `fixed-legal-context`, policy `obs-repair-loop`, evidence source
**`conec-class-lists-placebo-token-matched`** at `brief_max_entries_per_class` 12 through the
hash-pinned pad plan `configs/knowledge/e21-brief-placebo-v2/pad-plan-v1.json`
(sha256 `e3b494d0…d49c`) that KU-E1c already flew, response post-processor
`e21-entity-repair-substitutions-v1` at `max_span_tokens` 4 / `min_anchor_ratio` 0.60 /
`max_substituted_fraction` 0.10. Config hash `5d127545…`, protocol hash `669d9b96…`, split identity
`fcc1b0bc…d69e`. Temperature 0, seed 20260803, `max_tokens` 1024, `obs_batch_slices` 8.

Against the treatment cell's `05777ca3…` / `43b60556…`, **both hashes differ and they must**: the
one factor is the brief's content, and the composed config carries it. The plan builder asserted
that difference before takeoff rather than discovering it in the trace.

**Pass 1 was read, not flown, and it is the SAME pass 1 the arm edited.** Every window's request
carried that window's own sealed hypothesis from `SAEA-E21-FULL44-DIRECT-BASELINE-V2` (attempt
`attempt-20260904T233816Z-bcd338`) through the content-free binding
`docs/receipts/e21-predecessor-full44-direct-baseline-v2.json` (sha256 `26f1d9cc…a72a`), re-verified
in its fixed refusal order before a single window became readable. Both cells therefore edit the
identical sealed transcript, and no difference between them can be a pass-1 difference.

**Geometry.** `q4km-e21-buf90-mmproj-gpu-04ccc72a-np4`: `-c 36864 -np 4`, 4 slots of 9,216 tokens,
bf16 mmproj resident, raw audio, no feature cache — **the same geometry the treatment cell flew**,
because flying the twin at any other slot count would stop it being a twin. The prompt fit
(`SAEA-E21-KC-E1F-PROMPT-FIT-V1`) certified this pick for **both** cells by measuring all 1,593
windows of each.

## The one factor, on the wire

Read directly off the two cells' sealed `MODEL_REQUEST` records for the same window
(`4320211#w0001`), request `req-0001-i0000` in each:

| payload key | identical across the two cells? |
|---|---|
| `task_instruction` (the fragment's instruction **plus** the frozen `e21-entity-repair-frame-v1` filled with that window's sealed pass-1 hypothesis) | **yes** |
| `audio_seconds`, `sample_rate_hz`, `speech_ref`, `sample_id`, `request_id`, `history`, `decoding_params`, `carrier_lock_key` | **yes** |
| `media_relpath` | no — `derived/obs-slices/<run id>/…`, one per run id, **and the two files are byte-identical**: sha256 `6bd12cba…a029`, 2,880,044 bytes on both sides |
| `supplied_evidence`, `evidence_provenance` | **no — this is the factor** |

The placebo's roster block carries the same header, the same class labels and the same entry count
as the arm's, with every entity string replaced by position-chosen neutral placeholders
(`item entry term unit element field label value record part …`) where the arm carries
`Maureen Mulholland (Senior Vice President, General Counsel and Secretary) [normalized: maureen
mulholland]; …`. Same shape, no names.

## The token match — exactly +7 on 1,593 of 1,593 windows

The prompt fit asserted, before either cell flew, that the twin's rendered text is exactly **+7**
tokens on every window: the constant `[evidence <id>] ` header residual KU-E1c already documented,
a property of the evidence-id names and not of the content. **The flight re-measured it on the
requests that actually flew** — each cell's own `COST` record joined to its `OBS` record through the
shared request id, so the count is the flight server's own on the flight tokenizer, including the
identical speech tokens of the identical audio.

| | value |
|---|---:|
| windows matched to the sibling cell | **1,593 of 1,593** |
| delta min / median / max | **+7 / +7 / +7** |
| distinct values in the whole distribution | **1** (`{+7: 1593}`) |
| matches the prompt fit | **yes** |

Total prompt tokens 3,561,846 against the arm's 3,550,695 — a difference of 11,151, which is
1,593 × 7 exactly.

## The delivery-integrity guard — PASS on 1,593 of 1,593, before any score was read

§5's construction guard, run from the sealed trace against the sealed binding **before finalize and
before any score file was opened**: every window's delivered raw text carries the identical
whitespace-token count as its predecessor; a refused window delivers the predecessor byte for byte
and records zero applied substitutions; a delivered window is byte-identical at every token position
the repair did not substitute, so its differing positions equal that window's own
`obs_repair_substituted_tokens`. **Zero violations**, 2,154 differing token positions in total.

The refusal branch is checked first, the ordering the treatment cell's own run established (a
`substituted_fraction_above_ceiling` refusal carries a would-be count while applying nothing). Three
such refusals occurred here and all three delivered the predecessor byte for byte.

## The repair ledger, published whatever the outcome

| | windows | KC-E1f |
|---|---:|---:|
| windows | **1,593** | 1,593 |
| changed (>= 1 accepted substitution) | **1,023** | 1,064 |
| delivered unchanged without a refusal | 498 | 447 |
| refused | **72** | 82 |

| refusal reason | count | KC-E1f |
|---|---:|---:|
| `anchor_ratio_below_floor` | 67 | 75 |
| `empty_response` | 2 | 3 |
| `substituted_fraction_above_ceiling` | 3 | 4 |
| `empty_predecessor` | 0 | 0 |

| rejected opcode | count | KC-E1f |
|---|---:|---:|
| `unbalanced_replace` | 658 | 654 |
| `deletion` | 337 | 331 |
| `insertion` | 125 | 104 |
| `oversized_replace` | 3 | 4 |

**Accepted substitutions 2,125 over 2,154 substituted tokens** (the arm: 2,427 over 2,545); a further
6 tokens were the would-be count of the three ceiling refusals and were never applied. Anchor ratio
min / median / max **0.000 / 0.992 / 1.000** against the 0.60 floor.

**The placebo edits.** It is not a do-nothing arm: it proposed and had accepted 2,125 substitutions
on 1,023 windows. What those edits were worth is the verdict's question, not this receipt's.

## What the delivery guarantee bought, in operations

| | KU-E1fc | sealed comparator | delta | KC-E1f delta |
|---|---:|---:|---:|---:|
| substitutions | 13,105 | 13,098 | **+7** | −162 |
| deletions | 5,699 | 5,701 | −2 | −1 |
| insertions | 10,702 | 10,700 | +2 | +1 |
| reference words | 359,765 | 359,765 | 0 | 0 |

Raw-space delivery is substitution-only by construction; these are **normalized** counts, so the ±2
deletion/insertion moves are normalization deltas of substituted spans until the verdict attributes
them span by span (§5.1). A move that cannot be attributed to a substituted span is a defect report,
not a result.

## The four metrics, all 44 calls

Scored **once** over the complete manifest, never sharded, by `core.scoring_batch` with
`--include-per-sample` and one job (`batch-summary.json`: 1 job, 1 succeeded, 0 failed,
`no dataset sharding and no averaging of shard-level official metrics`, 1,543.31 s, empty stderr).
The batch read is `verified: true` and its aggregates are **byte-identical** to the ones finalize
sealed, on all four metrics.

| metric | KU-E1fc, all 44 | sealed comparator | KC-E1f |
|---|---:|---:|---:|
| corpus WER (`asr-wer-whisper`, Whisper normalizer) | **8.201 %** | 8.2 % | 8.154 % |
| ConEC-mirror **PERSON** entity WER | **22.592 %** — S 576 / D 83 over 2,917 | 22.489 % | 18.752 % |
| ConEC-mirror ORG entity WER | 17.052 % — S 674 / D 70 over 4,363 | 17.213 % | 16.502 % |
| numeric-value accuracy | **90.713 %** — 8,830 of 9,734, 913 spurious | 90.73 % | 90.744 % |
| semantic high-impact error rate | **0.0278 %** — 56 HIGH insertions, 100 HIGH reference words | 0.0278 % | 0.0275 % |

Every ConEC class with its reference-word count is in `flight-receipt.json`
(`scores_aggregates.conec-entity-wer-official.by_entity_type`) and in `score-read.json`; the
per-sample rows (44 per metric) are in `score-read.json`. Insertions are not attributed to entity
classes, by the mirror's own definition. **These are this cell's own numbers against published ones,
not a contrast**: no interval, no pairing and no verdict is computed here.

PERSON deletions read **83**, the comparator's own figure exactly, which is what §9 item 1 predicts
for a mechanism that cannot repair a deletion. The arm's 80 is the number that needs attributing.

## Throughput and cost

1,593 windows in 6,350 s of run wall (105.83 min): **15.052 windows per minute**, realized realtime
factor **33.68×**, latency summed over 4 slots 38,187.34 s, CPU 358.19 s, peak VRAM 22,728 MiB, gate
setup 20.29 s. Against the arm's 104.15 min and 15.295 windows per minute at the same geometry, on
the same roster, in the same session.

Tokens: prompt **3,561,846** vs the arm's 3,550,695 (+11,151 = 1,593 × 7), the comparator's 1,935,965
and KC-E1's 2,907,274; completion **439,049** vs the arm's 434,219 and the comparator's 439,532. The
worst realized request was 3,511 tokens against the 9,216-token slot, a margin factor of **2.625** —
the prompt fit projected 3,498 and 2.635 for this cell before it flew.

**GPU hours: 1.1656** (`cost.gpu_seconds` 4,196.27, the nvidia-smi busy-time sampler) against the
registered **1.2**, so the ceiling held, as it did for the arm at 1.1093. Read the conservative way,
by the session monitor's wall clock over the contact window, the pass is 1.764 h. Both conventions
are published; neither is blended.

## Two windows saturated the decode cap, and neither cost a span

`saturated_slice_count` is **2** (call `4346923`); `skipped_slice_count` is 0. A saturated pass-2
decode reaches `core.repair_alignment` as the empty string, is refused as `empty_response`, and
**delivers pass 1** — and the `empty_response` count in the ledger is exactly 2.

## Serving — attached, never started, never stopped

`saea-driver run --session-receipt` reached the coordinator's resident session
`e21-np4-c36864-20260908` (pid 148748, port 8080) through `core.session.attach_session`.
`scripts/run_arm_sequence.sh` was deliberately not used, and no smoke step ran.

Monitor summary over this attempt's own contact window (1788852173–1788858523):

| wall | active | parked | requests | mean / peak power | mean util | host free min | VM avail min |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 6,334.10 s | 5,380.27 s (84.9 %) | 953.83 s (15.1 %) | 1,552 | 76.38 W / 107.06 W | 63.55 % | 13.66 GB | 29.40 GB |

`requests_delta` is a lower bound at the 10-second sampling interval; the charged contact count is
1,593, from the manifest and the trace. **The host-memory floor held, but by the smallest margin
recorded so far**: the Windows side reached **13.66 GB** free at 1788857539, against the 12 GB floor
the 2026-09-07 incident produced. The arm's own minimum was 17.12 GB. Worth watching before the next
resident-session flight; nothing was throttled or lost here.

## One pre-flight refusal, recorded rather than quietly re-run

The first launch was refused by the exposure gate **before any model contact**: the row had been
registered with `consumed = yes`, copied from the sibling's CLOSED row rather than its registration,
and `contracts.gate_exposure` requires `no`. `contracts.gate.assert_model_touch_allowed` closes
before `core.model.lifecycle` opens an attempt, so no attempt record exists under the run id, the
flight lock was never taken, the resident session was never contacted, and the manifest the driver
wrote for `attempt-20260908T071857Z-7d4f6d` is `ABORTED` with `calls_used` 0 and `audio_seconds_used`
0. The row was corrected and committed (`5988e7c2`) before the real launch. **It is a registration
defect, not a flight failure, and it does not spend the one permitted recovery re-registration**,
which is reserved for a CUDA fault in flight and remains **UNSPENT**.

## Carried rather than discovered

`fixed-legal-context` predates the 2026-08-15 legality doctrine's either-field rule, so this attempt
records provenance tier `UNVERIFIED` with a GRANDFATHERED declaration warning in the manifest's
`legality` block — the same property of the arm that §7.2 named in advance.

## What is still owed, and to whom

* the **paired verdict** — the content effect KC-E1f − KU-E1fc, the comparator contrast, the §5
  decision rule, the call-clustered CI90 intervals, saves / harms / ties and the sign test;
* `scripts/e21_window_pairing_read.py` over both cells' sealed outputs, with both profiles added to
  its `SEALED_PROFILES` (§8 item 6), before any per-window decomposition;
* the §5.2 strata under both weightings, the E5 split halves reported apart, and the span-by-span
  attribution of the normalized deletion/insertion deltas on both cells — all verdict work, on the
  per-sample rows committed here and in `../flight/`.

## Files

| file | what |
|---|---|
| `flight-receipt.json` | identity, plan, serving and monitor summary, the delivery-integrity result, the repair ledger, anchor-ratio distribution, the per-window token match against the sibling cell, substitutions per call, windows and token distributions, cost, throughput, saturation, the operation table, every scorer aggregate and every artifact's SHA-256 |
| `score-read.json` | the `core.scoring_batch --include-per-sample` verified read, aggregates and 44 per-sample rows per metric; per-sample mask arrays elided for size, the unreduced file's SHA-256 recorded inside |
| `batch-summary.json` | the batch record: one complete-manifest job, no sharding |
| `jobs.jsonl` | the one job that was run |

The receipt is written by the same `scripts/e21_kc_e1f_flight_receipt.py` the arm's was, now taking
the cell id and the sibling attempt as arguments. Its
`delivered_vs_comparator_operations` block keeps the v1 key name `kc_e1f` for the receipt's **own**
cell — deliberately not renamed, so the pair's two receipts stay comparable field for field.

Sealed run artifacts (plan, outputs, trace, manifest, scores, ledger row) live under
`$SPEECHRL_DATA_DIR/runs/SAEA-E21-KU-E1FC-PLACEBO-REPAIR-44-V1/` and never enter Git.
