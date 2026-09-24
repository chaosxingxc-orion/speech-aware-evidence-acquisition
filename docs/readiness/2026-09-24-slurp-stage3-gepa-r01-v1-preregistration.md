# Preregistration: SAEA-SLURP-STAGE3-GEPA-R01-V1 (Stage-3 layer A, the GEPA arm)

Written **before** any contact of this cell. Status: **HELD**; no decision receipt exists, all four
cells are `held`, and the four exposure rows at the end of `docs/exposure-ledger.md` are DRAFT and
uncountersigned. Nothing in this document authorises a flight.

Design note: `docs/superpowers/specs/2026-09-24-slurp-stage3-gepa-arm-design.md`. Readiness package:
`docs/readiness/2026-09-24-slurp-stage3-gepa-r01-v1/`.

## 1. The question

Does a SCENARIO-level reflective proposer, shown a scenario's worst- and best-outcome trajectories
together with the node's current guidance, produce delta statements that a per-ROW advantage
proposer could not? The CELL-1 read is the reason to ask: NEUTRAL overall, with per-scenario effects
that are large and opposite.

This cell does not answer that question. It produces the artifact whose effect CELL-1-GEPA measures.

## 2. The population, fixed here

68 (scenario, node) groups over the 17 scenarios that carry at least one sealed ROLL-1 trajectory;
`music` is excluded because none of its 27 R01C rows disagreed within its rollout group. The flown
rows are the 68 CARRIER rows, committed as
`docs/receipts/rosters/slurp-stage3-gepa-r01c-carriers-v1.json`. The gold shown belongs to the 173
distinct GROUP rows, each an item of the committed R01C parent receipt.

## 3. What the contact sees, fixed here

1. The scenario and the node, named twice (system message and per-group instruction).
2. The node's current released delta statements for that scenario, numbered, `prior_score`-ordered,
   capped at 12; a group whose node carries none is told so in words.
3. The scenario's worst-outcome rows and its best-outcome rows -- DISJOINT halves of the ranked
   list, at most 6 each -- every row with its Perception candidate list, its best and worst Solver
   samples, its delivered answer with the Reviewer verdict labels and the Planner route, and its own
   construction gold.

## 4. The ranking, fixed here

Rows are ranked by their rollout GROUP MEAN official SLU-F1 under
`slurp-slu-official-projected-v3-train`, ascending, ties by `sample_id`. `disagreement` and the
delivered score are rejected and the reasons are recorded in the design note's section 2; the
delivered score in particular is unusable in this seal because it was scored under a different
scorer id.

## 5. The response contract, fixed here

`stage3-gepa-proposal-v1`: one to five blocks, each `NODE / DELTA-KIND / TARGET / STATEMENT`, every
block naming the group's own node. `rails.stage3_gepa.parse_gepa_proposal` is the parser of record;
it never raises, it retains every illegal block with its reason, and curation -- not the parser --
drops one.

## 6. The decision rule, fixed here (STRUCTURAL ONLY, no gate number)

1. PARSE RATE, with its denominator.
2. NODE DISCIPLINE: blocks naming a node other than the group's.
3. ILLEGAL-BLOCK COUNT by the parser's own reason strings.
4. BLOCKS PER CONTACT: the one-to-five distribution.
5. REVISION SHARE: accepted proposals absorbed into an existing store row against those entering as
   new rows.
6. A clean seal with row accounting in = out.

No threshold is preregistered on any of the six. A low parse rate, a degenerate node distribution or
a zero revision share is a FORM defect that stops the arm and is root-caused, never a result.

## 7. The selection operator, fixed here

Decision 83's per-scenario frontier rule, as already implemented in
`scripts/build_slurp_stage3_delta_retention.py`, applied to the CELL-1 read to decide which
INHERITED v1r rows survive into the GEPA store. New GEPA rows inherit their scenario's decision and
their own per-row outcome is read at CELL-1-GEPA. The rule is not re-tuned for this family; that is
the point of running three families against one selection operator. The retention document is
written to the GEPA line's own prepared directory and never touches the `stage3-deltas-v2`
artifacts.

## 8. Budgets, fixed here

68 contacts (cap = target), fit ceiling 204, speech-second ceiling 292 (positive by contract; the
arm is text-only so the realised value is expected to read 0), GPU-h ceiling 1.0 against a ~0.2
point estimate, zero tool calls, zero scoring jobs. Ceilings are bounds, never targets, and budgets
are run-cumulative across every attempt of a run id.

## 9. The leakage rule, fixed here

Construction gold only, on a committed construction-role roster of a discovery split, under owner
decision 82 and `contracts.gate_exposure._require_construction_role_for_visible_targets`. Every row
whose gold is rendered is an item of the committed R01C receipt; the groups builder refuses
otherwise. The client binds the union once and each request narrows it. The delta statements shown
are this study's own released rows, curated under the six-token transcript containment rule. No
receipt carries rendered text. Nothing of this contact reaches an evaluated row.

## 10. Failure policy, fixed here

Stop on the first failure and preserve every contact; no retry. A failed smoke stops the arm. This
registration pre-authorises no recovery; a root-diagnosed recovery re-registration is a separate
act, and at most one is allowed per flight. A partial manifest is never read.

## 11. What this cell may never claim

An effectiveness result, a comparison against the Training-Free GRPO arm, a DEV or test number, or
anything paper-grade. The effect is read at CELL-1-GEPA on TRAIN Fold A -- a development number
(owner decisions 28 / 86) -- and the order of reads is TRAIN lock -> DEV confirmation -> the single
test read (owner decisions 99 and 107).

## 12. The re-pin obligation this registration creates

The commit moves `core/flight/runtime.py`, which is hashed into every prepared phase-supply
artifact's identity. Every such artifact prepared before this commit is stale and must be re-pinned
in the flip cycle, `--allow-output-change` never passed, outputs expected byte-identical.

## 13. The mint command the coordinator runs

```
python scripts/flights/batch/mint_decision_receipt.py \
  --decision-id slurp-stage3-gepa-r01-admission-v1 \
  --out coordination/slurp-stage3-delta-cell-gepa-r01-v1/root-admission-v1.json
```

then `bash scripts/flights/batch/gepa_flip_both.sh`, and only then
`bash scripts/flights/batch/batch_chain_gepa.sh`.
