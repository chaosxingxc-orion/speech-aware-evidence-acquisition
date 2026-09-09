# Four-case completion-budget engineering readout

Both arms sealed before readout. Root verified both immutable generation bundles and exact wire-response hashes. The same frozen Instruct weights, four-slot resident process, input packets, predecessor, original KC-S1b examples and prompts served both arms. Actual request payloads match after removing only request ID, slot ID and completion ceiling. This purposive set is not an accuracy sample.

| Selected case | Ceiling64: tokens / ending | Ceiling256: tokens / ending |
| --- | --- | --- |
| Ordinary historical case | 20 / normal, valid JSON | 20 / normal, identical text |
| Historical cap case A | 64 / length, incomplete JSON | 77 / normal, complete JSON |
| Historical cap case B | 64 / length, incomplete JSON | 79 / normal, complete JSON |
| Long non-cap case | 63 / normal, valid JSON | 63 / normal, identical text |

The two truncated texts are exact prefixes of their complete256 counterparts. Raising the ceiling fixes a demonstrated truncation defect in these two cases. It does not establish accuracy improvement or an overall truncation rate. Historical KC-S1b metadata had4 of1000 outputs at64, but no stop reason, so that count alone did not prove truncation.

All eight responses include scenario/action alongside entities, contrary to the entities-only phase instruction. The shared SLURP parser accepts the four complete256 objects, while the exact phase contract accepts none. Report this separately; do not silently repair the prompt or delivery during the comparison. Raw and delivered text were byte-identical for all eight rows, including truncated outputs. No official scorer or gold-label comparison was used for this engineering read.

The two arms generated211 and239 tokens:28 additional tokens, not four completions of256 tokens each. Their summed request latencies were32.381 and6.501 seconds. The second arm reused25278 of25282 prompt tokens, versus8564 cached tokens in the first arm. Cache state and order confound timing; these durations do not show that a larger ceiling speeds inference. No reasoning switch or weight change was tested.

The owner subsequently approved OWNER-KUS3-BUDGET-005: prepare KU-S3a, its twin and one1000-row no-retrieval control at256, retaining the original64 KC-S1b repeat. Register fresh source-bound preparation and full-roster capacity receipts before generation. Existing64 KU-S3 fit registrations remain unconsumed historical plans; do not repurpose them.

## Service and implementation receipt

Service: `slurp-g1-np4-c65536-20260909-codex`. The root released each exclusive capability only after a successful seal and exited worker. It explicitly stopped the service at16:03:19 UTC while the next protocol was being prepared; no worker managed the service. Server and monitor processes are gone. The externally requested SIGTERM was not forced; the foreground wrapper nevertheless reported exit1, which is retained in the lifecycle journal rather than described as an unexplained model crash.

The whole service window lasted about60.25 minutes with10-second monitor samples; about8.31 minutes were classified active and51.94 minutes parked. Exact generation contacts were1008 across the KC repeat and the two engineering arms; the sampled request counter is a lower bound. This window did not meet the intended handoff/idle target. It included root integration, frozen-checkout setup, CPU packet/media validation, decision work and readout. These categories are not all independently timed, so do not invent a precise allocation. Future sessions must stage validated work before loading the model.

The shared analyzer distinguishes wire, normalized and delivered views, requires exact source hashes, preserves unavailable stop metadata, and rejects unregistered request differences. Sixteen synthetic tests cover these checks. Raw traces and exact responses remain outside Git; `summary.json` binds the complete readout and its hashes.
