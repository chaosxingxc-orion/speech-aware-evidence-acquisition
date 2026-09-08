# REJECTED — KC-E1f, the Earnings-21 pre-meeting brief as a second-pass entity repair

The preregistration's own word for this outcome is **HARMFUL**: its rule says "HARMFUL if any guard
fails", and two guards fail. The primary is met on both legs and met comfortably — the repair pass
takes PERSON entity WER from 22.489 % to 18.752 %, with a call-clustered CI90 lower bound of +2.653
percentage points against the sealed comparator and +2.752 against its own token-matched twin — and
**the guard that rejected KC-E1 now passes in this cell's favour**: corpus WER *improves* by 0.045 pp
with a CI90 that excludes zero. The two guards that fail are **numeric-value accuracy (call-pooled)**
and **over-generation**, and they fail on differences of **one matched value in 9,734** and **one
insertion in 10,700**, because both guards are written as "the CI90 must exclude zero on the good
side" with no non-inferiority margin, which is a superiority test wearing a guard's clothes. That is
the rule this cell was registered under, it was fixed before any result existed, and it is applied
here as written.

Decides exposure row `SAEA-E21-KC-E1F-REPAIR-44-V1` under
`docs/readiness/2026-09-07-e21-kc-e1f-brief-repair-pass-v1-preregistration.md` §5. This verdict's own
row is `SAEA-E21-KC-E1F-VERDICT-V1` (`model-free-check`), registered and committed before the first
sealed byte was opened; **zero model, GPU, tool, embedder, tokenizer, network, audio-decode and
paid-API contacts**. Receipt:
`docs/checks/speech-aware-evidence-acquisition/2026-09-08-e21-kc-e1f-verdict/`.

---

## 1. The rule, quoted before any number

From the preregistration §5, verbatim:

> **ADMITTED** iff, on the reported roster, the **call-clustered CI90 lower bound** on the PERSON
> entity-WER **reduction** — pooled `(S + D) / tagged reference words`, comparator minus KC-E1f, so a
> positive value means fewer errors — is **> 0 against the sealed comparator** AND **> 0 against
> KU-E1fc**, and every guard below holds.
>
> **NULL** if either lower bound includes 0. A NULL with a positive point estimate against the twin
> and a negative one against the comparator is reported as "the form carried it", and the next cell
> is a supply-form question, not a content one.
>
> **HARMFUL** if any guard fails, with the failing guard named and the per-class table published
> either way.

and its guard table, verbatim:

| guard | test | unit |
|---|---|---|
| **delivery integrity** | for every window, the delivered raw text equals the sealed predecessor outside the accepted substitution spans and carries the identical whitespace-token count — a **construction check**, verified from the sealed trace, that **aborts the read** rather than producing a number | window |
| corpus WER non-inferiority | call-clustered CI90 **upper** bound on (KC-E1f − comparator) pooled corpus WER **<= 0** | window rows, call-clustered |
| numeric-value accuracy not worse | CI90 lower bound on (KC-E1f − comparator) accuracy **>= 0**, on the **call-pooled** figure | call |
| over-generation not worse | insertions per reference word against the comparator's 10,700 / 359,765 | window rows, call-clustered |
| negation-critical rate not worse | point estimate with the taxonomy id; **advisory only** | window rows, reported |

The reported roster is **all 44 discovery calls**, the population both cells flew. Pairing unit: the
fixed 90-second window (1,593). Bootstrap cluster: the call (44). Estimator: the pooled ratio,
`sum(numerator) / sum(denominator)` over the resampled units, through
`analysis.paired.resampled_statistic(cluster_of=analysis.e21_window_pairing.call_of)` at seed
**20260903**, **10,000** replicates, **CI90**.

## 2. The verdict, applied line by line

| test | required | measured (call-clustered CI90, natural mixture) | |
|---|---|---|---|
| **primary**, PERSON reduction vs comparator | LB > 0 | **+3.737 pp** [+2.653, +4.855] | **MET** |
| **primary**, PERSON reduction vs KU-E1fc | LB > 0 | **+3.840 pp** [+2.752, +4.958] | **MET** |
| guard, delivery integrity | construction, aborts the read | 1,593 / 1,593 windows, **0 violations**, both arms; §5.1 attribution closed | **PASSES** |
| guard, corpus WER (KC-E1f − comparator) | UB <= 0 | **−0.045 pp** [−0.061, **−0.029**] | **PASSES** |
| guard, numeric accuracy call-pooled (KC-E1f − comparator) | LB >= 0 | **+0.0103 pp** [**−0.0212**, +0.0512] | **FAILS** |
| guard, insertions per reference word (KC-E1f − comparator) | UB <= 0 | **+0.00028 pp** [−0.00199, **+0.00255**] | **FAILS** |
| guard, negation-critical rate | advisory point estimate | 0.0278 % → **0.0275 %** (100 → 99 HIGH reference words), taxonomy `e22-semantic-scan-2026-09-06-content-impact-word-pair-v1` | directionally better, gates nothing |

