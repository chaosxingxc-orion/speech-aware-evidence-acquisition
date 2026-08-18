"""The registered budgets this flight's ``ExecutionPlan`` carries, and why each
one differs from (or matches) the committed flight config.

``FrozenCoreGate._require_exposure_preregistration`` enforces
``registered >= planned`` per column against the matched exposure row, and
``core.model.adapter`` refuses the request that would cross ``planned`` at
runtime. So these three numbers are simultaneously the runtime ceiling and the
thing the ledger row must cover.

``configs/probes/g0-binding/pa2t-a0-flight.json`` declares 420 / 2400 / 2.0 and
its own ``cost_budget`` note explicitly invites refinement:
"planned_gpu_hours=2.0 is a conservative placeholder the flying agent should
refine against a real per-request latency measurement", and
"planned_speech_audio_seconds=2400 is a documented, generous ceiling over the
known 1801.3s, not a precise figure".

- ``planned_model_calls = 420`` -- the committed config's own value, unchanged.
  400 items x 1 request (zero-supply, one arm) plus 20 retry headroom. The
  exposure row registers 450, the mission's hard ceiling, so the gate's
  ``registered >= planned`` holds with room to spare.

- ``planned_speech_audio_seconds = 3000`` -- REFINED UP from the config's 2400.
  The config's 2400 was derived from the binding JSON's partial 1801.3 s (the
  350 items carrying a top-level duration); the adapter itself resolves all
  400 and the model-free pre-flight measures the REAL total at 2159.69 s. The
  worst case within the call budget is 2159.69 + 20 retries each bounded by
  the split's own longest item (35.714 s) = 2874.0 s, so 3000 is the smallest
  round ceiling that cannot be crossed before the call budget stops the run.
  2400 would have been crossed by ~240 s of retries.

- ``planned_gpu_hours = 1.5`` -- REFINED DOWN from the config's 2.0 placeholder
  to the mission's registered hard ceiling. GPU hours are not metered by
  ``core.model.adapter`` (only calls and audio seconds are), so this number's
  operative role is the ledger cross-check; the flying agent enforces the real
  1.5 h ceiling by watching wall clock.
"""

from __future__ import annotations

PLANNED_MODEL_CALLS = 420
PLANNED_SPEECH_AUDIO_SECONDS = 3000
PLANNED_GPU_HOURS = 1.5

# What the exposure row registers (must be >= the planned values above).
REGISTERED_CALLS = 450
REGISTERED_SPEECH_AUDIO_SECONDS = 3000
REGISTERED_GPU_HOURS = 1.5

# Operational stop line for the flying agent (not machine-enforced).
GPU_HOURS_CEILING = 1.5
CALLS_CEILING = 450
