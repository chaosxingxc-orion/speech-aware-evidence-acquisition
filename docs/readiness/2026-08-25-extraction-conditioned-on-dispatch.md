# EXTRACTION CONDITIONED ON DISPATCH — the supply cannot be judged where it was never delivered (2026-08-25)

**Exposure row:** `SAEA-SN-MF-EXTRACTION-CONDITIONED-ON-DISPATCH`, registered `849a09c7` BEFORE any
computation.
**Module:** `src/speech_aware_evidence_acquisition/analysis/extraction_conditioned_on_dispatch.py`.
**Receipt:** `docs/checks/speech-aware-evidence-acquisition/2026-08-25-extraction-conditioned-on-dispatch/read-report.json`,
sha256 `7662fbc381e6994f3c71422154a0facfc86c0e99b656cf91670577036a337525`.
**Spend exactly as registered:** 0 frozen-core contacts, 0 embedding-tool contacts, 0 tokenizer
contacts, 0 HTTP or socket requests, 0 audio seconds, 0.0 GPU hours, 0 new dependencies.
`arm_offline_guard()` was armed before the first input was opened and recorded **0 outbound
connection attempts against zero targets**. The resident np2 llama-server (pid 38623, port 8090)
was not contacted, probed, reconfigured or stopped. No knob changed; no line under `rails/`
touched.

---

## 0. The defect under test

`docs/readiness/2026-08-25-matching-vs-extraction-read.md` (commit `d4c75c7a`, receipt sha256
`378757b5…6523`) partitioned each population by the two arms' **matching** outcome and concluded
that, conditioned on matching, the supply does not serve extraction. **Its fidelity gate passed to
full float precision and its arithmetic closes. Every one of its four-cell contribution figures is
reproduced exactly by this reading** (§7). That work is sound as far as it goes.

**But it never conditioned on whether the trajectory actually RECEIVED SUPPLY.** In this controller
a RETAINED trajectory stops at contact 0 and is handed no evidence at all; only a DISPATCHED
trajectory receives supply. A cell dominated by retained trajectories cannot exhibit a supply
effect — not because the supply fails, but because there was none.

This reading crosses the four matching cells with the DISPATCH/RETAIN branch **as the controller
actually decided it**, and the suspicion is confirmed on both carriers.

---

## 1. FIDELITY GATE — **PASS**

Identical to the landed read's gate: the four sealed `*-outputs.jsonl` files re-scored through the
same imported path, required to reproduce the landed aggregates to the sample and to full float
precision. All ten targets reproduced (SLURP unexposed M0 278 / 0.17097619047619048, BLEND 379 /
0.20641428571428572; SLURP exposed M0 258 / 0.12224761904761905, BLEND 378 / 0.15097142857142856;
A2T tool accuracy 62 / 63, exact match 29 / 29, empty call 14 / 3). This module's scorer was also
cross-checked sample by sample against `dev500_confirmatory_read.score_arm`, and the A2T adapter
against `toolcall_scoring.score_item`.

---

## 2. Where the branch comes from — READ, never re-derived

| carrier | artifact | sha256 | predicate |
|---|---|---|---|
| SLURP | `$SPEECHRL_DATA_DIR/runs/SAEA-DEV1000-BASELINE-LOCK/attempt-20260825T054707Z-dev1000blend/arm2-blend-mechanical.json` | `e55b6632d85a0037fb928d565fb2ef1b40c987c915dd98a9f2599d78113c828e` | DISPATCH `contacts == 2` / RETAIN `contacts == 1` |
| Audio2Tool | `$SPEECHRL_DATA_DIR/runs/SAEA-A2T-G1/attempt-20260825T144405Z-a2tg1blend/arm2-blend-mechanical.json` | `59458c491368a117721041e4ba1538549f3e1e28bdb342e4927703ad5892644e` | DISPATCH `not retained_primary` |

The SLURP bytes are the exact ones `dev1000_lock_read.ARM_PINS` already pins, and
`load_per_sample_mechanical` cross-checks them against the committed
`arm2-blend-mechanical-report.json` (`c3ed0169…5930`) retain-override block and the per-sample
contact counts — so the branch is proved twice before it is used once. The A2T hash is the value the
landed A2T gold-absence diagnosis report already carries; every retained A2T trajectory was
additionally asserted to carry an **empty** `fusion_selected_value_ids` list, i.e. the record's own
statement that it received nothing.

> **BRANCH ASYMMETRY, carried at every citation.** DISPATCH is a property of the **BLEND arm alone**.
> The M0 arm is single-contact and supplies nothing, so "the dispatched trajectories" means "the
> trajectories the BLEND controller chose to supply", scored under **both** arms on the same sample
> ids. A retained BLEND trajectory answers with its **own contact-0 direct decode**, which is a
> different decode of the same prompt from the M0 arm's — so a retained pair can still differ
> through decode variance alone. §9 measures that channel rather than assuming it away.

> **CAVEAT — DOUBLE CONDITIONING.** Cell membership is a function of the arms' matching OUTCOMES
> **and** of a POST-TREATMENT branch decision (the dispatch decision is itself an outcome of the
> controller acting on the trajectory), so every conditioned number here carries selection
> (collider) bias **twice over**. These are **DESCRIPTIVE MECHANISM READINGS, NEVER EFFECT SIZES**,
> and a small-n cell is a mechanism reading whatever its interval says. Both rules were fixed in the
> ledger row before any n was known.

