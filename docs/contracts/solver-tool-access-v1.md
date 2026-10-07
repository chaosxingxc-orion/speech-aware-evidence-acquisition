# Prospective Solver slot lookup contract

`native_episode.solver_tool_access = "bounded-slot-lookup-v1"` opts the shared
native executor into one model-selected invocation of the existing
`saea-tool-knowledge-target-lookup-v1` tool. Omit the field to preserve historical
Solver permissions and request rendering. Null, Boolean values and aliases are
invalid. This contract admits an offline-tested capability; it does not register
or authorize an experiment or any model contact.

The opted-in graph is Perception once, Solver at most twice, then accept.
Declare `review_loop = "off"`, zero revisions, Reviewer and Planner iterations
zero, Solver samples one, `tool_iteration_policy = "reserve-final-report"`, and
`tool_schema_rendering = "per-role"`. The total model-contact ceiling is three;
the Solver can answer immediately without a lookup, using two total contacts.
Acquisition, refresh, re-listen, Solver supply variants and Perception branches
are outside this profile. Existing context and output-budget validation applies.

The only phase-tool authority is Solver, with this exact bounded specification:

```json
{
  "solver": {
    "mode": "native-tools",
    "source_authority_role": "solver",
    "allowed_tools": ["saea-tool-knowledge-target-lookup-v1"],
    "knowledge_views": ["text"],
    "knowledge_store_ids": ["slot-contracts"],
    "knowledge_target_axis": "slot-type",
    "knowledge_selection_mode": "targeted",
    "candidate_limit": 2,
    "knowledge_values_per_candidate": 1,
    "knowledge_value_limit": 2,
    "max_calls_per_sample": 1
  }
}
```

`knowledge_value_limit` can instead be one. Bind the existing fixed, released
`slot-contracts` store, authored slot-target index and exposure custodian before
runtime. Calls use the existing canonical arguments: `store_id`, `view`,
`candidate_ids` (one or two unique slot IDs), and a nonempty `distinction`.
Missing fixed-source IDs return an explicit empty result; invalid arguments,
wrong stores, extra calls and out-of-scope abilities are refused before tool
transport. There is no automatic lookup or alternate answerer. The tool result
and custody appear in the final Solver context; the reserved final iteration
has no tools. Only the Solver's deliverable final response reaches the existing
answer contract and scorer. Exhaustion cannot deliver tool-call text as an answer.

## Compiler identity and candidate preparation

For a declared consumption module, place `review_loop = "off"` on the module
block. Add the same `solver_tool_access` field only for the tool arm, and arm
`knowledge-consumption-opportunity` with `mode = "targeted"`,
`store_id = "slot-contracts"` and a prospective `solver_template` path. That
template must explicitly permit the bounded tool contract; the historical seed
instruction prohibiting analytical tools is incompatible with this arm. The
compiler binds these choices in the module hash and emits registered programs
`phase-native-module-v1-c2` (plain) or `phase-native-module-v1-c3` (tool). No
postcompile topology mutation is supported. Historical module blocks are unchanged.

The plain review-off profile preserves the locked Perception and Solver material
unless an explicitly armed component changes it. It also preserves the locked
schema-rendering declaration, including constant mode. The tool profile requires
per-role schemas. Removing globally rendered Reviewer/Planner schemas can change
the Perception request even when its text and evidence are unchanged; candidate
registration must describe and pin those bytes honestly. Keep the historical
system-text verifier strict; a tool profile needs a prospective text bundle with
its own Solver template and explicit per-role node context.

To validate a complete compiled config and obtain active-role/contact geometry:

```python
from speech_aware_evidence_acquisition.rails.controllers import default_phase_program
from speech_aware_evidence_acquisition.rails.native_episode_config import load_native_episode_config

parsed = load_native_episode_config(values, default_phase_program(values["policy"]))
active_roles = tuple(role.role_kind for role in parsed.roles if role.max_iterations > 0)
contact_cap = parsed.max_contacts
```

The loader recompiles a declared module and rejects differing declared values.
Runtime rechecks authority and fixed-store binding before any model request.
File hashes, prospective template text identity, released data identity,
population membership, exposure registration and live service identity remain
explicit caller responsibilities under their existing shared gates.
