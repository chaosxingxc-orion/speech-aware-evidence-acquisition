# Audio2Tool official-protocol replication, v1 — verdict

Run `SAEA-A2T-OFFICIAL-PROTOCOL-REPLICATION-V1`, flown 2026-09-04 on the frozen 400-item Audio2Tool
discovery split (`A2T-CALIBRATION-400`, flight split identity hash
`11091b38ae9d53530952af632636d7e79a614350213e10c6c26583c37f85846b`), one cell `R-official-raw`,
attempt `attempt-20260904T135250Z-rofficialraw`, study commit `7eb4aa00`, manifest SHA-256
`64d0759d6cb117574e4bfdb23c3b6832b5bde7434990b74b859f56aa145a2401`.

Preregistration: `docs/readiness/2026-09-04-a2t-official-protocol-replication-v1-preregistration.md`.
Full numbers:
`docs/checks/speech-aware-evidence-acquisition/2026-09-04-a2t-official-protocol-replication-400-v1/result-summary.json`.
Paper-facing scorer: `a2t-toolcall-official` — the pinned release's own `metrics.py`, git blob
`d98277bcf69795c9a0ae54e538c170abfd8c51ca`, commit `b9d5383ca30945fbafb965a04bea40117e1e8a82`.

## Verdict: FAIL. But the protocol was the wrong suspect for most of the gap, and Tier 1 is now the whole story.

The preregistered rule (section 7) asked for |delta| <= 5 pp against the paper row on tiers 1, 2, 5
and 6 with the tier rank order preserved. **One of those four tiers passes** (tier 6, +2.5 pp), the
rank order is not preserved, and the paper's value lies outside the Wilson CI90 on three of the four.
FAIL, not CONSISTENT-WITHIN-NOISE.

That is the letter of it. The substance is different from the calibration's, in three ways:

1. **The published prompt is a third the size of the reconstruction, and its output contract is
   different in kind.** The compact registry renders to 3,581 tokens against 13,236 for this
   repository's legacy registry text — measured through the pinned template before any contact. The
   published protocol asks for a **call string**; the reconstruction asked for a JSON array.
2. **Mirroring the published protocol genuinely improves tool selection**, by +5.50 pp overall on the
   same 400 rows, paired, sign test p = 0.023, CI90 [+1.75, +9.25] pp. It closes 39 pp of the summed
   per-tier gap to the paper (77.3 pp remaining, from 116.3 pp).
3. **Tier 1 moves the wrong way.** Under the published protocol Tier-1 tool accuracy is **60.0 %**,
   *lower* than the reconstruction's 66.0 % on the same rows and the same metric, against a published
   92.4 %. Every other acceptance tier improved. Whatever produces the paper's Tier-1 row, it is not
   the request protocol, and it is now the only large unexplained quantity left.

## Per-tier, official scorer, n = 50 per tier

Tool accuracy (%), with the Wilson score CI90 for a binomial proportion at n = 50.

| tier | ours | CI90 | paper | delta | within 5 pp | paper in CI90 |
|---|---:|---|---:|---:|:--:|:--:|
| tier1_direct | 60.0 | [48.4, 70.6] | 92.4 | **−32.4** | no | no |
| tier2_parametric | 74.0 | [62.8, 82.8] | 84.6 | −10.6 | no | no |
| tier3_multi_intent | 72.0 | [60.6, 81.1] | 74.7 | −2.7 | yes | yes |
| tier4_implicit | 28.0 | [18.9, 39.4] | 33.4 | −5.4 | no | yes |
| tier5_needle | 78.0 | [67.1, 86.1] | 90.6 | −12.6 | no | no |
| tier6_correction | 84.0 | [73.8, 90.7] | 81.5 | **+2.5** | yes | yes |
| tier7_multiturn | 58.0 | [46.4, 68.8] | 54.6 | +3.4 | yes | yes |
| tier8_intent_blending | 34.0 | [24.1, 45.6] | 41.7 | −7.7 | no | yes |

Decision tiers are 1, 2, 5, 6. Summed absolute gap across all eight tiers: **77.3 pp**.

Rank order, ours: tier6 > tier5 > tier2 > tier3 > tier1 > tier7 > tier8 > tier4.
Rank order, paper: tier1 > tier5 > tier2 > tier6 > tier3 > tier7 > tier8 > tier4.
The two agree on the bottom three and disagree at the top entirely because of Tier 1.

### The other official metrics, per tier

