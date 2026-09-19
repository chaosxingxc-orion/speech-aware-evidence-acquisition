"""E11: the delivery node, read against the SEALED bytes of cell B1.

Zero contact of any kind. The sealed arm
``SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-TRAIN-FOLD-A-RECOVERY-V2`` (module
M1, ADMITTED 2026-09-18) is read READ-ONLY from ``SPEECHRL_DATA_DIR`` and
copied under the test's own ``tmp_path`` before anything else happens; no run
directory is ever written, no scorer is run, no gold is read, and no
utterance text or filler is printed. The whole module skips when the data
root or that run is absent, so it is a no-op on any machine but the primary
dev host.

WHAT IS PROVEN, AND WHY IT IS THE RIGHT THING TO PROVE. The official SLURP
number of a set of rows is a pure function of the per-row PREDICTION TRIPLE
(scenario, action, entities) the scorer hands ``evaluate.py``, together with
the fixed gold. The v3 SCORER builds that triple by parsing the row's text
and then applying ``project_slu_label_v3`` and ``normalize_filler_p2``; the
delivery NODE applies the same two functions and renders the result as the
delivered answer, which the OFFICIAL (unprojected) scorer then parses back
into a triple. So if, on every sealed row, the triple parsed back out of the
node's delivered text is byte-identical to the triple the v3 scorer builds
from the same row, then the official number of the in-agent cell is exactly
the v3-projected number of the sealed arm -- identically, not to two decimal
places. That is what this module asserts, row by row, over all 1,080 rows,
and it needs neither a scorer run nor gold to do it.
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.analysis.deliver_normaliser_replay import replay
from speech_aware_evidence_acquisition.core.base import DELIVERY_NORMALISERS

# Importing rails.delivery_normalisers is what POPULATES
# core.base.DELIVERY_NORMALISERS.
from speech_aware_evidence_acquisition.rails import (  # noqa: F401
    delivery_normalisers as _delivery_normalisers,
)
from speech_aware_evidence_acquisition.rails.delivery_normalisers import (
    DELIVER_NORMALISE_V3,
)
from speech_aware_evidence_acquisition.rails.slurp_projection_v3 import (
    normalize_filler_p2,
    project_slu_label_v3,
)
from speech_aware_evidence_acquisition.reproduction.slurp_scoring import (
    SlotEntity,
    parse_slu_response,
)

RUN_ID = "SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-TRAIN-FOLD-A-RECOVERY-V2"
ATTEMPT = (
    "attempt-slurp-native-exemplars-k20-anchor-train-fold-a-generation-recovery-v2"
)
OUTPUTS_NAME = f"{RUN_ID}.outputs.jsonl"


def _sealed_outputs_path() -> Path | None:
    root = os.environ.get("SPEECHRL_DATA_DIR")
    if not root:
        return None
    path = Path(root) / "runs" / RUN_ID / ATTEMPT / OUTPUTS_NAME
    return path if path.is_file() else None


pytestmark = pytest.mark.skipif(
    _sealed_outputs_path() is None,
    reason="the sealed B1 recovery arm is not present under SPEECHRL_DATA_DIR",
)


@pytest.fixture(scope="module")
def sealed_copy(tmp_path_factory):
    """A private copy of the sealed outputs. Nothing under
    ``SPEECHRL_DATA_DIR`` is opened for writing at any point."""

    source = _sealed_outputs_path()
    target_dir = tmp_path_factory.mktemp("sealed-b1")
    target = target_dir / "outputs.jsonl"
    shutil.copyfile(source, target)
    return target


@pytest.fixture(scope="module")
def sealed_rows(sealed_copy):
    rows = []
    for line in sealed_copy.read_text(encoding="utf-8").split("\n"):
        if line.strip():
            rows.append(json.loads(line))
    assert rows
    return rows


@pytest.fixture(scope="module")
def inventory():
    """The REAL TRAIN-mined legal intent inventory -- the same object the v3
    scorer loads, so the comparison below is between two applications of one
    rule rather than between two label spaces."""

    from speech_aware_evidence_acquisition.data.lock import (
        data_root,
        load_lock,
        umbrella_lock_path,
    )
    from speech_aware_evidence_acquisition.reproduction.slurp_official_eval import (
        load_legal_intent_inventory,
    )

    return load_legal_intent_inventory(load_lock(umbrella_lock_path()), data_root())


def _scorer_side_triple(text, inventory):
    """The prediction triple ``reproduction.slurp_official_eval.
    score_slurp_outputs_official(project_labels=True, projection_version='v3',
    project_fillers=True)`` hands the official evaluator for one row: parse,
    then the v3 label rule, then the P2 filler rule. Written in the scorer's
    own order, calling the scorer's own functions."""

    scenario, action, entities, parsed = parse_slu_response(text)
    if parsed:
        outcome = project_slu_label_v3(scenario, action, inventory, parsed=parsed)
        scenario, action = outcome.scenario, outcome.action
    entities = tuple(
        SlotEntity(type=entity.type, filler=normalize_filler_p2(entity.filler))
        for entity in entities
    )
    return scenario, action, entities, parsed


