"""Exposure-ledger markdown table parsing (fail-closed against hidden/duplicate rows).

Split out of the former monolithic ``contracts.py`` (R0 repair refactor stage 1,
pure move, no behaviour change).
"""

from __future__ import annotations

import re

from .errors import GateClosed

_EXPOSURE_RUN_COLUMN = "run/experiment id"
_EXPOSURE_CARRIER_COLUMN = "speech carrier + split"
# Every column name `_require_exposure_preregistration` looks up on a matched or
# summed row. Used (I2) to decide whether an UNRECOGNIZED table header -- one
# that does not carry `_EXPOSURE_RUN_COLUMN` -- might still be a disguised or
# malformed contract table (sharing a contract column name) and must therefore
# be refused rather than silently ignored.
_ALL_LEDGER_COLUMNS = frozenset(
    {
        _EXPOSURE_RUN_COLUMN,
        _EXPOSURE_CARRIER_COLUMN,
        "execution profile",
        "split role",
        "split identity hash",
        "consumed",
        "calls",
        "speech audio seconds",
        "gpu hours",
    }
)
# Tokenizes the free-text "speech carrier + split" cell (e.g. "earnings21-original
# + earnings22-original + conec, identity layers; e22 subset10 (dev)") so a plan's
# carrier can be matched exactly against a known lock key rather than by
# unanchored substring -- an unanchored `plan.carrier_lock_key in cell_text` check
# lets one row that happens to name two carriers authorize either identity, and
# lets a carrier name that is a prefix of another (e.g. "earnings2" as a substring
# of "earnings22-original") falsely match.
_CARRIER_CELL_TOKEN_SPLIT = re.compile(r"[\s,;+()]+")


def _split_table_row(line: str) -> tuple[bool, list[str]]:
    """Recognize a markdown table row and split it into raw (unlowered) cells.

    A "row" is any line whose stripped form starts and ends with ``|`` -- this
    intentionally matches header, separator and data rows alike; callers tell
    them apart afterward."""

    stripped = line.strip()
    if len(stripped) < 2 or not (stripped.startswith("|") and stripped.endswith("|")):
        return False, []
    return True, [cell.strip() for cell in stripped[1:-1].split("|")]


def _is_separator_row(cells: list[str]) -> bool:
    """A GFM header-separator row: every cell is only ``-``, ``:`` or space."""

    return bool(cells) and all(not cell.strip("-: ") for cell in cells)


# IMPORTANT C (round-2 external-threat-model review): the ledger parser must
# know it is reading MARKDOWN, not merely "any line that looks like a table
# row". Two GFM constructs make content invisible to a human reading the
# RENDERED ledger while still being plain text to a naive line-by-line
# scanner: an HTML comment (``<!-- ... -->``, possibly spanning many lines)
# and a fenced code block (opened/closed by a line of 3+ backticks or
# tildes, the natural way to document the row format as an illustrative
# example). Demonstrated: a complete contract table inside an HTML comment
# parsed as a real, binding registration that a human reading the rendered
# ledger sees NOTHING of; a contract table inside a fenced example block
# silently exhausted the campaign slice cap.
#
# IMPORTANT 1 fix-wave3 (round-3 external-threat-model review): the round-2
# fix above over-corrected. Its own justification -- "a line containing
# ``<!--`` is never itself a genuine table row (a real row is exactly
# ``| ... |``)" -- is FALSE: ``| 2026-08-05 | RUN-OLD | ... | scope amended
# <!-- see git history --> |`` is a completely genuine, GFM-legal table row
# that GitHub renders normally, hiding only the comment text inside its last
# cell. Consuming that WHOLE LINE (as round-2 did, for ANY line containing
# ``<!--``) made the ENTIRE row -- including its budget-relevant cells:
# ``calls``, ``consumed``, etc. -- invisible to every check below, even
# though a human reading the rendered ledger sees the row perfectly clearly.
# Demonstrated: an honest ledger whose slice total was 3100 calls (correctly
# REFUSED) was wrongly ACCEPTED once an inline ``<!-- ... -->`` was added
# inside one row's notes cell; a ``consumed = yes`` row became invisible to
# the consumed check the same way; and an UNCLOSED ``<!--`` inside a cell
# silently dropped every row below it for the rest of the document while
# ``saw_contract_header`` stayed True, so the gate never failed closed at
# all -- exactly the "silently drop rows" failure mode I2 already exists to
# prevent, just via a different trigger.
#
# The fix distinguishes two shapes precisely:
#
# 1. A comment that both OPENS and CLOSES on the SAME line -- the demonstrated
#    defect's shape -- is stripped from that line's TEXT (see
#    :func:`_strip_same_line_comments`), leaving every surrounding
#    character -- including the REST of that same row's other cells --
#    completely untouched. Row/header recognition then runs on the
#    comment-stripped text exactly as if the comment had never been there,
#    so a genuine row is never lost, and a ``consumed``/budget cell hidden
#    only by an inline comment is read correctly.
# 2. A comment that OPENS on one line without also closing on it begins a
#    genuinely multi-line span; every line up to and including the one that
#    finally closes it is consumed WHOLE, UNCHANGED from the round-2
#    behavior -- this is what keeps the round-2 "a complete table hidden
#    inside a comment block" case (its own dedicated header-then-rows-then-
#    close-marker shape, each on its own line) invisible exactly as before:
#    that case never involves a genuine, otherwise-recognizable row losing
#    only its comment tail, so it needs no different treatment.
#
# A comment opened this way that NEVER closes before end-of-document is no
# longer silently equivalent to "everything after it is invisible prose" --
# it now FAILS CLOSED (:class:`GateClosed`) at the end of parsing, since an
# unterminated comment could, in principle, be hiding a real row's remainder
# (or an entire real table) that this parser can never distinguish from
# intentionally-hidden draft content once the comment never closes.
_HTML_COMMENT_OPEN = "<!--"
_HTML_COMMENT_CLOSE = "-->"
_FENCE = re.compile(r"^(`{3,}|~{3,})")


