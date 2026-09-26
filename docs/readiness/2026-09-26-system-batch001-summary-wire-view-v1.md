# Compact complete-system summary input

The original 16 internal-envelope summaries measured 57386--99721 input tokens
and all failed a 24576-token slot. A smaller actor update batch does not solve
this single-trajectory bottleneck.

This successor uses exact original fitted model request bodies rather than
duplicating framework custody envelopes. It retains all original role contacts,
normalized responses, untouched wire-response text, actual tool records, their
order, control routes, interrupted responses, fallbacks and delivered answers.
No source episode, knowledge text or model-visible history is selected away.
Repeated JSON subtrees share short local references, with reserved-key escaping
and exact reconstruction. This is lossless sharing of the declared wire view,
not a claim that every non-model internal field remains in the summary prompt.

Internal envelopes, raw traces and their provenance remain immutable. Every
archived request body must match the original native-contact fit hash; each fit
must bind the original input boundary and complete source roster. Original
flight receipts bind the finalized actor manifest and source configuration.
Archive loading is offline: the old service need not remain alive. A former
role's tool-result claim remains ordinary response text, not an actual tool
event. Original episode hashes remain the downstream feedback/summary join.

Use the shared prepare_actor_wire_requests API with the normal transport's
render_request method, then the existing rails.system_summary_context entry
point with a saea-system-summary-source-v2 binding. The new baseline is
system-trajectory-summary-wire-text-v1. There is no additional controller,
executor, serving process or scorer. Historical v1 bindings retain their
original representation.

Preparation reconstructed 67 original fitted requests and 16 whole episodes
with no POST, scoring, encoding or semantic generation. Compact model contexts
occupy 47800--75413 UTF-8 bytes. Bytes are not capacity evidence. The registered
successor measures every actual shared-executor payload on the same two-slot
decoder-only service, preserving output2048, special2 and reserve3072. It admits
no generation. Record both physical fit and the stricter operational margin.

Validation: 49 tests passed, including exact JSON reconstruction and reserved
keys, missing/cyclic references, actual tool versus response preservation,
interrupted/abstaining episodes, offline source rebuilding, archive/fit
tampering, default summary compatibility and the shared fit/send path.
