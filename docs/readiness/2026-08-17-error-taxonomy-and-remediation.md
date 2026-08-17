# Error taxonomy and remediation plan

Date: 2026-08-17 (late night). Owner directive: reclassification is not dismissal — every error
bucket gets a cause, a fix path, an owning module, and a status. Sources: T-NDL decomposition
(`2026-08-17-tndl-decomposition/`), N1 re-run (`2026-08-17-n1-rerun-truewrong/`), P2 R-ladder
verdict, kb34 probe, guard forensics. Denominator: 2,873 wrong entity mentions (r1verify arm,
10 earnings21 calls) unless stated.

## Bucket map

| # | Bucket | Mass | Root cause | Fix lives in | Status |
|---|---|---|---|---|---|
| 1 | FORMAT (written/spoken convention) | 1,921 (66.9%) | output-style vs reference-style mismatch; scorer v1 has no number expansion | scorer v2 + ITN post-layer + format-instruction supply | ticket queued |
| 2 | NAME true errors | 376 true-wrong (236 with 5+ char keys) | OOV/rare proper nouns; per-call evidence starvation | ORG (name KB) + SUPPLY (roster) + flag v3 | main line |
| 3 | NUMERIC true errors | 282 true-wrong | digit mishearing; DATE 17.2% novel (relative dates); reference defects | date-anchor supply; data-defect mask; bounded backlog | mixed |
| 4 | CONVENTION true errors | 294 true-wrong | contraction/abbreviation orthography, 51% novel | scorer equivalence classes + style instruction | hygiene ticket |
| 5 | Consumption behavior (copy/ignore) | P2: 7/9 blind-copy; RIR 0/54 | prompt-level verification incapability; form/dose dependence | scheme design (form/dose/tripwires) — rails | fixed by design, verify per probe |
| 6 | Routing system defects | 45% budget to 3 terms; 2 null-timing windows; 4/10 calls zero windows; precision 48% | flag floor/budget config; roster quality; LOCALIZE bug; evidence starvation | flag v3 offline development | ticket queued |
| 7 | Our own measurement bad cases | 0.94% conflation; uncommitted N1 code; 84.75% misread; multi-label inflation | one-off analysis without committed derivation; no denominator discipline | process rules | partially done |

## Bucket 1 — FORMAT: three fixes, not zero

Reclassifying these as scoring artifacts does NOT close them. A deployment that needs
written-form transcripts ("$53.2M", "2026") still receives wrong-form output; that is a real
capability gap in inverse text normalization (ITN).

1. **Scorer v2 (measurement honesty)**: frozen format-normalizing scorer beside v1, dual
   reporting. Removes 1,921 phantom mentions from every future metric. (Queued behind B0.)
2. **ITN post-layer (deployment fix)**: a deterministic, rule-based ITN module in the control
   plane's USE stage — outside the frozen core, zero model contact, fully legal. A few hundred
   lines; converts spoken-form numerals/currency/dates to written form. This *fixes the output*,
   not just the score.
3. **Format-instruction supply (capability probe)**: one cheap arm — does the frozen core follow
   "write numbers as digits, currency as $X.XM" prompt instructions? Measures whether the gap is
   instruction-followable; informs whether the ITN layer is needed at all.

## Bucket 2 — NAME: the main line, four concrete fixes

Causes: long-tail proper nouns the core cannot know; and *evidence starvation* — 4 of 10 calls
shipped 19–54 bytes of ORG/SUPPLY evidence, so nothing could ever route there.

1. **Name-scoped KB from pre-published materials** (52.5% of name errors covered; 54.2% at
   5+ char keys, 0.0% decoy): participant lists, ConEC docs. Owner-ratified.
2. **Compact-roster supply form** (kb34: 10/14 flips; P2: whole-text = copy trap): enforced by
   `SupplyPacket.form` in rails.
3. **Flag v3 — offline development, no flight needed**: the N1 re-run infrastructure evaluates
   any flag against consumed traces via D5 replay (zero GPU, zero exposure). Ticket: (a) per-term
   window cap (anti-monopoly; 45% of budget went to 3 terms), (b) repair/drop the LOCALIZE
   null-timing channel (2 windows burned on nothing), (c) guaranteed per-call minimum roster
   from participant metadata (kills the 4-call starvation), (d) floor/budget re-tune (worth
   15.7 pts) and roster quality (worth 11.4 pts) against the pre-registered gates: clear the
   28.81% roster ceiling to earn consideration; 40.25% matched-budget oracle is the pass line.
4. **NOVEL floor 32.2%**: honest ceiling for KB approaches; candidate mechanisms for a later
   probe: within-episode self-consistency (first vs repeated mentions) and spelled-out cues.

### 2.1 The repair chain for the 376 (owner question: can they be DETECTED and ACQUIRED?)

Repair = Reach × Acquire × Consume. Measured link by link:

**Acquire** (does the correct form exist legally?): within the 376 true-wrong names, 233
(**62.0%**) are pre-published in the call's own materials; 143 (38.0%) are novel. On the
5+ char subset the coverage is 54.2% at 0.0% decoy.

**Reach** has two modes with opposite economics:

