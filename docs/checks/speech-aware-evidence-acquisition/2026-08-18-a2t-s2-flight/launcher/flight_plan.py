"""The registered budgets this flight's ``ExecutionPlan`` carries, and why each
one differs from (or matches) the exposure row and the committed flight config.

``FrozenCoreGate._require_exposure_preregistration`` enforces
``registered >= planned`` per column against the matched exposure row, and
``core.model.adapter`` refuses the request that would cross ``planned`` at
runtime. So these three numbers are simultaneously the runtime ceiling and the
thing the ledger row must cover.

Exposure row ``SAEA-PROBE-a2t-s2-120`` (docs/exposure-ledger.md) registers
450 calls / 3500 speech-audio-seconds / 1.0 GPU-h, matching the preregistration's
own section 6 ceilings. The committed flight config
``configs/probes/g0-binding/a2t-s2-flight.json`` declares the same three under
``execution_plan``.

- ``planned_model_calls = 420`` -- 400 real requests (120 S1p + 120 S2 + 120 S4
  + 40 N0r, the config's own ``cost_budget.call_formula``) plus 20 retry
  headroom. The exposure row registers 450, the mission's hard ceiling, so the
  gate's ``registered >= planned`` holds with room to spare and the mission's
  own 450 stop-line (enforced on the TOTAL request index, replays included)
  still binds above it.

- ``planned_speech_audio_seconds = 3000`` -- REFINED DOWN from the registered
  3500. The model-free pre-flight measures the REAL metered load at 2110.47 s:
  every S1p/S2/S4 request re-sends its sample's own audio, so the total is
  3 x 635.28 (one pass over the 120) + 204.62 (the N0r 40), not one pass. The
  worst case within the 420-call budget is 2110.47 + 20 retries each bounded by
  the headroom set's own longest item (35.71 s) = 2824.7 s, so 3000 is the
  smallest round ceiling that cannot be crossed before the CALL budget stops
  the run. (2110.47 is well under the registered 3500 either way.)

- ``planned_gpu_hours = 1.0`` -- the registered hard ceiling, unchanged. GPU
  hours are not metered by ``core.model.adapter`` (only calls and audio seconds
  are), so this number's operative role is the ledger cross-check; the flying
  agent enforces the real 1.0 h ceiling by watching CUMULATIVE wall clock
  across attempts (the launcher's ``--prior-wall-seconds``), measured from
  llama-server spawn -- model load occupies the GPU too.
"""

from __future__ import annotations

PLANNED_MODEL_CALLS = 420
PLANNED_SPEECH_AUDIO_SECONDS = 3000
PLANNED_GPU_HOURS = 1.0

# What the exposure row registers (must be >= the planned values above).
REGISTERED_CALLS = 450
REGISTERED_SPEECH_AUDIO_SECONDS = 3500
REGISTERED_GPU_HOURS = 1.0

# Operational stop lines for the flying agent (not machine-enforced by the
# contract layer; enforced by the launcher's own HealthProxy).
GPU_HOURS_CEILING = 1.0
CALLS_CEILING = 450

# What the flight is expected to issue, for the launcher's own completeness
# check (prereg section 2: 120/120/120/40).
EXPECTED_REQUESTS = 400
