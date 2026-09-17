# SLURP node context audit: what every agent node actually receives

Date: 2026-09-17. Root: Fable 5.1. Program:
`docs/superpowers/specs/2026-09-16-slurp-v2-base-program-design.md`. Answers the owner directive of
2026-09-17 (section 0) and is the evidence base for
`docs/superpowers/specs/2026-09-17-node-context-policy-design.md`.

Zero model, tokenizer, encoder, scorer or server contacts. The only inputs are the sealed bytes of
`SAEA-SLURP-NATIVE-DUAL-STORE-TRAIN-FOLD-A-ANCHOR-RECOVERY-V1` (`.trace.jsonl` 479.7 MB,
`.outputs.jsonl`), opened read-only, plus the repository at `0c09978f`. No utterance text, gold
label, entity filler or model output text is quoted, printed or persisted anywhere; only lengths,
counts, hashes and structural classes.

Machine result: `analysis/SAEA-SLURP-NODE-CONTEXT-AUDIT-V1/result.json` under `SPEECHRL_DATA_DIR`,
SHA-256 `c46aabeaff53e19fe76b4ca0131765dafaff1e29f296950314ae7006dcdaae48`, with `README.md`,
`node-visits.csv`, `contacts.jsonl` (5,417 rows), `wire-composition.jsonl` (5,417 rows),
`episodes.jsonl` (1,080 rows) and `drivers/` beside it.

## 0. The directive this audit answers

Owner, 2026-09-17, verbatim in Chinese:
"我希望每个智能体node之前的上下文有一个统一的处理策略，不要把模型的输出不加工的提交给下一个node，至于node的上下文，你可以提供一些模板甚至必要的时候我们可以增加一次模型调用来提升模型的上下文的干净程度以提升模型在不同任务上的表现"

