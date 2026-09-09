"""Model-free coverage for the Audio2Tool input-rate fragments and wire check.

Every assertion runs on the committed config fragments and the committed
wire-check receipt. No data root, no model, network, tokenizer or scorer
contact, and **no gold label, reference transcript, evaluation query, tool name,
sealed output or score is opened**.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
FRAGMENTS_SCRIPT = REPO / "scripts/build_a2t_input_rate_16k_fragments.py"
WIRE_SCRIPT = REPO / "scripts/a2t_input_rate_16k_wire_check.py"
WIRE_DIR = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-07-a2t-input-rate-16k-wire-check"
)

DATASETS = {
    "16k": ("audio2tool-calibration-400-16k", 400, 2159.647312, 16000),
    "16k-smoke": ("audio2tool-calibration-400-16k-smoke4", 4, None, 16000),
    "16k+ts2": ("audio2tool-calibration-400-16k-tail2s", 400, 2959.647312, 16000),
    "16k+ts2-smoke": ("audio2tool-calibration-400-16k-tail2s-smoke4", 4, None, 16000),
}
EXPERIMENTS = (
    "a2t-official-protocol-16k-400-v1",
    "a2t-official-protocol-16k-400-smoke-v1",
    "a2t-official-protocol-16k-tail2s-400-v1",
    "a2t-official-protocol-16k-tail2s-400-smoke-v1",
)


def _module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


FRAG = _module(FRAGMENTS_SCRIPT, "a2t_input_rate_16k_fragments_test")
WIRE = _module(WIRE_SCRIPT, "a2t_input_rate_16k_wire_check_test")
RECEIPT = json.loads((WIRE_DIR / "wire-check.json").read_text(encoding="utf-8"))


def _dataset(name: str) -> dict:
    return json.loads(
        (REPO / f"configs/dataset/{name}.json").read_text(encoding="utf-8")
    )


def _experiment(name: str) -> dict:
    return json.loads(
        (REPO / f"configs/experiment/{name}.json").read_text(encoding="utf-8")
    )


# ---------------------------------------------------------------------------
# The fragments the builder emits, re-derived
# ---------------------------------------------------------------------------


def test_the_builder_reproduces_every_committed_fragment() -> None:
    """The strongest available check: re-emit and compare digests, no writes."""

    for relpath, digest in FRAG.emit(write=False):
        landed = hashlib.sha256((REPO / relpath).read_bytes()).hexdigest()
        assert landed == digest, relpath


@pytest.mark.parametrize("key", sorted(DATASETS))
def test_dataset_fragment_shape(key: str) -> None:
    name, count, seconds, rate = DATASETS[key]
    fragment = _dataset(name)
    assert fragment["carrier_lock_key"] == "audio2tool"
    assert fragment["a2t_calibration_count"] == count
    assert fragment["a2t_calibration_sample_rate_hz"] == rate
    assert fragment["a2t_calibration_source_sample_rate_hz"] == 24000
    assert fragment["a2t_calibration_split_role"] == "discovery"
    assert fragment["a2t_calibration_derived_subdir"].startswith(
        "derived/a2t-calibration-400-16k"
    )
    assert fragment["a2t_calibration_d1_media_supplement"].startswith("receipts/artifacts/")
    if seconds is not None:
        assert fragment["a2t_calibration_audio_seconds_total"] == pytest.approx(
            seconds, abs=1e-6
        )


def test_every_population_has_its_own_identity() -> None:
    identities = {
        _dataset(name)["a2t_calibration_flight_split_identity_hash"]
        for name, *_ in DATASETS.values()
    }
    assert len(identities) == len(DATASETS)
    sealed = "11091b38ae9d53530952af632636d7e79a614350213e10c6c26583c37f85846b"
    assert sealed not in identities
    # And the full populations carry exactly the media build's own identity.
    assert (
        _dataset("audio2tool-calibration-400-16k")[
            "a2t_calibration_flight_split_identity_hash"
        ]
        == "292b7220abc5e44325c01aad555d3813aa24cb4db8f5d6e414fded836d7f12b0"
    )
    assert (
        _dataset("audio2tool-calibration-400-16k-tail2s")[
            "a2t_calibration_flight_split_identity_hash"
        ]
        == "655b5ed6a65325891e9824d3bb25964681d50c8bb9f36e2deb11822e3179db67"
    )


@pytest.mark.parametrize("name", EXPERIMENTS)
def test_experiment_fragment_serves_on_the_comparators_own_model_fragment(name: str) -> None:
    doc = _experiment(name)
    assert doc["execution_profile"] == "baseline-reproduction"
    assert doc["population"]["split_role"] == "discovery"
    assert doc["population"]["media_exposure_row"] == FRAG.MEDIA_ROW
    assert doc["preregistration"] == FRAG.PREREGISTRATION
    assert doc["resampler_audit"] == FRAG.AUDIT
    for cell in doc["cells"]:
        # The media is the single factor: same model fragment, same geometry.
        assert cell["model_fragment"] == "q4km-featcache-a2t-official-04ccc72a"
        assert cell["baseline_fragment"] == "a2t-direct-official-protocol"
        assert cell["dataset_fragment"] == doc["population"]["dataset_fragment"]
    assert doc["comparator"]["split_identity_hash"] == (
        "e1d751e6c76e49d087620842ba17c34e432a4602169dc2b93ee7e0a529ca332c"
    )
    assert doc["authorizes"].startswith("nothing")
    assert doc["open_preconditions"]


@pytest.mark.parametrize("name", EXPERIMENTS)
def test_the_plans_stay_inside_the_preregistered_ceilings(name: str) -> None:
    plan = _experiment(name)["execution_plan"]
    smoke = name.endswith("-smoke-v1")
    assert plan["execution_profile"] == "baseline-reproduction"
    assert plan["split_role"] == "discovery"
    assert plan["planned_model_calls"] == (8 if smoke else 408)
    assert plan["planned_gpu_hours"] == (0.05 if smoke else 0.20)
    assert plan["planned_speech_audio_seconds"] <= (60 if smoke else 3100)


def test_the_smoke_fragments_name_their_four_rows() -> None:
    for name in EXPERIMENTS:
        doc = _experiment(name)
        if not name.endswith("-smoke-v1"):
            assert "populations" not in doc
            continue
        populations = doc["populations"]
        assert len(populations) == 1
        ids = populations[0]["ids"]
        assert len(ids) == FRAG.SMOKE_SIZE == 4
        assert ids == sorted(ids)
        assert len({sample_id.split(":", 1)[0] for sample_id in ids}) == 4
        suffix = "@16k+ts2" if "tail2s" in name else "@16k"
        assert all(sample_id.endswith(suffix) for sample_id in ids)


def test_only_the_tail_cell_declares_what_it_supersedes() -> None:
    assert "supersedes" not in _experiment("a2t-official-protocol-16k-400-v1")
    supersedes = _experiment("a2t-official-protocol-16k-tail2s-400-v1")["supersedes"]
    assert supersedes["cell_id"] == "R-official-tail2s"
    assert supersedes["experiment"] == "a2t-official-protocol-tail2s-400-v1"
    assert "only if" in supersedes["condition"]
    # The superseded cell's own fragment still exists and is untouched.
    assert (REPO / "configs/experiment/a2t-official-protocol-tail2s-400-v1.json").is_file()


# ---------------------------------------------------------------------------
# The committed wire-check receipt
# ---------------------------------------------------------------------------


def test_wire_check_receipt_identity_and_zero_contacts() -> None:
    assert RECEIPT["schema"] == "saea-a2t-input-rate-16k-wire-check-v1"
    assert RECEIPT["execution_profile"] == "model-free-check"
    assert RECEIPT["media_exposure_row"] == FRAG.MEDIA_ROW
    for key, value in RECEIPT["contacts"].items():
        assert value == 0, key
    assert len(RECEIPT["cells"]) == len(WIRE.CELLS) == 4


def test_every_cell_stopped_at_a_named_class_and_none_was_a_surprise() -> None:
    for row in RECEIPT["cells"]:
        assert row["preflight"]["stop_class"] == "gate-not-authorized"
        assert row["preflight"]["model_contacts"] == 0
        assert row["preflight"]["opened_a_socket"] is False
        assert row["wire_check"]["stop_class"] in WIRE.EXPECTED_STOPS
        assert row["wire_check"]["model_contacts"] == 0
        assert row["wire_check"]["opened_a_socket"] is False


def test_preflight_reaching_the_gate_is_the_correct_state() -> None:
    # Composition, roster hydration with a per-file re-hash, media confinement,
    # the count check and ExecutionPlan construction all pass BEFORE the gate is
    # asked -- so a gate refusal means everything upstream of it worked.
    for row in RECEIPT["cells"]:
        assert "has no pre-registered exposure row" in row["preflight"]["stopped_at"]


def test_the_seal_half_is_reported_as_pending_against_a_named_change() -> None:
    rail = RECEIPT["gold_id_rail"]
    if rail["landed"]:
        for row in RECEIPT["cells"]:
            assert row["seal_half"].startswith("RAN")
        return
    assert rail["call_site"].endswith("Audio2ToolAdapter.gold")
    assert rail["lands_on"] == "wt/ts2y"
    for row in RECEIPT["cells"]:
        assert row["seal_half"].startswith("PENDING")
        assert row["request_half"].startswith("RAN")
        assert "is not in the frozen audio2tool probe receipt" in row["wire_check"][
            "stopped_at"
        ]


#: The four ``@16k`` / ``@16k+ts2`` dataset fragments MOVED on 2026-09-09, and
#: the sealed 2026-09-07 receipt is never rewritten to hide it. Each gained the
#: plain ``d1_media_supplement`` / ``d1_media_supplement_sha256`` pair the media
#: identity gate reads -- the D1 declaration fix of ``docs/readiness/
#: 2026-09-09-a2t-derived-media-d1-declaration-fix-v1.md``. The pre-fix digest
#: is recorded here so the receipt stays pinned to a KNOWN document rather than
#: to "whatever differs today", and every fragment NOT listed must still match
#: the live bytes exactly.
SUPERSEDED_BY_THE_D1_DECLARATION_FIX = {
    "configs/dataset/audio2tool-calibration-400-16k.json": (
        "8f4595aa5ba4c6f6472f288b1558cea9e1eac39f5e0417213fd38485e1f6177c"
    ),
    "configs/dataset/audio2tool-calibration-400-16k-smoke4.json": (
        "569c7beae971b9f9ef99697e8b35e309ef5e56ae8fe3b8809d597541578c1ca3"
    ),
    "configs/dataset/audio2tool-calibration-400-16k-tail2s.json": (
        "1b9902199bfbcc18d5e5868f04a13a40c572ad46ee96c6fbeec934628766264f"
    ),
    "configs/dataset/audio2tool-calibration-400-16k-tail2s-smoke4.json": (
        "d3c86ee422b8e28d173689f54cc1a5a16ad376046bb53fc96716be1e162355fe"
    ),
}


def test_the_receipt_pins_the_fragments_it_drove() -> None:
    assert set(RECEIPT["fragments"]) == set(WIRE.FRAGMENTS)
    for relpath, digest in RECEIPT["fragments"].items():
        if relpath in SUPERSEDED_BY_THE_D1_DECLARATION_FIX:
            assert digest == SUPERSEDED_BY_THE_D1_DECLARATION_FIX[relpath], relpath
            continue
        assert hashlib.sha256((REPO / relpath).read_bytes()).hexdigest() == digest


@pytest.mark.parametrize("relpath", sorted(SUPERSEDED_BY_THE_D1_DECLARATION_FIX))
def test_every_superseded_fragment_moved_for_exactly_the_declaration_fix(
    relpath: str,
) -> None:
    """The supersession above is bounded: each listed fragment now declares the
    D1 media supplement under BOTH spellings, in agreement -- the plain pair the
    identity gate reads and the carrier-prefixed pair
    ``core.base.declared_derived_media_roots`` reads."""

    values = json.loads((REPO / relpath).read_text(encoding="utf-8"))
    assert (
        values["d1_media_supplement"] == values["a2t_calibration_d1_media_supplement"]
    )
    assert (
        values["d1_media_supplement_sha256"]
        == values["a2t_calibration_d1_media_supplement_sha256"]
    )
    assert hashlib.sha256((REPO / relpath).read_bytes()).hexdigest() != (
        SUPERSEDED_BY_THE_D1_DECLARATION_FIX[relpath]
    )


def test_wire_check_manifest_reproduces() -> None:
    lines = (WIRE_DIR / "MANIFEST.sha256").read_text(encoding="utf-8").splitlines()
    recorded = {name.lstrip("*"): digest for digest, name in (line.split() for line in lines)}
    present = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in WIRE_DIR.iterdir()
        if path.is_file() and path.name != "MANIFEST.sha256"
    }
    assert recorded == present


def test_the_wire_check_never_writes_into_a_sealed_check_directory() -> None:
    # The runner's own --wire-check-out default points inside the sealed
    # 2026-09-04 calibration receipt; this script must always override it.
    source = WIRE_SCRIPT.read_text(encoding="utf-8")
    assert '"--wire-check-out"' in source
    assert "2026-09-04-a2t-direct-calibration-400-v1" not in source
