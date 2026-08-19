# P-KEY verdict — INCONCLUSIVE-KEY (registered one-shot read, 2026-08-19)

Mechanical outcome per the registered metrics and verdict rules
(`docs/readiness/2026-08-18-pkey-preregistration-REGISTERED.md` §4 as **amended by §7**),
computed by the pinned offline read suite (`analysis.pkey_read`, built at `01583dc`,
coordinator-reviewed) over the already-flown attempt
`attempt-20260819T111032Z-3109e8` (`SAEA-PROBE-pkey2-338`, status `COMPLETED`, error `None`,
338/338 rows) — zero model contact, zero GPU, no attempt-directory mutation.

Read archive: `docs/checks/speech-aware-evidence-acquisition/2026-08-19-pkey2-read/`
(`verdict.json`, `report.txt`, `README.md`, `MANIFEST.sha256`). The suite ran exactly once
(idempotence-guarded output dir), exit 0, at study HEAD `dbe3503` with a clean tree. Exposure
row `SAEA-PROBE-pkey2-338` flips to consumed in the same commit. Scope: **descriptive,
discovery-tier, n = 60 SLURP devel, single run, same-distribution**. SLURP audio CC BY-NC 4.0
carried on every audio-derived number.

Pre-read gates, all green before anything was opened: `test_pkey_read.py` + `test_bootstrap.py`
**69 passed**; the flight archive's `MANIFEST.sha256` verified 30/30 OK; the P-PHON
cross-reference archive's `MANIFEST.sha256` verified 3/3 OK; ledger row `consumed = no`;
attempt-directory fingerprint identical before and after the read (`24e961b2…`).

---

## 1. REACHABILITY STATEMENT (mandatory, published BEFORE any verdict was evaluated)

Amendment item 2 requires the maximum |I| attainable given P-PHON's consumed class census to
be published before the verdicts are read, and forbids reporting KEY-ONLY as an affirmative
negative if SPEECH-TERM-PRESENT is unreachable.

| quantity | value |
|---|---|
| CITED P-PHON census: NEAR-MISS baseline failures | **4 / 85** (rate 0.0471) |
| this run's own AUD-NOSUP failures | **60 / 60** |
| eligible = min(NEAR_MISS_COUNT, AUD-NOSUP failures) | min(4, 60) = **4** |
| **max attainable \|I\| = eligible / n_samples** | 4 / 60 = **0.0667** |
| SPEECH-TERM-PRESENT floor | **+0.06** |
| **verdict** | **REACHABLE** — headroom **+0.0067** |

**SPEECH-TERM-PRESENT was reachable**, so this read is *not* under amendment item 2's
suppression clause: KEY-ONLY was legally available as an affirmative negative had the CI
supported it. It did not.

Two honesty notes travel with this bound, both flagged in the suite's own source rather than
buried. First, the arithmetic reads `NEAR_MISS_COUNT` as an **absolute cap**, not as a rate:
P-PHON's 85-failure census was measured over a larger evaluated set than this probe's 60
samples, and re-applying 4/85 as a rate would put the bound at ≈0.047 — below the +0.06 floor
for *every possible input*, making SPEECH-TERM-PRESENT unreachable by construction and the
gate uninformative. The absolute-cap reading is the non-degenerate one and is what the
registered instrument was built on. Second, the bound is **honored but not tight**: it models
the audio-exclusive benefit as sample-level repair confined to the NEAR-MISS class, while the
measured effects are slot-level and an order of magnitude larger (Δ_AUD = +0.44). Treat 0.0667
as the registered legality gate it is, not as a validated power model.

The consequence is worth stating plainly: the reachable window for an affirmative speech term
was **[0.06, 0.0667]** — **0.0067 wide**. The instrument cleared its own reachability gate by
11 %, and the affirmative branch it licensed was correspondingly narrow.

---

## 2. VERDICT

> ## OVERALL: **INCONCLUSIVE-KEY**
> (the CI-gated verdict of amendment items 1–2, authoritative; VOID checked first and not met)

