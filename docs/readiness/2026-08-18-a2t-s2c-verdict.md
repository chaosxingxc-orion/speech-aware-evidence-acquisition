# P-A2T Stage-2c form-robustness verdict — ROBUST / CHANNEL-REOPENED (registered one-shot read, 2026-08-18)

Mechanical outcomes computed by the pinned offline read suite (`59c6fa5` — `scripts/a2t_s2c_read.py`
-> `speech_aware_evidence_acquisition.analysis.a2t_s2c_read`; 20/20 unit tests green immediately
before the read, clean tree at `878e1ee`) over the single COMPLETED attempt
`attempt-20260818T175018Z-0d3363` of the flown Stage-2c form-robustness probe (360 rows = C1 120 +
C2 120 + C3 120, flight archive `878e1ee`, flight machinery `cabe07c`, registration `a6652da`). Read
archive: `docs/checks/speech-aware-evidence-acquisition/2026-08-18-a2t-s2c-read/` (`verdict.json`,
`report.txt`, `README.md`, `MANIFEST.sha256`). The suite ran **exactly once** (it is
idempotence-guarded: a pre-existing `verdict.json` refuses a second run before any work happens);
the exposure row `SAEA-PROBE-a2t-s2c-120` flips to consumed in the same commit.

The primary verdict is decided by **C1 and C2 jointly**; C3 fires no primary branch and is read only
through the **independent DEPLOY-AUGMENT overlay** (preregistration §3). The suite's module
docstring carries eight numbered engineering-interpretation notes; they were reviewed and approved
before the read and are cited here by number, never re-litigated. Notes 1 (the induced-substitution
yardstick is the UNCHANGED Stage-2/2b one — the supplied tool's defaults looked up in the FULL
registry, identically for all three arms, mirroring B2's own convention for C3), 2 (rate-based
conversion thresholds, raw-count induced thresholds), 4 (retention is computed and reported but
carries NO verdict clause in this probe) and 7 (verdicts are evaluated pooled) are load-bearing for
the tables below. Every scoring primitive is imported unchanged from `analysis.a2t_s2_read`, so
each number here is directly comparable to the consumed Stage-2 and Stage-2b verdicts' own.

## 1. Headline — the clean supply form is not a rendering artifact; the augmenting position re-opens the value channel

| question | verdict | one line |
|---|---|---|
| **FORM-ROBUSTNESS** (C1+C2 jointly) | **ROBUST** | Permuted (**10/120**, induced 4) and verbalized (**9/120**, induced 3) both clear every clause — B1's 8/120 was the envelope **minimum**, not a knife edge. |
| **DEPLOY-AUGMENT** overlay (C3, independent) | **CHANNEL-REOPENED** | Appended to the full registry, the stripped right row still converts **7/120** but injects **22** — the registry's own in-context defaults resume as a copy source. |

### FORM-ROBUSTNESS clauses (C1 + C2; retention carries NO clause, note 4)

| branch | clause | verdict | detail |
|---|---|---|---|
| **ROBUST** | C1 conversion >= 6/120 | **MET** | conversion **0.0833 (10/120)**, floor 0.0500 — margin +4 flips |
| **ROBUST** | C2 conversion >= 6/120 | **MET** | conversion **0.0750 (9/120)**, floor 0.0500 — margin +3 flips |
| **ROBUST** | C1 induced-substitutions <= 5 | **MET** | induced **4**, ceiling 5 — margin **1** |
| **ROBUST** | C2 induced-substitutions <= 5 | **MET** | induced **3**, ceiling 5 — margin 2 |
| FORM-FRAGILE | C1 conversion <= 3/120 | not met | 0.0833 vs ceiling 0.0250 |
| FORM-FRAGILE | C2 conversion <= 3/120 | not met | 0.0750 vs ceiling 0.0250 |
| FORM-FRAGILE | C1 induced >= 20 | not met | 4 vs floor 20 |
| FORM-FRAGILE | C2 induced >= 20 | not met | 3 vs floor 20 |

**FORM-ROBUSTNESS OVERALL: ROBUST** — all four clauses fired; no fragility clause came close.

