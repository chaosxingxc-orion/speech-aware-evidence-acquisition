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
     episode meaningless; today only `plan-action`, where the harness already refuses.

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