| quantity | value |
|---|---|
| Δ_AUD = AUD-SUP − AUD-NOSUP | **+0.4397** |
| Δ_TXT = TXT-SUP − TXT-NOSUP | **+0.3934** |
| **INTERACTION I = Δ_AUD − Δ_TXT** | **+0.0463** (0.046322) |
| **σ̂(I)** paired cluster bootstrap | **0.0306** (0.030612) |
| **90 % CI** (N = 10,000, seed 20260807) | **[−0.0033, +0.0970]** |
| **TXT-duplicate block empirical \|ΔF1\| floor** (n = 35 byte-identical resends) | **0.0000** |

### Clause margins (every clause, in the registered order)

| clause | result | margin |
|---|---|---|
| **SPEECH-TERM-PRESENT**: I ≥ +0.06 | **not met** | I = +0.0463 vs floor +0.06 — short by **−0.0137** |
| **KEY-ONLY (CI-gated, authoritative)**: entire 90 % CI ⊂ [−0.03, +0.03] AND reachable | **not met** | CI high **+0.0970** overshoots the +0.03 ceiling by **+0.0670**; CI low −0.0033 *is* inside the band. Reachability was satisfied — this clause failed on the CI alone |
| **KEY-ONLY (pre-amendment point-only, reported, no longer authoritative)**: \|I\| ≤ 0.03 | **not met** | \|I\| = 0.0463 vs ceiling 0.03 — over by **−0.0163** |
| **TEXT-DOMINANT**: I ≤ −0.06 | **not met** | I = +0.0463 vs ceiling −0.06 — **−0.1063** |

Note that the two KEY-ONLY readings agree here: the point estimate was already outside the
equivalence band before the CI gate was applied, so this is not a case of the amendment
overturning a point-level pass. The amendment's discipline still mattered — it is what
prevents the CI's near-zero lower bound from being narrated as evidence for equivalence.

### The duplicate-block floor next to σ̂(I)

The 35-call TXT duplicate sub-block existed to give this axis its own measured resend floor.
It returned **|ΔF1| = 0.0000** (original 0.15525310545495605, duplicate 0.15525310545495605 —
bit-identical), against σ̂(I) = **0.0306**. The decode path is exactly deterministic on the
text axis in-session, so **none** of σ̂(I) is resend noise; all of it is between-sample
variance, which is precisely what the paired cluster bootstrap is supposed to be measuring.
This is a clean result for the instrument: the CI width is real sampling uncertainty at
n = 60, not harness jitter.

### Why this is INCONCLUSIVE and what would and would not fix it

The point estimate landed in the **registered dead zone** — the 0.03-wide gap between the
KEY-ONLY ceiling (0.03) and the SPEECH-TERM-PRESENT floor (+0.06) that the registration's own
"otherwise INCONCLUSIVE-KEY" clause covers. I = +0.0463 sits at almost exactly its midpoint
(+0.045).

This matters for any successor design: **more samples alone cannot resolve this.** Increasing
n shrinks the CI around the point estimate, but KEY-ONLY can never fire while |I| > 0.03 and
SPEECH-TERM-PRESENT can never fire while I < +0.06, at any n. An INCONCLUSIVE at a point
estimate inside the dead zone is resolved only by the estimate *moving* — a genuinely larger
effect, a different measurement, or a differently-structured threshold set — never by
precision alone. This is a finding about the registered instrument, recorded here; it is not a
licence to re-cut the thresholds after the fact, and this read stands as registered.

---

## 3. The four arms

Primary metric is the official pooled SLU-F1 (registration §4). `slot_f1_exact` and
`intent_acc` are the scoring stack's own companions, **descriptive only — no clause attaches**.

| arm | n | **SLU-F1** | slot_f1_exact | intent_acc | copy_rate | induced subs |
|---|---|---|---|---|---|---|
| AUD-NOSUP | 60 | **0.1741** | 0.0435 | 0.0000 | 0.0000 | 0 |
| AUD-SUP | 60 | **0.6138** | 0.5236 | 0.0000 | 0.0000 (0/6000) | 3 |
| TXT-NOSUP | 60 | **0.1740** | 0.0339 | 0.0000 | 0.0000 | 0 |
| TXT-SUP | 60 | **0.5674** | 0.3708 | 0.0000 | 0.0000 (0/6000) | 3 |

Full precision: AUD-NOSUP 0.1740786454061426 / AUD-SUP 0.6138239343259204 /
TXT-NOSUP 0.17399230835961918 / TXT-SUP 0.5674156837879871.

