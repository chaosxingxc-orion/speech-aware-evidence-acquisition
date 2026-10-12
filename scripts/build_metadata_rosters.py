#!/usr/bin/env python3
"""PRE Track A deployment-legal metadata-roster builder (tool(pre) build).

roster(call) = [company_name] + sorted unique speaker_name, verbatim from
the earnings21 asset's OWN file/speaker metadata CSVs (no gold at any
step): honorifics kept, typos kept, NO recasing, case-insensitive dedupe
(first-seen casing wins).

**Filtering rule, verified against the two already-committed reference
manifests before this script was written** (``derived/evidence-candidates/
p1-metadata-v1/manifest.json`` and ``.../p1-metadata-v2/manifest.json``,
plus the raw ``speaker-metadata.csv`` rows for the calls those manifests
cover): the ONLY excluded speaker names are the placeholder pattern
``^Speaker \\d+$``. ``"Operator"`` is a literal, real ``speaker_name`` CSV
value (verified directly against ``speaker-metadata.csv`` -- e.g. call
4330115, speaker_id 0), NOT a placeholder -- both p1-metadata-v1
(4366522: ``[..., "Operator"]``) and p1-metadata-v2 (4330115: ``[...,
"Operator", ...]``) keep it in the roster, and both manifests' own
``deployment_legality`` text says so explicitly ("placeholder speaker names
(^Speaker \\d+$) dropped as the only filtering rule"). This script
reproduces that verified rule exactly; it does NOT exclude ``"Operator"``.

Model-free, deterministic, stdlib-only (``csv``/``re``/``json``): never
opens a model session, never reads a reference/gold layer. Writes
``$SPEECHRL_DATA_DIR/derived/evidence-candidates/<out-id>/<id>.candidates.txt``
(one term per line, LF) plus a ``manifest.json`` (``rule_version``
``metadata-roster-rule-v1``). ``--dry-run`` prints every roster and writes
nothing.

Usage:
    python scripts/build_metadata_rosters.py --out-id p1-metadata-v3-kb34 --dry-run
    python scripts/build_metadata_rosters.py --out-id p1-metadata-v3-kb34
"""

from __future__ import annotations
import os

import argparse
import csv
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.data.carriers import get_carrier_descriptor  # noqa: E402
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    asset_dir,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.e0.artifacts import (  # noqa: E402
    sha256_file,
    write_json_artifact,
)

