# Node Context Policy (NCP): design

Author: Fable 5.1, root coordinator. Date: 2026-09-17. Status: DESIGN DRAFT — no owner GO, no
execution contract, no model contact. Program:
`docs/superpowers/specs/2026-09-16-slurp-v2-base-program-design.md`. Evidence base:
`docs/results/2026-09-17-slurp-node-context-audit-v1.md` (machine tables
`analysis/SAEA-SLURP-NODE-CONTEXT-AUDIT-V1/result.json`, SHA-256
`c46aabeaff53e19fe76b4ca0131765dafaff1e29f296950314ae7006dcdaae48`).

## 1. The directive and what it asks for

Owner, 2026-09-17, translated from the Chinese original (quoted verbatim in the audit, section 0):
*every agent node's input context must follow one unified handling policy; never hand a model's raw
output to the next node unprocessed; per-node templates, and where necessary one extra model call to
clean the context, to raise the model's performance across tasks.*

Three requirements, in the owner's own order: **one policy**, **no raw hand-off**, **templates, and
optionally one cleaning call**. This spec proposes one policy object that covers all three and can be
switched off to byte-identical current behaviour.

The audit established the starting point. In the sealed anchor there is exactly one node-boundary
admission test — `bool(output.strip())` — and one rendering template —
`[agent state {state_id} kind={state_kind}] {content}` — applied to the upstream model's own bytes.
Seven Solver drafts that do not parse as the task answer were passed verbatim to the Reviewer and the
Planner and accepted by all seven Planners; 2,167 of 2,167 Reviewer outputs fail the repository's own
registered findings parser; the Planner spends 25.0 % of the run's prompt budget to emit a median of
two tokens, 1,079 of 1,085 of them the literal `ACCEPT`.

## 2. Scope and non-goals

**In scope:** what an upstream *model output* looks like when it enters a downstream node's request,
for the SLURP native four-role episode, plus the shape that makes the same object reusable by the
Earnings and Audio2Tool adapters (section 12).

**Explicitly not in scope**, and not to be bundled into any cell this spec proposes:

- the knowledge/evidence blocks, which are unchanged at every level — they remain the supply path's
  business (the audit's finding (b): the same ~32,010 characters of evidence are re-sent on four to
  five contacts per row, which dwarfs the 2.17 % of wire text that is upstream model text);
