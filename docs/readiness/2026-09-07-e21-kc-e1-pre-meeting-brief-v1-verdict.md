# REJECTED — KC-E1, the Earnings-21 pre-meeting brief on the whole prompt, capped at 12 entries per class

The preregistration's own word for this outcome is **HARMFUL**: its rule says "HARMFUL if any guard
fails", and two guards fail. The primary is met on both legs and met comfortably — the brief takes
PERSON entity WER from 22.489 % to 18.341 %, with a call-clustered CI90 lower bound of +2.633
percentage points against the sealed comparator and +3.914 against its own token-matched twin — and
the cell is still rejected, because **corpus-WER non-inferiority fails and numeric-value accuracy
fails**. The brief buys entity names with ordinary words: 152 fewer PERSON substitutions, 2,242 more
non-entity deletions.

Decides exposure row `SAEA-E21-KC-E1-BRIEF-44-V1` under
`docs/readiness/2026-09-06-e21-kc-e1-pre-meeting-brief-v2-preregistration.md` §5. This verdict's own
row is `SAEA-E21-KC-E1-VERDICT-V1` (`model-free-check`), registered and committed before the first
sealed byte was opened; **zero model, GPU, tool, embedder, tokenizer, network, audio-decode and
paid-API contacts**. Receipt:
`docs/checks/speech-aware-evidence-acquisition/2026-09-07-e21-kc-e1-verdict/`.

---

## 1. The rule, quoted before any number

From the preregistration §5, verbatim:

> **ADMITTED** iff, on the reported roster, the **call-clustered CI90 lower bound** on the PERSON
> entity-WER **reduction** — pooled `(S + D) / tagged reference words`, comparator minus KC-E1, so a
> positive value means fewer errors — is **> 0 against the sealed comparator** AND **> 0 against
> KU-E1c**, and every guard below holds.
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
| corpus WER non-inferiority | call-clustered CI90 **upper** bound on (KC-E1 − comparator) pooled corpus WER **<= 0** | window rows, call-clustered |
| numeric-value accuracy not worse | CI90 lower bound on (KC-E1 − comparator) accuracy **>= 0**, computed on the **call-pooled** figure | call |
| negation-critical rate not worse | point estimate with the taxonomy id; **advisory only** — 14 HIGH reference words on the evaluation ten cannot gate anything | window rows, reported |
| over-generation not worse | insertions per reference word against the comparator's 10,700 / 359,765; a brief that gets read aloud shows up here first | window rows, call-clustered |

The reported roster is **all 44 discovery calls**, the population the cell flew. Pairing unit: the
fixed 90-second window (1,593). Bootstrap cluster: the call (44). Estimator: the pooled ratio,
`sum(numerator) / sum(denominator)` over the resampled units, through
`analysis.paired.resampled_statistic(cluster_of=analysis.e21_window_pairing.call_of)` at seed
**20260903**, **10,000** replicates, **CI90**.

## 2. The verdict, applied line by line

| test | required | measured (call-clustered CI90, natural mixture) | |
|---|---|---|---|
| **primary**, PERSON reduction vs comparator | LB > 0 | **+4.148 pp** [+2.633, +5.740] | **MET** |
| **primary**, PERSON reduction vs KU-E1c | LB > 0 | **+5.382 pp** [+3.914, +6.989] | **MET** |
| guard, corpus WER (KC-E1 − comparator) | UB <= 0 | **+0.536 pp** [+0.195, +0.917] | **FAILS** |
| guard, numeric accuracy call-pooled (KC-E1 − comparator) | LB >= 0 | **−0.544 pp** [−1.104, −0.041] | **FAILS** |
| guard, insertions per reference word (KC-E1 − comparator) | UB <= 0 | **−0.191 pp** [−0.256, −0.123] | **PASSES** |
| guard, negation-critical rate | advisory point estimate | 0.0278 % → **0.0334 %** (100 → 120 HIGH reference words), taxonomy `e22-semantic-scan-2026-09-06-content-impact-word-pair-v1` | directionally worse, gates nothing |

