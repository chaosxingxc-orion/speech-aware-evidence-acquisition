#!/usr/bin/env python3
"""Build a tier-1 Audio2Tool roster drawn the RELEASE's own way.

Why this roster exists
----------------------
``docs/readiness/2026-09-04-a2t-official-protocol-replication-v1-verdict.md``
left one unexplained quantity: tier-1 tool accuracy 60.0 % against a
published 92.4 %, on a roster that is 50 stratified rows per tier with mixed
speakers. That verdict ranked the ROSTER first among the remaining suspects,
because the released benchmark code evaluates the FIRST SUCCESSFUL SPEAKER OF
EVERY QUERY of a tier, not a stratified subsample over both shipped speakers.
This builder draws from that population instead.

The official population rule, derived from the pinned code
-----------------------------------------------------------
Source: ``github.com/audio2tool/Audio2Tool`` at commit
``b9d5383ca30945fbafb965a04bea40117e1e8a82`` (MIT); clone receipt
``docs/receipts/environments/audio2tool-official-code.json``.

``audio_benchmark/datasets/tier1_dataset.py`` walks ``sorted(data_dir.glob(
"query_*"))`` and, per query directory, keeps the rows of
``generation_results.csv`` **in file order** whose ``success`` is true,
resolving each row's ``audio_path`` and falling back to ``query_dir /
Path(audio_path).name`` when the CSV's absolute path is stale (the released
CSVs carry the authors' internal ``/data2/...`` paths, so on any public copy
the fallback is the branch that fires). ``BenchmarkEvaluator`` with
``max_speakers_per_query 1`` then evaluates ``audio_paths[0]``.

The public v1.0 release ships exactly TWO of the up-to-25 generated speakers
per tier-1 query directory, and the tier manifest
(``public/tier1_direct_data/tier1_direct.json``) carries one item per shipped
(query, speaker) recording, ordered by query directory and then by
``speaker_idx``. Applying the loader rule above to the released bytes
therefore selects, for each query directory, the shipped speaker with the
LOWEST ``speaker_idx`` -- which is the manifest item with the lowest ``id``
in that directory. This builder verifies that equivalence directory by
directory rather than assuming it (``--verify-official-rule``, on by
default): for all 2,146 tier-1 query directories the two agree.

ONE directory is a documented exception. ``query_01982``'s
``generation_results.csv`` names 25 speaker filenames, none of which is
either of the two wavs the release actually ships in that directory
(``speaker_11_3dspeaker_...`` and ``speaker_14_3dspeaker_...``): its CSV
belongs to a different synthesis batch. The internal loader would resolve no
audio there and skip the query; the released manifest is unambiguous. This
builder treats the MANIFEST as authoritative -- the population is 2,146
queries -- and records the exception in the receipt so a reader can subtract
it.

``max_samples`` is deliberately NOT used to reach 500. The release orders
every subset ``smart_home -> wearables -> smart_car`` (its own README says
so), so the first 500 sorted query directories would be a pure ``smart_home``
sample. The draw below is uniform without replacement over all 2,146.

Contact surface
---------------
Label-free and contact-free. The tier manifest is read for identity and
media facts ONLY (``id``, ``query_idx``, ``path``, ``duration``,
``speaker_idx``, and ``domain`` for the aggregate stratum counts the
preregistration reports); ``query``, ``tool_name``, ``expected_tool_call``,
``extracted_params``, ``additional_tool_calls``, ``functions`` and
``instruction`` are never read. ``generation_results.csv`` is read for
``speaker_idx``/``audio_path``/``success`` only. WAV bytes are hashed and
their container headers read; no audio is decoded. No model, network,
tokenizer or scorer contact.

Outputs
-------
``--part draw`` (default) writes the 500-row flight roster;
``--part remainder`` writes the other 1,646 rows, which is the roster the
preregistered extension contingency would fly; ``--part all`` writes all
2,146. Every part uses the SAME draw, so ``draw`` and ``remainder`` are a
partition of ``all``.

Usage::

    python scripts/build_a2t_tier1_official_population_roster.py             # print only
    python scripts/build_a2t_tier1_official_population_roster.py --write
    python scripts/build_a2t_tier1_official_population_roster.py \\
        --part remainder --write
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import random
import wave
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

REPO = Path(__file__).resolve().parents[1]

CARRIER = "audio2tool"
TIER = "tier1_direct"
SPLIT_ROLE = "discovery"
DRAW_SEED = 20260803
DRAW_COUNT = 500
POPULATION_COUNT = 2146
SHIPPED_SPEAKERS_PER_QUERY = 2
# The one query directory whose generation_results.csv names a different
# synthesis batch than the wavs the release ships beside it (module
# docstring). Recorded, not silently repaired.
CSV_MISMATCH_QUERY_DIRS = ("query_01982",)
MANIFEST_DURATION_TOLERANCE = 1e-3
PROBE_RECEIPT_STEM = "a2t-tier1-official-population-500"
OFFICIAL_CODE_COMMIT = "b9d5383ca30945fbafb965a04bea40117e1e8a82"
OFFICIAL_CODE_RECEIPT = "docs/receipts/environments/audio2tool-official-code.json"

SPLIT_NAMES = {
    "draw": "A2T-TIER1-OFFICIAL-POP-500",
    "remainder": "A2T-TIER1-OFFICIAL-POP-REMAINDER-1646",
    "all": "A2T-TIER1-OFFICIAL-POP-2146",
}
DEFAULT_OUTPUTS = {
    "draw": "flight-roster-receipt.json",
    "remainder": "flight-roster-receipt-remainder.json",
    "all": "flight-roster-receipt-all.json",
}
OUTPUT_DIR = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-04-a2t-tier1-official-population-roster"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_lines(values) -> str:
    return hashlib.sha256("\n".join(sorted(values)).encode("utf-8")).hexdigest()


def canonical_sha256(document: object) -> str:
    payload = json.dumps(
        document, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _validate_relpath(relpath: object, context: str) -> str:
    if not isinstance(relpath, str) or not relpath:
        raise ValueError(f"{context}: audio path must be a non-empty string")
    if "\\" in relpath or ":" in relpath or relpath.startswith("/"):
        raise ValueError(f"{context}: audio path {relpath!r} is not a plain relative path")
    pure = PurePosixPath(relpath)
    if any(part in ("", ".", "..") for part in pure.parts):
        raise ValueError(f"{context}: audio path {relpath!r} escapes its tier directory")
    if not relpath.endswith(".wav"):
        raise ValueError(f"{context}: audio path {relpath!r} is not a .wav file")
    return relpath


def _seconds(value: object, context: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value <= 0
    ):
        raise ValueError(f"{context}: duration must be a finite positive number, got {value!r}")
    return float(value)


def _wav_seconds(path: Path, context: str) -> float:
    try:
        with wave.open(str(path), "rb") as handle:
            frames = handle.getnframes()
            rate = handle.getframerate()
    except (OSError, EOFError, wave.Error) as error:
        raise ValueError(f"{context}: cannot read wav header of {path}: {error}") from error
    if frames <= 0 or rate <= 0:
        raise ValueError(f"{context}: wav header of {path} is degenerate")
    return frames / rate


def official_population(
    public_dir: Path, *, verify_official_rule: bool = True
) -> tuple[list[dict[str, object]], dict[str, object]]:
    """The release's own tier-1 population: one manifest row per query
    directory, the first shipped speaker, in sorted query-directory order.

    Returns ``(rows, audit)`` where ``audit`` records how the manifest-first
    rule compared against a direct replay of the released loader's
    ``generation_results.csv`` walk.
    """

    manifest_path = public_dir / f"{TIER}_data" / f"{TIER}.json"
    audios_dir = public_dir / f"{TIER}_audios"
    if not manifest_path.is_file():
        raise ValueError(f"tier manifest missing: {manifest_path}")
    if not audios_dir.is_dir():
        raise ValueError(f"tier audio directory missing: {audios_dir}")
    try:
        entries = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot read tier manifest {manifest_path}: {error}") from error
    if not isinstance(entries, list) or not entries:
        raise ValueError(f"tier manifest {manifest_path} must be a non-empty JSON list")

    by_query_dir: dict[str, list[dict[str, object]]] = {}
    seen_ids: set[int] = set()
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise ValueError("tier manifest item must be an object")
        entry_id = entry.get("id")
        query_idx = entry.get("query_idx")
        speaker_idx = entry.get("speaker_idx")
        if (
            isinstance(entry_id, bool)
            or not isinstance(entry_id, int)
            or entry_id in seen_ids
            or isinstance(query_idx, bool)
            or not isinstance(query_idx, int)
            or isinstance(speaker_idx, bool)
            or not isinstance(speaker_idx, int)
            or speaker_idx < 0
        ):
            raise ValueError(f"tier manifest item is malformed: id={entry_id!r}")
        seen_ids.add(entry_id)
        relpath = _validate_relpath(entry.get("path"), f"{TIER}:{entry_id:06d}")
        parts = relpath.split("/")
        if len(parts) != 3 or parts[0] != f"{TIER}_audios" or not parts[1].startswith("query_"):
            raise ValueError(f"unexpected tier-1 audio layout: {relpath!r}")
        domain = entry.get("domain")
        if not isinstance(domain, str) or not domain:
            raise ValueError(f"tier manifest item {entry_id} has no domain")
        by_query_dir.setdefault(parts[1], []).append(
            {
                "id": entry_id,
                "query_idx": query_idx,
                "speaker_idx": speaker_idx,
                "audio_relpath_in_public": relpath,
                "audio_seconds": _seconds(entry.get("duration"), f"{TIER}:{entry_id:06d}"),
                "domain": domain,
                "wav_name": parts[2],
                "query_dir": parts[1],
            }
        )

    on_disk_dirs = sorted(
        path.name for path in audios_dir.iterdir() if path.is_dir() and path.name.startswith("query_")
    )
    if on_disk_dirs != sorted(by_query_dir):
        raise ValueError(
            "the tier manifest and the on-disk query directories disagree "
            f"({len(by_query_dir)} manifest vs {len(on_disk_dirs)} on disk)"
        )
    if len(by_query_dir) != POPULATION_COUNT:
        raise ValueError(
            f"expected {POPULATION_COUNT} tier-1 query directories, found {len(by_query_dir)}"
        )

    rows: list[dict[str, object]] = []
    for query_dir in on_disk_dirs:
        shipped = sorted(by_query_dir[query_dir], key=lambda row: int(row["id"]))
        if len(shipped) != SHIPPED_SPEAKERS_PER_QUERY:
            raise ValueError(
                f"{query_dir}: the release ships {len(shipped)} tier-1 speakers, "
                f"expected {SHIPPED_SPEAKERS_PER_QUERY}"
            )
        first = shipped[0]
        if int(first["speaker_idx"]) != min(int(row["speaker_idx"]) for row in shipped):
            raise ValueError(
                f"{query_dir}: the lowest-id manifest row is not the lowest speaker_idx; "
                "the first-speaker rule cannot be resolved from the manifest alone"
            )
        if len({int(row["query_idx"]) for row in shipped}) != 1:
            raise ValueError(f"{query_dir}: shipped rows disagree on query_idx")
        rows.append(first)

    audit = _verify_official_rule(audios_dir, rows) if verify_official_rule else {
        "performed": False,
        "reason": "--no-verify-official-rule",
    }
    return rows, audit


def _verify_official_rule(
    audios_dir: Path, rows: Sequence[Mapping[str, object]]
) -> dict[str, object]:
    """Replay ``Tier1Dataset._get_audio_paths`` on the released bytes and
    compare its first pick with this builder's manifest-first pick."""

    agreements = 0
    unresolved: list[str] = []
    disagreements: list[dict[str, object]] = []
    success_false_rows = 0
    for row in rows:
        query_dir = str(row["query_dir"])
        directory = audios_dir / query_dir
        results_path = directory / "generation_results.csv"
        chosen: str | None = None
        if results_path.is_file():
            with results_path.open(newline="", encoding="utf-8") as handle:
                for csv_row in csv.DictReader(handle):
                    if str(csv_row.get("success", "True")).lower() != "true":
                        success_false_rows += 1
                        continue
                    audio_path = str(csv_row.get("audio_path", ""))
                    if not audio_path:
                        continue
                    name = PurePosixPath(audio_path.replace("\\", "/")).name
                    if (directory / name).is_file():
                        chosen = name
                        break
        else:
            wavs = sorted(path.name for path in directory.glob("speaker_*.wav"))
            chosen = wavs[0] if wavs else None
        if chosen is None:
            unresolved.append(query_dir)
            continue
        if chosen == str(row["wav_name"]):
            agreements += 1
        else:
            disagreements.append(
                {"query_dir": query_dir, "loader_pick": chosen, "manifest_pick": row["wav_name"]}
            )
    if disagreements:
        raise ValueError(
            "the released loader's first pick disagrees with the manifest-first pick on "
            f"{len(disagreements)} query directories: {disagreements[:3]}"
        )
    if sorted(unresolved) != sorted(CSV_MISMATCH_QUERY_DIRS):
        raise ValueError(
            "the set of query directories whose generation_results.csv resolves no shipped "
            f"wav changed: {sorted(unresolved)} (documented: {sorted(CSV_MISMATCH_QUERY_DIRS)})"
        )
    return {
        "performed": True,
        "method": (
            "replay of audio_benchmark/datasets/tier1_dataset.py::_get_audio_paths "
            "(only_successful=True, speakers_per_query=1, stale-absolute-path fallback to "
            "query_dir/<basename>) at commit " + OFFICIAL_CODE_COMMIT
        ),
        "query_directories": len(rows),
        "agreements": agreements,
        "disagreements": 0,
        "csv_rows_marked_unsuccessful": success_false_rows,
        "query_directories_whose_csv_resolves_no_shipped_wav": sorted(unresolved),
        "note": (
            "the released generation_results.csv files carry the authors' internal "
            "/data2/... absolute paths, so the loader's documented stale-path fallback is "
            "the branch that fires on any public copy; on every directory but the recorded "
            "exception it selects exactly the manifest's lowest-id (lowest speaker_idx) row"
        ),
    }