English (the form that enters every downstream context, per the program's first principle): *every
agent node's input context must follow one unified handling policy; never hand a model's raw output
to the next node unprocessed; per-node templates, and where necessary one extra model call to clean
the context, to raise the model's performance across tasks.*

**The audit's answer to the premise: it is correct as stated.** In the sealed anchor there is no
node-boundary handling policy at all. Every upstream model output reaches the next node as its own
bytes, under one fixed prefix, with no parse, no schema check, no normalisation and no declared rule
for a malformed output. The one exception is the Perception output, which a second, independent
channel does parse — and that exception is the proof that the mechanism is available and simply not
applied at the other three boundaries.

## 1. How a node request is assembled (the mechanism, in code)

The native episode graph (`reproduction/ojw/native_episode.py`) owns routing only. It carries episode
state (`original_query`, `candidates`, `perception`, `latest_solver`, `review`, `plan`,
`revision_count`, `role_visits`, `planner_routes`) and calls one `RoleInputBuilder` per visit. It
never writes a prompt.

The builder is `role_input` in `rails/runner.py:1798`. Per visit it:

1. settles the previous contact into episode custody (`settle(next_phase=phase_id)`), which seals the
   previous model response as an `AgentStateArtifact` and, if the destination phase declares
   `knowledge: "supplied"`, runs `binding.supply_for_phase`;
2. builds `PhaseMaterial` for the phase (`binding.material_for_phase`), whose `instruction` is the
   phase's own committed template file;
3. appends `"\n\nNative episode limits: " + json.dumps(limits, sort_keys=True)` to that instruction
   (`revision_index`, `max_revisions`, `remaining_model_contacts`, `role_max_iterations`,
   `available_planner_actions`);
4. returns `material.instruction` as the node's query.

The request itself is composed in `reproduction/ojw/native_request.py`
(`MeteredNativeSpeechRequest.prepare`) over the shared two-message base
(`_agent_messages` → `[system, user]`) plus `agent_state`, and rendered onto the wire by
`core/model/transport.py` with `core/model/native_history.py` and
`core/model/native_framework_history.py`. The four content slots a node sees are:

| slot | source | per-node? |
| --- | --- | --- |
| `task_instruction` (system message) | `task_instruction_template` `probes/slurp_native_role_context_v3.txt` + fill `slurp-label-inventory` | **no** — byte-identical for all four roles, 8,118 chars |
| `supplied_evidence` (user text parts `[evidence <id>] <content>`) | `knowledge_stores` phase supply | yes, per phase |
| agent-state text parts `[agent state <id> kind=<kind>] <content>` | every sealed prior model response | yes, by accumulation |
| the role query (last user text part) | the role's own `probes/slurp_native_role_*.txt` + the limits JSON | yes |

The exact verbatim-copy template is `core/model/transport.py:300`:

```
rendered.append(f"[agent state {state_id} kind={state_kind}] {content}")
```

`content` is `completion.text` of the upstream contact, unchanged. `rails/controllers.py:553`
(`seal_phase_response_state`) documents the seam that is not used: *"state_content is the raw
response **or a registered view of it**"* — the native runner passes
`state_content=completion.text, raw_response_text=completion.text`, so today the view is the raw
response.

## 2. The graph as flown

Config `configs/baseline/slurp-native-dual-store-train-fold-a-anchor-v1.json`, policy
`configs/policy/phase-native-candidates-review-revise-v1.json`: `max_revisions 1`; roles perception 1,
solver 1, reviewer 3, planner 1 iteration; contact ceiling `1 + (1+1)*(1+3+1) = 11`; Reviewer alone
holds tool authority (`saea-tool-task-contract-v1`); `exhaustion_policy "deliver-latest-solver"`;
`planner_output_format` defaults to `exact-text`; **no `role_context` block and no `history_scope`**,
so every role's `history_scope` is `"full"`.

Realised over 1,080 rows: 5,417 contacts (5.0157/row).

| episode shape | rows |
| --- | ---: |
| perception → solver → review → planner | 1,075 |
| perception → solver → review → planner → solver → review → planner | 5 |

Planner action sequences: `ACCEPT` 1,075; `REVISE → ACCEPT` 4; `REVISE → REVISE` 1 (the single
terminal delivery). Planner outputs overall: 1,079 `ACCEPT`, 6 `REVISE`, 0 other. Reviewer iterations
per episode: 2 in 1,072 episodes, 4 in 5, and **1 in 3 episodes — three Reviewers never made the tool
call their own prompt calls mandatory, and nothing refused the visit.**

## 3. Every node boundary: what enters, through which field, raw or parsed

| boundary | what crosses | field | form | validated? |
| --- | --- | --- | --- | --- |
| (entry) → Perception | speech packet; 8 intent-boundary knowledge values | user speech part; `supplied_evidence` | typed knowledge | n/a |
| Perception → Solver **(a)** | the Perception response text | `history` `agent_state` `phase:perception` → `[agent state … kind=phase:perception] <raw>` | **raw bytes** | no |
| Perception → Solver **(b)** | the same response, *parsed* | `supplied_evidence` (the block set grows from 8 to a median of 20) | `project_bounded_slurp_intent_hypotheses` → up to 3 legal intent ids → `slurp-candidate-semantic-v1` retrieval into the slot-contracts store | **yes**, 1,080/1,080 |
| Solver → Reviewer | the Solver draft text | `agent_state` `phase:solver` → raw text part | **raw bytes** | no |
| Reviewer(it.1) → Reviewer(it.2) | its own tool-call turn + the tool result | assistant message + `tool` message (`native_tool_result_message`) | framework replay | source-authority hashes only |
| Reviewer → Planner | the Reviewer findings text | `agent_state` `phase:reviewer` → raw text part | **raw bytes** | no |
| Reviewer → Planner (carried) | the Reviewer's turn-1 state and its tool result | assistant + `tool` message | framework replay | source-authority hashes only |
| Planner → Solver (REVISE) | the Planner action text | `agent_state` `phase:planner` → raw text part (6 chars) | **raw bytes** | exact-text match against the registered action set only |
| Planner → episode | the action | `_ApplyRole` / `_planner_action` | `output in {ACCEPT, REVISE, ACQUIRE}` else `NativeEpisodeError` | yes, but on the action token only |

Only one of the four model-output boundaries is parsed, and it is parsed by the knowledge-supply
path, not by any context policy: the Perception → Solver **(b)** channel. Its verdict on a
malformed Perception output is to raise `CandidateSemanticSupplyError` and fail the row; zero rows
failed, because Perception is the only role whose phase declares a `response_format_id`
(`slurp-intent-hypotheses-v1`, strict JSON schema). Solver, Reviewer and Planner all declare
`response_format_id: null` and are generated as free text.

## 4. Sizes, per node visit (1,080 rows)

Wire-side character decomposition, reconstructed with the repository's own rendering rules
(`_speech_history_texts`, `project_native_history`, `project_native_framework_history`,
`native_tool_result_message`); prompt/completion tokens are the sealed per-contact COST receipts.

| node visit | contacts | prompt tok med | prompt tok p95 | system chars | role-instruction chars | knowledge chars (evidence) | knowledge chars (tool msg) | **upstream model text chars** | model-text share | verbatim state parts | assistant replays | tool msgs | completion tok med |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| perception#0 | 1,080 | 3,593 | 3,674 | 8,118 | 1,135 | 6,022 | 0 | **0** | 0.0 % | 0 | 0 | 0 | 134 |
| solver#0 | 1,080 | 8,954 | 11,072 | 8,118 | 1,304 | 32,010 | 0 | **686** | 1.6 % | 1 | 0 | 0 | 24 |
| reviewer#0 | 1,080 | 9,065 | 11,178 | 8,118 | 609 | 32,010 | 0 | **924** | 2.3 % | 2 | 0 | 0 | 22 |
| reviewer#1 | 1,077 | 10,841 | 12,956 | 8,118 | 609 | 31,901 | 6,243 | **1,058** | 2.3 % | 2 | 1 | 1 | 67 |
| planner#0 | 1,080 | 10,800 | 12,947 | 8,118 | 367 | 32,010 | 6,243 | **1,544** | 3.4 % | 3 | 1 | 1 | 2 |
| solver#1 | 5 | 10,927 | 12,799 | 8,118 | 1,293 | 30,825 | 6,243 | **2,125** | 4.5 % | 4 | 1 | 1 | 26 |
| reviewer#2 | 5 | 11,026 | 12,914 | 8,118 | 599 | 30,825 | 6,243 | **2,428** | 5.0 % | 5 | 1 | 1 | 22 |
| reviewer#3 | 5 | 12,804 | 14,692 | 8,118 | 599 | 30,825 | 12,486 | **2,563** | 4.7 % | 5 | 2 | 2 | 82 |
| planner#1 | 5 | 12,757 | 14,697 | 8,118 | 357 | 30,825 | 12,486 | **3,095** | 5.7 % | 6 | 2 | 2 | 2 |

Prompt growth along the episode: 3,593 → 8,954 → 9,065 → 10,800 median tokens, i.e. **+7,207 tokens
(3.0×) from Perception to Planner**. That growth is almost entirely knowledge, not model text: the
`supplied_evidence` block set goes from 8 blocks / 6,022 chars at Perception to 20 blocks /
32,010 chars from the Solver onwards, and the Reviewer's tool call adds a further 6,243 chars.
Upstream model text is 686 → 1,544 chars over the same span.

Run totals: **45,998,267 prompt tokens** and 255,153 completion tokens; 42,591 prompt tokens per
roster row. Upstream model text is **4,493,011 of 206,799,138 wire text characters = 2.17 %**.

| role | contacts | prompt tokens | share | completion tokens |
| --- | ---: | ---: | ---: | ---: |
| perception | 1,080 | 3,884,813 | 8.45 % | 127,124 |
| solver | 1,085 | 9,492,410 | 20.64 % | 25,224 |
| reviewer | 2,167 | 21,112,471 | 45.90 % | 100,629 |
| planner | 1,085 | 11,508,573 | **25.02 %** | 2,176 |

**The Planner spends a quarter of the run's prompt budget — 11.5 M tokens, median 10,800 per contact
— to emit a median of 2 tokens, and 1,079 of its 1,085 outputs are the literal `ACCEPT`.** That is
5,289 prompt tokens per completion token.

Prompt fit: `serving_slot_tokens` is 24,576 and the largest prompt observed anywhere in the run is
14,868 tokens (planner#1). Headroom at the worst observed contact is 9,708 tokens (39.5 % of the
slot), so no node-boundary policy in the design's L1 range is fit-constrained.

## 5. Every place a model output is copied verbatim into a downstream prompt

1. **`core/model/transport.py:300` (and `:228` for the same path)** — `[agent state {state_id}
   kind={state_kind}] {content}`, where `content` is the upstream `completion.text`. Median 1 part at
   solver#0, 2 at reviewer#0/#1, 3 at planner#0, up to 6 at planner#1. This is the whole of the
   Perception → Solver (a), Solver → Reviewer, Reviewer → Planner and Planner → Solver channels.
2. **`core/model/native_history.py:466` / `native_framework_history.py:312`** — the Reviewer's own
   tool-calling assistant turn is replayed into later contexts as the original assistant message,
   content and `tool_calls` unchanged, verified against `source_authority.original_assistant_message`.
   1 replay per Reviewer second iteration and per Planner contact; 2 at reviewer#3/planner#1.
3. **`rails/phase_material.py:1041`** — `render_phase_predecessor_block`, which appends
   `"Prior phase response ({state_kind}):\n{content}"` into the *instruction* itself under
   `predecessor_binding` `append-sealed-state` / `sealed-manifest`. **Not used by the anchor**
   (`predecessor_binding: "none"` on all four phases), but it is a second live verbatim channel and a
   policy that ignores it would be incomplete.
4. **`reproduction/ojw/native_request.py:296`** — `framework_contact_instruction` encodes the complete
   framework message list (including the system message and the role query) as a JSON envelope in the
   `control` history entry. This is custody, not wire bytes: `project_native_framework_history`
   replaces it with the role query alone as the final user text part. Median envelope 9,626–10,591
   chars; it must not be counted as on-wire token consumption.

Nothing else copies a model output forward. There is no summariser, no field extractor, no
normaliser and no truncation on any of these paths.

## 6. Malformed upstream output: what actually happens

The only admission test at a node boundary is `role_delivery_allowed` in `rails/runner.py`:

```python
def role_delivery_allowed(_role: str, output: str) -> bool:
    return isinstance(output, str) and bool(output.strip())
```

Non-empty text is a valid draft, a valid review and a valid plan. Measured on the anchor:

| node | outputs | fail today's registered structured parser | consequence |
| --- | ---: | ---: | --- |
| perception | 1,080 | 0 (`project_bounded_slurp_intent_hypotheses`) | — (generated under a strict JSON schema) |
| solver | 1,085 | **7** (`parse_slu_response`; the same 7 fail `json.loads`) | none: all 7 were passed verbatim to the Reviewer and the Planner, **all 7 Planners answered `ACCEPT`**, and all 7 were delivered as the row's final answer |
| reviewer | 2,167 | **2,167** (`rails.review_findings.parse_review_findings`) | none: the prose findings are passed verbatim to the Planner |
| planner | 1,085 | 0 (exact-text action match) | an unmatched token would raise `NativeEpisodeError` and fail the row |

The 7 malformed rows are `slurp:train:{002929, 003759, 004509, 005800, 006310, 009172, 015927}`. On
each, the Reviewer emitted a longer-than-median finding (294–538 chars against a 60-char median) and
the Planner accepted anyway. The review loop is not a malformed-output filter and was never asked to
be one.

The `2,167/2,167` Reviewer figure is the sharpest result in this audit and deserves care: it is not a
model failure. The Reviewer prompt (`probes/slurp_native_role_reviewer_v1.txt`, 435 bytes) asks for
"concise findings for the Planner" in prose, and the phase declares no response format, so the model
complies. `rails/review_findings.parse_review_findings` expects a structured findings document. The
two were never connected. **A structured policy applied to today's Reviewer output would therefore
find nothing to structure** — see section 9.

## 7. What the Reviewer and the Planner actually see

**Reviewer, first iteration** (1,080 contacts): system task contract (8,118 chars, identical to every
other node's), speech packet, 20 knowledge evidence blocks (32,010 chars, the same set the Solver
saw), the raw Perception response (median 508 chars) and the raw Solver draft (median 94 chars) as
two `[agent state …]` text parts, then its own 609-char instruction. Median 9,065 prompt tokens. It
is fully draft-visible and receives no isolation of any kind; `docs/results/2026-09-16-slurp-review-context-provenance.md`
already recorded this qualitatively — "Reviewer is a separate role with a separate output
responsibility, but is neither draft-blind nor a statistically independent judge" — and this audit
supplies the field-level and size-level proof.

**Reviewer, second iteration** (1,077 contacts): the above plus its own turn-1 assistant message
replayed with its `tool_calls`, plus the tool result as a `tool` message (6,243 chars). Median 10,841
prompt tokens.

**Planner** (1,080 contacts): the same system contract and the same 20 knowledge blocks, plus, in
order: the raw Perception response, the raw Solver draft, the Reviewer's turn-1 assistant message
(replayed with its tool call), the Reviewer's tool result rendered as a 6,243-char `tool` message,
the raw Reviewer findings, and finally its own 367-char instruction. Three verbatim state parts, one
assistant replay, one tool message; median 10,800 prompt tokens for a 2-token answer. **The Planner
receives the entire episode unfiltered, including everything the Reviewer already consumed, and its
only registered use of it is to choose one of two tokens.**

## 8. The second Solver visit (REVISE), 5 rows

On `REVISE` the graph re-enters `_add_role("solver_1", predecessors=(revise_id,))` with the same
`role_input` builder. The revising Solver sees four `[agent state …]` text parts plus one
assistant/tool replay pair: the raw Perception response (median 563 chars), **its own previous
draft** (median 57 chars on these 5 rows), the Reviewer's turn-1 assistant message and its
6,243-char tool result, the raw Reviewer findings (the Reviewer states total a median 666 chars) and
the Planner's 6-character `REVISE` token. Median 2,125 chars of upstream model text, 10,927 prompt
tokens. Its role instruction changes by 11 characters relative to visit 0 — only the
`Native episode limits` JSON differs (`revision_index 1`, `remaining_model_contacts`,
`available_planner_actions` reduced to `["ACCEPT"]`); the prompt file
`probes/slurp_native_role_solver_v2.txt` carries a single fixed sentence for the revision case
("On a revision, reconsider your answer using the same original Perception candidates and the
intervening Reviewer/Planner evidence"). **There is no revise-specific template, no diff, no
statement of what the Reviewer objected to and no constraint on what may change.** Owner ruling of
2026-09-08 ("revise needs new information + constrained edits + core answer authority") is
unimplemented at this boundary.

## 9. Structured machinery that exists and is switched off

`rails/role_context.py` (839 lines) implements `SlurpRoleContextCompiler`, a complete typed
role-context compiler: per role kind it selects the relevant states, replaces each with a derived
`role-context:<semantic_class>` artifact whose content is canonical JSON
(`saea-typed-role-context-state-v1`), and emits a hash-bound compilation receipt
(`saea-role-context-compilation-v1`) listing every retained state with its source binding and every
excluded state with a reason. It is bound by `rails/role_context_binding.py` through the optional
`native_episode.role_context` config block, compiled once per Perception visit in
`rails/runner.py:1806`, and applied in `speech_binding` at `rails/runner.py:1944`. It is deterministic
and costs zero contacts.

Its declared per-class rules today are:

- candidate hypothesis (Solver, Reviewer): the projected candidate list plus an
  `evidence_ref_availability` table; a failure raises.
- current draft (Solver, Reviewer): `{"parsed": {scenario, action, entities}}` when the draft
  validates against the closed draft schema, else `{"raw_text": <source content>}`; for the Planner,
  only `{"source_state_id", "parse_status"}` — **the Planner would see no draft content at all**.
- review finding (Solver, Planner, Perception): the parsed findings report plus citation
  availability, or, on a parse failure, `{"reason": "malformed-review-findings"}` — **which on the
  anchor's prose Reviewer would be 100 % of rows, i.e. the Planner would lose the findings entirely.**

The anchor config does not declare `role_context`. The one flight that did —
`SAEA-SLURP-NATIVE-TYPED-ROLE-CONTEXT-TRAIN-FOLD-A-V1`, 2026-09-16 — aborted after 507 contacts with
no paired quality read (`docs/results/2026-09-16-slurp-two-track-evidence-synthesis.md`, row 1). **The
typed context has therefore never been measured against the anchor on a complete roster.** It is also
mutually exclusive with `history_scope` filtering by validation
(`rails/native_episode_config.py:500`).

The second, working instance is `reproduction/ojw/native_group_solver.py` (E2b, merged): a grouped
Solver visit parses all N sample outputs with `parse_slu_response`, records each as
`parse_status: "ok" | "malformed"`, applies a registered commit policy over the parsed answers only,
and **re-renders the committed answer through a fixed canonical template** (`_default_render_answer`,
`json.dumps(..., sort_keys=True)`). That is parse → declared malformed rule → fixed template → zero
extra contacts, which is exactly the shape the owner asked for. Its gap: the committed text becomes
the delivered, scored answer, but each of the N raw samples is still sealed individually by
`capture_completion`, so a downstream Reviewer would receive all N raw drafts and never the committed
one. The reviewed draft and the delivered draft would differ.

## 10. Two findings that sit beside the node boundary

**(a) The Reviewer's mandated tool re-delivers its own system prompt.** The tool result's
`result.task_contract` is 5,424 characters and is a **literal substring of the 8,118-character
`task_instruction` already in the same request's system message** (verified by substring test on 20
sampled envelopes; the check is in `drivers/dup2.py`). Rendered as a `tool` message it costs 6,243
characters, and it is delivered 2,184 times across the run — **13,634,712 characters, roughly 3.4 M
prompt tokens, about 7.4 % of the run's entire prompt budget, carrying no information the receiving
context did not already hold.** `docs/results/2026-09-16-slurp-review-context-provenance.md` reached
the same duplication from the leakage side; this is its cost side.

**(b) Knowledge, not model text, is what actually grows the context.** The same 20 evidence blocks
(~32,010 chars) are re-sent on every Solver, Reviewer and Planner contact of a row — four to five
times per row. This is a supply-policy question, not a node-context question, and the design spec
keeps it out of scope; it is recorded here so that no one reads "2.17 % upstream model text" as
"the context is already clean".

## 11. Limits

- One run, one roster (TRAIN Fold A, 1,080 rows), one geometry. Nothing here is a quality claim.
- The wire decomposition is a faithful *reconstruction* from the sealed D2 payloads using the
  repository's own rendering functions, not a capture of the rendered bodies, which the trace does
  not retain. Token counts are the sealed COST receipts and are exact; character counts are the
  reconstruction and are exact up to the rendering functions being applied as written.
- `parse_review_findings` and `parse_slu_response` were run offline over sealed response text purely
  to count acceptance; no output was rewritten, scored or persisted.
- The three episodes whose Reviewer skipped its mandated tool call are reported, not diagnosed.
- This audit adds no ledger row: it is a model-free read, not a Stage-2 cell.
