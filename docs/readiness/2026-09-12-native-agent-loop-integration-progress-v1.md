# Shared native agent loop integration progress

Status: three prerequisites integrated in an isolated WSL checkout; no live loop or new flight yet.

The integration checkout is /home/chao/saea-worktrees/agentic-native-tool-loop-v1 on codex/agentic-native-tool-loop-v1. Its merged prerequisite tree is faf4c95b3d713867cdaef5f6da978727e70071e9. The main checkout remains f78aab7083580502c81edfe33dcaf13964b5f5b2. The active resident service and its frozen launch checkout were not changed.

Integrated:
- Source-bound opt-in native completion metadata: 2f655cd568444e9f6fb9e0e3b5ee5479d7feed56.
- Native per-contact auto/none tool choice and parallel_tool_calls=false, with historical omission preserved: b0bdcc84709bfceeda83cb3f5a1e34e909000bb4.
- On-demand CPU Whisper provider and selected-source decoding with retained weights: ab1eb1dbc7ce79df568f69989b6c4ee7b04aa0b7.

Root reviewed the production changes. Combined actual-client/fake-transport, adapter, native request, transport, capacity, speech provider, backend and preparation regressions passed: 419 passed, 2 skipped. Engineering-base and diff checks passed. There were no real model, tokenizer, audio-tool, GPU, or scorer contacts.

Next root implementation:
1. Carry CoreCompletion through both shared runner paths using response-local metadata, including prepared requests and OpenJiuwen fan-in; preserve ordinary string responses.
2. Extend the existing EvidenceAgentController with an opt-in bounded native answer-or-tool program. Strictly parse raw calls, verify source identity, and allow early final answers. Keep final-answer authority with the frozen core.
3. Bind registered internal knowledge/observation tools, real runtime contact custody, and source-bound results into successor requests. Do not confuse predicted Audio2Tool business calls with internally executed evidence tools.
4. Register the actual capacity and engineering proof before any contact, then use SLURP to stabilize the complete baseline before transferring it to Audio2Tool.

The held fixed TRAIN-A incumbent-source generation remains a zero-contact aborted flight. It is not restarted by this integration. No optimized memory, training-free policy, live Whisper benefit, or native agentic efficacy is established.

The owner's stage-specific knowledge rationale and closed historical comparisons are recorded in docs/readiness/2026-09-12-audio2tool-stage-knowledge-root-review-v1.md. The 104-row SELECT/FILL study is historical evidence, not authority to reuse an obsolete small-screen protocol.
