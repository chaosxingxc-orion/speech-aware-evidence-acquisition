"""Per-entry credit from sealed Solver citations: gap G1's reward edge, read.

Training-free RL assigns credit from a terminal reward back to the action
that earned it. Before ``rails.solver_citation`` the finest action a SLURP
trajectory could credit was "the whole supply block"; with the Solver's
``cited_value_ids`` sealed, every supplied entry has a trajectory-level
record of whether the answer that scored actually rested on it. This module
turns those sealed records plus per-row correctness into the smallest table
the construction lines need, and nothing more:

``value_id`` -- the supplied entry (a knowledge value id, a ``key:`` facet id
or any other evidence id the contact rendered);
``supplied`` -- rows on which the entry was rendered to the delivering Solver
contact;
``cited`` -- rows on which that contact cited it;
``cited_correct`` -- rows on which it was cited AND the row scored correct;
``supplied_uncited`` -- rows on which it was rendered and never cited
(``supplied - cited``).

Byte-reproducible by construction: entries are sorted by id, the document is
canonical JSON, and ``table_sha256`` is the digest of the entries alone, so
two readers over the same sealed rows produce the same bytes regardless of
input order. Model-free and gold-free: correctness arrives as a caller-supplied
``{sample_id: bool}`` derived from the official per-row score, and no text --
no utterance, answer or knowledge body -- is read or written.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

CREDIT_TABLE_SCHEMA = "saea-citation-credit-table-v1"
CREDIT_ROWS_SCHEMA = "saea-citation-credit-rows-v1"


class CitationCreditError(ValueError):
    """The sealed rows cannot be aggregated into one unambiguous table."""


def _canonical(document: object) -> str:
    return json.dumps(
        document, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CitationRow:
    """One delivered Solver contact: what it was shown, what it cited, how it scored."""

    sample_id: str
    supplied_value_ids: tuple[str, ...]
    cited_value_ids: tuple[str, ...]
    correct: bool

    def validate(self) -> "CitationRow":
        if not isinstance(self.sample_id, str) or not self.sample_id:
            raise CitationCreditError("a citation row needs a sample id")
        for name in ("supplied_value_ids", "cited_value_ids"):
            ids = getattr(self, name)
            if not isinstance(ids, tuple) or any(
                not isinstance(value, str) or not value for value in ids
            ):
                raise CitationCreditError(f"{name} must be a tuple of non-empty ids")
            if len(set(ids)) != len(ids):
                raise CitationCreditError(f"{name} repeats an id on row {self.sample_id!r}")
        unknown = set(self.cited_value_ids) - set(self.supplied_value_ids)
        if unknown:
            raise CitationCreditError(
                f"row {self.sample_id!r} cites {len(unknown)} id(s) it was never supplied; "
                "the seal refuses this, so such a row is not a sealed row"
            )
        if not isinstance(self.correct, bool):
            raise CitationCreditError(f"row {self.sample_id!r} correctness must be a bool")
        return self

    def as_json(self) -> dict[str, object]:
        return {
            "sample_id": self.sample_id,
            "supplied_value_ids": list(self.supplied_value_ids),
            "cited_value_ids": list(self.cited_value_ids),
            "correct": self.correct,
        }

    @classmethod
    def from_json(cls, document: Mapping[str, object]) -> "CitationRow":
        return cls(
            sample_id=str(document["sample_id"]),
            supplied_value_ids=tuple(document["supplied_value_ids"]),
            cited_value_ids=tuple(document["cited_value_ids"]),
            correct=document["correct"],
        ).validate()


def credit_table(rows: Iterable[CitationRow]) -> dict[str, object]:
    """The per-entry table over ``rows``; independent of the rows' order."""

    supplied: Counter[str] = Counter()
    cited: Counter[str] = Counter()
    cited_correct: Counter[str] = Counter()
    seen: set[str] = set()
    row_count = correct_count = citation_count = supplied_count = 0
    for row in rows:
        row.validate()
        if row.sample_id in seen:
            raise CitationCreditError(f"sample {row.sample_id!r} appears twice")
        seen.add(row.sample_id)
        row_count += 1
        correct_count += int(row.correct)
        supplied_count += len(row.supplied_value_ids)
        citation_count += len(row.cited_value_ids)
        supplied.update(row.supplied_value_ids)
        cited.update(row.cited_value_ids)
        if row.correct:
            cited_correct.update(row.cited_value_ids)
    entries = [
        {
            "value_id": value_id,
            "supplied": supplied[value_id],
            "cited": cited[value_id],
            "cited_correct": cited_correct[value_id],
            "supplied_uncited": supplied[value_id] - cited[value_id],
        }
        for value_id in sorted(supplied)
    ]
    return {
        "schema": CREDIT_TABLE_SCHEMA,
        "totals": {
            "rows": row_count,
            "rows_correct": correct_count,
            "entries": len(entries),
            "supplied_slots": supplied_count,
            "citations": citation_count,
        },
        "entries": entries,
        "table_sha256": _sha256(_canonical(entries)),
    }


