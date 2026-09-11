# SLURP-first system baseline and training-free optimization

**September 11 owner correction:** The [complete multimodal system specification](2026-09-11-multimodal-task-agent-system.md), under OWNER-MULTIMODAL-SYSTEM-FIRST-016, supersedes this document's binary supply-action implementation and early optimizer priority. Keep the saved result/headroom analysis below as historical evidence. Build tools, TRAIN episodic memory, state and evidence-use control first; retrieve/no-retrieve remains a later component contrast.

Authority: OWNER-SYSTEM-OPTIMIZATION-014 and OWNER-SLURP-FIRST-2026-RL-015. Status: root-reviewed implementation and experiment design; no new model contact has occurred for this design. Supersede the E21-first proposal in the earlier September 11 selection note. Retain E21 and E22 as subsequent transfer stages.

## Decision and evidence

Select the existing SLURP shared live intent-to-slots system as the engineering starting point. Short independent utterances, prepared speech packets, a working two-phase executor, completed official per-row scores and replicated retrieval-component effects make its feedback loop simpler to inspect. This is an engineering selection, not a claim that the full system reliably beats direct calls.

The fixed-predecessor S3 replication supports retrieval benefit: NEW500 mean per-row SLU F1 gain 7.1810 percentage points over its matched control, CI90 [5.2226, 9.1592]. Preserve original examples, all 60 legal labels, the approved 256-token completion bound and source-bound prepared retrieval. Do not infer full-system gain from that component estimand.

The final freshly generated, program-matched system comparison has NEW500 mean per-row F1 gain 1.0187 points, CI90 [-0.9059, 2.8329], and intent -0.2 points. It failed its historical admission and is closed. Its direct normalized intents agree on only 466 of the 500 NEW500 items despite equal structured direct requests. A new action comparison must isolate that source of variation.

Read the unchanged [final system result](2026-09-11-slurp-program-matched-result.md). Do not reopen the final pair to search for a pass.

## Is SLU too simple?

Do not infer policy headroom from the gap between the score and 100%. Acoustic/model errors may be inaccessible to any legal external action. Conversely, a short horizon does not imply a trivial evidence decision.

An additive, model-free reuse of the sealed official scores gives:

| Population | Retrieval better | Retrieval worse | Equal | Mean row-F1 change, points | Retrospective per-item max-of-two above control / retrieval, points |
|---|---:|---:|---:|---:|---:|
| NEW500 | 46 | 35 | 419 | +1.0187 | +5.3707 / +4.3520 |
| OLD500 | 50 | 35 | 415 | +2.7285 | +6.7531 / +4.0246 |
| DEV1000 | 96 | 70 | 834 | +1.8736 | +6.0619 / +4.1883 |

Source: DATA coordination/slurp-existing-pair-headroom-audit-v1.json, SHA256 96ab7d24fb30e55ff771fc16e6d6f73b00ff601b8b2f2478ffd67e7f100373bf. It pins both scores, roster, paired analysis and semantic identity receipt. No scoring or model contact was repeated.

This is descriptive complementarity between two realized outputs. The max-of-two uses outcome information unavailable to a deployed controller and includes generation noise and unequal direct states. It is neither an achievable policy estimate nor an unbiased causal retrieval effect. The semantic receipt has aggregate intent agreement only, so a same-intent F1 subset is not asserted.

Three questions determine useful headroom:
1. Under the same current state, do legal actions lead to different quality outcomes?
2. Do runtime-visible features predict useful choices on examples excluded from that update?
3. Does the frozen updated policy improve over the fixed agent when the complete system generates its own state?

If the first answer is no, stop expanding SLURP actions. If the first is yes but the second is no, preserve the fixed agent and record a state/feedback limitation. If a working interface yields only small or uncertain gains, it may still be locked as the engineering baseline and transferred. Do not make a large gain a prerequisite for E21.

SLURP mainly exercises short-horizon evidence supply and answer use. It cannot establish long-call temporal credit assignment, speaker/topic memory or multi-turn observation quality. Those are reasons for later E21/E22 transfer, not reasons to manufacture extra SLURP steps.

## Freeze the smallest useful agent first

Reuse TaskAdapter, KnowledgeProvider, EvidenceAgentController, FlightRuntime and the existing OpenJiuwen executor.

Current executable sources:
- configs/baseline/slurp-live-program-matched-control-v1.json and the speech counterpart compose experiment fragments of the same names.
- Both run phase-direct-then-slots-supplied-v1 with a whole-roster wave barrier.
- Direct preserves the original full task response contract and seals its state; slots consumes its predicted intent and state through append-sealed-state and slurp-intent-slot-schema-for-state.
- Control has empty phase_supply; speech binds slots to the existing kb-facet-v1 supply and prepared recall pins.
- The shared controller already calls _resolve_supply(next_phase, staged) after sealing direct state. Preserve that state and the slots phase.

The first new action surface is exactly:
- use the already registered slots retrieval supply;
- explicitly supply no retrieval while still generating the same slots task.

These are row-level choices from a single registered policy artifact, not different experiment runners. Neither choice skips the slots phase; a direct-delivery early-exit policy would be a different comparison. No schema narrowing, diarization, exemplar encoding, unconstrained memory rewrite or extra review call is required for this first seam.

The existing phase_planner decides early-stop/continue and cannot express this supply choice. Add a registered supply-action policy at the existing transition boundary, not a new controller or a repurposed early-exit declaration. Preserve old config defaults and request semantics. Trace a no-supply choice explicitly just as retrieval is traced.

