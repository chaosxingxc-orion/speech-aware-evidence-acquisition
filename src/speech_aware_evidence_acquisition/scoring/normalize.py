"""Frozen text normalization v1 for the E0 scoring stack (D3).

Every scorer in this study normalizes text through exactly this function. The rules
are deliberately small, deterministic and stdlib-only; changing any rule is a new
scoring-stack version, never an in-place edit (E0 D3 freeze).

v1 rules, applied in order:

1. Unicode NFKC normalization.
2. Case folding (aggressive lowercase).
3. Unicode apostrophe variants (‘ ’ ʼ) become ASCII ``'``.
4. Hyphen/dash variants (‐-―, ASCII ``-``) become a single space.
5. Every remaining character that is not a letter, digit, apostrophe or whitespace
   becomes a space (punctuation is not scored).
6. An apostrophe not flanked by letters/digits on both sides becomes a space
   (intra-word apostrophes like ``don't`` survive; quoting apostrophes do not).
7. Whitespace collapses to single spaces; leading/trailing whitespace is dropped.

Tokens are the space-separated units of the normalized string. No number expansion,
no spelled-out punctuation, no language-specific rewriting in v1.
"""

from __future__ import annotations

import unicodedata


SCORING_STACK_VERSION = "saea-scoring-v1"

_APOSTROPHES = {"‘", "’", "ʼ"}
_DASHES = set("-‐‑‒–—―")


def normalize_text_v1(text: str) -> str:
    if not isinstance(text, str):
        raise TypeError(f"normalize_text_v1 expects str, got {type(text).__name__}")
    folded = unicodedata.normalize("NFKC", text).casefold()
    chars: list[str] = []
    for char in folded:
        if char in _APOSTROPHES:
            chars.append("'")
        elif char in _DASHES:
            chars.append(" ")
        elif char == "'" or char.isalnum() or char.isspace():
            chars.append(char)
        else:
            chars.append(" ")
    joined = "".join(chars)
    kept: list[str] = []
    for index, char in enumerate(joined):
        if char == "'":
            before = joined[index - 1] if index > 0 else " "
            after = joined[index + 1] if index + 1 < len(joined) else " "
            if before.isalnum() and after.isalnum():
                kept.append(char)
            else:
                kept.append(" ")
        else:
            kept.append(char)
    return " ".join("".join(kept).split())


def tokens_v1(text: str) -> list[str]:
    normalized = normalize_text_v1(text)
    return normalized.split(" ") if normalized else []
