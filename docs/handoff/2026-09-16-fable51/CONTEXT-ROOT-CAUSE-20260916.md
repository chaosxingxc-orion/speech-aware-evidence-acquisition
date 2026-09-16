# Follow-up root diagnosis: repeated knowledge bodies across request surfaces

Date: 2026-09-16. Root scientific/engineering interpretation by Codex.
Supersede only the earlier uncertainty about which tool content grew the request.
The flight remains CLOSED_SECOND_FAILURE_NO_FURTHER_RECOVERY. No task-quality result
or new GPU admission is created. No actual Fable takeover was recorded when this
bounded follow-up began.

## Established evidence

The failed episode made two Reviewer calls to the same registered target-knowledge
lookup. Both tool selections had supply_disposition=already-visible and zero new
values. Exact evidence-ID and content matching gives:

| Return | Selected blocks | New values | Body bytes already present in the initial Reviewer input | Model tool-message content bytes |
| --- | ---: | ---: | ---: | ---: |
| First lookup | 3 | 0 | 2,165 | 3,486 |
| Second lookup | 21 | 0 | 38,938 | 46,231 |

These are UTF-8 bytes, not tokens. The 21 second-return blocks account for the same
38,938 bytes previously added between Perception and Solver: initial supplied
knowledge grows from 5,873 to 44,811 bytes. No semantic contents, task labels,
transcripts, answers or reference text were displayed or evaluated by this audit.

The recorded Reviewer request after the first lookup was projected through the
existing pure shared feature/history functions. All three returned blocks appear
both in the base user evidence and in the tool message. Their full evidence IDs
and content match, not merely their lengths.

For the second return, all 21 blocks match the initial Reviewer's supplied evidence.
The model-facing tool message was reconstructed through the actual model-result
field filter and native_tool_result_message, with no tool or model execution.
The same reconstruction for the first return exactly equals its recorded framework
tool message. Thus the second return's 46,231-byte tool message is source-bound;
it contains 38,938 bytes of already-present knowledge body.

The existing numeric fit receipts show Reviewer text tokens 13,024 -> 13,960 ->
24,299. The last increase is 10,339 text tokens; the final request requires 24,878
tokens in a 24,576-token slot. The guard refuses it before generation.

## What this establishes, and what it does not

The named avoidable mechanism is repeated knowledge serialization across the base
evidence surface and the native tool-return surface. It is not the already-fixed
missing-observation issue. It does not require a new retrieval algorithm to explain.

The rejected final request payload was not recorded as a MODEL_REQUEST. Its exact
full wire hash has not been independently reconstructed. Do not claim a measured
token saving, an exact allocation of every token of the last increase, or that an
unimplemented deduplication policy has passed actual capacity. Other messages and
tool definitions also participate in a request. Bytes are not a tokenizer result.

This is a structural diagnosis on the failure-selected episode, not an estimate of
how often duplication occurs across the cohort and not a task-effectiveness analysis.
The current complete paired-quality release is still unavailable. The old positive
SLURP base remains the usable research anchor.

## The shared source chain

All source locations below refer to frozen commit
9bf27b28708bb93607138e7bcd1eacb66eab3f08, under
/home/chao/saea-worktrees/slurp-typed-context-full-recovery-v1/.
The prefix is src/speech_aware_evidence_acquisition/.

1. rails/knowledge_target_lookup.py:146-238 distinguishes selected, new and
   already-visible values. Repeated selection correctly creates no new supply.
2. rails/phase_tools.py:1244-1303 retains all selected IDs in the result.
   Lines 921-942 serialize full selected native evidence even when supply is absent;
   lines 943-957 make the smaller model-result metadata object.
3. rails/runner.py:2049-2079 settles each tool before the next same-role contact.
   Lines 1696-1754 advance the state; 1688-1694 rebuild the base messages.
4. rails/phase_tools.py:1327-1420 rerenders retained QueryState knowledge.
   Avoiding a second state insertion therefore does not avoid a second wire copy.
5. core/model/native_framework_history.py:227-290 removes duplicate local
   assistant/tool agent-state records, then appends their canonical framework turns.
   It does not remove matching knowledge from the base user evidence.
6. core/preparation_fit.py:1185-1331 checks the realized request and correctly
   rejects an overflow. This is a final guard, not a policy that bounds prior
   tool-result growth or reserves a valid continuation.

The existing history tests establish one copy of each assistant/tool history turn.
They do not establish one copy of each knowledge body across user and tool messages.
In particular tests/unit/test_native_framework_history.py:45-58 and
tests/unit/test_native_target_knowledge_tools.py:283-361 do not cover this cross-surface
invariant. The latter file's repeated-lookup unit case confirms no new supply while
the native result still contains selected blocks.

## Root recommendation: represent selection without copying an existing body

A lookup can still convey useful attention or selection information when it discovers
no new knowledge body. Do not suppress the call/result or declare it useless merely
because new_value_count is zero. Preserve what was requested, which values were
selected, missing mappings, source identities and the outcome of the lookup.

