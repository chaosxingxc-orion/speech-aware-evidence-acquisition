"""SUPPLY dose knob: ``evidence_budget_bytes`` (optional baseline-config key).

Absent or ``0`` is unlimited -- byte-identical to every pre-existing run,
never a code default silently applied. A positive ``N`` caps the UTF-8 bytes
of evidence text a run actually supplies to the model, cutting at the last
whitespace boundary at or below ``N`` so a request never carries a split
multi-byte codepoint or a split word.

Single application seam: ``core.driver.run.run_experiment`` calls
:func:`apply_evidence_budget` exactly ONCE per sample, right after the
derivation-chain registry has verified every source's untouched content and
after any ``evidence_mismatch`` rotation, but BEFORE ``_emit_sample_preamble``
computes its SUPPLY/ORG byte counts and before ``ctx.evidence`` ever reaches a
policy. Every downstream reader therefore sees the identical, already
-truncated content: the existing ``supply_content_bytes`` trace field and the
run-cost ``supplied_evidence_bytes``/``admitted_evidence_bytes`` aggregates
report the POST-truncation size with no field added, and a slice-fanning
policy (``reproduction.obs_loop.ObsAgentLoopPolicy``) sends the SAME
truncated text on every one of a sample's N slice requests, because it reads
the one already-truncated ``ctx.evidence`` list, never re-derives it.
"""

from __future__ import annotations

from typing import Mapping

from .base import EvidenceError, EvidenceItem


def resolve_evidence_budget_bytes(values: Mapping[str, object]) -> int:
    """Validate the composed config's ``evidence_budget_bytes`` (absent/0 =
    unlimited). Fails closed on a negative or non-integer value, same style
    as ``ObsLoopConfig.from_values`` (reproduction.obs_loop) -- a typo here
    would otherwise either do nothing (silently unlimited) or crash deep
    inside a truncation call instead of refusing up front, before this run
    spends anything. Config-hashed like every sibling optional key: ``core.
    config.compose`` merges and hashes the whole fragment verbatim, so
    declaring this key already changes ``config_hash`` -> ``protocol_hash``
    with no separate wiring."""

    value = values.get("evidence_budget_bytes", 0)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise EvidenceError(
            "config evidence_budget_bytes must be a non-negative integer "
            f"(absent/0 = unlimited), got {value!r}"
        )
    return value


def _truncate_utf8_at_whitespace(text: str, budget_bytes: int) -> str:
    """Cut ``text`` to at most ``budget_bytes`` of UTF-8, at the last
    whitespace boundary at or below the budget. Deterministic: the same
    ``(text, budget_bytes)`` always yields the same result.

    Never splits a multi-byte codepoint: the byte-level prefix is decoded
    back to front, dropping trailing bytes until it decodes cleanly (Python
    ``str`` slicing itself is codepoint-safe, but a raw byte-count cut is
    not). Never splits a word: the codepoint-safe prefix is then cut back
    further to its last whitespace character. A single token longer than the
    whole budget has no whitespace to cut back to -- the codepoint-safe
    prefix is the best achievable result in that case, still never over
    budget and never invalid UTF-8.
    """

    encoded = text.encode("utf-8")
    if len(encoded) <= budget_bytes:
        return text
    cut = encoded[:budget_bytes]
    while cut:
        try:
            candidate = cut.decode("utf-8")
            break
        except UnicodeDecodeError:
            cut = cut[:-1]
    else:
        candidate = ""
    trimmed = candidate.rstrip()
    if trimmed != candidate:
        # the codepoint-safe prefix already ends mid (or right after) a
        # whitespace run -- stripping it IS the whitespace cut.
        return trimmed
    last_space = -1
    for index in range(len(candidate) - 1, -1, -1):
        if candidate[index].isspace():
            last_space = index
            break
    if last_space == -1:
        return candidate
    return candidate[:last_space].rstrip()


def apply_evidence_budget(
    evidence_by_sample: Mapping[str, list[EvidenceItem]], budget_bytes: int
) -> dict[str, list[EvidenceItem]]:
    """Truncate every sample's evidence to at most ``budget_bytes`` combined
    UTF-8 bytes, in list order: an item that fits inside whatever budget
    remains is untouched, the item that first overflows is cut at a
    whitespace boundary (:func:`_truncate_utf8_at_whitespace`) and the
    budget is then exhausted, and any following item in that sample is
    dropped entirely rather than emitting a second, independently-truncated
    fragment. Every registered evidence source today returns exactly one
    item per sample, so in practice this caps that one item's content to
    ``budget_bytes``.

    ``budget_bytes <= 0`` is unlimited: returns a shallow copy of
    ``evidence_by_sample`` with every ``EvidenceItem`` untouched (same
    objects, same ``content`` bytes) -- the module docstring's "byte
    -identical to every pre-existing run" guarantee.
    """

    if budget_bytes <= 0:
        return dict(evidence_by_sample)
    truncated: dict[str, list[EvidenceItem]] = {}
    for sample_id, items in evidence_by_sample.items():
        remaining = budget_bytes
        kept: list[EvidenceItem] = []
        for item in items:
            if remaining <= 0:
                break
            content_bytes = len(item.content.encode("utf-8"))
            if content_bytes <= remaining:
                kept.append(item)
                remaining -= content_bytes
                continue
            new_content = _truncate_utf8_at_whitespace(item.content, remaining)
            remaining = 0
            if new_content:
                kept.append(
                    EvidenceItem(
                        evidence_id=item.evidence_id,
                        source_uri=item.source_uri,
                        content=new_content,
                        provenance=item.provenance,
                        derivation=item.derivation,
                        derivation_source_bytes=item.derivation_source_bytes,
                    )
                )
        truncated[sample_id] = kept
    return truncated
