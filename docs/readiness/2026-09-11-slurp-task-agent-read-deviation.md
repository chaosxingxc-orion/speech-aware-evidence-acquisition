# SLURP task-agent direct seal verification: unintended response serialization

Date: September 11, 2026. Status: retrospective deviation record, not a preregistration. The three-arm protocol and all configurations were frozen at 1c11d910 before this event.

The root structural seal check called verify_bundle successfully, then mistakenly printed and serialized its rich VerifiedBundle return object. That object includes parsed outputs and traces. The tool output was heavily truncated, but this was response-bearing output emitted before the knowledge and frame arms had sealed. An untouched result-read barrier can no longer be claimed.

No official score or reference was read, no intentional semantic quality review occurred, and no configuration, selection, stopping or repeat decision was made using this output. Root retained the already registered direct -> knowledge -> frame sequence. Intentional scoring and quality review remain held until all three arms seal or a formal failed-comparison hold. The final report must carry this limitation.

The direct manifest remains immutable: SHA256 4d1dec6bd3695553c25041288cb4c536a194ea6b028acd90a2775c492b5108ff. It contains 1000 completed rows and 1000 generation calls.

Preserve these external records:
- DATA coordination/slurp-task-agent-response-serialization-incident-v1.json, SHA256 34e4c5cbca085906dcd50b07f5c72c0679f6b5b34d35e3e4ff2ca0f63814a9b1.
- The bulky verification v1, SHA256 80a6d21a95ac061de248483a64647bf3b701fddda949b2e30699dc98ac806e5a, is superseded, not rewritten. Its broad quality_read=false field is qualified by this incident.
- Compact verification v2, SHA256 ff92160b6e92badb48e6a8c6b664b0f10b56f6c265082a1e39e2ab58d88707ed, records scalar verification metadata and the read limitation.

Future structural checks must never print or serialize the rich bundle return. Emit only explicit scalar status, roster size, call count, source identities and hashes. This correction changes root record handling, not the frozen runtime or scientific comparison.
