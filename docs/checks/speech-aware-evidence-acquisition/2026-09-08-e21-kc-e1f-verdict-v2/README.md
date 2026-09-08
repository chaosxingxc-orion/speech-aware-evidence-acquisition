# KC-E1f v2 — ADMITTED, and the margins that were measured to say so

Exposure row `SAEA-E21-KC-E1F-VERDICT-V2` (`model-free-check`), registered and committed before the
first number was recomputed. **Zero model, GPU, tool, embedder, tokenizer, network, audio-decode and
paid-API contacts.** No arm is re-flown; not one byte of any arm's output is new. Reference
transcripts and `wer_tags` are reached only through the registered scoring path's own loaders
(`data.references`, `reproduction.conec_entity_scoring`, `reproduction.numeric_value_accuracy`,
`reproduction.semantic_impact`), inside `scripts/e21_window_pairing_read.py`.

The rule, the argument and every reading of them:
`docs/readiness/2026-09-08-e21-kc-e1f-repair-pass-v2-redecision.md`. **This directory holds the
evidence; the note holds the argument.**

**The v1 verdict stays on record.** `docs/checks/…/2026-09-08-e21-kc-e1f-verdict/` decided these same
sealed bytes REJECTED under guards written without margins. Nothing here withdraws it.

## The one-line result

**ADMITTED**, provisionally and with a replication obligation fixed before the verdict was known.
The primary is met on both legs — PERSON entity-WER reduction **+3.737 pp** [+2.653, +4.855] against
the sealed comparator and **+3.840 pp** [+2.752, +4.958] against the token-matched twin,
call-clustered CI90 — and all three gating guards pass at margins measured by this carrier's own
same-request replicate. **PERSON is the only metric in this cell whose effect is disjoint from that
null**; the corpus-WER, ORG and numeric-accuracy movements v1 reported as improvements are inside
replicate noise and are not demonstrated effects.

## The guard table

Percentage points; the harmful bound is the CI90 bound on the side where the arm would be worse.

| guard | v1 test | v1 | harmful bound | **v2 margin** | v2 test | slack | **v2** |
|---|---|---|---:|---:|---|---:|---|
| delivery integrity | construction; aborts the read | PASS | — | — | unchanged | — | **PASS** |
| corpus WER non-inferiority | `UB <= 0` | PASS | −0.02936 | **0.05793** | `−0.02936 <= +0.05793` | 0.08729 | **PASS** |
| numeric-value accuracy (call-pooled) | `LB >= 0` | **FAIL** | −0.02122 | **0.15651** | `−0.02122 >= −0.15651` | 0.13528 | **PASS** |
| over-generation | `UB <= 0` | **FAIL** | +0.00255 | **0.02218** | `+0.00255 <= +0.02218` | 0.01963 | **PASS** |
| negation-critical / semantic | advisory | ADVISORY | — | — | advisory; its own null excludes zero | — | **ADVISORY** |

The two guards that flipped did so because the bar moved from "significantly better" to "not worse
than this carrier's own noise". In counts: **the same request flown twice moved 31 insertions where
KC-E1f moved one, and moved three numeric values where KC-E1f moved one.**

## Where each margin comes from

| margin | value | source |
|---|---:|---|
| corpus WER | 0.05793 | `SAEA-E21-FULL44-NULL-REPLICATE-V1` null table, read from its committed receipt |
| numeric-value accuracy | 0.15651 | the same null table |
| over-generation (`δ_ins`) | **0.02218** | **computed here** from the null replicate's own per-window rows, through the same instrument — the null cell's published table does not carry this quantity |
| ConEC PERSON (reported, gates nothing) | 0.25009 | the same null table |
| semantic high-impact | 0.00148, **and its null excludes zero** | the same null table — deliberately NOT used as a margin |

`δ_ins` is anchored before it is applied: the same two row files must reproduce the null cell's
**own published** corpus-WER interval to the digit through this instrument, on point, `ci_low`,
`ci_high`, `sigma_hat` and half-width. They do. The pairing gate behind it is set at the call —
44 of 44 calls carry an identical reference-word total, 359,765 reference words on both sides —
because a window's reference-word attribution legitimately follows the alignment (68 of 1,593
windows move it) while a call's reference length cannot, and the call is the bootstrap cluster.

## The two refusals this read carries

Both are refusals, not reports: each exits non-zero and produces no decision.

1. **No number moved.** Every numeric leaf of the committed v1 decision block is compared against the
   freshly recomputed one; a single differing digit means the recomputation is not the v1 read, and
   the script refuses. It did not have to.
2. **The null instrument anchor.** A band computed from two row files may not serve as a margin
   unless those files reproduce the null cell's own published interval through this instrument.

Beside them, the instrument's own standing refusals still apply: each arm's identity anchor must be
`PASS` (30/30 per arm), the class anchor must hold on every bucket (87/87), each rows file's SHA-256
must equal the one its anchor recorded, and the §5.1 normalization attribution must close before any
contrast is computed.

## The three arms

