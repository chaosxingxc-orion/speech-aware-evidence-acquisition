"""Candidate artifacts for the system-evolution loop (E3a).

The loop is preregistered in ``docs/readiness/2026-09-05-three-dimension-
experiment-program.md`` section 5. This module owns ONE half of it: what a
single candidate description-override set IS, how the frozen core is asked to
propose one, how its answer is parsed, and every form/decontamination gate a
candidate must clear before it is allowed anywhere near a flight.
``rails.evolution`` owns the other half (targets, portfolios, selection,
confirmation, rounds, budget).

The state the loop evolves is deliberately small: ``A_r`` is a mapping from a
TARGETED tool name to a replacement ``description`` string, and nothing else.
``A_0`` is the empty mapping -- i.e. the released compact registry, byte for
byte. Rendering is always ``data.audio2tool_tools.render_registry_compact
(description_overrides=...)``: the same 152 lines, the same ``"- {signature}:
{description}"`` shape, the same plain ``tool_name`` sort. A candidate can
therefore change only what a description SAYS, never how the registry is
organized, how long it is, or which tools it contains -- which is what makes
"the description content" a single, attributable factor.

Three candidate families, all the same dataclass:

* ``proposer`` -- the frozen core's own rewrite, produced on the text-only
  construction-proposer arm (track E2's) from the pair's registry rows, M
  block-disjoint construction exemplars per tool with their gold calls, and
  the incumbent descriptions. It also returns the CUE it used to separate the
  tools, which is recorded for the reviewer and never rendered.
* ``deterministic`` -- the control: append the registry's own ``domain`` and
  ``category`` to each incumbent description. Zero model contact, so a round
  whose proposer never beats it has learned nothing the registry did not
  already carry.
* ``placebo`` -- a length-matched rewrite the proposer is explicitly told to
  write WITHOUT a distinguishing cue (``render_placebo_instruction``). If the
  placebo is indistinguishable from the proposer candidate, the gain was
  form, not content; that is one of the preregistered kill results.

Decontamination is a gate, not a footnote. A candidate description is
refused if it is non-ASCII, longer than 200 characters, carries a sample
identifier, or shares a word 6-gram with any evaluation-roster query text
unless that 6-gram already occurs in the released registry itself. Overlap
with the CONSTRUCTION exemplars the proposer was shown is measured and
reported rather than gated: construction rows are legally visible to the
proposer, so overlap there is a memorization signal for the reviewer, not an
illegality.

Two ARTIFACT families, one candidate dataclass. The three families above
say how a candidate was PRODUCED; :data:`ARTIFACT_FAMILIES` says what its
content IS. ``a2t-descriptions`` is the mapping described above.
``slurp-slot-schema`` (EVO-S1) is a mapping from a SLURP intent to that
intent's slot block -- an ordered entity-type list with up to five TRAIN
fillers each -- rendered through ``data.slurp
.render_slurp_intent_slot_schema`` with the header line and every share
re-derived from the unfloored TRAIN table, so a candidate can choose which
types to list, in what order, and with which fillers, and can never write a
number. Everything family-specific lives behind a family switch in this one
module: there is no second candidate class, no second validator module and
no probe.

No class here defines both ``initial_contact`` and ``advance``, and nothing
here subclasses ``rails.task_adapter.TaskAdapter``: this module is data and
gates, and the one controller stays ``rails.controllers.EvidenceAgentController``.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Callable, Mapping, Sequence

from ..data.audio2tool_tools import render_registry_compact_rows
from .hashing import canonical_json_bytes, content_hash

CANDIDATE_SCHEMA = "saea-evolution-candidate-v1"
VALIDATION_SCHEMA = "saea-evolution-candidate-validation-v1"

#: Form caps, verbatim from the program document's section 5.
MAX_DESCRIPTION_CHARS = 200
TOKEN_HEADROOM = 40
REGISTRY_LINE_COUNT = 152

#: Decontamination n-gram width (program section 5: "no shared word 6-gram").
DECONTAMINATION_NGRAM = 6

#: Schema of the committed EVO-S1 decontamination artifact
#: (``docs/receipts/knowledge/slurp-evo-decontamination-v1.json``, exposure row
#: ``SAEA-SLURP-MF-EVO-DECONTAMINATION-V1``). The artifact carries the SHA-256
#: DIGEST of every DEV-1000 sentence 6-gram and never the 6-gram itself: the
#: gate has to be reproducible from committed bytes, and a committed file of
#: literal 6-grams would be six-word windows of devel sentences written into
#: the repository, which is exactly what coordinator decision 5 of 2026-09-06
#: forbids. Digests compare identically and reconstitute nothing.
SLURP_DECONTAMINATION_SCHEMA = "saea-slurp-evo-decontamination-v1"

#: The appended-note family's fixed shape (KC-A1): every note opens with this
#: separator, and a category-only control is padded to the note's length with
#: this neutral filler word before any trailing space.
NOTE_PREFIX = "; "
CONTROL_FILLER = " tool"

FAMILIES = ("proposer", "deterministic", "placebo")

#: What a candidate's CONTENT is, as opposed to how it was produced.
#: ``a2t-descriptions`` -- ``{tool_name: description}``, EVO-A1's state.
#: ``slurp-slot-schema`` -- ``{intent: {"types": [{"entity_type": str,
#: "fillers": [str, ...]}, ...]}}``, EVO-S1's state.
A2T_DESCRIPTIONS_FAMILY = "a2t-descriptions"
SLURP_SLOT_SCHEMA_FAMILY = "slurp-slot-schema"
ARTIFACT_FAMILIES = (A2T_DESCRIPTIONS_FAMILY, SLURP_SLOT_SCHEMA_FAMILY)

#: EVO-S1 form constants (preregistration sections 3 and 5).
#: The token budget is RELATIVE -- ``+20 %`` over the INCUMBENT block, per
#: intent -- because a SLURP block is 494 to 1,224 characters and an absolute
#: cap would price a nine-intent scenario like a one-intent one.
SLURP_RELATIVE_TOKEN_BUDGET = 0.20
SLURP_MAX_FILLERS_PER_TYPE = 5

#: The exact text ``data.slurp.render_slurp_intent_slot_schema`` emits for a
#: listed type carrying no filler. It is a real renderer output (that is what
#: the shares-only control F2 renders to), so the block parser accepts it and
#: reads it back as an empty filler list.
SLURP_NO_FILLER_SENTINEL = "no example filler recorded"

#: The neutral placeholders the token-matched form twin (F3) writes in place
#: of a type's fillers, one per filler POSITION, and the unit it pads with
#: (the first entry). One word per position rather than one word repeated,
#: because the renderer's own grammar and the block parser both refuse a type
#: that lists the same filler twice -- so a twin built from a single repeated
#: word would not be a legal block at all. Five entries because a type carries
#: at most :data:`SLURP_MAX_FILLERS_PER_TYPE` fillers.
SLURP_PLACEHOLDER_FILLERS = ("item", "thing", "one", "part", "unit")
SLURP_PLACEHOLDER_FILLER = SLURP_PLACEHOLDER_FILLERS[0]

#: The only token counter a REGISTERED EVO-S1 candidate may be priced with:
#: the serving geometry's own tokenizer, reached over the resident server's
#: ``/tokenize``. KC-A1 died four tokens over a forty-token cap because its
#: builder injected a chars-per-token ratio as its counter, so an estimator is
#: refused here unless the caller says ``allow_estimator=True`` -- which the
#: offline tests do and a flight never may.
SERVING_TOKENIZER_ID = "llama-server:/tokenize"

#: The registry columns every proposer prompt and every gate reads.
ROW_FIELDS = (
    "tool_name",
    "signature",
    "description",
    "domain",
    "category",
    "argument_constraints",
    "argument_defaults",
)

__all__ = [
    "CANDIDATE_SCHEMA",
    "VALIDATION_SCHEMA",
    "NOTE_PREFIX",
    "CONTROL_FILLER",
    "MAX_DESCRIPTION_CHARS",
    "TOKEN_HEADROOM",
    "REGISTRY_LINE_COUNT",
    "DECONTAMINATION_NGRAM",
    "SLURP_DECONTAMINATION_SCHEMA",
    "FAMILIES",
    "ARTIFACT_FAMILIES",
    "A2T_DESCRIPTIONS_FAMILY",
    "SLURP_SLOT_SCHEMA_FAMILY",
    "SLURP_RELATIVE_TOKEN_BUDGET",
    "NULL_REWRITE_GATE",
    "NULL_REWRITE_SCHEMA",
    "SLURP_MAX_FILLERS_PER_TYPE",
    "SLURP_NO_FILLER_SENTINEL",
    "SLURP_PLACEHOLDER_FILLER",
    "SLURP_PLACEHOLDER_FILLERS",
    "SERVING_TOKENIZER_ID",
    "PROPOSER_INSTRUCTION_VERSIONS",
    "ROW_FIELDS",
    "ProposerError",
    "CandidateArtifact",
    "CandidateValidation",
    "NullRewriteCheck",
    "candidate_bytes",
    "candidate_id_for",
    "candidate_text",
    "contrast_note_records",
    "derive_target_id",
    "deterministic_candidate",
    "parse_proposer_response",
    "prompt_sha256",
    "proposer_instruction_version",
    "placebo_candidate",
    "proposer_candidate",
    "render_placebo_instruction",
    "render_proposer_instruction",
    "validate_candidate_artifact",
    "rendered_artifact_sha256",
    "null_rewrite_check",
    "word_ngrams",
    "ngram_digest",
    "ngram_digests",
    "load_evaluation_ngram_digests",
    # -- the SLURP slot-schema artifact family (EVO-S1) -----------------
    "parse_slurp_schema_response",
    "render_slurp_proposer_instruction",
    "slurp_proposer_candidate",
    "slurp_shares_only_candidate",
    "slurp_form_twin_candidate",
    "slurp_candidate_schema",
    "slurp_block_texts",
    "slurp_blocks_from_schema",
    "validate_slurp_candidate_artifact",
]


class ProposerError(ValueError):
    """A candidate, a proposer prompt, or a proposer response is malformed."""


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

_WORD_RE = re.compile(r"[a-z0-9]+")

#: ``tier3_multi_intent:000412`` -- the Audio2Tool sample identity shape --
#: and any bare six-digit run of digits, which is the query index that shape
#: ends in. Either inside a description would mean an evaluation identifier
#: was copied into the prompt.
_SAMPLE_ID_RE = re.compile(r"tier\d_[a-z_]+:\d{6}")
_BARE_SIX_DIGIT_RE = re.compile(r"(?<!\d)\d{6}(?!\d)")

#: ``slurp:devel:001234`` / ``slurp:train:001234:headset`` -- the SLURP
#: sample identity shape (preregistration section 12.1 item P4). Added beside
#: the Audio2Tool shape rather than instead of it: an identifier is an
#: identifier whichever carrier minted it, and both families refuse both.
_SLURP_SAMPLE_ID_RE = re.compile(r"slurp:(?:train|devel|test):\d{6}(?::[A-Za-z0-9-]+)?")

#: Intent and entity-type names, which SLURP spells the same way
#: (``alarm_query``, ``definition_word``) and which the block grammar's two
#: line shapes both key on.
_SLURP_NAME_RE = re.compile(r"[a-z0-9_]+")

#: The two line shapes ``data.slurp.render_slurp_intent_slot_schema`` emits
#: for a block (preregistration section 12.1 item P2): the header line, which
#: carries the intent and its TRAIN counts, and one type line per listed type.
_SLURP_BLOCK_HEADER_RE = re.compile(
    r"^== (?P<intent>[a-z0-9_]+) == (?P<n>\d+) TRAIN utterances, "
    r"(?P<mentions>\d+) slot mentions$"
)
_SLURP_TYPE_LINE_RE = re.compile(
    r"^- (?P<entity_type>[a-z0-9_]+) \((?P<share>\d+\.\d) percent of slot "
    r"mentions\): (?P<fillers>\S.*)$"
)


def _carries_sample_identifier(text: str) -> bool:
    """Whether ``text`` carries anything shaped like a corpus sample id.

    One helper for both artifact families, so "no identifier reaches a
    candidate" means exactly the same thing on either carrier: an Audio2Tool
    ``tier3_multi_intent:000412``, a SLURP ``slurp:devel:001234``, or the
    bare six-digit run of digits both shapes end in.
    """

    return bool(
        _SAMPLE_ID_RE.search(text)
        or _SLURP_SAMPLE_ID_RE.search(text)
        or _BARE_SIX_DIGIT_RE.search(text)
    )


def word_ngrams(text: str, n: int = DECONTAMINATION_NGRAM) -> set[tuple[str, ...]]:
    """Lower-cased alphanumeric word ``n``-grams of ``text``.

    One tokenizer for every decontamination comparison in the loop, so
    "shared 6-gram" means exactly the same thing on the candidate side, the
    evaluation-query side and the registry side. Punctuation and case are
    dropped (a rewritten description will not reproduce an evaluation query's
    punctuation, and requiring it to would make the gate trivially passable).
    """

    if not isinstance(text, str):
        raise ProposerError("word_ngrams needs text")
    if isinstance(n, bool) or not isinstance(n, int) or n <= 0:
        raise ProposerError("n must be a positive integer")
    words = _WORD_RE.findall(text.lower())
    if len(words) < n:
        return set()
    return {tuple(words[index : index + n]) for index in range(len(words) - n + 1)}


def ngram_digest(gram: Sequence[str]) -> str:
    """The SHA-256 hex digest of one word n-gram, joined by single spaces.

    The whole point of the digest is that it travels where the words may not.
    A committed decontamination artifact carries these and never the words
    (:data:`SLURP_DECONTAMINATION_SCHEMA`), so the gate is reproducible from
    committed bytes without those bytes being devel sentence text; and a
    refusal names digests, so a log line cannot echo the six words a filler
    and a devel sentence happen to share.
    """

    if isinstance(gram, (str, bytes)) or not isinstance(gram, Sequence) or not gram:
        raise ProposerError("ngram_digest needs a non-empty sequence of words")
    words = []
    for word in gram:
        if not isinstance(word, str) or not word:
            raise ProposerError("every n-gram word must be non-empty text")
        words.append(word)
    return hashlib.sha256(" ".join(words).encode("utf-8")).hexdigest()


def ngram_digests(texts: Sequence[str], n: int = DECONTAMINATION_NGRAM) -> set[str]:
    """Every word ``n``-gram of ``texts``, as digests.

    :func:`word_ngrams` is the one tokenizer for every decontamination
    comparison in the loop, so this is exactly that set hashed -- never a
    second notion of what a shared 6-gram is.
    """

    if isinstance(texts, (str, bytes)):
        raise ProposerError("ngram_digests needs a sequence of texts")
    digests: set[str] = set()
    for item in texts:
        if not isinstance(item, str):
            raise ProposerError("every text entry must be a string")
        digests |= {ngram_digest(gram) for gram in word_ngrams(item, n)}
    return digests


def load_evaluation_ngram_digests(document: Mapping[str, object]) -> frozenset[str]:
    """The evaluation 6-gram digest set of a committed decontamination
    artifact, verified fail-closed.

    Checks the schema, the n-gram width, the declared count and the content
    hash of the digest list itself, so a validator can never be handed a
    silently truncated or hand-edited gate. The artifact is built by
    ``scripts/build_slurp_evo_decontamination.py`` under exposure row
    ``SAEA-SLURP-MF-EVO-DECONTAMINATION-V1``.
    """

    if not isinstance(document, Mapping) or not document:
        raise ProposerError("decontamination artifact must be a non-empty mapping")
    if document.get("schema") != SLURP_DECONTAMINATION_SCHEMA:
        raise ProposerError(
            f"decontamination artifact schema must be "
            f"{SLURP_DECONTAMINATION_SCHEMA!r}, got {document.get('schema')!r}"
        )
    if document.get("ngram") != DECONTAMINATION_NGRAM:
        raise ProposerError(
            f"decontamination artifact is built at n={document.get('ngram')!r}; this "
            f"gate compares {DECONTAMINATION_NGRAM}-grams"
        )
    raw = document.get("evaluation_ngram_digests")
    if isinstance(raw, (str, bytes)) or not isinstance(raw, Sequence) or not raw:
        raise ProposerError(
            "decontamination artifact carries no evaluation_ngram_digests"
        )
    digests: list[str] = []
    for entry in raw:
        if not isinstance(entry, str) or not re.fullmatch(r"[0-9a-f]{64}", entry):
            raise ProposerError(
                "every evaluation_ngram_digests entry must be a sha256 hex digest"
            )
        digests.append(entry)
    if sorted(digests) != digests:
        raise ProposerError("evaluation_ngram_digests must be sorted")
    if len(set(digests)) != len(digests):
        raise ProposerError("evaluation_ngram_digests repeats a digest")
    declared_count = document.get("evaluation_ngram_count")
    if declared_count is not None and int(declared_count) != len(digests):
        raise ProposerError(
            f"decontamination artifact declares {declared_count} digests and carries "
            f"{len(digests)}"
        )
    declared_hash = document.get("evaluation_ngram_digests_content_hash")
    if declared_hash is not None:
        measured = content_hash(digests)
        if measured != declared_hash:
            raise ProposerError(
                f"decontamination artifact digest list hashes to {measured}, not the "
                f"{declared_hash} it declares"
            )
    return frozenset(digests)


def _rows_by_name(rows: Sequence[Mapping[str, str]]) -> dict[str, Mapping[str, str]]:
    if isinstance(rows, (str, bytes)) or not rows:
        raise ProposerError("registry_rows must be a non-empty sequence of rows")
    by_name: dict[str, Mapping[str, str]] = {}
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise ProposerError(f"registry row {index} is not a mapping")
        missing = [field for field in ROW_FIELDS if field not in row]
        if missing:
            raise ProposerError(f"registry row {index} is missing {missing}")
        name = row["tool_name"]
        if not isinstance(name, str) or not name:
            raise ProposerError(f"registry row {index} has no usable tool_name")
        if name in by_name:
            raise ProposerError(f"registry rows repeat tool_name {name!r}")
        by_name[name] = row
    return by_name


def _checked_descriptions(
    descriptions: Mapping[str, str], label: str
) -> dict[str, str]:
    if not isinstance(descriptions, Mapping) or not descriptions:
        raise ProposerError(f"{label} must be a non-empty mapping")
    out: dict[str, str] = {}
    for tool, text in descriptions.items():
        if not isinstance(tool, str) or not tool:
            raise ProposerError(f"{label} has a non-text tool name")
        if not isinstance(text, str) or not text.strip():
            raise ProposerError(f"{label}[{tool!r}] must be non-empty text")
        out[tool] = text
    return out


def _checked_slurp_blocks(
    blocks: Mapping[str, object], label: str
) -> dict[str, dict[str, object]]:
    """Shape check for a ``slurp-slot-schema`` artifact. Structure only.

    ``{intent: {"types": [{"entity_type": str, "fillers": [str, ...]}, ...]}}``
    -- no counts, no shares, no header line, because a candidate never writes
    a number: :func:`slurp_candidate_schema` re-derives all of those from the
    unfloored TRAIN table before anything is rendered. The FORM gates (the
    line cap, the filler cap, the relative token budget, the TRAIN-mention
    rule) are :func:`validate_slurp_candidate_artifact`'s, one seam out, where
    the TRAIN table and the tokenizer are in scope.
    """

    if not isinstance(blocks, Mapping) or not blocks:
        raise ProposerError(f"{label} must be a non-empty mapping of intent to block")
    out: dict[str, dict[str, object]] = {}
    for intent, block in blocks.items():
        if not isinstance(intent, str) or not intent:
            raise ProposerError(f"{label} has a non-text intent name")
        if not isinstance(block, Mapping) or set(block) != {"types"}:
            raise ProposerError(
                f"{label}[{intent!r}] must be an object carrying exactly 'types'"
            )
        raw_types = block["types"]
        if isinstance(raw_types, (str, bytes)) or not isinstance(raw_types, Sequence):
            raise ProposerError(f"{label}[{intent!r}].types must be a list")
        if not raw_types:
            raise ProposerError(
                f"{label}[{intent!r}] lists no entity type; a candidate may reorder or "
                "re-fill a block, never empty it"
            )
        entries: list[dict[str, object]] = []
        seen: set[str] = set()
        for index, entry in enumerate(raw_types):
            if not isinstance(entry, Mapping) or set(entry) != {"entity_type", "fillers"}:
                raise ProposerError(
                    f"{label}[{intent!r}].types[{index}] must carry exactly "
                    "'entity_type' and 'fillers'"
                )
            entity_type = entry["entity_type"]
            if not isinstance(entity_type, str) or not _SLURP_NAME_RE.fullmatch(entity_type):
                raise ProposerError(
                    f"{label}[{intent!r}].types[{index}] entity_type {entity_type!r} is "
                    "not a lower-case entity type name"
                )
            if entity_type in seen:
                raise ProposerError(
                    f"{label}[{intent!r}] lists entity type {entity_type!r} twice"
                )
            seen.add(entity_type)
            raw_fillers = entry["fillers"]
            if isinstance(raw_fillers, (str, bytes)) or not isinstance(
                raw_fillers, Sequence
            ):
                raise ProposerError(
                    f"{label}[{intent!r}].types[{index}] fillers must be a list"
                )
            fillers: list[str] = []
            for filler in raw_fillers:
                _checked_slurp_filler(filler, f"{label}[{intent!r}].{entity_type}")
                if filler in fillers:
                    raise ProposerError(
                        f"{label}[{intent!r}].{entity_type} repeats filler {filler!r}"
                    )
                fillers.append(filler)
            entries.append({"entity_type": entity_type, "fillers": fillers})
        out[intent] = {"types": entries}
    return out


def _checked_slurp_filler(filler: object, label: str) -> str:
    """One filler, fail-closed: ASCII, lower case, no separator, no padding.

    ``"; "`` is the renderer's own filler separator, so a filler carrying one
    would render into two fillers and the artifact would no longer be
    reproducible from its rendering -- which is the whole reason the block
    grammar, and not JSON, is EVO-S1's output contract.
    """

    if not isinstance(filler, str) or not filler:
        raise ProposerError(f"{label} has an empty filler")
    if not filler.isascii():
        raise ProposerError(f"{label} filler {filler!r} carries non-ASCII characters")
    if filler != filler.lower():
        raise ProposerError(f"{label} filler {filler!r} is not lower case")
    if filler != filler.strip() or "  " in filler:
        raise ProposerError(f"{label} filler {filler!r} carries padding whitespace")
    if ";" in filler or "\n" in filler or "\r" in filler:
        raise ProposerError(
            f"{label} filler {filler!r} carries a separator the renderer owns"
        )
    return filler


def _checked_exemplars(
    exemplars: Sequence[tuple[str, str, str]],
) -> tuple[tuple[str, str, str], ...]:
    if isinstance(exemplars, (str, bytes)):
        raise ProposerError("exemplars must be a sequence of triples")
    checked: list[tuple[str, str, str]] = []
    seen: set[str] = set()
    for index, item in enumerate(exemplars):
        if isinstance(item, (str, bytes)) or len(tuple(item)) != 3:
            raise ProposerError(
                f"exemplar {index} must be a (sample_id, query_text, gold_call) triple"
            )
        sample_id, query_text, gold_call = tuple(item)
        for field, value in (
            ("sample_id", sample_id),
            ("query_text", query_text),
            ("gold_call", gold_call),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ProposerError(f"exemplar {index} {field} must be non-empty text")
        if sample_id in seen:
            raise ProposerError(f"exemplars repeat sample_id {sample_id!r}")
        seen.add(sample_id)
        checked.append((sample_id, query_text, gold_call))
    return tuple(checked)


def _tool_of_gold_call(gold_call: str) -> str:
    """The function name a call string opens with (``setAlarm(...)`` ->
    ``setAlarm``) -- the Audio2Tool gold format the official parser reads.

    A released ``expected_tool_call`` is occasionally NAMESPACED
    (``smart_home.setApplianceMode(...)``) while the row's own ``tool_name``
    column, which is what the official scorer compares a prediction against,
    is the bare name. The last dotted segment is therefore the tool: 1 of the
    274 rows of ``A2T-EVO-EXEMPLARS-V2`` and 3 of fold A's 424 carry such a
    head, and grouping them under a namespaced key would refuse a legal
    exemplar over a released-data quirk. The call string itself is still
    rendered VERBATIM -- only the grouping key is normalized.
    """

    head = gold_call.split("(", 1)[0].strip()
    if not head:
        raise ProposerError(f"gold call {gold_call!r} names no tool")
    return head.rsplit(".", 1)[-1]


# ---------------------------------------------------------------------------
# The candidate artifact
# ---------------------------------------------------------------------------


def candidate_text(
    descriptions: Mapping[str, object],
    cue: str | None,
    *,
    artifact_family: str = A2T_DESCRIPTIONS_FAMILY,
) -> str:
    """The candidate's own canonical text -- the thing its id hashes.

    Deliberately NOT the rendered block a flight sends: that rendering is a
    function of fixed material (the whole 152-line registry; the unfloored
    TRAIN counts and shares), so hashing it would make every candidate id
    depend on bytes that never change while hiding what actually differs.

    ``a2t-descriptions`` -- the cue line followed by one
    ``"{tool}: {description}"`` line per targeted tool in name order.
    ``slurp-slot-schema`` -- a family marker, then one ``"== {intent}"`` line
    per rewritten intent in name order and one
    ``"- {entity_type}: {filler}; ..."`` line per listed type IN THE
    CANDIDATE'S OWN ORDER: the type order is part of what the candidate chose,
    so two candidates differing only in it must not collide.
    """

    if cue is not None and (not isinstance(cue, str) or not cue.strip()):
        raise ProposerError("cue must be non-empty text or None")
    if artifact_family == SLURP_SLOT_SCHEMA_FAMILY:
        blocks = _checked_slurp_blocks(descriptions, "blocks")
        block_lines = [f"artifact: {SLURP_SLOT_SCHEMA_FAMILY}"]
        for intent in sorted(blocks):
            block_lines.append(f"== {intent}")
            for entry in blocks[intent]["types"]:
                joined = "; ".join(entry["fillers"])
                block_lines.append(f"- {entry['entity_type']}: {joined}")
        return "\n".join(block_lines)
    if artifact_family != A2T_DESCRIPTIONS_FAMILY:
        raise ProposerError(f"artifact_family must be one of {ARTIFACT_FAMILIES}")
    checked = _checked_descriptions(descriptions, "descriptions")
    lines = ["cue: %s" % ("" if cue is None else cue)]
    lines.extend(f"{tool}: {checked[tool]}" for tool in sorted(checked))
    return "\n".join(lines)


def candidate_id_for(
    *,
    text: str,
    proposer_prompt_sha256: str | None,
    exemplar_ids: Sequence[str],
    round: int,
    target_id: str,
    k: int,
    family: str,
) -> str:
    """``sha256`` of the canonical JSON of the seven identity fields.

    Program section 5: "Candidate id = sha256 over text, proposer prompt,
    exemplar ids, round, target, k and family". All seven are inside the
    hash, so two candidates that differ only in which exemplars were drawn,
    or only in which round produced them, are different objects with
    different ids -- and a candidate cannot be silently re-labelled into
    another round, target, family or portfolio slot without changing its id.
    """

    if not isinstance(text, str) or not text:
        raise ProposerError("candidate text must be non-empty")
    if proposer_prompt_sha256 is not None and (
        not isinstance(proposer_prompt_sha256, str)
        or not re.fullmatch(r"[0-9a-f]{64}", proposer_prompt_sha256)
    ):
        raise ProposerError("proposer_prompt_sha256 must be a sha256 hex digest or None")
    if isinstance(exemplar_ids, (str, bytes)):
        raise ProposerError("exemplar_ids must be a sequence of ids")
    ids = tuple(exemplar_ids)
    for item in ids:
        if not isinstance(item, str) or not item:
            raise ProposerError("every exemplar id must be non-empty text")
    if len(set(ids)) != len(ids):
        raise ProposerError("exemplar_ids contains a duplicate")
    if isinstance(round, bool) or not isinstance(round, int) or round < 0:
        raise ProposerError("round must be a nonnegative integer")
    if isinstance(k, bool) or not isinstance(k, int) or k < 0:
        raise ProposerError("k must be a nonnegative integer")
    if not isinstance(target_id, str) or not target_id:
        raise ProposerError("target_id must be non-empty text")
    if family not in FAMILIES:
        raise ProposerError(f"family must be one of {FAMILIES}")
    return content_hash(
        {
            "text": text,
            "proposer_prompt_sha256": proposer_prompt_sha256,
            "exemplar_ids": list(ids),
            "round": round,
            "target": target_id,
            "k": k,
            "family": family,
        }
    )


@dataclass(frozen=True)
class CandidateArtifact:
    """One target's proposed artifact content for one round and slot.

    ``descriptions`` is the candidate's content mapping, and what its values
    ARE depends on ``artifact_family``: ``{tool: description}`` text for
    ``a2t-descriptions``, ``{intent: {"types": [...]}}`` blocks for
    ``slurp-slot-schema``. The field keeps its A2T name because it is the key
    every landed EVO-A1 receipt already carries and renaming it would make
    those receipts unreadable; the family is what says how to read it.
    """

    candidate_id: str
    family: str
    target_id: str
    round: int
    k: int
    descriptions: Mapping[str, object]
    cue: str | None
    proposer_prompt_sha256: str | None
    exemplar_ids: tuple[str, ...]
    artifact_family: str = A2T_DESCRIPTIONS_FAMILY

    @property
    def text(self) -> str:
        return candidate_text(
            self.descriptions, self.cue, artifact_family=self.artifact_family
        )

    def expected_candidate_id(self) -> str:
        return candidate_id_for(
            text=self.text,
            proposer_prompt_sha256=self.proposer_prompt_sha256,
            exemplar_ids=self.exemplar_ids,
            round=self.round,
            target_id=self.target_id,
            k=self.k,
            family=self.family,
        )

    def validate(self) -> "CandidateArtifact":
        """Fail closed unless every field is well formed AND ``candidate_id``
        is the digest its own contents produce.

        Recomputing the id is the point: an artifact read back from a receipt
        whose text was edited by hand no longer matches, so a round cannot be
        replayed against content that is not what was flown.
        """

        if self.artifact_family not in ARTIFACT_FAMILIES:
            raise ProposerError(f"artifact_family must be one of {ARTIFACT_FAMILIES}")
        if self.artifact_family == SLURP_SLOT_SCHEMA_FAMILY:
            _checked_slurp_blocks(self.descriptions, "blocks")
        else:
            _checked_descriptions(self.descriptions, "descriptions")
        recomputed = self.expected_candidate_id()
        if not isinstance(self.candidate_id, str) or self.candidate_id != recomputed:
            raise ProposerError(
                f"candidate_id {self.candidate_id!r} does not match this candidate's "
                f"contents (expected {recomputed})"
            )
        if self.family == "deterministic" and self.proposer_prompt_sha256 is not None:
            raise ProposerError(
                "a deterministic control candidate has no proposer prompt"
            )
        if self.family == "placebo" and self.cue is not None:
            raise ProposerError(
                "a placebo candidate carries no distinguishing cue by construction"
            )
        if self.artifact_family == SLURP_SLOT_SCHEMA_FAMILY:
            # A SLURP block set carries no cue: the EVO-S1 output contract is
            # the block grammar itself, so there is nothing beside the blocks
            # for a cue to be, and a candidate that carried one would have
            # been parsed by something other than the block parser.
            if self.cue is not None:
                raise ProposerError(
                    "a slurp-slot-schema candidate carries no cue; its whole output "
                    "contract is the block grammar"
                )
            if self.family == "proposer" and self.proposer_prompt_sha256 is None:
                raise ProposerError(
                    "a proposer candidate must carry its prompt digest"
                )
        elif self.family == "proposer" and (
            self.cue is None or self.proposer_prompt_sha256 is None
        ):
            raise ProposerError(
                "a proposer candidate must carry both its cue and its prompt digest"
            )
        return self

    def as_json(self) -> dict[str, object]:
        return {
            "schema": CANDIDATE_SCHEMA,
            "candidate_id": self.candidate_id,
            "family": self.family,
            "artifact_family": self.artifact_family,
            "target_id": self.target_id,
            "round": self.round,
            "k": self.k,
            "descriptions": {
                tool: self.descriptions[tool] for tool in sorted(self.descriptions)
            },
            "cue": self.cue,
            "proposer_prompt_sha256": self.proposer_prompt_sha256,
            "exemplar_ids": list(self.exemplar_ids),
        }


def candidate_bytes(candidate: CandidateArtifact) -> int:
    """Canonical byte size of a candidate's override mapping.

    The stage-one tie-break's "fewer bytes" rule (program section 5) measures
    the OVERRIDE, not the artifact envelope: two candidates that say the same
    thing in fewer characters cost fewer prompt tokens for the same effect.
    """

    return len(
        canonical_json_bytes(
            {tool: candidate.descriptions[tool] for tool in sorted(candidate.descriptions)}
        )
    )


# ---------------------------------------------------------------------------
# Proposer instructions
# ---------------------------------------------------------------------------


def _render_tool_block(rows_by_name: Mapping[str, Mapping[str, str]],
                       incumbent: Mapping[str, str]) -> list[str]:
    lines: list[str] = []
    for tool in sorted(rows_by_name):
        row = rows_by_name[tool]
        lines.append(f"### {tool}")
        lines.append(f"signature: {row['signature']}")
        lines.append(f"domain: {row['domain']}")
        lines.append(f"category: {row['category']}")
        lines.append(f"argument constraints: {row['argument_constraints'] or '(none)'}")
        lines.append(f"argument defaults: {row['argument_defaults'] or '(none)'}")
        lines.append(f"current description: {incumbent[tool]}")
        lines.append("")
    return lines


def _render_exemplar_block(
    rows_by_name: Mapping[str, Mapping[str, str]],
    exemplars: Sequence[tuple[str, str, str]],
) -> list[str]:
    """Exemplars grouped under the tool their GOLD CALL names.

    Sample ids are used only to group and to seed the candidate id; they
    never reach the rendered instruction, so a description written from this
    prompt cannot copy one back out (which is exactly what
    :func:`validate_candidate_artifact` refuses).
    """

    grouped: dict[str, list[tuple[str, str]]] = {tool: [] for tool in rows_by_name}
    for sample_id, query_text, gold_call in exemplars:
        tool = _tool_of_gold_call(gold_call)
        if tool not in grouped:
            raise ProposerError(
                f"exemplar {sample_id!r} has gold call for {tool!r}, which is not one "
                f"of this target's tools {sorted(rows_by_name)}"
            )
        grouped[tool].append((query_text, gold_call))
    lines: list[str] = []
    for tool in sorted(grouped):
        lines.append(f"### {tool}")
        if not grouped[tool]:
            lines.append("(no exemplars drawn for this tool)")
        for index, (query_text, gold_call) in enumerate(grouped[tool], start=1):
            lines.append(f"{index}. spoken request: {query_text}")
            lines.append(f"   gold call: {gold_call}")
        lines.append("")
    return lines


def _output_contract(tools: Sequence[str], *, with_cue: bool) -> list[str]:
    keys = ", ".join(f'"{tool}": "..."' for tool in tools)
    cue_field = '"cue": "...", ' if with_cue else ""
    return [
        "## Output",
        "",
        "Reply with ONE JSON object and nothing else -- no prose before or after it,",
        "no code fence, no explanation:",
        "",
        "{" + cue_field + '"descriptions": {' + keys + "}}",
        "",
        "Rules:",
        f"- the descriptions object has exactly these keys: {', '.join(tools)}",
        f"- each description is at most {MAX_DESCRIPTION_CHARS} ASCII characters, on one line",
        "- describe what the tool does and when to choose it, never an example value",
        "- never copy a sample identifier, a numeric id, or a gold call string",
        "- keep each description close in length to the current one",
    ]


def render_proposer_instruction(
    registry_rows: Sequence[Mapping[str, str]],
    incumbent_descriptions: Mapping[str, str],
    exemplars: Sequence[tuple[str, str, str]],
    *,
    target_id: str,
    round: int,
    k: int,
) -> str:
    """The text-only instruction that asks the frozen core for one rewrite.

    Byte-deterministic for identical inputs: every block is name-sorted, the
    exemplars are grouped by their gold call's tool and kept in the caller's
    draw order within a group, and the header carries ``target_id``, ``round``
    and ``k`` so the three proposer slots of one round have distinct prompt
    bytes even in the degenerate case where their exemplar draws collide.

    The inputs are exactly what section 5 preregisters: the PAIR's registry
    rows (not the whole registry), M construction exemplars per tool with
    their gold calls, and the incumbent descriptions. No evaluation row, no
    evaluation gold, no score ever enters this prompt.
    """

    rows_by_name = _rows_by_name(registry_rows)
    incumbent = _checked_descriptions(incumbent_descriptions, "incumbent_descriptions")
    if set(incumbent) != set(rows_by_name):
        raise ProposerError(
            "incumbent_descriptions must name exactly this target's tools "
            f"{sorted(rows_by_name)}; it names {sorted(incumbent)}"
        )
    checked = _checked_exemplars(exemplars)
    if not isinstance(target_id, str) or not target_id:
        raise ProposerError("target_id must be non-empty text")
    if isinstance(round, bool) or not isinstance(round, int) or round < 0:
        raise ProposerError("round must be a nonnegative integer")
    if isinstance(k, bool) or not isinstance(k, int) or k < 0:
        raise ProposerError("k must be a nonnegative integer")

    tools = sorted(rows_by_name)
    lines = [
        f"# target {target_id} | round {round} | variant {k}",
        "",
        "You are rewriting the catalogue descriptions of tools that a speech "
        "assistant confuses with one another.",
        "",
        f"There are {len(tools)} tools below. They are selected from the same "
        "catalogue by the same request text, and today a reader cannot reliably "
        "tell them apart from their descriptions alone.",
        "",
        "## Tools",
        "",
    ]
    lines.extend(_render_tool_block(rows_by_name, incumbent))
    lines.append("## Example requests and their correct calls")
    lines.append("")
    lines.extend(_render_exemplar_block(rows_by_name, checked))
    lines.append("## Task")
    lines.append("")
    lines.append(
        "First decide the single cue that separates these tools -- the thing in a "
        "spoken request that should send a reader to one rather than another."
    )
    lines.append(
        "Then rewrite each description so that cue is unmistakable in it."
    )
    lines.append("")
    lines.extend(_output_contract(tools, with_cue=True))
    return "\n".join(lines) + "\n"


def render_placebo_instruction(
    registry_rows: Sequence[Mapping[str, str]],
    incumbent_descriptions: Mapping[str, str],
    *,
    target_id: str,
    round: int,
    k: int,
    target_lengths: Mapping[str, int],
) -> str:
    """The length-matched placebo prompt: rewrite, but carry NO cue.

    The placebo exists to separate FORM from CONTENT. A proposer candidate
    changes two things at once -- the description text is new, and it now
    names a separating cue. The placebo changes only the first: same tools,
    same target length per tool (``target_lengths``, normally the proposer
    winner's own character counts), a rewrite that is explicitly forbidden to
    say anything that would help choose between the tools. If the placebo
    scores like the proposer candidate, the round's gain was novelty of
    wording, and section 5 names that a kill result.

    No exemplars are shown: an exemplar's gold call IS a distinguishing cue,
    so showing them would defeat the construction.
    """

    rows_by_name = _rows_by_name(registry_rows)
    incumbent = _checked_descriptions(incumbent_descriptions, "incumbent_descriptions")
    if set(incumbent) != set(rows_by_name):
        raise ProposerError(
            "incumbent_descriptions must name exactly this target's tools "
            f"{sorted(rows_by_name)}; it names {sorted(incumbent)}"
        )
    if not isinstance(target_lengths, Mapping) or set(target_lengths) != set(rows_by_name):
        raise ProposerError(
            "target_lengths must name exactly this target's tools "
            f"{sorted(rows_by_name)}"
        )
    for tool, length in sorted(target_lengths.items()):
        if isinstance(length, bool) or not isinstance(length, int) or length <= 0:
            raise ProposerError(f"target_lengths[{tool!r}] must be a positive integer")
        if length > MAX_DESCRIPTION_CHARS:
            raise ProposerError(
                f"target_lengths[{tool!r}] exceeds the {MAX_DESCRIPTION_CHARS}-character cap"
            )
    if not isinstance(target_id, str) or not target_id:
        raise ProposerError("target_id must be non-empty text")
    if isinstance(round, bool) or not isinstance(round, int) or round < 0:
        raise ProposerError("round must be a nonnegative integer")
    if isinstance(k, bool) or not isinstance(k, int) or k < 0:
        raise ProposerError("k must be a nonnegative integer")

    tools = sorted(rows_by_name)
    lines = [
        f"# target {target_id} | round {round} | variant {k} | placebo",
        "",
        "Rewrite each tool description below in different words.",
        "",
        "This is a wording exercise, not a disambiguation exercise. Carry no "
        "distinguishing cue: after your rewrite it must be no easier to choose "
        "between these tools than it is now. Do not add the domain, the category, "
        "the argument names, an example request, or any contrast between the tools.",
        "",
        "## Tools",
        "",
    ]
    lines.extend(_render_tool_block(rows_by_name, incumbent))
    lines.append("## Length")
    lines.append("")
    for tool in tools:
        lines.append(f"- {tool}: about {target_lengths[tool]} characters")
    lines.append("")
    lines.extend(_output_contract(tools, with_cue=False))
    return "\n".join(lines) + "\n"


#: Which revision of each family's rendered proposer instruction this module
#: emits. The instruction text is inside every candidate id (through
#: ``proposer_prompt_sha256``) and it is the preregistered prompt, so a change
#: to its bytes is a version bump and is recorded in the PROPOSE receipt --
#: never a silent edit that leaves two rounds' candidate ids incomparable with
#: nothing in the record to say why.
#:
#: ``slurp-slot-schema`` moved to v2 on 2026-09-07 (track E3e). EVO-S1 round 1
#: lost 23 of its 54 draws to ONE formatting habit: the model separated its
#: blocks with a blank line, which the v1 rules covered only as the general
#: "no blank lines" and which the fail-closed parser refuses without repair.
#: v2 names the between-blocks case in its own line. The parser is unchanged:
#: the fix belongs in the instruction, because a repair here would be a second,
#: unlogged policy deciding what the frozen core meant. Round 1's sealed
#: prompts are untouched -- they were flown under v1 and stay v1.
#:
#: ``a2t-descriptions`` stays v1: its output contract is strict JSON, whose
#: parser treats a blank line as the insignificant whitespace it is, so the
#: same habit cannot cost that family a draw.
PROPOSER_INSTRUCTION_VERSIONS: Mapping[str, str] = {
    A2T_DESCRIPTIONS_FAMILY: "proposer-instruction-v1",
    SLURP_SLOT_SCHEMA_FAMILY: "proposer-instruction-v2",
}


def proposer_instruction_version(artifact_family: str) -> str:
    """Which instruction revision this module renders for ``artifact_family``."""

    version = PROPOSER_INSTRUCTION_VERSIONS.get(artifact_family)
    if version is None:
        raise ProposerError(f"artifact_family must be one of {ARTIFACT_FAMILIES}")
    return version


def prompt_sha256(instruction: str) -> str:
    """SHA-256 of a rendered proposer instruction, the digest a candidate id
    carries as ``proposer_prompt_sha256``."""

    if not isinstance(instruction, str) or not instruction:
        raise ProposerError("instruction must be non-empty text")
    return hashlib.sha256(instruction.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------


def parse_proposer_response(
    text: str, *, expected_tools: Sequence[str]
) -> tuple[str, dict[str, str]]:
    """Strict JSON only. ``(cue, {tool: description})`` or ``ProposerError``.

    Strict means strict: the whole response, after surrounding whitespace is
    stripped, must be one JSON object with exactly the keys ``cue`` and
    ``descriptions``, and ``descriptions`` must name exactly
    ``expected_tools`` -- no extra tool, no missing tool, no code fence, no
    prose around the object, no second object. A parse repair here would be a
    silent second policy deciding what the proposer meant; a refusal costs
    one candidate slot and is visible in the round receipt.
    """

    if isinstance(expected_tools, (str, bytes)):
        raise ProposerError("expected_tools must be a sequence of tool names")
    tools = tuple(expected_tools)
    if not tools:
        raise ProposerError("expected_tools must be non-empty")
    for tool in tools:
        if not isinstance(tool, str) or not tool:
            raise ProposerError("every expected tool name must be non-empty text")
    if len(set(tools)) != len(tools):
        raise ProposerError("expected_tools contains a duplicate")
    if not isinstance(text, str) or not text.strip():
        raise ProposerError("proposer response is empty")

    try:
        document = json.loads(text.strip())
    except json.JSONDecodeError as error:
        raise ProposerError(f"proposer response is not strict JSON: {error}") from error
    if not isinstance(document, dict):
        raise ProposerError("proposer response must be a JSON object")
    if set(document) != {"cue", "descriptions"}:
        raise ProposerError(
            f"proposer response must carry exactly 'cue' and 'descriptions'; it "
            f"carries {sorted(document)}"
        )
    cue = document["cue"]
    if not isinstance(cue, str) or not cue.strip():
        raise ProposerError("proposer response cue must be non-empty text")
    descriptions = document["descriptions"]
    if not isinstance(descriptions, dict):
        raise ProposerError("proposer response descriptions must be a JSON object")
    if set(descriptions) != set(tools):
        raise ProposerError(
            f"proposer response describes {sorted(descriptions)}, not exactly "
            f"{sorted(tools)}"
        )
    out: dict[str, str] = {}
    for tool in sorted(descriptions):
        value = descriptions[tool]
        if not isinstance(value, str) or not value.strip():
            raise ProposerError(f"description for {tool!r} must be non-empty text")
        out[tool] = value
    return cue, out


# ---------------------------------------------------------------------------
# Candidate constructors
# ---------------------------------------------------------------------------


def _build(
    *,
    family: str,
    descriptions: Mapping[str, object],
    cue: str | None,
    target_id: str,
    round: int,
    k: int,
    proposer_prompt_sha256: str | None,
    exemplar_ids: Sequence[str],
    artifact_family: str = A2T_DESCRIPTIONS_FAMILY,
) -> CandidateArtifact:
    if artifact_family == SLURP_SLOT_SCHEMA_FAMILY:
        checked: Mapping[str, object] = _checked_slurp_blocks(descriptions, "blocks")
    else:
        checked = _checked_descriptions(descriptions, "descriptions")
    ids = tuple(exemplar_ids)
    text = candidate_text(checked, cue, artifact_family=artifact_family)
    candidate = CandidateArtifact(
        candidate_id=candidate_id_for(
            text=text,
            proposer_prompt_sha256=proposer_prompt_sha256,
            exemplar_ids=ids,
            round=round,
            target_id=target_id,
            k=k,
            family=family,
        ),
        family=family,
        target_id=target_id,
        round=round,
        k=k,
        descriptions=dict(sorted(checked.items())),
        cue=cue,
        proposer_prompt_sha256=proposer_prompt_sha256,
        exemplar_ids=ids,
        artifact_family=artifact_family,
    )
    return candidate.validate()


def proposer_candidate(
    cue: str,
    descriptions: Mapping[str, str],
    *,
    target_id: str,
    round: int,
    k: int,
    proposer_prompt_sha256: str,
    exemplar_ids: Sequence[str],
) -> CandidateArtifact:
    """The frozen core's own rewrite, as returned by
    :func:`parse_proposer_response`, bound to the prompt digest and the
    exemplar draw that produced it."""

    return _build(
        family="proposer",
        descriptions=descriptions,
        cue=cue,
        target_id=target_id,
        round=round,
        k=k,
        proposer_prompt_sha256=proposer_prompt_sha256,
        exemplar_ids=exemplar_ids,
    )


def contrast_note_records(
    registry_rows: Sequence[Mapping[str, str]],
    targets: Mapping[str, Mapping[str, str]],
    *,
    function_words: Sequence[str],
    prefix: str = NOTE_PREFIX,
    filler: str = CONTROL_FILLER,
    token_counter: Callable[[str], int] | None = None,
) -> list[dict[str, object]]:
    """One record per targeted tool for the APPENDED-NOTE family (KC-A1).

    ``targets`` maps a target id to that target's ``{tool_name: note}``. Each
    record carries the released description, the note, the matched
    CATEGORY-ONLY control note, and both rendered descriptions, so a caller
    builds the treatment artifact, its control and its receipt from one pass.

    Three rules, all fail-closed, and all of them exist because the ORG-1
    verdict showed that prompt FORM moves this metric on its own:

    * a note starts with ``prefix`` and is ASCII, so the released
      ``"- {signature}: {description}"`` line keeps its shape and only grows;
    * every alphanumeric word of a note is either a ``function_words`` entry
      or occurs (case-insensitively) in the registry columns of the tools of
      its OWN target. A note may therefore say nothing the registry does not
      already say -- no invented device knowledge, and no evaluation text;
    * the control is ``"; " + category`` grown with ``filler`` until it
      matches the note, so the control prices the note's form at the same
      per-line cost with none of its contrast. A category longer than its
      note is refused rather than truncated, because a truncated control is
      neither matched nor a category.

    ``token_counter`` selects WHICH quantity the control is matched on, and
    the owner ruling of 2026-09-06 makes that choice the whole point of the
    control. ``None`` keeps the original CHARACTER match: filler while it
    fits, then trailing spaces. A counter -- the serving geometry's own
    tokenizer, injected exactly as :func:`validate_candidate_artifact` takes
    it -- switches to a TOKEN match: whole ``filler`` repeats until the
    rendered description cell ``description + control`` measures exactly as
    many tokens as ``description + note``. KC-A1's first attempt showed why:
    two arms that were character-identical line for line measured 14 tokens
    apart (``; kelvin only, no color`` costs 3.659 characters per token,
    repeated ``" tool"`` and trailing spaces 5.367), so a character-matched
    control prices only part of the form it exists to price. A control that
    cannot land exactly on the note's token count is refused rather than
    approximated; the caller still has to assert WHOLE-BLOCK token equality,
    which is the invariant a per-cell match only makes likely.
    """

    rows_by_name = _rows_by_name(registry_rows)
    if not isinstance(targets, Mapping) or not targets:
        raise ProposerError("targets must be a non-empty mapping of target id to notes")
    if isinstance(function_words, (str, bytes)):
        raise ProposerError("function_words must be a sequence of words")
    allowed = {str(word).lower() for word in function_words}
    records: list[dict[str, object]] = []
    for target_id in sorted(targets):
        notes = targets[target_id]
        if not isinstance(notes, Mapping) or not notes:
            raise ProposerError(f"target {target_id!r} carries no notes")
        legal = set(allowed)
        for tool in notes:
            if tool not in rows_by_name:
                raise ProposerError(f"target {target_id!r} names unknown tool {tool!r}")
            for column in rows_by_name[tool].values():
                legal |= set(_WORD_RE.findall(str(column).lower()))
        for tool in sorted(notes):
            row = rows_by_name[tool]
            note = notes[tool]
            if not isinstance(note, str) or not note.startswith(prefix) or not note.isascii():
                raise ProposerError(
                    f"note for {tool!r} must be ASCII text starting with {prefix!r}"
                )
            illegal = sorted(set(_WORD_RE.findall(note.lower())) - legal)
            if illegal:
                raise ProposerError(
                    f"note for {tool!r} carries word(s) the registry does not: {illegal}"
                )
            control = f"{prefix}{row['category']}"
            measured: dict[str, object] = {}
            if token_counter is None:
                if len(control) > len(note):
                    raise ProposerError(
                        f"the category-only control for {tool!r} is {len(control)} "
                        f"characters and cannot be padded down to its {len(note)}-"
                        "character note"
                    )
                while len(control) + len(filler) <= len(note):
                    control += filler
                padding = len(note) - len(control)
                control += " " * padding
                measured = {"control_match": "characters", "control_space_padding": padding}
            else:
                control, measured = _token_matched_control(
                    tool,
                    str(row["description"]),
                    note,
                    control,
                    filler=filler,
                    token_counter=token_counter,
                )
            records.append(
                {
                    "tool_name": tool,
                    "target_id": target_id,
                    "domain": row["domain"],
                    "category": row["category"],
                    "description_chars": len(row["description"]),
                    "note": note,
                    "note_chars": len(note),
                    "control_note": control,
                    "control_chars": len(control),
                    "kc_a1": row["description"] + note,
                    "kc_a1c": row["description"] + control,
                    **measured,
                }
            )
    return records


def _token_matched_control(
    tool: str,
    description: str,
    note: str,
    control: str,
    *,
    filler: str,
    token_counter: Callable[[str], int],
) -> tuple[str, dict[str, object]]:
    """``control`` grown by whole ``filler`` repeats until the rendered
    description cell measures exactly the treatment cell's token count."""

    target = int(token_counter(description + note))
    measured = int(token_counter(description + control))
    if measured > target:
        raise ProposerError(
            f"the category-only control for {tool!r} measures {measured} tokens and "
            f"cannot be padded down to its {target}-token note"
        )
    repeats = 0
    while measured < target:
        grown = control + filler
        after = int(token_counter(description + grown))
        if after > target:
            raise ProposerError(
                f"the category-only control for {tool!r} cannot be token-matched: one "
                f"more {filler!r} takes it from {measured} to {after} tokens against "
                f"the note's {target}"
            )
        if after == measured:
            raise ProposerError(
                f"filler {filler!r} adds no token to the control for {tool!r}; it "
                "cannot close a token gap"
            )
        control, measured, repeats = grown, after, repeats + 1
    return control, {
        "control_match": "tokens",
        "control_filler_repeats": repeats,
        "note_cell_tokens": target,
        "control_cell_tokens": measured,
    }


def derive_target_id(tools: Sequence[str]) -> str:
    """The canonical id of a target that has no MF-1 name of its own:
    ``"+".join(sorted(tools))``.

    MF-1's TARGET list names its twin pairs; that name is what
    ``rails.evolution.Target`` carries and what every receipt keys on. This
    derivation exists so a candidate built ad hoc (a dry run, a unit test, a
    one-off control) still gets a stable, content-determined id rather than a
    blank one, and so two callers naming the same tool set never disagree.
    """

    if isinstance(tools, (str, bytes)) or not tools:
        raise ProposerError("tools must be a non-empty sequence of tool names")
    names = tuple(tools)
    for name in names:
        if not isinstance(name, str) or not name:
            raise ProposerError("every tool name must be non-empty text")
    if len(set(names)) != len(names):
        raise ProposerError("tools contains a duplicate")
    return "+".join(sorted(names))


def deterministic_candidate(
    registry_rows: Sequence[Mapping[str, str]],
    target_tools: Sequence[str],
    *,
    round: int,
    k: int = 0,
    target_id: str | None = None,
) -> CandidateArtifact:
    """The zero-contact control: append ``" (domain: d; category: c)"``.

    It uses only columns the released registry already carries and the
    compact rendering already drops. That is what makes it the right control
    for a proposer rewrite: a proposer candidate that cannot beat this one has
    not added knowledge, it has re-stated the registry. Section 5 names "the
    deterministic control within 0.5 pp of the proposer" a kill result.

    ``target_id`` defaults to :func:`derive_target_id` over ``target_tools``;
    a loop that has MF-1 target names passes its own.
    """

    rows_by_name = _rows_by_name(registry_rows)
    if isinstance(target_tools, (str, bytes)) or not target_tools:
        raise ProposerError("target_tools must be a non-empty sequence of tool names")
    tools = tuple(target_tools)
    resolved_target = derive_target_id(tools) if target_id is None else target_id
    descriptions: dict[str, str] = {}
    for tool in sorted(tools):
        row = rows_by_name.get(tool)
        if row is None:
            raise ProposerError(
                f"target tool {tool!r} is not among the supplied registry rows"
            )
        descriptions[tool] = (
            f"{row['description']} (domain: {row['domain']}; "
            f"category: {row['category']})"
        )
    return _build(
        family="deterministic",
        descriptions=descriptions,
        cue=None,
        target_id=resolved_target,
        round=round,
        k=k,
        proposer_prompt_sha256=None,
        exemplar_ids=(),
    )


def placebo_candidate(
    descriptions: Mapping[str, str],
    *,
    target_id: str,
    round: int,
    k: int,
    proposer_prompt_sha256: str,
    exemplar_ids: Sequence[str] = (),
    no_cue: bool = True,
) -> CandidateArtifact:
    """The length-matched paraphrase hook.

    ``descriptions`` is the proposer's PARSED text from a
    :func:`render_placebo_instruction` call -- the placebo is a model
    product, not a string transformation, because a mechanical paraphrase
    would be a different manipulation than the one the proposer arm performs.
    ``no_cue`` must be ``True`` and is the explicit marker that the caller
    used the no-cue instruction; a placebo built from a cue-bearing prompt
    would silently be a second proposer candidate, so it is refused.
    """

    if no_cue is not True:
        raise ProposerError(
            "placebo_candidate requires no_cue=True: a placebo is built from the "
            "'carry no distinguishing cue' instruction, never from a cue-bearing one"
        )
    return _build(
        family="placebo",
        descriptions=descriptions,
        cue=None,
        target_id=target_id,
        round=round,
        k=k,
        proposer_prompt_sha256=proposer_prompt_sha256,
        exemplar_ids=exemplar_ids,
    )


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CandidateValidation:
    """What a passing candidate measured, for the round receipt."""

    candidate_id: str
    rendered_sha256: str
    rendered_lines: int
    rendered_tokens: int
    token_budget: int
    max_description_chars: int
    exemplar_overlap_count: int
    exemplar_overlap_ngrams: tuple[str, ...]
    artifact_family: str = A2T_DESCRIPTIONS_FAMILY
    token_counter_id: str = SERVING_TOKENIZER_ID
    #: Per-artifact-key measurements, which the EVO-S1 round receipt reports
    #: because that cell's budget is RELATIVE and per intent: one record per
    #: rewritten intent carrying its line count, its cap, its characters and
    #: its token delta against the incumbent block. Empty for EVO-A1, whose
    #: budget is one absolute number over the whole rendered registry.
    per_key: tuple[Mapping[str, object], ...] = ()

    def as_json(self) -> dict[str, object]:
        return {
            "schema": VALIDATION_SCHEMA,
            "candidate_id": self.candidate_id,
            "artifact_family": self.artifact_family,
            "token_counter_id": self.token_counter_id,
            "rendered_sha256": self.rendered_sha256,
            "rendered_lines": self.rendered_lines,
            "rendered_tokens": self.rendered_tokens,
            "token_budget": self.token_budget,
            "max_description_chars": self.max_description_chars,
            "exemplar_overlap_count": self.exemplar_overlap_count,
            "exemplar_overlap_ngrams": list(self.exemplar_overlap_ngrams),
            "per_key": [dict(record) for record in self.per_key],
        }


def validate_candidate_artifact(
    candidate: CandidateArtifact,
    *,
    registry_rows: Sequence[Mapping[str, str]],
    token_counter: Callable[[str], int],
    compact_baseline_tokens: int,
    evaluation_query_texts: Sequence[str] = (),
    registry_text: str = "",
    exemplar_texts: Sequence[str] = (),
    expected_row_count: int = REGISTRY_LINE_COUNT,
) -> CandidateValidation:
    """Every form and decontamination gate of section 5, in one fail-closed pass.

    Form caps (a candidate that fails any of these never flies):

    * ASCII only, in every description and in the cue;
    * at most ``MAX_DESCRIPTION_CHARS`` (200) characters per description, and
      no newline inside one;
    * the WHOLE rendered block within ``compact_baseline_tokens +
      TOKEN_HEADROOM`` (+40) tokens. ORG-1 lost three points at +87, which is
      why the budget is a gate and not a preference. Token counting is
      INJECTED (``token_counter``): the authority is the serving geometry's
      own tokenizer, and this module must not grow a second, disagreeing one;
    * exactly ``expected_row_count`` (152) rendered lines, in plain
      ``tool_name`` sorted order -- the shape the baseline was sealed with.

    Decontamination:

    * no Audio2Tool sample identifier (``tier3_multi_intent:000412``) and no
      bare six-digit id anywhere in a description;
    * no word 6-gram shared with any text in ``evaluation_query_texts``,
      UNLESS that 6-gram already occurs in ``registry_text`` (the released
      registry is legal material: a description may of course reuse the
      registry's own phrasing even when an evaluation query happens to
      contain it too);
    * overlap with ``exemplar_texts`` -- the CONSTRUCTION rows the proposer
      was shown -- is COUNTED and returned, never gated. Construction rows are
      legally visible to the proposer; the count is the memorization signal a
      reviewer reads beside the round's gain.

    Returns the measured record on success; raises :class:`ProposerError` with
    the failed gate named on any failure.
    """

    candidate.validate()
    rows_by_name = _rows_by_name(registry_rows)
    if isinstance(expected_row_count, bool) or not isinstance(expected_row_count, int):
        raise ProposerError("expected_row_count must be an integer")
    if len(rows_by_name) != expected_row_count:
        raise ProposerError(
            f"registry carries {len(rows_by_name)} rows, not the expected "
            f"{expected_row_count}"
        )
    unknown = sorted(set(candidate.descriptions) - set(rows_by_name))
    if unknown:
        raise ProposerError(f"candidate overrides tools absent from the registry: {unknown}")
    if isinstance(compact_baseline_tokens, bool) or not isinstance(
        compact_baseline_tokens, int
    ) or compact_baseline_tokens <= 0:
        raise ProposerError("compact_baseline_tokens must be a positive integer")
    if not callable(token_counter):
        raise ProposerError("token_counter must be callable")

    # -- form: per description -------------------------------------------
    if candidate.cue is not None and not candidate.cue.isascii():
        raise ProposerError("candidate cue carries non-ASCII characters")
    for tool in sorted(candidate.descriptions):
        text = candidate.descriptions[tool]
        if not text.isascii():
            raise ProposerError(f"description for {tool!r} carries non-ASCII characters")
        if "\n" in text or "\r" in text:
            raise ProposerError(f"description for {tool!r} carries a newline")
        if len(text) > MAX_DESCRIPTION_CHARS:
            raise ProposerError(
                f"description for {tool!r} is {len(text)} characters, over the "
                f"{MAX_DESCRIPTION_CHARS}-character cap"
            )
        if _carries_sample_identifier(text):
            raise ProposerError(
                f"description for {tool!r} carries what looks like a sample identifier"
            )

    # -- form: the whole rendered block ----------------------------------
    rendered = render_registry_compact_rows(
        list(registry_rows), description_overrides=dict(candidate.descriptions)
    )
    lines = rendered.split("\n")
    if len(lines) != expected_row_count:
        raise ProposerError(
            f"rendered registry has {len(lines)} lines, not {expected_row_count}"
        )
    expected_order = [
        f"- {rows_by_name[tool]['signature']}: " for tool in sorted(rows_by_name)
    ]
    for line, prefix in zip(lines, expected_order):
        if not line.startswith(prefix):
            raise ProposerError(
                "rendered registry is not in plain tool_name sorted order with the "
                "released one-line-per-tool shape"
            )
    tokens = token_counter(rendered)
    if isinstance(tokens, bool) or not isinstance(tokens, int) or tokens < 0:
        raise ProposerError("token_counter must return a nonnegative integer")
    budget = compact_baseline_tokens + TOKEN_HEADROOM
    if tokens > budget:
        raise ProposerError(
            f"rendered registry is {tokens} tokens, over the {budget}-token budget "
            f"({compact_baseline_tokens} compact + {TOKEN_HEADROOM})"
        )

    # -- decontamination --------------------------------------------------
    candidate_grams: set[tuple[str, ...]] = set()
    for tool in sorted(candidate.descriptions):
        candidate_grams |= word_ngrams(candidate.descriptions[tool])

    if isinstance(evaluation_query_texts, (str, bytes)):
        raise ProposerError("evaluation_query_texts must be a sequence of texts")
    evaluation_grams: set[tuple[str, ...]] = set()
    for item in evaluation_query_texts:
        if not isinstance(item, str):
            raise ProposerError("every evaluation query text must be text")
        evaluation_grams |= word_ngrams(item)
    if not isinstance(registry_text, str):
        raise ProposerError("registry_text must be text")
    legal_grams = word_ngrams(registry_text) if registry_text else set()
    illegal = sorted(" ".join(gram) for gram in (candidate_grams & evaluation_grams) - legal_grams)
    if illegal:
        raise ProposerError(
            f"candidate shares {len(illegal)} word {DECONTAMINATION_NGRAM}-gram(s) with "
            f"the evaluation roster that the registry does not carry: {illegal[:3]}"
        )

    if isinstance(exemplar_texts, (str, bytes)):
        raise ProposerError("exemplar_texts must be a sequence of texts")
    exemplar_grams: set[tuple[str, ...]] = set()
    for item in exemplar_texts:
        if not isinstance(item, str):
            raise ProposerError("every exemplar text must be text")
        exemplar_grams |= word_ngrams(item)
    overlap = sorted(" ".join(gram) for gram in candidate_grams & exemplar_grams)

    return CandidateValidation(
        candidate_id=candidate.candidate_id,
        rendered_sha256=hashlib.sha256(rendered.encode("utf-8")).hexdigest(),
        rendered_lines=len(lines),
        rendered_tokens=tokens,
        token_budget=budget,
        max_description_chars=max(
            len(candidate.descriptions[tool]) for tool in candidate.descriptions
        ),
        exemplar_overlap_count=len(overlap),
        exemplar_overlap_ngrams=tuple(overlap),
    )


# ---------------------------------------------------------------------------
# The SLURP slot-schema artifact family (EVO-S1)
# ---------------------------------------------------------------------------
#
# What a candidate may choose, and nothing else (preregistration section 3):
# per intent, WHICH entity types to list and in what ORDER, and up to five
# FILLERS per listed type. The header line, every count and every share are
# re-rendered by ``data.slurp.render_slurp_intent_slot_schema`` from the
# UNFLOORED TRAIN table, so a candidate can never misstate what TRAIN
# contains, and the block grammar, the intent-selection rule, the fallback,
# the system message, the contact count and the roster are all exactly
# KC-S1b's.


#: Identity of the evolved schema this family builds. Distinct from
#: ``data.slurp.SLURP_INTENT_SLOT_SCHEMA_ID`` so a rendered evolved block can
#: never be mistaken for A_0's own in a receipt.
SLURP_EVOLVED_SCHEMA_ID = "slurp-evolved-slot-schema-v1"


def _slurp_schema_types():
    """``data.slurp``'s two schema dataclasses, imported lazily.

    Function-local for the same reason ``rails.phase_material`` imports them
    that way: ``rails`` is imported by the flight runtime long before any
    carrier is chosen, and this family is the only thing in this module that
    needs the SLURP loader at all.
    """

    from ..data.slurp import (  # noqa: PLC0415 (cycle guard, and lazily paid)
        SlurpIntentSlots,
        SlurpIntentSlotSchema,
        render_slurp_intent_slot_schema,
    )

    return SlurpIntentSlots, SlurpIntentSlotSchema, render_slurp_intent_slot_schema


def slurp_blocks_from_schema(schema, intents: Sequence[str] | None = None):
    """A schema's own blocks as an ARTIFACT mapping.

    The inverse of :func:`slurp_candidate_schema`: it drops exactly what a
    candidate may not write (the counts and the shares) and keeps exactly what
    it may (the ordered type list and the fillers). This is how the incumbent
    ``A_r`` becomes the starting point of the two deterministic controls and
    of a round's own incumbent artifact.
    """

    requested = tuple(schema.intent_ids) if intents is None else tuple(intents)
    blocks: dict[str, dict[str, object]] = {}
    for intent in requested:
        profile = schema.intents.get(intent)
        if profile is None:
            raise ProposerError(f"schema has no block for intent {intent!r}")
        blocks[intent] = {
            "types": [
                {
                    "entity_type": entity_type,
                    "fillers": list(profile.fillers.get(entity_type, ())),
                }
                for entity_type, _count, _share in profile.types
            ]
        }
    return _checked_slurp_blocks(blocks, "blocks")


def slurp_candidate_schema(blocks: Mapping[str, object], *, unfloored, base):
    """The flyable schema a candidate's blocks name, with every number
    re-derived from TRAIN.

    ``unfloored`` is ``data.slurp.load_slurp_intent_slot_schema(...,
    min_share=0.0)`` -- the WHOLE TRAIN type table per intent, unfiltered --
    and it is the only authority for a type's count and share. ``base`` is
    ``A_0``, and every intent the candidate did not rewrite keeps its ``base``
    block byte for byte: preregistration section 5, "any intent the draw did
    not cover keeps its incumbent block unchanged", stated as code.

    Fail-closed on a listed type TRAIN never records for that intent -- there
    is no count to re-derive, so the block could not be rendered honestly.
    """

    SlurpIntentSlots, SlurpIntentSlotSchema, _render = _slurp_schema_types()
    checked = _checked_slurp_blocks(blocks, "blocks")
    unknown = sorted(set(checked) - set(base.intents))
    if unknown:
        raise ProposerError(f"candidate rewrites intents absent from A_0: {unknown}")
    profiles: dict[str, object] = {}
    for intent in sorted(base.intents):
        if intent not in checked:
            profiles[intent] = base.intents[intent]
            continue
        train = unfloored.intents.get(intent)
        if train is None:
            raise ProposerError(
                f"the unfloored TRAIN table has no profile for intent {intent!r}"
            )
        table = {
            entity_type: (count, share) for entity_type, count, share in train.types
        }
        types: list[tuple[str, int, float]] = []
        fillers: dict[str, tuple[str, ...]] = {}
        for entry in checked[intent]["types"]:
            entity_type = str(entry["entity_type"])
            measured = table.get(entity_type)
            if measured is None or measured[0] < 1:
                raise ProposerError(
                    f"intent {intent!r} lists entity type {entity_type!r}, which TRAIN "
                    "never records for it; a block may not name a type with no mention"
                )
            types.append((entity_type, measured[0], measured[1]))
            fillers[entity_type] = tuple(entry["fillers"])
        profiles[intent] = SlurpIntentSlots(
            intent=intent,
            n=train.n,
            mentions=train.mentions,
            types=tuple(types),
            fillers=fillers,
        )
    return SlurpIntentSlotSchema(
        schema_id=SLURP_EVOLVED_SCHEMA_ID,
        source_split=unfloored.source_split,
        source_identity_hash=unfloored.source_identity_hash,
        utterance_count=unfloored.utterance_count,
        min_share=base.min_share,
        examples_per_type=SLURP_MAX_FILLERS_PER_TYPE,
        intents=profiles,
    )


def slurp_block_texts(schema, intents: Sequence[str] | None = None) -> dict[str, str]:
    """``{intent: block text}`` through the ONE renderer, shared header removed.

    ``data.slurp.render_slurp_intent_slot_schema`` always emits its single
    shared header sentence first and then one block per requested intent; a
    BLOCK, in every sense this cell uses the word (the 494-to-1,224-character
    unit of preregistration section 3, the thing a proposer rewrites, the
    thing the token budget is relative to), is what follows that one line.
    Nothing here re-implements the grammar: a second renderer would be free to
    drift from the one the flight actually sends.
    """

    _slots, _schema_type, render = _slurp_schema_types()
    requested = tuple(schema.intent_ids) if intents is None else tuple(intents)
    texts: dict[str, str] = {}
    for intent in requested:
        rendered = render(schema, intents=(intent,))
        head, _, block = rendered.partition("\n")
        if not head or not block:
            raise ProposerError(f"the renderer produced no block for intent {intent!r}")
        texts[intent] = block
    return texts


def _slurp_fillers_of(blocks: Mapping[str, object]) -> list[str]:
    return [
        str(filler)
        for intent in sorted(blocks)
        for entry in blocks[intent]["types"]  # type: ignore[index]
        for filler in entry["fillers"]
    ]


def _illegal_filler_digests(
    fillers: Sequence[str],
    evaluation_digests: frozenset[str],
    legal_digests: frozenset[str],
) -> list[str]:
    """The word 6-gram DIGESTS a candidate's FILLERS share with the evaluation
    sentences and A_0 does not already carry.

    A_0's own 1,008 fillers are exempt because they are TRAIN and KC-S1b
    already sent every one of them; refusing them would refuse the incumbent
    itself (preregistration section 8).

    Digests rather than words, throughout: a shared 6-gram is by construction
    six words of a DEV-1000 sentence, and the row that opens that text
    (``SAEA-SLURP-MF-EVO-DECONTAMINATION-V1``) is registered on the promise
    that it never renders, logs or echoes it. Comparing digests keeps the
    refusal reportable without the report being the leak.
    """

    digests = _filler_digests(fillers)
    return sorted((digests & evaluation_digests) - legal_digests)


def _filler_digests(fillers: Sequence[str]) -> frozenset[str]:
    digests: set[str] = set()
    for filler in fillers:
        digests |= {ngram_digest(gram) for gram in word_ngrams(filler)}
    return frozenset(digests)


def _grams_of(texts: Sequence[str], label: str) -> set[tuple[str, ...]]:
    if isinstance(texts, (str, bytes)):
        raise ProposerError(f"{label} must be a sequence of texts")
    grams: set[tuple[str, ...]] = set()
    for item in texts:
        if not isinstance(item, str):
            raise ProposerError(f"every {label} entry must be text")
        grams |= word_ngrams(item)
    return grams


def _digests_of(texts: Sequence[str], label: str) -> frozenset[str]:
    """``_grams_of`` hashed -- one tokenizer, one notion of a shared 6-gram."""

    return frozenset(
        ngram_digest(gram) for gram in _grams_of(texts, label)
    )


def _checked_digests(digests: Sequence[str], label: str) -> frozenset[str]:
    if isinstance(digests, (str, bytes)) or not isinstance(digests, Sequence):
        raise ProposerError(f"{label} must be a sequence of sha256 hex digests")
    out: set[str] = set()
    for entry in digests:
        if not isinstance(entry, str) or not re.fullmatch(r"[0-9a-f]{64}", entry):
            raise ProposerError(f"every {label} entry must be a sha256 hex digest")
        out.add(entry)
    return frozenset(out)


def parse_slurp_schema_response(
    text: str,
    *,
    expected_intents: Sequence[str],
    allowed_entity_types: Sequence[str],
    refuse_ngrams: Sequence[str] = (),
) -> dict[str, dict[str, object]]:
    """Read a proposer's rewritten BLOCKS back into an artifact. Fail-closed.

    EVO-S1's output contract is the block grammar itself and not JSON
    (preregistration section 12.1 item P8): the artifact has to be
    reproducible byte for byte by ``render_slurp_intent_slot_schema``, and a
    JSON envelope would put a second, unrendered representation between the
    proposer and the flight.

    Refused, with the failed rule named and no repair attempted: any line that
    is neither the header shape nor the type shape; a blank line; trailing
    whitespace; non-ASCII anywhere; an entity type outside
    ``allowed_entity_types`` (the closed list the prompt showed); a repeated
    intent or a repeated type inside a block; more than
    :data:`SLURP_MAX_FILLERS_PER_TYPE` fillers on a line; a block with no type
    line; blocks in an order other than ``expected_intents``; and a filler
    carrying one of ``refuse_ngrams`` -- the devel word 6-grams the
    decontamination row supplies, already minus A_0's own.

    The header's counts and the type line's share ARE parsed and then
    DISCARDED: :func:`slurp_candidate_schema` re-derives both from the
    unfloored TRAIN table, so a hallucinated count or percentage cannot reach
    a flight even if the proposer writes one.
    """

    if isinstance(expected_intents, (str, bytes)):
        raise ProposerError("expected_intents must be a sequence of intent names")
    wanted = tuple(str(intent) for intent in expected_intents)
    if not wanted:
        raise ProposerError("expected_intents must be non-empty")
    if len(set(wanted)) != len(wanted):
        raise ProposerError("expected_intents contains a duplicate")
    if isinstance(allowed_entity_types, (str, bytes)):
        raise ProposerError("allowed_entity_types must be a sequence of type names")
    allowed = {str(name) for name in allowed_entity_types}
    if not allowed:
        raise ProposerError("allowed_entity_types must be non-empty")
    if not isinstance(text, str) or not text.strip():
        raise ProposerError("proposer response is empty")
    if not text.isascii():
        raise ProposerError("proposer response carries non-ASCII characters")

    blocks: dict[str, dict[str, object]] = {}
    order: list[str] = []
    current: str | None = None
    for number, line in enumerate(text.strip().split("\n"), start=1):
        if not line.strip():
            raise ProposerError(f"line {number} is blank; a block carries no blank line")
        if line != line.rstrip():
            raise ProposerError(f"line {number} carries trailing whitespace")
        header = _SLURP_BLOCK_HEADER_RE.fullmatch(line)
        if header is not None:
            current = header.group("intent")
            if current in blocks:
                raise ProposerError(f"the response opens a second block for {current!r}")
            blocks[current] = {"types": []}
            order.append(current)
            continue
        entry = _SLURP_TYPE_LINE_RE.fullmatch(line)
        if entry is None:
            raise ProposerError(
                f"line {number} is outside the block grammar: {line[:80]!r}"
            )
        if current is None:
            raise ProposerError(f"line {number} is a type line before any block header")
        entity_type = entry.group("entity_type")
        if entity_type not in allowed:
            raise ProposerError(
                f"line {number} names entity type {entity_type!r}, which is not one of "
                "the type names the instruction offered"
            )
        listed = blocks[current]["types"]
        if any(item["entity_type"] == entity_type for item in listed):  # type: ignore[index]
            raise ProposerError(
                f"block {current!r} lists entity type {entity_type!r} twice"
            )
        raw = entry.group("fillers")
        fillers = [] if raw == SLURP_NO_FILLER_SENTINEL else raw.split("; ")
        if len(fillers) > SLURP_MAX_FILLERS_PER_TYPE:
            raise ProposerError(
                f"block {current!r} type {entity_type!r} lists {len(fillers)} fillers, "
                f"over the {SLURP_MAX_FILLERS_PER_TYPE}-filler cap"
            )
        for filler in fillers:
            _checked_slurp_filler(filler, f"block {current!r} type {entity_type!r}")
        listed.append({"entity_type": entity_type, "fillers": fillers})  # type: ignore[union-attr]

    empty = sorted(intent for intent in blocks if not blocks[intent]["types"])
    if empty:
        raise ProposerError(f"block(s) {empty} carry no entity type line")
    if tuple(order) != wanted:
        raise ProposerError(
            f"the response carries blocks {order}, not exactly {list(wanted)} in that "
            "order"
        )
    parsed = _checked_slurp_blocks(blocks, "blocks")
    if refuse_ngrams:
        refused = frozenset(
            ngram_digest(tuple(str(gram).split())) for gram in refuse_ngrams
        )
        illegal = _illegal_filler_digests(
            _slurp_fillers_of(parsed), refused, frozenset()
        )
        if illegal:
            raise ProposerError(
                f"a filler carries {len(illegal)} refused word "
                f"{DECONTAMINATION_NGRAM}-gram(s): {illegal[:3]}"
            )
    return parsed


def render_slurp_proposer_instruction(
    incumbent_blocks: Mapping[str, str],
    *,
    intent_order: Sequence[str],
    entity_type_names: Sequence[str],
    exemplars: Sequence[Sequence[object]],
    line_caps: Mapping[str, int],
    scenario: str,
    round: int,
    k: int,
) -> str:
    """The text-only instruction that asks the frozen core for one scenario's
    rewritten blocks -- preregistration section 5, verbatim.

    ``exemplars`` are ``(sample_id, intent, utterance text, [(entity type,
    filler), ...])`` rows of the drawn construction sample, rendered GROUPED
    BY INTENT and, within an intent, in the caller's own drawn order. No
    sample id ever reaches the rendered bytes: ids group, order and seed the
    candidate id, and nothing else.

    One documented substitution decision. The verbatim rule reads "at most
    {L} type lines per block", but ``L`` is per INTENT (that intent's
    unfloored TRAIN type count) and a scenario owns up to nine intents. The
    rendered number is the scenario's LARGEST cap, so the instruction never
    understates what a block may carry, and the per-intent cap is enforced
    where it can be enforced honestly -- in
    :func:`validate_slurp_candidate_artifact`, against the TRAIN table, before
    anything flies.
    """

    if not isinstance(incumbent_blocks, Mapping) or not incumbent_blocks:
        raise ProposerError("incumbent_blocks must be a non-empty mapping")
    if isinstance(intent_order, (str, bytes)) or not intent_order:
        raise ProposerError("intent_order must be a non-empty sequence of intents")
    intents = tuple(str(intent) for intent in intent_order)
    if len(set(intents)) != len(intents):
        raise ProposerError("intent_order repeats an intent")
    if set(intents) != set(incumbent_blocks):
        raise ProposerError(
            f"incumbent_blocks must name exactly {sorted(intents)}; it names "
            f"{sorted(incumbent_blocks)}"
        )
    if isinstance(entity_type_names, (str, bytes)) or not entity_type_names:
        raise ProposerError("entity_type_names must be a non-empty sequence")
    if not isinstance(line_caps, Mapping) or set(line_caps) != set(intents):
        raise ProposerError(f"line_caps must name exactly {sorted(intents)}")
    for intent in intents:
        cap = line_caps[intent]
        if isinstance(cap, bool) or not isinstance(cap, int) or cap < 1:
            raise ProposerError(f"line_caps[{intent!r}] must be a positive integer")
    if not isinstance(scenario, str) or not scenario:
        raise ProposerError("scenario must be non-empty text")
    if isinstance(round, bool) or not isinstance(round, int) or round < 0:
        raise ProposerError("round must be a nonnegative integer")
    if isinstance(k, bool) or not isinstance(k, int) or k < 0:
        raise ProposerError("k must be a nonnegative integer")

    grouped: dict[str, list[tuple[str, tuple[tuple[str, str], ...]]]] = {
        intent: [] for intent in intents
    }
    for index, row in enumerate(exemplars):
        if isinstance(row, (str, bytes)) or len(tuple(row)) != 4:
            raise ProposerError(
                f"exemplar {index} must be a (sample_id, intent, text, entities) row"
            )
        sample_id, intent, said, entities = tuple(row)
        for name, value in (("sample_id", sample_id), ("intent", intent), ("text", said)):
            if not isinstance(value, str) or not value.strip():
                raise ProposerError(f"exemplar {index} {name} must be non-empty text")
        if intent not in grouped:
            raise ProposerError(
                f"exemplar {index} names intent {intent!r}, which is not one of this "
                f"scenario's intents {list(intents)}"
            )
        pairs: list[tuple[str, str]] = []
        for pair in entities:
            if isinstance(pair, (str, bytes)) or len(tuple(pair)) != 2:
                raise ProposerError(
                    f"exemplar {index} entities must be (entity type, filler) pairs"
                )
            entity_type, filler = (str(value) for value in tuple(pair))
            pairs.append((entity_type, filler))
        grouped[intent].append((said, tuple(pairs)))

    lines = [
        f"# scenario {scenario} | round {round} | variant {k}",
        "",
        "You are rewriting the slot-schema blocks a speech assistant is given before "
        "it extracts the",
        "entities of a spoken command. The assistant hears the command; it does not "
        "see any text.",
        "",
        "A block describes one intent: which entity types that intent draws its slots "
        "from, how much of",
        "the intent's slot mentions each type carries, and fillers heard with that type.",
        "",
        "## The blocks you are rewriting",
    ]
    for intent in intents:
        block = incumbent_blocks[intent]
        if not isinstance(block, str) or not block.strip():
            raise ProposerError(f"incumbent block for {intent!r} is empty")
        lines.append(block)
    lines.append("")
    lines.append("## Entity type names you may use")
    lines.append(", ".join(str(name) for name in entity_type_names))
    lines.append("")
    lines.append("## Example commands of this scenario, and the entities they carry")
    number = 0
    for intent in intents:
        for said, pairs in grouped[intent]:
            number += 1
            lines.append(f"{number}. intent: {intent}")
            lines.append(f"   said: {said}")
            rendered = "; ".join(
                f"{entity_type} = {filler}" for entity_type, filler in pairs
            )
            lines.append(f"   entities: {rendered or '(none)'}")
    if number == 0:
        raise ProposerError(
            "a proposer instruction with no exemplar has no grounding at all"
        )
    lines.extend(
        [
            "",
            "## Task",
            "First decide what a reader who has only these blocks would still get wrong "
            "on the examples",
            "above: a type the block never lists, a type it lists that this intent "
            "barely uses, or a filler",
            "written in a form nobody would say out loud.",
            "Then rewrite each block so that a reader who has only your block, and "
            "hears one of these",
            "commands, writes the entities the examples show.",
            "",
            "## Output",
            "Reply with the rewritten blocks and nothing else -- no prose before or "
            "after them, no code",
            "fence, no explanation. One block per intent, in the order the blocks were "
            "given, each in",
            "exactly this grammar:",
            "== {intent} == {n} TRAIN utterances, {m} slot mentions",
            "- {entity type} ({p} percent of slot mentions): {filler}; {filler}; {filler}",
            "Rules:",
            "- reproduce each header line exactly as it was given to you",
            "- every entity type name comes from the list above, and must be one this "
            "intent actually uses",
            f"- at most {max(int(line_caps[intent]) for intent in intents)} type lines "
            "per block, the most used type first",
            "- at most five fillers per type, lower case, written as they would be spoken",
            "- ASCII only; one line per type; no blank lines; no numbering",
            "- leave no blank line between one block and the next: the next block's "
            "== header line comes immediately after the previous block's last type "
            "line",
            "- never write anything that is not an entity type name or a filler",
            "- never write an identifier, a file name or a number that is not part of a "
            "filler",
        ]
    )
    return "\n".join(lines) + "\n"


def slurp_proposer_candidate(
    blocks: Mapping[str, object],
    *,
    target_id: str,
    round: int,
    k: int,
    proposer_prompt_sha256: str,
    exemplar_ids: Sequence[str],
) -> CandidateArtifact:
    """The frozen core's own rewrite, as :func:`parse_slurp_schema_response`
    returned it, bound to the prompt digest and the exemplar draw."""

    return _build(
        family="proposer",
        descriptions=blocks,
        cue=None,
        target_id=target_id,
        round=round,
        k=k,
        proposer_prompt_sha256=proposer_prompt_sha256,
        exemplar_ids=exemplar_ids,
        artifact_family=SLURP_SLOT_SCHEMA_FAMILY,
    )


def slurp_shares_only_candidate(
    incumbent_blocks: Mapping[str, object],
    *,
    target_id: str,
    round: int,
    k: int,
) -> CandidateArtifact:
    """F2, the CONTENT floor: the incumbent blocks with every filler deleted.

    Types, their order and their shares are untouched; only the filler lists
    go. Zero model contact. The KC-S1b verdict attributes its whole +8.55 to
    "which types this intent uses, WITH the fillers TRAIN heard for them", so
    a proposer that cannot beat a block with the fillers removed has learned
    nothing about fillers -- and section 9 names "the shares-only control
    within 0.5 pp of the proposer" a kill result.

    This is deliberately NOT the program's alternative F2 phrasing, "counts
    refreshed": A_0's counts ARE the current TRAIN counts, so that control
    would be byte-identical to the incumbent and would waste a slot.
    """

    checked = _checked_slurp_blocks(incumbent_blocks, "incumbent_blocks")
    blocks = {
        intent: {
            "types": [
                {"entity_type": entry["entity_type"], "fillers": []}
                for entry in checked[intent]["types"]
            ]
        }
        for intent in checked
    }
    return _build(
        family="deterministic",
        descriptions=blocks,
        cue=None,
        target_id=target_id,
        round=round,
        k=k,
        proposer_prompt_sha256=None,
        exemplar_ids=(),
        artifact_family=SLURP_SLOT_SCHEMA_FAMILY,
    )


def slurp_form_twin_candidate(
    incumbent_blocks: Mapping[str, object],
    *,
    unfloored,
    base,
    token_counter: Callable[[str], int],
    target_id: str,
    round: int,
    k: int,
    tolerance: int = 0,
    placeholders: Sequence[str] = SLURP_PLACEHOLDER_FILLERS,
) -> CandidateArtifact:
    """F3, the FORM floor: every filler replaced by a neutral placeholder, at
    the incumbent block's own token count.

    Deterministic, and a real difference from EVO-A1, whose placebo spends one
    contact per target: here the twin is a string transformation priced on the
    flight tokenizer, so ``K_1 = 5`` costs 54 proposer contacts and not 90.

    The construction, per intent: replace the fillers of each type with
    ``placeholders`` position by position, keeping the type list, its order
    and the number of fillers per type exactly as the incumbent has them;
    then, while the rendered block is under the incumbent's token count,
    extend one placeholder by one more ``placeholders[0]`` word, cycling over
    the (type, filler) positions in rendered order, so the padding never lands
    all on one line. A block whose plain placeholders ALREADY exceed the
    incumbent's count cannot be matched downward without deleting a filler --
    which would change the block's shape and make it a second shares-only
    control -- so it is refused rather than approximated.

    ``tolerance`` is the per-block token slack the caller accepts; it is 0 by
    default because the padding unit is one word and a subword tokenizer
    prices ``" item"`` at one token, so exactness is normally reachable. A
    flight that finds otherwise raises it deliberately and reports it.
    """

    if not callable(token_counter):
        raise ProposerError("token_counter must be callable")
    if isinstance(tolerance, bool) or not isinstance(tolerance, int) or tolerance < 0:
        raise ProposerError("tolerance must be a nonnegative integer")
    if isinstance(placeholders, (str, bytes)) or not placeholders:
        raise ProposerError("placeholders must be a non-empty sequence of words")
    words = tuple(str(word) for word in placeholders)
    for word in words:
        _checked_slurp_filler(word, "placeholders")
    if len(set(words)) != len(words):
        raise ProposerError("placeholders repeats a word; a type's fillers are distinct")
    pad = words[0]
    checked = _checked_slurp_blocks(incumbent_blocks, "incumbent_blocks")
    incumbent_texts = slurp_block_texts(
        slurp_candidate_schema(checked, unfloored=unfloored, base=base),
        intents=tuple(sorted(checked)),
    )

    blocks: dict[str, dict[str, object]] = {}
    for intent in sorted(checked):
        target_tokens = _slurp_tokens(token_counter, incumbent_texts[intent])
        positions: list[tuple[int, int]] = []
        types: list[dict[str, object]] = []
        for type_index, entry in enumerate(checked[intent]["types"]):
            if len(entry["fillers"]) > len(words):
                raise ProposerError(
                    f"intent {intent!r} type {entry['entity_type']!r} carries "
                    f"{len(entry['fillers'])} fillers but only {len(words)} distinct "
                    "placeholders were supplied"
                )
            fillers = [words[index] for index in range(len(entry["fillers"]))]
            for filler_index in range(len(fillers)):
                positions.append((type_index, filler_index))
            types.append({"entity_type": entry["entity_type"], "fillers": fillers})
        if not positions:
            raise ProposerError(
                f"intent {intent!r} has no filler to match on; a form twin of a block "
                "with no filler would be the shares-only control"
            )
        blocks[intent] = {"types": types}
        step = 0
        while True:
            rendered = slurp_block_texts(
                slurp_candidate_schema(
                    {intent: blocks[intent]}, unfloored=unfloored, base=base
                ),
                intents=(intent,),
            )[intent]
            tokens = _slurp_tokens(token_counter, rendered)
            if abs(tokens - target_tokens) <= tolerance:
                break
            if tokens > target_tokens:
                raise ProposerError(
                    f"the form twin of intent {intent!r} is {tokens} tokens against the "
                    f"incumbent's {target_tokens}; a shorter twin would have to delete a "
                    "filler, which would make it the shares-only control"
                )
            type_index, filler_index = positions[step % len(positions)]
            fillers = blocks[intent]["types"][type_index]["fillers"]  # type: ignore[index]
            fillers[filler_index] = f"{fillers[filler_index]} {pad}"
            step += 1
    return _build(
        family="placebo",
        descriptions=blocks,
        cue=None,
        target_id=target_id,
        round=round,
        k=k,
        proposer_prompt_sha256=None,
        exemplar_ids=(),
        artifact_family=SLURP_SLOT_SCHEMA_FAMILY,
    )


def _slurp_tokens(token_counter: Callable[[str], int], text: str) -> int:
    tokens = token_counter(text)
    if isinstance(tokens, bool) or not isinstance(tokens, int) or tokens < 0:
        raise ProposerError("token_counter must return a nonnegative integer")
    return tokens


def validate_slurp_candidate_artifact(
    candidate: CandidateArtifact,
    *,
    unfloored,
    base,
    incumbent_blocks: Mapping[str, str],
    token_counter: Callable[[str], int],
    token_counter_id: str = SERVING_TOKENIZER_ID,
    evaluation_sentence_texts: Sequence[str] = (),
    evaluation_ngram_digests: Sequence[str] = (),
    baseline_filler_texts: Sequence[str] = (),
    exemplar_texts: Sequence[str] = (),
    allow_estimator: bool = False,
) -> CandidateValidation:
    """Every EVO-S1 form and decontamination gate, in one fail-closed pass.

    Form (preregistration section 5, "Other form caps"):

    * the block RENDERS, which is what proves the candidate is reproducible
      byte for byte from the committed TRAIN table plus its own choices;
    * the header line is byte-identical to the incumbent's -- guaranteed by
      construction, since it is re-rendered from TRAIN, and asserted anyway;
    * at most ``1 + L`` lines per intent, ``L`` = that intent's UNFLOORED
      TRAIN type count;
    * at most :data:`SLURP_MAX_FILLERS_PER_TYPE` fillers per type, ASCII,
      lower case;
    * every listed type carries at least one TRAIN mention for that intent
      (:func:`slurp_candidate_schema` refuses otherwise);
    * the block within ``+20 %`` tokens of the INCUMBENT block, measured
      through ``token_counter``. This is a budget on the SEARCH, not a gate on
      the claim: it exists so a round cannot buy its gain with prompt volume
      alone, and the measured delta is reported per intent either way.

    ``token_counter_id`` names the authority. A registered candidate is priced
    on :data:`SERVING_TOKENIZER_ID` -- the resident server's own ``/tokenize``
    -- and any other id, a character-length estimator above all, is refused
    unless ``allow_estimator=True``. KC-A1 died four tokens over a forty-token
    cap because its builder injected a chars-per-token ratio as its counter.

    Decontamination (preregistration section 8): no sample identifier in a
    filler; no word 6-gram shared between a FILLER and the evaluation
    sentences unless that 6-gram already occurs in ``baseline_filler_texts``
    (A_0's own 1,008 fillers, which are TRAIN and were already sent by
    KC-S1b); overlap with ``exemplar_texts`` COUNTED and reported, never
    gated.

    The evaluation side arrives by EITHER of two routes, and their union is
    what the gate compares against. ``evaluation_sentence_texts`` are raw
    sentences, which only a caller that is itself registered to open them may
    supply; ``evaluation_ngram_digests`` is the committed artifact's digest
    set (:func:`load_evaluation_ngram_digests`), which is how a FLIGHT reaches
    this gate. The flight route exists because
    ``SAEA-SLURP-MF-EVO-DECONTAMINATION-V1`` is the one row licensed to read
    SLURP devel sentence text, and a per-round candidate validation is not
    that row: it consumes the row's hash-pinned product instead, so no devel
    text is opened, held or written a second time.
    """

    candidate.validate()
    if candidate.artifact_family != SLURP_SLOT_SCHEMA_FAMILY:
        raise ProposerError(
            f"candidate {candidate.candidate_id} is a {candidate.artifact_family!r} "
            f"artifact, not a {SLURP_SLOT_SCHEMA_FAMILY!r} one"
        )
    if not callable(token_counter):
        raise ProposerError("token_counter must be callable")
    if not isinstance(token_counter_id, str) or not token_counter_id:
        raise ProposerError("token_counter_id must be non-empty text")
    if token_counter_id != SERVING_TOKENIZER_ID and not allow_estimator:
        raise ProposerError(
            f"token_counter_id {token_counter_id!r} is not the serving geometry's own "
            f"tokenizer ({SERVING_TOKENIZER_ID!r}); a candidate that only an estimator "
            "admits is refused"
        )
    if not isinstance(incumbent_blocks, Mapping) or not incumbent_blocks:
        raise ProposerError("incumbent_blocks must be a non-empty mapping")
    missing = sorted(set(candidate.descriptions) - set(incumbent_blocks))
    if missing:
        raise ProposerError(f"no incumbent block supplied for intent(s) {missing}")

    schema = slurp_candidate_schema(
        candidate.descriptions, unfloored=unfloored, base=base
    )
    intents = tuple(sorted(candidate.descriptions))
    rendered = slurp_block_texts(schema, intents=intents)

    per_key: list[dict[str, object]] = []
    for intent in intents:
        block = rendered[intent]
        incumbent = incumbent_blocks[intent]
        if not isinstance(incumbent, str) or not incumbent.strip():
            raise ProposerError(f"incumbent block for {intent!r} is empty")
        if block.split("\n", 1)[0] != incumbent.split("\n", 1)[0]:
            raise ProposerError(
                f"intent {intent!r} header line is not byte-identical to the "
                "incumbent's"
            )
        train = unfloored.intents.get(intent)
        if train is None:
            raise ProposerError(f"the unfloored TRAIN table has no {intent!r} profile")
        cap = 1 + len(train.types)
        lines = block.split("\n")
        if len(lines) > cap:
            raise ProposerError(
                f"intent {intent!r} block is {len(lines)} lines, over the {cap}-line cap "
                f"(one header plus {len(train.types)} unfloored TRAIN type rows)"
            )
        for entry in candidate.descriptions[intent]["types"]:  # type: ignore[index]
            if len(entry["fillers"]) > SLURP_MAX_FILLERS_PER_TYPE:
                raise ProposerError(
                    f"intent {intent!r} type {entry['entity_type']!r} lists "
                    f"{len(entry['fillers'])} fillers, over the "
                    f"{SLURP_MAX_FILLERS_PER_TYPE}-filler cap"
                )
        tokens = _slurp_tokens(token_counter, block)
        incumbent_tokens = _slurp_tokens(token_counter, incumbent)
        budget = int(incumbent_tokens * (1.0 + SLURP_RELATIVE_TOKEN_BUDGET))
        if tokens > budget:
            raise ProposerError(
                f"intent {intent!r} block is {tokens} tokens against the incumbent's "
                f"{incumbent_tokens}, over the {budget}-token relative budget "
                f"(+{SLURP_RELATIVE_TOKEN_BUDGET:.0%})"
            )
        per_key.append(
            {
                "intent": intent,
                "lines": len(lines),
                "line_cap": cap,
                "characters": len(block),
                "tokens": tokens,
                "incumbent_tokens": incumbent_tokens,
                "token_delta": tokens - incumbent_tokens,
                "token_budget": budget,
                "types": len(lines) - 1,
            }
        )

    fillers = _slurp_fillers_of(candidate.descriptions)
    for filler in fillers:
        if _carries_sample_identifier(filler):
            raise ProposerError(
                f"filler {filler!r} carries what looks like a sample identifier"
            )
    evaluation_digests = _digests_of(
        evaluation_sentence_texts, "evaluation_sentence_texts"
    ) | _checked_digests(evaluation_ngram_digests, "evaluation_ngram_digests")
    legal_digests = _digests_of(baseline_filler_texts, "baseline_filler_texts")
    illegal = _illegal_filler_digests(fillers, evaluation_digests, legal_digests)
    if illegal:
        raise ProposerError(
            f"candidate fillers share {len(illegal)} word {DECONTAMINATION_NGRAM}-gram(s) "
            f"with the evaluation sentences that A_0's own fillers do not carry; "
            f"digest(s) {illegal[:3]}"
        )
    exemplar_grams = _grams_of(exemplar_texts, "exemplar_texts")
    candidate_grams: set[tuple[str, ...]] = set()
    for filler in fillers:
        candidate_grams |= word_ngrams(filler)
    overlap = sorted(" ".join(gram) for gram in candidate_grams & exemplar_grams)

    whole = "\n".join(rendered[intent] for intent in intents)
    return CandidateValidation(
        candidate_id=candidate.candidate_id,
        rendered_sha256=hashlib.sha256(whole.encode("utf-8")).hexdigest(),
        rendered_lines=sum(int(record["lines"]) for record in per_key),
        rendered_tokens=sum(int(record["tokens"]) for record in per_key),
        token_budget=sum(int(record["token_budget"]) for record in per_key),
        max_description_chars=max(int(record["characters"]) for record in per_key),
        exemplar_overlap_count=len(overlap),
        exemplar_overlap_ngrams=tuple(overlap),
        artifact_family=SLURP_SLOT_SCHEMA_FAMILY,
        token_counter_id=token_counter_id,
        per_key=tuple(per_key),
    )


# ---------------------------------------------------------------------------
# The null-rewrite form gate (track E3e, 2026-09-07)
# ---------------------------------------------------------------------------
#
# EVO-S1 round 1 admitted `social` on a candidate whose rendered block IS the
# incumbent's: the proposer returned A_0's own `social_post` block verbatim,
# the guard checked that a candidate EXISTED rather than that it DIFFERED, and
# the round spent one of two admissions on an arm that is byte-identical to
# the incumbent on the wire. Sixty of the confirmation's rows were therefore
# pure decoder noise. A rendering that equals the incumbent's is not a
# rewrite, and this gate says so before the candidate can reach a portfolio.


#: The name a null-rewrite refusal records, in ``reason`` and in ``gate``.
NULL_REWRITE_GATE = "null-rewrite"

#: Schema of one recorded check, which a candidates receipt carries per
#: candidate whether or not it refused.
NULL_REWRITE_SCHEMA = "saea-evolution-null-rewrite-check-v1"


def rendered_artifact_sha256(
    descriptions: Mapping[str, object],
    *,
    artifact_family: str = A2T_DESCRIPTIONS_FAMILY,
    registry_rows: Sequence[Mapping[str, str]] = (),
    base: object = None,
    unfloored: object = None,
) -> str:
    """The digest of what ONE artifact mapping renders to, over its own keys.

    The same bytes both validators already measure as
    :attr:`CandidateValidation.rendered_sha256`, factored out so that the two
    sides of the null-rewrite gate are rendered by ONE code path: a candidate
    compared against an incumbent rendered by a second renderer would be
    comparing two spellings, not two artifacts.

    ``a2t-descriptions``: the whole compact registry with these descriptions
    substituted. ``slurp-slot-schema``: this mapping's own blocks, in sorted
    intent order, joined by newlines, with every count and share re-derived
    from the unfloored TRAIN table -- so ``base`` and ``unfloored`` are
    required and an estimated block is impossible.
    """

    if artifact_family == SLURP_SLOT_SCHEMA_FAMILY:
        blocks = _checked_slurp_blocks(descriptions, "blocks")
        if base is None or unfloored is None:
            raise ProposerError(
                "a slurp-slot-schema rendering needs A_0 (base) and the unfloored "
                "TRAIN table"
            )
        intents = tuple(sorted(blocks))
        texts = slurp_block_texts(
            slurp_candidate_schema(blocks, unfloored=unfloored, base=base),
            intents=intents,
        )
        whole = "\n".join(texts[intent] for intent in intents)
    elif artifact_family == A2T_DESCRIPTIONS_FAMILY:
        overrides = _checked_descriptions(descriptions, "descriptions")
        whole = render_registry_compact_rows(
            list(registry_rows), description_overrides=dict(overrides)
        )
    else:
        raise ProposerError(f"artifact_family must be one of {ARTIFACT_FAMILIES}")
    return hashlib.sha256(whole.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class NullRewriteCheck:
    """What one candidate renders to, beside what the incumbent renders to
    over exactly the same artifact keys."""

    candidate_id: str
    target_id: str
    artifact_family: str
    keys: tuple[str, ...]
    candidate_rendered_sha256: str
    incumbent_rendered_sha256: str

    @property
    def null_rewrite(self) -> bool:
        return self.candidate_rendered_sha256 == self.incumbent_rendered_sha256

    @property
    def reason(self) -> str:
        """The refusal text, which names the gate first so a receipt can be
        filtered on it without parsing English."""

        return (
            f"{NULL_REWRITE_GATE}: this candidate renders byte-identically to the "
            f"incumbent's own artifact for target {self.target_id!r} over "
            f"{list(self.keys)} (sha256 {self.incumbent_rendered_sha256}); it is not "
            "a rewrite and never flies"
        )

    def as_json(self) -> dict[str, object]:
        return {
            "schema": NULL_REWRITE_SCHEMA,
            "gate": NULL_REWRITE_GATE,
            "candidate_id": self.candidate_id,
            "target_id": self.target_id,
            "artifact_family": self.artifact_family,
            "keys": list(self.keys),
            "candidate_rendered_sha256": self.candidate_rendered_sha256,
            "incumbent_rendered_sha256": self.incumbent_rendered_sha256,
            "null_rewrite": self.null_rewrite,
        }


def null_rewrite_check(
    candidate: CandidateArtifact,
    incumbent_artifact: Mapping[str, object],
    *,
    registry_rows: Sequence[Mapping[str, str]] = (),
    base: object = None,
    unfloored: object = None,
) -> NullRewriteCheck:
    """Render ``candidate`` and the incumbent over the candidate's OWN keys,
    and report whether the two renderings are the same bytes.

    ``incumbent_artifact`` is ``A_r`` in the candidate's own family --
    ``{tool: description}`` for ``a2t-descriptions``, ``{intent: block}`` for
    ``slurp-slot-schema`` -- and must cover every key the candidate rewrote.
    It is restricted to those keys here, because a candidate that touched two
    intents of a nine-intent scenario is a null rewrite exactly when those two
    are unchanged, whatever the other seven say.

    Fail-closed: a candidate whose blocks cannot be rendered raises, and the
    caller records that as the refusal it is. Nothing here decides anything --
    :func:`rails.evolution.run_candidates_step` owns the refusal.
    """

    candidate.validate()
    if not isinstance(incumbent_artifact, Mapping):
        raise ProposerError("incumbent_artifact must be a mapping")
    missing = sorted(set(candidate.descriptions) - set(incumbent_artifact))
    if missing:
        raise ProposerError(
            f"the incumbent artifact carries no entry for {missing}, which this "
            "candidate rewrites; a null-rewrite check needs both sides"
        )
    keys = tuple(sorted(candidate.descriptions))
    incumbent = {key: incumbent_artifact[key] for key in keys}
    render = {
        "artifact_family": candidate.artifact_family,
        "registry_rows": registry_rows,
        "base": base,
        "unfloored": unfloored,
    }
    return NullRewriteCheck(
        candidate_id=candidate.candidate_id,
        target_id=candidate.target_id,
        artifact_family=candidate.artifact_family,
        keys=keys,
        candidate_rendered_sha256=rendered_artifact_sha256(
            candidate.descriptions, **render
        ),
        incumbent_rendered_sha256=rendered_artifact_sha256(incumbent, **render),
    )
