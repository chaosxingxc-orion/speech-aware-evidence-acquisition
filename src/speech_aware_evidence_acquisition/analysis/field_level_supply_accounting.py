"""FIELD-LEVEL SUPPLY ACCOUNTING: what the injected supply is made of, and
what each part of it costs.

Exposure row ``SAEA-SN-MF-FIELD-LEVEL-SUPPLY-ACCOUNTING`` (registered before
any computation, ledger commit ``834c36dd``): zero frozen-core contacts, zero
embedding-tool contacts, zero tokenizer contacts, zero HTTP or socket
requests, zero audio decoded, zero GPU hours, zero new dependencies. Every
byte read here is already landed. No knob is changed and no line under
``rails/`` is touched.

The question
------------
The supplied :class:`~rails.knowledge.ValueBundle` content on both carriers is
a FIXED COMPOSITE STRING assembled at KB-CONSTRUCTION time and injected
VERBATIM. Nothing at use time selects which FIELDS of it are relevant. Two
landed reads have now measured what the supply DOES:

* the matching-versus-extraction read (landed ``d4c75c7a``) established that,
  CONDITIONED ON MATCHING, the supply does not serve extraction on either
  carrier;
* the A2T gold-absence diagnosis (landed ``aaa366ad``) quantified the
  FORM-REPAIR channel on Audio2Tool.

Neither priced the supply. This module prices it, field by field, and does
nothing else.

What this module does NOT do
----------------------------
It does not propose or evaluate a field-selection policy and it does not
change how anything is rendered. It produces the ACCOUNTING that a later,
separately-registered design step would use.

The parse-fidelity gate
-----------------------
Every supplied value is segmented into field groups by anchors read off the
builders themselves, the segments are REASSEMBLED and asserted BYTE-EQUAL to
the original content, and every anchor literal is asserted to occur exactly
once. A value that does not reassemble, or whose anchors are ambiguous, is
reported rather than dropped; if the gate does not pass on 100 percent of
supplied values the run raises rather than publishing a partial table.

Deliberate reuse -- nothing here is re-implemented
--------------------------------------------------
:mod:`.cross_carrier_ceiling_decomposition` owns the A2T attempt-4 carrier
and its hash pins; :mod:`.contrast_fewshot_preanalysis` owns the snapshot
bundle and the sealed-flight population loader; :mod:`.k1_hybrid_ranking_gate`
owns the DEV-1000 byte pins and population partition;
:mod:`.dev100_supply_budget_projection` owns the paired within-sample token
rate and the trace primitive it reads; :mod:`.a2t_admission_scale_sweep` owns
the A2T characters-per-token calibration against the landed prompt-fit
receipt; :mod:`.a2t_gold_absence_diagnosis` owns the form classifier;
:mod:`.dev100_reviewer_audit` owns the offline guard.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Sequence

from . import a2t_admission_scale_sweep as sweep
from . import a2t_gold_absence_diagnosis as agd
from . import contrast_fewshot_preanalysis as cf
from . import cross_carrier_ceiling_decomposition as ccd
from . import dev100_reviewer_audit as ra
from . import dev100_supply_budget_projection as sb
from . import dev500_confirmatory_read as d5
from . import k1_hybrid_ranking_gate as k1

SCHEMA = "saea-field-level-supply-accounting-v1"
EXPOSURE_ROW_ID = "SAEA-SN-MF-FIELD-LEVEL-SUPPLY-ACCOUNTING"
LEDGER_COMMIT = "834c36dd"

CHECK_DIR_RELPATH = (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-08-25-field-level-supply-accounting"
)

#: The control instruction the runner appends to every evidence contact. It is
#: NOT part of the value block; it is the fixed non-value overhead the block
#: rides on, and it is priced separately.
CONTROL_INSTRUCTION = (
    "Decide under the task contract already given above, now considering the "
    "retrieved evidence. Answer using the speech query together with the "
    "supplied knowledge evidence."
)
CONTROL_INSTRUCTION_SHA256 = (
    "ac8a0debc9dc79cdd5acd04b2cdb408c52f5f6f24173e4ce4ee1bcccd1dfda28"
)

SECONDARY_UNEXPOSED_LABEL = (
    "SECONDARY READING on the LOCKED baseline's own population (SLURP "
    "DEV-1000-NEW500, UNEXPOSED). Descriptive only: it MUST NOT be used to "
    "revise, re-tune or restate the DEV-1000 LOCK."
)
SECONDARY_EXPOSED_LABEL = (
    "SECONDARY READING on an EXPOSED population; free to read, never a "
    "campaign claim."
)
SMALL_N_CAVEAT = (
    "MECHANISM READING AT SMALL n, never an effect size. The n is published "
    "beside every figure for exactly that reason."
)
SUPERSEDED_PREMISE_CORRECTION = {
    "what_was_superseded": (
        "the exposure row SAEA-SN-MF-FIELD-LEVEL-SUPPLY-ACCOUNTING (ledger commit "
        "834c36dd) registers, in its question (4), the premise that the "
        "extraction-oriented fields are 'currently paying for a channel the landed "
        "read measured at ZERO effect'. That premise came from "
        "docs/readiness/2026-08-25-matching-vs-extraction-read.md and is FALSE"
    ),
    "the_successor": (
        "docs/readiness/2026-08-25-extraction-conditioned-on-dispatch.md, commit "
        "6c6ec719, receipt sha256 "
        "7662fbc381e6994f3c71422154a0facfc86c0e99b656cf91670577036a337525"
    ),
    "why": (
        "the earlier read conditioned on MATCHING but never on whether the "
        "trajectory RECEIVED SUPPLY. A retained trajectory stops at contact 0 and is "
        "handed no evidence at all. Its SLURP unexposed 'both matched' cell holds 273 "
        "samples of which only 3 were dispatched (98.90 percent unsupplied); its A2T "
        "'both matched' cell holds 60 of which 0 were dispatched"
    ),
    "the_corrected_effect": (
        "where the supply IS delivered the extraction channel works: SLURP dispatched "
        "n=163 official SLU-F1 +13.7570 pts CI90 [+8.8840, +18.6695] and macro "
        "slot-F1 +9.4391 pts CI90 [+4.3558, +14.5194]; A2T dispatched n=15 slot "
        "micro-F1 +12.1212 pts. Where it was not delivered A2T is -3.0250 pts with a "
        "CI90 excluding zero, which is decode variance on unsupplied trajectories"
    ),
    "consequence_for_this_row": (
        "question (4) is answered as COST PER CHANNEL against delivery, not as dead "
        "weight. No extraction-oriented field is written off. The ledger row is "
        "append-only and is left exactly as registered; this correction travels with "
        "the verdict document and this receipt"
    ),
}

ACCOUNTING_ONLY = (
    "ACCOUNTING ONLY. This module does not propose or evaluate a "
    "field-selection policy and changes no rendering. A design step is a "
    "separate, separately-registered row."
)


class AccountingError(RuntimeError):
    """Raised when a landed input does not match its pinned identity, or when
    a parse does not reassemble byte-for-byte."""


# ---------------------------------------------------------------------------
# 1. The field enumeration, read off the builders
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FieldGroup:
    """One field group of a carrier's composite value string."""

    name: str
    builder_line: str
    what_it_carries: str
    orientation: str
    orientation_justification: str
    #: The literal filler the builder emits when the source material is empty,
    #: or ``None`` when the group has no placeholder form.
    placeholder: str | None
    #: True when the builder can omit the group entirely.
    optional: bool


#: ``rails/knowledge_build_a2t.py`` lines 1035-1082 (the ``content_text``
#: f-string) plus the optional appended prior representation.
A2T_FIELD_GROUPS: tuple[FieldGroup, ...] = (
    FieldGroup(
        name="A2T-EXEMPLAR-UTTERANCE",
        builder_line='Invocation exemplar: "{row.text}"',
        what_it_carries="the construction-pool utterance this value was built from",
        orientation="MATCHING",
        orientation_justification=(
            "a natural-language utterance carrying no call syntax and no argument "
            "value schema; its only usable content is the lexical bridge from what "
            "was said to which tool it names. It is also the material the content "
            "facet embeds, i.e. the retrieval key itself"
        ),
        placeholder=None,
        optional=False,
    ),
    FieldGroup(
        name="A2T-CALL-RENDER",
        builder_line="-> tool call: {row.call_render}.",
        what_it_carries="a rendered, well-formed tool call for that utterance",
        orientation="FORM",
        orientation_justification=(
            "a literal, syntactically complete tool call. It demonstrates the SHAPE "
            "of a legal answer; its argument values belong to another utterance and "
            "cannot be copied into this one"
        ),
        placeholder=None,
        optional=False,
    ),
    FieldGroup(
        name="A2T-TOOL-IDENTITY",
        builder_line="Tool '{row.tool_name}' (domain={row.domain}, category={row.category});",
        what_it_carries="the tool name and its taxonomy position",
        orientation="MATCHING",
        orientation_justification=(
            "names the candidate and places it in a domain/category taxonomy; "
            "carries no argument schema and no answer syntax"
        ),
        placeholder=None,
        optional=False,
    ),
    FieldGroup(
        name="A2T-REGISTRY-SIGNATURE",
        builder_line="registry signature {signature or 'unavailable'};",
        what_it_carries="the callable signature with argument names and types",
        orientation="FORM",
        orientation_justification=(
            "the canonical declaration of the callable form. Classified FORM "
            "because that is its primary content, but it is the one MIXED group on "
            "this carrier: everything it adds beyond the tool name (already carried "
            "by A2T-TOOL-IDENTITY) is the argument list, which is extraction "
            "material. It is therefore reported in the BROAD extraction band as "
            "well as in the FORM class"
        ),
        placeholder="unavailable",
        optional=False,
    ),
    FieldGroup(
        name="A2T-DESCRIPTION",
        builder_line="{description or 'no registry description'}",
        what_it_carries="the registry's prose description of the tool",
        orientation="MATCHING",
        orientation_justification=(
            "prose about what the tool does; it discriminates between candidate "
            "tools and says nothing about answer syntax or argument values"
        ),
        placeholder="no registry description",
        optional=False,
    ),
    FieldGroup(
        name="A2T-ARG-DEFAULTS",
        builder_line="Argument defaults: {defaults or 'none'}.",
        what_it_carries="default values for the tool's arguments",
        orientation="EXTRACTION",
        orientation_justification=(
            "argument VALUES and nothing else. It cannot help pick the tool (it is "
            "only read once the tool is already named) and it is not answer syntax"
        ),
        placeholder="none",
        optional=False,
    ),
    FieldGroup(
        name="A2T-ARG-CONSTRAINTS",
        builder_line="Argument constraints: {constraints or 'none'}.",
        what_it_carries="the admissible ranges/enumerations for each argument",
        orientation="EXTRACTION",
        orientation_justification=(
            "the value domain of each argument. Pure fill-the-slot material, read "
            "only after the tool is chosen"
        ),
        placeholder="none",
        optional=False,
    ),
    FieldGroup(
        name="A2T-OWN-PATTERN",
        builder_line="This exemplar's argument pattern: {own_pattern}.",
        what_it_carries="the key=value pairs the exemplar's own call used",
        orientation="FORM",
        orientation_justification=(
            "the argument shape of a concrete legal call. Its VALUES are another "
            "utterance's and are not transferable, so what survives transfer is the "
            "pattern, i.e. the form. One of the two form-repair candidates the "
            "mission names"
        ),
        placeholder="no arguments",
        optional=False,
    ),
    FieldGroup(
        name="A2T-OTHER-PATTERNS",
        builder_line="Other argument patterns for this tool: {other_text}.",
        what_it_carries="up to five other argument-key signatures seen for this tool",
        orientation="FORM",
        orientation_justification=(
            "key signatures with no values attached -- e.g. '(temperature, zone)'. "
            "It is a menu of legal call shapes, not of legal values. The second "
            "form-repair candidate the mission names"
        ),
        placeholder="no other argument pattern observed for this tool",
        optional=False,
    ),
    FieldGroup(
        name="A2T-POOL-VALUES",
        builder_line=(
            "Argument values observed for this tool in the construction pool: "
            "{filler_text}."
        ),
        what_it_carries="up to five observed filler values per argument key",
        orientation="EXTRACTION",
        orientation_justification=(
            "a value inventory per argument key. Its entire purpose is to supply "
            "candidate fillers; it carries no syntax and no tool discrimination"
        ),
        placeholder="no argument values observed",
        optional=False,
    ),
    FieldGroup(
        name="A2T-EXTRA-CALLS",
        builder_line="Further calls in this exemplar: {', '.join(row.extra_call_names)}.",
        what_it_carries="the other tool names the exemplar's answer also called",
        orientation="FORM",
        orientation_justification=(
            "it says that a legal answer may contain MORE THAN ONE call, and names "
            "which. That is a statement about answer structure, not about which tool "
            "this utterance wants or what values to put in it"
        ),
        placeholder=None,
        optional=True,
    ),
    FieldGroup(
        name="A2T-PRIOR-TABLE",
        builder_line="{prior_representation[row.tool_name]}",
        what_it_carries=(
            "p(argument pattern | tool) and p(argument key | tool) as numeric "
            "frequency tables over the full construction pool"
        ),
        orientation="EXTRACTION",
        orientation_justification=(
            "a distribution over ARGUMENT KEYS conditioned on a tool that is already "
            "assumed. It cannot discriminate between tools (it is keyed by the tool) "
            "and it is not answer syntax; it exists to tell the core which arguments "
            "to populate"
        ),
        placeholder="no argument patterns observed",
        optional=True,
    ),
)

