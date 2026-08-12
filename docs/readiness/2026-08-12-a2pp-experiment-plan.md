# Experiment plan on baseline A″ (2026-08-12)

Owner sequence: "都lock后就请你打包基线,然后基于最新基线规划具体实验". A″ is locked
(`2026-08-12-hbmfree-baseline-verdict.md`); this plans the science that runs on it.

## What A″ changes about experiment pricing

| Cost driver | old (A′ era) | A″ | consequence |
|---|---|---|---|
| matched-evidence arm, fast-3 | 43.2 min | 20 min | trios in ~1 h |
| matched-evidence arm, sub10 | 132.6 min | ~60 min (est. from 2.2×) | sub10 trio ≈ 3 h |
| WER noise floor | ±3.2 pp mean | 0.11 pp | Δ ≥ 0.5 pp readable at n=3–5 |
| bare WER floor | 0.23 (tail era) | 0.1397 | every prior effect size re-prices |

The 30-min task cap now admits: any fast-3 arm, any fast-3 A/B pair (sequenced), bare
sub10 singles. Sub10 trios are campaign-scale and get owner scheduling.

## E-005 — R4 context-dose, clean re-read (FIRST science on A″)

The reason this is first: the tail-era R4 read (matched 24.36 ≈ mismatched 24.60 ≪
nocontext 27.12 → "context = domain priming") was measured against a floor inflated by
tail poisoning. On the clean floor the probe-B pilot hints the direction may REVERSE:
matched 0.1498 vs bare 0.1397 (+1.0 pp, n=3, discovery hint only). If evidence text no
longer helps — or hurts — once OBS is clean, that reshapes ORG/SUPPLY entirely: the
prior "priming value" may have been compensation for self-poisoned context.

- Arms: `fixed-batch-bare8` (nocontext) / `fixed-batch-matched8` / `fixed-batch-mismatched8`.
- Stage 1 fast-3 trio (~1 h): pre-registered contrasts matched−nocontext,
  mismatched−nocontext, matched−mismatched, read against the 0.11 pp floor.
- Stage 2 sub10 trio (~3 h) only if stage 1 shows |Δ| ≥ 0.5 pp on any contrast.
- Registration: run IDs SAEA-E-005-*; new ledger block; carrier cell names exactly
  `earnings21-original` (I2 lesson, 2026-08-12).

## E-003 — SUPPLY form contrasts (after the E-005 verdict)

E-005 decides what "evidence value" even means on the clean floor; form contrasts
(dose, composition, placement of evidence in SUPPLY) inherit its direction. Candidate
knobs already speced in the validation plan: evidence token budget (now an explicit
SUPPLY knob with the 10,240-slot ceiling), full-pack vs entity-list distillation,
matched-domain vs matched-call granularity.

## Multi-dataset expansion (owner directive: not only E-21/E-22)

1. **E-22 substrate replication** (W-A): bare + matched trio on an earnings22 fast
   subset — same fragments, dataset fragment swap; prices at ~1 h fast trio.
2. **ConEC biasing arms** (W-B): entity-list SUPPLY on the ConEC layer; needs the
   entity-class WER scorer (owner decision item, still open).
3. Cache warmup for each new carrier is one cold pass, then all subsequent arms run
   encoder-free at the A″ rates.

## Wave recalibration of the 24-item validation plan

The 2026-08-11 plan priced items at A′ walls. Re-pricing at A″ (2.2× on evidence arms,
noise floor 30× tighter) moves every fast-split item under the 30-min cap; the plan's
4-wave structure stands, but Wave 0 (substrate checks) is now DONE by the A″ probe
chain (fixed windows, tail=0, slice-parallel, featcache, hbmfree all landed). Wave 1
begins at E-005.

## Standing owner decision items (unchanged, carried forward)

1. carrier lock-profile batch policy; 2. entity-class WER scorer; 3. secondary-carrier
engineering; 4. confirmatory-touch disposition id 4420696; 5. audio2tool id collision
SAEA-E-002→E-006; 6. B-5/D-6 gaps; 7. np16short registered-but-unlaunched row
disposition (recommend: close as not-pursued, rationale in the A″ verdict).
