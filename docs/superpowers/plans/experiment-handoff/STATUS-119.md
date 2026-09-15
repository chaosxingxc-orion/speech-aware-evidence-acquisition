# STATUS 119 - Raw native fit integrated; crash dumps reviewed

Recorded at 2026-09-15T03:28:02.712353+00:00. Root owns scientific decisions and attribution.

## Live experiment

The exact Audio2Tool recovery process 25213 was verified live: true. Its attempt is OPENED, with 1993 metered model contacts. Contacts are not completed sample counts. A whole-run seal is not expected before generation completes. The current exit receipt is absent.

The active checkout remains frozen at 834d4d475ec4ffe0e9d61ea031746d5c2dd024ee. The diagnostic work did not modify its code, service, configuration or outputs. Preserve the one named recovery limit. Direct quality remains unread pending the registered paired release.

## Integrated shared engineering

The shared native-contact capacity gate now supports the explicit raw-speech-agent-native-tools arm. It validates the prepared raw identity against the actual rendered audio bytes, uses the resident multimodal measurement endpoint, rejects mixed raw/feature input and non-raw text arms before contacts, and preserves the legacy feature endpoint protocol.

Root reviewed the implementation, required shared control-identity validation and corrected callable selection, and independently ran the raw/native/control/fit regression: 359 tests passed. Two source commits 49e23e43d2eb37774a3539595aa027c92e5c01c3 and bdecfa8cca0ec675a0d8e33e5dba5691dccfd5e4 were integrated into local master. Canonical code HEAD: 3153a60d4f87da96a9adfeb2ad5b8ccce3344bb8. The integrated source/test bytes match the verified worktree. No remote push or model contact occurred.

Evidence: coordination/a2t-native-role-control-recovery-v1/root-raw-native-fit-verification-v1.json and root-raw-fit-integration-and-live-recovery-v1.json under SPEECHRL_DATA_DIR.

## E21 remaining integration

Raw client, transport, public native runner and actual per-contact fit are implemented. E21 window execution is not yet enabled and no E21 native quality claim is made.

The next bridge must reuse the existing 1,593-window SliceRegistry inventory and preserve the 44-call split. The public runner currently requires one speech binding per sample; it cannot represent all windows merely by looping over the same call identity. Native contact IDs and fit ceilings must bind an explicit registered window/episode identity, with whole-call stitching and complete-manifest scoring retained. Do not fabricate feature descriptors or replace call sample IDs with window IDs. Do not add a private experiment executor.

## Root crash-dump finding

The owner provided readable copies of both minidumps. Root analyzed both locally with matching images and Microsoft public symbols. Both show 0x116, the same nine-frame GPU reset/recovery stack, the same NVIDIA image PE identity and the same responsibility pointer offset nvlddmkm+0x19b1050. The matching NVIDIA image version is 592.01.

This narrows the next stability investigation to the NVIDIA driver/device recovery path. It does not identify the original CUDA request, prove a driver software defect or establish VRAM exhaustion. Windows Update restart prevention remains a separate issue. No system settings were changed.

Evidence: coordination/restart-root-cause-20260915-v1/ROOT-DUMP-ASSESSMENT-v4.md and root-dump-comparison-v1.json. The prior missing-copy blocker is resolved; the initiating defect remains unknown.

## Next execution order

1. Keep the admitted Audio2Tool recovery running; on terminal state, verify sealing, actual accounting and the first complete official score before root releases paired task-quality analysis. A second full failure closes this flight.
2. Preserve the replicated SLURP base and the root breadth analysis from STATUS 118. Prepare the next compact discriminative-value/candidate workspace while keeping actual candidate coverage distinct from knowledge-card availability.
3. Finish the E21 registered-window bridge and shared stitching/fit accounting before preregistering a bounded live raw native proof.
4. Select a concrete maintenance-time driver intervention only after checking device support and rollback availability; do not change the live comparison geometry or restart Windows mid-flight.