def render_credit_table(table: Mapping[str, object]) -> str:
    """The table's canonical bytes (what a receipt pins)."""

    return _canonical(table)


def rows_from_outputs(
    outputs_path: Path, correctness: Mapping[str, bool]
) -> tuple[list[CitationRow], dict[str, int]]:
    """Read a sealed run's ``outputs.jsonl`` into citation rows.

    A row contributes exactly when its ``native_episode_receipt`` carries a
    ``solver_citations`` block AND a record for the DELIVERED Solver contact
    (``accepted_solver_receipt.final_contact.agent_contact_id``) whose parse
    is ``"ok"``; abstentions and non-authoritative finishes are counted under
    ``skipped``. Correctness must be present for every contributing row.
    """

    rows: list[CitationRow] = []
    counts = {"outputs_rows": 0, "rows": 0, "skipped": 0, "unarmed": 0}
    missing: list[str] = []
    with Path(outputs_path).open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            document = json.loads(line)
            counts["outputs_rows"] += 1
            receipt = document.get("native_episode_receipt") or {}
            block = receipt.get("solver_citations")
            if not isinstance(block, Mapping):
                counts["unarmed"] += 1
                continue
            accepted = (receipt.get("accepted_solver_receipt") or {}).get("final_contact") or {}
            delivered_contact = accepted.get("agent_contact_id")
            records = [
                record for record in block.get("contacts", [])
                if record.get("contact_id") == delivered_contact and record.get("parse") == "ok"
            ]
            if delivered_contact is None or len(records) != 1:
                counts["skipped"] += 1
                continue
            sample_id = str(document["sample_id"])
            if sample_id not in correctness:
                missing.append(sample_id)
                continue
            record = records[0]
            rows.append(
                CitationRow(
                    sample_id=sample_id,
                    supplied_value_ids=tuple(record["supplied_value_ids"]),
                    cited_value_ids=tuple(record["cited_value_ids"]),
                    correct=bool(correctness[sample_id]),
                ).validate()
            )
            counts["rows"] += 1
    if missing:
        raise CitationCreditError(
            f"{len(missing)} cited row(s) have no correctness entry; the table needs "
            "every delivered row's official per-row verdict"
        )
    return rows, counts


def load_correctness(path: Path) -> dict[str, bool]:
    """``{sample_id: bool}`` from a JSON object file."""

    document = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(document, Mapping) or not all(
        isinstance(key, str) and isinstance(value, bool) for key, value in document.items()
    ):
        raise CitationCreditError("correctness must be a JSON object of sample_id -> bool")
    return dict(document)


def load_rows(path: Path) -> list[CitationRow]:
    """Citation rows from a JSONL of ``CitationRow.as_json`` documents."""

    rows = []
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(CitationRow.from_json(json.loads(line)))
    return rows


def main(argv: Sequence[str] | None = None) -> int:
    """``python -m speech_aware_evidence_acquisition.analysis.citation_credit``.

    Either ``--rows rows.jsonl`` (one ``CitationRow`` document per line) or
    ``--outputs outputs.jsonl --correctness correct.json`` (a sealed run plus
    the official per-row verdicts). Writes the canonical table to ``--out``
    and prints counts and the table digest; never a text.
    """

    import argparse

    parser = argparse.ArgumentParser(description="Per-entry credit from sealed Solver citations.")
    parser.add_argument("--rows", type=Path)
    parser.add_argument("--outputs", type=Path)
    parser.add_argument("--correctness", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if (args.rows is None) == (args.outputs is None):
        parser.error("pass exactly one of --rows or --outputs")
    if args.outputs is not None and args.correctness is None:
        parser.error("--outputs requires --correctness")
    if args.rows is not None:
        rows, counts = load_rows(args.rows), {}
    else:
        rows, counts = rows_from_outputs(args.outputs, load_correctness(args.correctness))
    table = credit_table(rows)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render_credit_table(table) + "\n", encoding="utf-8")
    print(json.dumps({"totals": table["totals"], "table_sha256": table["table_sha256"],
                      **({"source_counts": counts} if counts else {})}, sort_keys=True))
    return 0


__all__ = [
    "CREDIT_ROWS_SCHEMA",
    "CREDIT_TABLE_SCHEMA",
    "CitationCreditError",
    "CitationRow",
    "credit_table",
    "load_correctness",
    "load_rows",
    "main",
    "render_credit_table",
    "rows_from_outputs",
]


if __name__ == "__main__":  # pragma: no cover - CLI entry
    raise SystemExit(main())
