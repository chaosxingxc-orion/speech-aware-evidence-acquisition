#!/usr/bin/env python3
"""Build a tiers-2/5/8 Audio2Tool roster drawn the RELEASE's own way.

Why this roster exists
----------------------
``docs/readiness/2026-09-04-a2t-tier1-official-population-v1-verdict.md``
bought resolution on tier 1 by replacing the frozen 400's 50 stratified rows
with 500 queries of the release's own tier-1 population. On the frozen 400
(n = 50 per tier, CI90 about +/-11 pp) three more tiers came out "not
aligned" but inside a noise band that cannot separate the owner's 3-point
rule: tier 2 74.0 against a published 84.6, tier 5 78.0 against 90.6, tier 8
34.0 against 41.7. This roster repeats the tier-1 recipe, unchanged, on
exactly those three tiers at n = 500 each.

The official population rule, derived from the pinned code
-----------------------------------------------------------
Source: ``github.com/audio2tool/Audio2Tool`` at commit
``b9d5383ca30945fbafb965a04bea40117e1e8a82`` (MIT); clone receipt
``docs/receipts/environments/audio2tool-official-code.json``.

Per tier the released loader walks ``sorted(data_dir.glob("query_*"))`` and
keeps, per query directory, the first audio its ``_get_audio_paths`` resolves;
``BenchmarkEvaluator`` with ``max_speakers_per_query 1`` evaluates
``audio_paths[0]``. The three tiers spell that differently and the
differences are recorded per tier rather than smoothed over:

``tier2_parametric`` (``tier2_dataset.py``) is the tier-1 spelling exactly:
the rows of ``generation_results.csv`` in file order whose ``success`` is
true, resolving each row's ``audio_path`` and falling back to ``query_dir /
Path(audio_path).name`` when the CSV's absolute path is stale. The released
CSVs carry the authors' internal ``/data2/...`` paths, so on any public copy
the fallback is the branch that fires.

``tier5_needle`` (``tier5_dataset.py``) is the SAME walk with the fallback
branch MISSING: it appends only when ``Path(audio_path).exists()``. Because
``results_path.exists()`` is true for every tier-5 query directory, the
``else`` glob never runs either, so a literal replay of that loader against
the public release resolves ZERO audio paths and ``_load_query`` returns
``None`` for all 2,146 directories -- the released tier-5 loader cannot read
the released tier-5 dataset at all. This builder therefore applies the
tier-1/tier-2 spelling (the same walk WITH the documented fallback) and
records BOTH replays in the receipt: the literal one, which resolves
nothing, and the fallback one, which agrees with the manifest-first rule on
all 2,146 directories.

``tier8_intent_blending`` (``tier8_dataset.py``) has no speaker choice to
make: each query directory ships exactly one ``mixed.wav`` (foreground and
background intents mixed into one recording), there is no
``generation_results.csv``, and the manifest rows carry ``speaker_idx``
``null``. The loader reads ``query_dir / "mixed.wav"`` directly, so the
file-order rule resolves to that single file and the population is the 821
query directories themselves.

For tiers 2 and 5 the public v1.0 release ships exactly TWO of the up-to-25
generated speakers per query directory, and the tier manifest carries one
item per shipped (query, speaker) recording ordered by query directory and
then by ``speaker_idx``. Applying the loader rule to the released bytes
therefore selects the shipped speaker with the LOWEST ``speaker_idx``, which
is the manifest item with the lowest ``id`` in that directory. This builder
verifies that equivalence directory by directory rather than assuming it
(``--verify-official-rule``, on by default): 3,160 and 2,146 agreements,
zero disagreements, zero unresolved directories -- no tier-2 or tier-5
counterpart of tier 1's one documented ``query_01982`` exception exists.

``max_samples`` is deliberately NOT used to reach 500. The release orders
every subset ``smart_home -> wearables -> smart_car`` (its own README says
so), so the first 500 sorted query directories would be a pure
``smart_home`` sample on tiers 2 and 5. The draw below is uniform without
replacement over each tier's whole population.

Contact surface
---------------
Label-free and contact-free. The tier manifests are read for identity and
media facts ONLY (``id``, ``query_idx``, ``path``, ``duration``,
``speaker_idx``, and ``domain``/``category`` for the aggregate stratum
counts the preregistration and the verdict report); ``query``,
``tool_name``, ``expected_tool_call``, ``extracted_params``,
``additional_tool_calls``, ``background_*``, ``functions`` and
``instruction`` are never read. ``generation_results.csv`` is read for
``speaker_idx``/``audio_path``/``success`` only. WAV bytes are hashed and
their container headers read; no audio is decoded. No model, network,
tokenizer or scorer contact.

Usage::

    python scripts/build_a2t_tier258_official_population_roster.py           # print only
    python scripts/build_a2t_tier258_official_population_roster.py --write
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
TIERS = ("tier2_parametric", "tier5_needle", "tier8_intent_blending")
SPLIT_ROLE = "discovery"
DRAW_SEED = 20260803
DRAW_COUNT_PER_TIER = 500
POPULATION_COUNTS = {
    "tier2_parametric": 3160,
    "tier5_needle": 2146,
    "tier8_intent_blending": 821,
}
SHIPPED_SPEAKERS_PER_QUERY = {
    "tier2_parametric": 2,
    "tier5_needle": 2,
    "tier8_intent_blending": 1,
}
# The single wav every tier-8 query directory ships; there is no speaker
# choice and no generation_results.csv beside it.
TIER8_WAV_NAME = "mixed.wav"
MANIFEST_DURATION_TOLERANCE = 1e-3
SPLIT_NAME = "A2T-TIER258-OFFICIAL-POP-1500"
PROBE_RECEIPT_STEM = "a2t-tier258-official-population-1500"
OFFICIAL_CODE_COMMIT = "b9d5383ca30945fbafb965a04bea40117e1e8a82"
OFFICIAL_CODE_RECEIPT = "docs/receipts/environments/audio2tool-official-code.json"
OFFICIAL_LOADERS = {
    "tier2_parametric": "audio_benchmark/datasets/tier2_dataset.py::_get_audio_paths",
    "tier5_needle": "audio_benchmark/datasets/tier5_dataset.py::_get_audio_paths",
    "tier8_intent_blending": "audio_benchmark/datasets/tier8_dataset.py::_load_query",
}
OUTPUT_DIR = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-04-a2t-tier258-official-population-roster"
)
DEFAULT_OUTPUT = "flight-roster-receipt.json"


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


def _validate_relpath(relpath: object, tier: str, context: str) -> str:
    if not isinstance(relpath, str) or not relpath:
        raise ValueError(f"{context}: audio path must be a non-empty string")
    if "\\" in relpath or ":" in relpath or relpath.startswith("/"):
        raise ValueError(f"{context}: audio path {relpath!r} is not a plain relative path")
    pure = PurePosixPath(relpath)
    if any(part in ("", ".", "..") for part in pure.parts):
        raise ValueError(f"{context}: audio path {relpath!r} escapes its tier directory")
    if not relpath.endswith(".wav"):
        raise ValueError(f"{context}: audio path {relpath!r} is not a .wav file")
    parts = relpath.split("/")
    if len(parts) != 3 or parts[0] != f"{tier}_audios" or not parts[1].startswith("query_"):
        raise ValueError(f"{context}: unexpected {tier} audio layout: {relpath!r}")
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
    public_dir: Path, tier: str, *, verify_official_rule: bool = True
) -> tuple[list[dict[str, object]], dict[str, object]]:
    """One tier's released population: one manifest row per query directory,
    the first shipped recording, in sorted query-directory order.

    Returns ``(rows, audit)`` where ``audit`` records how the manifest-first
    rule compared against a direct replay of the released loader's own walk.
    """

    manifest_path = public_dir / f"{tier}_data" / f"{tier}.json"
    audios_dir = public_dir / f"{tier}_audios"
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
        ):
            raise ValueError(f"tier manifest item is malformed: id={entry_id!r}")
        # tier8 rows carry speaker_idx null: the mixed recording has no single
        # speaker. Every other tier must carry a non-negative integer.
        if tier == "tier8_intent_blending":
            if speaker_idx is not None:
                raise ValueError(
                    f"{tier}:{entry_id:06d} carries speaker_idx {speaker_idx!r}; the "
                    "released tier-8 rows carry null because the recording is a mix"
                )
        elif isinstance(speaker_idx, bool) or not isinstance(speaker_idx, int) or speaker_idx < 0:
            raise ValueError(f"tier manifest item is malformed: id={entry_id!r}")
        seen_ids.add(entry_id)
        relpath = _validate_relpath(entry.get("path"), tier, f"{tier}:{entry_id:06d}")
        parts = relpath.split("/")
        domain = entry.get("domain")
        category = entry.get("category")
        if not isinstance(domain, str) or not domain:
            raise ValueError(f"tier manifest item {entry_id} has no domain")
        by_query_dir.setdefault(parts[1], []).append(
            {
                "id": entry_id,
                "query_idx": query_idx,
                "speaker_idx": speaker_idx,
                "audio_relpath_in_public": relpath,
                "audio_seconds": _seconds(entry.get("duration"), f"{tier}:{entry_id:06d}"),
                "domain": domain,
                "category": category if isinstance(category, str) else "",
                "wav_name": parts[2],
                "query_dir": parts[1],
                "tier": tier,
            }
        )

    on_disk_dirs = sorted(
        path.name
        for path in audios_dir.iterdir()
        if path.is_dir() and path.name.startswith("query_")
    )
    if on_disk_dirs != sorted(by_query_dir):
        raise ValueError(
            f"{tier}: the tier manifest and the on-disk query directories disagree "
            f"({len(by_query_dir)} manifest vs {len(on_disk_dirs)} on disk)"
        )
    if len(by_query_dir) != POPULATION_COUNTS[tier]:
        raise ValueError(
            f"expected {POPULATION_COUNTS[tier]} {tier} query directories, "
            f"found {len(by_query_dir)}"
        )

    shipped_per_query = SHIPPED_SPEAKERS_PER_QUERY[tier]
    rows: list[dict[str, object]] = []
    for query_dir in on_disk_dirs:
        shipped = sorted(by_query_dir[query_dir], key=lambda row: int(row["id"]))
        if len(shipped) != shipped_per_query:
            raise ValueError(
                f"{tier}/{query_dir}: the release ships {len(shipped)} recordings, "
                f"expected {shipped_per_query}"
            )
        first = shipped[0]
        if tier != "tier8_intent_blending" and int(first["speaker_idx"]) != min(
            int(row["speaker_idx"]) for row in shipped
        ):
            raise ValueError(
                f"{tier}/{query_dir}: the lowest-id manifest row is not the lowest "
                "speaker_idx; the first-speaker rule cannot be resolved from the "
                "manifest alone"
            )
        if tier == "tier8_intent_blending" and str(first["wav_name"]) != TIER8_WAV_NAME:
            raise ValueError(
                f"{tier}/{query_dir}: expected the single {TIER8_WAV_NAME}, found "
                f"{first['wav_name']!r}"
            )
        if len({int(row["query_idx"]) for row in shipped}) != 1:
            raise ValueError(f"{tier}/{query_dir}: shipped rows disagree on query_idx")
        rows.append(first)

    audit = (
        _verify_official_rule(audios_dir, tier, rows)
        if verify_official_rule
        else {"performed": False, "reason": "--no-verify-official-rule"}
    )
    return rows, audit


def _verify_official_rule(
    audios_dir: Path, tier: str, rows: Sequence[Mapping[str, object]]
) -> dict[str, object]:
    """Replay the released loader's own audio walk and compare its first pick
    with this builder's manifest-first pick.

    tier8 has no walk to replay -- the loader names ``mixed.wav`` -- so the
    replay there is an existence check on that exact filename. For tiers 2
    and 5 the walk is the tier-1 spelling; tier 5's own loader omits the
    stale-path fallback, so BOTH replays are recorded (see the module
    docstring).
    """

    if tier == "tier8_intent_blending":
        missing = [
            str(row["query_dir"])
            for row in rows
            if not (audios_dir / str(row["query_dir"]) / TIER8_WAV_NAME).is_file()
        ]
        if missing:
            raise ValueError(
                f"{tier}: {len(missing)} query directories ship no {TIER8_WAV_NAME}: "
                f"{missing[:3]}"
            )
        return {
            "performed": True,
            "method": (
                "audio_benchmark/datasets/tier8_dataset.py::_load_query names "
                "query_dir/'mixed.wav' directly at commit " + OFFICIAL_CODE_COMMIT
                + "; there is no generation_results.csv, no speaker choice and no "
                "file-order ambiguity to resolve"
            ),
            "query_directories": len(rows),
            "agreements": len(rows),
            "disagreements": 0,
            "csv_rows_marked_unsuccessful": 0,
            "query_directories_whose_csv_resolves_no_shipped_wav": [],
            "how_the_file_order_rule_resolved": (
                "trivially: each of the 821 query directories ships exactly one "
                "recording, mixed.wav, and the manifest carries exactly one row for it "
                "with speaker_idx null. 'First successful speaker' therefore selects "
                "that file for every directory, and the released manifest and the "
                "released loader cannot disagree"
            ),
        }

    agreements = 0
    unresolved: list[str] = []
    disagreements: list[dict[str, object]] = []
    success_false_rows = 0
    literal_resolutions = 0
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
                    if Path(audio_path).is_file():
                        # the tier-5 loader's ONLY branch; on a public copy the
                        # authors' internal /data2/... path never exists
                        literal_resolutions += 1
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
            f"{tier}: the released loader's first pick disagrees with the manifest-first "
            f"pick on {len(disagreements)} query directories: {disagreements[:3]}"
        )
    if unresolved:
        raise ValueError(
            f"{tier}: {len(unresolved)} query directories resolve no shipped wav under "
            f"the documented fallback: {unresolved[:3]}"
        )
    audit = {
        "performed": True,
        "method": (
            f"replay of {OFFICIAL_LOADERS[tier]} (only_successful=True, "
            "speakers_per_query=1, stale-absolute-path fallback to query_dir/<basename>) "
            "at commit " + OFFICIAL_CODE_COMMIT
        ),
        "query_directories": len(rows),
        "agreements": agreements,
        "disagreements": 0,
        "csv_rows_marked_unsuccessful": success_false_rows,
        "query_directories_whose_csv_resolves_no_shipped_wav": [],
        "note": (
            "the released generation_results.csv files carry the authors' internal "
            "/data2/... absolute paths, so the loader's stale-path fallback is the "
            "branch that fires on any public copy; on every directory it selects "
            "exactly the manifest's lowest-id (lowest speaker_idx) row"
        ),
    }
    if tier == "tier5_needle":
        audit["literal_loader_replay"] = {
            "rows_resolved": literal_resolutions,
            "finding": (
                "tier5_dataset.py::_get_audio_paths appends an audio path ONLY when "
                "Path(audio_path).exists(); it has no query_dir/<basename> fallback, and "
                "because generation_results.csv exists in every tier-5 query directory "
                "the else-branch glob never runs either. Replayed literally against the "
                "public release it resolves ZERO audio paths, so _load_query returns None "
                "for all 2,146 directories and the released tier-5 loader loads an EMPTY "
                "dataset. This builder therefore applies the tier-1/tier-2 spelling of "
                "the same walk (identical except for the documented fallback), which is "
                "recorded as a deviation in the preregistration rather than silently "
                "assumed"
            ),
        }
    return audit


def build_roster(
    *,
    data_root: Path,
    seed: int = DRAW_SEED,
    count_per_tier: int = DRAW_COUNT_PER_TIER,
    verify_official_rule: bool = True,
) -> dict[str, object]:
    """The flight-roster receipt: ``count_per_tier`` queries from each of the
    three tiers' released populations, one receipt, one split identity."""

    from speech_aware_evidence_acquisition.data.lock import (
        asset_dir,
        load_lock,
        lock_entry,
        umbrella_lock_path,
    )
    from speech_aware_evidence_acquisition.data.splits import prefixed, split_identity_hash

    lock = load_lock(umbrella_lock_path())
    carrier_dir = asset_dir(lock, CARRIER, data_root)
    subdir = str(lock_entry(lock, CARRIER)["local_subdir"]).rstrip("/")
    public_dir = carrier_dir / "public"

    root = Path(data_root).resolve()
    items: list[dict[str, object]] = []
    per_tier: dict[str, dict[str, object]] = {}
    facts: dict[str, dict[str, object]] = {}
    for tier in TIERS:
        population, audit = official_population(
            public_dir, tier, verify_official_rule=verify_official_rule
        )
        population.sort(key=lambda row: int(row["id"]))
        if not 0 < count_per_tier <= len(population):
            raise ValueError(
                f"{tier}: draw count {count_per_tier} is outside 1..{len(population)}"
            )
        # The draw: uniform without replacement over the WHOLE tier population,
        # from a population list in ascending manifest id (== sorted
        # query-directory) order, through random.Random(seed).sample -- the same
        # call, with the same seed, the tier-1 flight used. Each tier draws from
        # its own freshly seeded generator so a tier's draw does not depend on
        # the tiers built before it.
        drawn_ids = {
            int(row["id"]) for row in random.Random(seed).sample(population, count_per_tier)
        }
        selected = [row for row in population if int(row["id"]) in drawn_ids]
        tier_items: list[dict[str, object]] = []
        for row in selected:
            sample_id = f"{tier}:{int(row['id']):06d}"
            media_relpath = f"{subdir}/public/{row['audio_relpath_in_public']}"
            media_path = (root / media_relpath).resolve()
            try:
                media_path.relative_to(root)
            except ValueError as error:
                raise ValueError(f"media path escapes the data root for {sample_id}") from error
            if not media_path.is_file():
                raise ValueError(f"media file is missing for {sample_id}")
            header_seconds = _wav_seconds(media_path, sample_id)
            # The tier manifests record `duration` to three decimals, so the
            # roster carries the EXACT header-derived value (frames / sample
            # rate) and cross-checks the manifest figure only to its own
            # recorded precision; the additive D1 media receipt re-derives the
            # same header number and compares to 1e-6.
            if abs(header_seconds - float(row["audio_seconds"])) > MANIFEST_DURATION_TOLERANCE:
                raise ValueError(
                    f"{sample_id}: manifest duration {row['audio_seconds']} disagrees "
                    f"with the wav header's {header_seconds:.6f}"
                )
            tier_items.append(
                {
                    "audio_seconds": round(header_seconds, 9),
                    "audio_sha256": sha256_file(media_path),
                    "id": int(row["id"]),
                    "key": f"{CARRIER}:{sample_id}",
                    "media_relpath": media_relpath,
                    "query_idx": int(row["query_idx"]),
                    "sample_id": sample_id,
                    "tier": tier,
                }
            )
        items.extend(tier_items)
        by_id = {int(row["id"]): row for row in population}
        seconds = [float(item["audio_seconds"]) for item in tier_items]
        facts[tier] = {"by_id": by_id, "population": population}
        per_tier[tier] = {
            "count": len(tier_items),
            "population_size": len(population),
            "population_domain_counts": dict(
                sorted(Counter(str(row["domain"]) for row in population).items())
            ),
            "domain_counts": dict(
                sorted(
                    Counter(
                        str(by_id[int(item["id"])]["domain"]) for item in tier_items
                    ).items()
                )
            ),
            "speaker_idx_counts": dict(
                sorted(
                    Counter(
                        str(by_id[int(item["id"])]["speaker_idx"]) for item in tier_items
                    ).items()
                )
            ),
            "audio_seconds_total": round(sum(seconds), 6),
            "audio_seconds_longest_item": round(max(seconds), 6),
            "audio_seconds_shortest_item": round(min(seconds), 6),
            "population_audio_seconds_total": round(
                sum(float(row["audio_seconds"]) for row in population), 6
            ),
            "shipped_recordings_per_query": SHIPPED_SPEAKERS_PER_QUERY[tier],
            "official_loader": OFFICIAL_LOADERS[tier],
            "official_rule_audit": audit,
        }

    items.sort(key=lambda item: str(item["sample_id"]))
    identity = sha256_lines(str(item["key"]) for item in items)
    flight_identity = split_identity_hash(
        prefixed(CARRIER, [str(item["sample_id"]) for item in items])
    )
    seconds_all = [float(item["audio_seconds"]) for item in items]
    return {
        "schema": "saea-a2t-agentloop-flight-roster-receipt-v1",
        "study": "speech-aware-evidence-acquisition",
        "carrier": CARRIER,
        "split_name": SPLIT_NAME,
        "split_role": SPLIT_ROLE,
        "part": "draw",
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
        "tier_counts": {tier: per_tier[tier]["count"] for tier in TIERS},
        "strata": "tier",
        "audio_seconds_total": round(sum(seconds_all), 6),
        "audio_seconds_longest_item": round(max(seconds_all), 6),
        "audio_seconds_shortest_item": round(min(seconds_all), 6),
        "audio_seconds_basis": (
            "exact wav header value (frames / sample rate), rounded to 9 decimals; the "
            "tier manifests record duration to 3 decimals and are cross-checked to that "
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
        "per_tier": {tier: per_tier[tier] for tier in TIERS},
        "population": {
            "rule": (
                "each tier's released population: for every query_* directory in sorted "
                "order, the first recording the released loader resolves. On tiers 2 and "
                "5 that is the shipped speaker with the lowest speaker_idx (the manifest "
                "row with the lowest id); on tier 8 it is the single mixed.wav the "
                "directory ships, whose manifest row carries speaker_idx null"
            ),
            "official_code_commit": OFFICIAL_CODE_COMMIT,
            "official_code_receipt": OFFICIAL_CODE_RECEIPT,
            "evaluator": (
                "audio_benchmark/evaluation/evaluator.py::BenchmarkEvaluator with "
                "max_speakers_per_query 1 evaluates audio_paths[0]"
            ),
            "why_not_max_samples": (
                "the release orders every subset smart_home -> wearables -> smart_car "
                "(its own README), so max_samples 500 over sorted query directories "
                "would be a near-pure smart_home sample on tiers 2 and 5; each tier's "
                "draw below is uniform over its whole population"
            ),
        },
        "selection": {
            "rule": "uniform without replacement over each tier's whole released population",
            "algorithm": (
                "random.Random(seed).sample(population, count_per_tier) per tier, where "
                "population is that tier's official first-recording rows in ascending "
                "manifest id order (identical to sorted query-directory order); each "
                "tier uses its own freshly seeded generator"
            ),
            "seed": seed,
            "draw_count_per_tier": count_per_tier,
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
        "per_tier_already_in_a_probe_sample_receipt": dict(
            sorted(Counter(sample.split(":")[0] for sample in already).items())
        ),
    }


def build_probe_receipt(
    roster: Mapping[str, Any], repo_root: Path, *, roster_relpath: str, roster_sha256: str
) -> dict[str, object]:
    """The additive probe-sample receipt that puts this roster's NEW sample
    ids inside ``data.audio2tool``'s frozen-receipt universe.

    Additive rather than a copy of the roster: ``data.audio2tool.
    _resolve_items`` builds the carrier's loadable universe from the UNION of
    every committed ``audio2tool`` probe-sample receipt and refuses a sample
    id that appears in two of them, so this receipt carries exactly the ids
    no committed receipt covers yet. The receipt exists for SCORING identity
    -- ``load_official_gold`` and ``load_expected_calls`` refuse any sample
    outside the frozen-receipt universe -- and opens no gold itself.
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
        "strata_counts": dict(
            sorted(Counter(str(item["tier"]) for item in items).items())
        ),
        "source_roster": roster_relpath,
        "source_roster_sha256": roster_sha256,
        "source_roster_count": int(roster["count"]),
        "source_roster_split_identity_hash": str(roster["split_identity_hash"]),
        "already_covered_by_other_receipts": {
            name: hits for name, hits in overlap["by_receipt"].items()
        },
        "design": (
            "Additive identity receipt for the tiers-2/5/8 official-population roster: "
            "the sample ids of that roster that no committed audio2tool probe-sample "
            "receipt covers yet. Identifiers only -- no gold, expected call, task text, "
            "media path, annotation, output or score. It grants no contact authority; "
            "the preregistration and the exposure ledger do that."
        ),
        "authority": (
            "docs/readiness/2026-09-04-a2t-tier258-official-population-v1-"
            "preregistration.md fixes these discovery identities before model contact."
        ),
        "target_gold_opened_before_receipt": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=DRAW_SEED)
    parser.add_argument("--count-per-tier", type=int, default=DRAW_COUNT_PER_TIER)
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--write", action="store_true")
    parser.add_argument(
        "--no-verify-official-rule",
        dest="verify_official_rule",
        action="store_false",
        help="skip the released-loader replay (the receipt then says so)",
    )
    parser.set_defaults(verify_official_rule=True)
    parser.add_argument(
        "--probe-receipt-out",
        type=Path,
        default=None,
        help=(
            "also emit the additive probe-sample receipt that puts this roster's NEW "
            "sample ids inside data.audio2tool's frozen-receipt universe (scoring "
            "identity)"
        ),
    )
    args = parser.parse_args()

    root = args.data_root
    if root is None:
        value = os.environ.get("SPEECHRL_DATA_DIR")
        if not value:
            raise SystemExit("--data-root or SPEECHRL_DATA_DIR is required")
        root = Path(value)
    output = Path(args.output) if args.output else OUTPUT_DIR / DEFAULT_OUTPUT

    roster = build_roster(
        data_root=root,
        seed=args.seed,
        count_per_tier=args.count_per_tier,
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
            "strata_counts": receipt["strata_counts"],
        }
    print(
        json.dumps(
            {
                "audio_seconds_longest_item": roster["audio_seconds_longest_item"],
                "audio_seconds_total": roster["audio_seconds_total"],
                "count": roster["count"],
                "flight_split_identity_hash": roster["flight_split_identity_hash"],
                "output": str(output),
                "output_sha256": roster_sha256,
                "overlap": _overlap_report(
                    roster["items"], REPO, ignore_receipt_stems=(PROBE_RECEIPT_STEM,)
                ),
                "per_tier": {
                    tier: {
                        key: value
                        for key, value in roster["per_tier"][tier].items()
                        if key != "official_rule_audit"
                    }
                    for tier in TIERS
                },
                "probe_receipt": probe_receipt_summary,
                "split_identity_hash": roster["split_identity_hash"],
                "split_name": roster["split_name"],
                "tier_counts": roster["tier_counts"],
                "written": bool(args.write),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
