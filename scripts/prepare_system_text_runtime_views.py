#!/usr/bin/env python3
"""Publish the registered TRAIN slices through the existing native media loader.

Read metadata, seed ancestry and TRAIN media bytes only. Add no model, encoder,
scorer or GPU contacts. Validate every source and output before publication;
refuse replacement of different bytes. Candidate supplies and admission remain
separate requirements, including a fresh cumulative-source check per candidate.
"""

import argparse
import hashlib
import json
import tempfile
from pathlib import Path

from speech_aware_evidence_acquisition.data.runtime_subset import build_runtime_subset
from speech_aware_evidence_acquisition.data.slurp import load_slurp_engineering_gate
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.system_search_protocol import (
    build_protocol,
    stage_for,
)
from speech_aware_evidence_acquisition.rails.system_text_policy import (
    SystemTextPolicyBundle,
    _read_pin,
    assert_roster_disjoint,
    require,
)

PACKAGE = "docs/readiness/2026-10-01-slurp-system-text-search-v1"
SLICES = (
    ("update-1", "fold_a", 0),
    ("update-2", "fold_a", 400),
    ("update-3", "fold_b", 0),
    ("selection", "fold_b", 400),
)


def encode(document):
    return (
        json.dumps(
            document, sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False
        )
        + "\n"
    ).encode()


def pin(relative, raw):
    return {"relpath": relative, "sha256": hashlib.sha256(raw).hexdigest()}


