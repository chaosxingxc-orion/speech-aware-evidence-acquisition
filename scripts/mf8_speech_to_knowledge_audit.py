#!/usr/bin/env python3
"""MF-8 -- the speech-to-knowledge audit (model-free).

Prices the owner's 2026-09-08 three-dimension direction: how (multi-speaker)
speech maps onto already-constructed knowledge in text-domain, speech-domain
and state-knowledge form. Readiness note and boundary:
``docs/readiness/2026-09-08-mf8-speech-to-knowledge-audit-v1.md``.
Exposure row ``SAEA-SLURP-MF8-SPEECH-TO-KNOWLEDGE-AUDIT-V1``.

**Zero model, GPU, tool, embedding, network and audio-decode contacts.** The
script starts no server, loads no model and decodes no waveform; flac
*headers* are the only audio bytes it touches, through the loaders' own
``soundfile.info`` path.

Subcommands
-----------
``speakers``
    Question 1: SLURP speaker structure in TRAIN and in the DEV-1000 roster,
    the speaker overlap, and the per-row same-speaker same-intent TRAIN
    exemplar distribution against other speakers'.

Boundary enforced in code, not only in prose: no devel ``sentence`` string is
ever read (``data.slurp.load_slurp_split`` does not carry one), the held-out
``test`` split is never named, and every read is a committed or governed byte
some earlier registered row already opened.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

ROW_ID = "SAEA-SLURP-MF8-SPEECH-TO-KNOWLEDGE-AUDIT-V1"
RECEIPT_DIRNAME = "2026-09-08-mf8-speech-to-knowledge-audit"
DEV1000_CONFIG = "configs/dataset/slurp-speech-native-dev1000.json"
UMBRELLA_LOCK_FALLBACK = "/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json"

# The DEV-1000 roster's own sample ids name a devel recording; this is the
# inverse of ``data.slurp._parse_record``'s sample-id construction.
_SAMPLE_ID_PARTS = 4


def recording_filename(sample_id: str) -> str:
    """``slurp:devel:000011:audio-1497266596`` to ``audio-1497266596.flac``."""

    parts = sample_id.split(":")
    if len(parts) != _SAMPLE_ID_PARTS or not parts[3]:
        raise ValueError(f"not a SLURP sample id: {sample_id!r}")
    return f"{parts[3]}.flac"


def roster_sample_ids(config_path: Path) -> tuple[str, ...]:
    """The roster's sample ids in committed file order."""

    document = json.loads(Path(config_path).read_text(encoding="utf-8"))
    items = document.get("items")
    if not isinstance(items, list) or not items:
        raise ValueError(f"{config_path} carries no items")
    ids: list[str] = []
    for item in items:
        sample_id = item.get("sample_id") if isinstance(item, Mapping) else None
        if not isinstance(sample_id, str) or not sample_id:
            raise ValueError(f"{config_path} carries an item without a sample id")
        ids.append(sample_id)
    if len(set(ids)) != len(ids):
        raise ValueError(f"{config_path} repeats a sample id")
    return tuple(ids)


def histogram(values: Iterable[int]) -> dict[str, int]:
    """A stable count histogram keyed by the string of the integer."""

    return {str(key): int(count) for key, count in sorted(Counter(values).items())}


def quantiles(values: Sequence[float]) -> dict[str, float]:
    """min / p25 / median / p75 / p90 / max / mean, nearest-rank quantiles."""

    if not values:
        return {}
    ordered = sorted(float(value) for value in values)
    size = len(ordered)

    def rank(fraction: float) -> float:
        index = max(0, min(size - 1, int(round(fraction * (size - 1)))))
        return ordered[index]

    return {
        "min": ordered[0],
        "p25": rank(0.25),
        "median": rank(0.50),
        "p75": rank(0.75),
        "p90": rank(0.90),
        "max": ordered[-1],
        "mean": sum(ordered) / size,
    }


def at_least_counts(values: Sequence[int], thresholds: Sequence[int]) -> dict[str, int]:
    """How many entries reach each threshold."""

    return {
        f">={threshold}": sum(1 for value in values if value >= threshold)
        for threshold in thresholds
    }