def _strip_same_line_comments(line: str) -> tuple[str, bool]:
    """Remove every ``<!-- ... -->`` span that both opens AND closes on
    ``line``, leaving all other characters -- including a row's OTHER cells
    on either side -- completely untouched; handles more than one such span
    per line. Returns ``(visible_text, opens_unterminated)`` where
    ``opens_unterminated`` is True iff, after removing every already-closed
    same-line span, the text still contains a ``<!--`` with no matching
    ``-->`` later on this SAME line -- the caller's signal to fall back to
    the existing whole-line multi-line-comment consumption, unchanged."""

    parts: list[str] = []
    i = 0
    while True:
        open_idx = line.find(_HTML_COMMENT_OPEN, i)
        if open_idx == -1:
            parts.append(line[i:])
            return "".join(parts), False
        close_idx = line.find(_HTML_COMMENT_CLOSE, open_idx + len(_HTML_COMMENT_OPEN))
        if close_idx == -1:
            parts.append(line[i:open_idx])
            return "".join(parts), True
        parts.append(line[i:open_idx])
        i = close_idx + len(_HTML_COMMENT_CLOSE)


def _parse_ledger_tables(text: str) -> list[dict[str, str]]:
    """Parse EVERY markdown table in ``text``, not just the first (I2).

    The reproduced defect: the old parser walked lines once and stopped at the
    first non-table line found after its header, so a second table -- or even
    a single stray prose line between two data rows of the same table -- made
    every row after it invisible to the budget/duplicate/consumed checks.

    A table row immediately followed by a GFM separator row (dashes/colons
    only) is unambiguously a header, independent of anything earlier or later
    in the document -- so a stray prose line elsewhere can never end a table
    early, and a later plain data row can never be mistaken for a new header.
    A recognized header (its lowered cells carry ``_EXPOSURE_RUN_COLUMN``)
    opens a contract table: every following data row -- up to the next header
    -- is captured as a ``{column_name: cell}`` mapping keyed by THAT table's
    own header (M4: a row whose cell count disagrees with its governing
    header is refused outright, never positionally misaligned). A header
    that is NOT recognized either belongs to a genuinely unrelated table
    (silently ignored, e.g. a legend/description table) or, if it shares any
    contract column name or the current contract header's width, is refused
    fail-closed rather than risking silently dropped budget rows (I2).

    IMPORTANT C (round-2 external-threat-model review): before any row/header
    recognition, every line is first classified as being inside a fenced code
    block or an HTML comment; a line consumed whole by either state is never
    treated as a row, a separator, or a header, and never allowed to close
    the CURRENTLY open contract table (matching the existing "a stray prose
    line never drops rows below it" discipline: content the rendered ledger
    hides is exactly as inert as ordinary prose to the table state machine).
    A whole table hidden inside a comment or framed by a documentation fence
    is therefore simply invisible -- IGNORED, never a registration and never
    a fail-closed refusal on their own: a comment is a legitimate way to keep
    old/draft content out of the rendered view without deleting it, and
    content a human reader cannot see can never satisfy this file's whole
    purpose as the OWNER-VISIBLE pre-registration record either way, so there
    is nothing gained by refusing outright over silently not treating it as
    binding.

    IMPORTANT 1 fix-wave3 (round-3 external-threat-model review): comment
    handling is now CELL-TEXT-aware, not merely line-level -- see the module
    comment above :func:`_strip_same_line_comments` for exactly what changed
    and why. A comment that never closes before end-of-document fails closed
    rather than silently discarding every row after it."""

    lines = text.splitlines()
    n = len(lines)
    current_header: list[str] | None = None
    rows: list[dict[str, str]] = []
    saw_contract_header = False
    in_comment = False
    in_fence = False
    fence_char = ""
    fence_len = 0
    i = 0
    while i < n:
        line = lines[i]

        if in_comment:
            if _HTML_COMMENT_CLOSE in line:
                in_comment = False
            i += 1
            continue

        stripped_for_fence = line.strip()
        if in_fence:
            fence_match = _FENCE.match(stripped_for_fence)
            if (
                fence_match
                and fence_match.group(1)[0] == fence_char
                and len(fence_match.group(1)) >= fence_len
            ):
                in_fence = False
            i += 1
            continue
        fence_match = _FENCE.match(stripped_for_fence)
        if fence_match:
            in_fence = True
            fence_char = fence_match.group(1)[0]
            fence_len = len(fence_match.group(1))
            i += 1
            continue

        # IMPORTANT 1 fix-wave3: strip any comment(s) that both open AND close
        # on THIS line from its text, leaving every surrounding character --
        # including the rest of the SAME row's other cells -- untouched, and
        # continue treating the (possibly modified) line as an ordinary
        # row/header/data candidate below. A comment that opens here WITHOUT
        # also closing here is a genuinely multi-line span: fall back to the
        # existing whole-line consumption, unchanged from round-2.
        line, opens_unterminated = _strip_same_line_comments(line)
        if opens_unterminated:
            in_comment = True
            i += 1
            continue

        is_row, cells = _split_table_row(line)
        if not is_row:
            i += 1
            continue
        if _is_separator_row(cells):
            # A bare separator with nothing recognized as its header: never
            # data, never a header by itself -- skip wherever it appears.
            i += 1
            continue
        next_is_row, next_cells = (
            _split_table_row(lines[i + 1]) if i + 1 < n else (False, [])
        )
        if next_is_row and _is_separator_row(next_cells):
            lowered = [cell.lower() for cell in cells]
            if len(lowered) != len(set(lowered)):
                raise GateClosed(
                    f"exposure ledger table header has duplicate columns: {cells!r}"
                )
            if _EXPOSURE_RUN_COLUMN in lowered:
                current_header = lowered
                saw_contract_header = True
            else:
                overlap = set(lowered) & _ALL_LEDGER_COLUMNS
                same_width = current_header is not None and len(lowered) == len(current_header)
                if overlap or same_width:
                    raise GateClosed(
                        f"exposure ledger contains a table header {cells!r} that is not "
                        f"the recognized contract header ({_EXPOSURE_RUN_COLUMN!r} column) "
                        "but shares contract-shaped columns or width with one; refusing "
                        "rather than silently ignoring rows that might be contract rows "
                        "(I2 fail-closed)"
                    )
                current_header = None  # a genuinely unrelated table: its rows are ignored
            i += 2  # consume header + separator row together
            continue
        # Not a header (no separator immediately follows): a data row of
        # whichever contract table is currently active, if any.
        if current_header is not None:
            if len(cells) != len(current_header):
                raise GateClosed(
                    f"exposure ledger row {cells!r} has {len(cells)} cells but its "
                    f"table header has {len(current_header)} columns {current_header!r}; "
                    "refusing rather than guessing column alignment (M4)"
                )
            rows.append(dict(zip(current_header, cells)))
        i += 1
    # IMPORTANT 1 fix-wave3: an HTML comment that opens somewhere in the
    # document and NEVER closes before end-of-file must fail closed, not
    # silently behave as "everything after it is invisible prose" -- the
    # reproduced defect (3 registered rows / 3500 calls silently became 0
    # rows / 0 calls, with saw_contract_header still True so nothing ever
    # refused). An unterminated comment could in principle be hiding a real
    # row's remainder, or an entire real table, that this line-oriented
    # parser can never distinguish from deliberately-hidden draft content
    # once the comment never closes -- so it refuses outright instead of
    # guessing either way.
    if in_comment:
        raise GateClosed(
            "exposure ledger contains an unterminated HTML comment (a `<!--` with no "
            "matching `-->` before end of file); refusing rather than silently treating "
            "everything after it as invisible prose -- a genuine row could be hidden "
            "behind it (fail-closed)"
        )
    if not saw_contract_header:
        raise GateClosed(
            f"exposure ledger lacks a table header with a {_EXPOSURE_RUN_COLUMN!r} column"
        )
    return rows
