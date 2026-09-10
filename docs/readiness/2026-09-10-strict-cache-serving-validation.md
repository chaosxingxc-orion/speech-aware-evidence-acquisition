# Strict raw-audio feature-cache serving configuration

Date: 2026-09-10 UTC. Implement a shared structural check for OWNER-FEATURE-SERVING-007.

## Behavior

The sole server command builder now validates opt-in `LLAMA_MTMD_FEAT_CACHE_REQUIRE_HIT` before process creation. Require an explicit environment binding, an existing absolute cache directory, a runtime-pinned CPU projector selected by exactly `--no-mmproj-offload`, and the raw-audio legacy session role. Refuse conflicting model/projector flags model-selection environment settings, and any inherited or declared `LLAMA_MTMD_FEAT_CACHE_VALIDATE`, including empty and `0` values: the C++ cache guard checks presence, not truthiness. Refuse implicitly inherited strict mode so a shell cannot change the declared serving path.

Preserve historical commands when strict mode is absent. Packet inference continues to inject `--no-mmproj` and omit projector model files. Preprocessing must not enable this strict generation mode because it needs to create missing features.

The check does not change context, parallel slots, batch size, microbatch size, output limits, model weights or prompt bytes. It uses the same builder called by root-owned resident serving and session startup. It does not create an alternate launcher.

## Evidence and limits

Test-first validation reproduced 19 initial refusal failures, seven initial model-alias failures, and 20 additional alias/environment cases found during review. The final focused suite has 52 passing cases and 100% statement/branch coverage for the new validator. The final focused/session/resident-session regression suite has 208 passes and six pre-existing platform skips. Root reviewed the pinned C++ parser: it recognizes additional short aliases and normalizes underscores in long flags; the guard covers both. The C++ CLI explicitly overrides environment values, so rejecting redundant projector environment settings removes ambiguity and does not imply a demonstrated GPU-offload bypass from the environment alone. Ruff and the engineering base check pass. All execution used WSL Ubuntu-24.04, the existing speechrl Python environment, an explicit worktree PYTHONPATH, and synthetic files only.

This is a structural configuration check, not runtime feature-cache qualification. A binary that ignores the environment variable is not qualified by these tests. Complete current-build feature provenance, immutable chunk bindings, verified preprocessing completion and stop receipts, runtime cache-hit/miss/decode-failure tests, per-request consumption checks, full actual-request capacity receipts and scientific admission remain required. No model, encoder, scorer or service contact was performed. No historical manifest or active experimental configuration was changed.
