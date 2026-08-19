# V4 whole-population regression verdict — REGRESSION-COSTLY (registered one-shot read, 2026-08-19)

Mechanical outcome per the registered metrics and verdict rules
(`docs/readiness/2026-08-19-a2t-pop-preregistration-REGISTERED.md` §3), computed by the pinned
offline read suite (`analysis.a2t_pop_read`, coordinator-reviewed before the read) over the
already-flown attempt `attempt-20260819T162625Z-b3257c` (`SAEA-PROBE-a2t-pop-194`, status
`COMPLETED`, 194/194 rows across R0/R1) — zero model contact, zero GPU, no attempt-directory
mutation.

Read archive: `docs/checks/speech-aware-evidence-acquisition/2026-08-19-a2t-pop-read/`
(`verdict.json`, `report.txt`, `README.md`, `MANIFEST.sha256`). The suite ran exactly once
(idempotence-guarded output dir), exit 0, at study HEAD `b5b7f7c` with a clean tree. Exposure row
`SAEA-PROBE-a2t-pop-194` flips to consumed in the same commit. Scope: **descriptive,
discovery-tier, n = 97, single run, one carrier, the EM-regression-eligible population only**.
Audio2Tool CC BY-NC 4.0 carried on every number below.

Pre-read gates, all green before anything was opened: `test_a2t_pop_read.py` **29 passed**; the
flight archive's `MANIFEST.sha256` verified **22/22 OK**; ledger row `consumed = no`; tree clean.
Attempt-directory fingerprint identical before and after the read (`252c8cbd…a582`).

---

## 1. R0-STABILITY STATEMENT (mandatory §3 pre-read item; published BEFORE any verdict)

The registration calls the branch space "trivially reachable — EM can fall on all 97" and makes
the statement's real job the documentation of **R0's own re-fly stability, this population's
first**. R0 is A0's own zero-supply request rebuilt byte-identically through
`Audio2ToolAdapter.assemble_prompt(sample, None)` — the same full-152-row registry, the same
audio, no prompt change whatsoever.

| quantity | R0 value |
|---|---|
| samples | **97** |
| **EM regressions (1 → 0) under a bare re-fly** | **0 / 97** (rate **0.0000**) |
| tool-selection retention | **1.0000** |
| slot F1 | **1.0000** |
| empty-call rate | 0.0000 |
| parse-failure rate | 0.0000 |
| induced substitutions | **0** |

**The frozen core reproduced all 97 already-correct answers exactly.** No prior re-fly of this
specific EM-correct population existed; this is its first empirical stability measurement, and it
is perfect. Two consequences follow and both are load-bearing for everything below.

**(i) The decode path contributes exactly zero regression noise on this axis, in-session.** The
in-session comparator design was not paying for drift it needed to guard against — but it *proved*
that, rather than assuming it. This mirrors P-KEY's TXT-duplicate block, which returned an
empirical |ΔF1| floor of 0.0000 over 35 byte-identical resends.

**(ii) Every regression measured on R1 is therefore attributable to the supply**, not to sampling
variation. Δreg = reg(R1) − reg(R0) is not a difference of two noisy quantities here; the
subtrahend is exactly zero and the σ̂ below is between-sample variance alone.

---

## 2. VERDICT

> ## OVERALL: **REGRESSION-COSTLY**

| quantity | value |
|---|---|
| reg(R0) — zero-supply re-fly | **0 / 97** (0.0000) |
| reg(R1) — B1-form values-stripped self-supplied row | **36 / 97** (**0.3711**) |
| **Δreg = reg(R1) − reg(R0)** | **+36** |
| **σ̂(Δreg)** paired per-sample bootstrap | **4.7616** |
| **90 % CI** (N = 10,000, seed 20260807) | **[+28, +44]** |

### Clause margins (every clause, in the registered order)

| clause | result | margin |
|---|---|---|
| **REGRESSION-SAFE**: Δreg ≤ 2 **and** CI upper ≤ 5 | **not met** | Δreg = 36 exceeds the ≤2 ceiling by **34**; CI upper +44 exceeds the ≤5 ceiling by **39**. *Both* conjuncts fail, each by an order of magnitude |
| **REGRESSION-COSTLY**: Δreg ≥ 6 | **MET** | Δreg = 36 vs floor 6 — clears by **+30**, six times the floor |
| **INCONCLUSIVE-POP** (otherwise) | not reached | — |

