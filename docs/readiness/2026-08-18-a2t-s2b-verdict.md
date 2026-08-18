# P-A2T Stage-2b follow-up verdict — Q-A CONFIRMED-CUT / Q-B INCONCLUSIVE-B (registered one-shot read, 2026-08-18)

Mechanical outcomes computed by the pinned offline read suite (`d85a025` — `scripts/a2t_s2b_read.py`
-> `speech_aware_evidence_acquisition.analysis.a2t_s2b_read`; 21/21 unit tests green immediately
before the read, clean tree) over the single COMPLETED attempt `attempt-20260818T153859Z-8da515` of
the flown Stage-2b follow-up probe (240 rows = B1 120 + B2 120, flight archive `8380a81`). Read
archive: `docs/checks/speech-aware-evidence-acquisition/2026-08-18-a2t-s2b-read/` (`verdict.json`,
`report.txt`, `README.md`, `MANIFEST.sha256`). The suite ran **exactly once**; the exposure row
`SAEA-PROBE-a2t-s2b-120` flips to consumed in the same commit.

The two questions are **independent** — no exclusive branch lattice across them (preregistration §1,
the P-SLU rule-gap lesson), and the MISLEAD overlay fires independently of whichever Q-B verdict
holds. The suite's module docstring carries seven numbered engineering-interpretation notes; they
were reviewed and approved before the read and are cited here by number, never re-litigated. Notes 1
(rate-based conversion thresholds, raw-count induced thresholds), 2 (the 6/120 floor is Stage-2's own
N0r formula cited, not re-measured) and 3 (retention == raw mean `tool_accuracy`) are load-bearing
for the tables below. Every scoring primitive is imported unchanged from `analysis.a2t_s2_read`, so
each number here is directly comparable to the consumed Stage-2 verdict's own.

## 1. Headline — the corruption channel IS the default values; the wrong row is inert but retention is short

| question | verdict | one line |
|---|---|---|
| **Q-A** — corruption-channel localization (arm B1) | **CONFIRMED-CUT** | Stripping `argument_defaults` collapses injection **34 -> 2** while keeping conversion above the registered floor at **8/120**. |
| **Q-B** — schema vs knowledge (arm B2) | **INCONCLUSIVE-B** | A highlighted wrong row with the correct tool present converts **1/120** — below the cited noise floor — but retention **0.8250** misses KNOWLEDGE-TIED's 85% clause. |
| **MISLEAD** overlay (independent) | **not met** | B2 retention 0.8250 >= the 0.80 ceiling. The highlighted wrong row did **not** clearly drag selection. |

### Q-A clauses (arm B1)

| branch | clause | verdict | detail |
|---|---|---|---|
| **CONFIRMED-CUT** | B1 induced-substitutions <= 5 | **MET** | induced **2**, ceiling 5 |
| **CONFIRMED-CUT** | B1 conversion >= 8/120 | **MET** | conversion **0.0667 (8/120)**, floor 0.0667 |
| NOT-DEFAULTS | B1 induced-substitutions >= 20 | not met | induced 2, floor 20 |

**Q-A OVERALL: CONFIRMED-CUT** — both clauses fired; the alternative did not.

### Q-B clauses (arm B2)

| branch | clause | verdict | detail |
|---|---|---|---|
| SCHEMA-CONTRIBUTES | B2 conversion >= 6/120 (= max(2x noise, 5%), cited) | not met | conversion **0.0083 (1/120)**, floor 0.0500 |
| KNOWLEDGE-TIED | B2 conversion <= 2/120 | **MET** | conversion 0.0083, ceiling 0.0167 |
| KNOWLEDGE-TIED | B2 tool-selection retention >= 85% | **not met** | retention **0.8250 (99/120)**, floor 0.85 |
| MISLEAD (independent) | B2 retention < 80% | not met | retention 0.8250, ceiling 0.80 |

**Q-B OVERALL: INCONCLUSIVE-B** — KNOWLEDGE-TIED is a conjunction and it fails on its second clause
by 2.5pp, while SCHEMA-CONTRIBUTES fails by a factor of six on the first. §4 argues the *content*
half of Q-B is in fact answered decisively and only the retention guardrail is undetermined.

