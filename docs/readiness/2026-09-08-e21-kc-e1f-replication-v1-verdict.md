# REPLICATED — KC-E1f, flown a second time on the same roster

**REPLICATED.** The 44 Earnings-21 discovery calls and the same 1,593 fixed 90-second windows were
flown again as a second independent pass under a configuration proved identical by hash before the
first contact. The PERSON effect is met on both legs and is again **disjoint from this carrier's own
PERSON null interval**; all three gating guards pass at the margins that null measured; and the
first-pass-versus-replicate contrast sits **inside the null band on six of the seven metrics that
have a band**, the seventh being the advisory metric whose own null excludes zero and which the v2
rule already ruled unanswerable on this carrier.

This discharges the obligation section 3 of
`docs/readiness/2026-09-08-e21-kc-e1f-repair-pass-v2-redecision.md` fixed **before** that verdict was
known, and it is the thing that re-decision could not do for itself: a re-decision of sealed bytes
produces no second sample, and this is the second sample.

Decides exposure row `SAEA-E21-KC-E1F-REPAIR-44-REPLICATE-V1` (`bounded-discovery-probe`), attempt
`attempt-20260908T232501Z-36792e`, `FINALIZED`, study commit `82903e70`, `study_repo_dirt` empty.
Receipt: `docs/checks/speech-aware-evidence-acquisition/2026-09-08-e21-kc-e1f-replication-v1/`.
The read that decides spends **zero model, GPU, tool, embedder, tokenizer, network, audio-decode and
paid-API contacts**: it runs on bytes sealed before it opened them.

---

## 1. The rule, quoted from the clause that fixed it in advance

> 1. **The same roster, flown again.** All 44 discovery calls, the same 1,593 fixed 90-second
>    windows, the same configuration, as a second independent pass of the KC-E1f arm.
> 2. **A second pass through the null band.** The replicate's PERSON effect and every gating guard
>    must be re-read against the null's measured intervals, and the PERSON effect must again be
>    disjoint from `[−0.24338, +0.25680]`.
> 3. **No freeze before both hold.**

Nothing about the instrument moved. The pairing unit is the fixed 90-second window (1,593), the
bootstrap cluster is the call (44), the estimator is the pooled ratio
`sum(numerator) / sum(denominator)` through
`analysis.paired.resampled_statistic(cluster_of=analysis.e21_window_pairing.call_of)` at seed
**20260903**, **10,000** replicates, **CI90**, reported under **both weightings**. The margins are
this carrier's own, read from `SAEA-E21-FULL44-NULL-REPLICATE-V1`'s published table and the v2
decision's computed over-generation band rather than retyped.

**The read is literally the same instrument.** `scripts/e21_kc_e1f_replication_read.py` imports
`scripts/e21_kc_e1f_verdict_read.py` and calls its own helpers, so the replication and the thing it
replicates come out of one estimator rather than two dialects.

## 2. Identical configuration, and the falsifier that proves it

| | first pass `SAEA-E21-KC-E1F-REPAIR-44-V1` | this replicate |
|---|---|---|
| composed config hash | `05777ca3…3b3e5f` | **identical** |
| protocol hash | `43b60556…6bd630` | **identical** |
| split identity hash | `fcc1b0bc…d69e` | **identical** |
| `obs_prefetch_depth` | absent | **absent** |
| **prompt tokens, total** | **3,550,695** | **3,550,695 — equal to the digit** |
| metered speech seconds | 141,345.8526875 | 141,345.8526875 |
| charged contacts | 1,593 | 1,593 |
| completion tokens, total | 434,219 | 437,350 |

**The request side is provably unchanged and only the completions moved.** Over 1,593 windows the
encoder saw the same token count to the digit, on the same audio, with the same cap-12 brief and the
same sealed pass-1 hypothesis in every prefill — so nothing but decode-time batch composition
separates the two passes. That is what makes this a replicate rather than a second cell.

The cross-call dispatcher's admission entry reads NEUTRAL and would have licensed
`obs_prefetch_depth` 1 for an Earnings-21 cell at this geometry, and the ported openJiuwen graph
landed on master after the first pass. **Neither was used**, deliberately: a replicate that changes
the configuration it replicates has replicated nothing.

## 3. Three refusals ran before any contrast, and each of them passed