def test_the_node_reproduces_the_v3_scorer_projection_on_every_sealed_row(
    sealed_rows, inventory
):
    normaliser = DELIVERY_NORMALISERS.resolve(DELIVER_NORMALISE_V3)
    compared = 0
    unparsed = 0
    changed = 0
    for row in sealed_rows:
        text = row["text"]
        outcome = normaliser(text, inventory=inventory)
        expected = _scorer_side_triple(text, inventory)
        if not expected[3]:
            # An unparsed answer has no triple to project; the node delivers
            # it byte-identically, exactly as the scorer leaves it unparsed.
            unparsed += 1
            assert outcome.text == text
            assert outcome.changed is False
            continue
        delivered = parse_slu_response(outcome.text)
        assert delivered[3] is True
        assert delivered[0] == expected[0]
        assert delivered[1] == expected[1]
        assert tuple(delivered[2]) == expected[2]
        compared += 1
        changed += int(outcome.changed)
    assert compared == len(sealed_rows) - unparsed
    assert compared > 0
    # The arm is not already normalised: the node is doing real work here.
    assert changed > 0


def test_the_node_is_idempotent_on_every_sealed_row(sealed_rows, inventory):
    normaliser = DELIVERY_NORMALISERS.resolve(DELIVER_NORMALISE_V3)
    for row in sealed_rows:
        once = normaliser(row["text"], inventory=inventory)
        twice = normaliser(once.text, inventory=inventory)
        assert twice.text == once.text
        assert twice.changed is False


def test_the_offline_replay_reproduces_the_node_over_the_sealed_arm(
    sealed_copy, sealed_rows, tmp_path, inventory
):
    """The model-free replay entry point over the sealed arm: it re-applies
    the SAME registered rule to every row, writes a fresh scoreable
    ``outputs.jsonl`` and never touches the input."""

    before = sealed_copy.read_bytes()
    provenance = replay(
        outputs_path=sealed_copy,
        normaliser_id=DELIVER_NORMALISE_V3,
        output_dir=tmp_path / "replay",
    )
    assert sealed_copy.read_bytes() == before
    assert provenance["model_calls"] == 0
    assert provenance["rows"] == len(sealed_rows)
    assert provenance["rows_already_normalised"] == 0
    assert provenance["rows_changed"] > 0

    normaliser = DELIVERY_NORMALISERS.resolve(DELIVER_NORMALISE_V3)
    replayed = {
        json.loads(line)["sample_id"]: json.loads(line)
        for line in (tmp_path / "replay" / "outputs.jsonl")
        .read_text(encoding="utf-8")
        .split("\n")
        if line.strip()
    }
    assert set(replayed) == {row["sample_id"] for row in sealed_rows}
    for row in sealed_rows:
        expected = normaliser(row["text"], inventory=inventory)
        assert replayed[row["sample_id"]]["text"] == expected.text
