# Audio2Tool semantic AgentLoop 104 v1 preprocessing preregistration

Date: 2026-09-03. Status: **REGISTERED BEFORE CONTACT**.
Experiment: `SAEA-SN-A2T-SEMANTIC-AGENTLOOP-104-PREPROCESS`.
Execution profile: `bounded-discovery-probe`.
Composed-config and protocol SHA-256:
`459e92147accb07c721d93a9cd029633a4b55a83324b870b96a2fd3da67aa107`.

## Purpose and population

Create one audited speech-feature packet for every item in the fresh semantic AgentLoop discovery
roster. The frozen roster is
`docs/checks/speech-aware-evidence-acquisition/2026-09-03-a2t-fresh-agentloop-roster/flight-roster-receipt.json`,
SHA-256 `457297464e4e0acc9db541cbee5a2215d3447974c55d9c712c0cb1765623079e`,
split identity `84c56416a36d5eb1737fa49f6b255b0a59585df8c8ff1754240a87022983eab0`,
and media-roster identity `d8765ccbdceaaa30d9317822dafaf76be04519bd1b2ebd642f211eed601f6906`.
It contains 104 items, 13 per tier, totaling 554.255707 seconds. It is a deterministic subset of
the proposed unexposed 400-item discovery partition and is disjoint from construction query blocks,
previously exposed identities, and test data.

This pass opens the 104 speech carriers only to the frozen audio encoder. It does not read task
text, labels, expected calls, reference transcripts, annotations, prior responses, scores, test
data, or future turns. The fixed response has a one-token ceiling and its meaning is never
interpreted.

## One-shot procedure

Use the receipt-pinned CPU-only llama.cpp preprocessing sidecar on loopback port 8081 with
`-ngl 0` and `--no-mmproj-offload`. Construct each runtime sample directly from the roster's
sample id, media path, audio SHA-256, and duration. Resolve every path below the declared data root,
verify its bytes against the receipt, and derive the packet id by replacing `:` with `/`. Never
invoke the carrier's gold or task-text loader.

Make one fixed-minimal-prompt contact per recording. Do not retry, repair, substitute, resample, or
expand the population. Stop the sidecar before the carrier-neutral promotion primitive reads the
current-build feature cache. Promote into the exclusive root
`/home/chao/feat-cache/a2t-semantic-agentloop-v1-packets-04ccc72a` and write
`A2T-SEMANTIC-AGENTLOOP-104-V1-promotion.json` there. The GPU inference service is not started or
contacted by this pass.

Intended use is exactly 104 contacts and 554.255707 speech-audio seconds. The structured run-level
ExecutionPlan reserves at most 120 contacts, 650 speech-audio seconds, and 0.2 GPU hours. Paid API,
embedding, tokenizer, external network, and scorer contacts are zero.

## Packet and context consequence

Record the exact speech-token count of all 104 promoted packets without truncation. A packet-size
distribution is descriptive only for this successor; it does not inherit or impose the earlier
455-speech-token prompt-fit rule. Before every later M0, OBS, matched USE, or shuffled USE contact,
the final inference transport must separately measure the exact current rendered text and add the
selected packet's measured speech tokens, the registered special-token reserve, and that request's
completion ceiling. The later contact is allowed only when this complete required window is at most
24,576 tokens inside the 32,768-token physical slot.

## Failure and terminal rule

Any identity drift, audio hash mismatch, runtime-receipt drift, gate failure, failed encode contact,
incomplete cache, incomplete promotion, or packet provenance mismatch stops the pass. Partial
packets do not authorize inference, and recovery requires a prospective amendment. Network jitter,
retry stress, and latency injection are outside scope.

Successful promotion opens only the separately preregistered 104-row semantic AgentLoop flight. It
does not establish task effectiveness, open gold or the scorer, fit Vowpal Wabbit, authorize the
approximately-1,000 scale step, open test data, or authorize Stage-3 or paper-scale work.

## Pre-contact closure

The contact-free preflight verified all 104 roster paths and hashes, 554.255707 total seconds, zero
of 104 current-build cache entries, zero of 104 packet manifests, and an absent promotion receipt.
The relevant WSL test set passes, and the profile composes to the registered hash above. Formal
execution starts only from a clean study commit after the matching exposure-ledger row is present;
the launcher constructs and validates the exact-attempt ExecutionPlan before starting the sidecar.
