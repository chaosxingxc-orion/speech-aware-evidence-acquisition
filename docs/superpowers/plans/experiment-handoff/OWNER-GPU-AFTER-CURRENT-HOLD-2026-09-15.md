# Owner directive: hold GPU experiments after the current task

Recorded at 2026-09-15T05:50:47.817968+00:00.

Owner instruction, translated from Chinese: After the GPU task stops, pause starting GPU
experiments.

Allow the currently running Audio2Tool native full4000 recovery to complete. When that task
completes, fails, is interrupted or otherwise stops, do not start another GPU experiment until
the owner explicitly resumes GPU work. This supersedes the queue-launch portion of
OWNER-GPU-RESUME-013 and the previously planned immediate SLURP handoff.

Hold the queued SLURP successor, prospective E21 experiments, new GPU encoding, new model
capacity checks and automatic experiment restarts after the active task terminates. Existing
registered contacts required to finish the current active task may continue.

CPU-only preparation, synthetic verification, complete scoring and scientific analysis may
continue. Preserve the earlier owner preference against proactively unloading the model merely
to release GPU memory. This scheduling hold neither changes an active comparison's geometry
nor rewrites any scientific or exposure record.

At the directive boundary, the verified active campaign contains exactly one cell:
a2t-native-role-dual-store-union4000-recovery-v1. The campaign and supervisor handles were
present. There is no queued successor inside that campaign plan. Root owns any later dispatch;
the bounded observer and CPU coding agent have received this directive.

Canonical handoff state and DATA/coordination/gpu-after-current-hold-20260915-v1.json record
the hold. This document is the scheduling authority; the receipt does not claim a new global
runtime gate has been added.