**The entire confidence interval lies above the COSTLY floor.** The CI's lower bound (+28) clears
the ≥6 threshold by **+22**; there is no part of the interval in which this result could have been
SAFE or even inconclusive. Combined with §1's exact-zero R0 arm, the finding is about as
unambiguous as this instrument can produce: **the clean supply form destroys roughly 37 % of the
answers the frozen core already had right.**

The registration's own consequence clause applies verbatim: *"the signed law's negative term is
real at whole-population scale; C1/C5 must carry it."*

---

## 3. Induced substitutions — the harm is real and it is *not* the injection channel

| arm | induced substitutions (full-registry default-value yardstick) |
|---|---|
| R0 | **0** |
| R1 | **0** |

This is a **genuine empirical zero on a fixed yardstick, not an instrument null.** The suite builds
`supplied_values` from `full_registry_supplied_values(registry_rows)` — the **full 152-row
registry's** `argument_defaults` — and applies that same yardstick to every row of both arms,
irrespective of what each arm actually supplied (`registry_defaults_parse_warnings` is empty, so
the yardstick parsed cleanly). Had R1's damage taken the form of the core reaching for
registry-default values where the gold wanted something else, this counter would have caught it.
It caught nothing.

**So the 36 regressions are not value injections.** The harm channel C2 characterizes — "the harm
channel rides supplied VALUES, and any in-context values, not structure" — is measured here at
**zero**, while EM regression is measured at **36/97**. Whatever destroys these answers, it is not
the core copying a supplied or in-context value into a slot that wanted a different one.

**What it appears to be instead, with the confound named.** R1 is a **replacing** supply: the
registered construction fills `{tool_schemas}` with the B1-form stripped row(s) of the core's own
A0-selected tool (219–596 characters) **instead of** the full 152-row registry (50,291
characters). Two things change at once — the 151 other rows disappear, and the surviving row's
`argument_defaults` are stripped — and **this design cannot separate them.** The damage is driven
by what the replacing supply *removes*, not by what it *injects*; whether the operative loss is
the registry context or the defaults is not identified by this read and must not be asserted. A
successor separating them (stripped-augmenting over the intact registry vs stripped-replacing) is
the obvious next measurement and is a fresh registration.

**The consequence for C2 is a scope correction, not a refutation.** C2 is true of the *injection*
channel it was measured on and false as a statement about harm in general: on this population,
with induced substitutions at exactly 0, the clean form still destroyed 36 already-correct
answers. Harm does not only ride supplied values. C2 must carry that, and its "not structure"
clause must be restated as a claim about the injection channel specifically.

---

## 4. Per-arm and per-tier tables

### Per-arm (pooled)

| arm | n | retention | reg count | reg rate | slot F1 | empty | parse fail | induced |
|---|---|---|---|---|---|---|---|---|
| **R0** | 97 | **1.0000** | **0** | 0.0000 | **1.0000** | 0.0000 | 0.0000 | 0 |
| **R1** | 97 | 0.9278 | **36** | **0.3711** | 0.7273 | 0.0722 | 0.0722 | 0 |

Three counts coincide exactly at **7/97**: the empty-call rate (0.0722), the parse-failure rate
(0.0722), and the retention loss (90 of 97 retained). The read does not publish the per-sample
intersection, so read this as a strong coincidence rather than a proven set equality — but the
natural decomposition it implies is:

| component of the 36 regressions | count | what happened |
|---|---|---|
| tool-selection lost (empty / unparseable output) | **7** | format collapse — the core emitted nothing callable |
| **right tool, wrong arguments** | **29** | the call survived, the arguments did not |

**29 of the 90 samples (32 %) that still selected the correct tool nevertheless failed EM.** The
dominant failure mode is argument corruption on a correctly selected tool, not selection loss —
which is precisely the mode the *values-stripped* construction would be expected to produce, and
which the induced-substitution yardstick (§3) confirms is not default-copying.

### Per-tier

R0 is uniform and needs no table beyond the statement that **every tier is 0 regressions,
retention 1.0000**. R1:

| tier | n | reg count | reg rate | retention | slot F1 |
|---|---|---|---|---|---|
| tier5_needle | 15 | **9** | **0.6000** | 0.8667 | 0.5882 |
| tier7_multiturn | 22 | **10** | 0.4545 | 0.9545 | 0.7143 |
| tier2_parametric | 19 | 7 | 0.3684 | 1.0000 | 0.8077 |
| tier6_correction | 20 | 6 | 0.3000 | 0.8500 | 0.7429 |
| tier4_implicit | 12 | 3 | 0.2500 | 0.9167 | 0.6667 |
| tier8_intent_blending | 1 | 1 | 1.0000 | 1.0000 | 0.6667 |
| **tier1_direct** | 6 | **0** | **0.0000** | 1.0000 | 0.0000\* |
| **tier3_multi_intent** | 2 | **0** | **0.0000** | 1.0000 | 1.0000 |

