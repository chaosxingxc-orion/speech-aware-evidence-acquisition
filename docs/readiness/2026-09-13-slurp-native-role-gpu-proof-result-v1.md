# Native role GPU proof: tool loop verified, candidate interface held

The registered four-row TRAIN engineering flight completed through the shared FlightRuntime, shared speech runner, stable-slot scheduler and OpenJiuwen role graph at code cd261a2331b53f91c79c4d55f1aabe148aa44b2b. The instructed native tool-loop acceptance passes. This configuration is not ready for a task-quality or knowledge-supply experiment.

## Actual execution

| Item | Observed |
| --- | --- |
| Completed rows | 4 of 4 |
| Frozen-core requests | 20 of the 44-contact ceiling |
| Reviewer native task-contract calls | 4, one per row |
| Tool responses consumed by the next Reviewer request | 4 of 4, exact source result matched |
| Perception / Solver / Planner tool calls | 0 |
| Final output custody | 4 of 4 accepted Solver request and text hashes |
| Planner routes | 4 ACCEPT, 0 REVISE |
| Actual request capacity receipts | 20, all passed |
| Tokenizer endpoints | 80 of the 176-contact ceiling |
| Minimum actual context margin | 3,339 tokens |
| Finish reasons | 16 stop, 4 tool_calls, 0 length |
| Scoring, ASR and new encoding | 0 |

Root compared every tool call with the original assistant message in the saved HTTP response, its normalized response receipt, the role authority record and the following native tool message. Raw-wire and normalized-response hashes are different hash domains and were checked against their own records. Every capacity receipt matches the corresponding recorded request boundary. No call was injected by the harness, and no contact was replayed.

The model service uses the prepared speech packets, decoder-only inference, no mmproj, total context 65,536, eight 8,192-token slots and a 256-token output ceiling. The new session is serving-slurp-native-role-gpu-proof-np8-v1. Root released the worker lease after sealing; the resident service and its 10-second monitor remain available.

The worker ran from 14:33:36.609657 to 14:34:20.737554 UTC. The recorded contact window is about 25.13 seconds. Model contact accounting records 65,904 prompt tokens, 849 completion tokens and 52.9778125 repeated-observation audio seconds. The three monitor samples inside that brief window average 58% GPU utilization; this is a small engineering observation, not a sustained-throughput benchmark. Four source rows can occupy at most four of eight slots. No extra samples were added for utilization.

## Named integration defects

All four raw Perception responses use the requested compact candidate object, but their ten candidate IDs are bare scenario or action names. None is a complete canonical intent ID. The supplied task context contains the 60 legal scenario/action pairs, while the role prompt requests an exact intent ID without specifying the scenario_action representation.

The common system material also directs every role to emit the Solver's final scenario/action/entities JSON. Role-neutral task facts and each role's output contract must be separated in configuration.

Finally, the native history currently preserves the raw compact response as its phase state. The existing strict hypothesis-state consumer expects the canonical schema, semantics and sample identity. Reuse canonicalize_slurp_intent_hypothesis_response with explicit derived-state provenance; never rewrite the original response or substitute a different hash as its source. The canonicalizer independently rejects all four observed responses for illegal intent IDs.

These are verified configuration/interface defects. This run does not establish their causal contribution to task accuracy. Retain strict validation and repair the named integration points before a new separately registered knowledge experiment. Preserve this completed flight, its original prompts and all spent contacts.

## Interpretation and next work

The actual framework tool cycle works. Its instructed execution does not establish selective tool-trigger usefulness. All Planner actions accepted the first Solver draft, so the revision branch was not exercised on GPU. No gold comparison or official task scoring was performed.

The next bounded work is to use role-neutral task context, define the complete candidate ID representation, and connect source-bound canonical phase state to the existing candidate-conditioned knowledge provider. The separately released 60 intent values and 54 slot values remain unconsumed in this proof. Their support does not replace the authoritative full legal label/type inventories.

## Artifacts

- Generation manifest SHA-256: 5512b5515bb927fd6604cccdc868f08fe864f6a19b2a2472cdfddea21e897017.
- Outputs SHA-256: a05ff3ce5a306b2f892fde6d38dcff7c7e65d2b07d6a87d9d4b786160994841f.
- Raw trace SHA-256: 1c61519fd41660fbe3827c495ab8e21c8bb073658959d9b85335782c856056e9.
- Root engineering audit: coordination/slurp-native-role-gpu-proof-v1/engineering-audit-v2.json under the configured data root.
- Audit SHA-256: b1990f5ae0a5463c059a88a2636727a6687ff2070dc62cf1f6b3f0e1c6d6f90a.
- Audit v1 remains preserved; v2 separately adds compact-response validation rather than treating the canonical-state parser as a compact parser.