### DEPLOY-AUGMENT clauses (C3 alone; fires no primary branch, note 5)

| flag | clause | verdict | detail |
|---|---|---|---|
| DEPLOYABLE | C3 conversion >= 6/120 | **MET** | conversion **0.0583 (7/120)**, floor 0.0500 — margin **1** flip |
| DEPLOYABLE | C3 induced-substitutions <= 5 | **not met** | induced **22**, ceiling 5 — exceeded 4.4x |
| CHANNEL-REOPENED | C3 induced-substitutions >= 20 | **MET** | induced **22**, floor 20 — margin **2** |

**DEPLOY-AUGMENT OVERALL: CHANNEL-REOPENED.**

The two headlines in one sentence each. **ROBUST: "supply structure, withhold values" is a property
of the content choice, not of B1's exact rendering** — permuting the field/constraint order or
verbalizing the constraints as prose moves conversion *up* (8 -> 10 and 8 -> 9) while injection stays
in the 2–4 band, so the Stage-2b caveat that B1 cleared its floor with zero margin is now bounded:
across three independent renderings of the same stripped content, 8/120 is the envelope floor and
both perturbed forms sit above it (both also clear B1's own stricter 8/120 CONFIRMED-CUT floor, at
+2 and +1). **CHANNEL-REOPENED: the clean regime does not survive the deployment augmenting
position** — when the stripped row is appended to the full 152-row registry (whose body still
carries the correct tool's `argument_defaults`, exactly as a retriever-over-an-unmodified-registry
would present it), injection returns at 22 against B1's 2, and the benefit-to-harm ratio inverts
from B1's 4:1 to **7:22 (0.32:1)** — worse-signed than even Stage-2's full-value row (16:34,
0.47:1). Across the four stripped-row arms, injection tracks one variable: whether the tool's
values are anywhere in context (absent — B1 2, C1 4, C2 3; present in the registry body — C3 22).

## 2. Per-arm aggregates (pooled — never the headline, per note 7)

Exactly as the pinned suite wrote them. Counts in parentheses are derived from the rates against
n=120 and are exact integers. `empty` is the broad definition inherited from Stage-2 (predicted call
list literally empty regardless of `parsed`), so parse failure is a subset of it.

| arm | n | retention | conversion | EM flips | slot P | slot R | slot F1 | empty | parse-fail | induced |
|---|---|---|---|---|---|---|---|---|---|---|
| **C1** (permuted stripped row, replacing) | 120 | 0.7417 (89) | **0.0833 (10)** | 10 | 0.2944 | 0.3867 | 0.3343 | 0.2500 (30) | 0.2500 (30) | **4** |
| **C2** (verbalized stripped row, replacing) | 120 | 0.8917 (107) | **0.0750 (9)** | 9 | 0.2451 | 0.4133 | 0.3077 | 0.1000 (12) | 0.0917 (11) | **3** |
| **C3** (stripped row appended to full registry) | 120 | 0.9417 (113) | **0.0583 (7)** | 7 | 0.2821 | 0.5267 | 0.3674 | 0.0583 (7) | 0.0583 (7) | **22** |

Cited from the consumed Stage-2 and Stage-2b verdicts (`docs/readiness/2026-08-18-a2t-s2-verdict.md`,
`docs/readiness/2026-08-18-a2t-s2b-verdict.md`) — same 120 ids, same scorer, same primitives, not
re-measured here:

| arm | n | retention | conversion | EM flips | slot F1 | empty | parse-fail | induced |
|---|---|---|---|---|---|---|---|---|
| B1 (ordered stripped row, replacing) | 120 | 0.8667 (104) | 0.0667 (8) | 8 | 0.3307 | 0.1250 (15) | 0.1083 (13) | **2** |
| B2 (full registry + highlighted **wrong** row) | 120 | 0.8250 (99) | 0.0083 (1) | 1 | 0.3102 | 0.1000 (12) | 0.0500 (6) | **0** |
| S1' (full row with values, replacing) | 120 | 0.9333 (112) | 0.1333 (16) | 16 | 0.4077 | 0.0583 (7) | 0.0583 (7) | **34** |
| N0r (zero-supply re-fly) | 40 | 0.8750 (35) | 0.0000 (0) | 0 | 0.3200 | 0.1250 (5) | 0.1250 (5) | 0 |

