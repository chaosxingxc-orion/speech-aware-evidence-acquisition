# KC-E1f — the flight of `E21-kc-e1f-brief-repair`, all 44 calls

The flight half of `docs/readiness/2026-09-07-e21-kc-e1f-brief-repair-pass-v1-preregistration.md`
§8 item 5, for the treatment cell of the second-pass entity-repair pair. Exposure row
`SAEA-E21-KC-E1F-REPAIR-44-V1`; owner GO 2026-09-07 (umbrella owner record Decision 7). Study commit
**`f0926699`**, clean tree, `study_repo_dirt` empty in the sealed manifest. Attempt
**`attempt-20260908T040832Z-ecda9c`**, state `FINALIZED`, manifest `COMPLETED`, and it is the
**FIRST AND ONLY** attempt — the one permitted recovery re-registration is unspent.

**This receipt reports; it decides nothing.** No pairing, no interval, no verdict: the comparator
contrast, the form twin `KU-E1fc` and the decision rule of §5 are separate acts under their own rows.

---

## The cell that flew

One charged contact per fixed 90-second window, 1,593 windows over the 44 `earnings21-original`
discovery calls, arm `fixed-legal-context`, policy `obs-repair-loop`, evidence source
`conec-class-lists` at `brief_max_entries_per_class` 12, response post-processor
`e21-entity-repair-substitutions-v1` at `max_span_tokens` 4 / `min_anchor_ratio` 0.60 /
`max_substituted_fraction` 0.10. Config hash `05777ca3…`, protocol hash `43b60556…`, split identity
`fcc1b0bc…d69e`. Temperature 0, seed 20260803, `max_tokens` 1024, `obs_batch_slices` 8.

**Pass 1 was read, not flown.** Every window's request carried that window's own sealed hypothesis
from `SAEA-E21-FULL44-DIRECT-BASELINE-V2` (attempt `attempt-20260904T233816Z-bcd338`) through the
content-free binding `docs/receipts/e21-predecessor-full44-direct-baseline-v2.json`
(sha256 `26f1d9cc…a72a`), re-verified in its fixed refusal order before a single window became
readable.

**Geometry.** `q4km-e21-buf90-mmproj-gpu-04ccc72a-np4`: `-c 36864 -np 4`, 4 slots of 9,216 tokens,
bf16 mmproj resident, raw audio, no feature cache. The np6 fragment the cell was scoped to fails this
family's `slot_tokens >= 2 × worst_required` rule for this cell at 1.764; §7.1's own pre-fixed lever
order took lever 1 (widen the slot, changing no request byte), and the prompt fit
(`SAEA-E21-KC-E1F-PROMPT-FIT-V1`) certified it by measuring all 1,593 windows of both cells.

## Serving — attached, never started, never stopped

`saea-driver run --session-receipt` reached the coordinator's resident session
`e21-np4-c36864-20260908` (pid 148748, port 8080) through `core.session.attach_session`.
`scripts/run_arm_sequence.sh` was deliberately not used.

Monitor summary over this attempt's own contact window (1788840537–1788846786):

| wall | active | parked | requests | mean / peak power | mean util | host free min | VM avail min |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 6,231.93 s | 5,394.77 s (86.6 %) | 837.16 s (13.4 %) | 1,531 | 78.69 W / 102.74 W | 63.17 % | 17.12 GB | 30.44 GB |

`requests_delta` is a lower bound at the 10-second sampling interval; the charged contact count is
1,593, from the manifest and the trace. The host-memory floor held: the Windows side never fell below
**17.12 GB** free, against the 12 GB floor the 2026-09-07 incident produced.

## The delivery-integrity guard — PASS on 1,593 of 1,593, before any score was read

§5's construction guard, run from the sealed trace against the sealed binding **before finalize**:
every window's delivered raw text carries the identical whitespace-token count as its predecessor; a
refused window delivers the predecessor byte for byte and records zero applied substitutions; a
delivered window is byte-identical at every token position the repair did not substitute, so its
differing positions equal that window's own `obs_repair_substituted_tokens`. **Zero violations.**