**Two guards fail, so the rule says HARMFUL and this note says REJECTED.** The failing guards are
named above; the per-class table is §6, published either way, as the rule requires.

The two failures survive no reading, because there is nothing in them to survive. Both are decided by
the *sign of a CI bound on a quantity whose point estimate is not worse*:

* **numeric-value accuracy is BETTER**: 8,833 matched values of 9,734 against the comparator's 8,832,
  a call-pooled 90.744 % against 90.730 %. Exactly **two of the 44 calls move at all** — `4346923` by
  −1 and `4367535` by +2 — so a 44-cluster bootstrap straddles zero and the lower bound lands at
  −0.0212 pp. The guard as written demands the arm be *significantly better* on numeric accuracy to
  count as "not worse";
* **over-generation is worse by one insertion**: 10,701 against 10,700 over 359,765 reference words.
  It fails the CI reading (upper bound +0.00255 pp) and it also fails the plain point reading of the
  guard's own words ("insertions per reference word against the comparator's 10,700 / 359,765"),
  because 10,701 > 10,700. **There is no reading of this guard that this cell passes**, and none is
  offered.

And §4 proves what that one insertion **is**: not a word the model emitted, but a substituted span
that normalizes to one more word than the span it replaced. In raw whitespace-token space the
delivered hypothesis carries the comparator's own token count on **every one of 1,593 windows**, so
this arm cannot over-generate by construction. The guard is measuring a normalization delta, and the
preregistration's §5.1 exists precisely because that was foreseen — but §5.1 requires the delta to be
*attributed*, not *forgiven*, and the guard table sets no margin. Under the rule as written, the cell
is rejected.

## 3. The identity anchor, first and refusable

No contrast was computed until each arm's 1,593 per-window rows re-aggregated to that arm's own
sealed numbers exactly, through the fixed window-pairing instrument (`analysis.e21_window_pairing`,
whose `obs_delivered_text` branch reads the **delivered** post-processed span rather than the raw
pass-2 answer; runner `scripts/e21_window_pairing_read.py`, one committed sealed profile per run).
The runner exits non-zero on any mismatch and the verdict script refuses an arm whose anchor is not
`PASS`.

| arm | run id | attempt | checks | corpus WER, per-window sum | sealed | S / D / I |
|---|---|---|---|---|---|---|
| comparator | `SAEA-E21-FULL44-DIRECT-BASELINE-V2` | `attempt-20260904T233816Z-bcd338` | 30/30 **PASS** | **8.1995 %** | 8.200 % | 13,098 / 5,701 / 10,700 |
| form twin | `SAEA-E21-KU-E1FC-PLACEBO-REPAIR-44-V1` | `attempt-20260908T072231Z-ec8a5b` | 30/30 **PASS** | **8.2015 %** | 8.201 % | 13,105 / 5,699 / 10,702 |
| treatment | `SAEA-E21-KC-E1F-REPAIR-44-V1` | `attempt-20260908T040832Z-ecda9c` | 30/30 **PASS** | **8.1545 %** | 8.154 % | 12,936 / 5,700 / 10,701 |

All three over 359,765 reference words, 1,593 windows, 44 calls, split identity `fcc1b0bc…d69e`. The
comparator is not only the comparator here — **it is both treated arms' pass 1**, the bytes they
edited, bound through the content-free snapshot receipt
`docs/receipts/e21-predecessor-full44-direct-baseline-v2.json` (sha256 `26f1d9cc…a72a`).

**The class anchor is widened past the eight published classes.** The per-window rows now carry every
key of the ConEC mirror's own `by_entity_type` — 26 typed classes plus `__NON_ENTITY__`,
`__UNLABELLED__` and `__UNTYPED__` — and each arm's per-window sums are checked against that arm's own
committed score receipt, class by class, on `(substitutions, deletions, reference words)`: **87 of 87
checks PASS**, so no column of §6 is unanchored.

## 4. The §5.1 attribution — the whole normalized move sits on substituted spans

