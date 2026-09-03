# Audio2Tool semantic AgentLoop 104 preprocessing V2 preregistration

Date: 2026-09-03. Status: **REGISTERED BEFORE V2 CONTACT**.
Experiment: `SAEA-SN-A2T-SEMANTIC-AGENTLOOP-104-PREPROCESS-V2`.
Execution profile: `bounded-discovery-probe`.
Composed-config and protocol SHA-256:
`4eca67ae7aba8bb5623285173f968f0fbb8cd8b56df01bdf0117641066780f93`.

## Prospective amendment and fixed population

V1 stopped before constructing a core client and before its first model contact because the fresh
roster is outside the immutable base D1 Audio2Tool 400-row media manifest. The normal CPU sidecar
stop and zero-contact refusal are recorded in
`docs/checks/speech-aware-evidence-acquisition/2026-09-03-a2t-semantic-agentloop-104-v1/preprocess-v1-zero-contact-refusal.json`.
V2 is a new run and attempt identity; it does not retry or mutate V1.

Keep the exact same fresh roster:
`docs/checks/speech-aware-evidence-acquisition/2026-09-03-a2t-fresh-agentloop-roster/flight-roster-receipt.json`,
SHA-256 `457297464e4e0acc9db541cbee5a2215d3447974c55d9c712c0cb1765623079e`,
split identity `84c56416a36d5eb1737fa49f6b255b0a59585df8c8ff1754240a87022983eab0`,
and media-roster identity `d8765ccbdceaaa30d9317822dafaf76be04519bd1b2ebd642f211eed601f6906`.
It contains 104 discovery items, 13 per tier, totaling 554.255707 seconds; it is disjoint from
construction query blocks, previously exposed identities, and test data.

## Additive D1 successor

Bind `docs/receipts/artifacts/d1-a2t-semantic-agentloop-104.json`, SHA-256
`774f3a9afdcb36a81e35032cf424b8d46d30c17fdc82402eb7ea4d3873fc9e0f`.
This existing `saea-d1-media-supplement-v1` receipt type is additive: it does not rewrite the
immutable parent D1 artifact. It is bound to parent D1 SHA-256
`9c10fad1e5b625f977a5bdc71ed0c782e5d5c76c7a13af11ce811c5e152d35e3` and source-roster SHA-256
`457297464e4e0acc9db541cbee5a2215d3447974c55d9c712c0cb1765623079e`. Its 104 sorted entries
record exact sample id, confined media path, measured byte length, measured SHA-256, WAV-header
duration, sample rate, and the `query` role. Its manifest SHA-256 is
`a72476fe8219a42a9ab01f52cc031b2781fc03332058a72232a9072e09108648`.

Before starting the sidecar, reconstruct the payload binding from the roster and require the
existing gate to re-hash and verify all 104 files against this supplement. Any mismatch stops V2
without starting the sidecar. The model-free preflight has already passed this exact 104/104 check.

## One-shot procedure and budgets

After the D1 check and the full frozen runtime/weight attestation pass, start the receipt-pinned
CPU-only llama.cpp preprocessing sidecar on loopback port 8081 with `-ngl 0` and
`--no-mmproj-offload`. The GPU answering service remains stopped and untouched. Make exactly one
fixed-minimal-prompt contact per recording with a one-token response ceiling. Do not retry, repair,
substitute, resample, expand the population, or interpret response content.

Stop the sidecar before promoting current-build cache entries through the carrier-neutral
promotion primitive into
`/home/chao/feat-cache/a2t-semantic-agentloop-v1-packets-04ccc72a`. Require exactly 104 finalized
contacts, 104 new cache entries, 104 hash-validated packet manifests, and one promotion receipt.
Intended use is exactly 104 contacts and 554.255707 speech-audio seconds. The ExecutionPlan reserves
at most 120 contacts, 650 speech-audio seconds, and 0.2 GPU hours. Paid API, embedding, tokenizer,
external network, and scorer contacts are zero.

## Knowledge and context boundary

V2 reads no task text, labels, expected calls, reference transcripts, annotations, prior
responses, scores, test data, or future turns. The additive receipt measures carrier identity only;
it contains no speech transcript or task semantics. The fixed one-token response is not interpreted.

Record every promoted packet's exact speech-token count without truncation. These counts do not
define a fixed future prompt allowance. Immediately before each later M0, OBS, matched USE, or
shuffled USE contact, serialize and measure the exact current request, then add that packet's exact
speech tokens, the registered special-token reserve, and the request-specific completion ceiling.
Permit the contact only when that complete required window is at most 24,576 tokens inside the
32,768-token physical slot.

Successful V2 promotion opens only a separately preregistered 104-row semantic AgentLoop flight.
It does not establish task effectiveness, open gold or the scorer, fit Vowpal Wabbit, authorize the
approximately-1,000 scale step, open test data, or authorize Stage-3 or paper-scale work.

## Frozen implementation bindings

- dataset fragment SHA-256: `26cf6a6ad0b60ccb5aca63c8903bff3529e9745f15ac7811da4cddd36b8c73bc`;
- experiment fragment SHA-256: `fbc7f0a65dab47e0c417a2e1bd80b8e984fd6bbb89d0cbfde0effc4260c69f80`;
- preprocessing launcher SHA-256: `c10d74e76da99e18b854de4223424c6c10f16a147eb57e924a8455b925aa5072`;
- D1 successor builder SHA-256: `8e4c3a41ec8ab065d47c254772f4e49d32ba2e39793928789ee97c50db8f57f3`.

Formal execution starts only after these files, the supplement, this preregistration, and the
matching exposure-ledger row are committed and the study worktree is clean.
