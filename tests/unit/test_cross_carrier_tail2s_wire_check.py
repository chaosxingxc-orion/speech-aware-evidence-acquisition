"""``scripts/cross_carrier_tail2s_wire_check.py``'s stop classifier.

The check drives each ``@ts2`` cell with zero sockets and records the EXACT
line it stops at; ``classify`` turns that line into a stop class, and the
receipt-driven tests in ``test_cross_carrier_tail2s_fragments.py`` read the
class. These tests pin the classifier itself, on the gate's own messages,
independent of any committed receipt.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts/cross_carrier_tail2s_wire_check.py"
WIRE = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-07-cross-carrier-tail2s-wire-check/wire-check.json"
)


def _module():
    spec = importlib.util.spec_from_file_location(
        "cross_carrier_ts2_wire_check_test", SCRIPT
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MOD = _module()

#: The gate's own refusal for a run whose exposure row is marked consumed
#: (``contracts.gate_exposure``), as the SLURP ``@ts2`` cells raise it after
#: their exposure rows were marked consumed on 2026-09-09.
CONSUMED_STOP = (
    "speech_aware_evidence_acquisition.contracts.errors.GateClosed: exposure row "
    "for 'SAEA-SLURP-DEV1000-CLOSED-LIST-TAIL2S-SMOKE-V1' is already consumed; "
    "a consumed run cannot be re-executed"
)

#: The gate's refusal for a run that was never registered, as the two
#: Audio2Tool ``@ts2`` cells still raise it.
UNREGISTERED_STOP = (
    "speech_aware_evidence_acquisition.contracts.errors.GateClosed: model touch "
    "refused: run 'SAEA-A2T-OFFICIAL-PROTOCOL-TAIL2S-V1' has no pre-registered "
    "exposure row in /mnt/d/x/docs/exposure-ledger.md"
)


def test_a_consumed_row_stop_of_a_flown_cell_is_expected() -> None:
    assert MOD.classify(CONSUMED_STOP) == "consumed"
    assert "consumed" in MOD.EXPECTED_STOPS


def test_the_consumed_needle_is_the_gates_own_message() -> None:
    """The needle must be a substring of what the real gate raises, so the
    classification can never be satisfied by a paraphrase."""

    from speech_aware_evidence_acquisition.contracts import gate_exposure

    source = Path(gate_exposure.__file__).read_text(encoding="utf-8")
    needle = MOD.EXPECTED_STOPS["consumed"]
    # The message is split across two source lines; both halves are present.
    assert "is already consumed; a consumed run " in source
    assert "cannot be re-executed" in source
    assert needle in CONSUMED_STOP


@pytest.mark.parametrize(
    "text,expected",
    [
        (UNREGISTERED_STOP, "gate-not-authorized"),
        (
            "packet root disagrees with the promotion receipt",
            "slurp-packet-root-missing",
        ),
        (
            "sample x is not in the frozen audio2tool probe receipt",
            "a2t-gold-id-rail-missing",
        ),
        ("RuntimeError: something nobody preregistered", "UNEXPECTED"),
        ("", "UNEXPECTED"),
    ],
)
def test_every_other_classification_is_unchanged(text: str, expected: str) -> None:
    assert MOD.classify(text) == expected


def test_an_unregistered_cell_never_classifies_as_consumed() -> None:
    """A never-registered cell and a flown cell must stay distinguishable: the
    needles are pairwise disjoint, so no message can match two classes."""

    assert MOD.classify(UNREGISTERED_STOP) != "consumed"
    assert MOD.classify(CONSUMED_STOP) != "gate-not-authorized"
    needles = list(MOD.EXPECTED_STOPS.values())
    assert len(set(needles)) == len(needles)
    for outer in needles:
        assert not any(other != outer and other in outer for other in needles)


def test_the_committed_receipt_table_is_a_subset_of_the_live_table() -> None:
    """Adding a class must never rename or drop one the sealed ``cf566cb6``
    receipt recorded; the receipt schema is unchanged."""

    receipt = json.loads(WIRE.read_text(encoding="utf-8"))
    assert receipt["schema"] == "saea-cross-carrier-ts2-wire-check-v1"
    for name, needle in receipt["expected_stops"].items():
        assert MOD.EXPECTED_STOPS[name] == needle, name
    assert set(MOD.EXPECTED_STOPS) - set(receipt["expected_stops"]) == {"consumed"}
