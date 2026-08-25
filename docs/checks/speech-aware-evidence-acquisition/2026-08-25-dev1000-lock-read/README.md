# DEV-1000 BASELINE-LOCK — the ONE registered one-shot lock read

Date: 2026-08-25. Exposure row: `SAEA-SN-MF-DEV1000-LOCK-READ` (registered before any
computation, ledger commit `11ce2cef`). Profile: `model-free-check`. Spend: **0** frozen-core
contacts, **0** pinned-tool embedding contacts, **0** tokenizer contacts, **0** audio seconds,
**0.0** GPU hours.

Read module: `src/speech_aware_evidence_acquisition/analysis/dev1000_lock_read.py`.
Verdict artifact: `read-verdict.json` (this directory).

This artifact reports the registered outputs only. **The coordinator interprets and writes the
verdict.** Nothing below is an interpretation, a recommendation, or a claim beyond the
preregistered statistic and the registered secondaries.

## 1. One-shot semantics (binding)

The preregistration
(`docs/readiness/2026-08-24-dev1000-baseline-lock-preregistration.md` sections 1 and 2) and the
candidate-selection note (`docs/readiness/2026-08-25-lock-candidate-selection.md` sections 3 and
4) froze the statistic, the population, and the lock condition **before** the arms flew. The
campaign row `SAEA-DEV1000-BASELINE-LOCK` explicitly RESERVED this read and did not authorize it;
its three landings (`11309317`, `fbc651bb`, `9928d7ce`) stopped hard at mechanical eligibility
with gold never opened.

The statistic was computed **exactly once, exactly as frozen**. No threshold was changed, no
parameter re-tried, no partial re-read performed, no arm re-flown. A second execution of the
module against these same pinned bytes is a reproducibility check and can never become a second
read — which is why every input is pinned by sha256 and a mismatch is a fail-closed `ReadError`,
never a warning. Gold opened ONCE, here, scoring-side, for all 1,000 DEV-1000 samples.

## 2. Sources (all sha256-verified at load; every one matched)

Committed per-arm mechanical reports, under
`docs/checks/speech-aware-evidence-acquisition/2026-08-25-dev1000-baseline-lock/`:

| artifact | sha256 |
|---|---|
| `arm1-m0-mechanical-report.json` | `c751ca585bfacd71b2a62093afaf744ceee5cf7ad63980b5145ae43a825f24f1` |
| `arm2-blend-mechanical-report.json` | `c3ed01699a43087e719b917c751d1ce96d6b0992107d58437fc048fd12ba5930` |

Sealed attempt-store artifacts, under `$SPEECHRL_DATA_DIR/runs/SAEA-DEV1000-BASELINE-LOCK/`:

| artifact | sha256 |
|---|---|
| `attempt-20260825T053342Z-dev1000m0/arm1-m0-outputs.jsonl` | `ea7045d3cfd3d1652f568911a0c47c16d66b879e824d314a6cb5061d7f07decc` |
| `attempt-20260825T053342Z-dev1000m0/arm1-m0-mechanical.json` | `814532760a712888d943c4a781f358cff426001ac0394ee29814cf4ee0335d16` |
| `attempt-20260825T054707Z-dev1000blend/arm2-blend-outputs.jsonl` | `542a029adca8fb8daf3618e8a049aecdba1b04aba30eafedb67099fb6e08cf14` |
| `attempt-20260825T054707Z-dev1000blend/arm2-blend-mechanical.json` | `e55b6632d85a0037fb928d565fb2ef1b40c987c915dd98a9f2599d78113c828e` |

Committed split receipts (file sha256, all matched):
`DEV-1000.json` `653c7556edf88e56af2e18a25239426b2efc3b080af0173fd65c87fe8e4f528b`,
`DEV-500.json` `adc3e4ddd20518d279dc6c3aa42821629ca67b05eaba7802e1918f0349c2f315`,
`DEV-1000-NEW500.json` `1feefb8c327c0234160e96906bd5344cfef25ac665ddbb4db957fab067a234a3`.
TRAIN knowledge snapshot `e27b274516604ffc0e21319758aea99dc027f459d480a32a74a715b023a51b57`
and its content-facet NPZ `0bcb955a3a0ab84880f0d039ae702e77d1247ed23c3b8cecb468cbb1e0221c72`
(value vectors stay SEALED and were never loaded). Lock candidate
`configs/policy/kb-policy-v2-lock-candidate.json`
`0c34ebe7be636b8e432bffe504b0175d1a122000a74051b183e09615de69033e`.

