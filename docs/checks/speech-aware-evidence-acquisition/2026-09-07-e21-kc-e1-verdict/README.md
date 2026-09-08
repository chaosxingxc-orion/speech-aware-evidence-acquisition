# KC-E1 verdict — REJECTED, and what was measured to say so

Exposure row `SAEA-E21-KC-E1-VERDICT-V1` (`model-free-check`), registered and committed before the
first sealed byte was opened. **Zero model, GPU, tool, embedder, tokenizer, network, audio-decode and
paid-API contacts.** Reference transcripts and `wer_tags` are reached only through the registered
scoring path's own loaders (`data.references`, `reproduction.conec_entity_scoring`,
`reproduction.numeric_value_accuracy`, `reproduction.semantic_impact`), inside
`scripts/e21_window_pairing_read.py`; nothing else in this receipt opens a reference.

The verdict, the rule quoted verbatim, and every reading of it:
`docs/readiness/2026-09-07-e21-kc-e1-pre-meeting-brief-v1-verdict.md`. **This directory holds the
evidence; the note holds the argument.**

## The one-line result

**REJECTED** — the preregistration's own word is HARMFUL. The primary is met on both legs (PERSON
entity-WER reduction +4.148 pp [+2.633, +5.740] against the sealed comparator and +5.382 pp
[+3.914, +6.989] against the token-matched twin, call-clustered CI90) and **two guards fail**:
corpus-WER non-inferiority (KC-E1 − comparator +0.536 pp [+0.195, +0.917], upper bound above zero)
and numeric-value accuracy at the call-pooled figure (−0.544 pp [−1.104, −0.041], lower bound below
zero). The over-generation guard passes and passes the other way: insertions FALL by 686.

## The three arms and the identity anchor

| arm | run id | attempt | anchor | corpus WER, per-window sum vs sealed | S / D / I |
|---|---|---|---|---|---|
| comparator | `SAEA-E21-FULL44-DIRECT-BASELINE-V2` | `attempt-20260904T233816Z-bcd338` | 30/30 **PASS** | 8.1995 % vs 8.200 % | 13,098 / 5,701 / 10,700 |
| form twin | `SAEA-E21-KU-E1C-PLACEBO-44-V1` | `attempt-20260907T200859Z-251383` | 30/30 **PASS** | 8.3538 % vs 8.354 % | 13,254 / 6,460 / 10,340 |
| treatment | `SAEA-E21-KC-E1-BRIEF-44-V1` | `attempt-20260907T171238Z-f02eef` | 30/30 **PASS** | 8.7360 % vs 8.736 % | 13,022 / 8,393 / 10,014 |

Each arm's 1,593 per-window rows re-aggregate to its own sealed corpus WER, S/D/I, reference words,
every published ConEC class with its reference-word count, the non-entity and unlabelled buckets, the
negation-critical counts and the numeric partition **exactly**. The verdict runner refuses to compute
a contrast for an arm whose anchor is not `PASS`, and re-checks each rows file's SHA-256 against the
one its anchor recorded.

**KU-E1c is read from the run ROOT.** `saea-driver run --run-dir` wrote that flight's sealed artifacts
to `$SPEECHRL_DATA_DIR/runs/SAEA-E21-KU-E1C-PLACEBO-44-V1/` rather than one attempt level deeper — the
placement deviation its own closure records. Its sealed profile in
`scripts/e21_window_pairing_read.py` carries an `attempt_at_run_root` flag so the attempt id still
names the attempt that was decomposed.

## What the runner did, in order

1. `scripts/e21_window_pairing_read.py --run-id <each of the three>` — the fixed window-pairing
   instrument (`analysis.e21_window_pairing`, 2026-09-07 saturation fix, receipt
   `../2026-09-07-e21-window-pairing-fix/`), one committed sealed profile per run. Wall clock 512.4 s
   / 522.5 s / 576.2 s. Writes each arm's rows under `$SPEECHRL_DATA_DIR` and its `reaggregation.json`
   here.
2. `scripts/e21_kc_e1_verdict_read.py` — anchors, then the paired contrasts. Wall clock 319.2 s.
   Pooled ratios (`sum(numerator) / sum(denominator)` over the resampled units) through
   `analysis.paired.resampled_statistic(cluster_of=analysis.e21_window_pairing.call_of)`, seed
   **20260903**, **10,000** replicates, **CI90**; the window-level interval beside it, labelled
   optimistic; saves / harms / ties and the exact sign test from `analysis.paired.paired_contrast`,
   whose own mean-of-differences bootstrap is carried but is never the decision interval.

