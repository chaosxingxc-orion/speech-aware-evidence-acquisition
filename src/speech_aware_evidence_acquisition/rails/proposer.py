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

FAMILIES = ("proposer", "deterministic", "placebo")

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
    "MAX_DESCRIPTION_CHARS",
    "TOKEN_HEADROOM",
    "REGISTRY_LINE_COUNT",
    "DECONTAMINATION_NGRAM",
    "FAMILIES",
    "ROW_FIELDS",
    "ProposerError",
    "CandidateArtifact",
    "CandidateValidation",
    "candidate_bytes",
    "candidate_id_for",
    "candidate_text",
    "derive_target_id",
    "deterministic_candidate",
    "parse_proposer_response",
    "prompt_sha256",
    "placebo_candidate",
    "proposer_candidate",
    "render_placebo_instruction",
    "render_proposer_instruction",
    "validate_candidate_artifact",
    "word_ngrams",
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
    ``setAlarm``) -- the Audio2Tool gold format the official parser reads."""

    head = gold_call.split("(", 1)[0].strip()
    if not head:
        raise ProposerError(f"gold call {gold_call!r} names no tool")
    return head


# ---------------------------------------------------------------------------
# The candidate artifact
# ---------------------------------------------------------------------------


def candidate_text(descriptions: Mapping[str, str], cue: str | None) -> str:
    """The candidate's own canonical text -- the thing its id hashes.

    Deliberately NOT the rendered 152-line block: the block is a function of
    the whole registry, which is fixed, so hashing it would make every
    candidate id depend on registry bytes that never change while hiding what
    actually differs. This is the cue line followed by one
    ``"{tool}: {description}"`` line per targeted tool in name order.
    """

    checked = _checked_descriptions(descriptions, "descriptions")
    if cue is not None and (not isinstance(cue, str) or not cue.strip()):
        raise ProposerError("cue must be non-empty text or None")
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
    """One target's proposed description overrides for one round and slot."""

    candidate_id: str
    family: str
    target_id: str
    round: int
    k: int
    descriptions: Mapping[str, str]
    cue: str | None
    proposer_prompt_sha256: str | None
    exemplar_ids: tuple[str, ...]

    @property
    def text(self) -> str:
        return candidate_text(self.descriptions, self.cue)

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
        if self.family == "proposer" and (
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
    descriptions: Mapping[str, str],
    cue: str | None,
    target_id: str,
    round: int,
    k: int,
    proposer_prompt_sha256: str | None,
    exemplar_ids: Sequence[str],
) -> CandidateArtifact:
    checked = _checked_descriptions(descriptions, "descriptions")
    ids = tuple(exemplar_ids)
    text = candidate_text(checked, cue)
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

    def as_json(self) -> dict[str, object]:
        return {
            "schema": VALIDATION_SCHEMA,
            "candidate_id": self.candidate_id,
            "rendered_sha256": self.rendered_sha256,
            "rendered_lines": self.rendered_lines,
            "rendered_tokens": self.rendered_tokens,
            "token_budget": self.token_budget,
            "max_description_chars": self.max_description_chars,
            "exemplar_overlap_count": self.exemplar_overlap_count,
            "exemplar_overlap_ngrams": list(self.exemplar_overlap_ngrams),
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
        if _SAMPLE_ID_RE.search(text) or _BARE_SIX_DIGIT_RE.search(text):
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
