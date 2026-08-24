# DEV-100 reviewer audit — an adversarial statistical read of the sealed campaign

Date: 2026-08-24. Status: **DESIGN INPUT — iteration tier. No verdict, no knob selected, no
flight authorized, no promotion claim.** Profile: `model-free-check`. Exposure row
`SAEA-SN-MF-DEV100-REVIEWER-AUDIT` (registered before any computation; **0** frozen-core
contacts, **0** embedding-tool contacts, **0** tokenizer contacts, **0** audio seconds,
**0.0** GPU hours).

This document is written from the chair of a skeptical reviewer who has been handed the
campaign's headline — *the knowledge-conditioned two-contact decode beats direct decode on
SLURP dev by +15 to +19 samples* — and is deciding what, if anything, that sentence has
earned. It reports what the sealed rounds already contain. It selects nothing.

## 1. Authority, scope, and offline proof

- Owner discipline `2026-08-23-knowledge-plane-baseline-rulings.md` §7.2 (iterate on exposed
  data before concluding); campaign preregistration `2026-08-23-dev100-campaign-preregistration.md`;
  sibling analysis `2026-08-24-dev100-damage-channel-analysis.md`.
- **Consumed**: the four sealed round reports
  (`docs/checks/speech-aware-evidence-acquisition/2026-08-24-dev100-round{0,1,2,3}/round*-report.json`),
  the committed `docs/receipts/probe-samples/DEV-100.json`,
  `docs/receipts/knowledge/slurp-kb-size-full.json` and
  `docs/receipts/knowledge/slurp-split-identity.json`, the four sealed attempt stores
  (per-sample score files and durable traces), the pinned TRAIN snapshot
  `e27b2745…a51b57`, and devel gold scoring-side for the **same** 100 samples whose gold was
  lawfully opened at each round seal. TRAIN **value** vectors stayed sealed.
- **Round 3 was included** because its report was committed (land commit `03a85964`) before
  this audit reached synthesis. It is the best sealed round and therefore the primary object.
- **Offline proof.** The tool arms a socket guard before it opens any input:
  `socket.socket.connect`, `connect_ex` and `socket.create_connection` are replaced by
  raisers that count attempts. Measured: **0 connect attempts**. Independently, the resident
  decoder unit's `server.log` measured **733,638 → 733,693 bytes** across the session's
  observation window and was **byte-identical (733,693) immediately before and after** the
  audit runs themselves; the earlier growth belongs to the concurrent round-3 flight, not to
  this row. The guard is the stronger of the two statements: it cannot be satisfied by a
  contact that happens to log nothing.
- **Tool**: `src/speech_aware_evidence_acquisition/analysis/dev100_reviewer_audit.py`; receipt
  `docs/checks/speech-aware-evidence-acquisition/2026-08-24-dev100-reviewer-audit/reviewer-audit.json`
  (sha256 `e039b5818fa23ef5568f4c6e505ea6d66e0fbb8493121f0c606994695f3bcc89`). `rails/`,
  `core/` and the round launchers are untouched; the shared `analysis.bootstrap` primitive and
  the sibling analysis's landed-input readers are imported, not re-implemented.
- **Two-source discipline.** Every paired outcome was built twice — once from the landed
  per-sample score files, once from the committed report's own movement lists and arm totals —
  and the tool refuses to publish unless the two agree sample-for-sample. They agree on
  400/400 (4 rounds × 100).

## 2. Question 1 — uncertainty

Per-sample paired **cluster bootstrap**, N = 10,000, seed 20260807, resampling the 100 DEV-100
ids with replacement and scoring both arms on the identical resampled multiset. Units are
percentage points; on a 100-sample split one point = one sample.

