#!/usr/bin/env python3
"""Model-free gate over the Stage-2 results ledger (owner Decision 14-Q, 2026-09-09).

``docs/results/stage2-results-ledger.json`` claims, one row per cell, what each
Stage-2 cell measured, under which rule, against which comparator, with which
margin, and what the verdict's own first line called it. A ledger that nobody
re-derives is prose. This script re-derives four of its claims from the
repository, and reports three cross-checks it deliberately does not fix.

**Enforced (a failure exits non-zero).**

1. **Every run id is registered, and a decided cell's run id is closed.** Each
   ``run_ids`` entry must appear in a contract table of ``docs/exposure-ledger.md``
   -- parsed with the repository's own parser, ``contracts._parse_ledger_tables``,
   so a row hidden in a comment or a fence is exactly as invisible here as it is
   to the frozen-core gate. For a row that is not ``pending`` the ledger must
   also record the run as finished: a closure block ``**<RUN-ID> COMPLETED|
   CLOSED|FINALIZED|TERMINAL`` in the ledger's prose, or a closure token
   (``COMPLETED``, ``FINALIZED``, ``FLOWN AND COMPLETE``, ``ROW CLOSED``) in the
   row's own ``scope`` or ``notes`` cell. A ``pending`` row is required to be
   registered and is reported, never failed, whatever its closure state.

2. **Every cited path exists.** Every ``source`` field of every value, plus
   ``verdict_note``, ``receipt`` and ``preregistration``, resolves to a file or a
   directory in this checkout. This is what makes "no number may be computed
   anew" auditable: a number whose source path is gone is a number nobody can
   re-read.

3. **The STATUS word is the verdict's own.** When a row says its status comes
   from the verdict's first line (``status_source`` ``h1`` or
   ``first-paragraph``), that line is parsed here -- the H1, then the first
   non-empty paragraph after it -- and the row's ``status`` must appear in it.
   Rows whose status lives further down the verdict declare where, and are
   reported under cross-check A rather than failed: the verdict is the
   authority, and this script's job is to say so out loud, not to pretend the
   word was in the title.

4. **The ledger's own tallies are the rows'.** ``carrier_summary`` must count
   the rows it says it counts.

**Reported, never fixed.**

A. **Verdicts whose first line lacks a status word.** For a note this ledger
   cites, the authority is the row's own ``status_source``: a row that says its
   status came from "section: Verdict" is attesting that the first line did not
   carry it. For a window verdict note the ledger does NOT cite, a lexical scan
   of the first line is all there is -- and it is only a scan, which is why the
   cited half does not rely on it ("closed-list" and "replicate null" put a
   status word into a title that is not a status).

B. **Cells with a closed ledger row and no verdict note.** Every closed
   exposure-ledger flight row dated in the ledger's window whose run id is named
   in no ``*-verdict.md`` / ``*-redecision.md`` note under ``docs/readiness/``.

C. **Harness-admission entries with no ledger row**, and any entry of
   ``docs/receipts/harness-admission.json`` that this ledger carries no row for.

D. **Umbrella disagreements.** Where a row declares ``umbrella_values``, each
   value must appear somewhere in the umbrella page
   ``wiki/experiments/speech-aware-evidence-acquisition/published-baselines.md``.
   A value the umbrella does not carry is a finding: either the umbrella states
   a different headline for the same cell, or it carries no row for that cell at
   all. **This script never edits the umbrella.** If the umbrella is not
   reachable from this checkout (a worktree outside ``studies/``), that is
   itself reported and the comparison is skipped.

Zero model contacts, zero GPU, zero tool and embedder contacts, no network, no
``SPEECHRL_DATA_DIR`` read.

Flags: ``--repo-root``, ``--ledger``, ``--umbrella``, ``--json``.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT_DEFAULT = Path(__file__).resolve().parents[2]
LEDGER_JSON_DEFAULT = Path("docs/results/stage2-results-ledger.json")
EXPOSURE_LEDGER = Path("docs/exposure-ledger.md")
HARNESS_ADMISSION = Path("docs/receipts/harness-admission.json")
READINESS = Path("docs/readiness")

UMBRELLA_CANDIDATES = (
    Path("../../wiki/experiments/speech-aware-evidence-acquisition/published-baselines.md"),
    Path("../../../exploring-l4-intelligence/wiki/experiments/speech-aware-evidence-acquisition/published-baselines.md"),
)

# A closure block in the exposure ledger's prose: "**<RUN-ID> COMPLETED - ...".
_PROSE_CLOSURE = re.compile(
    r"\*\*(SAEA-[A-Z0-9\-]+)[^*]{0,80}?\b(COMPLETED|CLOSED|FINALIZED|TERMINAL)\b"
)
# A closure token inside the row's own cells. Bare "CLOSED" is deliberately not
# accepted: run ids such as SAEA-SLURP-DEV1000-CLOSED-LIST-... contain the word,
# so only the dated form "CLOSED 2026-09-08" counts.
_ROW_CLOSURE = re.compile(
    r"(?<![A-Z-])(COMPLETED|FINALIZED)(?![A-Z-])"
    r"|FLOWN AND COMPLETE"
    r"|ROW CLOSED"
    r"|\bCLOSED\s+20\d\d-\d\d-\d\d"
)

_STATUS_WORDS = (
    "ALIGNED",
    "ADMITTED",
    "REPLICATED",
    "NEUTRAL",
    "NULL",
    "NOT ADMITTED",
    "REJECTED",
    "HARMFUL",
    "CLOSED",
    "NOT ALIGNED",
    "EXCLUDED",
    "REJECT",
    "FAIL",
)

# Flight-shaped run ids only: preparation, smoke, prompt-fit, media-build and
# wire-check rows are not cells and are not expected to carry a verdict note.
_NOT_A_CELL = (
    "SMOKE",
    "PROMPT-FIT",
    "TOKEN-MATCH",
    "PLACEMENT-FIT",
    "PREPROCESS",
    "-MF-",
    "MF7",
    "MF8",
    "MF9",
    "MF10",
    "VECTORS",
    "SNAPSHOT",
    "ROSTER",
    "PACKETS",
    "WIRE-CHECK",
    "VERDICT",
)


class ResultsLedgerCheckError(RuntimeError):
    """The check could not run at all -- a missing ledger, an unparsable file."""


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _parse_exposure_ledger(repo_root: Path) -> tuple[dict[str, dict[str, str]], set[str]]:
    """Return ``({run_id: row}, {run ids closed in the ledger's prose})``.

    The table parser is the repository's own (``contracts._parse_ledger_tables``),
    which is what the frozen-core gate reads, so this check and that gate agree
    on what a registration is.
    """

    src = repo_root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    try:
        from speech_aware_evidence_acquisition.contracts import (  # noqa: PLC0415
            _parse_ledger_tables,
        )
    except Exception as exc:  # pragma: no cover - import environment problem
        raise ResultsLedgerCheckError(
            f"cannot import the repository's exposure-ledger parser from {src}: {exc}"
        ) from exc

    path = repo_root / EXPOSURE_LEDGER
    if not path.is_file():
        raise ResultsLedgerCheckError(f"missing {EXPOSURE_LEDGER}")
    text = _read(path)
    rows: dict[str, dict[str, str]] = {}
    for row in _parse_ledger_tables(text):
        run_id = row.get("run/experiment id", "").strip()
        if run_id:
            rows.setdefault(run_id, row)
    prose_closed = {m.group(1) for m in _PROSE_CLOSURE.finditer(text)}
    return rows, prose_closed


def _row_is_closed(row: dict[str, str], prose_closed: set[str]) -> bool:
    if row.get("run/experiment id", "") in prose_closed:
        return True
    blob = f"{row.get('scope', '')} {row.get('notes', '')}"
    return bool(_ROW_CLOSURE.search(blob))


def _first_line(text: str) -> str:
    """The verdict's first line: its H1, plus the first paragraph after it.

    Markdown wraps, so "the first line" of a verdict note is the first
    PARAGRAPH -- contiguous non-empty lines -- and not the first physical line.
    """

    lines = text.splitlines()
    head = ""
    i = 0
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i < len(lines) and lines[i].lstrip().startswith("#"):
        head = lines[i].strip()
        i += 1
    while i < len(lines) and not lines[i].strip():
        i += 1
    para: list[str] = []
    while i < len(lines) and lines[i].strip():
        para.append(lines[i].strip())
        i += 1
    return f"{head} {' '.join(para)}".strip()


def _status_words_in(line: str) -> list[str]:
    upper = line.upper()
    found = []
    for word in _STATUS_WORDS:
        if re.search(r"(?<![A-Z-])" + re.escape(word) + r"(?![A-Z-])", upper):
            found.append(word)
    # "NOT ADMITTED" implies "ADMITTED"; keep the longer form only.
    if "NOT ADMITTED" in found and "ADMITTED" in found:
        found.remove("ADMITTED")
    if "NOT ALIGNED" in found and "ALIGNED" in found:
        found.remove("ALIGNED")
    return found


def _collect_sources(node: Any, out: set[str]) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "source" and isinstance(value, str) and value:
                out.add(value)
            elif key in {"verdict_note", "receipt", "preregistration"} and isinstance(value, str) and value:
                out.add(value)
            else:
                _collect_sources(value, out)
    elif isinstance(node, list):
        for item in node:
            _collect_sources(item, out)


def _umbrella_carries(text: str, value: str) -> bool:
    """Does the umbrella page state this headline?

    Trailing zeros are formatting, not disagreement: the umbrella writes a tier
    row as ``79.6`` where the study verdict writes ``79.60``, and calling that a
    disagreement would bury the real ones. Everything else must match
    character for character, and the match may not run into a further digit, so
    ``65.0`` never matches ``65.05``.
    """

    candidates = {value}
    if "." in value:
        trimmed = value.rstrip("0").rstrip(".")
        if trimmed:
            candidates.add(trimmed)
    return any(
        re.search(re.escape(candidate) + r"(?!\d)", text) for candidate in candidates
    )


def _find_umbrella(repo_root: Path, override: Path | None) -> Path | None:
    if override is not None:
        return override if override.is_file() else None
    for candidate in UMBRELLA_CANDIDATES:
        path = (repo_root / candidate).resolve()
        if path.is_file():
            return path
    return None


def evaluate(repo_root: Path, ledger_path: Path, umbrella_override: Path | None) -> dict[str, Any]:
    ledger_file = repo_root / ledger_path
    if not ledger_file.is_file():
        raise ResultsLedgerCheckError(f"missing {ledger_path}")
    try:
        doc = json.loads(_read(ledger_file))
    except json.JSONDecodeError as exc:
        raise ResultsLedgerCheckError(f"{ledger_path} is not valid JSON: {exc}") from exc

    rows = doc.get("rows")
    if not isinstance(rows, list) or not rows:
        raise ResultsLedgerCheckError(f"{ledger_path} carries no rows")

    ledger_rows, prose_closed = _parse_exposure_ledger(repo_root)
    failures: list[str] = []
    findings: list[str] = []

    # ---------------------------------------------------------------- rule 1
    for row in rows:
        cell = row.get("cell_id", "<unnamed>")
        pending = bool(row.get("pending"))
        for run_id in row.get("run_ids", []):
            entry = ledger_rows.get(run_id)
            if entry is None:
                failures.append(
                    f"{cell}: run id {run_id} has no row in {EXPOSURE_LEDGER}"
                )
                continue
            closed = _row_is_closed(entry, prose_closed)
            if not pending and not closed:
                failures.append(
                    f"{cell}: run id {run_id} is registered but the ledger does not "
                    f"record it as closed"
                )
            if pending and closed:
                findings.append(
                    f"pending row {cell} names run id {run_id}, whose ledger row IS "
                    f"closed (a model-free preparation row, not the pending flight)"
                )

    # ---------------------------------------------------------------- rule 2
    cited: set[str] = set()
    _collect_sources(doc, cited)
    missing = sorted(p for p in cited if not (repo_root / p).exists())
    for path in missing:
        failures.append(f"cited source path does not exist: {path}")

    # ---------------------------------------------------------------- rule 3
    status_checked = 0
    for row in rows:
        cell = row.get("cell_id", "<unnamed>")
        note = row.get("verdict_note")
        source = row.get("status_source", "")
        status = row.get("status", "")
        if not note or source not in {"h1", "first-paragraph"}:
            continue
        note_path = repo_root / note
        if not note_path.is_file():
            continue  # already a rule-2 failure
        first = _first_line(_read(note_path))
        status_checked += 1
        head = status.split("(")[0].strip().rstrip(".").upper()
        if head and head not in first.upper():
            failures.append(
                f"{cell}: status {status!r} is declared to come from the verdict's "
                f"first line, but that line does not contain it: {first[:160]!r}"
            )

    # ------------------------------------------------------------ finding A
    # Two sources, because neither alone is honest. For a note this ledger
    # cites, the AUTHORITY is the row's own ``status_source``: a row that says
    # its status came from "section: Verdict" is telling us the first line did
    # not carry it, and no lexical scan overrides that. For a note the ledger
    # does not cite, a lexical scan is all there is -- and it is only a scan:
    # "closed-list" and "replicate null" put a status word in a title that is
    # not a status, which is exactly why the cited half does not rely on it.
    verdict_notes = {
        path: _read(path)
        for path in sorted((repo_root / READINESS).glob("2026-09-0[456789]*.md"))
        if "verdict" in path.name or "redecision" in path.name
    }
    statusless: list[str] = []
    for row in rows:
        rel = row.get("verdict_note")
        source = row.get("status_source", "")
        if not rel or source in {"h1", "first-paragraph"}:
            continue
        if not (repo_root / rel).is_file():
            continue
        statusless.append(rel)
        findings.append(
            f"cross-check A: {rel} -- the first line does not carry the status word; "
            f"this ledger takes {row.get('status')!r} from {source!r} for "
            f"{row.get('cell_id')}"
        )
    cited_notes = {r.get("verdict_note") for r in rows if r.get("verdict_note")}
    for path, text in verdict_notes.items():
        rel = path.relative_to(repo_root).as_posix()
        if rel in cited_notes:
            continue
        if _status_words_in(_first_line(text)):
            continue
        statusless.append(rel)
        findings.append(
            f"cross-check A: {rel} -- the first line carries no status word, and this "
            f"ledger carries no row for it"
        )

    # ---------------------------------------------------------------- rule 4
    tallies = {
        "admitted": 0, "aligned": 0, "neutral": 0, "rejected": 0,
        "instrument": 0, "closed-unread": 0, "pending": 0,
    }
    for row in rows:
        tally = row.get("tally")
        if tally in tallies:
            tallies[tally] += 1
    for summary in doc.get("carrier_summary", []):
        carrier = summary.get("carrier")
        sub = [r for r in rows if r.get("carrier") == carrier]
        for key, field in (
            ("admitted", "admitted"), ("aligned", "aligned"), ("neutral", "neutral"),
            ("rejected", "rejected"), ("instrument", "instrument"),
            ("closed-unread", "closed_unread"), ("pending", "pending"),
        ):
            claimed = summary.get(field)
            actual = sum(1 for r in sub if r.get("tally") == key)
            if claimed is not None and claimed != actual:
                failures.append(
                    f"carrier_summary {carrier}: {field} says {claimed}, the rows say {actual}"
                )
        claimed_rows = summary.get("rows")
        if claimed_rows is not None and claimed_rows != len(sub):
            failures.append(
                f"carrier_summary {carrier}: rows says {claimed_rows}, the ledger carries {len(sub)}"
            )
        claimed_flown = summary.get("cells_flown")
        actual_flown = sum(1 for r in sub if r.get("flown"))
        if claimed_flown is not None and claimed_flown != actual_flown:
            failures.append(
                f"carrier_summary {carrier}: cells_flown says {claimed_flown}, the rows say {actual_flown}"
            )

    # ------------------------------------------------------------ finding B
    window_start = "2026-09-04"
    closed_without_verdict: list[str] = []
    for run_id, entry in sorted(ledger_rows.items()):
        if entry.get("date", "") < window_start:
            continue
        if any(token in run_id for token in _NOT_A_CELL):
            continue
        try:
            calls = float(entry.get("calls", "0").replace(",", ""))
        except ValueError:
            calls = 0.0
        if calls <= 0:
            continue
        if not _row_is_closed(entry, prose_closed):
            continue
        if any(run_id in text for text in verdict_notes.values()):
            continue
        closed_without_verdict.append(run_id)
        findings.append(
            f"cross-check B: {run_id} has a closed exposure-ledger row and no verdict note"
        )

    # ------------------------------------------------------------ finding C
    admission_path = repo_root / HARNESS_ADMISSION
    admission_rows: list[str] = []
    if admission_path.is_file():
        admission = json.loads(_read(admission_path))
        ledger_cells = {rid for row in rows for rid in row.get("run_ids", [])}
        for entry in admission.get("entries", []):
            row_id = entry.get("row", "")
            admission_rows.append(row_id)
            if row_id not in ledger_rows:
                findings.append(
                    f"cross-check C: harness-admission entry {row_id} has no row in {EXPOSURE_LEDGER}"
                )
            if row_id not in ledger_cells:
                findings.append(
                    f"cross-check C: harness-admission entry {row_id} has no row in this results ledger"
                )
    else:
        findings.append(f"cross-check C: {HARNESS_ADMISSION} is missing")

    # ------------------------------------------------------------ finding D
    umbrella = _find_umbrella(repo_root, umbrella_override)
    umbrella_compared = 0
    umbrella_disagreements: list[str] = []
    if umbrella is None:
        findings.append(
            "cross-check D: the umbrella page published-baselines.md is not reachable "
            "from this checkout, so the headline comparison was skipped"
        )
    else:
        umbrella_text = _read(umbrella)
        for row in rows:
            values = row.get("umbrella_values") or []
            if not values:
                continue
            umbrella_compared += 1
            for value in values:
                if not _umbrella_carries(umbrella_text, value):
                    umbrella_disagreements.append(f"{row.get('cell_id')}: {value}")
                    findings.append(
                        f"cross-check D: the umbrella page does not carry {value!r}, which "
                        f"this ledger reports for {row.get('cell_id')}"
                    )

    return {
        "passed": not failures,
        "failures": failures,
        "findings": findings,
        "rows": len(rows),
        "run_ids": sorted({rid for r in rows for rid in r.get("run_ids", [])}),
        "cited_paths": len(cited),
        "status_first_line_checked": status_checked,
        "verdicts_without_a_first_line_status": sorted(set(statusless)),
        "closed_without_verdict": closed_without_verdict,
        "harness_admission_rows": admission_rows,
        "umbrella": str(umbrella) if umbrella else None,
        "umbrella_rows_compared": umbrella_compared,
        "umbrella_disagreements": umbrella_disagreements,
        "tallies": tallies,
    }


def main(argv: list[str] | None = None) -> int:
    # Findings quote verdict text, which carries en dashes and minus signs; the
    # default console encoding on the primary dev machine is not UTF-8.
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):  # pragma: no cover - exotic streams
                pass

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT_DEFAULT)
    parser.add_argument("--ledger", type=Path, default=LEDGER_JSON_DEFAULT)
    parser.add_argument("--umbrella", type=Path, default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    try:
        data = evaluate(args.repo_root.resolve(), args.ledger, args.umbrella)
    except ResultsLedgerCheckError as exc:
        print(f"results ledger check: FAIL: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(data, indent=2, sort_keys=True))
        return 0 if data["passed"] else 1

    for failure in data["failures"]:
        print(f"results ledger check: FAIL: {failure}")
    for finding in data["findings"]:
        print(f"results ledger check: finding: {finding}")
    if data["failures"]:
        print(f"results ledger check: FAIL ({len(data['failures'])} failure(s))")
        return 1

    print(
        "results ledger check: PASS "
        f"({data['rows']} row(s), {len(data['run_ids'])} run id(s) registered and closed, "
        f"{data['cited_paths']} cited path(s) present, "
        f"{data['status_first_line_checked']} status word(s) re-parsed from the verdict's "
        f"first line, {data['umbrella_rows_compared']} row(s) compared against the umbrella, "
        f"{len(data['findings'])} finding(s) reported)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
