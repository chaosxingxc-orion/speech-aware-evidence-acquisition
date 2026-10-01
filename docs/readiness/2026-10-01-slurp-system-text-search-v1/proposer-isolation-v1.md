# System-text proposer input isolation: model-free implementation and client audit

Recorded by ChatGPT root on 2026-10-01. Owner214/215 authorizes implementation;
this note grants no new model contact, dataset read, proposal, or flight admission.
The initial CONTROL2 seed/A/A campaign remains on its frozen worker. All search
updates wait for the complete initial feedback family and an admitted proposer.

## Implemented boundary

`rails.system_proposer_capsule` extends the existing proposal input/archive path.
It snapshots typed, hash-bound English artifacts and exposes character pages by
opaque artifact ID. The broker has no path, shell, network, repository, or chat
access operation. Both branches use the same interface and limits. It records
every supplied page and every denied request, with response hashes. All cases
remain addressable; packaging does not select success cases or discard failures.

The blind packet permits only the frozen seed and its registered knowledge
artifacts. Feedback, complementary policies, history and undeclared fields are
rejected before any artifact is opened. The learning packet indexes its complete
own-branch feedback, traces, terminal deliveries and earlier L input/response/
disposition records. Earlier packets are verified recursively, with decreasing
round numbers. Other-branch feedback, test IDs, changed hashes, path traversal,
symlinks and hardlinks are refused. Removing knowledge does not remove source
ancestry: the existing proposal/source compiler remains authoritative.

The `proposal-capsule` command in `scripts/system_text_search.py` revalidates the
current complete family through the existing reader before packaging L feedback.
It checks the frozen protocol and model binding and creates a new archive record;
it never invokes a proposer. Use `protocol-control-v2.json` (and its eventual
explicitly pinned successor), whose seed is the corrected CONTROL2 bundle
`6c5717d2cf8d88da38216cf24f6880b184cb977e0d0000726c5b0f02e606737b`.
The original `protocol.json` and original seed remain historical bytes.

The custody primitive reserves an allocation, a sequence-wide model identity and
a fresh session before entering an injected transport. A failed transport cannot
reuse that opportunity. Exact responses remain saved even when model identity or
metering fails. Compatible receipts join the existing import/compile path; no
proposal is repaired, activated, or replaced automatically.

`attest_outbound` requires exact equality of the actual outbound request with the
registered request, including input, nested tool declarations, model, instructions
and limits. A real adapter must call it at egress, before every send, including
after artifact calls. Inspecting a command line or trusting a prompt is insufficient.
No live transport is supplied by this implementation. Its callback is tested with
synthetic responses only. Provider compatibility, contact registration, token
accounting and output-limit enforcement remain prerequisites, not assumed facts.

The original in-memory path caps one artifact at128MiB and a capsule at256MiB.
The [streaming successor](complete-feedback-streaming-v1.md) adds lossless,
hash-bound chunk storage and is now the CLI default. Both paths expose identical
model inputs and pages. These are packaging choices, not scientific budgets;
silently clipping traces or selecting favorable cases is forbidden. Initial
feedback is indexed rather than inserted wholesale into the first context.
Actual token limits must cover the full proposer conversation, including tool
responses, before admission.

## Installed-client result

The installed Codex0.159.2 executable was exercised through a local synthetic
Responses endpoint using a fresh empty profile, fresh ephemeral thread, no
environments, a sanitized process environment, no authentication, disabled common
tools/plugins/hooks/memory, disabled project documents, and one declared artifact
tool. The endpoint returned a constant synthetic completion; no remote model,
dataset task, research proposal, or paid API was contacted.

The actual request did **not** equal the registered input contract. It contained
an automatically attached skill catalog and additional tool declarations in
`input` entries of type `additional_tools`, while the requested output cap was
absent. Looking only at the top-level `tools` key would miss this: that key was
absent. The audit does not claim that a file was read or an extra tool executed;
it demonstrates that this tested client profile does not meet the experiment's
context/tool/limit contract. Fresh-session and read-only flags alone do not prove
the required blind-input isolation.

The direct installed-client profile is therefore **not admitted**. The next
implementation must enforce the exact request and artifact-only response loop
through a compatible, subscription-backed transport, preserve actual model and
usage receipts, and pass the same synthetic egress audit before any registered
proposal. No API-key spend is authorized. A bundled `gpt-6-sol` label is a candidate
identifier, not proof of account access or an immutable backend weight revision.
The protocol's actual proposer pin remains unset until this is resolved.

## Evidence and validation

- 36 new unit cases and6 lifecycle integration cases pass, with99% statement
  coverage for the capsule module. The complete related search test selection
  passes83 cases. All are model-free and carry no benefit claim.
- The repeatable host fixture is
  `scripts/checks/system_text_proposer_transport_audit.py`. It accepts only its
  fixed synthetic input and writes raw request/events outside Git.
- The raw proof is under data-root
  `coordination/system-text-proposer-isolation-v1/synthetic-client-proof-1/`.
  Its compact report is linked from the continuation receipt. Authentication
  headers were absent; header values are never retained by the fixture.
- The first Windows invocation stopped during import because that interpreter
  lacked a study dependency. No endpoint or attempt was created. The host audit
  now uses the standard library and a contract exported by the WSL study module;
  the study runtime and GPU environment were not modified.

Keep both completed milestones and failed historical artifacts outside optimizer
inputs. Preserve all held lines and the frozen running worker. No owner decision
is requested by this offline engineering result.

The broader Stage-3 algorithm-label gate still reports empty operator lists in
two frozen native-capacity registrations. This predates the proposer change;
the original bytes and the failing gate remain intact. Other listed gates pass
with their existing advisories. See the continuation receipt for exact findings.