| round | M0 | BLEND | gain | σ̂ | 90% CI | 95% CI | replicates ≤ 0 | McNemar n01/n10 | exact p | mid-p |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 48 | 63 | **+15** | 5.82 | **[+5, +24]** | [+3, +26] | 0.58% | 26 / 11 | 0.0201 | 0.0139 |
| 1 | 48 | 63 | +15 | 5.81 | [+5, +24] | [+4, +26] | 0.59% | 26 / 11 | 0.0201 | 0.0139 |
| 2 | 48 | 65 | +17 | 5.94 | [+7, +27] | [+5, +29] | 0.28% | 28 / 11 | 0.0095 | 0.0064 |
| **3 (best)** | 48 | **67** | **+19** | **5.00** | **[+11, +27]** | **[+9, +29]** | **0.00%** | **24 / 5** | **5.46e-4** | **3.25e-4** |

**Answer: yes, the 90% CI excludes zero in every sealed round, and so does the 95% CI.** For
the best round the entire replicate distribution is positive (0 of 10,000 replicates at or
below zero) and the continuity-corrected McNemar χ² is 11.17 (p = 8.3e-4).

Discordant-pair accounting, stated plainly: the brief's 26-versus-11 is round 0. Round 3's
discordant table is 24 repairs against 5 damages — the damage list collapsed by the round-3
label-identity repair while the repair list stayed within two of its round-0 value. The
McNemar test conditions on the discordant set and therefore answers a narrower question than
the bootstrap ("is the direction reliable?" rather than "how big is the effect?"); both are
reported so neither can be quoted alone.

Two reviewer-grade caveats attach to every number in this table and are **not** removed by any
of them:

1. These are intervals on **exposed** data. Four rounds of knob and code selection were made
   against these same 100 samples. A CI is not a defence against selection; it prices sampling
   noise only.
2. The M0 arm was **flown once** (round-0 attempt 1, zero-copy build) and reused thereafter,
   while every BLEND arm re-decoded the same prompts on the base build under 8-slot
   concurrency. The paired contrast therefore spans a build change and a concurrency change.
   §4 gives the within-session comparator that does not.

## 3. Question 2 — variance-channel robustness

The campaign documents its own nondeterminism: per-sample sha256 equality between a round's
flown direct decode and the attempt-1 M0 responses is **78 / 79 / 75 / 81 of 100** for rounds
0 / 1 / 2 / 3 (22 / 21 / 25 / 19 disagreements). Pooled, **36 distinct samples** are byte-
unstable in at least one round and **11 are unstable in every round**. Of the 100 samples,
**12** actually changed their scored BLEND outcome across the four rounds; **5** are in both
sets — byte-unstable *and* demonstrably outcome-flipping.

Three floors, from a measurement to a fiction:

