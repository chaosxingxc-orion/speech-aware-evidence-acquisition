# SLURP A1: USE-axis projection audit on sealed outputs

Date: 2026-09-17. Root: Fable 5.1. Program: `docs/superpowers/specs/2026-09-16-slurp-v2-base-program-design.md`
(Phase A, item A1; decides module M3 and cell B3). Zero model, tokenizer, encoder or server
contacts; 42 runs of the pinned official `evaluate.py` (commit 8eb16545) on projected copies of
sealed outputs; repository tree untouched; no utterance text or filler persisted.

Machine result: `analysis/SAEA-SLURP-A1-USE-PROJECTION-AUDIT-V1/result.json` under
`SPEECHRL_DATA_DIR`, SHA-256 457506719d0018913737f10f25c5ad63c6e142effe3f0770bee4fee6bc6467b3,
with `README.md`, `per-scenario.csv`, `per-type.csv`, `illegal-label-headroom.json`,
`p0-row-identity.json` and the driver scripts beside it.

## Inputs and identity

Sealed TRAIN A anchor (SAEA-SLURP-NATIVE-DUAL-STORE-TRAIN-FOLD-A-ANCHOR-RECOVERY-V1), sealed
DEV1000 base-replication agent and direct arms. P0 (no projection) reproduces every sealed
aggregate bit-exactly and 0 mismatches over 3,080 rows x 13 per-sample scoring fields. Paired
whole-speaker bootstrap, 10,000 draws, seed 20260915 (TRAIN A speakers from the released
direct-anchor metadata, DEV1000 from the null-calibration metadata).

## Projections

