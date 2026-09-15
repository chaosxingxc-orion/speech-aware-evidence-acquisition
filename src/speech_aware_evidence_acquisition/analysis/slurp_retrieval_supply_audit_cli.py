"""CLI for the source-bound SLURP retrieval-supply breadth audit."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from typing import Mapping

from .dev100_reviewer_audit import arm_offline_guard
from .slurp_retrieval_supply_audit import (
    AUDIT_SCHEMA,
    AuditError,
    ReferenceIntentRow,
    build_audit_report,
    build_selection_grid,
    load_observed_support,
    load_selection_anchor,
    write_new_json,
)
from .slurp_topn_diagnostics_cli import load_verified_slurp_reference_intents
from ..data.slurp import load_slurp_split
from ..rails.knowledge_stores import load_knowledge_store_binding
from ..rails.phase_supply import load_sealed_segment_vectors, load_sealed_vectors

CONFIG_SCHEMA = "saea-slurp-retrieval-supply-audit-config-v1"
RECEIPT_SCHEMA = "saea-slurp-retrieval-supply-audit-receipt-v1"
_SHA256 = re.compile(r"[0-9a-f]{64}")


def _pin(value: object, field: str) -> dict[str, str]:
    if not isinstance(value, Mapping) or set(value) != {"relpath", "sha256"}:
        raise AuditError(f"{field} must contain exactly relpath and sha256")
    relpath, sha256 = value["relpath"], value["sha256"]
    if (
        not isinstance(relpath, str)
        or not relpath
        or relpath.startswith("/")
        or "\\" in relpath
        or any(part in {"", ".", ".."} for part in relpath.split("/"))
    ):
        raise AuditError(f"{field}.relpath must be a confined relative path")
    if not isinstance(sha256, str) or _SHA256.fullmatch(sha256) is None:
        raise AuditError(f"{field}.sha256 must be lowercase 64-hex")
    return {"relpath": relpath, "sha256": sha256}


def _read_pinned(root: Path, pin: Mapping[str, str], field: str) -> tuple[Mapping[str, object], str]:
    base = Path(root).resolve()
    path = (base / pin["relpath"]).resolve()
    if path == base or base not in path.parents:
        raise AuditError(f"{field} escapes its root")
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise AuditError(f"cannot read {field}: {path}") from error
    measured = hashlib.sha256(raw).hexdigest()
    if measured != pin["sha256"]:
        raise AuditError(f"{field} SHA-256 mismatch")
    try:
        document = json.loads(raw)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise AuditError(f"{field} is not valid UTF-8 JSON") from error
    if not isinstance(document, Mapping):
        raise AuditError(f"{field} must be a JSON object")
    return document, measured


def _load_config(path: Path) -> tuple[Mapping[str, object], str]:
    raw = Path(path).read_bytes()
    document = json.loads(raw)
    if not isinstance(document, Mapping) or document.get("schema") != CONFIG_SCHEMA:
        raise AuditError("audit config has the wrong schema")
    return document, hashlib.sha256(raw).hexdigest()


def _reference_rows(
    binding: Mapping[str, object], sample_ids: tuple[str, ...]
) -> tuple[ReferenceIntentRow, ...]:
    captured = {}

    def loader(*args, **kwargs):
        records = load_slurp_split(*args, **kwargs)
        captured.update({record.sample_id: record for record in records})
        return records

    verified = load_verified_slurp_reference_intents(
        binding, sample_ids, loader=loader
    )
    return tuple(
        ReferenceIntentRow(
            row.sample_id,
            row.intent_id,
            captured[row.sample_id].scenario,
        )
        for row in verified
    )


def run(
    *,
    config_path: Path,
    repo_root: Path,
    data_root: Path,
    output_dir: Path,
) -> dict[str, object]:
    """Run selection, seal it, then perform the authorized offline join."""

    attempts = arm_offline_guard()
    config, config_sha256 = _load_config(config_path)
    pins = config.get("inputs")
    expected = config.get("expected")
    if not isinstance(pins, Mapping) or not isinstance(expected, Mapping):
        raise AuditError("audit config needs inputs and expected objects")
    baseline_pin = _pin(pins.get("baseline"), "inputs.baseline")
    release_pin = _pin(pins.get("release"), "inputs.release")
    diagnostic_pin = _pin(
        pins.get("reference_config"), "inputs.reference_config"
    )
    support_pin = _pin(
        pins.get("support_diagnostic"), "inputs.support_diagnostic"
    )
    baseline, _ = _read_pinned(repo_root, baseline_pin, "baseline")
    release, _ = _read_pinned(data_root, release_pin, "root release")
    reference_config, _ = _read_pinned(
        data_root, diagnostic_pin, "reference config"
    )
    if (
        release.get("schema") != "saea-root-complete-quality-release-v1"
        or release.get("model_tool_scorer_contacts_added") != 0
        or "Join governed TRAIN references offline for exactly the sealed Fold A cohort"
        not in release.get("allowed", ())
        or "Fold B result or reference consumption" not in release.get("excluded", ())
    ):
        raise AuditError("root release does not authorize this exact offline join")

    count = expected.get("sample_count")
    ordered_sha = expected.get("ordered_sample_ids_sha256")
    if isinstance(count, bool) or not isinstance(count, int) or count <= 0:
        raise AuditError("expected.sample_count must be positive")
    support_path = data_root / support_pin["relpath"]
    anchor = load_selection_anchor(
        support_path,
        expected_sha256=support_pin["sha256"],
        expected_sample_count=count,
        expected_ordered_sample_ids_sha256=ordered_sha,
    )

    store_id = config.get("store_id")
    phase = config.get("phase")
    if not isinstance(store_id, str) or not isinstance(phase, str):
        raise AuditError("store_id and phase must be strings")
    stores = load_knowledge_store_binding(baseline, data_root=data_root)
    if stores is None:
        raise AuditError("baseline has no knowledge stores")
    store = stores.store(store_id)
    route = store.phase_supply.get(phase)
    if not isinstance(route, Mapping):
        raise AuditError("baseline lacks the selected store phase route")
    if (
        route.get("provider") != "kb-facet-v1"
        or route.get("rank_policy") != "saea-rank-wcos-prior-agree-v1"
        or route.get("fuse_policy") != "saea-fuse-associated-values-v1"
        or route.get("tau") != 0.0
        or route.get("rank_weights")
        != {"w_agree": 0.0, "w_cos": 1.0, "w_prior": 0.0}
        or route.get("fuse_coverage") != {"c": 1, "m": 8, "top_l": 8}
        or route.get("k") != 8
    ):
        raise AuditError("baseline route differs from the registered breadth-eight anchor")
    dimensions = route.get("dimensions")
    query_source = route.get("query_source")
    facet_source = route.get("facet_source")
    if not isinstance(query_source, Mapping) or not isinstance(facet_source, Mapping):
        raise AuditError("baseline route lacks vector sources")
    query_pin = _pin(
        {"relpath": query_source.get("relpath"), "sha256": query_source.get("sha256")},
        "query source",
    )
    facet_pin = _pin(
        {"relpath": facet_source.get("relpath"), "sha256": facet_source.get("sha256")},
        "facet source",
    )
    if (
        not isinstance(dimensions, list)
        or not dimensions
        or route["query_source"].get("kind") != "sealed-segment-vectors"
        or route["facet_source"].get("kind") != "sealed-vectors"
    ):
        raise AuditError("audit requires registered segment queries and sealed facets")

    queries = load_sealed_segment_vectors(
        data_root / query_pin["relpath"],
        expected_sha256=query_pin["sha256"],
        dimensions=dimensions,
    )
    facets = load_sealed_vectors(
        data_root / facet_pin["relpath"],
        expected_sha256=facet_pin["sha256"],
        dimensions=dimensions,
    )
    breadths = config.get("breadths")
    if not isinstance(breadths, list):
        raise AuditError("breadths must be a list")
    selection = build_selection_grid(
        snapshot=store.snapshot,
        query_vectors_by_sample=queries,
        facet_vectors=facets,
        ordered_sample_ids=anchor.sample_ids,
        breadths=tuple(breadths),
        store_id=store_id,
        workers=1,
    )
    replay_breadth = expected.get("replay_breadth")
    if replay_breadth not in selection.by_breadth:
        raise AuditError("registered replay breadth is absent")
    if any(
        selection.by_breadth[replay_breadth][sample_id].selected_ids_sha256
        != selected_sha
        for sample_id, selected_sha in zip(
            anchor.sample_ids, anchor.selected_ids_sha256, strict=True
        )
    ):
        raise AuditError("breadth-eight selected value hash replay mismatch")

    outputs = config.get("outputs")
    if not isinstance(outputs, Mapping):
        raise AuditError("outputs must be an object")
    selection_name = outputs.get("selection")
    report_name = outputs.get("report")
    receipt_name = outputs.get("receipt")
    if any(
        not isinstance(name, str) or not name or "/" in name or "\\" in name
        for name in (selection_name, report_name, receipt_name)
    ):
        raise AuditError("output names must be simple filenames")
    selection_ref = write_new_json(
        output_dir / selection_name, selection.commitment()
    )

    # The reference-bearing reads occur only after the model-free selection
    # commitment is durable.
    observed = load_observed_support(
        support_path,
        expected_sha256=support_pin["sha256"],
        expected_sample_ids=anchor.sample_ids,
    )
    reference_source = reference_config.get("reference_source")
    if not isinstance(reference_source, Mapping):
        raise AuditError("reference config lacks reference_source")
    references = _reference_rows(reference_source, anchor.sample_ids)
    report = build_audit_report(
        selection=selection,
        reference_rows=references,
        observed_rows=observed,
        replay_breadth=replay_breadth,
        expected_replay_own_supplied=expected.get("replay_own_supplied"),
        expected_replay_supply_and_covered=expected.get(
            "replay_supply_and_covered"
        ),
    )
    observed_misses = sum(not row.c0_covered for row in observed)
    observed_neither = sum(
        not row.c0_covered and not row.own_intent_supplied for row in observed
    )
    if (
        observed_misses != expected.get("c0_miss_count")
        or observed_neither != expected.get("c0_neither_count")
    ):
        raise AuditError("released C0 subgroup counts differ from registered anchors")
    report["provenance"] = {
        "config_sha256": config_sha256,
        "input_sha256": {
            "baseline": baseline_pin["sha256"],
            "release": release_pin["sha256"],
            "reference_config": diagnostic_pin["sha256"],
            "support_diagnostic": support_pin["sha256"],
            "query_vectors": query_pin["sha256"],
            "facet_vectors": facet_pin["sha256"],
            "knowledge_snapshot": store.snapshot_pin["sha256"],
            "knowledge_release": store.release_pin["sha256"],
        },
        "selection": {
            "relpath": selection_name,
            "sha256": selection_ref["sha256"],
        },
    }
    report_ref = write_new_json(output_dir / report_name, report)

    code_paths = (
        Path(__file__),
        Path(__file__).with_name("slurp_retrieval_supply_audit.py"),
    )
    code_hashes = {
        str(path.relative_to(repo_root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in code_paths
    }
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "audit_schema": AUDIT_SCHEMA,
        "config": {
            "relpath": str(Path(config_path).resolve().relative_to(Path(repo_root).resolve())),
            "sha256": config_sha256,
        },
        "code_sha256": code_hashes,
        "inputs": report["provenance"]["input_sha256"],
        "outputs": {
            "selection": {
                "relpath": selection_name,
                "sha256": selection_ref["sha256"],
            },
            "report": {
                "relpath": report_name,
                "sha256": report_ref["sha256"],
            },
        },
        "cohort": report["cohort"],
        "breadths": list(selection.breadths),
        "offline_connect_attempts": attempts.count,
        "model_tool_scorer_contacts_added": 0,
    }
    if attempts.count != 0:
        raise AuditError("offline guard observed a connection attempt")
    receipt_ref = write_new_json(output_dir / receipt_name, receipt)
    return {
        "schema": RECEIPT_SCHEMA,
        "selection": selection_ref,
        "report": report_ref,
        "receipt": receipt_ref,
        "sample_count": len(anchor.sample_ids),
        "breadths": list(selection.breadths),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result = run(
        config_path=args.config,
        repo_root=args.repo_root,
        data_root=args.data_root,
        output_dir=args.output_dir,
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
