"""A Perception branch's ``prepared_seed`` pin is a receipt, never an identity input.

Regression for the 2026-09-29 P-SV-1 smoke re-pin refusal ("prepared artifact
identity mismatch" inside ``ensure_branch_seeds_pinned``): the prepared-artifact
identity (``core.preparation.artifact_inputs``' ``config_sha256`` and
``core.flight.runtime._perception_branches_identity``) bound each B branch's
``prepared_seed`` pin. ``repin_package`` mints the phase supply under the OLD
seed pin, then the branch-seed rebuild DROPS the pin before producing -- and the
producer's load of that phase supply recomputed a different identity. The same
circularity made a pinned branch seed unverifiable at flight time (produced with
the pin dropped, verified with it present).

The fakes below compute identity exactly the way ``FlightRuntime._phase_seed_inputs``
does (the composed config through the real ``artifact_inputs``, plus the
``perception_branches`` source through the real ``_perception_branches_identity``)
and use the real ``prepare_artifact`` / ``load_artifact``, re-reading the
baseline fragment from disk on every call as a freshly built runtime would.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from speech_aware_evidence_acquisition.core.flight.repin import (
    ArtifactPin,
    CellIdentity,
    baseline_fragment_path,
    ensure_artifact_pinned,
    ensure_branch_seeds_pinned,
)
from speech_aware_evidence_acquisition.core.flight.runtime import (
    _perception_branches_identity,
)
from speech_aware_evidence_acquisition.core.preparation import (
    artifact_inputs,
    digest,
    load_artifact,
    prepare_artifact,
)

RUN_ID = "TEST-PSV-SMOKE-1"
SPLIT = "a" * 64
CONTRAST = {"relpath": "prepared/CONTRAST/table-v1.json", "sha256": "c" * 64}


def _write_json(path: Path, document: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2), encoding="utf-8", newline="\n")


def _branches_block(prepared_seed: dict | None) -> dict:
    row_b = {"branch_id": "B", "max_supplied_items": 8, "contrast_pairs": dict(CONTRAST)}
    if prepared_seed is not None:
        row_b["prepared_seed"] = prepared_seed
    return {
        "level": 2,
        "branches": [
            row_b,
            {"branch_id": "T", "replicate_of": "A", "max_supplied_items": 8},
            {"branch_id": "A", "deliver": True, "max_supplied_items": 8},
        ],
        "fit_estimate": {},
    }


def _baseline(prepared_seed: dict | None) -> dict:
    return {
        "arm": "test-arm",
        "policy": "phase-direct-only-supplied-v1",
        "native_episode": {"roles": {"perception": {"branches": _branches_block(prepared_seed)}}},
    }


def _identity(baseline_fragment: str, *, seed_pin: ArtifactPin | None) -> CellIdentity:
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
        split_identity_hash=SPLIT,
        config_hash="b" * 64,
        protocol_hash="c" * 64,
        prepared_phase_supply=None,
        perception_branch_seed_pin=seed_pin,
        has_perception_branch_group=True,
    )


class RuntimeLikeIdentity:
    """Stand-ins for ``prepare-supply`` / ``prepare-branch-seeds`` that bind the
    SAME identity the runtime binds, recomputed from the on-disk baseline."""

    def __init__(self, repo_root: Path, data_root: Path, baseline_fragment: str):
        self.repo_root = repo_root
        self.data_root = data_root
        self.baseline_path = baseline_fragment_path(repo_root, baseline_fragment)

    def config(self) -> dict:
        return json.loads(self.baseline_path.read_text(encoding="utf-8"))

    def inputs(self) -> dict:
        config = self.config()
        return artifact_inputs(
            config=config,
            split_identity_hash=SPLIT,
            sources={"perception_branches": _perception_branches_identity(config.get("native_episode"))},
        )

    def load_supply(self) -> object:
        pin = self.config()["prepared_phase_supply"]
        return load_artifact(
            self.data_root / pin["relpath"], expected_sha256=pin["sha256"],
            kind="phase-supply", inputs=self.inputs(),
        )

    def load_branch_seed(self) -> object:
        rows = self.config()["native_episode"]["roles"]["perception"]["branches"]["branches"]
        pin = next(row for row in rows if row["branch_id"] == "B")["prepared_seed"]
        return load_artifact(
            self.data_root / pin["relpath"], expected_sha256=pin["sha256"],
            kind="perception-branch-seeds", inputs=self.inputs(),
        )

    def prepare_supply(self, *, output_path, **_kwargs):
        return prepare_artifact(
            Path(output_path), kind="phase-supply", inputs=self.inputs(),
            producer=lambda: {"facets": {}, "values": {"direct": {"s1": ["v1"]}}},
        )

    def prepare_branch_seeds(self, *, output_path, **_kwargs):
        def produce():
            # _phase_supply_seeds -> _load_phase_supply_seed: the producer
            # loads the cell's own pinned first-phase supply.
            supply = self.load_supply()
            return {"branches": {"B": dict(supply["values"]["direct"])}}

        return prepare_artifact(
            Path(output_path), kind="perception-branch-seeds", inputs=self.inputs(), producer=produce,
        )


def _setup(tmp_path: Path) -> tuple[RuntimeLikeIdentity, CellIdentity, dict]:
    repo = tmp_path / "repo"
    data = tmp_path / "data"
    baseline_fragment = "psv-smoke-baseline-1"
    # A stale branch seed pinned before the contrast_pairs axis existed: its
    # recorded inputs no longer match, its selection is the one a rebuild
    # reproduces (so the output-change guard stays quiet).
    stale = data / "prepared" / RUN_ID / "perception-branch-seeds-v1.json"
    _write_json(stale, {
        "schema": "saea-prepared-artifact-v1", "kind": "perception-branch-seeds",
        "inputs": {}, "contact_class": "model-free",
        "output": {"branches": {"B": {"s1": ["v1"]}}}, "output_sha256": "0" * 64,
    })
    stale_pin = ArtifactPin(f"prepared/{RUN_ID}/perception-branch-seeds-v1.json", "d" * 64)
    _write_json(baseline_fragment_path(repo, baseline_fragment), _baseline(stale_pin.as_dict()))
    _write_json(repo / "configs" / "experiment" / "experiment-1.json", {
        "cells": [{"cell_id": "cell-1", "readiness": {"requirements": []}}],
    })
    fakes = RuntimeLikeIdentity(repo, data, baseline_fragment)
    common = dict(
        repo_root=repo, data_root=data, runtime_root=tmp_path / "runtime",
        lock_path=tmp_path / "lock.json", experiment="experiment-1",
    )
    return fakes, _identity(baseline_fragment, seed_pin=stale_pin), common


def test_supply_then_branch_seed_repin_completes_over_a_stale_seed_pin(tmp_path):
    """repin_package's order: mint the supply, then rebuild the branch seed.

    Before the fix the branch-seed producer's supply load raised
    ``PreparationError("prepared artifact identity mismatch")``.
    """

    fakes, identity, common = _setup(tmp_path)

    supply_report = ensure_artifact_pinned(
        **common, identity=identity, prepare_supply_fn=fakes.prepare_supply,
        allow_output_change=False,
    )
    assert supply_report["rebuilt"] is True
    seed_report = ensure_branch_seeds_pinned(
        **common, identity=identity, prepare_branch_seeds_fn=fakes.prepare_branch_seeds,
    )

    assert seed_report["rebuilt"] is True
    assert seed_report["new_pin"]["relpath"] == f"prepared/{RUN_ID}/perception-branch-seeds-v2.json"
    # Flight time: both pins now stand in the config; both artifacts verify.
    assert fakes.load_supply()["values"]["direct"] == {"s1": ["v1"]}
    assert fakes.load_branch_seed() == {"branches": {"B": {"s1": ["v1"]}}}


def test_a_second_repin_pass_is_a_verified_no_op(tmp_path):
    """The fixed point: once pinned, neither artifact goes stale because of
    the other's pin, so the flip loop's next pass rebuilds nothing."""

    fakes, identity, common = _setup(tmp_path)
    supply = ensure_artifact_pinned(
        **common, identity=identity, prepare_supply_fn=fakes.prepare_supply,
        allow_output_change=False,
    )
    seed = ensure_branch_seeds_pinned(
        **common, identity=identity, prepare_branch_seeds_fn=fakes.prepare_branch_seeds,
    )
    second = replace(
        identity,
        prepared_phase_supply=ArtifactPin(**supply["new_pin"]),
        perception_branch_seed_pin=ArtifactPin(**seed["new_pin"]),
    )

    assert ensure_artifact_pinned(
        **common, identity=second, prepare_supply_fn=fakes.prepare_supply,
        allow_output_change=False,
    ) == {"rebuilt": False, "pin": supply["new_pin"]}
    assert ensure_branch_seeds_pinned(
        **common, identity=second, prepare_branch_seeds_fn=fakes.prepare_branch_seeds,
    ) == {"rebuilt": False, "pin": seed["new_pin"]}


def test_artifact_inputs_ignore_a_branch_prepared_seed_but_bind_its_axes():
    unpinned = _baseline(None)
    pinned = _baseline({"relpath": "prepared/X/perception-branch-seeds-v9.json", "sha256": "e" * 64})
    moved_axis = json.loads(json.dumps(unpinned))
    moved_axis["native_episode"]["roles"]["perception"]["branches"]["branches"][0]["contrast_pairs"] = None

    def config_sha(config):
        return artifact_inputs(config=config, split_identity_hash=SPLIT, sources={})["config_sha256"]

    assert config_sha(pinned) == config_sha(unpinned)
    assert config_sha(moved_axis) != config_sha(unpinned)
    # The input mapping itself is never mutated.
    assert "prepared_seed" in pinned["native_episode"]["roles"]["perception"]["branches"]["branches"][0]


def test_artifact_inputs_unchanged_for_a_config_without_a_branch_seed_pin():
    """No existing identity moves: without a pin the digest is the old formula's."""

    for config in ({"arm": "x", "policy": "p"}, _baseline(None)):
        assert artifact_inputs(config=config, split_identity_hash=SPLIT, sources={})[
            "config_sha256"
        ] == digest(config)


def test_perception_branches_identity_drops_prepared_seed_and_keeps_contrast_pairs():
    pinned = _baseline({"relpath": "prepared/X/perception-branch-seeds-v9.json", "sha256": "e" * 64})
    identity = _perception_branches_identity(pinned["native_episode"])
    assert identity == _branches_block(None)
    assert identity["branches"][0]["contrast_pairs"] == CONTRAST
