# Solver intent decision: a model-initiated second look at the top-2 (design)

Author: analysis and design agent (Claude Opus 5.5) for the root coordinator (Fable 5.1), 2026-09-30. Worktree
`fable/solverdecision`, base master `a2f6baab6`. This note is a model-free design: no flight, no registration, no
admission, no exposure-ledger row. Every number is a TRAIN development number (owner decisions 28 and 86). The
evidence section is quoted from `docs/results/2026-09-30-slurp-solver-decision-oracle-offline.md` (read id
`SAEA-SLURP-SOLVER-DECISION-ORACLE-OFFLINE-V1`, driver `scripts/analysis/slurp_solver_decision_oracle.py`).

**Authorities.**

- Owner directive 205: build the system and optimise at system level.
- Owner directive 206: evidence acquisition and tool use are model-initiated, never a system default. Deterministic
  form normalisers are the one exception.
- Owner decision 199: empty is legal.
- Module design `docs/superpowers/specs/2026-09-29-slurp-consumption-module-design.md` section 2d: tool use is a
  model decision, and the decision node is credited before the tool's quality. Section 2c: empty is legal.
- E5 design `docs/superpowers/specs/2026-09-29-e5-asr-tool-slot-value-verification-design.md`: the decision-oracle
  pattern and the three-part gate for slots. This note is its intent analogue.

## 0. The blank

Between about 86 % and the 95 % intent target, the second blank is the Solver's choice among Perception's
candidates. The Solver converts gold at Perception rank 1 at 97.6 %, at rank 2 at about 27 % and at rank 3 at about
12 % (node-gain ledger). Two leads are already closed:

- **The Perception contrast block** was harmful.
- **The "Solver-side contrast" lead** was a composition artefact (block-depth read, Q4).

The question here is narrower. When the Solver keeps rank 1 and gold sits at rank 2 or 3, can the MODEL be given a
way to decide to look again, and would a second look convert?

## 1. Evidence: the decision oracle (offline, seven sealed pools)

Definitions:

- **Decision population:** rows whose note lists two or more candidates and whose Solver kept rank 1.
- **Positive:** gold at note rank 2 or 3. **Negative:** gold at rank 1. **Cost row:** gold off the note.
- **Pools:** AGREE, COMP-1b, W-SV-1 and W4-SV (TRAIN Fold A); P-SV-1, P-SV-2 and P-SV-3 level-2 branch A (TRAIN
  Fold B).

### 1.1 Ceiling

| pool | ceiling rows (gold at rank 2/3, pick wrong) | ceiling pp | positives / negatives / cost rows | b = ceiling / 1,080 |
| --- | ---: | ---: | --- | ---: |
| AGREE | 68 | 6.30 | 59 / 841 / 69 | 0.063 |
| COMP-1b | 75 | 6.94 | 67 / 858 / 64 | 0.069 |
| W-SV-1 | 65 | 6.02 | 63 / 847 / 79 | 0.060 |
| W4-SV | 62 | 5.74 | 61 / 854 / 69 | 0.057 |
| P-SV-1 | 81 | 7.50 | 78 / 836 / 78 | 0.075 |
| P-SV-2 | 80 | 7.41 | 74 / 818 / 85 | 0.074 |
| P-SV-3 | 82 | 7.59 | 79 / 807 / 77 | 0.076 |

**The Solver already leaves rank 1 on its own.** Its spontaneous switches are right on 47-74 % of occasions, but they
reach only 18-28 % of the rank-2/3 gold rows (results note, section 1).

### 1.2 Signals (AUC, positive vs negative; CI95 row bootstrap)

| signal | model-visible today | AUC range over the 7 pools | reading |
| --- | --- | --- | --- |
| boundary margin s(r1) − s(r2), recomputed | no (order only) | 0.20-0.24 | strong (inverted 0.76-0.80) |
| agreement share r1 − r2 | no (pinned table) | 0.21-0.24 | strong, and the same signal: its argmax equals the exemplar-vote argmax on 1,080 / 1,080 rows in every pool |
| exemplar votes r1 − r2 (20 delivered) | yes | 0.21-0.25 | strong |
| exemplar votes for r2 | yes | 0.70-0.73 | moderate |
| r1 scenario (cross-fitted rate) | yes | 0.54-0.65 | weak |
| note r1 is not block rank 1 | yes | 0.55-0.61 | weak |
| exemplar winner is r2 | yes | 0.52-0.56 | weak |
| note candidate count | yes | 0.45-0.54 | none |
| r1 and r2 share the scenario | yes | 0.45-0.48 | none |
| entity-free share of the 20 exemplars | yes | 0.52-0.59 | none |
| twin disagreement | no | 0.50 (same-flight twins: 0-2 disagreeing rows of 1,080); 0.54 cross-flight | none same-flight |