\* tier1_direct's slot-F1 column is a **definitional artifact** (zero-argument golds) — qualification
bound 5, carried verbatim; it reads 0.0000 on *both* arms and carries no information.

**The damage is concentrated exactly where arguments matter.** The two tiers with zero regressions
are `tier1_direct` (6 samples, simple direct calls) and `tier3_multi_intent` (2 samples), while the
worst are `tier5_needle` (9/15 = 60 %) and `tier7_multiturn` (10/22 = 45 %) — the tiers whose gold
calls require extracting specific argument values out of the speech. `tier8_intent_blending`'s
1/1 is n = 1 and carries no weight. Two tiers rest on n ≤ 2 and the largest is n = 22, so these
rates are directional structure, not calibrated per-tier estimates.

---

## 5. THE WHOLE-POPULATION SIGNED ACCOUNT

### The registered licence, stated first

The preregistration attached the citable net account to the **SAFE** branch: *"on SAFE the whole-
population net account (conversions cited [8,10]/120 − Δreg, over 400) becomes citable."* SAFE did
not fire. The arithmetic below is therefore published as **the measured magnitude of the negative
term** — the thing the COSTLY branch explicitly requires C1/C5 to carry — and **not** under the
registration's SAFE-branch citation licence. The distinction matters because the SAFE framing was
designed to license a *favourable* net claim; nothing here licenses a favourable one, and this
section makes no superiority claim in either direction.

### The population arithmetic

| population | n | status |
|---|---|---|
| headroom (tool_accuracy = 1 ∧ EM = 0) — where supply can convert | **120** | consumed, cited |
| **EM-correct (tool_accuracy = 1 ∧ EM = 1)** — where supply can regress | **97** | **measured here** |
| **tool-correct total (disjoint union, 0 overlap machine-checked)** | **217** | the ids where an EM-signed rule is defined |
| **tool-selection failures — EXCLUDED** | **183** | EM cannot regress there **and** no gold-free supply-row rule exists for them (prereg §1, recorded limitation) |
| frozen A2T discovery split | **400** | 183/400 = **45.75 %** of the denominator is undefined for this account |

### The signed sum