The two headlines in one sentence each. **Q-A: the copy trap was carried by the supplied row's
literal values, not by its schema.** Remove the values and 32 of the 34 injections disappear (94.1%)
while half the conversions survive (8 of 16) — the benefit-to-harm ratio moves from S1's 16:34
(0.47:1) to **8:2 (4:1)**, an ~8.5x improvement, and the sign of the supply flips from net-negative
to net-positive on the registered rule's own comparison. **Q-B: with the correct tool left in the
registry, a highlighted wrong row does essentially nothing** — 1 conversion in 120, zero induced
substitutions, and per-axis behaviour statistically indistinguishable from Stage-2's zero-supply N0r
arm. What blocks the clean KNOWLEDGE-TIED label is a retention number sitting 5pp below N0r's own
byte-identical re-fly band, on the same metric Stage-2 already recorded as too noisy to bear this
weight.

## 2. Per-arm aggregates (pooled — never the headline, per note 6)

Exactly as the pinned suite wrote them. Counts in parentheses are derived from the rates against
n=120 and are exact integers. `empty` is the broad definition inherited from Stage-2 (predicted call
list literally empty regardless of `parsed`), so parse failure is a subset of it.

| arm | n | retention | conversion | EM flips | slot P | slot R | slot F1 | empty | parse-fail | induced |
|---|---|---|---|---|---|---|---|---|---|---|
| **B1** (nodefaults row) | 120 | 0.8667 (104) | **0.0667 (8)** | 8 | 0.2727 | 0.4200 | 0.3307 | 0.1250 (15) | 0.1083 (13) | **2** |
| **B2** (augmented wrong row) | 120 | 0.8250 (99) | **0.0083 (1)** | 1 | 0.2376 | 0.4467 | 0.3102 | 0.1000 (12) | 0.0500 (6) | **0** |

Cited from the consumed Stage-2 verdict (`docs/readiness/2026-08-18-a2t-s2-verdict.md`) — same 120
ids, same scorer, same primitives, not re-measured here:

| arm | n | retention | conversion | EM flips | slot P | slot R | slot F1 | empty | parse-fail | induced |
|---|---|---|---|---|---|---|---|---|---|---|
| S1' (`S1p`, full row) | 120 | 0.9333 (112) | 0.1333 (16) | 16 | 0.3184 | 0.5667 | 0.4077 | 0.0583 (7) | 0.0583 (7) | **34** |
| S2 (diluted K=9) | 120 | 0.9250 (111) | 0.0917 (11) | 11 | 0.2945 | 0.5400 | 0.3812 | 0.0583 (7) | 0.0583 (7) | **34** |
| S4 (replacing wrong row) | 120 | 0.0000 (0) | 0.0000 (0) | 0 | 0.0000 | 0.0000 | 0.0000 | 0.9583 (115) | 0.0333 (4) | 0 |
| N0r (zero-supply re-fly) | 40 | 0.8750 (35) | 0.0000 (0) | 0 | 0.2632 | 0.4082 | 0.3200 | 0.1250 (5) | 0.1250 (5) | 0 |

Baseline for every conversion figure is fixed by the headroom set's own defining criterion:
`tool_accuracy = 1.0`, `exact_match = 0.0` for all 120. "Conversion" and "EM-flip rate" are the same
quantity; "retention" is the raw mean `tool_accuracy` (note 3). No A0 re-fly.