Additionally, for the 14 override trajectories ONLY, the BLEND attempt's own durable trace
(`SAEA-DEV1000-BASELINE-LOCK.trace.jsonl`, sealed bytes in the same attempt store) was streamed
once to recover the direct-decode TEXT for a hash the per-sample mechanical record already
carries; every recovered text was re-hashed and matched to the hash that asked for it. Nothing
else was taken from the trace.

**Population.** DEV-1000 load-split identity `8580d199…3c84`, receipt-integrity `9fb44e33…243b`.
The lock population is the unexposed NEW500 (run-identity `48a96f6f…6ecd`, receipt-integrity
`1d6d4ba6…c66d`), re-derived at load as the deterministic set difference DEV-1000 minus DEV-500 on
the receipts' `id` field — never the carrier-prefixed `key` field, the A4 lesson, asserted
non-empty here — and matched to its own committed receipt. Disjointness from the exposed 500 and
union to DEV-1000 were both asserted.

## 3. LOCK CONDITION — outcome

Statistic citation, verbatim from preregistration section 2:

> Statistic: paired per-sample BLEND − M0 over the unexposed 500; paired cluster bootstrap
> (N=10,000, seed 20260807) 90% and 95% CIs; McNemar exact. **Lock condition (preregistered): the
> 90% CI lower bound ≥ +10 pp** — i.e. not merely "excludes zero" but retains the bulk of the
> DEV-500 margin (+19.75 pp, CI [+16.5, +23.0]) at double scale. A CI that excludes zero but falls
> below +10 is recorded as CONFIRMED-BUT-SHRUNKEN and does NOT lock; it returns to iteration.

### OUTCOME: **LOCKED**

The 90% CI lower bound is **+17.20 pp**, which is **+7.20 pp above** the +10 pp lock threshold.

## 4. The primary statistic (the 500 UNEXPOSED samples)

| quantity | value |
|---|---|
| population | DEV-1000-NEW500, 500 unexposed |
| M0 | **278 / 500 = 55.60%** |
| BLEND(v2) | **379 / 500 = 75.80%** |
| paired delta | **+101 samples = +20.20 pp** |
| 90% CI | **[+17.20, +23.40] pp** |
| 95% CI | **[+16.60, +24.00] pp** |
| bootstrap sigma-hat | 1.8986 pp |
| replicates at or below zero | 0 of 10,000 |
| McNemar exact two-sided p | **1.0352e-25** |
| McNemar mid-p two-sided | 5.4157e-26 |
| chi-square (continuity corrected) | 90.0901, p = 2.2756e-21 |
| wrong→correct | **106** |
| correct→wrong | **5** |
| discordant / concordant | 111 / 389 |
| odds ratio n01/n10 | 21.2 |

Bootstrap: N = 10,000, seed 20260807, paired cluster resampling in which the same resampled
multiset scores both arms.

## 5. Registered secondaries (reported, NO claim attaches)

### 5.1 The prior-exposed 500, separately — never pooled into the lock claim

M0 258/500 = 51.60%; BLEND 378/500 = 75.60%; delta +120 = **+24.00 pp**; 90% CI [+20.80, +27.20];
95% CI [+20.20, +27.80]; McNemar exact p = 7.8406e-33; W→C 123, C→W 3.

### 5.2 Pooled 1,000 — DESCRIPTIVE ONLY, explicitly not the lock claim

M0 536/1000 = 53.60%; BLEND 757/1000 = 75.70%; delta +221 = **+22.10 pp**; 90% CI [+19.90,
+24.40]; 95% CI [+19.40, +24.80]; McNemar exact p = 2.0551e-57; W→C 229, C→W 8.