def build_roster(
    *,
    data_root: Path,
    part: str,
    seed: int = DRAW_SEED,
    count: int = DRAW_COUNT,
    verify_official_rule: bool = True,
) -> dict[str, object]:
    """Return the flight-roster receipt for one part of the tier-1 official
    population."""

    from speech_aware_evidence_acquisition.data.lock import (
        asset_dir,
        load_lock,
        lock_entry,
        umbrella_lock_path,
    )
    from speech_aware_evidence_acquisition.data.splits import prefixed, split_identity_hash

    if part not in SPLIT_NAMES:
        raise ValueError(f"unknown part {part!r}; expected one of {sorted(SPLIT_NAMES)}")
    lock = load_lock(umbrella_lock_path())
    carrier_dir = asset_dir(lock, CARRIER, data_root)
    subdir = str(lock_entry(lock, CARRIER)["local_subdir"]).rstrip("/")
    public_dir = carrier_dir / "public"

    population, audit = official_population(
        public_dir, verify_official_rule=verify_official_rule
    )
    population.sort(key=lambda row: int(row["id"]))
    if not 0 < count <= len(population):
        raise ValueError(f"draw count {count} is outside 1..{len(population)}")

    # The draw: uniform without replacement over the WHOLE tier-1 official
    # population, from a population list in ascending manifest id (== sorted
    # query-directory) order, through random.Random(seed).sample. Recorded
    # exactly so the same 500 can be redrawn from the receipt's own fields.
    drawn_ids = set(
        int(row["id"])
        for row in random.Random(seed).sample(population, count)
    )
    if part == "draw":
        selected = [row for row in population if int(row["id"]) in drawn_ids]
    elif part == "remainder":
        selected = [row for row in population if int(row["id"]) not in drawn_ids]
    else:
        selected = list(population)

    root = Path(data_root).resolve()
    items: list[dict[str, object]] = []
    for row in selected:
        sample_id = f"{TIER}:{int(row['id']):06d}"
        media_relpath = f"{subdir}/public/{row['audio_relpath_in_public']}"
        media_path = (root / media_relpath).resolve()
        try:
            media_path.relative_to(root)
        except ValueError as error:
            raise ValueError(f"media path escapes the data root for {sample_id}") from error
        if not media_path.is_file():
            raise ValueError(f"media file is missing for {sample_id}")
        header_seconds = _wav_seconds(media_path, sample_id)
        # The tier manifest records `duration` to three decimals, so a wav
        # whose true length is 2.3125 s is written as 2.312. The roster
        # carries the EXACT header-derived value (frames / sample rate),
        # because the additive D1 media receipt re-derives the same number
        # from the same header and compares to 1e-6; the manifest figure is
        # only cross-checked to its own recorded precision.
        if abs(header_seconds - float(row["audio_seconds"])) > MANIFEST_DURATION_TOLERANCE:
            raise ValueError(
                f"{sample_id}: manifest duration {row['audio_seconds']} disagrees with the "
                f"wav header's {header_seconds:.6f}"
            )
        items.append(
            {
                "audio_seconds": round(header_seconds, 9),
                "audio_sha256": sha256_file(media_path),
                "id": int(row["id"]),
                "key": f"{CARRIER}:{sample_id}",
                "media_relpath": media_relpath,
                "query_idx": int(row["query_idx"]),
                "sample_id": sample_id,
                "tier": TIER,
            }
        )
    items.sort(key=lambda item: str(item["sample_id"]))

    identity = sha256_lines(str(item["key"]) for item in items)
    flight_identity = split_identity_hash(
        prefixed(CARRIER, [str(item["sample_id"]) for item in items])
    )
    by_id = {int(row["id"]): row for row in population}
    domain_counts = dict(
        sorted(Counter(str(by_id[int(item["id"])]["domain"]) for item in items).items())
    )
    speaker_idx_counts = dict(
        sorted(
            Counter(int(by_id[int(item["id"])]["speaker_idx"]) for item in items).items()
        )
    )
    seconds = [float(item["audio_seconds"]) for item in items]

    return {
        "schema": "saea-a2t-agentloop-flight-roster-receipt-v1",
        "study": "speech-aware-evidence-acquisition",
        "carrier": CARRIER,
        "split_name": SPLIT_NAMES[part],
        "split_role": SPLIT_ROLE,
        "part": part,
        "split_identity_hash": identity,
        "split_identity_hash_convention": (
            "sha256 over the LF-joined sorted 'key' values "
            "(audio2tool:<tier>:<id6>, UTF-8, no trailing newline) -- the Audio2Tool "
            "probe-receipt integrity convention"
        ),
        "flight_split_identity_hash": flight_identity,
        "flight_split_identity_hash_convention": (
            "data.splits.split_identity_hash(prefixed('audio2tool', sample_ids)) over "
            "audio2tool/<tier>:<id6> -- the value core.flight.FlightRuntime.preflight "
            "computes at flight time and an exposure row for a FlightRuntime flight of "
            "this roster must carry"
        ),
        "count": len(items),
        "tier_counts": {TIER: len(items)},
        "domain_counts": domain_counts,
        "speaker_idx_counts": speaker_idx_counts,
        "audio_seconds_total": round(sum(seconds), 6),
        "audio_seconds_longest_item": round(max(seconds), 6),
        "audio_seconds_shortest_item": round(min(seconds), 6),
        "audio_seconds_basis": (
            "exact wav header value (frames / sample rate), rounded to 9 decimals; the "
            "tier manifest records duration to 3 decimals and is cross-checked to that "
            "precision (tolerance 1e-3 s)"
        ),
        "media_roster_sha256": canonical_sha256(
            [
                {
                    "sample_id": item["sample_id"],
                    "media_relpath": item["media_relpath"],
                    "audio_sha256": item["audio_sha256"],
                    "audio_seconds": item["audio_seconds"],
                }
                for item in items
            ]
        ),
        "population": {
            "rule": (
                "the released benchmark's own tier-1 population: for each of the "
                f"{POPULATION_COUNT} query_* directories in sorted order, the FIRST "
                "successful speaker, which on the public v1.0 release is the shipped "
                "speaker with the lowest speaker_idx (the manifest row with the lowest id)"
            ),
            "official_code_commit": OFFICIAL_CODE_COMMIT,
            "official_code_receipt": OFFICIAL_CODE_RECEIPT,
            "loader": "audio_benchmark/datasets/tier1_dataset.py::_get_audio_paths",
            "evaluator": (
                "audio_benchmark/evaluation/evaluator.py::BenchmarkEvaluator with "
                "max_speakers_per_query 1 evaluates audio_paths[0]"
            ),
            "query_directories": POPULATION_COUNT,
            "shipped_speakers_per_query": SHIPPED_SPEAKERS_PER_QUERY,
            "population_audio_seconds_total": round(
                sum(float(row["audio_seconds"]) for row in population), 6
            ),
            "documented_exception": {
                "query_dirs": list(CSV_MISMATCH_QUERY_DIRS),
                "explanation": (
                    "generation_results.csv there names 25 speaker filenames, none of "
                    "which is either wav the release ships in that directory; the "
                    "internal loader would resolve no audio and skip the query, while the "
                    "released manifest is unambiguous. The manifest is treated as "
                    "authoritative, so the population is the full 2,146"
                ),
            },
            "official_rule_audit": audit,
            "why_not_max_samples": (
                "the release orders every subset smart_home -> wearables -> smart_car "
                "(its own README), so max_samples 500 over sorted query directories would "
                "be a pure smart_home sample; the draw below is uniform over all 2,146"
            ),
        },
        "selection": {
            "rule": (
                "uniform without replacement over the whole tier-1 official population"
                if part == "draw"
                else (
                    "the complement of the seeded 500-row draw"
                    if part == "remainder"
                    else "the whole tier-1 official population, undrawn"
                )
            ),
            "algorithm": (
                "random.Random(seed).sample(population, count), where population is the "
                "official first-speaker rows in ascending manifest id order (identical to "
                "sorted query-directory order)"
            ),
            "seed": seed,
            "draw_count": count,
            "population_size": len(population),
            "uses_gold_at_runtime": False,
            "uses_test": False,
        },
        "contacts": {"audio": 0, "model": 0, "network": 0, "scorer": 0},
        "status": "PREPARED_NOT_CONTACT_AUTHORITY",
        "items": items,
    }


