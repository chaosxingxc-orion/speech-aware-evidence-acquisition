"""The six Audio2Tool derived-media cells declare their D1 media supplement
where the IDENTITY GATE reads it -- and the gate admits their ids.

The defect this pins (2026-09-09, ``docs/readiness/
2026-09-09-a2t-derived-media-d1-declaration-fix-v1.md``): all six fragments
declared the supplement ONLY under the carrier-prefixed keys
``a2t_calibration_d1_media_supplement`` / ``..._sha256``. ``core.base.
declared_derived_media_roots`` reads exactly those, so payload confinement was
satisfied; ``core.flight.FlightRuntime.preflight`` builds the media-identity
gate from ``core.config.d1_media_supplement_relpath``, which reads only the
PLAIN pair, so the gate saw no supplement and refused every roster id as
outside D1's closure at the first real request.

Model-free, zero sockets, zero model contacts, no data root: the gate is
constructed exactly as ``preflight`` constructs it, over the REAL committed
supplement artifacts under ``docs/receipts/artifacts/``, and only membership
of D1's identity closure is asserted -- no media file is opened. **No gold
label, reference transcript, tool name, sealed output or score is read.**
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.contracts import FrozenCoreGate, GateClosed
from speech_aware_evidence_acquisition.core.config import (
    ConfigError,
    compose,
    d1_media_supplement_relpath,
    d1_media_supplement_sha256,
    model_lock_key,
    model_materialization_root,
    runtime_receipt_relpath,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
RECEIPTS = REPO_ROOT / "docs" / "receipts"
CARRIER = "audio2tool"

pytestmark = pytest.mark.skipif(
    not (RECEIPTS / "e0-closure.json").is_file(),
    reason="E0 closure receipts not landed in this checkout",
)

#: The six cells, as ``(experiment fragment, dataset fragment, cell id,
#: expected supplement relpath)``. Every one composes the model and baseline
#: fragments its own experiment cell declares, exactly as
#: ``scripts/flights/run_calibration_cell.py::build_runtime`` does.
CELLS = (
    (
        "a2t-official-protocol-16k-400-v1",
        "audio2tool-calibration-400-16k",
        "R-official-16k",
        "receipts/artifacts/d1-a2t-calibration-400-16k.json",
    ),
    (
        "a2t-official-protocol-16k-400-smoke-v1",
        "audio2tool-calibration-400-16k-smoke4",
        "R-official-16k-smoke-4",
        "receipts/artifacts/d1-a2t-calibration-400-16k.json",
    ),
    (
        "a2t-official-protocol-16k-tail2s-400-v1",
        "audio2tool-calibration-400-16k-tail2s",
        "R-official-16k-tail2s",
        "receipts/artifacts/d1-a2t-calibration-400-16k-tail2s.json",
    ),
    (
        "a2t-official-protocol-16k-tail2s-400-smoke-v1",
        "audio2tool-calibration-400-16k-tail2s-smoke4",
        "R-official-16k-tail2s-smoke-4",
        "receipts/artifacts/d1-a2t-calibration-400-16k-tail2s.json",
    ),
    (
        "a2t-official-protocol-tail2s-400-v1",
        "audio2tool-calibration-400-tail2s",
        "R-official-tail2s",
        "receipts/artifacts/d1-a2t-calibration-400-tail2s.json",
    ),
    (
        "a2t-official-protocol-tail2s-400-smoke-v1",
        "audio2tool-calibration-400-tail2s-smoke4",
        "R-official-tail2s-smoke-4",
        "receipts/artifacts/d1-a2t-calibration-400-tail2s.json",
    ),
)

#: One real id per derived variant. ``tier1_direct:000045`` is the very first
#: row of the frozen 400 discovery roster, and the id the September 2026-09-09
#: flight agent's first real request died on.
ADMITTED_IDS = (
    "tier1_direct:000045@16k",
    "tier1_direct:000045@16k+ts2",
    "tier1_direct:000045@ts2",
)


def _compose(experiment: str, dataset: str, cell_id: str):
    document = json.loads(
        (REPO_ROOT / "configs" / "experiment" / f"{experiment}.json").read_text(
            encoding="utf-8"
        )
    )
    cell = next(
        item for item in document["cells"] if str(item["cell_id"]) == cell_id
    )
    return compose(
        REPO_ROOT,
        str(cell["model_fragment"]),
        dataset,
        str(cell["baseline_fragment"]),
        experiment,
    )


def _preflight_gate(values, tmp_path: Path) -> FrozenCoreGate:
    """The gate ``core.flight.FlightRuntime.preflight`` builds, verbatim.

    Same ``for_study_repo`` call, same four config-derived keyword arguments
    off the same composed values (``core/flight/runtime.py`` ~1708). The data
    root is a tmp path on purpose: every assertion below is about D1's
    identity CLOSURE, which opens no media file -- so this test needs no data
    root and can never be green because a stale media file happened to match.
    """

    configured_model_root = model_materialization_root(values)
    return FrozenCoreGate.for_study_repo(
        REPO_ROOT,
        tmp_path,
        tmp_path,
        runtime_receipt_relpath=runtime_receipt_relpath(values),
        expected_model_lock_key=model_lock_key(values),
        model_root=(
            Path(configured_model_root) if configured_model_root is not None else None
        ),
        d1_media_supplement_relpath=d1_media_supplement_relpath(values),
        d1_media_supplement_sha256=d1_media_supplement_sha256(values),
    )


# ---------------------------------------------------------------------------
# The declaration the gate reads
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "experiment,dataset,cell_id,supplement",
    CELLS,
    ids=[cell[2] for cell in CELLS],
)
def test_the_gate_side_reader_now_resolves_the_supplement_for_every_cell(
    experiment: str, dataset: str, cell_id: str, supplement: str
) -> None:
    """``d1_media_supplement_relpath`` -- the ONLY reader ``preflight`` has --
    returns the cell's own supplement. Before the fix it returned ``None`` for
    all six."""

    values = _compose(experiment, dataset, cell_id).values
    assert d1_media_supplement_relpath(values) == supplement
    digest = d1_media_supplement_sha256(values)
    assert digest is not None and len(digest) == 64
    # The prefixed pair stays, because ``core.base.declared_derived_media_roots``
    # reads it to vouch for the derived media root -- and the two spellings
    # must agree, which is what makes one fragment one declaration.
    assert values["a2t_calibration_d1_media_supplement"] == supplement
    assert values["a2t_calibration_d1_media_supplement_sha256"] == digest


def test_a_prefixed_only_declaration_is_refused_at_composition() -> None:
    """The state the six fragments were in is now unrepresentable: a
    carrier-prefixed pair with a real digest and no plain pair refuses in
    ``core.config``, before any gate is built."""

    values = dict(_compose(*CELLS[0][:3]).values)
    del values["d1_media_supplement"]
    del values["d1_media_supplement_sha256"]
    with pytest.raises(ConfigError) as refusal:
        d1_media_supplement_relpath(values)
    assert "a2t_calibration_d1_media_supplement" in str(refusal.value)
    assert "identity closure" in str(refusal.value)


def test_two_disagreeing_spellings_are_refused() -> None:
    """When both spellings exist they name the same artifact and the same
    bytes, or the fragment is refused."""

    values = dict(_compose(*CELLS[0][:3]).values)
    values["d1_media_supplement"] = "receipts/artifacts/d1-a2t-calibration-400-tail2s.json"
    with pytest.raises(ConfigError) as refusal:
        d1_media_supplement_relpath(values)
    assert "disagree" in str(refusal.value)


def test_prose_under_a_prefixed_key_stays_inert() -> None:
    """The sealed frozen 400 explains in PROSE why it needs no supplement.
    That is not a declaration and must not be read as one."""

    values = json.loads(
        (REPO_ROOT / "configs/dataset/audio2tool-calibration-400.json").read_text(
            encoding="utf-8"
        )
    )
    assert values["a2t_calibration_d1_media_supplement"].startswith("none, by design")
    assert "a2t_calibration_d1_media_supplement_sha256" not in values
    assert d1_media_supplement_relpath(values) is None


# ---------------------------------------------------------------------------
# The real gate, on the real supplement files
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "experiment,dataset,cell_id,supplement",
    CELLS,
    ids=[cell[2] for cell in CELLS],
)
def test_the_real_gate_admits_the_cells_own_first_roster_id(
    experiment: str, dataset: str, cell_id: str, supplement: str, tmp_path: Path
) -> None:
    """Each cell's gate, built as ``preflight`` builds it, carries that cell's
    variant ids inside D1's identity closure."""

    values = _compose(experiment, dataset, cell_id).values
    gate = _preflight_gate(values, tmp_path)
    suffix = str(values["split_id"]).removeprefix("A2T-CALIBRATION-400")
    variant = {"-16K": "@16k", "-16K-TS2": "@16k+ts2", "-TS2": "@ts2"}[
        suffix.removesuffix("-SMOKE-4")
    ]
    gate.assert_media_identity_closure(CARRIER, [f"tier1_direct:000045{variant}"])