### 5.3 The δ ≥ 0.14 retain-override subgroup (the v2 variable)

14 fires in total: **3 inside the unexposed 500**, 11 inside the prior-exposed 500. The
counterfactual is exact rather than estimated: the override is branch-only, so had it not fired
the trajectory would have RETAINED and answered with its own direct decode, whose text the sealed
record pins by hash.

| sample | population | δ | direct → fused top-1 | gold | M0 | v1 retain (counterfactual) | BLEND(v2) | outcome |
|---|---|---|---|---|---|---|---|---|
| `slurp:devel:002303:audio-1501690619-headset` | UNEXPOSED | 0.140362 | music_likeness → play_music | music_likeness | 0 | 1 | 0 | DAMAGED |
| `slurp:devel:002955:audio-1495733256-headset` | UNEXPOSED | 0.140362 | music_likeness → play_music | music_likeness | 1 | 1 | 0 | DAMAGED |
| `slurp:devel:014737:audio-1495376531` | UNEXPOSED | 0.185729 | cooking_query → cooking_recipe | cooking_query | 1 | 1 | 0 | DAMAGED |
| `slurp:devel:002814:audio-1490194699` | exposed | 0.171835 | takeaway_order → iot_coffee | iot_coffee | 0 | 0 | 1 | RECOVERED |
| `slurp:devel:009926:audio-1501697340-headset` | exposed | 0.187079 | cooking_query → cooking_recipe | cooking_recipe | 0 | 0 | 1 | RECOVERED |
| `slurp:devel:009965:audio-1501754719` | exposed | 0.187079 | cooking_query → cooking_recipe | cooking_recipe | 0 | 0 | 1 | RECOVERED |
| `slurp:devel:009968:audio-1490182854` | exposed | 0.261457 | cooking_query → general_quirky | cooking_recipe | 0 | 0 | 1 | RECOVERED |
| `slurp:devel:009978:audio-1501753701` | exposed | 0.187079 | cooking_query → cooking_recipe | cooking_recipe | 0 | 0 | 1 | RECOVERED |
| `slurp:devel:009999:audio-1501778625` | exposed | 0.147608 | cooking_query → cooking_recipe | cooking_recipe | 0 | 0 | 1 | RECOVERED |
| `slurp:devel:010017:audio-1490371035-headset` | exposed | 0.233457 | cooking_query → cooking_recipe | cooking_recipe | 0 | 0 | 1 | RECOVERED |
| `slurp:devel:010037:audio-1500386970-headset` | exposed | 0.159446 | cooking_query → cooking_recipe | cooking_recipe | 0 | 0 | 1 | RECOVERED |
| `slurp:devel:010218:audio-1502377622` | exposed | 0.216224 | cooking_query → iot_coffee | cooking_recipe | 0 | 0 | 1 | RECOVERED |
| `slurp:devel:010242:audio-1495370816-headset` | exposed | 0.157348 | cooking_query → cooking_recipe | cooking_recipe | 0 | 0 | 1 | RECOVERED |
| `slurp:devel:011819:audio--1505404383-headset` | exposed | 0.148629 | takeaway_query → recommendation_locations | recommendation_locations | 0 | 0 | 1 | RECOVERED |

**Realized contribution to the lock statistic**: 3 fires, 0 recovered, **3 damaged**, net
**−3 samples = −0.60 pp**. Bounded at ±3 samples (±0.60 pp) BY CONSTRUCTION, because only 3 of the
14 fires fall inside the unexposed 500.

On the prior-exposed 500 (no claim): 11 fires, **11 recovered, 0 damaged**, net +11.
Over all 1,000 descriptively: 11 recovered, 3 damaged, net +8.

**Loss-side disclosure, recorded not repaired.** The candidate-selection note records the
override's loss side as zero by construction and holding at zero in flight on both sealed DEV-100
bases. On the previously unexposed 500 it **did not hold**: all three fires damaged a
trajectory that would have been correct under v1. Two of the three are the same
`music_likeness → play_music` confusion at δ = 0.140362, sitting 0.000362 above the frozen bar.

### 5.4 Dispatch decomposition — three-way (v2 has three trajectory classes)