def _overlap_report(
    items: Sequence[Mapping[str, Any]],
    repo_root: Path,
    *,
    ignore_receipt_stems: Sequence[str] = (),
) -> dict[str, object]:
    """How many of these sample ids are already inside the committed
    Audio2Tool probe-sample receipts and the immutable D1 identity artifact."""

    receipts_dir = Path(repo_root) / "docs" / "receipts" / "probe-samples"
    by_receipt: dict[str, list[str]] = {}
    for path in sorted(receipts_dir.glob("*.json")):
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        if not isinstance(document, Mapping) or document.get("carrier") != CARRIER:
            continue
        if path.stem in ignore_receipt_stems:
            # A previous run of THIS builder wrote that receipt; counting it
            # would make the additive receipt shrink to nothing on a rebuild.
            continue
        known = {
            f"{entry['tier']}:{int(entry['id']):06d}"
            for entry in document.get("items", [])
            if isinstance(entry, Mapping)
        }
        hit = sorted(str(item["sample_id"]) for item in items if item["sample_id"] in known)
        if hit:
            by_receipt[path.stem] = hit
    d1_path = Path(repo_root) / "docs" / "receipts" / "artifacts" / "d1-identity.json"
    d1_ids: set[str] = set()
    if d1_path.is_file():
        document = json.loads(d1_path.read_text(encoding="utf-8"))
        manifest = document["carriers"][CARRIER]["layers"]["media"]["manifest"]
        d1_ids = {str(entry["id"]) for entry in manifest}
    in_d1 = sorted(str(item["sample_id"]) for item in items if item["sample_id"] in d1_ids)
    already = sorted({sample for hits in by_receipt.values() for sample in hits})
    return {
        "already_in_a_probe_sample_receipt": already,
        "already_in_a_probe_sample_receipt_count": len(already),
        "by_receipt": {name: hits for name, hits in by_receipt.items()},
        "already_in_parent_d1": in_d1,
        "already_in_parent_d1_count": len(in_d1),
        "new_probe_receipt_ids_needed": len(items) - len(already),
        "new_d1_supplement_ids_needed": len(items) - len(in_d1),
    }


