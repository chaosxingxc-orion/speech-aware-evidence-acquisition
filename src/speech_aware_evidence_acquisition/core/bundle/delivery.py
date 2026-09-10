"""Build and verify declared delivery derivatives without another model contact.

Derived text is not a model response. The parent keeps its original trace and
I7 binding; this distinct schema instead replays every terminal window and
compares exact output bytes. Hashes establish local consistency, not external
proof that a writer with access to all source files really ran a model.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

from ..base import CoreError
from ..config import ConfigError, _reject_duplicate_keys, compose, fragment_path
from ..predecessor_snapshot import binding_from_values, load_predecessor_binding
from . import RUN_MANIFEST_SCHEMA, BundleError, _refuse_if_inside_repo
from .artifacts import VerifiedBundle, _read_bytes, _verify_artifact
from .delivery_replay import (
    canonical, delivery_declarations, replay_delivery, selected_phase_delivery_declarations, sha256,
)

DELIVERY_MANIFEST_SCHEMA = "saea-derived-delivery-v1"
_SOURCE_FILES = (
    "core/delivery.py",
    "core/repair_alignment.py",
    "core/bundle/delivery.py",
    "core/bundle/delivery_replay.py",
    "core/model/adapter.py",
    "rails/controllers.py",
    "rails/core_client.py",
    "rails/phase_runner.py",
    "rails/phase_material.py",
    "reproduction/slurp_delivery.py",
    "reproduction/slurp_scoring.py",
    "core/policies.py",
)
_INHERITED = (
    "study",
    "study_commit",
    "plan",
    "split",
    "arm",
    "config",
    "protocol_hash",
    "scorers",
)


def _sources():
    package_root = Path(__file__).resolve().parents[2]
    return {
        name: sha256(_read_bytes(package_root / name, "delivery implementation"))
        for name in _SOURCE_FILES
    }


def _meta(path):
    path = Path(path).resolve()
    return {"path": str(path), "sha256": sha256(_read_bytes(path, "delivery input"))}


def _load_inputs(parent_path, repo_root, experiment_path, data_root, cell_id):
    from .verify import verify_bundle

    parent_doc = json.loads(_read_bytes(parent_path, "parent manifest"))
    if (
        not isinstance(parent_doc, Mapping)
        or parent_doc.get("schema") != RUN_MANIFEST_SCHEMA
    ):
        raise BundleError("delivery parent must be an ordinary generation bundle")
    parent = verify_bundle(parent_path)
    if parent.manifest.get("status") != "COMPLETED" or not parent.outputs_rows:
        raise BundleError("delivery parent must be a complete generation")
    fragments = parent.manifest["config"]["fragments"]
    composed = compose(repo_root, **fragments)
    expected_experiment = (
        Path(repo_root) / "configs/experiment" / f"{fragments['experiment']}.json"
    )
    if Path(experiment_path).resolve() != expected_experiment.resolve():
        raise BundleError(
            "delivery experiment must be the parent's actual config fragment"
        )
    if composed.config_hash != parent.manifest["config"]["config_hash"]:
        raise BundleError("delivery config changed after parent generation")
    values = composed.values
    declarations = delivery_declarations(values)
    if not declarations:
        raise BundleError("experiment config lacks predeclared delivery_derivatives")
    selected = [item for item in declarations if item["cell_id"] == cell_id]
    if len(selected) != 1:
        raise BundleError("delivery cell is not uniquely declared")
    declaration = selected[0]
    cells = values.get("cells", [])
    matches = [
        cell for cell in cells if cell.get("cell_id") == declaration["parent_cell_id"]
    ]
    if len(matches) != 1 or any(
        matches[0].get(f"{kind}_fragment") != fragments[kind]
        for kind in ("model", "dataset", "baseline")
    ):
        raise BundleError("delivery parent cell differs from generation fragments")
    if declaration.get("source_selector") is None:
        if values.get("policy") not in ("obs-repair-loop", "obs-repair-loop-ojw"):
            raise BundleError("legacy delivery requires the shared full-window repair policy")
        relpath, receipt_hash = binding_from_values(values)
        receipt = Path(repo_root) / "docs" / relpath
        snapshot = load_predecessor_binding(
            receipt, data_root, expected_receipt_sha256=receipt_hash
        )
    else:
        receipt = None
        snapshot = None
    rows, windows = replay_delivery(parent, snapshot, declaration, values)
    return parent, declaration, receipt, rows, windows


def _expected(
    parent,
    declaration,
    receipt,
    rows,
    windows,
    *,
    repo_root,
    experiment_path,
    data_root,
):
    identity_fields = ("sample_id", "carrier_lock_key", "arm", "text")
    parent_identity = [
        [row[key] for key in identity_fields] for row in parent.outputs_rows
    ]
    derived_identity = [[row[key] for key in identity_fields] for row in rows]
    score_reuse = None
    if (
        parent_identity == derived_identity
        and parent.manifest.get("scores") is not None
    ):
        score_reuse = {
            "source_run_id": parent.manifest["run_id"],
            "source_scores": parent.manifest["scores"],
            "identity_fields": list(identity_fields),
            "identity_sha256": sha256(canonical(parent_identity)),
            "scorers": parent.manifest["scorers"],
            "config_hash": parent.manifest["config"]["config_hash"],
        }
    document = {
        "schema": DELIVERY_MANIFEST_SCHEMA,
        "status": "COMPLETED",
        "run_id": f"{parent.manifest['run_id']}--delivery-{declaration['cell_id']}",
        **{key: parent.manifest.get(key) for key in _INHERITED},
        "parent": _meta(parent.manifest_path),
        "experiment": _meta(experiment_path),
        "repo_root": str(Path(repo_root).resolve()),
        "data_root": str(Path(data_root).resolve()),
        "declaration": declaration,
        "declaration_sha256": sha256(canonical(declaration)),
        "rule_sources": _sources(),
        "score_reuse": score_reuse,
        "outputs_sha256": sha256(b"".join(canonical(row) + b"\n" for row in rows)),
        "cost": {
            "calls_used": 0,
            "additional_model_contacts": 0,
            "parent_run_id": parent.manifest["run_id"],
            "parent_generation_cost": parent.manifest.get("cost", {}),
            "attribution": "Charge the shared generation once; this derivative adds no model contacts.",
        },
    }
    if receipt is not None:
        document["predecessor_receipt"] = _meta(receipt)
        document["windows"] = windows
    else:
        document["phase_sources"] = windows
    return document


def build_delivery_bundle(
    *,
    parent_manifest: Path,
    repo_root: Path,
    experiment_path: Path,
    data_root: Path,
    derivative_cell_id: str,
    output_dir: Path,
) -> Path:
    """Write a new derived bundle after verifying its pre-generation declaration.

    No attempt is acquired or finalized. Output directories must be new and
    outside the repository; raw model responses remain only in the parent.
    """
    try:
        parent, declaration, receipt, rows, windows = _load_inputs(
            parent_manifest, repo_root, experiment_path, data_root, derivative_cell_id
        )
        document = _expected(
            parent,
            declaration,
            receipt,
            rows,
            windows,
            repo_root=repo_root,
            experiment_path=experiment_path,
            data_root=data_root,
        )
        output_dir = Path(output_dir).resolve()
        _refuse_if_inside_repo(output_dir, "derived output directory")
        if output_dir.is_relative_to(Path(repo_root).resolve()):
            raise BundleError("derived output directory must be outside repository")
        if output_dir.exists():
            raise BundleError("derived output directory already exists")
        output_dir.mkdir(parents=True, exist_ok=False)
        run_id = document["run_id"]
        outputs = output_dir / f"{run_id}.outputs.jsonl"
        with outputs.open("xb") as stream:
            stream.write(b"".join(canonical(row) + b"\n" for row in rows))
        document["outputs"] = _meta(outputs)
        manifest = output_dir / f"{run_id}.run-manifest.json"
        with manifest.open("xb") as stream:
            stream.write(canonical(document) + b"\n")
        verify_delivery_bundle(manifest, document)
        return manifest
    except (CoreError, ConfigError, KeyError, TypeError, ValueError, OSError) as error:
        raise BundleError(f"delivery build refused: {error}") from error


def verify_delivery_bundle(manifest_path: Path, manifest: Mapping) -> VerifiedBundle:
    """Recompute every derivative from verified parent bytes; never alter them."""
    try:
        for key in ("parent", "experiment"):
            if _verify_artifact(manifest.get(key), key) is None:
                raise BundleError(f"delivery lacks {key}")
        if manifest.get("declaration", {}).get("source_selector") is None:
            if _verify_artifact(
                manifest.get("predecessor_receipt"), "predecessor_receipt"
            ) is None:
                raise BundleError("delivery lacks predecessor_receipt")
        elif "predecessor_receipt" in manifest:
            raise BundleError("phase-pair delivery must not name a predecessor receipt")
        raw = _verify_artifact(
            manifest.get("outputs"),
            "derived outputs",
            confine_to=Path(manifest_path).resolve().parent,
        )
        if raw is None:
            raise BundleError("delivery lacks outputs")
        parent, declaration, receipt, rows, windows = _load_inputs(
            Path(manifest["parent"]["path"]),
            Path(manifest["repo_root"]),
            Path(manifest["experiment"]["path"]),
            Path(manifest["data_root"]),
            manifest["declaration"]["cell_id"],
        )
        expected = _expected(
            parent,
            declaration,
            receipt,
            rows,
            windows,
            repo_root=manifest["repo_root"],
            experiment_path=manifest["experiment"]["path"],
            data_root=manifest["data_root"],
        )
        expected["outputs"] = _meta(Path(manifest["outputs"]["path"]))
        if dict(manifest) != expected:
            raise BundleError(
                "delivery provenance differs from deterministic recomputation"
            )
        if raw != b"".join(canonical(row) + b"\n" for row in rows):
            raise BundleError("derived output bytes differ from deterministic replay")
        return VerifiedBundle(
            Path(manifest_path),
            manifest,
            Path(manifest["outputs"]["path"]),
            tuple(rows),
            parent.trace_records,
            parent.split_ids,
            "DERIVED",
        )
    except (CoreError, ConfigError, KeyError, TypeError, ValueError, OSError) as error:
        raise BundleError(f"delivery verification refused: {error}") from error


def recorded_phase_delivery_declarations(
    bundle: VerifiedBundle, repo_root: Path,
) -> tuple[Mapping, ...]:
    """Resolve this parent's declarations from its exact recorded Git blob.

    Historical programmatic manifests without a named experiment blob return
    an empty tuple, preserving their existing raw-scoring behavior.
    """

    if bundle.manifest.get("schema") != RUN_MANIFEST_SCHEMA:
        return ()
    config = bundle.manifest.get("config", {})
    fragments = config.get("fragments", {})
    if not isinstance(fragments, Mapping) or "experiment" not in fragments:
        return ()
    from .git_commit import _git

    path = fragment_path(repo_root, "experiment", fragments["experiment"])
    relative = path.relative_to(repo_root).as_posix()
    commit = bundle.manifest.get("study_commit")
    if not isinstance(commit, str) or len(commit) != 40 or any(
        c not in "0123456789abcdef" for c in commit
    ):
        raise BundleError("cannot inspect phase delivery without a valid study commit")
    code, _, _ = _git(repo_root, "cat-file", "-e", commit + "^{commit}")
    if code:
        raise BundleError("cannot inspect phase delivery: recorded study commit is unavailable")
    code, raw, _ = _git(repo_root, "show", f"{commit}:{relative}")
    if code:
        return ()
    document = json.loads(raw, object_pairs_hook=_reject_duplicate_keys(path))
    if not isinstance(document, Mapping):
        raise BundleError("recorded experiment fragment must be a mapping")
    return selected_phase_delivery_declarations(document, {
        f"{kind}_fragment": fragments.get(kind)
        for kind in ("model", "dataset", "baseline")
    })


def assert_raw_parent_scoreable(bundle: VerifiedBundle, repo_root: Path) -> None:
    """Refuse required phase delivery from either the marker or its Git source."""

    if bundle.manifest.get("schema") != RUN_MANIFEST_SCHEMA:
        return
    if "required_phase_deliveries" in bundle.manifest:
        raise BundleError("raw phase parent requires declared delivery before scoring")
    if recorded_phase_delivery_declarations(bundle, repo_root):
        raise BundleError(
            "raw phase parent requires declared delivery from its recorded config; "
            "the manifest delivery marker is missing"
        )


def reused_delivery_scores(bundle: VerifiedBundle) -> dict | None:
    """Return verified paired source scores; never silently rerun a partial source."""
    from .verify import verify_bundle

    if bundle.manifest.get("schema") != DELIVERY_MANIFEST_SCHEMA:
        return None
    verified = verify_bundle(bundle.manifest_path)
    reuse = verified.manifest["score_reuse"]
    if reuse is None:
        return None
    try:
        raw = _verify_artifact(reuse["source_scores"], "reused source scores")
        scores = json.loads(raw)
        names = verified.manifest["scorers"]
        if not isinstance(scores, dict) or set(scores) != set(names):
            raise BundleError("reused scores do not match configured scorer identities")
        for name in names:
            entry = scores[name]
            if (
                not isinstance(entry, dict)
                or not isinstance(entry.get("aggregate"), dict)
                or not isinstance(entry.get("per_sample"), list)
            ):
                raise BundleError(
                    "reused scores require aggregate and full per_sample records"
                )
            if name != "cost":
                ids = [
                    row.get("sample_id")
                    for row in entry["per_sample"]
                    if isinstance(row, dict)
                ]
                if (
                    len(ids) != len(verified.split_ids)
                    or set(ids) != verified.split_ids
                ):
                    raise BundleError(
                        "reused per_sample scores do not match complete roster"
                    )
        if "cost" in scores:
            scores["cost"] = {
                "aggregate": dict(verified.manifest["cost"]),
                "per_sample": [],
            }
        return scores
    except (KeyError, TypeError, ValueError) as error:
        raise BundleError(f"reused source scores are malformed: {error}") from error