Fifteen metrics — corpus WER, the eight published ConEC classes, non-entity, unlabelled, numeric
accuracy window-pooled and call-pooled, the negation-critical rate and insertions per reference word
— under three contrasts (total / form / content), three interval readings (call-clustered natural
mixture, call-clustered equal-stratum, window-level optimistic) and two saturation sensitivities.

## Two changes to the instrument, both additive

* `scripts/e21_window_pairing_read.py` gains KU-E1c's sealed profile (with `attempt_at_run_root`) and
  writes an additive `entity_class_counts` field on every window row — the eight published classes
  plus `__NON_ENTITY__` and `__UNLABELLED__`, as `[substitutions, deletions, reference words]` — so a
  paired read can pool any class over a resampled set of calls without re-running the decomposition
  once per class. No existing row key, check or aggregate moves; the 2026-09-07 fix receipt's own
  files are untouched and stay sealed under their own `MANIFEST.sha256`.
* `per_call_numeric` rows gain `call_numeric_expected`, so the numeric guard can be bootstrapped at
  the call unit its published 90.73 lives at.

`ruff` is clean on both scripts, `scripts/checks/engineering_base_check.py` PASSes, and
`tests/unit/test_e21_window_pairing.py` + `tests/unit/test_analysis_paired.py` pass 58/58.

## The saturation covariate

Two saturated windows per treated arm, zero in the comparator, on **four disjoint calls**: KC-E1
`4360717#w0023` (1,980–2,070 s) and `4363614#w0027` (2,340–2,430 s); KU-E1c `4384683#w0015`
(1,260–1,350 s) and `4397829#w0005` (360–450 s). Each is charged zero reference words and zero
operations, because `reproduction.obs_loop` stitched nothing from it — which is why **two** exclusions
are reported. Dropping the four windows moves nothing (the untranscribed mass already sits on the
neighbouring window's deletion cursor); dropping the four **calls** from all three arms takes the
corpus-WER cost from +0.536 to +0.339 pp and **leaves the verdict unchanged** (upper bound +0.619,
still above zero).

## Files

| file | what it holds |
|---|---|
| `result-summary.json` | every number: the three identity anchors with their rows-file hashes, the three contrasts over fifteen metrics under three interval readings, both saturation sensitivities, the descriptive window layer, the 44-row per-call block, the E5 roster halves and the token covariate |
| `per-call-table.md` | the 44 calls — corpus WER and PERSON entity WER for baseline, placebo and brief, with each call's PERSON reference words and saturated-window counts |
| `token-throughput-covariate.json` | both arms' per-call brief token counts from their own flight receipts, the constant `+7` twin-minus-arm residual on all 44 calls, prompt/completion totals, throughput, GPU hours, and each source receipt's SHA-256 |
| `reaggregation/comparator/reaggregation.json` | the comparator's identity anchor — every check, pooled buckets, semantic and numeric totals, per-call numeric rows |
| `reaggregation/kc-e1/reaggregation.json` | the treatment's identity anchor, same shape |
| `reaggregation/ku-e1c/reaggregation.json` | the form twin's identity anchor, same shape |
| `cited/ku-e1c-flight-README.md` | the KU-E1c flight receipt's own README, the source of this verdict's twin-side flight numbers |
| `cited/ku-e1c-flight-batch-summary.json`, `cited/ku-e1c-flight-jobs.jsonl` | that flight's one complete-manifest scoring job, no sharding |
| `cited/SOURCES.md` | where each cited byte came from, and the SHA-256 of the two large receipt files that were hashed rather than copied |
| `MANIFEST.sha256` | this directory's byte manifest |

Per-window rows live under `$SPEECHRL_DATA_DIR/runs/SAEA-E21-MF-WINDOW-PAIRING-V1/`
(`verdict-v1-window-rows-comparator.json`, `-kc-e1.json`, `-ku-e1c.json`) — per-request derivatives of
sealed model outputs, so they live where those live and never in Git. Their SHA-256 values are pinned
in each arm's anchor and re-checked before a contrast is computed.

**This receipt decides one cell and nothing else.** The verdict is scoped to these 44 discovery calls,
this serving geometry, this cap of 12 entries per class and this frozen core; it is not a superiority,
generality or Stage-3 claim, and `paper-scale-confirmatory` is neither available to this repository
nor requested.