**One ordering defect, in the checker and not the cell.** The first pass flagged 4 windows
(`4365948#w0004`, `4366522#w0016`, `4366893#w0027`, `4387383#w0021`) as "0 differing positions
against 36 / 23 / 2 / 30 recorded substituted tokens". All four are
`substituted_fraction_above_ceiling` **refusals**: `core.repair_alignment._refuse` is handed the
would-be `substituted_tokens` on that path, so a refusal can carry a non-zero count while applying
nothing, and all four delivered the predecessor byte for byte. The refusal branch now comes first in
`scripts/e21_kc_e1f_flight_receipt.py`, which is where the check lives. Recorded rather than quietly
re-run.

## The repair ledger, published whatever the outcome

| | windows |
|---|---:|
| windows | **1,593** |
| changed (>= 1 accepted substitution) | **1,064** |
| delivered unchanged without a refusal | 447 |
| refused | **82** |

| refusal reason | count |
|---|---:|
| `anchor_ratio_below_floor` | 75 |
| `empty_response` | 3 |
| `substituted_fraction_above_ceiling` | 4 |
| `empty_predecessor` | 0 |

| rejected opcode | count |
|---|---:|
| `unbalanced_replace` | 654 |
| `deletion` | 331 |
| `insertion` | 104 |
| `oversized_replace` | 4 |

**Accepted substitutions 2,427 over 2,545 substituted tokens**; a further 91 tokens were the would-be
count of the four ceiling refusals and were never applied. Anchor ratio min / median / max
**0.000 / 0.992 / 1.000** against the 0.60 floor.

## What the delivery guarantee bought, in operations

| | KC-E1f | sealed comparator | delta |
|---|---:|---:|---:|
| substitutions | 12,936 | 13,098 | **−162** |
| deletions | 5,700 | 5,701 | −1 |
| insertions | 10,701 | 10,700 | +1 |
| reference words | 359,765 | 359,765 | 0 |

Raw-space delivery is substitution-only by construction; these are **normalized** counts, so the ±1
deletion/insertion moves are normalization deltas of substituted spans until the verdict attributes
them span by span (§5.1). What KC-E1 could not do, this cell did: KC-E1 bought its names with 2,242
extra non-entity deletions, and here the deletion column does not move.

## The four metrics, all 44 calls

Scored **once** over the complete manifest, never sharded, by `core.scoring_batch` with
`--include-per-sample` and one job (`batch-summary.json`: 1 job, 1 succeeded, 0 failed,
`no dataset sharding and no averaging of shard-level official metrics`, 1,410.71 s, empty stderr).
The batch read is `verified: true` and its aggregates are **byte-identical** to the ones finalize
sealed, on all four metrics.

| metric | KC-E1f, all 44 | sealed comparator | KC-E1 |
|---|---:|---:|---:|
| corpus WER (`asr-wer-whisper`, Whisper normalizer) | **8.154 %** | 8.2 % | 8.736 % |
| ConEC-mirror **PERSON** entity WER | **18.752 %** — S 467 / D 80 over 2,917 | 22.489 % | 18.341 % |
| ConEC-mirror ORG entity WER | 16.502 % — S 650 / D 70 over 4,363 | 17.213 % | 17.992 % |
| numeric-value accuracy | **90.744 %** — 8,833 of 9,734, 913 spurious | 90.73 % | 90.189 % |
| semantic high-impact error rate | **0.0275 %** — 56 HIGH insertions, 99 HIGH reference words | 0.0278 % | 0.0334 % |

Every ConEC class with its reference-word count is in `flight-receipt.json`
(`scores_aggregates.conec-entity-wer-official.by_entity_type`) and in `score-read.json`; the
per-sample rows (44 per metric) are in `score-read.json`. Insertions are not attributed to entity
classes, by the mirror's own definition. **These are this cell's own numbers against published ones,
not a contrast**: no interval, no pairing and no verdict is computed here.

