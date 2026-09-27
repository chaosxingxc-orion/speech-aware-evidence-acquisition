# Cell DET: preregistration

Registered 2026-09-27 at study commit `9255ac71`, before any contact, from the sealed
PLAN lock fragments by script (decision 58; `scripts/flights/derive_slurp_det_np1_cells.py`,
`scripts/flights/write_slurp_det_np1_registration.py`). Development numbers only (owner decisions 28
and 86); never a test claim. **READINESS HELD on both cells.**

## 1. The question

Is the programme's between-flight measurement floor -- +1.87 pp SLU between two request-identical
flights at n = 625, 91.5 % byte identity even inside one flight -- an engineering artefact of the serving
geometry (four slots under continuous batching, prompt cache on, q8_0 KV cache: the configuration in
which llama.cpp greedy decoding is not bitwise reproducible) or a property of the model's numerics on
this hardware? Nobody has measured a single-slot, prompt-cache-off server. This cell does.

## 2. The cell

| item | value |
| --- | --- |
| base | the LOCKED v2.0 plan, cell PLAN (`SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1`), byte-identical in every knob |
| the one variable | the serving geometry: one 24,576-token slot (`-np 1 -c 24576`), `--no-cache-prompt`, no `--slot-prompt-similarity`; model fragment `q4km-mmproj-free-slurp-native-bounded-perception-proof-np1-nocache-ctx24k-max512-v1`, session `serving-slurp-native-det-np1-nocache-v1`; in the baseline `serving_slots` 4 -> 1 (the flight-side half of the same geometry) |
| not variables | everything else: `native_episode`, `knowledge_stores`, `phase_material`, `policy`, `scorers`, `decoding_params` (temperature 0, seed 20260913, max_tokens 512), `prompt_order`, `server_env`, the model file and sha256, the runtime receipt, `-fa on`, `-ctk/-ctv q8_0`, `-b 2048 -ub 512`, `-ngl 999`, `--cache-ram 0`, `--no-cache-idle-slots`, the speech packets (`tests/unit/test_stage3_det_np1_cells.py`, `geometry-diff-v1.json`) |
| design | pass A then pass B, two cells that differ only in their run/attempt/FIT identities and prose, consecutively in ONE chain on ONE resident session (the VAR1 PLAN / PLANR shape) |
| roster | the first 50 rows of TRAIN Fold A in roster order, `docs/receipts/rosters/slurp-stage3-det-fold-a-50-v1.json` (`SLURP-STAGE3-DET-FOLD-A-50-V1`); 10 of 18 scenarios; the same first 50 rows PLAN flew |
| runs | A `SAEA-SLURP-STAGE3-DET-NP1-FOLD-A-50-A-V1` / `SAEA-SLURP-STAGE3-DET-NP1-FOLD-A-50-A-FIT-V1`; B `SAEA-SLURP-STAGE3-DET-NP1-FOLD-A-50-B-V1` / `SAEA-SLURP-STAGE3-DET-NP1-FOLD-A-50-B-FIT-V1`; read `SAEA-SLURP-STAGE3-DET-NP1-FOLD-A-50-READ-V1` |
| composed config hashes | A `658e8032585f7214133d21528d5b7b2afebabe8ebfb48432c6645cf45a2d2ac9`; B `26b248f6541989f25205169a6c963b66bc00c345ee362e89ad963b5277c6de78` |
| protocol hashes | A `3c915405b94fac53bb59d91d34f098a56ac85adb3f0b9ff74cbf472dd5b77931`; B `6548e1ff67469a5318badf614cd96c70ea5ea9e01e3f6760dda835cc49e3fc53` |
| split identity | `af8154d5dedd3768b145a9d5f5ef6d90eb0ab0f6611a02ee82b2f22fd73a07fa` |
| id-list sha256 | `1fed658cdf96580f021887e54b1964d544dd55e8d70afd39a7e3744640f2f4b5` |
| comparator | none: the pair is its own control; the sealed np4 answers of the same 50 rows (PLAN) are available offline for a third, descriptive comparison |
| authority | owner decision 140; docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md; docs/results/2026-09-24-slurp-stage3-roll-aa-within-flight-null-read.md; docs/results/2026-09-25-slurp-var1-complete-evidence.md; owner decisions 28, 86 and 101 |

## 3. The read rule (fixed here)

DESCRIPTIVE; no verdict, no admission. Per row: byte identity of the delivered answer between pass A
and pass B (the sealed outputs row's `text`, whose `response_text_sha256` the read re-derives); the
count of identical rows out of 50; and, beside it, ROLL-AA's within-flight np4 statistic (183 of 200,
91.5 %) and the cross-flight np4 disagreement the instrument note records (about 28 % of raw outputs).
Then the pair's pooled SLU-F1 and intent paired deltas (row bootstrap, 10,000 draws, seed 20260915) as
descriptive numbers, and the intent-flip and entity-set-flip shares where the sealed per-sample scores
carry the parsed prediction. Driver `scripts/analysis/slurp_det_pair_read.py`, runbook `scripts/flights/det/det_read.sh`, recipe
`docs/readiness/2026-09-26-slurp-stage3-det-np1-fold-a-50-v1/analysis-recipe-v1.json`.

**Routing.** 50 of 50 identical -> the coordinator registers the 200-row re-estimate; fewer -> the
offset is intrinsic and this axis closes. **A 50-row cell cannot support a floor re-estimate**; it decides
only whether the 200-row re-estimate is worth flying.

## 4. Decision 140: determinism decided, throughput informed

