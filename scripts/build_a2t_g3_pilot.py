#!/usr/bin/env python3
"""Materialize the identity-only G3 roster and complete tier-7 dialogue WAVs.

This command performs no model contact and does not preprocess speech features.
Large derived WAVs and their runtime media manifest stay under the controlled
data root. Only the identity-only 40-sample roster is written in the study.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Mapping

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from speech_aware_evidence_acquisition.analysis.a2t_g3_pilot import (  # noqa: E402
    G3_SELECTION_NAMESPACE,
    build_repo_pilot_roster,
)
from speech_aware_evidence_acquisition.data.audio2tool import (  # noqa: E402
    AUDIO2TOOL_LOCK_KEY,
)
from speech_aware_evidence_acquisition.data.audio2tool_dialogue import (  # noqa: E402
    DEFAULT_SILENCE_SECONDS,
    DialogueMaterializationError,
    materialize_tier7_dialogue,
    verify_dialogue_receipt,
)
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    asset_dir,
    load_lock,
    umbrella_lock_path,
)

DEFAULT_ROSTER = REPO_ROOT / "docs" / "receipts" / "a2t" / "A2T-G3-PILOT-40.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json_atomic(
    path: Path, payload: Mapping[str, object], *, overwrite: bool
) -> None:
    if path.exists() and not overwrite:
        raise RuntimeError(f"refusing to overwrite existing output: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False, newline="\n"
    ) as handle:
        temporary = Path(handle.name)
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(temporary, path)


def _tier7_entries(public_dir: Path, wanted_ids: set[int]) -> dict[int, dict[str, object]]:
    path = public_dir / "tier7_multiturn_data" / "tier7_multiturn.json"
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RuntimeError(f"cannot read tier-7 manifest: {error}") from error
    if not isinstance(document, list):
        raise RuntimeError("tier-7 manifest must be a list")
    selected: dict[int, dict[str, object]] = {}
    for entry in document:
        if not isinstance(entry, Mapping) or entry.get("id") not in wanted_ids:
            continue
        item_id = entry.get("id")
        history = entry.get("chat_history")
        if not isinstance(item_id, int) or not isinstance(history, list):
            raise RuntimeError("selected tier-7 entry is malformed")
        # Build an allowlisted projection. Transcript content and every gold field
        # are discarded before the dialogue materializer receives the entry.
        projected_turns: list[dict[str, object]] = []
        for turn in history:
            if not isinstance(turn, Mapping):
                raise RuntimeError(f"tier-7 entry {item_id} has a malformed turn")
            projected_turns.append(
                {
                    "duration": turn.get("duration"),
                    "path": turn.get("path"),
                    "role": turn.get("role"),
                }
            )
        selected[item_id] = {
            "chat_history": projected_turns,
            "id": item_id,
            "tier": "tier7_multiturn",
        }
    if set(selected) != wanted_ids:
        raise RuntimeError(
            f"tier-7 manifest lacks selected ids {sorted(wanted_ids - set(selected))}"
        )
    return selected


def materialize(
    *,
    repo_root: Path,
    data_root: Path,
    roster_path: Path,
    output_dir: Path,
    silence_seconds: float,
    overwrite: bool,
) -> dict[str, object]:
    """Materialize the roster, five derived WAVs, receipts, and media manifest."""

    controlled_root = data_root.resolve()
    target_root = output_dir.resolve()
    if not target_root.is_relative_to(controlled_root):
        raise RuntimeError("derived dialogue output must stay under the controlled data root")
    roster = build_repo_pilot_roster(repo_root)
    _write_json_atomic(roster_path, roster, overwrite=overwrite)

    lock = load_lock(umbrella_lock_path(repo_root))
    public_dir = asset_dir(lock, AUDIO2TOOL_LOCK_KEY, data_root) / "public"
    tier7_items = [item for item in roster["items"] if item["tier"] == "tier7_multiturn"]
    entries = _tier7_entries(public_dir, {int(item["id"]) for item in tier7_items})
    runtime_items: list[dict[str, object]] = []
    dialogue_receipts: list[dict[str, object]] = []
    for item in roster["items"]:
        runtime_item = {
            "audio_seconds": item["audio_seconds"],
            "audio_sha256": item["audio_sha256"],
            "media_relpath": item["media_relpath"],
            "sample_id": item["sample_id"],
            "tier": item["tier"],
        }
        if item["tier"] == "tier7_multiturn":
            query_dir = output_dir / "tier7_multiturn" / f"query_{int(item['id']):05d}"
            output_wav = query_dir / "complete_dialogue.wav"
            receipt_path = query_dir / "complete_dialogue.receipt.json"
            receipt = materialize_tier7_dialogue(
                sample_id=str(item["sample_id"]),
                entry=entries[int(item["id"])],
                public_dir=public_dir,
                output_wav=output_wav,
                receipt_path=receipt_path,
                silence_seconds=silence_seconds,
                overwrite=overwrite,
            )
            verify_dialogue_receipt(
                receipt_path, public_dir=public_dir, output_wav=output_wav
            )
            runtime_item.update(
                {
                    "audio_seconds": receipt["output"]["audio_seconds"],
                    "audio_sha256": receipt["output"]["audio_sha256"],
                    "media_relpath": output_wav.relative_to(data_root).as_posix(),
                    "source_final_turn_media_relpath": item["media_relpath"],
                }
            )
            dialogue_receipts.append(
                {
                    "receipt_relpath": receipt_path.relative_to(data_root).as_posix(),
                    "receipt_sha256": _sha256(receipt_path),
                    "sample_id": item["sample_id"],
                }
            )
        runtime_items.append(runtime_item)

    manifest = {
        "count": len(runtime_items),
        "dialogue_receipts": dialogue_receipts,
        "identity_roster": roster_path.relative_to(repo_root).as_posix(),
        "identity_roster_sha256": _sha256(roster_path),
        "items": runtime_items,
        "schema": "saea-a2t-g3-runtime-media-manifest-v1",
        "selection_namespace": G3_SELECTION_NAMESPACE,
        "tier7_complete_dialogue_count": len(dialogue_receipts),
    }
    manifest_path = output_dir / "pilot-media.json"
    _write_json_atomic(manifest_path, manifest, overwrite=overwrite)
    return {
        "dialogue_audio_seconds_total": round(
            sum(
                float(item["audio_seconds"])
                for item in runtime_items
                if item["tier"] == "tier7_multiturn"
            ),
            6,
        ),
        "manifest_path": str(manifest_path),
        "roster_path": str(roster_path),
        "selected_count": len(runtime_items),
        "tier7_count": len(dialogue_receipts),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--roster", type=Path, default=DEFAULT_ROSTER)
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument("--silence-seconds", type=float, default=DEFAULT_SILENCE_SECONDS)
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main() -> int:
    args = _parser().parse_args()
    output_dir = args.out_dir or (
        args.data_root / "derived" / "audio2tool" / G3_SELECTION_NAMESPACE
    )
    try:
        summary = materialize(
            repo_root=args.repo_root,
            data_root=args.data_root,
            roster_path=args.roster,
            output_dir=output_dir,
            silence_seconds=args.silence_seconds,
            overwrite=args.overwrite,
        )
    except (RuntimeError, DialogueMaterializationError) as error:
        raise SystemExit(str(error)) from error
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
