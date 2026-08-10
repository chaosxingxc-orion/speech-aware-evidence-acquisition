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

A third pure function, :func:`reconstruct_bias_phrases` (2026-08-10,
``docs/readiness/2026-08-09-conec-evidence-shape.md`` "B-2a redesigned
again"), answers the FORM question that finding raised: the real, materialized
ConEC corpus is a unigram word list, so a multi-word entity such as
``GOLDMAN SACHS`` arrives fragmented as ``goldman``/``sachs`` on separate
lines. It re-assembles ADJACENT listline tokens (same document, same line
order -- never a reference transcript) into bigram phrase candidates, capped
by a WORD-COUNT budget rather than an entry count, so the phrase arm can be
compared against the bag arm (:func:`extract_bias_candidates`) at matched
content VOLUME rather than confounding form with dose. Feeds
:mod:`core.evidence`'s ``conec-bias-phrases`` source.

CLOSED GAP (2026-08-09, ``docs/readiness/2026-08-09-conec-evidence-shape.md``
"Blocking gap"): a prior revision of this module noted that the D1
evidence-identity gate assumed an evidence source's ``EvidenceItem.content``
was BYTE-IDENTICAL to the raw D1-tracked source file -- true for
``_conec_contexts`` (pure passthrough), false for ``conec-bias-list``/
``distractor-only-bias-list``, both of which TRANSFORM their source. The fix
is the derivation-chain rail in ``core.evidence_derivation`` (mirrors
``core.model.slices`` for runtime audio slices): ``conec_bias_list_content``/
``distractor_only_content`` below are the PURE, deterministic transform
functions registered into ``core.evidence_derivation.TRANSFORMS`` (pinned
name+version); ``core.evidence``'s ``_conec_bias_list``/
``_distractor_only_bias_list`` call them to build both the returned
``EvidenceItem.content`` AND a ``core.base.DerivedEvidenceRecord`` naming the
verified source, the pinned transform, and the resulting content's own hash,
so ``core.evidence_derivation.DerivedEvidenceRegistry`` can re-verify the
whole chain before ``core.driver.run_experiment`` lets a run proceed. See
``core.evidence_derivation``'s own module docstring for the exact four
conditions.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Mapping

from ..data.lock import asset_dir, lock_entry
from ..e0.artifacts import sha256_file
from .base import EvidenceError
from .evidence_derivation import TRANSFORMS

DEFAULT_BIAS_LIST_MAX_ENTRIES = 100

# 2026-08-10 (B-2a phrase-reconstruction arm, docs/readiness/2026-08-09-
# conec-evidence-shape.md "B-2a redesigned again"): matched to the bag arm's
# own DEFAULT_BIAS_LIST_MAX_ENTRIES (100) at its own content VOLUME, not its
# entry count -- a bag entry is always exactly ONE listline token (no
# internal whitespace), so 100 bag entries carry 100 words of content. A
# reconstructed-phrase entry is a bigram (TWO adjacent source tokens, see
# reconstruct_bias_phrases), so a 100-WORD budget caps out at 50 phrase
# entries -- equal total word content to the bag arm at its default cap,
# never double it. This is the crux of the B-2a "form, not dose" contrast:
# capping the phrase arm at 100 ENTRIES instead would carry 2x the bag arm's
# content and confound form with dose (R4/SAEA-E-002 already measures dose
# separately).
DEFAULT_BIAS_PHRASE_MAX_TOKENS = 100

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


def _validate_max_tokens(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise EvidenceError(f"bias_phrase_max_tokens must be a positive integer, got {value!r}")
    return value


def resolve_bias_phrase_max_tokens(values: Mapping[str, object] | None) -> int:
    """Read ``bias_phrase_max_tokens`` from a run's composed config (the SAME
    ``values`` mapping :func:`resolve_bias_list_max_entries` already reads),
    defaulting to :data:`DEFAULT_BIAS_PHRASE_MAX_TOKENS` when absent or when
    no config was supplied at all -- the identical fallback discipline, a
    DIFFERENT knob (a word-count budget, not an entry count -- see
    :data:`DEFAULT_BIAS_PHRASE_MAX_TOKENS` for why the two are not
    interchangeable for this arm)."""

    if values is None:
        return DEFAULT_BIAS_PHRASE_MAX_TOKENS
    if not isinstance(values, Mapping):
        raise EvidenceError(f"composed config values must be a mapping, got {type(values).__name__}")
    return _validate_max_tokens(values.get("bias_phrase_max_tokens", DEFAULT_BIAS_PHRASE_MAX_TOKENS))


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


def _read_text_file(path: Path, label: str) -> str:
    """Missing/unreadable-file refusal, factored out of :func:`_load_term_list`
    so :func:`distractor_only_source_texts` (which needs the raw TEXT, not a
    line list) shares the same fail-closed checks rather than a second,
    independently drifting read."""

    if not path.is_file():
        raise EvidenceError(f"{label} missing: {path}")
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise EvidenceError(f"cannot read {label} {path}: {error}") from error


def _terms_from_text(text: str, label: str) -> list[str]:
    """Pure (no filesystem access): one term per non-blank, stripped line --
    the SAME parsing :func:`_load_term_list` always applied, factored out so
    :func:`distractor_only_content` (the registered transform,
    ``core.evidence_derivation.TRANSFORMS``) can apply it to a source TEXT
    that was never read from disk by this call (it re-derives from bytes the
    caller already holds, module docstring discipline)."""

    if not isinstance(text, str):
        raise EvidenceError(f"{label} text must be a string, got {type(text).__name__}")
    terms = [line.strip() for line in text.splitlines() if line.strip()]
    if not terms:
        raise EvidenceError(f"{label} is empty")
    return terms


def _load_term_list(path: Path, label: str) -> list[str]:
    return _terms_from_text(_read_text_file(path, label), label)


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


def _distractor_only_from_terms(
    oracle_terms: list[str], distractor_terms: list[str], max_entries: int
) -> tuple[list[str], dict[str, object]]:
    """Pure core of the set difference ``distractor_terms - oracle_terms``
    (no filesystem access): case-insensitive de-duplication, ``distractor_
    terms``' own order preserved, independently re-verified for oracle
    overlap (see :func:`_assert_no_oracle_overlap`) before truncation.
    Shared by :func:`distractor_only_terms` (the pre-existing, file-based
    entry point) and :func:`distractor_only_content` (the registered
    transform, text-based) -- ONE implementation, never two independently
    drifting copies of this logic."""

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
    return distractor_only[:max_entries], {"distractor_only_total": len(distractor_only)}


def distractor_only_terms(
    lock: Mapping[str, object],
    root: Path,
    max_entries: int = DEFAULT_BIAS_LIST_MAX_ENTRIES,
) -> tuple[list[str], dict[str, object]]:
    """The set difference ``distractor_list.txt - oracle_list.txt``, computed
    at LOAD TIME from the two shipped files (never a hand-copied name list in
    this module, per the task's own non-negotiable constraint). Returns
    ``(capped_terms, facts)`` where ``facts`` carries the two source files'
    own relpath/sha256 plus the FULL (uncapped) distractor-only count, for
    evidence provenance."""

    _validate_max_entries(max_entries)
    bias_dir = _bias_lists_dir(lock, root)
    oracle_path = bias_dir / ORACLE_LIST_FILENAME
    distractor_path = bias_dir / DISTRACTOR_LIST_FILENAME
    oracle_terms = _load_term_list(oracle_path, "oracle bias list")
    distractor_terms = _load_term_list(distractor_path, "distractor bias list")

    capped, partial_facts = _distractor_only_from_terms(oracle_terms, distractor_terms, max_entries)

    facts = {
        "oracle_relpath": bias_list_relpath(lock, ORACLE_LIST_FILENAME),
        "oracle_sha256": sha256_file(oracle_path),
        "distractor_relpath": bias_list_relpath(lock, DISTRACTOR_LIST_FILENAME),
        "distractor_sha256": sha256_file(distractor_path),
        "distractor_only_total": partial_facts["distractor_only_total"],
    }
    return capped, facts


# ---------------------------------------------------------------------------
# Registered transforms (core.evidence_derivation.TRANSFORMS): pure,
# deterministic ``(source_text, params) -> derived_text`` functions -- the
# SAME functions core.evidence's conec-bias-list/distractor-only-bias-list
# sources call to build their EvidenceItem.content, so there is exactly ONE
# implementation of "what does this transform produce", never a content
# construction inline at the call site plus a SEPARATE copy the registry
# re-invokes to verify it (module docstring, "CLOSED GAP").
# ---------------------------------------------------------------------------


def conec_bias_list_content(text: str, params: Mapping[str, object]) -> str:
    """TRANSFORMS: ``conec-bias-list`` v1. The full ``EvidenceItem.content``
    ``core.evidence._conec_bias_list`` returns for a given ConEC context TEXT
    and ``{"max_entries": N}`` -- deterministic (:func:`extract_bias_
    candidates` is a pure left-to-right regex scan), never touches a
    filesystem or a model."""

    if not isinstance(params, Mapping):
        raise EvidenceError(
            f"conec-bias-list transform params must be a mapping, got {type(params).__name__}"
        )
    max_entries = _validate_max_entries(params.get("max_entries"))
    candidates = extract_bias_candidates(text, max_entries=max_entries)
    if not candidates:
        raise EvidenceError(
            "no bias-candidate entities could be extracted from the source text; "
            "refusing to emit an empty bias list"
        )
    header = (
        f"ConEC-derived bias candidates for this call ({len(candidates)} of "
        f"max {max_entries}), extracted deterministically from the call's own "
        "ConEC context materials (participant/press-release vocabulary; no "
        "model, no reference transcript):"
    )
    return format_bias_list_content(candidates, header)


TRANSFORMS.register("conec-bias-list", "v1", conec_bias_list_content)


def distractor_only_source_texts(
    lock: Mapping[str, object], root: Path
) -> tuple[str, str, str, str]:
    """The two shipped bias-list files' own raw TEXT + relpath (oracle, then
    distractor) -- the material ``core.evidence._distractor_only_bias_list``
    combines into its carrier-independent
    ``core.base.DerivedEvidenceRecord`` source document
    (``carrier_bound=False``: there is no single per-sample carrier file to
    name here, module docstring). A read independent of
    :func:`distractor_only_terms`'s own (unchanged) file access -- both read
    the same small, static files, once each, per evidence-source call."""

    bias_dir = _bias_lists_dir(lock, root)
    oracle_text = _read_text_file(bias_dir / ORACLE_LIST_FILENAME, "oracle bias list")
    distractor_text = _read_text_file(bias_dir / DISTRACTOR_LIST_FILENAME, "distractor bias list")
    return (
        oracle_text,
        distractor_text,
        bias_list_relpath(lock, ORACLE_LIST_FILENAME),
        bias_list_relpath(lock, DISTRACTOR_LIST_FILENAME),
    )


def distractor_only_source_document(
    oracle_text: str, distractor_text: str, oracle_relpath: str, distractor_relpath: str
) -> str:
    """Canonical, sorted-key JSON document combining the two shipped bias-list
    files' own text -- the carrier-independent SOURCE for the
    ``distractor-only`` transform. There is no SINGLE per-sample carrier file
    to hash here (module docstring "CLOSED GAP"), so this document itself IS
    the source, and its own sha256 becomes the derivation record's
    ``source_sha256`` (``core.base.DerivedEvidenceRecord.carrier_bound=
    False``)."""

    return json.dumps(
        {
            "distractor_relpath": distractor_relpath,
            "distractor_text": distractor_text,
            "oracle_relpath": oracle_relpath,
            "oracle_text": oracle_text,
        },
        sort_keys=True,
    )


def distractor_only_content(source_text: str, params: Mapping[str, object]) -> str:
    """TRANSFORMS: ``distractor-only`` v1. ``source_text`` is a
    :func:`distractor_only_source_document`; this parses it back into the two
    term lists and reproduces the SAME ``EvidenceItem.content``
    ``core.evidence._distractor_only_bias_list`` returns. Pure: never reads a
    file, never touches a model, deterministic given (source_text, params)."""

    if not isinstance(params, Mapping):
        raise EvidenceError(
            f"distractor-only transform params must be a mapping, got {type(params).__name__}"
        )
    max_entries = _validate_max_entries(params.get("max_entries"))
    try:
        document = json.loads(source_text)
    except json.JSONDecodeError as error:
        raise EvidenceError(
            f"distractor-only source document is not valid JSON: {error}"
        ) from error
    if (
        not isinstance(document, Mapping)
        or "oracle_text" not in document
        or "distractor_text" not in document
    ):
        raise EvidenceError(
            "distractor-only source document is missing oracle_text/distractor_text"
        )
    oracle_terms = _terms_from_text(document["oracle_text"], "oracle bias list")
    distractor_terms = _terms_from_text(document["distractor_text"], "distractor bias list")
    capped, partial_facts = _distractor_only_from_terms(oracle_terms, distractor_terms, max_entries)
    header = (
        f"Distractor-only bias terms ({len(capped)} of max {max_entries}, "
        f"{partial_facts['distractor_only_total']} total before the cap): Fortune-500/"
        "CEO names present in the shipped Earnings-21 distractor list but "
        "ABSENT from its reference-derived oracle list (negative control; no "
        "reference-transcript content):"
    )
    return format_bias_list_content(capped, header)


TRANSFORMS.register("distractor-only", "v1", distractor_only_content)


# ---------------------------------------------------------------------------
# Phrase reconstruction (2026-08-10, B-2a "form, not dose": docs/readiness/
# 2026-08-09-conec-evidence-shape.md "B-2a redesigned again"). Leakage
# boundary: this reads ONLY the ConEC context text already verified by D1
# (the same source _conec_bias_list reads) and its OWN line order -- it never
# opens oracle_list.txt/distractor_list.txt, so it needs no
# _assert_no_oracle_overlap call at all (unlike distractor_only, which
# legitimately reads the oracle list to compute a set difference, this
# function structurally cannot reach oracle content -- the same reasoning
# that already makes _conec_bias_list oracle-free, module docstring).
# ---------------------------------------------------------------------------

# Standalone (deliberately NOT reused from _TERM_PATTERN's `listline`
# alternative, which is a lookahead embedded in a larger left-to-right scan
# that also matches roster/span/ticker shapes at the SAME position): this
# matches a WHOLE line that is exactly the real ConEC corpus's own shape --
# one token, whitespace, a bare integer count, nothing else (module
# docstring, "Verified against the real, materialized ConEC corpus"). Phrase
# reconstruction needs each candidate LINE's own boundary to test adjacency
# against its neighbour, not an entity scan across a whole document.
_LISTLINE_ONLY = re.compile(r"[A-Za-z][A-Za-z0-9'-]{2,}[ \t]+\d+[ \t]*")


def _listline_token_runs(text: str) -> list[list[str]]:
    """The source's own tokens, split into maximal RUNS of consecutive lines
    that are each individually shaped like a real ConEC listline. A line that
    does NOT match that shape (roster prose, a blank line, junk) breaks the
    run -- :func:`reconstruct_bias_phrases` below only ever joins two lines
    that are BOTH confirmed listline shape, never bridges across a line of a
    different shape. Order and duplicates from the source are both preserved
    (adjacency, not a deduped candidate set, is what a phrase is built from);
    on the real corpus (0 non-listline lines observed) this is one single run
    per file, which is exactly the "preserves roster blocks, headline
    phrases, contact blocks" document order the readiness note describes."""

    runs: list[list[str]] = []
    current: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if _LISTLINE_ONLY.fullmatch(stripped) is None:
            if current:
                runs.append(current)
                current = []
            continue
        current.append(stripped.split()[0])
    if current:
        runs.append(current)
    return runs


def reconstruct_bias_phrases(
    text: str, max_tokens: int = DEFAULT_BIAS_PHRASE_MAX_TOKENS
) -> list[str]:
    """Deterministic multi-word phrase reconstruction from a ConEC-shaped
    context file's OWN LINE ORDER (module docstring): every candidate is an
    OVERLAPPING (stride-1) bigram of two lines directly adjacent in the
    source, both individually confirmed listline shape
    (:func:`_listline_token_runs`) -- "goldman" immediately followed by
    "sachs" in the file yields "goldman sachs" regardless of which parity
    offset the pair falls on (a stride-2/non-overlapping window would
    silently miss half of all true adjacent pairs). Case-insensitive
    de-duplication keeps first-seen casing/order (matching
    :func:`extract_bias_candidates`'s own discipline), capped by a
    WORD-COUNT budget (``max_tokens``, two words per bigram) rather than an
    entry count -- see :data:`DEFAULT_BIAS_PHRASE_MAX_TOKENS` for why
    entry-count capping would confound form with dose. A budget too small to
    fit even one bigram (``max_tokens < 2``) legitimately yields an empty
    list, exactly like :func:`extract_bias_candidates` on text with no
    matching shape -- the caller (``core.evidence``'s ``conec-bias-phrases``
    source) is what fails closed on an empty result, not this function. Same
    purity guarantees as :func:`extract_bias_candidates`: no filesystem
    access, no model, no network; same input -> byte-identical output."""

    if not isinstance(text, str):
        raise EvidenceError(f"phrase reconstruction requires text, got {type(text).__name__}")
    _validate_max_tokens(max_tokens)
    seen: set[str] = set()
    candidates: list[str] = []
    total_words = 0
    for run in _listline_token_runs(text):
        for index in range(len(run) - 1):
            phrase = f"{run[index]} {run[index + 1]}"
            key = phrase.casefold()
            if key in seen:
                continue
            seen.add(key)
            if total_words + 2 > max_tokens:
                # Every remaining candidate is also a 2-word bigram and
                # total_words never decreases, so the budget can never fit
                # another one from here on -- stop scanning entirely rather
                # than skip-and-continue through the rest of the source.
                return candidates
            candidates.append(phrase)
            total_words += 2
    return candidates


def conec_bias_phrase_content(text: str, params: Mapping[str, object]) -> str:
    """TRANSFORMS: ``conec-bias-phrases`` v1. The full ``EvidenceItem.content``
    ``core.evidence._conec_bias_phrases`` returns for a given ConEC context
    TEXT and ``{"max_tokens": N}`` -- deterministic
    (:func:`reconstruct_bias_phrases` is a pure scan), never touches a
    filesystem or a model. Same structure as :func:`conec_bias_list_content`
    (module "CLOSED GAP" note): the evidence source and this registry-facing
    transform call the SAME function, one implementation only."""

    if not isinstance(params, Mapping):
        raise EvidenceError(
            f"conec-bias-phrases transform params must be a mapping, got {type(params).__name__}"
        )
    max_tokens = _validate_max_tokens(params.get("max_tokens"))
    candidates = reconstruct_bias_phrases(text, max_tokens=max_tokens)
    if not candidates:
        raise EvidenceError(
            "no phrase candidates could be reconstructed from the source text; "
            "refusing to emit an empty phrase list"
        )
    header = (
        f"ConEC-derived reconstructed phrase candidates for this call "
        f"({len(candidates)} phrases, {2 * len(candidates)} of max {max_tokens} "
        "words budget), assembled from adjacent lines of the call's own ConEC "
        "context materials (document order preserved; no model, no reference "
        "transcript):"
    )
    return format_bias_list_content(candidates, header)


TRANSFORMS.register("conec-bias-phrases", "v1", conec_bias_phrase_content)
