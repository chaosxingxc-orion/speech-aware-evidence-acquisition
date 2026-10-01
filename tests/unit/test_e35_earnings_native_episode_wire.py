"""Item E35 (owner decision 89, 2026-09-21) wire proof: the Earnings21+ConEC
carrier flies the SAME six-node native episode SLURP flies (Perception ->
Solver -> Reviewer -> Planner -> Acquisition -> Delivery normaliser) through
the REAL shared role graph and a FAKE transport -- no model, tokenizer,
encoder, tool, server or network contact.

Proves, on the carrier-neutral program this item registers
(``configs/policy/phase-native-review-revise-acquire-v1.json``):

1. the episode runs end to end on FOUR synthetic units for each Earnings
   carrier. This model-free extension supplies no E22 null or flight admission;
2. the role visit sequence covers every phase the program declares
   (perception, solver, reviewer, planner) and the zero-contact acquisition
   node is armed but never visited when the Planner ACCEPTs immediately --
   exactly the E32/E18 acquisition contract, now proven for this carrier;
3. the delivered text is the Earnings delivery normaliser's OWN hygiene
   output of the Solver's raw response, never the raw model bytes -- the
   node changes no request byte (every rendered request is identical with
   the normaliser on or off), and the OFF arm delivers the raw response
   verbatim.

Same ``_ActualEpisodeHarness`` fake-transport pattern
``tests/unit/test_e32_acquisition_phase_program.py`` and
``tests/unit/test_native_episode_runner_deliver_normaliser.py`` use.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.rails import acquisition as acq
from speech_aware_evidence_acquisition.rails.controllers import default_phase_program
from speech_aware_evidence_acquisition.rails.delivery_normalisers import (
    DELIVER_NORMALISE_EARNINGS_TEXT_V1,
    DELIVER_NORMALISE_EARNINGS22_TEXT_V1,
)
from speech_aware_evidence_acquisition.rails.native_episode_config import (
    load_native_episode_config,
)
from speech_aware_evidence_acquisition.reproduction.ojw import openjiuwen_available
from speech_aware_evidence_acquisition.reproduction.ojw.native_episode import (
    ACQUISITION_STAGE,
)

from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401
from test_native_episode_runner import _ActualEpisodeHarness

REPO_ROOT = Path(__file__).resolve().parents[2]
PROGRAM_ID = "phase-native-review-revise-acquire-v1"

#: A markup-wrapped, ragged-whitespace Solver answer, so the delivered text
#: proves the hygiene actually ran rather than merely being a no-op on
#: already-clean text.
RAW_SOLVER_ANSWER = "Transcript: revenue   grew nine percent\n\nacross every segment"
HYGIENED_ANSWER = "revenue grew nine percent across every segment"
NORMALISERS = {
    "earnings21-original": DELIVER_NORMALISE_EARNINGS_TEXT_V1,
    "earnings22-original": DELIVER_NORMALISE_EARNINGS22_TEXT_V1,
}


def _values(*, armed: bool, carrier: str = "earnings21-original") -> dict:
    values: dict = {
        "carrier_lock_key": carrier,
        "native_episode": {
            "schema": "saea-native-episode-config-v1",
            "episode_id": "e35-earnings-native-window-wire-proof",
            "max_revisions": 1,
            "actions": {"accept": "ACCEPT", "revise": "REVISE", "acquire": "ACQUIRE"},
            "roles": {
                "perception": {"phase_id": "perception", "max_iterations": 1},
                "solver": {"phase_id": "solver", "max_iterations": 1},
                "reviewer": {"phase_id": "reviewer", "max_iterations": 3},
                "planner": {"phase_id": "planner", "max_iterations": 1},
                "acquisition": {
                    "phase_id": "acquisition",
                    "max_iterations": 0,
                    "kinds": ["knowledge-requery"],
                },
            },
            "acquisition": {
                "policy": acq.KNOWLEDGE_REQUERY_POLICY_ID,
                "budget": {"max_acquisitions_per_row": 1, "contact_budget": 0},
            },
        },
    }
    if armed:
        values["native_episode"]["deliver_normaliser"] = {
            "normaliser": NORMALISERS[carrier],
        }
    return values


def _output(key):
    sample_id, phase, visit, _turn = key
    if phase == "solver":
        return RAW_SOLVER_ANSWER
    if phase == "planner":
        return "ACCEPT"
    return f"{phase}-analysis:{sample_id}:visit:{visit}"


def _run(tmp_path, *, sample_count: int, armed: bool, carrier: str):
    harness = _ActualEpisodeHarness(
        tmp_path,
        sample_count=sample_count,
        max_revisions=1,
        max_contacts=11,
        planner_actions=("ACCEPT",),
        arm="speech-feature-query",
    )
    program = default_phase_program(PROGRAM_ID)
    config = load_native_episode_config(_values(armed=armed, carrier=carrier), program)
    harness.config = config
    harness.program = program
    harness.repo_root = REPO_ROOT
    harness._output = _output
    return harness


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
@pytest.mark.parametrize("carrier", NORMALISERS)
def test_the_six_node_earnings_episode_runs_end_to_end_on_four_units(tmp_path, carrier):
    # The shared _World fake-transport fixture models exactly two independent
    # synthetic samples per harness instance (test_rails_frozen_core_client._World);
    # every sample is independent within a run (no cross-sample interaction),
    # so two disjoint two-sample harness invocations exercise the item's own
    # four-row engineering scale exactly as one four-sample invocation would.
    results = []
    for batch in range(2):
        harness = _run(tmp_path / f"batch-{batch}", sample_count=2, armed=True, carrier=carrier)
        try:
            summary = harness.run()
        finally:
            harness.close()
        results.extend(summary.results)

    assert len(results) == 4
    for result in results:
        receipt = result.native_episode_receipt
        stages = [visit["stage"] for visit in receipt["role_visits"]]
        # Every declared phase the program carries visits at least once
        # (Planner ACCEPTs on its first turn, so no REVISE loop and no
        # acquisition visit -- item 2 of the module docstring).
        for expected_stage in ("perception", "solver", "review", "planner"):
            assert expected_stage in stages, (expected_stage, stages)
        assert ACQUISITION_STAGE not in stages
        # The zero-contact acquisition module still carries its own per-row
        # summary block with zero acquisitions (E18/E32 contract).
        assert receipt["acquisition"]["acquisitions"] == []
        assert receipt["acquisition"]["contacts_used"] == 0
        # Item 3: the delivered text is the Earnings normaliser's hygiene
        # output, never the raw Solver response.
        assert result.final_response_text == HYGIENED_ANSWER
        assert result.final_response_text != RAW_SOLVER_ANSWER
        assert receipt["deliver_normaliser"]["normaliser_id"] == (
            NORMALISERS[carrier]
        )
        assert receipt["deliver_normaliser"]["carrier_lock_key"] == carrier


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
@pytest.mark.parametrize("carrier", NORMALISERS)
def test_the_off_arm_delivers_the_raw_solver_response_and_makes_the_same_requests(tmp_path, carrier):
    off_harness = _run(tmp_path / "off", sample_count=1, armed=False, carrier=carrier)
    try:
        off_summary = off_harness.run()
    finally:
        off_harness.close()
    off_requests = [
        off_harness.prepared[key]["rendered"]
        for event, key in off_harness.events
        if event == "dispatch"
    ]

    on_harness = _run(tmp_path / "on", sample_count=1, armed=True, carrier=carrier)
    try:
        on_summary = on_harness.run()
    finally:
        on_harness.close()
    on_requests = [
        on_harness.prepared[key]["rendered"]
        for event, key in on_harness.events
        if event == "dispatch"
    ]

    [off_result] = off_summary.results
    [on_result] = on_summary.results
    assert off_result.final_response_text == RAW_SOLVER_ANSWER
    assert "deliver_normaliser" not in off_result.native_episode_receipt
    assert on_result.final_response_text == HYGIENED_ANSWER

    # The node runs after the last contact of the episode is already spent:
    # every rendered request is identical whether it is armed or not.
    assert len(on_requests) == len(off_requests)
    assert on_requests == off_requests