One number to read with §9 item 1 open beside it: PERSON deletions read **80** against the
comparator's 83, and the mechanism cannot repair a deletion. The three are a normalization effect of
substituted spans on the entity alignment, and the verdict must attribute them rather than treat them
as recovered words.

## Throughput and cost

1,593 windows in 6,249 s of run wall (104.15 min): **15.295 windows per minute**, realized realtime
factor **35.40×**, latency summed over 4 slots 36,424.38 s, CPU 335.76 s, peak VRAM 22,728 MiB, gate
setup 17.95 s. Finalize (verify, score, upload, settle) took a further ~2,100 s.

Tokens: prompt **3,550,695** vs the comparator's 1,935,965 (+83.4 %) and KC-E1's 2,907,274 (+22.1 %);
completion **434,219** vs 439,532 (−1.2 %) and 423,115 (+2.6 %). The pass-1 hypothesis rides in every
prefill, and the answer is a re-emission of a text of known length.

**GPU hours: 1.1093** (`cost.gpu_seconds` 3,993.32, the nvidia-smi busy-time sampler) against the
registered **1.2**, so the ceiling held — this is stated as it was registered, in advance: the 1.2 was
derived from KC-E1's 0.9948 realized at SIX slots and this cell flew at FOUR. Read the conservative
way instead, by the session monitor's wall clock over the contact window, the pass is 1.731 h. Both
conventions are published; neither is blended. Windows per minute against KC-E1's 16.244 carries the
slot change as well as the protocol one.

## Three windows saturated the decode cap, and none of them cost a span

`saturated_slice_count` is **3** (calls `4365948` and `4383161`); `skipped_slice_count` is 0. This is
where the mechanism differs from KC-E1 by construction: a saturated pass-2 decode reaches
`core.repair_alignment` as the empty string, is refused as `empty_response`, and **delivers pass 1**.
KC-E1's two saturated windows contributed the empty string to its stitched hypothesis; these three
contributed the comparator's own transcript. The `empty_response` count in the ledger is exactly 3.

## Carried rather than discovered

`fixed-legal-context` predates the 2026-08-15 legality doctrine's either-field rule, so this attempt
records provenance tier `UNVERIFIED` with a GRANDFATHERED declaration warning in the manifest's
`legality` block. A property of the arm, named in the preregistration's §7.2 so the flight would not
be surprised by it.

## What is still owed, and to whom

* the **form twin** `KU-E1fc` and the paired verdict — later agents, their own rows;
* `scripts/e21_window_pairing_read.py` over this cell's sealed outputs, with this cell's profile added
  to its `SEALED_PROFILES` (§8 item 6), before any per-window decomposition;
* the §5.2 strata, the E5 split halves reported apart, and the span-by-span attribution of the ±1
  normalized deletion/insertion deltas — all verdict work, on the per-sample rows committed here.

## Files

| file | what |
|---|---|
| `flight-receipt.json` | identity, plan, serving and monitor summary, the delivery-integrity result, the repair ledger, anchor-ratio distribution, substitutions per call, windows and token distributions, cost, throughput, saturation, the operation table, every scorer aggregate and every artifact's SHA-256 |
| `score-read.json` | the `core.scoring_batch --include-per-sample` verified read, aggregates and 44 per-sample rows per metric; per-sample mask arrays elided for size, the unreduced file's SHA-256 recorded inside |
| `batch-summary.json` | the batch record: one complete-manifest job, no sharding |
| `jobs.jsonl` | the one job that was run |

Sealed run artifacts (plan, outputs, trace, manifest, scores, ledger row) live under
`$SPEECHRL_DATA_DIR/runs/SAEA-E21-KC-E1F-REPAIR-44-V1/` and never enter Git.
