# Root host-restart diagnosis, 2026-09-15

Root reviewed the delegated Windows/WSL evidence, independently checked nine
Windows event hashes and recomputed the two historical monitor summaries.

The September14 19:15-19:18 UTC loss was planned Windows Update servicing.
Earlier host failures around September13 23:17 UTC and September14 05:02 UTC
were confirmed VIDEO_TDR_FAILURE (0x116) bugchecks. Their exact initiating driver,
resource or hardware cause is unresolved. Event41 times are reboot records,
not exact crash times. Surviving samples do not support host-RAM exhaustion
or show all four slots busy at either last sample.

Keep the immutable local evidence outside Git:
DATA/coordination/restart-root-cause-20260915-v1/ROOT-REVIEW.md
SHA256: 045173d9b0e5703d59e57f2fd6ef2c10191f837cb11f4aff9c02b1ae2bde0199

The evidence directory includes the original report, telemetry supplement,
event/telemetry verification, source review, and official debugger acquisition
receipt. Raw dumps were not read: Windows denied the non-administrator account.
Readable owner-provided local copies are required for module-level analysis.

No system setting was changed. Keep Windows update maintenance distinct from
the GPU bugcheck investigation. Do not disable TDR or change registered serving
geometry mid-comparison. Preserve completed SLURP and Audio2Tool proof products;
the planned update occurred after their normal completion.