Only add bounded revision versus deliver after the first routing seam establishes a named USE error and an actionable flag. Maximum one revision is a later design bound, not an already implemented or registered flight. OBS remains fixed on the first SLURP base.

## Shared external policy contract

Use the existing source-bound AgentRuntimeContext and AgentStateArtifact. Project an allowlist of current legal state: draft and response identity, valid predicted intent, source speech identity, declared task and phase, available evidence provenance/similarity metadata, prior executed actions and available runtime flags. Use sample IDs and hashes for custody, never as a memorized correctness lookup. Exclude references, gold entities, future content and offline correctness from runtime state.

A decision record binds policy ID/version/hash, legal state hash, candidate action IDs, chosen action, any behavior probability, source phase/response and transition. Do not fabricate a propensity for a deterministic action or treat verbalized confidence as calibrated probability.

Separate interfaces:
- runtime selection consumes frozen policy artifact plus legal state and action mask;
- post-seal reward extraction consumes existing complete official scores and trajectory bindings;
- offline update consumes permitted quality feedback and legal trajectory projections;
- freeze emits a new policy artifact and then evaluation disables all updates.

Initially preserve the original S3 retrieval payloads. An external memory stores strategy/utility and provenance, not a new gold-bearing answer dictionary. No upstream runner or independent experimental model is imported.

## Optimization sequence and comparisons

1. Complete the descriptive reuse above and exact action/state mapping. This work is now done.
2. Implement the narrow shared supply-action seam and meaningful model-free tests: both choices reach slots; same-state prompt/fit behavior; policy and state binding; no gold-bearing fields; old configurations unchanged. Prepare roster roles and action-group configurations in parallel.
3. Register a bounded SLURP discovery action cohort. Generate each current direct draft once, then branch the two supply actions from that exact sealed state. Predeclare an independent same-action noise comparison only if needed to interpret action dispersion. This cohort estimates component headroom; it is not a substitute for live end-to-end evaluation.
4. Use the 2025 TF-GRPO mechanism as the first engineering feedback baseline: grouped outcomes, contrastive feedback and bounded external experience updates. Implement through the shared contract, not through the upstream paid-API runner. The upstream ground-truth-to-prompt default is disallowed; use score-only feedback with legal traces and explicitly label the adaptation.
5. Compare one 2026 optimizer on the same action surface and update data. Prioritize EvoTool-style targeted module evolution for the first system-level challenger. Keep MemRL-style external utility updates as the narrow memory RL comparator once a useful experience store exists. Do not add memory solely to fit a paper, or blend methods before learning which mechanism works. See the companion 2026 source audit.
6. Freeze the updated artifact before a disjoint evaluation pass. Report optimized-minus-fixed-agent and optimized-minus-direct separately. Then transfer the same interfaces to E21 even if improvement is small; distinguish engineering closure from uncertain scientific gain.

Freeze update, validation and evaluation membership before reading new outcomes. Use speaker-disjoint partitions where feasible; check metadata coverage first. Existing OLD500/NEW500 labels do not prove speaker disjointness or freshness. NEW500 is historically exposed. Any reuse supports bounded discovery with full exposure disclosure, not a fresh confirmatory claim. Evaluation comparisons need the existing n >= 400 standard; a four-row dry run proves only engineering.

Do not tune a policy against evaluation results or choose a favorable stratum. Repeated validation is optimization data, not an untouched test. Freeze the update schedule and attempt limits prospectively. Keep quality as the objective: official slot metrics with intent/scenario/action protections; report both mean row-F1 and micro counts, natural mixture and equal-stratum results. Do not optimize solely for JSON validity or reviewer confidence. Keep cost/utilization as receipts, not reward penalties.

## GPU rhythm

Keep the existing decoder-only service geometry while the SLURP source/configuration is stabilized: prepared source packets, no GPU mmproj, c65536, four concurrent slots, actual max output 256. The runtime still requires complete identity matching and a newly registered lease; this plan is not a dispatch receipt.

Prepare both action branches and their fit inputs before dispatch. One root service and one generating flight use all admitted slots. Capacity checks use actual composed requests and their own registered contact allowance. Run one complete official score per sealed manifest, overlapping the next technically and scientifically eligible wave. Hold global CPU preparation at the existing 20 idle / 8 campaign limits. Avoid model reloads between eligible same-geometry cohorts.

The current source-only literature review and saved-score audit made zero new GPU contacts. The existing service remains resident; a process snapshot does not by itself establish health at the next dispatch. Do not fill idle time with closed experiments or held exemplars.

## Transfer and stopping conditions

Lock SLURP engineering when configuration alone reproduces the direct/fixed/updated policy paths, actions change actual execution, reward lineage is exact, frozen evaluation cannot update memory, and a complete registered feedback cycle has executed. Statistical improvement is reported with its uncertainty and is not silently assumed by this lock.

Next extend the shared action surface to E21: preserve versus constrained repair, selected re-listening and bounded legal context. Complete its current Reviewer/Planner/selected-observation seam at that point. Preserve its current PERSON benefit and insertion limitation. Longer tasks can then test temporal credit, context conflicts and selective acquisition, while native WER/entity metrics remain primary.

E22 follows the E21 interface and packet/preparation readiness check, with its own dataset identity, split/admission, official metrics and registered experiment. The owner has named it as a later destination, not authorized an implicit carrier identity or an immediate unbounded campaign. Speaker/topic summaries remain hypotheses to test against dataset-native tasks.

Do not block transfer on exhaustive SLURP searches, all 2026 optimizer ports, large gains, new general-purpose infrastructure or completing the held S4 branch.