#: ``rails/knowledge_build.py`` lines 668-694 (the ``content_text`` f-string)
#: plus the optional appended prior representation. Enumerated from the code,
#: not by analogy with Audio2Tool -- the shapes differ, and SLURP has NO
#: form-oriented group at all.
SLURP_FIELD_GROUPS: tuple[FieldGroup, ...] = (
    FieldGroup(
        name="SLURP-EXEMPLAR-SENTENCE",
        builder_line='Exemplar sentence: "{row.content}"',
        what_it_carries="the TRAIN utterance this value was built from",
        orientation="MATCHING",
        orientation_justification=(
            "a natural-language sentence. Its usable content is the lexical bridge "
            "from what was said to which intent it belongs to; it is also the "
            "material the content facet embeds, i.e. the retrieval key itself"
        ),
        placeholder=None,
        optional=False,
    ),
    FieldGroup(
        name="SLURP-INTENT-LABEL",
        builder_line="-> intent {row.intent} (scenario={row.scenario}, action={row.action}).",
        what_it_carries="the exemplar's gold intent and its scenario/action decomposition",
        orientation="MATCHING",
        orientation_justification=(
            "the label the matching metric scores. It is the answer to the matching "
            "question and carries no slot content"
        ),
        placeholder=None,
        optional=False,
    ),
    FieldGroup(
        name="SLURP-SLOT-PAIRS",
        builder_line="Slot type=filler pairs: {slot_text}.",
        what_it_carries="the exemplar's own type=filler entity pairs",
        orientation="EXTRACTION",
        orientation_justification=(
            "the exemplar's own slot fillers -- exactly the object the extraction "
            "metric scores. Its fillers belong to another utterance and are not "
            "transferable; what it demonstrates is which slot types to pull"
        ),
        placeholder="no slot entities",
        optional=False,
    ),
    FieldGroup(
        name="SLURP-NORMALIZATION",
        builder_line="{normalization_text}.",
        what_it_carries=(
            "up to five surface-form variants seen elsewhere in TRAIN for each of "
            "this exemplar's entity types"
        ),
        orientation="EXTRACTION",
        orientation_justification=(
            "a surface-form inventory per entity type. It exists solely to help "
            "normalise a filler; it discriminates no intent and imposes no answer "
            "syntax"
        ),
        placeholder=(
            "no additional surface-form variants observed for this utterance's "
            "entity types"
        ),
        optional=False,
    ),
    FieldGroup(
        name="SLURP-PRIOR-TABLE",
        builder_line="{prior_representation_by_intent[row.intent]}",
        what_it_carries=(
            "p(entity type | intent) as a numeric frequency table over full TRAIN"
        ),
        orientation="EXTRACTION",
        orientation_justification=(
            "a distribution over ENTITY TYPES conditioned on an intent that is "
            "already assumed. It cannot discriminate between intents (it is keyed by "
            "the intent); it exists to tell the core which slots to fill"
        ),
        placeholder="no entity types observed",
        optional=True,
    ),
)

FIELD_GROUPS: Mapping[str, tuple[FieldGroup, ...]] = {
    "audio2tool": A2T_FIELD_GROUPS,
    "slurp": SLURP_FIELD_GROUPS,
}

#: Groups counted as extraction-oriented under the STRICT reading (the field's
#: whole content is fill-the-slot material) and under the BROAD reading (plus
#: the one mixed group, whose incremental content over its neighbours is the
#: argument list).
STRICT_EXTRACTION = {
    "audio2tool": (
        "A2T-ARG-DEFAULTS",
        "A2T-ARG-CONSTRAINTS",
        "A2T-POOL-VALUES",
        "A2T-PRIOR-TABLE",
    ),
    "slurp": ("SLURP-SLOT-PAIRS", "SLURP-NORMALIZATION", "SLURP-PRIOR-TABLE"),
}
BROAD_EXTRACTION = {
    "audio2tool": STRICT_EXTRACTION["audio2tool"] + ("A2T-REGISTRY-SIGNATURE",),
    "slurp": STRICT_EXTRACTION["slurp"],
}

#: The two groups the mission names as the obvious form-repair carriers, plus
#: the third the builder emits that is also pure answer-structure material.
FORM_CHANNEL_CANDIDATES = (
    "A2T-CALL-RENDER",
    "A2T-OWN-PATTERN",
    "A2T-OTHER-PATTERNS",
    "A2T-REGISTRY-SIGNATURE",
    "A2T-EXTRA-CALLS",
)


# ---------------------------------------------------------------------------
# 2. The segmenters -- anchors read off the builders, every boundary asserted
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Segmentation:
    """One value's field groups, in builder order, plus the payloads."""

    value_id: str
    task_target: str
    #: ``group name -> the exact substring of ``content`` that group occupies``
    segments: tuple[tuple[str, str], ...]
    #: ``group name -> the payload inside the framing literals``
    payloads: Mapping[str, str]

    def reassembles(self, content: str) -> bool:
        return "".join(text for _name, text in self.segments) == content

    def characters(self) -> dict[str, int]:
        return {name: len(text) for name, text in self.segments}


_A2T_TOOL_FACET_TAIL = re.compile(r" \d+ construction invocations in this snapshot\.$")
_SLURP_VARIANT_ANCHOR = re.compile(
    r"\. (?=\S+ surface-form variants observed elsewhere in TRAIN: )"
)
_A2T_SIGNATURE_SHAPE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*\(.*\)$")


def _require_once(haystack: str, needle: str, label: str, value_id: str) -> int:
    count = haystack.count(needle)
    if count != 1:
        raise AccountingError(
            f"{value_id}: the anchor {label} occurs {count} times, not exactly once "
            "-- the segmentation would be ambiguous and the gate refuses it"
        )
    return haystack.index(needle)


def segment_slurp_value(
    *,
    value_id: str,
    content: str,
    task_target: str,
    content_facet_representation: str,
    prior_representation: str | None,
) -> Segmentation:
    """Segment one SLURP value into its five field groups.

    The exemplar sentence and the prior table are recovered by EXACT identity
    against the snapshot's own content facet and prior facet representations,
    not by parsing, so those two boundaries carry no parsing risk at all."""

    head = f'Exemplar sentence: "{content_facet_representation}"'
    if not content.startswith(head):
        raise AccountingError(
            f"{value_id}: the value does not open with its own content facet's "
            "representation"
        )
    tail = ""
    if prior_representation is not None:
        tail = f" {prior_representation}"
        if not content.endswith(tail):
            raise AccountingError(
                f"{value_id}: the value does not close with its own prior facet's "
                "representation"
            )
    middle = content[len(head) : len(content) - len(tail)] if tail else content[len(head) :]

    slot_anchor = "). Slot type=filler pairs: "
    idx = _require_once(middle, slot_anchor, repr(slot_anchor), value_id)
    label_segment = middle[: idx + 2]
    rest = middle[idx + 2 :]
    expected_label_head = f" -> intent {task_target} (scenario="
    if not label_segment.startswith(expected_label_head):
        raise AccountingError(
            f"{value_id}: the label segment does not name the value's own task target"
        )

    placeholder_tail = (
        " no additional surface-form variants observed for this utterance's "
        "entity types."
    )
    if rest.endswith(placeholder_tail):
        slot_segment = rest[: -len(placeholder_tail)]
        norm_segment = placeholder_tail
    else:
        match = _SLURP_VARIANT_ANCHOR.search(rest)
        if match is None:
            raise AccountingError(
                f"{value_id}: neither the normalization placeholder nor a "
                "surface-form-variant line could be located"
            )
        cut = match.start() + 1  # keep the '.' with the slot segment
        slot_segment = rest[:cut]
        norm_segment = rest[cut:]
    if "surface-form variants observed elsewhere in TRAIN" in slot_segment:
        raise AccountingError(
            f"{value_id}: the slot region contains the normalization anchor phrase "
            "-- the boundary is ambiguous and the gate refuses it"
        )

    segments = [
        ("SLURP-EXEMPLAR-SENTENCE", head),
        ("SLURP-INTENT-LABEL", label_segment),
        ("SLURP-SLOT-PAIRS", slot_segment),
        ("SLURP-NORMALIZATION", norm_segment),
    ]
    if tail:
        segments.append(("SLURP-PRIOR-TABLE", tail))

    payloads = {
        "SLURP-EXEMPLAR-SENTENCE": content_facet_representation,
        "SLURP-INTENT-LABEL": label_segment[len(" -> intent ") : -1],
        "SLURP-SLOT-PAIRS": slot_segment[len(" Slot type=filler pairs: ") : -1],
        "SLURP-NORMALIZATION": norm_segment[1:-1],
    }
    if tail:
        payloads["SLURP-PRIOR-TABLE"] = prior_representation or ""

    seg = Segmentation(
        value_id=value_id,
        task_target=task_target,
        segments=tuple(segments),
        payloads=payloads,
    )
    if not seg.reassembles(content):
        raise AccountingError(f"{value_id}: SLURP segments do not reassemble byte-equal")
    return seg