| term | value | source |
|---|---|---|
| conversions, values-stripped row, envelope across three renderings | **+[8, 10] / 120** | **CITED** from the consumed Stage-2b reads; not re-measured here |
| conversions, the **B1 rendering specifically** (matched to R1's construction) | **+8 / 120** | cited; it is the envelope minimum, robust upward (qualification bound 2) |
| **regressions, B1-form stripped-replacing** | **−36 / 97** | **measured here**, Δreg, CI [+28, +44] |
| **net over the 217 ids where the rule is defined** | **−26 to −28 EM samples** | +[8,10] − 36 |
| **matched-rendering net (B1 vs B1)** | **+8 − 36 = −28** | |
| the same numerator over 400 | **−26 to −28 / 400** | with the 183-exclusion disclosure attached |

**Applied blindly, the clean supply form breaks between 3.6 and 4.5 answers for every one it
fixes.** (36/10 = 3.6; 36/8 = 4.5.)

### Why this one *is* a net-utility calculation, unlike the C2 ratio

Qualification bound 7 is emphatic that C2's "conversions vs injections" comparison **is not a
net-utility calculation**: it crosses two units (EM sample conversions against slot-level value
injections) on overlapping-but-distinct subsets. **This account does not have that defect.** Both
terms are counts of the *same unit* — samples whose exact-match flips — measured with the *same*
frozen scorer, on **disjoint** populations that exactly partition the 217 ids where the rule is
defined. It is a genuine signed sum, and it is the first one this program has been able to form.

That said, it carries its own four bounds, all binding:

1. **The 183 exclusion.** Nearly half the frozen 400 is outside the account entirely. On those ids
   EM cannot regress (already 0) and no gold-free rule exists for what to supply, so they are
   neither a hidden upside nor a hidden downside — they are undefined, and the account must never
   be stated as "over 400" without this sentence attached.
2. **The conversion term is cited, not co-measured.** +[8,10]/120 comes from consumed Stage-2b
   reads on a different session and inherits their bounds, including bound 2's note that B1's
   8/120 cleared its floor with zero margin. The two terms were not measured in one flight.
3. **The headroom set is a property of one A0 attempt** (qualification bound 8) — and so, by the
   identical derivation, is the 97-id EM-correct set. Both partitions are a registered seed's
   product, not an established stable set. R0's 97/97 stability shows the *scoring* is stable
   under re-fly; it does not establish that a different A0 attempt would partition the 400 the
   same way.
4. **Single run, discovery split, one carrier, no measured run-to-run variance on the conversion
   term.** Δreg has a CI; the conversion count does not.

### What this does to C1

C1 claims that **deployment-real supply converts real failures on a frozen core**, with primary
evidence on the 120-sample headroom set, and it already carries the binding population disclosure:
*"a deployment control plane cannot identify [the headroom population] and would supply on all 400;
the whole-population conversion-minus-regression rate is unmeasured pending the registered 97-id
regression arm."*

**That rate is now measured, and it is negative.** The consequences, stated as precisely as the
evidence allows:

- **The conditional claim survives intact.** On the gold-identified headroom set, the
  values-stripped row converts [8,10]/120. Nothing in this read touches that. C1's *mechanism*
  content — that supply can convert real failures on a frozen core — stands.
- **The unconditional deployment reading is refuted.** A control plane that cannot identify the
  headroom set and applies the clean form across the tool-correct population nets **−26 to −28**
  EM samples. C1's population disclosure asked exactly the right question and the answer went
  against the method. This must be stated in C1 as a measured negative, not as an open item.
- **The gold-identification gap is now the whole ballgame.** C1's value is entirely conditional on
  targeting. The measured gap between targeted supply (+8 to +10) and blind supply (−26 to −28) is
  **34 to 38 EM samples wide**, and closing it is an ORG/SUPPLY-side selection problem — deciding
  *where* to supply — not a supply-form problem. Every supply form tested so far is form-robust;
  none of them is safe to apply everywhere.
- **What C1 may become**, with no re-cutting of any registered threshold: a claim about supply
  under a *selection rule*, whose selection rule does not yet exist gold-free. That is a research
  object for a successor, and naming it here authorizes nothing.

### What this does to C2

Covered in §3 and repeated here for the claim record: C2's harm characterization ("rides supplied
VALUES … not structure") is measured at **zero induced substitutions** on both arms while EM
regression is **36/97**. C2 is correct about the injection channel and incomplete as a statement
about harm. The **regression channel is driven by what replacing supply removes**, is roughly four
times larger than the conversion benefit, and does not register on the injection yardstick at all.
C2 must carry the regression channel alongside the injection channel, and its "not structure"
clause must be scoped to injections. The registry-loss vs defaults-stripping confound (§3) is
unresolved and no mechanism attribution beyond "removal, not injection" is licensed.

---

## APPENDIX — SYNTHESIS OF THE FIVE PROBES (input for the §2b / C6 qualification freeze)

Written as the §2b and C6 input the qualification freeze needs, with every bound attached. Five
consumed probes: **P-PHON**, **P-KEY**, **P-TRAP** (the speech-term line) and **V1**
(abstention-asymmetry 2×2), **V4** (this whole-population regression arm) (the strengthening line).
Nothing here is a new measurement; it is the joint reading of five registered one-shot reads, and
it authorizes no claim that its parents do not.

### A. The headline

> The five probes converge on a candidate whose **mechanism is better established and whose
> deployment case is worse** than the draft assumed. On the speech term: supply-use matching is
> now **demonstrably acoustically mediated** — a roster entry equal to this sample's own earlier
> mishearing of this audio captures the output 29/32 (0.9062) while the identical construction
> seeded from another sample's mishearing captures 0/32, Δ = +0.9062, 90 % CI [+0.8125, +0.9688] —
> which kills the deflationary "audio is only a retrieval key" account of P-KEY's null, but leaves
> P-KEY's own question unresolved, since the *net benefit* of audio over the core's own
> 53.6 %-WER transcript is still I = +0.0463 with a CI crossing zero, and the one place acoustic
> mediation has been *measured* rather than inferred it is a **cost** (−0.0958 pooled SLU-F1, 8
> induced substitutions against the control's 0). On abstention: the drafted safety asymmetry is
> **inverted** — under missing evidence the core abstains 11/11, under a missing action it abstains
> 2/11 — so refusal is gated by evidence quality, not by the action space, C6 is unlicensed and
> false as drafted, and §3 item 9 closes affirmatively because the same 2×2 delivers the A2T
> carrier's first audio-conditioning control (9/11 tool calls → 0/11 under duration-matched
> silence). On deployment: the signed law's missing negative term is now measured and it is large
> — the clean values-stripped form converts +[8,10]/120 on the gold-identified headroom set and
> regresses **−36/97** on the EM-correct set (Δreg = 36, CI [+28, +44], against a re-fly baseline of
> exactly 0/97), netting **−26 to −28 EM samples** over the 217 ids where the rule is defined, with
> 183 of the frozen 400 excluded because EM cannot regress there and no gold-free supply rule
> exists. Every number above is discovery-tier, single-run, same-distribution, on n = 32 / 60 / 11 /
> 97 as marked, with SLURP and Audio2Tool both CC BY-NC 4.0; no test split was touched anywhere and
> no superiority, generalization, or paper-scale claim attaches to any of it.

### B. The speech term, as it now stands (§2b input)

§2b asked whether **speech knowledge participates in the supply loop** or the audio serves **only
as a retrieval key** with all benefit realized text-side. Three probes have now spoken and the
question has resolved into two separate questions with two different answers.

| question | probe | answer | bound |
|---|---|---|---|
| *What* does supply convert? | **P-PHON** | **recall-dominant**: 81.8 % (A3) of converted slots were MISSING at baseline; EQUIV-FORMAT 13.6 %; NEAR-MISS 1/44 | speech-snap branch class-starved — only 4/85 baseline failures were NEAR-MISS, so its 25 % floor was unreachable at CR = 1.0; its single NEAR-MISS conversion was format-adjacent on inspection |
| Is the *benefit* speech-specific? | **P-KEY** | **INCONCLUSIVE-KEY**: I = +0.0463, 90 % CI [−0.0033, +0.0970], in the registered dead zone; ~89 % of the supply benefit is realized text-side (Δ_TXT +0.393 vs Δ_AUD +0.440) | reachable window was [0.06, 0.0667], 0.0067 wide; more n cannot resolve a dead-zone point estimate at any n |
| Does *matching* consult the audio? | **P-TRAP** | **ACOUSTIC-MEDIATED**: capture 29/32 vs 0/32, Δ +0.9062, CI [+0.8125, +0.9688] | 28/60 samples excluded at K = 0, 23 of them by the gold zero-overlap check, so the usable 32 are enriched for genuine misperception and 0.9062 is upper-leaning |

**The joint answer, stated as narrowly as the evidence permits.** The speech channel
**participates in supply USE** — it is a live discriminator at match time, not a mere retrieval
key. That disjunct of §2b's question is now **closed affirmatively**, and the opposing disjunct is
**dead**: if matching were text-side, cross-percept traps would be no less matchable than
self-percept ones, and they captured zero. But participation is not benefit, and the **benefit
question remains exactly where P-KEY left it**. The reconciliation the evidence supports — a
reading, not a measurement — is that the acoustic percept is consulted at match time while the
core's own transcript already carries nearly all the information that consultation uses on this
carrier (P-KEY measured a 53.6 %-macro-WER self-transcript costing −0.0001 at baseline and +0.046
under supply).

**Therefore §2b stays OPEN and the freeze stays HELD**, but its statement must be rewritten. It is
no longer "speech knowledge participates, or the audio is only a key" — the second disjunct is
falsified. The live question is now: **speech participation in USE is established; its net value
in the supply loop is not.** P-KEY's own dead-zone finding still governs how that could be
resolved — only a moved estimate can do it, never more n.

**One durable, citable byproduct: self-percept contamination as a USE-side risk.** If a control
plane's evidence roster can contain the core's own earlier emissions on the same audio — any
pipeline with a recall, caching, or self-supply stage can produce this by accident — the core
re-commits at 0.9062 on the trapped population, *reversing repairs the legal roster had already
made* (A0 0.1741 → A3 0.5961 → V1 0.5003), and displaces gold content on 28 % of captures. The
implied mitigation is an ORG-side provenance rule: never re-supply the core's own prior emissions
for the same episode. Bounds: n = 32 usable, one carrier, single run, enriched trap stratum.

### C. The abstention asymmetry (C6 input)

**C6 is not licensed, and it is false as drafted.** The registration bound the C6 licence solely
to ASYMMETRY-CONFIRMED, which failed on both conjuncts (abstention(TW-A) 2/11 short by 6;
confabulation(TP-S) 0/11 short by 8). The measured direction is the reverse of the drafted one:
**refusal is gated by evidence quality, not by the action space.** Under duration-matched silence
the core abstains 11/11 on both registry conditions; under a missing action with real audio it
abstains 2/11, calling a wrong tool 5/11 and failing to parse 4/11.

Three consequences for the claim set, all corrections rather than additions:

1. **C5's silence/withholding sentence is refuted in both halves** on the A2T carrier and must be
   rewritten to the measured facts. The open safety question is not promoted to a claim; it is
   closed *against* the drafted direction.
2. **§3 item 9 is CLOSED affirmatively** — and this is the strengthening line's clearest win.
   Holding the registry fixed and swapping only the audio moves the core from **9/11 confabulated
   calls and 0/11 abstentions to 0/11 calls and 11/11 abstentions**. The A2T carrier, C1's
   primary-evidence carrier, now has a within-carrier audio-conditioning control and it is
   decisive rather than suggestive. Together with P-KEY's SLURP silence-swaps (3/3 changed, with a
   shared-confabulation signature) the program's audio-conditioning evidence is no longer the
   "0/6 on three ids" the draft described.