| gate | what it refuses | result |
|---|---|---|
| identity anchor, all four arms | an arm whose 1,593 per-window rows do not re-aggregate to its own sealed numbers | **4 × 30/30 PASS** |
| class anchor | any reported ConEC class that is unanchored against the arm's own committed receipt | **116/116 PASS** |
| section 5.1 attribution | a normalized deletion/insertion move not carried by a substituted span | **PASS**, 6 of 6 checks |
| delivery integrity (construction) | a delivered hypothesis whose whitespace-token count moved | **PASS**, 1,593/1,593, 0 violations |
| the v2 self-anchor | this instrument failing to reproduce the decision it extends | **PASS**, 2/2, 0 fields moved |

**The self-anchor is the one worth naming.** Before deciding anything about the replicate, this read
recomputes the v2 decision's own two primary legs from the v2 decision's own anchored rows and
refuses unless every field — point, both bounds, sigma — is equal to the published value. It returned
`+3.737 [+2.653, +4.855]` and `+3.840 [+2.752, +4.958]`, digit for digit. So the replicate is being
compared against a reference this read has demonstrated it can reproduce, not against a quoted number.

The attribution's own arithmetic: `(I − D)` moved by exactly **+6** against the comparator, the
attributed normalized-word delta is **+6**, and **no window moved without carrying a substituted
span** — 1,883 spans, 25 carrying a non-zero delta, 0 interior tokens moved.

## 4. The primary — met on both legs, and again outside the carrier's own noise

Call-clustered CI90, natural mixture, 44 clusters, 1,593 windows, seed 20260903, 10,000 replicates.
Percentage points. Signed as a REDUCTION, so a positive value means fewer errors.

| leg | required | measured | equal stratum | LB in PERSON null half-widths | disjoint from `[−0.24338, +0.25680]`? | verdict |
|---|---|---|---|---:|---|---|
| vs the sealed comparator | LB > **+0.25680** | **+3.634 [+2.590, +4.690]** | +3.610 [+2.433, +4.795] | **10.36** | **YES**, by 2.33 points | **MET** |
| vs the token-matched twin | LB > 0 | **+3.737 [+2.686, +4.773]** | +3.702 [+2.515, +4.868] | 10.74 | **YES** | **MET** |

PERSON entity WER goes **22.489 % → 18.855 %** against the comparator. The first pass measured
**+3.737 [+2.653, +4.855]** on the same contrast; the replicate measures +3.634, and the two
intervals overlap over almost their whole length.

**The bar here is stricter than the v2 primary's.** v2 asked for a lower bound above zero and
reported the null comparison; the replication clause makes disjointness from the null interval the
requirement. The replicate clears the stricter bar with 2.33 points to spare.

## 5. The guards, at the margins this carrier measured for itself

Signed **replicate minus comparator**; each margin is one-sided and applied only on the harmful side.

| # | guard | required (v2 margins) | replicate | first pass | slack | verdict |
|---|---|---|---:|---:|---:|---|
| 1 | delivery integrity | construction; aborts the read | 1,593/1,593, **0 violations** | 1,593/1,593, 0 | — | **PASS** |
| 2 | corpus WER non-inferiority | UB <= **+0.05793** | **−0.03090** (point −0.04642) | −0.02936 | 0.08883 | **PASS** |
| 3 | numeric accuracy, call-pooled | LB >= **−0.15651** | **−0.07745** (point −0.03082) | −0.02122 | 0.07905 | **PASS** |
| 4 | over-generation, insertions/ref word | UB <= **+0.02218** | **+0.00328** (point +0.00139) | +0.00255 | 0.01890 | **PASS** |
| 5 | negation-critical / semantic rate | advisory; gates nothing | **+0.00000 [0.00000, 0.00000]** | −0.00028 | — | ADVISORY |

**Every gating guard passes under both weightings.** Guard 3 is the loosest of the three in relative
terms — the replicate's harmful bound is 49 % of its margin against the first pass's 14 % — and it is
stated that way rather than as "PASS". The movement behind it is three matched numeric values:
8,829 against the comparator's 8,832, where the first pass read 8,833.

**Guard 5 moved by exactly zero.** The replicate's high-impact reference-word mass is **100**, the
comparator's own figure, and its high-impact insertions are **56**, also the comparator's; the first
pass read 99 and 56. On this pass the advisory metric is not merely non-inferior, it is identical.

## 6. The replication contrast — two passes of one configuration, against the null band

