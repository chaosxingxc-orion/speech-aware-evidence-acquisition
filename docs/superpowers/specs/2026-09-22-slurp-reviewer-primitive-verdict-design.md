# Reviewer verdict as a closed set of primitives (owner decision 84) -- design

Author: the coordinator (Fable 5.1). Date: 2026-09-22. Status: DESIGN for the engineering item E37; it
opens after the v2.0 lock record (cells PLAN / PLANr) and before the first Stage-3 pruning cell
(decision 85: Reviewer 3 -> 1 and review-off are read on a measurable Reviewer). Authority: owner
decision 84 of 2026-09-21 (`docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md`):
the Reviewer's verdict becomes a fixed vocabulary of verdict tokens that the parser matches
exactly, the free-text rationale stays beside them and is never parsed; NOT a JSON schema (decision
32's closure of cell B7r stands). Scouting basis: a read-only pass over the repository on 2026-09-22;
every pointer below was verified in that pass.

## 1. The defect this repairs

- The flown Reviewer instruction is one sentence of prose (`configs/probes/slurp_native_role_reviewer_v1.txt`,
  bound by `configs/baseline/slurp-native-default-plan-lock-baseline-v1.json` `phase_material.reviewer`,
  `response_format_id null`). Nothing on the flown path parses the Reviewer's text: `state["review"]` is
  rendered verbatim into the Planner's query (NCP is absent from the locked plan, so the
  `planner:review-finding` boundary is FALLBACK-RAW on 100 % of rows).
- The only closed-vocabulary match in the episode is the Planner's
  (`reproduction/ojw/native_episode.py` `_planner_action`, `output_format="exact-text"`: bare set
  membership against the legal action tokens, illegal -> `planner_action_illegal` disposition, row
  retained).
- The declared Reviewer parse (`rails/review_findings.py` `parse_review_findings`, the B7r JSON
  format `saea-review-findings-v1`) fails on 2,167 of 2,167 anchor outputs, so the verifier
  measurement (`scripts/analysis/slurp_verifier_measurement.py`) can rank Reviewer visits only by
  count; REVISE route precision 80-100 % at recall 0.5-5 % is a Planner-side number. The review loop
  costs 69 % of the anchor's GPU hours for +0.13 pp and cannot be tuned because its output is not
  measurable.

## 2. The primitive verdict

**Vocabulary `saea-review-primitives-v1`** (closed, case-sensitive, exact):

| token | meaning the Reviewer asserts about the current draft |
| --- | --- |
| `ACCEPT` | no supported issue |
| `REVISE-INTENT` | the scenario_action is wrong or missing |
| `REVISE-SLOT-MISSING` | a slot the speech supports is absent |
| `REVISE-SLOT-EXTRA` | a slot the speech does not support is present |
| `REVISE-SLOT-VALUE` | a slot type is right, its filler is wrong |
| `REVISE-FORMAT` | the draft does not follow the task contract's form |
| `UNSURE` | the Reviewer cannot decide from the speech |

**Output contract.** The Reviewer's response is: line 1 = exactly one token of the vocabulary;
every following line = free-text rationale (never parsed, never validated, never truncated by the
parser). The instruction text states the vocabulary once, in a fixed order, and asks for the token
on the first line. Nothing else in the Reviewer request changes (same context, same predecessor
binding, same iteration count).