- the duplicated task-contract tool message (audit finding (a): 13.6 M characters, ~7.4 % of the
  run's prompt budget, a literal substring of the system prompt each receiving node already holds) —
  that is a tool/contract-view change with its own bounded preparation decision already recorded in
  `docs/results/2026-09-16-slurp-review-context-provenance.md`;
- the speech packet, which every contact carries and which no level touches;
- any change to which roles run (that is `native_episode.review_loop`, module M0, already decided);
- any paper-scale or production-scale work.

## 3. The policy object

One **NodeContextPolicy** per **boundary**, where a boundary is the pair

```
(consumer_role_kind, semantic_class)
```

and `semantic_class` names the kind of upstream material, not the producer's contact. This is the
axis `rails/role_context.py` already uses (`candidate-hypothesis`, `current-draft`,
`review-finding`), extended with `plan-action` and `tool-observation`. It is the right axis because
the same producer output means different things to different consumers: the Solver's draft is *the
thing to check* for the Reviewer and *the thing being decided about* for the Planner, and the audit
shows the existing compiler already renders those two differently.

The boundaries of the SLURP native episode are:

| id | boundary | producer | today's form |
| --- | --- | --- | --- |
| `B-CAND-SOL` | (solver, candidate-hypothesis) | Perception | raw text part |
| `B-CAND-REV` | (reviewer, candidate-hypothesis) | Perception | raw text part |
| `B-DRAFT-REV` | (reviewer, current-draft) | Solver | raw text part |
| `B-DRAFT-PLAN` | (planner, current-draft) | Solver | raw text part |
| `B-DRAFT-SOL` | (solver, current-draft) | Solver, previous visit | raw text part |
| `B-REVIEW-PLAN` | (planner, review-finding) | Reviewer | raw text part |
| `B-REVIEW-SOL` | (solver, review-finding) | Reviewer | raw text part |
| `B-PLAN-SOL` | (solver, plan-action) | Planner | raw text part (6 chars) |
| `B-TOOL-*` | (any, tool-observation) | Reviewer's tool | assistant + `tool` replay |

Each boundary carries exactly one of three levels.

### L0 — `raw`: pass-through, byte-identical to the sealed anchor

No parse, no template, no derived state. The consumer receives
`[agent state {state_id} kind={state_kind}] {content}` with `content` the producer's
`completion.text`. This is today's behaviour and is the OFF arm of the switch. **L0 must be provably
byte-identical**, not merely "intended to be": see the falsifier in section 9.

### L1 — `structured`: parsed, normalised, rendered through a fixed per-node template

Deterministic, zero model contacts. For a boundary at L1:

1. **Parse.** A registered, carrier-local parser reads the producer's sealed content. SLURP today:
   `project_bounded_slurp_intent_hypotheses` for `candidate-hypothesis`, `parse_slu_response` for
   `current-draft`, `parse_review_findings` for `review-finding`, exact-text action match for
   `plan-action`.
2. **Normalise.** Only operations that add no information: field selection, ordering fixed by the
   producer's own order, whitespace collapse, and joins across two already-parsed upstream outputs
   (e.g. "is the draft's intent one of the Perception candidates?"). No gold, no external source, no
   retrieval, no judgment, no truncation of a field's value.
3. **Render** through a fixed, versioned, hash-pinned template (section 4). The rendered text becomes
   the derived state's `content`; the derived state keeps the producer's `source_response_sha256` and
   `source_query_state_sha256`, exactly as `_derived_state` already does, so the model bytes are
   never obscured.
4. **On a parse failure, apply the boundary's declared rule**, one of:
   - `FALLBACK-RAW` — render the template's header and the source content verbatim in a clearly
     labelled `UNPARSED` block. **This is the default and the only rule this spec proposes to fly.**
   - `FALLBACK-OMIT` — replace the block with a one-line reason and drop the content. This is what
     `rails/role_context.py::_review_view` does today (`{"reason": "malformed-review-findings"}`),
     and on the anchor's prose Reviewer it would fire on **100 % of rows**, deleting the review from
     the Planner's context. B0 already measured deleting the review loop and found it HARMFUL; a
     policy that silently reproduces that is a defect, not a policy. `FALLBACK-OMIT` stays
     implementable and is not admitted for any SLURP boundary without its own cell.
   - `FALLBACK-REFUSE` — fail the row. Reserved for boundaries where a malformed upstream makes the
     episode meaningless; today only `plan-action`. (E8c, section 6: the harness no longer refuses
     a Planner output that names no registered action — it seals that row — and the boundary is
     reached only on a `REVISE`, so this level is now effectively unreachable on SLURP.)

`knowledge and evidence blocks are unchanged` at L1, by construction: the policy only replaces
`agent_state` entries, never `supplied_evidence`, never the speech part, never the system message.

### L2 — `cleaned`: L1 plus one context-cleaning model contact at declared boundaries

L1 first. Then, at each boundary whose entry declares `cleaning`, one additional contact to the same
frozen core in the same resident session and geometry:

- its request is composed by the same `role_input` / `speech_binding` path as every other contact, so
  it is metered, budget-gated, exposure-bound, traced and costed identically — there is no separate
  accounting path, exactly as `GroupedSolverRoleNode` established for grouped sampling;
- its phase declares `knowledge: "none"` (no evidence blocks) and its own `response_format_id`;
- its instruction is a fixed, committed template file, carrying only the L1-rendered material and the
  cleaning contract — never the task, never the answer schema, never a request for a new judgment;
- its output is validated against a closed JSON schema. **On any validation failure the boundary
  falls back to its L1 rendering** and the receipt records `validation: "rejected"` with the reason.
  There is no retry: one attempt, one fallback (the program's one-shot attempt semantics).
- it is refused past `config.max_contacts`, like every other contact.

A cleaning contact may not introduce content: its schema constrains it to selecting, labelling and
compressing what L1 handed it. The test that enforces this is in section 9.

## 4. Per-node templates

All templates are committed files under `configs/probes/`, hash-pinned in the receipt, rendered with
`sort_keys=True`-equivalent determinism (fixed field order, no dict iteration, no float formatting).
Concrete drafts follow; field values shown as `{…}` come only from the parsed upstream output.

**`ncp_slurp_candidate_hypothesis_v1.txt`** — consumers: Solver, Reviewer (`B-CAND-SOL`,
`B-CAND-REV`).

```
PERCEPTION CANDIDATES ({n} of at most {max}, in the order Perception produced them)
  1. {intent_id} - {distinction}
  2. {intent_id} - {distinction}
  3. {intent_id} - {distinction}
These are hypotheses to choose between, not evidence that anything was said.
```

**`ncp_slurp_current_draft_reviewer_v1.txt`** — consumer: Reviewer (`B-DRAFT-REV`).

```
DRAFT UNDER REVIEW (Solver, {parsed|UNPARSED})
  scenario: {scenario}
  action:   {action}
  intent:   {scenario}_{action}  [{among the Perception candidates | NOT among the Perception candidates}]
  entities: {type}={filler}
            {type}={filler}
            (none declared)
UNPARSED DRAFT, VERBATIM:
{source content}
```

The bracketed candidate-membership flag is a deterministic join of two already-parsed upstream
outputs. It is the single derived fact this design adds, and it exists because
`docs/results/2026-09-16-slurp-review-context-provenance.md` recorded a revision whose replacement
intent left the candidate set although the Solver prompt forbids it, with nothing in the loop able to
see that. See open question 2.

**`ncp_slurp_current_draft_solver_v1.txt`** — consumer: revising Solver (`B-DRAFT-SOL`).

```
YOUR PREVIOUS ANSWER (revision {i} of {max})
  scenario: {scenario}   action: {action}
  entities: {type}={filler}; ...
  status:   {parsed|UNPARSED}
```

**`ncp_slurp_review_finding_v1.txt`** — consumers: Planner, revising Solver (`B-REVIEW-PLAN`,
`B-REVIEW-SOL`).

```
REVIEW OF THE CURRENT DRAFT (Reviewer, {parsed|UNPARSED})
  verdict: {draft_is_supported|draft_has_issues}
  issues:
    - {field}: {problem}
    - {field}: {problem}
  cited evidence: {evidence_id} [{available|not available in this context}]
UNPARSED REVIEW, VERBATIM:
{source content}
```

On today's SLURP Reviewer this renders the header plus the verbatim block for every row
(`FALLBACK-RAW`), which is exactly the honest description of what the Planner is being given. It is
also the boundary where L2 has the clearest job.

**`ncp_slurp_plan_action_v1.txt`** — consumer: revising Solver (`B-PLAN-SOL`).

```
PLANNER DECISION: {action}
Revisions remaining: {n}. Actions still available to the Planner: {list}.
```

**`ncp_slurp_planner_brief_v1.txt`** — consumer: Planner, the composed brief that concatenates
`B-DRAFT-PLAN` and `B-REVIEW-PLAN` under one header.

```
DECISION BRIEF (revision {i} of {max}; you may answer {available actions})
{draft block}
{review block}
HARNESS CHECKS (deterministic, computed from the material above; not a judgment)
  - draft parses as the task answer schema: {yes|NO}
  - selected intent is one of the Perception candidates: {yes|NO|n/a}
  - every entity type is in the legal inventory: {yes|NO (list)}
```

The `HARNESS CHECKS` block is the direct answer to the audit's sharpest finding: seven malformed
drafts, seven `ACCEPT`s, nothing in the loop able to notice. It is deterministic, derived only from
material the Planner already receives, and contains no gold. It is nonetheless the one place where
the harness tells the model what to attend to, so it is open question 2 rather than a settled
decision.

**`ncp_slurp_cleaning_review_v1.txt`** (L2, boundary `B-REVIEW-PLAN`) — the cleaning instruction:

```
Below is one reviewer's free-text commentary on a draft answer, and the draft it commented on.
Restate the commentary as structured issues. Do not add an issue the commentary does not state,
do not judge the draft yourself, do not propose a replacement answer, and do not mention the
speech. Return only:
{"verdict":"draft_is_supported|draft_has_issues",
 "issues":[{"field":"scenario|action|entity_type|entity_filler|none","problem":"<at most 20 English words>"}]}
```

with the closed schema

```json
{"type":"object","additionalProperties":false,"required":["verdict","issues"],
 "properties":{
  "verdict":{"enum":["draft_is_supported","draft_has_issues"]},
  "issues":{"type":"array","maxItems":5,
    "items":{"type":"object","additionalProperties":false,"required":["field","problem"],
      "properties":{"field":{"enum":["scenario","action","entity_type","entity_filler","none"]},
                    "problem":{"type":"string","maxLength":140}}}}}}
```

## 5. Config surface: one switch key

One key, in the `episode` admission class, on the closed allowlist
`rails.config_tables.EPISODE_LEVEL_SWITCH_KEYS` (today `native_episode.roles.solver` and
`native_episode.review_loop`; this is the proposed third, and admitting it is a code change with a
test, never a receipt edit):

```
native_episode.context_policy
```

Its value is either the string level that applies to every boundary, or an object whose `level` is
that default and whose `boundaries` overrides named boundaries:

```json
"native_episode": {
  "context_policy": {
    "level": "structured",
    "policy_id": "typed-slurp-node-context-v1",
    "boundaries": {
      "solver:candidate-hypothesis": {"level": "structured", "template": "probes/ncp_slurp_candidate_hypothesis_v1.txt", "on_parse_failure": "raw"},
      "reviewer:candidate-hypothesis": {"level": "structured", "template": "probes/ncp_slurp_candidate_hypothesis_v1.txt", "on_parse_failure": "raw"},
      "reviewer:current-draft":  {"level": "structured", "template": "probes/ncp_slurp_current_draft_reviewer_v1.txt", "on_parse_failure": "raw"},
      "planner:current-draft":   {"level": "structured", "template": "probes/ncp_slurp_planner_brief_v1.txt", "on_parse_failure": "raw"},
      "planner:review-finding":  {"level": "cleaned", "template": "probes/ncp_slurp_review_finding_v1.txt", "on_parse_failure": "raw",
                                  "cleaning": {"phase_id": "context_clean_review", "instruction_template": "probes/ncp_slurp_cleaning_review_v1.txt",
                                               "response_format_id": "ncp-review-issues-v1", "on_invalid": "fallback-l1"}},
      "solver:current-draft":    {"level": "structured", "template": "probes/ncp_slurp_current_draft_solver_v1.txt", "on_parse_failure": "raw"},
      "solver:review-finding":   {"level": "structured", "template": "probes/ncp_slurp_review_finding_v1.txt", "on_parse_failure": "raw"},
      "solver:plan-action":      {"level": "structured", "template": "probes/ncp_slurp_plan_action_v1.txt", "on_parse_failure": "refuse"}
    }
  }
}
```

**Values and null arm.** `"raw"` (or the key's absence) is the OFF arm: `is_episode_null_arm` returns
`True` for `None` and for the literal `"raw"`, and for an object whose `level` is `"raw"` with no
`boundaries` entry above `raw`. That makes OFF compose to the same `config_hash` as the key being
absent, which is what the harness-admission gate requires of an OFF arm.

**One key, not two.** The existing optional block `native_episode.role_context` (validated by
`rails/role_context_binding.validate_role_context_config`) becomes the `structured` level's
implementation, not a second switch: `load_native_episode_config` refuses a fragment that carries
both, and a fragment carrying only `role_context` keeps working unchanged for backward reading of
the 2026-09-16 aborted flight's configs. Open question 3 asks the owner to confirm this folding.

**Interaction already validated and kept:** `role_context` refuses to combine with a
`history_scope` filter (`rails/native_episode_config.py:500`). `context_policy` inherits that
refusal — a boundary policy and a history filter are two ways to answer the same question, and
composing them silently would make neither auditable.

## 6. E2c: the first instance of L1

Merged item E2b (`reproduction/ojw/native_group_solver.py`) already performs, on the delivery side,
exactly what L1 specifies: it parses every one of the N Solver samples with `parse_slu_response`,
records each as `parse_status: "ok" | "malformed"`, commits over the parsed answers only through a
registered policy, and **re-renders the committed answer through a fixed canonical template**
(`_default_render_answer`). Parse → declared malformed rule → fixed template → zero extra contacts.

Its gap, identified by this audit: the committed text becomes the delivered and scored answer, but
each raw sample is still sealed individually by `rails/runner.py::capture_completion`, so a
downstream Reviewer at `B-DRAFT-REV` would receive all N raw drafts and never the committed one — the
reviewed draft and the delivered draft would differ.

**E2c is therefore the `solver:current-draft` boundary at level `structured` with N > 1**: the state
the consumer sees is the committed render, the N raw samples stay in `solver_group` custody and in
the trace, and the receipt binds the rendered text to every sample's `response_text_sha256`. Under
this design E2c is not a special case; it is one boundary entry, and it is the first one because its
parser, its template and its malformed rule are already written, tested and merged.

**E8a as built (2026-09-17, branch `fable/e8a`), and how it reconciles with E2c.** E2c and the NCP
stay two seams, and they compose without a special case, because they answer different questions.
E2c is PRODUCER-side: `rails/runner.py::settle` seals ONE `phase:<solver>` state per grouped visit
through `seal_phase_response_state`'s `state_content` / `raw_response_text` seam, holding the commit
policy's aggregated answer re-rendered by `_default_render_answer`. The NCP is CONSUMER-side: what
each downstream node reads at the `current-draft` boundary. Because the committed state has exactly
the wire form a samples-1 Solver state has — canonical
`{"scenario","action","entities"}` JSON — L1 parses it under the same closed draft contract and
renders it through the same template, with `parse_status: "parsed"` and no fallback. The proof is
`tests/unit/test_node_context_policy.py::
test_the_committed_grouped_solver_draft_parses_under_l1_by_construction`. Folding the two into one
object would have made the commit policy a consumer-side concern and the N raw samples visible to a
boundary that must never see them; they stay separate.

Four things E8a builds differently from the drafts above, each deliberate:

1. **The policy is a per-state TRANSFORM, never a re-selection.** It keeps every state of the
   already-selected history, in order, and replaces only the content of the ones whose
   `(consumer_role_kind, semantic_class)` is a declared, non-`raw` boundary. That is what makes L0's
   byte identity true by construction rather than by inspection, and it is why the NCP composes with
   `history_scope`'s own selection instead of competing with it.
2. **The Planner's brief is two adjacent blocks, not one merged block.** Merging `B-DRAFT-PLAN` and
   `B-REVIEW-PLAN` would drop a state, which rule 1 forbids. `probes/ncp_slurp_planner_brief_v1.txt`
   therefore carries the `DECISION BRIEF` header, the draft fields and the `HARNESS CHECKS` block on
   the draft state, and `probes/ncp_slurp_review_finding_v1.txt` renders the review on the review
   state immediately after it. The Planner reads the same three things in the same order.
3. **The tool-observation boundary is confined to REPLAYS.** A Reviewer's own live tool chain is
   replayed inside its framework contract and verified byte-for-byte against the sealed observation
   (`core/model/native_framework_history.py`), so the policy leaves it verbatim and records
   `raw_reason: "live-tool-chain"`. A later role's replay of that same observation is rewritten:
   `result.task_contract` is replaced by a reference line, and only when the contract is provably a
   substring of that request's own system message. On the anchor's shape that reaches the Planner's
   1,080 contacts and the revising Solver's, roughly half of the 2,184 deliveries the audit counted.
4. **`"raw"` is a declared arm that still emits receipts.** The key's ABSENCE is the arm that
   composes to the pre-key config hash and is what a cell's OFF arm uses. A DECLARED all-raw policy
   renders identical request bytes and still emits one `level: "raw"` row per boundary per contact,
   which is what turns section 9's byte-identity claim into a checked statement.

**E8b as built (2026-09-17, branch `fable/e8b`): L2.** A boundary declared
`{"level": "cleaned", "cleaning": {...}}` renders L1 first, then makes ONE additional contact, then
renders the accepted result or falls back to that L1 rendering. Seven things it fixes that this
section left open, each deliberate:

1. **The cleaning contact runs inside the CONSUMER contact's own worker.** `run_contact` holds one
   trajectory lock and one pinned slot per sample, so a nested `run_contact` would deadlock. The
   invoker therefore runs from inside `speech_binding`, on the consumer's already-held slot, before
   that consumer's own request is dispatched. That is what makes "the same resident session and
   geometry" true rather than intended. It composes through a SECOND
   `MeteredNativeSpeechRequest` instance — the same class, the same `prepare`, the same
   `FrozenCoreClient` — whose completion sink settles nothing, because a cleaning contact must never
   reach `capture_completion` and seal a phase state.
2. **It is a declared contact, not a program phase.** `load_native_episode_config` requires the four
   role phases to cover the program exactly once, so a fifth phase would be a much larger change
   than this design asks for. `cleaning.phase_id` is therefore the contact's own identity and
   namespace, refused when it collides with a program phase name; `knowledge: "none"` is enforced by
   the runner (every knowledge/evidence part of the consumer's user turn is dropped, the system
   contract and the speech packet stay, the agent-state history is empty); and
   `cleaning.response_format_id` is resolved from `core.base.RESPONSE_FORMATS` alone, so the
   registered builder must render with no lock and no root — checked when the config is validated.
3. **At most ONE cleaning contact per consumer contact per boundary.** The Planner at revision 2
   holds BOTH Reviewer outputs; cleaning each would spend three contacts where section 7 budgets
   two. The policy cleans the LAST state of the boundary in that contact's exposed history — the
   review the Planner is deciding about — and renders the earlier ones at L1 with
   `validation: "skipped"`. The ceiling therefore gains
   `(max_revisions + 1) × consumer_role.max_iterations` per cleaned boundary, which for
   `planner:review-finding` on a one-iteration Planner is exactly the `(max_revisions + 1)` of
   section 7: the anchor's 11 becomes 13.
4. **Two committed templates, not one.** `probes/ncp_slurp_cleaning_review_v1.txt` is the
   INSTRUCTION the cleaner reads (the contract of section 4 plus the L1 material, and nothing else);
   `probes/ncp_slurp_cleaned_review_v1.txt` is how an ACCEPTED output is rendered into the
   consumer's context. Both are ordinary node-context templates, so both are validated at load time
   and hash-pinned in every receipt, beside the boundary's L1 template. The instruction drops
   section 4's inline JSON example: the declared `response_format_id` IS that contract, and the
   template grammar refuses an unrecognised brace.
5. **The closed schema is section 4's, verbatim.** The two rules it cannot state live in
   `validate_cleaning_document`: a `problem` may not be blank, and the response may not introduce
   content — every content token of an accepted output is either one of the schema's own fixed words
   or occurs, case-folded, in the L1 material that contact was handed. Case is not content; anything
   else is.
6. **`cleaned` is declared per boundary, never as a default.** A default level applies to all twelve
   boundaries and no carrier registers cleaning assets for all twelve, so `"level": "cleaned"` at the
   top level and a bare `"cleaned"` string are both refused; so is a `cleaning` block on a boundary
   that is not `cleaned`, a `cleaned` boundary with no `cleaning` block, and a `cleaned` boundary
   whose semantic class has no registered cleaning renderer (today only `review-finding` has one).
7. **The cleaning contact is in the trace and in the ceiling, not in the wave ledger.** It carries
   its own trace buffer, its own ordinary `native-role-contact` USE record, its own
   `AgentContactPlan` (checked against the knowledge-payload rule), the episode's evidence pins and
   the run's budget id, and it increments `scheduled_contacts`. It is NOT appended to the episode's
   `contacts`/`waves` ledger, whose invariant is one wave per QueryState transition: a cleaning
   contact registers no agent state and routes no episode step. The receipt row's `cleaning_contact`
   block is what binds it — contact id, request id, request/response digests, the three committed
   hashes, the schema hash, `validation` and `rejected_reason`.

One consequence worth stating for the cell: the episode appends its own bounded limits to every
instruction, including `remaining_model_contacts`. A cleaning contact therefore shifts that number
for every later contact of the same row, and raising the ceiling from 11 to 13 shifts it for every
contact. B7b's requests are not byte-identical to B7a's outside the cleaned boundary, and the
wire-check receipt must say so. Holding the ceiling fixed isolates the boundary's own effect, which
is what `tests/unit/test_node_context_policy_l2_runner.py::
test_l2_changes_only_the_declared_boundarys_consumer` measures.

Proofs: `tests/unit/test_node_context_policy_l2.py` (model-free: the committed assets, the five
invalid-answer cases, the containment rule, the one-contact-per-consumer-contact bound, the ceiling
11 → 13) and `tests/unit/test_node_context_policy_l2_runner.py` (production render path: the cleaned
block on the Planner's actual request, the extra metered contact and its trace binding, refusal past
the ceiling, the evidence-free cleaning request, and L0/L1 byte identity against E8a's pins).

E8c (2026-09-17, cell B7a abort): **a malformed Planner output is a retained row, never a flight
failure.** B7a's 1,080-row L1 arm generated 3,278 contacts and then died at row 618 because ONE of
its 665 Planner responses was the six-letter token `REJECT` and one was an 80-character sentence;
the other 663 were exactly `ACCEPT` or `REVISE`. The sealed anchor's 1,085 Planner responses had
never produced one, so the harness had no designed behaviour for it and
`reproduction/ojw/native_episode.py::_planner_action` raised, taking the campaign with it. That is a
harness defect, not a finding about the policy under test: the program's rule is that malformed rows
are RETAINED and reported. `_planner_action` now returns the reserved routing value
`PLANNER_ACTION_ILLEGAL` instead of raising -- for a token outside the configured action set, and
under `json-action-v1` for any output the strict single-key parse refuses -- and the graph maps that
value to the SAME explicit-accept component an `ACCEPT` takes. The row delivers its committed draft
unchanged, contacts no further role, spends no revision, and records the truth in two places: its
`planner_routes` entry gains `"legal": false`, `"disposition": "planner_action_illegal"`,
`"action_sha256"` over the whole token and `"action_chars"`, with `"action"` cut to the first 32
characters (the Planner may quote the draft, which the route record is not a place for), and the
receipt gains a `planner_action_illegal` mark carrying the count and that sha256. Under `exact-text`
the sealed sha256 IS that Planner visit's own `response_text_sha256`, so the mark is bound to the
actual contact. A route the episode really took as `ACCEPT` or `REVISE` keeps exactly its three
pre-E8c keys, and the anchor's pins in `tests/unit/test_node_context_policy_runner.py`
(`ANCHOR_REQUEST_SHA256`, `ANCHOR_TRANSITION_SHA256`, `ANCHOR_FRAGMENT_SHA256`) and
`tests/unit/test_native_episode_runner_grouped_solver.py` are unmoved.

The `solver:plan-action` boundary and its `FALLBACK-REFUSE` are untouched by this, and the reason is
structural: that boundary renders the Planner's plan into a RE-ENTERED Solver, which happens only
after a `REVISE`. An illegal Planner output terminates its row at the Planner, so the Solver is
never re-entered and the boundary is never reached. What E8c does change is the sentence in section
3 that says the harness "already refuses" a malformed plan: it no longer does -- the row is sealed
before any boundary rendering, so `FALLBACK-REFUSE` now guards only a plan that IS a registered
action yet defeats `parse_plan_action`, which under `exact-text` (where a registered action is
exactly `ACCEPT` or `REVISE`) cannot occur.

Proofs: `tests/unit/test_ojw_native_episode.py` (the episode graph: the disposition, the 32-character
truncation on the 80-character shape, an earlier legal route's byte identity beside an illegal one,
the `json-action-v1` cases, the reserved routing value) and
`tests/unit/test_flight_native_episode_dispatch.py::
test_an_illegal_planner_token_seals_its_row_and_the_campaign_continues` (a real two-row dispatch:
the campaign runs both rows and its contact accounting, the bundle verifier accepts the sealed row,
and the registered SLURP official scorer scores it exactly like the accepted row beside it).


## 7. Contact-ceiling arithmetic for L2

`rails/native_episode_config.py:530` fixes the ceiling and asserts it equals `program.max_contacts`:

```
ceiling = perception.max_iterations
        + (max_revisions + 1) * sum(role.max_iterations * (samples if solver else 1) for the other roles)
        + max_refreshes * perception.max_iterations
```

A cleaning contact is one iteration of one extra role inside the revision loop, so each declared
cleaning boundary adds `(max_revisions + 1)` to the ceiling. On the anchor's shape
(`perception 1, solver 1, reviewer 3, planner 1, max_revisions 1`, ceiling 11, measured 5.0157
contacts/row):

| L2 boundaries declared | per-revision sum | ceiling | contacts/row (worst) | vs anchor contacts | est. GPU-h/cell |
| --- | ---: | ---: | ---: | ---: | --- |
| none (L0/L1) | 5 | 11 | 5 | — | ~3.4 |
| `planner:review-finding` | 6 | **13** | 6 | **+20.0 %** | ~4.0–4.3 |
| `+ reviewer:current-draft` | 7 | 15 | 7 | +40 % | ~4.6–5.2 |
| all four model boundaries | 9 | 19 | 9 | +80 % | ~6 |

**This spec proposes exactly one cleaning boundary — `planner:review-finding` — for cell B7b.** It is
the only boundary where L1 provably cannot structure anything today (0/2,167 Reviewer outputs parse),
and it feeds the node that consumes 25.0 % of the run's prompt budget to emit two tokens.

Prompt-token cost of that one cleaner: its phase declares `knowledge: "none"`, so its request is the
system contract (8,118 chars) plus the speech packet plus the L1-rendered material plus its own
instruction — by comparison with the Perception contact (3,593 median tokens, of which ~1,500 are its
6,022 characters of evidence) this estimates at ~2,400–2,700 prompt tokens. At 1,080 rows that is
~+2.8 M prompt tokens on a 46.0 M baseline, **+6.1 %**, against +20.0 % contacts; contact setup, not
prompt volume, is what the extra wall-clock buys.

## 8. Prompt-fit consequences

Measured headroom: `serving_slot_tokens` is 24,576 and the largest prompt anywhere in the anchor is
14,868 tokens (planner#1) — 60.5 % occupancy, 9,708 tokens of headroom at the worst observed contact.

L1 changes only the model-text slice, whose medians today are 686 (solver#0), 924 (reviewer#0), 1,058
(reviewer#1), 1,544 (planner#0) characters. The templates are more verbose than the raw JSON they
replace — labels, the membership flag, the harness-checks block — and `FALLBACK-RAW` keeps the source
content in the block, so the worst case is *additive*: a bounded +400 to +600 characters, roughly
+110 to +170 tokens, on prompts of 9,000–14,900 tokens. That is inside the measured headroom by two
orders of magnitude, and a `--dry-run` prompt-fit receipt is still required per cell by the program's
section 5.

L2 at `planner:review-finding` *reduces* the consumer's slice (a bounded ≤5-issue brief replaces the
verbatim findings, whose p95 is 439 and max 1,759 characters) and adds one small request of its own.

## 9. Receipts

Per boundary, per contact, extending `saea-role-context-compilation-v1` rather than replacing it:

```json
{"schema": "saea-node-context-policy-v1",
 "policy_id": "typed-slurp-node-context-v1",
 "boundary": {"consumer_role_kind": "planner", "semantic_class": "review-finding"},
 "level": "cleaned",
 "source": {"state_id": "...", "state_kind": "phase:reviewer", "artifact_sha256": "...",
            "content_sha256": "...", "source_response_sha256": "...",
            "source_query_state_sha256": "...", "producer_policy_id": "...", "source_position": 4},
 "parse_status": "malformed",
 "parser_id": "rails.review_findings.parse_review_findings",
 "fallback_applied": "raw",
 "template_id": "probes/ncp_slurp_review_finding_v1.txt",
 "template_sha256": "...",
 "rendered_state_id": "node-context:planner:review-finding:<sample>:<sha>",
 "rendered_sha256": "...", "rendered_chars": 612,
 "derived_fields": {"verdict": "draft_has_issues", "issue_count": 2,
                    "citation_availability": [{"evidence_id": "...", "available": true}]},
 "cleaning_contact": {"agent_contact_id": "...", "request_id": "...", "request_sha256": "...",
                      "response_sha256": "...", "response_text_sha256": "...",
                      "response_format_id": "ncp-review-issues-v1", "schema_sha256": "...",
                      "validation": "accepted", "rejected_reason": null},
 "receipt_sha256": "..."}
```

Every boundary emits a row on every contact, including `level: "raw"` rows, whose `rendered_sha256`
must equal the source's `content_sha256` — that is what makes L0's claim of byte identity a checked
statement rather than a comment. The rows land in the episode's compact receipt under
`node_context_policy_compilations`, beside the existing `role_context_compilations`, and the run's
aggregate (per boundary: contacts, parsed, fallback counts, cleaning contacts, rejections, median
rendered chars) lands in the cell's check receipt.

## 10. Test plan

**L0 byte identity (zero contacts, the module's `request-bytes-identical` falsifier).** Compose the
anchor fragment plus `context_policy: "raw"`; assert its `config_hash` equals the sealed anchor's.
Then replay the sealed anchor's own history: for a sample of the 5,417 sealed contacts, rebuild the
request payload through `speech_binding` / `MeteredNativeSpeechRequest.prepare` from the sealed
states and assert the payload SHA-256 equals the trace's `payload_sha256` for that contact. This is
the same falsifier shape the harness-admission gate already requires of a `run`-class module and the
same evidence form the dispatcher admission used; it proves OFF is a twin of the pre-key baseline
without spending a contact.

**L1 determinism and coverage (zero contacts).** Over all 1,080 sealed Perception outputs, 1,085
Solver outputs, 2,167 Reviewer outputs and 1,085 Planner outputs: (a) every one renders; (b) rendering
is byte-stable across 1,000 repetitions and across a fresh process; (c) the malformed rule fires on
exactly the known sets — 0 Perception, 7 Solver, 2,167 Reviewer, 0 Planner; (d) the rendered block's
`UNPARSED` section, when present, contains the source content unchanged.

**L1 adds no information (zero contacts).** For every rendered block, every token of every
`{…}`-substituted value is drawn from the source content, the legal inventory already in the system
contract, or the template's own literal text. A property test over the 1,080 rows; a failure means
the policy invented something.

**L1 twin.** A token-matched control that renders the same template with the *fields of another row's
parsed output* of the same shape (a within-scenario derangement, gold-free by construction) isolates
"structure" from "this row's content", exactly as M1's derangement twin does. It flies only if B7a
shows a positive CI95 against the anchor, per the program's twin rule.

**L2 schema validation and fallback (zero contacts for the unit half).** A cleaning response that is
valid JSON but schema-invalid, one that is not JSON, one that is empty, and one that exceeds
`maxItems` each produce the L1 rendering and a receipt with `validation: "rejected"` and the reason;
a valid one produces the cleaned rendering. A metering test asserts the cleaning contact increments
`scheduled_contacts`, carries its own `agent_contact_id`, appears in the trace as an ordinary
contact, and is refused past `max_contacts`. A 4-row dry run against the resident session proves the
form before any cell.

**Gates.** `engineering_base_check.py`, `harness_admission_check.py` (with the new episode key on the
allowlist and its proof test `tests/unit/test_config_table_module_switches.py::
test_node_context_policy_is_one_episode_class_key`), `results_ledger_check.py`,
`tool_catalog_check.py`, `derived_media_confinement_check.py`, `experiment_handoff_check.py`.

## 11. Admission cells

Both on TRAIN A 1,080 (`docs/receipts/rosters/slurp-evo-fold-a-v2.json`), the resident
`q4km-mmproj-free-slurp-native-bounded-perception-proof-np4-ctx24k-max512-v1` geometry (attach, never
spawn), primary scorer `slurp-slu-official-train` run once per complete manifest through
`core.scoring_batch`, projection v3 applied to every official number and reported beside the
symmetric-normalised one, paired whole-speaker bootstrap 10,000 draws seed 20260915, CI95 for
advancement and CI90 for diagnostics, natural-mixture and equal-scenario tables, comparators as
sealed bytes and never re-flown. **The measured own null of this roster and geometry — pooled SLU
half-width 1.1218 pp, intent 1.0051 pp — is the margin in every rule below**; the imported DEV1000
margins are not used.

| cell | module | base / comparator | control | contacts/row | ceiling | GPU-h |
| --- | --- | --- | --- | ---: | ---: | --- |
| B7a | NCP L1 (`structured` on all eight boundaries, `on_parse_failure: raw`) | sealed anchor `SAEA-SLURP-NATIVE-DUAL-STORE-TRAIN-FOLD-A-ANCHOR-RECOVERY-V1` | the anchor; L1 derangement twin only if B7a shows a positive CI95 | 5 | 11 | ~3.4 |
| B7b | NCP L2, cleaning declared at `planner:review-finding` only | B7a's sealed bytes | B7a | 6 | 13 | ~4.0–4.3 |

**B7a decision rule** (fixed here, copied verbatim into the preregistration): ADMITTED iff the
primary official SLU CI95 lower bound is > 0 against the anchor, intent is non-inferior at the own
null margin 1.0051 pp, the symmetric-normalised scorer agrees in sign, and no scenario loses intent
beyond the null band. NEUTRAL iff both primary metrics are non-inferior within the own null margins
(SLU 1.1218, intent 1.0051); a NEUTRAL L1 still enters the SLURP default plan, because it removes a
named defect class at no measured cost — the seven malformed drafts that reached the Planner
unflagged and the 2,167 unstructured reviews now carry a declared, receipted disposition. HARMFUL
otherwise, and then L2 is not flown.

**B7b decision rule:** ADMITTED iff primary SLU CI95 lower bound > 0 against **B7a** and intent
non-inferior at 1.0051 pp, with the same scenario-harm and normalised-sign conditions; NEUTRAL if
non-inferior within the null margins, in which case it does **not** enter the default plan, because
it costs +20 % contacts for no measured gain; HARMFUL otherwise. B7b flies only if B7a is ADMITTED or
NEUTRAL.

**Sequencing.** Both cells sit after B4a/B4c and before B5, so that an admitted policy is part of the
"v2 candidate" set B5 measures rather than a change layered onto a locked base — subject to open
question 5. One experiment in flight; a wire-check receipt showing the request differs from the base
only in this channel, a 4-row smoke, and a prompt-fit receipt precede each cell, as section 5 of the
base program requires.

## 12. The same object on Earnings and Audio2Tool

The policy object is carrier-independent. Its key is `(consumer_role_kind, semantic_class)`; only the
per-class *parser* and *template* are carrier-local, and they register through the existing
`core.base.ROLE_CONTEXT_COMPILERS` registry the same way `build_slurp_role_context_compiler` does.
Nothing new appears under `rails/probes/`, no `TaskAdapter` or controller is subclassed, and the base
remains `rails.controllers.EvidenceAgentController` + `core.flight.FlightRuntime` (owner 2026-09-03:
one base, thin derivations).

| carrier | consumer roles | semantic classes | parser today | template |
| --- | --- | --- | --- | --- |
| SLURP | perception/solver/reviewer/planner | candidate-hypothesis, current-draft, review-finding, plan-action | `slurp_intent_hypotheses`, `slurp_scoring`, `review_findings` | `ncp_slurp_*` |
| Earnings 21/22 | the `e21_native_window_*` role set | window-observation, current-transcript, review-finding, plan-action | the window/repair readers behind `e21-substitution-alignment-flag-v1` | `ncp_e21_*` (to be drafted with its cell) |
| Audio2Tool | the `a2t_native_role_*` set | tool-candidates, current-call, review-finding, plan-action | `rails/a2t_response_schema.py`, `a2t_hard_validity` | `ncp_a2t_*` (to be drafted with its cell) |

One config key, one receipt schema, one set of L0/L1/L2 semantics, one admission class for all three.
Each carrier admits its own entries through its own cells; no carrier inherits another's verdict, and
this spec proposes cells for SLURP only.

## 13. Open questions for the owner

1. **The Reviewer's output contract.** L1 at `planner:review-finding` can only pass through raw
   today: 0 of 2,167 anchor Reviewer outputs parse under the repository's registered findings parser,
   because the Reviewer prompt asks for prose and its phase declares no response format. Keep
   `FALLBACK-RAW` and let L2 (cell B7b) carry that boundary, as this spec proposes — or give the
   Reviewer a `response_format_id`, which is a second factor and would need its own cell before B7a?
2. **The `HARNESS CHECKS` block.** May the Planner's L1 brief carry the deterministic check list
   (draft parses / selected intent is among the Perception candidates / entity types are legal)? It
   is computed only from material the Planner already receives and contains no gold, but it changes
   the Planner's job from reading prose to checking a list, and it is the one place the harness tells
   the model what to attend to. Include it in B7a, split it into its own cell, or omit it?
3. **The third episode switch key.** `EPISODE_LEVEL_SWITCH_KEYS` is a deliberately closed allowlist
   of two. Confirm `native_episode.context_policy` as the third, and confirm that the existing
   optional `native_episode.role_context` block is folded under it (refused when both are present)
   rather than kept as a parallel path.
4. **The L2 budget and the cleaning contact's speech packet.** Confirm one cleaning boundary for B7b
   (+20 % contacts, ceiling 13, ~+0.7 GPU-h) rather than two or four. And confirm that the cleaning
   contact may carry the speech packet, which this harness attaches to every contact — suppressing it
   would require a text-only arm and a second serving geometry, which this spec does not propose.
5. **Order against B5.** Do B7a/B7b run before the B5 "v2 candidate" set, so an admitted policy is
   part of what B5 measures, or after the lock as a Stage-3 optimisation? The "one experiment in
   flight" rule makes this an ordering decision, not a parallel one.

## 14. What this spec does not authorise

No model contact, no cell, no config commit, no allowlist edit. B7a and B7b need the owner's GO, their
own exposure rows registered before the first contact, their own `contracts.ExecutionPlan`
(`bounded-discovery-probe`, discovery role), their own preregistrations carrying the decision rules of
section 11 verbatim, and their wire-check, smoke and prompt-fit receipts. No paper-scale claim, no
Fold B or test read, no reuse of any aborted attempt.

## 15. Coordinator resolutions (Fable 5.1, 2026-09-17, after E8a)

Recorded so the cells are registered against one reading; the owner may override any of them before
the cell in question registers.

1. **Cell B7a is the eight model-output boundaries at `structured`** (section 3), tool-observation
   boundaries declared `raw`, no Reviewer producer format. It measures the consumer-side policy alone.
2. **The Reviewer response format is its own one-factor cell, B7r** (`saea-review-findings-v1`
   bound on the Reviewer phase on top of B7a's sealed bytes), because it changes what the Reviewer
   generates, not only what its consumers read.
3. **The tool-observation rewrite is its own one-factor cell, B7c** (the replayed task-contract
   observation rendered by reference instead of the 5,424-character echo), on top of B7a's bytes.
4. **B7b (L2) stays as section 11 defines it**, one cleaning boundary at `planner:review-finding`,
   on top of B7a's sealed bytes; E8b implements the mechanism.
5. Order in the GPU queue: after B4a (and B4c if B4a admits), B7a -> B7r -> B7c -> B7b -> B5. Each
   later cell flies only if its predecessor is not HARMFUL; a NEUTRAL B7a still enters the default
   plan (section 11); NEUTRAL B7r/B7c/B7b do not unless they lower cost.
6. The E8a doubts are answered as follows: the registered Reviewer format is the parser's own
   contract (`parse_review_findings`), not the L2 cleaning schema; `uniqueItems` dropped from the
   decoding schema is acceptable and the rejection rate is read at B7r's smoke;
   `scripts/checks/derived_media_confinement_check.py` rewriting its own receipt is a defect filed for
   repair outside any flight window and the gate is not run while a campaign flies.


## 16. Analyses as node context (owner directive 26)

Owner directive 26 of 2026-09-18 extends this document's own premise. Sections 1-15 ask what a node
may READ: one declared handling policy per `(consumer_role_kind, semantic_class)` boundary, so no
node is ever handed another node's raw output. Directive 26 asks the same question of the
program's own OFFLINE ANALYSES: an analysis this program trusts enough to quote in a verdict is
knowledge the system should be ACTING on, not a paragraph in a report. Where an analysis has
produced a rule, that rule belongs in a node -- on the read side as declared context, or on the
write side as a deterministic transform of what a node produces -- and the number the owner reads
then measures the system that contains it.

Family **B8** collects the cells that place an existing analysis into a node. Each is one factor on
the shared harness, each keeps its own comparator, and none of them is admitted by this section:

| Cell | Analysis placed | Where it lands | Engineering |
| --- | --- | --- | --- |
| B8a | A1's USE projection v3 (`R_action` + legal-label v2, filler normalisation P2) | a delivery-time node, applied once to the accepted answer before delivery | E11, 2026-09-18 -- built, tested, `held` |
| B8b | the A3 coverage-confusion and slot-loss audits | a Reviewer-side slot-audit context block: what the audit says about THIS row's delivered slot types, rendered as typed content at the reviewer boundary | E12, 2026-09-19 -- built, tested, `held` |
| B8c | the A3 per-scenario confusion pairs | Solver-side scenario hints: the neighbours a scenario is actually confused with, as typed content at the solver boundary | E14, 2026-09-19 -- built, tested, NOT registered |

B8a is the write-side instance and is the one this program has built: it is a transform of what the
episode DELIVERS, so it owes custody rather than context handling (`core.bundle.outputs` invariant
I7n; program spec section 3, item E11). B8b and B8c are read-side instances and are ordinary
boundaries of this document's own policy object -- they render typed content into a node's exposed
context and are governed by sections 3, 4 and 9 exactly as any other boundary is.

**The boundary that makes this legal.** Every B8 node is authored from CONSTRUCTION data only --
the TRAIN pool minus every utterance with a recording in TRAIN A, TRAIN B or DEV-1000 (the
2026-09-13 exclusion), plus closed lists such as the 60-id legal intent inventory that the task
contract already renders into the prompt. No B8 node may be authored from, keyed on, or
conditioned by the gold of a row it is evaluated on, and no B8 node may read a future turn or a
reference transcript. An analysis that only exists because it was fitted to the evaluated rows'
gold is a diagnostic ceiling and stays a diagnostic ceiling: A1's own `R_action` was identified
against gold after the fact, which is exactly why E4 preregistered it as a RULE to be confirmed
prospectively rather than tuned, and why the node applies it to every row unconditionally rather
than where it helps. The same test applies to B8b and B8c before either is built.

### 16.1 B8b as built (E12, 2026-09-19, branch `fable/e12`)

**The boundary.** `reviewer:current-draft` (`B-DRAFT-REV`), and no other. The slot-audit block is
an ADDITION to that boundary's own L1 rendering, appended after the draft block with one newline
between them; the draft block itself is produced by the same code and the same template as on the
base, byte for byte. That is what keeps rule 1 of section 15's E8a notes intact -- the policy is a
per-state transform, it adds no state, drops none and reorders none -- and it is why the block
requires that boundary at level `structured`: it has nothing to attach to at `raw` and would be
replaced at `cleaned`, and both are refused by name before contact.

**The analysis, and where it may come from.** A released construction view,
`knowledge/slurp/semantic/slot-audit-v1/` (`release.json` + `snapshot.json`, built by
`scripts/build_slurp_slot_audit_view.py`, registered under
`rails.slot_audit.SLOT_AUDIT_VIEW_ID`). Per intent: every entity type attested with it in the
construction pool and the share of that intent's construction rows carrying it, the share of its
rows carrying no entity at all, and the `date` / `time` representation conventions quoted verbatim
from the released slot store v2 cards. 60 intents, 54 entity types, 9,354 construction utterances
-- the governed TRAIN split minus every utterance with a recording in TRAIN Fold A, Fold B or
DEV-1000, exactly the pool `scripts/build_slurp_exemplar_pool_assets.py` pins for module M1, proved
disjoint by the builder's own `refuse_evaluated_rows` and bound to that pool's identity hash. The
table carries COUNTS and SHARES only: no filler, no sentence, no utterance id, no recording, and no
gold of any evaluated row. It is a committed repository artifact rather than a
`SPEECHRL_DATA_DIR` store for exactly that reason -- its pin is a git blob hash an auditor can
check offline.

**The flags**, all four computed by the harness and none by a model
(`rails.slot_audit.slot_audit_flags`, rendered through
`configs/probes/ncp_slurp_slot_audit_reviewer_v1.txt`):

| Flag | Fires when | Reads |
| --- | --- | --- |
| `TYPE-UNSEEN` | a draft entity type is not attested with this intent anywhere in the construction pool | the draft's types, the table |
| `EMPTY-DRAFT` | the draft declares no entity while at least `empty_draft_min_entity_row_share` (default 0.5) of this intent's construction rows carry one | the draft, the table |
| `MISSING-COMMON` | a type above `missing_common_min_row_share` (default 0.5) of this intent's construction rows is absent from the draft; `date` and `time` are named like any other type | the draft's types, the table |
| `REPRESENTATION` | a `date` or `time` filler breaks the released spoken-form convention `saea-spoken-form-v1` -- no ASCII digit, no colon, no slash | the draft's fillers, the table's conventions |

A fifth number, `profile_min_row_share` (default 0.05), bounds how many types the profile LISTS; it
gates no flag. The draft's fillers are read only by the `REPRESENTATION` predicate and never reach
a rendered line: a flag names a TYPE and its counts. An intent the table does not carry renders the
"no construction rows" line and is still `REPRESENTATION`-checked, because a convention is a
property of the type, not of the intent.

**Zero contacts, and the receipt that says so.** The block makes no model, tokenizer, encoder,
scorer, tool, server or network contact, so the bounded ceiling of section 7 is unmoved (11 stays
11) and cell B8b carries cell B7r's budgets unchanged. The boundary's own
`saea-node-context-policy-v1` row gains a `slot_audit` block (`saea-reviewer-slot-audit-v1`)
carrying the view id, the release and snapshot sha256s, the table's content hash, the template id
and hash, the thresholds, `applied` / `reason`, the intent and whether the table carries it, the
rendered block's sha256 and character count, the count of each of the four flags and the flag list
itself. A malformed draft renders no block and records `applied: false`, `reason:
"draft-unparsed"`. The compilation record's `template_sha256s` gains the three assets the block was
composed from. Every row of every other boundary keeps exactly its pre-E12 fields and digest.

**The switch.** One `episode`-class key, `native_episode.reviewer_audit`
(`rails.config_tables.EPISODE_LEVEL_SWITCH_KEYS`, the fifth), OFF = the key's absence, ON = the
armed object, proof `tests/unit/test_config_table_module_switches.py::
test_reviewer_audit_is_one_episode_class_key`. It is a SECOND key beside
`native_episode.context_policy` rather than a field inside it because a cell that moves the audit
must stay distinguishable from a cell that moves the policy.

**Prompt fit.** 687-787 characters on the released table, roughly 170-200 tokens, against the 9,708
tokens of headroom section 8 measured at the worst observed contact. The largest single line is a
`REPRESENTATION` detail, which quotes the slot store v2 `time` card's admissible-format sentence
verbatim, attested construction forms included -- verbatim because this program quotes a released
card rather than paraphrasing it.

**Proofs.** `tests/unit/test_slurp_slot_audit_view.py` (the builder's refusals, the released
table's shape and pins, the "no filler, no sentence, no utterance id" content audit, the
spoken-form predicate, each flag firing and staying silent, and the committed view reproducing from
the construction pool); `tests/unit/test_reviewer_slot_audit_block.py` (the block is an addition and
the L1 draft block is byte-identical, no other boundary moves, byte-stable rendering, the receipt,
the "adds no information" property test, and the config refusals);
`tests/unit/test_native_episode_runner_reviewer_audit.py` (the production render path: exactly the
three Reviewer contacts move, the receipt and the asset pins reach the sealed episode receipt, and
the OFF arm is the key's absence down to the byte); `tests/unit/test_b8b_reviewer_audit_config.py`
(the two committed fragments are one factor on B7r, the composed configuration loads with the block
armed, and the loader refuses the wrong carrier and a non-L1 boundary).

**What it does not authorise.** No owner decision, no preregistration, no exposure row and no
contact. Cell B8b's fragments are `held`; it flies only after cell B7r seals and is not HARMFUL,
behind its own four-row smoke.
### 16.2 B8c as built (E14, 2026-09-19, branch `fable/e14`)

**The boundary.** `solver:candidate-hypothesis` (`B-CAND-SOL`), and no other. The scenario-hints
block is an ADDITION to that boundary's own L1 rendering, appended after the candidate list with
one newline between them; the candidate list itself is produced by the same code and the same
template as on the base, byte for byte. The Reviewer's own `candidate-hypothesis` boundary is
deliberately NOT included: the hints are for the node that CHOOSES between the candidates, and
keeping them out of the Reviewer is what makes "Perception, Reviewer and Planner requests are
byte-identical with the key on and off" a checkable statement rather than an intention. For the
same reason section 16.1 gives, the block requires its boundary at level `structured`: it has
nothing to attach to at `raw` and would be replaced at `cleaned`, and both are refused by name
before contact.

**The analysis, and where it may come from.** A released construction view,
`$SPEECHRL_DATA_DIR/knowledge/slurp/semantic/scenario-hints-v1/` (`release.json` +
`snapshot.json` + `completion.json`, built by `scripts/build_slurp_scenario_hints_view.py`,
registered under `rails.scenario_hints.SCENARIO_HINTS_VIEW_ID`). A3's own confusion pairs are
NOT read: they were computed on the evaluated rows' gold, so they are a diagnostic ceiling and
they stay one. The table re-derives its neighbours from the construction pool alone -- the
governed TRAIN split minus every utterance with a recording in TRAIN Fold A, Fold B or DEV-1000,
the 2026-09-13 exclusion, 9,354 utterances, exactly the pool `scripts/build_slurp_slot_audit_view.py`
and `scripts/build_slurp_exemplar_pool_assets.py` pin, proved disjoint by the builder's own
`refuse_evaluated_rows` and, additionally, checked identical to the identity hash the E12
slot-audit receipt records for the same exclusion.

**The derivation rule**, fixed in `rails.scenario_hints`, mirrored into the snapshot and refused
by the loader when a snapshot declares another:

| Step | Rule |
| --- | --- |
| neighbours | for each construction utterance of intent `i`, its `k = 10` nearest pool neighbours by cosine over the sealed content facet vectors (`vectors/slurp-kus3/facet-vectors.jsonl`, sha256 `5dfe7523…`, tool row `SAEA-SLURP-MF7B-NEMOTRON-EMBEDDING-V1`), leave-one-out; `leaked(i, j)` counts the neighbours carrying `j != i`, out of `rows(i) * k` |
| neighbour floor | the top 3 `j` whose leakage share is at least 5 %, most leaked first, ties by intent id |
| cues | per kept `(i, j)` pair, the content words with the highest `+1`-prior log-odds of DOCUMENT frequency in `i` against `j`, stopwords removed (a closed English function-word list committed in the module), minimum 3 documents in `i`, top 3 kept, ties by word |

The vectors are READ, never recomputed: the pass that produced them is already paid for, and the
builder hashes the file against the pin every committed exemplar fragment carries. Cosine is
normalisation-invariant, so the build takes a local unit-norm copy and alters no released number.
Every row's neighbour order is a FULL stable sort of its own similarity vector, so ties break by
ascending pool index and the table does not depend on the chunk size the similarities were
measured in.

**What the released table carries.** 60 intents; 44 of them carry at least one neighbour (16 carry
none, 18 one, 15 two, 11 three); 81 `(intent, neighbour)` pairs; 231 cue rows over 130 distinct
cue words. Construction counts, construction leakage rates and construction WORDS -- no utterance
id, no sentence, no recording, no entity filler and no gold of any evaluated row. Unlike the E12
slot-audit table, which carries counts and shares only and is therefore committed, this one carries
construction text, which in this program lives under the controlled data root; its pin is a
declared sha256 checked on every binding, and `docs/receipts/knowledge/slurp-scenario-hints-v1.json`
carries the same hashes into the repository.

**Zero contacts, and the receipt that says so.** The block makes no model, tokenizer, encoder,
scorer, tool, server or network contact, so the bounded ceiling of section 7 is unmoved. The
boundary's own `saea-node-context-policy-v1` row gains a `solver_hints` block
(`saea-solver-scenario-hints-v1`) carrying the view id, the release and snapshot sha256s, the
table's content hash, the template id and hash, the bounds, `applied` / `reason`, the candidate ids
the block was handed, the candidates it covered, the rendered block's sha256 and character count,
the three counts (candidates, neighbours, cues) and the hints themselves. An unparsed Perception
output renders no block and records `applied: false`, `reason: "candidates-unparsed"`. The
compilation record's `template_sha256s` gains the three assets the block was composed from. Every
row of every other boundary keeps exactly its pre-E14 fields and digest.

**The switch.** One `episode`-class key, `native_episode.solver_hints`
(`rails.config_tables.EPISODE_LEVEL_SWITCH_KEYS`, the seventh), OFF = the key's absence, ON = the
view id, the two pins and the two optional render bounds `max_neighbours` / `max_cues`, which may
only NARROW the released table. It is a SECOND key beside `native_episode.reviewer_audit` for the
reason section 16.1 gives for that one: a cell that moves the Solver's hints must stay
distinguishable from a cell that moves the Reviewer's audit. The armed key also requires the
controlled data root, carried into the episode binding as the new optional
`NativeEpisodeRunBinding.data_root`; every binding that arms no hints leaves it `None` and is
byte-identical to its pre-E14 self.

**Prompt fit.** The block is bounded at 3 candidates x 3 neighbours x 3 cues. Measured on the
released table through the production render path: 578 characters when the three candidates carry
no neighbour at all, 788 at the median candidate, 1,608 in the widest case the table admits --
roughly 145, 197 and 402 tokens at the 4-characters-per-token convention section 16.1 used, against
the 9,708 tokens of headroom section 8 measured at the worst observed contact.

**Proofs.** `tests/unit/test_slurp_scenario_hints_view.py` (the builder's three falsifiers, the
agreement with the E12 pool receipt, the leave-one-out and chunk-independence of the leakage
measurement, the document-scoped cue frequencies, the log-odds formula, the loader's refusals over
synthetic tables, and the released table's own content audit);
`tests/unit/test_solver_scenario_hints_block.py` (the block is an addition and the L1 candidate
list is byte-identical, no other boundary and no other role moves, byte-stable rendering, the
bounds, the receipt, the "adds no information" property test, and the config refusals);
`tests/unit/test_native_episode_runner_solver_hints.py` (the production render path: exactly the
two Solver contacts move, the block appears once per Solver contact and nowhere else, the receipt
and the asset pins reach the sealed episode receipt, and the OFF arm is the key's absence down to
the byte); `tests/unit/test_b8c_solver_hints_config.py` (the key is one episode-class factor, the
loaded OFF arm is the key's absence, and the loader refuses the wrong carrier, a non-L1 boundary
and an armed block with no data root). Gates `engineering_base_check`, `harness_admission_check`,
`tool_catalog_check`, `results_ledger_check` and `finite_completion_policy_check` PASS.

**What it does not authorise, and what is NOT claimed.** No owner decision, no preregistration, no
exposure row, no readiness package, no committed arm and no contact. Cell B8c is NOT registered by
E14: there is no admission, no cell and no flight. No claim is made that the block helps, or that
the construction neighbours reproduce A3's gold-derived pairs -- that comparison is one of the
questions the cell would answer, not a premise of building it. The comparator will be the sealed
B7r arm or the B7a v2 arm, decided at registration, on that arm's own roster and budgets.

---

## 17. E15 (2026-09-19): a Planner `ACQUIRE` with no acquisition node is a disposition

**The defect.** Finding I-1 of `docs/superpowers/specs/2026-09-19-slurp-agent-base-lock-v1-draft.md`.
Under the flown `planner_output_format: "exact-text"`, `reproduction/ojw/native_episode.py` built the
Planner's legal action set from the configured actions alone -- `{ACCEPT, REVISE, ACQUIRE}` -- for
every episode, while the graph's own action set (`NativeEpisodeWorkflow._planner_actions`, which
already drops `ACQUIRE` when no acquisition node was supplied) reached the node only under
`json-action-v1`. So an `ACQUIRE` token was *not* the E8c illegal-output disposition: at a
non-terminal revision it routed into `_Exhausted("episode has no configured analytical acquisition
role")`, which **raises** and takes the whole flight with it, and at the terminal revision it was
sealed as a `revision_limit` terminal delivery. One Planner word meant "the campaign dies" or "the
row is retained" depending only on when it arrived. That is the failure class item E8c removed for
unregistered Planner tokens, still open on one action. No SLURP cell -- the anchor, B1, B4b, B5e,
B7a v2, B7r, B8b, B4a, B8c -- has an acquisition node; in fact `rails/native_episode_config.py`
admits exactly the `perception`, `solver`, `reviewer` and `planner` roles, so **no** configuration
this runner accepts can build one.

**The fix.** The graph's own action set is now the authority for every Planner visit, under both
output formats: `NativeEpisodeWorkflow._add_role` hands `self._planner_actions` to the Planner's
`_ApplyRole` whenever `kind == "planner"`, instead of only under `json-action-v1`. Nothing else
moved. For an episode built without an acquisition node `ACQUIRE` is therefore an output that names
no registered action, and `_planner_action` returns `PLANNER_ACTION_ILLEGAL` exactly as it does for
`REJECT`: the row is **retained** through the E8c path -- the committed Solver draft is delivered
unchanged, no further role is contacted, no revision is spent, `planner_routes[-1]` carries
`legal: false`, `disposition: "planner_action_illegal"`, `action_sha256` and `action_chars`, and the
receipt's `planner_action_illegal` mark counts it. A cell verdict reads that count exactly as
section 2.4 of the base-lock draft already requires. For an episode that *does* carry an acquisition
node, `ACQUIRE` stays in the set and every byte of its behaviour is unchanged.

The router's `acquire_unavailable_<revision>` branch keeps its `_Exhausted` refusal. After E15 it is
unreachable by construction; it stays as defence in depth, so that a future caller that made
`ACQUIRE` legal without wiring a node would still be refused loudly rather than answer with no route.

**Alternative rejected.** Keeping `ACQUIRE` legal and routing `acquire_unavailable_<revision>` to a
new terminal disposition `acquire_unavailable` would have needed a new component, a new reason, a
new receipt field and matching validator, diagnostics and ledger updates -- and it would have kept
the untruth that an action the episode cannot execute is legal. The chosen fix is one expression.

**What changed for a real row.** Two behaviours, both on episodes with no acquisition node: an
`ACQUIRE` at a non-terminal revision no longer aborts the flight, and an `ACQUIRE` at the terminal
revision is now sealed as the illegal-output disposition (explicit-accept seal plus the route record
and the receipt mark) instead of as a `revision_limit` terminal delivery. The delivered text is the
same latest committed draft either way, and the row makes exactly the same contacts. No request byte
of any cell moves: `ACQUIRE` is never advertised in a Planner prompt
(`rails/runner.py` sets `available_planner_actions` from `ACCEPT`/`REVISE`/refresh only), and the
prompt builders are untouched.

**Proofs.** `tests/unit/test_ojw_native_episode.py::test_acquire_without_an_acquisition_node_is_a_retained_row_not_a_flight_abort`
(both output formats x first/terminal revision: no raise, the draft delivered, one Planner contact,
zero revisions spent, the route record, the receipt mark and an `accepted` delivery receipt);
`::test_acquire_with_an_acquisition_node_still_routes_to_acquisition` (unchanged behaviour when the
node exists, both formats); `::test_the_acquire_unavailable_branch_still_refuses_loudly_when_forced`
(the defensive branch still raises when `ACQUIRE` is forced back into the set);
`tests/unit/test_native_episode_runner.py::test_e15_actual_terminal_acquire_is_a_retained_row_not_a_terminal_delivery`
(the production runner: same contact count, accepted seal, no terminal disposition);
`tests/unit/test_node_context_policy_runner.py::test_e15_an_acquire_planner_output_keeps_the_anchor_request_bytes`
(byte identity: the anchor episode with the Planner answering `ACQUIRE` renders the first five
requests -- Perception, Solver, Reviewer x2, Planner -- at exactly the `ANCHOR_REQUEST_SHA256`
digests pinned from the pre-change tree, and the row is retained). The E8c proofs are unchanged and
still green.

**Zero contacts.** No model, tool, server or network contact; no config key, no cell, no
registration, no claim.

## 18. E16 (2026-09-19): a prepared artifact is evidence only for the implementation that produced it

**The rule.** A prepared artifact is evidence only for the implementation that produced it. `check`
verifies that identity. The flip and the flight commit are the same commit.

**The defect.** Two four-row smokes (B8b, B4a v2) were re-pinned at `7f97e0cf` / `60e01de3`, passed
`core.flight.cli check` at `1a617563` -- the registered composed and protocol hashes matched -- and
then flew from worktrees at `1a617563`. Each **opened an attempt** (`SPEECHRL_DATA_DIR/attempts/
<run>/<attempt>.json`, state `OPENED`, zero calls) and died in `FlightRuntime.run_phases ->
_dispatch_phase_program -> _phase_supply_seeds -> _load_phase_supply_seed ->
core.preparation.load_artifact` with `PreparationError("prepared artifact identity mismatch")`. The
coordinator voided both attempts with `AttemptStore.abort_if_opened` and re-pinned.

The cause is not the hashes `check` measured. `core.preparation.artifact_inputs` binds three things
into a prepared artifact: `config_sha256`, `split_identity_hash` and `sources` -- and for the
phase-supply artifact `sources["implementation"]` carries the SHA-256 of `core/flight/runtime.py`
plus `rails.kb_policy`, `rails.knowledge_provider`, `rails.phase_supply` and (when a named store is
bound) `rails.knowledge_stores`. The E14 and E15 merges moved those files, so every artifact
prepared before them was stale by construction. `check` never loaded the artifact, so it could not
see that: it measured the composed config and protocol hashes, which the artifact's identity
deliberately does **not** depend on (`_RECEIPT_KEYS` strips `prepared_phase_supply` and the cells'
`readiness` blocks precisely so a re-pin does not invalidate what it pins). A green `check` and a
dead flight were therefore consistent, which is the property this item removes.

**The fix, in three places that share one identity computation.**

`FlightRuntime.phase_supply_artifact_identity()` is now the single derivation of the phase-supply
artifact's identity: it builds the phase-program binding from config
(`_prepared_phase_program_binding`, which also loads every pinned `prepared_phase_recall` artifact
through the ordinary `_resolve_phase_supply`), selects the program's first supplied phase, and
returns the `_phase_seed_inputs(...)` document. `prepare_phase_supply` produces the artifact through
it, `core.flight.repin.ensure_artifact_pinned` verifies a pin by re-running that producer on the
existing path, and `_load_phase_supply_seed` binds it at dispatch through the same
`_phase_seed_inputs`. `check`, `repin` and the flight therefore cannot disagree about what makes an
artifact stale.

`FlightRuntime.verify_prepared_artifacts()` recomputes that identity read-only -- it never builds,
writes or raises -- and returns one report per prepared artifact this flight would load in
`run_phases`: `{key, relpath, sha256, identity_ok, reason, difference}`. `difference` is the first
differing key path of the two `inputs` documents, walked in sorted order by
`core.preparation.first_input_difference`, so the stale B8b/B4a artifacts would have named
`sources.implementation.runtime` rather than an undifferentiated "identity mismatch". A cell that
pins no prepared artifact, and a policy that never loads one (`fixed` and the obs policies dispatch
outside `_dispatch_phase_program`), verify nothing and pay nothing. The verdict is memoized on the
runtime, so the launch guard and the preflight behind it compute it once.

`FlightRuntime.preflight()` runs the verification **before** `preprocess`, `serve`, the client and
therefore before `core.model.adapter.FrozenCoreAdapter` calls `AttemptStore.open_attempt`, and
refuses with a `PreparationError` naming every stale artifact and its cause. Its receipt carries
`prepared_artifacts` and `prepared_artifacts_ok`. `core.flight.cli check` is the one caller that
passes `enforce_prepared_artifacts=False`: a check exists to print the verdict, so it reports
instead of raising, adds a `blockers` entry per stale artifact, leaves
`scientific_readiness.state` exactly as the registration declares it, and **exits non-zero**.
`core.flight.cli` additionally calls `assert_prepared_artifacts_current(flights)` for `worker` and
`campaign` before anything else runs, so the refusal is visible at the launch boundary and not only
inside a queue's `preflight-failed` state.

**What a stale artifact now costs.** Zero model contacts, zero attempt records, one non-zero exit
and one message naming the artifact and the first input that moved. The remedy is unchanged:
re-pin the package with `core.flight.repin` on the launch commit and fly from that commit.

**Proofs.** `tests/unit/test_flight_prepared_artifact_preflight.py` -- the diff-namer on a moved
implementation source, a config edit, both together and a key present on one side only; a real
prepared phase-supply artifact that verifies, and the same artifact with its embedded
`inputs.sources.implementation.runtime` rewritten (identity refused, `difference ==
"sources.implementation.runtime"`); a moved file hash; an absent artifact; the memoized verdict;
`prepare_phase_supply` naming the difference on a warm mismatch (the path `repin` uses);
`preflight` recording the verdict, refusing a stale artifact with no `attempts/` directory created
and no `preflight` receipt recorded, and reporting instead of refusing under
`enforce_prepared_artifacts=False`; and `core.flight.cli` worker refusing before the attempt file
exists, worker proceeding when every artifact verifies, `check` exiting 1 with `blockers` and
`preflight.prepared_artifacts_ok: false`, and `check` exiting 0 otherwise.

**Zero contacts.** No model, tool, server or network contact; no config key, no cell, no
registration, no claim.

## 19. E19 (2026-09-19): the Reviewer slot-audit block, re-based off L1

Cell B7a v2 read level L1 **HARMFUL** on 2026-09-19
(`docs/results/2026-09-19-slurp-b7a-ncp-l1-anchor-v2-verdict.md`: official pooled SLU
−0.3100 pp [−1.8072, +1.1211], intent −0.6481 pp [−2.1849, +0.8688], +11.6 % GPU hours for no
gain). Owner decision 32 was pre-authorised for exactly that outcome: cells B7r and B7c close
unflown, level L2 stays unflown, and **cell B8b is re-based on the anchor and re-registered**,
because — in the decision's own words — "the audit block attaches to the L1 structured Reviewer
boundary".

That attachment was the only thing L1 was giving it. Section 16.1's block is an **addition**: it
needs somewhere to be appended, not something to read. The B7a v2 rendering diagnostics make the
point exactly: *0 parsed of 1,243 structured review-finding rows — FALLBACK-RAW on 100 % of them*.
The Reviewer stayed prose on that base and the audit never saw a parsed Reviewer output. What E12
coupled to L1 was the **rendering slot** of the `reviewer:current-draft` boundary, and a rendering
slot is not a level.

### 19.1 The mechanism: a second attachment

`native_episode.reviewer_audit` now resolves an **attachment** rather than demanding a level
(`rails.node_context_binding.reviewer_audit_boundary_attachment`,
`rails.node_context_policy.SLOT_AUDIT_ATTACHMENTS`):

| the boundary's declared level | attachment | what the block follows |
| --- | --- | --- |
| `structured` | `l1-rendering` (E12, unchanged) | the boundary's own L1 rendering |
| `raw`, or no `context_policy` declared at all | `sealed-draft` (E19) | the **sealed Solver response**, byte for byte |
| `cleaned` | refused by name | a cleaning contact rewrites what the block is appended to |

At `sealed-draft` the transform appends the block to `state.content` after one newline and derives
the exposed state from it; everything else passes through untouched. The block itself is rendered
by one function through one template for both attachments
(`SlurpNodeContextPolicy._slot_audit_block`), so the two modes cannot drift apart.

Three consequences follow, and they are what make the cell one-factor on the anchor:

1. **The ON arm needs no policy.** A fragment that arms the audit and declares no `context_policy`
   composes the key's own bare `"raw"` arm (`IMPLICIT_RAW_CONTEXT_POLICY`), so the node-context
   transform still runs and still emits one `level: "raw"` receipt row per boundary per contact.
   L0's byte identity therefore stays a **checked statement** at every boundary, exactly as section
   9 requires.
2. **The only byte that moves is the block.** Perception, Solver and Planner requests are
   byte-identical to the anchor's. Proved over the production render path in
   `tests/unit/test_native_episode_runner_reviewer_audit.py`
   (`test_on_the_anchor_shape_the_block_moves_only_the_reviewer_contacts`), which flies both arms
   through the real role graph, the real runner and the real request renderer over the shared fake
   transport.
3. **The inequality is never silent.** `_raw_row` gains exactly one exception to
   `rendered_sha256 == source.content_sha256`, and that row always carries a
   `saea-reviewer-slot-audit-v1` receipt naming the block by `block_sha256` and `block_chars`. No
   `slot_audit` block, no inequality — which is the diagnostic the verdict reports.

An all-raw policy parses nothing of its own, so the sealed-draft attachment binds the carrier's own
closed draft contract (`SLURP_CLOSED_DRAFT_SCHEMA`) to read the draft it is auditing. A test pins
those bytes against the committed L1 fragment's `params.draft_response_schema`, so a draft parses
identically under either attachment; a draft that does not parse takes the untouched state and an
`applied: false` / `reason: "draft-unparsed"` receipt.

### 19.2 Why not a minimal per-boundary L1 declaration

The alternative was a `context_policy` restricted to `reviewer:current-draft` at `structured` with
every other boundary raw. It was rejected on the cell's own criterion. That declaration replaces
the sealed draft JSON with the L1 draft rendering **and** appends the block, so the ON-vs-OFF
Reviewer diff would carry two changes, not one, and the cell would no longer be a one-factor read
of the audit. The sealed-draft attachment adds the block to exactly the one thing the Reviewer
would otherwise have received.

### 19.3 What is not claimed

E19 is engineering plus a registration; it is not a result. It does not revive level L1 — B7a v2's
HARMFUL read stands and cells B7r and B7c stay closed. It does not claim the audit is useful: cell
B8b-anchor (`docs/readiness/2026-09-19-slurp-b8b-anchor-reviewer-audit-v1/`) is registered `held`
and measures that once, against the sealed anchor, under a rule fixed before any number is seen. It
does not claim the two attachments render the same block on the same row — they render the same
block, appended to different text, and only the block's own bytes are shared. And it makes no claim
about the Solver hints of E14, which keep the L1 requirement: their block is an addition to the
candidate **list** rendering, which at raw is a projected Perception JSON the hints were never
designed to follow.
## 20. E20 (2026-09-19): an over-long request degrades into a retained row

Owner decision 45, and the measured analysis
`docs/results/2026-09-19-slurp-serving-geometry-and-degradation-v1.md` part B. Before this item a
request wider than the live serving slot ended the **flight**, in three places at once:

* **Preflight.** `core.flight.runtime.FlightRuntime._assess_prompt_budget` raised
  `FlightRuntimeError` on anything but `ALLOW`, and its own comment said why — "A pre-flight
  estimate has no live compaction mechanism to apply, so `COMPACT_REQUIRED` is just as fail-closed
  here as `REFUSE`". The rail's own "this is fixable by dropping context" verdict aborted the
  flight before a single contact.
* **Dispatch.** `rails.context_budget.assess_context_budget` was called from exactly one place —
  that preflight. No realised request was ever budgeted against the live slot, and the rail's
  `MAX_COMPACTION_PASSES = 2` and its `agent-state:` / `facet:` / `value:` droppable-identifier
  validation had no caller at all.
* **The wire.** The built fork answers a prompt at or above the slot width with HTTP 400 and
  `error.type == "exceed_context_size_error"` (`tools/server/server-common.cpp:59-62`), and
  `core/model/transport.py` turned every `HTTPError` into one `FrozenCoreError`. The row died, and
  with it every row after it. WSL 2 makes the alternative impossible: unified-memory
  oversubscription cannot work on this host (part B section 3.1), so the harness has to degrade.

`native_episode.context_fit_policy` is the **tenth** episode-level switch key
(`rails.config_tables.EPISODE_LEVEL_SWITCH_KEYS`) and the **second failure-mode** key, after E13's
`finite_completion_policy`. Values: `"raise"` (the pre-E20 behaviour; the null arm is the key's
absence or this literal) and `"compact-or-abstain"`.

### 20.1 The mechanism

**At preflight**, under `compact-or-abstain`, a `COMPACT_REQUIRED` representative no longer
raises: the decision is recorded in the `prompt_budget` receipt exactly as an `ALLOW` is, and the
flight proceeds — because from E20 there *is* a live compaction mechanism. What still aborts, on
**both** arms, is a **negative physical margin**: the required window exceeds the physical slot
itself, not merely the operational reserve. That is what "REFUSE" means at this seam; the rail's
literal `REFUSE` is unreachable here by its own rule (it is returned only at `compaction_pass ==
MAX_COMPACTION_PASSES`, and a preflight candidate is always at pass 0). No compaction can repair a
prompt that does not fit the hardware, because the undroppable part is already inside that window.

**At dispatch** (`rails.runner._invoke_native_role_episode.fit_contact_to_slot`), every realised
request is budgeted against the live slot immediately before it is sent — the seam
`rails.context_budget`'s own module docstring reserved ("receipt-bound exact counts for an already
rendered payload immediately before each model contact") and nothing had ever wired. The budget is
`rails.native_episode_config.ContextFitBudget`: the live per-slot limit E17 already binds the
preflight to, minus the live-slot operational reserve, the completion ceiling and the registered
special-token reserve. A request that does not fit has droppable blocks removed in the declared
order, at most two passes, and is sent with a `context_compaction` record. Re-composition goes
through the SAME `MeteredNativeSpeechRequest.prepare` over a narrowed binding
(`binding_override`), never through the binding provider a second time: that provider settles
episode state and may spend a cleaning contact, so calling it twice for one contact is a defect.

**At the wire**, `FrozenCoreContextSizeError` (a `FrozenCoreError` subclass) is raised for that one
error class only, classified from the PARSED body — never from a substring of a free-text message —
so a schema error is never mistaken for an overflow. Every other status, and every other 400,
raises exactly the `FrozenCoreError` it always did.

### 20.2 The declared drop order

Deterministic, declared, never a heuristic; lowest authority first
(`rails.context_fit.DROP_ORDER`):

| # | block | addressed as | within the block |
| --- | --- | --- | --- |
| 1 | `exemplar-supply` | `value:<value_id>` | tail first |
| 2 | `candidate-cards` | `facet:<facet_id>` | tail first |
| 3 | `scenario-hints` | `facet:native-episode-scenario-hints` | the whole block |
| 4 | `reviewer-audit` | `facet:native-episode-reviewer-audit` | the whole block |
| 5 | `agent-states` | `agent-state:<state_id>` | oldest first |

**Never droppable, byte for byte:** the instruction text and task contract (the system message),
the speech packet reference, the current draft (the newest Solver state, and the role query the
request carries) and the tools array. They are the request's identity.

Two passes, each with its own allowance. Pass 1 spends each block's **surplus**: the exemplar and
candidate tails beyond `k // 2`, the two whole attachment blocks, and every agent state but the
newest. Pass 2 spends what is left, down to each block's hard floor (nothing for the two evidence
blocks; the newest state for the history). Within a pass the walk stops at the first view that
fits, so a request one item over loses exactly one item.

Blocks 3 and 4 are the one piece of new plumbing the analysis called for. They are not separate
message parts: `rails.node_context_policy` **appends** them to a rendered state as
`f"{rendered}\n{block}"`. The contact's own compilation receipt records each appended block's
`block_sha256` and `block_chars` (never its text), which is exactly enough to remove it by exact
trailing bytes — and to refuse to remove anything on a digest mismatch, in which case the block is
simply not a droppable item for that contact and the walk moves on down the order.

### 20.3 Receipts

Per contact: `native_episode_receipt.context_fit.contacts[i].context_compaction`, or `null` for a
request that fitted, so the receipt says the check ran on every contact rather than only on the
ones that moved. The record names the schema, the pass count, the blocks and identifiers dropped
with their item counts, tokens before and after, the limit, and the never-droppable list.

Per row: a request that cannot be made to fit takes a `terminal_disposition` with
`reason: "context_compaction"`, modelled on E13's finite-completion row — `role_id`, `stage`,
`revision_count`, `planner_accepted: false`, the compaction pass, the dropped identifiers, the
token counts, the `source` (`dispatch-budget` or `server-refusal`) and the server's own message
when the server is the one that refused. The row is **retained and scored**: the latest
delivery-eligible Solver draft is delivered, or, with none, the row abstains through a derivation
bound to its own disposition (`core.delivery.native_context_abstention_records`) rather than to a
source contact, because there is none. `rails.native_episode_receipt._context_fit_delivery`
validates the shape and returns delivery kinds `context-fit` / `context-abstention`;
`validate_native_episode_terminal_policy` accepts either only under a **declared**
`context_fit_policy`, so a row can never degrade under a policy inferred from its own failure.

Per run: `run_phases` now carries `native_episode_dispositions` with
`planner_action_illegal_rows`, `finite_completion_rows`, `context_compaction_rows` and
`context_compaction_contacts`, read off the rows' own sealed receipts. The last two are different
numbers: most compacted contacts belong to rows that go on to deliver normally.

### 20.4 What is not claimed

E20 is engineering. It is **not** a result, and it does not license spending the np4 margin — part
B's own conclusion is that the read is guaranteed by geometry **plus** this policy, not by this
policy alone. It makes no claim that a compacted request answers as well as an uncompacted one:
dropping exemplars and history is a loss, and a cell that arms the key must report
`context_compaction_contacts` and `context_compaction_rows` as diagnostics beside its primary
number. It does not bound the test split's prompt tail — that is part B step 1, a separate
model-free pass, and no geometry may be chosen for a split whose tail nobody has seen. It changes
no request byte on a row that fits (proved by pinned request hashes, as E17 and E18 were), and it
arms nothing: every committed fragment still composes `"raise"`.

### 20.5 Two limits of this implementation, stated

**The cleaning contact is not covered.** `rails.runner`'s metered cleaning path
(`run_cleaning_contact`, used only by a `level: "cleaned"` boundary) still prepares and dispatches
without a fit check, and a `FrozenCoreContextSizeError` there still ends the flight. No committed
fragment declares a cleaned boundary, and level L2 is unflown (section 19), so this is a gap rather
than an exposure; it belongs to the item that flies L2.

**A context abstention on the FIRST contact cannot be sealed.** A row whose very first request is
refused for width has no recorded timing at all, and `seal()` refuses it with its existing message
("no per-request record for sample ..."): an outputs row cannot carry response identity hashes for
a request no core ever answered. Every other context abstention -- refused after at least one
completed contact -- seals on the sample's own last recorded timing, with its delivered identity
derived from the disposition. This is fail-closed rather than silent, and it is the honest
boundary: a row that never reached the core produced nothing to score.

**`monitor.jsonl`'s `requests_total` undercounts, and the fix is not a one-liner.** Part B section
1.2 measured it: over the B4a v2 arm the counter advances 4,466 where the server completed 5,409
requests and the seal records 5,412 contacts. The cause is in
`scripts/serving_monitor.py:116-127` (`count_new_requests`) driven from the poll loop at
`scripts/serving_monitor.py:206`: it counts a `/slots` task-id CHANGE per poll, so two requests
that share one slot between two polls count once. Its own docstring already says so — "a LOWER
BOUND at the sampling interval". The exact counter exists (`llamacpp:requests_processed` on
`GET /metrics`, which `read_metrics` already parses), but the pinned fragments deliberately do not
pass `--metrics`, because that flag changes the argv and therefore the serving identity every
flight compares. So the repair is a serving-identity change with its own receipt, not a code fix,
and this item leaves it as a finding: **every throughput number must be counted from `server.log`
release records, and `monitor.jsonl` used only for utilisation, power, busy slots and VRAM, which
it samples directly.**