def build_probe_receipt(
    roster: Mapping[str, Any], repo_root: Path, *, roster_relpath: str, roster_sha256: str
) -> dict[str, object]:
    """The additive probe-sample receipt that puts this roster's NEW sample
    ids inside ``data.audio2tool``'s frozen-receipt universe.

    Why it is additive rather than a copy of the roster. ``data.audio2tool.
    _resolve_items`` builds the carrier's loadable universe from the UNION of
    every committed ``audio2tool`` probe-sample receipt and refuses a sample
    id that appears in two of them. Some of the drawn tier-1 queries are
    already inside an existing receipt (the frozen 400 and the two 104-row
    post-seal AgentLoop scoring receipts), so this receipt carries exactly
    the ids no committed receipt covers yet; the already-covered ids resolve
    through their existing receipt and are listed here for the record.

    The receipt exists for SCORING identity: ``load_official_gold`` and
    ``load_expected_calls`` refuse any sample outside the frozen-receipt
    universe. It opens no gold itself -- it carries identifiers only.
    """

    overlap = _overlap_report(
        roster["items"], repo_root, ignore_receipt_stems=(PROBE_RECEIPT_STEM,)
    )
    already = set(overlap["already_in_a_probe_sample_receipt"])
    items = [
        {
            "id": int(item["id"]),
            "key": str(item["key"]),
            "query_idx": int(item["query_idx"]),
            "tier": str(item["tier"]),
        }
        for item in roster["items"]
        if str(item["sample_id"]) not in already
    ]
    items.sort(key=lambda item: (str(item["tier"]), int(item["id"])))
    identity = sha256_lines(str(item["key"]) for item in items)
    return {
        "probe": PROBE_RECEIPT_STEM,
        "carrier": CARRIER,
        "split_role": SPLIT_ROLE,
        "items": items,
        "n_items": len(items),
        "seed": DRAW_SEED,
        "split_identity_hash": identity,
        "split_identity_hash_basis": (
            "sha256 over LF-joined sorted receipt item key values; the Audio2Tool "
            "probe-receipt integrity convention data.audio2tool._verify_receipt recomputes"
        ),
        "strata_counts": {TIER: len(items)},
        "source_roster": roster_relpath,
        "source_roster_sha256": roster_sha256,
        "source_roster_count": int(roster["count"]),
        "source_roster_split_identity_hash": str(roster["split_identity_hash"]),
        "already_covered_by_other_receipts": {
            name: hits for name, hits in overlap["by_receipt"].items()
        },
        "design": (
            "Additive identity receipt for the tier-1 official-population roster: the "
            "sample ids of that roster that no committed audio2tool probe-sample receipt "
            "covers yet. Identifiers only -- no gold, expected call, task text, media "
            "path, annotation, output or score. It grants no contact authority; the "
            "preregistration and the exposure ledger do that."
        ),
        "authority": (
            "docs/readiness/2026-09-04-a2t-tier1-official-population-v1-preregistration.md "
            "fixes these discovery identities before model contact."
        ),
        "target_gold_opened_before_receipt": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--part", choices=sorted(SPLIT_NAMES), default="draw")
    parser.add_argument("--seed", type=int, default=DRAW_SEED)
    parser.add_argument("--count", type=int, default=DRAW_COUNT)
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--write", action="store_true")
    parser.add_argument(
        "--no-verify-official-rule",
        dest="verify_official_rule",
        action="store_false",
        help="skip the generation_results.csv replay (the receipt then says so)",
    )
    parser.add_argument(
        "--probe-receipt-out",
        type=Path,
        default=None,
        help=(
            "also emit the additive probe-sample receipt that puts this roster's NEW "
            "sample ids inside data.audio2tool's frozen-receipt universe (scoring "
            "identity); only meaningful for --part draw"
        ),
    )
    parser.set_defaults(verify_official_rule=True)
    args = parser.parse_args()

    root = args.data_root
    if root is None:
        value = os.environ.get("SPEECHRL_DATA_DIR")
        if not value:
            raise SystemExit("--data-root or SPEECHRL_DATA_DIR is required")
        root = Path(value)
    output = Path(args.output) if args.output else OUTPUT_DIR / DEFAULT_OUTPUTS[args.part]

    roster = build_roster(
        data_root=root,
        part=args.part,
        seed=args.seed,
        count=args.count,
        verify_official_rule=args.verify_official_rule,
    )
    payload = json.dumps(roster, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    roster_sha256 = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    if args.write:
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_suffix(output.suffix + ".tmp")
        temporary.write_text(payload, encoding="utf-8", newline="\n")
        temporary.replace(output)
        roster_sha256 = sha256_file(output)
    probe_receipt_summary: dict[str, object] | None = None
    if args.probe_receipt_out is not None:
        try:
            roster_relpath = str(output.resolve().relative_to(REPO)).replace("\\", "/")
        except ValueError:
            roster_relpath = str(output)
        receipt = build_probe_receipt(
            roster, REPO, roster_relpath=roster_relpath, roster_sha256=roster_sha256
        )
        receipt_payload = (
            json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        )
        receipt_path = Path(args.probe_receipt_out)
        if args.write:
            receipt_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = receipt_path.with_suffix(receipt_path.suffix + ".tmp")
            temporary.write_text(receipt_payload, encoding="utf-8", newline="\n")
            temporary.replace(receipt_path)
        probe_receipt_summary = {
            "n_items": receipt["n_items"],
            "output": str(receipt_path),
            "output_sha256": (
                sha256_file(receipt_path)
                if args.write
                else hashlib.sha256(receipt_payload.encode("utf-8")).hexdigest()
            ),
            "split_identity_hash": receipt["split_identity_hash"],
        }
    print(
        json.dumps(
            {
                "audio_seconds_longest_item": roster["audio_seconds_longest_item"],
                "audio_seconds_total": roster["audio_seconds_total"],
                "count": roster["count"],
                "domain_counts": roster["domain_counts"],
                "flight_split_identity_hash": roster["flight_split_identity_hash"],
                "output": str(output),
                "output_sha256": roster_sha256,
                "overlap": _overlap_report(
                    roster["items"], REPO, ignore_receipt_stems=(PROBE_RECEIPT_STEM,)
                ),
                "probe_receipt": probe_receipt_summary,
                "part": roster["part"],
                "split_identity_hash": roster["split_identity_hash"],
                "split_name": roster["split_name"],
                "written": bool(args.write),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
