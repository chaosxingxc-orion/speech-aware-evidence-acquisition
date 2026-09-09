# The KC-E1f replication flight — the same 44 calls, flown a second time

The flight half of the replication obligation section 3 of
`docs/readiness/2026-09-08-e21-kc-e1f-repair-pass-v2-redecision.md` fixed **before** that verdict
was known. Exposure row `SAEA-E21-KC-E1F-REPAIR-44-REPLICATE-V1`, registered and committed before
the first contact. Study commit **`82903e70`**, clean tree, `study_repo_dirt` empty in the sealed
manifest. Attempt **`attempt-20260908T232501Z-36792e`**, state `FINALIZED`, manifest `COMPLETED`,
MLflow run `eedc08d823d34fd8923e34ee8a5986b9`, and it is the **first and only attempt that reached a
contact** — the one permitted recovery re-registration is unspent.

**This receipt reports; the verdict decides.** The pairing, the intervals and the REPLICATED /
NOT REPLICATED line are `verdict/` and
`docs/readiness/2026-09-08-e21-kc-e1f-replication-v1-verdict.md`.

---

## Identical configuration, proved by hash before the first contact

The point of a replicate is that nothing moved, so this is checked first and it is checked against
the sealed first pass rather than asserted:

| | first pass `SAEA-E21-KC-E1F-REPAIR-44-V1` | this replicate |
|---|---|---|
| composed config hash | `05777ca3a3abdc75cd105021fe2104a639440d0ffd4ca2654ad18e50123b3e5f` | **identical** |
| protocol hash | `43b60556bd739192869ac1666612e027c6c1214de242e26ddf5cb0f00f6bd630` | **identical** |
| split identity hash | `fcc1b0bc…d69e` | **identical** |
| fragments | `q4km-e21-buf90-mmproj-gpu-04ccc72a-np4` / `earnings21-discovery-conec-names` / `e21-kc-e1f-brief-repair` / `e21-kc-e1f-repair-44-v1` | **the same four** |
| `obs_prefetch_depth` | absent | **absent** |
| **prompt tokens, total** | **3,550,695** | **3,550,695 — equal to the digit** |
| metered speech seconds | 141,345.8526875 | 141,345.8526875 |
| charged contacts | 1,593 | 1,593 |
| completion tokens, total | 434,219 | 437,350 (+0.72 %) |

**The request side is provably unchanged and only the completions moved.** The encoder saw the same
number of tokens to the digit over 1,593 windows, on the same audio, with the same brief and the
same sealed pass-1 hypothesis riding in every prefill — so nothing but decode-time batch composition
separates the two passes.

**The plain driver path was flown, deliberately.** `core.driver run` with the `obs-repair-loop`
policy and no `obs_prefetch_depth` key. The cross-call dispatcher's own admission entry reads
NEUTRAL and would license depth 1 for an Earnings-21 cell at this geometry, and the ported openJiuwen
graph landed on master after the first pass — a replicate may use neither, because a replicate that
changes the configuration it replicates is a different cell.

## The cell that flew

One charged contact per fixed 90-second window, 1,593 windows over the 44 `earnings21-original`
discovery calls, arm `fixed-legal-context`, policy `obs-repair-loop`, evidence source
`conec-class-lists` at `brief_max_entries_per_class` 12, response post-processor
`e21-entity-repair-substitutions-v1` at `max_span_tokens` 4 / `min_anchor_ratio` 0.60 /
`max_substituted_fraction` 0.10. Temperature 0, seed 20260803, `max_tokens` 1024, `obs_batch_slices` 8.

**Pass 1 was read, not flown.** Every window's request carried that window's own sealed hypothesis
from `SAEA-E21-FULL44-DIRECT-BASELINE-V2` (attempt `attempt-20260904T233816Z-bcd338`) through the
content-free binding `docs/receipts/e21-predecessor-full44-direct-baseline-v2.json`
(sha256 `26f1d9cc…a72a`), re-verified in its fixed refusal order before a single window became
readable. The replicate edits the same bytes the first pass edited, which is what makes the two
passes comparable at all.

**Geometry.** `q4km-e21-buf90-mmproj-gpu-04ccc72a-np4`: `-c 36864 -np 4`, 4 slots of 9,216 tokens,
bf16 mmproj resident, raw audio, no feature cache — the first pass's own geometry.

## Serving — attached, never started, never stopped

`saea-driver run --session-receipt` reached the coordinator's resident session
`e21-np4-c36864-20260908b` (pid 694, port 8080) through `core.session.attach_session`.
`scripts/run_arm_sequence.sh` was deliberately not used, and no server-log replay ran beside the
flight.

Monitor summary over this attempt's own run wall window (1788909919–1788916349), 584 samples:

