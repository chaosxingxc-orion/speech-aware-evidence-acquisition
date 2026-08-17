# SAEA-P2-r0bias guard-chain forensics — the 52 rejected replay windows

Read-only analysis, 2026-08-16 evening, from the committed salvage
(`docs/checks/speech-aware-evidence-acquisition/2026-08-16-p2-r0bias-salvage/`), the frozen guard
code (`reproduction/replay_loop.py`), and the gold reference/entity layers read offline
(scoring-side). Ceiling-tier diagnostic material (oracle roster); informs WP3/N1 design, never a
deployment claim. Performed after the P2 block was consumed (`186a228`); r0bias's one-shot read
was already spent — this is secondary analysis of preserved bytes only.

## Headline facts

1. **49 of 53 replay outputs were byte-identical to the delivered reference string.** The bias
   framing did not re-transcribe; it parroted the hint. Token-level confirmation of the D4/P2
   copy findings — no audio adjudication is happening in the replay position.
2. **Of the 52 rejections: 30 FALSE (guard overcaution), 15 CORRECT (13 saved gold hits,
   2 neutral), 5 undetermined, 2 N/A (no call made).** Honest discount: 9 of the 30 "gains" are
   earnings21 gold-annotation artifacts (possessive stripping `SiTime's`→`SiTimes`, inconsistent
   gold spellings `Tribeca`/`Tribecca`), so **21 genuine name recoveries** were lost.
3. **The 3 accepted splices delivered exactly zero gold tokens** and ~4 spurious insertions —
   the chain's net contribution to this arm was negative-to-nil.
4. **Counterfactual ceiling is small**: accepting every false rejection would move corpus
   ASR-WER 12.431%→12.392% (−0.039pp) and entity-WER 34.07%→33.79% (−0.28pp). Compare the
   static-supply oracle arm's −12pp entity-WER: the replay-splice architecture's reachable
   ceiling on this flag set is two orders of magnitude below static supply — the choke point is
   ROUTING (only 55 windows / 23 reachable entity mentions were ever surfaced).

## Rejection taxonomy

| reason | guard/stage | count | FALSE | CORRECT(save) | CORRECT(neutral) | UNDET | N/A |
|---|---|---|---|---|---|---|---|
| no-overlap-words | LOCALIZE (align + midpoint filter) | 33 | **21** | 8 | 2 | 2 | — |
| reference-echo | Guard 2 (D7D) | 16 | **8** | 5 | 0 | 3 | — |
| length-ratio-exceeded | length-ratio (3.0×) | 1 | 1 | 0 | 0 | 0 | — |
| no-candidates | RETRIEVE SKIP gate | 2 | 0 | 0 | 0 | 0 | 2 |
| accepted | — | 3 | (0 net gain, ~4 insertions) | | | | |

## Guard tuning map (for WP3 design)

- **LOCALIZE is the largest loss channel (21 FALSE), and the root cause is upstream, not a
  threshold**: forced alignment of a one-word replay transcript over a ~10s window is
  unreliable; 33 rows returned empty localization. A raw-transcript fallback (when localization
  is empty AND length is within the ratio bound) nets **+13 tokens on this channel alone**
  (+21/−8). Better still: align the reference word against the window with phone-level scoring,
  or shrink `replay_context_s` for single-word spans. Instrumentation gap: carry
  `replay_localize_source` into every future extract so alignment-failure vs midpoint-miss can
  be separated.
- **Guard 2 (reference-echo) is provably NOT fixable by string-distance tuning**: the identical
  `(pass1, ref)` pairs — `sitime/sitimes` (0.143), `tribeca/tribecca` (0.125),
  `livingston/livingstone` (0.091), `china/ching` (0.200) — appear as a genuine fix at one
  occurrence and a hit-corrupting error at another. The discriminator is WHICH occurrence,
  i.e. per-occurrence acoustic support — exactly what LOCALIZE failed to supply. Naive
  loosening yields +8/−5 (net +3), a poor ratio. Levers: per-occurrence acoustic support;
  draft-consistency rules; roster hygiene.
- **Roster/flag hygiene is a prerequisite to any guard retuning**: 25.5% of windows (14/55)
  fired on already-correct spans (pure flag false positives — the sole source of the guards'
  13 saves); 45% of the window budget went to three terms with tiny gold capacity (`SiTimes`
  11 windows/5 slots, `Ching` 9/1, `Tribecca` 5/1); a roster PERSON name fuzzy-matched the
  ordinary word "fastest", passed the 0.1 flag floor, and was accepted. Oracle-roster
  contamination (possessive stripping, inconsistent gold spellings) entered the pack as
  authoritative forms — dedupe/normalization needed in construction (WP1).
- Guards with zero aperture in this arm: Guard 3 (splice-unsupported) 0, replay-text-unchanged
  0, empty-replay-output 0. The SKIP gate's 2 refusals were both correct (hold-music
  boilerplate).

## Transfer to the surviving candidate (targeted legal supply)

The replay path is voided; what transfers: (1) flag/routing quality findings → N1 routing gate
and entity-aware flagging (the 55-window budget, 25% false-positive rate, and monopolization
are routing-stage facts independent of the consumption operator); (2) roster hygiene → WP1
construction ladder; (3) the parroting fact → further confirmation that knowledge must be
introduced for consumption (supply), not adjudication (verify).

Caveats: ceiling-tier oracle material; n=55 windows over 6 samples; window-to-gold mapping via
monotone assignment (5 rows undetermined); 9/30 gains are gold-annotation artifacts.

Full per-row judgment table (55 rows) is preserved in the analysis session transcript; the
numbers above are the load-bearing aggregates.