§5.1 makes one obligation and makes it refusable: the delivery guarantee is exact in **raw**
whitespace-token space, the scored numbers are **normalized**, and "a deletion or insertion delta that
cannot be attributed to a substituted span is a defect report, not a result, and aborts the read".
`scripts/e21_kc_e1f_normalization_attribution.py` discharges it, and it ran **before** any contrast.

**The identity that makes the attribution exact.** For any alignment, `|hyp| = S + I + H` and
`|ref| = S + D + H`, so `I − D = |hyp| − |ref|`. The reference bytes are identical in all three arms,
so an arm's `(I − D)` move against the comparator **is** its normalized hypothesis-length move, digit
for digit. Attributing the length move attributes the deletion/insertion move itself.

| | KC-E1f | KU-E1fc |
|---|---:|---:|
| raw whitespace tokens, both sides | 372,488 | 372,488 |
| differing raw positions (= the flight's own count) | 2,545 | 2,154 |
| maximal substituted spans | 1,890 | 1,528 |
| normalized hypothesis words, comparator → arm | 364,764 → **364,766** | 364,764 → **364,768** |
| normalized-word delta | **+2** | **+4** |
| `(I − D)` delta, re-derived from the anchors | **+2** | **+4** |
| delta carried by substituted spans and their ±8-token normalization boundary | **+2 (100 %)** | **+4 (100 %)** |
| interior raw tokens (more than 8 tokens from any substitution) | 342,028 | 346,820 |
| interior segments whose contribution moved | **0** | **0** |
| spans carrying a non-zero normalization delta | 28 | 14 |
| windows whose normalized length moved | 22 | 10 |
| of those, windows carrying no substituted span | **0** | **0** |

Four independent checks close it, all `PASS`, all in `result-summary.json` under
`attribution_checks`:

1. the `(I − D)` identity above, at the corpus;
2. **the same identity per call**, on **44 of 44 calls** for both arms — so the corpus match cannot be
   two errors cancelling;
3. the attribution's own normalized word counts (364,764 / 364,766 / 364,768) equal each arm's **own
   sealed scorer's** `hypothesis_words`, exactly;
4. the raw-space construction guarantee: identical whitespace-token counts call by call and window by
   window, 0 violations on 1,593 windows in both arms, with the differing-position counts equal to the
   flights' own.

The 28 moving spans are what the mechanism predicted: a substituted surface form that the Whisper
normalizer splits or merges differently from the one it replaced. Their content-free shapes are in the
receipt (`spans_with_a_non_zero_delta`): 13 spans move by +1 word, 9 by −1, 2 by +2, 2 by −2 and 2
by −3; three of them replace a purely alphabetic span with a digit-bearing one, and none goes the
other way. **No hypothesis character enters Git**, exactly as the predecessor binding is content-free; the full span table lives beside the
per-window rows under `SPEECHRL_DATA_DIR` and its SHA-256 is pinned in the receipt.

**The operation-level counterpart, and the PERSON deletions.** The flight receipt asked the verdict to
attribute PERSON deletions **80** against the comparator's **83** rather than count them as recovered
words (§9 item 1: this mechanism cannot repair a deletion). It is attributed:

* **five windows** carry a PERSON deletion move, four of them 1 → 0 and one 0 → 1, net **−3**;
* **every one of the five carries accepted substitutions** (3, 1, 3, 4 and 1 spans respectively);
* across **all 29 class buckets and both treated arms**, the number of windows whose per-class
  deletion count moved *without* carrying a substituted span is **zero**.

A PERSON deletion became a substitution or a hit because a substituted span nearby normalized to one
more word and re-seated the alignment — the extra hypothesis word gave the reference position
something to align to. Not a recovered name; a re-seated cursor. The floor §5.3 named,
`83 / 2917 = 2.846 %`, still stands as the floor.

## 5. The three-way reading

`delta = right − left`; the column below is the **improvement**, re-signed so a positive number always
means the right-hand arm is better. Call-clustered CI90, natural mixture, 10,000 replicates, seed
20260903.

| | total (comparator → KC-E1f) | form (comparator → KU-E1fc) | content (KU-E1fc → KC-E1f) |
|---|---|---|---|
| **PERSON entity WER** | **+3.737** [+2.653, +4.855] | −0.103 [−0.238, −0.000] | **+3.840** [+2.752, +4.958] |
| ORG entity WER | +0.711 [+0.068, +1.475] | +0.160 [−0.023, +0.366] | +0.550 [−0.067, +1.257] |
| corpus WER | **+0.045** [+0.029, +0.061] | −0.002 [−0.006, +0.002] | **+0.047** [+0.031, +0.063] |
| non-entity WER | +0.002 [−0.003, +0.007] | −0.003 [−0.007, −0.000] | +0.005 [−0.001, +0.011] |
| unlabelled WER | −0.000 [−0.000, −0.000] | −0.068 [−0.204, −0.000] | +0.068 [−0.000, +0.204] |
| numeric accuracy, call-pooled | +0.010 [−0.021, +0.051] | −0.021 [−0.046, +0.000] | +0.031 [+0.000, +0.073] |
| numeric accuracy, window-pooled (diagnostic) | +0.000 [−0.039, +0.043] | −0.031 [−0.061, −0.009] | +0.031 [+0.000, +0.073] |
| insertions per reference word | −0.000 [−0.003, +0.002] | −0.001 [−0.002, +0.001] | +0.000 [−0.002, +0.002] |
| negation-critical rate | +0.000 [−0.000, +0.001] | −0.000 [−0.000, −0.000] | +0.000 [−0.000, +0.001] |

**The content is doing all of the work, again, and this time the form does nothing at all.** KU-E1fc —
the same second contact, the same instruction, the same frame, the same sealed pass 1, the same
substitution-only delivery rule, +7 rendered tokens and no entity strings — moves PERSON entity WER by
**−0.103 pp**, an interval whose upper bound touches zero, and corpus WER by −0.002 pp with a CI that
straddles zero. The content effect (**+3.840**) is therefore again **larger** than the total effect
(+3.737), exactly as in KC-E1. The form effect is not a robust finding in either direction: its
call-clustered upper bound is **zero to the last digit** (−0.000 natural, +0.000 equal-stratum) and
the window-level reading straddles zero outright.

**And the placebo is not a do-nothing arm**: it proposed and had accepted **2,125 substitutions on
1,023 windows**, against the arm's 2,427 on 1,064. It edited a comparable number of tokens and bought
nothing with them. That is the cleanest statement this pair makes: *the repair form is a channel, and
only the brief's content flows through it.*

## 6. The per-class table, published either way

Pooled `(S + D) / tagged reference words`; insertions are unattributable by the mirror's own
definition and reach only the `__ALL__` bucket. Reference-word counts are identical in all three arms.
Every class the scorer reports is here, not a chosen subset.

| class | ref words | comparator % | KU-E1fc % | KC-E1f % | KC-E1f S / D | contrast vs comparator, CI90 |
|---|---:|---:|---:|---:|---|---|
| **PERSON** | 2,917 | **22.489** | 22.592 | **18.752** | 467 / 80 | **+3.737 [+2.653, +4.855]** |
| **ORG** | 4,363 | 17.213 | 17.052 | **16.502** | 650 / 70 | **+0.711 [+0.068, +1.475]** |
| GPE | 1,537 | 18.673 | 18.608 | 17.957 | 247 / 29 | +0.716 [−0.062, +1.723] |
| LOC | 485 | 2.474 | 2.474 | 2.680 | 12 / 1 | −0.206 [−0.566, −0.000] |
| PRODUCT | 390 | 19.231 | 19.231 | 18.718 | 61 / 12 | +0.513 [−0.000, +1.158] |
| EVENT | 494 | 2.429 | 2.429 | 2.429 | 10 / 2 | −0.000 [−0.000, −0.000] |
| NORP | 236 | 9.746 | 9.746 | 9.746 | 17 / 6 | −0.000 [−1.081, +1.015] |
| FAC | 122 | 21.311 | 21.311 | 20.492 | 19 / 6 | +0.820 [−3.530, +4.959] |
| ABBREVIATION | 2,566 | 25.682 | 25.526 | 25.682 | 617 / 42 | −0.000 [−0.319, +0.380] |
| ALPHANUMERIC | 1,921 | 8.902 | 8.902 | 8.798 | 107 / 62 | +0.104 [−0.000, +0.270] |
| CARDINAL | 4,463 | 11.002 | 11.046 | 11.024 | 367 / 125 | −0.022 [−0.065, −0.000] |
| CONTRACTION | 17,667 | 4.828 | 4.828 | 4.828 | 417 / 436 | −0.000 [−0.000, −0.000] |
| DATE | 16,166 | 3.470 | 3.483 | 3.470 | 417 / 144 | −0.000 [−0.000, −0.000] |
| FALLBACK | 78 | 47.436 | 47.436 | 47.436 | 18 / 19 | −0.000 [−0.000, −0.000] |
| LANGUAGE | 2 | 50.000 | 50.000 | 50.000 | 1 / 0 | −0.000 |
| LAW | 62 | 3.226 | 3.226 | 3.226 | 2 / 0 | −0.000 |
| MONEY | 732 | 12.842 | 12.842 | 12.842 | 74 / 20 | −0.000 [−0.000, −0.000] |
| ORDINAL | 925 | 2.919 | 2.919 | 2.919 | 19 / 8 | −0.000 [−0.000, −0.000] |
| PERCENT | 1,868 | 10.171 | 10.171 | 10.171 | 169 / 21 | −0.000 [−0.000, −0.000] |
| QUANTITY | 327 | 6.422 | 6.422 | 6.422 | 19 / 2 | −0.000 [−0.000, −0.000] |
| RANGE | 24 | 50.000 | 50.000 | 50.000 | 11 / 1 | −0.000 |
| TIME | 721 | 3.745 | 3.745 | 3.745 | 14 / 13 | −0.000 [−0.000, −0.000] |
| TWITTER | 2 | 0.000 | 0.000 | 0.000 | 0 / 0 | −0.000 |
| WEBSITE | 120 | 10.833 | 10.833 | 10.000 | 12 / 0 | +0.833 [−0.000, +2.679] |
| WORK_OF_ART | 82 | 14.634 | 14.634 | 13.415 | 10 / 1 | +1.220 [−0.000, +4.348] |
| YEAR | 1,180 | 19.492 | 19.576 | 19.492 | 206 / 24 | −0.000 [−0.000, −0.000] |
| `__NON_ENTITY__` | 304,331 | 4.730 | 4.734 | 4.729 | 9,686 / 4,705 | +0.002 [−0.003, +0.007] |
| `__UNLABELLED__` | 1,479 | 12.847 | 12.914 | 12.847 | 179 / 11 | −0.000 [−0.000, −0.000] |
| `__UNTYPED__` | 2 | 0.000 | 0.000 | 0.000 | 0 / 0 | −0.000 |
| `__ALL__` (corpus WER) | 359,765 | 8.200 | 8.201 | **8.154** | 12,936 / 5,700 / I 10,701 | **+0.045 [+0.029, +0.061]** |

**Seventeen of the twenty-nine buckets do not move by a single operation.** Exactly twelve move —
PERSON, ORG, GPE, LOC, PRODUCT, FAC, ABBREVIATION, ALPHANUMERIC, CARDINAL, WEBSITE, WORK_OF_ART and
`__NON_ENTITY__` — and the other seventeen, `__UNLABELLED__` and `__UNTYPED__` among them, carry the
comparator's own substitution and deletion counts to the unit. (For the twin the figure is twenty
unmoved of twenty-nine.) That is what a substitution-only delivery over a sealed transcript looks
like when it works.