### 1.3 Best two-signal rule under cross-fit, and what the pack would say

- **The best rule.** Under cross-fit by utterance halves, the best rule is margin plus r1 scenario, or margin plus
  agreement. Its out-of-half AUC is 0.67-0.80. At a 10 % call rate its precision (including cost rows) is 0.14-0.22
  against b ≈ 0.06-0.08; the best point is 0.29. Restricted to model-visible signals, it is 0.69-0.80.
- **Following the evidence is net-wrong.** On the 102-115 rows per pool where the exemplar/agreement favourite among
  the note's candidates is not the kept r1, the favourite is gold on 10-13 rows and r1 is gold on 73-85. Following the
  evidence would net **−61 to −72 rows**. The Solver already overrules these votes correctly about seven times out of
  eight.

### 1.4 Conversion anchors (the binding term)

| anchor | conversion on positives | harm on negatives |
| --- | ---: | ---: |
| same-flight Solver twin (resample) | 0.008 | 0.0006 |
| cross-flight replicate (AGREE vs wave A/A) | 0.085 | 0.016 |
| Reviewer-routed second Solver contact (REV-TFRL-1: 10 / 54 INT-SHORTLIST repairs, 8 / 164 CORRECT breaks) | 0.185 | 0.049 |

The floors are 7.02 rows for the 0.65 pp same-flight intent floor and 27 rows for the 2.5 pp cross-flight bar, both
at n = 1,080.

| measure | rows (pp) |
| --- | --- |
| perfect decision × 0.085 | 5.25-6.95 (0.49-0.64): under the floor in every pool |
| perfect decision × 0.185 | 11.48-15.19 (1.06-1.41): over the same-flight floor, under the cross-flight bar |
| best offline rule at 0.185 / 0.049 | −0.19 to +1.32 (≤ 0.12 pp) |
| precision needed for 7.02 rows at 0.185 / 0.049 | recall 0.7: 0.44-0.68; recall 1.0: 0.33-0.40; recall 0.5: 0.78-0.83 on Fold B, unreachable on Fold A |

**What the evidence says.**

- **The decision is readable, but only by a signal the Solver already holds.** The strong signal is the exemplar vote
  margin, which is in the Solver's request. Its direction is also the wrong advice on disagreement rows.
- **Offline rules do not reach the needed precision** (at most 0.29 against 0.44-0.68).
- **The only measured decision-maker with that precision is the Solver itself** (0.47-0.74 on its spontaneous
  switches). It uses it at low recall.
- **Conversion is unmeasured on these rows.** The only anchor that clears the floor even under a perfect decision is
  a borrowed 10 / 54.

## 2. Mechanisms consistent with directive 206

Every mechanism below keeps the model as the decider. The system offers a capability or a contract field; it never
triggers a second look by rule. The gate form is the E5 addendum's, applied to intent.

**The pre-declared gate (all mechanisms; fixed now, before any flight).** b is the ceiling rate of the read roster's
own sealed comparator (for example 0.075 on P-SV-1 A), frozen before the flight.

1. **Call rate:** calls (or low-confidence declarations) per offered row within [max(0.01, 0.5 b), min(0.50, 4 b)].
   On Fold B that is about [0.038, 0.30]. Below the band the offer is inert; above it the model is calling by reflex.
2. **Decision precision against this oracle:** calls on oracle-positive rows over all calls ≥ max(b + 0.10, 2 b, 0.33),
   with a paired-cluster bootstrap CI95 lower bound (cluster `sample_id`, 10,000 draws, seed 20260807) above b.
   - 0.33 is the sufficiency line derived in 1.4: below it, even full recall at the best measured conversion cannot
     reach 7.02 rows. It is set from measured numbers, never above the published ceiling.
   - Recall against the oracle is reported beside precision and not gated.
3. **Conversion and no harm:**
   - The intent delta carried by the called rows, over the whole 1,080-row roster, must be ≥ +0.65 pp (same-flight
     floor, decision 190) with CI95 lower bound > 0.
   - The column's official SLU-F1 must show no measured loss (CI95 upper bound not below 0). SLU may differ only on
     called rows.
   - Conversion and harm on called rows are reported separately. They are never pooled into a single "effect".