3. **The SLURP silence-confabulation observation does not transfer.** The two carriers behave
   oppositely under the same manipulation. A reading, not a measurement: SLURP's answer schema
   always expects a filled slot structure so "nothing to say" has no legal surface form, while
   A2T's tool-calling protocol has a native legal empty output and the core uses it. Whether the
   governing variable is the output format's admission of refusal is a testable successor
   question and is untested.

Bounds on all of C: n = 11 per cell, one carrier, single run, and a **tier3-weighted flat draw**
(6/11 tier3 against its ≈24 % population share; four of eight tiers unrepresented). TW-A's 2/11 is
entirely a tier effect — 2/2 on tier1_direct, 0/9 elsewhere — and is the number that caveat
genuinely constrains. The verdict itself is tier-invariant: TP-S is 11/11 on every tier and
ASYMMETRY-CONFIRMED could not have fired under any reweighting.

### D. The whole-population signed account (C1/C2 input)

The strengthening line's second delivery is the term the claim matrix has been missing since C1
was drafted. On the EM-regression-eligible population the clean form regresses **36/97** against a
re-fly baseline of **exactly 0/97**, Δreg = 36, CI [+28, +44], every part of the interval above
the ≥6 COSTLY floor. Netted against the cited **+[8,10]/120** conversions on the disjoint headroom
set, the account over the **217** ids where an EM-signed rule is defined is **−26 to −28 EM
samples**; **183** of the frozen 400 are excluded because EM cannot regress there and no gold-free
supply rule exists for them. Unlike the C2 conversions-vs-injections ratio that bound 7 forbids,
this is a legitimate signed sum: one unit, one scorer, disjoint populations that partition the
defined set.

