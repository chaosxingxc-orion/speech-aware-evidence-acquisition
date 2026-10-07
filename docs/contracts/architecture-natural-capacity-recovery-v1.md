# Natural four-row prerequisite after one capacity recovery

Keep the ordinary `{registration, qualification}` prerequisite unchanged. Select
the recovery path explicitly in both paired registered generation/FIT plans:

```json
{
  "schema": "saea-architecture-recovered-capacity-prerequisite-v1",
  "original_evidence": {"relpath": "...", "sha256": "..."},
  "recovery_evidence": {"relpath": "...", "sha256": "..."},
  "root_disposition": {"relpath": "...", "sha256": "..."},
  "source_compatibility": {"relpath": "...", "sha256": "..."},
  "failed_contacts": {"relpath": "...", "sha256": "..."},
  "qualification": {"relpath": "...", "sha256": "..."}
}
```

Resolve these raw SHA-256 pins under the supplied data root. Use the original
evidence envelope and authority records accepted by
`qualify_architecture_capacity_recovery`; preserve original exit 1 and failed
endpoint spend. Give the completed recovery envelope the same fields:
`registration`, `original_registration`, `source_check`, `finished`,
`windows_exit`, `member_terminals`, `receipts`, and `pins`. The last field carries
absolute `{path, sha256}` pins for `registration`, `finished`, and `windows_exit`.
Keep their original filenames under each registration's `new_receipt_root`.
Keep the source check at its registered `frozen_preflight_receipts` pin, member
terminals at `<label>-capacity-finished.json`, and FIT receipts at
`<label>/request-fit-v1.json`. The validator re-reads these actual records and
compares them with the raw-pinned envelopes.

Write the recovery root qualification at the new entry's
`capacity-qualified-v1.json`. Use schema
`saea-simple-consumption-capacity-recovery-root-qualification-v1`, set
`runtime_admission` and `read_authorized` to false, and store the exact shared
recovery qualifier output as `result`. The natural validator recomputes that
result using independently composed original and recovery graphs and pinned
policies for every member. Do not substitute a synthetic all-success family.

Keep existing natural four-row roster, role, sampling, generation/FIT pairing,
contact ceilings, and no-scoring/no-learning checks. A returned natural binding
identifies the actual capacity registration and source commit for that member:
the original source for seed, A/A, and review-off; the recovery source for Solver.
It also retains source exits `[1, 0]`, failed-attempt endpoint spend, and the
canonical recovery-review hash. This library validation grants no contacts or
task-quality READ authority.