def test_the_real_gate_admits_16k_16kts2_and_ts2_ids_and_refuses_a_foreign_one(
    tmp_path: Path,
) -> None:
    """The three suffixed ids the six cells fly, each against ITS OWN cell's
    gate -- and a foreign id against every one of them.

    One gate carries exactly one supplement (``FrozenCoreGate.__post_init__``),
    so the three variants are three gates, which is what a flight sees.
    """

    gates = {
        "@16k": _preflight_gate(_compose(*CELLS[0][:3]).values, tmp_path),
        "@16k+ts2": _preflight_gate(_compose(*CELLS[2][:3]).values, tmp_path),
        "@ts2": _preflight_gate(_compose(*CELLS[4][:3]).values, tmp_path),
    }
    for variant, gate in gates.items():
        gate.assert_media_identity_closure(CARRIER, [f"tier1_direct:000045{variant}"])
        with pytest.raises(GateClosed) as refusal:
            gate.assert_media_identity_closure(CARRIER, ["tier1_direct:000045@forged"])
        assert "no D1-recorded media identity" in str(refusal.value)
        assert "outside D1's identity closure" in str(refusal.value)


def test_a_gate_built_without_the_supplement_refuses_the_very_id_the_flight_died_on(
    tmp_path: Path,
) -> None:
    """The pre-fix state, kept as a regression witness: strip the supplement
    the six fragments now declare and ``tier1_direct:000045@16k`` -- the first
    row of the frozen 400 roster, and the id the 2026-09-09 flight agent's
    first real request refused on -- falls straight back outside the closure."""

    values = _compose(*CELLS[0][:3]).values
    blind = FrozenCoreGate.for_study_repo(
        REPO_ROOT,
        tmp_path,
        tmp_path,
        runtime_receipt_relpath=runtime_receipt_relpath(values),
        expected_model_lock_key=model_lock_key(values),
    )
    with pytest.raises(GateClosed) as refusal:
        blind.assert_media_identity_closure(CARRIER, ["tier1_direct:000045@16k"])
    assert "tier1_direct:000045@16k" in str(refusal.value)
    # The unsuffixed sealed id was never the problem: it is in the base D1
    # manifest, which is why nothing before the first derived-media cell ever
    # noticed the missing declaration.
    blind.assert_media_identity_closure(CARRIER, ["tier1_direct:000045"])
