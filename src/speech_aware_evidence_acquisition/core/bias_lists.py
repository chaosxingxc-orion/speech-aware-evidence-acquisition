"""B-2a bias-list support: deterministic entity extraction + the distractor-
only set difference (design: docs/readiness/2026-08-09-exploration-plan.md
section 3b "Leakage note on the E-21 bias lists").

The shipped Earnings-21 ``bias_lists/oracle_list.txt`` is REFERENCE-DERIVED
(its own README: "contains words and phrases found in the Earnings21
reference transcripts") and this study's contract forbids gold/reference
material from ever entering runtime. ``distractor_list.txt`` is a strict
superset of the oracle list (oracle plus ~769 Fortune-500/CEO names absent
from Earnings-21) and inherits the same problem verbatim.

This module never returns oracle-list content to a caller. It reads the
oracle list ONLY to compute a set difference (:func:`distractor_only_terms`)
and asserts, before returning anything, that the result has an EMPTY
intersection with the oracle list (:func:`_assert_no_oracle_overlap`) --
independently of the filtering loop itself, so a future refactor that breaks
the filter is still caught here, not shipped silently.

Two pure functions do the real work, both stdlib-only (``re``/``pathlib``),
no model, no network:

* :func:`extract_bias_candidates` -- deterministic candidate-entity
  extraction from arbitrary evidence text (used on the call's own ConEC
  context materials, ``core.evidence._conec_contexts``'s own content).
  Verified against the real, materialized ConEC corpus (44 Earnings-21
  calls, read-only) before this module was written: every one of those 44
  files is a lowercase, one-token-per-line word list with a constant
  trailing "1" marker and zero uppercase characters anywhere -- ConEC's own
  README calls these "biasing word lists ... extracted from the PDF files,
  with stop words, numerical values and irrelevant pages removed" (i.e.
  ConEC already did stopword/number/junk-page filtering). Only the
  ``listline`` pattern below actually fires on that real corpus today; the
  ``roster``/``span``/``ticker`` patterns exist for robustness against a
  differently-shaped evidence text (participant-roster "Name - Affiliation"
  lines, capitalized company/person spans, bare ticker symbols) without ever
  requiring a model or a hand-maintained name list.
* :func:`distractor_only_terms` -- the set difference
  ``distractor_list.txt - oracle_list.txt``, computed at LOAD TIME from the
  two shipped files (never a hand-copied name list in this module).

Both feed :mod:`core.evidence`'s ``conec-bias-list``/``distractor-only-bias-
list`` sources, which wrap the result as ONE :class:`~.base.EvidenceItem`
each, newline-joined under a header, capped by ``bias_list_max_entries``
(config knob, default :data:`DEFAULT_BIAS_LIST_MAX_ENTRIES`).

KNOWN GAP (read before wiring an actual model run of B-2a arm 2): the D1
evidence-identity gate (``contracts.gate_evidence_identity`` /
``core.driver.run_experiment``'s ``evidence_relpaths``/``evidence_contents``
binding) currently assumes an evidence source's ``EvidenceItem.content`` is
BYTE-IDENTICAL to the raw D1-tracked file at
``core.evidence.evidence_file_relpath``'s path -- true for
``_conec_contexts`` (pure passthrough) and thus verified today by
``tests/unit/test_driver.py::test_run_experiment_wires_evidence_relpaths_
into_the_evidence_identity_gate``'s ``evidence_contents == {..., "sha256(raw
file)"}`` assertion. ``conec-bias-list`` (arm 2) deliberately returns a
TRANSFORMED (extracted, capped, header-wrapped) content, so
``verify_evidence_content_identity`` will refuse a real gated run with a
content-identity-drift error the moment this arm supplies non-empty
evidence, until ``core.driver.run_experiment``'s evidence-identity binding
is made evidence-source-aware (or a new D1 layer is registered for the
derived content) -- a separate, reviewed change, out of this "no model
touch" task's scope. ``distractor-only-bias-list`` (arm 3) is unaffected by
its OWN content only in the sense that its content is identical across every
sample; ``run_experiment`` still independently re-derives
``evidence_relpaths[sample_id]`` from the CARRIER alone (never from the
evidence source), so it too will be checked against the per-sample ConEC
context file's D1 hash and will also fail the SAME way. Flagged here, in the
config fragments, and in the engineering report -- fix before an actual B-2a
model run is attempted.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Mapping

from ..data.lock import asset_dir, lock_entry
from ..e0.artifacts import sha256_file
from .base import EvidenceError

DEFAULT_BIAS_LIST_MAX_ENTRIES = 100

ORACLE_LIST_FILENAME = "oracle_list.txt"
DISTRACTOR_LIST_FILENAME = "distractor_list.txt"
_BIAS_LISTS_CARRIER_LOCK_KEY = "earnings21-original"
_BIAS_LISTS_SUBDIR = "bias_lists"

# One combined, named-group regex, scanned once left-to-right so matches come
# out in DOCUMENT order regardless of which alternative fired (never a
# per-category re-ordering) -- see the module docstring for why only
# ``listline`` fires on the real, materialized ConEC corpus today.
#
#   roster   -- a whole line shaped like ConEC's own participant_names/*.txt
#               format ("Brett Ponton - President and CEO"): a capitalized
#               name run, " - ", then anything (affiliation).
#   span     -- 2+ consecutive Titlecase/ALLCAPS words elsewhere in the text
#               ("Goldman Sachs & Co", "New York") -- company/person names in
#               ordinary capitalized prose; a continuation word may also
#               start with "&" (the connector in "Goldman Sachs & Co").
#   listline -- ConEC's OWN shipped shape: a single lowercase (or any-case)
#               token, length >= 3, immediately followed on the same line by
#               nothing but a bare integer (the constant "1" marker every
#               real ConEC context line carries). The lookahead means the
#               match itself never consumes the trailing count.
#   ticker   -- an isolated 2-5 letter ALL-CAPS token, standing alone (not
#               already covered by ``span``) -- e.g. a bare stock ticker.
_TERM_PATTERN = re.compile(
    r"""
    (?P<roster>^[A-Z][A-Za-z.'-]*(?:\s[A-Z][A-Za-z.'-]*)*\s-\s.+$)
  | (?P<span>[A-Z][A-Za-z.&'-]*(?:\s[A-Z&][A-Za-z.&'-]*){1,})
  | (?P<listline>^[A-Za-z][A-Za-z0-9'-]{2,}(?=[ \t]+\d+[ \t]*$))
  | (?P<ticker>\b[A-Z]{2,5}\b)
    """,
    re.MULTILINE | re.VERBOSE,
)
_WHITESPACE_RUN = re.compile(r"\s+")


def _validate_max_entries(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise EvidenceError(f"bias_list_max_entries must be a positive integer, got {value!r}")
    return value


def resolve_bias_list_max_entries(values: Mapping[str, object] | None) -> int:
    """Read ``bias_list_max_entries`` from a run's composed config (the
    ``values`` mapping ``core.driver.run_experiment`` already threads to
    every registered evidence source), defaulting to
    :data:`DEFAULT_BIAS_LIST_MAX_ENTRIES` when absent or when no config was
    supplied at all (e.g. a caller resolving an evidence source directly, the
    same "no config -> the pre-config default" fallback
    ``core.config.runtime_receipt_relpath`` already applies)."""

    if values is None:
        return DEFAULT_BIAS_LIST_MAX_ENTRIES
    if not isinstance(values, Mapping):
        raise EvidenceError(f"composed config values must be a mapping, got {type(values).__name__}")
    return _validate_max_entries(values.get("bias_list_max_entries", DEFAULT_BIAS_LIST_MAX_ENTRIES))


def extract_bias_candidates(
    text: str, max_entries: int = DEFAULT_BIAS_LIST_MAX_ENTRIES
) -> list[str]:
    """Deterministic candidate-entity extraction (module docstring for the
    four patterns and their priority). Same input -> byte-identical output:
    a single left-to-right regex scan, case-insensitive de-duplication that
    keeps the FIRST-SEEN casing, first-appearance order preserved, truncated
    to ``max_entries``. Never touches a filesystem or a network; never calls
    a model."""

    if not isinstance(text, str):
        raise EvidenceError(f"bias-candidate extraction requires text, got {type(text).__name__}")
    _validate_max_entries(max_entries)
    seen: set[str] = set()
    candidates: list[str] = []
    for match in _TERM_PATTERN.finditer(text):
        term = _WHITESPACE_RUN.sub(" ", match.group(match.lastgroup).strip())
        if not term:
            continue
        key = term.casefold()
        if key in seen:
            continue
        seen.add(key)
        candidates.append(term)
        if len(candidates) >= max_entries:
            break
    return candidates


def format_bias_list_content(candidates: list[str], header: str) -> str:
    """One evidence item's content: a clear header line, then the candidates,
    one per line, newline-joined (no trailing newline)."""

    if not isinstance(header, str) or not header.strip():
        raise EvidenceError("bias list header must be a non-empty string")
    if not candidates:
        raise EvidenceError("bias list candidates must be non-empty")
    return header + "\n" + "\n".join(candidates)


def _bias_lists_dir(lock: Mapping[str, object], root: Path) -> Path:
    return asset_dir(lock, _BIAS_LISTS_CARRIER_LOCK_KEY, root) / _BIAS_LISTS_SUBDIR


def bias_list_relpath(lock: Mapping[str, object], filename: str) -> str:
    """The SAME relative-path convention ``core.evidence.evidence_file_
    relpath`` already uses for the ConEC evidence layer, applied to
    ``earnings21-original``'s OWN asset root (bias_lists ship as part of the
    Earnings-21 release itself, not under the separate ``conec`` lock key)."""

    entry = lock_entry(lock, _BIAS_LISTS_CARRIER_LOCK_KEY)
    local_subdir = entry.get("local_subdir")
    if not isinstance(local_subdir, str) or not local_subdir:
        raise EvidenceError(
            f"asset {_BIAS_LISTS_CARRIER_LOCK_KEY!r} lacks a usable local_subdir in the lock"
        )
    return f"{local_subdir.rstrip('/')}/{_BIAS_LISTS_SUBDIR}/{filename}"


def _load_term_list(path: Path, label: str) -> list[str]:
    if not path.is_file():
        raise EvidenceError(f"{label} missing: {path}")
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        raise EvidenceError(f"cannot read {label} {path}: {error}") from error
    terms = [line.strip() for line in lines if line.strip()]
    if not terms:
        raise EvidenceError(f"{label} is empty: {path}")
    return terms


def _assert_no_oracle_overlap(candidates: list[str], oracle_terms: list[str]) -> None:
    """Independent re-verification (task requirement): ``candidates`` must
    have an EMPTY intersection with ``oracle_terms``, re-checked separately
    from whatever filtering loop produced ``candidates`` -- a future
    refactor that accidentally drops the exclusion guard is caught HERE,
    never shipped as a silent leak of reference-derived content. Refuses
    (:class:`EvidenceError`) rather than silently drop the leaking entries:
    an unsound distractor-only computation is a defect to fix, not paper
    over."""

    oracle_keys = {term.casefold() for term in oracle_terms}
    leaked = sorted({c for c in candidates if c.casefold() in oracle_keys})
    if leaked:
        raise EvidenceError(
            f"distractor-only bias list leaks {len(leaked)} oracle-list entries "
            f"after set difference (e.g. {leaked[:5]!r}); refusing to return "
            "reference-derived content"
        )


def distractor_only_terms(
    lock: Mapping[str, object],
    root: Path,
    max_entries: int = DEFAULT_BIAS_LIST_MAX_ENTRIES,
) -> tuple[list[str], dict[str, object]]:
    """The set difference ``distractor_list.txt - oracle_list.txt``, computed
    at LOAD TIME from the two shipped files (never a hand-copied name list in
    this module, per the task's own non-negotiable constraint). Case-
    insensitive de-duplication, ``distractor_list.txt``'s own file order
    preserved (empirically near-uniformly scattered across the alphabet, not
    clustered -- so a simple prefix cap stays representative), independently
    re-verified for oracle overlap (see _assert_no_oracle_overlap) before
    any truncation. Returns ``(capped_terms, facts)`` where ``facts`` carries
    the two source files' own relpath/sha256 plus the FULL (uncapped)
    distractor-only count, for evidence provenance."""

    _validate_max_entries(max_entries)
    bias_dir = _bias_lists_dir(lock, root)
    oracle_path = bias_dir / ORACLE_LIST_FILENAME
    distractor_path = bias_dir / DISTRACTOR_LIST_FILENAME
    oracle_terms = _load_term_list(oracle_path, "oracle bias list")
    distractor_terms = _load_term_list(distractor_path, "distractor bias list")

    oracle_keys = {term.casefold() for term in oracle_terms}
    seen: set[str] = set()
    distractor_only: list[str] = []
    for term in distractor_terms:
        key = term.casefold()
        if key in seen or key in oracle_keys:
            seen.add(key)
            continue
        seen.add(key)
        distractor_only.append(term)

    _assert_no_oracle_overlap(distractor_only, oracle_terms)
    if not distractor_only:
        raise EvidenceError(
            "distractor-only bias list is empty after removing every oracle-list "
            "entry from the distractor list"
        )

    facts = {
        "oracle_relpath": bias_list_relpath(lock, ORACLE_LIST_FILENAME),
        "oracle_sha256": sha256_file(oracle_path),
        "distractor_relpath": bias_list_relpath(lock, DISTRACTOR_LIST_FILENAME),
        "distractor_sha256": sha256_file(distractor_path),
        "distractor_only_total": len(distractor_only),
    }
    return distractor_only[:max_entries], facts
