# Shared native feedback portability: Audio2Tool numeric join

Status: offline engineering implemented; no carrier experiment or policy admitted.
This advances the owner's cross-carrier engineering goal without expanding the
SLURP-only system-text search registered under decision214.

## Missing connection and implementation

The existing reward-link and group-feedback readers accepted SLURP and Earnings
native scores but rejected Audio2Tool. Reuse those readers, their complete bundle
verification, saved-score receipt, exact construction cohort, terminal response
identity, and role/tool custody. Do not add another executor or feedback framework.

`a2t-toolcall-official` now has an explicit numeric projection. It retains primary
tool correctness, whole-call exact match, parameter exact match/precision/recall/F1,
parameter counts, parse success, and the official multi-tool metrics with their
applicability and expected-tool count. Preserve the official first-call protocol;
do not substitute either older repository scorer. Convert only named official
boolean fields to numeric indicators. Refuse nonfinite values, invalid domains,
missing fields, inconsistent count identities, answer strings and nonquality fields.

The group reader centers each quality dimension independently. It does not merge
tool and parameter objectives into a scalar reward, and it does not interpret a
relative outcome as a node's causal effect or a policy gradient. On single-tool
samples, the official scorer's inapplicable multi-tool zeroes remain in the saved
counts but are omitted from the quality vector. Cost retains its separate existing
path. The official empty-parameter convention is preserved even on an unparsed
response: parameter F1 alone is not a successful system outcome.

## Evidence and limits

Test-first proof: before implementation, the Audio2Tool projection was absent and
the new tests failed. The integrated test then constructs complete synthetic native
role traces, verifies real bundle/receipt custody, invokes the existing official
scorer only against the repository's synthetic Audio2Tool fixture, writes and warm
reverifies reward artifacts, and pairs both candidates through the shared group
reader. It retains a correct-tool/incorrect-parameter contrast, empty gold parameter
cases, unparsed answers, and multi-tool applicability. It also rejects evaluation
rosters, non-discovery sources, mismatched scorers and malformed numeric feedback.

Validation: 240 tests passed, one skipped because the external pinned clone was not
available in the deliberately data-isolated test environment. The vendored official
metrics identity test passed. Coverage over both changed production readers is91%.
Existing SLURP feedback/CLI and Audio2Tool/E21/E22 runtime adapter tests passed.
Engineering-base, tool-catalog and derived-media confinement gates passed.

No real data, task quality, model, network, tokenizer, GPU or production scorer was
contacted. No frozen scorer bytes, runtime prompt, policy, queue or held registration
changed. A capability in a library is not authorization to read an existing run.

The decision214 `CompleteSystemFeedback` entry still refuses non-SLURP sources;
this refusal has an explicit regression test. Its bundle compiler, source ancestry
and construction release remain registered for SLURP slot knowledge. Cross-carrier
system-text optimization still needs carrier-specific policy/knowledge surfaces,
governed construction cohorts, exact registrations, capacity proof and full-system
validation. E22 still lacks an admitted consumption profile and own null. The new
numeric join proves neither those missing pieces nor a transferable quality gain.

Keep P-SV-4 and the Audio2Tool/E21 GPU holds. Preserve the CONTROL2 scoring failure,
pending owner216 recovery disposition and proposer budget/admission decision.
