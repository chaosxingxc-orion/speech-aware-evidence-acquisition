"""The Earnings-22 PRE-MEETING BRIEF: the corpus's OWN metadata table, rendered
as labelled fact lines, plus its deranged form twin.

KC-E2 (``docs/readiness/2026-09-07-e22-kc-e2-pre-meeting-brief-v1-preregistration.
md``) needs, for the Earnings-22 short-form DEV clips, the same thing
``core.class_lists`` builds for Earnings-21: what a participant holds BEFORE the
call, and nothing distilled from the answer. Earnings-22 ships no ConEC context
files this repository can read (``data.carriers.EARNINGS22_ORIGINAL`` declares
``evidence=None``: the ConEC Earnings-22 side is per-call PDF packets, binary,
with no D1 layer). What it does ship is its own metadata table, and this module
builds a brief from that table and from nothing else.

WHAT THE TABLE ACTUALLY CARRIES, COUNTED
----------------------------------------
``<earnings22 asset root>/metadata.csv``, 125 data rows, eight columns::

    File ID,Ticker Symbol,Country by Ticker,UN Defined,Major Dialect Family,
    Language Family + Area Based,File Length (seconds),Sampling Rate (Hz)

Five of those eight are call facts a participant would hold in advance -- the
ticker, the country, the UN region, the dialect family and the language family.
The remaining three are the sample id and two recording properties (length,
sampling rate), which say nothing about the call's content and are NOT rendered.

**The table carries no company name.** The owner ruling of 2026-09-07 forbids
bringing one in from outside: Earnings-22 must not collect any external
information, or the resulting numbers stop being comparable with the academic
references this study aligns against. There is therefore exactly ONE brief
variant, built from the corpus's own metadata file, hash-pinned in the composed
config, and a company-name lookup table is neither built nor registered.

WHAT IS NEVER READ
------------------
No reference transcript, no ESB reference sentence, no ``.nlp`` file, no
force-aligned reference, no speaker list, no HALAS or annotation overlay, no
segment table, no roster's gold column and no other call's audio. The metadata
table is the only file this module can name, and
``tests/unit/test_metadata_brief.py`` proves it by refusing the renderer any
filesystem access at all: every entry point takes TEXT.

WHY THE SOURCE UNIT IS A ROW, NOT THE FILE
------------------------------------------
``core.evidence_derivation``'s transform signature is ``(text, params)`` and
carries no sample id, and ``core.evidence.resolve_declared_transform_params``
resolves params from the composed config alone -- so a per-call transform can
never be told which call it is rendering through either seam. The source unit is
therefore the call's OWN two-line slice of the table (the header line, verbatim,
plus that call's data line, verbatim): a deterministic, literally-quoted excerpt
of the pinned file whose sha256 is what ``DerivedEvidenceRecord.source_sha256``
records, so re-invoking the pinned transform on the same slice reproduces the
same brief byte for byte.

The WHOLE file's identity is not dropped for that: it is pinned by path and
sha256 in the composed config (:data:`BRIEF_SOURCE_KEY`, the same two-field pin
``core.class_lists.validate_pad_plan_pin`` uses for the E21 pad plan and
``core.instructions.render_evolved_registry`` uses for an evolved registry), and
:func:`resolve_brief_source_pin` is what every reader goes through, so a table
edited after the fragment was written is refused rather than silently flown.

CARRIER-BOUND IS FALSE, AND THAT IS THE HONEST ANSWER
-----------------------------------------------------
``DerivedEvidenceRecord.carrier_bound`` is ``False`` here, for the reason
``distractor-only-bias-list`` and ``derived-candidates`` already state for
themselves: D1 records this table's 125 sample IDS
(``data.identity.earnings22_layers``'s ``file_metadata`` layer, built by
``_csv_layer``) and deliberately records NO per-file manifest for it, because a
CSV layer has no per-sample files to hash. There is therefore no D1-recorded
per-sample evidence identity for this source to be checked against, the
evidence-identity rail is not entitled to pretend otherwise, and identity rests
on this record's own re-derived chain plus the composed config's byte pin on the
table. See the preregistration's "why this cell carries no D1 evidence
supplement" for the two structural reasons a supplement cannot be written here.

THE FORM TWIN IS ANOTHER CALL'S BRIEF, NOT A PLACEHOLDER
---------------------------------------------------------
``core.class_lists``' twin replaces every entry token with a neutral
placeholder. That is the right control for a brief whose entries are dozens of
proper nouns. It is the WRONG control for a five-line table of country and
dialect names: "Country: item" does not read as a country, so the twin would
vary the content AND the plausibility of the content at once.

The twin here is therefore the DERANGEMENT twin the E5 brief already names as an
alternative -- "the same shape with names from OTHER calls" -- made explicit and
deterministic: each call is paired with the NEXT call in sorted order, cyclically
(:func:`derange_calls`), so the twin is a real, well-formed Earnings-22 brief of
a real Earnings-22 call that is never the call being decoded. Same labels, same
field set, same kind of value in every field, zero information about this call.
Ten calls give a shift-by-one permutation with no fixed point.

The pairing is not recomputed at flight time from whatever call set happens to be
loaded: it is a hash-pinned artifact under ``configs/knowledge/``
(:data:`DERANGEMENT_KEY`), so a roster change can never silently re-pair the
control.

TOKEN MATCHING (owner ruling, 2026-09-06)
------------------------------------------
A control is locked to its treatment on the FLIGHT tokenizer, not on characters
or whitespace. "United States" and "South Africa" do not cost the same number of
tokens, so the deranged twin is padded, line by line, until each of its rendered
PREFIXES measures its own brief line's -- through
``core.class_lists.placebo_pad_repeats``/``pad_placebo``, i.e. the SAME padder
KU-E1c uses, reached through the same ``token_counter`` seam, never a second
implementation. The measurement is taken once against a resident server by
``scripts/e22_kc_e2_prompt_fit.py`` and materialised as a hash-pinned pad plan;
the flight replays it and needs no tokenizer of its own.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Mapping, Sequence

from ..e0.artifacts import REPO_ROOT
from .base import EvidenceError
from .class_lists import (
    MAX_PAD_REPEATS_PER_LINE,
    PLACEBO_PAD_FILLER,
    annotate_normalized,
    pad_placebo,
    validate_pad_repeats,
)
from .evidence_derivation import TRANSFORMS

#: The metadata columns the brief renders, in render order, paired with the
#: label each becomes. Column names are the table's own, verbatim; a table whose
#: header does not carry one of them is refused rather than rendered short.
BRIEF_FIELDS: tuple[tuple[str, str], ...] = (
    ("Ticker Symbol", "Ticker symbol"),
    ("Country by Ticker", "Country"),
    ("UN Defined", "UN region"),
    ("Major Dialect Family", "Major dialect family"),
    ("Language Family + Area Based", "Language family and area"),
)

#: The table's id column, the only other column this module names. ``File
#: Length (seconds)`` and ``Sampling Rate (Hz)`` are deliberately absent from
#: :data:`BRIEF_FIELDS`: they are recording properties, not call facts, and a
#: brief that recited them would be telling the core about the WAV rather than
#: about the meeting.
ID_COLUMN = "File ID"

PROVENANCE = (
    "the call's own row of the Earnings-22 corpus metadata table as published "
    "with the benchmark (metadata.csv: ticker, country, UN region, dialect "
    "family, language family). No transcript content, no external lookup, and "
    "no company name -- the table carries none and none is brought in."
)

BRIEF_HEADING = "Pre-meeting brief for this earnings call -- " + PROVENANCE

#: The composed-config key pinning the metadata TABLE by path and sha256. The
#: path is relative to the controlled DATA root (the table lives outside Git
#: under ``SPEECHRL_DATA_DIR``), which is the one difference from
#: ``core.class_lists.PLACEBO_PAD_PLAN_KEY``'s ``configs/``-rooted pin.
BRIEF_SOURCE_KEY = "evidence_brief_source"
#: The composed-config key pinning the call PAIRING of the form twin, by path
#: and sha256, under ``configs/``.
DERANGEMENT_KEY = "evidence_brief_derangement"
#: The composed-config key pinning the twin's measured per-line pad plan, by
#: path and sha256, under ``configs/``.
PAD_PLAN_KEY = "evidence_brief_pad_plan"

DERANGEMENT_SCHEMA = "saea-e22-brief-derangement-v1"
PAD_PLAN_SCHEMA = "saea-e22-brief-placebo-token-match-v1"

_SHA256_HEX = re.compile(r"[0-9a-f]{64}")
_DATA_RELPATH = re.compile(r"[A-Za-z0-9._][A-Za-z0-9._/-]*")
_CALL_ID = re.compile(r"[0-9A-Za-z_]+")


class MetadataBriefError(EvidenceError):
    """The Earnings-22 metadata table could not be rendered as a brief."""


# ---------------------------------------------------------------------------
# Reading the table
# ---------------------------------------------------------------------------


def metadata_header_and_rows(text: str) -> tuple[str, dict[str, str]]:
    """``(header line, {call id -> that call's data line})``, both VERBATIM.

    The lines are kept as they appear so a rendered brief's source slice is a
    literal quotation of the pinned file rather than a re-serialization that
    could drift from it. Parsing is only used to find the id column and to key
    the rows; nothing is rewritten.
    """

    if not isinstance(text, str):
        raise MetadataBriefError(
            f"the Earnings-22 metadata table must be text, got {type(text).__name__}"
        )
    lines = text.splitlines()
    if len(lines) < 2:
        raise MetadataBriefError(
            "the Earnings-22 metadata table needs a header line and at least one row"
        )
    header = lines[0]
    reader = csv.DictReader(io.StringIO(text))
    fieldnames = list(reader.fieldnames or ())
    missing = [
        column
        for column in (ID_COLUMN, *(name for name, _ in BRIEF_FIELDS))
        if column not in fieldnames
    ]
    if missing:
        raise MetadataBriefError(
            f"the Earnings-22 metadata table is missing column(s) {missing}; refusing "
            "to render a brief from a table whose shape is not the one this module "
            "was written against"
        )
    rows: dict[str, str] = {}
    for offset, row in enumerate(reader):
        call_id = str(row.get(ID_COLUMN) or "").strip()
        if not call_id:
            raise MetadataBriefError(
                f"the Earnings-22 metadata table has a blank {ID_COLUMN!r} on data row "
                f"{offset + 1}"
            )
        if call_id in rows:
            raise MetadataBriefError(
                f"the Earnings-22 metadata table names call {call_id!r} twice"
            )
        line = lines[offset + 1] if offset + 1 < len(lines) else ""
        if not line.strip():
            raise MetadataBriefError(
                f"the Earnings-22 metadata table's data row {offset + 1} does not "
                "occupy one physical line; an embedded newline would make the source "
                "slice ambiguous and is refused"
            )
        rows[call_id] = line
    if not rows:
        raise MetadataBriefError("the Earnings-22 metadata table carries no data rows")
    return header, rows


def call_source_slice(text: str, call_id: str) -> str:
    """One call's SOURCE SLICE: the header line and that call's data line, joined
    by a single newline. This is the exact text a brief transform is invoked on
    and whose sha256 the derivation record carries."""

    header, rows = metadata_header_and_rows(text)
    line = rows.get(str(call_id))
    if line is None:
        raise MetadataBriefError(
            f"the Earnings-22 metadata table has no row for call {call_id!r}"
        )
    return f"{header}\n{line}"


def _slice_fields(slice_text: str) -> dict[str, str]:
    """The five brief fields of a two-line source slice, refusing anything else."""

    if not isinstance(slice_text, str):
        raise MetadataBriefError(
            f"a metadata source slice must be text, got {type(slice_text).__name__}"
        )
    lines = slice_text.splitlines()
    if len(lines) != 2 or "\n".join(lines) != slice_text:
        raise MetadataBriefError(
            "a metadata source slice must be exactly two lines (the header and one "
            "data row) with no trailing newline; a slice that does not round-trip "
            "through splitlines() can never be re-derived"
        )
    reader = csv.DictReader(io.StringIO(slice_text))
    rows = list(reader)
    if len(rows) != 1:
        raise MetadataBriefError(
            f"a metadata source slice must parse to exactly one row, got {len(rows)}"
        )
    row = rows[0]
    values: dict[str, str] = {}
    for column, label in BRIEF_FIELDS:
        if column not in row:
            raise MetadataBriefError(
                f"the metadata source slice carries no {column!r} column"
            )
        value = str(row[column] or "").strip()
        if not value:
            raise MetadataBriefError(
                f"the metadata source slice carries an empty {column!r}; a brief line "
                "is never emitted blank and a partial brief is never guessed at"
            )
        values[label] = value
    call_id = str(row.get(ID_COLUMN) or "").strip()
    if not call_id:
        raise MetadataBriefError("the metadata source slice carries no File ID")
    values[ID_COLUMN] = call_id
    return values


def call_id_of_slice(slice_text: str) -> str:
    """The call the source slice belongs to -- used by the pad-plan and
    derangement audits, never by the render path (which needs no id)."""

    return _slice_fields(slice_text)[ID_COLUMN]


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def render_brief(slice_text: str) -> str:
    """The pre-meeting brief for one call, from that call's source slice.

    One heading line carrying the provenance sentence, then one ``Label: value``
    line per field of :data:`BRIEF_FIELDS`, each value annotated with its
    Whisper-normalized form where casing or punctuation moves it -- the SAME
    ``core.class_lists.annotate_normalized`` the Earnings-21 brief uses, so the
    two carriers tell the core about the measurement's spelling in one voice
    rather than two.
    """

    values = _slice_fields(slice_text)
    lines = [BRIEF_HEADING]
    for _, label in BRIEF_FIELDS:
        lines.append(f"{label}: {annotate_normalized(values[label])}")
    return "\n".join(lines)


def brief_terms(slice_text: str) -> dict[str, str]:
    """``{label -> raw value}`` for one call -- the brief's TERMS, unannotated.

    The audit's brief-term recall metric needs the values without the
    ``[normalized: ...]`` annotation (the annotation is a spelling aid for the
    core, never a term a speaker utters), so it reads them here rather than
    parsing them back out of the rendered brief.
    """

    values = _slice_fields(slice_text)
    return {label: values[label] for _, label in BRIEF_FIELDS}


# ---------------------------------------------------------------------------
# The derangement
# ---------------------------------------------------------------------------


def derange_calls(call_ids: Sequence[str]) -> dict[str, str]:
    """``{call -> the call whose brief twins it}``: sorted order, shift by one,
    cyclic. Deterministic, involution-free and fixed-point-free for any set of
    two or more distinct calls, and refused outright below two -- a "twin" that
    is the call itself is not a control.

    The same construction ``core.evidence.rotated_mismatch`` applies at the
    SAMPLE level, applied here at the CALL level instead: the Earnings-22 dev
    clips come 150 to a call, so a sample-level rotation would hand almost every
    clip its own call's brief back.
    """

    ordered = sorted({str(call_id) for call_id in call_ids})
    if len(ordered) != len(list(call_ids)):
        raise MetadataBriefError(
            "the derangement's call list repeats a call; a call can be twinned once"
        )
    if len(ordered) < 2:
        raise MetadataBriefError(
            "a derangement needs at least two calls; with one call the twin would be "
            "the call itself"
        )
    return {call: ordered[(index + 1) % len(ordered)] for index, call in enumerate(ordered)}


def validate_derangement(mapping: object) -> dict[str, str]:
    """Fail-closed derangement validation: a non-empty call -> call bijection
    with no fixed point."""

    if not isinstance(mapping, Mapping) or not mapping:
        raise MetadataBriefError("a derangement must be a non-empty call -> call mapping")
    checked: dict[str, str] = {}
    for key, value in mapping.items():
        if not isinstance(key, str) or _CALL_ID.fullmatch(key) is None:
            raise MetadataBriefError(f"derangement key {key!r} is not a call id")
        if not isinstance(value, str) or _CALL_ID.fullmatch(value) is None:
            raise MetadataBriefError(f"derangement value {value!r} is not a call id")
        if key == value:
            raise MetadataBriefError(
                f"the derangement maps call {key!r} to itself; a twin that is the call "
                "it twins carries the call's own information and is not a control"
            )
        checked[key] = value
    if len(set(checked.values())) != len(checked):
        raise MetadataBriefError(
            "the derangement is not a bijection: two calls share one twin, so a pad "
            "plan keyed by the twin's source bytes could never be unambiguous"
        )
    return checked


# ---------------------------------------------------------------------------
# Pinned artifacts
# ---------------------------------------------------------------------------


def _validate_pin(values: Mapping[str, object] | None, key: str, *, under: str) -> tuple[str, str]:
    """``(relpath, sha256)`` out of a composed config's two-field pin."""

    if not isinstance(values, Mapping):
        raise MetadataBriefError(
            f"the {key} pin needs a composed config to read from; there is no default "
            "and deliberately no fallback"
        )
    pin = values.get(key)
    if not isinstance(pin, Mapping) or set(pin) != {"artifact_relpath", "artifact_sha256"}:
        raise MetadataBriefError(
            f"{key} must be an object with exactly 'artifact_relpath' and "
            "'artifact_sha256'"
        )
    relpath = pin["artifact_relpath"]
    digest = pin["artifact_sha256"]
    if not isinstance(relpath, str) or _DATA_RELPATH.fullmatch(relpath) is None:
        raise MetadataBriefError(
            f"{key} artifact_relpath {relpath!r} is not a plain relative path "
            "(no absolute paths, no backslashes)"
        )
    if ".." in relpath.split("/"):
        raise MetadataBriefError(f"{key} artifact_relpath {relpath!r} escapes its root")
    if not relpath.startswith(under):
        raise MetadataBriefError(
            f"{key} artifact_relpath {relpath!r} is not under {under!r}"
        )
    if not isinstance(digest, str) or _SHA256_HEX.fullmatch(digest) is None:
        raise MetadataBriefError(
            f"{key} artifact_sha256 {digest!r} is not a 64-character sha256 hex digest"
        )
    return relpath, digest


def resolve_brief_source_pin(values: Mapping[str, object] | None) -> tuple[str, str]:
    """The metadata table's ``(data-root relpath, sha256)``. The path must sit
    under ``datasets/`` -- the controlled corpus tree -- so a fragment can never
    point this source at a derived or hand-written table."""

    return _validate_pin(values, BRIEF_SOURCE_KEY, under="datasets/")


@lru_cache(maxsize=8)
def _load_pinned_json(relpath: str, sha256_hex: str, repo_root: str, schema: str) -> Mapping[str, object]:
    path = Path(repo_root) / relpath
    if not path.is_file():
        raise MetadataBriefError(f"pinned artifact missing: {path}")
    try:
        blob = path.read_bytes()
    except OSError as error:
        raise MetadataBriefError(f"cannot read pinned artifact {path}: {error}") from error
    measured = hashlib.sha256(blob).hexdigest()
    if measured != sha256_hex:
        raise MetadataBriefError(
            f"pinned artifact {path} hashes to {measured}, not the configured "
            f"{sha256_hex}; an artifact edited after its fragment was written is "
            "refused rather than silently flown"
        )
    try:
        document = json.loads(blob.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise MetadataBriefError(f"pinned artifact {path} is not UTF-8 JSON: {error}") from error
    if not isinstance(document, Mapping) or document.get("schema") != schema:
        raise MetadataBriefError(f"pinned artifact {path} does not declare schema {schema!r}")
    return document


def resolve_derangement_params(
    values: Mapping[str, object] | None, *, repo_root: Path | str | None = None
) -> dict[str, object]:
    """The deranged twin's declared params: the metadata pin plus the pinned
    call pairing, resolved from THIS run's own composed config and the bytes it
    pins. Returned to the two callers that must agree exactly -- the evidence
    source that applies them and ``core.evidence.resolve_declared_transform_
    params``, which the driver uses to re-verify the derivation record."""

    metadata_relpath, metadata_sha256 = resolve_brief_source_pin(values)
    relpath, digest = _validate_pin(values, DERANGEMENT_KEY, under="configs/")
    root = Path(repo_root) if repo_root is not None else REPO_ROOT
    document = _load_pinned_json(relpath, digest, str(root), DERANGEMENT_SCHEMA)
    mapping = validate_derangement(document.get("derangement"))
    return {
        "metadata_relpath": metadata_relpath,
        "metadata_sha256": metadata_sha256,
        "derangement_artifact_relpath": relpath,
        "derangement_artifact_sha256": digest,
        "derangement": dict(sorted(mapping.items())),
    }


def resolve_token_matched_params(
    values: Mapping[str, object] | None, *, repo_root: Path | str | None = None
) -> dict[str, object]:
    """The token-matched twin's declared params: :func:`resolve_derangement_params`
    plus the measured per-line pad plan, keyed by the SOURCE SLICE's sha256 --
    exactly the key ``DerivedEvidenceRecord.source_sha256`` carries, so a plan
    entry is bound to the bytes the chain already proves. The derangement is a
    bijection, so each twin slice is a plan key at most once."""

    params = resolve_derangement_params(values, repo_root=repo_root)
    relpath, digest = _validate_pin(values, PAD_PLAN_KEY, under="configs/")
    root = Path(repo_root) if repo_root is not None else REPO_ROOT
    document = _load_pinned_json(relpath, digest, str(root), PAD_PLAN_SCHEMA)
    entries = document.get("entries")
    if isinstance(entries, (str, bytes)) or not isinstance(entries, Sequence) or not entries:
        raise MetadataBriefError(f"pad-plan artifact {relpath} carries no 'entries' list")
    line_pad_repeats: dict[str, list[int]] = {}
    for index, entry in enumerate(entries):
        if not isinstance(entry, Mapping):
            raise MetadataBriefError(f"pad-plan {relpath} entry {index} is not an object")
        key = entry.get("source_sha256")
        if not isinstance(key, str) or _SHA256_HEX.fullmatch(key) is None:
            raise MetadataBriefError(
                f"pad-plan {relpath} entry {index} carries no source_sha256"
            )
        if key in line_pad_repeats:
            raise MetadataBriefError(
                f"pad-plan {relpath} names source bytes {key[:12]}... twice; two plans "
                "for one source can never both be the plan"
            )
        repeats = entry.get("pad_repeats")
        if isinstance(repeats, (str, bytes)) or not isinstance(repeats, Sequence):
            raise MetadataBriefError(
                f"pad-plan {relpath} entry {index} carries no pad_repeats list"
            )
        line_pad_repeats[key] = validate_pad_repeats(repeats, len(list(repeats)))
    params.update(
        {
            "pad_artifact_relpath": relpath,
            "pad_artifact_sha256": digest,
            "line_pad_repeats": line_pad_repeats,
        }
    )
    return params


# ---------------------------------------------------------------------------
# Registered transforms (core.evidence_derivation.TRANSFORMS)
# ---------------------------------------------------------------------------


def e22_metadata_brief_content(text: str, params: Mapping[str, object]) -> str:
    """TRANSFORMS: ``e22-metadata-brief`` v1 -- the arm's own brief, rendered
    from the call's two-line source slice. ``params`` carries the pinned table's
    path and digest so ``params_hash`` records WHICH table the slice was cut
    from; the render itself is a pure function of the slice."""

    _require_metadata_pin(params, "e22-metadata-brief")
    return render_brief(text)


def e22_metadata_brief_deranged_content(text: str, params: Mapping[str, object]) -> str:
    """TRANSFORMS: ``e22-metadata-brief-deranged`` v1 -- the UNPADDED form twin.

    Identical to the arm's transform: the twin is a real brief, and what makes
    it a twin is WHICH call's slice the evidence source feeds it (the pinned
    derangement's partner, never this call). Keeping the render shared is the
    point -- the twin can never drift into a different shape from the arm,
    because there is one renderer.
    """

    _require_derangement_params(params, "e22-metadata-brief-deranged")
    return render_brief(text)


def e22_metadata_brief_deranged_tm_content(text: str, params: Mapping[str, object]) -> str:
    """TRANSFORMS: ``e22-metadata-brief-deranged-tm`` v1 -- the token-matched
    form twin: the deranged brief with its measured per-line pad plan replayed
    through ``core.class_lists.pad_placebo``. No tokenizer, no I/O: line ``i``
    grows by ``pad_repeats[i]`` whole ``" item"`` repeats and by nothing else."""

    transform = "e22-metadata-brief-deranged-tm"
    _require_derangement_params(params, transform)
    base = render_brief(text)
    return pad_placebo(base, _pad_repeats_for_source(text, params, transform))


def _require_metadata_pin(params: Mapping[str, object], transform: str) -> None:
    if not isinstance(params, Mapping):
        raise MetadataBriefError(
            f"{transform} transform params must be a mapping, got {type(params).__name__}"
        )
    relpath = params.get("metadata_relpath")
    digest = params.get("metadata_sha256")
    if not isinstance(relpath, str) or not relpath.startswith("datasets/"):
        raise MetadataBriefError(
            f"{transform}: the declared params carry no pinned metadata_relpath"
        )
    if not isinstance(digest, str) or _SHA256_HEX.fullmatch(digest) is None:
        raise MetadataBriefError(
            f"{transform}: the declared params carry no pinned metadata_sha256"
        )


def _require_derangement_params(params: Mapping[str, object], transform: str) -> None:
    _require_metadata_pin(params, transform)
    try:
        validate_derangement(params.get("derangement"))
    except MetadataBriefError as error:
        raise MetadataBriefError(f"{transform}: {error}") from error


def _pad_repeats_for_source(
    text: str, params: Mapping[str, object], transform: str
) -> list[int]:
    plan = params.get("line_pad_repeats") if isinstance(params, Mapping) else None
    if not isinstance(plan, Mapping) or not plan:
        raise MetadataBriefError(
            f"{transform}: the declared params carry no pad plan; a token-matched twin "
            "is never rendered unpadded"
        )
    key = hashlib.sha256(text.encode("utf-8")).hexdigest()
    repeats = plan.get(key)
    if repeats is None:
        raise MetadataBriefError(
            f"{transform}: the pad plan has no entry for source bytes {key[:12]}...; a "
            "twin can never be token-matched to a call the plan never measured"
        )
    return list(repeats)


TRANSFORMS.register("e22-metadata-brief", "v1", e22_metadata_brief_content)
TRANSFORMS.register("e22-metadata-brief-deranged", "v1", e22_metadata_brief_deranged_content)
TRANSFORMS.register(
    "e22-metadata-brief-deranged-tm", "v1", e22_metadata_brief_deranged_tm_content
)

#: The arm's own transform. Its declared params are the metadata pin alone.
METADATA_BRIEF_TRANSFORMS = ("e22-metadata-brief",)
#: The unpadded twin's transform: metadata pin PLUS the pinned derangement.
METADATA_BRIEF_DERANGED_TRANSFORMS = ("e22-metadata-brief-deranged",)
#: The token-matched twin's transform: the above PLUS the pinned pad plan.
METADATA_BRIEF_TOKEN_MATCHED_TRANSFORMS = ("e22-metadata-brief-deranged-tm",)

__all__ = [
    "BRIEF_FIELDS",
    "BRIEF_HEADING",
    "BRIEF_SOURCE_KEY",
    "DERANGEMENT_KEY",
    "DERANGEMENT_SCHEMA",
    "ID_COLUMN",
    "MAX_PAD_REPEATS_PER_LINE",
    "METADATA_BRIEF_DERANGED_TRANSFORMS",
    "METADATA_BRIEF_TOKEN_MATCHED_TRANSFORMS",
    "METADATA_BRIEF_TRANSFORMS",
    "MetadataBriefError",
    "PAD_PLAN_KEY",
    "PAD_PLAN_SCHEMA",
    "PLACEBO_PAD_FILLER",
    "PROVENANCE",
    "brief_terms",
    "call_id_of_slice",
    "call_source_slice",
    "derange_calls",
    "metadata_header_and_rows",
    "render_brief",
    "resolve_brief_source_pin",
    "resolve_derangement_params",
    "resolve_token_matched_params",
    "validate_derangement",
]