- **Global mode (detection-free)**: put the compact name roster in every prompt; no error
  detection needed at all. Reach = 100% of acquirable mass by construction. Earnings rosters
  are 6–15 names/call — far below the 50–100-entry dose-degradation onset, so global supply is
  dose-safe here. Consume: kb34 measured 10/14 flips (small n). Chain estimate:
  1.0 × 0.62 × ~0.7 ≈ **~40% of the 376 plausibly repairable with no detector** — this is the
  L1 name-supply mechanism probe's registered question.
- **Targeted mode (detection-dependent)**: runtime detection signals that are legal today:
  (a) roster-band grapheme distance (the current flag family — shipped reach 8.51%/376,
  13.14%/236; roster ceiling 28.81%; perfect-flag-at-budget 40.25%); (b) lexical
  implausibility (non-word tokens like "sitimes"); (c) decode disagreement (two-pass
  self-consistency, costs a second pass); (d) token-level confidence via API logprobs —
  observation not control, but absent from consumed traces, so it needs one instrumented
  flight before it can be evaluated. **The broken link in targeted mode is Consume, not
  Reach**: the replay chain converted 0 (27 routed → 0 flips; RIR 0/54) because it supplied
  whole reference text — the measured copy trap. Any flag-v3 targeted arm must therefore
  switch its supply form to compact roster as well.

**Why detection still matters even though global mode wins on earnings**: global mode's
dose-safety is a small-corpus luxury. At L2 (ContextASR) the legal subset-wide roster is
thousands of entities — far past the dose law — so the SUPPLY gate (retrieval/threshold
selection) becomes load-bearing exactly where the corpus scales. Earnings lets us skip
detection; L2 does not. Detection R&D (flag v3, offline) is therefore an L2 prerequisite,
not an L1 luxury.

### 3.1 Relative-date resolution is agent-plane work, not ASR (owner ruling direction)

Splitting "date handling" into three layers resolves the confusion:

1. **Transcription** (L1, verbatim): "the fourth quarter of last year" transcribed as those
   words is CORRECT. Demanding "Q4 2019" from a transcript is a category error.
2. **Form conversion** (control plane, deterministic ITN): "twenty twenty" → "2020". Rules,
   no semantics.
3. **Semantic resolution** (agent plane): "last year" → 2019 requires a temporal anchor plus
   inference. This is exactly what L3 slots and L5 tool arguments demand (tool calls need ISO
   dates), and where the omni-agent earns its keep over dedicated ASR. Accordingly the
   **temporal anchor** (call/current date from shipped metadata) is promoted from an "L1 ASR
   patch" to a **standard element of the scheme's prompt assembly**, and resolution accuracy
   is measured at L3/L5 where the task demands it — not scored against L1 transcripts.

## Bucket 3 — NUMERIC true errors: two real fixes plus one bounded backlog

1. **Date anchoring (new, cheap, legal)**: DATE is the worst numeric class (17.2% novel) partly
   because relative dates ("the fourth quarter of last year") need the call date to resolve. The
   call date is shipped metadata. Supplying "this call took place on YYYY-MM-DD" is a
   few-token, legal-tier arm. Add to the L1 mechanism-probe backlog.
2. **Reference-defect mask (data hygiene, do now)**: truncated gold tokens ("199", "201" for
   1995/2015) manufacture wrong mentions against correct hypotheses. Extend the recorded-defect
   pattern (cf. `a3e22af`): audit-verified defect list, documented scoring mask, upstream note.
   Without this every future measurement inherits poisoned rows.
3. **Pre-published numeric residue (178 mentions, ~6% of true mass)**: values exist in PDFs but
   number supply via rosters is ineffective by construction (ConEC itself strips numerals from
   biasing lists). Bounded backlog with explicit reason: low mass, needs document-grounded
   retrieval machinery; revisit only if L2+ probes show number-slot demand.

## Bucket 4 — CONVENTION: hygiene

Contraction/abbreviation equivalence classes in scorer v2; a style-instruction line in the
prompt template. Low research value; must not silently inflate any metric again.

## Bucket 5 — consumption behavior: fixed by design, verified per probe

The standard scheme v1 encodes the fixes: compact-roster form, dose caps (degradation past
50–100 entries), per-arm copy-rate with registered tripwires, self-supplied provenance tier for
history-derived content, silence/mismatch controls. Every probe re-verifies them; none is
assumed.

## Bucket 6 — routing defects: see Bucket 2 fix 3 (flag v3 offline ticket)

## Bucket 7 — our own measurement bad cases: fixes and new rules

Occurred: the 0.94% figure conflated targeting with routing on a two-thirds-phantom denominator;
the original N1 analysis was never committed; 84.75% was quoted as number/date share when it was
non-name share; multi-label tag inflation went unstated; agent harness twice blocked report.md
writes (coordinator archived verbatim — workaround documented).

Fixed: figure retired, re-derived from stronger provenance, bundles committed with manifests.

New standing rules (this document is their record):
1. Any quoted metric must have committed derivation code and a pinned denominator definition in
   the same bundle.
2. Mention-level and distinct-token shares are reported together wherever labels are
   multi-valued.
3. A "phantom" reclassification always names the module that inherits the fix (scorer, ITN,
   KB, flag, mask) — reclassification without an owner is dismissal, which is prohibited.
