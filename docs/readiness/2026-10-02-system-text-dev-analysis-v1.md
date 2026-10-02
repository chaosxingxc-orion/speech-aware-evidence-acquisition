# System-text DEV endpoint analysis: offline engineering

Owner scope: decision214. This implementation completes the analysis entry point for the registered four-system DEV endpoint. It adds no proposal, model, tokenizer or scorer contact and reads no current scientific output. The current update1 worker remains frozen.

## Shared analysis and endpoint isolation

`scripts/analysis/system_text_dev_read.py` verifies the exact root READ using the existing ledger predicates, then validates the frozen DEV stage against its pinned protocol and ordered1000-row roster. It binds all four systems (`seed`, `seed-aa`, `L-frozen`, `B-frozen`) to their registered run/attempt identities and compiled configuration hashes. All operational metadata must qualify before seal verification; all seals must pass before complete score receipt verification. A COMPLETED manifest alone is never sufficient. Missing members, wrong partitions, duplicate score jobs, a failed official score, changed configuration/roster, an incomplete receipt or unsigned READ refuse the report. The final custody/authority check occurs again before publishing the summary.

The existing Stage-3 paired reader provides the official pooled sufficient-count reconstruction, paired utterance bootstrap, per-stratum tables, natural-mixture and equal-stratum views, structural errors and existing cost/frontier diagnostics. No scorer is run. Five prespecified pairs cover the seed/A/A null, primary L-minus-B, secondary L-minus-seed and each frozen branch versus the in-chain A/A. The last two are diagnostic null-context comparisons, not new primary claims or new system evaluations. Root still applies the registered measurement rules; the script returns a descriptive report and never adopts a policy.

The separate execution summary reuses native terminal/role/tool trace accounting, including failed contacts, abstention, reliable completion and missing responses. Unknown token totals stay null. The same-cohort point-estimate Pareto view reuses the search archive's non-dominance predicate on official SLU-F1, intent, actual model contacts and actual tool contacts. A/A remains a distinct measured point even when its bundle matches the seed; no replicate averaging occurs. Token and GPU-time diagnostics remain separately reported, and no matched-realized-compute or statistical-superiority claim follows from the frontier. Legacy pair-level wire diagnostics must be interpreted with their explicit completeness flags; the attributed endpoint execution summary is authoritative for missing token usage.

The new optional frontier identity key leaves the default search behavior unchanged. The READ helper's default remains discovery; DEV is an explicit endpoint-only scope. The `CompleteSystemFeedback` and reward-link learning paths remain TRAIN-only. Endpoint reports can only be created in a fresh data-root `analysis/` subdirectory, never in the policy archive. They are not feedback capsules or policy updates.

## Future registration and use

Before the real DEV flights, register an analysis recipe containing its exact READ ID, `family_id: dev`, the four `expected_members`, the frozen `system_search_stage`, matching `system_search_evaluation`, pinned repository `protocol` and `roster`, and the four original `attempts`. Copy the driver's fixed `COMPARISONS` mapping into `comparisons`. In `analysis`, register `cluster_key: utterance_id`, the resampling seed/draw count, and the hash-pinned offline `gold_bank` (`data_relpath`, `sha256`, `roster: dev2000-added`). The bank must carry the existing `stratum` field for every DEV row. No missing-strata fallback may silently publish a complete report.

After all four members qualify operationally, collect a family specification with exactly `family_id`, `expected_members`, `read_registration` (the pinned recipe), and `bindings`. Each binding contains its pinned finalized `manifest`, original successful `score_batch` and `complete_score_receipt` including its `cell_id`. A separately recorded saved-score envelope may bind finalized bytes without rescoring, through the existing receipt verifier. Never invent future manifest hashes in the prelaunch recipe. These post-flight pins do not alter preregistered identities, comparisons or configuration.

Only after the exact root READ countersignature may the offline entry point run:

```text
python -B scripts/analysis/system_text_dev_read.py --family <complete-family.json> --repo-root <registered-checkout> --data-root <speechrl-data> --output <speechrl-data>/analysis/<registered-dev-read>
```

Set `PYTHONDONTWRITEBYTECODE=1`. No real DEV recipe was registered or countersigned by this engineering change. No DEV label/quality/answer was read. Actual finalists, supplies, capacity and execution remain future prerequisites. Historically exposed DEV is a regression, not fresh independent confirmation; one three-update sequence does not establish stable recursive improvement.

## Verification

Test-first verification reproduced the missing analysis entry point (20 failing cases) and the missing replicate identity option (one failing case). All181 related tests now pass. Statement coverage is99% for the endpoint reader,98% for the shared archive and99% combined; the endpoint's only uncovered statement is the direct module entry guard. Ruff, engineering-base and harness-admission checks pass.

The integration test runs the real standard paired analysis over four synthetic1000-row systems and checks all five pair outputs, both stratified weightings and omission of a sentinel answer string from report artifacts. Seal/score verifier hooks and native terminal extraction are stubbed in that integration; distinct refusal/order tests verify the gate sequence. Existing native terminal and official receipt verification remain reused, not replaced. No synthetic quality value is experimental evidence.

## Live checkpoint

At2026-10-02T04:51:51Z campaign process243879 still matched the registered frozen update1 worker2f07dd3d6. L-parent is FINALIZED with400 rows and exactly one successful official score/zero failed scores after2793 contacts. L-parent-AA is OPENED with2226 contacts; the three B members have not started. Contacts are not completed rows. STOP is absent, service is healthy, telemetry is3.363 seconds old, GPU uses22976MiB and Windows has11.91GiB free. The whole five-member READ remains unsigned; no current result was interpreted, queue changed or held carrier released.

Machine-readable evidence: [receipt](../receipts/continuation/2026-10-02-system-text-dev-analysis.json).
