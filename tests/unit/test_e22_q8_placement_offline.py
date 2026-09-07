"""``scripts/e22_q8_placement_offline.py``: the offline ``--n-cpu-moe``
projection for Earnings-22 cell (a).

No model, GPU, server or network contact anywhere in this file. The GGUF-reader
tests are skipped when the 32 GB decoder is not materialized on this host; every
other test runs against two COMMITTED receipts -- the A2T probe's own live
placement ladder and the projection this script wrote -- so the arithmetic is
checked against measurements rather than against itself.

Loaded via ``importlib.util`` rather than a package import for the same reason
``tests/unit/test_engineering_base_check.py`` does it: ``scripts/`` carries no
``__init__.py`` and is not part of the distributed package.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "e22_q8_placement_offline.py"
PROJECTION_PATH = (
    REPO_ROOT
    / "docs/checks/speech-aware-evidence-acquisition/2026-09-06-e22-dev-usage-cells"
    / "q8-placement.json"
)
LADDER_PATH = (
    REPO_ROOT
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-04-a2t-q8-quantization-probe-400-v1/placement/placement-fit.json"
)

MIB = 1024 * 1024


def _load_module():
    spec = importlib.util.spec_from_file_location("e22_q8_placement_offline", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


placement = _load_module()


def _projection() -> dict:
    return json.loads(PROJECTION_PATH.read_text(encoding="utf-8"))


def _ladder() -> dict:
    return json.loads(LADDER_PATH.read_text(encoding="utf-8"))


def _model_terms(projection: dict) -> dict[str, float]:
    return {
        "non_expert_mib": float(projection["decoder_tensor_table"]["non_expert_mib"]),
        "expert_mib_per_layer": float(
            projection["decoder_tensor_table"]["expert_mib_per_layer"]
        ),
        "expert_layers": int(projection["decoder_tensor_table"]["expert_layers"]),
        "mmproj_mib": float(projection["mmproj"]["resident_mib"]),
    }


# ---------------------------------------------------------------------------
# The arithmetic, against the A2T probe's own LIVE ladder.
# ---------------------------------------------------------------------------


def test_the_projection_reproduces_every_measured_rung_of_the_live_ladder():
    """The load-bearing check. The A2T probe measured device memory at eight
    ``--n-cpu-moe`` rungs of the SAME decoder, mmproj and llama.cpp build; the
    projection's model must reproduce each one from the GGUF's tensor table plus
    one fitted constant, or it is not a model of this runtime and the N it picks
    for a different geometry means nothing."""

    projection = _projection()
    ladder = _ladder()
    terms = _model_terms(projection)
    kv_mib = float(projection["kv_cache"]["ladder_kv_mib"])
    overhead = float(projection["calibration"]["fitted_overhead_mib"])

    checked = 0
    for trial in ladder["trials"]:
        measured = float(trial["device_memory_resident_mib"]["used_mib"])
        if float(trial["device_memory_resident_mib"]["free_mib"]) < 64.0:
            continue  # saturated: the card was full, so this is a truncation
        predicted = placement.predicted_used_mib(
            kv_mib=kv_mib,
            overhead_mib=overhead,
            n_cpu_moe=int(trial["n_cpu_moe"]),
            **terms,
        )
        assert abs(predicted - measured) <= 1.0, (
            f"n_cpu_moe {trial['n_cpu_moe']}: predicted {predicted:.1f} MiB against a "
            f"measured {measured:.1f} MiB"
        )
        checked += 1
    assert checked == 7, f"expected seven non-saturated rungs, checked {checked}"


def test_the_fitted_overhead_is_one_constant_and_the_receipt_says_so():
    projection = _projection()
    ladder = _ladder()
    terms = _model_terms(projection)

    fitted, residuals = placement.fit_overhead(
        ladder["trials"],
        kv_mib=float(projection["kv_cache"]["ladder_kv_mib"]),
        free_before_mib=float(projection["device"]["free_before_mib"]),
        **terms,
    )
    assert fitted == pytest.approx(
        float(projection["calibration"]["fitted_overhead_mib"]), abs=1e-3
    )
    assert float(projection["calibration"]["residual_spread_mib"]) == pytest.approx(
        0.0, abs=1e-6
    )
    saturated = [entry for entry in residuals if entry["saturated"]]
    assert [entry["n_cpu_moe"] for entry in saturated] == [20]
    assert saturated[0]["excluded_reason"]


def test_a_ladder_that_is_not_linear_is_refused_rather_than_averaged():
    """A fit is only a fit if the data supports it: a rung that does not lie on
    the line means the model is wrong, and extrapolating it to another geometry
    would be worse than not answering."""

    ladder = _ladder()
    trials = [json.loads(json.dumps(trial)) for trial in ladder["trials"]]
    trials[2]["device_memory_resident_mib"]["used_mib"] += 900

    with pytest.raises(placement.PlacementError, match="not linear"):
        placement.fit_overhead(
            trials,
            kv_mib=2448.0,
            free_before_mib=24137.0,
            **_model_terms(_projection()),
        )


# ---------------------------------------------------------------------------
# The decision.
# ---------------------------------------------------------------------------


def test_the_chosen_placement_is_28_and_24_misses_the_floor():
    """Section 1.3 of the preregistration expected N = 28 and forbade copying
    the A2T probe's N = 24. Both halves are asserted here against the receipt's
    own inputs, recomputed rather than read back."""

    projection = _projection()
    chosen, rungs = placement.choose_placement(
        kv_mib=float(projection["kv_cache"]["cell_kv_mib"]),
        overhead_mib=float(projection["calibration"]["fitted_overhead_mib"]),
        free_before_mib=float(projection["device"]["free_before_mib"]),
        min_free_mib=float(projection["min_free_mib"]),
        step=int(projection["step"]),
        **_model_terms(projection),
    )
    assert chosen == 28
    assert projection["chosen_n_cpu_moe"] == 28

    by_n = {int(rung["n_cpu_moe"]): rung for rung in rungs}
    assert by_n[28]["projected_free_mib"] == pytest.approx(5083.0, abs=0.5)
    assert by_n[28]["meets_min_free"] is True
    assert by_n[24]["projected_free_mib"] == pytest.approx(2635.0, abs=0.5)
    assert by_n[24]["meets_min_free"] is False
    # The rule is "the largest GPU-resident share that still clears the floor",
    # i.e. the SMALLEST N -- and the ladder stops at the first rung that fails.
    assert min(by_n) == 24
    assert projection["rejected_next_rung"]["n_cpu_moe"] == 24


def test_the_floor_is_the_encoder_estimate_rounded_up():
    projection = _projection()
    assert projection["min_free_mib"] == 3072
    assert "2,940" in projection["min_free_basis"]


def test_the_projection_does_not_claim_to_discharge_the_live_pass():
    """The receipt must say what it is. A projection filed as a measurement is
    exactly how a precondition gets skipped."""

    projection = _projection()
    assert projection["status"].startswith("PROJECTION")
    assert projection["model_contacts"] == 0
    assert projection["total_generated_tokens"] == 0
    assert "LIVE" in projection["does_not_replace_the_live_pass"]
    assert projection["live_pass_still_required"]


def test_the_cell_geometry_is_the_sealed_comparators():
    projection = _projection()
    assert projection["cell_geometry"]["context_tokens"] == 40960
    assert projection["cell_geometry"]["slots"] == 8
    assert projection["cell_geometry"]["slot_tokens"] == 5120
    assert projection["calibration"]["source_serving_geometry"]["context_tokens"] == 49152
    assert projection["calibration"]["source_serving_geometry"]["slots"] == 3


def test_the_model_fragment_carries_the_projected_placement():
    """A projection nobody flies is decoration: the number has to be in the
    fragment the cell composes."""

    fragment = json.loads(
        (
            REPO_ROOT
            / "configs/model/q8-e22-dev1500-esb-mmproj-gpu-04ccc72a-np8-c40960.json"
        ).read_text(encoding="utf-8")
    )
    args = [str(value) for value in fragment["server_args"]]
    assert args[args.index("--n-cpu-moe") + 1] == "28"
    assert args[args.index("-c") + 1] == "40960"
    assert args[args.index("-np") + 1] == "8"
    assert "LLAMA_MTMD_FEAT_CACHE_DIR" not in fragment["server_env"]
    assert fragment["model_lock_key"] == "qwen3-omni-30b-a3b-instruct-gguf"
    # The factor is the decoder, so the request must not also carry cell (b)'s
    # per-sample cap: two factors in one cell would make neither readable.
    assert fragment["decoding_params"]["max_tokens"] == 1024


# ---------------------------------------------------------------------------
# The pieces the arithmetic reads out of the GGUF.
# ---------------------------------------------------------------------------


def test_kv_bytes_per_token_from_the_decoders_own_metadata():
    metadata = {
        "general.architecture": "qwen3vlmoe",
        "qwen3vlmoe.block_count": 48,
        "qwen3vlmoe.attention.head_count_kv": 4,
        "qwen3vlmoe.attention.key_length": 128,
        "qwen3vlmoe.attention.value_length": 128,
    }
    # 48 blocks x 4 KV heads x (128 + 128) elements at 34 bytes per 32 elements.
    assert placement.kv_bytes_per_token(metadata) == 52224
    assert 40960 * 52224 / MIB == pytest.approx(2040.0)
    assert 49152 * 52224 / MIB == pytest.approx(2448.0)


def test_kv_geometry_refuses_a_metadata_block_it_cannot_read():
    with pytest.raises(placement.PlacementError, match="general.architecture"):
        placement.kv_bytes_per_token({"block_count": 48})
    with pytest.raises(placement.PlacementError, match="block_count"):
        placement.kv_bytes_per_token({"general.architecture": "x"})


def test_expert_geometry_splits_the_tensor_table():
    tensors = [
        {"name": "token_embd.weight", "bytes": 100},
        {"name": "blk.0.attn_q.weight", "bytes": 10},
        {"name": "blk.0.ffn_gate_exps.weight", "bytes": 300},
        {"name": "blk.0.ffn_up_exps.weight", "bytes": 300},
        {"name": "blk.1.attn_q.weight", "bytes": 10},
        {"name": "blk.1.ffn_gate_exps.weight", "bytes": 300},
        {"name": "blk.1.ffn_up_exps.weight", "bytes": 300},
    ]
    geometry = placement.expert_geometry(tensors)
    assert geometry["expert_layers"] == 2
    assert geometry["expert_bytes_per_layer"] == 600
    assert geometry["expert_bytes_total"] == 1200
    assert geometry["non_expert_bytes"] == 120
    assert geometry["expert_tensor_names"] == [
        "ffn_gate_exps.weight",
        "ffn_up_exps.weight",
    ]


def test_expert_geometry_refuses_layers_of_different_sizes():
    tensors = [
        {"name": "blk.0.ffn_gate_exps.weight", "bytes": 300},
        {"name": "blk.1.ffn_gate_exps.weight", "bytes": 301},
    ]
    with pytest.raises(placement.PlacementError, match="differ in size"):
        placement.expert_geometry(tensors)


def test_expert_geometry_refuses_a_model_with_nothing_to_offload():
    with pytest.raises(placement.PlacementError, match="no \\*_exps tensors"):
        placement.expert_geometry([{"name": "token_embd.weight", "bytes": 1}])


@pytest.mark.skipif(
    not (
        Path("/home/chao/models/qwen3-omni-30b-a3b-instruct-gguf")
        / "Qwen3-Omni-30B-A3B-Instruct-Q8_0.gguf"
    ).is_file(),
    reason="the Q8_0 decoder is not materialized on this host",
)
def test_the_gguf_header_reader_reproduces_the_receipts_tensor_table():
    """Header only: the reader must land on the same tensor totals the committed
    projection recorded, without reading a byte of tensor payload."""

    projection = _projection()
    root = Path(projection["model"]["model_materialization_root"])
    decoder = next(
        root / path for path in projection["model"]["gguf_files"] if "mmproj" not in path
    )
    metadata, tensors = placement.read_gguf_header(decoder)
    geometry = placement.expert_geometry(tensors)
    table = projection["decoder_tensor_table"]

    assert metadata["general.architecture"] == table["architecture"]
    assert len(tensors) == table["tensor_count"]
    assert geometry["expert_layers"] == table["expert_layers"]
    assert geometry["expert_bytes_per_layer"] == table["expert_bytes_per_layer"]
    assert geometry["expert_bytes_total"] == table["expert_bytes_total"]
    assert geometry["non_expert_bytes"] == table["non_expert_bytes"]
    assert placement.kv_bytes_per_token(metadata) == projection["kv_cache"][
        "bytes_per_token"
    ]
