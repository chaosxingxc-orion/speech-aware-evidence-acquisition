# Bounded proposer transport: implementation and admission boundary

Status: implemented and proved against a local synthetic HTTP/SSE server. No
live proposer has been admitted or contacted by this package. This is an
extension of the existing system-text proposal path, not a new task executor.

The [proof receipt](../../receipts/continuation/2026-10-01-system-text-proposer-responses.json)
pins the source, tests and raw local wire evidence. The related suite passes127
tests, including44 transport tests; transport statement coverage is100%. The
end-to-end fixture sends two real loopback HTTP requests: request an indexed
artifact, receive its verified page, then return a synthetic proposal. It makes
zero external model contacts, reads no account credentials and produces no
research candidate. The fixture is not a provider compatibility proof.

## Implemented behavior

`rails.system_proposer_responses.ResponsesProposer` runs inside the existing
`ProposalDispatch` one-shot reservation. It constructs each continuation from
the pinned initial context, validated model output and the registered artifact
broker's response. Only `read_artifact` is executable. Shell requests, new tool
declarations, new message roles, duplicate calls, refusals and unsupported output
types stop the allocation. No hidden history, skills, host file access or tool
namespace is added by this client.

Save the outgoing request and contact reservation before contacting the provider.
Require the coordinator's contact-registration callback before opening the
socket. Preserve received SSE bytes, parsed events and provider usage before
interpreting them. After malformed input, preserve the received prefix and close
the stream; do not drain an unbounded peer. A disconnect without final usage is
an unmetered contact, never zero consumption. Known usage remains recorded.

Use one POST per registered contact. Do not follow redirects, use environment
proxies, retry HTTP/auth/stream failures, refresh credentials implicitly, or
resume a consumed proposal. Keep credentials in the authentication callback and
HTTP header only; exclude them from payloads, artifacts, receipts and errors.
Literal unauthenticated loopback is the only fixture destination. Live access
requires a separately verified endpoint/model/protocol admission and an explicit
credential callback; there is no account discovery or paid API default.

Require a separately admitted, model-free full-request input meter. Check its
bound before each contact and verify it against reported usage. Decrease the
provider output limit by cumulative output usage, including tool turns. Bound
the request count separately from candidate opportunities. The caller must bind
these limits, the meter and provider profile to the preregistered proposal plan;
constructing a client or supplying a self-consistent hash is not authorization.
No public live-dispatch command has been enabled before that integration.

## Open compatibility decision

OpenAI's [ChatGPT plan limitations](https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations)
currently exclude `max_output_tokens`. Therefore this profile cannot implement
the registered server-enforced output bound. The adapter retains that bound and
refuses the known incompatible profile. It does not silently omit the limit.
The previous installed-client audit also remains valid: the tested Codex profile
inserted extra context/tools. A subscription login alone proves neither exact
context isolation nor compatibility with this transport.

Root has asked the owner whether to permit a separate, uniformly applied
subscription profile with equal declared limits/targets, complete actual usage
reporting and consumed-but-rejected over-budget or unmetered proposals. That
would not establish equal realized compute or a hard generation cap. Until an
answer is recorded, keep the existing hard-bound protocol unchanged. Do not
assume that cancellation bounds hidden reasoning tokens or server computation.
The alternative is to retain the hard bound and await a compatible zero-spend
provider. No paid route or borrowing of another application's OAuth token is
authorized by this proposal.

## Remaining work before real proposals

Qualify both initial seed/A/A members and countersign their exact READ row before
exporting feedback. Resolve the provider-bound question, pin the exact available
model and an authenticated zero-paid-spend route, register the full-request
meter and per-proposal contact allocation, then prove the chosen provider path
with its own pre-contact registration. Reuse the same admitted settings for L/B.
Keep raw invalid outputs and charge their original candidate slots. Do not let
any milestone test feedback enter these inputs.

The broader gates pass except for the already reported empty operator labels in
the two frozen native-capacity fragments. Their bytes were not changed and the
gate was not waived. This transport proof does not resolve that separate
annotation defect, activate an experiment, or change the current GPU queue.