Beside the published rows this family reports against
(`docs/readiness/2026-09-06-earnings-agentic-metric-baseline-v1.md` §3): ConEC Table 2 row 8
(Whisper-large, no biasing) **28.9**, row 1 (their in-domain no-biasing condition) **45.9**, row 5 (the
post-hoc oracle) **13.0**. **PERSON 18.752 sits 39 % of the way from the comparator's 22.489 to the
oracle's 13.0**, and KC-E1's whole-prompt supply reached 18.341 — so the repair form recovered
**90 % of KC-E1's entity gain while the transcript improved instead of collapsing**. That comparison
is a cross-cell reading, reported and never ruled on here.

## 7. The mechanism, both ledgers side by side

Published whatever the outcome, from each flight's own receipt.

| | KC-E1f | KU-E1fc |
|---|---:|---:|
| windows | 1,593 | 1,593 |
| changed (≥ 1 accepted substitution) | **1,064** | **1,023** |
| delivered unchanged without a refusal | 447 | 498 |
| refused | 82 | 72 |
| — `anchor_ratio_below_floor` | 75 | 67 |
| — `empty_response` | 3 | 2 |
| — `substituted_fraction_above_ceiling` | 4 | 3 |
| — `empty_predecessor` | 0 | 0 |
| accepted substitutions | **2,427** | **2,125** |
| substituted tokens applied | 2,545 | 2,154 |
| would-be tokens never applied (ceiling refusals) | 91 | 6 |
| rejected `unbalanced_replace` | 654 | 658 |
| rejected `deletion` | 331 | 337 |
| rejected `insertion` | 104 | 125 |
| rejected `oversized_replace` | 4 | 3 |
| anchor ratio min / median / max (floor 0.60) | 0.000 / 0.992 / 1.000 | 0.000 / 0.992 / 1.000 |