**Read design (all mechanisms).** Each mechanism changes the Solver's request bytes (a contract field or a tool
schema), so none can be a shadow.

- **A same-flight Solver column exists today only as a SUPPLY variant.** The W-SV instrument,
  `phase-native-candidates-review-revise-variants3first-v1`, varies supply knobs at the first Solver visit. It has no
  answer-contract knob and no in-column second contact. Module section 3.3's columns reach Perception branches and
  post-delivery shadows.
- **A cross-flight read is infeasible by construction.** Its bar is 27 rows. Even a perfect decision at the best
  anchor gives 11.5-15.2 rows.
- **Every mechanism below therefore reads ONLY as a same-flight Solver column.** That requires an instrument
  extension (open question 2).
- **Without that extension, no mechanism here is readable, and none should be flown.**

### M-A. `request_second_opinion` tool at the Solver

- **Who decides.** The model. One tool, one closed argument (`candidate_pair: [r1, r2]` restricted to the note's
  first three ids), rendered only in the Solver's request at the intent step.
- **What it returns.** A compact pack for the two intents: agreement votes, exemplar counts among the 20 delivered, and
  one contrast pair from the pinned contrast-pair table v2. Empty is legal (decision 199) when the pair has no
  contrast entry.
- **Receipt.** `tool_decision: {offered, called, args_hash, result_hash, used_in_answer}` per row. `used_in_answer` is
  computed after delivery: the delivered intent differs from the pre-call draft intent. The pack is receipted
  `saea-intent-second-opinion-v1` (pair ids, vote counts, contrast-pair value id, sha256 of the rendered pack, never
  pack text).
- **Read.** A same-flight Solver column (the offered Solver beside the unoffered A and the twin T), under the gate
  above.
- **Predicted effect at measured signals.**
  - Two of the pack's three contents (votes, agreement) are the signal the Solver already holds, and they point to
    the wrong candidate 73-85 times out of 85-98 disagreements. Following them nets −61 to −72 rows.
  - The third (a contrast pair) is the content that harmed at Perception: P-SV-1 level-1 top-1 −1.67 pp.
  - If the model's call precision equals the best offline rule's (≤ 0.29), the prediction at the 0.185 / 0.049 anchor
    is **≤ +1.3 rows (≤ 0.12 pp)**.
- **Risk.**
  - EFF-1: a constant tool schema made the Solver answer with a tool-call-shaped string on 145 of 1,092 contacts, SLU
    −4.39 [−6.69, −2.17].
  - A per-node, one-function schema lowers that risk but does not remove it.
  - The pack can move a right r1 to a wrong r2 on exactly the rows where the evidence disagrees.

### M-B. Confidence declaration in the Solver's answer contract

- **Who decides.** The model, by declaring `decision: {chosen, runner_up, confident: bool}` in its answer.
- **The deterministic USE rule.** When `confident` is false, the Solver is re-asked ONCE with the top-2 pack. The
  trigger is the model's own declaration, not a system score.
- **Staging.** Stage 1 is declaration-only: no re-ask, instrument only. Stage 2 adds the re-ask.
- **Receipt.** `solver_decision: {declared, confident, chosen, runner_up, chosen_rank_on_note, runner_up_rank_on_note,
  reasked, reask_changed_intent}` plus the re-ask contact id and request sha256. The declaration fields are parsed
  gold-free. A missing or malformed declaration counts as `declared: false` and never triggers a re-ask.
- **Read.**
  - Stage 1 is a same-flight Solver column carrying the extended contract. It is read for parts 1 and 2 of the gate
    only (call rate = share of `confident: false`; precision against the oracle), plus the SLU guard, because a
    contract change can move entities (the COMP-1 citation contract added 102 false positives on 414 zero-gold rows).
  - Stage 2 (the re-ask) is registered only if stage 1 clears parts 1 and 2. It is read for part 3.
- **Predicted effect at measured signals.**
  - Stage 1 predicts no intent change beyond the contract's form cost.
  - For stage 2, the only measured model-side precision is the Solver's spontaneous switching: 0.47-0.74. At the
    0.185 / 0.049 anchor, a declaration at precision 0.47-0.74 and recall 0.7 clears the 7.02-row floor in every pool
    where the needed precision (0.44-0.68) falls inside that range.
  - At the best offline-rule precision it does not (≤ +1.3 rows).
  - This is a conditional prediction on two measured numbers, not a claim that the declaration will reach either.
