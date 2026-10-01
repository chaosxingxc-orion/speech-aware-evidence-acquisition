"""Offline re-application of a registered DELIVERY normaliser over a sealed run.

E11 (2026-09-18, owner directive 26; ``docs/superpowers/specs/
2026-09-16-slurp-v2-base-program-design.md`` section 3, item E11): read a
sealed ``outputs.jsonl`` and re-apply a registered
``core.base.DELIVERY_NORMALISERS`` entry to every row's delivered text,
without any model, tool, server or network contact. It writes a NEW
``outputs.jsonl``-shaped file plus a provenance JSON to a caller-named output
directory, refuses to overwrite an existing replay, and never opens the
sealed input file for writing.

Two uses, both read-only:

* on an OFF-arm (anchor) run, it answers what the delivery node WOULD have
  delivered, so a sealed arm's projected numbers can be re-derived offline
  and the in-agent cell's own number can be predicted before it flies; and
* on an ON-arm run it is the idempotence witness -- re-applying a
  deterministic normaliser to an already-normalised answer must change
  nothing, so every row comes back ``changed: false``.

This is the delivery-side sibling of
``analysis.native_commit_replay`` (the offline COMMIT re-aggregation), and
it follows that module's shape deliberately: same sealed-row reader
discipline, same refuse-to-overwrite rule, same zero-contact provenance
block.

Expected sealed row shape: one JSON object per line carrying at minimum
``sample_id`` (str) and ``text`` (str). A row carrying a
``native_episode_receipt.deliver_normaliser`` block is replayed too, and its
``already_normalised`` flag is recorded, so the idempotence read above needs
no second entry point.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Mapping, Sequence

from ..e0.artifacts import sha256_file, write_json_artifact

RESULT_SCHEMA = "saea-deliver-normaliser-replay-v1"


class DeliverNormaliserReplayError(RuntimeError):
    """The replay cannot proceed: a bad sealed input, or an attempted overwrite."""


def _read_sealed_rows(outputs_path: Path) -> list[dict[str, object]]:
    """Read a sealed ``outputs.jsonl`` exactly as
    :func:`analysis.native_commit_replay._read_sealed_rows` does: one JSON
    object per nonblank line, unique ``sample_id``, no tolerance for a
    malformed line. Read-only -- never writes to ``outputs_path``."""

    try:
        text = outputs_path.read_text(encoding="utf-8")
    except OSError as error:
        raise DeliverNormaliserReplayError(f"cannot read {outputs_path}: {error}") from error
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    if not lines:
        raise DeliverNormaliserReplayError(f"{outputs_path} is empty")
    rows: list[dict[str, object]] = []
    seen: set[str] = set()
    for number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            raise DeliverNormaliserReplayError(
                f"{outputs_path} line {number} is malformed: {error}"
            ) from error
        if not isinstance(row, Mapping):
            raise DeliverNormaliserReplayError(
                f"{outputs_path} line {number} is not an object"
            )
        sample_id = row.get("sample_id")
        if not isinstance(sample_id, str) or not sample_id:
            raise DeliverNormaliserReplayError(
                f"{outputs_path} line {number} lacks a sample_id"
            )
        if sample_id in seen:
            raise DeliverNormaliserReplayError(
                f"{outputs_path} has a duplicate sample_id {sample_id!r}"
            )
        seen.add(sample_id)
        rows.append(dict(row))
    return rows


def _already_normalised(row: Mapping[str, object]) -> bool:
    receipt = row.get("native_episode_receipt")
    return isinstance(receipt, Mapping) and isinstance(
        receipt.get("deliver_normaliser"), Mapping
    )


def replay_row(
    row: Mapping[str, object], *, normaliser, source_text: str | None = None
) -> dict[str, object]:
    """Re-apply ``normaliser`` to ONE sealed row's delivered text.

    ``source_text`` overrides the text taken from the row (the bundle
    verifier passes the trace's own recorded response bytes); left ``None``
    the row's own ``text`` is used, which is what an offline replay over a
    sealed arm wants. Never reads or writes anything beyond ``row`` itself.
    """

    text = row.get("text") if source_text is None else source_text
    if not isinstance(text, str):
        raise DeliverNormaliserReplayError(
            f"row {row.get('sample_id')!r} carries no delivered text to normalise"
        )
    outcome = normaliser(text)
    receipt = dict(outcome.receipt)
    return {
        "sample_id": row["sample_id"],
        "text": outcome.text,
        "final_response_text": outcome.text,
        "final_response_sha256": hashlib.sha256(
            outcome.text.encode("utf-8")
        ).hexdigest(),
        "source_text_sha256": receipt["input_sha256"],
        "normaliser_id": receipt["normaliser_id"],
        "normaliser_version": receipt["version"],
        "rule_id": receipt["rule_id"],
        "applied": receipt["applied"],
        "changed": bool(outcome.changed),
        # Transcript hygiene has no SLU label/filler diagnostic. Missing is
        # not zero, and its unchanged text is not an unparsed SLU answer.
        "labels_changed": receipt.get("labels_changed"),
        "label_branch": receipt.get("label_branch"),
        "fillers_changed": receipt.get("fillers_changed"),
        "already_normalised": _already_normalised(row),
    }


def replay(
    *, outputs_path: Path, normaliser_id: str, output_dir: Path
) -> dict[str, object]:
    """Read a sealed run, re-apply ``normaliser_id`` to every row, and write
    the result to a fresh ``output_dir``.

    Refuses to overwrite: ``output_dir`` must not already contain
    ``outputs.jsonl`` or ``provenance.json``. Never opens ``outputs_path``
    for writing, and makes zero model, tool or network contacts.
    """

    # Function-local: importing rails.delivery_normalisers is what POPULATES
    # core.base.DELIVERY_NORMALISERS (same registration discipline as the
    # rest of this package).
    from ..core.base import DELIVERY_NORMALISERS, CoreError  # noqa: PLC0415
    from ..rails import delivery_normalisers as _normalisers  # noqa: PLC0415, F401

    outputs_path = Path(outputs_path)
    output_dir = Path(output_dir)
    outputs_target = output_dir / "outputs.jsonl"
    provenance_target = output_dir / "provenance.json"
    if outputs_target.exists() or provenance_target.exists():
        raise DeliverNormaliserReplayError(
            f"refusing to overwrite an existing replay at {output_dir}"
        )
    try:
        normaliser = DELIVERY_NORMALISERS.resolve(normaliser_id)
    except CoreError as error:
        raise DeliverNormaliserReplayError(str(error)) from error

    rows = _read_sealed_rows(outputs_path)
    replayed = [replay_row(row, normaliser=normaliser) for row in rows]

    slu_diagnostics = all(
        row["labels_changed"] is not None and row["fillers_changed"] is not None
        for row in replayed
    )
    source_sha256 = sha256_file(outputs_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    text = "\n".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) for row in replayed
    ) + "\n"
    outputs_target.write_text(text, encoding="utf-8", newline="\n")
    provenance = {
        "schema": RESULT_SCHEMA,
        "source": {"outputs_path": str(outputs_path), "sha256": source_sha256},
        "normaliser_id": normaliser_id,
        "normaliser_version": str(getattr(normaliser, "version", "")),
        "carrier_lock_key": str(getattr(normaliser, "carrier_lock_key", "")),
        "model_calls": 0,
        "rows": len(replayed),
        "rows_changed": sum(1 for row in replayed if row["changed"]),
        "rows_label_changed": (sum(1 for row in replayed if row["labels_changed"])
                               if slu_diagnostics else None),
        "rows_filler_changed": (sum(1 for row in replayed if row["fillers_changed"])
                                if slu_diagnostics else None),
        "entities_filler_changed": (sum(int(row["fillers_changed"]) for row in replayed)
                                    if slu_diagnostics else None),
        "rows_unparsed": (sum(1 for row in replayed if not row["applied"])
                          if slu_diagnostics else None),
        "rows_already_normalised": sum(
            1 for row in replayed if row["already_normalised"]
        ),
    }
    write_json_artifact(provenance_target, provenance)
    return provenance


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Offline re-application of a registered core.base.DELIVERY_NORMALISERS "
            "entry over a sealed run's delivered answers. Zero model contact; never "
            "touches the sealed input file."
        ),
    )
    parser.add_argument("--outputs", required=True, help="sealed outputs.jsonl path")
    parser.add_argument(
        "--normaliser",
        required=True,
        help="registered core.base.DELIVERY_NORMALISERS id",
    )
    parser.add_argument(
        "--output-dir", required=True, help="a new, not-yet-existing output directory",
    )
    args = parser.parse_args(argv)
    provenance = replay(
        outputs_path=Path(args.outputs),
        normaliser_id=args.normaliser,
        output_dir=Path(args.output_dir),
    )
    print(json.dumps(provenance, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "DeliverNormaliserReplayError",
    "RESULT_SCHEMA",
    "main",
    "replay",
    "replay_row",
]