Owner decision 140 (2026-09-26): the np1 cache-off test is authorised as a CHEAP TEST, but ADOPTION of any geometry is decided on THROUGHPUT, because future rounds need massive sampling. This cell decides a DETERMINISM question and INFORMS a THROUGHPUT one; the coordinator will not adopt np1 for sampling-heavy work on determinism alone. The read therefore reports, beside per-row byte identity, contacts per minute and prompt tokens per second for each pass at the np1 cache-off geometry -- from the sealed dispatch window (flight-receipts.json run_phases: wall_seconds, contact_window, contact_count) and the sealed generation manifest's cost block (prompt_tokens_total) -- and the same two numbers for the resident np4 geometry from ROLL-2's sealed arm (8,996 contacts, 81,435,827 prompt tokens, 16:00:01Z to 18:22:39Z, 8,558 s: 63.07 contacts per minute, 9,515.8 prompt tokens per second), so the trade is one table.

| geometry | contacts per minute | prompt tokens per second |
| --- | ---: | ---: |
| np4 x 24,576, prompt cache on (ROLL-2 sealed arm) | 63.07 | 9,515.8 |
| np1 x 24,576, prompt cache off (pass A) | measured from the sealed dispatch window | measured |
| np1 x 24,576, prompt cache off (pass B) | measured from the sealed dispatch window | measured |

## 5. The measurement declaration

```json
{
  "stage3_measurement": {
    "SAEA-SLURP-STAGE3-DET-NP1-FOLD-A-50-A-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "form-proof",
      "note": "The cell measures REPRODUCIBILITY -- per-row byte identity of the delivered answer across two request-identical passes on a single-slot, prompt-cache-off serving geometry, and the SLU/intent difference of the pair -- and makes NO effectiveness claim. Its 50 rows are under the measurement instrument's MIN_BENEFIT_ROWS, so under rule 5 this is a form proof by size; claims_benefit is false and expected_effect_pp is 0.0 because the cell registers no effect to look for: the passes are the same request and any difference between them is the instrument, not a mechanism. It is NOT an admission request: no admission mode is declared and no harm margin is claimed. A 50-row cell cannot support a floor re-estimate; it decides only whether the 200-row re-estimate is worth flying, and (decision 140) it decides a determinism question while merely informing a throughput one.",
      "primary_metric": "per-row byte identity of the delivered answer between pass A and pass B (the count of identical rows out of 50), with the pair's pooled SLU-F1 and intent difference reported as descriptive numbers and, under decision 140, contacts per minute and prompt tokens per second per pass beside ROLL-2's np4 numbers",
      "rows": 50
    },
    "SAEA-SLURP-STAGE3-DET-NP1-FOLD-A-50-B-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "form-proof",
      "note": "The cell measures REPRODUCIBILITY -- per-row byte identity of the delivered answer across two request-identical passes on a single-slot, prompt-cache-off serving geometry, and the SLU/intent difference of the pair -- and makes NO effectiveness claim. Its 50 rows are under the measurement instrument's MIN_BENEFIT_ROWS, so under rule 5 this is a form proof by size; claims_benefit is false and expected_effect_pp is 0.0 because the cell registers no effect to look for: the passes are the same request and any difference between them is the instrument, not a mechanism. It is NOT an admission request: no admission mode is declared and no harm margin is claimed. A 50-row cell cannot support a floor re-estimate; it decides only whether the 200-row re-estimate is worth flying, and (decision 140) it decides a determinism question while merely informing a throughput one.",
      "primary_metric": "per-row byte identity of the delivered answer between pass A and pass B (the count of identical rows out of 50), with the pair's pooled SLU-F1 and intent difference reported as descriptive numbers and, under decision 140, contacts per minute and prompt tokens per second per pass beside ROLL-2's np4 numbers",
      "rows": 50
    }
  }
}
```

`50` rows is under the instrument's `MIN_BENEFIT_ROWS` of 200, so rule 5 makes this a form proof by
size: `form-proof`, `claims_benefit` false, `expected_effect_pp` 0.0. No `admission` mode is declared.
`stage3_algorithm` is `none` on both cells.

## 6. Budgets and failure rule

Per pass: 550 generation contacts (50 x 11, run-cumulative),
2200 FIT endpoints, 300 native
task-contract calls (tool-free form, expected 0), 1184 repeated
speech seconds, 2.0 GPU hours, one official complete score. Expected about
251 contacts and about 0.6814 GPU hours per
pass at an assumed 4x np1 per-contact cost (PLAN's realised
0.000679 h per contact on four slots); both assumptions are what the flight
measures. Stop and preserve on the first failure; AT MOST ONE root-diagnosed recovery re-registration per
pass; a second failure closes the pass and the fix is proven on a four-row dry run. A resident-session
identity refusal spends no contact and is not a flight failure. A pass that seals alone answers nothing.

## 7. What this registration does NOT authorise

`readiness.state` is `held` on both cells and `requirements` is empty (the flip appends the decision and
preparation requirements). No flight before root mints `coordination/slurp-stage3-det-np1-fold-a-50-v1/root-admission-v1.json` (decision id
`slurp-stage3-det-np1-fold-a-50-admission-v1`, four eligible run ids), countersigns the five DRAFT rows, flips both passes and swaps
the resident session (stop `serving-slurp-native-candidate-five-train-a-np4-v1`, start `serving-slurp-native-det-np1-nocache-v1`); the registration agent never
touched the np4 session, any lock, any scheduled task or any batch script. No contact of any kind was
made. No test-split, Fold B or DEV contact or read; no knob change; no floor re-estimate from 50 rows;
no adoption of np1 for sampling-heavy work on determinism alone; `--allow-output-change` is never passed.

## 8. Claim boundary

No superiority, generalisation, component-causal, bar, admission, held-out, confirmatory or paper-scale
claim of any kind. A byte-identity count measures the instrument, not an effect; 50 of 50 would not
make a 200-row floor, and fewer would not make a defect.
