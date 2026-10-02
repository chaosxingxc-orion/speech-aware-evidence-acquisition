# Owner220 pilot: precontact startup refusal and proposed bounded waiting

Status: **Owner221 APPROVES the8GiB resource amendment and the exact seven-member continuation.**

The human explicitly approved the concrete STOP disposition after all tests and frozen checks. Preserve historical pending statements below as the preparation history; the current [owner receipt](../../receipts/owner/2026-10-02-decision221-memory-amendment.json) supersedes them. Fresh live checks and exact control custody still precede dispatch.

## Observed incident

The first20-row L-parent completed generation, verified sealing and its single official score at13:35:30Z. The second member was refused at13:35:56Z before a worker, attempt or model contact existed. Its guard observed14.075386GiB free, below the unchanged14.5GiB startup requirement. Windows free memory was15.7933GiB at13:39:56Z. The first member's sampled running memory stayed above10GiB; no live campaign or scorer remained at inspection. No partial task-quality feedback was read.

The operational cause is the transition from a fixed20-second inter-member delay to a one-sample startup guard. The source of the host-memory fluctuation is not established; this record does not attribute it to a residual process or prove any WSL reclamation mechanism. The guard correctly refused unsafe startup by its registered criterion.

## Tested correction

Add an optional, read-only batch-boundary observer. Wait at most600 seconds for three consecutive observations at least12.5GiB,10 seconds apart. Do not create a worker, lease or attempt while waiting. Reset the consecutive count after any valid reading between8 and12.5GiB. Refuse immediately on missing/stale observations, a reading below8GiB, or an existing/new STOP. Expiry stops the queue. Re-run normal prelaunch checks after success; the original frozen process guard rechecks memory immediately before spawning. It uses the explicitly approved8GiB running floor and one-shot child semantics.

This observer does not flush caches, change host settings, kill processes, mutate frozen workers or retry execution. Old queues without these two optional fields preserve their previous behavior. The batch wrapper uses shared observation primitives. A new clean worker includes the operational8GiB minimum; candidate text/config, model-facing runtime and scorer bytes stay unchanged. Original4101a4925 artifacts and worker remain immutable. Historical callers retain the default10GiB floor unless explicitly overridden.

## Exact continuation to review

[The proposal](proposal.json) and [seven-member queue](remaining-seven-queue-v1.json) retain original order, identities, prepared supplies, roster, candidates, scientific budget, model-facing runtime/scorer source and eight-member READ gate. The20 completed first-member trajectories remain part of that gate. Only the140 trajectories in the seven never-started members remain. No re-generation, re-scoring or re-sealing of the first member is proposed.

Root must verify every precondition again, preserve the exact incident controls, and act only after the owner explicitly approves the new STOP disposition. Owner220 records `automatic_failure_recovery=false`; this is why the prior pilot permission does not itself restart this stopped queue. The full400-row family stays HELD.

## Analysis boundary

The family remains unread and its READ remains unsigned. After all eight qualify, use the registered exploratory diagnosis: valid handoffs and terminal custody, actual knowledge use, paired changes against own parent/A/A, correct repairs versus damage, pooled official quality, intent, completion and actual cost. At20 rows, estimates guide engineering hypotheses only; no stable-benefit claim or automatic scale-up is justified. A separate validated pilot analysis path must retain the normal400-row optimizer feedback minimum and prevent pilot feedback entering blind proposal sessions.


## Resource amendment and disk-backed material audit

The owner subsequently approved about8GiB free for Windows. Use8GiB as the running stop floor and12.5GiB before each member, retaining the previous4.5GiB loading headroom. Do not ask the owner again about that approved memory choice. Only reconciliation of this new STOP remains pending.

The live decoder process explicitly uses `--cache-ram 0` and `--no-cache-idle-slots`; its GGUF has two file-backed mappings in `/proc/942/maps`. Local weight bytes are already file-backed rather than an extra application RAM-cache copy. Linux still has reclaimable page cache; on-demand mapping does not mean zero OS cache. The pilot prepared phase-supply document is24419 bytes. Repository inspection identifies an eager JSON parse in `rails/knowledge_stores.py:load_knowledge_store_binding` and a retained composite snapshot in `FlightRuntime._load_knowledge_snapshot`. Current sequential processes already bound that lifetime to one member. A later indexed/lazy knowledge view needs equivalence/provenance tests before use; it is not silently inserted into this frozen comparison. No cache-release command, host change, model restart or scientific read was performed in this audit.

## Validation

The new observer, actual batch-shell routing and original process supervisor pass74 tests, with95% scoped statement coverage (observer97%, process guard94%). Tests cover the exact14.08GiB-to-ready transition, consecutive-sample resets, bounded expiry, STOP preservation, malformed/stale observations,8GiB acceptance versus7.99GiB refusal, unchanged default10GiB behavior, owned-child termination and no retry. The prior test failures demonstrated the missing waiting path and refusal of the newly approved8GiB policy before implementation. Engineering-base, lint and shell checks are rerun after final edits; no model or scorer is involved.

The prospective unsigned READ row's split role is corrected from construction to discovery to match TRAIN evaluation in the shared read gate. Its root signature is still absent. This clerical correction does not grant reading permission or optimizer exposure; the original frozen row is preserved.

## Exact clean preparation

All seven clean frozen model-free checks pass on `62b487e9be02b6c9e63379957f2275a640646ddc`; registration has zero blocking findings and seven historical tuning-alias advisories. Every unstarted attempt is absent and original live control hashes are unchanged. Runtime/controller/scorer and configs are byte-identical to the first member. The only changed source file is the operational process guard. The [final preparation receipt](../../receipts/continuation/2026-10-02-pilot20-owner221-ready.json) binds the frozen source and logs. This does not dispose of the STOP or grant automatic launch.

The three knowledge snapshots total15157907 bytes (about14.5MiB); their eager parser is not evidence for tens of GiB of memory use. Preserve this scientific runtime now and prioritize local file-backed weights, bounded per-member lifetime and explicit resource headroom. A speculative indexed-store rewrite is deferred.