| wall | active | parked | requests | mean / peak power | mean util | host free min | VM avail min |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 6,414.73 s | 5,439.25 s (84.8 %) | 975.48 s (15.2 %) | 1,545 | 73.64 W / 103.78 W | 62.46 % | 11.29 GB | 29.28 GB |

`requests_delta` is a lower bound at the 10-second sampling interval; the charged contact count is
1,593. **Host free memory bottomed at 11.29 GB**, below the 12 GB floor `serving_session.sh start`
refuses to start below — stated because it is the condition the 2026-09-07 host-memory incident
produced, and this flight ran under it for part of its window without being killed. It is reported,
not explained away; the VM's own working set peaked at 38.81 GB.

## The delivery-integrity guard — PASS on 1,593 of 1,593, before finalize and before any score

Section 5's construction guard, run from the sealed trace against the sealed binding **before
finalize**, with no score file in existence: every window's delivered raw text carries the identical
whitespace-token count as its predecessor; a refused window delivers the predecessor byte for byte
and records zero applied substitutions; a delivered window is byte-identical at every token position
the repair did not substitute. **Zero violations**, 2,543 differing token positions in total. The
refusal branch is checked first, as the first pass's own defect report required.

## The repair ledger, beside the first pass's

| | replicate | first pass |
|---|---:|---:|
| windows | **1,593** | 1,593 |
| changed (>= 1 accepted substitution) | **1,075** | 1,064 |
| delivered unchanged without a refusal | 431 | 447 |
| refused | **87** | 82 |
| — `anchor_ratio_below_floor` | 81 | 75 |
| — `empty_response` | 3 | 3 |
| — `substituted_fraction_above_ceiling` | 3 | 4 |
| — `empty_predecessor` | 0 | 0 |
| accepted substitutions | **2,446** | 2,427 |
| substituted tokens applied | **2,543** | 2,545 |
| would-be tokens never applied | 36 | 91 |
| rejected `unbalanced_replace` | 790 | 654 |
| rejected `deletion` | 281 | 331 |
| rejected `insertion` | 131 | 104 |
| rejected `oversized_replace` | 8 | 4 |

Anchor ratio min / median / max **0.000 / 0.992 / 1.000** against the 0.60 floor, against the first
pass's 0.000 / 0.992 / 1.000.

**The control plane's decision share is the stable half of this cell.** 1,075 windows changed against
1,064; 87 refused against 82; 2,543 tokens applied against 2,545. What moved between the two passes
is which opcodes the model proposed — 790 unbalanced replacements against 654 — not how many the
alignment rule let through.

## What the delivery guarantee bought, in operations

| | replicate | first pass | sealed comparator |
|---|---:|---:|---:|
| substitutions | **12,927** | 12,936 | 13,098 |
| deletions | **5,700** | 5,700 | 5,701 |
| insertions | **10,705** | 10,701 | 10,700 |
| reference words | 359,765 | 359,765 | 359,765 |

Raw-space delivery is substitution-only by construction; these are **normalized** counts, so the
`-1` deletion and `+5` insertion moves against the comparator are normalization deltas of substituted
spans. `attribution/kc-e1f-rep/attribution.json` attributes all six of them: `(I - D)` moved by
exactly `+6`, the attributed normalized-word delta is `+6`, **and no window moved without carrying a
substituted span** — 1,883 spans, 25 of them carrying a non-zero delta, 0 interior tokens moved.

## The five metrics, all 44 calls

Scored **once** over the complete manifest, never sharded, by `core.scoring_batch` with
`--include-per-sample` and one job (`batch-summary.json`: 1 job, 1 succeeded, 0 failed,
`no dataset sharding and no averaging of shard-level official metrics`, 1,518.22 s, empty stderr).
The batch read is `verified: true` and its aggregates are **byte-identical** to the ones finalize
sealed, field for field, with zero disagreements.

| metric | replicate | first pass | sealed comparator |
|---|---:|---:|---:|
| corpus WER (`asr-wer-whisper`, Whisper normalizer) | **8.153 %** | 8.154 % | 8.200 % |
| ConEC-mirror **PERSON** entity WER | **18.855 %** — S 470 / D 80 over 2,917 | 18.752 % | 22.489 % |
| ConEC-mirror ORG entity WER | **16.204 %** — S 637 / D 70 over 4,363 | 16.502 % | 17.213 % |
| ConEC non-entity WER | 4.729 % | 4.729 % | 4.730 % |
| numeric-value accuracy | **90.703 %** — 8,829 of 9,734, 914 spurious | 90.744 % | 90.734 % |
| semantic high-impact error rate | **0.0278 %** — 56 HIGH insertions, 100 HIGH reference words | 0.0275 % | 0.0278 % |