**Two guards fail, so the rule says HARMFUL and this note says REJECTED.** The failing guards are
named above; the per-class table is §5, published either way, as the rule requires.

The two failures survive every reading the preregistration asks for. Equal-stratum (per call)
weighting: corpus WER +0.489 pp [+0.178, +0.832], numeric −0.571 pp [−1.088, −0.094]. The
window-level interval, which §3 labels the optimistic bound: corpus WER +0.536 pp [+0.255, +0.836].
The saturation sensitivity of §6, which drops the four calls carrying a decode-cap window from all
three arms: corpus WER +0.339 pp [+0.091, +0.619]. **No reading puts the corpus-WER upper bound at
or below zero.**

## 3. The identity anchor, first and refusable

No contrast was computed until each arm's 1,593 per-window rows re-aggregated to that arm's own
sealed numbers exactly, through the fixed window-pairing instrument (`analysis.e21_window_pairing`
with the 2026-09-07 saturation fix; runner `scripts/e21_window_pairing_read.py`, one committed sealed
profile per run). The runner exits non-zero on any mismatch and the verdict script refuses an arm
whose anchor is not `PASS`.

| arm | run id | attempt | checks | corpus WER, per-window sum | sealed | S / D / I |
|---|---|---|---|---|---|---|
| comparator | `SAEA-E21-FULL44-DIRECT-BASELINE-V2` | `attempt-20260904T233816Z-bcd338` | 30/30 **PASS** | **8.1995 %** | 8.200 % | 13,098 / 5,701 / 10,700 |
| form twin | `SAEA-E21-KU-E1C-PLACEBO-44-V1` | `attempt-20260907T200859Z-251383` | 30/30 **PASS** | **8.3538 %** | 8.354 % | 13,254 / 6,460 / 10,340 |
| treatment | `SAEA-E21-KC-E1-BRIEF-44-V1` | `attempt-20260907T171238Z-f02eef` | 30/30 **PASS** | **8.7360 %** | 8.736 % | 13,022 / 8,393 / 10,014 |

All three over 359,765 reference words, 1,593 windows, 44 calls, split identity `fcc1b0bc…d69e`. Every
published ConEC class, the non-entity and unlabelled buckets, the negation-critical counts and the
numeric partition (9,734, exact on all three) reproduce as well. **KU-E1c's sealed artifacts sit at
the run ROOT rather than one attempt level deeper** — the placement deviation its own closure records,
carried here as an `attempt_at_run_root` flag on that run's sealed profile so the attempt id stays in
the receipt.

## 4. The three-way reading

`delta = right − left`; the column below is the **improvement**, re-signed so a positive number always
means the right-hand arm is better. Call-clustered CI90, natural mixture, 10,000 replicates, seed
20260903.

| | total (comparator → KC-E1) | form (comparator → KU-E1c) | content (KU-E1c → KC-E1) |
|---|---|---|---|
| **PERSON entity WER** | **+4.148** [+2.633, +5.740] | **−1.234** [−2.033, −0.484] | **+5.382** [+3.914, +6.989] |
| corpus WER | −0.536 [−0.917, −0.195] | −0.154 [−0.353, +0.038] | −0.382 [−0.742, −0.045] |
| non-entity WER | −0.777 [−1.188, −0.408] | −0.234 [−0.439, −0.036] | −0.543 [−0.914, −0.197] |
| numeric accuracy, call-pooled | −0.544 [−1.104, −0.041] | +0.205 [−0.322, +0.712] | −0.750 [−1.503, −0.101] |
| numeric accuracy, window-pooled (diagnostic) | −0.699 [−1.280, −0.187] | +0.226 [−0.330, +0.765] | −0.925 [−1.705, −0.221] |
| insertions per reference word | +0.191 [+0.123, +0.256] | +0.100 [+0.050, +0.149] | +0.091 [+0.033, +0.148] |
| negation-critical rate | −0.006 [−0.011, −0.000] | −0.003 [−0.006, +0.001] | −0.003 [−0.007, +0.001] |

