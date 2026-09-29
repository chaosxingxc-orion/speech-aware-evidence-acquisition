"""``core.flight.repin`` Perception branch-seed re-pin (design section 5 item
4; the item-4 GAP): ``ensure_branch_seeds_pinned`` and its small helpers,
exercised in isolation against a throwaway baseline fragment -- never a real
registered package, never git, never ``repin_package``'s own ledger/protocol
orchestration (already covered end to end for ``prepared_phase_supply`` by
``tests/unit/test_flight_repin.py``; this module is that same verify-or-
rebuild shape's twin for the branch-seed artifact and its nested pin
location).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.flight.repin import (
    ArtifactPin,
    CellIdentity,
    NO_BRANCH_GROUP_MESSAGE,
    RepinError,
    _drop_perception_branch_seed_pins,
    _perception_branches_list,
    _set_perception_branch_seed_pins,
    branch_seed_pin,
    ensure_branch_seeds_pinned,
)

RUN_ID = "TEST-PSV-RUN-1"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, document: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2), encoding="utf-8", newline="\n")


def _branches_block(*, b_prepared_seed: dict | None) -> dict:
    row_b = {"branch_id": "B", "max_supplied_items": 8}
    if b_prepared_seed is not None:
        row_b["prepared_seed"] = b_prepared_seed
    return {
        "level": 1,
        "branches": [
            row_b,
            {"branch_id": "T", "replicate_of": "A", "max_supplied_items": 8},
            {"branch_id": "A", "deliver": True, "max_supplied_items": 8},
        ],
        "fit_estimate": {},
    }


def _baseline(*, branches: dict | None, extra: dict | None = None) -> dict:
    document = {"arm": "test-arm"}
    if branches is not None:
        document["native_episode"] = {"roles": {"perception": {"branches": branches}}}
    if extra:
        document.update(extra)
    return document


def _identity(
    baseline_fragment: str, *, pin: ArtifactPin | None, has_group: bool = True,
) -> CellIdentity:
    return CellIdentity(
        experiment="experiment-1",
        cell_id="cell-1",
        run_id=RUN_ID,
        attempt_id="attempt-1",
        model_fragment="model-1",
        dataset_fragment="dataset-1",
        baseline_fragment=baseline_fragment,
        carrier_lock_key="testcarrier",
        arm="test-arm",
        split_identity_hash="a" * 64,
        config_hash="b" * 64,
        protocol_hash="c" * 64,
        prepared_phase_supply=None,
        perception_branch_seed_pin=pin,
        has_perception_branch_group=has_group,
    )


class FakePrepareBranchSeeds:
    """A fake ``prepare_branch_seeds_fn``: raises for run ids in
    ``mismatched`` when called on an EXISTING path (a stale pin), raises
    :data:`NO_BRANCH_GROUP_MESSAGE` when ``no_group`` is set, and otherwise
    writes a fresh ``perception-branch-seeds-v1``-shaped artifact and returns
    its receipt -- structurally ``test_flight_repin.Fake``'s twin."""

    def __init__(self, *, mismatched: set[str] | None = None, no_group: bool = False, output: dict | None = None):
        self.mismatched = mismatched or set()
        self.no_group = no_group
        self.output = output if output is not None else {"branches": {"B": {"row-a": ["v1"]}}}
        self.calls: list[dict] = []

    def __call__(self, *, run_id, output_path, **kwargs):
        self.calls.append({"run_id": run_id, "output_path": str(output_path), **kwargs})
        if self.no_group:
            raise RuntimeError(NO_BRANCH_GROUP_MESSAGE)
        output_path = Path(output_path)
        if output_path.exists():
            if run_id in self.mismatched:
                raise RuntimeError(f"simulated identity mismatch for {run_id}")
            return {"path": str(output_path), "sha256": _sha(output_path), "cache": "warm"}
        document = {
            "schema": "saea-prepared-artifact-v1",
            "kind": "perception-branch-seeds",
            "inputs": {},
            "contact_class": "model-free",
            "output": self.output,
            "output_sha256": "0" * 64,
        }
        raw = json.dumps(document, indent=2).encode()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(raw)
        return {"path": str(output_path), "sha256": hashlib.sha256(raw).hexdigest(), "cache": "cold"}


