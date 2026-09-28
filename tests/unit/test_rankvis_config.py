"""Cell RANKVIS (owner decision 171) is the registered AGREE arm with ONE key added, on a proven roster.

Config only: no data root, no lock, no adapter, no contact.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.config import compose
from speech_aware_evidence_acquisition.data.splits import prefixed, split_identity_hash
from speech_aware_evidence_acquisition.rails.controllers import default_phase_program
from speech_aware_evidence_acquisition.rails.native_episode_config import load_native_episode_config

REPO = Path(__file__).resolve().parents[2]
ROWS = 119
CELL = f"slurp-native-stage3-rankvis-fold-a-{ROWS}-v1"
RUN = f"SAEA-SLURP-STAGE3-RANKVIS-FOLD-A-{ROWS}-V1"
PARENT = "slurp-native-stage3-agree-w1-fold-a-v1"
PACKAGE = REPO / "docs/readiness/2026-09-27-slurp-stage3-rankvis-probe-fold-a-v1"
ONE_KEY = "native_episode.knowledge_value_rendering"
BOOKKEEPING = ("native_contact_fit.", "prepared_phase_supply", "what_this_is")
DECISION_ID = "slurp-stage3-rankvis-fold-a-119-admission-v1"


def _is_own_supply(relpath: str, run_id: str) -> bool:
    """This cell's own first-phase supply, minted under its own run id at the flip
    (item E16); the relpath/prefix identifies the cell, the digest is rewritten by
    scripts/flights/repin_cell.py and is never asserted here."""

    return re.fullmatch(rf"prepared/{re.escape(run_id)}/phase-supply-v\d+\.json", relpath) is not None


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _flatten(node, prefix: str = "") -> dict:
    out = {}
    if isinstance(node, dict):
        for key, value in node.items():
            out.update(_flatten(value, f"{prefix}{key}."))
    else:
        out[prefix[:-1]] = node
    return out


def _compose(experiment_stem: str):
    cell = _read(REPO / "configs/experiment" / f"{experiment_stem}.json")["cells"][0]
    return compose(REPO, cell["model_fragment"], cell["dataset_fragment"], cell["baseline_fragment"], experiment_stem)


@pytest.fixture(scope="module")
def experiment() -> dict:
    return _read(REPO / "configs/experiment" / f"{CELL}.json")


def test_the_one_key_is_the_only_treatment_difference():
    mine_cell = _read(REPO / "configs/experiment" / f"{CELL}.json")["cells"][0]
    parent_cell = _read(REPO / "configs/experiment" / f"{PARENT}.json")["cells"][0]
    for key in ("model_fragment", "dataset_fragment"):
        assert mine_cell[key] == parent_cell[key]
    mine = _flatten(_read(REPO / "configs/baseline" / f"{mine_cell['baseline_fragment']}.json"))
    parent = _flatten(_read(REPO / "configs/baseline" / f"{parent_cell['baseline_fragment']}.json"))
    moved = sorted(k for k in set(mine) | set(parent) if mine.get(k) != parent.get(k))
    treatment = [k for k in moved if not k.startswith(BOOKKEEPING)]
    assert treatment and all(k.startswith(ONE_KEY) for k in treatment), treatment
    # The composed cells agree on every native_episode, store and phase key but the one.
    composed = _flatten(_compose(CELL).values)
    composed_parent = _flatten(_compose(PARENT).values)
    for key in set(composed) | set(composed_parent):
        shared = key.startswith(("native_episode.", "knowledge_stores.", "phase_material.", "policy", "scorers"))
        if shared and not key.startswith(ONE_KEY):
            assert composed.get(key) == composed_parent.get(key), key


def test_the_key_parses_through_the_real_loader():
    values = _compose(CELL).values
    program = default_phase_program(values["policy"])
    parsed = load_native_episode_config(values, program)
    assert parsed.knowledge_value_rendering == {
        "schema": "saea-knowledge-value-rendering-v1",
        "order": "retrieval-rank",
        "rank_visible": True,
        "stores": ["intent-boundaries", "train-exemplars"],
    }
    assert parsed.max_contacts == 11
    parent_values = _compose(PARENT).values
    assert load_native_episode_config(parent_values, default_phase_program(parent_values["policy"])).knowledge_value_rendering is None


def test_the_roster_is_the_derivation_and_readiness_is_flip_indifferent(experiment: dict):
    derivation = _read(PACKAGE / "roster-derivation-v1.json")
    ids = derivation["roster"]["ids"]
    assert len(ids) == ROWS == experiment["population"]["count"]
    assert experiment["populations"][0]["ids"] == ids
    assert experiment["population"]["split_identity_hash"] == split_identity_hash(prefixed("slurp", ids))
    assert derivation["proof_a_partition_reproduced"]["differences"] == []
    assert derivation["synthesis_subset"]["matches_synthesis"] is True
    cell = experiment["cells"][0]
    assert cell["run_id"] == RUN
    readiness = cell["readiness"]
    assert readiness["state"] in ("held", "ready")
    # HELD as registered; the flip's re-pin adds the family decision and mints this cell's OWN
    # first-phase supply under its own run id (item E16), never a foreign one -- the COMP-1
    # flip is the pattern.
    if readiness["state"] == "held":
        assert readiness["requirements"] == []
    else:
        decisions = [r for r in readiness["requirements"] if r.get("kind") == "decision"]
        assert [d["expected_decision_id"] for d in decisions] == [DECISION_ID]
        own = [r for r in readiness["requirements"] if r["kind"] == "preparation"]
        assert len(own) == 1 and _is_own_supply(own[0]["relpath"], cell["run_id"]), own
    assert experiment["stage3_algorithm"]["id"] == "none"
    facts = _read(PACKAGE / "registered-facts-v1.json")
    assert facts["stage3_measurement"][RUN]["claims_benefit"] is False
    assert facts["stage3_measurement"][RUN]["measurement_design"] == "form-proof"
    assert experiment["family_budget"]["generation_calls_cap"] == ROWS * 11


def test_no_prepared_supply_is_committed():
    baseline = _read(REPO / "configs/baseline" / f"slurp-native-stage3-rankvis-fold-a-{ROWS}-baseline-v1.json")
    # HELD as registered; the flip's re-pin mints this cell's OWN first-phase supply under its
    # own run id (item E16), never a foreign one -- the COMP-1 flip is the pattern.
    supply = baseline.get("prepared_phase_supply")
    assert supply is None or _is_own_supply(supply["relpath"], RUN), supply
    assert baseline["native_contact_fit"]["contact_cap"] == ROWS * 11 * 4
