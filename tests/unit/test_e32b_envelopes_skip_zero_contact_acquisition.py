"""Item E32b (2026-09-21): the pre-flight envelope renderer skips the zero-contact acquisition phase.

Cell B9a composes the E32 program (four phases plus ``acquisition``); item E18's kind (a) never sends a request, so
``rails.phase_material`` exempts the phase from the per-phase material rule and the renderer must not look it up.
Every other phase without a material spec is still the configuration error it always was.
"""

import pytest

from speech_aware_evidence_acquisition.core.flight.runtime import (
    FlightRuntimeError,
    render_phase_prompt_envelopes,
)


def _render(phase_names):
    return render_phase_prompt_envelopes(
        program_id="phase-native-candidates-review-revise-acquire-v1",
        phase_names=phase_names,
        specs={},
        static_text_by_phase={},
        system_text="system",
        prompt_order="speech-query-prefix-v2",
        packet_descriptor={"packet_id": "p", "sha256": "p-sha"},
        sample_id="slurp:train:000001:audio-1",
        completion_token_ceiling=512,
    )


def test_an_acquisition_phase_without_material_renders_no_envelope():
    assert _render(("acquisition",)) == {}


def test_any_other_phase_without_material_is_still_refused():
    with pytest.raises(FlightRuntimeError, match="no phase material spec"):
        _render(("solver",))
