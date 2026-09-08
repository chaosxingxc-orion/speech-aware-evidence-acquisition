# `SAEA-E21-FULL44-TAIL2S-V1` — the Earnings-21 arm of the cross-carrier silence-tail probe

The Earnings-21 cell of
`docs/readiness/2026-09-07-cross-carrier-silence-tail-v1-preregistration.md` §§1.4, 4.3 and 6.3:
the sealed full-44 direct baseline flown again, byte for byte, with one factor moved — the baseline
fragment's `obs_slice_tail_silence_seconds` 2.0, which appends exactly 32,000 zero samples at 16 kHz
to every buffered 90-second window after the cut and before the request.

**Verdict: NOT ADMITTED.** Corpus WER falls 8.1995 % → **7.2714 %**, a paired **−0.9281**
[−1.0514, −0.7949] call-clustered; §4.3 clauses 1 and 3 pass and clause 2 fails. The full reasoning
is `docs/readiness/2026-09-07-e21-full44-tail2s-v1-verdict.md`.

| | |
|---|---|
| study commit | `81f2b1e9` (registration) — both flights bind it, `study_repo_dirt` empty |
| smoke | `SAEA-E21-FULL44-TAIL2S-SMOKE-V1`, attempt `attempt-20260907T230846Z-e2f699`, 13 windows on one call, falsifier 13 of 13 |
| flight | `SAEA-E21-FULL44-TAIL2S-V1`, attempt `attempt-20260907T231248Z-00f13c`, 1,593 windows over 44 calls, falsifier **1,593 of 1,593** |
| comparator | `SAEA-E21-FULL44-DIRECT-BASELINE-V2`, attempt `attempt-20260904T233816Z-bcd338` |
| serving | attached to the coordinator's resident session `e21-np6-c36864-20260907b`; no server started, none stopped |
| cost | 1,593 calls of 1,750; 141,345.8527 metered speech seconds of 150,000; **0.9765 GPU-h of 1.2**; paid API spend 0 |

## Layout

| path | what |
|---|---|
| `smoke-1call/` | the §8 item 5 smoke: one call, 13 windows, its media falsifier and flight receipt. **Carries no metric.** |
| `flight-1593/` | the flight: media falsifier, flight receipt, window-level section, the verified score batch record |
| `verdict/result-summary.json` | the machine form of the verdict: identity gate, every interval, the per-call and per-stratum tables, the error structure, the §4.3 clause-by-clause decision and the §5 prediction check |
| `verdict/per-call-table.md` | all 44 calls with sector, sample rate, window count, reference words, both corpus-WER figures and both S/D/I triples |

## The three things this receipt exists to pin

1. **The media accounting closes on every flown row.** 1,593 of 1,593 emitted slice SHA-256s equal
   the committed `@ts2` entries, 1,593 of 1,593 `pre_sha256` values chain back to the sealed
   comparator's own cuts, and the delivered totals (144,531.852688 s, 4,625,089,378 bytes) are the
   committed supplement's own to the digit. Checked **before any score file was opened**.
2. **The identity gate passed before any contrast was computed.** The sealed comparator reproduced
   §1.4's published anchors from its own committed score receipts — corpus WER 8.19952, S/D/I
   13,098 / 5,701 / 10,700 over 359,765 reference words, ConEC overall 8.19952 and non-entity
   4.73038, numeric accuracy 90.73351, semantic high-impact 0.02780 — all to the digit.
3. **Scoring ran once over the complete manifest, never sharded**, and the verified
   `core.scoring_batch` read reproduced all seven scorers' aggregates byte-identically against what
   finalize sealed.

## Reproduction

```bash
# the media falsifier (zero contacts)
python scripts/e21_tail2s_falsifier.py <attempt-dir> SAEA-E21-FULL44-TAIL2S-V1 1593 falsifier.json

# the two per-window decompositions, side by side (zero contacts)
python scripts/build_e21_tail2s_verdict.py --window-rows-only comparator ...
python scripts/build_e21_tail2s_verdict.py --window-rows-only cell ...

# the paired read (zero contacts)
python scripts/build_e21_tail2s_verdict.py \
  --score-read <verified score read> --attempt-dir <attempt-dir> \
  --comparator-window-rows <cache> --cell-window-rows <cache> --out result-summary.json

# the flight receipt (zero contacts)
python scripts/e21_tail2s_flight_receipt.py <attempt-dir> <run-id> <t0> <t1> falsifier.json out.json
```

Every one of these reads sealed artifacts only: no model, GPU, tool, embedding or network contact,
and no Earnings-22 surface is named, loaded or scored.