Unexposed 500:

| class | n | share | M0 | BLEND | M0 acc | BLEND acc | delta | W→C | C→W |
|---|---|---|---|---|---|---|---|---|---|
| retain_primary | 337 | 67.4% | 271 | 279 | 80.42% | 82.79% | +8 (+2.37 pp) | 9 | 1 |
| dead_direct_dispatch | 160 | 32.0% | 5 | 100 | 3.13% | 62.50% | +95 (+59.38 pp) | 97 | 2 |
| override_dispatch | 3 | 0.6% | 2 | 0 | 66.67% | 0.00% | −2 (−66.67 pp) | 0 | 2 |

Prior-exposed 500:

| class | n | share | M0 | BLEND | M0 acc | BLEND acc | delta | W→C | C→W |
|---|---|---|---|---|---|---|---|---|---|
| retain_primary | 323 | 64.6% | 253 | 259 | 78.33% | 80.19% | +6 (+1.86 pp) | 6 | 0 |
| dead_direct_dispatch | 166 | 33.2% | 5 | 108 | 3.01% | 65.06% | +103 (+62.05 pp) | 106 | 3 |
| override_dispatch | 11 | 2.2% | 0 | 11 | 0.00% | 100.00% | +11 (+100.00 pp) | 11 | 0 |

Pooled 1,000 (descriptive):

| class | n | share | M0 | BLEND | M0 acc | BLEND acc | delta | W→C | C→W |
|---|---|---|---|---|---|---|---|---|---|
| retain_primary | 660 | 66.0% | 524 | 538 | 79.39% | 81.52% | +14 (+2.12 pp) | 15 | 1 |
| dead_direct_dispatch | 326 | 32.6% | 10 | 208 | 3.07% | 63.80% | +198 (+60.74 pp) | 203 | 5 |
| override_dispatch | 14 | 1.4% | 2 | 11 | 14.29% | 78.57% | +9 (+64.29 pp) | 11 | 2 |

The two-way (retain vs all-dispatched) view the DEV-500 read published is also carried in the
verdict JSON under `profiles.subgroups_*_two_way`.

### 5.5 Field decomposition

Unexposed 500 — M0: scenario_exact 360, action_exact 308, scenario_action_exact 278, unparsed 2,
mean slot-F1 0.17098. BLEND: scenario_exact 426, action_exact 386, scenario_action_exact 379,
unparsed 2, mean slot-F1 0.20641.

Prior-exposed 500 — M0: scenario_exact 340, action_exact 307, scenario_action_exact 258,
unparsed 3, mean slot-F1 0.12225. BLEND: scenario_exact 413, action_exact 390,
scenario_action_exact 378, unparsed 0, mean slot-F1 0.15097.

### 5.6 Per-scenario accuracy, unexposed 500

| scenario | n | M0 | BLEND | M0 acc | BLEND acc | delta |
|---|---|---|---|---|---|---|
| alarm | 30 | 27 | 27 | 0.900 | 0.900 | +0 |
| audio | 2 | 1 | 2 | 0.500 | 1.000 | +1 |
| calendar | 33 | 12 | 21 | 0.364 | 0.636 | +9 |
| cooking | 9 | 1 | 5 | 0.111 | 0.556 | +4 |
| datetime | 33 | 27 | 29 | 0.818 | 0.879 | +2 |
| email | 33 | 27 | 30 | 0.818 | 0.909 | +3 |
| general | 33 | 1 | 6 | 0.030 | 0.182 | +5 |
| iot | 33 | 22 | 25 | 0.667 | 0.758 | +3 |
| lists | 32 | 26 | 28 | 0.812 | 0.875 | +2 |
| music | 23 | 13 | 13 | 0.565 | 0.565 | +0 |
| news | 32 | 25 | 29 | 0.781 | 0.906 | +4 |
| play | 32 | 0 | 26 | 0.000 | 0.812 | +26 |
| qa | 32 | 9 | 21 | 0.281 | 0.656 | +12 |
| recommendation | 32 | 0 | 23 | 0.000 | 0.719 | +23 |
| social | 33 | 25 | 26 | 0.758 | 0.788 | +1 |
| takeaway | 12 | 9 | 11 | 0.750 | 0.917 | +2 |
| transport | 33 | 22 | 27 | 0.667 | 0.818 | +5 |
| weather | 33 | 31 | 30 | 0.939 | 0.909 | **−1** |