**The form did not carry it; the form hurt.** KU-E1c — same class labels, same entry count, every
entity token replaced by a neutral placeholder, token-equal to the arm line by line and call by call
— makes PERSON entity WER **worse** by 1.234 pp with a CI90 that excludes zero. The content effect
(+5.382) is therefore **larger** than the total effect (+4.148), and the one factor this pair
isolates is doing all of the work and more. That is the cleanest positive result in this cell and it
is not enough to admit it.

**The corpus-WER cost is also content, not form.** The twin costs 0.154 pp with a CI90 that includes
zero; the brief's own content costs a further 0.382 pp with a CI90 that does not. A long neutral
evidence block is nearly free; a long block of this call's real names and terms is not.

## 5. The per-class table, published either way

Pooled `(S + D) / tagged reference words`; insertions are unattributable by the mirror's own
definition and reach only the `__ALL__` bucket. Reference-word counts are identical in all three arms.

| class | ref words | comparator % | KU-E1c % | KC-E1 % | KC-E1 S / D | contrast vs comparator, CI90 |
|---|---:|---:|---:|---:|---|---|
| **PERSON** | 2,917 | **22.489** | 23.723 | **18.341** | 421 / 114 | **+4.148 [+2.633, +5.740]** |
| ORG | 4,363 | 17.213 | 18.244 | 17.992 | 644 / 141 | −0.779 [−2.530, +0.838] |
| GPE | 1,537 | 18.673 | 19.714 | 19.519 | 250 / 50 | −0.846 [−4.167, +3.041] |
| LOC | 485 | 2.474 | 3.299 | 2.680 | 12 / 1 | −0.206 [−1.104, +0.476] |
| PRODUCT | 390 | 19.231 | 18.205 | 16.667 | 52 / 13 | +2.564 [−0.704, +6.024] |
| EVENT | 494 | 2.429 | 2.429 | 2.429 | 10 / 2 | −0.000 [−0.575, +0.457] |
| NORP | 236 | 9.746 | 9.746 | 11.864 | 22 / 6 | −2.119 [−4.678, −0.000] |
| FAC | 122 | 21.311 | 20.492 | 21.311 | 15 / 11 | −0.000 [−7.865, +6.173] |
| `__NON_ENTITY__` | 304,331 | 4.730 | 4.964 | **5.507** | 9,820 / 6,941 | **−0.777 [−1.188, −0.408]** |
| `__UNLABELLED__` | 1,479 | 12.847 | 14.064 | 13.996 | 188 / 19 | −1.149 [−1.902, −0.425] |
| `__ALL__` (corpus WER) | 359,765 | 8.200 | 8.354 | **8.736** | 13,022 / 8,393 / I 10,014 | −0.536 [−0.917, −0.195] |

Beside the published rows the comparator note already places this arm against (ConEC Table 2 row 8,
Whisper large, no biasing; row 1, the in-domain biasing floor; row 5, the post-hoc oracle ceiling):
**PERSON 18.341 is below row 8's 28.9 and past the halfway mark toward row 5's oracle 13.0**, which is
the single most interesting number this cell produced. FAC, NORP, PRODUCT, LOC and EVENT are thin
(122 to 494 reference words) and directional only, exactly as the comparator note says.

## 6. Where the corpus-WER cost actually is — deletions, and non-entity ones

The three operation counts move in different directions, and only one of them moves against the cell:

| | comparator | KU-E1c | KC-E1 | KC-E1 − comparator |
|---|---:|---:|---:|---:|
| substitutions | 13,098 | 13,254 | 13,022 | **−76** |
| deletions | 5,701 | 6,460 | 8,393 | **+2,692** |
| insertions | 10,700 | 10,340 | 10,014 | **−686** |
| errors | 29,499 | 30,054 | 31,429 | +1,930 |

**The over-generation guard passes because there is no over-generation.** The brief was not read
aloud: insertions FALL by 686 and completion tokens fall from 439,532 to 423,115 (−3.7 %). The cost is
the opposite failure — the model transcribes **less**.

And what it stops transcribing is ordinary speech, not names:

| bucket | comparator S / D | KC-E1 S / D | Δ substitutions | Δ deletions |
|---|---|---|---:|---:|
| `__NON_ENTITY__` | 9,697 / 4,699 | 9,820 / 6,941 | +123 | **+2,242** |
| PERSON | 573 / 83 | 421 / 114 | **−152** | +31 |
| ORG | 680 / 71 | 644 / 141 | −36 | +70 |
| `__UNLABELLED__` | 179 / 11 | 188 / 19 | +9 | +8 |

**83 % of the extra deletion mass is non-entity.** This is the mechanism's actual trade, stated in
counts rather than adjectives: 152 PERSON substitutions repaired, 2,242 ordinary words dropped.

**A Simpson-shaped detail the pooled estimator is right about.** At the window unit KC-E1 has the
LOWER corpus WER on 710 of 1,593 windows against 613 for the comparator (ties 270, exact two-sided
sign test p = 8.28e-03) — a majority of windows improve while the pooled corpus WER gets worse,
because the harms land in the dense windows and the saves in the thin ones. That is exactly the case
§3 of the preregistration ruled the pooled ratio for, and a mean of per-window rates would have
reported the opposite sign.

## 7. The saturation covariate, and both exclusions

`saturated_slice_count` is 2 in each treated arm and 0 in the comparator, on **four disjoint calls**.

| arm | call | window | seconds |
|---|---|---|---|
| KC-E1 | `4360717` | `#w0023` | 1,980–2,070 |
| KC-E1 | `4363614` | `#w0027` | 2,340–2,430 |
| KU-E1c | `4384683` | `#w0015` | 1,260–1,350 |
| KU-E1c | `4397829` | `#w0005` | 360–450 |

`reproduction.obs_loop` quarantines a slice that reaches the 1,024-token decode cap: it contributes
the empty string to the stitched hypothesis and is counted, never scored silently. **Each of the four
windows is therefore charged zero reference words and zero operations** — which is why the
window-level exclusion the preregistration names is nearly vacuous here: the untranscribed reference
mass has already landed on the neighbouring window's deletion cursor, and dropping the window cannot
take it back. Both exclusions are reported rather than the flattering one:

| sensitivity | n | PERSON reduction vs comparator | corpus WER (KC-E1 − comparator) |
|---|---|---|---|
| primary, all windows | 1,593 windows / 44 calls | +4.148 [+2.633, +5.740] | +0.536 [+0.195, +0.917] |
| the four saturated **windows** excluded from all three arms | 1,589 / 44 | +4.214 [+2.688, +5.832] | +0.541 [+0.198, +0.923] |
| the four saturated **calls** excluded from all three arms | 1,412 / 40 | +4.125 [+2.524, +5.853] | **+0.339 [+0.091, +0.619]** |

The call-level exclusion is the one that bounds the covariate, and it does bound it: a third of the
corpus-WER cost sits in those four calls. **It does not change the verdict** — the upper bound is
still +0.619 and the guard still fails. Reported beside the primary, never in place of it.

One thing the call-level exclusion does change is the reading of the twin: with those four calls
dropped, KU-E1c's own corpus WER is level with the comparator — improvement +0.019 pp
[−0.117, +0.168], a delta that straddles zero — so the form's small apparent cost was itself mostly
the twin's two saturated calls.

## 8. Both weightings, and the descriptive window layer

| contrast, metric | natural mixture | equal stratum (per call) | window-level (OPTIMISTIC) |
|---|---|---|---|
| total, PERSON | +4.148 [+2.633, +5.740] | +4.499 [+2.586, +6.505] | +4.148 [+2.814, +5.474] |
| total, corpus WER (improvement) | −0.536 [−0.917, −0.195] | −0.489 [−0.832, −0.178] | −0.536 [−0.836, −0.255] |
| content, PERSON | +5.382 [+3.914, +6.989] | +6.246 [+4.481, +8.099] | +5.382 [+4.090, +6.666] |
| form, PERSON | −1.234 [−2.033, −0.484] | −1.747 [−2.694, −0.847] | −1.234 [−2.158, −0.337] |

The window-level column treats 1,593 units as independent, which they are not; it is carried because
§3 asks for it and it decides nothing.