def a2t_registry_block(tool_facet_representation: str, tool: str) -> str:
    """The registry-derived substring the tool facet and every value of that
    tool share BYTE FOR BYTE, recovered from the facet rather than parsed out
    of the value."""

    anchor = "); registry signature "
    idx = tool_facet_representation.find(anchor)
    if idx < 0:
        raise AccountingError(f"tool facet for {tool!r} has no registry-signature anchor")
    block = tool_facet_representation[idx + len("); ") :]
    match = _A2T_TOOL_FACET_TAIL.search(block)
    if match is None:
        raise AccountingError(
            f"tool facet for {tool!r} does not close with its invocation count"
        )
    return block[: match.start()] + " "


def segment_a2t_value(
    *,
    value_id: str,
    content: str,
    task_target: str,
    content_facet_representation: str,
    registry_block: str,
    prior_representation: str | None,
) -> Segmentation:
    """Segment one Audio2Tool value into its up-to-twelve field groups.

    The exemplar utterance, the registry block (signature + description +
    defaults + constraints) and the prior table are recovered by EXACT
    identity against the snapshot's own facet representations."""

    head = f'Invocation exemplar: "{content_facet_representation}"'
    if not content.startswith(head):
        raise AccountingError(
            f"{value_id}: the value does not open with its own content facet's "
            "representation"
        )
    tail = ""
    if prior_representation is not None:
        tail = f" {prior_representation}"
        if not content.endswith(tail):
            raise AccountingError(
                f"{value_id}: the value does not close with its own prior facet's "
                "representation"
            )
    body = content[len(head) : len(content) - len(tail)] if tail else content[len(head) :]

    identity_anchor = f". Tool '{task_target}' (domain="
    idx = _require_once(body, identity_anchor, repr(identity_anchor), value_id)
    call_segment = body[: idx + 1]
    after_call = body[idx + 1 :]

    reg_idx = _require_once(after_call, registry_block, "the tool's registry block", value_id)
    identity_segment = after_call[: reg_idx - 1]
    if not identity_segment.endswith(";"):
        raise AccountingError(f"{value_id}: the tool-identity segment does not close with ';'")
    reg_segment = after_call[reg_idx - 1 : reg_idx + len(registry_block) - 1]
    remainder = after_call[reg_idx + len(registry_block) - 1 :]

    # Split the registry block into signature / description / defaults /
    # constraints. Each anchor is asserted unique inside the block itself.
    inner = reg_segment[len(" registry signature ") :]
    d_idx = _require_once(inner, " Argument defaults: ", "' Argument defaults: '", value_id)
    sig_and_desc = inner[:d_idx]
    defaults_and_constraints = inner[d_idx:]
    if "; " not in sig_and_desc:
        raise AccountingError(f"{value_id}: no signature/description delimiter")
    sig, _, desc = sig_and_desc.partition("; ")
    if sig != "unavailable" and not _A2T_SIGNATURE_SHAPE.match(sig):
        raise AccountingError(
            f"{value_id}: the recovered registry signature {sig!r} is not a callable "
            "shape -- the signature/description boundary is unsafe and the gate "
            "refuses it"
        )
    c_idx = _require_once(
        defaults_and_constraints,
        " Argument constraints: ",
        "' Argument constraints: '",
        value_id,
    )
    signature_segment = f" registry signature {sig};"
    description_segment = f" {desc}"
    defaults_segment = defaults_and_constraints[:c_idx]
    constraints_segment = defaults_and_constraints[c_idx:]
    # ``registry_block`` carries a trailing space; the slice above assigns that
    # space to ``remainder`` instead, so every group after the first opens with
    # its own separator and the constraints segment closes on its period.
    if not constraints_segment.endswith("."):
        raise AccountingError(f"{value_id}: the constraints segment does not close with '.'")

    own_anchor = " This exemplar's argument pattern: "
    other_anchor = " Other argument patterns for this tool: "
    pool_anchor = " Argument values observed for this tool in the construction pool: "
    extra_anchor = " Further calls in this exemplar: "

    o_idx = _require_once(remainder, own_anchor, repr(own_anchor), value_id)
    if o_idx != 0:
        raise AccountingError(f"{value_id}: the argument-pattern block does not start where expected")
    p_idx = _require_once(remainder, other_anchor, repr(other_anchor), value_id)
    v_idx = _require_once(remainder, pool_anchor, repr(pool_anchor), value_id)
    own_segment = remainder[:p_idx]
    other_segment = remainder[p_idx:v_idx]
    pool_rest = remainder[v_idx:]

    extra_segment = ""
    extra_count = pool_rest.count(extra_anchor)
    if extra_count > 1:
        raise AccountingError(
            f"{value_id}: the further-calls anchor occurs {extra_count} times"
        )
    if extra_count == 1:
        e_idx = pool_rest.index(extra_anchor)
        pool_segment = pool_rest[:e_idx]
        extra_segment = pool_rest[e_idx:]
    else:
        pool_segment = pool_rest

    segments = [
        ("A2T-EXEMPLAR-UTTERANCE", head),
        ("A2T-CALL-RENDER", call_segment),
        ("A2T-TOOL-IDENTITY", identity_segment),
        ("A2T-REGISTRY-SIGNATURE", signature_segment),
        ("A2T-DESCRIPTION", description_segment),
        ("A2T-ARG-DEFAULTS", defaults_segment),
        ("A2T-ARG-CONSTRAINTS", constraints_segment),
        ("A2T-OWN-PATTERN", own_segment),
        ("A2T-OTHER-PATTERNS", other_segment),
        ("A2T-POOL-VALUES", pool_segment),
    ]
    if extra_segment:
        segments.append(("A2T-EXTRA-CALLS", extra_segment))
    if tail:
        segments.append(("A2T-PRIOR-TABLE", tail))

    payloads = {
        "A2T-EXEMPLAR-UTTERANCE": content_facet_representation,
        "A2T-CALL-RENDER": call_segment[len(" -> tool call: ") : -1],
        "A2T-TOOL-IDENTITY": identity_segment,
        "A2T-REGISTRY-SIGNATURE": sig,
        "A2T-DESCRIPTION": desc,
        "A2T-ARG-DEFAULTS": defaults_segment[len(" Argument defaults: ") : -1],
        "A2T-ARG-CONSTRAINTS": constraints_segment[len(" Argument constraints: ") : -1],
        "A2T-OWN-PATTERN": own_segment[len(own_anchor) : -1],
        "A2T-OTHER-PATTERNS": other_segment[len(other_anchor) : -1],
        "A2T-POOL-VALUES": pool_segment[len(pool_anchor) : -1],
    }
    if extra_segment:
        payloads["A2T-EXTRA-CALLS"] = extra_segment[len(extra_anchor) : -1]
    if tail:
        payloads["A2T-PRIOR-TABLE"] = prior_representation or ""

    seg = Segmentation(
        value_id=value_id,
        task_target=task_target,
        segments=tuple(segments),
        payloads=payloads,
    )
    if not seg.reassembles(content):
        raise AccountingError(f"{value_id}: A2T segments do not reassemble byte-equal")
    return seg


# ---------------------------------------------------------------------------
# 3. Snapshot-wide segmentation and the parse-fidelity gate
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SegmentedSnapshot:
    carrier: str
    snapshot_sha256: str
    segmentations: Mapping[str, Segmentation]
    contents: Mapping[str, str]
    gate: Mapping[str, object]


def segment_snapshot(bundle: cf.SnapshotBundle, carrier: str) -> SegmentedSnapshot:
    """Segment EVERY value in the pinned snapshot and gate the parse."""

    facet_representation = {
        facet.facet_id: str(facet.representation) for facet in bundle.snapshot.facets
    }
    registry_blocks: dict[str, str] = {}
    if carrier == "audio2tool":
        for facet_id, representation in facet_representation.items():
            if facet_id.startswith("facet:label:tool:"):
                tool = facet_id[len("facet:label:tool:") :]
                registry_blocks[tool] = a2t_registry_block(representation, tool)

    segmentations: dict[str, Segmentation] = {}
    contents: dict[str, str] = {}
    failures: list[dict[str, str]] = []
    for value in bundle.snapshot.values:
        value_id = str(value.value_id)
        content = str(value.content)
        contents[value_id] = content
        target = str(value.task_target)
        unit_id = value_id[len("value:") :] if value_id.startswith("value:") else value_id
        content_rep = facet_representation.get(f"facet:content:{unit_id}")
        if content_rep is None:
            failures.append({"value_id": value_id, "reason": "no content facet"})
            continue
        prior_rep = facet_representation.get(f"facet:prior:{target}")
        try:
            if carrier == "slurp":
                seg = segment_slurp_value(
                    value_id=value_id,
                    content=content,
                    task_target=target,
                    content_facet_representation=content_rep,
                    prior_representation=prior_rep,
                )
            else:
                block = registry_blocks.get(target)
                if block is None:
                    failures.append({"value_id": value_id, "reason": "no tool facet"})
                    continue
                seg = segment_a2t_value(
                    value_id=value_id,
                    content=content,
                    task_target=target,
                    content_facet_representation=content_rep,
                    registry_block=block,
                    prior_representation=prior_rep,
                )
        except AccountingError as error:
            failures.append({"value_id": value_id, "reason": str(error)})
            continue
        segmentations[value_id] = seg

    total = len(bundle.snapshot.values)
    gate = {
        "carrier": carrier,
        "snapshot_values": total,
        "segmented": len(segmentations),
        "reassembled_byte_equal": len(segmentations),
        "failures": len(failures),
        "failure_rows": failures[:20],
        "semantics": (
            "every value is split on anchors read off the builder, every anchor is "
            "asserted to occur exactly once, the exemplar / registry-block / prior "
            "boundaries are recovered by EXACT identity against the snapshot's own "
            "facet representations rather than parsed, and the segments are "
            "reassembled and asserted byte-equal to the original content"
        ),
        "passed": not failures,
    }
    if failures:
        raise AccountingError(
            f"{carrier}: the parse-fidelity gate failed on {len(failures)} of {total} "
            f"snapshot values; first failure: {failures[0]}"
        )
    return SegmentedSnapshot(
        carrier=carrier,
        snapshot_sha256=bundle.snapshot_sha256,
        segmentations=segmentations,
        contents=contents,
        gate=gate,
    )


def is_placeholder(carrier: str, group: str, payload: str) -> bool:
    for entry in FIELD_GROUPS[carrier]:
        if entry.name != group:
            continue
        if entry.placeholder is None:
            return False
        if group in ("A2T-PRIOR-TABLE", "SLURP-PRIOR-TABLE"):
            return payload.rstrip().endswith(entry.placeholder + ".")
        return payload == entry.placeholder
    raise AccountingError(f"unknown field group {group!r} for carrier {carrier!r}")


