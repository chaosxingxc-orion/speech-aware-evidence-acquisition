# Offline proposer continuation capacity audit

Owner scope:214/217. This implements a prospective engineering check, not a new
proposal allocation, provider admission, scientific update or retry.

## Problem and implementation

The initial request fitting its allocation does not establish that a later tool
turn fits. The proposer retains whole response items, tool results and earlier
context; each subsequent request must also fit the remaining cumulative budget.

`rails/system_proposer_capacity.py` reconstructs an explicit assumed continuation
using the production capsule request builder, output validator and registered
artifact broker. It retains reasoning and all previous tool turns. It checks the
initial request and the request after every specified read, with the unchanged
full serialized UTF-8 byte bound plus4096 reserve. It reports request hashes,
remaining budgets, margins, artifact response hashes and the first failing contact.
The original capsule, access log, provider transport and launcher remain unchanged.

The checker uses a private restored capsule and neither constructs an HTTP client
nor reserves an opportunity. It never reads an arbitrary path requested by a model.
Unknown artifacts, malformed/duplicate/parallel calls, invalid pages, unexpected
scenario fields and impossible usage assumptions are rejected by the shared gates.
It cannot add learning feedback to a blind capsule.

## Interface

Use `scripts/checks/system_text_proposer_capacity_check.py` with `--capsule`,
`--capsule-sha256`, `--scenario`, `--scenario-sha256`, and `--report`. Both input
files must match their hashes. The report is create-only. Exit0 means only that
the covered requests fit; exit2 means the explicit scenario exceeds a budget.

The scenario schema is `saea-proposer-capacity-scenario-v1`. Declare `contact_cap`
from1to4 and a `turns` array shorter than that cap, preserving a following request
slot. Each turn contains exactly `output` (the complete assumed Responses output
items requesting one registered artifact), `assumed_input_tokens`, and
`assumed_output_tokens`. No provider usage is inferred from text length.

The report explicitly labels usage as assumed, actual contacts as0, and dispatch
authority as false. Scenarios do not establish the registered contact cap; the
actual admission remains responsible for binding the capsule and protocol.

## Validation and actual-size evidence

The first test run failed because the new audit module did not exist. After
implementation,168 related tests pass, including28 new tests. Scoped statement
coverage is100% for the audit module and97% for the CLI,99% combined. Ruff,
engineering-base and harness-admission checks pass. Four hard-budget branch/profile
combinations and a three-request subscription sequence match the production
transport's request hashes through the real local HTTP/SSE fixture. The CLI also
runs in a subprocess and refuses changed inputs and existing reports.

Only the already root-READ initial400 family was used for actual-size scenarios.
No update1 answer, quality result or partial feedback was read. Evidence is under
`SPEECHRL_DATA_DIR/coordination/system-text-proposer-capacity-engineering-v1`:

| Explicit assumed path | Request bounds | Result |
| --- | --- | --- |
| L, prior largest-brief two-page path |17044,19237,21420| third request exceeds remaining21374 by46 |
| L, one complete brief |17044,20482| second request fits assumed remaining28366 |
| B, initial request only |14538| fits32768; later turns unassessed |

The two-page reconstruction matches both previous hypothetical request hashes
exactly. The one-page scenario uses its own explicit call identity and therefore
does not claim equality to the earlier one-page proof. Assumed usage4402/6992
input and65/64 output comes from the prior recorded envelope; it is not a new
provider observation. Neither scenario repairs or replaces spent round-one slots.

## Remaining boundary

This check demonstrates the enumerated path only. Different model choices,
reasoning lengths, actual usage, final proposal length and additional reads remain
unknown. Even a passing scenario does not promise a completed proposal. The runtime
continues checking every actual request and metered completion against the original
limits. Admit exact round-two L/B capsules only after update1's complete-family
READ and their own isolation, version and capacity review. No budget, scientific
policy, provider model, source exposure or held-carrier permission changes here.
