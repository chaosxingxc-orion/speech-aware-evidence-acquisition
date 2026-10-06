# Capacity terminal evidence for structural entry

Capture the exact current capacity task after it is terminal. Do not reuse the
old update4 terminal record or its failed epoch.

- Task: `SAEA-Update5-Aggregate-Capacity-V1`.
- Coordination: `coordination/partitioned-update5-aggregate-capacity-owner227-v1`.
- Registration SHA256: `b3dc8c07e8b20ac5500caefd98385e60a97272077c16ad0e66e51c8c7b3b99fd`.
- Original launch epoch: `2026-10-06T10:26:37.3217847+00:00`.

Read the original `capacity-started.json` with a JSON reader that preserves the
epoch as a string. Set terminal `launch_epoch` to that exact original string;
do not replace it with a Scheduled Task local-time display or reserialize it
through a local-time DateTime object. The qualifier deliberately binds the
original epoch exactly. A historical failed update4 terminal file uses a local
offset and is neither authority nor an output template for this epoch.

Before writing `windows-task-terminal-v1.json`, verify all of the following:

1. The exact task is terminal and its actual result agrees with
   `capacity-finished.json`; check the bound registration hash and original epoch.
2. The original Windows owner process is absent by identity, not just by a stale
   PID. Record any PID reuse separately rather than treating it as the owner.
3. Every configured Windows observer is terminal, and the corresponding member
   exit/lease/guard/observer receipts retain their actual exit codes.
4. No admitted WSL entry, lease or capacity worker remains for this coordination
   directory. Revalidate process command lines and start identities.
5. Delete `slurp-update5-capacity-monitor` after terminal verification. Keep all
   original logs, outputs and runtime controls unchanged.

The terminal record uses schema `saea-windows-task-terminal-v1` and includes
`at_utc`, `task_name`, integer `exit_code`, task `state`,
`registration_sha256`, original-string `launch_epoch`, and verified
`owner_process_absent`, `observer_process_absent`, and
`wsl_entry_processes_absent` booleans. Preserve failure truth; never convert a
failed or incomplete family into success.

Only a complete successful family may proceed through the prepared
`qualify-capacity-v1.py` and shared `qualify_capacity_family`. That qualifier
checks every configured member, all source/graph/config bindings, measured
request reserves, actual contact caps and immutable output hashes. Capacity
qualification grants no task-quality read and does not itself dispatch a
structural or scientific worker.
