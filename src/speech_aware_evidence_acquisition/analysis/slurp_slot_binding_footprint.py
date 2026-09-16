"""Model-free structural footprint of candidate-specific SLURP slot bindings.

Enumerate hypothetical candidate sets, never campaign answers or labels. This is
an ideal body-only calculation, not a runtime projection or a capacity verdict.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import statistics
from pathlib import Path

from ..rails.candidate_semantic_supply import (
    _read_released_authored_source,
    _released_candidate_index,
)
from ..rails.knowledge_provider import select_candidate_semantic_values
from ..rails.knowledge_stores import load_knowledge_store_binding
from ..rails.semantic_knowledge_build import _slot


def audit_footprint(
    *, source_rows, value_contents, candidate_values, candidate_ids,
    widths=(1, 2, 3), max_values_per_candidate=16, max_total_values=28,
):
    """Preserve every global section and count only omitted binding lines."""
    if (not candidate_ids or len(candidate_ids) != len(set(candidate_ids))
            or any(not isinstance(x, str) or not x for x in candidate_ids)):
        raise ValueError("candidate IDs must be nonempty and unique")
    if (not widths or len(widths) != len(set(widths))
            or any(type(x) is not int or not 1 <= x <= len(candidate_ids) for x in widths)
            or any(type(x) is not int or x < 1
                   for x in (max_values_per_candidate, max_total_values))):
        raise ValueError("enumeration widths and caps must be valid positive integers")
    rows = {f"slot-contract:{row['slot_id']}": row for row in source_rows}
    if len(rows) != len(source_rows) or set(rows) != set(value_contents):
        raise ValueError("source values are missing or duplicated")
    expected_index = {}
    lengths = {}
    for key, row in rows.items():
        if _slot(row)[2] != value_contents[key]:
            raise ValueError("rendered source differs from the released value")
        lengths[key] = {}
        for binding in row["intent_bindings"]:
            candidate = binding["intent_id"]
            if candidate not in candidate_ids:
                raise ValueError("source binding is outside candidate inventory")
            expected_index.setdefault(candidate, []).append(key)
            # Removing a nonfinal set of lines also removes one separator per
            # omitted binding. At least one binding remains on every selected card.
            lengths[key][candidate] = len(
                f"{candidate}: {binding['semantic_role'].strip()}".encode("utf-8")
            ) + len("\n- ".encode())
    expected_index = {k: tuple(sorted(v)) for k, v in expected_index.items()}
    if {k: tuple(v) for k, v in candidate_values.items()} != expected_index:
        raise ValueError("candidate mapping differs from the authored bindings")
    if set(expected_index) != set(candidate_ids):
        raise ValueError("footprint requires a construction binding for each enumerated ID")
    full_sizes = {k: len(v.encode("utf-8")) for k, v in value_contents.items()}
    all_sets = []
    for width in widths:
        count = total_full = total_projected = 0
        fractions, full_range, projected_range, selected_counts = [], [], [], []
        for candidates in itertools.permutations(candidate_ids, width):
            selected, _ = select_candidate_semantic_values(
                candidates, candidate_values,
                max_values_per_candidate=max_values_per_candidate,
                max_total_values=max_total_values,
            )
            full = sum(full_sizes[key] for key in selected)
            removed = sum(
                sum(lengths[key].values())
                - sum(lengths[key].get(candidate, 0) for candidate in candidates)
                for key in selected
            )
            projected = full - removed
            if not 0 < projected <= full:
                raise ValueError("projection accounting did not retain full global content")
            count += 1
            total_full += full
            total_projected += projected
            fractions.append(removed / full)
            full_range.append(full)
            projected_range.append(projected)
            selected_counts.append(len(selected))
        all_sets.append({
            "distinct_candidate_width": width, "ordered_sets": count,
            "full_body_bytes_sum": total_full,
            "projected_body_bytes_sum": total_projected,
            "pooled_body_byte_reduction_fraction": 1 - total_projected / total_full,
            "per_set_reduction_fraction_min": min(fractions),
            "per_set_reduction_fraction_median": statistics.median(fractions),
            "per_set_reduction_fraction_max": max(fractions),
            "full_body_bytes_min": min(full_range), "full_body_bytes_max": max(full_range),
            "projected_body_bytes_min": min(projected_range),
            "projected_body_bytes_max": max(projected_range),
            "selected_card_count_min": min(selected_counts),
            "selected_card_count_max": max(selected_counts),
        })
    return {
        "schema": "saea-slurp-slot-binding-footprint-v1",
        "candidate_count": len(candidate_ids), "card_count": len(rows),
        "binding_count": sum(len(row["intent_bindings"]) for row in source_rows),
        "full_store_body_bytes": sum(full_sizes.values()),
        "selection_caps": {"per_candidate": max_values_per_candidate, "total": max_total_values},
        "weighting": "Every ordered distinct candidate set once; not a campaign mixture.",
        "all_ordered_candidate_sets": all_sets,
        "limits": [
            "Ideal body bytes exclude derived-view headers, references and custody metadata.",
            "No tokenization, full request fit, model understanding or task quality is measured.",
            "Retain all global sections; only cross-candidate binding rows are omitted.",
            "Construction bindings are not exhaustive legal or mandatory slot schemas.",
            "Actual draft/explicit-tool targets outside candidates need separate handling.",
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    raw = args.baseline.read_bytes()
    config = json.loads(raw)
    binding = load_knowledge_store_binding(config, data_root=args.data_root)
    if binding is None:
        raise ValueError("baseline requires released named knowledge stores")
    store = binding.store("slot-contracts")
    catalog_pin = config["phase_material"]["perception"]["fill_params"]["source_catalog"]
    root = args.data_root.resolve()
    catalog_path = (root / catalog_pin["data_relpath"]).resolve()
    if root not in catalog_path.parents:
        raise ValueError("candidate catalog escapes data root")
    catalog_raw = catalog_path.read_bytes()
    if hashlib.sha256(catalog_raw).hexdigest() != catalog_pin["sha256"]:
        raise ValueError("candidate catalog source pin differs")
    candidates = tuple(row["candidate_id"] for row in json.loads(catalog_raw)["profiles"])
    index = _released_candidate_index(store, data_root=root, legal_candidate_ids=candidates)
    source = _read_released_authored_source(store, root)
    spec = config["knowledge_stores"]["slot-contracts"]["candidate_supply"]["solver"]
    report = audit_footprint(
        source_rows=source["rows"],
        value_contents={v.value_id: v.content for v in store.snapshot.values},
        candidate_values=index, candidate_ids=candidates,
        widths=tuple(range(1, spec["max_candidates"] + 1)),
        max_values_per_candidate=spec["max_values_per_candidate"],
        max_total_values=spec["max_total_values"],
    )
    report["source"] = {
        "baseline_file_sha256": hashlib.sha256(raw).hexdigest(),
        "slot_snapshot_content_sha256": store.snapshot.content_hash(),
        "slot_release_file_pin": dict(store.release_pin),
        "authored_source_file_pin": dict(store.source_pin),
        "candidate_catalog_file_pin": dict(catalog_pin),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    print(json.dumps({"output": str(args.output), "ordered_sets": sum(
        row["ordered_sets"] for row in report["all_ordered_candidate_sets"])}))


if __name__ == "__main__":
    main()
