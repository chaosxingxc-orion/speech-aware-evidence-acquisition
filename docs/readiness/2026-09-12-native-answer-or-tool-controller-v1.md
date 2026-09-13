# Shared native answer-or-tool controller

Status: shared controller and executor wiring implemented; live runtime contact proof pending.

The registered native-answer-or-tool-v1 program has decision-1, decision-2, and final phases with a maximum of three core contacts. Its explicit native-answer-or-tool stop rule requires the native internal-tool dispatcher. Each decision permits a plain final task answer or a native tool request. The final contact sets tool_choice=none. An external stop policy, forced phase response grammar, or phase barrier cannot silently override this program.

Before sealing, EvidenceAgentController verifies the response-local CoreCompletion against the active sample, contact, response text, and query-state binding. Plain answers stop immediately. Native requests invoke the configured shared dispatcher and require a returned source-bound observation before continuing. Malformed native calls are left raw for strict dispatcher validation; they are never inferred from compatibility text.

Both shared rails runner paths carry immutable response-local metadata. OpenJiuwen keeps it in a per-sample/wave/branch sidecar, verifies it against the actual fan-in text, and consumes it once. Its historical three-field serialized response remains unchanged. A separate TOOL/native-completion record binds raw native call JSON and request/response hashes; historical MODEL_RESPONSE bytes are not changed. Staged review/tool context keeps this metadata; the next contact's context starts without stale completion metadata.

FrozenCoreClient.record_tool_call delegates the existing adapter counter. Internal invocations and cold neural-tool calls remain separate events: this counter never debits model calls or audio.

Validation: tests began failing on the missing program and missing metadata handoff. The actual FrozenCoreClient/FrozenCoreAdapter and actual OpenJiuwen executor with fake transport then exercised two concurrent samples: one immediate final answer and one two-tool trajectory ending at the forced-final phase. Both observations reached the actual successor payload; prepared requests matched transmitted requests after routing-only fields; completed rows left later capacity waves. Controller source mismatch, missing metadata, final-call refusal, and default behavior were also checked. Combined controller/runner/client/tools/planner tests: 223 passed. Ruff and engineering-base checks passed.

No live model, tokenizer, ASR, raw dataset audio, or official scorer was contacted. Runtime tool custody and the actual four-row engineering flight remain required before calling this a live baseline. This change does not restart the held fixed TRAIN-A source flight.
