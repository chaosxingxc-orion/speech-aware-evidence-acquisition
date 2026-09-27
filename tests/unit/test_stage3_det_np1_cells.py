"""Cell DET: the single-slot, prompt-cache-off request-identical pair of the locked plan.

Byte proofs, in the ``tests/unit/test_stage3_roll_aa_baseline_cell.py`` style:

* the DET model fragment equals the resident np4 fragment on every key except
  ``server_args``, ``profile_slot_count`` and ``geometry_basis``, and its
  server argv differs from the resident's in EXACTLY four flags: ``-np`` 4 -> 1,
  ``-c`` 98304 -> 24576, ``--cache-prompt`` -> ``--no-cache-prompt``, and
  ``--slot-prompt-similarity 0`` removed;
* the two halves of the geometry agree -- the fragment's ``-np``/``-c`` and
  the baseline's ``serving_slots``/``serving_slot_tokens`` -- so
  ``core.session.serving.merge_server_args`` is the identity on ``-np``/``-c``
  and ``resolve_serving_profile`` resolves one 24,576-token slot;
* each DET baseline equals the LOCKED PLAN baseline on every key except
  ``serving_slots`` (the one geometry key) and the per-cell bookkeeping;
  pass B equals pass A except for its FIT identity and its prose;
* the experiment fragments are held, empty-requirements, budgeted at the
  program ceiling, bound to the first 50 rows of TRAIN Fold A in roster order
  (the sealed PLAN arm's own first 50), and labelled ``stage3_algorithm``
  ``none``;
* the roster receipt is a pure prefix of the Fold A v2 receipt with a
  recomputed split identity;
* the composed-config diff against the PLAN lock is exactly the geometry keys
  plus per-cell bookkeeping, key by key and fragment by fragment; and the
  hashes the readiness package registers reproduce from ``core.config.compose``.

Zero model, tokenizer, encoder, scorer, server and network contacts; no
``SPEECHRL_DATA_DIR`` read.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.config import compose, protocol_hash, read_fragment
from speech_aware_evidence_acquisition.core.roster import verify_roster
from speech_aware_evidence_acquisition.core.session.serving import merge_server_args
from speech_aware_evidence_acquisition.data.splits import prefixed, split_identity_hash

REPO_ROOT = Path(__file__).resolve().parents[2]
MODELS = REPO_ROOT / "configs" / "model"
BASELINES = REPO_ROOT / "configs" / "baseline"
EXPERIMENTS = REPO_ROOT / "configs" / "experiment"
CAMPAIGNS = REPO_ROOT / "configs" / "campaign"
ROSTERS = REPO_ROOT / "docs" / "receipts" / "rosters"
PACKAGE = REPO_ROOT / "docs" / "readiness" / "2026-09-26-slurp-stage3-det-np1-fold-a-50-v1"
DERIVE = REPO_ROOT / "scripts" / "flights" / "derive_slurp_det_np1_cells.py"

RESIDENT = "q4km-mmproj-free-slurp-native-bounded-perception-proof-np4-ctx24k-max512-v1"
DET_MODEL = "q4km-mmproj-free-slurp-native-bounded-perception-proof-np1-nocache-ctx24k-max512-v1"
PLAN_BASELINE = "slurp-native-default-plan-lock-baseline-v1"
PLAN_EXPERIMENT = "slurp-native-default-plan-lock-v1"
DATASET = "slurp-speech-native-evo-fold-a-1080"
SESSION = "serving-slurp-native-det-np1-nocache-v1"
ROWS = 50
CEILING = 11

CELLS = {
    "a": "slurp-native-stage3-det-np1-fold-a-50-a-v1",
    "b": "slurp-native-stage3-det-np1-fold-a-50-b-v1",
}
RUNS = {
    "a": "SAEA-SLURP-STAGE3-DET-NP1-FOLD-A-50-A-V1",
    "b": "SAEA-SLURP-STAGE3-DET-NP1-FOLD-A-50-B-V1",
}

BASELINE_BOOKKEEPING = frozenset({"native_contact_fit", "prepared_phase_supply", "what_this_is"})
GEOMETRY_KEY = "serving_slots"
MODEL_MOVED = frozenset({"server_args", "profile_slot_count", "geometry_basis"})
EXPERIMENT_BOOKKEEPING = frozenset({
    "cells", "date", "execution_plan", "experiment_id", "failure_policy", "family_budget",
    "fragment_kind", "generation_budget", "population", "populations", "purpose",
    "service_session", "stage3_algorithm",
})


#: Cell DET as REGISTERED (8bcd4eb3), before the flips (3e882625 pass a, 99a3f1f5 pass b) re-pinned it with
#: core.flight.repin: each flip set readiness ready and pinned the pass's OWN minted supply into its baseline.
_REGISTERED_COMMIT = "8bcd4eb3"
DECISION_ID = "slurp-stage3-det-np1-fold-a-50-admission-v1"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _registered_bytes(relpath: str) -> bytes:
    import subprocess

    return subprocess.run(
        ["git", "-C", str(REPO_ROOT), "show", f"{_REGISTERED_COMMIT}:{relpath}"],
        check=True, capture_output=True,
    ).stdout


def _own_supply(p: str) -> str:
    return f"prepared/{RUNS[p]}/phase-supply-v1.json"


def _derive_module():
    spec = importlib.util.spec_from_file_location("derive_slurp_det_np1_cells", DERIVE)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _flags(args: list[str]) -> dict[str, list[object]]:
    return _derive_module().argv_flags(args)


# --------------------------------------------------------------------------
# the model fragment
# --------------------------------------------------------------------------


def test_the_det_fragment_moves_only_the_geometry_keys() -> None:
    resident = _load(MODELS / f"{RESIDENT}.json")
    det = _load(MODELS / f"{DET_MODEL}.json")
    assert set(resident) == set(det)
    moved = {key for key in resident if resident[key] != det[key]}
    assert moved == MODEL_MOVED, sorted(moved ^ MODEL_MOVED)
    assert det["decoding_params"] == {
        "temperature": 0, "seed": 20260913, "max_tokens": 512, "id_slot": "per-sample"
    }
    assert det["prompt_order"] == resident["prompt_order"]
    assert det["server_env"] == resident["server_env"]
    assert det["runtime_receipt"] == resident["runtime_receipt"]
    assert det["model_lock_key"] == resident["model_lock_key"]
    assert det["profile_slot_count"] == 1


def test_the_server_argv_differs_in_exactly_four_flags() -> None:
    resident = _load(MODELS / f"{RESIDENT}.json")["server_args"]
    det = _load(MODELS / f"{DET_MODEL}.json")["server_args"]
    left, right = _flags(resident), _flags(det)
    moved = {flag for flag in set(left) | set(right) if left.get(flag) != right.get(flag)}
    assert moved == {"-np", "-c", "--cache-prompt", "--no-cache-prompt", "--slot-prompt-similarity"}
    assert left["-np"] == ["4"] and right["-np"] == ["1"]
    assert left["-c"] == ["98304"] and right["-c"] == ["24576"]
    assert left["--cache-prompt"] == [True] and "--cache-prompt" not in right
    assert right["--no-cache-prompt"] == [True] and "--no-cache-prompt" not in left
    assert left["--slot-prompt-similarity"] == ["0"] and "--slot-prompt-similarity" not in right
    # everything else rides through unchanged, in the resident's own order
    for flag in ("-b", "-ub", "-fa", "-ngl", "-ctk", "-ctv", "--cache-ram", "--no-cache-idle-slots"):
        assert left[flag] == right[flag], flag
    # the exact edit, token by token: -c and -np re-valued, --cache-prompt renamed,
    # the --slot-prompt-similarity pair removed, nothing reordered
    module = _derive_module()
    assert resident == module.EXPECTED_RESIDENT_ARGS
    assert det == module.DET_ARGS
    expected = list(resident)
    expected[expected.index("-c") + 1] = "24576"
    expected[expected.index("-np") + 1] = "1"
    expected[expected.index("--cache-prompt")] = "--no-cache-prompt"
    similarity = expected.index("--slot-prompt-similarity")
    del expected[similarity:similarity + 2]
    assert det == expected


def test_the_two_halves_of_the_geometry_agree() -> None:
    det = _load(MODELS / f"{DET_MODEL}.json")
    args = det["server_args"]
    slots, context = int(args[args.index("-np") + 1]), int(args[args.index("-c") + 1])
    assert (slots, context) == (1, 24576)
    for p in ("a", "b"):
        baseline = _load(BASELINES / f"slurp-native-stage3-det-np1-fold-a-50-{p}-baseline-v1.json")
        assert baseline["serving_slots"] == slots
        assert baseline["serving_slot_tokens"] == context // slots == 24576
        merged = merge_server_args(
            args, slots=baseline["serving_slots"],
            context_tokens=baseline["serving_slots"] * baseline["serving_slot_tokens"],
        )
        assert merged == args  # the merge is the identity: nothing is silently overridden
    assert det["profile_slot_count"] == slots


def test_resolve_serving_profile_resolves_one_slot_of_24576() -> None:
    from speech_aware_evidence_acquisition.core.session.serving import resolve_serving_profile

    profile = resolve_serving_profile(REPO_ROOT, DET_MODEL)
    assert profile["serving_geometry"] == {"slots": 1, "slot_tokens": 24576, "max_tokens": 512}
    argv = profile["extra_argv"]
    assert "--no-cache-prompt" in argv and "--cache-prompt" not in argv
    assert "--slot-prompt-similarity" not in argv
    assert argv[argv.index("-np") + 1] == "1" and argv[argv.index("-c") + 1] == "24576"
    resident = resolve_serving_profile(REPO_ROOT, RESIDENT)
    assert resident["serving_geometry"] == {"slots": 4, "slot_tokens": 24576, "max_tokens": 512}
    assert profile["runtime_receipt_sha256"] == resident["runtime_receipt_sha256"]
    assert profile["session_role"] == resident["session_role"]
    assert profile["model_root"] == resident["model_root"]


# --------------------------------------------------------------------------
# baselines
# --------------------------------------------------------------------------


@pytest.mark.parametrize("p", ["a", "b"])
def test_each_baseline_moves_only_serving_slots_against_the_plan_lock(p: str) -> None:
    plan = _load(BASELINES / f"{PLAN_BASELINE}.json")
    det = _load(BASELINES / f"slurp-native-stage3-det-np1-fold-a-50-{p}-baseline-v1.json")
    moved = {
        key for key in (set(plan) | set(det)) - BASELINE_BOOKKEEPING
        if plan.get(key) != det.get(key)
    }
    assert moved == {GEOMETRY_KEY}, sorted(moved)
    assert plan["serving_slots"] == 4 and det["serving_slots"] == 1
    assert det["serving_slot_tokens"] == plan["serving_slot_tokens"] == 24576
    # absent as registered; after the flip, this pass's own minted supply and never a foreign one
    assert det.get("prepared_phase_supply", {"relpath": _own_supply(p)})["relpath"] == _own_supply(p)
    assert det["native_contact_fit"] == {
        "attempt_id": f"attempt-slurp-native-stage3-det-np1-fold-a-50-{p}-fit-v1",
        "contact_cap": ROWS * CEILING * 4,
        "max_speech_packets": 1,
        "run_id": f"SAEA-SLURP-STAGE3-DET-NP1-FOLD-A-50-{p.upper()}-FIT-V1",
    }
    # the knobs that define the locked plan, spelled out
    assert det["native_episode"] == plan["native_episode"]
    assert det["knowledge_stores"] == plan["knowledge_stores"]
    assert det["phase_material"] == plan["phase_material"]
    assert det["policy"] == plan["policy"] == "phase-native-candidates-review-revise-v1"
    assert det["scorers"] == plan["scorers"]
    assert det["native_episode"]["finite_completion_policy"] == "deliver-latest-or-abstain"
    assert det["native_episode"]["react_exhaustion_policy"] == "continue-without-answer"


def test_pass_b_equals_pass_a_except_its_fit_identity_and_prose() -> None:
    a = _load(BASELINES / "slurp-native-stage3-det-np1-fold-a-50-a-baseline-v1.json")
    b = _load(BASELINES / "slurp-native-stage3-det-np1-fold-a-50-b-baseline-v1.json")
    moved = {key for key in set(a) | set(b) if a.get(key) != b.get(key)}
    # each pass's flip pins its own minted supply, so the pin differs by run id once either pass is flipped
    assert moved - {"prepared_phase_supply"} == {"native_contact_fit", "what_this_is"}, sorted(moved)
    for p, baseline in (("a", a), ("b", b)):
        assert baseline.get("prepared_phase_supply", {"relpath": _own_supply(p)})["relpath"] == _own_supply(p)


# --------------------------------------------------------------------------
# roster and experiments
# --------------------------------------------------------------------------


def test_the_roster_is_a_pure_prefix_of_fold_a() -> None:
    parent = _load(ROSTERS / "slurp-evo-fold-a-v2.json")
    receipt = _load(ROSTERS / "slurp-stage3-det-fold-a-50-v1.json")
    assert receipt["items"] == parent["items"][:ROWS]
    assert receipt["roster_role"] == "construction" and receipt["split_role"] == "discovery"
    ids = [item["sample_id"] for item in receipt["items"]]
    assert verify_roster(receipt) == split_identity_hash(prefixed("slurp", ids))
    assert receipt["parent"]["split_identity_hash"] == parent["split_identity_hash"]
    assert sum(receipt["strata_counts"].values()) == ROWS
    assert len(receipt["strata_counts"]) == 10


@pytest.mark.parametrize("p", ["a", "b"])
def test_the_experiment_fragments_are_held_and_budgeted_at_the_ceiling(p: str) -> None:
    document = _load(EXPERIMENTS / f"{CELLS[p]}.json")
    plan = _load(EXPERIMENTS / f"{PLAN_EXPERIMENT}.json")
    receipt = _load(ROSTERS / "slurp-stage3-det-fold-a-50-v1.json")
    ids = [item["sample_id"] for item in receipt["items"]]
    view = _load(REPO_ROOT / "configs" / "dataset" / f"{DATASET}.json")
    assert ids == [item["sample_id"] for item in view["items"]][:ROWS]
    assert ids == plan["populations"][0]["ids"][:ROWS]

    cell = document["cells"][0]
    assert len(document["cells"]) == 1
    assert cell["cell_id"] == CELLS[p] and cell["run_id"] == RUNS[p]
    assert cell["model_fragment"] == DET_MODEL
    assert cell["baseline_fragment"] == f"slurp-native-stage3-det-np1-fold-a-50-{p}-baseline-v1"
    assert cell["dataset_fragment"] == DATASET
    readiness = cell["readiness"]
    assert readiness["state"] in ("held", "ready")
    if readiness["state"] == "held":
        assert readiness["requirements"] == []
    else:
        by_kind = {req["kind"]: req for req in readiness["requirements"]}
        assert len(by_kind) == len(readiness["requirements"]) == 2, readiness["requirements"]
        assert by_kind["decision"]["expected_decision_id"] == DECISION_ID
        assert by_kind["preparation"]["relpath"] == _own_supply(p)
    assert cell["allowed_execution_stages"] == ["check", "prepare-supply", "worker", "campaign"]
    assert document["service_session"] == SESSION
    assert document["split_id"] == plan["split_id"] == "SLURP-EVO-FOLD-A-V2"
    assert document["population"]["count"] == ROWS
    assert document["populations"] == [{"dataset_fragment": DATASET, "ids": ids}]
    assert document["population"]["split_identity_hash"] == split_identity_hash(prefixed("slurp", ids))
    assert document["population"]["roster_receipt"] == "docs/receipts/rosters/slurp-stage3-det-fold-a-50-v1.json"
    assert document["execution_plan"]["planned_model_calls"] == ROWS * CEILING == 550
    assert document["family_budget"]["generation_calls_cap"] == 550
    assert document["family_budget"]["fit_endpoint_calls_cap"] == 2200
    assert document["family_budget"]["native_task_contract_calls_cap"] == 300
    assert document["family_budget"]["repeated_speech_audio_seconds_cap"] == 1184
    assert document["family_budget"]["official_complete_scoring_jobs"] == 1
    assert document["execution_plan"]["execution_profile"] == "bounded-discovery-probe"
    assert document["stage3_algorithm"]["id"] == "none"
    assert document["stage3_algorithm"]["operators_used"] == []
    assert document["preserve_wire_responses"] is True
    campaign = _load(CAMPAIGNS / f"{CELLS[p]}.json")
    assert campaign == {"cells": [{"cell": CELLS[p], "experiment": CELLS[p]}],
                        "schema": "saea-campaign-plan-v1"}


def test_the_derivation_reproduces_every_committed_file() -> None:
    # Against the files as REGISTERED: the flips re-pinned the baselines and plans this derivation wrote.
    module = _derive_module()
    for relpath, text in module.derived_artifacts(REPO_ROOT):
        assert _registered_bytes(relpath).decode("utf-8") == text, relpath


# --------------------------------------------------------------------------
# the composed diff and the registered hashes
# --------------------------------------------------------------------------


def _origins(model: str, baseline: str, experiment: str) -> dict[str, str]:
    origins: dict[str, str] = {}
    for kind, name in (("model", model), ("dataset", DATASET), ("baseline", baseline), ("experiment", experiment)):
        for key in read_fragment(REPO_ROOT, kind, name):
            origins[key] = kind
    return origins


def test_the_composed_diff_against_the_plan_lock_is_geometry_plus_bookkeeping() -> None:
    plan = compose(REPO_ROOT, RESIDENT, DATASET, PLAN_BASELINE, PLAN_EXPERIMENT)
    plan_origins = _origins(RESIDENT, PLAN_BASELINE, PLAN_EXPERIMENT)
    for p in ("a", "b"):
        baseline = f"slurp-native-stage3-det-np1-fold-a-50-{p}-baseline-v1"
        det = compose(REPO_ROOT, DET_MODEL, DATASET, baseline, CELLS[p])
        det_origins = _origins(DET_MODEL, baseline, CELLS[p])
        moved: dict[str, set[str]] = {"model": set(), "dataset": set(), "baseline": set(), "experiment": set()}
        for key in set(plan.values) | set(det.values):
            if plan.values.get(key) != det.values.get(key):
                moved[det_origins.get(key) or plan_origins[key]].add(key)
        assert moved["model"] == MODEL_MOVED, sorted(moved["model"])
        assert moved["dataset"] == set()
        assert moved["baseline"] == BASELINE_BOOKKEEPING | {GEOMETRY_KEY}, sorted(moved["baseline"])
        assert moved["experiment"] <= EXPERIMENT_BOOKKEEPING, sorted(moved["experiment"] - EXPERIMENT_BOOKKEEPING)
        assert det.values["serving_slots"] == 1 and plan.values["serving_slots"] == 4
        assert det.values["decoding_params"] == plan.values["decoding_params"]
        assert det.values["arm"] == plan.values["arm"]


def test_the_registered_hashes_reproduce_from_compose() -> None:
    facts = _load(PACKAGE / "registered-facts-v1.json")
    for p in ("a", "b"):
        baseline = f"slurp-native-stage3-det-np1-fold-a-50-{p}-baseline-v1"
        composed = compose(REPO_ROOT, DET_MODEL, DATASET, baseline, CELLS[p])
        document = _load(EXPERIMENTS / f"{CELLS[p]}.json")
        split = document["population"]["split_identity_hash"]
        identity = facts["cells"][p]
        assert identity["composed_config_hash"] == composed.config_hash
        assert identity["protocol_hash"] == protocol_hash(composed.config_hash, composed.values["arm"], split)
        assert identity["split_identity_hash"] == split
        assert identity["run_id"] == RUNS[p]
        plan = _load(PACKAGE / f"{p}-generation-plan-registered-v1.json")
        assert plan["cell"] == CELLS[p]
        assert plan["composed_config_hash"] == composed.config_hash
        assert plan["execution_plan"]["protocol_hash"] == identity["protocol_hash"]
        assert plan["expected_session_id"] == SESSION
    measurement = facts["stage3_measurement"]
    for run_id in RUNS.values():
        block = measurement[run_id]
        assert block["measurement_design"] == "form-proof"
        assert block["claims_benefit"] is False
        assert block["expected_effect_pp"] == 0.0
        assert block["rows"] == ROWS
    diff = _load(PACKAGE / "geometry-diff-v1.json")
    assert {entry["flag"] for entry in diff["server_argv_flag_diff"]} == {
        "-np", "-c", "--cache-prompt", "--no-cache-prompt", "--slot-prompt-similarity"
    }
    assert diff["composed_diff_against_plan_lock"]["pass_a"]["moved_by_fragment"]["baseline"] == sorted(
        BASELINE_BOOKKEEPING | {GEOMETRY_KEY}
    )