Signed **replicate minus first pass**. The question is not whether the two passes agree, but whether
they differ by more than this carrier's own runtime can manufacture with nothing changed.

| metric | delta | CI90 | this carrier's null band | inside? |
|---|---:|---|---|---|
| PERSON entity WER | +0.10285 | [−0.33075, +0.56023] | [−0.24338, +0.25680] | **YES** |
| corpus WER | −0.00139 | [−0.00842, +0.00502] | [−0.08502, +0.03085] | **YES** |
| ORG entity WER | −0.29796 | [−0.61713, −0.02448] | [−0.44313, +0.26904] | **YES** |
| non-entity WER | +0.00066 | [−0.00329, +0.00474] | [−0.11375, +0.01575] | **YES** |
| numeric accuracy (call-pooled) | −0.04109 | [−0.07574, −0.01042] | [−0.18758, +0.12543] | **YES** |
| insertions per reference word | +0.00111 | [−0.00056, +0.00279] | [−0.01356, +0.03079] | **YES** |
| semantic high-impact rate | +0.00028 | [+0.00000, +0.00080] | [+0.00080, +0.00377] | **NO** |

**Six of seven inside, and the two that would have looked like findings against zero are exactly why
the band exists.** ORG (`[−0.61713, −0.02448]`) and numeric accuracy (`[−0.07574, −0.01042]`) both
exclude zero on the first-pass-versus-replicate contrast — that is, the same configuration flown
twice produces "significant" movements on both — and both sit comfortably inside the interval this
carrier's own null measured. Reading either as a difference between the passes would be reading
decode noise.

**The seventh is the metric the v2 rule already retired from gating.** The semantic high-impact rate
counts about a hundred reference words out of 359,765; its own same-request null **excludes zero**
(`[+0.00080, +0.00377]`), which is why v2 §2.3 refused to give it a margin at all. Its
first-pass-versus-replicate interval `[+0.00000, +0.00080]` falls just below that band, and the whole
movement is **one high-impact reference word** — 99 on the first pass, 100 on the replicate, which is
the comparator's own count. A metric whose null band excludes zero cannot answer "did these two
passes agree" in either direction; it is reported here for completeness and it gates nothing.

## 7. Per call, and the stratum table the reporting rule requires

`verdict/per-call-table.md` carries all 44 calls with each arm's corpus WER and PERSON entity WER and
the replicate-minus-first-pass delta on both, plus the E5 halves.

**The per-call spread is the caution this table exists to publish.** Per-call PERSON moves between
the two passes reach ±2.6 points (`4344866` +2.632, `4330115` −2.222) on calls carrying 38 and 45
PERSON reference words, while the corpus deltas stay inside ±0.05. The own-null replicate measured
about a **point** of per-call corpus-WER replicate noise on this carrier and PERSON at n≈40 words per
call is far noisier still, so **no per-call story here is admissible**, in either direction. The
corpus and the 44-cluster bootstrap are the readable units; the per-call rows are published so no
reader has to take that on trust.

The E5 halves, **descriptive and with no interval quoted** — the evaluation ten carry 342 paired
windows, below the program's `n >= 400` rule:

| half | calls | windows | metric | comparator | first pass | replicate |
|---|---:|---:|---|---:|---:|---:|
| construction | 34 | 1,251 | corpus WER | 8.4700 | 8.4323 | 8.4302 |
| construction | 34 | 1,251 | PERSON | 23.4685 | 19.5427 | 19.7584 |
| construction | 34 | 1,251 | ORG | 16.0070 | 15.7742 | 15.3958 |
| evaluation | 10 | 342 | corpus WER | 7.1854 | 7.1128 | 7.1141 |
| evaluation | 10 | 342 | PERSON | 18.6978 | 15.6928 | 15.3589 |
| evaluation | 10 | 342 | ORG | 21.6828 | 19.2017 | 19.2017 |

## 8. The core-pressure covariates, published beside the admission

A gain bought with core pressure is a different thing from a gain bought with a better prompt.

