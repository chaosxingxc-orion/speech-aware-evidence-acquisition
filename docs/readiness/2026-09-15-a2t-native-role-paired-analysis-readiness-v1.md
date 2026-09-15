# Audio2Tool native-role paired analysis readiness

Date: 2026-09-15. Owner GPU hold remains in force after the current recovery stops.

## Scope and state

Prepare the frozen full4000 direct-versus-native-system comparison without reading either arm's task quality. The active source is the isolated worktree at commit 834d4d475ec4ffe0e9d61ea031746d5c2dd024ee. Do not edit that worktree during the flight. Preserve the completed direct arm's first official score and the sole recovery's original artifacts.

The existing analysis recipe is docs/readiness/2026-09-14-a2t-native-role-base-analysis-recipe-v1.json, SHA-256 7697ce0e8303fa2dd68f34a91bdfd9fc5e3322e986a923f4b11d570a2bb3f104. The decision rule is configs/analysis/a2t-native-role-base-decision-v1.json, SHA-256 6d7cd578f66c44cfc195fff4a2eb42f508e3546b4018918357f347161b468156. No statistical or decision field changes.

## Completed outcome-free preparation

The shared analysis.a2t_evo_capacity.domains_by_sample_id helper joined released-manifest domain metadata to the frozen roster. The projection contains only sample ID, query index, tier and domain. It is an analysis artifact and must never enter runtime requests.

| Check | Verified result |
| --- | --- |
| Exact unique sample IDs | 4,000 |
| Cross-tier query clusters | 2,097 |
| Tier counts | Eight tiers, 500 each |
| Domain counts | smart_home 2,792; wearables 857; smart_car 351 |
| Frozen roster counts | Exact agreement |
| Source stability | All eight released-manifest hashes unchanged across construction |
| Model, tokenizer, encoder and tool inference contacts | 0 |
| Scorer invocations and task-quality reads | 0 |

Evidence under SPEECHRL_DATA_DIR/analysis/SAEA-A2T-NATIVE-ROLE-BASE-ANALYSIS-V1/:

- metadata-preparation-intent-v1.json: records the allowed projection before construction.
- full4000-metadata-v1.json: SHA-256 98683bc8115c80c00e7d458ae13c6fdef68082d3539008e61460e06937a41952.
- metadata-preparation-receipt-v1.json: SHA-256 2bc9d362ddd87e21363a67a6e48e42a89b0392c10ebc3d8c0e9b26d0a3ef075c.

The direct complete scoring-batch metadata reports one successful job and full per-sample retention. Its quality remains unread. Its finalized manifest references the existing attached scores, so use score_source: finalized-bundle; do not fabricate a missing separate complete-score receipt or rescore the arm.

## Release and execution sequence

1. Reconcile the original campaign handle and its exit receipt. A watcher timeout is not an experiment stop. Preserve the GPU hold after any actual stop; do not restart, recover again, fit, encode or dispatch a successor.
2. Require both complete manifests and their first complete saved scores. If the recovery fails or lacks a complete manifest, preserve that failure and do not score a partial population.
3. Hash-bind both manifests, their attached first scores and the prepared metadata. Register the paired model-free outcome read in the exposure ledger before inspecting quality.
4. Instantiate the recipe without modifying statistical fields. Use the shared entry python -m speech_aware_evidence_acquisition.analysis.score_compare_cli --config <bound-config.json> --output <new-output.json> in WSL with the explicit frozen source path.
5. Use 10,000 paired whole-query-cluster replicates, seed 20260914, and at most two CPU workers. The primary exact-match contrast uses CI95; registered diagnostic contrasts use CI90. Report natural mixture, equal-tier and equal-domain sensitivity plus all tier/domain rows.
6. Read the outcome and perform attribution personally at root. Evaluate the frozen headroom threshold and published Table 3 reference exactly as registered. A promising discovery result requires a same-roster replication before a reproducible-benefit claim; no new GPU run is authorized by this document.

## Attribution boundary

The shared analysis.native_episode_diagnostics.analyze_verified_native_episode_statistics and receipt validators already support source-bound role/contact counts, task-tool events, Planner routes, revision counts, accepted/terminal/finite/abstention delivery and supplied-value metadata. Use a complete verified source, not partial workflow log successes.

The generic audit does not establish candidate coverage. Bind a separate preserved-trajectory join before reading that diagnostic, distinguish the official target from full multi-action coverage, and retain actual candidate widths. Lexical overlap with a supplied value is descriptive use attribution, not causal proof of benefit. Do not invent ordered full-call correctness or a repo micro-slot-F1 paired interval absent the required persisted counts.

This readiness note is not a quality verdict, a GPU admission or an algorithmic training-free RL result.


## Frozen native attribution recipe

Before either arm's paired quality read, root froze the descriptive definitions in SPEECHRL_DATA_DIR/analysis/SAEA-A2T-NATIVE-ROLE-BASE-ANALYSIS-V1/native-attribution-recipe-v1.json, SHA-256 31ac67fbaf2f031d53367be03169ef1eeb9b09d7584173696314d7b2015843bd. This is a definition receipt; source bindings and implementation of the A2T-specific join are still pending complete seal.

Use the active Audio2Tool parser in rails/a2t_perception_state.py and the actual Audio2ToolCandidateSemanticProvider candidate_occurrences/selection receipt. The similarly named analysis/native_candidate_stage_projections.py imports the SLURP parser and cannot substitute for the Audio2Tool projection.

Distinguish the saved official primary tool's union membership from complete ordered action-occurrence coverage. For the latter, a repeated gold tool requires a separate matched candidate action occurrence; preserve order and separately report extra proposed actions and strict equal-count positional coverage. That full-action diagnostic needs separately bound scorer-side action-name sequences and must not be guessed from the official primary-tool metric. Retain unavailable source rows and denominator coverage rather than silently treating absent receipts as observed misses. The primary effectiveness decision remains unchanged.
