# On-demand slot knowledge: implementation and execution checkpoint

Date: 2026-10-01 UTC. Status: **OFFLINE IMPLEMENTATION; F1 HELD; F2/F3 CONDITIONAL**.
Authority and boundaries: [owner-decisions.md](owner-decisions.md). The current coordinator retains shared checkout, queue and service ownership.

## Implemented

- Future manifests preserve the exact owner-allowance path and hash and validate on reconstruction. Historical failed bytes are untouched.
- The registered target-knowledge tool supports authored slot identifiers and an explicit reread mode. Targeted lookup selects at most two existing cards; reread selects at most two already-visible cards and cannot acquire a new one. Neither response asserts occurrence in the current speech.
- The shared dispatcher enforces one lookup per sample/execution unit across repeated Planner visits. A second request yields a source-bound rejection observation without contacting the tool. No automatic lookup is introduced.
- Optional `slot-issues-v1` Reviewer handoff validates, trims and deduplicates criticism. Invalid output stays explicitly invalid; raw responses remain sealed. The real native graph test verifies the normalized state reaches Planner and revised Solver.
- The consumption-module compiler produces the capability configuration and owns its optional tool block. An explicit construction-store component binds the existing minus-R01 exemplar release for ALL arms. Perception and first Solver instructions are unchanged. Historical absent options preserve request behavior.
- `prepare_knowledge_opportunity_family.py` delegates to the shared module compiler, runtime-subset helper and released-store loader. It refuses overwriting different prepared bytes and performs no model/tool/GPU/scoring contacts.
- Seeded metadata selection: ascending SHA256 of UTF-8 `20261001:<sample_id>`, with sample-id tie-break, first 400 of the existing R01C625. This precisely specifies the owner's seeded ordering before any outcome read. Receipt: `docs/receipts/rosters/slurp-knowledge-opportunity-r01c400-v1.json`.
- The source loader verified all three existing stores. Recording-independent source overlap with the whole R01C625 is zero for intent boundaries (60 values), slot-contracts v2 (54 values), and minus-R01 exemplars (8,554 values). See `source-binding.json`.

## F1 configuration and remaining preparation

`configs/experiment/slurp-native-stage3-knowledge-opportunity-v1.json` declares four HELD cells. A and A-prime use request-identical baseline fragments, separated only to bind each run's own preparation receipt. B and C use identical role templates, graph, tool schema, one-call bound and two-card return cap; only the registered selection mode differs. They are budget-matched opportunity arms, not cost-identical trajectories. B versus A measures the entire extra review/tool opportunity bundle; C versus B isolates selection of knowledge under that bundle.

The common base is compiled COMP-1b on lock v2.1, retargeted to R01C source-excluded construction knowledge and own query vectors. This is a matched construction base, not a claim that an old DEV run has identical knowledge bytes. Each arm runs its complete downstream graph and final delivery independently. Full-arm contact ceilings: A 4,400; A-prime 4,400; B 5,200; C 5,200. One official complete score per arm. Smoke and FIT must receive separate registrations before contact; draft generation ceilings do not authorize them.

Still required, in order:

1. Owner decision 213 now authorizes the fresh F0 pair under its own successor allowance. The new package must pass all launch gates; preserve old attempts and current queue until controlled handover.
2. Build the R01C agreement table with the existing `build_slurp_intent_exemplar_agreement.py`, using the common minus-R01 vote channel and this roster's packet/query identities. Register its model-free preparation first. COMPLETED: the exact 400-row agreement artifact is pinned as 5ea6962628beb137f60a7cd87b8e1253070954a093b577a6b5e5b5ffd496d223; every row has 20 votes. See agreement-preparation-completion.json. The initial older R01C skeleton was refused for missing discovery identity; the new identity-only preparation source binds the correct role and roster. No old registration was changed.
3. COMPLETED: each cell has its own prepared supply, pinned through the shared re-pin helper and verified warm against current inputs. All four selection-output hashes match. Two rows have no initial selected boundary card (both have sealed query vectors); all 400 rows remain in the flight and evaluation. The selection is unchanged from the frozen retrieval mechanism. See supply-preparation-completion.json, supply-output-equality.json and supply-warm-verification.json.
4. Freeze the new source version after serial integration. Register exact execution/budget/exposure documents and fresh service identity. Use the existing 4-slot decoder-only model fragment; any proposed geometry change needs a new comparison binding.
5. Real full-roster capacity checks must include largest legal tool returns, normalized Reviewer state, revision history and complete configured output reserves. Use only the coordinator-owned service. Do not treat a text estimate or fake-server test as a FIT receipt.
6. Four-row engineering proof of decline, empty return, targeted return and revision/terminal path through the same executor. No quality read or policy update from this proof.
7. Authorized independent background queue A -> A-prime -> B -> C. One generating flight and one complete scorer, with complete-family reading only after all four seals and score receipts. Monitoring does not dispatch.

## F1 analysis and promotion

