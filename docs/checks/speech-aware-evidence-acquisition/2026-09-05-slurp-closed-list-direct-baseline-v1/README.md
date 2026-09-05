# SLURP closed-list direct baseline — flight and read receipts (2026-09-05)

Run id `SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1`, attempt
`attempt-20260905T060424Z-2c5596`, profile `baseline-reproduction`, study commit at
takeoff `aae0a90d`. Verdict:
`docs/readiness/2026-09-05-slurp-closed-list-direct-baseline-v1-verdict.md`.
Preregistration:
`docs/readiness/2026-09-05-slurp-closed-list-direct-baseline-v1-preregistration.md`.

## Headline

| arm | scenario | action | intent (scen_act) | entities strict | Word-F1 | Char-F1 | SLU-F1 |
|---|---|---|---|---|---|---|---|
| **closed-list (this flight)** | 81.00 | 73.90 | **71.40** | 21.91 | 33.69 | 38.20 | **35.80** |
| DEV-1000 M0 (sealed) | 70.00 | 61.50 | 53.60 | 21.94 | 34.66 | 39.46 | 36.90 |
| DEV-1000 BLEND (locked) | 83.90 | 77.60 | 75.70 | 27.27 | 39.41 | 44.24 | 41.69 |

Intent +17.80 pp paired over M0 (CI90 [+15.70, +19.90]); SLU-F1 −1.10. Impossible
(scenario, action) pairs 32.20 % → 4.20 %. BLEND's +22.10 pp intent margin over M0 falls
to +4.30 pp over this arm, and to +2.60 pp (CI90 [−0.20, +5.60]) on the unexposed 500.

## Files

| file | what it is |
|---|---|
| `result-summary.json` | the machine-readable verdict: identity, the official table, the paired contrasts, the bracket table, cost |
| `read.py` | the single registered read. Scoring-side only, zero contacts. Scores all three output sets through the SAME registered `slurp-slu-official` scorer and computes the paired contrasts |
| `read.json` | that script's full output, including per-stratum rows and the bootstrap detail |
| `flight-receipt.json` | the flight's own six-stage `FlightReceipts` document (preflight, preprocess, serve, run_phases, seal, score) |
| `smoke-receipt.json` | the four-row smoke that proved the runtime first (`SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-SMOKE-V1`) |

Sealed bytes live under `$SPEECHRL_DATA_DIR/runs/SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1/attempt-20260905T060424Z-2c5596/`
and never enter Git: `…outputs.jsonl` (sha256 `34fda7fa…885b`),
`…run-manifest.json` (sha256 `f908ff4c…c94c`), `…scores.json`, `…trace.jsonl`.

## Reproduce the read

```bash
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD:$PWD/src
D=docs/checks/speech-aware-evidence-acquisition/2026-09-05-slurp-closed-list-direct-baseline-v1
python -B $D/read.py \
  --arm-outputs $SPEECHRL_DATA_DIR/runs/SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1/attempt-20260905T060424Z-2c5596/SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1.outputs.jsonl \
  --out $D/read.json
```

## Identity anchors that had to pass before any number was trusted

1. The wire instruction's first 5,747 characters hash to
   `cef527896e9beef5774305e01dc29192fc2d5ca89fba5143e82f0b91a7cb86b8` — the whole system
   message all 1,000 sealed DEV-1000 M0 `MODEL_REQUEST` records carried. Asserted in
   `scripts/flights/run_slurp_closed_list_cell.py` before takeoff, so a prompt rewrite
   could not have been mistaken for a prompt extension.
2. The recomputed split identity `8580d199…3c84` equals the value the sealed 2026-08-25
   M0 execution plan recorded: the same 1,000 rows, id-for-id.
3. The official-vs-port identity check passed on all three arms at an absolute
   difference of 0.0.
4. The sealed M0 and BLEND columns reproduce the 2026-09-04 alignment audit exactly, to
   the second decimal, on all seven metrics.

## Boundaries

Gold never entered the flight process: samples were built label-free from the runtime
view and the adapter's `gold()` refuses outright. Gold opened once, scoring-side, after
the seal, on `split_id="devel"` with `allow_heldout=False`. The held-out test split was
never named, loaded or scored. The two sealed August arms were read through the 1:1
key-rename projection the 2026-09-04 audit established; both source and projection
sha256 are recorded in `read.json` and no response text was altered.