def _kwargs(tmp_path: Path, baseline_fragment: str, identity: CellIdentity, fake: FakePrepareBranchSeeds) -> dict:
    return dict(
        repo_root=tmp_path / "repo",
        data_root=tmp_path / "data",
        runtime_root=tmp_path / "runtime",
        lock_path=tmp_path / "lock.json",
        experiment="experiment-1",
        identity=identity,
        prepare_branch_seeds_fn=fake,
    )


def _write_old_artifact(path: Path, output: dict) -> None:
    _write_json(path, {
        "schema": "saea-prepared-artifact-v1",
        "kind": "perception-branch-seeds",
        "inputs": {},
        "contact_class": "model-free",
        "output": output,
        "output_sha256": "0" * 64,
    })


def _setup(tmp_path: Path, *, branches: dict | None) -> tuple[Path, str]:
    repo = tmp_path / "repo"
    baseline_fragment = "psv-baseline-1"
    baseline_path = repo / "configs" / "baseline" / f"{baseline_fragment}.json"
    _write_json(baseline_path, _baseline(branches=branches))
    return baseline_path, baseline_fragment


# --------------------------------------------------------------------------
# branch_seed_pin / _perception_branches_list (pure helpers)
# --------------------------------------------------------------------------


def test_branch_seed_pin_is_none_without_a_branch_group():
    assert branch_seed_pin({"arm": "x"}) is None
    assert branch_seed_pin({"native_episode": {"roles": {}}}) is None


def test_branch_seed_pin_is_none_when_the_b_branch_carries_none():
    document = _baseline(branches=_branches_block(b_prepared_seed=None))
    assert branch_seed_pin(document) is None


def test_branch_seed_pin_reads_the_shared_pin():
    pin = {"relpath": "prepared/R/perception-branch-seeds-v1.json", "sha256": "a" * 64}
    document = _baseline(branches=_branches_block(b_prepared_seed=pin))
    assert branch_seed_pin(document) == ArtifactPin(pin["relpath"], pin["sha256"])


def test_branch_seed_pin_refuses_when_b_branches_disagree():
    block = _branches_block(b_prepared_seed={"relpath": "prepared/R/x.json", "sha256": "a" * 64})
    block["branches"].insert(0, {
        "branch_id": "B2", "max_supplied_items": 8,
        "prepared_seed": {"relpath": "prepared/R/y.json", "sha256": "b" * 64},
    })
    document = _baseline(branches=block)
    with pytest.raises(RepinError, match="disagree"):
        branch_seed_pin(document)


def test_perception_branches_list_none_for_non_mapping_levels():
    assert _perception_branches_list({"native_episode": "not-a-mapping"}) is None
    assert _perception_branches_list({"native_episode": {"roles": "nope"}}) is None


# --------------------------------------------------------------------------
# ensure_branch_seeds_pinned
# --------------------------------------------------------------------------


def test_no_rebuild_when_the_pin_already_verifies(tmp_path):
    pin = ArtifactPin(f"prepared/{RUN_ID}/perception-branch-seeds-v1.json", "a" * 64)
    baseline_path, baseline_fragment = _setup(
        tmp_path, branches=_branches_block(b_prepared_seed=pin.as_dict()),
    )
    # The pinned file need not exist with real bytes for the warm-check to
    # be exercised; the fake only inspects whether the path already exists.
    artifact_path = tmp_path / "data" / pin.relpath
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_bytes(b"{}")
    fake = FakePrepareBranchSeeds()
    identity = _identity(baseline_fragment, pin=pin)

    report = ensure_branch_seeds_pinned(**_kwargs(tmp_path, baseline_fragment, identity, fake))

    assert report == {"rebuilt": False, "pin": pin.as_dict()}
    assert len(fake.calls) == 1
    assert fake.calls[0]["output_path"] == str(artifact_path)
    # Untouched: the baseline file's bytes never moved.
    assert json.loads(baseline_path.read_text(encoding="utf-8"))["native_episode"]["roles"]["perception"][
        "branches"
    ]["branches"][0]["prepared_seed"] == pin.as_dict()


