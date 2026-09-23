"""Stage-3 S3-6 proof obligation: the delta-cell baseline fragment differs
from the locked PLAN fragment ONLY in the ONE added store
(``knowledge_stores.stage3-deltas``) plus the per-flight bookkeeping keys
this cell must re-prepare under its own run id -- the same exclusion set the
locked plan's own proof test already uses against its predecessor
(``configs/baseline/slurp-native-default-plan-lock-baseline-v1.json``
``the_one_difference_from_slurp_direct_closed_list``-style precedent).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PLAN_PATH = REPO_ROOT / "configs" / "baseline" / "slurp-native-default-plan-lock-baseline-v1.json"

_BOOKKEEPING_KEYS = {
    "native_contact_fit",
    "prepared_phase_supply",
    "preparation_source_receipts",
    "speech_feature_key_representation_id",
    "speech_feature_matcher_policy_id",
    "speech_packet_promotion_receipt",
    "speech_packet_promotion_receipt_sha256",
}
_DOC_KEYS = {
    "what_this_is",
    "what_the_train_exemplars_store_is",
    "what_the_stage3_deltas_store_is",
    "knowledge_stores_note",
    "smoke_note",
}
_EXCLUDED_KEYS = _BOOKKEEPING_KEYS | _DOC_KEYS


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _comparable(document: dict) -> dict:
    return {key: value for key, value in document.items() if key not in _EXCLUDED_KEYS}


def _assert_only_stage3_deltas_added(plan_ks: dict, cell_ks: dict) -> None:
    assert set(cell_ks) == set(plan_ks) | {"stage3-deltas"}
    for store_id in plan_ks:
        assert cell_ks[store_id] == plan_ks[store_id]


def test_generation_cell_differs_from_plan_only_by_the_one_store() -> None:
    plan = _load(PLAN_PATH)
    cell = _load(REPO_ROOT / "configs" / "baseline" / "slurp-native-stage3-delta-cell-baseline-v1.json")
    plan_ks = plan.pop("knowledge_stores")
    cell_ks = cell.pop("knowledge_stores")
    assert _comparable(plan) == _comparable(cell)
    _assert_only_stage3_deltas_added(plan_ks, cell_ks)
    store = cell_ks["stage3-deltas"]
    assert store["store_role"] == "stage3-deltas"
    # S3-4s (owner decision 106): PER-NODE supply on the same one store.
    assert set(store["context_supply"]) == {
        "perception", "solver", "reviewer", "planner",
    }
    for phase, cap in (("solver", 8), ("reviewer", 4), ("planner", 4)):
        spec = store["context_supply"][phase]
        assert spec["cap"] == cap, phase
        assert spec["rank_by"] == "prior_score"
        assert spec["provider"] == "stage3-delta-candidate-bound-v1"
        assert spec["candidate_state_phase"] == "perception"
        assert spec["node_target"] == phase
    # Perception produces the candidate list, so its route is unconditional
    # and carries NO candidate_state_phase.
    perception = store["context_supply"]["perception"]
    assert perception == {
        "cap": 4,
        "node_target": "perception",
        "provider": "stage3-delta-unconditional-v1",
        "rank_by": "prior_score",
    }


def test_the_cell_differs_from_plan_by_exactly_the_store_keys() -> None:
    """The S3-6 equality proof, stated as a KEY DIFF rather than a value diff:
    after excluding the per-flight bookkeeping and the documentation keys, the
    only difference between the cell fragment and the locked plan is the one
    ``knowledge_stores.stage3-deltas`` key and its own sub-keys."""

    plan = _load(PLAN_PATH)
    cell = _load(REPO_ROOT / "configs" / "baseline" / "slurp-native-stage3-delta-cell-baseline-v1.json")
    assert set(_comparable(plan)) == set(_comparable(cell))
    differing = {
        key for key in _comparable(plan)
        if _comparable(plan)[key] != _comparable(cell)[key]
    }
    assert differing == {"knowledge_stores"}
    added = set(cell["knowledge_stores"]) - set(plan["knowledge_stores"])
    assert added == {"stage3-deltas"}
    assert set(cell["knowledge_stores"]["stage3-deltas"]) == {
        "context_supply", "release", "snapshot", "store_role",
    }


def test_twin_cell_differs_from_generation_cell_only_by_the_release_namespace() -> None:
    generation = _load(REPO_ROOT / "configs" / "baseline" / "slurp-native-stage3-delta-cell-baseline-v1.json")
    twin = _load(REPO_ROOT / "configs" / "baseline" / "slurp-native-stage3-delta-cell-twin-baseline-v1.json")
    gen_store = generation["knowledge_stores"].pop("stage3-deltas")
    twin_store = twin["knowledge_stores"].pop("stage3-deltas")
    assert generation["knowledge_stores"] == twin["knowledge_stores"]
    assert "twin" in twin_store["snapshot"]["relpath"]
    assert "twin" not in gen_store["snapshot"]["relpath"]
    # The twin differs in the released STORE, never in the routing: the same
    # four per-node routes, the same caps, the same node targets.
    assert gen_store["context_supply"] == twin_store["context_supply"]


_BASELINES = (
    "slurp-native-stage3-delta-cell-baseline-v1.json",
    "slurp-native-stage3-delta-cell-twin-baseline-v1.json",
    "slurp-native-stage3-delta-cell-smoke-4-baseline-v1.json",
    "slurp-native-stage3-delta-cell-twin-smoke-4-baseline-v1.json",
)
#: The store version the four baselines pin. S3-5 revision v1r (2026-09-23)
#: superseded v1, whose facets were the statements' TARGETs and therefore
#: unreachable on 258 of 379 rows; see
#: docs/readiness/2026-09-22-slurp-stage3-delta-cell-r01-v1/
#: stage3-deltas-v1-superseded-v1.md.
_STORE_VERSION = "v1r"


def test_no_bookkeeping_key_is_left_as_a_pending_token() -> None:
    """The CELL-1 registration (commit 6d1f30fc and its repair fb4d8915)
    filled the per-flight bookkeeping this cell prepares under its OWN run id
    and REMOVED ``prepared_phase_supply``, because ``core.config.compose``
    raises on a PENDING ``preparation_source_receipts`` and
    ``core.flight.repin.ArtifactPin.from_mapping`` refuses a string pin
    before ``ensure_artifact_pinned`` can mint the real one. Neither
    ``core.flight.cli check`` nor ``scripts/flights/repin_cell.py`` could
    reach the preparation step while a token was left, so a token left here
    is a defect, not a hand-off."""

    for filename in _BASELINES:
        document = _load(REPO_ROOT / "configs" / "baseline" / filename)
        # The flip mints this one and inserts its readiness requirement.
        assert "prepared_phase_supply" not in document, filename
        for key in _BOOKKEEPING_KEYS - {"prepared_phase_supply"}:
            value = document[key]
            assert value, (filename, key)
            if isinstance(value, str):
                assert not value.startswith("PENDING_"), (filename, key, value)
        # native_contact_fit carries THIS cell's own fit identity, never cell
        # PLAN's (owner rule E16).
        fit = document["native_contact_fit"]
        assert "stage3-delta-cell" in fit["run_id"].lower().replace("_", "-")
        assert "stage3-delta-cell" in fit["attempt_id"]


def test_the_store_pins_name_one_released_version_and_two_distinct_digests() -> None:
    """Commit fb4d8915: ``rails.knowledge_stores`` checks the snapshot pin
    against BOTH ``KnowledgeSnapshot.content_hash()`` and the release
    document's own ``snapshot_sha256`` -- one number, and NOT the
    ``snapshot.json`` FILE digest, which is a third value. The release pin IS
    the ``release.json`` file digest. The two pins are therefore always
    different numbers over the same store, and both are real digests.

    Repository-only: nothing here reads ``SPEECHRL_DATA_DIR``."""

    seen = set()
    for filename in _BASELINES:
        document = _load(REPO_ROOT / "configs" / "baseline" / filename)
        store = document["knowledge_stores"]["stage3-deltas"]
        twin = "twin" in filename
        namespace = (
            f"knowledge/slurp/semantic/stage3-deltas"
            f"{'-twin' if twin else ''}-{_STORE_VERSION}"
        )
        assert store["release"]["relpath"] == f"{namespace}/release.json", filename
        assert store["snapshot"]["relpath"] == f"{namespace}/snapshot.json", filename
        for pin in ("release", "snapshot"):
            digest = store[pin]["sha256"]
            assert re.fullmatch(r"[0-9a-f]{64}", digest), (filename, pin, digest)
        assert store["release"]["sha256"] != store["snapshot"]["sha256"], filename
        seen.add((store["release"]["sha256"], store["snapshot"]["sha256"], twin))
    # The arm's two baselines pin one store and the twin's two pin the other.
    assert len(seen) == 2
    assert {twin for _, _, twin in seen} == {False, True}


def test_the_experiment_readiness_requirements_pin_the_same_release() -> None:
    """A cell is HELD on its store's ``release.json``; that requirement and
    the baseline's own release pin are the same document and the same
    digest, or the flip would mint a readiness requirement for a store the
    fragment does not use."""

    by_side = {}
    for filename in _BASELINES:
        document = _load(REPO_ROOT / "configs" / "baseline" / filename)
        store = document["knowledge_stores"]["stage3-deltas"]
        by_side["twin" if "twin" in filename else "arm"] = store["release"]
    for name in (
        "slurp-native-stage3-delta-cell-r01-v1.json",
        "slurp-native-stage3-delta-cell-smoke-4-v1.json",
    ):
        fragment = _load(REPO_ROOT / "configs" / "experiment" / name)
        pinned = {
            (requirement["relpath"], requirement["sha256"])
            for cell in fragment["cells"]
            for requirement in cell["readiness"]["requirements"]
            if requirement["kind"] == "preparation"
        }
        assert pinned == {
            (pin["relpath"], pin["sha256"]) for pin in by_side.values()
        }, name


def test_smoke_variants_carry_the_same_store_shape_as_their_full_siblings() -> None:
    full = _load(REPO_ROOT / "configs" / "baseline" / "slurp-native-stage3-delta-cell-baseline-v1.json")
    smoke = _load(REPO_ROOT / "configs" / "baseline" / "slurp-native-stage3-delta-cell-smoke-4-baseline-v1.json")
    assert (
        full["knowledge_stores"]["stage3-deltas"]["context_supply"]
        == smoke["knowledge_stores"]["stage3-deltas"]["context_supply"]
    )


# ---------------------------------------------------------------------------
# The v2 smoke (2026-09-23): the same cell under a new run identity
#
# Run id SAEA-SLURP-STAGE3-DELTA-CELL-SMOKE-4-V1 failed twice -- refused before
# contact, then 4 metered Perception contacts and a refusal at solver_0_input
# on the sealed Perception state's shape -- so the program's own rule ("a
# second failure stops the flight and the fix is proven on a 4-row dry run")
# retires it. The replacement must be the SAME cell: what moves is the run,
# attempt and fit identity, because a plan budget is run-cumulative across
# every attempt of one run id.
# ---------------------------------------------------------------------------

_V2_BASELINE = "slurp-native-stage3-delta-cell-smoke-4-v2-baseline-v1.json"
_V2_FRAGMENT = "slurp-native-stage3-delta-cell-smoke-4-v2.json"
_V1_SMOKE_BASELINE = "slurp-native-stage3-delta-cell-smoke-4-baseline-v1.json"
_V1_SMOKE_FRAGMENT = "slurp-native-stage3-delta-cell-smoke-4-v1.json"


def test_the_v2_smoke_baseline_moves_only_its_fit_identity() -> None:
    """Every DECIDED key is the v1 smoke's, byte for byte.

    Exactly three things differ, and each for a named reason: the fit spend
    identity (``native_contact_fit``, which must be this run id's own -- owner
    rule E16), the prose ``smoke_note`` that records the retirement, and the
    ABSENCE of ``prepared_phase_supply`` -- the re-pin mints this cell's own
    artifact under its own run id, and a committed pin would give it something
    to compare against that was never prepared for it.
    """

    v1 = _load(REPO_ROOT / "configs" / "baseline" / _V1_SMOKE_BASELINE)
    v2 = _load(REPO_ROOT / "configs" / "baseline" / _V2_BASELINE)
    assert set(v1) - set(v2) == {"prepared_phase_supply"}
    assert set(v2) - set(v1) == set()
    differing = {key for key in set(v1) & set(v2) if v1[key] != v2[key]}
    assert differing == {"native_contact_fit", "smoke_note"}

    fit = v2["native_contact_fit"]
    assert fit["run_id"] == "SAEA-SLURP-STAGE3-DELTA-CELL-SMOKE-4-V2-FIT-V1"
    assert fit["attempt_id"] == "attempt-slurp-native-stage3-delta-cell-smoke-4-v2-fit"
    assert fit["contact_cap"] == v1["native_contact_fit"]["contact_cap"]
    assert fit["max_speech_packets"] == v1["native_contact_fit"]["max_speech_packets"]


def test_the_v2_smoke_fragment_is_one_held_cell_on_the_same_population() -> None:
    v1 = _load(REPO_ROOT / "configs" / "experiment" / _V1_SMOKE_FRAGMENT)
    v2 = _load(REPO_ROOT / "configs" / "experiment" / _V2_FRAGMENT)

    assert len(v2["cells"]) == 1
    cell = v2["cells"][0]
    assert cell["cell_id"] == "slurp-native-stage3-delta-cell-smoke-4-v2"
    assert cell["run_id"] == "SAEA-SLURP-STAGE3-DELTA-CELL-SMOKE-4-V2"
    assert (
        cell["attempt_id"]
        == "attempt-slurp-native-stage3-delta-cell-smoke-4-v2-generation"
    )
    assert cell["baseline_fragment"] == _V2_BASELINE[: -len(".json")]
    assert cell["readiness"]["state"] == "held"

    v1_cell = next(
        item
        for item in v1["cells"]
        if item["cell_id"] == "slurp-native-stage3-delta-cell-smoke-4-v1"
    )
    for key in ("dataset_fragment", "model_fragment", "allowed_execution_stages"):
        assert cell[key] == v1_cell[key], key

    # The population, its identity and every cap are the retired smoke's.
    for key in (
        "execution_plan",
        "family_budget",
        "population",
        "populations",
        "split_id",
        "service_session",
        "execution_profile",
    ):
        assert v2[key] == v1[key], key
    assert v2["generation_budget"]["cap"] == v1["generation_budget"]["cap"]
    assert v2["generation_budget"]["target"] == v1["generation_budget"]["target"]
    assert v2["stage3_algorithm"]["id"] == v1["stage3_algorithm"]["id"]
    assert v2["stage3_algorithm"]["operators_used"] == (
        v1["stage3_algorithm"]["operators_used"]
    )

    # The twin smoke keeps its own v1 run id and stays where it was registered.
    twin = [
        item
        for item in v1["cells"]
        if item["run_id"] == "SAEA-SLURP-STAGE3-DELTA-CELL-SMOKE-4-TWIN-V1"
    ]
    assert len(twin) == 1
    assert not any(
        item["run_id"] == "SAEA-SLURP-STAGE3-DELTA-CELL-SMOKE-4-TWIN-V1"
        for item in v2["cells"]
    )


def test_the_v2_smoke_run_ids_are_registered_before_contact_and_unconsumed() -> None:
    """Both v2 identities carry a DRAFT exposure row, ``consumed = no``.

    Parsed with the repository's own parser, so a row hidden in a comment or a
    fence is exactly as invisible here as it is to the frozen-core gate.
    """

    from speech_aware_evidence_acquisition.contracts import _parse_ledger_tables

    ledger = (REPO_ROOT / "docs" / "exposure-ledger.md").read_text(encoding="utf-8")
    rows = _parse_ledger_tables(ledger)
    for run_id, plan in (
        (
            "SAEA-SLURP-STAGE3-DELTA-CELL-SMOKE-4-V2",
            "smoke-v2-generation-plan-registered-v1.json",
        ),
        (
            "SAEA-SLURP-STAGE3-DELTA-CELL-SMOKE-4-V2-FIT-V1",
            "smoke-v2-fit-plan-registered-v1.json",
        ),
    ):
        matches = [row for row in rows if row.get("run/experiment id") == run_id]
        assert len(matches) == 1, run_id
        row = matches[0]
        assert row["consumed"].strip().lower() == "no", run_id
        assert row["artifacts"].endswith(plan), run_id
        assert plan in row["artifacts"], run_id


def test_the_v2_plan_documents_name_the_v2_identities() -> None:
    package = REPO_ROOT / "docs" / "readiness" / "2026-09-22-slurp-stage3-delta-cell-r01-v1"
    for name, run_id, calls in (
        (
            "smoke-v2-generation-plan-registered-v1.json",
            "SAEA-SLURP-STAGE3-DELTA-CELL-SMOKE-4-V2",
            44,
        ),
        (
            "smoke-v2-fit-plan-registered-v1.json",
            "SAEA-SLURP-STAGE3-DELTA-CELL-SMOKE-4-V2-FIT-V1",
            176,
        ),
    ):
        document = _load(package / name)
        assert document["cell"] == "slurp-native-stage3-delta-cell-smoke-4-v2"
        assert document["experiment"] == "slurp-native-stage3-delta-cell-smoke-4-v2"
        plan = document["execution_plan"]
        assert plan["run_id"] == run_id
        assert plan["planned_model_calls"] == calls
        assert plan["split_identity_hash"] == (
            "4e3413fe64a51cea597bbd1de5c1b4bb5ac5194969a8522d7f3173b6c4b969cb"
        )
        assert document["supersedes"]["run_ids"] == [
            "SAEA-SLURP-STAGE3-DELTA-CELL-SMOKE-4-V1",
            "SAEA-SLURP-STAGE3-DELTA-CELL-SMOKE-4-FIT-V1",
        ]
