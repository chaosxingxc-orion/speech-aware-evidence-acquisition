# Audio2Tool SELECT/FILL fresh-104 preprocessing V1 preregistration

Date: 2026-09-03. Status: **REGISTERED BEFORE CONTACT**.
Experiment: `SAEA-SN-A2T-SEMANTIC-AGENTLOOP-SELECT-FILL-104-PREPROCESS-V1`.
Execution profile: `bounded-discovery-probe`.
Composed-config and protocol SHA-256:
`2c2f34a9144ed44ce8bb1b559948eeea03f8659f66540c26a5e42c7c8cb4eb91`.

## Fixed population and purpose

Preprocess exactly the fresh roster at
`docs/checks/speech-aware-evidence-acquisition/2026-09-03-a2t-select-fill-fresh-roster-v1/flight-roster-receipt.json`,
SHA-256 `dea74114430ed5e45e29d908dc2ecebf41788edfa2704435a2966f260de5bc4f`,
split identity `bcbad5405aa8522ff53a91d624c54a909e01f8a31612b5165844b8e2cbca6eb3`.
It contains 104 discovery rows, exactly 13 per tier, totaling 549.489916 speech-audio
seconds. The roster is disjoint from the preceding semantic AgentLoop flight by sample identity,
query block, and normalized-token hash. This preprocessing run provides speech-feature packets only;
it neither evaluates nor modifies any task method.

## Additive D1 media identity

Bind the additive receipt
`docs/receipts/artifacts/d1-a2t-semantic-agentloop-select-fill-104.json`, SHA-256
`52c870f04200b21e3a86dd315085f0ccf44c3e13388b7c1a0f62e04233411a21`. It is bound to parent
D1 SHA-256 `9c10fad1e5b625f977a5bdc71ed0c782e5d5c76c7a13af11ce811c5e152d35e3`
and source-roster SHA-256
`dea74114430ed5e45e29d908dc2ecebf41788edfa2704435a2966f260de5bc4f`. Its 104 entries record
only sample identity, confined media path, file bytes and SHA-256, WAV-header duration, sample rate,
and the query role. Its canonical manifest SHA-256 is
`f319d6b9608916bd2044e1650d4050c68f9e8fb41e0a03bcf7c2c5f24181d925`.

Before any model contact, reconstruct the payload binding from the roster and require the existing
frozen-core gate to verify all 104 media files against this additive receipt. The contact-free
preflight already passed all 104 path, byte-hash, header, roster, and D1 checks. At that point the
new packet root and promotion receipt were absent, as required.

## One-shot procedure and budget

After the D1 check and full runtime and weight attestation pass, start the receipt-pinned CPU-only
llama.cpp preprocessing sidecar on loopback port 8081 with `-ngl 0` and
`--no-mmproj-offload`. Keep the answering GPU service stopped and untouched. Make exactly one
fixed-minimal-prompt contact per roster item with a one-token completion ceiling. Do not retry,
repair, substitute, resample, or interpret response content. Network jitter is not an experimental
variable and causes no resend.

Stop the sidecar before promoting current-build cache entries through the carrier-neutral packet
promotion primitive into
`/home/chao/feat-cache/a2t-semantic-agentloop-select-fill-v1-packets-04ccc72a`. Require exactly
104 finalized contacts, 104 new cache entries, 104 hash-valid packet manifests, and the promotion
receipt `A2T-SEMANTIC-AGENTLOOP-SELECT-FILL-104-V1-promotion.json`. Intended use is 104 contacts
and 549.489916 speech-audio seconds. The structured `ExecutionPlan` reserves at most 120 contacts,
650 speech-audio seconds, and 0.2 GPU hours. Paid API, embedding, tokenizer, scorer, and external
network contacts are zero.

## Information boundary and future context fit

The launcher reads no task text, label, expected call, reference transcript, annotation, prior
response, score, test data, or future turn. The fixed one-token response is not read semantically.
This run is not a task experiment and cannot authorize evaluation, policy fitting, or scale.

Record exact packet speech-token counts without truncation. These counts do not define a fixed
future prompt allowance. Every later inference phase must serialize and measure all 104 exact
requests before that phase begins, including phase-specific context, selected-tool ground,
canonical state, schema, special-token reserve, and completion ceiling. Each request must fit the
24,576-token operating limit inside its 32,768-token physical slot. This preserves 8,192 tokens of
headroom for loop-dependent prompt growth instead of treating a forecast as an exact budget.

Successful promotion opens only a separately preregistered paired 104-row workflow experiment.
It opens no gold or scorer, Vowpal Wabbit fit, approximately-1,000 expansion, test, confirmatory,
Stage-3, or paper-scale work.

## Frozen implementation bindings

- dataset fragment SHA-256: `b39a166a1a711c3580ba91d3753a74c4953ee3224614b23be200c5fb51d91b76`;
- experiment fragment SHA-256: `ef2be36be4cd9e703b1fcd289b7693ca1411ecc2bfe232f5b906874a06fd227d`;
- preprocessing launcher SHA-256: `e995fd85fb63f98922730b4decda4bf834cfe89b6e0c41e6c8277cc93aade833`;
- D1 successor builder SHA-256: `8e4c3a41ec8ab065d47c254772f4e49d32ba2e39793928789ee97c50db8f57f3`.

Formal execution starts only after the launcher, fragments, D1 receipt, tests, this
preregistration, and the matching exposure-ledger row are committed and the study worktree is
clean.