- **Δ_AUD = +0.4397**, **Δ_TXT = +0.3934**. Supply is a very large effect on **both**
  modalities. Whatever the interaction turns out to be, the dominant fact of this factorial is
  that the roster is worth ~0.4 SLU-F1 regardless of whether the core is looking at the audio
  or at its own transcript of that audio.
- **Cross-session reproduction, unprompted and exact**: AUD-NOSUP's SLU-F1
  (0.1740786454061426) and slot_f1_exact (0.043478260869565216) are **bit-identical** to the
  consumed P-SLU parent read's A0 arm. The A0 baseline reproduced to the last digit across
  sessions and across a week — strong independent evidence that the frozen core plus this
  decode config is deterministic, and that the in-session comparator design was not paying for
  a drift it needed to guard against on this arm. AUD-SUP (0.6138) sits +0.0177 above the
  parent's A3 (0.5961); AUD-SUP is registered as *A3-form*, not A3-identical, so this is a
  prompt-content difference and not a determinism finding.
- **`intent_acc = 0.0000` on all four arms.** The scenario/action label is never exactly right
  anywhere in this factorial. This is a **pre-existing property** of this scoring stack on this
  manifest, not something this flight introduced: the consumed P-SLU parent read shows 0.0
  intent accuracy across its arms as well. Its consequence for this read is specific and
  significant — see §5.

---

## 4. The perception gap — what frozen self-transcription costs

Registered descriptive (§4): TXT-NOSUP − AUD-NOSUP.

| | value |
|---|---|
| **Perception gap (SLU-F1)** | **−0.0001** (−0.0000863) |
| same, on slot_f1_exact (descriptive) | −0.0096 (0.0339 vs 0.0435; ≈ −22 % relative) |
| T0 transcript quality vs gold (scoring-side WER, macro over 60) | **0.5359** |

**Replacing the audio with the core's own transcription of that audio costs essentially
nothing at the no-supply baseline** — one ten-thousandth of an SLU-F1 point — even though that
transcription carries a **53.6 % macro WER** against gold. Per-sample WER spans 0.20 to 1.33
(several samples at 1.0 or above, i.e. the hypothesis is as long as the reference and wholly
wrong). The strict exact-slot companion does show a real cost (−0.0096, about a fifth of an
already tiny 0.0435), so the loss is not literally zero — it is invisible at the partial-credit
metric and visible at the exact-slot one.

The honest reading of a ~0 gap next to a 53.6 % WER is not "self-transcription is lossless".
It is that **at 0.174 SLU-F1 the no-supply baseline is already so weak that the extra damage
from a 53.6 %-WER transcript has almost nothing left to destroy** — a floor effect. The
interesting number is what the same substitution costs once supply is present, and that is the
interaction itself.

**A useful identity.** Because the two no-supply arms are equal to within 0.0001,
I = Δ_AUD − Δ_TXT collapses to ≈ (AUD-SUP − TXT-SUP) = 0.6138 − 0.5674 = **+0.0464**. In
words: **the modality difference is worth nothing without a roster and ≈ +0.046 SLU-F1 with
one.** Real audio only pays once there is something to resolve it against. That is
directionally exactly the speech-term hypothesis — and it does not clear the registered bar.

**Unregistered corroboration, explicitly no clause and no CI.** The same interaction computed
on `slot_f1_exact` is far larger: Δ_AUD(exact) = +0.4801, Δ_TXT(exact) = +0.3369,
**I(exact) = +0.1432** — which would clear the +0.06 floor by a wide margin. This metric was
**not** the registered primary, has **no** bootstrap CI here, and **no** verdict attaches to
it. It is recorded because it points the same direction as the registered estimate, more
strongly, and because the choice of partial-credit SLU-F1 as primary is now visibly
consequential for a successor registration to weigh — not because it changes this verdict. It
does not.

---

## 5. Converted-set difference — the instrument returned empty

| set | count |
|---|---|
| AUD converted (AUD-SUP correct, AUD-NOSUP not) | **0** |
| TXT converted (TXT-SUP correct, TXT-NOSUP not) | **0** |
| **AUD-only (the perception-repair set)** | **0** |

