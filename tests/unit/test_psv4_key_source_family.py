"""P-SV-4 (scripts/flights/psv/psv_family.py CELLS['psv4']): the key_source cell's identities, its
derived baseline fragments (arm and smoke) loading through the real config loader with the
b-k6p key_source branch, and its registered measurement declaration. Model-free."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
for extra in (REPO / "scripts" / "flights" / "psv", REPO / "scripts" / "checks"):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

import psv_family as ff  # noqa: E402
import stage3_effect_floor_check as floor_gate  # noqa: E402

from speech_aware_evidence_acquisition.rails.controllers import default_phase_program  # noqa: E402
from speech_aware_evidence_acquisition.rails.native_episode_config import (  # noqa: E402
    load_native_episode_config,
)


def _baseline(kind: str) -> dict:
    return json.loads((REPO / f"configs/baseline/{ff.names('psv4', kind)['baseline']}.json").read_text(encoding="utf-8"))


def test_psv4_names_its_own_dated_package_and_leaves_the_others_unchanged():
    n = ff.names("psv4", "arm")
    assert n["package"] == "docs/readiness/2026-09-30-slurp-stage3-psv4-fold-b-v1"
    assert n["run_id"] == "SAEA-SLURP-STAGE3-PSV4-FOLD-B-V1"
    assert n["read_run"] == "SAEA-SLURP-STAGE3-PSV4-FOLD-B-BRANCH-READ-V1"
    assert ff.names("psv3", "arm")["package"] == "docs/readiness/2026-09-29-slurp-stage3-psv3-fold-b-v1"
    assert ff.fit_measure_relpath("psv4") == ff.FIT_MEASURE_V2
    assert ff.fit_measure_relpath("psv1") == ff.FIT_MEASURE


def test_the_k6p_key_source_swaps_facet_and_query_and_keeps_the_agreement():
    ks = ff.k6p_key_source()
    assert ks["store_id"] == ff.BOUNDARY_STORE_ID
    assert ks["facet_source"]["sha256"] == ff.K6P_KEY["sha256"]
    assert ks["query_source"]["sha256"] == ff.K6P_QUERIES_FOLD_B["sha256"]
    assert ks["query_source"]["embedded_signal"].startswith("speech:")
    assert ks["agreement_source"] is None


def test_the_derived_psv4_fragments_load_with_the_b_k6p_branch():
    for kind in ("arm", "smoke"):
        values = _baseline(kind)
        values.setdefault("carrier_lock_key", "slurp")  # composed from the dataset fragment in a real flight
        assert values["policy"] == ff.NEW_PROGRAM
        program = default_phase_program(values["policy"])
        config = load_native_episode_config(values, program)
        assert config.max_contacts == ff.NEW_CEILING
        role = next(r for r in config.roles if r.role_kind == "perception")
        group = role.perception_branches
        assert group.level == 2 and group.branch_ids == ("b-k6p", ff.ARM_T, ff.ARM_A)
        b = group.branch("b-k6p")
        assert b.key_source.as_json() == ff.k6p_key_source()
        assert not b.knobs and b.presentation_id is None and b.min_candidates is None
        assert group.delivering_branch.key_source is None and group.twin_branch.key_source is None
        # the cell's own first-phase pins are untouched: A reads the flown description key and Fold B queries
        spec = values["knowledge_stores"][ff.BOUNDARY_STORE_ID]["phase_supply"][ff.FIRST_PHASE_ID]
        assert spec["facet_source"]["relpath"] != ff.K6P_KEY["relpath"]
        assert spec["query_source"]["relpath"] != ff.K6P_QUERIES_FOLD_B["relpath"]
        assert spec["agreement_source"]["relpath"] == ff.AGREEMENT["relpath"]


def test_the_registered_declaration_is_intent_primary_and_clears_the_same_flight_floor():
    package = REPO / ff.names("psv4", "arm")["package"]
    facts = json.loads((package / "registered-facts-v1.json").read_text(encoding="utf-8"))
    block = facts["stage3_measurement"]["SAEA-SLURP-STAGE3-PSV4-FOLD-B-V1"]
    assert block["measurement_design"] == "same-flight-perception-variant"
    assert block["primary_metric_key"] == "intent" and block["claims_benefit"] is True
    assert block["expected_effect_pp"] == 1.1 and block["rows"] == 1080 and block["claim"] == "nominated"
    floor, _ = floor_gate.floor_for("same-flight-perception-variant", 1080, metric="intent")
    assert floor < block["expected_effect_pp"]
    assert facts["key_source"]["block"] == ff.k6p_key_source()