- **Risk.**
  - Contract form cost on SLU (the citation contract's history).
  - The declaration may be uncalibrated (always `true`: inert; always `false`: reflex). Part 1's band catches both.
  - The re-ask pack must not carry the vote margin as advice, because of the evidence-follow table. Section 3 fixes its
    content.

### M-C. A `verify_span`-style tool for intents

**Not viable, and this note says so.** A slot value has an external witness: the audio, and a pinned transcript's
span. The E5 oracle is defined per entity because "the transcript contains the gold span" is checkable. An intent has
no such witness.

- The gold intent is a latent label over a closed set of 60. No artefact the system could consult contains it.
- Any "verifier" is one of three things:
  - a second classifier, which is a second answering model and barred;
  - retrieval over labelled exemplars, which is already delivered and, per 1.3, net-wrong when it disagrees;
  - transcript text, which enters intent-bearing words that hurt intent (DEV-1000 −0.90 [−1.68, −0.09]) and which
    the E5 boundary bars from the intent decision.
- The only honest intent "check" is a re-decision by the core itself, which is M-B or M-D.
- **Recommendation: close M-C.**

### M-D. The Reviewer as the decision node, reached only on declared low confidence

- **Who decides.** The model twice. The Solver declares low confidence (M-B's field). The Reviewer, visited only on
  those rows, decides REVISE or ACCEPT. The Planner routes, and the Solver revises. This ties to decision 188's
  deferred B5 round.
- **Receipt.** M-B's `solver_decision` plus the existing Reviewer and Planner receipts, with the reach scope recorded
  as `reviewer_reach: {rule: "solver-declared-low-confidence", rows_reached}`.
- **Read.** A same-flight column is not possible today: the Reviewer loop is a multi-contact episode, and the W-SV
  columns cover only the first Solver visit. The fallback is cross-flight against the in-chain A/A at 27 rows, which
  1.4 shows is unreachable. **So M-D is readable only after M-B's stage 1 and an instrument extension to
  multi-contact columns.**
- **Predicted effect at measured signals.**
  - REV-TFRL-1 is this mechanism's own anchor: 0.185 conversion on revised shortlist visits, 0.049 harm on revised
    correct visits.
  - Its Reviewer showed reach without judgment: REVISE on 30.57 % of visits, intent repairs / breaks 14 / 15.
  - With reach limited to declared-low-confidence rows, the precision is the declaration's, and the Reviewer adds a
    second filter whose measured discrimination is nil.
  - The prediction is therefore at most M-B stage 2's, at 2-3 more contacts per reached row.
- **Risk.**
  - Reviewer nil-gain history: node ledger S1→R nets −1 / +1 rows; REV-TFRL-1 NOT ADMITTED; the review loop is NEUTRAL.
  - Added contacts.
  - Coupling to M-B: M-D inherits every M-B failure.

## 3. Ranking and the smallest next step

**Ranking.**

1. **M-B stage 1 (declaration-only instrument).** It is the only route whose decision-maker, the Solver, has a
   measured precision (0.47-0.74) in the range the floor needs. It costs no extra contact and no tool schema.
2. **M-D.** Worth reading only after M-B stage 1 clears, and only if the Reviewer beats the plain re-ask. Its own
   anchor shows no judgment.
3. **M-A.** A tool schema adds risk (EFF-1), and the pack's content is either redundant (votes the Solver holds) or
   net-wrong when it disagrees (−61 to −72 rows).
4. **M-C.** Not viable. An intent has no external witness.

**For M-B stage 2's re-ask pack,** 1.3 leaves one content candidate that is not already in the request: the contrast
pair. The vote margin may be SHOWN as the row's own exemplar counts. It must not be framed as a recommendation.

**Registered cell: not warranted now.** The best offline rule's flip count times the best measured conversion is
at most +1.32 rows, about 0.12 pp, against 7.02 rows. The decision is readable (AUC about 0.78). The binding term is
conversion on these rows, which no sealed flight has measured.

**Smallest next step: one offline instrument, model-free, on sealed bytes.** Apply this oracle's labels to the
Reviewer-routed revisions that already exist:

- the REV-TFRL-1 arm: 464 revised rows;
- its A/A: 34;
- the AGREE and wave A/A REVISE rows: 23 and 29.

It measures two things:

- **Conversion and harm on this oracle's own positives and negatives,** replacing the borrowed 10 / 54 and 8 / 164.
- **The REVISE decision's precision against this oracle.** This is a model decision-maker's precision at this blank,
  the one number no offline rule can supply.

It reuses `slurp_solver_decision_oracle.py`'s `classify` and cross-fit and needs no flight. Its outcome decides the
next move:

- **Conversion on positives ≥ 0.30 and REVISE precision ≥ 0.33:** open the instrument extension (open question 2) and
  register M-B stage 1 as a same-flight Solver column on Fold B.
- **Otherwise:** close the Solver-decision blank at the Solver node, and put the intent effort where the ledger puts
  the decision, which is Perception's ranking and shortlist.

## 4. Open questions for the coordinator

1. **No cell now.** Accept that the Solver-decision blank does not warrant a registered cell (at most 1.32 rows at the
   best measured conversion against 7.02), and authorise the offline re-decision instrument of section 3 as the next
   step?
2. **Instrument extension.** Should the same-flight supply-variant instrument gain a Solver CONTRACT knob (an
   answer-contract variant at the first Solver visit) and, later, an in-column second contact? Without it M-B and M-D
   are unreadable, because a cross-flight read needs 27 rows and a perfect decision gives at most 15.2.
3. **Sufficiency floor.** Add 0.33 (the derived sufficiency line) to part 2 of the 206 gate for intent offers, beside
   the E5 form max(b + 0.10, 2 b)?
4. **Close M-C.** Record that an intent is not tool-verifiable (no external witness), so that no intent "verify" tool
   is designed?
5. **Pack content.** Given the evidence-follow table (−61 to −72 rows), should any top-2 pack (M-A, or M-B stage 2)
   be restricted to the contrast pair plus the row's own exemplar counts shown as data, with no vote-based
   recommendation?

## 5. What this design does not decide

- No admission, registration, flight, flip, exposure row or test-sample contact.
- Not the instrument extension's engineering (open question 2).
- Not the Reviewer B5 round (decision 188); M-D only states its preconditions.
- Not any Perception-side intent lever. The block-depth read closed the pinned-key recall and depth levers. Where the
  intent effort goes if section 3's instrument fails is the coordinator's call.

## Coordinator rulings (Fable 5.1, 2026-09-30)

- **R1. The mechanism ranking is accepted.** M-B (confidence declared in the Solver's answer contract) goes first, as
  a declaration-only instrument. M-D (the Reviewer as the decision node) is read only after M-B stage 1. M-A (a
  `request_second_opinion` tool) carries the EFF-1 risk of a tool schema at the Solver. M-C (an intent `verify_span`
  tool) is not viable, because an intent has no external witness; no intent "verify" tool is designed.
- **R2. The smallest next step is the offline REV-TFRL-1 revision instrument of section 3,** dispatched on
  `fable/revisioninstr`. It is model-free and runs on sealed bytes. Thresholds:
  - conversion on this oracle's positives ≥ 0.30 **and** REVISE-decision precision ≥ 0.33: register M-B stage 1 on
    TRAIN Fold B, with a Solver answer-contract setting added to the same-flight supply-variant instrument (open
    question 2 answered yes, conditionally);
  - otherwise: close the Solver-decision blank at the Solver node.
- **R3. The evidence-follow finding is a structural fact.** On the 102-115 disagreeing rows per pool, following the
  exemplar/agreement votes would net −61 to −72 rows: the knowledge already delivered favours the wrong intent on
  those rows. More evidence of the SAME kind therefore cannot fix rank-2/3. Any further intent gain at the Solver
  needs a different evidence kind or the model's own confidence. Any top-2 pack (M-A, or M-B stage 2) carries no
  vote-based recommendation.
- **R4. No cell is registered from this design.** No admission, registration, flight, flip, exposure row or
  test-sample contact follows from it; the next move is decided by the R2 instrument's read.
- **R5 (2026-09-30, after the revision instrument).** The Solver-node blank is CLOSED under the current evidence kinds: across 16 sealed pools the Reviewer's REVISE route reaches 4–11 % of the oracle positives at precision 0.05–0.29 (pooled 0.122 [0.10, 0.15]; standard forms 0.153), converts 0.159 where it actually reaches them (REV-TFRL-1: 7/31 at rank 2, 0/13 at rank 3), and every confidence proxy (Solver switching elsewhere, REVISE route, low margin, low vote difference) scores at or below +0.1 pp per pool at the measured rates; only a perfect flag would clear the 0.65 floor (+0.84–1.36 pp). M-B stage 1 is NOT registered. Any further intent gain at the Solver needs a different evidence kind (owner decision 209 to be put after the A2 and milestone reads).