Every ConEC class with its reference-word count is in `flight-receipt.json`
(`scores_aggregates.conec-entity-wer-official.by_entity_type`) and in `score-read.json`; the
per-sample rows (44 per metric) are in `score-read.json`. **These are this cell's own numbers, not a
contrast**: no interval, no pairing and no verdict is computed here.

## Three windows saturated the decode cap, and none cost a span

`saturated_slice_count` is **3** (calls `4359732`, `4364366`, `4384198`); `skipped_slice_count` is 0.
The first pass also saturated exactly three, on two different calls. A saturated pass-2 decode
reaches `core.repair_alignment` as the empty string, is refused as `empty_response` and delivers pass
1 — the `empty_response` count is exactly 3 on both passes.

## Throughput and cost

1,593 windows in 6,430 s of run wall (107.17 min): **14.865 windows per minute** against the first
pass's 15.295, realized realtime factor **32.84×**, latency summed over 4 slots 39,719.30 s, CPU
377.29 s, peak VRAM 22,728 MiB, gate setup 22.83 s. Finalize took a further ~26 min and the verified
re-score 25 min.

**GPU hours: 1.1957** (`cost.gpu_seconds` 4,304.63, the nvidia-smi busy-time sampler) against the
**1.4** this run's own exposure row registered, and against the first pass's realized 1.1093 at the
same geometry — a **7.8 % spread on a request-identical pass**, which is twice the 3.6 % the
Earnings-21 own-null replicate measured and is the reason the row registered 1.4 rather than 1.2 in
advance. Read the conservative way, by the session monitor's wall clock over the contact window, the
pass is 1.786 h. Both conventions are published; neither is blended.

**Note on `cost.registered_gpu_hours` inside `flight-receipt.json`.** That field reads `1.2`: it is a
constant carried by `scripts/e21_kc_e1f_flight_receipt.py` from the FIRST pass's registration, and
this builder is reused unchanged rather than edited for one number. **This run registered 1.4**
(exposure row `SAEA-E21-KC-E1F-REPAIR-44-REPLICATE-V1`), and the realized 1.1957 is under both.

## One launcher defect, recorded rather than quietly repaired

`attempt-id.txt` was written by Windows Python and therefore carried CRLF. `$(cat …)` strips the
newline but not the carriage return, so every path this flight's launcher built ended in a bare CR,
and the driver wrote its artifacts into a directory whose **name** ends in CR and recorded that name
inside the manifest. `core.tracking.ledger_row` refuses a ledger cell containing a newline character
— a CR is one — so the first `finalize` failed on the `artifact location` cell.

**The repair moved no bytes and edited no manifest.** The directory was renamed to the canonical
attempt id and the CR-suffixed name left behind as a symlink to it, so the three absolute paths the
manifest already records still resolve to the same files and still hash to the same values
(`outputs`, `raw_trace` and `trace_manifest` were each re-hashed against the manifest's own recorded
sha256 and all three MATCH). `artifact location` is derived from the manifest path the operator
passes, resolved, so finalize was then handed the clean one and settled `FINALIZED`.

Two further consequences, both stated rather than hidden:

* **`<run_id>.plan.json` is placed, not produced.** `saea-driver run` does not copy the plan beside
  its own artifacts — only the `smoke` and `speech-native` paths do — so the plan the driver READ was
  copied there byte for byte (sha256 `af913c97…a5e9` on both sides) to give the receipt builder the
  shape the first pass's receipt was built from.
* **An earlier launch was refused by the gate and spent nothing.** The registration row first went in
  with `consumed` reading `yes`; `contracts.gate_exposure` refuses a consumed row, and it refused
  inside `assert_model_touch_allowed` — before an attempt was opened and before a socket was touched.
  Its directory `attempt-20260908T232245Z-599b59` holds an `ABORTED` manifest with no artifacts. **A
  refused launch is not an attempt**: no model, GPU or audio contact was made, and the recovery
  re-registration is untouched.

## Files

| file | what |
|---|---|
| `flight-receipt.json` | identity, plan, serving and monitor summary, the delivery-integrity result, the repair ledger, anchor-ratio distribution, substitutions per call, windows and token distributions, cost, throughput, saturation, the operation table, every scorer aggregate and every artifact's SHA-256 |
| `score-read.json` | the `core.scoring_batch --include-per-sample` verified read, aggregates and 44 per-sample rows per metric, with the finalize-agreement check; per-sample mask arrays elided for size, the unreduced file's SHA-256 recorded inside |
| `batch-summary.json` | the batch record: one complete-manifest job, no sharding |
| `jobs.jsonl` | the one job that was run |

Sealed run artifacts (plan, outputs, trace, manifest, scores, ledger row) live under
`$SPEECHRL_DATA_DIR/runs/SAEA-E21-KC-E1F-REPAIR-44-REPLICATE-V1/` and never enter Git.
