#!/usr/bin/env python3
"""Freeze ``SLURP-TEST-FULL-13078-V1``: the complete official SLURP test split.

Owner decisions 99 and 107 of 2026-09-22/23
(``docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md``): exactly
ONE complete official SLURP test-split read happens at the end of Stage 3, and
its preparations are registered and built ahead of time so the read waits on
nothing. Section 2 of the one-shot read protocol draft
(``docs/readiness/2026-09-19-slurp-test-split-one-read-protocol-v1-draft.md``,
commit 16ed5b3f) fixes the roster this script freezes: the entire split, both
microphone channels, no subsampling, no stratified draw, no filtering, no
reserve.

**This script registers nothing and authorises nothing.** It freezes an
identity receipt plus a disjointness proof. Reading the frozen roster still
requires the owner allowance of ``contracts.plan.require_owner_split_allowance``
(decision 108, pending), and every preparation still needs its own
countersigned exposure row.

What is read, and what is never read
------------------------------------
Identity only. The sample ids come from ``rails.knowledge_build
.slurp_split_sample_ids``, the identity-only enumerator that reads ONLY
``slurp_id`` and ``recordings[].file`` from the governed jsonl and never
``scenario`` / ``action`` / ``entities`` / ``tokens`` / ``sentence`` (the SLU
gold layer), and they are cross-checked against the already-frozen committed
receipt ``docs/receipts/knowledge/slurp-split-identity.json``. Durations and
sample rates come from the FLAC container header (``soundfile.info``); no audio
sample is decoded and no media byte is rewritten. No utterance text, transcript,
gold label, intent or slot annotation of any row is opened, printed or stored.

Strata are the MICROPHONE CHANNEL only -- ``headset`` (the ``-headset`` id
suffix) and ``far-field``. The protocol draft's section 2.2 also mentions a
per-scenario breakdown; scenario is a gold field of the test split, so it is
deliberately NOT used here and the per-stratum table is channel-only.

The freeze is take-all: ``core.roster.freeze_roster`` is given a per-stratum
quota equal to each stratum's full capacity, so every candidate is selected,
``excluded_count`` is 0 and the seed (20260923) advances the shared rng without
ever changing the outcome. The seed is recorded because the receipt schema
carries one, not because anything is sampled.

MODEL-FREE: no model, tokenizer, encoder, ASR, scorer, server, network or GPU is
reached; the offline guard is armed before the first input is opened. CPU work is
capped at 8 workers (standing rule while a GPU campaign flies).

Run in WSL2::

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<repo>:<repo>/src \\
      python scripts/build_slurp_test_full_roster.py --write
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Iterable, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.analysis.dev100_reviewer_audit import (  # noqa: E402
    arm_offline_guard,
)
from speech_aware_evidence_acquisition.contracts import _parse_ledger_tables  # noqa: E402
from speech_aware_evidence_acquisition.core.roster import (  # noqa: E402
    EVALUATION_ROSTER_ROLE,
    RosterItem,
    canonical_receipt_bytes,
    freeze_roster,
    verify_roster,
    write_roster,
)
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.data.slurp import _governed_roots  # noqa: E402
from speech_aware_evidence_acquisition.e0.d1_identity import (  # noqa: E402
    _confined_media_path,
    _probe_speech_media,
)
from speech_aware_evidence_acquisition.rails.knowledge_build import (  # noqa: E402
    slurp_split_sample_ids,
)

CARRIER = "slurp"
SPLIT = "test"
ROSTER_ID = "SLURP-TEST-FULL-13078-V1"
SPLIT_NAME = "TEST-FULL"
#: The machine role a final-reporting read carries (protocol section 6.3: a role
#: "named for what it is", never a reuse of ``dev``). Admitted by
#: ``contracts.plan`` only behind a live owner allowance.
SPLIT_ROLE = "final-report"
SEED = 20260923
EXPECTED_RECORDINGS = 13078
EXPECTED_UTTERANCES = 2974
HEADSET_SUFFIX = "-headset"
HEADSET_STRATUM = "headset"
FAR_FIELD_STRATUM = "far-field"
WORKERS = 8  # standing rule: <= 8 CPU workers while a GPU campaign may fly

ROSTER_RELPATH = "docs/receipts/rosters/slurp-test-full-13078-v1.json"
CHECK_DIR = (
    "docs/checks/speech-aware-evidence-acquisition/2026-09-23-slurp-test-roster"
)
DISJOINTNESS_NAME = "disjointness.json"
SPLIT_IDENTITY_RELPATH = "docs/receipts/knowledge/slurp-split-identity.json"
EXPOSURE_LEDGER_RELPATH = "docs/exposure-ledger.md"
PROTOCOL_RELPATH = (
    "docs/readiness/2026-09-19-slurp-test-split-one-read-protocol-v1-draft.md"
)
AUTHORITY = (
    "docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md owner "
    "decisions 99 (2026-09-22) and 107 (2026-09-23); roster shape from "
    + PROTOCOL_RELPATH
    + " section 2"
)
GENERATOR = "scripts/build_slurp_test_full_roster.py"

#: Where the disjointness proof looks for id sets, beyond the committed roster
#: and probe-sample receipts. Knowledge stores and exemplar pools keep their
#: ``source_sample_ids`` in the snapshot document under the data root.
KNOWLEDGE_GLOB = "knowledge/{carrier}/**/snapshot.json"


class RosterBuildError(RuntimeError):
    """The roster cannot be frozen from these inputs -- fail closed."""


def canonical_sha256(document: object) -> str:
    return hashlib.sha256(
        json.dumps(
            document, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, document: object) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(
            json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        )
    return sha256_file(path)


def stratum_of(sample_id: str) -> str:
    """The MICROPHONE CHANNEL of one recording -- never a gold field."""

    return HEADSET_STRATUM if sample_id.endswith(HEADSET_SUFFIX) else FAR_FIELD_STRATUM


def utterance_id_of(sample_id: str) -> str:
    """``slurp:test:000123`` from ``slurp:test:000123:audio-...``."""

    parts = sample_id.split(":")
    if len(parts) != 4:
        raise RosterBuildError(f"malformed SLURP sample id {sample_id!r}")
    return ":".join(parts[:3])


def utterance_number_of(sample_id: str) -> str:
    """The split-free SLURP prompt number, for the prompt-level overlap pass.

    A prompt-level collision between two splits would be invisible at recording
    level and would not show up in a ``slurp:test:`` vs ``slurp:train:``
    comparison either, because the split token differs. SLURP's ``slurp_id`` is
    the prompt identity, so the bare number is what has to be compared.
    """

    parts = sample_id.split(":")
    if len(parts) != 4:
        raise RosterBuildError(f"malformed SLURP sample id {sample_id!r}")
    return parts[2]


def _load_json(path: Path, label: str) -> object:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RosterBuildError(f"cannot read {label} ({path}): {error}") from error


def _verify_governed_metadata(lock: Mapping[str, object], root: Path) -> dict[str, object]:
    """Re-measure the governed ``test.jsonl`` against the umbrella lock's pin.

    Only the file's BYTES are hashed here; not one line is parsed.
    """

    entry = None
    for list_key in ("datasets", "asset_catalog"):
        for item in lock.get(list_key, []) or []:
            if isinstance(item, Mapping) and item.get("name") == CARRIER:
                entry = item
    if entry is None:
        raise RosterBuildError("the umbrella lock carries no 'slurp' dataset entry")
    annotations = entry.get("annotations")
    if not isinstance(annotations, Mapping):
        raise RosterBuildError("the 'slurp' lock entry carries no annotations block")
    pinned = annotations.get("sha256")
    records = annotations.get("records")
    if not isinstance(pinned, Mapping) or not isinstance(records, Mapping):
        raise RosterBuildError("the 'slurp' annotations block is malformed")
    _audio_relpath, _audio_root, metadata_dir = _governed_roots(lock, root)
    measured = sha256_file(metadata_dir / "test.jsonl")
    if measured != pinned.get("test.jsonl"):
        raise RosterBuildError(
            "governed test.jsonl bytes drifted from the umbrella lock pin "
            f"({measured} != {pinned.get('test.jsonl')})"
        )
    if int(records.get(SPLIT, -1)) != EXPECTED_UTTERANCES:
        raise RosterBuildError(
            f"the umbrella lock records {records.get(SPLIT)!r} test sentence records, "
            f"expected {EXPECTED_UTTERANCES}"
        )
    return {
        "metadata_relpath": f"{metadata_dir.relative_to(root).as_posix()}/test.jsonl",
        "sha256": measured,
        "lock_revision": entry.get("revision"),
        "lock_records_test": int(records[SPLIT]),
    }


def _cross_check_frozen_receipt(ids: Sequence[str]) -> dict[str, object]:
    """The live identity-only enumeration must equal the committed receipt."""

    document = _load_json(REPO_ROOT / SPLIT_IDENTITY_RELPATH, "split identity receipt")
    if not isinstance(document, Mapping):
        raise RosterBuildError("split identity receipt must be a JSON object")
    splits = document.get("splits")
    block = splits.get(SPLIT) if isinstance(splits, Mapping) else None
    if not isinstance(block, Mapping):
        raise RosterBuildError("split identity receipt carries no test block")
    frozen_ids = block.get("ids")
    if not isinstance(frozen_ids, list) or list(frozen_ids) != list(ids):
        raise RosterBuildError(
            "the live identity-only enumeration of the SLURP test split disagrees "
            "with the committed receipt's frozen id list"
        )
    recomputed = hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest()
    if recomputed != block.get("identity_hash") or int(block.get("count", -1)) != len(ids):
        raise RosterBuildError(
            "the committed split identity receipt's own count/hash do not reproduce"
        )
    return {
        "relpath": SPLIT_IDENTITY_RELPATH,
        "file_sha256": sha256_file(REPO_ROOT / SPLIT_IDENTITY_RELPATH),
        "test_ids": int(block["count"]),
        "test_identity_hash": str(block["identity_hash"]),
        "basis": (
            "sha256 over the LF-joined sorted BARE sample ids -- the "
            "rails.knowledge_build.freeze_slurp_split_identity convention, which is "
            "NOT the carrier-prefixed core.roster/data.splits convention the roster's "
            "own split_identity_hash uses"
        ),
    }


# --------------------------------------------------------------------------- #
# disjointness sources
# --------------------------------------------------------------------------- #


def _roster_receipt_sources() -> list[dict[str, object]]:
    sources: list[dict[str, object]] = []
    directory = REPO_ROOT / "docs/receipts/rosters"
    for path in sorted(directory.glob("*.json")):
        document = _load_json(path, "roster receipt")
        if not isinstance(document, Mapping):
            continue
        if document.get("carrier_lock_key") != CARRIER:
            continue
        items = document.get("items")
        if not isinstance(items, list):
            continue
        ids = {str(item["sample_id"]) for item in items if isinstance(item, Mapping)}
        sources.append(
            {
                "kind": "roster-receipt",
                "relpath": path.relative_to(REPO_ROOT).as_posix(),
                "roster_id": document.get("roster_id"),
                "roster_role": document.get("roster_role", EVALUATION_ROSTER_ROLE),
                "split_role": document.get("split_role"),
                "file_sha256": sha256_file(path),
                "ids": ids,
            }
        )
    return sources


def _probe_sample_sources() -> list[dict[str, object]]:
    sources: list[dict[str, object]] = []
    directory = REPO_ROOT / "docs/receipts/probe-samples"
    for path in sorted(directory.glob("*.json")):
        document = _load_json(path, "probe-sample receipt")
        if not isinstance(document, Mapping) or document.get("carrier") != CARRIER:
            continue
        items = document.get("items")
        if not isinstance(items, list):
            continue
        ids = {
            str(item["id"])
            for item in items
            if isinstance(item, Mapping) and isinstance(item.get("id"), str)
        }
        if not ids:
            continue
        sources.append(
            {
                "kind": "probe-sample-receipt",
                "relpath": path.relative_to(REPO_ROOT).as_posix(),
                "roster_id": document.get("probe"),
                "roster_role": None,
                "split_role": document.get("split_role"),
                "file_sha256": sha256_file(path),
                "ids": ids,
            }
        )
    return sources


def _knowledge_snapshot_sources(root: Path) -> list[dict[str, object]]:
    """Every knowledge store / exemplar pool snapshot of this carrier.

    Only ``source_sample_ids`` is taken. The ``values`` and ``facets`` blocks of
    these documents carry TRAIN gold, which this pass never inspects.
    """

    sources: list[dict[str, object]] = []
    base = Path(root) / "knowledge" / CARRIER
    if not base.is_dir():
        return sources
    for path in sorted(base.rglob("snapshot.json")):
        document = _load_json(path, "knowledge snapshot")
        if not isinstance(document, Mapping):
            continue
        ids_value = document.get("source_sample_ids")
        if not isinstance(ids_value, list) or not ids_value:
            continue
        ids = {str(value) for value in ids_value}
        sources.append(
            {
                "kind": "knowledge-snapshot",
                "relpath": path.relative_to(Path(root)).as_posix(),
                "roster_id": document.get("snapshot_id"),
                "roster_role": document.get("source_partition_role"),
                "split_role": None,
                "file_sha256": None,  # data-root bytes; the snapshot_sha256 below is the identity
                "snapshot_sha256": document.get("snapshot_sha256"),
                "ids": ids,
            }
        )
        del document
    return sources


def _probe_binding_sources() -> list[dict[str, object]]:
    """Config-side probe bindings that name SLURP sample ids directly."""

    sources: list[dict[str, object]] = []
    directory = REPO_ROOT / "configs/probes"
    if not directory.is_dir():
        return sources
    for path in sorted(directory.rglob("*.json")):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        if f"{CARRIER}:{SPLIT}:" not in text and f"{CARRIER}:devel:" not in text:
            continue
        document = json.loads(text)
        ids = set()

        def harvest(node: object) -> None:
            if isinstance(node, str) and node.startswith(f"{CARRIER}:"):
                ids.add(node)
            elif isinstance(node, Mapping):
                for value in node.values():
                    harvest(value)
            elif isinstance(node, list):
                for value in node:
                    harvest(value)

        harvest(document)
        if not ids:
            continue
        sources.append(
            {
                "kind": "probe-binding-config",
                "relpath": path.relative_to(REPO_ROOT).as_posix(),
                "roster_id": path.stem,
                "roster_role": None,
                "split_role": None,
                "file_sha256": sha256_file(path),
                "ids": ids,
            }
        )
    return sources


def _exposure_closure(identity_hashes: Iterable[str]) -> dict[str, object]:
    """The split must appear in no CONSUMED exposure-ledger row.

    Protocol section 2.3 item 4 states the criterion exactly: "the test identity
    hash appears in no consumed exposure-ledger row: the split is unread at the
    moment of registration". A row with ``consumed = no`` is a REGISTRATION --
    the three preparation rows of this very read are exactly that, and they are
    written after this receipt is minted -- so it is reported, not treated as a
    violation. Only a consumed row means the split has already been read, and
    that stops everything.
    """

    text = (REPO_ROOT / EXPOSURE_LEDGER_RELPATH).read_text(encoding="utf-8")
    rows = _parse_ledger_tables(text)
    wanted = {value for value in identity_hashes if value}
    matches = []
    consumed = []
    for row in rows:
        cell = row.get("split identity hash", "")
        for value in wanted:
            if value and value in cell:
                record = {
                    "run_id": row.get("run/experiment id"),
                    "consumed": row.get("consumed"),
                    "identity_hash": value,
                }
                matches.append(record)
                if str(record["consumed"]).strip().lower() != "no":
                    consumed.append(record)
    return {
        "ledger_relpath": EXPOSURE_LEDGER_RELPATH,
        "rows_parsed": len(rows),
        "identity_hashes_searched": sorted(wanted),
        "matching_rows": matches,
        "consumed_rows": consumed,
        "verdict": "UNREAD" if not consumed else "ALREADY CONSUMED -- STOP",
    }


def build_disjointness(
    *,
    roster_ids: Sequence[str],
    roster_identity_hash: str,
    frozen_identity_hash: str,
    data_root_path: Path,
    attempts: object,
) -> dict[str, object]:
    recording_ids = set(roster_ids)
    utterance_ids = {utterance_id_of(value) for value in roster_ids}
    utterance_numbers = {utterance_number_of(value) for value in roster_ids}

    sources = (
        _roster_receipt_sources()
        + _probe_sample_sources()
        + _probe_binding_sources()
        + _knowledge_snapshot_sources(data_root_path)
    )
    checked: list[dict[str, object]] = []
    violations: list[dict[str, object]] = []
    for source in sources:
        ids = source.pop("ids")
        shared_recordings = sorted(recording_ids & ids)
        other_utterances = {utterance_id_of(value) for value in ids}
        other_numbers = {utterance_number_of(value) for value in ids}
        shared_utterances = sorted(utterance_ids & other_utterances)
        shared_numbers = sorted(utterance_numbers & other_numbers)
        row = {
            **source,
            "items": len(ids),
            "shared_recording_ids": len(shared_recordings),
            "shared_utterance_ids": len(shared_utterances),
            "shared_utterance_numbers": len(shared_numbers),
        }
        checked.append(row)
        if shared_recordings or shared_utterances or shared_numbers:
            violations.append(
                {
                    "relpath": source["relpath"],
                    "shared_recording_ids": shared_recordings[:20],
                    "shared_utterance_ids": shared_utterances[:20],
                    "shared_utterance_numbers": shared_numbers[:20],
                }
            )

    closure = _exposure_closure((roster_identity_hash, frozen_identity_hash))
    document: dict[str, object] = {
        "schema": "saea-final-report-roster-disjointness-v1",
        "study": "speech-aware-evidence-acquisition",
        "authority": AUTHORITY,
        "generator": GENERATOR,
        "roster": {
            "roster_id": ROSTER_ID,
            "relpath": ROSTER_RELPATH,
            "split_role": SPLIT_ROLE,
            "roster_split_identity_hash": roster_identity_hash,
            "carrier_split_identity_hash": frozen_identity_hash,
            "recordings": len(recording_ids),
            "utterances": len(utterance_ids),
        },
        "passes": {
            "1_by_recording_id": {
                "sources_checked": len(checked),
                "total_shared": sum(int(row["shared_recording_ids"]) for row in checked),
            },
            "2_by_utterance_id": {
                "sources_checked": len(checked),
                "total_shared": sum(int(row["shared_utterance_ids"]) for row in checked),
                "note": (
                    "Compared BOTH as the full 'slurp:<split>:<number>' utterance id and "
                    "as the bare SLURP prompt number, because the split token alone would "
                    "make every cross-split comparison trivially empty."
                ),
                "total_shared_prompt_numbers": sum(
                    int(row["shared_utterance_numbers"]) for row in checked
                ),
            },
            "3_by_text": {
                "status": "NOT RUN",
                "why": (
                    "Protocol section 9 item 3 leaves it undecided whether a hash-only "
                    "comparison that touches the test 'sentence' field is admissible under "
                    "the information boundary, and this build was run under a mission "
                    "boundary that forbids opening the test split's annotations at all. "
                    "The id-level proof above is therefore the whole proof this receipt "
                    "carries; if the owner rules the hashed pass admissible it is a "
                    "successor receipt, never an edit of these bytes."
                ),
            },
            "4_exposure_closure": closure,
        },
        "sources": checked,
        "violations": violations,
        "verdict": "CLEAN" if not violations and not closure["consumed_rows"] else "STOP",
        "offline_guard": {
            "outbound_connection_attempts": getattr(attempts, "count", None),
            "attempted_targets": list(getattr(attempts, "targets", ()) or ()),
        },
    }
    document["proof_sha256"] = canonical_sha256(document)
    return document


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write the two receipts")
    parser.add_argument("--workers", type=int, default=WORKERS)
    args = parser.parse_args(argv)
    if not 1 <= int(args.workers) <= WORKERS:
        raise SystemExit(f"--workers must be in [1, {WORKERS}]")

    attempts = arm_offline_guard()
    lock = load_lock(umbrella_lock_path(REPO_ROOT))
    root = data_root()
    metadata = _verify_governed_metadata(lock, root)

    ids = list(slurp_split_sample_ids(lock, root, SPLIT))
    if len(ids) != EXPECTED_RECORDINGS:
        raise SystemExit(
            f"the SLURP test split enumerates {len(ids)} recordings, expected "
            f"{EXPECTED_RECORDINGS}"
        )
    utterances = {utterance_id_of(value) for value in ids}
    if len(utterances) != EXPECTED_UTTERANCES:
        raise SystemExit(
            f"the SLURP test split enumerates {len(utterances)} utterances, expected "
            f"{EXPECTED_UTTERANCES}"
        )
    frozen = _cross_check_frozen_receipt(ids)

    audio_root_relpath, _audio_root, _metadata_dir = _governed_roots(lock, root)
    media_relpaths = {
        sample_id: f"{audio_root_relpath}/slurp_real/{sample_id.split(':')[3]}.flac"
        for sample_id in ids
    }
    confined = [
        (
            sample_id,
            *_confined_media_path(
                root,
                media_relpaths[sample_id],
                context=f"SLURP test recording {sample_id!r}",
            ),
        )
        for sample_id in ids
    ]
    started = time.monotonic()
    with ThreadPoolExecutor(
        max_workers=min(int(args.workers), len(confined)),
        thread_name_prefix="saea-test-roster",
    ) as pool:
        measured = tuple(pool.map(_probe_speech_media, (entry[2] for entry in confined)))
    inventory_seconds = time.monotonic() - started

    facts: dict[str, dict[str, object]] = {}
    total_bytes = 0
    sample_rates: set[int] = set()
    for (sample_id, relpath, _path), probe in zip(confined, measured, strict=True):
        media_bytes, media_sha256, audio_seconds, sample_rate_hz = probe
        total_bytes += int(media_bytes)
        sample_rates.add(int(sample_rate_hz))
        facts[sample_id] = {
            "media_relpath": relpath,
            "bytes": int(media_bytes),
            "audio_sha256": media_sha256,
            "audio_seconds": round(float(audio_seconds), 9),
            "sample_rate_hz": int(sample_rate_hz),
        }

    candidates = [
        RosterItem(
            sample_id=sample_id,
            stratum=stratum_of(sample_id),
            extra={
                "audio_seconds": facts[sample_id]["audio_seconds"],
                "headset": stratum_of(sample_id) == HEADSET_STRATUM,
                "utterance_id": utterance_id_of(sample_id),
            },
        )
        for sample_id in ids
    ]
    capacities: dict[str, int] = {}
    for item in candidates:
        capacities[item.stratum] = capacities.get(item.stratum, 0) + 1

    receipt = freeze_roster(
        carrier_lock_key=CARRIER,
        candidates=candidates,
        per_stratum=capacities,  # take-all: the quota IS the capacity
        seed=SEED,
        split_role=SPLIT_ROLE,
        roster_id=ROSTER_ID,
        roster_role=EVALUATION_ROSTER_ROLE,
    )
    if int(receipt["excluded_count"]) != 0:
        raise SystemExit("a take-all freeze must exclude nothing")
    if len(receipt["items"]) != EXPECTED_RECORDINGS:
        raise SystemExit("the frozen roster does not carry every test recording")
    if dict(receipt["strata_counts"]) != capacities:
        raise SystemExit("the frozen roster's strata counts are not the full capacities")
    roster_identity_hash = verify_roster(receipt)

    audio_seconds_total = round(
        sum(float(item["audio_seconds"]) for item in receipt["items"]), 9
    )
    disjointness = build_disjointness(
        roster_ids=ids,
        roster_identity_hash=roster_identity_hash,
        frozen_identity_hash=str(frozen["test_identity_hash"]),
        data_root_path=root,
        attempts=attempts,
    )
    if disjointness["verdict"] != "CLEAN":
        raise SystemExit(
            "disjointness is NOT clean; the roster is not frozen: "
            + json.dumps(disjointness["violations"][:3], sort_keys=True)
        )
    disjointness_bytes = (
        json.dumps(disjointness, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    disjointness_sha256 = hashlib.sha256(disjointness_bytes).hexdigest()

    receipt.update(
        {
            "authority": AUTHORITY,
            "generator": GENERATOR,
            "protocol_draft": {
                "relpath": PROTOCOL_RELPATH,
                "sha256": sha256_file(REPO_ROOT / PROTOCOL_RELPATH),
                "section": "2 (the roster), 6 (the venue), 7 (the registration form)",
            },
            "split_name": SPLIT_NAME,
            "status": "FROZEN; MODEL-FREE, LABEL-FREE, ZERO CONTACTS",
            "design": (
                "The COMPLETE official SLURP test split: every sentence record, every "
                "recording, both microphone channels. No subsampling, no stratified draw, "
                "no filtering, no reserve. Read exactly once, at the end of Stage 3, under "
                "the owner allowance of decision 108; the roster itself authorises nothing."
            ),
            "selection_rule": (
                "the complete split, id-sorted; no sampling. core.roster.freeze_roster is "
                "given a per-stratum quota equal to each stratum's own capacity, so every "
                "candidate is selected and the seed never changes the outcome."
            ),
            "seed_note": (
                f"seed {SEED} is recorded because the receipt schema carries one; a take-all "
                "freeze draws nothing, so the value cannot affect the frozen id set"
            ),
            "strata_definition": (
                "MICROPHONE CHANNEL only: 'headset' is the '-headset' recording-id suffix, "
                "'far-field' is everything else. Scenario is a GOLD field of the test split "
                "and is deliberately not used as a stratum here, so the protocol draft's "
                "section 2.2 per-scenario breakdown is NOT part of this receipt."
            ),
            "channel_counts": {
                "headset": capacities.get(HEADSET_STRATUM, 0),
                "far_field": capacities.get(FAR_FIELD_STRATUM, 0),
            },
            "counts": {
                "recordings": len(receipt["items"]),
                "distinct_utterances": len(utterances),
                "total_bytes": total_bytes,
                "audio_seconds_total": audio_seconds_total,
                "sample_rates_hz": sorted(sample_rates),
            },
            "audio_seconds_total": audio_seconds_total,
            "item_fields": sorted(
                {key for item in receipt["items"] for key in item}
            ),
            "governed_metadata": metadata,
            "split_identity_receipt": frozen,
            "split_identity_hash_basis": (
                "sha256 over the LF-joined sorted carrier-prefixed 'slurp/<sample_id>' ids "
                "-- the core.roster / data.splits convention, which is what an ExecutionPlan "
                "declares"
            ),
            "disjointness": {
                "relpath": f"{CHECK_DIR}/{DISJOINTNESS_NAME}",
                "sha256": disjointness_sha256,
                "verdict": disjointness["verdict"],
                "sources_checked": len(disjointness["sources"]),
            },
            "media_identity": (
                "Per-row audio_sha256, media_relpath, bytes and sample rate live in the "
                "runtime view configs/dataset/slurp-speech-native-test-full.json and in the "
                "D1 supplement docs/receipts/artifacts/d1-slurp-test-full.json; this receipt "
                "is the identity statement and carries durations only."
            ),
            "one_read_rule": (
                "ONE complete read, registered before contact, scored once as one complete "
                "manifest job. There is no smoke, pilot, preview or sanity batch on these "
                "rows, no second configuration, no re-score and no re-registration. The "
                "preparations (packets, speech query vectors) are label-free encoder passes "
                "and do not consume the split's answer surface, but they carry the same "
                "machine role and the same owner allowance."
            ),
            "target_gold_opened_before_receipt": False,
            "offline_guard": disjointness["offline_guard"],
            "measurement": {
                # No wall-clock or throughput value belongs in an identity
                # receipt: it would make the frozen bytes unreproducible. The
                # measured CPU throughput of this pass lives beside the media
                # inventory under the packets check directory.
                "decoder": (
                    "soundfile header probe for duration and rate; bytes hashed with "
                    "SHA-256. No audio sample is decoded, ffmpeg is absent by design and no "
                    "media byte is rewritten."
                ),
                "durations_rounded_to": 9,
            },
        }
    )
    verify_roster(receipt)
    receipt_bytes = canonical_receipt_bytes(receipt)

    summary = {
        "roster_id": ROSTER_ID,
        "roster_relpath": ROSTER_RELPATH,
        "roster_receipt_sha256": hashlib.sha256(receipt_bytes).hexdigest(),
        "split_role": SPLIT_ROLE,
        "roster_split_identity_hash": roster_identity_hash,
        "carrier_split_identity_hash": frozen["test_identity_hash"],
        "recordings": len(receipt["items"]),
        "distinct_utterances": len(utterances),
        "channel_counts": receipt["channel_counts"],
        "audio_seconds_total": audio_seconds_total,
        "total_bytes": total_bytes,
        "sample_rates_hz": sorted(sample_rates),
        "disjointness_relpath": f"{CHECK_DIR}/{DISJOINTNESS_NAME}",
        "disjointness_sha256": disjointness_sha256,
        "disjointness_verdict": disjointness["verdict"],
        "disjointness_sources_checked": len(disjointness["sources"]),
        "governed_test_jsonl_sha256": metadata["sha256"],
        "offline_guard": disjointness["offline_guard"],
        "media_inventory_wall_seconds": round(inventory_seconds, 3),
        "media_inventory_files_per_second": round(
            len(ids) / max(inventory_seconds, 1e-9), 3
        ),
        "workers": int(args.workers),
        "written": bool(args.write),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))

    if args.write:
        check_dir = REPO_ROOT / CHECK_DIR
        check_dir.mkdir(parents=True, exist_ok=True)
        target = check_dir / DISJOINTNESS_NAME
        if target.exists():
            raise SystemExit(f"refusing to overwrite {target}")
        with target.open("wb") as handle:
            handle.write(disjointness_bytes)
        write_roster(receipt, REPO_ROOT / ROSTER_RELPATH)
        print(f"wrote {ROSTER_RELPATH}")
        print(f"wrote {CHECK_DIR}/{DISJOINTNESS_NAME}")
    return 0


if __name__ == "__main__":
    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    raise SystemExit(main())