| | replicate | first pass | comparator |
|---|---:|---:|---:|
| core calls charged per window, this cell | **1** | 1 | 1 |
| core calls per window including the pass 1 it edits | 2 | 2 | 1 |
| prompt tokens per window — min / median / max | **683 / 2,260 / 2,480** | 683 / 2,260 / 2,480 | — |
| prompt tokens, total | **3,550,695** | 3,550,695 | 1,935,965 |
| completion tokens, total | **437,350** | 434,219 | 439,532 |
| worst realized request / slot | 3,504 / 9,216 (margin 2.630) | 3,504 / 9,216 (2.630) | — |
| GPU hours (nvidia-smi sampler) | **1.1957** | 1.1093 | 0.9734 |
| windows per minute | 14.865 | 15.295 | 16.38 (at np6) |

**The system's own decision share**, which is the part of the outcome the control plane decided
rather than the core:

| | replicate | first pass |
|---|---:|---:|
| windows | 1,593 | 1,593 |
| windows changed (>= 1 accepted substitution) | **1,075** | 1,064 |
| windows delivered unchanged without a refusal | 431 | 447 |
| windows refused | **87** | 82 |
| — `anchor_ratio_below_floor` | 81 | 75 |
| — `empty_response` | 3 | 3 |
| — `substituted_fraction_above_ceiling` | 3 | 4 |
| — `empty_predecessor` | 0 | 0 |
| accepted substitutions | **2,446** | 2,427 |
| substituted tokens applied | **2,543** | 2,545 |
| rejected opcodes, total | **1,210** | 1,093 |
| — `unbalanced_replace` | 790 | 654 |
| — `deletion` | 281 | 331 |
| — `insertion` | 131 | 104 |
| — `oversized_replace` | 8 | 4 |

**The stable half of this cell is the control plane, not the core.** Between two passes of an
identical request the model's proposals moved substantially — 790 unbalanced replacements against
654, 281 rejected deletions against 331 — while what reached the transcript barely moved: 2,543
substituted tokens against 2,545, on 1,075 windows against 1,064. **27 % of windows (431 + 87 of
1,593) again ended with the sealed pass-1 text unchanged**, and 1,210 proposed opcodes were rejected
by class before delivery. The gain is bought at one contact per window; its safety is bought by the
rejections, and the replicate reproduces both.

**GPU cost is the one covariate that did not reproduce tightly.** 1.1957 GPU-h against the first
pass's 1.1093 is a **7.8 % spread on a request-identical pass**, twice the 3.6 % the own-null
replicate measured on byte-identical work. No GPU-hour comparison in this family is meaningful below
about 8 % on this evidence.

## 9. What this verdict means, and what may now be said

**The citable sentence gains one clause and loses one.** The v2 note's single citable sentence ended
"…**provisional until replicated on the same roster**". That clause is discharged. The sentence may
now read:

> On the 44 Earnings-21 discovery calls, a second, substitution-only repair pass over the frozen
> core's own sealed transcript, supplied with a 12-entry ConEC pre-meeting brief, reduces PERSON
> entity WER from 22.489 % — a call-clustered CI90 reduction of **+3.737 points [+2.653, +4.855]** on
> the first pass and **+3.634 [+2.590, +4.690]** on an independent second pass of the same roster
> under a configuration identical to the digit in prompt tokens, each disjoint from this carrier's
> own same-request replicate null and each met against a token-matched placebo twin — with every
> guard holding at the non-inferiority margins that null measured, on both passes; the result is
> training-free, zero-parameter-update, discovery-split and single-carrier.

**What may still not be said**, and each of these was checked rather than assumed:

1. **Not that corpus WER improved.** The v2 correction stands: the corpus-WER movement is inside
   replicate noise on both passes. It is not worse; that is all.
2. **Not that ORG improved.** Same reason, and the replication contrast makes it vivid — ORG moved
   −0.298 with an interval excluding zero **between two identical passes**.
3. **No evaluation-split claim.** 34 of the 44 calls are the kb-construction half; the evaluation ten
   carry 342 paired windows, below `n >= 400`. This verdict quotes no interval on them.
4. **No superiority and no generality.** One carrier, one frozen core at Q4_K_M on build `04ccc72a`,
   one 90-second OBS tiling, greedy, 44 discovery calls, one null's margins, now two passes.
5. **Not that the mechanism repaired a deletion.** It cannot, by construction; PERSON deletions read
   80 on both passes against the comparator's 83, and that is the normalization re-seating v1 §4
   attributed, not recovered words. The reachable floor stays `83 / 2917 = 2.846 %`.
6. **No per-call claim.** §7.
7. **No Stage-3 claim**, and no `paper-scale-confirmatory` profile.
8. **Not that two passes are a distribution.** §10 item 1.

