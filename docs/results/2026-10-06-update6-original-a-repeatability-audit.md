# Update6 original-a: seed/A/A request repeatability audit

Root diagnostic completed 2026-10-06T21:57:05.510962+00:00.

## Scope and custody

This is a contact-free audit of the already qualified original-a complete family. Its exact root READ and full independent seal/score qualification were revalidated before reading source traces. No active remaining-b1 result, old malformed family, test feedback, model/scorer contact or optimizer export enters this audit. Original frozen bytes and acceptance rules remain unchanged.

## Configuration and serving identity

The two seed baseline fragments differ only in their FIT run/attempt identities and prepared-supply envelope path/hash. Role texts, knowledge configuration, assembly controls and other baseline fields match. All116 seed and131 A/A request records carry temperature0 and seed20260913. Each has one matching actual-request FIT receipt. Both share the recorded session identity, response model path and server fingerprint `b8-04ccc72a2`. This establishes matched declared configuration, not bitwise numerical determinism.

## First role-visit comparisons

Each role is aligned on the same20 input identities, using only its first visit. Downstream role inputs may already reflect upstream divergence. Request-body equality refers to the rendered-body canonical hash in the actual-request FIT receipt; this is not independent network packet capture. Response equality is checked both on adapter text and on the original wire choice message, excluding outer request IDs/timestamps.

| Role | Pairs | Same slot | Same rendered request body | Same response text | Same body, different original choice |
| --- | ---: | ---: | ---: | ---: | ---: |
| perception | 20 | 7 | 7 | 2 | 6 |
| planner | 20 | 7 | 0 | 11 | 0 |
| reviewer | 20 | 7 | 1 | 0 | 1 |
| solver | 20 | 7 | 1 | 12 | 0 |

For Perception, seven paired requests share the rendered-body hash and slot. Six return different original choice messages. Every one of those seven pairs has equal reported cached-token count2526 and equal newly processed prompt-token count within the pair. Thus this observation does not identify a cache eviction or reduced cache-hit-count event. Equal token counts do not prove identical internal KV values or numerical execution.

Across all20 Perception pairs, different recorded payload fields are limited to provenance addresses, request IDs and13 slot assignments. The first two are provenance differences; compare actual FIT body hashes rather than treating all payload differences as changes to model-visible instructions. No role-template or decoding-temperature/seed difference was found.

## Separate wording variation from decision variation

All20 Perception responses on each side parse into the registered candidate form. The top intent agrees20/20. The complete ordered candidate list and candidate set agree11/20; nine pairs differ in their additional hypotheses. Within the seven equal-body pairs, the top intent agrees7/7 and complete list/set agrees5/7. No gold labels are used in these identity comparisons. They do not identify which response is better.

These counts show that much response-text variation is not a changed top intent, while some additional hypotheses also vary. Subsequent histories and supplied materials can therefore differ before Solver/Reviewer comparison. This is a possible propagation path, not a causal decomposition of the observed SLU-F1 gap.

## Consequences for the next experiment

- Keep the current registered Update6 execution and verdict rule intact. Its A/A observations remain part of measurement, not policy-learning gain.
- Do not assume that fixed temperature and seed guarantee identical outputs under the actual serving execution. The root cause of the observed equal-body divergence is UNESTABLISHED.
- Before changing the next learning algorithm, prospectively register a small request-repeatability diagnostic that holds model-visible request bodies fixed and explicitly records serving schedule/slot/cache state. A controlled serial-versus-current-concurrency contrast could distinguish execution effects; no such new contact is admitted or launched by this document.
- Do not attribute the gap to prompt changes, cache eviction, hardware, or sampling without that evidence. Do not solve it by silently homogenizing independent node prompts or changing the active serving geometry.
- Treat secondary-hypothesis and downstream context stability as useful process observations. Evaluate any stabilization proposal through complete system quality, not equality alone; forcing agreement can also erase useful alternatives.

## Evidence

- Audit script: `/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/coordination/update6-original-a-repeatability-audit-v1/audit-v1.py`.
- Audit result SHA256: `075249f71f77ada9dd5534b6045425e7a3e85039434b9e9a5ef6eb7e9b1fa03b`.
- Candidate identity diagnostic SHA256: `3f1652008b17d7bb7913265343845c230c49a7a8550e17860c40b0186f87f0a8`.
- Source pins and anonymous paired hashes/timings remain in the private external audit; no task content is copied into this report.
- [Official quality and process report](2026-10-06-update6-original-a-complete-review.md) and [paired-process semantic clarification](2026-10-06-update6-original-a-paired-process-review.md) remain separate.
