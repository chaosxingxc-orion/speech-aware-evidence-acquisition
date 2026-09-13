# Audio2Tool: native role reuse and task-contract audit

Date: September 13, 2026. Source checkout: d1c0c851dd3050ab24b6f9bf9b74e65520cb3f8c.

## Scope and decision

Keep the direct frozen-model call versus a complete agentic system as the task comparison.
Expand the system after its predecessor's result identifies a useful capability boundary.
Keep Audio2Tool in the architecture, with SLURP first in the live queue.

This source and frozen media-metadata audit reads no current SLURP answer, quality
result or trajectory. It adds no model, encoder, ASR or scorer invocation and
admits no Audio2Tool flight. Root reviewed the actual configured factory path
after an initial generic-adapter inventory proved insufficient.

Reuse the existing four-role executor and media-roster interfaces. Do not build
another controller, change the generic loader or add a new scorer based on this
audit. Carrier-specific configuration and bounded execution proof remain needed.

## What the closed experiment actually exercised

The [closed result](2026-09-12-a2t-native-system-final-result-v1.md) concerns direct,
fixed plan/solve, and plan/solve with fixed knowledge supply. The recovery baseline
selects phase-task-tools-then-solve-v1 and a fixed saea-tool-phase-knowledge-v1
action. It does not declare native_episode. Its name's use of "native" refers to
task alignment, not proof of the newer four-role graph or selective tools.

Preserve that experiment's negative or unresolved verdict and sealed bytes.
Its format, interface and per-tier observations can motivate a successor but do
not establish a single cause of the result.

## Verified reuse map

| Requirement | Existing path | Remaining task-specific work |
|---|---|---|
| Same runtime for direct and system | core/flight/factory.py, core/flight/runtime.py, rails/runner.py | Configure direct-only and the generic native role program |
| Role authority and bounded continuation | rails/native_episode_config.py | Bind four roles, contact limits and analytical tools only to Reviewer/Planner |
| Sole answer authority | Native runner's source-bound Solver delivery | Preserve the selected final delivery contract across arms |
| Full tool task contract | rails/adapters/audio2tool_runtime.py and active instruction | Separate task-target tools from callable analytical tools |
| Frozen media population | data/audio2tool_runtime_roster.py, rails/adapters/audio2tool_runtime.py | Bind the media-only roster and audio identities |
| Complete dialogue preparation | data/audio2tool_dialogue.py | If admitted, verify chronological audio, derivation receipts and a new runtime roster |
| Multiple calls | rails/a2t_response_schema.py | Bind call count to the task; its default of four is not an established dataset bound |
| Standard and ordered scoring | Registered a2t-toolcall-official, a2t-toolcall-v2, a2t-toolcall | Score the complete manifest once and reuse saved row statistics |

The native graph is implemented and covered by synthetic runner tests. No
Audio2Tool baseline declares that graph at this commit. Real Audio2Tool
native-role execution and quality improvement remain unproven.

## Correct media-path interpretation

The factory registers Audio2ToolRuntimeAdapter. Its builder reads the pinned
roster's media fields, constructs samples and returns them from a split-locked
load_split. It does not use the generic adapter's media-selection path.

The closed audio2tool-org1-union-4000 fragment explicitly inherits the official
population's FIRST-user-turn rule for Tier 7. Root verified the configured roster
SHA-256 e5a81b71e1253ff866262991f79d132b89f4bfb47e7c8a0c0cf0aa04857b8736.
All 500 Tier-7 rows among its 4,000 media-only rows use turn_00_user_ paths.
The generic loader's final-turn behavior therefore does not describe this flight.
Neither path supplies complete dialogue.

For a future complete-dialogue task question, use the existing materializer and
runtime adapter's declared derived-media root. Bind source turns, derived audio,
packet identities and capacity before contact. Give direct and system the same
lawful dialogue input when estimating system benefit. Explicitly report the
input difference from historical official-protocol results; do not attribute
added context to agent control or rewrite the historical media binding.

## Preserve the eight task forms

| Task form | Information the system must preserve |
|---|---|
| Direct request | Requested operation, with no invented actions or unspoken arguments |
| Parametric request | Spoken argument meaning, value form and evidence |
| Multiple intents | Every supported action, including repeated tools and request order |
| Implicit intent | Desired end state and discriminative activation conditions |
| Embedded request | Actionable request distinguished from unrelated narrative |
| Correction | Final active intent/values and the superseded earlier state |
| Multiple turns | Prior lawful dialogue needed to resolve the current request |
| Blended intent | Decomposition into supported ordered calls |

These are task-contract requirements, not measured capabilities of the closed
system. Do not copy SLURP's mutually exclusive Top-3 intent state into a
multi-action task. Alternative hypotheses within an action and multiple requested
actions are different objects. A task-specific candidate provider is needed only
if the successor selects that mechanism; the generic graph can consume the full
legal task contract first.

Separate tool activation knowledge from parameter meaning and extraction
knowledge. The [native value audit](2026-09-12-a2t-native-value-and-query-assembly.md)
distinguishes public declarations, construction-supported native forms and
benchmark extraction targets. Do not require all public parameters, copy example
values or treat observed key sets as exhaustive constraints. The historical
active prompt uses call strings; the generic adapter's JSON-array default must
not silently replace that configured contract.

## Scoring and claim limits

The already-registered a2t-toolcall-v2 compares tool-name sequences position by
position and reports ordered tool accuracy. An additional ordered validator is
not automatically needed. Its exact match deliberately remains multiset-based
after documented normalization. Ordered tool accuracy does not establish
argument-to-occurrence correctness or successful dependency execution.

Use existing metric names and semantics. Add a diagnostic only for a registered
claim those metrics cannot resolve. Audio2Tool target calls are predictions, not
evidence of actual smart-device side effects.

## Next execution boundary

Complete the current SLURP generation and paired analysis. Select its successor
from candidate coverage, joint selection, spoken-value errors and revision
behavior. Keep source-only Audio2Tool preparation parallel.

Before an Audio2Tool native-role successor is admitted, freeze its task contract,
media choice, output form, knowledge versions, role/tool limits, comparison roster
and metrics. Reuse existing interfaces for bounded proof and full execution.
Do not reopen the closed recovery, assume complete-dialogue execution is already
admitted, or implement every possible capability in advance.
