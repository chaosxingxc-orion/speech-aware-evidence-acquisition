"""The registered budgets this abstention-asymmetry flight's ``ExecutionPlan``
carries, and why each one differs from (or matches) the exposure row.

``FrozenCoreGate._require_exposure_preregistration`` enforces
``registered >= planned`` per column against the matched exposure row, and
``core.model.adapter`` refuses the request that would cross ``planned`` at
runtime. So these three numbers are simultaneously the runtime ceiling and the
thing the ledger row must cover.

Exposure row ``SAEA-PROBE-a2t-abst-44`` (docs/exposure-ledger.md) registers
60 calls / 500 speech-audio-seconds / 0.15 GPU-h, matching the preregistration's
own section 3 ceilings ("44 requests; <=60 core calls; <=500 metered
audio-seconds; <=0.15 GPU-h"). This probe has no committed g0-binding flight
config (``flight_identity`` module docstring), so the REGISTERED_* values below
are read from the preregistration's own section 3 and cross-checked against the
live ledger cells by ``preflight.py`` -- never trusted from this file alone.

- ``PLANNED_MODEL_CALLS = 50`` -- 44 real requests (11 samples x 4 cells) plus
  6 retry headroom, under the registered 60. The mission's hard 60 stop-line
  (enforced on the TOTAL request index, replays included) still binds above it.

- ``PLANNED_SPEECH_AUDIO_SECONDS`` -- DERIVED, not hand-typed: 4 x the measured
  one pass over the drawn 11 (``split-measurement.json``, written by the
  model-free ``measure.py``) plus 6 retries each bounded by the drawn set's own
  longest item, rounded up. Every one of the 4 cells re-sends its sample's own
  audio once; the two SILENCE cells send a matched-duration derived slice, which
  meters the SAME number of seconds as its real parent. Fails closed if the
  derivation exceeds the registered 500.

- ``PLANNED_GPU_HOURS = 0.15`` -- the registered hard ceiling, unchanged. GPU
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

# Preregistration section 3, quoted: "44 requests; <=60 core calls; <=500
# metered audio-seconds; <=0.15 GPU-h". preflight.py cross-checks all three
# against the live exposure-ledger cells.
REGISTERED_CALLS = 60
REGISTERED_SPEECH_AUDIO_SECONDS = 500
REGISTERED_GPU_HOURS = 0.15

EXPECTED_REQUESTS = 44
RETRY_HEADROOM_CALLS = 6

PLANNED_MODEL_CALLS = EXPECTED_REQUESTS + RETRY_HEADROOM_CALLS  # 50
PLANNED_GPU_HOURS = REGISTERED_GPU_HOURS


def _planned_audio_seconds() -> int:
    if not _MEASUREMENT_PATH.is_file():
        raise RuntimeError(
            f"{_MEASUREMENT_PATH} is missing; run measure.py (model-free) before the pre-flight "
            "-- planned_speech_audio_seconds is DERIVED from the measured split, never hand-typed"
        )
    document = json.loads(_MEASUREMENT_PATH.read_text(encoding="utf-8"))
    n_cells = len(document["cells"])
    one_pass = float(document["one_pass_audio_seconds"])
    longest = float(document["longest_sample_audio_seconds"])
    derived = math.ceil(n_cells * one_pass + RETRY_HEADROOM_CALLS * longest)
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