- P1a / P1b: support filter (drop a predicted entity whose type never / in < 1 % of mentions
  occurs under the delivered intent in TRAIN; 432 (intent, type) bindings over full TRAIN, of
  which the released store's 402 are a strict subset).
- P2: surface normalisation of fillers: lowercase, whitespace collapse, punctuation stripped
  except apostrophes and internal hyphens, meridiem forms to `am` / `pm`, numeric tokens to
  English words. P2t = P2 restricted to date/time types. Rung ablation P2r0 (case + whitespace),
  P2r1 (+ punctuation), P2r2 (+ meridiem), P2 (+ numeric words).
- P5: illegal-intent repair by stripping a duplicated scenario prefix from the action; V2 = the
  registered `slurp-legal-label-projection-v2`.

## Headline (official pooled SLU-F1 %, deltas in pp, CI = paired whole-speaker bootstrap)

| Cohort | Projection | SLU | Delta | CI95 | Span F1 | Intent | Entities dropped / changed | Normalised-scorer delta |
| --- | --- | ---: | ---: | --- | ---: | ---: | --- | ---: |
| TRAIN A | P0 | 48.534 | -- | -- | 29.498 | 77.963 | 0 / 0 | -- |
| TRAIN A | P1a | 48.737 | +0.204 | [-0.230, +0.581] | 29.715 | = | 27 / 0 | +0.27 |
| TRAIN A | P1b | 49.016 | +0.483 | [-0.154, +1.082] | 29.782 | = | 58 / 0 | +0.63 |
| TRAIN A | P2 | 51.995 | +3.461 | [+2.781, +4.180] | 40.303 | = | 0 / 195 | +0.16 |
| TRAIN A | P2t | 50.086 | +1.552 | [+1.060, +2.151] | 34.360 | = | 0 / 61 | +0.16 |
| TRAIN A | P4 (P1b+P2) | 52.620 | +4.086 | [+3.171, +5.047] | 40.937 | = | 58 / 193 | +0.79 |
| TRAIN A | P5 | 48.534 | 0 | -- | 29.498 | 78.611 | 0 / 0 | 0 |
| TRAIN A | V2 | 48.534 | 0 | -- | 29.498 | 78.611 | 0 / 0 | -- |
| DEV1000 agent | P0 | 50.298 | -- | -- | 30.428 | 75.600 | 0 / 0 | -- |
| DEV1000 agent | P1a | 50.147 | -0.152 | [-0.63, +0.31] | 30.176 | = | 31 / 0 | -0.13 |
| DEV1000 agent | P2 | 54.031 | +3.733 | [+3.03, +4.47] | 41.906 | = | 0 / 211 | +0.18 |
| DEV1000 agent | P4 | 53.817 | +3.519 | [+2.62, +4.41] | 41.587 | = | 58 / 204 | -0.03 |
| DEV1000 agent | V2 | 50.298 | 0 | -- | 30.428 | 76.600 | 0 / 0 | -- |
| DEV1000 direct | P0 | 35.675 | -- | -- | 22.191 | 72.300 | 0 / 0 | -- |
| DEV1000 direct | P2 | 36.217 | +0.542 | [+0.31, +0.79] | 24.564 | = | 0 / 43 | 0.00 |
| DEV1000 direct | V2 | 35.675 | 0 | -- | 22.191 | 73.300 | 0 / 0 | -- |

Row-level saves / harms / ties on per-row SLU-F1 under P2: TRAIN A 128 / 3 / 949, DEV1000 agent
133 / 0 / 867, DEV1000 direct 32 / 0 / 968. Under P1a: 5 / 3 / 1,072 and 3 / 11 / 986.

Per scenario, P2 improves or ties every scenario in both cohorts (alarm +12.21 / +10.05,
datetime +13.52 / +7.75, qa +5.20 / +6.11, general 0 / 0, lists 0 / +0.90). Per type, no type
gets worse; `time` alone yields a third of the saving (loss mass 212.7 to 111.8), place_name
-66.5, business_name -35.1, date -32.8; total loss mass 2,324.5 to 2,023.8. Date stays the
largest single loss (FN 203.6 of 253.2): a slot the core never emitted cannot be normalised.

## Mechanical decision

- P2 RECOMMENDED: all six clauses pass (TRAIN A +3.461 >= 1.0 with CI95 lower bound +2.781;
  DEV1000 same sign; no scenario loses; intent unchanged; normalised scorer same sign).
- P1a, P1b, P3, P4 and their P5 combinations REJECTED: deltas below the bar or CI95 straddling
  zero, DEV1000 negative for the filter, and the scenario clause fails on `cooking` (-2.31 to
  -2.58) and `recommendation` (-3.13); the support filter deletes gold-present entities whose
  type is unattested under the delivered intent.
- P5 cannot move SLU by construction (the official entity block ignores the label) and is read
  on intent: it repairs 10 of the 20 illegal rows (7 to gold, 77.963 to 78.611), the same as V2;
  V2 also reaches 76.600 on DEV1000 agent and 73.300 on the direct twin (42 illegal rows there),
  so P5 adds nothing over V2.

## Two findings that bound the interpretation

1. About three quarters of P2's official gain is case: the official `evaluate.py` lower-cases
   the gold filler and not the prediction. Rung P2r0 alone gives +2.347 (TRAIN A) and +2.860
   (DEV1000) official, and exactly 0.00 under the symmetric `slurp-slu-f1-normalized-v1`; only
   the numeric-word rung is a spoken-convention repair (+0.16 / +0.18 symmetric). Published SLURP
   systems emit lowercase spoken text, so applying P2 to our outputs aligns our representation
   with the dataset convention rather than adding capability; it must be reported as such, and
   the SLU-F1 >= 64 bar is not to be read as approached by representation alignment. Under P2
   the system-versus-direct gap on DEV1000 widens from 14.62 to 17.81 pp because the agent
   arm's surface convention is the worse of the two.
2. The measured headroom of the illegal-label repair is 15 of 20 rows: rule R_action, "when the
   delivered action string is itself a legal composed intent id, adopt that id's own split",
   lands 15 of 20 on gold on TRAIN A (+1.389 pp intent, 79.352) and 12 on DEV1000, whereas V2's
   edit-distance branch mis-repairs this class (music_play_music -> music_likeness x9). R_action
   was identified against gold after the fact; it is a diagnostic ceiling that E4 preregisters
   as v3's first label rule ahead of the V2 fallback, to be confirmed prospectively.

## Consequences for the program (module M3, cell B3)

Projection v3 = (a) label rule R_action then the registered legal-label projection v2 as the
fallback, (b) filler normalisation P2 (all four rungs), no support filter. It is registered both
as the scorer-side `slurp-slu-official-projected-v3[-train]` and as the runtime commit judge that
applies the same function to delivered answers, so later cells deliver normalised, legal outputs
and the scorer-side projection is a no-op on them. Every verdict that cites v3 reports the
official number, the symmetric normalised number and the rung decomposition beside each other.
Date omission remains an M1 / M4b problem.
