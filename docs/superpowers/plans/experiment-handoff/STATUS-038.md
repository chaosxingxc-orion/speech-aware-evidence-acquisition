# Status038: full multimodal system before local policy optimization

Date: 2026-09-11T14:29:38.697546+00:00. Source inspected: 7ed5f3021f6955c864c1bf7be74895aeaeeb68f2. Progress: owner architecture correction accepted, full system design and source-backed readiness recorded. The original goal remains active. No new GPU flight, optimizer or production runtime feature is claimed.

## Current direction

Read OWNER-MULTIMODAL-SYSTEM-FIRST-016 and docs/readiness/2026-09-11-multimodal-task-agent-system.md. Build the task-solving system: tool capability and real invocation, TRAIN declarative/episodic knowledge, current working state, memory consumption, Solver/Reviewer/Planner control. A binary retrieve/no-retrieve action is an eventual ablation, not the architecture. Keep SLURP first and E21/E22 later; native task metrics and OWNER014's quality/headroom objective govern selection.

The full system specification distinguishes fixed Planner and frozen-core Planner modes. The latter must really select a permitted action, dispatch it, consume a returned result and continue through the same frozen Solver and shared executor. Current catalog defaults are system-invoked; native tool-call output alone proves none of this. Preserve historical defaults and add an explicit configured mode.

## Completed this boundary

- Root inspected shared TRAIN construction, KnowledgeSnapshot, KnowledgeProvider, controller/phase Planner, tool catalog and multimodal transport. Existing TRAIN annotations are lawful BUILD inputs under the August23 rulings; evaluation references remain outside runtime.
- Audited three separate stores: TRAIN episodic/declarative knowledge; current-episode working state; later procedural experience/external policy. Proposed a common semantic action/result contract and complete path through existing bases.
- TRAIN snapshot has 11,514 content facets and values, covering 50,628 TRAIN source recording identities. Existing 11,514 retrieval keys embed TRAIN text; current 1,000 queries embed evaluation speech. They do not establish a complete TRAIN audio-memory index.
- Valid asset receipt: DATA coordination/slurp-train-multimodal-memory-readiness-v2.json, SHA256 f5360d2d8293448e3d0cdec281e209d3235d48982c253f11b5d42188c25b9e2d. It records 90 known promoted TRAIN decoder packets but unknown source-joined overlap/missing counts. V1 remains preserved and superseded: malformed trailing bytes and an invalid facet-minus-packet gap were corrected in v2, not silently rewritten.
- Root independently validated the snapshot with KnowledgeSnapshot.from_frozen_json. Raw file SHA16bc0becc16b6b8b2387c9c921b2b2ecf70a90effa863a974a805e29b5c1ffbb and canonical semantic SHA2c43147780b60fe64a3f46de5e9f6ab28b053f3a28a6900b2a92c04591541cf6 are intentionally distinct.
- Existing prepared recall has 1,000 rows, five facets each and a 2,621-TRAIN-facet union, all contained in the snapshot. This sizes a potential first audio-value preparation; it does not adopt a roster or establish missing recording count. Root receipt DATA coordination/multimodal-system-root-readiness-v1.json SHA7582ff0758ea4a6da1bf3b7c36ce1515fbc05c285e8439ea91933081d01173b9.
- A subsequent governed-loader join resolves all 2,621 recalled TRAIN candidates: 294 have one eligible recording, 2,327 have multiple, none have zero. DATA coordination/slurp-train-recalled-candidate-media-readiness-v1.json SHA6344964135820a133c6aba5cb41108ff10ba15e3600ba483801f96427018875d. Root verified the exact candidate set, source pins, canonical mapping hash, TRAIN identities and existence of all2,621 proposed selected media paths. The proposed per-episode lexical source-ID choice is not yet an adopted experiment roster; audio hashes/cache overlap remain to prepare. Media paths are relative to SPEECHRL_DATA_DIR.
- Paired VALUE evidence does not require TRAIN audio retrieval KEYs. Keep existing selection in the first text/paired modality contrast, fix the same episode/recording identities and prepare only their missing qualified decoder packets. Audio-key retrieval is a separate later factor.
- Metadata role audit found 102 speakers shared between OLD500/NEW500. A proposed whole-speaker 383/205/412 optimization/validation/evaluation partition exists only as readiness; it is not adopted or fresh confirmatory data.
- Root paused the not-yet-implemented binary supply policy. Its sole draft test is preserved outside pytest collection; no production code or historical configuration changed. The attempted --no-cov test command was rejected by pytest argument parsing, so no red/green runtime proof is asserted.
- Existing 2026 source review remains valid. It no longer chooses EvoTool as the first optimizer before the system objects exist.

## Next executable increment

1. Freeze the recording-selection rule over the now-complete source-to-media join, hash the selected media and audit existing decoder packets. This is a specific preparation task, not a request for a generic memory platform.
2. Extend shared memory views and the configured action/result bridge in KnowledgeProvider, EvidenceAgentController and the existing OpenJiuwen path. Preserve current query origin and source-bound TRAIN evidence.
3. Qualify real action -> tool -> returned state -> changed Solver request -> review/continuation -> delivery trajectories. The fixed policy is the attribution anchor; qualify the frozen-core Planner variant before locking the optimization system.
4. Prepare missing decoder packets once, restore one no-mmproj decoder, fit actual multipacket/stage requests and run prospectively registered direct/fixed/no-memory/text/paired comparisons consecutively. Compare fixed versus model-selected control with the same available tools/memory. Counts, roles, contact caps and scientific eligibility are prospective configuration, never recycled closed-flight allowance.
5. Freeze a useful system and its state/action/reward interface, then compare external-policy optimization against the fixed system and direct model. Transfer to E21/E22 without requiring large SLURP gains or exhaustive component/algorithm sweeps.

## Preserved results and service

All four previous E21/SLURP attempts are FINALIZED with complete official scores and settlement. E21 has PERSON benefit but failed historical insertion protection; the final SLURP matched pair failed its NEW500 primary/intent gates. Existing S3 component gains remain evidence; S4N failed non-inferiority and the old encoding/sample campaign remains held. No result is reinterpreted as fresh superiority and no old flight is reopened.

Latest process-only snapshot: wrapper35765, decoder35780 and monitor35824 alive at about2h30m elapsed. Resident serving-slurp-live-program-matched-np4-v1 stays on frozen source21ebe2bc8f9c03469a48fe0c68e9b31f1c360dff, c65536/np4/max256, no-mmproj. No current endpoint qualification or new model contact was made. This boundary performed source review, metadata preparation and documentation; it did not drive new GPU generation.

## Boundary verification

WSL experiment_handoff_check accepts generation38 with no errors; engineering_base_check and git diff --check pass. Root validated source/receipt JSON, shared snapshot loading, recall counts, media-join identities and proposed selected-file existence. No runtime test pass is claimed for this documentation boundary. Documentation completion is not implementation completion; the original goal stays active.