> **SLURP OVERRIDE CAVEAT.** The flown BLEND arm is the v2 policy, whose delta retain-override can
> dispatch a trajectory whose direct label *was* recovered. The locked v1 cell would have RETAINED
> those fires. This reading takes the branch **as the controller actually decided it**, because the
> answers being scored are the flown v2 answers; the three-way trajectory-class split is published
> below so the v1 reading can be recovered from the same table.

### Two premises in the brief, corrected against the record

- The brief expected SLURP unexposed-500 to show **160 dispatched, M0 correct on 5**. The flown v2
  arm dispatched **163** (160 `dead_direct_dispatch` + 3 `override_dispatch`); 160 is the locked-v1
  reachable set. M0 was correct on **7** of the 163, not 5.
- The brief expected A2T's 15 dispatched to be **all 15 M0-wrong**. Measured: **14 of 15**. One
  dispatched trajectory had M0 correct (`m0_only_matched|dispatched`, n = 1). This does not change
  the conclusion — that trajectory had BLEND *wrong*, so the both-matched cell is still empty.

---

## 3. SLURP — DEV-1000-NEW500 (500 UNEXPOSED)

> **SECONDARY READING on the LOCKED baseline's population.** Every conditioned statistic in this
> section is a SECONDARY reading and **MUST NOT be used to revise, re-tune or restate the LOCK**,
> which stands exactly as landed at `d9fef537`. It is descriptive.

### The eight-cell cross-tabulation (SECONDARY)

| matching cell | n | **DISPATCHED** | **RETAINED** | dispatched share | trajectory classes |
|---|---|---|---|---|---|
| **both matched** | **273** | **3** | **270** | **1.10 %** | dead-direct 3, retain 270 |
| only BLEND matched | 106 | 97 | 9 | 91.51 % | dead-direct 97, retain 9 |
| only M0 matched | 5 | 4 | 1 | 80.00 % | dead-direct 2, override 2, retain 1 |
| neither matched | 116 | 59 | 57 | 50.86 % | dead-direct 58, override 1, retain 57 |
| **population** | **500** | **163** | **337** | 32.60 % | dead-direct 160, override 3, retain 337 |

Both marginals close against the population and against the branch record.

**The landed document's conditioned headline cell contains 3 supplied trajectories out of 273.**
270 of 273 (98.90 %) received no evidence whatsoever.

### Dispatched versus retained, paired on the same samples (SECONDARY)

| | **DISPATCHED (n = 163)** | **RETAINED (n = 337)** |
|---|---|---|
| matching M0 → BLEND | 7 → 100 (**+57.0552 pp**, CI90 [+50.3067, +63.8037]) | 271 → 279 (+2.3739 pp, CI90 [+0.8902, +3.8576]) |
| macro `slot_f1_exact_mean` | 0.220552 → 0.314943, **+9.4391 pts**, CI90 **[+4.3558, +14.5194]**, CI95 **[+3.4794, +15.6179]** | 0.146997 → 0.153921, +0.6924 pts, CI90 [−0.6924, +2.0772], CI95 [−0.8902, +2.3739] |
| micro `slot_f1_exact` P / R / F1, M0 | 0.351562 / 0.286624 / 0.315789 (TP/FP/FN 45/83/112) | 0.254167 / 0.183735 / 0.213287 (61/179/271) |
| micro `slot_f1_exact` P / R / F1, BLEND | 0.525000 / 0.401274 / 0.454874 (63/57/94) | 0.263374 / 0.192771 / 0.222609 (64/179/268) |
| micro `slot_f1_exact` ΔF1 | **+13.9084 pts** | +0.9322 pts |
| official `slu_f1` micro P / R / F1, M0 | 0.469283 / 0.394682 / 0.428761 | 0.407331 / 0.306558 / 0.349832 |
| official `slu_f1` micro P / R / F1, BLEND | 0.641896 / 0.506685 / 0.566332 | 0.423374 / 0.322840 / 0.366335 |
| official `slu_f1` ΔF1 | **+13.7570 pts**, CI90 **[+8.8840, +18.6695]**, CI95 **[+7.9762, +19.7020]** | +1.6502 pts, CI90 [+0.2208, +3.1577], CI95 [−0.0344, +3.4216] |

Bold intervals exclude zero. **The dispatched stratum is still matching-confounded** (matching moves
+57 pp inside it), which is exactly why §7 restricts to concordant matching cells.

### The eight cells, extraction (SECONDARY)

| cell | n | macro Δ (pts) | CI90 | official `slu_f1` Δ (pts) | CI90 |
|---|---|---|---|---|---|
| both matched \| **dispatched** | **3** | +22.2222 | [0.0000, +44.4444] | +6.3063 | [0.0000, +21.2121] |
| both matched \| retained | 270 | −0.3704 | [−1.7284, +0.9877] | −0.0049 | [−1.0258, +1.0324] |
| blend-only \| **dispatched** | 97 | +11.0506 | **[+3.3677, +19.0034]** | +12.6958 | **[+6.4738, +19.3592]** |
| blend-only \| retained | 9 | +11.1111 | [0.0000, +33.3333] | +20.3391 | [−0.7243, +45.4545] |
| m0-only \| **dispatched** | 4 | 0.0000 | [0, 0] | 0.0000 | [0, 0] |
| m0-only \| retained | 1 | +100.0000 | [+100, +100] | +100.0000 | [+100, +100] |
| neither \| **dispatched** | **59** | **+6.7797** | **[+1.6949, +11.8644]** | **+15.2312** | **[+8.2127, +22.9778]** |
| neither \| retained | 57 | +2.3392 | [0.0000, +4.6784] | +6.7547 | **[+0.8247, +13.7973]** |