Saves / harms / ties and the exact two-sided sign test at the window unit, from
`analysis.paired.paired_contrast` (whose own bootstrap is the mean of per-window differences and is
**not** the decision interval):

| contrast, metric | n | saves | harms | ties | sign test p |
|---|---:|---:|---:|---:|---:|
| total, PERSON | 1,593 (935 carry PERSON reference words) | 152 | 82 | 1,359 | 5.55e-06 |
| total, corpus WER | 1,593 | 710 | 613 | 270 | 8.28e-03 |
| form, PERSON | 1,593 | 50 | 77 | 1,466 | 2.07e-02 |
| content, PERSON | 1,593 | 161 | 61 | 1,371 | 1.37e-11 |

Per call: PERSON entity WER improves on **29 of 44** calls, worsens on 8, ties on 7; corpus WER
worsens on 27 and improves on 17. The full 44-row table is
`docs/checks/speech-aware-evidence-acquisition/2026-09-07-e21-kc-e1-verdict/per-call-table.md`.

## 9. The E5 halves, reported apart

| roster | calls | windows | corpus WER: comparator / KU-E1c / KC-E1 | PERSON: comparator / KU-E1c / KC-E1 | ORG: comparator / KU-E1c / KC-E1 |
|---|---:|---:|---|---|---|
| construction 34 | 34 | 1,251 | 8.470 / 8.590 / **9.097** | 23.469 / 24.676 / **19.629** | 16.007 / 17.637 / 18.248 |
| evaluation 10 | 10 | 342 | 7.185 / 7.467 / **7.381** | 18.698 / 20.033 / **13.356** | 21.683 / 20.496 / **17.044** |

**No interval is quoted on the evaluation ten and none should be.** 342 paired windows is below the
program's `n >= 400` rule for an effectiveness claim, and 10 clusters is a thin bootstrap. The ten's
column is descriptive, and it is descriptively striking — PERSON 18.698 → 13.356 at a corpus cost of
0.196 pp rather than 0.627 — which is a reason to design the next cell, not a result.

## 10. The token covariate, throughput and cost of both cells

The twin was matched to the arm on the flight tokenizer line by line and call by call. What is left
is a **constant +7 tokens** for the twin on **every one of the 44 calls** — the `[evidence <id>] `
header of the two evidence blocks, not the brief — re-derived here from the two flight receipts
rather than quoted (`token-throughput-covariate.json`, 44 rows, residual set `{7}`).

| | comparator | KC-E1 | KU-E1c |
|---|---:|---:|---:|
| prompt tokens | 1,935,965 | **2,907,274** (+50.2 %) | 2,918,425 |
| completion tokens | 439,532 | **423,115** (−3.7 %) | 430,779 |
| per-window prompt min / median / max | — | 541 / 1,855 / 2,040 | 548 / 1,862 / 2,047 |
| brief text envelope min / median / max | 62 (constant) | 456 / 688 / 870 | arm + 7 at every quantile |
| GPU hours (manifest nvidia-smi sampler) | 0.9734 | **0.9948** | **1.0087** |
| run wall | — | 5,884 s (98.07 min) | 5,799 s (96.65 min) |
| windows per minute | — | 16.24 | 16.48 |
| realized realtime factor | — | 39.47× | 38.92× |
| peak VRAM | — | 22,726 MiB | 22,726 MiB |

Half again as much prefill costs about 2 % of GPU time: 90 seconds of audio dominates the window.
The pair cost **2.0035 GPU-h** by the receipts' own convention, against a registered 4.7 for the two
cells; paid API spend 0, unchanged.

## 11. What this cell cannot conclude

1. **Nothing about the whole brief.** The prompt fit measured the uncapped brief's worst request at
   8,268 tokens against a 6,144-token slot; what flew is the brief capped at 12 entries per class,
   the largest value on the grid that keeps the margin rule. Every number here is about the capped
   brief at this serving geometry.
2. **No superiority and no generality.** One carrier, one frozen core at Q4_K_M on build `04ccc72a`,
   one 90-second OBS tiling, greedy, 44 discovery calls. `paper-scale-confirmatory` is neither
   available to this repository nor requested.