Baseline for every conversion figure is fixed by the headroom set's own defining criterion:
`tool_accuracy = 1.0`, `exact_match = 0.0` for all 120. "Conversion" and "EM-flip rate" are the same
quantity; "retention" is the raw mean `tool_accuracy`. No A0 re-fly. **Noise floor 0.0250 and
conversion floor 0.0500 (= 6/120) are cited from Stage-2's N0r, not re-measured** (preregistration
§4); this probe flew no noise arm. Registry `argument_defaults` parse warnings: **0**.

### Empty-call decomposition, against B1's format-hygiene finding

Parse failure fails closed to an empty prediction, so `empty - parse_fail` counts **well-formed**
empty tool-call lists. Stage-2b recorded, as an unregistered observation, that stripping the
defaults degraded format hygiene (S1' 7/7 -> B1 15/13). The three C-arms bound that finding:

| arm | empty (total) | parse failure | well-formed abstention |
|---|---|---|---|
| **C1** (permuted) | **30** | **30** | 0 |
| **C2** (verbalized) | 12 | 11 | 1 |
| **C3** (augmenting) | 7 | 7 | 0 |
| B1 (cited) | 15 | 13 | 2 |
| S1' (cited) | 7 | 7 | 0 |

The degradation is **form-sensitive, not value-sensitive**. Permuting the stripped row's field and
constraint order doubles B1's damage (13 -> 30 parse failures, 25% of the arm — the worst format
hygiene of any correct-tool arm flown, concentrated in tier8_intent_blending 8/16 and
tier3_multi_intent 13/29); verbalizing the same content as prose *improves* on B1 (13 -> 11); and
embedding the stripped row in the full registry restores S1'-level hygiene exactly (7/7). So B1's
regression was not the cost of removing values per se but of the resulting object's presentation,
and the augmenting position — whatever its injection cost (§4) — is the format-safest way to show a
stripped row. C1's depressed pooled retention (0.7417) is largely this same artifact: its 30 parse
failures mechanically zero `tool_accuracy` on those rows, and its retention floor cells
(tier3 0.5517, tier8 0.5000) are its parse-failure cells. Retention carries no verdict clause here
(note 4), and none of these axes was registered.

## 3. The robustness envelope — B1 / C1 / C2