`n = 1`, `n = 3` and `n = 4` are MECHANISM readings and nothing else.

**The cleanest available evidence that the supply serves extraction is `neither|dispatched`**
(n = 59): both arms failed matching, so no matching movement can explain anything, and the supply
was actually delivered. Macro slot-F1 **+6.7797 pts** and official SLU-F1 **+15.2312 pts**, both
CI90 excluding zero.

---

## 4. SLURP — DEV-500 (500 PRIOR-EXPOSED)

> SECONDARY READING on the nested prior-exposed half; **never pooled into the lock claim.**

| matching cell | n | **DISPATCHED** | **RETAINED** | dispatched share |
|---|---|---|---|---|
| **both matched** | **255** | **2** | **253** | **0.78 %** |
| only BLEND matched | 123 | 117 | 6 | 95.12 % |
| only M0 matched | 3 | 3 | 0 | 100.00 % |
| neither matched | 119 | 55 | 64 | 46.22 % |
| **population** | **500** | **177** | **323** | 35.40 % |

Trajectory classes: dead-direct 166, override 11, retain 323.

| | **DISPATCHED (n = 177)** | **RETAINED (n = 323)** |
|---|---|---|
| matching | 5 → 119 (**+64.4068 pp**, CI90 [+58.1921, +70.6215]) | 253 → 259 (+1.8576 pp, CI90 [+0.6192, +3.0960]) |
| macro `slot_f1_exact_mean` | 0.157466 → 0.235782, **+7.8316 pts**, CI90 **[+3.6911, +12.0500]**, CI95 **[+2.9567, +12.8787]** | 0.102949 → 0.104497, +0.1548 pts, CI90 [−0.6192, +0.8772] |
| micro `slot_f1_exact` M0 → BLEND | 0.256410 → 0.416988 (**+16.0578 pts**); TP/FP/FN 35/88/115 → 54/55/96 | 0.156134 → 0.161654 (+0.5520 pts); 42/185/269 → 43/178/268 |
| official `slu_f1` micro | 0.398240 → 0.551693, **+15.3453 pts**, CI90 **[+9.7455, +21.0429]**, CI95 **[+8.5961, +22.1995]** | 0.342989 → 0.334524, −0.8465 pts, CI90 [−2.3246, +0.5800] |

Eight-cell extraction (macro Δ / official SLU Δ, CI90):

| cell | n | macro Δ | CI90 | official Δ | CI90 |
|---|---|---|---|---|---|
| both \| **dispatched** | **2** | 0.0000 | [0, 0] | 0.0000 | [0, 0] |
| both \| retained | 253 | −0.5270 | [−1.3175, 0.0000] | **−1.6442** | **[−3.2420, −0.1396]** |
| blend-only \| **dispatched** | 117 | +12.0757 | **[+6.7922, +17.6646]** | +18.1825 | **[+11.8384, +24.8903]** |
| blend-only \| retained | 6 | 0.0000 | [0, 0] | −8.6263 | [−25.6456, +2.9331] |
| m0-only \| **dispatched** | 3 | 0.0000 | [0, 0] | −10.0000 | [−50, 0] |
| m0-only \| retained | 0 | — | — | — | — |
| neither \| **dispatched** | 55 | −0.4848 | [−6.5455, +5.5758] | +4.7128 | [−5.1298, +15.8581] |
| neither \| retained | 64 | +2.8646 | **[+0.7812, +5.7292]** | +3.6553 | **[+0.4535, +7.4503]** |

**Two findings that must be reported together.**

1. The landed document's single most-cited negative result — "the one interval in this whole reading
   that separates from zero inside a conditioned cell, and it points the wrong way", the exposed
   both-matched official SLU-F1 at −1.6351 pts, CI90 [−3.2291, −0.1108] — resolves **entirely into
   the 253 UNSUPPLIED trajectories** (−1.6442 pts, CI90 [−3.2420, −0.1396]). The 2 supplied
   trajectories in that cell moved **0.0000**. It is not evidence about the supply.
2. **Honesty in the other direction:** on the exposed half the *dispatched* concordant cells do
   **not** reproduce the unexposed half's positive supply effect. `neither|dispatched` (n = 55) is
   −0.4848 macro pts and +4.7128 official pts, both CI90 straddling zero. The unexposed half's
   `neither|dispatched` result **does not replicate here**.

---

## 5. Audio2Tool — A2T-G1-104 (104 EXPOSED)

> **SECONDARY READING on an EXPOSED population**: every number here is a secondary reading and can
> never be a campaign claim; the claim interval needs n ≥ 400 UNEXPOSED and belongs to G2. n = 104
> is below the campaign plan's own power floor.

### The eight-cell cross-tabulation

| matching cell | n | **DISPATCHED** | **RETAINED** | dispatched share |
|---|---|---|---|---|
| **both matched** | **60** | **0** | **60** | **0.00 %** |
| only BLEND matched | 3 | 3 | 0 | 100.00 % |
| only M0 matched | 2 | 1 | 1 | 50.00 % |
| neither matched | 39 | 11 | 28 | 28.21 % |
| **population** | **104** | **15** | **89** | 14.42 % |