| floor | definition | gain | W→C | C→W | 90% CI |
|---|---|---|---|---|---|
| headline (round 3, as sealed) | — | +19 | 24 | 5 | [+11, +27] |
| **observed-worst** | each sample takes its **worst** paired outcome across the four sealed rounds — every value is something the stack actually produced | **+12** | 24 | 12 | **[+2, +22]** |
| **adversarial-flipped** (the brief's mandated floor) | every byte-unstable **and** cross-round-flipped sample is scored against the claim (BLEND wrong, M0 correct) | **+15** | 24 | 9 | **[+6, +24]** |
| adversarial-all-unstable | all 36 byte-unstable samples scored against the claim, flipped or not | −24 | 16 | 40 | — |

**Answer: the headline survives the mandated floor. The conservative gain floor is +15
samples (90% CI [+6, +24], excludes zero); the stricter observed-worst floor is +12 samples
(90% CI [+2, +22], excludes zero).** The all-unstable bound is reported for completeness and
should not be read as a test: it charges the claim for 31 samples whose outcome never moved,
and any effect of this size would fail it.

Why the mandated floor is mild rather than devastating: of round 3's 29 discordant pairs, only
**9** are in the byte-unstable union at all (8 repairs and 1 damage), and the repairs among
them held their sign across four independent re-decodes. The variance channel is real, it is
large in bytes, and it is mostly *not* where the effect lives.

## 4. Question 3 — is M0 the right comparator?

**What arm M0 contains.** The full task contract in the system message (output schema, field
names, the instruction to answer from the speech query alone); the original speech packet on
its single contact — never a transcript-only query; JSON-shaped constrained decoding, which
is why parse failures are **0/100 in every round**; one frozen-core contact, no revision.

**What it does not contain.** The SLURP label inventory: the contract never enumerates the 60
legal (scenario, action) pairs, so the arm is free to invent a label — and does, on **35–39
of 100** direct answers, which name a pair that is not a TRAIN intent **as written** (4–5 of
those would be a real intent with the two fields exchanged). It also contains no retrieved
evidence, no in-context example, and no prior.

**Majority-class baseline (computed from DEV-100 gold).** The split is scenario-stratified over
18 scenarios (6×10 + 5×8), which deliberately flattens the label marginal. The 100 samples
carry **42 distinct gold intents**; the single most frequent is `cooking_recipe` at
**6/100 = 6%**. Uniform chance over the 60-intent space is 1.7%. **M0's 48% is eight times the
majority-class floor**, so the baseline is not a straw man on this axis.

One number a reviewer will notice and should be handed rather than left to find: a rule that
is *given the gold scenario* and then emits that scenario's most frequent action **within these
same 100 samples** reaches 67/100 — numerically identical to BLEND-r3. It is not a baseline and
must not be quoted as one: it consumes gold twice (the scenario label at inference time, and
the split's own action distribution at n = 5–6 per stratum, which is near-memorization). What
it legitimately measures is how *concentrated* a 100-sample stratified draw is — which is
exactly why the train-prior rule below, the honest version of the same idea, scores 39–41
instead.

**Two harder baselines a reviewer would demand, both computed here at zero contacts.**

- **Train-prior baseline** — take the arm's own predicted scenario from its direct answer, then
  emit the most frequent action for that scenario in TRAIN (from the pinned snapshot's own
  value counts, i.e. exactly the `prior_source = "train"` prior the campaign registers). This
  scores **41 / 39 / 40 / 39** across rounds 0–3, *below* M0's 48 and 26–28 samples below
  BLEND. **The gain is not reducible to a train prior applied to the model's scenario guess.**
  This is the strongest positive finding in the audit.
- **In-session direct comparator** — score each round's *own* direct-decode responses, removing
  the cross-build confound of §2. They score **51 / 49 / 50 / 47**, and the BLEND gain over
  them is **+12 / +14 / +15 / +20**. The registered M0 number (48) sits inside that band and
  the round-3 gain is, if anything, one sample *larger* against the within-session baseline.
  **The cross-build confound does not manufacture the effect.**

**Field decomposition (round 3).** `scenario_action_exact` is a conjunction, and the conjunction
hides which conjunct moved:

| arm | scenario exact | action exact | both | scenario right / action wrong |
|---|---|---|---|---|
| M0 | 67 | 59 | 48 | 19 |
| BLEND-r3 | 74 | 72 | **67** | 7 |

The mechanism buys +7 on the scenario field and +13 on the action field, and its largest single
effect is collapsing the *inconsistent* cell (scenario right, action wrong) from 19 to 7.

**Per-scenario M0 profile (and where BLEND pays).**

| scenario | n | M0 | BLEND-r3 | Δ samples |
|---|---|---|---|---|
| alarm | 6 | 1.00 | 1.00 | 0 |
| audio | 6 | 0.17 | 0.67 | **+3** |
| calendar | 6 | 0.67 | 0.67 | 0 |
| cooking | 6 | 0.00 | 0.83 | **+5** |
| datetime | 6 | 0.67 | 0.67 | 0 |
| email | 6 | 0.83 | 0.67 | **−1** |
| general | 6 | 0.00 | 0.33 | +2 |
| iot | 6 | 0.33 | 0.83 | **+3** |
| lists | 6 | 1.00 | 1.00 | 0 |
| music | 6 | 0.33 | 0.00 | **−2** |
| news | 5 | 0.60 | 0.60 | 0 |
| play | 5 | 0.00 | 1.00 | **+5** |
| qa | 5 | 0.00 | 0.40 | +2 |
| recommendation | 5 | 0.00 | 0.40 | +2 |
| social | 5 | 0.60 | 0.60 | 0 |
| takeaway | 5 | 0.60 | 0.60 | 0 |
| transport | 5 | 0.80 | 0.80 | 0 |
| weather | 5 | 1.00 | 1.00 | 0 |

M0 scores **0.00** on five scenarios (`cooking`, `general`, `play`, `qa`, `recommendation`) and
**1.00** on three (`alarm`, `lists`, `weather`). The gain is **concentrated**: `cooking` and
`play` alone supply 10 of the 19 net samples, nine scenarios are flat, and two lose (`music`
−2, `email` −1). By recording channel, M0 scores 0.52 on close-talk (58 samples) and 0.43 on
headset (42); BLEND-r3 scores 0.69 and 0.64.

**Is 48% consistent with the train-side E108 K0-M0 71.3% (77/108)?** The 23.3-point gap is
**not decomposable from sealed DEV-100 bytes**, and this audit records that as a limitation
rather than inventing an attribution. The two numbers differ in split side (train vs devel),
selection rule (a discovery-split eligibility filter vs a scenario-stratified draw over the
devel pool), serving stack (zero-copy np16 M-line vs the np8 campaign service) and prompt
lineage. What the sealed data *does* show is the per-scenario profile above: five scenarios at
zero and three at ceiling is a difficulty signature, not a uniform degradation, so a
"DEV-100 is simply harder" story is at least consistent with the shape. Settling it needs a
matched same-protocol train-side direct-decode control — roughly 100 contacts, **not
authorized by this row**.

## 5. Question 4 — leakage and hygiene checklist

Cited, not re-derived: re-deriving a decontamination verdict would mean opening the rosters the
receipt exists to keep closed.

| item | status | citation |
|---|---|---|
| KB ↔ devel/test disjoint | **clean**, 50,628 samples checked | `docs/receipts/knowledge/slurp-kb-size-full.json` → `decontamination`; snapshot built from 11,514 TRAIN utterances only; forbidden roster = frozen devel/test identity + FINAL60 + DEV-100/500/1000 |
| frozen split identity | devel 8,690 ids, identity-only enumeration (no scenario/action/entities read) | `docs/receipts/knowledge/slurp-split-identity.json` |
| FINAL60 exclusion | 60 utterances excluded at **utterance** granularity | `docs/receipts/probe-samples/DEV-100.json` → `exclusions.final60` |
| historic probe-60 exclusion | 60 utterances excluded at utterance granularity | same receipt → `exclusions.historic_probe60` |
| gold-opening discipline | seal-then-score: gold opens scoring-side only, after every arm of a round has sealed; devel gold moves between rounds, never into runtime | preregistration §3/§6; each round report's `authority` |
| runtime split role | `dev` (`QueryState.use_partition_role`) on every contact | round reports; campaign row |
| test / FINAL60 / DEV-500/1000 | untouched | campaign row, preregistration §6 |

**What a reviewer may conclude.** The knowledge snapshot contains no devel, test, FINAL60 or
DEV-tier utterance. The 100 scored utterances exclude the reserved tiers at utterance
granularity. Gold never entered runtime, and every arm's decisions were sealed before scoring.

**What a reviewer may not conclude.** That any DEV-100 number generalizes — the split is
exposed by construction and has now been read four times. That the gain is a held-out effect
size; only a one-shot confirmatory tier can produce that, and none has been read. That
decontamination was re-verified here.

**One open hygiene finding this audit surfaces.** `DEV-100` is an **exact subset of DEV-500**
(the split receipt's own `nesting` block). A DEV-500 confirmatory reading as currently framed
therefore re-reads the 100 samples all four rounds of selection were made against: **20% of the
confirmatory denominator is already exposed.** Two remedies exist — pre-register the 400-sample
unexposed remainder as the primary number with the full 500 as secondary, or accept and price
the 20% exposure explicitly — and **neither is registered as of this audit**. This is design
input for whoever writes the DEV-500 preregistration.

## 6. Question 5 — how much of the gain is mechanism, and how much is noise?

Attribution is per step and per sample, using only the sealed movement lists and the sealed
direct-agreement lists. A moved sample is charged to the variance channel when its own direct
decode changed bytes between the two rounds being compared.

| step | Δ | moved samples in the variance channel | moved samples outside it | reading |
|---|---|---|---|---|
| 0 → 1 | **0** | 2 (`012185` out, `015370` in) | 0 | τ 0.5 → 0.65 is a **mechanism null**; the two moves cancel and both are noise |
| 1 → 2 | **+2** | 2 (`005565`, `013522` both newly correct) | 0 | **entirely noise-attributable** — matching the sibling analysis's proof that α is mathematically inert while the direct term is dead |
| 2 → 3 | **+2** | 3 (2 lost, 1 gained) | **7** (6 damage heals + the 1 predicted repair loss) | the only step with a **live mechanism**: +6 −1 = **+5 outside the channel**, of which the variance channel took back 3 |

The mechanism's own signature is unusually clean at step 2 → 3: the six healed samples are
*exactly* the six the sibling analysis projected by name, every one via retain-primary, and the
one projected repair loss (`011819`) also landed as projected. The four projection misses all
sit in the byte-variance channel.

**The stable core.** 24 samples are wrong-direct → correct-BLEND in **every** sealed round, and
4 are correct → wrong in every round: a paired movement of **+20 samples that is invariant
across four independent flights**, with each round's own total landing 1 to 5 samples below it
(15, 15, 17, 19). Only 8 of those 28 ever showed direct-byte instability, and all 8 kept their
sign across four re-decodes.

So the honest split of the headline is: a **large, stable, evidence-override core** (+20
invariant; nearest-neighbour retrieval succeeding where the direct answer failed), **one real
mechanism increment** at round 3 (+5 at the sample level, from restoring the protect-direct
term the baseline form was designed around and never had), and **a ±3-to-5-sample noise band**
that the α and τ rounds mistook for signal. The +2 of round 2 is noise; the +15 of round 0 is
the mechanism.

## 7. Question 6 — reviewer report

### Strengths

1. **The direction is not in doubt on this split.** Four independent flights, four positive
   gains, 90% and 95% CIs excluding zero in every round, and 0 of 10,000 bootstrap replicates
   at or below zero for the best round.
2. **The effect is not a prior in disguise.** The train-prior baseline — the arm's own scenario
   plus TRAIN's majority action, at zero extra contacts — scores 39–41 and is beaten by 26–28
   samples. This is the single hardest question a reviewer asks of a retrieval result, and the
   answer is unambiguous.
3. **The effect survives its own documented nondeterminism.** The mandated adversarial floor is
   +15 (CI [+6, +24]); the observed-worst floor is +12 (CI [+2, +22]). Both exclude zero.
4. **The effect survives the baseline's build confound.** Scored against each round's own
   in-session direct responses, the gain is +12/+14/+15/+20 — the same story.
5. **A large invariant core.** +20 samples of paired movement is stable across all four flights.
6. **Mechanism-level predictability.** Round 3's outcome was projected sample-by-sample offline
   before the flight and landed with zero mechanism-level misses. Predictive offline modelling
   of one's own system is stronger evidence of understanding than the aggregate number is.
7. **Hygiene is genuinely good.** Decontamination receipt, utterance-granularity exclusion of
   reserved tiers, seal-then-score, dev-role runtime, no gold in runtime.

### Threats to validity

| # | threat | status |
|---|---|---|
| T1 | **Selection on the evaluation set.** Four rounds of knobs *and one code change* were chosen against these 100 samples. Every interval here prices sampling noise, not selection. | **OPEN — structural.** Only a one-shot confirmatory tier answers it. |
| T2 | **Non-determinism in the comparator.** 19–25 of 100 direct responses differ byte-wise from the M0 responses the pairing uses. | **MITIGATED, not closed**: §3's floors and §4's in-session comparator both survive; resend pairs are byte-identical by construction; but the campaign has no repeated-decode variance estimate at fixed configuration. |
| T3 | **Cross-build baseline.** M0 was flown once on the zero-copy build; BLEND arms ran the base build at `-np 8`. | **MITIGATED** by the in-session direct comparator (§4), which shows the same gain. |
| T4 | **Confirmatory-tier contamination.** DEV-100 nests inside DEV-500; 20% of the planned confirmatory denominator is exposed. | **OPEN** — no remedy registered (§5). |
| T5 | **Concentration of the effect.** 10 of 19 net samples come from two scenarios (`cooking`, `play`), nine scenarios are flat, two lose. n = 5–6 per scenario. | **OPEN** — per-scenario claims are unsupported at this n; only the pooled number is defensible, and even it rests on a narrow base. |
| T6 | **Small absolute denominator.** 100 samples, 29 discordant pairs at round 3. | **OPEN by design** (iteration tier), closed only by a larger confirmatory read. |
| T7 | **Two systematic losses.** `music` −2 and `email` −1: the damage mechanism is nearest-neighbour retrieval onto a confusable sibling intent. | **CHARACTERIZED** (sibling analysis §5–6): 5 of the residual damage samples carry fused mass 1.0 on the sibling. Not fixed. |
| T8 | **Label-space conformance is a confound in the framing, not in the arithmetic.** 35–39 of 100 direct answers name a non-existent intent; part of what the knowledge plane supplies is the legal vocabulary. | **QUANTIFIED, OPEN as a framing question**: the train-prior baseline (which also has the vocabulary) still loses by 26–28, so vocabulary alone does not explain the gain — but a reviewer is entitled to ask for a label-inventory-in-contract control arm. |
| T9 | **Single carrier, single core, single snapshot.** SLURP only, one frozen model, one KB build. | **OPEN** — a generalization claim is out of scope at this tier and is not made. |

### The conditions under which the claim would be publication-credible

The claim — *"a knowledge-conditioned two-contact decode beats direct decode on SLURP dev"* —
would be credible to this reviewer when all of the following hold, and not before:

1. **A confirmatory-tier interval excluding zero**, read **once**, on a split whose samples
   were not used for selection. Concretely: DEV-500's 400-sample unexposed remainder as the
   primary number (T4), with the pre-registered statistic, seed and CI level fixed in advance
   and the tuned configuration frozen by hash before the read.
2. **Resend-controlled determinism.** A repeated-decode variance estimate at fixed
   configuration — the same arm flown twice, byte-identical prompts, same service — so the
   effect can be reported against a *measured* run-to-run band rather than against a floor
   constructed adversarially after the fact (T2). The campaign's per-round resend pair proves
   prompt identity; it does not estimate outcome variance.
3. **A same-protocol no-knowledge control that shares the label vocabulary** (T8), so the
   claim is "evidence helps" and not "telling the model the label set helps".
4. **The literature-consistency check** — that the measured effect size and mechanism are in
   the range the retrieval-augmented-SLU literature reports for comparable training-free
   settings, and that no published baseline already achieves it more cheaply. (Being conducted
   in parallel; its outcome is not prejudged here.)
5. **Honest scope in the sentence itself**: one carrier, one frozen core, one KB snapshot, one
   operating point — with the damage channel (`music`, `email`) reported alongside the gain,
   not buried.

Items 1–3 are all cheap relative to what the campaign has already spent. None of them is
authorized by this row.

## 8. What this document does not do

It registers no round, selects no knob, authorizes no flight, and reaches no verdict on the
baseline form, on convergence, or on paper-candidate qualification. It adds one analysis module,
one machine-readable receipt, and this note. Every number in it is an **iteration-tier** number
on data that has been read four times; the ladder's answer to the question the campaign poses is
a one-shot confirmatory reading that has not happened.
