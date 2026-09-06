# EVO-S1 prompt fit — the worst admissible envelope, and the F3 token counter

Exposure row `SAEA-SLURP-EVO-S1-PROMPT-FIT-V1`, attempt
`attempt-20260906T202423Z-evos1promptfit`, `bounded-discovery-probe`. Authority:
`docs/readiness/2026-09-06-slurp-evo-s1-slot-schema-evolution-v1-preregistration.md`
section 13 item 6 and section 16 (what round 1 waits on, item 1). Entry point
`scripts/slurp_evo_s1_prompt_fit.py`.

**Zero generated tokens and zero decoder evaluations.** 1 `GET /props`, 2
`POST /apply-template`, 68 `POST /tokenize`. The server was spawned under a
gate-checked `contracts.ExecutionPlan` (frozen-core gate PASS, umbrella lock
`c4ee908562c0…`), served for 28 seconds, and was stopped with its own stop receipt
(`SIGTERM`, not forced). GPU read before the spawn: 0 MiB used at the 100 W
enforced limit.

## The four things this row owed

| # | owed | result |
|---|---|---|
| a | the worst envelope **measured**, not estimated | **11,336 text tokens**; upper bound 11,611 with the speech term |
| b | `-np` re-derived against the folds' own speech term | **`-np 4` unchanged**, margin 4,709 tokens |
| c | the `token_counter` binding written down | `llama-server:/tokenize` at `-np 4` / `-c 65536`, chat template `45777d2e…` |
| d | that counter handed to `run_candidates_step` | bound by `scripts/run_evolution_round.py --token-counter-url` for round 1's F3 |

## The worst envelope is a candidate's, not `A_0`'s

KC-S1b's widest row was `A_0`'s 26,720-character full-schema fallback. A round-1
candidate may raise **every one of the sixty per-intent blocks** to `+20 %` of the
incumbent's tokens (`rails.proposer.SLURP_RELATIVE_TOKEN_BUDGET`), so the widest
prompt an admissible round-1 cell can send is that fallback with all sixty blocks at
their own budget. The script BUILDS that string — the pad word ` item` measured to
cost exactly one token on this tokenizer, then each block padded to its own budget —
and renders it through the production instruction path
(`rails.phase_material.build_material_for_phase` with the phase's real spec, its real
static text, and a predecessor pad measured at exactly the 64-token completion
ceiling). The envelope is therefore a real rendering, not an arithmetic sum.

| | `A_0` (the admitted incumbent) | worst admissible candidate |
|---|---:|---:|
| schema characters | 26,720 | 33,915 |
| schema tokens | 7,460 | 8,899 |
| instruction characters | 28,176 | 35,371 |
| text prompt tokens | 9,897 | **11,336** |
| speech feature tokens (bound) | 273 | 273 |
| prompt tokens upper bound | 10,172 | **11,611** |
| context margin at 16,384-token slots | 6,148 | **4,709** |

`A_0`'s 7,460 measured tokens confirm the preregistration's "about 7,500"; the
`+20 %` search budget costs 1,439 tokens on top of it, well inside the slot.

Per-intent incumbent blocks run **31 to 223 tokens** (sum 7,319; sum of budgets
8,758) over 60 intents; the per-intent table is in `prompt-fit.json`.

## Geometry: unchanged

`np_admissible` is `[4, 2, 1]` against the 65,536-token server context: at `-np 8`
the 8,192-token slot cannot hold 11,611 + 64. **`-np 4` is confirmed and the model
fragment `q4km-mmproj-free-speech-native-np4-base-speech-query-prefix-max64` is not
changed**, so the round-1 cells fly the geometry the preregistration and every
committed EVO-S1 fragment already name, and the KC-S1b contrast stays
geometry-matched.

## The speech term is a bound, and the bound is evidence

The fit deliberately runs BEFORE `SAEA-SLURP-EVO-FOLD-PACKETS-V2` so a geometry
surprise costs no packet contacts, so it cannot read the folds' own packets. It uses
the encoder's own token function, `13 * ceil(audio_seconds / 0.96)`, replayed
fail-closed by `verify.py` against all 1,000 committed DEV-1000 packets:
**0 violations, maximum shortfall 13 tokens, the bound attained at the maximum**
(`speech-token-bound.json`). Fold A's longest row bounds at 156 tokens and fold B's
at 273, against a text envelope near 11,336 — the speech term cannot decide this
geometry. `verify.py` re-runs against the fold packets once they land and records
the realized maxima beside the bound.

## Files

| file | what it is |
|---|---|
| `prompt-fit.json` | the receipt: both envelopes, the per-intent budget table, the fold speech facts, the `token_counter` binding, the session and stop receipts |
| `verify.py` | the model-free bound replay, zero contacts |
| `speech-token-bound.json` | its output: DEV-1000 VERIFIED / PASS, the two folds PENDING until promotion |
| `README.md` | this file |

## Deviation recorded

The flight brief asked for an entry point of at most 150 lines;
`scripts/slurp_evo_s1_prompt_fit.py` is 311. The excess is the mandatory
`REPO`/`PYTHONPATH` guard block, the import surface and the receipt document; the
measurement body is under 90 lines and nothing was folded away to hit a count.
