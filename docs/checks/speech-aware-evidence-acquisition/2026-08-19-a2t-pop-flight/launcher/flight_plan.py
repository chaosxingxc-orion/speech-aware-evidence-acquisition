"""The registered budgets this whole-population regression flight's
``ExecutionPlan`` carries, and why each one differs from (or matches) the
exposure row.

``FrozenCoreGate._require_exposure_preregistration`` enforces
``registered >= planned`` per column against the matched exposure row, and
``core.model.adapter`` refuses the request that would cross ``planned`` at
runtime. So these three numbers are simultaneously the runtime ceiling and the
thing the ledger row must cover.

Exposure row ``SAEA-PROBE-a2t-pop-194`` (docs/exposure-ledger.md) registers
220 calls / 2000 speech-audio-seconds / 0.5 GPU-h, matching the
preregistration's own section 4 ceilings ("194 requests; <=220 core calls;
<=2,000 metered audio-seconds; <=0.5 GPU-h"). This probe has no committed
g0-binding flight config (``flight_identity`` module docstring), so the
REGISTERED_* values below are read from the preregistration's own section 4 and
cross-checked against the live ledger cells by ``preflight.py`` -- never trusted
from this file alone.

- ``PLANNED_MODEL_CALLS = 210`` -- 194 real requests (97 samples x 2 arms) plus
  16 retry headroom, under the registered 220. The mission's hard 220 stop-line
  (enforced on the TOTAL request index, replays included) still binds above it.

- ``PLANNED_SPEECH_AUDIO_SECONDS`` -- DERIVED, not hand-typed: 2 x the measured
  one pass over the EM-correct 97 (``split-measurement.json``, written by the
  model-free ``measure.py``) plus 16 retries each bounded by that population's
  own longest item, rounded up. R0 and R1 EACH re-send their sample's own real
  audio once; no derived media is involved. Fails closed if the derivation
  exceeds the registered 2000.

- ``PLANNED_GPU_HOURS = 0.5`` -- the registered hard ceiling, unchanged. GPU
  hours are not metered by ``core.model.adapter`` (only calls and audio seconds
  are), so this number's operative role is the ledger cross-check; the flying
  agent enforces the real ceiling by watching CUMULATIVE wall clock measured
  from llama-server spawn (model load occupies the GPU too).
"""

from __future__ import annotations

import json
import math
from pathlib import Path

_MEASUREMENT_PATH = Path(__file__).resolve().parent / "split-measurement.json"

# Preregistration section 4, quoted: "194 requests; <=220 core calls; <=2,000
# metered audio-seconds; <=0.5 GPU-h". preflight.py cross-checks all three
# against the live exposure-ledger cells.
REGISTERED_CALLS = 220
REGISTERED_SPEECH_AUDIO_SECONDS = 2000
REGISTERED_GPU_HOURS = 0.5

EXPECTED_REQUESTS = 194
RETRY_HEADROOM_CALLS = 16

PLANNED_MODEL_CALLS = EXPECTED_REQUESTS + RETRY_HEADROOM_CALLS  # 210
PLANNED_GPU_HOURS = REGISTERED_GPU_HOURS


def _planned_audio_seconds() -> int:
    if not _MEASUREMENT_PATH.is_file():
        raise RuntimeError(
            f"{_MEASUREMENT_PATH} is missing; run measure.py (model-free) before the pre-flight "
            "-- planned_speech_audio_seconds is DERIVED from the measured split, never hand-typed"
        )
    document = json.loads(_MEASUREMENT_PATH.read_text(encoding="utf-8"))
    n_arms = len(document["arms"])
    one_pass = float(document["one_pass_audio_seconds"])
    longest = float(document["longest_sample_audio_seconds"])
    derived = math.ceil(n_arms * one_pass + RETRY_HEADROOM_CALLS * longest)
    if derived > REGISTERED_SPEECH_AUDIO_SECONDS:
        raise RuntimeError(
            f"derived planned_speech_audio_seconds {derived} exceeds the registered ceiling "
            f"{REGISTERED_SPEECH_AUDIO_SECONDS}; this is a REGISTRATION matter, not an "
            "implementer edit"
        )
    return derived


PLANNED_SPEECH_AUDIO_SECONDS = _planned_audio_seconds()

# Operational stop lines for the flying agent (not machine-enforced by the
# contract layer; enforced by the launcher's own HealthProxy).
CALLS_CEILING = REGISTERED_CALLS
GPU_HOURS_CEILING = REGISTERED_GPU_HOURS