| tier | exact match | paper EM | param F1 macro | param F1 micro | parse rate | rows naming >1 call |
|---|---:|---:|---:|---:|---:|---:|
| tier1_direct | 12.0 | 92.4 | 18.0 | 3.0 | 100.0 | 0 |
| tier2_parametric | 20.0 | 15.6 | 44.3 | 44.4 | 100.0 | 0 |
| tier3_multi_intent | 32.0 | 28.6 | 43.3 | 36.2 | 100.0 | 27 |
| tier4_implicit | 16.0 | 11.3 | 20.3 | 8.2 | 98.0 | 0 |
| tier5_needle | 18.0 | 36.0 | 29.3 | 32.2 | 100.0 | 0 |
| tier6_correction | 28.0 | 24.8 | 36.6 | 25.7 | 100.0 | 0 |
| tier7_multiturn | 18.0 | 16.3 | 35.3 | 33.1 | 100.0 | 0 |
| tier8_intent_blending | 18.0 | 12.4 | 26.0 | 18.3 | 100.0 | 25 |
| **overall, n = 400** | **20.25** | — | **31.65** | **27.39** | **99.75** | **52** |

Both parameter-F1 columns are reported because the published code and the published prose disagree:
`evaluator._compute_metrics` takes a plain mean of each sample's F1, which is a **macro** average,
while the paper's wording says "micro". The macro column is the published code's own number.

Exact match beats the paper on five of eight tiers and loses badly on two: tier5 (18.0 vs 36.0) and,
overwhelmingly, tier1 (12.0 vs 92.4).

## Tier 1 is the anomaly, and this flight sharpens it rather than solving it

The calibration verdict already flagged that the paper reports 92.4 for BOTH tool accuracy and exact
match on tier 1 — identical figures on one tier and nowhere else. This flight adds three facts:

- Under the published protocol, faithfully mirrored, Tier-1 tool accuracy **fell** from 66.0 to 60.0
  against the same gold and the same metric. It is the only acceptance tier that got worse.
- Tier-1 parse rate is 100 %: every row produced a well-formed call. The misses are tool choice.
- Tier-1 exact match is 12.0 % against a tool accuracy of 60.0 %, i.e. most rows that pick the right
  tool then attach parameters gold does not have. Tier-1 gold is argument-free by the benchmark's own
  construction, so a single unsolicited argument destroys exact match. The paper's 92.4/92.4 pair
  means its Qwen3-Omni run emitted **no** unsolicited arguments on tier 1 while choosing the right
  tool 92.4 % of the time. Neither half of that reproduces here.

## Protocol effect: like-for-like against the sealed calibration cell

`A0prime-legacy-raw` (`attempt-20260904T081627Z-a0primelegacyraw`) is the calibration's raw-audio
legacy cell on the same 400 rows and the same harness. Comparing it needs care, because each scorer
parses one output contract and not the other. Three readings, all zero-contact re-scores of already
sealed bytes:

**(a) Official scorer on both — mechanical, and dominated by format.** The official parser looks for
`name(...)`. A0prime's JSON arrays contain no such span, so it scores 0.0 tool accuracy and 0.0 parse
rate on all 400 rows. Delta +0.6100, CI90 [+0.5725, +0.6450]. This number is real but it measures
format compatibility, not tool choice, and it is reported only so nobody later mistakes its absence
for an omission.

**(b) Each cell under the scorer that reads its own contract.** R-official-raw 61.0 % (official);
A0prime 51.75 % (`a2t-toolcall` multiset) and 50.50 % (`a2t-toolcall-v2` ordered). Not a like-for-like
metric — different scorers, different gold interpretation.

**(c) Format-matched diagnostic — the honest protocol effect.** The **same** official metric and the
**same** official gold, with each cell's prediction taken by the parser its own contract asks for.
Only the parser is swapped, and only for the cell built to emit the other contract. This is a
diagnostic and enters no decision.

| tier | A0prime (format-matched) | R-official-raw | protocol effect | paper |
|---|---:|---:|---:|---:|
| tier1_direct | 66.0 | 60.0 | **−6.0** | 92.4 |
| tier2_parametric | 68.0 | 74.0 | +6.0 | 84.6 |
| tier3_multi_intent | 60.0 | 72.0 | **+12.0** | 74.7 |
| tier4_implicit | 30.0 | 28.0 | −2.0 | 33.4 |
| tier5_needle | 62.0 | 78.0 | **+16.0** | 90.6 |
| tier6_correction | 70.0 | 84.0 | **+14.0** | 81.5 |
| tier7_multiturn | 58.0 | 58.0 | 0.0 | 54.6 |
| tier8_intent_blending | 30.0 | 34.0 | +4.0 | 41.7 |
| **overall** | **55.50** | **61.00** | **+5.50** | — |

Paired over the same 400 rows, tier-stratified, 10,000 replicates, seed 20260903:
**delta +0.0550, saves 54, harms 32, ties 314, sign test p = 0.0230, CI90 [+0.0175, +0.0925]**.

Summed absolute per-tier gap to the paper: **77.3 pp** for the official protocol against **116.3 pp**
for the reconstruction. The published protocol is a genuine and statistically significant improvement
in tool selection, and it is still 77 pp of tier-summed gap away from the published row.

## Parse and multi-call behaviour

