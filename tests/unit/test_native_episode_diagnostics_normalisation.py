"""Post-seal system diagnostics include deterministic final delivery."""
from copy import deepcopy
from dataclasses import replace

import pytest

from speech_aware_evidence_acquisition.analysis.native_episode_diagnostics import (
    NativeEpisodeDiagnosticError, analyze_verified_native_episode_statistics,
)
from speech_aware_evidence_acquisition.rails.delivery_normalisers import DELIVER_NORMALISE_V3
from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401
from test_native_episode_runner import _ActualEpisodeHarness
from test_native_episode_runner_deliver_normaliser import (
    RAW_ANSWER, _slurp_output, _synthetic_inventory,  # noqa: F401
)


@pytest.fixture
def normalized_system(tmp_path):
    harness = _ActualEpisodeHarness(
        tmp_path, sample_count=1, max_revisions=0, max_contacts=4,
        planner_actions=("ACCEPT",), arm="speech-feature-query",
    )
    harness.config = replace(harness.config, deliver_normaliser_id=DELIVER_NORMALISE_V3)
    harness._output = _slurp_output
    try:
        summary = harness.run()
    finally:
        harness.close()
    result = summary.results[0]
    row = result.as_json()
    # I7n: a normalised row names the normaliser's carrier, like the receipt block does.
    output = {"sample_id": "s1", "text": result.final_response_text,
              "carrier_lock_key": row["native_episode_receipt"]["deliver_normaliser"]["carrier_lock_key"],
              "native_episode_receipt": deepcopy(row["native_episode_receipt"])}
    return dict(
        sample_ids=("s1",), controller_policy_id=summary.controller_policy_id,
        phase_results={"s1": row}, output_rows={"s1": output},
        trace_records={key: payload for _axis, key, payload in harness.trace.records},
    )


def test_system_diagnostic_preserves_raw_solver_and_normalized_delivery(normalized_system):
    source = normalized_system
    raw_trace = deepcopy(source["trace_records"])
    assert source["output_rows"]["s1"]["text"] != RAW_ANSWER
    result = analyze_verified_native_episode_statistics(**source)
    assert result["sample_count"] == 1
    row = result["samples"][0]
    normalizer = source["phase_results"]["s1"]["native_episode_receipt"]["deliver_normaliser"]
    assert row["delivery_normalisation"] == {
        "normaliser_id": normalizer["normaliser_id"],
        "input_sha256": normalizer["input_sha256"],
        "output_sha256": normalizer["output_sha256"],
        "changed": True,
    }
    assert source["trace_records"] == raw_trace


def test_system_diagnostic_rejects_rehashed_false_normalized_delivery(normalized_system):
    source = normalized_system
    for row in (source["phase_results"]["s1"], source["output_rows"]["s1"]):
        row["native_episode_receipt"]["deliver_normaliser"]["input_sha256"] = "e" * 64
    with pytest.raises(NativeEpisodeDiagnosticError, match="normalisation"):
        analyze_verified_native_episode_statistics(**source)