**There are no per-sample rows to list, and the P-PHON cross-reference has nothing to key
against.** The reason is structural, not empirical. The suite's "converted" test requires a
sample to be **fully correct** — exact scenario/action match **and** an exact entity slot set
(zero FP, zero FN). With `intent_acc = 0.0000` on every arm (§3), the scenario/action
conjunct is false for all 240 scored rows, so **no sample can ever be fully correct** and all
three sets are empty by construction. The AUD-NOSUP failure count of **60/60** that fed the
reachability statement has the same origin.

This is a **null of the instrument, not a null of the mechanism**. The slot-level metrics move
enormously (+0.44 / +0.39), so supply is plainly converting slots; the converted-set
difference simply cannot see them because it only counts whole-sample conversions and the
intent conjunct gates every one to false. Recorded as a defect in the registered descriptive's
reach on this manifest, for a successor design to address — a slot-level converted-set
difference would have been informative here where the sample-level one was not.

**NEAR-MISS cross-reference caveat (amendment item 3), carried verbatim in force:** P-PHON's
own consumed class census names at most **n ≤ 4** NEAR-MISS baseline failures — effectively
**n ≤ 3** after P-PHON disqualified its single A3 NEAR-MISS row as a clock-format variant. It
licenses **no mechanism claim** on its own. Here it licenses nothing at all, the set being
empty.

---

## 6. Induced substitutions, silence-swaps, and VOID

**Induced substitutions**: 0 on AUD-NOSUP, **3** on AUD-SUP, 0 on TXT-NOSUP, **3** on TXT-SUP.
Supply induces a small and *modality-symmetric* number of wrong-value substitutions — the harm
channel is present, equal on both axes, and contributes nothing to the interaction.
`copy_rate = 0.0000` on both supply arms across 6,000 supplied-item checks each.