And what the guarantee bought, in operations against the comparator:

| | comparator | KU-E1fc | KC-E1f | KC-E1f − comparator |
|---|---:|---:|---:|---:|
| substitutions | 13,098 | 13,105 | 12,936 | **−162** |
| deletions | 5,701 | 5,699 | 5,700 | **−1** |
| insertions | 10,700 | 10,702 | 10,701 | **+1** |
| errors | 29,499 | 29,506 | 29,337 | −162 |

Set that beside KC-E1's own row — substitutions −76, deletions **+2,692**, insertions −686 — and the
trade this cell exists to make is visible in one line: **the deletion column does not move.** The
delivery rule rejected 331 deletions and 104 insertions the model proposed; that is exactly where
KC-E1's 2,242 extra non-entity deletions would have come from.

## 8. The saturation covariate, and both sensitivities

| arm | saturated windows | calls |
|---|---:|---|
| comparator | 0 | — |
| KC-E1f | 3 | `4365948` (`#w0002`), `4383161` (`#w0012`, `#w0022`) |
| KU-E1fc | 2 | `4346923` (`#w0011`, `#w0039`) |

**Here the repair form differs from KC-E1 by construction, and the rows prove it.** A saturated pass-2
decode reaches `core.repair_alignment` as the empty string, is refused as `empty_response` and
**delivers pass 1** — so each of these five windows carries the comparator's own transcript, its full
reference-word charge (250 / 235 / 246 and 230 / 194 words) and **zero substituted spans**. KC-E1's two
saturated windows contributed the empty string and were charged nothing at all. The covariate is still
named and still carried:

| sensitivity | n | PERSON reduction vs comparator | corpus WER improvement | insertions/ref word |
|---|---|---|---|---|
| primary, all windows | 1,593 / 44 | +3.737 [+2.653, +4.855] | +0.045 [+0.029, +0.061] | −0.000 [−0.003, +0.002] |
| the five saturated **windows** excluded from all three arms | 1,588 / 44 | +3.743 [+2.657, +4.864] | +0.045 [+0.029, +0.062] | −0.000 [−0.003, +0.002] |
| the three saturated **calls** excluded from all three arms | 1,474 / 41 | +3.752 [+2.616, +4.911] | +0.046 [+0.031, +0.064] | +0.001 [−0.001, +0.003] |

**No exclusion changes anything.** Unlike KC-E1, where a third of the corpus-WER cost sat in the
saturated calls, here the covariate is inert — which is what a mechanism that delivers pass 1 on a
saturated decode should look like.

## 9. Both weightings, and the descriptive window layer

| contrast, metric | natural mixture | equal stratum (per call) | window-level (OPTIMISTIC) |
|---|---|---|---|
| total, PERSON | +3.737 [+2.653, +4.855] | +3.700 [+2.501, +4.925] | +3.737 [+2.839, +4.639] |
| total, corpus WER | +0.045 [+0.029, +0.061] | +0.046 [+0.028, +0.064] | +0.045 [+0.033, +0.057] |
| content, PERSON | +3.840 [+2.752, +4.958] | +3.781 [+2.576, +5.008] | +3.840 [+2.935, +4.759] |
| form, PERSON | −0.103 [−0.238, −0.000] | −0.082 [−0.180, +0.000] | −0.103 [−0.266, +0.034] |

The window-level column treats 1,593 units as independent, which they are not; it is carried because
§5 asks for it and it decides nothing. Note that the form effect's interval **touches or includes zero
under all three readings** — the twin's small apparent PERSON cost is not a robust finding, and this
note does not claim one.

Saves / harms / ties and the exact two-sided sign test at the window unit, from
`analysis.paired.paired_contrast` (whose own bootstrap is the mean of per-window differences and is
**not** the decision interval):

| contrast, metric | n | saves | harms | ties | sign test p |
|---|---:|---:|---:|---:|---:|
| total, PERSON | 1,593 (928 carry PERSON reference words) | 101 | 27 | 1,465 | 2.99e-11 |
| total, corpus WER | 1,593 | 161 | 57 | 1,375 | 1.12e-12 |
| form, PERSON | 1,593 | 1 | 3 | 1,589 | 6.25e-01 |
| form, corpus WER | 1,593 | 22 | 24 | 1,547 | 8.83e-01 |
| content, PERSON | 1,593 | 104 | 28 | 1,461 | 1.77e-11 |
| content, corpus WER | 1,593 | 172 | 62 | 1,359 | 3.79e-13 |