**Parser `rails.review_primitives.parse_review_primitive(text)`**: first non-empty line, stripped,
matched against the vocabulary. Legal -> `(token, rationale)`. Anything else ->
`REVIEW_VERDICT_ILLEGAL` with the offending head retained (bounded, as
`PLANNER_ACTION_RECORD_CHARS` bounds the Planner's), the row RETAINED and the raw text rendered to the
Planner exactly as today (the B7a lesson: the harness never raises on a model's malformed output).
E22's `continue-without-answer` visit (the Reviewer exhausted its ReAct loop; its output is `""`)
records the disposition `react_exhaustion` and no token.

**The verdict is a recommendation, not a route.** The Planner keeps routing authority
(`tests/unit/test_review_findings.py::test_framework_carries_review_report_but_planner_keeps_routing_authority`
stays green). The Planner's query renders the token and the rationale as its review block; the
router still reads only the Planner's action. Decision 84 asks for a measurable verdict, not for the
Reviewer to route.

## 3. Where it lives

| piece | location | rule it satisfies |
| --- | --- | --- |
| config key | `native_episode.reviewer_verdict` = `{"vocabulary": "saea-review-primitives-v1"}`; OFF form = key absent or `null` | `rails/config_tables.py` `EPISODE_LEVEL_SWITCH_KEYS` (13th key) + `is_episode_null_arm` arm; `scripts/checks/harness_admission_check.py` rule 5 (`_check_episode_switch`); class `episode` (request bytes move, so never `run`) |
| instruction | `configs/probes/slurp_native_role_reviewer_primitives_v1.txt`, bound through `phase_material.reviewer.instruction_template` by the cell fragment | one authority per phase output contract (`rails/native_episode_config.py`) |
| parser + vocabulary | `rails/review_primitives.py` (new, small); vocabulary registered once, referenced by id | no new module under `rails/probes/`; no adapter change |
| receipt mark | `native_episode_receipt.reviewer_verdicts = [{"visit": n, "token": ..., "disposition": "legal" / "review_verdict_illegal" / "react_exhaustion", "head": ...}]` written by the Reviewer's `_ApplyRole` branch in `reproduction/ojw/native_episode.py` beside `planner_routes` | the verifier instrument reads receipts, never response text (`scan_episodes`) |
| NCP hook | `rails/node_context_policy.py` `PARSER_IDS["review-primitive"] = "rails.review_primitives.parse_review_primitive"` and a renderer section, so a later NCP arm can render the token structurally; the locked plan (NCP off) needs none of it | `SLURP_BOUNDARY_PARSE_FAILURE` FALLBACK-RAW stays |
| measurement | `scripts/analysis/slurp_verifier_measurement.py`: `scan_episodes` also collects `reviewer_verdicts`; new stage `primitives`: parse rate, per-token counts, precision P(draft wrong | token in REVISE-*), recall, the token x official-correctness confusion, agreement between Reviewer visits, and the Planner's route conditioned on the token | decision 74: measure the verifier first |
| admission entry | `docs/receipts/harness-admission.json`: switch class `episode`, key `native_episode.reviewer_verdict`, proof test named | `harness_admission_check.py` |

## 4. The cell (R-PRIM) and its decision rule

- One factor on the locked default plan (cell PLAN's fragment): `native_episode.reviewer_verdict`
  armed and the Reviewer instruction swapped. Roster TRAIN Fold A 1,080; comparator = the sealed
  PLAN arm at the plan's own null (PLANr's margins); paired whole-speaker bootstrap, seed 20260915;
  frontier row (decision 75); flown only through the scheduled-task queue (decision 77).
- Expected: SLU and intent NEUTRAL (the Planner routes the same way it does today); parse rate is
  the primary engineering number.
- Rule: parse rate >= 95 % AND NEUTRAL-or-better on the official numbers -> the primitive verdict
  becomes the base's Reviewer form (base lock v3 amendment) and the pruning cells of decision 85 read
  on it; parse rate < 95 % -> one instruction repair, one recovery registration; HARMFUL on SLU or
  intent -> keep the prose Reviewer, pruning cells read on visit counts only (as the prelude did).
- Cost: about 1.8 GPU hours (the plan's own cost).

## 5. Proofs before the flight (model-free)

1. Parser unit tests: every token; leading blank lines; trailing rationale kept byte-exact; near-miss
   tokens (`Accept`, `REVISE`, `REVISE-SLOT`) illegal; empty text -> illegal; E22 empty output ->
   `react_exhaustion`.
2. Config switch tests: the key resolves in the episode class; OFF form is the null arm; the
   locked plan's fragment is byte-unchanged; `test_default_plan_lock_cells` diff proof extended.
3. Wire proof through the real role graph with the fake transport (the E18 / E32 pattern): three
   Reviewer visits with legal, illegal and exhausted outputs; the receipt carries three marks; the
   Planner's request renders the raw review text unchanged; the delivered text is a model response.
4. The verifier script's `primitives` stage runs on a synthetic receipt set with known precision.
5. Gates: `harness_admission_check`, `engineering_base_check`, `finite_completion_policy_check`.

## 6. Not done here

No JSON schema, no findings list, no Reviewer-side routing, no change to the Planner token contract,
no NCP level change, no Reviewer count change (that is decision 85's cell). Nothing here authorises
a contact; R-PRIM is a registered cell with its own package, ledger rows and decision receipt.