def test_rebuild_when_no_pin_is_configured_and_pins_only_the_b_branch(tmp_path):
    baseline_path, baseline_fragment = _setup(
        tmp_path, branches=_branches_block(b_prepared_seed=None),
    )
    fake = FakePrepareBranchSeeds()
    identity = _identity(baseline_fragment, pin=None)

    report = ensure_branch_seeds_pinned(**_kwargs(tmp_path, baseline_fragment, identity, fake))

    assert report["rebuilt"] is True
    assert report["old_pin"] is None
    new_pin = report["new_pin"]
    assert new_pin["relpath"] == f"prepared/{RUN_ID}/perception-branch-seeds-v1.json"
    assert report["branches_updated"] == 1
    document = json.loads(baseline_path.read_text(encoding="utf-8"))
    branches = document["native_episode"]["roles"]["perception"]["branches"]["branches"]
    by_id = {row["branch_id"]: row for row in branches}
    assert by_id["B"]["prepared_seed"] == new_pin
    assert "prepared_seed" not in by_id["T"]
    assert "prepared_seed" not in by_id["A"]
    assert (tmp_path / "data" / new_pin["relpath"]).is_file()


def test_rebuild_when_the_pinned_artifact_is_absent_on_disk(tmp_path):
    pin = ArtifactPin(f"prepared/{RUN_ID}/perception-branch-seeds-v1.json", "a" * 64)
    baseline_path, baseline_fragment = _setup(
        tmp_path, branches=_branches_block(b_prepared_seed=pin.as_dict()),
    )
    fake = FakePrepareBranchSeeds()
    identity = _identity(baseline_fragment, pin=pin)

    report = ensure_branch_seeds_pinned(**_kwargs(tmp_path, baseline_fragment, identity, fake))

    assert report["rebuilt"] is True
    assert report["old_pin"] == pin.as_dict()
    assert report["new_pin"]["relpath"] == pin.relpath  # same relpath, version 1 never existed
    document = json.loads(baseline_path.read_text(encoding="utf-8"))
    branches = document["native_episode"]["roles"]["perception"]["branches"]["branches"]
    assert next(r for r in branches if r["branch_id"] == "B")["prepared_seed"] == report["new_pin"]


def test_rebuild_mints_a_new_version_when_the_pin_is_stale(tmp_path):
    pin = ArtifactPin(f"prepared/{RUN_ID}/perception-branch-seeds-v1.json", "a" * 64)
    baseline_path, baseline_fragment = _setup(
        tmp_path, branches=_branches_block(b_prepared_seed=pin.as_dict()),
    )
    artifact_path = tmp_path / "data" / pin.relpath
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    # Same output the fake's default rebuild produces: a stale pin (moved
    # implementation hash, say) need not select different rows, so this
    # proves version-bumping alone, without tripping the output-change guard.
    _write_old_artifact(artifact_path, {"branches": {"B": {"row-a": ["v1"]}}})
    fake = FakePrepareBranchSeeds(mismatched={RUN_ID})
    identity = _identity(baseline_fragment, pin=pin)

    report = ensure_branch_seeds_pinned(**_kwargs(tmp_path, baseline_fragment, identity, fake))

    assert report["rebuilt"] is True
    assert report["new_pin"]["relpath"] == f"prepared/{RUN_ID}/perception-branch-seeds-v2.json"
    assert report["new_pin"] != pin.as_dict()
    document = json.loads(baseline_path.read_text(encoding="utf-8"))
    branches = document["native_episode"]["roles"]["perception"]["branches"]["branches"]
    assert next(r for r in branches if r["branch_id"] == "B")["prepared_seed"] == report["new_pin"]