The prior-exposed-500 per-scenario table is carried in the verdict JSON under
`profiles.per_scenario_exposed500`.

### 5.7 Top confusions

Unexposed 500 — M0: 222 errors over 135 distinct gold→predicted pairs (140 wrong-scenario, 82
right-scenario/wrong-action), 2 unparsed. Leading pairs: `play_music → music_play` 12,
`general_quirky → general_greet` 9, `calendar_set → calendar_createoradd` 8,
`recommendation_locations → recommendation_query` 7, `qa_factoid → qa_query` 7,
`cooking_recipe → cooking_createoradd` 6.

Unexposed 500 — BLEND: 121 errors over 90 distinct pairs (74 wrong-scenario, 47
right-scenario/wrong-action), 2 unparsed. Leading pairs: `general_quirky → general_greet` 9,
`general_quirky → general_query` 4, `general_quirky → qa_definition` 4,
`music_likeness → play_music` 3, `calendar_query → recommendation_events` 3,
`qa_factoid → qa_query` 3.

Full top-25 lists for both arms and both populations are in the verdict JSON under
`profiles.confusion_unexposed500` and `profiles.confusion_exposed500`.

### 5.8 Retrieval-reachability ceiling over the unexposed 500 (preregistration section 3)

**Charter disclosure, restated at every citation:** the literature-standard oracle/GT-prompt
ceiling requires gold-conditioned supply at RUNTIME, which this repository's immutable charter
forbids, so that arm was never flown. This analytic substitute bounds what RETRIEVAL could have
reached and is SILENT on what the frozen core would have answered given that supply.

Gold-bearing content facet present for 500 of 500 (absent for 0). Position in the full cosine
ordering: median 1, p10 1, p90 82, max 1,632, over 11,514 content facets. Recall@k:

| k | count | rate |
|---|---|---|
| 1 | 318 | 0.636 |
| 2 | 352 | 0.704 |
| 3 | 362 | 0.724 |
| **5 (frozen top_k)** | **372** | **0.744** |
| 8 | 389 | 0.778 |
| 10 | 396 | 0.792 |
| 16 | 408 | 0.816 |
| 32 | 433 | 0.866 |
| 64 | 443 | 0.886 |
| 128 | 470 | 0.940 |

4,500 vectorised cosines were cross-checked against `kb_policy._cosine` and all agreed to 1e-9.
Value vectors stayed SEALED.

### 5.9 Scale stability against the DEV-500 tier — the question this tier exists to answer

| | DEV-500 unexposed 400 (v1 cell) | DEV-1000 unexposed 500 (v2 candidate) |
|---|---|---|
| n | 400 | 500 |
| M0 | 210 (52.50%) | 278 (55.60%) |
| BLEND | 289 (72.25%) | 379 (75.80%) |
| delta | +79 = **+19.75 pp** | +101 = **+20.20 pp** |
| 90% CI | [+16.50, +23.00] | [+17.20, +23.40] |
| 95% CI | [+15.75, +23.75] | [+16.60, +24.00] |
| sigma-hat | 2.0563 pp | 1.8986 pp |
| W→C / C→W | 81 / 2 | 106 / 5 |

Margin change: **+0.45 pp**. The DEV-1000 point estimate lies inside the DEV-500 90% CI; the
DEV-500 point estimate lies inside the DEV-1000 90% CI; the two 90% intervals overlap.

