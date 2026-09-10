# Shared OBS wire-check verification

Date: 2026-09-10 UTC. Review base: 7c2f34f3. This is model-free engineering work under the existing shared-base continuation, not an exposure registration or scientific admission.

## Defect and intended behavior

FlightRuntime.wire_check treated every policy other than fixed as a registered phase program. The shared OJW OBS policies are window policies, so the method refused them before reaching the existing driver. A whole-call roster also cannot provide the right contact count: one call can produce several selected windows.

Route supported fixed/explicit-plan OJW OBS configurations through the existing actual-window materializer and _dispatch_obs_policy/core.driver.run_experiment. Substitute only WireCheckGate and WireCheckTransport. Bind preparation, request routing, attempt accounting and artifacts to a fresh WIRECHECK identity; never borrow the registered run's namespace. Size the synthetic successful-contact plan from the exact materialized windows. Validate full normalized request-boundary content and one-to-one identities independently of concurrent arrival order, count every simulated request and verify stitched output coverage.

Always abort the synthetic attempt after dispatch and restore the original runtime state. Restore it even if dispatch, abort or the post-cleanup observer fails. Preserve the synthetic spent-attempt evidence. Invoke observers only after abort and restoration. Explicitly refuse unsupported scoring and concurrency override options before materialization rather than ignore them.

## Scope and limits

Call wire_check(seal_and_score=False) for this path. OBS owns its core adapter and deliberately has no FlightRuntime FrozenCoreClient; the existing wire-check seal/scoring path assumes that client. This extension therefore does not prove OBS bundle finalization or official scoring. Their existing production paths remain unchanged and still require separate evidence. Plain/adaptive OBS policies and rotated evidence remain outside the exact-window materializer's supported scope.

The method's contact_count/cost describe synthetic adapter attempts. model_contacts remains zero. No model service, tokenizer, speech encoder, paid experimental API or real scoring task is admitted by the receipt. Synthetic audio and local test fixtures establish request wiring and cleanup only, not strict-cache neural behavior, capacity, throughput or effectiveness. Original scientific configurations, budgets, raw artifacts and verdicts remain unchanged.

## Validation required before integration

Prove the pre-fix refusal; exercise the real shared OpenJiuwen repair path on four synthetic windows and one stitched call; show no fifth request or socket; compare materialized and dispatched boundaries; inject failures and verify cleanup and original-run isolation. Run the existing wire-check and adjacent OBS/controller tests, then the engineering-base and style checks. Record actual test results in the root review receipt rather than treating this checklist as evidence.

## Root validation outcome

The root review passed 9 focused cases and 296 adjacent regression cases across the existing runtime, OJW OBS, window controller, request fitting and phase execution tests. The real-driver success and injected-failure cases refuse socket connections and retain synthetic spent-attempt evidence. Ruff, the engineering-base check and whitespace validation passed. Three existing dependency deprecation warnings remain. Read [the root receipt](../receipts/obs-wire-check-root-review-v1.json) for code hashes, exact scope and corrected verification assumptions. No scientific setting or model service was changed.