def prepare(*, repo, data_root, protocol_path, workers=4, parent_protocol_paths=()):
    """Materialize exact prospective cohorts; never change an exposure record."""
    repo, data_root, protocol_path = (
        Path(repo).resolve(),
        Path(data_root).resolve(),
        Path(protocol_path).resolve(),
    )
    require(protocol_path.is_relative_to(repo), "protocol escaped repository")
    require(
        type(workers) is int and 1 <= workers <= 8,
        "preparation workers must be in [1, 8]",
    )
    protocol_raw = protocol_path.read_bytes()
    protocol = json.loads(protocol_raw)
    rosters = {
        key: [row["sample_id"] for row in json.loads(_read_pin(source, repo))["items"]]
        for key, source in protocol["source_rosters"].items()
    }
    expected = build_protocol(rosters)
    require(
        protocol["schema"] == expected["schema"]
        and protocol["seed"] == expected["seed"]
        and protocol["stages"] == expected["stages"],
        "registered selection differs",
    )
    seed_pin = protocol["seed_bundle"]
    known, ancestry = {}, []
    for source_path in [*parent_protocol_paths, protocol_path]:
        source_path = Path(source_path).resolve()
        require(source_path.is_relative_to(repo), "parent protocol escaped repository")
        source_pin = json.loads(source_path.read_bytes())["seed_bundle"]
        document = json.loads(
            _read_pin(
                {key: source_pin[key] for key in ("relpath", "sha256")}, data_root
            )
        )
        require(
            set(document["parent_ids"]) <= set(known),
            "seed parent chain is missing or unordered",
        )
        bundle = SystemTextPolicyBundle.from_json(
            document, parents=[known[p] for p in document["parent_ids"]]
        )
        require(
            bundle.bundle_id == source_pin["bundle_id"], "seed bundle identity differs"
        )
        require(bundle.bundle_id not in known, "duplicate seed ancestor")
        known[bundle.bundle_id] = bundle
        if source_path != protocol_path:
            ancestry.append(source_pin)
    referenced = {p for b in known.values() for p in b.as_json()["parent_ids"]}
    require(referenced == set(known) - {bundle.bundle_id}, "unrelated seed ancestor")
    for stage, _, _ in SLICES:
        assert_roster_disjoint(
            bundle.as_json()["cumulative_sources"],
            stage_for(protocol, stage)["sample_ids"],
        )

    parents, parent_pins = {}, {}
    for key, letter in (("fold_a", "a"), ("fold_b", "b")):
        relative = f"configs/dataset/slurp-speech-native-evo-fold-{letter}-1080.json"
        path = repo / relative
        raw = path.read_bytes()
        parent = json.loads(raw)
        require(
            parent["split_role"] == "discovery"
            and parent["count"] == 1080
            and [item["sample_id"] for item in parent["items"]] == rosters[key],
            "parent roster differs",
        )
        load_slurp_engineering_gate(
            path,
            data_root=data_root,
            expected_count=1080,
            expected_split_name=parent["split_name"],
            workers=workers,
        )
        parents[key], parent_pins[key] = parent, pin(relative, raw)

    outputs, stages = {}, []
    with tempfile.TemporaryDirectory(prefix="saea-system-text-views-") as temporary:
        for stage, source, start in SLICES:
            spec = stage_for(protocol, stage)
            view, receipt = build_runtime_subset(
                parents[source],
                seed=protocol["seed"],
                start=start,
                count=400,
                name=f"SLURP-SYSTEM-TEXT-{stage.upper()}-400-V1",
            )
            require(
                receipt["sample_ids"] == spec["sample_ids"],
                "runtime slice differs from registration",
            )
            view_rel = (
                f"configs/dataset/slurp-speech-native-system-text-{stage}-400-v1.json"
            )
            receipt_rel = f"docs/receipts/rosters/slurp-system-text-{stage}-400-v1.json"
            raw = encode(view)
            temporary_view = Path(temporary) / f"{stage}.json"
            temporary_view.write_bytes(raw)
            load_slurp_engineering_gate(
                temporary_view,
                data_root=data_root,
                expected_count=400,
                expected_split_name=view["split_name"],
                workers=workers,
            )
            outputs[view_rel], outputs[receipt_rel] = raw, encode(receipt)
            stages.append(
                {
                    "stage": stage,
                    "source_roster": protocol["source_rosters"][source],
                    "parent_runtime_view": parent_pins[source],
                    "runtime_view": pin(view_rel, raw),
                    "subset_receipt": pin(receipt_rel, outputs[receipt_rel]),
                    "slice_start": start,
                    "count": view["count"],
                    "audio_seconds_total": view["audio_seconds_total"],
                    "split_identity_hash": view["split_identity_hash"],
                    "roster_sha256": spec["roster_sha256"],
                    "runtime_view_sha256": view["runtime_view_sha256"],
                    "source_binding_sha256": content_hash(receipt),
                    "native_media_verification": "PASS",
                    "seed_source_overlap_utterances": 0,
                }
            )

    result = {
        "schema": "saea-system-text-runtime-views-v1",
        "protocol": pin(protocol_path.relative_to(repo).as_posix(), protocol_raw),
        "seed_bundle": seed_pin,
        "seed_ancestry": ancestry,
        "stages": stages,
        "workers": workers,
        "no_runtime_authority": True,
        "contacts": {"model": 0, "tool": 0, "scorer": 0, "gpu": 0},
        "limits": "Metadata and TRAIN media verification only. No task answers or quality read. "
        "Recheck cumulative sources, own supply, FIT and admission for every future candidate.",
    }
    outputs[f"{PACKAGE}/runtime-views-v1.json"] = encode(result)
    for relative, raw in outputs.items():
        path = (repo / relative).resolve()
        require(path.is_relative_to(repo), "output escaped repository")
        require(
            not path.exists() or path.read_bytes() == raw,
            f"Refuse to replace different bytes: {relative}",
        )
    for relative, raw in outputs.items():
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            with path.open("xb") as stream:
                stream.write(raw)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--protocol", required=True, type=Path)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument(
        "--parent-protocol",
        action="append",
        type=Path,
        default=[],
        help="Earlier pinned seed protocols, oldest first; metadata only",
    )
    args = parser.parse_args()
    result = prepare(
        repo=args.repo_root,
        data_root=args.data_root,
        protocol_path=args.protocol,
        workers=args.workers,
        parent_protocol_paths=args.parent_protocol,
    )
    print(
        json.dumps(
            {
                "stages": [s["stage"] for s in result["stages"]],
                "rows": sum(s["count"] for s in result["stages"]),
                "contacts": result["contacts"],
                "no_runtime_authority": True,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