**The landed document's A2T conditioned headline cell contains ZERO dispatched trajectories.** Not
one of the 60 doubly-matched samples was ever handed any evidence.

### Dispatched versus retained

| | **DISPATCHED (n = 15)** | **RETAINED (n = 89)** |
|---|---|---|
| `tool_accuracy` | 1 → 3 (+13.3333 pp, CI90 [−6.6667, +33.3333]) | 61 → 60 (−1.1236 pp) |
| `exact_match` | 0 → 1 (+6.6667 pp, CI90 [0.0000, +20.0000]); McNemar 1 W→C / 0 C→W, exact p = 1.0 | 29 → 28 (−1.1236 pp); McNemar 0 W→C / 1 C→W |
| slot micro P / R / F1, M0 | 0.000000 / 0.000000 / 0.000000 (TP 0, expected 20, predicted 4) | 0.373737 / 0.637931 / 0.471338 (TP 74, expected 116, predicted 198) |
| slot micro P / R / F1, BLEND | 0.153846 / 0.100000 / 0.121212 (TP 2, expected 20, predicted 13) | 0.339535 / 0.629310 / 0.441088 (TP 73, expected 116, predicted 215) |
| **slot micro ΔF1** | **+12.1212 pts**, CI90 [0.0000, +23.0769], CI95 [0.0000, +25.0000] | **−3.0250 pts**, CI90 **[−6.1940, −0.5941]**, CI95 **[−6.9087, −0.2971]** |
| empty calls | 12 → 3 | 2 → 0 |
| unparsed | 2 → 0 | 2 → 0 |

**The sign of the A2T extraction effect inverts on the dispatch axis.** Where the supply was
delivered it is **+12.1212 slot micro-F1 points**; where it was not, it is **−3.0250 points with a
CI90 excluding zero**. The landed aggregate of −2.5781 points is the weighted blend of the two, and
the retained side dominates it because the retained side is 89 of 104.

### The eight cells

| cell | n | `exact_match` M0 → BLEND | slot micro-F1 M0 → BLEND (Δ pts) | predicted triples | TP |
|---|---|---|---|---|---|
| both \| **dispatched** | **0** | — | — | — | — |
| both \| retained | 60 | 28 → 28 (0) | 0.583784 → 0.577540 (−0.6244) | 111 → 113 | 54 → 54 |
| blend-only \| **dispatched** | 3 | 0 → 1 (+1) | 0.000000 → 0.285714 (+28.5714) | 0 → 4 | 0 → 1 |
| blend-only \| retained | 0 | — | — | — | — |
| m0-only \| **dispatched** | 1 | 0 → 0 | 0.000000 → 0.000000 (0.0000) | 2 → 0 | 0 → 0 |
| m0-only \| retained | 1 | 1 → 0 (−1) | 1.000000 → 0.000000 (−100.0000) | 1 → 0 | 1 → 0 |
| neither \| **dispatched** | 11 | 0 → 0 | 0.000000 → 0.076923 (+7.6923) | 2 → 9 | 0 → 1 |
| neither \| retained | 28 | 0 → 0 | 0.299213 → 0.265734 (−3.3478) | 86 → 102 | 19 → 19 |

`n = 1` and `n = 3` are MECHANISM readings and nothing else.

---

## 6. The A2T 26 extra triples — located by counting

The landed document reports the A2T slot micro-F1 aggregate at **−2.5781 points**, with BLEND
emitting **26 more predicted argument triples** (202 → 228) for exactly **one** more true positive
(74 → 75), and attributes this to "the empty-call repair working as designed on the matching axis
and paying for it on the extraction axis". Both raw counts reproduce exactly. Their location does
not support the attribution.

| stratum | n | trajectories moved | **Δ predicted triples** | **Δ true positives** |
|---|---|---|---|---|
| **DISPATCHED** | 15 | 5 | **+9** (34.62 %) | **+2** |
| **RETAINED** | 89 | 5 | **+17** (65.38 %) | **−1** |
| total | 104 | 10 | **+26** ✓ | **+1** ✓ |

Every mover, individually:

| sample id | stratum | predicted triples | Δ | TP | Δ | expected | M0 empty / unparsed | BLEND empty / unparsed |
|---|---|---|---|---|---|---|---|---|
| `tier1_direct:001631` | **dispatched** | 2 → 0 | −2 | 0 → 0 | 0 | 0 | no / no | **yes** / no |
| `tier3_multi_intent:000879` | **dispatched** | 0 → 5 | +5 | 0 → 1 | **+1** | 1 | yes / yes | no / no |
| `tier4_implicit:000655` | **dispatched** | 0 → 2 | +2 | 0 → 0 | 0 | 2 | yes / no | no / no |
| `tier4_implicit:003312` | **dispatched** | 0 → 2 | +2 | 0 → 0 | 0 | 1 | yes / no | no / no |
| `tier5_needle:000061` | **dispatched** | 0 → 2 | +2 | 0 → 1 | **+1** | 2 | yes / yes | no / no |
| `tier1_direct:001432` | retained | 2 → 3 | +1 | 0 → 0 | 0 | 0 | no / no | no / no |
| `tier5_needle:003841` | retained | 2 → 3 | +1 | 2 → 2 | 0 | 3 | no / no | no / no |
| `tier8_intent_blending:000192` | retained | 0 → 5 | **+5** | 0 → 0 | 0 | 1 | yes / yes | no / no |
| `tier8_intent_blending:000441` | retained | 1 → 0 | −1 | 1 → 0 | **−1** | 1 | no / no | no / no |
| `tier8_intent_blending:000713` | retained | 0 → 11 | **+11** | 0 → 0 | 0 | **0** | yes / yes | no / no |