def test_skipped_when_the_cell_declares_no_branch_group(tmp_path):
    baseline_path, baseline_fragment = _setup(tmp_path, branches=None)
    original = baseline_path.read_text(encoding="utf-8")
    fake = FakePrepareBranchSeeds(no_group=True)
    identity = _identity(baseline_fragment, pin=None, has_group=False)

    report = ensure_branch_seeds_pinned(**_kwargs(tmp_path, baseline_fragment, identity, fake))

    assert report == {"rebuilt": False, "pin": None, "skipped": NO_BRANCH_GROUP_MESSAGE}
    assert not fake.calls
    assert baseline_path.read_text(encoding="utf-8") == original


def test_refuses_on_output_change_without_the_override_and_restores_the_baseline(tmp_path):
    pin = ArtifactPin(f"prepared/{RUN_ID}/perception-branch-seeds-v1.json", "a" * 64)
    baseline_path, baseline_fragment = _setup(
        tmp_path, branches=_branches_block(b_prepared_seed=pin.as_dict()),
    )
    artifact_path = tmp_path / "data" / pin.relpath
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    _write_old_artifact(artifact_path, {"branches": {"B": {"row-a": ["v1"]}}})
    original = baseline_path.read_text(encoding="utf-8")
    fake = FakePrepareBranchSeeds(
        mismatched={RUN_ID}, output={"branches": {"B": {"row-a": ["v-different"]}}},
    )
    identity = _identity(baseline_fragment, pin=pin)

    with pytest.raises(RepinError, match="different output"):
        ensure_branch_seeds_pinned(**_kwargs(tmp_path, baseline_fragment, identity, fake))

    # The baseline is restored verbatim on refusal -- no half-applied pin.
    assert baseline_path.read_text(encoding="utf-8") == original


def test_allow_output_change_accepts_a_different_selection(tmp_path):
    pin = ArtifactPin(f"prepared/{RUN_ID}/perception-branch-seeds-v1.json", "a" * 64)
    baseline_path, baseline_fragment = _setup(
        tmp_path, branches=_branches_block(b_prepared_seed=pin.as_dict()),
    )
    artifact_path = tmp_path / "data" / pin.relpath
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    _write_old_artifact(artifact_path, {"branches": {"B": {"row-a": ["v1"]}}})
    fake = FakePrepareBranchSeeds(
        mismatched={RUN_ID}, output={"branches": {"B": {"row-a": ["v-different"]}}},
    )
    identity = _identity(baseline_fragment, pin=pin)

    report = ensure_branch_seeds_pinned(
        **_kwargs(tmp_path, baseline_fragment, identity, fake), allow_output_change=True,
    )

    assert report["rebuilt"] is True
    assert report["row_counts"]["old"] == {"B": 1}
    assert report["row_counts"]["new"] == {"B": 1}


def test_drop_and_set_pins_helpers_round_trip(tmp_path):
    baseline_path, _fragment = _setup(tmp_path, branches=_branches_block(b_prepared_seed={
        "relpath": "prepared/R/x.json", "sha256": "a" * 64,
    }))
    _drop_perception_branch_seed_pins(baseline_path)
    document = json.loads(baseline_path.read_text(encoding="utf-8"))
    branches = document["native_episode"]["roles"]["perception"]["branches"]["branches"]
    assert all("prepared_seed" not in row for row in branches)

    new_pin = ArtifactPin("prepared/R/new.json", "b" * 64)
    updated = _set_perception_branch_seed_pins(baseline_path, new_pin)
    assert updated == 1
    document = json.loads(baseline_path.read_text(encoding="utf-8"))
    branches = document["native_episode"]["roles"]["perception"]["branches"]["branches"]
    by_id = {row["branch_id"]: row for row in branches}
    assert by_id["B"]["prepared_seed"] == new_pin.as_dict()
    assert "prepared_seed" not in by_id["T"]
    assert "prepared_seed" not in by_id["A"]