**Registered caveat, carried as registered:** the two populations are disjoint (NEW500 was
unexposed at both tiers; NEW400 sits inside this tier's prior-exposed half), but the ARMS DIFFER —
DEV-500 flew the v1 cell and DEV-1000 flew v2 = v1 plus the retain-override. The override's
realized contribution to the unexposed-500 statistic is reported in §5.3 and is bounded at 3
samples (−3 realized). So this is a comparison between two cells that differ by a mechanism of
bounded size, not two runs of the same cell.

## 6. Standing disclosures

1. **Fit-not-validated δ.** The δ ≥ 0.14 retain-override bar was FIT on exposed data (DEV-100
   r4/r5 and DEV-500 NEW400) and frozen on 2026-08-25 before this read. The unexposed-500 read
   therefore validates the bar AND confirms the cell in a single touch — legitimate only because
   the bar was frozen before the read and the fit is declared (candidate-selection note §3).
2. **Preregistration erratum, recorded not repaired.** Preregistration §2 quotes `e9a7b7fe…d853`
   as the DEV-1000 load-split identity; that value is DEV-100's run identity, a drafting copy
   error. The correct DEV-1000 load-split identity is `8580d199…3c84`, which is what this read
   pins and asserts and what the campaign row's split-identity cell carries. The
   receipt-integrity value `9fb44e33…243b` quoted alongside it is correct. The erratum moves NO
   sample.
3. **Stale label inside the imported bootstrap wrapper.** `dev100_reviewer_audit.bootstrap_gain`
   emits a hard-coded `resampling` string that reads "over the 100 DEV-100 ids". The resampling
   universe is in fact whatever `sample_ids` the caller passes — here the 500 unexposed ids for
   the primary, the 500 exposed ids and the 1,000 pooled ids for the secondaries. The string is a
   stale description in a module frozen against a sealed read and is reported here rather than
   edited; the arithmetic is unaffected.
4. **Stale label inside the imported ceiling helper.** `dev500_confirmatory_read.reachability_ceiling`
   hard-codes its original caller's population label. The arithmetic is population-agnostic; the
   verdict carries the returned label under
   `population_label_as_returned_by_the_imported_helper` and the corrected label under
   `population`.
5. **Scope, binding (preregistration §5).** A LOCK records the cell as the baseline version for
   large-scale experiments. It does NOT authorize test contact, a superiority claim, a
   generalization claim, or any Stage-3 activity. FINAL60 and test remain untouched.

## 7. Zero-contact proof

- Registered contacts: frozen core **0**, pinned-tool embedding **0**, tokenizer **0**.
- In-process offline guard (`analysis.dev100_reviewer_audit.arm_offline_guard`, reused verbatim)
  was armed **before any input was opened**; it makes every outbound socket connection raise and
  counts the attempts. **Outbound connection attempts: 0. Targets: none.**
- Resident decoder service `saea-np8-dev100-r6-base` (unit active, port 8080) was never started,
  stopped, probed, reconfigured or contacted. Its durable log
  `/home/chao/runs/services/SAEA-SN-Q4KM-NP8-BASE-DEV100-20260824T120910Z/server.log` measured
  **5,847,465 bytes / sha256 `8a3a9b19227cf228585f77910eba1d7ee10ed82eb6b25e6a66f1d6f23d4fb590`
  BEFORE the read and byte-length- and hash-IDENTICAL AFTER it.**
- Every pinned input hash matched at load; no fail-closed stop was triggered.

## 8. Campaign spend re-summed from the two committed reports

| | M0 | BLEND(v2) | campaign total | ceiling |
|---|---|---|---|---|
| frozen-core contacts | 1,002 | 1,343 | **2,345** | 3,400 |
| embedding tool contacts | 0 | 1,002 | **1,002** | 1,200 |
| metered audio seconds | 2,888.3772 | 3,854.8629 | **6,743.2402** | 9,000 |
| GPU-active hours | 0.537458 | 1.213486 | **1.750944** | 3.0 |

Inside every ceiling. **This read adds 0 / 0 / 0 / 0.0.**

Mechanical cross-checks re-verified at load: the BLEND dispatch decomposition closes exactly
(660 retain-primary + 326 dead-direct dispatch + 14 override dispatch = 1,000; 340 dispatched;
674 direct labels recovered), the branch-only property holds with zero supply mismatches, the M0
arm is single-contact throughout with zero override fires, and every sealed response text
re-hashes to its sealed `response_sha256` on all 1,000 samples of both arms.