Three independent renderings of the identical content (the correct tool's registry row, schema
structure and constraints kept, `argument_defaults` stripped, replacing supply position), same 120
ids, same reused Stage-2 roster mapping (the suite's note-6 harness check proved per-row that all
three C-arms carry exactly Stage-2's `s1p_tool_names` labels), same detector:

| axis | B1 (ordered) | C1 (permuted) | C2 (verbalized) | envelope |
|---|---|---|---|---|
| conversion | 8/120 (0.0667) | 10/120 (0.0833) | 9/120 (0.0750) | **[0.0667, 0.0833]** |
| induced substitutions | 2 | 4 | 3 | **[2, 4]** |
| benefit : harm | 4.0 : 1 | 2.5 : 1 | 3.0 : 1 | [2.5 : 1, 4.0 : 1] |
| retention | 0.8667 (104) | 0.7417 (89) | 0.8917 (107) | descriptive only |
| parse failures | 13 | 30 | 11 | [11, 30] |

**The envelope holds.** Its conversion floor (B1's 8/120) sits above the registered 6/120 clause
floor with two flips to spare; its induced ceiling (C1's 4) sits under the 5-count clause ceiling;
and B1 — the arm whose zero-margin clearance motivated this probe — turns out to be the *worst* of
the three renderings on the benefit axis, not a lucky one. Per the registered ROBUST outcome,
Stage-2B qualification may cite this envelope: **conversion [8/120, 10/120], induced [2, 4], across
three surface forms of the values-stripped row**. The per-tier stability behind it is stronger than
the pooled numbers suggest (§5): C2's conversion cells differ from B1's in exactly one tier
(tier7_multiturn +1) and C1's in exactly two (tier2 +1, tier7 +1); tier1_direct converts 5/23 in
all three arms and the two compositional tiers convert 0 in all three.

What the envelope does not license: the induced clauses cleared on margins of **1 and 2 raw
counts** — one additional injection in C1 would have voided ROBUST (into INCONCLUSIVE-C, since the
20-count fragility floor is far away). The clean-form injection band [2, 4] is narrow and
consistent, but at these counts it is not a robust clearance of the ceiling, and no re-fly of any
arm exists to give it a variance.

## 4. C3 vs B2 — the augmenting position, right row vs wrong row

C3 and B2 are byte-for-byte the same construction with opposite content: the full 152-row registry
exactly as A0 showed it, plus one row appended under the same "particularly relevant" header — B2's
appended row is the deranged **wrong** tool's (values included), C3's is the **right** tool's row
with values stripped. The pair is the direct content contrast in the deployment-realistic position,
where a retriever *adds* a row and the registry — including the highlighted tool's own
`argument_defaults` — remains in context:

| axis | B2 (wrong row) | C3 (right row, stripped) |
|---|---|---|
| conversion | 1/120 (0.0083) | **7/120 (0.0583)** |
| induced substitutions | 0 | **22** |
| retention | 0.8250 (99) | **0.9417 (113)** |
| slot recall / precision | 0.4467 / 0.2376 | 0.5267 / 0.2821 |
| well-formed abstentions | 6 | 0 |

**Content decides both channels, in opposite directions.** The right row converts seven times what
the wrong row does (7 vs 1 — B2 sat below the cited noise floor, C3 sits above the 6/120
DEPLOYABLE floor), which re-confirms Stage-2b's knowledge-gating from the other side: the benefit
channel responds to *correct* content even in augmenting position. But the right row also injects
22 where the wrong row injected 0 — and since C3's highlighted row itself carries **no values**,
the copied values can only have come from the registry body's own entry for that tool, the exact
bytes A0 and B2 also had in context. Highlighting a tool makes its in-context registry defaults
active as a copy source; highlighting a wrong tool leaves them inert (B2: 0 induced against its own
row's values, which *were* in the prompt). The injection is concentrated where Stage-2's copy trap
lived: tier3_multi_intent 12 of 22 (S1': 14 of 34), then tier2_parametric 3 and
tier8_intent_blending 3 — same homes, roughly scaled. C3's tier3 slot recall 0.7941 at precision
0.2308 is the sprawling-call signature Stage-2b already described for B2.

Two descriptive counterpoints so the flag is not over-read. C3's retention 0.9417 is the highest of
any supply arm flown in this campaign (S1' 0.9333) and its format hygiene is S1'-clean — the
augmenting position is *gentle* on every axis except injection. And CHANNEL-REOPENED fired on a
margin of **2 raw counts** (22 vs 20); at 19 induced, no overlay flag at all would have fired. The
substantive comparison — 22 against the replacing-form band of [2, 4] on the identical yardstick —
is an 11x step and does not depend on the threshold, but the registered flag itself is a
near-threshold fire and is recorded as such.

## 5. Full per-tier tables (per-tier reporting MANDATORY)

Tiers 1/2/3/8 (n >= 16) carry interpretive weight; tiers 4/5/6/7 are flagged small-n (from each
cell's own row count against the >= 16 threshold). Headroom tier distribution 23/17/29/3/12/12/8/16.

### C1 — permuted stripped row (replacing)

| tier | n | conversion | flips | retention | slot P | slot R | slot F1 | empty | parse-fail | induced | weight |
|---|---|---|---|---|---|---|---|---|---|---|---|
| tier1_direct | 23 | **0.2174** | 5 | 0.9565 (22) | 0.0000 | 0.0000 | 0.0000 ‡ | 1 | 1 | 0 ‡ | interpretive |
| tier2_parametric | 17 | 0.0588 | 1 | 0.8824 (15) | 0.4800 | 0.4286 | 0.4528 | 2 | 2 | 1 | interpretive |
| tier3_multi_intent | 29 | 0.0000 | 0 | 0.5517 (16) | 0.2500 | 0.4412 | 0.3191 | 13 | 13 | 1 | interpretive |
| tier4_implicit | 3 | 0.0000 | 0 | 1.0000 (3) | 0.5000 | 0.6000 | 0.5455 | 0 | 0 | 1 | small-n |
| tier5_needle | 12 | 0.0833 | 1 | 0.9167 (11) | 0.4167 | 0.4545 | 0.4348 | 1 | 1 | 0 | small-n |
| tier6_correction | 12 | 0.1667 | 2 | 0.6667 (8) | 0.3000 | 0.2609 | 0.2791 | 3 | 3 | 0 | small-n |
| tier7_multiturn | 8 | 0.1250 | 1 | 0.7500 (6) | 0.6667 | 0.4444 | 0.5333 | 2 | 2 | 1 | small-n |
| tier8_intent_blending | 16 | 0.0000 | 0 | 0.5000 (8) | 0.1667 | 0.2000 | 0.1818 | 8 | 8 | 0 | interpretive |
| **pooled** | **120** | **0.0833** | **10** | **0.7417 (89)** | **0.2944** | **0.3867** | **0.3343** | **30** | **30** | **4** | — |

### C2 — verbalized stripped row (replacing)

| tier | n | conversion | flips | retention | slot P | slot R | slot F1 | empty | parse-fail | induced | weight |
|---|---|---|---|---|---|---|---|---|---|---|---|
| tier1_direct | 23 | **0.2174** | 5 | 0.9565 (22) | 0.0000 | 0.0000 | 0.0000 ‡ | 1 | 0 | 0 ‡ | interpretive |
| tier2_parametric | 17 | 0.0000 | 0 | 1.0000 (17) | 0.4615 | 0.4286 | 0.4444 | 0 | 0 | 1 | interpretive |
| tier3_multi_intent | 29 | 0.0000 | 0 | 0.8276 (24) | 0.1522 | 0.4118 | 0.2222 | 5 | 5 | 0 | interpretive |
| tier4_implicit | 3 | 0.0000 | 0 | 1.0000 (3) | 0.5000 | 0.6000 | 0.5455 | 0 | 0 | 1 | small-n |
| tier5_needle | 12 | 0.0833 | 1 | 0.7500 (9) | 0.3684 | 0.3182 | 0.3415 | 3 | 3 | 0 | small-n |
| tier6_correction | 12 | 0.1667 | 2 | 0.8333 (10) | 0.2400 | 0.2609 | 0.2500 | 1 | 1 | 0 | small-n |
| tier7_multiturn | 8 | 0.1250 | 1 | 1.0000 (8) | 0.5882 | 0.5556 | 0.5714 | 0 | 0 | 1 | small-n |
| tier8_intent_blending | 16 | 0.0000 | 0 | 0.8750 (14) | 0.2381 | 0.5000 | 0.3226 | 2 | 2 | 0 | interpretive |
| **pooled** | **120** | **0.0750** | **9** | **0.8917 (107)** | **0.2451** | **0.4133** | **0.3077** | **12** | **11** | **3** | — |

### C3 — stripped row appended to the full 152-row registry (augmenting)

| tier | n | conversion | flips | retention | slot P | slot R | slot F1 | empty | parse-fail | induced | weight |
|---|---|---|---|---|---|---|---|---|---|---|---|
| tier1_direct | 23 | 0.1304 | 3 | 1.0000 (23) | 0.0000 | 0.0000 | 0.0000 ‡ | 0 | 0 | 0 ‡ | interpretive |
| tier2_parametric | 17 | 0.0000 | 0 | 1.0000 (17) | 0.3667 | 0.3929 | 0.3793 | 0 | 0 | 3 | interpretive |
| tier3_multi_intent | 29 | 0.0000 | 0 | 1.0000 (29) | 0.2308 | **0.7941** | 0.3576 | 0 | 0 | **12** | interpretive |
| tier4_implicit | 3 | 0.0000 | 0 | 1.0000 (3) | 0.3333 | 0.4000 | 0.3636 | 0 | 0 | 2 | small-n |
| tier5_needle | 12 | 0.0833 | 1 | 0.6667 (8) | 0.4375 | 0.3182 | 0.3684 | 4 | 4 | 0 | small-n |
| tier6_correction | 12 | 0.1667 | 2 | 0.7500 (9) | 0.4118 | 0.3043 | 0.3500 | 3 | 3 | 1 | small-n |
| tier7_multiturn | 8 | 0.1250 | 1 | 1.0000 (8) | 0.6471 | 0.6111 | 0.6286 | 0 | 0 | 1 | small-n |
| tier8_intent_blending | 16 | 0.0000 | 0 | 1.0000 (16) | 0.2979 | 0.7000 | 0.4179 | 0 | 0 | 3 | interpretive |
| **pooled** | **120** | **0.0583** | **7** | **0.9417 (113)** | **0.2821** | **0.5267** | **0.3674** | **7** | **7** | **22** | — |

‡ **tier1_direct's slot F1 = 0.0000 and induced = 0 are definitional artifacts, not quality
signals** — inherited verbatim from the Stage-2 verdict §4: all 23 tier1_direct headroom golds carry
zero arguments, so micro slot P/R is 0/0 and the bare-key alignment excludes every predicted
argument from induced counting there. Its real failure mode is argument over-generation, invisible
to both guardrail columns.

Per-tier readings, kept descriptive:

- **The conversion pattern is nearly form-invariant.** tier1_direct 5/5/3 flips across C1/C2/C3
  (B1: 5), tier6_correction 2 in every arm (B1: 2), tier5_needle 1 in every arm (B1: 1),
  tier7_multiturn 1 in every arm (B1: 0). C2 differs from B1's conversion cells in exactly one
  tier, C1 in exactly two, each by one flip. The ROBUST verdict is carried by the same samples
  converting under every rendering, not by different wins netting out.
- **The two compositional tiers remain immovable — now under seven supply forms.** tier3_multi_intent
  (29) and tier8_intent_blending (16) convert 0 under S1', S2, S4, B1, B2, C1, C2 and C3 alike.
  45 of the 120 headroom samples, 37.5%, have never been converted by any single-row supply flown.
- **C3's injection sits exactly where Stage-2's did.** tier3_multi_intent 12 (S1': 14),
  tier2_parametric 3 (S1': 8), tier8_intent_blending 3 — with tier3 pairing the campaign's highest
  slot recall (0.7941) with 0 conversions: coverage through copied defaults is not correctness.
- **C1's format collapse co-locates with its retention collapse.** tier3 13 parse failures /
  retention 0.5517, tier8 8 / 0.5000 — a permuted schema row does not merely convert less, it
  breaks call emission in the tiers that need composition. C2 shows the same shape at half the
  amplitude (tier3 5 parse failures); C3 shows none of it (0 parse failures in all four
  interpretive-weight tiers; its 7 live entirely in tier5_needle and tier6_correction).
- **C3's retention is a wall of 1.0000 in five tiers** including all four interpretive-weight tiers
  — the augmenting position never cost the core a previously-correct selection outside the two
  small-n tiers (tier5 8/12, tier6 9/12) whose losses are parse-failure-mechanical.

## 6. Integrity

- Flight status `COMPLETED`, `error: null`, `request_failures: []`, `arms: ["C1","C2","C3"]`, 360
  result rows, arm counts exactly 120/120/120, `requests_replayed_from_cache: 0`, no duplicate
  `(arm, sample_id)` pairs, seed 20260807.
- `split_identity_hash` `e1d751e6c76e49d087620842ba17c34e432a4602169dc2b93ee7e0a529ca332c` agrees
  verbatim across the flight receipt, the frozen discovery-split probe receipt and the
  exposure-ledger cell. `config_hash` `54a4617c…bc71`, `protocol_hash` `a805d906…900e`, trace
  manifest hash `eb49ea6c…d48d`.
- **Harness defects: none.** Every structural check is a fail-closed refusal raised before any
  scoring; the suite scored, so none fired. The note-6 check independently verified, per row, that
  every C-arm's written `supplied_tool` label matches what Stage-2's reused arm plan implies for
  that sample — the same `s1p_tool_names` set for all three arms — so "the C-arms supply exactly
  B1's content" is proved from the flight's own bytes. The reused plan is
  `$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-a2t-s2-120/attempt-20260818T124955Z-84b944/SAEA-PROBE-a2t-s2-120.arm-plan.json`.
- Registry `argument_defaults` parse warnings: **0**.
- **No recheck section exists, by design**: like Stage-2/2b, the flight embedded no metrics, so
  nothing independently cross-validates the scorer.
- The read was model-free and read-only: no model session, no GPU, no installs, no mutation of the
  attempt directory. **Zero core contact.**
- Spend (from the flight, not this read): **360 core calls** of the 380 planned / 400 registered;
  **1905.846 speech-audio-seconds** of 2621 planned / 3000 registered; **0.124 GPU-h** of the 0.75
  registered (16.5%); wall 340.9 s flight loop / 446.1 s GPU-occupied; 1,672,839 prompt tokens,
  14,946 completion tokens, 0 tool calls. Server `llama.cpp-featcache` build sha256 `097c96ec…1c68`,
  model `Qwen3-Omni-30B-A3B-Instruct-Q4_K_M` sha256 `0751c279…066d`, mmproj sha256 `f0dfe825…2883`,
  `-np 1` context delta so C3's ~12.9k-token prefill fits the single slot. Feature-cache delta zero.
- Read suite pre-gate: `pytest tests/unit/test_a2t_s2c_read.py` 20 passed, clean tree at `878e1ee`;
  flight archive MANIFEST verified (`sha256sum -c`, 29 files OK) immediately before the read.

## 7. What Stage-2, Stage-2b and Stage-2c jointly establish for the L5 supply law

Stage-2 found that single-row schema supply on this carrier is **signed** — it converts 16/120 of
the argument-failure headroom while injecting 34 of the supplied row's literal default values
(COPY-TRAP), and dilution does not attenuate the harm. Stage-2b **located the sign in the values**:
stripping `argument_defaults` collapses injection 34 -> 2 while keeping 8 of the 16 conversions
(4:1), and the corrected wrong-row control showed the benefit channel is **knowledge-gated** — a
highlighted wrong row converts 1/120 and injects nothing. Stage-2c now answers the two questions
that reading left exposed, one each way.

**"Supply structure, withhold values" survives presentation perturbation.** The law is not an
artifact of B1's exact rendering: across three surface forms of the same stripped content the
conversion envelope is [8/120, 10/120] with induced [2, 4], every rendering clears every registered
clause, and B1 — the zero-margin arm — is the envelope's *floor*, not its lucky draw. The per-tier
conversion pattern is nearly identical across forms, which is what a content-carried (rather than
rendering-carried) effect should look like. What *is* form-sensitive is format hygiene: a permuted
stripped row doubles B1's parse failures to 30/120 and drags its unregistered retention axis to
0.7417, so within the robust envelope the renderings are not interchangeable in cost — ordered or
verbalized presentation is strictly saner than permuted.

**It does not survive the deployment augmenting position.** When the stripped row is *appended* to
the unmodified registry — the position a retrieval-augmentation SUPPLY plane actually occupies —
the correct tool's defaults are still in context inside the registry body, and highlighting the
tool re-activates them as a copy source: 22 injections against the replacing-form band of [2, 4],
on the identical yardstick, concentrated in exactly Stage-2's copy-trap tiers. Conversion holds
above floor (7/120) and selection is the campaign's best (0.9417), but the benefit-to-harm ratio
(0.32:1) is worse than the full-value row Stage-2 flagged as net-negative. The joint mechanism
statement across all seven correct-tool supply arms is one sentence: **the benefit channel follows
the row's structure and its knowledge content; the harm channel follows the presence of the tool's
values anywhere in context, not merely in the supplied row.** The engineering consequence for the
OBS/ORG/SUPPLY/USE decomposition: the clean 4:1 regime is not reachable by SUPPLY-side augmentation
over an intact registry — it requires the values to be absent from the whole context, which is an
ORG-side action (a value-stripped registry, or replacing supply) rather than a retrieval choice.

What each bound licenses. The Stage-2 row licenses citing the signed-supply/COPY-TRAP finding
(16/120 vs 34, dilution non-attenuating). The Stage-2b row licenses the channel localization
(values, 34 -> 2, 4:1) and the knowledge-gating of the benefit channel (wrong row inert). This row
licenses exactly two citations: (i) the **form-robustness envelope** — Stage-2B qualification may
cite conversion [8/120, 10/120] and induced [2, 4] across B1/C1/C2 as the registered ROBUST outcome
permits; and (ii) the **CHANNEL-REOPENED deployment flag** — descriptive, near-threshold (22 vs
20), meaning the clean form's harm bound does *not* transfer to the augmenting position. None of
the three rows licenses a confirmatory, superiority or generalization claim; all are n=120
discovery-split readings under one quantization, one sampling policy and one prompt family.

## 8. Limitations — read these with the numbers

- **Discovery split, n=120 per arm, descriptive only.** No confirmatory claim, no superiority
  claim, no generalization beyond this split, this quantization, this sampling policy, this prompt.
  One conversion is 0.83pp.
- **The ROBUST induced clauses cleared on margins of 1 and 2 raw counts** (C1 4 vs ceiling 5, C2 3
  vs 5). One additional injection in C1 would have voided ROBUST into INCONCLUSIVE-C. The [2, 4]
  band is narrow and internally consistent across three renderings, which is the best evidence at
  this n, but no clause on raw counts this small is a robust clearance.
- **CHANNEL-REOPENED is a near-threshold fire: 22 vs floor 20.** At 19 induced no overlay flag
  would have fired at all. The 11x step against the replacing band does not depend on the
  threshold; the registered flag does.
- **No registry-only induced baseline exists on this yardstick.** A0 and N0r were never scored for
  induced substitutions against the correct tool's default set (A0's read predates the detector;
  N0r supplied no roster), and the registry body containing those defaults was in context for A0
  too. C3's 22 is therefore attributed to *highlighting* by design contrast (same yardstick as
  B1's 2 with values absent; B2's 0 with a wrong row highlighted and its values present), not by
  subtracting a measured un-highlighted baseline. A registry-only arm scored on this yardstick
  would close the gap cheaply.
- **DEPLOYABLE's conversion clause was met on a margin of 1 flip** (7 vs floor 6) — moot for the
  overlay outcome, recorded for completeness.
- **No noise arm flew, and no C-arm or B-arm has ever been re-flown.** Both floors are cited from
  Stage-2's N0r; every cross-arm delta in this document is a single-run difference, and the
  run-to-run variance of conversion and induced counts on supply arms is unknown.
- **C1's format collapse (30/30 empty/parse-fail) and every retention number are unregistered
  axes.** Retention carries no verdict clause in this probe by design (note 4); the §2 and §5
  format readings are observations for the next design, not findings.
- **Induced substitution is bare argument-key granularity** (the approved Stage-2 choice,
  unchanged): counts are upper bounds, so the [2, 4] band is if anything overstated and the 22 is
  an upper bound — but all arms share the inflation, and the C3-vs-C1/C2 step is measured on the
  identical detector.
- **The tier1_direct slot and induced columns are degenerate** (‡ in §5): 23/23 zero-argument golds
  make those columns blind to over-generation on 23 of 120 samples; every injection statement is
  computed on the other 97.
- **Verdicts were evaluated pooled** (note 7). Per-tier tables are a reporting obligation, never a
  second tier-scoped evaluation.
- **No scorer cross-check**: the flight embedded no metrics, so unlike the A0 read nothing
  independently validates the scoring pass.
- **Scorer semantics are interpretation, not ground truth** (`a2t-scorer-v1`: order-insensitive
  multiset tool matching, case-sensitive names, canonicalized argument comparison, fail-closed
  parsing). Those choices are load-bearing for every number above.
- **The headroom set is a property of one A0 attempt** — a registered seed, not an established
  stable set.
