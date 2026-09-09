# `SAEA-SLURP-DEV1000-CLOSED-LIST-TAIL2S-V1` — the SLURP arm of the cross-carrier silence-tail probe

The SLURP cell of
`docs/readiness/2026-09-07-cross-carrier-silence-tail-v1-preregistration.md` §§1.2, 4.1 and 6.1: the
sealed DEV-1000 closed-list direct baseline flown again, byte for byte, with one factor moved — the
media, exactly 2.0 s of digital silence appended to every one of the 1,000 sealed devel FLACs, and
the packet root that media forces (the legacy feature-cache key is FNV-1a over the original media
bytes, so an `@ts2` file is a cache miss by construction).

**Verdict: NOT ADMITTED.** Intent accuracy rises 73.10 % → **74.40 %**, a paired **+1.30 pp**
[+0.19, +2.43] speaker-clustered, and SLU-F1 35.80 → **37.83** — every headline number moves up and
§4.1's three clauses all fail anyway. The full reasoning is
`docs/readiness/2026-09-09-slurp-silence-tail-v1-verdict.md`.

| | |
|---|---|
| study commit | `53d31f59` (registration) — both flights bind it, `study_repo_dirt` empty |
| smoke | `SAEA-SLURP-DEV1000-CLOSED-LIST-TAIL2S-SMOKE-V1`, attempt `attempt-20260909T034421Z-f00629`, 4 rows, falsifier 4 of 4 |
| flight | `SAEA-SLURP-DEV1000-CLOSED-LIST-TAIL2S-V1`, attempt `attempt-20260909T035340Z-95296f`, 1,000 rows, falsifier **1,000 of 1,000** |
| comparator | `SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1`, attempt `attempt-20260905T060424Z-2c5596` |
| paper-facing scorer | `slurp-slu-official-projected-v2`; secondary `slurp-slu-f1-normalized-v1` |
| serving | attached to the coordinator's resident session `slurp-np8-ts2-c65536-20260909`; no server started, none stopped |
| cost | 1,000 calls of 1,050; 4,884.7937 metered speech seconds of 5,000; **0.0687 GPU-h of 0.30**; paid API spend 0 |

## Layout

| path | what |
|---|---|
| `read.py` | the archived copy of the single registered read: the score batch, the identity gate, both interval families, both weightings, the secondary scorer and the §4.1 decision. Scoring-side only, zero contacts. It resolves the checkout and the data root from its own constants, so this copy reproduces the bytes but not the invocation |
| `falsifier.py` | the archived copy of the §4.4 media falsifier, run on both populations **before any score file was opened** |
| `build_result_summary.py` | the assembler of `verdict/result-summary.json` and `verdict/per-scenario-table.md`; reads nothing but `verdict/read.json` |
| `smoke-4/` | the §8 item 5 smoke: its media falsifier, flight receipt and monitor window. **Carries no metric** |
| `flight-1000/` | the flight: the 1,000-row media falsifier, the flight receipt, the monitor summary over the contact window |
| `verdict/read.json` | the full read — every aggregate, every interval, the per-scenario tables, both weightings, the secondary |
| `verdict/result-summary.json` | the machine form of the verdict: identity gate, falsifier, every interval, the §4.1 clause-by-clause decision and the §5 prediction check |
| `verdict/per-scenario-table.md` | all 18 gold scenarios with intent and SLU-F1 deltas |
| `verdict/batch-summary.json` | the verified `core.scoring_batch` record: one job per manifest, `include_per_sample`, never sharded |

## The four things this receipt exists to pin

1. **The media accounting closes on every flown row.** 1,000 of 1,000 delivered media SHA-256s and
   byte counts equal the committed `@ts2` D1 supplement's entries and the frozen runtime view's own
   records; 1,000 of 1,000 delivered durations equal the sealed comparator's plus exactly 2.0 s (and
   exactly 32,000 samples at 16 kHz); 1,000 of 1,000 packets equal the promoted `@ts2` packets by
   SHA-256 from the pinned promotion receipt. Zero disagreeing rows, zero missing, zero extra.
   Checked **before any score file was opened**.
2. **The wire moved by exactly the tail and by nothing else.** Prompt tokens 2,216,161 against the
   comparator's 2,190,161 — **+26 on every one of the 1,000 rows**, no other value in the histogram
   and no residue. 26 tokens is 2.0 s at this encoder's block rate, and it is the figure Earnings-21
   measured independently on 1,593 windows.
3. **The identity gate passed before any contrast was computed.** The sealed comparator reproduced
   §1.2's nine published anchors from its own sealed bytes to the digit — scenario 82.60, action
   74.60, intent 73.10, entities-strict 21.91, word-F1 33.69, char-F1 38.20, SLU-F1 35.80, unparsed
   3, and the port-vs-official identity check at 0.0 absolute difference.
4. **The margin this verdict applied is IMPORTED, not measured.** SLURP has no same-request null.
   §4.1's ±0.60 pp is the Earnings-22 null's half-width on the same scale, and measuring this
   carrier's own null is the named blocking next cell.

## Two things this receipt records rather than tidies away

* **The smoke's monitor window carries zero samples.** Its contact window was 4.08 s and fell
  entirely between two 10-second monitor samples. The file is kept with `sample_count: 0` rather
  than widened to a window that would have shown a parked card.
* **Speaker clusters and scenario strata cannot be crossed on this carrier.** A SLURP speaker records
  across scenarios, so no speaker cluster sits inside one gold-scenario stratum and the two
  resampling rules cannot be combined. Both families are therefore reported side by side, the
  speaker-clustered one read as honest — and on this cell they reach the same verdict on all three
  §4.1 clauses, so nothing turns on the choice.