# ---------------------------------------------------------------------------
# 4. Token models -- the campaign's own established offline estimators
# ---------------------------------------------------------------------------


#: The two groups whose content is a DENSE NUMERIC FREQUENCY TABLE rather
#: than prose or a short list. ``dev100_supply_budget_projection.token_model``
#: already records that those tables tokenize at about 1.93 characters per
#: token against roughly twice that for exemplar prose; this module measures
#: the two rates separately rather than assuming one.
DENSE_GROUPS = frozenset({"SLURP-PRIOR-TABLE", "A2T-PRIOR-TABLE"})

#: Groups whose content is a comma/semicolon-separated LIST of values or
#: constraints. They are priced at the PROSE rate here, which under-prices
#: them; every one of them is extraction-oriented, so the extraction share
#: this module reports is a LOWER bound.
LIST_LIKE_UNDERPRICED_GROUPS = (
    "A2T-ARG-DEFAULTS",
    "A2T-ARG-CONSTRAINTS",
    "A2T-POOL-VALUES",
    "A2T-OTHER-PATTERNS",
)


def _ols(xs: Sequence[float], ys: Sequence[float]) -> dict[str, float]:
    n = float(len(xs))
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    covariance = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True))
    variance = sum((x - mean_x) ** 2 for x in xs)
    if variance <= 0.0:
        raise AccountingError("the supplied-value character counts do not vary")
    slope = covariance / variance
    intercept = mean_y - slope * mean_x
    residuals = [y - (intercept + slope * x) for x, y in zip(xs, ys, strict=True)]
    total_ss = sum((y - mean_y) ** 2 for y in ys)
    residual_ss = sum(value**2 for value in residuals)
    return {
        "slope": slope,
        "intercept": intercept,
        "r_squared": 1.0 - (residual_ss / total_ss) if total_ss > 0 else float("nan"),
        "max_absolute_residual": max(abs(value) for value in residuals),
        "n": len(xs),
    }


@dataclass(frozen=True)
class TokenPricer:
    """One measured character-to-token model, and its calibration error."""

    name: str
    #: ``field group -> tokens per character``
    rates: Mapping[str, float]
    default_rate: float
    report: Mapping[str, object]

    def tokens(self, group: str, characters: int) -> float:
        return characters * self.rates.get(group, self.default_rate)


def _multi_ols(design, y):
    import numpy as np

    matrix = np.asarray(design, dtype=float)
    target = np.asarray(y, dtype=float)
    beta, *_ = np.linalg.lstsq(matrix, target, rcond=None)
    predicted = matrix @ beta
    residual = target - predicted
    total = ((target - target.mean()) ** 2).sum()
    return {
        "beta": [float(value) for value in beta],
        "r_squared": float(1.0 - (residual**2).sum() / total) if total > 0 else float("nan"),
        "max_absolute_residual": float(abs(residual).max()),
        "rmse": float((residual**2).mean() ** 0.5),
    }


def _holdout_mae(design, y, *, folds: int = 5, seed: int = 20260807) -> dict[str, float]:
    import numpy as np

    matrix = np.asarray(design, dtype=float)
    target = np.asarray(y, dtype=float)
    order = np.arange(len(target))
    np.random.default_rng(seed).shuffle(order)
    errors = []
    for fold in np.array_split(order, folds):
        mask = np.ones(len(target), dtype=bool)
        mask[fold] = False
        beta, *_ = np.linalg.lstsq(matrix[mask], target[mask], rcond=None)
        errors.append(np.abs(target[~mask] - matrix[~mask] @ beta))
    joined = np.concatenate(errors)
    return {
        "folds": folds,
        "seed": seed,
        "mean_absolute_error_tokens": round(float(joined.mean()), 3),
        "max_absolute_error_tokens": round(float(joined.max()), 2),
    }


def build_pricers(
    *,
    carrier: str,
    paired_rows: Sequence[Mapping[str, object]],
    single_rate: Mapping[str, object],
) -> dict[str, TokenPricer]:
    """Fit the registered single-rate model and the two-rate refinement.

    ``paired_rows`` carries, per paired contact, the prompt-token delta and
    the supplied block's characters broken down by field group. Three models
    are fitted; the third is REFUSED and the refusal is published:

    1. **UNIFORM** -- the registered estimator
       (``dev100_supply_budget_projection.flown_value_token_rate``): one rate
       for every character of value text.
    2. **DENSE/PROSE** -- the same paired within-sample regression with TWO
       predictors, splitting the dense numeric prior table from everything
       else. Motivated and then confirmed by the landed density contrast.
    3. **PER-GROUP** -- one rate per field group. Fitted, measured, and
       REFUSED because the group character counts are collinear (the intent
       label's length is determined by the same intent that determines the
       prior table), which drives at least one coefficient negative. A
       negative tokens-per-character is not a quantity, so this model is not
       used and its coefficients are published as the reason.
    """

    groups = [entry.name for entry in FIELD_GROUPS[carrier]]
    dense = [name for name in groups if name in DENSE_GROUPS]
    prose = [name for name in groups if name not in DENSE_GROUPS]

    y = [float(row["prompt_token_delta"]) for row in paired_rows]
    chars = [row["characters_by_group"] for row in paired_rows]  # type: ignore[index]
    prose_x = [sum(float(row.get(name, 0)) for name in prose) for row in chars]  # type: ignore[union-attr]
    dense_x = [sum(float(row.get(name, 0)) for name in dense) for row in chars]  # type: ignore[union-attr]

    two = _multi_ols([[p, d, 1.0] for p, d in zip(prose_x, dense_x, strict=True)], y)
    two_hold = _holdout_mae(
        [[p, d, 1.0] for p, d in zip(prose_x, dense_x, strict=True)], y
    )
    prose_rate, dense_rate, two_intercept = two["beta"]

    per_group_design = [
        [float(row.get(name, 0)) for name in groups] + [1.0] for row in chars  # type: ignore[union-attr]
    ]
    per_group = _multi_ols(per_group_design, y)
    per_group_rates = dict(zip(groups, per_group["beta"][:-1], strict=True))
    negative = {name: rate for name, rate in per_group_rates.items() if rate <= 0.0}

    uniform_slope = float(single_rate["_slope"])
    uniform_x = [[p + d, 1.0] for p, d in zip(prose_x, dense_x, strict=True)]
    uniform_hold = _holdout_mae(uniform_x, y)

    usable_two_rate = prose_rate > 0.0 and dense_rate > 0.0

    uniform = TokenPricer(
        name="UNIFORM",
        rates={},
        default_rate=uniform_slope,
        report={
            "model": (
                "the REGISTERED estimator: "
                "dev100_supply_budget_projection.flown_value_token_rate, one "
                "tokens-per-character rate for every character of value text"
            ),
            "tokens_per_character": round(uniform_slope, 6),
            "characters_per_token": round(1.0 / uniform_slope, 4),
            "intercept_tokens": single_rate["constant_instruction_cost_tokens"],
            "r_squared": single_rate["r_squared"],
            "max_absolute_residual_tokens": single_rate["max_absolute_residual_tokens"],
            "paired_contacts": single_rate["paired_contacts"],
            "holdout": uniform_hold,
            "consequence": (
                "because it is linear in characters, a field group's TOKEN share "
                "under this model equals its CHARACTER share exactly"
            ),
        },
    )
    two_rate = TokenPricer(
        name="DENSE/PROSE",
        rates={name: dense_rate for name in dense},
        default_rate=prose_rate,
        report={
            "model": (
                "the same paired within-sample regression with TWO predictors: the "
                "dense numeric prior table separated from every other character of "
                "value text"
            ),
            "dense_groups": dense,
            "prose_tokens_per_character": round(prose_rate, 6),
            "prose_characters_per_token": (
                round(1.0 / prose_rate, 4) if prose_rate > 0 else None
            ),
            "dense_tokens_per_character": round(dense_rate, 6),
            "dense_characters_per_token": (
                round(1.0 / dense_rate, 4) if dense_rate > 0 else None
            ),
            "intercept_tokens": round(two_intercept, 3),
            "r_squared": round(two["r_squared"], 6),
            "max_absolute_residual_tokens": round(two["max_absolute_residual"], 2),
            "rmse_tokens": round(two["rmse"], 2),
            "paired_contacts": len(y),
            "holdout": two_hold,
            "independent_confirmation": (
                "dev100_supply_budget_projection.token_model measured 1.93 characters "
                "per token on three of these same dense prior tables from the two "
                "landed prompt-fit receipts, by a completely different route (a "
                "tokenizer-only receipt difference). This regression lands nearby, "
                "which is the cross-check"
            ),
            "usable": usable_two_rate,
        },
    )
    refused = {
        "model": "one tokens-per-character rate per field group",
        "coefficients_tokens_per_character": {
            name: round(rate, 6) for name, rate in per_group_rates.items()
        },
        "intercept_tokens": round(per_group["beta"][-1], 3),
        "r_squared": round(per_group["r_squared"], 6),
        "max_absolute_residual_tokens": round(per_group["max_absolute_residual"], 2),
        "negative_coefficients": {name: round(rate, 6) for name, rate in negative.items()},
        "refused": bool(negative),
        "reason": (
            "the per-group character counts are COLLINEAR -- a value's label segment "
            "length is determined by the same task target that determines its prior "
            "table -- so the fit drives at least one coefficient negative. A negative "
            "tokens-per-character is not a quantity, so this model is measured, "
            "published and NOT used"
        ),
    }
    return {
        "uniform": uniform,
        "two_rate": two_rate,
        "_refused_per_group": refused,  # type: ignore[dict-item]
    }


def _characters_by_group(
    supplied: Sequence[str], segmented: "SegmentedSnapshot"
) -> dict[str, int]:
    out: dict[str, int] = {}
    for value_id in supplied:
        for name, text in segmented.segmentations[value_id].segments:
            out[name] = out.get(name, 0) + len(text)
    return out


