# SLURP TRAIN speech-query embedding preparation

## Current status

This package is model-free preparation for two prospective retrieval-tool runs. It is not an exposure registration and does not authorize a model, tokenizer, encoder, GPU, network, scoring, or answering contact. The two run rows remain in `2026-09-12-slurp-training-query-embedding-registration-draft-v1.json`; they have not been appended to `docs/exposure-ledger.md`.

Use two exact 1,080-item runs. Fold-specific vector indexes are required because shared recall validates exact query-roster membership. A single 2,160-item output would not match either fold and the repository has no shared splitter for that derivative.

## Frozen model-free inputs

Fold A is `SLURP-EVO-FOLD-A-V2`, split identity `61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6`, 1,080 unique full utterances and 3,084.5284375 source seconds. Its roster receipt SHA-256 is `1fe7908c31396774d7535fdf37bd791762215c324999d66ed7beb9e7b2f9033d`, dataset-config SHA-256 is `4ba55688e80d8d768ec6cfc3ff4bacc9802fb34e4dab54913934015184497215`, and prepared source-inventory SHA-256 is `43af4aba29630969e03d16a5bcb6fe99e4f5532b1d3a93c8d3da511261b1db14`.

Fold B is `SLURP-EVO-FOLD-B-V2`, split identity `4407794c4a5d2e8883d93fdf242deb33c0987405d62e05a7d8416f5251a3484a`, 1,080 unique full utterances and 3,154.797375 source seconds. Its roster receipt SHA-256 is `47b89b9e33b1aed553ad94a1819acba6ac8837130ca546c33219d91a1ab944a8`, dataset-config SHA-256 is `1d30c501612686004936b5dd295885d9452175e6449b4a66187c08227a322cea`, and prepared source-inventory SHA-256 is `baf4a1fbab43c83540bc24eb11a9a0bd3df849fc760b4fac509b3374aa7044a9`.

The model-free source-preparation receipt is `/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/coordination/slurp-tfrl-speech-query-source-preparation-v3.json`, SHA-256 `23e3172dfd3df55c79e7b4ffe22c8953ac0a36b8d5e8ee684003ee0f9384dd7b`. The shared verifier confirmed every carrier hash and audio header, exact frame coverage, 1,080 unique spans per fold, and zero transcript, label, encoder, tokenizer, model, network, or GPU contacts.

Reuse the complete frozen local `omni-embed-nemotron-3b` inventory at `/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/coordination/a2t-speech-query-encoder-inventory-v2.json`, SHA-256 `1548387ba91209921fd747e9eff981027be618c618b732efe20ca7d43680bb31`. Its pinned files and package versions were reverified without loading the model. These vectors are Nemotron query vectors; the existing 2,160 Qwen speech-feature packets are different artifacts and cannot satisfy this input.

The successor compact K5 snapshot remains independently pinned by content SHA-256 `9c64e8ec48a0fce4f172bd190932f99c98c7efa18bbfb14526d54c62fdf7032b`, file SHA-256 `f2785aa3521b08e874d4075154e65cc639284497afc789a3654c2c70a65405ef`, and build-receipt SHA-256 `5db718d38426e5e6d2311efbed0c4faf36bf30473c8d00b14e06618257889766`. It excludes both A and B. Query encoding does not inspect or depend on knowledge values; the later recall configuration must pin this successor separately.

## Prospective protocols and budgets

The fold-A protocol is `configs/preparation/slurp-tfrl-fold-a-speech-query-encoding-protocol-v1.json`, SHA-256 `c4c2eecca865a477bda01e578b7dffe32cd1384b341e4c187640962e7280c8c4`. Its prospective plan reserves exactly 1,080 contacts, 3,085 speech seconds and 2.0 GPU hours under run `SAEA-SLURP-TFRL-FOLD-A-SPEECH-QUERY-ENCODING-V1`, attempt `encode-v1`.

The fold-B protocol is `configs/preparation/slurp-tfrl-fold-b-speech-query-encoding-protocol-v1.json`, SHA-256 `36d2425ef516ca446d607ab92e7df86d3c310e5c9d03cca3e6b94a8df70f013a`. Its prospective plan reserves exactly 1,080 contacts, 3,155 speech seconds and 2.0 GPU hours under run `SAEA-SLURP-TFRL-FOLD-B-SPEECH-QUERY-ENCODING-V1`, attempt `encode-v1`.

Both preserve the shipped literal `query: ` prompt, complete audio, 2,048 dimensions, masked mean pooling, L2 normalization, batch size one, 120-second windows, 8-second overlap, an 8,192-token bound, a 1,920,000-sample bound, four CPU prefetch workers, and ten-second monitoring. They share the immutable cache root `prepared/slurp-tfrl-speech-query-span-cache-v1` and write separate indexes and JSONL query-row exports under their run IDs.

## Final registration and execution handoff

After the current flight closes, the root coordinator must review and append each draft as one valid 15-cell row in `docs/exposure-ledger.md`, commit those rows and protocols, and freeze a clean execution checkout. Only then create each external runtime JSON from the exact `runtime_config_shape` in the draft, replacing `SET_TO_THE_FINAL_CLEAN_REGISTRATION_COMMIT` with that commit. Do not alter the plan, protocol, roster, source inventory, encoder inventory, budgets, session ID, or output paths after registration.

Run the existing shared entry only after admission:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<frozen-checkout>/src OMP_NUM_THREADS=1 \
python -m speech_aware_evidence_acquisition.core.speech_preparation_runtime \
  --config <external-runtime-config.json> \
  --config-sha256 <runtime-config-sha256> \
  --data-root /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data \
  --source-root <frozen-checkout>
```

`run_preparation` supplies the existing `ExecutionPlan`, tool-plan gate, full encoder-inventory verification, `GenerationLease`, `AttemptStore`, before-forward accounting, immutable per-span start markers, create-only index publication, query-row export, monitoring, and one-shot abort semantics. The encoder is an in-process local retrieval tool; it has no endpoint and must hold exclusive GPU custody without a resident answering server.

There is no missing shared encoder or storage seam. The remaining blockers are intentional governance bindings: the two exposure rows are still drafts, and the final clean registration commit cannot be placed in an external runtime config before it exists. Historical A/B exposure remains inherited under the V2 roster/supplement, packet, intent-flight, fold A/B, prompt-fit, smoke, and successor-KB rows; these preparations must not describe either fold as fresh data.
