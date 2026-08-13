"""Offline materializer for the ``derived-candidates`` evidence source
(``core.evidence`` module docstring): the E-003R retrieval-gated-candidate
mechanism and the KC-Q3 two-pass machinery's shared evidence-preparation
step.

Model-free, deterministic, stdlib + repo modules only -- this module never
opens a model session, never mutates run/attempt state, and never reads a
carrier's frozen bytes outside what an already-registered evidence source
(``conec-contexts``/``conec-names``) itself resolves. It is a WRITER, not a
reader over run bundles (unlike ``analysis.context_dose``): it reads one
already-produced draft run's stitched hypotheses, retrieval-gates a per
-sample candidate vocabulary against them with ``core.retrieval.retrieve``,
and writes the top-k one-per-line under ``$SPEECHRL_DATA_DIR/derived/
evidence-candidates/<out-id>/<sample_id>.candidates.txt`` -- exactly the
layout ``core.evidence``'s ``derived-candidates`` source reads back at run
time -- plus one ``manifest.json`` per materialization id.

Pipeline, per sample:

1. **Draft hypothesis.** The newest ``attempt-*/`` subdirectory under
   ``$SPEECHRL_DATA_DIR/runs/<draft-run>/`` (by directory mtime, tie-broken
   by name -- deliberately NOT ``analysis.context_dose.find_completed_
   attempt``'s manifest-``created_at``/COMPLETED-status selection: a draft
   run supplying candidate material has no "comparability" concept to
   enforce, and may legitimately be an ABORTED attempt that still produced
   usable partial output) carries exactly one ``*.outputs.jsonl``
   (``core.driver.run.run_experiment``'s own naming,
   ``<run_id>.outputs.jsonl``). Each line is one JSON row; this module reads
   two required STRUCTURED fields off it directly -- ``sample_id`` and
   ``carrier_lock_key`` (the latter picks this sample's pack source below,
   step 2, straight off the draft run's own row, never guessed) -- and then,
   deliberately field-name-agnostic over everything else (never hardcoding
   ``"text"``), takes the LONGEST remaining string-valued field on that row
   as the row's hypothesis fragment. Rows sharing a ``sample_id`` are STITCHED --
   concatenated in file order, space-joined -- into that sample's one draft
   hypothesis (a no-op concatenation for today's one-row-per-sample driver
   output; forward-compatible with a future multi-row-per-sample writer).
2. **Candidate pool.** ``--pack-source`` names an already-registered,
   carrier-gated evidence source (``conec-contexts`` or ``conec-names``,
   resolved through the SAME ``core.base.EVIDENCE_SOURCES`` registry every
   run uses -- never a second, independently-drifting file-path
   construction) read for this sample's own ``carrier_lock_key`` (taken
   straight off its draft-run outputs row, never guessed). ``conec-contexts``
   splits its whitespace-delimited content into the unique tokens longer
   than 3 characters; ``conec-names`` takes one candidate per line, the name
   part before ``" - "`` (the ``"Name - Role/Affiliation"`` shape
   ``core.evidence``'s own module docstring documents).
3. **Retrieval gate.** Query terms are the draft hypothesis's own unique
   words longer than 3 characters. ``core.retrieval.retrieve(query_terms,
   candidates, k, min_score)`` -- already in this repo, never reimplemented
   here -- scores and keeps the top ``k`` candidates at or above
   ``min_score``, written one per line.

Deterministic end to end: every step above is a pure function of the input
bytes (draft outputs.jsonl content, pack file content, ``k``/``min_score``)
except the newest-attempt-directory selection, which is a function of
filesystem mtimes fixed once the caller's draft run finished -- re-running
this materializer against the SAME already-written inputs always produces
byte-identical candidate files. ``--dry-run`` computes and prints every
per-sample count without writing anything.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Mapping

from ..e0.artifacts import REPO_ROOT, sha256_file, write_json_artifact
from .base import EVIDENCE_SOURCES, CoreError, EvidenceError
from . import evidence as _evidence  # noqa: F401 (registration: conec-contexts/conec-names/...)
from .retrieval import RetrievalError, normalize_term, retrieve

MANIFEST_SCHEMA = "saea-derived-candidates-materialization-v1"

_SUPPORTED_PACK_SOURCES = ("conec-contexts", "conec-names")
_MIN_QUERY_TERM_LENGTH = 3


class MaterializeError(RuntimeError):
    """A draft run, a pack source, or a materialization request is malformed
    or cannot be resolved; also raised for a sample whose retrieval gate
    yields zero admissible candidates (refusing to write an empty candidates
    file no ``derived-candidates`` read at run time could ever accept --
    ``core.base.EvidenceItem.validate`` requires non-empty content, the same
    "refusing to emit an empty ... list" discipline ``core.evidence.
    _conec_bias_list`` already applies)."""


@dataclass(frozen=True)
class DraftSample:
    sample_id: str
    carrier_lock_key: str
    hypothesis: str


# ---------------------------------------------------------------------------
# Step 1: locate the newest attempt's outputs.jsonl and stitch hypotheses.
# ---------------------------------------------------------------------------


def find_newest_attempt_dir(run_dir: Path) -> Path:
    """The ``attempt-*/`` subdirectory under ``run_dir`` (a stable parent,
    ``core.driver.smoke.fresh_attempt_id``'s own convention) with the latest
    mtime, tie-broken by name for a fully deterministic result regardless of
    ``Path.iterdir()``'s unordered enumeration."""

    run_dir = Path(run_dir)
    if not run_dir.is_dir():
        raise MaterializeError(f"draft run directory does not exist: {run_dir}")
    attempt_dirs = [
        path for path in run_dir.iterdir() if path.is_dir() and path.name.startswith("attempt-")
    ]
    if not attempt_dirs:
        raise MaterializeError(f"no attempt-* subdirectories found under {run_dir}")
    return max(attempt_dirs, key=lambda path: (path.stat().st_mtime, path.name))


def find_outputs_file(attempt_dir: Path) -> Path:
    """The one ``*.outputs.jsonl`` under ``attempt_dir``
    (``core.driver.run.run_experiment``'s own ``<run_id>.outputs.jsonl``
    naming) -- fails closed on none (nothing to materialize from) or more
    than one (ambiguous; refuses rather than guessing)."""

    matches = sorted(Path(attempt_dir).glob("*.outputs.jsonl"))
    if not matches:
        raise MaterializeError(f"no *.outputs.jsonl found under {attempt_dir}")
    if len(matches) > 1:
        raise MaterializeError(
            f"multiple *.outputs.jsonl found under {attempt_dir}: {matches}; refusing to guess"
        )
    return matches[0]


def _longest_string_field(row: Mapping[str, object], *, exclude: frozenset[str], outputs_path: Path, line_number: int) -> str:
    candidates = [
        value
        for key, value in row.items()
        if key not in exclude and isinstance(value, str) and value
    ]
    if not candidates:
        raise MaterializeError(
            f"{outputs_path}:{line_number}: row has no non-empty string field besides "
            f"{sorted(exclude)}"
        )
    return max(candidates, key=len)


def load_draft_samples(outputs_path: Path) -> dict[str, DraftSample]:
    """Parse ``outputs_path`` into one :class:`DraftSample` per sample id
    (module docstring, step 1). Fails closed on invalid JSON, a non-object
    row, a missing/empty ``sample_id`` or ``carrier_lock_key``, a row with no
    usable hypothesis fragment, or two rows for the SAME sample id disagreeing
    on ``carrier_lock_key``."""

    outputs_path = Path(outputs_path)
    fragments: dict[str, list[str]] = {}
    carrier_lock_keys: dict[str, str] = {}
    with outputs_path.open(encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as error:
                raise MaterializeError(f"{outputs_path}:{line_number}: invalid JSON: {error}") from error
            if not isinstance(row, Mapping):
                raise MaterializeError(f"{outputs_path}:{line_number}: row is not a JSON object")
            sample_id = row.get("sample_id")
            if not isinstance(sample_id, str) or not sample_id:
                raise MaterializeError(f"{outputs_path}:{line_number}: row has no usable sample_id")
            carrier_lock_key = row.get("carrier_lock_key")
            if not isinstance(carrier_lock_key, str) or not carrier_lock_key:
                raise MaterializeError(
                    f"{outputs_path}:{line_number}: row for sample {sample_id!r} has no usable "
                    "carrier_lock_key"
                )
            previous = carrier_lock_keys.get(sample_id)
            if previous is not None and previous != carrier_lock_key:
                raise MaterializeError(
                    f"{outputs_path}: sample {sample_id!r} carries two different "
                    f"carrier_lock_key values ({previous!r} and {carrier_lock_key!r}) across rows"
                )
            carrier_lock_keys[sample_id] = carrier_lock_key
            # Both sample_id and carrier_lock_key are already-extracted
            # structured metadata (module docstring, step 1) -- excluded here
            # so a short test/real hypothesis can never lose the "longest
            # field" contest to its own carrier_lock_key string.
            fragment = _longest_string_field(
                row,
                exclude=frozenset({"sample_id", "carrier_lock_key"}),
                outputs_path=outputs_path,
                line_number=line_number,
            )
            fragments.setdefault(sample_id, []).append(fragment)
    if not fragments:
        raise MaterializeError(f"{outputs_path} contains no usable rows")
    return {
        sample_id: DraftSample(
            sample_id=sample_id,
            carrier_lock_key=carrier_lock_keys[sample_id],
            hypothesis=" ".join(parts),
        )
        for sample_id, parts in fragments.items()
    }


# ---------------------------------------------------------------------------
# Step 2: per-sample candidate pool from the pack source.
# ---------------------------------------------------------------------------


def _unique_words_over_min_length(text: str) -> list[str]:
    """Unique whitespace-delimited tokens longer than
    :data:`_MIN_QUERY_TERM_LENGTH` characters, in first-seen order (a
    deterministic function of ``text`` alone)."""

    seen: dict[str, None] = {}
    for token in text.split():
        if len(token) > _MIN_QUERY_TERM_LENGTH:
            seen.setdefault(token, None)
    return list(seen)


def pack_candidates(pack_source: str, content: str) -> list[str]:
    """The per-sample candidate vocabulary a pack file's raw content yields
    (module docstring, step 2). ``conec-contexts``: unique whitespace tokens
    longer than 3 characters. ``conec-names``: one candidate per line, the
    name part before ``" - "`` (``core.evidence``'s own ``_CONEC_NAMES_*``
    shape), blank lines skipped."""

    if pack_source == "conec-contexts":
        return _unique_words_over_min_length(content)
    if pack_source == "conec-names":
        candidates: list[str] = []
        for line in content.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            name = stripped.split(" - ", 1)[0].strip()
            if name:
                candidates.append(name)
        return candidates
    raise MaterializeError(
        f"unsupported --pack-source {pack_source!r}; expected one of {_SUPPORTED_PACK_SOURCES}"
    )


def _load_pack_content(
    lock: Mapping[str, object], root: Path, pack_source: str, sample_id: str, carrier_lock_key: str
) -> str:
    try:
        source = EVIDENCE_SOURCES.resolve(pack_source)
    except CoreError as error:
        raise MaterializeError(f"unknown --pack-source {pack_source!r}: {error}") from error
    try:
        items = source(lock, root, sample_id, carrier_lock_key)
    except EvidenceError as error:
        raise MaterializeError(
            f"cannot load pack source {pack_source!r} for sample {sample_id!r}: {error}"
        ) from error
    if not items:
        raise MaterializeError(
            f"pack source {pack_source!r} returned no evidence for sample {sample_id!r}"
        )
    return items[0].content


# ---------------------------------------------------------------------------
# Step 3: retrieve, write, and manifest.
# ---------------------------------------------------------------------------


def materialize_sample(
    draft: DraftSample, pack_content: str, pack_source: str, *, k: int, min_score: float
) -> list[tuple[str, float]]:
    """One sample's ``(candidate, score)`` top-``k`` (module docstring, step
    3) -- fails closed (never silently empty) when the draft hypothesis has
    no usable query terms or the pack yields no candidates at all."""

    query_terms = _unique_words_over_min_length(draft.hypothesis)
    if not query_terms:
        raise MaterializeError(
            f"sample {draft.sample_id!r}: draft hypothesis has no query terms longer than "
            f"{_MIN_QUERY_TERM_LENGTH} characters"
        )
    candidates = pack_candidates(pack_source, pack_content)
    if not candidates:
        raise MaterializeError(
            f"sample {draft.sample_id!r}: pack source {pack_source!r} produced no candidates"
        )
    # Correction semantics (2026-08-13 first-materialization read): a pack
    # term the draft already contains verbatim needs no supplying -- exact
    # matches score 1.0, flood the top-k, and the lexicographic tie-break
    # then returns the alphabet ("able", "across", ...), not the entities
    # the draft got WRONG. Supply only what the draft LACKS: drop candidates
    # whose normalized form already appears among the query terms, so every
    # surviving hit is a fuzzy/phonetic match -- the draft's garbled version
    # pointing at the pack's correct form.
    draft_forms = {normalize_term(term) for term in query_terms}
    candidates = [c for c in candidates if normalize_term(c) not in draft_forms]
    if not candidates:
        raise MaterializeError(
            f"sample {draft.sample_id!r}: every pack candidate already appears in the "
            "draft; nothing to supply"
        )
    try:
        return retrieve(query_terms, candidates, k, min_score)
    except RetrievalError as error:
        raise MaterializeError(f"sample {draft.sample_id!r}: {error}") from error


@dataclass(frozen=True)
class MaterializeResult:
    out_dir: Path
    manifest_path: Path | None
    per_sample: Mapping[str, Mapping[str, object]]


def materialize(
    *,
    lock: Mapping[str, object],
    root: Path,
    draft_run: str,
    pack_source: str,
    k: int,
    min_score: float,
    out_id: str,
    dry_run: bool = False,
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
) -> MaterializeResult:
    """Run the full pipeline (module docstring) for every sample id in the
    draft run's newest attempt, writing ``<out_id>/<sample_id>.candidates.txt``
    plus ``<out_id>/manifest.json`` under ``$SPEECHRL_DATA_DIR/derived/
    evidence-candidates/`` -- unless ``dry_run``, which computes and returns
    the identical per-sample counts without writing anything."""

    if not isinstance(out_id, str) or not out_id:
        raise MaterializeError(f"--out-id must be a non-empty string, got {out_id!r}")
    if pack_source not in _SUPPORTED_PACK_SOURCES:
        raise MaterializeError(
            f"--pack-source must be one of {_SUPPORTED_PACK_SOURCES}, got {pack_source!r}"
        )

    run_dir = Path(root) / "runs" / draft_run
    attempt_dir = find_newest_attempt_dir(run_dir)
    outputs_path = find_outputs_file(attempt_dir)
    drafts = load_draft_samples(outputs_path)

    out_dir = Path(root) / "derived" / "evidence-candidates" / out_id
    per_sample: dict[str, dict[str, object]] = {}
    written_lines: dict[str, list[str]] = {}
    for sample_id in sorted(drafts):
        draft = drafts[sample_id]
        pack_content = _load_pack_content(lock, root, pack_source, sample_id, draft.carrier_lock_key)
        retrieved = materialize_sample(draft, pack_content, pack_source, k=k, min_score=min_score)
        lines = [candidate for candidate, _score in retrieved]
        if not lines:
            raise MaterializeError(
                f"sample {sample_id!r}: retrieval gate admitted zero candidates at "
                f"k={k} min_score={min_score}; refusing to write an empty candidates file"
            )
        written_lines[sample_id] = lines
        per_sample[sample_id] = {
            "candidate_count": len(lines),
            "query_term_count": len(_unique_words_over_min_length(draft.hypothesis)),
            "pack_pool_size": len(pack_candidates(pack_source, pack_content)),
        }

    if dry_run:
        return MaterializeResult(out_dir=out_dir, manifest_path=None, per_sample=per_sample)

    out_dir.mkdir(parents=True, exist_ok=True)
    for sample_id, lines in written_lines.items():
        candidate_path = out_dir / f"{sample_id}.candidates.txt"
        candidate_path.write_text("".join(f"{line}\n" for line in lines), encoding="utf-8", newline="\n")
        per_sample[sample_id]["sha256"] = sha256_file(candidate_path)

    manifest_path = out_dir / "manifest.json"
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "generated_at": now().astimezone(timezone.utc).isoformat(),
        "materialization_id": out_id,
        "inputs": {
            "draft_run": draft_run,
            "attempt_dir": str(attempt_dir),
            "outputs_path": str(outputs_path),
            "pack_source": pack_source,
        },
        "params": {"k": k, "min_score": min_score},
        "samples": per_sample,
    }
    write_json_artifact(manifest_path, manifest)
    return MaterializeResult(out_dir=out_dir, manifest_path=manifest_path, per_sample=per_sample)


# ---------------------------------------------------------------------------
# CLI entry point (scripts/materialize_candidates.py is a thin wrapper).
# ---------------------------------------------------------------------------


def _cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="materialize-candidates",
        description=(
            "Offline materializer for the derived-candidates evidence source "
            "(core.evidence's own module docstring): retrieval-gates a per-sample "
            "candidate vocabulary against a draft run's own stitched hypothesis and "
            "writes the top-k one-per-line under $SPEECHRL_DATA_DIR/derived/"
            "evidence-candidates/<out-id>/<sample_id>.candidates.txt, plus a "
            "manifest.json. Model-free, deterministic, stdlib + repo modules only."
        ),
    )
    parser.add_argument(
        "--draft-run", required=True,
        help="run_id under $SPEECHRL_DATA_DIR/runs/<run_id>/ whose newest attempt's "
        "outputs.jsonl supplies the per-sample stitched hypothesis",
    )
    parser.add_argument(
        "--pack-source", required=True, choices=_SUPPORTED_PACK_SOURCES,
        help="registered evidence source naming this sample's candidate vocabulary pack",
    )
    parser.add_argument("--k", required=True, type=int, help="top-k candidates to keep per sample")
    parser.add_argument(
        "--min-score", required=True, type=float, help="minimum core.retrieval score, in [0, 1]"
    )
    parser.add_argument(
        "--out-id", required=True,
        help="materialization_id -- the derived-candidates evidence source's own "
        "evidence_materialization_id baseline-config value",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="print per-sample candidate counts without writing"
    )
    parser.add_argument(
        "--repo-root", type=Path, default=None, help="TEST-ONLY override of the study repo root"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    from ..data.lock import data_root, load_lock, umbrella_lock_path

    args = _cli_parser().parse_args(argv)
    repo_root = Path(args.repo_root) if args.repo_root else REPO_ROOT
    lock = load_lock(umbrella_lock_path(repo_root))
    root = data_root()
    try:
        result = materialize(
            lock=lock,
            root=root,
            draft_run=args.draft_run,
            pack_source=args.pack_source,
            k=args.k,
            min_score=args.min_score,
            out_id=args.out_id,
            dry_run=args.dry_run,
        )
    except (MaterializeError, RetrievalError) as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        return 1

    print(
        json.dumps(
            {
                "dry_run": bool(args.dry_run),
                "out_dir": str(result.out_dir),
                "manifest": str(result.manifest_path) if result.manifest_path else None,
                "samples": result.per_sample,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