**The form twin ties on 1,589 of 1,593 windows for PERSON and on 1,547 for corpus WER.** Per call:
PERSON entity WER improves on **31 of 44** calls, worsens on 7, ties on 6; corpus WER improves on 29,
worsens on 9, ties on 6. The full 44-row table is
`docs/checks/speech-aware-evidence-acquisition/2026-09-08-e21-kc-e1f-verdict/per-call-table.md`, which
also carries each call's accepted-substitution count from both flights.

## 10. The E5 halves, reported apart

| roster | calls | windows | corpus WER: comparator / KU-E1fc / KC-E1f | PERSON: comparator / KU-E1fc / KC-E1f | ORG: comparator / KU-E1fc / KC-E1f |
|---|---:|---:|---|---|---|
| construction 34 | 34 | 1,251 | 8.470 / 8.475 / **8.432** | 23.469 / 23.598 / **19.543** | 16.007 / 15.978 / **15.774** |
| evaluation 10 | 10 | 342 | 7.185 / 7.176 / **7.113** | 18.698 / 18.698 / **15.693** | 21.683 / 21.036 / **19.202** |

**No interval is quoted on the evaluation ten and none should be.** 342 paired windows is below the
program's `n >= 400` rule for an effectiveness claim, and 10 clusters is a thin bootstrap. The ten's
column is descriptive: PERSON 18.698 → 15.693 with corpus WER *improving* by 0.072 pp, and the twin
landing on the comparator's PERSON figure to three decimals.

## 11. The token covariate, throughput and cost of both cells

The twin was matched to the arm on the flight tokenizer, and this pair measured it on **the requests
that actually flew** rather than on a projection: joining each cell's `COST` record to its `OBS` record
through the shared request id gives a delta of **exactly +7 tokens on 1,593 of 1,593 windows** —
min = median = max = 7, one single value in the whole distribution — the constant `[evidence <id>] `
header residual KU-E1c already documented, not a content difference.

| | comparator | KC-E1f | KU-E1fc |
|---|---:|---:|---:|
| prompt tokens | 1,935,965 | **3,550,695** (+83.4 %) | 3,561,846 (= arm + 1,593 × 7) |
| completion tokens | 439,532 | **434,219** (−1.2 %) | 439,049 |
| worst realized request / slot | — | 3,504 / 9,216 (margin 2.630) | 3,511 / 9,216 (margin 2.625) |
| GPU hours (manifest nvidia-smi sampler) | 0.9734 | **1.1093** | **1.1656** |
| GPU hours (session monitor wall clock) | — | 1.7358 | 1.7639 |
| run wall | — | 6,249 s (104.15 min) | 6,350 s (105.83 min) |
| windows per minute | 16.38 (np6) | 15.295 (np4) | 15.052 (np4) |
| realized realtime factor | — | 35.40× | 33.68× |

Both cells held the registered 1.2 GPU-h ceiling by the manifest's own sampler, at four slots where
the registration said in advance it might not. The pair cost **2.2749 GPU-h** by that convention
against a registered 2.4; paid API spend 0, unchanged. Both conventions are published and neither is
blended. The windows-per-minute comparison against the comparator and KC-E1 carries a serving change
(np6 → np4) as well as a protocol one.

## 12. What this cell cannot conclude

1. **It cannot repair a deletion, by construction — so the comparator's PERSON deletions stay.** The
   delivery rule admits substitutions only; the reachable PERSON floor is `83 / 2917 = 2.846 %` and
   the three-deletion move to 80 is a normalization re-seating (§4), not three recovered words.
2. **It cannot say the brief is better consumed this way in general.** One carrier, one frozen core at
   Q4_K_M on build `04ccc72a`, one 90-second OBS tiling, greedy, 44 discovery calls. No superiority,
   no generality, no Stage-3 claim; `paper-scale-confirmatory` is neither available to this repository
   nor requested.
3. **No evaluation claim.** 34 of the 44 calls are the kb-construction half; the evaluation ten carry
   342 paired windows, below the `n >= 400` rule, and are reported apart and descriptively in §10.
4. **It cannot separate the roster half of the brief from the candidate half.** Both are supplied
   together in every window; §6's table is a class split, not an evidence-source split.
5. **It cannot say WHY a substitution was made or refused.** §7 counts refusals by reason and
   rejections by class; no instrument here reads the model's reason for proposing an edit.
6. **It cannot attribute a gain to the audio versus the brief.** Pass 2 sees both. A brief-only
   variant (repair with no audio) would separate them and is a different cell.