**Noise floor 0.0250 and conversion floor 0.0500 (= 6/120) are cited from Stage-2's N0r, not
re-measured** (preregistration §2; note 2 verifies that Stage-2's own formula evaluated at N0r's 0/40
reproduces the preregistration's literal 6/120 exactly). This probe flew no noise arm.

Registry `argument_defaults` parse warnings: **0**. No supplied value was silently dropped.

### Empty-call decomposition (derived from the two rates above, no second read)

Parse failure fails closed to an empty prediction, so `empty - parse_fail` counts **well-formed**
empty tool-call lists — a deliberate decision not to call anything:

| arm | empty (total) | parse failure | well-formed abstention |
|---|---|---|---|
| **B1** | 15 | 13 | **2** |
| **B2** | 12 | 6 | **6** |
| S1' (cited) | 7 | 7 | 0 |
| S4 (cited) | 115 | 4 | 111 |
| N0r (cited) | 5 | 5 | 0 |

B1's format hygiene is materially worse than S1's — 13 parse failures against 7, and 15 empty
predictions against 7 — which is the first cost of stripping the defaults and is discussed in §3.
B2's 6 well-formed abstentions are the first non-trivial abstention count on a full-registry prompt;
S1'/S2/N0r all recorded zero.

## 3. Q-A — the corruption channel is the default values (arm B1 against S1')

B1 is S1' with one change: the supplied row keeps its schema structure and constraints and loses its
`argument_defaults`. Same 120 ids, same replacing supply form, same reused S1p roster mapping (the
suite's note-5 harness check independently proved the flight used exactly that mapping, per-row).
The paired deltas:

| axis | S1' | B1 | delta |
|---|---|---|---|
| induced substitutions | **34** | **2** | **-32 (-94.1%)** |
| conversions | 16 (0.1333) | 8 (0.0667) | -8 (-50.0%) |
| benefit : harm | 16 : 34 = 0.47 : 1 | 8 : 2 = **4 : 1** | ~8.5x better |
| retention | 0.9333 (112) | 0.8667 (104) | -8 samples |
| slot F1 | 0.4077 | 0.3307 | -0.0770 |
| empty / parse-fail | 7 / 7 | 15 / 13 | +8 / +6 |

**The registered question is answered cleanly.** The preregistration's CONFIRMED-CUT definition —
"the corruption channel IS the default values; the clean supply form is 'row minus defaults'" — is
met on both clauses, and NOT-DEFAULTS is refuted by a factor of ten (2 against a floor of 20). The
induced-substitution yardstick is unchanged from Stage-2: B1's count is still computed against the
**full registry's** default-value set for the supplied tool via `score_row`'s own `registry_index`
lookup, not against the stripped prompt text, so 34 -> 2 is an apples-to-apples measurement of the
same event on the same detector. That is what makes it a localization rather than a definitional
artifact — the detector still looked for exactly the values it found 34 times under S1', and found 2.

The per-tier collapse is as clean as the pooled number. Stage-2 recorded the copy trap concentrated
in tier3_multi_intent (14 of 34) and tier2_parametric (8 of 34); under B1 those become **0 and 1**.
The two survivors are one in tier2_parametric and one in tier4_implicit (n=3).

**Two costs are recorded honestly against the CONFIRMED-CUT headline.**

- **Half the conversions go with the values.** 16 -> 8. The default values were not purely a
  corruption channel; they were also carrying half the benefit. On the interpretive-weight tiers
  alone the loss is 9 -> 5 (all five B1 conversions there are tier1_direct). The clean supply form
  is better-signed, not strictly better: a control plane choosing it trades 8 conversions for 32
  avoided injections.
- **Format hygiene degrades.** Parse failures nearly double (7 -> 13) and empty predictions rise
  (7 -> 15), concentrated in tier8_intent_blending (4/16 parse failures), tier3_multi_intent (5/29)
  and tier6_correction (2/12). A row stripped of concrete values appears to be a harder object for
  the core to emit a well-formed call against. This is an unregistered observation and no rule
  turned on it, but it is the mechanism most likely behind the conversion loss and it should be
  measured deliberately before "row minus defaults" is adopted as the standard supply form.
- **Retention drops 8 samples (0.9333 -> 0.8667).** At 13.3% loss this sits essentially exactly on
  Stage-2's measured 12.5% byte-identical selection-noise band, so it is not read as damage.

## 4. Q-B — the wrong row is inert; only the retention guardrail is undetermined

B2 shows the core the full 152-row registry exactly as A0 did, plus the deranged wrong tool's row
appended under a "particularly relevant" header — the correct tool is **present**, the wrong row is
**highlighted**. This is precisely the redesigned control the Stage-2 verdict §5 named as the single
highest-value next probe, and it does what S4 structurally could not.

**The content half of the question is answered decisively, and the answer is "knowledge".**

- **Conversion 1/120 (0.0083)** — below not just the 0.0500 conversion floor but below the cited
  **0.0250 noise floor** itself. A wrong-content row, however prominently framed, does not convert
  argument failures. The single flip is in tier7_multiturn (n=8).
- **Induced substitutions 0.** The core never copied the highlighted wrong row's default values into
  a call. The copy channel that Stage-2 measured at 34 under a *correct* row is completely absent
  under a *wrong* one — which is itself strong evidence that the copy trap is a content-relevance
  effect rather than a blind proximity/formatting effect.
- **B2 lands on N0r's profile on every axis.** Retention 0.8250 vs 0.8750, conversion 0.0083 vs
  0.0000, slot F1 0.3102 vs 0.3200, slot recall 0.4467 vs 0.4082. Adding a highlighted wrong row to
  the full registry leaves the frozen core approximately where showing it nothing leaves it. (The
  two arms score different sample sets — 120 vs a tier-proportional 40 — so this is a profile
  comparison, not a paired test; see §7.)
- Against S1' the contrast is the one Q-B was written to draw: same registry-present condition, one
  supplied row each, **right row 16 conversions / 0.4077 slot F1, wrong row 1 conversion / 0.3102
  slot F1**. Stage-2's conversions are knowledge-tied.

**What is undetermined is the retention guardrail, and only that.** KNOWLEDGE-TIED is a conjunction
and its second clause asks B2 to hold >= 85% of A0's correct tool selections; it held 99/120 =
82.50%, missing by 3 samples' worth. Read against the comparator that exists, the shortfall is
marginal: N0r's byte-identical zero-supply re-fly lost 12.5% (5/40) of previously-correct selections,
B1 lost 13.3% (16/120), B2 lost 17.5% (21/120). B2 is ~5pp worse than the re-fly band and ~4pp worse
than B1 — a real direction, far too small at this n to separate from the noise Stage-2 already
documented on this axis, and explicitly not enough to fire MISLEAD's 80% ceiling.

Descriptively (not a second evaluation — note 6 fixes verdicts to pooled aggregates), B2's retention
loss is concentrated in small-n tiers: tier7_multiturn loses 5 of 8 and tier4_implicit loses 3 of 3,
which together with tier2_parametric's 4 of 17 account for 12 of the 21 losses. Restricted to the
four interpretive-weight tiers (n=85) B2's retention is 75/85 = **0.8824**, above the 85% clause;
restricted to the four small-n tiers (n=35) it is 24/35 = 0.6857. The registered rule is pooled and
its answer stands, but the pooled number is being set by 35 samples across four tiers, three of which
have n <= 12.

**The MISLEAD overlay did not fire, and that is a substantive result rather than an absence.** The
concern it encoded — that a prominently framed wrong row drags selection — is not supported: 82.5%
of selections survived, no wrong-row values were copied, and the core's behaviour tracked the
zero-supply arm. The highlighted wrong row **did not mislead** at any level this instrument can
resolve. What cannot be excluded is a mild drag of a few samples, and this read cannot decompose the
21 lost selections into "went to the highlighted wrong tool" versus "went somewhere else in the
152-row registry" — the retention metric is `tool_accuracy` and records only correctness. That
decomposition is the obvious cheap follow-up if the question matters.

## 5. Full per-tier tables (per-tier reporting MANDATORY)

Tiers 1/2/3/8 (n >= 16) carry interpretive weight; tiers 4/5/6/7 are flagged small-n. The suite flags
this generically from each cell's own row count against the >= 16 threshold, never from a hardcoded
tier list. Headroom tier distribution is 23/17/29/3/12/12/8/16.

### B1 — nodefaults row (schema structure + constraints, no values)

| tier | n | conversion | flips | retention | slot P | slot R | slot F1 | empty | parse-fail | induced | weight |
|---|---|---|---|---|---|---|---|---|---|---|---|
| tier1_direct | 23 | **0.2174** | 5 | 0.8696 (20) | 0.0000 | 0.0000 | 0.0000 ‡ | 3 | 1 | 0 ‡ | interpretive |
| tier2_parametric | 17 | 0.0000 | 0 | 1.0000 (17) | 0.4615 | 0.4286 | 0.4444 | 0 | 0 | 1 | interpretive |
| tier3_multi_intent | 29 | 0.0000 | 0 | 0.8276 (24) | 0.1875 | 0.4412 | 0.2632 | 5 | 5 | 0 | interpretive |
| tier4_implicit | 3 | 0.0000 | 0 | 1.0000 (3) | 0.5000 | 0.6000 | 0.5455 | 0 | 0 | 1 | small-n |
| tier5_needle | 12 | 0.0833 | 1 | 0.9167 (11) | 0.4000 | 0.4545 | 0.4255 | 1 | 1 | 0 | small-n |
| tier6_correction | 12 | 0.1667 | 2 | 0.7500 (9) | 0.2609 | 0.2609 | 0.2609 | 2 | 2 | 0 | small-n |
| tier7_multiturn | 8 | 0.0000 | 0 | 1.0000 (8) | 0.5625 | 0.5000 | 0.5294 | 0 | 0 | 0 | small-n |
| tier8_intent_blending | 16 | 0.0000 | 0 | 0.7500 (12) | 0.2500 | 0.4000 | 0.3077 | 4 | 4 | 0 | interpretive |
| **pooled** | **120** | **0.0667** | **8** | **0.8667 (104)** | **0.2727** | **0.4200** | **0.3307** | **15** | **13** | **2** | — |

### B2 — augmented wrong row (full 152-row registry + highlighted deranged row)

| tier | n | conversion | flips | retention | slot P | slot R | slot F1 | empty | parse-fail | induced | weight |
|---|---|---|---|---|---|---|---|---|---|---|---|
| tier1_direct | 23 | 0.0000 | 0 | 0.9130 (21) | 0.0000 | 0.0000 | 0.0000 ‡ | 2 | 0 | 0 ‡ | interpretive |
| tier2_parametric | 17 | 0.0000 | 0 | 0.7647 (13) | 0.2581 | 0.2857 | 0.2712 | 1 | 0 | 0 | interpretive |
| tier3_multi_intent | 29 | 0.0000 | 0 | 0.9310 (27) | 0.2435 | **0.8235** | 0.3758 | 1 | 1 | 0 | interpretive |
| tier4_implicit | 3 | 0.0000 | 0 | **0.0000 (0)** | 0.0000 | 0.0000 | 0.0000 | 3 | 1 | 0 | small-n |
| tier5_needle | 12 | 0.0000 | 0 | 0.8333 (10) | 0.4091 | 0.4091 | 0.4091 | 1 | 1 | 0 | small-n |
| tier6_correction | 12 | 0.0000 | 0 | 0.9167 (11) | 0.2593 | 0.3043 | 0.2800 | 0 | 0 | 0 | small-n |
| tier7_multiturn | 8 | **0.1250** | 1 | **0.3750 (3)** | 0.3846 | 0.2778 | 0.3226 | 2 | 1 | 0 | small-n |
| tier8_intent_blending | 16 | 0.0000 | 0 | 0.8750 (14) | 0.2500 | 0.5000 | 0.3333 | 2 | 2 | 0 | interpretive |
| **pooled** | **120** | **0.0083** | **1** | **0.8250 (99)** | **0.2376** | **0.4467** | **0.3102** | **12** | **6** | **0** | — |

‡ **tier1_direct's slot F1 = 0.0000 and induced = 0 are definitional artifacts, not quality
signals** — inherited verbatim from the Stage-2 verdict §4, which verified against the frozen gold
that all 23 tier1_direct headroom samples carry gold calls with **zero arguments**. Micro-summed slot
precision/recall over an empty gold slot set is 0/0 and reported 0.0000, and the bare-key alignment
rule excludes every predicted argument from induced-substitution counting there. The substantive
reading is the opposite of what the zeros suggest: tier1_direct headroom failure is **argument
over-generation**, and it is the one tier where a stripped schema row still works — B1 converts
5/23 (21.74%), against S1's 6/23 (26.09%). Telling the core the primitive takes no arguments does
not require showing it any values, which is exactly what Q-A predicts.

Other per-tier readings, kept descriptive:

- **The copy trap's two homes went quiet.** tier3_multi_intent 14 -> 0 induced and tier2_parametric
  8 -> 1 under B1, with conversion unchanged at 0/29 in tier3 and 3 -> 0 in tier2. The largest
  headroom tier remains immovable under every supply form flown so far (0/29 under S1', S2, B1 and
  B2 alike): single-row schema supply, with or without values, is not a compositional-failure remedy.
- **tier2_parametric is where the conversion cost of stripping lands hardest.** 3 -> 0 conversions
  and 8 -> 1 induced — the densest-argument tier converts only when it is shown actual values, and
  when it is shown them it copies them. It is the cleanest single-tier illustration of the whole
  Q-A trade.
- **tier6_correction inverts** (S1' 0/12 -> B1 2/12) and **tier7_multiturn collapses** (S1' 4/8 ->
  B1 0/8). Both are small-n at 12 and 8; neither difference is separable from noise and neither is
  read as a finding.
- **tier3_multi_intent's B2 slot recall 0.8235 is the highest recall cell in either arm** while its
  precision is 0.2435 — the full registry plus a distractor produces sprawling calls that cover the
  gold slots and much else. It converts nothing (0/29): coverage is not correctness.
- **B2's retention floor cells are tier4_implicit 0/3 and tier7_multiturn 3/8.** These two tiers,
  11 samples, contribute 8 of the 21 lost selections that block KNOWLEDGE-TIED.

## 6. Integrity

- Flight status `COMPLETED`, `error: null`, `request_failures: []`, `arms: ["B1","B2"]`, 240 result
  rows, arm counts exactly 120/120, `requests_replayed_from_cache: 0`, no duplicate
  `(arm, sample_id)` pairs, seed 20260807.
- `split_identity_hash` `e1d751e6c76e49d087620842ba17c34e432a4602169dc2b93ee7e0a529ca332c` agrees
  verbatim across the flight receipt, the frozen discovery-split probe receipt and the
  exposure-ledger cell. `config_hash` `8820275b…4d12`, `protocol_hash` `ff642e87…a3d7`.
- **Harness defects: none.** Every structural check is a fail-closed refusal raised before any
  scoring; the suite scored, so none fired. This probe's own added check (note 5) independently
  verified, per row, that the attempt's written `supplied_tool` label matches what Stage-2's reused
  arm plan implies for that `(arm, sample)` — B1's S1p roster names, B2's single wrong-tool name —
  so the claim "Stage-2's derangement mapping was reused verbatim" is proved from the flight's own
  bytes rather than assumed. The reused plan is
  `$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-a2t-s2-120/attempt-20260818T124955Z-84b944/SAEA-PROBE-a2t-s2-120.arm-plan.json`.
- Registry `argument_defaults` parse warnings: **0**.
- **No recheck section exists, by design**: like Stage-2 and unlike the A0 read, this probe's
  `outputs.jsonl` embeds no flight-time metrics, so nothing independently cross-validates the scorer.
- The read was model-free and read-only: no model session, no GPU, no installs, no mutation of the
  attempt directory. **Zero core contact.**
- Spend (from the flight, not this read): **240 core calls** of the 260 planned / 280 registered;
  **1270.564 speech-audio-seconds** of 1985 planned / 2000 registered; **0.1177 GPU-h** of the 0.5
  registered (23.5%); wall 315.6 s; 1,638,764 prompt tokens, 9,632 completion tokens, 0 tool calls.
  Server `llama.cpp-featcache` build sha256 `097c96ec…1c68`, model
  `Qwen3-Omni-30B-A3B-Instruct-Q4_K_M` sha256 `0751c279…066d`, mmproj sha256 `f0dfe825…2883`,
  `-c 49152 -np 1 -fa on -ngl 999 -ctk q8_0 -ctv q8_0`.
- Read suite pre-gate: `pytest tests/unit/test_a2t_s2b_read.py` 21 passed, clean tree at `8380a81`.

## 7. What Stage-2 and Stage-2b jointly settle for the L5 supply law

Stage-1 established the target: +30.0pp, 120 named samples where the frozen core picks the right tool
and still fails the call. Stage-2 asked whether prompt-level schema supply converts them and returned
**COPY-TRAP** — supply converts 16/120 while injecting 34 of the supplied row's literal default
values, a benefit-to-harm ratio of roughly 1:2. Its finding was that **supply is signed**: not a
monotonically beneficial dose axis, because past the first row it opens a copy channel that dilution
does not attenuate. It left two things open, and Stage-2b closes one and largely settles the other.

**The signed-supply law now has a located sign.** The harm and the benefit are not the same channel
and can be separated by construction. The corruption rides on the **concrete values** in the supplied
row; the schema **structure** carries a real but smaller share of the benefit and almost none of the
harm. Stripping the values removes 94% of the injection and retains 50% of the conversions, moving
the ratio from 0.47:1 to 4:1. That converts Stage-2's warning ("supply as flown is net-negative")
into an engineering instruction ("the value payload is the failure mode; supply structure, withhold
values"), and it comes with a measured price — 8 lost conversions, worse format hygiene, and the
observation that on the densest-argument tier the values were doing all the work. So the L5 supply
curve is not one curve but at least two superposed channels with opposite signs, and a control plane
can choose its point on each independently rather than accepting the bundled sign.

**And the benefit channel is knowledge, not format.** Stage-2 could not test this: its wrong-row arm
replaced the registry, withheld the correct tool, and its 0.0000 conversion was structural. B2 runs
the corrected control — correct tool present, wrong row highlighted — and the wrong row converts
1/120, below the noise floor, injects nothing, and leaves the core's whole per-axis profile sitting on
the zero-supply arm's. Stage-2's 16 conversions therefore required the **right** row: they are tied to
the content of the supplied knowledge, not to the presence of a schema-shaped object or to attention
paid to a highlighted block. Stage-2's provisional inference from the tier profile — that the gains
sort by compositional complexity in a way a pure formatting effect would not — is now confirmed by a
measured contrast rather than left as an inference. The registered KNOWLEDGE-TIED **label** is
withheld only because the conjunction's retention clause asks B2 to beat 85% on a metric whose own
byte-identical re-fly loses 12.5%, and B2 landed at 82.5%; the same clause design already sank
SUPPLY-CONVERTS in Stage-2 for the same reason. That is a defect in the guardrail's calibration
against a known-noisy axis, not evidence of misleading, and MISLEAD's independent test explicitly did
not fire.

Jointly, then: **supply on this carrier is a two-channel, content-gated intervention.** It helps only
when it carries the right knowledge; the help is modest (13.3% of the headroom at best, concentrated
in tiers 1/2/7 and exactly zero on the 45 compositional samples in tiers 3 and 8); the harm is a
value-copy channel that can be cut almost entirely at the cost of half the help; and a wrong supply
is inert rather than actively damaging — the core neither copies from it nor is meaningfully dragged
by it. For the OBS/ORG/SUPPLY/USE decomposition this is a SUPPLY-side result with a USE-side
corollary: what a control plane must get right is *which* row it retrieves, because a wrong retrieval
costs almost nothing and a right one pays only when its values are withheld. None of this is
confirmatory; it is an n=120 discovery-split reading and is licensed only as such.

## 8. Limitations — read these with the numbers

- **Discovery split, n=120 per arm, descriptive only.** No confirmatory claim, no superiority claim,
  no generalization beyond this split, this quantization, this sampling policy, this prompt. One
  conversion is 0.83pp; the 8-flip Q-A conversion loss and the 3-sample Q-B retention shortfall are
  suggestive at this n, nothing more.
- **B1's conversion of exactly 8/120 sits precisely ON the CONFIRMED-CUT floor.** One fewer
  conversion — a single sample — would have produced INCONCLUSIVE-A. The verdict is correct as
  registered and evaluated, but it has zero margin on that clause and must not be cited as a robust
  clearance. The induced clause, by contrast, cleared its ceiling by a wide margin (2 vs 5) and
  refuted NOT-DEFAULTS by 10x.
- **No supply-arm noise floor exists, and this probe flew no noise arm at all.** Both floors are
  cited from Stage-2's N0r (EM 0/40, selection 5/40). Nothing repeats B1 or B2, so their run-to-run
  variance is unknown, and every delta against S1'/S2/S4 is a single-run difference.
- **Selection-axis instability is material and now blocks a verdict.** Stage-2 measured 12.5% loss
  across byte-identical re-flies; Q-B's KNOWLEDGE-TIED clause demands >= 85% retention. B2's 82.5%
  is inside that noise, so INCONCLUSIVE-B is at least partly an artifact of a guardrail calibrated
  above the axis's own reproducibility. This is recorded as a rule-design defect, consistent with
  Stage-2's identical finding on SUPPLY-CONVERTS.
- **Harm cannot appear as an EM regression on this sample set.** All 120 headroom ids have
  `exact_match = 0.0` by construction, so induced substitutions and retention losses are the only
  channels through which supply damage can register at all. The instrument measures the copy channel
  as an argument-level event count, not as a score drop, and the "conversions vs injections" ratio
  the registered rules compare is therefore a comparison across two different units on two
  overlapping-but-distinct sample subsets. It is the registered comparison and is reported as such;
  it is not a net-utility calculation.
- **Induced substitution is measured at bare argument-key granularity, not `(tool_name, key)`** —
  the approved Stage-2 choice, unchanged. A supplied default that coincidentally matches a gold
  argument key of a different tool in the same sample counts. Exposure is bounded but non-zero, and
  it can only inflate a count, never deflate one — which means B1's **2** is an upper bound and the
  34 -> 2 collapse is if anything understated.
- **The tier1_direct slot and induced columns are degenerate** (‡ above): 23/23 zero-argument golds
  make micro slot F1 0/0 and exclude every predicted argument from induced alignment. Argument
  over-generation on 23 of the 120 samples is invisible to both guardrail metrics, and every
  statement about leakage is computed on the other 97.
- **B2 vs N0r is a profile comparison, not a paired test.** They score different sample sets (120 vs
  a tier-proportional 40) and no B2-restricted-to-N0r's-40 figure was computed — that would be a
  second scoring pass, which the one-shot discipline forbids. The "B2 lands on N0r" reading in §4 is
  descriptive.
- **The read cannot say where B2's 21 lost selections went.** Retention is raw mean `tool_accuracy`
  and records correctness only, so "dragged to the highlighted wrong tool" is not distinguished from
  "drifted elsewhere in the 152-row registry". MISLEAD's mechanism is therefore untested even though
  its registered threshold did not fire.
- **B1's format-hygiene regression is unregistered.** Parse failures 7 -> 13 and empty predictions
  7 -> 15 are real and are the most plausible mechanism behind the halved conversion, but no rule
  covers them, no threshold was pre-registered for them, and they are reported here as an
  observation for the next design rather than as a finding.
- **Verdicts were evaluated pooled** (note 6). The per-tier tables are a reporting obligation, not a
  second evaluation; the §4 observation that B2's interpretive-weight-tier retention would clear 85%
  is descriptive and does **not** amend the verdict.
- **No scorer cross-check**: unlike the A0 read's 0/2400 recheck mismatches, nothing independently
  validates the scoring here, because the flight deliberately embedded no metrics.
- **Scorer semantics are interpretation, not ground truth.** `a2t-scorer-v1` reimplements the paper's
  metrics (order-insensitive multiset tool matching, case-sensitive names, canonicalized argument
  comparison, fail-closed parsing); those choices are load-bearing for every number above.
- **The headroom set is a property of one A0 attempt.** A re-fly would not reproduce it exactly; the
  120 are a registered seed, not an established stable set.
