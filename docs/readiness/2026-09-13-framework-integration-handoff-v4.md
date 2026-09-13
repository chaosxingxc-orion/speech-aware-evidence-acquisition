# Framework integration handoff v4

Status: progress. The paired GPU campaign and primary scoring/analysis are closed.
The native production speech/tool episode is not yet admitted. Keep the active
research goal open.

## Owner-facing answer

OpenJiuwen already implements conditional Workflow routing, ReAct tool loops,
tool registration/dispatch and conversation history. Use those public APIs.
The remaining defects belong to the repository integration: actual speech and
selected knowledge must reach each request, historical tool evidence must carry
its source authority, and Solver delivery must remain explicit. Do not resume
the paused custom actor controller.

## Closed diagnostic work

The shared distinct-source diagnostic entry now consumes the actual verified
DERIVED source with its ABORTED original attempt and preserves actual candidate
widths one, two and three. Root repaired both actual-source binding and
full-population variable-width aggregation. Root checks: 42 tests and Ruff pass;
the actual model-free diagnostic run succeeds; the engineering base check passes.

Output:
/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/analysis/SAEA-SLURP-DISTINCT-COMMITMENT-PAIRED-ANALYSIS-V1/conditional-diagnostics-v1.json
SHA-256: 9d92ca29f9ae733dbf827979f68e3103f0f9c01f6e3a79d77223f24f1ded83a2.

NEW500: 450 gold-included candidates; hard-first 383 correct intents; joint 397.
Joint partitions the 500 rows into 50 missing gold candidates, 53 covered but
not correctly selected, 236 correct intents with inexact entities, and 161
jointly exact rows. See the conditional-result-v1 report and the unchanged
primary verdict. This locates unresolved stages but does not establish that
semantic knowledge will fix them.

Raw attempt diagnostics need a narrow supplement: the legacy aggregate
out-of-shortlist field parses delivered output, so refused proposals can be
hidden. Read the verified delivery_diagnostics flags instead. Hubble is adding
that shared CLI extension in an isolated tree from 33d8db2f. Preserve v1 output;
write any extended result to a new path.

## Future integration checkout

/home/chao/saea-worktrees/native-agentic-system-integration-v1

Current code HEAD: e8730cdd51865c517e47a6e5525283cdade0581e.

Integrated after f2cf6799:
- 1321f545 / fde6e050: registered semantic preparation with governed A/B and DEV
  forbidden-roster readers. Root semantic/knowledge tests: 220 pass.
- 5dd9656e: native bounded conditional episode from original 274fe4df. Uses
  public Workflow and BranchRouter; independent and root reviews found no
  concrete routing/authority defect. Revision and acquisition edges forward
  state; only accepted valid Solver output delivers.
- 63c55698: source-bound reversible null assistant content from original
  bcc3e344. Projection maps source null to framework empty; restoration uses
  the preserved completion and exact OpenJiuwen serialization. Original wire
  bytes, empty string and structured content remain distinct. Helpers are not
  standalone authorization; the caller must choose a source-bound completion.

No model generation has run on this integration version. Do not substitute it
for the frozen campaign checkout or claim that graph/helper tests prove a
production multimodal loop.

## Source-authority review closed

Herschel replaced original 7273fd59 with 9496eb1884d569f158aa563b4e13a9bfc2f7df8f
after root review. The replacement is integrated as e8730cdd in the future
checkout. The full dispatcher union is now narrowed by the actual ordered
completion.tool_names and checked against the complete selected schema hash.
The validator also requires finish_reason=tool_calls and retains structured,
string and null assistant content.

A real shared dispatcher/custodian synthetic test registers two tools,
advertises one to Reviewer, then projects the counted result into a tool-free
Solver request. Root integrated authority/dispatcher/history/role/episode
checks: 89 pass. This closes the source-scope seam; it still does not close the
full framework-message-to-speech callback described below.

## Next root-owned integration

Finish the production MeteredRoleRequest callback, not another framework:
bind the registered role prompt and actual original query; preserve the full
framework message sequence; validate assistant history against metered
CoreCompletion receipts and tool messages against counted source-bound
observations; project through the existing shared speech request and transport.
Do not flatten or ignore the framework's later messages. Use the same
prepare/send path for actual capacity and generation requests.

Current legacy native history can reproduce counted tool exchanges, but this
alone does not bind arbitrary complete ReAct history. The current
NativeRoleModelRequest callback remains the missing production seam.
SLURP prepared features are the first target. Raw E21 is a separate carrier
proof and is not covered automatically.

In parallel, register actual semantic-source authoring before reading TRAIN
content; then author independent intent-boundary and slot-explanation stores
from the governed A/B-excluded pool. The preparation machinery is implemented,
but no new semantic release or production store config exists yet.

## Serving state

The original root-owned decoder service remains resident, with no mmproj:
serving-slurp-top3-commitment-np8-v1, PID 102694, port 8080, eight slots.
Latest inspected monitor at 10:00:47 UTC on 2026-09-13 reports healthy, eight idle
slots, zero GPU utilization and 21,264 MiB allocated. This is a waiting interval,
not effective generation. Do not restart or add unregistered contacts merely
to occupy the GPU. Keep the ten-second monitor alive.

No active generation or official scorer remains in flight. Preserve frozen
campaign code c4e7bb1f, all raw runs, scoring receipts and resident service.