**What it means for the freeze**: C1's *conditional* claim survives untouched, its *unconditional
deployment* reading is refuted, and the decisive open problem has moved from supply **form** to
supply **targeting** — a 34-to-38-sample gap between targeted and blind application, with no
gold-free selection rule in existence. C2's harm characterization must be scoped to the injection
channel, because the regression channel registered **zero** induced substitutions while destroying
36 answers; the registry-loss vs defaults-stripping confound is unresolved and only "removal, not
injection" is licensed. C5's replacing-branch cost, which the draft described qualitatively, now
has a number.

### E. What the freeze may and may not record

**May record as settled**: the supply benefit is large and overwhelmingly text-side realizable
(P-KEY); the L3 gain is recall-dominant (P-PHON); supply-use matching is acoustically mediated
(P-TRAP); the A2T carrier is audio-conditioned, decisively (V1); refusal is gated by evidence
quality, not action space (V1); the clean form's whole-population signed account is negative (V4);
self-percept contamination is a measured USE-side risk (P-TRAP).

**May not record**: any speech-term benefit claim (P-KEY INCONCLUSIVE, dead zone); C6 in any
restated form (measured false on its carrier); any unconditional deployment claim for the clean
supply form (V4 negative); any per-tier or per-carrier generalization (n ≤ 22 per tier, one
carrier each); any mechanism attribution for the regression channel beyond "removal, not
injection"; and anything at paper scale, which belongs to Stage-3 under its own owner contract.

**The honest one-line summary for the owner**: the mechanism story got stronger and more specific,
the safety story reversed, and the deployment story got worse — and all three of those are results,
not obstacles.

---

No superiority, generalization, deployment, or paper-scale claim attaches to any number in this
document. SLURP and Audio2Tool audio are CC BY-NC 4.0; no test split was touched.
