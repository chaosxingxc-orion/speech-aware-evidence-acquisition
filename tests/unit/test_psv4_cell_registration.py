"""P-SV-4 (Fold B, K6p key source): model-free pre-contact preflight, committed files only.

Re-derives, for BOTH registered cells (arm and four-row smoke), the refusals the worker raises before its first model
contact: FIT contact cap arithmetic, run-cumulative generation budget, distinct FIT/generation identities, consistent
attempt ids across the experiment fragments, baseline FIT blocks, registered plans, protocol and chain script, and the
registered-supply-binding between the plans and the cell baseline.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "flights" / "psv"))

import psv_family as ff  # noqa: E402

from speech_aware_evidence_acquisition.rails.controllers import default_phase_program  # noqa: E402

KEY = "psv4"
KINDS = ("arm", "smoke")
PREFIX = {"arm": "", "smoke": "smoke-"}
CEILING = 15


def _load(relpath: str) -> dict:
    return json.loads((REPO / relpath).read_text(encoding="utf-8"))


def _package() -> str:
    return ff.names(KEY, "arm")["package"]


def _baseline(kind: str) -> dict:
    return _load(f"configs/baseline/{ff.names(KEY, kind)['baseline']}.json")


def _experiment(kind: str) -> dict:
    return _load(f"configs/experiment/{ff.names(KEY, kind)['experiment']}.json")


def _plan(kind: str, plan_kind: str) -> dict:
    return _load(f"{_package()}/{PREFIX[kind]}{plan_kind}-plan-registered-v1.json")


def test_fit_gate_arithmetic_and_distinct_identities():
    from speech_aware_evidence_acquisition.core.flight.runtime import arm_uses_speech_feature_packets
    from speech_aware_evidence_acquisition.core.preparation_fit import validate_native_contact_fit_config

    for kind in KINDS:
        n = ff.names(KEY, kind)
        baseline = _baseline(kind)
        program = default_phase_program(baseline["policy"])
        assert baseline["policy"] == ff.NEW_PROGRAM
        assert program.max_contacts == CEILING
        spec = validate_native_contact_fit_config(baseline, program)
        assert spec is not None
        roster = _load(ff.ROSTER[kind]["relpath"])
        ids = [item["sample_id"] for item in roster["items"]]
        assert ids and len(set(ids)) == len(ids)
        rows = len(ids)
        assert rows == (4 if kind == "smoke" else 1080)
        assert arm_uses_speech_feature_packets(baseline["arm"]), kind
        assert spec["contact_cap"] == rows * program.max_contacts * (spec["max_speech_packets"] + 3), kind
        gen = _plan(kind, "generation")["execution_plan"]
        assert spec["run_id"] != gen["run_id"] and spec["attempt_id"] != gen["attempt_id"]
        assert spec["run_id"] == n["fit_run_id"] and spec["attempt_id"] == n["fit_attempt_id"]


def test_generation_budget_covers_the_worst_case_and_fit_cap_is_structural():
    for kind in KINDS:
        n = ff.names(KEY, kind)
        experiment = _experiment(kind)
        baseline = _baseline(kind)
        roster = _load(ff.ROSTER[kind]["relpath"])
        rows = len(roster["items"])
        audio = sum(float(i["audio_seconds"]) for i in roster["items"])
        declared = experiment["execution_plan"]
        assert declared["planned_model_calls"] >= rows * CEILING, kind
        assert declared["planned_speech_audio_seconds"] >= math.ceil(audio * CEILING - 1e-9), kind
        fam = experiment["family_budget"]
        assert fam["fit_endpoint_calls_cap"] == baseline["native_contact_fit"]["contact_cap"]
        for plan_kind in ("generation", "fit"):
            plan = _plan(kind, plan_kind)["execution_plan"]
            assert plan["run_id"] == (n["run_id"] if plan_kind == "generation" else n["fit_run_id"])
            assert plan["split_role"] == "discovery"
            assert plan["split_identity_hash"] == ff.ROSTER[kind]["split_identity_hash"]
            if plan_kind == "generation":
                assert plan["planned_model_calls"] == declared["planned_model_calls"] == fam["generation_calls_cap"]
            else:
                assert plan["planned_model_calls"] == fam["fit_endpoint_calls_cap"]


def test_attempt_and_run_ids_agree_across_fragments_plans_protocol_chain_and_queue():
    chain = (REPO / "scripts" / "flights" / "psv" / "batch_chain_psv.sh").read_text(encoding="utf-8")
    protocol = _load(f"{_package()}/protocol-registered-v1.json")["cells"]
    for kind in KINDS:
        n = ff.names(KEY, kind)
        cell = _experiment(kind)["cells"][0]
        fit_block = _baseline(kind)["native_contact_fit"]
        gen = _plan(kind, "generation")["execution_plan"]
        fit = _plan(kind, "fit")["execution_plan"]
        assert cell["attempt_id"] == n["attempt_id"] == gen["attempt_id"] == protocol[kind]["attempt_id"]
        assert cell["run_id"] == n["run_id"] == gen["run_id"] == protocol[kind]["run_id"]
        assert fit_block["attempt_id"] == n["fit_attempt_id"] == fit["attempt_id"] == protocol[kind]["fit_attempt_id"]
        assert fit_block["run_id"] == n["fit_run_id"] == fit["run_id"] == protocol[kind]["fit_run_id"]
        assert n["run_id"] != n["fit_run_id"] and n["attempt_id"] != n["fit_attempt_id"]
        # The chain builds the attempt ids from the cell slug: the f-string must spell the registered id.
        slug = ff.CELLS[KEY]["slug"]
        key = "smoke_attempt_id" if kind == "smoke" else "gen_attempt_id"
        spelled = n["attempt_id"].replace(slug, "{slug}")
        assert f'"{key}": f"{spelled}"' in chain, (kind, spelled)
    assert "ceiling_per_row\": 15" in chain and "expected_rows\": 1080" in chain


def test_registered_plans_declare_the_baseline_prepared_supply_verbatim_once_minted():
    for kind in KINDS:
        pinned = _baseline(kind).get("prepared_phase_supply")
        for plan_kind in ("generation", "fit"):
            declared = _plan(kind, plan_kind)["prepared_phase_supply"]
            if isinstance(pinned, dict) and pinned.get("sha256") not in (None, "", "MINTED_AT_THE_FLIP"):
                assert declared == pinned, (kind, plan_kind)
            else:
                assert declared["sha256"] == "MINTED_AT_THE_FLIP"