Use official pooled SLU-F1 as primary and intent as a protection metric. Preserve all 400 rows, failures, fallback dispositions, tool refusals and empty returns. Report A/A offset and uncertainty before arm comparisons, using the inherited measurement instrument and its paired grouping, natural mixture and equal-stratum tables. Do not substitute mean per-row F1 for official micro F1.

The current registration declares `claims_benefit=false`: this is the explicitly authorized bounded capability exploration, with no measured effect forecast. It must not be reported as an admitted improvement simply because the offline floor checker passes. Before formal dispatch, freeze the complete analysis registration, including the inherited intent non-inferiority margin and the in-chain A/A-relative formal promotion rule. No threshold may be chosen after reading an arm. If the complete-system effect is uncertain, stop without opening F2 or changing subgroups to seek success.

Trace analysis must separate suspected issue -> model call decision -> returned relevant knowledge -> Solver consumption -> correct repair or damage. Compare B-A and C-B, as well as each nondefault arm against the same-chain baseline. Tool-use strata are explanatory post-treatment slices, never the decision population. Association between type and intent is a retrieval aid, not an output whitelist. Example fillers are never evidence of speech occurrence.

## F2: conditional implementation map

Reuse `rails.finite_action_policy`, `finite_policy_artifacts` and the existing source-verified terminal-feedback readers. They already implement immutable snapshots, complete-round updates, official-count utility, recorded probabilities, balanced allocation, epsilon-greedy sampling and sparse fallback at 20. Do not build another updater.

There is a material remaining runtime integration: `SystemEpisodePolicy` currently selects at episode start and explicitly refuses future state. F2 needs a registered decision seam AFTER the first Reviewer and BEFORE offering the Planner a handling opportunity. Do not rename episode-start selection as Reviewer-conditioned learning. Add this seam only if F1 admits a nondefault action, retaining the common Perception/Solver/Reviewer prefix and independent complete tails. Record the pre-action query-state hash, normalized review hash, draft-empty state, type/intent association, knowledge coverage, policy version, draw and propensity. These are runtime observations only; no labels or terminal state may enter allocation.

Build on R01C625, ordered and partitioned 200/200/225 before outcomes; first batch balanced over qualified actions including accept, later batches 80% current preferred action plus 20% uniform exploration. Freeze the policy inside each batch; run one complete official score on the batch and verify all terminal trajectories before calling the updater. Keep failed/fallback rows. Freeze F0 from the predeclared F1 A baseline official pooled score, in [0,1]. Utility is `2*TP - F0*(2*TP+FP+FN)` under the scorer's word/char count convention. Intent is separately protected. This is a contextual bandit with complete-system return, not GRPO or multi-step RL.

## F3 and closure

After three completed batches, freeze knowledge, states, actions and snapshot; epsilon zero. Run same-chain base and A/A, best fixed action selected on construction data, learned policy and feedback-disabled static policy through the same interface on DEV-2000-ADDED (1,000 already-exposed rows). Primary comparison: learned versus best fixed. Freeze the static policy before updates; do not select it from validation outcomes. No test labels, complementary-test rows or milestone results may update the policy.

If no learned advantage is established, report effective fixed configuration only. A final valid milestone comparison still needs its exact allowance and complete-family read gate. Audio2Tool and E21 remain held until SLURP closure.

## Operations

Keep GPU generation and scoring in Windows-owned WSL background tasks independent of network, credits and this conversation. Use one resident service per registered geometry, one generating flight and one scorer. CPU preparation is globally bounded at 20 idle / 8 during generation, further reduced for memory. Require at least 10 GiB Windows free memory and stricter startup floors. Use 10-second telemetry and the existing 15-minute script monitor. Never clear STOP, restart, retry, rescore, alter frozen sources or release dependencies automatically.

No new GPU or model contact was made while preparing this package. All GPU experiments and scientific verdicts remain outstanding.

## Validation at this checkpoint

389 related tests passed in WSL (387 combined, one historical Git equivalence proof and one prepared-config proof). The standard OpenJiuwen native-tool round-trip proof passed, as did engineering-base, catalog, algorithm-label, finite-completion, effect-floor, harness and results-ledger checks. Existing advisories remain documented in `validation.json`; a HELD cell without exposure registration is not admitted by these passes. The derived-media confinement check could not resolve the umbrella lock from this managed-worktree layout and is NOT claimed passed. Re-run that integration check with the canonical umbrella layout after serial integration. No new derived media mechanism is introduced here.

The successful broad suite ran without repository-wide Git environment overrides. An earlier interrupted invocation exposed a test-fixture/environment interaction affecting `core.worktree`; the exact injected setting was removed, with both HEADs unchanged, no staged changes and a clean main checkout. Keep Git overrides confined to read-only history checks, never temporary-repository tests.

The initial metadata/config derivation script intentionally refuses changed existing configurations. After receipt binding, use the existing shared re-pin tool, never rerun the initial derivation to erase pins. The gold-free analysis roster supplies the shared reader with utterance cluster and channel metadata.
