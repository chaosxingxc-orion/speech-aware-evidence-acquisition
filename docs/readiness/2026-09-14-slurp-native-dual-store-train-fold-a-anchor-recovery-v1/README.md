# Sole native TRAIN A recovery after CUDA failure

The original full1080 Fold A anchor aborted after a recorded CUDA illegal
memory access. Five requests were charged; one answered and four did not.
No sample completed the native episode and no manifest or score exists.
The owner subsequently rebooted and explicitly requested service restoration.

Root restored a fresh process with the same frozen model, no-mmproj geometry,
four 24,576-token slots and max512. Preparation output is exactly unchanged
and warm reuse invoked no producer. Root preserved the aborted attempt and
reconciled its stale lease only after the old process, port and GPU were
verified quiescent. No task-quality read informed this recovery.

This is the sole recovery of the unchanged full1080 source. It uses new run,
attempt, fit and service identities with full source-bound registration.
The CUDA error is observed, but its kernel, context, driver or hardware root
cause is unknown. A second failure closes this flight; do not automatically
retry or change its configuration. Only one complete official TRAIN score
may run after sealing. Fold B and enhanced mechanisms remain untouched.