def a2t_paired_token_rate(
    *,
    carrier: ccd.A2TAttempt4,
    data_root: Path,
    segmented: SegmentedSnapshot,
) -> dict[str, object]:
    """The established paired within-sample method, executed ACROSS the three
    sealed A2T attempt traces.

    :func:`.dev100_supply_budget_projection.flown_value_token_rate` cannot be
    called unmodified on this carrier: attempt 4 carries only the fifteen
    EVIDENCE contacts, while the Pass-A DIRECT contacts of the same
    trajectories landed in attempts 1 and 2. This function reuses that
    module's own trace primitive on each attempt directory and pairs a
    trajectory ONLY when the direct contact's response text re-hashes to the
    ``direct_response_sha256`` the sealed attempt-4 Pass-A file carries, so no
    substitution is possible. This is stated rather than hidden: it is the
    same estimator, executed across attempt boundaries."""

    run_dir = Path(data_root) / "runs" / ccd.A2T_RUN_ID / ccd.A2T_ATTEMPT4_ID
    evidence = sb._load_contact_prompt_tokens(run_dir, ccd.A2T_RUN_ID)
    direct: dict[str, int] = {}
    sources: dict[str, str] = {}
    for attempt in ccd.A2T_PASS_A_ATTEMPTS if hasattr(ccd, "A2T_PASS_A_ATTEMPTS") else (
        "attempt-20260825T101057Z-a2tg1blend",
        "attempt-20260825T114856Z-a2tg1blend",
    ):
        attempt_dir = Path(data_root) / "runs" / ccd.A2T_RUN_ID / attempt
        trace = attempt_dir / f"{ccd.A2T_RUN_ID}.trace.jsonl"
        if not trace.exists():
            continue
        texts_by_request: dict[str, str] = {}
        kind_by_request: dict[str, tuple[str, str]] = {}
        tokens_by_request: dict[str, int] = {}
        with trace.open(encoding="utf-8") as handle:
            for line in handle:
                record = json.loads(line)
                channel = record["channel"]
                record_id = str(record["record_id"])
                if channel == "MODEL_REQUEST":
                    payload = record["payload"]["payload"]
                    representation = str(payload.get("key_representation_id", ""))
                    kind = "direct" if representation.endswith(":direct") else "evidence"
                    kind_by_request[str(payload["request_id"])] = (
                        str(payload["sample_id"]),
                        kind,
                    )
                elif channel == "MODEL_RESPONSE":
                    texts_by_request[record_id.rsplit("/", 1)[0]] = str(
                        record["payload"]["response_text_sha256"]
                    )
                elif channel == "COST" and record_id.endswith("/cost"):
                    tokens = record["payload"].get("prompt_tokens")
                    if tokens is not None:
                        tokens_by_request[record_id[: -len("/cost")]] = int(tokens)
        for request_id, (sample_id, kind) in kind_by_request.items():
            if kind != "direct" or sample_id in direct:
                continue
            digest = texts_by_request.get(request_id)
            expected = hashlib.sha256(
                carrier.direct_texts[sample_id].encode("utf-8")
            ).hexdigest()
            if digest != expected:
                continue
            tokens = tokens_by_request.get(request_id)
            if tokens is None:
                continue
            direct[sample_id] = tokens
            sources[sample_id] = attempt

    xs: list[float] = []
    ys: list[float] = []
    rows: list[dict[str, object]] = []
    for sample_id, evidence_pair in sorted(evidence.items()):
        if "evidence" not in evidence_pair or sample_id not in direct:
            continue
        supplied = carrier.flown_supply.get(sample_id, ())
        chars = sum(len(segmented.contents[value_id]) for value_id in supplied)
        delta = evidence_pair["evidence"] - direct[sample_id]
        xs.append(float(chars))
        ys.append(float(delta))
        rows.append(
            {
                "sample_id": sample_id,
                "supplied_values": len(supplied),
                "supplied_value_characters": chars,
                "characters_by_group": _characters_by_group(supplied, segmented),
                "prompt_token_delta": delta,
                "direct_contact_source_attempt": sources[sample_id],
            }
        )
    unpaired = sorted(
        sample_id
        for sample_id, pair in evidence.items()
        if "evidence" in pair and sample_id not in direct
    )
    if len(xs) < 5:
        raise AccountingError("too few paired A2T contacts to measure a value-token rate")
    fit = _ols(xs, ys)
    return {
        "method": (
            "the established paired within-sample method of "
            "dev100_supply_budget_projection.flown_value_token_rate, executed across "
            "the three sealed A2T attempt traces because attempt 4 carries only the "
            "evidence contacts while their Pass-A direct partners landed in attempts "
            "1 and 2. A trajectory is paired only when the direct contact's response "
            "re-hashes to the sealed Pass-A digest"
        ),
        "note_on_the_prompt_difference": (
            "the evidence request's history carries ONLY the control instruction (no "
            "assistant turn), verified on the landed MODEL_REQUEST payloads, so "
            "prompt_tokens(evidence) - prompt_tokens(direct) is exactly the control "
            "instruction plus the supplied value block and the regression intercept "
            "is a genuine constant"
        ),
        "paired_contacts": len(xs),
        "unpaired_evidence_contacts": unpaired,
        "tokens_per_character_of_value_text": round(fit["slope"], 6),
        "characters_per_token_of_value_text": (
            round(1.0 / fit["slope"], 4) if fit["slope"] > 0 else None
        ),
        "constant_instruction_cost_tokens": round(fit["intercept"], 2),
        "r_squared": round(fit["r_squared"], 6),
        "max_absolute_residual_tokens": round(fit["max_absolute_residual"], 2),
        "supplied_value_character_range": [int(min(xs)), int(max(xs))],
        "rows": rows,
        "_slope": fit["slope"],
        "_intercept": fit["intercept"],
    }


def slurp_paired_token_rate(cell: cf.CellPopulation, segmented: SegmentedSnapshot) -> dict:
    """:func:`.dev100_supply_budget_projection.flown_value_token_rate`, called
    unmodified on the DEV-1000 BLEND flight this row is accounting for.

    The imported function adds ``VALUE_EVIDENCE_PREFIX_CHARS`` per value -- the
    ``[evidence 000:value:value] `` prefix the PROMPT-FIT SCRIPTS render. The
    flown runner (``rails.runner._agent_messages``) renders no such prefix, so
    this module also reports the same regression against the RAW value
    characters and uses the raw-character slope, with the imported figure kept
    beside it as the published cross-check."""

    imported = sb.flown_value_token_rate({cell.pin.population_id: cell})
    paired = sb._load_contact_prompt_tokens(cell.run_dir, cell.pin.run_id)
    xs: list[float] = []
    ys: list[float] = []
    rows: list[dict[str, object]] = []
    for sample_id in cell.sample_ids:
        by_id = paired.get(sample_id, {})
        if "direct" not in by_id or "evidence" not in by_id:
            continue
        supplied = tuple(cell.inputs.logged_supply.get(sample_id, ()) or ())
        if not supplied:
            continue
        chars = sum(len(segmented.contents[value_id]) for value_id in supplied)
        delta = by_id["evidence"] - by_id["direct"]
        xs.append(float(chars))
        ys.append(float(delta))
        rows.append(
            {
                "sample_id": sample_id,
                "supplied_values": len(supplied),
                "supplied_value_characters": chars,
                "characters_by_group": _characters_by_group(supplied, segmented),
                "prompt_token_delta": delta,
            }
        )
    fit = _ols(xs, ys)
    return {
        "method": (
            "dev100_supply_budget_projection.flown_value_token_rate, called on the "
            "DEV-1000 BLEND flight itself; restated against RAW value characters "
            "because the flown runner renders no '[evidence NNN:value:value] ' prefix"
        ),
        "imported_call": {
            key: value
            for key, value in imported.items()
            if not key.startswith("_") and key != "rows"
        },
        "paired_contacts": len(xs),
        "tokens_per_character_of_value_text": round(fit["slope"], 6),
        "characters_per_token_of_value_text": (
            round(1.0 / fit["slope"], 4) if fit["slope"] > 0 else None
        ),
        "constant_instruction_cost_tokens": round(fit["intercept"], 2),
        "r_squared": round(fit["r_squared"], 6),
        "max_absolute_residual_tokens": round(fit["max_absolute_residual"], 2),
        "supplied_value_character_range": [int(min(xs)), int(max(xs))],
        "rows": rows,
        "_slope": fit["slope"],
        "_intercept": fit["intercept"],
    }


# ---------------------------------------------------------------------------
# 5. The accounting itself
# ---------------------------------------------------------------------------


@dataclass
class SupplyAccount:
    """Per-field-group totals over a set of CONTACTS (values weighted by how
    often they were actually supplied)."""

    carrier: str
    population: str
    #: Every trajectory in the population, whether or not it received supply.
    population_size: int = 0
    contacts: int = 0
    values_supplied: int = 0
    characters: dict[str, int] = field(default_factory=dict)
    placeholder_characters: dict[str, int] = field(default_factory=dict)
    placeholder_occurrences: dict[str, int] = field(default_factory=dict)
    occurrences: dict[str, int] = field(default_factory=dict)
    per_contact_characters: list[int] = field(default_factory=list)
    supplied_multiset: dict[str, int] = field(default_factory=dict)

    def add_value(self, seg: Segmentation) -> None:
        self.values_supplied += 1
        self.supplied_multiset[seg.value_id] = self.supplied_multiset.get(seg.value_id, 0) + 1
        for name, text in seg.segments:
            self.characters[name] = self.characters.get(name, 0) + len(text)
            self.occurrences[name] = self.occurrences.get(name, 0) + 1
            if is_placeholder(self.carrier, name, seg.payloads.get(name, "")):
                self.placeholder_characters[name] = (
                    self.placeholder_characters.get(name, 0) + len(text)
                )
                self.placeholder_occurrences[name] = (
                    self.placeholder_occurrences.get(name, 0) + 1
                )

    def total_characters(self) -> int:
        return sum(self.characters.values())


def build_account(
    *,
    carrier: str,
    population: str,
    supply: Mapping[str, Sequence[str]],
    sample_ids: Sequence[str],
    segmented: SegmentedSnapshot,
) -> SupplyAccount:
    account = SupplyAccount(
        carrier=carrier, population=population, population_size=len(sample_ids)
    )
    for sample_id in sample_ids:
        supplied = tuple(supply.get(sample_id, ()) or ())
        if not supplied:
            continue
        account.contacts += 1
        contact_chars = 0
        for value_id in supplied:
            seg = segmented.segmentations.get(value_id)
            if seg is None:
                raise AccountingError(
                    f"{sample_id}: supplied value {value_id!r} is not in the pinned snapshot"
                )
            account.add_value(seg)
            contact_chars += len(segmented.contents[value_id])
        account.per_contact_characters.append(contact_chars)
    return account


