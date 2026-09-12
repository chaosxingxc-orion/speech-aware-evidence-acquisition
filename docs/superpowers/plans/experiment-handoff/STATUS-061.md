# STATUS-061: Speech tool configuration is ready for final binding

Snapshot UTC: 2026-09-12T16:02:15.258245+00:00.

Root integrated the local speech producer and tool inventory into canonical master at a486ba0275e4375ab9ebc46fd150c8378b738d61. See STATUS-060 for its 402-test validation, source export and exact local tool readiness.

Root reviewed the subsequent minimal three-phase program at a3757d67bcfd49d451fe6dac075f1fd2f08a48f4. It adds one policy fragment and its literal shared controller registration. The old plan/solve program is unchanged. The new plan -> solve -> revise program runs three bounded core phases, supplies knowledge for solve, and preserves its selected IDs/order into revise. The prospective treatment adds a finalized OBS tool result between solve and revise; control omits it. Both use the same new revision instruction and max_tokens 256.

Scoped WSL suites passed 113 tests, including the real shared-controller transition path with a synthetic OBS-like step and unchanged knowledge order. Ruff, engineering-base and whitespace checks passed. Root independently checked the planned control and treatment through the shared tool configuration loader and verified all declared retained fields and the live-fit contact formula. No real model, speech or GPU tool contact occurred.

Read docs/readiness/2026-09-12-slurp-speech-observation-design-v1.json and its program-validation receipt. The design is explicitly not runnable. Each arm targets 3,000 Qwen generation calls and requires 9,003 live-phase fit contacts on DEV1000; the separate shared Whisper preparation covers 1,000 clips. Freeze finite attempt/family budgets in the actual registration. Do not treat these counts or the policy fragment as execution authority.

The original speech remains available in revision. Existing compact-frame knowledge is retained; the treatment adds fallible transcript evidence and its provenance. Reviewer targeting and training-free optimization are later comparisons, not conclusions from this availability design.

The recovery campaign remains the sole active GPU experiment at source 22b56d706e2f5601dc79f58a8fad2bb6a9629f51. Root verified DIRECT and STAGE-CONTROL finalized and KNOWLEDGE generating; keep root campaign 2179, resident 620, and monitor 678. Read quality only after all three recovery manifests seal or a terminal hold, then use the frozen finalized-bundle analysis without rescoring. No second recovery is authorized.

Next: complete A2T closure and admission; bind the Whisper protocol, ExecutionPlan and exposure ledger; run its exclusive preparation window; bind the finalized catalog and independently prepared equal-content recall receipts into both SLURP arms; perform complete actual request fitting; run matched arms on one decoder-only service process; score and analyze native outcomes. The research goal remains active.
