"""Stdlib-only PDF text extraction, including hex-encoded subsetted CID fonts.

Some ConEC decks draw every glyph as a hex glyph id (``[<0015><0013>...] TJ``)
rather than a literal string, so the naive "pull the parenthesised operands"
extractor returns nothing for them. The mapping back to characters is carried by
the PDF's own /ToUnicode CMaps, which are themselves ordinary Flate streams --
so they can be parsed with nothing but ``zlib`` and ``re``.

Fidelity caveat: a per-font CMap binding would require resolving /Font resource
dictionaries and Tf operators. Instead every CMap in the file is merged and the
decoding is accepted only if it scores as English-looking text (see
``textiness``). Collisions between two subset fonts that assign the same glyph id
to different characters are therefore possible; this layer is used for
substring PRESENCE testing, never as a transcript.
"""

from __future__ import annotations

import re
import zlib

_STREAM = re.compile(rb"stream\r?\n")
_LITERAL = re.compile(rb"\((?:\\.|[^\\()])*\)")
_HEXSTR = re.compile(rb"<([0-9A-Fa-f]{2,})>")
_COMMON = ("the", "and", "of", "to", "in", "for", "quarter", "million")


def _streams(raw):
    for match in _STREAM.finditer(raw):
        start = match.end()
        end = raw.find(b"endstream", start)
        if end < 0:
            continue
        try:
            yield zlib.decompress(raw[start:end])
        except zlib.error:
            continue


def _parse_cmap(data):
    mapping = {}
    for block in re.findall(rb"beginbfchar(.*?)endbfchar", data, re.S):
        for src, dst in re.findall(rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", block):
            mapping[int(src, 16)] = _utf16(dst)
    for block in re.findall(rb"beginbfrange(.*?)endbfrange", data, re.S):
        for lo, hi, dst in re.findall(
                rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", block):
            low, high, base = int(lo, 16), int(hi, 16), int(dst, 16)
            for offset in range(min(high - low + 1, 65536)):
                mapping[low + offset] = chr(base + offset) if base + offset < 0x110000 else ""
        for lo, _hi, items in re.findall(
                rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*\[(.*?)\]", block, re.S):
            low = int(lo, 16)
            for offset, dst in enumerate(re.findall(rb"<([0-9A-Fa-f]+)>", items)):
                mapping[low + offset] = _utf16(dst)
    return mapping


def _utf16(dst):
    try:
        return bytes.fromhex(dst.decode("ascii")).decode("utf-16-be", "replace")
    except Exception:
        return ""


def textiness(text):
    """How English-looking is this decoding? 0..1, used to accept or reject."""
    if not text:
        return 0.0
    good = sum(c.isalnum() or c in " .,%$-()/" for c in text)
    ratio = good / len(text)
    lowered = text.casefold()
    words = sum(1 for w in _COMMON if f" {w} " in lowered)
    return ratio * (0.5 + 0.5 * min(1.0, words / 4))


def pdf_text(path):
    """Best-effort text of one PDF: literal strings, plus CMap-decoded hex."""
    raw = path.read_bytes()
    streams = list(_streams(raw))

    cmap = {}
    for data in streams:
        if b"beginbfchar" in data or b"beginbfrange" in data:
            for code, char in _parse_cmap(data).items():
                cmap.setdefault(code, char)

    literal, hexed = [], []
    for data in streams:
        if b"BT" not in data or (b"Tj" not in data and b"TJ" not in data):
            continue
        for block in re.finditer(rb"BT(.*?)ET", data, re.S):
            body = block.group(1)
            for token in _LITERAL.finditer(body):
                piece = token.group(0)[1:-1]
                piece = re.sub(rb"\\([()\\])", rb"\1", piece)
                piece = re.sub(rb"\\[0-7]{1,3}", b" ", piece)
                piece = piece.replace(b"\\n", b" ").replace(b"\\r", b" ")
                literal.append(piece.decode("latin-1", "replace"))
            # One run per TEXT BLOCK, not per hex string: inside a TJ array each
            # <....> is a fragment of the same word, separated only by kerning
            # numbers, so concatenating them is what reconstitutes the word.
            run = []
            for token in _HEXSTR.finditer(body):
                digits = token.group(1)
                if len(digits) % 4:
                    continue
                run.extend(int(digits[i:i + 4], 16)
                           for i in range(0, len(digits), 4))
            if run:
                hexed.append(run)

    literal_text = " ".join(literal)
    hex_text, offset_used = "", None

    if hexed and cmap:
        hex_text = " ".join("".join(cmap.get(c, "") for c in run) for run in hexed)

    if hexed and textiness(hex_text) < 0.75:
        # No usable /ToUnicode. A subsetted TrueType font very often numbers its
        # glyphs in code-point order, so the whole file decodes under ONE constant
        # offset. Search for it and accept only if the result passes the SAME
        # English-looking gate every other decoding must pass -- a guess that
        # cannot be validated is discarded.
        best, best_score = None, textiness(hex_text)
        for candidate in range(0, 256):
            trial = " ".join(
                "".join(chr(c + candidate) if 32 <= c + candidate < 127 else ""
                        for c in run)
                for run in hexed)
            score = textiness(trial)
            if score > best_score:
                best, best_score, hex_text = trial, score, trial
                offset_used = candidate
        if best is None:
            offset_used = None

    accepted = bool(hexed) and textiness(hex_text) >= 0.75
    parts = [literal_text] + ([hex_text] if accepted else [])
    return " ".join(p for p in parts if p), {
        "literal_chars": len(literal_text),
        "hex_chars": len(hex_text),
        "hex_textiness": round(textiness(hex_text), 3),
        "hex_accepted": accepted,
        "cmap_entries": len(cmap),
        "glyph_offset": offset_used,
    }