def account_table(
    account: SupplyAccount, *, pricer: TokenPricer, label: str
) -> dict[str, object]:
    groups = FIELD_GROUPS[account.carrier]
    total_chars = account.total_characters()
    total_tokens = sum(
        pricer.tokens(entry.name, account.characters.get(entry.name, 0)) for entry in groups
    )
    rows = []
    for entry in groups:
        chars = account.characters.get(entry.name, 0)
        occurrences = account.occurrences.get(entry.name, 0)
        ph_chars = account.placeholder_characters.get(entry.name, 0)
        ph_n = account.placeholder_occurrences.get(entry.name, 0)
        tokens = pricer.tokens(entry.name, chars)
        rows.append(
            {
                "field_group": entry.name,
                "orientation": entry.orientation,
                "present_in_values": occurrences,
                "present_fraction_of_supplied_values": (
                    round(occurrences / account.values_supplied, 6)
                    if account.values_supplied
                    else None
                ),
                "characters": chars,
                "character_share_of_supply_block": (
                    round(chars / total_chars, 6) if total_chars else None
                ),
                "estimated_tokens": round(tokens, 1),
                "token_share_of_supply_block": (
                    round(tokens / total_tokens, 6) if total_tokens else None
                ),
                "estimated_tokens_per_contact": (
                    round(tokens / account.contacts, 2) if account.contacts else None
                ),
                "estimated_tokens_per_occurrence": (
                    round(tokens / occurrences, 2) if occurrences else None
                ),
                "mean_characters_per_occurrence": (
                    round(chars / occurrences, 2) if occurrences else None
                ),
                "tokens_per_character_used": round(
                    pricer.rates.get(entry.name, pricer.default_rate), 6
                ),
                "placeholder_occurrences": ph_n,
                "placeholder_fraction_of_occurrences": (
                    round(ph_n / occurrences, 6) if occurrences else None
                ),
                "placeholder_characters": ph_chars,
                "placeholder_estimated_tokens": round(
                    pricer.tokens(entry.name, ph_chars), 1
                ),
            }
        )
    per_contact = sorted(account.per_contact_characters)
    return {
        "population": account.population,
        "label": label,
        "token_model": pricer.name,
        "contacts_with_supply": account.contacts,
        "values_supplied_total": account.values_supplied,
        "mean_values_per_contact": (
            round(account.values_supplied / account.contacts, 4) if account.contacts else None
        ),
        "supply_block_characters_total": total_chars,
        "supply_block_estimated_tokens_total": round(total_tokens, 1),
        "supply_block_estimated_tokens_per_contact": (
            round(total_tokens / account.contacts, 2) if account.contacts else None
        ),
        "supply_block_characters_per_contact": {
            "min": per_contact[0] if per_contact else None,
            "median": per_contact[len(per_contact) // 2] if per_contact else None,
            "mean": round(total_chars / account.contacts, 2) if account.contacts else None,
            "max": per_contact[-1] if per_contact else None,
        },
        "placeholder_estimated_tokens_total": round(
            sum(
                pricer.tokens(entry.name, account.placeholder_characters.get(entry.name, 0))
                for entry in groups
            ),
            1,
        ),
        "rows": rows,
    }


def channel_cost(
    table: Mapping[str, object],
    carrier: str,
    *,
    pricer: TokenPricer,
    population_size: int,
) -> dict[str, object]:
    """What each channel COSTS, against how often it is actually delivered.

    This block was registered as a "dead weight" computation on the premise
    that the extraction channel had been measured at zero effect. That premise
    was superseded before this module ran, by
    ``docs/readiness/2026-08-25-extraction-conditioned-on-dispatch.md``
    (commit ``6c6ec719``), which showed the earlier read never conditioned on
    whether a trajectory RECEIVED supply: where the supply is delivered the
    extraction channel WORKS. So nothing here is written off. What is reported
    is the cost of carrying each channel and the delivery rate it is carried
    at."""

    rows = {row["field_group"]: row for row in table["rows"]}  # type: ignore[index]
    total_chars = int(table["supply_block_characters_total"])  # type: ignore[arg-type]
    total_tokens = float(table["supply_block_estimated_tokens_total"])  # type: ignore[arg-type]
    contacts = int(table["contacts_with_supply"])  # type: ignore[arg-type]

    def band(names: Sequence[str]) -> dict[str, object]:
        chars = sum(int(rows[name]["characters"]) for name in names if name in rows)
        tokens = sum(
            pricer.tokens(name, int(rows[name]["characters"])) for name in names if name in rows
        )
        return {
            "field_groups": list(names),
            "characters": chars,
            "character_fraction_of_supply_block": (
                round(chars / total_chars, 6) if total_chars else None
            ),
            "estimated_tokens_total": round(tokens, 1),
            "token_fraction_of_supply_block": (
                round(tokens / total_tokens, 6) if total_tokens else None
            ),
            "estimated_tokens_per_delivered_contact": (
                round(tokens / contacts, 2) if contacts else None
            ),
            "estimated_tokens_amortized_over_the_whole_population": (
                round(tokens / population_size, 2) if population_size else None
            ),
        }

    strict = band(STRICT_EXTRACTION[carrier])
    broad = band(BROAD_EXTRACTION[carrier])
    matching = band(
        tuple(entry.name for entry in FIELD_GROUPS[carrier] if entry.orientation == "MATCHING")
    )
    form = band(
        tuple(entry.name for entry in FIELD_GROUPS[carrier] if entry.orientation == "FORM")
    )
    return {
        "reading": (
            "cost per channel, against delivery. The extraction channel is NOT dead "
            "weight: conditioned on dispatch it works (SLURP dispatched n=163, "
            "official SLU-F1 +13.7570 pts CI90 [+8.8840, +18.6695]; A2T dispatched "
            "n=15, slot micro-F1 +12.1212 pts). What the accounting shows is how "
            "much of the injected token budget each channel consumes and how often "
            "that budget is actually delivered"
        ),
        "delivery": {
            "population_size": population_size,
            "contacts_that_received_supply": contacts,
            "delivery_rate": (
                round(contacts / population_size, 6) if population_size else None
            ),
            "semantics": (
                "a RETAINED trajectory stops at contact 0 and is handed no evidence "
                "at all; only a DISPATCHED trajectory receives supply"
            ),
        },
        "superseded_premise": (
            "this block was registered as a DEAD-WEIGHT computation on the premise "
            "that the extraction channel had been measured at zero effect. That "
            "premise is superseded by "
            "docs/readiness/2026-08-25-extraction-conditioned-on-dispatch.md (commit "
            "6c6ec719, receipt sha256 7662fbc381e6994f3c71422154a0facfc86c0e99b656cf9"
            "1670577036a337525). Nothing here is written off"
        ),
        "token_model": pricer.name,
        "lower_bound_disclosure": (
            "the list-like groups "
            + ", ".join(
                name for name in LIST_LIKE_UNDERPRICED_GROUPS if name in rows
            )
            + " are priced at the PROSE rate, which under-prices them, so the "
            "extraction share below is a LOWER bound"
            if any(name in rows for name in LIST_LIKE_UNDERPRICED_GROUPS)
            else "no list-like group on this carrier is priced below its own rate"
        ),
        "extraction_strict": strict,
        "extraction_broad": broad,
        "matching_oriented": matching,
        "form_oriented": form,
        "bands_sum_check": {
            "strict_plus_matching_plus_form_characters": (
                int(strict["characters"])
                + int(matching["characters"])
                + int(form["characters"])
            ),
            "supply_block_characters_total": total_chars,
            "closes": (
                int(strict["characters"])
                + int(matching["characters"])
                + int(form["characters"])
            )
            == total_chars,
        },
    }


# ---------------------------------------------------------------------------
# 6. The A2T form-channel candidate evidence
# ---------------------------------------------------------------------------


_PRIOR_HEADER = re.compile(r"^ (?:Entity-type|Argument-pattern) prior for [^:.]+?(?:: |\. )")


def prior_table_decomposition(
    *, account: SupplyAccount, segmented: SegmentedSnapshot, group: str
) -> dict[str, object]:
    """Split the PRIOR-TABLE group into its identifying HEADER and its numeric
    body, so the classification can be checked rather than asserted.

    The header names the intent/tool the table is keyed by, which is the only
    part of the group that repeats a matching cue. If the header is a small
    fraction of the group, the EXTRACTION classification stands on the numbers
    rather than on the label."""

    header_chars = 0
    body_chars = 0
    occurrences = 0
    # Counted over the ACTUAL supplied multiset, not over the snapshot.
    for value_id, count in account.supplied_multiset.items():
        seg = segmented.segmentations[value_id]
        for name, text in seg.segments:
            if name != group:
                continue
            occurrences += count
            match = _PRIOR_HEADER.match(text)
            if match is None:
                raise AccountingError(f"{value_id}: the prior table has no recognisable header")
            header_chars += len(match.group(0)) * count
            body_chars += (len(text) - len(match.group(0))) * count
    total = header_chars + body_chars
    return {
        "field_group": group,
        "occurrences": occurrences,
        "identifying_header_characters": header_chars,
        "numeric_body_characters": body_chars,
        "header_fraction_of_group": round(header_chars / total, 6) if total else None,
        "reading": (
            "the header is the only matching-redundant part of the group (it names "
            "the intent or tool the table is keyed by); everything else is the "
            "numeric distribution over slot types / argument keys"
        ),
    }


def form_channel_evidence(
    *, carrier: ccd.A2TAttempt4, segmented: SegmentedSnapshot
) -> dict[str, object]:
    """Which field groups the form-repaired trajectories actually received.

    MECHANISM READING AT SMALL n. Never an effect size."""

    dispatched = sorted(
        sample_id for sample_id in carrier.sample_ids if carrier.flown_dispatched[sample_id]
    )
    rows: dict[str, dict[str, object]] = {}
    for sample_id in dispatched:
        contact0 = agd._form_class(carrier.direct_texts[sample_id])
        final = agd._form_class(carrier.blend_final_texts[sample_id])
        supplied = tuple(carrier.flown_supply.get(sample_id, ()) or ())
        segs = [segmented.segmentations[value_id] for value_id in supplied]
        present = {}
        chars = {}
        nonplaceholder = {}
        for entry in FIELD_GROUPS["audio2tool"]:
            occurrences = sum(
                1 for seg in segs if any(name == entry.name for name, _ in seg.segments)
            )
            present[entry.name] = occurrences
            chars[entry.name] = sum(
                len(text) for seg in segs for name, text in seg.segments if name == entry.name
            )
            nonplaceholder[entry.name] = sum(
                1
                for seg in segs
                if any(name == entry.name for name, _ in seg.segments)
                and not is_placeholder("audio2tool", entry.name, seg.payloads.get(entry.name, ""))
            )
        rows[sample_id] = {
            "contact0_form": contact0,
            "blend_final_form": final,
            "form_repaired": contact0 in ("empty", "unparsed")
            and final == "well-formed-non-empty",
            "supplied_values": len(supplied),
            "supplied_value_ids": list(supplied),
            "supply_block_characters": sum(
                len(segmented.contents[value_id]) for value_id in supplied
            ),
            "field_group_occurrences": present,
            "field_group_characters": chars,
            "field_group_non_placeholder_occurrences": nonplaceholder,
        }

    contact0_classes: dict[str, int] = {}
    final_classes: dict[str, int] = {}
    for row in rows.values():
        contact0_classes[str(row["contact0_form"])] = (
            contact0_classes.get(str(row["contact0_form"]), 0) + 1
        )
        final_classes[str(row["blend_final_form"])] = (
            final_classes.get(str(row["blend_final_form"])) or 0
        ) + 1

    repaired = [s for s in dispatched if rows[s]["form_repaired"]]
    eligible = [
        s for s in dispatched if rows[s]["contact0_form"] in ("empty", "unparsed")
    ]
    not_repaired = [s for s in eligible if s not in repaired]

    def summarise(ids: Sequence[str]) -> dict[str, object]:
        if not ids:
            return {"n": 0}
        out: dict[str, object] = {"n": len(ids), "sample_ids": list(ids)}
        out["supplied_values"] = {
            "min": min(int(rows[s]["supplied_values"]) for s in ids),
            "mean": round(
                sum(int(rows[s]["supplied_values"]) for s in ids) / len(ids), 4
            ),
            "max": max(int(rows[s]["supplied_values"]) for s in ids),
        }
        out["supply_block_characters"] = {
            "min": min(int(rows[s]["supply_block_characters"]) for s in ids),
            "mean": round(
                sum(int(rows[s]["supply_block_characters"]) for s in ids) / len(ids), 2
            ),
            "max": max(int(rows[s]["supply_block_characters"]) for s in ids),
        }
        per_group = {}
        for entry in FIELD_GROUPS["audio2tool"]:
            occurrences = [int(rows[s]["field_group_occurrences"][entry.name]) for s in ids]
            values = [int(rows[s]["supplied_values"]) for s in ids]
            nonph = [
                int(rows[s]["field_group_non_placeholder_occurrences"][entry.name])
                for s in ids
            ]
            per_group[entry.name] = {
                "trajectories_receiving_it_at_least_once": sum(
                    1 for value in occurrences if value > 0
                ),
                "fraction_of_trajectories": round(
                    sum(1 for value in occurrences if value > 0) / len(ids), 4
                ),
                "occurrences_over_supplied_values": (
                    round(sum(occurrences) / sum(values), 4) if sum(values) else None
                ),
                "non_placeholder_occurrences_over_supplied_values": (
                    round(sum(nonph) / sum(values), 4) if sum(values) else None
                ),
                "mean_characters_per_trajectory": round(
                    sum(int(rows[s]["field_group_characters"][entry.name]) for s in ids)
                    / len(ids),
                    2,
                ),
            }
        out["per_field_group"] = per_group
        return out

    def supply_sets(ids: Sequence[str]) -> dict[str, object]:
        keys = [tuple(rows[s]["supplied_value_ids"]) for s in ids]  # type: ignore[arg-type]
        distinct = sorted({key for key in keys})
        return {
            "n": len(ids),
            "distinct_supply_sets": len(distinct),
            "distinct_supply_sets_list": [list(key) for key in distinct],
        }

    repaired_sets = {tuple(rows[s]["supplied_value_ids"]) for s in repaired}  # type: ignore[arg-type]
    not_repaired_sets = {
        tuple(rows[s]["supplied_value_ids"]) for s in not_repaired  # type: ignore[arg-type]
    }
    shared_sets = sorted(repaired_sets & not_repaired_sets)

    return {
        "caveat": SMALL_N_CAVEAT,
        "exposed_population_caveat": SECONDARY_EXPOSED_LABEL,
        "scope": (
            "DISPATCHED TRAJECTORIES ONLY (n=15). Retained trajectories received no "
            "evidence at all, so any arm-to-arm difference among them is decode "
            "variance -- measured at 10.11 percent divergent response text on the A2T "
            "retained set and 14.84 / 16.72 percent on the two SLURP retained sets by "
            "docs/readiness/2026-08-25-extraction-conditioned-on-dispatch.md section "
            "9. Nothing in this block touches a retained trajectory"
        ),
        "supply_set_identity": {
            "repaired": supply_sets(repaired),
            "not_repaired": supply_sets(not_repaired),
            "supply_sets_shared_by_BOTH_subgroups": [list(key) for key in shared_sets],
            "trajectories_in_a_shared_set": {
                "repaired": sorted(
                    s
                    for s in repaired
                    if tuple(rows[s]["supplied_value_ids"]) in set(shared_sets)  # type: ignore[arg-type]
                ),
                "not_repaired": sorted(
                    s
                    for s in not_repaired
                    if tuple(rows[s]["supplied_value_ids"]) in set(shared_sets)  # type: ignore[arg-type]
                ),
            },
            "reading": (
                "when a supply set appears in BOTH subgroups, the supply is held "
                "constant across the outcome, so no field of it can be what "
                "distinguishes the two -- the difference has to come from somewhere "
                "else"
            ),
        },
        "dispatched_n": len(dispatched),
        "contact0_form_classes": contact0_classes,
        "blend_final_form_classes": final_classes,
        "form_repaired_n": len(repaired),
        "form_repaired_sample_ids": repaired,
        "eligible_but_not_repaired_n": len(not_repaired),
        "eligible_but_not_repaired_sample_ids": not_repaired,
        "candidate_field_groups": list(FORM_CHANNEL_CANDIDATES),
        "repaired": summarise(repaired),
        "not_repaired": summarise(not_repaired),
        "per_trajectory": rows,
        "what_this_can_and_cannot_show": (
            "presence of a field group cannot discriminate two subgroups when the "
            "builder emits it on EVERY value. Where that is the case this block says "
            "so and reports the quantities that DO vary -- how many values were "
            "supplied, how many characters of each group arrived, and how often the "
            "group was a placeholder rather than real content"
        ),
    }


# ---------------------------------------------------------------------------
# 7. Orchestration
# ---------------------------------------------------------------------------


def _model_vs_measurement(
    rows: Sequence[Mapping[str, object]], pricers: Mapping[str, TokenPricer]
) -> dict[str, object]:
    """Estimated supply-block tokens against the MEASURED prompt-token delta,
    on exactly the contacts where both exist."""

    measured = sum(int(row["prompt_token_delta"]) for row in rows)  # type: ignore[arg-type]
    out: dict[str, object] = {
        "paired_contacts": len(rows),
        "measured_total_prompt_token_delta": measured,
        "note": (
            "the measured delta also contains the fixed control instruction, so a "
            "small positive gap between measurement and estimate is expected"
        ),
    }
    for key in ("uniform", "two_rate"):
        pricer = pricers[key]
        estimated = sum(
            pricer.tokens(name, int(count))
            for row in rows
            for name, count in row["characters_by_group"].items()  # type: ignore[union-attr]
        )
        out[key] = {
            "estimated_supply_block_tokens_total": round(estimated, 1),
            "difference_tokens": round(measured - estimated, 1),
            "relative_difference": (
                round((measured - estimated) / measured, 6) if measured else None
            ),
        }
    return out


def _delta_summary(rows: Sequence[Mapping[str, object]]) -> dict[str, object]:
    deltas = sorted(int(row["prompt_token_delta"]) for row in rows)  # type: ignore[arg-type]
    if not deltas:
        return {"n": 0}
    return {
        "n": len(deltas),
        "min": deltas[0],
        "median": deltas[len(deltas) // 2],
        "mean": round(sum(deltas) / len(deltas), 2),
        "max": deltas[-1],
        "total": sum(deltas),
    }


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


DEV1000_ALL_PIN = cf.CellPin(
    population_id="DEV-1000",
    run_id=k1.DEV1000_PIN.run_id,
    attempt_id=k1.DEV1000_PIN.attempt_id,
    outputs_basename=k1.DEV1000_PIN.outputs_basename,
    arm_key=k1.DEV1000_PIN.arm_key,
    report_relpath=k1.DEV1000_PIN.report_relpath,
    report_arm_key=k1.DEV1000_PIN.report_arm_key,
    restrict_to=None,
)


def run(*, repo_root: Path, data_root: Path) -> dict[str, object]:
    guard = ra.arm_offline_guard()
    started = datetime.now(timezone.utc)

    repo_root = Path(repo_root)
    data_root = Path(data_root)

    # ---- Audio2Tool -----------------------------------------------------
    a2t_carrier = ccd.load_a2t_attempt4(data_root=data_root, repo_root=repo_root)
    a2t_segmented = segment_snapshot(a2t_carrier.bundle, "audio2tool")

    # ---- SLURP ----------------------------------------------------------
    slurp_bundle = cf.load_snapshot_bundle(data_root=data_root, repo_root=repo_root)
    slurp_segmented = segment_snapshot(slurp_bundle, "slurp")
    dev1000_hashes = k1.assert_dev1000_byte_pins(repo_root=repo_root, data_root=data_root)
    populations = d5.load_populations(repo_root)
    shim = k1.load_populations(repo_root)
    cell = cf.load_cell_population(
        pin=DEV1000_ALL_PIN,
        bundle=slurp_bundle,
        populations=populations,
        data_root=data_root,
        repo_root=repo_root,
    )
    if len(cell.sample_ids) != 1000:
        raise AccountingError(
            f"the DEV-1000 BLEND arm covers {len(cell.sample_ids)} samples, not 1000"
        )
    new500 = set(shim.new500)
    dev500 = set(shim.dev500)
    if new500 | dev500 != set(cell.sample_ids) or new500 & dev500:
        raise AccountingError("the DEV-1000 halves do not partition the flown arm")

    # ---- token models ---------------------------------------------------
    slurp_rate = slurp_paired_token_rate(cell, slurp_segmented)
    a2t_rate = a2t_paired_token_rate(
        carrier=a2t_carrier, data_root=data_root, segmented=a2t_segmented
    )
    a2t_receipt_calibration = sweep.token_calibration(
        repo_root=repo_root, data_root=data_root
    )
    control_digest = hashlib.sha256(CONTROL_INSTRUCTION.encode("utf-8")).hexdigest()
    if control_digest != CONTROL_INSTRUCTION_SHA256:
        raise AccountingError(
            "the control instruction this module prices does not hash to the digest "
            "the sealed MODEL_REQUEST payloads carry"
        )

    # ---- accounts -------------------------------------------------------
    a2t_account = build_account(
        carrier="audio2tool",
        population="A2T-G1-104 (EXPOSED)",
        supply=a2t_carrier.flown_supply,
        sample_ids=a2t_carrier.sample_ids,
        segmented=a2t_segmented,
    )
    slurp_accounts = {
        "DEV-1000-NEW500 (UNEXPOSED)": build_account(
            carrier="slurp",
            population="DEV-1000-NEW500 (UNEXPOSED)",
            supply=cell.inputs.logged_supply,
            sample_ids=tuple(sorted(new500)),
            segmented=slurp_segmented,
        ),
        "DEV-500 (PRIOR-EXPOSED)": build_account(
            carrier="slurp",
            population="DEV-500 (PRIOR-EXPOSED)",
            supply=cell.inputs.logged_supply,
            sample_ids=tuple(sorted(dev500)),
            segmented=slurp_segmented,
        ),
        "DEV-1000 (BOTH HALVES)": build_account(
            carrier="slurp",
            population="DEV-1000 (BOTH HALVES)",
            supply=cell.inputs.logged_supply,
            sample_ids=cell.sample_ids,
            segmented=slurp_segmented,
        ),
    }

    slurp_pricers = build_pricers(
        carrier="slurp",
        paired_rows=slurp_rate["rows"],  # type: ignore[arg-type]
        single_rate=slurp_rate,
    )
    a2t_pricers = build_pricers(
        carrier="audio2tool",
        paired_rows=a2t_rate["rows"],  # type: ignore[arg-type]
        single_rate=a2t_rate,
    )

    def _label(name: str) -> str:
        if "NEW500" in name:
            return SECONDARY_UNEXPOSED_LABEL
        if "BOTH" in name:
            return SECONDARY_UNEXPOSED_LABEL + " (this row pools the locked half)"
        return SECONDARY_EXPOSED_LABEL

    a2t_table = {
        key: account_table(
            a2t_account, pricer=a2t_pricers[key], label=SECONDARY_EXPOSED_LABEL
        )
        for key in ("uniform", "two_rate")
    }
    slurp_tables = {
        name: {
            key: account_table(account, pricer=slurp_pricers[key], label=_label(name))
            for key in ("uniform", "two_rate")
        }
        for name, account in slurp_accounts.items()
    }

    a2t_dead = {
        key: channel_cost(
            a2t_table[key],
            "audio2tool",
            pricer=a2t_pricers[key],
            population_size=a2t_account.population_size,
        )
        for key in ("uniform", "two_rate")
    }
    slurp_dead = {
        name: {
            key: channel_cost(
                tables[key],
                "slurp",
                pricer=slurp_pricers[key],
                population_size=slurp_accounts[name].population_size,
            )
            for key in ("uniform", "two_rate")
        }
        for name, tables in slurp_tables.items()
    }
    prior_decomposition = {
        "audio2tool": {
            "A2T-G1-104 (EXPOSED)": prior_table_decomposition(
                account=a2t_account, segmented=a2t_segmented, group="A2T-PRIOR-TABLE"
            )
        },
        "slurp": {
            name: prior_table_decomposition(
                account=account, segmented=slurp_segmented, group="SLURP-PRIOR-TABLE"
            )
            for name, account in slurp_accounts.items()
        },
    }

    def _header_sensitivity(
        *, decomposition, tables, costs, pricer_by_key, group: str
    ) -> dict[str, object]:
        out: dict[str, object] = {
            "question": (
                "the PRIOR-TABLE group opens with an identifying header naming the "
                "intent or tool it is keyed by. That header repeats a matching cue "
                "already carried by other groups, so it is framing overhead of an "
                "extraction field rather than new matching content. This block "
                "reports what the extraction share becomes if the header is "
                "reassigned away from EXTRACTION anyway -- the conservative bound"
            )
        }
        for key in ("uniform", "two_rate"):
            pricer = pricer_by_key[key]
            header_tokens = pricer.tokens(group, int(decomposition["identifying_header_characters"]))
            strict = costs[key]["extraction_strict"]
            total_tokens = float(tables[key]["supply_block_estimated_tokens_total"])
            reduced = float(strict["estimated_tokens_total"]) - header_tokens
            out[key] = {
                "prior_table_header_characters": decomposition["identifying_header_characters"],
                "prior_table_header_fraction_of_group": decomposition[
                    "header_fraction_of_group"
                ],
                "prior_table_header_estimated_tokens": round(header_tokens, 1),
                "extraction_strict_token_fraction_as_reported": strict[
                    "token_fraction_of_supply_block"
                ],
                "extraction_strict_token_fraction_without_the_header": (
                    round(reduced / total_tokens, 6) if total_tokens else None
                ),
            }
        return out

    header_sensitivity = {
        "audio2tool": _header_sensitivity(
            decomposition=prior_decomposition["audio2tool"]["A2T-G1-104 (EXPOSED)"],
            tables=a2t_table,
            costs=a2t_dead,
            pricer_by_key=a2t_pricers,
            group="A2T-PRIOR-TABLE",
        ),
        "slurp": {
            name: _header_sensitivity(
                decomposition=prior_decomposition["slurp"][name],
                tables=slurp_tables[name],
                costs=slurp_dead[name],
                pricer_by_key=slurp_pricers,
                group="SLURP-PRIOR-TABLE",
            )
            for name in slurp_tables
        },
    }
    measured_supply_tokens = {
        "semantics": (
            "MEASURED, not estimated: prompt_tokens(evidence-decode) - "
            "prompt_tokens(direct-decode) from the sealed COST channel, i.e. the "
            "control instruction plus the whole injected supply block through the "
            "real tokenizer"
        ),
        "slurp": _delta_summary(slurp_rate["rows"]),  # type: ignore[arg-type]
        "audio2tool": _delta_summary(a2t_rate["rows"]),  # type: ignore[arg-type]
        "estimate_versus_measurement": {
            "slurp": _model_vs_measurement(slurp_rate["rows"], slurp_pricers),  # type: ignore[arg-type]
            "audio2tool": _model_vs_measurement(a2t_rate["rows"], a2t_pricers),  # type: ignore[arg-type]
        },
    }

    # ---- dispatch cross-checks -----------------------------------------
    slurp_dispatched = sum(
        1 for sample_id in cell.sample_ids if cell.logged_contacts[sample_id] == 2
    )
    slurp_with_supply = sum(
        1
        for sample_id in cell.sample_ids
        if cell.inputs.logged_supply.get(sample_id)
    )
    report = cell.committed_report or {}
    committed_dispatched = int(
        report.get("mechanical", {}).get("two_contact_trajectories_dispatched", -1)
    )
    dispatch_gate = {
        "slurp_two_contact_trajectories": slurp_dispatched,
        "slurp_trajectories_with_non_empty_supply": slurp_with_supply,
        "slurp_committed_report_dispatched": committed_dispatched,
        "a2t_dispatched": sum(
            1 for s in a2t_carrier.sample_ids if a2t_carrier.flown_dispatched[s]
        ),
        "a2t_trajectories_with_non_empty_supply": sum(
            1 for s in a2t_carrier.sample_ids if a2t_carrier.flown_supply.get(s)
        ),
        "passed": (
            slurp_dispatched == slurp_with_supply == committed_dispatched
            and sum(1 for s in a2t_carrier.sample_ids if a2t_carrier.flown_dispatched[s])
            == sum(1 for s in a2t_carrier.sample_ids if a2t_carrier.flown_supply.get(s))
        ),
    }
    if not dispatch_gate["passed"]:
        raise AccountingError(f"the dispatch cross-check failed: {dispatch_gate}")

    form = form_channel_evidence(carrier=a2t_carrier, segmented=a2t_segmented)

    artifact_hashes = {
        "a2t_snapshot": a2t_carrier.bundle.snapshot_sha256,
        "slurp_snapshot": slurp_bundle.snapshot_sha256,
        **{f"a2t:{k}": v for k, v in a2t_carrier.artifact_hashes.items()},
        **{f"slurp:{k}": v for k, v in cell.artifact_hashes.items()},
        **{f"slurp-pin:{k}": v for k, v in dev1000_hashes.items()},
        "rails/knowledge_build.py": _sha256_file(
            repo_root / "src/speech_aware_evidence_acquisition/rails/knowledge_build.py"
        ),
        "rails/knowledge_build_a2t.py": _sha256_file(
            repo_root
            / "src/speech_aware_evidence_acquisition/rails/knowledge_build_a2t.py"
        ),
        "rails/runner.py": _sha256_file(
            repo_root / "src/speech_aware_evidence_acquisition/rails/runner.py"
        ),
    }

    finished = datetime.now(timezone.utc)
    return {
        "schema": SCHEMA,
        "exposure_row_id": EXPOSURE_ROW_ID,
        "ledger_commit": LEDGER_COMMIT,
        "generated_at": finished.isoformat(),
        "wall_seconds": round((finished - started).total_seconds(), 3),
        "accounting_only": ACCOUNTING_ONLY,
        "spend": {
            "frozen_core_contacts": 0,
            "embedding_tool_contacts": 0,
            "tokenizer_contacts": 0,
            "http_or_socket_requests": 0,
            "audio_seconds": 0,
            "gpu_hours": 0.0,
            "new_dependencies": 0,
            "outbound_connection_attempts": guard.count,
            "outbound_connection_targets": list(guard.targets),
        },
        "field_enumeration": {
            carrier: [
                {
                    "field_group": entry.name,
                    "builder_line": entry.builder_line,
                    "what_it_carries": entry.what_it_carries,
                    "orientation": entry.orientation,
                    "orientation_justification": entry.orientation_justification,
                    "placeholder_literal": entry.placeholder,
                    "optional": entry.optional,
                }
                for entry in groups
            ]
            for carrier, groups in FIELD_GROUPS.items()
        },
        "parse_fidelity_gate": {
            "audio2tool": a2t_segmented.gate,
            "slurp": slurp_segmented.gate,
        },
        "dispatch_cross_check": dispatch_gate,
        "token_model": {
            "why_no_tokenizer": (
                "the campaign's prompt-fit receipts were measured through the "
                "resident llama-server /props + /apply-template + /tokenize routes, "
                "which is an HTTP contact this row may not take. No offline copy of "
                "that tokenizer exists in this repository, so the campaign's own "
                "established OFFLINE estimators are used and named"
            ),
            "slurp_paired_regression": {
                key: value for key, value in slurp_rate.items() if key != "rows"
            },
            "audio2tool_paired_regression": {
                key: value for key, value in a2t_rate.items() if key != "rows"
            },
            "slurp_models": {
                "uniform": slurp_pricers["uniform"].report,
                "two_rate": slurp_pricers["two_rate"].report,
                "per_group_REFUSED": slurp_pricers["_refused_per_group"],
            },
            "audio2tool_models": {
                "uniform": a2t_pricers["uniform"].report,
                "two_rate": a2t_pricers["two_rate"].report,
                "per_group_REFUSED": a2t_pricers["_refused_per_group"],
            },
            "audio2tool_receipt_calibration_cross_check": a2t_receipt_calibration,
            "control_instruction": {
                "text": CONTROL_INSTRUCTION,
                "sha256": control_digest,
                "characters": len(CONTROL_INSTRUCTION),
                "slurp_estimated_tokens_from_regression_intercept": slurp_rate[
                    "constant_instruction_cost_tokens"
                ],
                "a2t_estimated_tokens_from_regression_intercept": a2t_rate[
                    "constant_instruction_cost_tokens"
                ],
            },
            "linearity_disclosure": (
                "the UNIFORM model is linear in characters, so under it a field "
                "group's TOKEN share equals its CHARACTER share exactly. The "
                "DENSE/PROSE model separates the two and is the better fit; both are "
                "published and every headline is given under both"
            ),
            "known_density_caveat": (
                "dev100_supply_budget_projection.token_model records that the dense "
                "numeric prior tables tokenize at about 1.93 characters per token "
                "against roughly twice that for exemplar prose. That is why the "
                "DENSE/PROSE model exists; the regression here confirms it "
                "independently. Every remaining list-like extraction group is still "
                "priced at the prose rate, so every extraction figure is a LOWER "
                "bound"
            ),
        },
        "token_tables": {
            "audio2tool": a2t_table,
            "slurp": slurp_tables,
        },
        "measured_supply_block_tokens": measured_supply_tokens,
        "prior_table_decomposition": prior_decomposition,
        "prior_table_header_sensitivity": header_sensitivity,
        "channel_cost": {
            "audio2tool": a2t_dead,
            "slurp": slurp_dead,
        },
        "form_channel_evidence": form,
        "superseded_premise_correction": SUPERSEDED_PREMISE_CORRECTION,
        "artifact_hashes": artifact_hashes,
        "governance": {
            "slurp_unexposed_500": SECONDARY_UNEXPOSED_LABEL,
            "exposed_populations": SECONDARY_EXPOSED_LABEL,
            "small_n": SMALL_N_CAVEAT,
            "accounting_only": ACCOUNTING_ONLY,
        },
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    report = run(repo_root=Path(args.repo_root), data_root=Path(args.data_root))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {out} sha256={_sha256_file(out)}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