**The verdict on this question is decided by two rows.** `tier8_intent_blending:000713` alone
contributes **+11 of the 26** extra triples (42.3 %) against **zero** expected triples — eleven pure
false positives — and it is a **RETAINED** trajectory that received no evidence at all. Together
with `tier8_intent_blending:000192` (+5 against 1 expected, also retained), **two unsupplied samples
account for 16 of the 26 extra triples (61.5 %)**.

Both of those retained samples went from an *empty, unparsed* M0 answer to a *parsed* BLEND answer —
i.e. the empty-call/unparsed repair happened there **without any supply**, purely because BLEND's own
contact-0 decode differed from M0's. On the retained set the counts are empty 2 → 0 and unparsed
2 → 0, delivered by decode variance alone.

The empty-call repair itself *is* mostly a supply effect: 9 of the 11 net empty-call repairs occur in
the dispatched stratum (12 → 3), against 2 in the retained stratum (2 → 0). But the *triples* those
repairs emitted are mostly not: the dispatched repairs added 9 net triples carrying **+2** true
positives, while the retained decode-variance repairs added 17 triples carrying **−1**.

**So "the empty-call repair pays for itself on the extraction axis" is a mis-attribution for the
majority of the effect.** The precision loss the landed document prices at −2.5781 points is
principally the behaviour of trajectories the supply never touched.

---

## 7. The (a)/(b) decomposition, RE-DONE with dispatch in it

The landed joint decomposition is refined, not replaced. **(a)** is unchanged — the two discordant
matching cells. The landed **(b)** ("matching-independent") term is split by whether evidence was
actually delivered:

- **SUPPLY-ATTRIBUTABLE** — concordant matching cells ∩ **DISPATCHED**. The only place where evidence
  reached the core with matching status held fixed, and therefore the only place a supply effect on
  extraction can appear at all.
- **DECODE-VARIANCE / UNSUPPLIED RESIDUE** — concordant matching cells ∩ **RETAINED**. Handed no
  evidence; the BLEND arm answered with its own contact-0 direct decode.

### SLURP DEV-1000-NEW500 (UNEXPOSED) — macro `slot_f1_exact_mean`, aggregate **+3.5438 pts**

| term | cells | n | cell Δ (pts) | contribution (pts) | share of \|total\| |
|---|---|---|---|---|---|
| **(a) matching-attributable** | the two discordant cells | 111 | +11.4586 | **+2.5438** | **71.78 %** |
| **(b1) supply-attributable** | concordant ∩ dispatched | 62 | +7.5269 | **+0.9333** | **26.34 %** |
| **(b2) decode-variance / unsupplied residue** | concordant ∩ retained | 327 | +0.1019 | **+0.0667** | 1.88 % |
| aggregate | | 500 | | **+3.5438** | closes (residual −6.9 × 10⁻¹⁸) |

**(a) still dominates, exactly as the landed document found — that finding survives untouched.**
But the landed (b) of +1.0000 pts is recovered here as +0.9333 + 0.0667, i.e. **93.33 % of the
matching-independent residue is SUPPLY-ATTRIBUTABLE**, not a diffuse effect on already-wrong intents.

### SLURP DEV-500 (PRIOR-EXPOSED) — aggregate **+2.8724 pts**

| term | n | cell Δ (pts) | contribution (pts) | share of \|total\| |
|---|---|---|---|---|
| **(a) matching-attributable** | 126 | +11.2132 | **+2.8257** | **94.85 %** |
| **(b1) supply-attributable** | 57 | −0.4678 | **−0.0533** | 1.79 % |
| **(b2) unsupplied residue** | 317 | +0.1577 | **+0.1000** | 3.36 % |
| aggregate | 500 | | **+2.8724** | closes (residual −3.5 × 10⁻¹⁸) |

On the exposed half the supply-attributable term is **slightly negative and does not replicate the
unexposed half's +0.9333**. Reported as it came out.

### Audio2Tool — `exact_match`, aggregate **0.0000 pp**

| term | n | contribution (pp) |
|---|---|---|
| (a) matching-attributable | 5 | **0.0000** (the two discordant singletons cancel: +0.9615 and −0.9615) |
| (b1) supply-attributable | 11 | **0.0000** |
| (b2) unsupplied residue | 88 | **0.0000** |
| aggregate | 104 | **0.0000**, closes exactly |

### Audio2Tool — macro slot-F1 mean, aggregate **−0.2885 pts**

| term | n | cell Δ (pts) | contribution (pts) | share of \|total\| |
|---|---|---|---|---|
| **(a) matching-attributable** | 5 | −10.0000 | **−0.4808** | **51.72 %** |
| **(b1) supply-attributable** | 11 | **+3.0303** | **+0.3205** | 34.48 % |
| **(b2) unsupplied residue** | 88 | −0.1515 | **−0.1282** | 13.79 % |
| aggregate | 104 | | **−0.2885** | closes exactly |