7. **A small share of every difference is decode noise.** Greedy decoding on llama-server is not
   bitwise reproducible across batch compositions, and the two arms flew as two separate passes; the
   sealed verdict's own build-and-audio-path noise on corpus WER was 0.05 points. The delivery rule
   damps this — a noisy pass-2 answer is refused, not delivered — but it does not remove it. **Both
   failing guards sit far inside that noise floor**, which is a statement about the guards, not a
   licence to re-read them.
8. **`fixed-legal-context` records provenance tier `UNVERIFIED`** with a GRANDFATHERED declaration
   warning in both flights' manifests. A property of the arm, carried rather than discovered.
9. **Nothing about the whole brief.** Cap 12 is what KC-E1 flew and what this cell reuses so the
   knowledge is identical; §7.1 of the preregistration shows the slot cannot afford more here.
10. **Nothing about KC-E1.** The consumption-form comparison in §6 is a cross-cell reading of two
    separately preregistered cells and is reported, never ruled on.

**The candidate freeze may cite nothing from this cell.** A rejected cell contributes no admitted
effect, and the PERSON reduction reported here must not be quoted as one.

## 13. One named next step — named, not built

**The guard specification is what rejected this cell, and no successor in this family can be admitted
until it is fixed. The next step is therefore a preregistration, not a mechanism: restate every "not
worse" guard as a non-inferiority test with a margin fixed in advance.**

As written, "numeric-value accuracy not worse" (`LB >= 0`) and "over-generation not worse"
(`UB <= 0`) can be passed only by an arm that is *significantly better* on those metrics. Any arm that
changes a single byte of a 359,765-word transcript will move some count by ±1 and fail them. KC-E1
passed both only because it was dramatically better on one and dramatically worse on the other; a cell
whose whole design is "change almost nothing" cannot pass a guard that requires a significant
improvement.

The successor preregistration must state a margin `δ` for each such guard (`UB <= +δ`, `LB >= −δ`) and
must derive `δ` from a source that **predates this contrast** — the family's own sealed
build-and-audio-path decode noise (0.05 corpus-WER points), and for the count metrics the sealed
pair-level variability that the tail2s and KC-E1 receipts already publish. **A margin chosen after
seeing this result would be a retrofit, and this note does not choose one.** Whether the same sealed
pair may then be re-decided under the new rule, or whether a re-decision requires a fresh flight, is an
owner's sequencing call and not an analyst's; it needs its own owner GO and its own row.

Everything else this pair suggests — reaching the 83 PERSON deletions, a brief-only repair with no
audio, a third pass — is a new mechanism and belongs behind that fix, because until the guards can be
passed by an arm that does no harm, admitting one is impossible by construction.

## 14. Files

| file | what it holds |
|---|---|
| `docs/checks/…/2026-09-08-e21-kc-e1f-verdict/result-summary.json` | every number in this note: the decision block, the three identity anchors, the 87-check class anchor, the §5.1 attribution and its four checks, the operation-delta localization, the three contrasts over 34 metrics under three interval readings, both saturation sensitivities, the descriptive window layer, the 44-row per-call block, the E5 halves, the mechanism ledgers and the token covariate |
| `…/per-call-table.md` | the 44 calls, corpus WER and PERSON entity WER in all three arms, with each cell's accepted-substitution and saturated-window counts |
| `…/token-throughput-covariate.json` | the measured +7-token match, both flights' token, cost, throughput and serving-monitor blocks, with each receipt's SHA-256 |
| `…/reaggregation/{comparator,kc-e1f,ku-e1fc}/reaggregation.json` | the identity anchor of each arm — every check, the pooled buckets, the per-call numeric rows |
| `…/attribution/{kc-e1f,ku-e1fc}/attribution.json` | the §5.1 receipt: the construction checks, the `(I − D)` identity, the interior-zero proof, every span that carries a non-zero normalization delta, and the per-call table |
| `…/MANIFEST.sha256` | the receipt directory's byte manifest |
| `scripts/e21_kc_e1f_verdict_read.py` | the runner |
| `scripts/e21_kc_e1f_normalization_attribution.py` | the §5.1 instrument, which refuses and exits non-zero on an unattributable delta |
| `scripts/e21_window_pairing_read.py` | gained both cells' sealed profiles and the full ConEC class column set |

Per-window rows for the three arms and the full span tables live under
`$SPEECHRL_DATA_DIR/runs/SAEA-E21-MF-WINDOW-PAIRING-V1/` — per-request derivatives of sealed model
outputs, so they live where those live and never in Git. Their SHA-256 values are pinned in each arm's
anchor and in each attribution receipt, and re-checked by the verdict runner before a contrast is
computed.