- **Parse rate 99.75 %** (399 of 400) under the official parser, against 89.0 % for A0prime under its
  own JSON parser. One tier-4 row failed to produce any call-shaped span.
- **52 rows named more than one call** — 27 on tier 3, 25 on tier 8, zero everywhere else. The
  official HF adapter never populates `all_tool_calls`, so **every one of those rows is scored on its
  first call only**. That is the published protocol faithfully reproduced, not a simplification made
  here, and it applies equally to the paper's own Qwen3-Omni row.
- **On the 100 rows whose gold asks for several calls, 48 named exactly one.** Distribution of
  call-shaped spans: 48 rows with 1, 31 with 2, 19 with 3, 2 with 4. Per tier: tier 3 emitted one
  call on 23 of 50 (mean 1.78 spans against a mean of 2.38 expected tools), tier 8 on 25 of 50
  (mean 1.72 against 2.70). The calibration addendum measured the same behaviour on the legacy JSON
  contract at **1 of 100** and on the native `tools` contract at **81–84 of 100**; the published
  protocol sits between them, which is unsurprising given that its prompt says "Output ONLY the tool
  call", singular. It costs this cell nothing on the headline metric, because the official metric
  reads only the first call either way — but it is the reason `multi_tool_recall` is 0.284.
- **`multi_tool_all_match` is 0.0 on all 100 multi-tool rows, by construction.** The official HF path
  can only ever report one predicted tool, so an unordered set match against 2+ expected tools cannot
  succeed for any model scored this way. The number is reported for completeness and carries no
  information about this cell.
- **`a2t-toolcall` and `a2t-toolcall-v2` report 0.0 on all 400 rows, with 400 parse failures each.**
  This is a format mismatch, not a model result: those scorers parse the reconstructed JSON-array
  contract and the published protocol asks for a call string. The preregistration promised "the same
  per-tier table under a2t-toolcall-v2 ordered"; that table is uniformly zero and is recorded in
  `result-summary.json` under `repo_scorers_on_this_cell`, labelled for what it is. The 4-row smoke
  caught this before the flight and the exposure row records it.

## Throughput

| quantity | value |
|---|---:|
| contacts | 400 of 408 planned, 450 registered |
| speech audio | 2,159.688 s of 2,300 registered |
| serving geometry | `-c 49152 -np 3`, 16,384 tokens per slot, `max_tokens` 256 |
| model load | 10.0 s |
| end-to-end wall (preflight through scoring) | 278 s |
| mean per-call latency | 0.782 s (A0prime: 1.401 s at `-np 2`) |
| prompt tokens per call | 3,660 (A0prime: 13,315) |
| completion tokens per call | 16.3 |
| GPU `enforced.power.limit` | 100.00 W before and after |

One attempt, FINALIZED, zero aborted, zero orphans, no recovery re-registration used.

## Deviations that remain in force

All ten recorded in preregistration section 4 still stand. The three that could plausibly matter for
Tier 1, in the order this flight would rank them:

1. **The roster.** The frozen 400 is 50 stratified rows per tier over 374 distinct `query_idx` with
   mixed speakers; the release evaluates the **first successful speaker of every query of every
   tier**. This is the largest population difference and the only one whose removal is a bounded,
   well-defined experiment.
2. **Quantization.** Q4_K_M against the release's bf16. Not flown.
3. **The system-prompt whitespace variant.** `configs/example_config.yaml` carries the same four
   sentences newline-separated with a trailing newline; a config-driven official run would send that
   variant, while the adapter's in-code default — the one flown here — separates them with spaces.
   The two differ only in whitespace, so this is the smallest of the three, but it is the one
   remaining place where the published protocol is genuinely ambiguous.

Everything else about the request is now the published protocol byte for byte: the system message is
identical to the one the release's own `format_tools_compact` builds over the same
`tools_registry.csv` (16,143 characters, SHA-256
`be7f31a2e8c7e6dd6a2db8673a54da26051cf2c3914218532521385175ffd8bd`), verified against the clone and
confirmed present verbatim in the rendered prompt.

## What this authorizes

Nothing new. The population is exposed discovery data and no knob was tuned on it. This is not a
superiority, generality or Stage-3 claim.

Mechanism work stays stopped, as the calibration verdict left it. What this flight changes is the
shape of the open question the owner has to decide on:

- The reconstruction is no longer a candidate explanation. It cost ~5.5 pp of tool accuracy, and
  correcting it does not approach the paper.
- Tier 1 is now a *single* anomaly rather than one of eight gaps: seven tiers sit between −12.6 and
  +3.4 pp of the paper, five of them within 8 pp, and Tier 1 sits at −32.4 pp while moving the wrong
  way under the correct protocol.
- The natural next question is whether the paper's Tier-1 row is produced on a population this
  roster does not represent (first-speaker-per-query over every query) or under a candidate tool set
  narrower than all 152. Drawing that roster, or asking the authors, is an owner decision.