SCHEMA = "saea-metadata-roster-v1"
RULE_VERSION = "metadata-roster-rule-v1"
DEFAULT_CARRIER = "earnings21-original"
DEFAULT_IDS_FILE = (
    REPO_ROOT / "docs" / "receipts" / "probe-samples" / "kb-construction-sample.json"
)
SPEAKER_METADATA_FILENAME = "speaker-metadata.csv"
DEFAULT_DATA_ROOT = Path(
    (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")
)

_PLACEHOLDER_RE = re.compile(r"^Speaker \d+$")

DEPLOYMENT_LEGALITY = (
    "LEGAL: all terms verbatim from the earnings21 asset's own file/speaker metadata; no "
    "gold at any step; metadata typos preserved as-is; placeholder speaker names matching "
    "^Speaker \\d+$ are the ONLY filtering rule -- verbatim metadata values such as "
    "'Operator' are KEPT, matching the p1-metadata-v1/v2 precedent"
)
TERMS_RULE = (
    "company_name + non-placeholder (^Speaker \\d+$) speaker_name values, verbatim "
    "(honorifics/typos kept, no recasing), case-insensitive dedup keeping first-seen "
    "casing, sorted"
)


class RosterError(RuntimeError):
    """Metadata CSVs, a sample id, or a roster cannot be resolved."""


def load_ids(ids_file: Path) -> list[str]:
    document = json.loads(Path(ids_file).read_text(encoding="utf-8"))
    items = document.get("items")
    if not isinstance(items, list) or not items:
        raise RosterError(f"{ids_file}: no usable 'items' list")
    ids = [item["id"] for item in items]
    if len(set(ids)) != len(ids):
        raise RosterError(f"{ids_file}: duplicate ids")
    return sorted(ids)


def load_company_names(path: Path, id_column: str) -> dict[str, str]:
    with Path(path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return {row[id_column].strip(): row["company_name"].strip() for row in reader}


def load_speaker_names(path: Path) -> dict[str, list[str]]:
    speakers: dict[str, list[str]] = {}
    with Path(path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            speakers.setdefault(row["file_id"].strip(), []).append(row["speaker_name"].strip())
    return speakers


def build_roster(company_name: str, speaker_names: list[str]) -> list[str]:
    """``[company_name] + sorted unique non-placeholder speaker_name``,
    verbatim (honorifics/typos kept, no recasing); case-insensitive dedupe
    keeps the first-seen casing (module docstring's verified filtering
    rule: only ``^Speaker \\d+$`` is dropped -- ``"Operator"`` stays)."""

    terms = [company_name] + [
        name for name in speaker_names if not _PLACEHOLDER_RE.match(name)
    ]
    seen: dict[str, str] = {}
    for term in terms:
        seen.setdefault(term.casefold(), term)
    return sorted(seen.values())


def build_rosters(
    *, data_root: Path, lock: Mapping[str, object], carrier_lock_key: str, ids: list[str]
) -> tuple[dict[str, list[str]], dict[str, object]]:
    descriptor = get_carrier_descriptor(carrier_lock_key)
    carrier_dir = asset_dir(lock, carrier_lock_key, data_root)
    file_metadata_path = carrier_dir / descriptor.metadata_filename
    speaker_metadata_path = carrier_dir / SPEAKER_METADATA_FILENAME
    if not file_metadata_path.is_file():
        raise RosterError(f"file metadata CSV not found: {file_metadata_path}")
    if not speaker_metadata_path.is_file():
        raise RosterError(f"speaker metadata CSV not found: {speaker_metadata_path}")

    companies = load_company_names(file_metadata_path, descriptor.metadata_columns.id_column)
    speakers = load_speaker_names(speaker_metadata_path)

    rosters: dict[str, list[str]] = {}
    for sample_id in ids:
        if sample_id not in companies:
            raise RosterError(f"{file_metadata_path}: no row for sample {sample_id!r}")
        rosters[sample_id] = build_roster(companies[sample_id], speakers.get(sample_id, []))

    local_subdir = carrier_dir.relative_to(data_root).as_posix()
    sources = {
        "file_metadata": {
            "relpath": f"{local_subdir}/{descriptor.metadata_filename}",
            "sha256": sha256_file(file_metadata_path),
        },
        "speaker_metadata": {
            "relpath": f"{local_subdir}/{SPEAKER_METADATA_FILENAME}",
            "sha256": sha256_file(speaker_metadata_path),
        },
    }
    return rosters, sources


def _cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-id", required=True, help="materialization_id under evidence-candidates/")
    parser.add_argument("--ids-file", type=Path, default=DEFAULT_IDS_FILE)
    parser.add_argument("--carrier-lock-key", default=DEFAULT_CARRIER)
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument(
        "--lock-path", type=Path, default=None, help="TEST-ONLY override of the umbrella lock path"
    )
    parser.add_argument("--dry-run", action="store_true", help="print rosters, write nothing")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _cli_parser().parse_args(argv)
    try:
        ids = load_ids(args.ids_file)
        lock_path = args.lock_path if args.lock_path else umbrella_lock_path(REPO_ROOT)
        lock = load_lock(lock_path)
        rosters, sources = build_rosters(
            data_root=args.data_root,
            lock=lock,
            carrier_lock_key=args.carrier_lock_key,
            ids=ids,
        )
    except RosterError as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        return 1

    if args.dry_run:
        for sample_id in ids:
            terms = rosters[sample_id]
            print(f"{sample_id} ({len(terms)}): {terms}")
        return 0

    out_dir = args.data_root / "derived" / "evidence-candidates" / args.out_id
    out_dir.mkdir(parents=True, exist_ok=True)
    per_sample: dict[str, object] = {}
    for sample_id in ids:
        terms = rosters[sample_id]
        candidate_path = out_dir / f"{sample_id}.candidates.txt"
        candidate_path.write_text(
            "".join(f"{term}\n" for term in terms), encoding="utf-8", newline="\n"
        )
        per_sample[sample_id] = {
            "terms": terms,
            "count": len(terms),
            "sha256": sha256_file(candidate_path),
        }

    manifest = {
        "schema": SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "materialization_id": args.out_id,
        "rule_version": RULE_VERSION,
        "extends": (
            "p1-metadata-v1 (fast-3) / p1-metadata-v2 (frozen ten); rules byte-identical, "
            f"applied to the {args.ids_file.stem} split"
        ),
        "deployment_legality": DEPLOYMENT_LEGALITY,
        "sources": sources,
        "inputs": {"carrier_lock_key": args.carrier_lock_key, "sample_ids": ids},
        "rules": {"terms": TERMS_RULE},
        "per_sample": per_sample,
    }
    manifest_path = out_dir / "manifest.json"
    manifest_sha256 = write_json_artifact(manifest_path, manifest)

    counts = [len(rosters[sample_id]) for sample_id in ids]
    print(
        json.dumps(
            {
                "out_dir": str(out_dir),
                "manifest": str(manifest_path),
                "manifest_sha256": manifest_sha256,
                "samples": len(ids),
                "term_count_min": min(counts),
                "term_count_max": max(counts),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
