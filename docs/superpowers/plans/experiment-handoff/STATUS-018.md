# Status 018: enforce feature serving requirements before E21 restart

Date: 2026-09-10 UTC. Supersede STATUS-017 for coordination only. Preserve all sealed scientific artifacts, decisions and frozen worktrees.

## Current service and scientific state

Root verified no resident llama-server or active experiment/scoring process. The device query reported 0 MiB occupied and 0% GPU utilization. This turn performed source inspection, synthetic tests and code integration in WSL Ubuntu-24.04 only; no model, encoder, tokenizer or scorer contact occurred. Do not restart the normally closed G1/G2 sessions or replay their attempts.

The owner requirement remains: prepare neural speech features before generation and keep mmproj parameters out of resident GPU memory. Completed SLURP flights already used decoder-only packet input with --no-mmproj. Their geometry was request-bound: KU-S3 required 10,457 tokens at max256, exceeding an 8,192-token slot at c65536/np8, whereas G2 N/twin requests fit that eight-slot geometry. Removing mmproj does not by itself prove that a wider geometry fits. Recheck actual requests, output reserve and memory before choosing a new comparison geometry.

G2 remains HOLD_NONINFERIORITY_FAILED. G3 exemplar encoding and G4 a/b/c remain held. Preserve the separate G1 KU-S3 ADMITTED_COMPONENT result. Continue independent E21 engineering; G5/G6 remain incomplete.

## Integrated shared checks

Canonical 30dac31e integrates source faa03a28611fc6609be4d2882afbba7136a5cf4a. The sole server command builder now validates strict raw-audio cache serving before process creation. Require an explicitly bound strict-cache flag and existing absolute cache directory, the raw-audio legacy role, exactly the CPU-projector option and a pinned projector. Refuse conflicting model selectors and aliases, redundant model/projector environment settings, implicitly inherited strict mode and any declared/inherited VALIDATE presence. Preserve historical defaults and decoder-only packet inference. Root reviewed the pinned C++ argument parser and expanded alias coverage. Final validation: 52 focused tests; 208 focused/session/resident-session tests passed with six pre-existing platform skips; the new validator has 100% statement/branch coverage. Ruff and engineering base checks passed.

Canonical cf8c274f, 3ad416d1 and 4c82e542 integrate cache-audit source commits 514e6f2774b78976886e83b1c06efaac654c6e66, d89adeca28b9ae3b636599f9eb41fc4922fce9ad and fc6620d68b898266d0699f4d5c2fbdc7507b78c7. The public core.preparation_feature_cache helpers combine the existing exact-window inventory and strict legacy-cache inspector. Bind every request, deduplicated exact audio, encoder identity, cache root and chunk hash/shape. Refuse missing, malformed, stale, colliding or observed concurrently changed inputs. Recheck complete source inventory before sealing through shared prepare_artifact. Root independently ran the audit/inventory suite: 27 passed. Helper audit module coverage was 81%; Ruff and whitespace checks passed.

The audit state is cache-files-verified-runtime-unqualified. It does not prove encoding provenance, a runtime hit, an atomic filesystem snapshot or permission to generate. Preserve those limits in future consumers.

## Shared preparation entry integration

Canonical b66bdc6e integrates source ffb427aef5fc8847682ba75835e5b5887a0078d1. FlightRuntime and the shared CLI now expose prepare-window-inventory through the existing four-fragment loader, an explicitly declared campaign stage and output path, the composed ExecutionPlan and actual window materializer. Encoder identity derives from the pinned receipt and actual binary/weight files. Root required extraction of the existing stable file hash into core.preparation.hash_stable_file; both inventory and runtime reuse it, preserving the old inventory alias and semantics. No duplicate hash implementation or experiment runner was added. The helper reported 60 focused and 229 adjacent tests passing; the new runtime method has 94.5% line and 81.2% branch coverage. Root independently ran the combined merged serving/campaign/preparation/inventory/cache/successor tests: 156 passed. The merged engineering base check passed. Do not infer encoding completion from the inputs-only inventory. No active E21 config or contact budget changed.

## Required next work

1. Register a concrete model-free successor cell for the existing E21 construction roster using the now-integrated shared preparation entry. A held cell without the required plan/stage remains refused; do not manufacture a model-contact budget to make it run.
2. Connect complete cache coverage to source encoding provenance, preprocessing completion and normal-stop receipts, immutable per-request consumption and the raw-audio transport. The new audit helper alone is not that connection. Correct the runtime raw-audio preprocessing metadata only when the opted-in prepared-cache path exists.
3. Qualify the isolated cddb000c strict-hit runtime using a bounded registered construction proof. Preserve its original/source-build provenance. Structural Python tests and successful compilation do not prove cache hit/miss or decode-failure refusal before encoding; no qualified new runtime receipt exists yet.
4. Materialize fresh exact-window neural features through the shared registered preparation path, keeping mmproj outside resident GPU memory. CPU-only preparation is compatible with the owner instruction; a separately GPU-backed encoder window remains subject to the unresolved placement clarification. Do not use the old cross-build E21 cache.
5. Check every actual DR/LOOP request using the qualified root-owned service and one geometry per comparison. The held V2 configs are not executable GPU-mmproj fallbacks. Complete the bounded current-executor bridge, then accepted two-generation/four-delivery DR and LOOP/twin, followed by live complete-system baselines.

Root retains scientific decisions and the sole service. Lower-cost cloud assistant helpers performed bounded code/read tasks in isolated WSL worktrees. No editable-package reinstall, paid experimental API, new carrier, Stage-3 promotion, publication or automatic replay occurred.

Root integration receipt: docs/checks/speech-aware-evidence-acquisition/2026-09-10-feature-serving-integration/review.json. Final device/process recheck again found 0 MiB GPU memory used, 0% GPU utilization and no active experiment service.