The landed document's own (b) of +0.1923 is recovered exactly as +0.3205 − 0.1282. **The supply
term is POSITIVE; the negative half of (b) belongs to the unsupplied trajectories.**

**Which dominates, per carrier:** matching-attributable dominates on all three populations. The
change is in second place: on the SLURP unexposed half second place is the **supply** term
(+0.9333 pts, 26.34 %); on the exposed half both remaining terms are near zero; on A2T's slot-F1
mean second place is the **supply** term too (+0.3205 pts, 34.48 %), and it is positive.

### Reconstruction check against the landed document

Every landed four-cell contribution is recovered by summing this reading's eight cells:

| population | landed both-matched | recovered | landed neither-matched | recovered | landed blend-only | recovered | landed m0-only | recovered |
|---|---|---|---|---|---|---|---|---|
| SLURP unexposed | −0.0667 | **−0.0667** (= +0.1333 dispatched − 0.2000 retained) | +1.0667 | **+1.0667** (= +0.8000 + 0.2667) | +2.3438 | **+2.3438** | +0.2000 | **+0.2000** |
| SLURP exposed | −0.2667 | **−0.2667** (= 0.0000 − 0.2667) | +0.3133 | **+0.3133** (= −0.0533 + 0.3667) | +2.8257 | **+2.8257** | 0.0000 | **0.0000** |

**The landed arithmetic is confirmed to the digit. Only its interpretation changes.** Note the first
row in particular: the landed "in the cell where matching already succeeds, the supply contributes
−0.0667" is **+0.1333 from the 3 trajectories the supply actually reached** and **−0.2000 from the
270 it did not**.

---

## 8. The matching axis, as a coherence check

All matching movement lands in the matching-attributable term by construction, and it does:
+20.2000 pp (SLURP unexposed), +24.0000 pp (SLURP exposed), +0.9615 pp (A2T), with both other terms
exactly 0.0000 pp in every case. The partition is coherent.

---

## 9. The decode-variance channel, measured here rather than imported

Retained trajectories received **no evidence**, so any arm-to-arm difference among them is decode
variance between two separate runs of the same prompt. Measured directly by response-text identity:

| population | retained n | byte-identical response text | **divergent text** | divergence rate | matching-outcome flips | slot-F1 flips |
|---|---|---|---|---|---|---|
| SLURP unexposed | 337 | 287 | **50** | **14.84 %** | 10 | 11 |
| SLURP exposed | 323 | 269 | **54** | **16.72 %** | 6 | 5 |
| Audio2Tool | 89 | 80 | **9** | **10.11 %** | 1 | 2 (exact-match flips: 1) |

This is the channel the A2T G1 campaign estimated at "about 1.9 pp of score noise on 104 samples"
(`docs/readiness/2026-08-25-a2t-admission-scale-sweep.md` §8), now measured on each population's own
retained set. **Everything inside a retained cell lives in this channel**, including:

- SLURP unexposed retained: matching +2.3739 pp, official SLU-F1 +1.6502 pts (CI90 lower bound
  +0.2208, but CI95 straddles zero);
- SLURP exposed retained: matching +1.8576 pp, official SLU-F1 −0.8465 pts;
- A2T retained: `exact_match` −1.1236 pp, slot micro-F1 −3.0250 pts (CI90 excludes zero).

Two mechanical notes so these are not over-read. **First**, a CI90 that excludes zero inside a
retained cell does not make it a method effect — the trajectories were unsupplied, so it is a
statement about how much two decodes of the same prompt differ at that n. **Second**, on A2T the
retained slot micro-F1 moves −3.0250 pts while only **2** of the 89 retained samples have a divergent
per-sample slot F1: the micro metric is a corpus ratio, so 17 extra predicted triples (16 of them
from two samples with 0 and 1 expected triples) depress corpus precision without changing those
samples' own per-sample F1 at all. The interval is carried by a handful of samples and is a mechanism
reading.

Conversely — and this must be said just as plainly — **no dispatched-cell movement is written off as
decode variance here.** The dispatched cells carry the supply, and their movement is reported as a
supply reading subject to the double-conditioning caveat.

---

## 10. VERDICT — is the landed document vacuous, sound, or inverted?

### Audio2Tool — **VACUOUS on the conditioned cell, INVERTED on the slot micro-F1 mechanism claim**

- **VACUOUS.** The conditioned headline cell (both matched, n = 60) contains **0 dispatched
  trajectories**. "Conditioned on matching, extraction does not move" is, on this carrier, a
  statement about 60 trajectories that were never given any evidence. It carries no information
  about the supply — not weak information, none.
- **INVERTED.** The landed "the supply's only measurable extraction effect is −2.5781 slot micro-F1
  points" reverses sign on the axis that matters: **+12.1212 pts on the dispatched 15**, **−3.0250
  pts (CI90 excluding zero) on the unsupplied 89**. And 17 of the 26 extra predicted triples — 16 of
  them from two samples — sit in the retained stratum.
- What survives: the exact-match aggregate really is a genuine zero in every cell, and the gap
  arithmetic (Δgap = Δtool_accuracy − Δexact_match = +0.9615 pp) is untouched.

### SLURP — **VACUOUS on the conditioned cell; the (a)-dominance finding SOUND; the (b) attribution INVERTED on the unexposed half**