| arm | run id | attempt | anchor | corpus WER, per-window sum vs sealed | S / D / I |
|---|---|---|---|---|---|
| comparator | `SAEA-E21-FULL44-DIRECT-BASELINE-V2` | `attempt-20260904T233816Z-bcd338` | 30/30 **PASS** | 8.1995 % vs 8.200 % | 13,098 / 5,701 / 10,700 |
| form twin | `SAEA-E21-KU-E1FC-PLACEBO-REPAIR-44-V1` | `attempt-20260908T072231Z-ec8a5b` | 30/30 **PASS** | 8.2015 % vs 8.201 % | 13,105 / 5,699 / 10,702 |
| treatment | `SAEA-E21-KC-E1F-REPAIR-44-V1` | `attempt-20260908T040832Z-ecda9c` | 30/30 **PASS** | 8.1545 % vs 8.154 % | 12,936 / 5,700 / 10,701 |

The comparator is also **both treated arms' pass 1**, the bytes they edited. All three arms' rows
were regenerated here from the sealed traces and came out **byte-identical to v1's**, file SHA-256
for file SHA-256.

## What is in each file

| file | what |
|---|---|
| `result-summary.json` | the v2 decision: the rule, every margin with its source and its null interval, the over-generation band with its anchor and its row gate, the guard table, the primary with its null-half-width comparison, and the no-number-moved proof |
| `guard-table.md` | the guard table alone, as one page |
| `recomputed/result-summary.json` | the freshly recomputed v1-form read this decision sits on: the three identity anchors, the 87-check class anchor, the §5.1 attribution and its checks, the operation-delta localization, the three contrasts (total / form / content) over 34 metrics under three interval readings and two weightings, both saturation sensitivities, the descriptive window layer, the 44-row per-call block, the E5 halves, both repair ledgers and the token covariate |
| `recomputed/per-call-table.md` | the 44 calls, corpus WER and PERSON entity WER in all three arms |
| `recomputed/token-throughput-covariate.json` | the measured +7-token match and both flights' token, cost, throughput and serving blocks |
| `reaggregation/{comparator,kc-e1f,ku-e1fc}/reaggregation.json` | each arm's identity anchor: every check, the pooled buckets, the per-call numeric rows, the rows file's path and SHA-256 |
| `attribution/{kc-e1f,ku-e1fc}/attribution.json` | the §5.1 receipt, regenerated: construction checks, the `(I − D)` identity, the interior-zero proof, every span with a non-zero normalization delta |
| `MANIFEST.sha256` | this directory's byte manifest |

**Content-free by construction.** Not one hypothesis character is in this receipt. Per-window rows
and span tables live under `$SPEECHRL_DATA_DIR/runs/SAEA-E21-MF-WINDOW-PAIRING-V1/` and never in
Git; their SHA-256 values are pinned in each anchor and re-checked before a contrast is computed.

## How it was produced

```
python scripts/e21_window_pairing_read.py --run-id <run> \
    --out-dir docs/checks/.../2026-09-08-e21-kc-e1f-verdict-v2/reaggregation/<slug> \
    --rows-out $SPEECHRL_DATA_DIR/runs/SAEA-E21-MF-WINDOW-PAIRING-V1/kce1f-v2-window-rows-<slug>.json

python scripts/e21_kc_e1f_normalization_attribution.py \
    --treated-run-id <run> --treated-attempt-id <attempt> \
    --out-dir docs/checks/.../2026-09-08-e21-kc-e1f-verdict-v2/attribution/<slug> \
    --spans-out $SPEECHRL_DATA_DIR/runs/SAEA-E21-MF-WINDOW-PAIRING-V1/kce1f-v2-attribution-spans-<run>.json

python scripts/e21_kc_e1f_verdict_read.py \
    --reaggregation-dir docs/checks/.../2026-09-08-e21-kc-e1f-verdict-v2/reaggregation \
    --attribution-dir  docs/checks/.../2026-09-08-e21-kc-e1f-verdict-v2/attribution \
    --rows-dir $SPEECHRL_DATA_DIR/runs/SAEA-E21-MF-WINDOW-PAIRING-V1 \
    --rows-prefix kce1f-v2-window-rows- \
    --out-dir docs/checks/.../2026-09-08-e21-kc-e1f-verdict-v2/recomputed

python scripts/e21_kc_e1f_v2_redecision.py \
    --verdict-summary docs/checks/.../2026-09-08-e21-kc-e1f-verdict-v2/recomputed/result-summary.json \
    --v1-summary      docs/checks/.../2026-09-08-e21-kc-e1f-verdict/result-summary.json \
    --null-summary    docs/checks/.../2026-09-08-e21-full44-null-replicate-v1/verdict/result-summary.json \
    --comparator-window-rows $SPEECHRL_DATA_DIR/runs/SAEA-E21-MF-WINDOW-PAIRING-V1/kce1f-v2-window-rows-comparator.json \
    --null-window-rows       $SPEECHRL_DATA_DIR/runs/SAEA-E21-FULL44-NULL-REPLICATE-V1/analysis/window-rows-replicate.json \
    --out-dir docs/checks/.../2026-09-08-e21-kc-e1f-verdict-v2
```

Seed 20260903, 10,000 replicates, CI90, pairing at the fixed 90-second window and clustering at the
call — the frozen constants of `analysis.e21_window_pairing`, not arguments this read chose. The v2
rule itself, in English and in code, was committed in `8808fe94` before the first of these commands
was run.