The next shared interface should distinguish canonical custody from model-visible
placement. Keep the complete original tool observation and its source hashes.
For each realized request, assign one authoritative visible body to each exact
(evidence ID, source URI, content hash) identity.

My preferred first implementation is an explicit opt-in request projection:

- Preserve the existing base evidence ordering and contents.
- Validate original source-bound assistant/tool groups before projecting anything.
- Where a tool-return body exactly matches evidence visible in that same request,
  return an explicit reference to that visible body, retaining selection metadata.
- Where no matching body is visible, retain the complete tool-return evidence.
  An earlier visit, a state-store ID or an already-visible selection flag alone is
  insufficient proof that this request contains the body.
- Preserve all actual call IDs and one result for every call, including rejected
  batches. Do not merge independent observations merely because text happens to match.
- Bind the policy, complete source observation, rendered projection and placement
  decisions in a receipt. Preserve historical/default request semantics unchanged.

This minimizes scope: it changes placement of identical content without selecting
different cards, rewriting their semantic content, expanding candidates, adding a
model role or moving final answer authority. It still changes model-visible requests;
it is a new system version, not a byte-equivalent repair or third recovery.

References must be intelligible to the model, not opaque hashes alone. Evidence IDs
identify the visible body; hashes/source identities provide custody. Content not
visible to a role cannot be replaced with an unresolvable reference.

## Bounded implementation and validation sequence

1. Implement the shared opt-in projection at the existing native request/history
   boundary. Reuse registered policy/config plumbing; introduce no experiment runner.
2. Add synthetic tests for retained base + repeated tool evidence, new evidence,
   repeated calls, multiple/rejected call groups, same text with distinct sources,
   ID/content/source conflicts, role-filtered absence, raw/feature speech paths,
   and unchanged historical defaults. Verify no source observation is modified.
3. Use the two recorded Reviewer request shapes and the source-bound second return
   for CPU structural verification. Display counts/hashes only. Do not score or
   reconstruct a successful experimental run from the failed prefix.
4. Address genuinely new large returns separately through prospective continuation
   admission. Single-copy rendering alone does not guarantee every future request
   fits. Keep exact actual-request checks; do not catch every capacity error and
   silently accept an unreviewed answer.
5. Once implementation and the bounded proof design are concrete, register any new
   tokenizer/engineering contacts with the full output reserve and unchanged
   comparison geometry. A four-row proof validates engineering only. A distinct
   complete experiment needs its own justified comparison and admission.

Do not sweep arbitrary text caps, truncate full values or lower max512 to make this
episode fit. Candidate-specific semantic projection remains a separate later scientific
mechanism; mixing it into this exact-duplicate placement change would obscure what changed.

## Expected benefit and contrary outcomes

The immediate expectation is less avoidable context growth and a usable continuation
after a repeated lookup. It is not a promised accuracy gain. Removing repetition may
also remove an accidental emphasis effect, or references may be harder to consume.
Whole-task quality and saves/harms still decide whether a later complete system advances.

A meaningful result would be: canonical tool observations and role-visible information
remain accounted for; actual capacity succeeds under a prospectively admitted design;
and complete task performance is preserved or improves. Smaller requests alone are
engineering evidence. They do not demonstrate training-free RL or Reviewer effectiveness.

## Audit recipe and custody

The metadata-only audit was registered before trace inspection. It selected only the
sample named by the failed FIT receipt, never by its task correctness.

Read MODEL_REQUEST.payload.payload for the four completed contacts, and USE result
records for the two target lookups. Extract roles, counts, lengths, exact ID/content
equality and hashes only. Reconstruct feature content using
_ordered_speech_feature_content, _speech_history_texts and
project_native_framework_history. For tool messages apply the exact
phase_tools.py:943-957 field filter and native_tool_result_message. Do not run a
FlightRuntime, tokenizer, model service, scorer, semantic answer parser or task metric.

DATA/coordination/slurp-typed-context-vs-direct-v1/ contains:

- root-capacity-structure-audit-registration-v1.json:
  7b5a5560cfcb490c0934dc372ebb126a63bbd8786d4be580680e8586fd1a6b8a.
- root-failed-episode-trace-structure-v1.json:
  45c497d8da47e36ab071e107fa9f21e73031c27195c3ac60f3072a701284e55d.
- root-failed-episode-request-structure-v1.json:
  663d9b69640b5a3262abc4030711a58b33bf5f139f23176812e8565306e70394.
- root-target-knowledge-duplication-audit-v2.json:
  7526c5f8d548dc7fd13cb8323b101a7e798f26cdcbd40d14979c0d7024ba473c.

The preserved v1 duplication receipt serialized full audit metadata when calculating
its native_tool_result_bytes field. That field is not actual model-message size.
V2 explicitly corrects this using the production model-result filter; the evidence
identity/byte-duplication findings are unchanged. Never rewrite the old receipt.

The trace itself, source files and their hashes are bound in the v2 receipt.
This follow-up parsed raw trace records programmatically for structural metadata;
it does not claim no trace access. No task-quality read or new model/tool contact
occurred. The frozen run, service, lease and old handoff records were not changed.