- **VACUOUS.** The conditioned headline cell is **98.90 %** unsupplied on the unexposed half
  (270/273) and **99.22 %** on the exposed half (253/255). It cannot show a supply effect.
  This is not bad luck: it is **the policy form**. The alpha veto makes `retain ==
  direct-label-recovered` a structural property (worst-case margin 1 − 2α = +0.10 at the frozen
  α = 0.45), so a trajectory whose contact-0 decode already recovered a label — which is what being
  matched almost always requires, since BLEND's retained answer *is* that decode — is **never**
  dispatched. The both-matched cell is unsupplied **by construction**, and no amount of n would
  change that.
- **SOUND.** (a) matching-attributable is **71.78 %** (unexposed) and **94.85 %** (exposed) of the
  aggregate extraction gain, unchanged to the digit. The landed headline "the SLURP aggregate
  extraction gain is mostly the matching gain" **stands**.
- **INVERTED.** The landed reading of the residual — that it "comes almost entirely from the
  neither-matched cell" and that "the supply adds nothing on top of an already-correct intent" — is
  wrong in attribution on the unexposed half. **93.33 % of the +1.0000-pt residue is
  supply-attributable** (n = 62, +0.9333 pts), and the cleanest cell available
  (`neither|dispatched`, n = 59, both arms matching-wrong, supply delivered) moves **+6.7797 macro
  pts, CI90 [+1.6949, +11.8644]** and **+15.2312 official SLU-F1 pts, CI90 [+8.2127, +22.9778]**.
  The landed "in the cell where matching already succeeds, the supply contributes −0.0667" is
  **+0.1333 from the 3 supplied trajectories and −0.2000 from the 270 unsupplied ones**.
- **Also inverted:** the landed document's one negative conditioned interval (exposed both-matched
  official SLU-F1 −1.6351 pts, CI90 excluding zero) sits **entirely in the 253 unsupplied
  trajectories**; the 2 supplied ones moved 0.0000.

### What can and cannot be concluded

**Can:** where the supply was actually delivered and matching status is held fixed, extraction moves
positively on the SLURP unexposed half (n = 59 cell, both intervals excluding zero) and on the A2T
dispatched stratum's slot micro-F1 (+12.1212 pts, CI90 touching zero at n = 15).

**Cannot — and this is the honest limit of this reading:**

1. The exposed half does **not** replicate the unexposed half's supply-attributable term
   (−0.0533 pts; `neither|dispatched` −0.4848 macro pts, CI90 straddling zero).
2. Whether the supply helps extraction **on top of an already-correct intent** remains **UNTESTED,
   not falsified**. The evidence available is n = 3, n = 2 and n = 0. The landed document treated
   that cell as a measurement; it is a structural blank.
3. Every number here is doubly conditioned on post-treatment variables and is a mechanism reading,
   never an effect size.

---

## 11. CORRECTION — explicit English successor to `2026-08-25-matching-vs-extraction-read.md`

`docs/readiness/2026-08-25-matching-vs-extraction-read.md` is **NOT rewritten in place**. This
section supersedes the following sentences of it, quoted verbatim. Its arithmetic is confirmed;
its interpretation of the conditioned cells is superseded.

**Superseded (§3, "The conditioned headline"):**

> "**On the 273 samples (54.6% of the population) where BOTH arms got the intent right, extraction
> does not move.** Macro slot-F1 −0.1221 pts with a CI90 straddling zero; micro slot-F1 exactly
> zero; official SLU-F1 +0.0894 pts with a CI90 straddling zero."

**Successor:** the arithmetic is exact and reproduces. But 270 of those 273 samples were RETAINED and
received no evidence, so the cell measures the supply on 3 trajectories, not 273. Restricted to those
3, macro slot-F1 moves **+22.2222 pts** (a MECHANISM reading at n = 3). The cell is unsupplied by the
policy form, not by outcome.

**Superseded (§3, "(a)/(b) decomposition"):**

> "The remaining +1.0000 point is *not* downstream of matching — but it does not live where the claim
> needs it either: it comes almost entirely from the **neither-matched** cell, where both arms got
> the intent wrong (+4.5977 macro pts, CI90 excludes zero; +10.8371 official SLU-F1 pts, CI90
> excludes zero). In the cell where matching already succeeds, the supply contributes −0.0667."

**Successor:** +0.9333 of the +1.0000 (93.33 %) is **supply-attributable** — concordant matching
cells restricted to DISPATCHED trajectories (n = 62). The neither-matched cell itself splits into
`dispatched` (n = 59, **+6.7797** macro pts, CI90 [+1.6949, +11.8644]; **+15.2312** official pts,
CI90 [+8.2127, +22.9778]) and `retained` (n = 57, +2.3392 macro pts). And "in the cell where matching
already succeeds, the supply contributes −0.0667" is **+0.1333 from the 3 trajectories the supply
reached** and **−0.2000 from the 270 it did not** — the sentence attributes to the supply a quantity
produced almost entirely by trajectories the supply never touched.

**Superseded (§5, "The A2T zero is a genuine zero"):**

> "Inside the conditioned cell there are **zero discordant exact-match pairs**: not one of the 60
> doubly-matched samples changed its extraction outcome."

**Successor:** true, and vacuous as a supply statement — **zero of those 60 samples were dispatched**.

**Superseded (§5, "The one A2T extraction effect that is measurable is NEGATIVE"):**