**Silence-swaps (3 seeded on AUD-SUP, unanimity VOID bar)**: **3/3 changed**; the VOID clause
requires *all* three to persist unchanged and none did. Beyond passing the bar, the failure
mode is itself evidence. All three silence variants collapsed to the **same** degenerate
answer — scenario "Setting an alarm", action "Set an alarm", with roster-shaped slots
(`alarm_type: wake up`, `time: five pm`, `time_zone: eastern`, `timeofday: morning`) — while
their real-audio counterparts returned three completely different and audio-appropriate
signatures (smart-home "turn off / room light"; calendar "Add event / baseball practice /
tonight"; "search / restaurants / chinese / nearby"). With the roster present and the acoustic
evidence removed, the core confabulates one canned roster-populated answer; with the audio
present it does not. **The audio is genuinely driving answer content on the supply arm**, and
the roster alone does not determine the output.

**VOID: not met** — all six clauses `not_met`:

| clause | result |
|---|---|
| silence-swap answers persist unchanged | not met (3/3 changed) |
| harness defect | not met (none detected) |
| per-sample TP/FP/FN fail to reproduce the committed scorer on recheck | not met (**0** mismatches; every row exact) |
| gold sentence text found inside a prompt | not met (**0** violations) |
| a TXT-* row's transcript disagrees with its own T0 output (byte-identity) | not met (**0** mismatches; all 120 TXT-* rows sha256-matched their own T0 response) |
| a `txt_duplicate` row disagrees with its pass-3 original (byte-identity) | not met (**0** mismatches; all 35 byte-matched) |

Transcript reuse is therefore proven byte-identical in both directions, the SELF-TXT design's
central integrity requirement, and no gold-derived text reached any prompt path — the study's
hard runtime rule held, verified mechanically rather than asserted.

---

## 7. Synthesis — what P-PHON + P-KEY jointly answer about "speech knowledge vs audio-as-key"

Stated with every bound attached.

The two probes converge on a picture that is **directionally speech-positive and evidentially
short of the registered bar**. P-PHON asked *what* supply converts and found the L3 gain
**recall-dominant**: 81.8 % (A3) / 85.4 % (A1'r) of converted slots were MISSING at baseline —
slots the zero-supply core never produced at all — with the speech-snap branch class-starved
(only 4 of 85 baseline failures were NEAR-MISS, so its 25 %-of-conversions floor was
unreachable even at CR = 1.0) and its single NEAR-MISS conversion format-adjacent on
inspection. P-KEY then asked the identity question directly, and its answer is that **the
supply benefit is overwhelmingly modality-invariant with a small positive audio-exclusive
residue**: the roster is worth +0.39 SLU-F1 to a core reading its own 53.6 %-WER transcript and
+0.44 to a core hearing the audio, leaving I = +0.0463 [90 % CI −0.0033, +0.0970] as the speech
term. Roughly **89 % of the supply benefit is realized text-side**; the residue leans positive
but its CI touches zero, and its point estimate sits in the registered dead zone where neither
verdict can fire.

Three converging observations make the residue more than a rounding artifact, and none of them
is sufficient to claim it. (i) The interaction is *entirely* a supply-condition effect: the
modality substitution is free at baseline (−0.0001) and costs +0.046 once the roster is
present — audio matters only when there is something to resolve against, which is the shape a
perception-repair mechanism would produce. (ii) The silence-swaps show the frozen core
collapsing to one canned roster-populated answer when the acoustic evidence is removed but the
roster is not, so the audio demonstrably drives answer content on the very arm where the
residue lives. (iii) The unregistered exact-slot companion puts the same interaction at
+0.1432. Against all three: the registered primary metric returned +0.0463 with a CI crossing
zero, and **that is the answer of record**.

The bounds are not decoration and each one narrows what may be said. **Reachability**: the
affirmative window this instrument could ever have reported was [0.06, 0.0667] — 0.0067 wide,
cleared by 11 % — so a null on the affirmative branch was always going to be weak evidence, and
the registered gate honestly says so. **Same-distribution**: every arm is the same frozen 60
SLURP devel samples, so this is a within-distribution mechanism reading and carries no
deployment or generalization content. **n = 60, discovery-tier, single run**: σ̂(I) = 0.0306 is
between-sample variance measured on exactly one flight, and the duplicate block establishes
that resend noise contributes zero to it — a clean instrument, but a small one. **The
converted-set difference returned empty for a structural reason** (`intent_acc = 0` gates
whole-sample correctness to false everywhere), so the per-sample perception-repair evidence
this verdict was meant to rest a mechanism story on **does not exist in this read**, and the
NEAR-MISS cross-reference (n ≤ 4, effectively n ≤ 3) licenses no mechanism claim in any case.
**CC BY-NC 4.0** carries on every number above.

**Effect on the qualification's §2b (the freeze is HELD on this).** §2b named P-KEY the decisive
instrument and set the condition explicitly: *either* outcome is publishable **if its
reachability statement licenses it** — a demonstrated speech term upgrades the candidate; a
CI-confirmed key-only honestly redirects the speech-specific thesis to the meeting carrier.
This read delivers **neither**. Reachability *did* license a verdict, and the verdict returned
was INCONCLUSIVE-KEY. Therefore:

- **§2b stays OPEN and the freeze stays HELD.** The open question is not closed in either
  direction and must not be narrated as closed. In particular, I = +0.0463 with a CI touching
  zero is **not** a demonstrated speech term, and it is emphatically **not** a CI-confirmed
  key-only — the CI-gated clause failed, so the deflationary redirect to the meeting carrier is
  *also* unlicensed by this read.
- **What §2b may now record as settled** is narrower and real: the supply benefit is
  **large and overwhelmingly text-side realizable** (Δ_TXT = +0.393, ~89 % of Δ_AUD), which
  substantially sharpens the honest framing of C1–C4 as substrate-general retrieval-augmentation
  logic; and the **audio-conditioning evidence on the SLURP carrier is materially stronger than
  the "0/6 silence-swap on three ids" §3 item 9 described** — 3/3 swaps changed with a
  diagnostic shared-confabulation signature, on top of a 338-row single-session factorial with
  zero VOID clauses and byte-verified transcript reuse. §3 item 9's finding that **the A2T
  carrier still has no audio-conditioning control** is untouched by this read and stands.
- **What a successor must confront** is that the dead zone, not the sample size, is the
  binding constraint: at I = +0.0463 no amount of additional n moves this out of INCONCLUSIVE
  (§2). Resolving §2b requires the estimate to move — a measurement with more headroom (the
  exact-slot axis is the obvious candidate, and it is *unregistered* here for exactly the
  reason it must be pre-registered there), a carrier where the perception gap is not at the
  floor, or a mechanism probe such as the registered P-TRAP that attacks the question from the
  self-percept side rather than through a difference-of-differences at n = 60. Any such
  successor is a fresh registration under its own owner decision; nothing here authorizes it.

No superiority, generalization, deployment, or paper-scale claim attaches to any number in
this document.