3. **No evaluation claim.** 34 of the 44 calls are the kb-construction half; the evaluation ten are
   reported apart in §9 and carry 342 paired windows, below the `n >= 400` rule.
4. **It cannot separate the roster half of the brief from the candidate half.** Both are supplied
   together in every window; §5's per-class table is a class split, not an evidence-source split.
5. **It cannot say WHY the deletions appear.** §6 localizes the cost to non-entity deletions with the
   arms' own counts; no attribution instrument in this cell can say whether the model is skipping
   speech, stopping early, or re-ranking its own output under a longer prompt. That is a diagnosis,
   and it has not been run.
6. **The negation-critical rate gates nothing.** 100 / 109 / 120 HIGH reference words across the three
   arms; the level moves by a handful of words and is advisory by the preregistration's own wording.
7. **A small share of every difference is decode noise.** Greedy decoding on llama-server is not
   bitwise reproducible across batch compositions, and the three arms flew as three separate passes;
   the sealed verdict's own build-and-audio-path noise on corpus WER was 0.05 points.
8. **The speaker strata of §4 are not attached.** The diarization artifact exists but this verdict did
   not read it; §4 explicitly allows attaching those strata afterwards over the same sealed window
   rows, and a stratum is a reporting dimension, never a knob — no decision here conditions on one.
9. **`fixed-legal-context` records provenance tier `UNVERIFIED`** with a GRANDFATHERED declaration
   warning in both flights' manifests. That is a property of the arm, predating the 2026-08-15
   legality doctrine, and it is carried rather than discovered.

## 12. One named next step — named, not built

The guard that failed is transcript completeness, so the next cell has to buy the entity gain without
spending the transcript. **`KC-E1f` — the brief as a second-pass entity repair (USE axis).** Pass 1
decodes the window with the comparator's own bare-core prompt, so the non-entity deletion profile is
the comparator's *by construction*; pass 2 sees the same window's audio, the pass-1 hypothesis and the
same capped brief, and may emit only a substitution list over pass-1 spans. The final answer authority
stays with the frozen core and no parameter moves.

**This is a new mechanism and it needs its own preregistration and its own owner GO.** It changes the
arm, the protocol hash and the policy; it doubles the contacts and roughly doubles the GPU hours per
pass; it needs its own token-matched twin, its own decision rule, and a stated rule for what a pass-2
edit is allowed to touch. It must not be built off the back of this note. A decode-cap or
brief-length knob is likewise a new mechanism, not a repair to this cell — and §7 shows the cap is
not where the cost is.

## 13. Files

| file | what it holds |
|---|---|
| `docs/checks/…/2026-09-07-e21-kc-e1-verdict/result-summary.json` | every number in this note: the three identity anchors, the three contrasts over 15 metrics under three interval readings, both saturation sensitivities, the descriptive window layer, the 44-row per-call block, the E5 halves and the token covariate |
| `…/per-call-table.md` | the 44 calls, corpus WER and PERSON entity WER, all three arms |
| `…/token-throughput-covariate.json` | both arms' per-call brief token counts, the constant +7 residual, prompt/completion totals, throughput and GPU hours, with each flight receipt's SHA-256 |
| `…/reaggregation/{comparator,kc-e1,ku-e1c}/reaggregation.json` | the identity anchor of each arm — every check, the pooled buckets, the per-call numeric rows |
| `…/cited/` | the KU-E1c flight receipt's own bytes for what this note cites, copied from the git blob at `df040750` |
| `…/MANIFEST.sha256` | the receipt directory's byte manifest |
| `scripts/e21_kc_e1_verdict_read.py` | the runner; `scripts/e21_window_pairing_read.py` gained KU-E1c's sealed profile and an additive per-window class-count field |

Per-window rows for the three arms live under
`$SPEECHRL_DATA_DIR/runs/SAEA-E21-MF-WINDOW-PAIRING-V1/verdict-v1-window-rows-*.json` — per-request
derivatives of sealed model outputs, so they live where those live and never in Git. Their SHA-256
values are pinned in each arm's anchor and re-checked by the verdict runner before a contrast is
computed.
