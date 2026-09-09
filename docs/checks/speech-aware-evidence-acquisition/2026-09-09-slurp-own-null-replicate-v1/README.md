# `SAEA-SLURP-DEV1000-NULL-REPLICATE-V1` — SLURP's own greedy replicate null

The cell of `docs/readiness/2026-09-09-slurp-own-null-replicate-v1-preregistration.md`: the sealed
DEV-1000 closed-list direct comparator flown a second time under its exact configuration, so that
SLURP's non-inferiority margins stop being imported from Earnings-22 and from EVO-S1's flip rate and
start being measured.

**There is no verdict.** The cell has no factor, so it admits and refutes nothing. Its whole output
is a table of intervals. The reasoning is
`docs/readiness/2026-09-09-slurp-own-null-replicate-v1-verdict.md`.

| | |
|---|---|
| study commit | `c6e8e95a` (registration) — the flight binds it, `study_repo_dirt` empty |
| flight | attempt `attempt-20260909T043847Z-f4306e`, 1,000 rows, one attempt, no recovery re-registration |
| comparator | `SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1`, attempt `attempt-20260905T060424Z-2c5596` |
| identity anchor | config `6be064ba…b894f`, protocol `7e83a705…951b2`, split `8580d199…1e3c84` — the comparator's own, to the digit |
| falsifier | **PASS on 1,000 of 1,000**, prompt-token delta histogram `{0: 1000}` |
| paper-facing scorer | `slurp-slu-official-projected-v2`; secondary `slurp-slu-f1-normalized-v1` |
| serving | attached to the coordinator's resident session `slurp-np8-base-c65536-20260909`; no server started, none stopped |
| cost | 1,000 calls of 1,050; 2,884.7937 metered speech seconds of 3,000; **0.0637 GPU-h**; paid API spend 0 |

## The headline

| | value |
|---|---:|
| intent accuracy, comparator → replicate | 73.10 → **73.60** |
| intent delta, speaker-clustered CI90 | **+0.5000** [−0.4049, +1.4341] |
| **intent margin (the CI90 half-width)** | **0.9195** |
| SLU-F1 (micro), comparator → replicate | 35.80 → **36.09** |
| **micro SLU-F1 margin** | **1.1804** |
| raw completion identity rate | **82.10 %** |
| projected-intent flip rate | **5.20 %** |

## Layout

| path | what |
|---|---|
| `falsifier.py` | the archived copy of the section 2 request-side falsifier, run **before any score file was opened**. Zero contacts |
| `read.py` | the archived copy of the single registered read. Scoring-side only, zero contacts. It resolves the checkout and the data root from its own constants, so this copy reproduces the bytes but not the invocation |
| `build_result_summary.py` | the assembler of `verdict/result-summary.json` and the three markdown tables; reads nothing but `verdict/read.json` and `flight-1000/falsifier.json` |
| `flight-1000/dry-run.json` | the zero-contact preflight that checked the identity anchor before the flight |
| `flight-1000/falsifier.json` | the 1,000-row falsifier result |
| `flight-1000/flight-receipt.json` | preflight, preprocess, serve (attached), `run_phases`, seal, score |
| `flight-1000/monitor-contact-window.json` | the monitor summary over the flight's own contact window |
| `verdict/read.json` | the full read |
| `verdict/result-summary.json` | the machine form of the verdict |
| `verdict/null-table.md` | the null table, micro and per row, both interval families, secondary beside |
| `verdict/per-scenario-table.md` | all 18 gold scenarios |
| `verdict/per-cluster-table.md` | all 124 speaker clusters |
| `verdict/batch-summary.json` | the verified `core.scoring_batch` record: one job per manifest, `include_per_sample`, never sharded |

## The four things this receipt exists to pin

1. **The request side is provably identical on every row.** 1,000 of 1,000 `MODEL_REQUEST` payloads
   hash equal after removing the two scheduling fields EVO-S1 already names (`request_id` and
   `decoding_params.id_slot`); 1,000 of 1,000 speech packets equal by sha256; **1,000 of 1,000
   prompt-token counts equal, with `{0: 1000}` as the entire delta histogram**; metered speech and
   `prompt_tokens_total` equal to the digit. Only the completions moved.
2. **The identity anchor was computed before the exposure row was written.** The composed config,
   protocol and split hashes were derived offline with zero contacts, and `FlightRuntime.preflight`
   re-derived the same three before the first contact. A replicate whose protocol hash moved is not
   a replicate.
3. **The margins are per metric and per estimand.** 35.80 is a micro figure; its margin is 1.1804,
   not the per-row 0.8188. A cell that quotes the per-row number while claiming the micro headline
   is using the wrong margin.
4. **The imported bar was too narrow on all eleven metrics**, by 1.28x to 2.12x, and the imported
   28.1 % flip floor was 1.57x too high. Both are recorded with their ratios so the correction is
   auditable rather than asserted.

## Two things this receipt records rather than tidies away

* **A null fails the silence-tail cell's clause 3.** With no factor at all, 5 of 18 scenarios lose
  intent and the worst loses 5.13 pp, against a rule allowing at most 2 losers and 3.0 pp. The
  clause is kept in the tables, marked as non-discriminating at this stratum size, rather than
  quietly dropped.
* **The projected-intent flip prediction failed by 0.2 pp** (5.20 % against a predicted "under
  5 %"), and the intent half-width prediction failed by 1.53x. Both are reported in the verdict's
  section 8 as failures, not rounded into agreement.
