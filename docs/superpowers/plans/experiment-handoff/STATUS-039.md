# Status039: shared task actions and knowledge views; distinct corrective memory

Date: 2026-09-11T15:28:49.573405+00:00. Base inspected: 2b2c96ffe8e2f194b9a7b04ae443b0bdf94e35e1. The current increment adds shared implementation and CPU proofs. The original goal remains active; no new GPU flight or experience-memory benefit is claimed.

## Owner direction

Read OWNER-KNOWLEDGE-EXPERIENCE-SEPARATION-017 and the revised docs/readiness/2026-09-11-multimodal-task-agent-system.md. TRAIN examples, speech packets, transcripts, labels, schemas and facts are knowledge. Memory means analyzed correction experiences and validated conditional rules. Raw trajectories, current-task working state and executable policy are separate objects.

Keep the complete multimodal system as the target, SLURP first and E21/E22 later. No large immediate gain, cost-efficiency target or new minutes task is required. Previous verdicts and exposure boundaries remain intact.

## Implemented and verified

- Shared phase_tools explicitly selects fixed or frozen-core-choice task actions. The Planner action really invokes a pinned ToolEntry; unknown/stale actions refuse before the tool. The returned source-bound AgentStateArtifact reaches the next Solver through EvidenceAgentController and OpenJiuwen. A Planner action cannot become final delivery.
- Registered two thin primitives: current task contract and shared phase knowledge. No new controller hierarchy or private experiment runner was added.
- Shared knowledge_value_views preserves historical text blocks and assembles source-bound speech/paired values. The prepared catalogue binds TRAIN snapshot/source, audio, packet, encoder, decoder and projector. Query speech stays distinct; ordered value-to-packet references survive the real FrozenCoreClient and LlamaServerTransport render path.
- FlightRuntime validates opt-in action/view configuration and dispatches through the continuous shared phase runner. Empty/historical configurations preserve their prior behavior. The new plan/solve fragment is a composable engineering anchor; it is not the complete reviewed system or a contact registration.
- Added generic registered-media preparation and a thin adapter for the frozen SLURP TRAIN roster. The adapter recomputes readiness-entry identity and verifies exact facet/source/media/utterance joins. Shared low-level encoding accepts registered raw media without forging OBS slices, while preserving custody/cache/source checks.
- Tests cover successful fixed/core-choice knowledge invocation through OpenJiuwen, invalid action refusal, real paired request rendering, cache hits with zero encoding contact, one contact per missing source and source-binding refusals.
- Root corrected a real-schema defect missed by the initial synthetic tests: the frozen roster includes utterance_id. The final adapter was run on the actual source roster, not only fixtures.

## Concrete CPU preparation

The deterministic lexical-smallest TRAIN sample per recalled facet roster contains 2,621 unique recordings. Independent byte/hash verification passed. Four existing packets qualify under the target decoder/projector; 2,617 selected recordings require packets. The older KU-S4 exemplar campaign remains held; this is a separate knowledge-system preparation.

Roster: DATA coordination/slurp-train-recalled-candidate-preparation-roster-v1.json, SHA256 094747c37870440cc4adf5dcea61a5afcd8ad0d5640444a5c68ba12f66ad4ebb.
Target qualification: DATA prepared/SAEA-SLURP-TRAIN-RECALLED-CANDIDATE-PACKET-AUDIT-V1/target-qualification-v1.json, SHA256 d787ee8aaa42a8ab86de6955de90361fb692348fa2dcf7daff18f427e99d872a.

Root located the existing preprocess-role runtime receipt, docs/receipts/runtime-q4km-preprocess.json, SHA256 e170f1c6360a9d0a1a7dde762bca01fb8e6e0373d73117dc212db0d75120fee5. Its declared build, decoder and bf16 projector match the target. Root ran prepare_slurp_train_recalled_media_feature_inventory on all real selected bytes and persisted DATA prepared/SAEA-SLURP-TRAIN-RECALLED-SOURCE-MEDIA-V1/inventory.json, SHA256 e578026f4ea30d64a4bc34091e88193f37c1eb16817d0187b719ef16bf0028b0. This is a model-free full-source inventory; retain the four qualified promoted packets when deriving the missing encoding work. A complete source inventory is not permission to re-encode existing qualified packets.

An earlier agent-only in-memory smoke used a decoder-only receipt as a structurally valid identity. It established the source join only and was explicitly retracted as encoder qualification. The root-produced persisted inventory instead pins the actual preprocess-role receipt above. No encoder service has been started or qualified here; runtime bytes, arguments, lease and contact registration remain execution-time gates.

## Actual remaining gaps and next sequence

1. Finish the shared public runtime/CLI connection for registered TRAIN media: create the correct FrozenCoreClient payload binding from that source roster, reuse attach-only prepare-window-features custody, and consume qualified packet hits while encoding missing sources. Low-level encoding support alone does not complete this entry.
2. Compose/register the first knowledge-enabled system cohort, including actual output bounds, full real request fits, data roles and all Planner/Solver/tool contacts. Switch the root-owned service once for the missing-packet window, then restore no-mmproj decoder inference.
3. Complete the reviewed acquisition/revision trajectory and the fixed/adaptive control proof. Current two primitives and two-stage CPU proof do not establish every OBS action or final full-system quality.
4. Add the smallest durable corrective experience/rule artifact and registered selector using existing trajectory/reviewer/policy inputs. Reuse the current-query tool-result bridge to expose selected past experience; do not inject stale AgentStateArtifact records or relabel KnowledgeSnapshot as memory.
5. Validate frozen experience as a separate factor with knowledge and available tools held fixed, then connect training-free policy/utility updates. The proposed DEV role split remains unadopted. Transfer the qualified base to E21/E22 on native tasks.

## Service and historical results

Process-only snapshot at about3h23m elapsed showed wrapper35765, decoder35780 and monitor35824 alive. The retained service is serving-slurp-live-program-matched-np4-v1 on frozen checkout21ebe2bc8f9c03469a48fe0c68e9b31f1c360dff, c65536/np4/max256/no-mmproj. This boundary performed no model, tokenizer, embedding or new scoring contact. Retention is not current endpoint qualification, dispatch authority or useful GPU utilization.

All four previous E21/SLURP attempts remain FINALIZED with complete scores and settlement. Existing S3 component evidence is positive; final matched SLURP system guards failed. E21 PERSON benefit and insertion-guard failure remain recorded. S4N non-inferiority failed and its old encoding/sample branch stays held. No old attempt is reopened, rescored or relabeled as a new experiment.

## Boundary validation

WSL Python3.12, explicit PYTHONPATH=src:tests/unit, no editable reinstall. Final selected suite: 386 passed in22.53s, with three existing dependency deprecation warnings. It includes action/knowledge/preparation tests and adjacent controller, phase runner, live fit, FlightRuntime and encoding paths.

Coverage with branches over the four new production modules is82% combined: action85%, knowledge views88%, thin wrappers100%, media inventory72%. This is not repository-wide coverage. Shared engineering-base check and tool-catalog check pass; the catalog contains28 tools. Formatting, changed-file lint, coordination and whitespace checks are checked at the integration boundary. Real-roster CPU preparation is separate from the synthetic model-free execution tests.

The latest code still needs its frozen cohort and GPU evidence. Do not describe this implementation boundary as a completed memory system or completed optimization experiment.