> "This is the empty-call repair working as designed on the matching axis (14 empty → 3, 4 unparsed
> → 0) and paying for it on the extraction axis."

**Successor:** **mis-attribution.** 17 of the 26 extra predicted triples (65.38 %) are in RETAINED
trajectories that received no evidence, and 16 of the 26 come from just two of them
(`tier8_intent_blending:000713` +11 against 0 expected, `:000192` +5 against 1 expected), both of
which went from an empty/unparsed M0 answer to a parsed BLEND answer by decode variance alone.
Restricted to DISPATCHED, slot micro-F1 is **+12.1212 pts** with +2 true positives; restricted to
RETAINED it is **−3.0250 pts** with −1 true positive.

**Superseded (§8, verdict items 1, 3 and 4, and the closing paragraph):**

> "**NO — not where it matters, on either carrier.**"

> "3. **The residual matching-independent signal is real but does not support the claim.** … So the
> supply *does* put usable slot content in front of the core — but only where the direct answer's
> intent was already wrong, and it adds nothing on top of an already-correct intent."

> "4. **On A2T the answer is flatly no, and the finer measure is negative.** … the supply's only
> measurable extraction effect is **−2.5781 slot micro-F1 points**, produced by 26 extra predicted
> argument triples carrying exactly one extra true positive."

> "The measured evidence does **not** support the second half — "supplies enough information for
> extraction" — as a property that operates once matching is correct."

**Successor:** "not where it matters" was measured where the supply was never delivered. On the
DISPATCHED set the supply does move extraction (SLURP unexposed `neither|dispatched` n = 59:
+6.7797 macro pts and +15.2312 official pts, both CI90 excluding zero; A2T dispatched slot micro-F1
+12.1212 pts). The claim "it adds nothing on top of an already-correct intent" is **UNTESTED, not
falsified** — n = 3 / n = 2 / n = 0 — and cannot be tested under the current policy, because the
alpha veto never dispatches a label-recovered trajectory. The honest residual limitation is
different from the landed one: the supply-attributable term **does not replicate on the
prior-exposed half** (−0.0533 pts).

**What is NOT superseded and should be cited as it stands:** the fidelity gate, all four-cell
arithmetic and contributions, the (a)-dominance finding (71.78 % / 94.85 %), the marginal Oaxaca
cross-check and its explanation, the exact-match genuine-zero finding, the gap arithmetic, and the
two-axis scoreboard.

### Who should carry this

This document is the successor record and no file outside this reading's own paths was edited. A
repository-wide search for citations of the landed read (`rg 'matching-vs-extraction|MATCHING-VS-EXTRACTION'`
over `docs/`, `src/`, `tests/`) returns only: the read's own document, module and receipt; this
reading's own files; and `docs/exposure-ledger.md`. **No landed readiness document carries the
superseded interpretation forward**, so nothing outside this reading needs repair on that account.

One in-flight item does, and its owner should be told rather than surprised:

- Exposure row **`SAEA-SN-MF-FIELD-LEVEL-SUPPLY-ACCOUNTING`** (registered `834c36dd`, another
  agent's, computation not yet landed at the time of writing) states in its scope that the landed
  read "established that CONDITIONED ON MATCHING the supply does NOT serve extraction on either
  carrier", and its question (4) prices the extraction-oriented share of the injected token budget as
  "currently paying for a channel the landed read measured at **ZERO effect**". **That premise is
  superseded by this reading.** The landed read measured zero on cells that were 98.9 % / 99.2 % /
  100 % unsupplied; restricted to trajectories that actually received supply the channel is not zero
  (SLURP unexposed `neither|dispatched` n = 59: +6.7797 macro pts and +15.2312 official pts, both
  CI90 excluding zero; A2T dispatched slot micro-F1 +12.1212 pts). A ledger row is append-only and is
  **not** edited here; the correction belongs in that row's own verdict document, which should price
  the extraction-oriented fields against the **dispatched-set** result rather than against a zero
  that was measured where nothing was delivered.

---

## 12. HARD STOP — what this document does NOT authorize

- **It does NOT revise, re-tune or restate the DEV-1000 LOCK.** Every SLURP unexposed-500 statistic
  here is a SECONDARY reading on the locked baseline's population and is descriptive only. The lock
  stands exactly as landed at `d9fef537`.
- **No knob change, no re-tune, no re-flight, no new arm, no threshold move.** In particular, the
  positive dispatched-cell result is **NOT** a licence to re-fit the alpha gate, the retain-override
  bar, the ranker, the fuser or the supply budget — and the observation that the alpha veto makes the
  both-matched cell structurally unsupplied is a **description of the current policy**, not a proposal
  to change it.
- **No claim.** No generality claim, no superiority claim, no cross-carrier transfer claim, no
  conclusion about the method's extraction capability beyond these two already-read populations. The
  dispatched cells are doubly post-treatment-conditioned mechanism readings.
- **No test contact, no FINAL60 contact, no new population**, and no G2 opening. The A2T numbers are
  a secondary reading on an EXPOSED n = 104 below the campaign plan's own power floor; the
  `n = 0/1/2/3/4` cells can never be cited as effect sizes.
- **No Stage-3 activity of any kind**, no manuscript, no paper-scale profile, no promotion.
- **Nothing here puts gold on a runtime path.** Gold was opened strictly scoring-side over
  populations whose seal the landed lock read and the landed G1 read had already broken.