## 10. What this replication cannot conclude

1. **Two samples are two samples.** The replication clause asked for a second independent pass and
   got one. Two passes bound the between-pass spread on PERSON at roughly a tenth of a point; they do
   not estimate its variance, and a third pass would move the estimate.
2. **The margins are still one replicate's.** Every band used here was measured by
   `SAEA-E21-FULL44-NULL-REPLICATE-V1` at 44 clusters, once. If the geometry, the build or the
   population changes, they must be re-measured before they are reused.
3. **Four of the six agentic metrics still cannot resolve a half-point effect at 44 clusters.** This
   verdict claims PERSON and nothing else for exactly that reason.
4. **Nothing about the other two carriers.** SLURP and Audio2Tool still have no measured null of
   their own, and none of these margins travels to them.
5. **The semantic metric is still unanswerable on this carrier**, and this cell adds a second reason:
   its null band excludes zero, so even a pure replication contrast falls outside it. The null
   verdict's §10 item 2 fix — widen the taxonomy or retire the metric from admission clauses — is
   still owed.
6. **The switch form the module is now recorded under has never been flown.** §11.

## 11. The admission entry, and the one thing this verdict deliberately does not do

`docs/receipts/harness-admission.json` carried this module as **ADMITTED, provisional, obligation
`UNMET`**. This verdict sets that obligation **`MET`** and records the replication evidence beside the
first pass's.

**It does not promote the module into the default plan, and the reason is a gap the receipt itself
already documents.** The entry's own `switch.what_flew` says it plainly: *"The sealed KC-E1f arm did
NOT fly through this key. It flew the obs-repair-loop policy with response_postprocessor
'e21-entity-repair-substitutions-v1'… This field records the form the module takes from now on, not
the form its evidence was produced in."* The switch the table records is
`judges.<phase>.judges = ["e21-substitution-alignment-flag-v1"]`, and **no committed config fragment
arms it**: entering a default plan would mean composing a new fragment and arming, on a carrier's
default path, a form of this module that has never been flown once. That is an engineering act with
its own evidence burden, and a replication flight is not the cell that may perform it.

So the obligation this note discharges is the one it was asked to discharge — the replication — and
the entry records the remaining blocker under its own name rather than pretending it away:
`plan_entry.state = "BLOCKED"`, reason **the recorded switch form has never been flown**, with the
named next step. `scripts/checks/harness_admission_check.py` reads `provisional.state`, so this note
keeps the entry blocked through that field with the new, honest reason, and the discharged
replication is recorded in its own `replication` block with its evidence. **A receipt that swapped an
unmet obligation for a silently satisfied one would be worse than the receipt it replaced.**

## 12. Files

| file | what it holds |
|---|---|
| `docs/checks/…/2026-09-08-e21-kc-e1f-replication-v1/verdict/result-summary.json` | the decision: the bands with their sources, the four identity anchors, the class anchor, the attribution checks, the v2 self-anchor, the primary, the guards, the replication contrast, five contrasts × every metric under three interval readings and two weightings, the per-call table and the E5 halves |
| `…/verdict/guard-table.md`, `…/verdict/per-call-table.md` | the guard table and the 44-call stratum table, each as one page |
| `…/flight/README.md`, `…/flight/flight-receipt.json` | the flight: identity, serving, monitor, the delivery-integrity guard, the repair ledger, cost, throughput, every scorer aggregate |
| `…/flight/score-read.json`, `…/flight/batch-summary.json`, `…/flight/jobs.jsonl` | the one complete-manifest scoring job and its verified read |
| `…/reaggregation/kc-e1f-rep/reaggregation.json` | the replicate's identity anchor, 30/30 PASS, with its rows file's SHA-256 |
| `…/attribution/kc-e1f-rep/attribution.json` | the section 5.1 receipt for the replicate |
| `…/MANIFEST.sha256` | the receipt directory's byte manifest |
| `scripts/e21_kc_e1f_replication_read.py` | the replication rule in executable form |

Per-window rows and span tables live under `$SPEECHRL_DATA_DIR/runs/SAEA-E21-MF-WINDOW-PAIRING-V1/`
and never in Git — per-request derivatives of sealed model outputs. Their SHA-256 values are pinned
in each arm's anchor and re-checked before a contrast is computed.