def resolve_lock_and_root() -> tuple[Mapping[str, object], Path, Path]:
    """The umbrella lock, the controlled data root, and the lock path used."""

    from speech_aware_evidence_acquisition.data.lock import data_root, load_lock

    lock_path = REPO_ROOT.parent.parent / "docs" / "datasets.lock.json"
    if not lock_path.is_file():
        # A git worktree sits outside the registered adjacent-checkout layout;
        # the umbrella lock is still the single live authority, so it is named
        # explicitly rather than copied.
        lock_path = Path(UMBRELLA_LOCK_FALLBACK)
    if not lock_path.is_file():
        raise SystemExit(f"umbrella datasets lock not found (tried {lock_path})")
    return load_lock(lock_path), data_root(), lock_path


def command_speakers(args: argparse.Namespace) -> int:
    from speech_aware_evidence_acquisition.data.slurp import (
        _governed_roots,
        _slurp_speaker_index,
        load_slurp_split,
        load_slurp_train_material,
    )

    lock, root, lock_path = resolve_lock_and_root()
    _, _, metadata_dir = _governed_roots(lock, root)
    speakers_by_file = _slurp_speaker_index(metadata_dir)

    train = load_slurp_train_material(lock, root)
    # TRAIN side: one row per (utterance, recording) -- the recording is the
    # unit an audio exemplar would actually carry.
    train_recordings_by_speaker_intent: dict[tuple[str, str], int] = defaultdict(int)
    train_sentences_by_speaker_intent: dict[tuple[str, str], set[str]] = defaultdict(set)
    train_recordings_by_intent: dict[str, int] = defaultdict(int)
    train_recordings_by_speaker: dict[str, int] = defaultdict(int)
    train_utterances_by_speaker: dict[str, set[str]] = defaultdict(set)
    train_intents_by_speaker: dict[str, set[str]] = defaultdict(set)
    train_recording_total = 0
    for utterance in train:
        intent = f"{utterance.scenario}_{utterance.action}"
        for recording in utterance.recordings:
            train_recording_total += 1
            key = (recording.speaker_id, intent)
            train_recordings_by_speaker_intent[key] += 1
            train_sentences_by_speaker_intent[key].add(utterance.utterance_id)
            train_recordings_by_intent[intent] += 1
            train_recordings_by_speaker[recording.speaker_id] += 1
            train_utterances_by_speaker[recording.speaker_id].add(utterance.utterance_id)
            train_intents_by_speaker[recording.speaker_id].add(intent)

    # DEV side: gold LABELS only. ``SlurpRecord`` deliberately carries no
    # reference sentence, so no devel text can reach this pass.
    devel = {record.sample_id: record for record in load_slurp_split(lock, root, "devel")}
    roster = roster_sample_ids(REPO_ROOT / DEV1000_CONFIG)

    rows: list[dict[str, object]] = []
    for sample_id in roster:
        record = devel.get(sample_id)
        if record is None:
            raise SystemExit(f"DEV-1000 sample {sample_id!r} is absent from devel.jsonl")
        filename = recording_filename(sample_id)
        speaker = speakers_by_file.get(filename)
        if speaker is None:
            raise SystemExit(f"DEV-1000 recording {filename!r} lacks a governed speaker")
        key = (speaker, record.intent)
        same_speaker_recordings = train_recordings_by_speaker_intent.get(key, 0)
        same_speaker_sentences = len(train_sentences_by_speaker_intent.get(key, ()))
        total_recordings = train_recordings_by_intent.get(record.intent, 0)
        rows.append(
            {
                "sample_id": sample_id,
                "speaker_id": speaker,
                "gold_intent": record.intent,
                "gold_scenario": record.scenario,
                "audio_seconds": record.audio_seconds,
                "speaker_in_train": speaker in train_recordings_by_speaker,
                "train_recordings_this_speaker": train_recordings_by_speaker.get(speaker, 0),
                "same_speaker_same_intent_recordings": same_speaker_recordings,
                "same_speaker_same_intent_sentences": same_speaker_sentences,
                "other_speaker_same_intent_recordings": total_recordings - same_speaker_recordings,
                "any_speaker_same_intent_recordings": total_recordings,
            }
        )

    dev_speakers = {row["speaker_id"] for row in rows}
    train_speakers = set(train_recordings_by_speaker)
    same_speaker_values = [int(row["same_speaker_same_intent_recordings"]) for row in rows]
    same_sentence_values = [int(row["same_speaker_same_intent_sentences"]) for row in rows]
    other_speaker_values = [int(row["other_speaker_same_intent_recordings"]) for row in rows]
    thresholds = (1, 2, 3, 5, 8, 10)

    devel_speakers_all = {
        speakers_by_file[recording_filename(sample_id)]
        for sample_id in devel
        if recording_filename(sample_id) in speakers_by_file
    }

    result: dict[str, object] = {
        "schema": "saea-mf8-speaker-structure-v1",
        "row_id": ROW_ID,
        "lock_path": str(lock_path),
        "boundary": (
            "zero model, GPU, tool, embedding, network and audio-decode contacts. DEV gold "
            "INTENT LABELS only; no devel sentence text is read and the test split is never "
            "named."
        ),
        "train": {
            "utterances": len(train),
            "recordings": train_recording_total,
            "distinct_speakers": len(train_speakers),
            "recordings_per_speaker": quantiles(sorted(train_recordings_by_speaker.values())),
            "utterances_per_speaker": quantiles(
                sorted(len(value) for value in train_utterances_by_speaker.values())
            ),
            "distinct_intents_per_speaker": quantiles(
                sorted(len(value) for value in train_intents_by_speaker.values())
            ),
            "distinct_intents": len(train_recordings_by_intent),
        },
        "devel": {
            "recordings_total": len(devel),
            "distinct_speakers": len(devel_speakers_all),
            "speakers_shared_with_train": len(devel_speakers_all & train_speakers),
        },
        "dev1000": {
            "rows": len(rows),
            "distinct_speakers": len(dev_speakers),
            "speakers_also_in_train": len(dev_speakers & train_speakers),
            "rows_whose_speaker_is_in_train": sum(1 for row in rows if row["speaker_in_train"]),
            "train_recordings_per_shared_speaker": quantiles(
                sorted(
                    train_recordings_by_speaker[speaker]
                    for speaker in sorted(dev_speakers & train_speakers)
                )
            ),
            "rows_per_dev_speaker": quantiles(
                sorted(Counter(row["speaker_id"] for row in rows).values())
            ),
        },
        "same_speaker_same_intent_recordings": {
            "quantiles": quantiles(same_speaker_values),
            "histogram": histogram(same_speaker_values),
            "at_least": at_least_counts(same_speaker_values, thresholds),
        },
        "same_speaker_same_intent_sentences": {
            "quantiles": quantiles(same_sentence_values),
            "histogram": histogram(same_sentence_values),
            "at_least": at_least_counts(same_sentence_values, thresholds),
        },
        "other_speaker_same_intent_recordings": {
            "quantiles": quantiles(other_speaker_values),
            "at_least": at_least_counts(other_speaker_values, thresholds),
        },
        "rows": rows,
    }

    by_scenario: dict[str, list[int]] = defaultdict(list)
    for row in rows:
        by_scenario[str(row["gold_scenario"])].append(
            int(row["same_speaker_same_intent_recordings"])
        )
    result["per_scenario"] = {
        scenario: {
            "n": len(values),
            "median_same_speaker_exemplars": quantiles(values).get("median"),
            "rows_with_at_least_5": sum(1 for value in values if value >= 5),
            "rows_with_zero": sum(1 for value in values if value == 0),
        }
        for scenario, values in sorted(by_scenario.items())
    }

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "speaker-structure.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    summary = dict(result)
    summary.pop("rows")
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="MF-8 speech-to-knowledge audit (model-free)")
    parser.add_argument(
        "--out-dir",
        default=str(
            REPO_ROOT / "docs" / "checks" / "speech-aware-evidence-acquisition" / RECEIPT_DIRNAME
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("speakers", help="question 1: SLURP speaker structure")
    args = parser.parse_args(argv)
    if args.command == "speakers":
        return command_speakers(args)
    parser.error(f"unknown command {args.command!r}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
