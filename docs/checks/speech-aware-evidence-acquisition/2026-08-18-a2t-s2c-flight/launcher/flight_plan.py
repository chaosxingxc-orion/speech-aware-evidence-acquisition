"""The registered budgets this Stage-2c flight's ``ExecutionPlan`` carries, and
why each one differs from (or matches) the exposure row and the committed flight
config.

``FrozenCoreGate._require_exposure_preregistration`` enforces
``registered >= planned`` per column against the matched exposure row, and
``core.model.adapter`` refuses the request that would cross ``planned`` at
runtime. So these three numbers are simultaneously the runtime ceiling and the
thing the ledger row must cover.

Exposure row ``SAEA-PROBE-a2t-s2c-120`` (docs/exposure-ledger.md) registers
400 calls / 3000 speech-audio-seconds / 0.75 GPU-h, matching the
preregistration's own section 5 ceilings ("360 requests (3x120); <=400 core
calls; <=3,000 metered audio-seconds; <=0.75 GPU-h"). The committed flight
config ``configs/probes/g0-binding/a2t-s2c-flight.json`` declares the same
three under ``execution_plan``, and this module reads all three FROM that
config rather than re-typing them, so the launcher can never drift from the
committed binding.

- ``planned_model_calls = 380`` (config) -- 360 real requests (120 C1 + 120 C2
  + 120 C3, the config's own ``cost_budget.call_formula``) plus 20 retry
  headroom. The exposure row registers 400, the mission's hard ceiling, so the
  gate's ``registered >= planned`` holds and the mission's own 400 stop-line
  (enforced on the TOTAL request index, replays included) still binds above it.

- ``planned_speech_audio_seconds = 2621`` (config) -- C1, C2 and C3 EACH
  re-send their sample's own audio once, so 3 x 635.28 (Stage-2's own measured
  one pass over the SAME 120 headroom ids) = 1905.84 s base, plus 20 retries
  each bounded by the headroom set's own longest item (35.71 s) = 2620.04 ->
  2621, under the registered 3000.

- ``planned_gpu_hours = 0.75`` -- the registered hard ceiling, unchanged. GPU
  hours are not metered by ``core.model.adapter`` (only calls and audio seconds
  are), so this number's operative role is the ledger cross-check; the flying
  agent enforces the real 0.75 h ceiling by watching CUMULATIVE wall clock
  across attempts (the launcher's ``--prior-wall-seconds``), measured from
  llama-server spawn -- model load occupies the GPU too.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(
    "/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition"
)

_CFG = json.loads(
    (REPO / "configs/probes/g0-binding/a2t-s2c-flight.json").read_text(encoding="utf-8")
)
_PLAN = _CFG["execution_plan"]
_BUDGET = _CFG["cost_budget"]

# Read from the committed flight config -- never re-typed here.
PLANNED_MODEL_CALLS = int(_PLAN["planned_model_calls"])
PLANNED_SPEECH_AUDIO_SECONDS = int(_PLAN["planned_speech_audio_seconds"])
PLANNED_GPU_HOURS = float(_PLAN["planned_gpu_hours"])

# What the exposure row registers (must be >= the planned values above); these
# are the config's own declared ceilings, which the preflight cross-checks
# against the real ledger cells.
REGISTERED_CALLS = int(_BUDGET["call_ceiling"])
REGISTERED_SPEECH_AUDIO_SECONDS = int(_BUDGET["audio_seconds_ceiling"])
REGISTERED_GPU_HOURS = float(_BUDGET["gpu_hours_ceiling"])

# Operational stop lines for the flying agent (not machine-enforced by the
# contract layer; enforced by the launcher's own HealthProxy).
GPU_HOURS_CEILING = REGISTERED_GPU_HOURS
CALLS_CEILING = REGISTERED_CALLS

# What the flight is expected to issue, for the launcher's own completeness
# check (prereg section 5: 360 = 3 x 120).
EXPECTED_REQUESTS = 360
