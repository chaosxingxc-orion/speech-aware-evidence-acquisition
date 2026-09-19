"""E14: the construction-data SCENARIO HINTS view and its bounded selection.

Owner directive 26 of 2026-09-18 ("analyses into nodes"): an offline analysis
this program trusts belongs INSIDE an agent node rather than only in a report.
Cell B8c is the third instance of family B8 and the second read-side one --
the A3 per-scenario confusion pairs placed at the SOLVER boundary as declared
context. This module is the ANALYSIS half of it: the pinned table the block is
rendered from, and the bounded, deterministic selection a harness (never a
model) makes against one row's Perception candidate list.

Design: ``docs/superpowers/specs/2026-09-17-node-context-policy-design.md``
section 16 (the B8c row and the boundary that makes it legal) and section
16.2 (B8c as built). Evidence base:
``docs/results/2026-09-17-slurp-a3-coverage-confusion-audit-v1.md`` (T3: 158
distinct gold -> delivered error pairs over 1,080 rows, the top 30 covering
43.7 % of the errors).

THE BOUNDARY, and it is the whole licence for this node:

* A3's own confusion pairs were computed on the EVALUATED rows' gold. They
  are a diagnostic ceiling and they stay one: nothing derived from them
  enters this table. The table re-derives its neighbours from the
  CONSTRUCTION POOL alone -- the governed SLURP TRAIN split minus every
  utterance with a recording in TRAIN Fold A, Fold B or DEV-1000 (the
  2026-09-13 exclusion), the same 9,354 utterances the E12 slot-audit view
  and the M1 exemplar pool bind.
* The neighbour rule is a k-nearest-neighbour LEAKAGE rate over the sealed
  construction text facet vectors, leave-one-out inside the pool: for each
  construction utterance of intent ``i`` its ``k`` nearest pool neighbours
  are read, and the share of those neighbours carrying intent ``j`` is the
  leakage of ``i`` into ``j``. No gold of an evaluated row is read, keyed on
  or conditioned upon, at build time or at runtime.
* The cue words are per (intent, neighbour) pair: the content words most
  over-represented in the intent's own construction utterances relative to
  the neighbour's, by log-odds with a ``+1`` prior on document frequencies,
  stopwords removed, minimum document count :data:`CUE_MIN_ROWS`. They are
  CONSTRUCTION text, which is knowledge this program may supply, and they
  carry no utterance id, no recording and no gold span.
* Rendering the block makes ZERO contacts of any kind -- no model, tokenizer,
  encoder, scorer, tool, server or network. It is a pure function of the
  Perception candidate list of this row, the pinned table and the declared
  bounds.
* The block is applied to EVERY row unconditionally. It is never gated on
  whether it helps, which is the same discipline E4 imposed on A1's
  ``R_action`` for exactly the same reason.

The table is released under ``SPEECHRL_DATA_DIR`` as
``knowledge/slurp/semantic/scenario-hints-v1/``, beside the released intent
boundaries and slot contracts, rather than committed like the E12 slot-audit
table: unlike that table, which carries counts and shares only, this one
carries construction WORDS, and construction text lives under the controlled
data root in this program. Its pin is therefore a declared sha256 over the
released bytes, checked on every binding, and a build receipt carries the
same hashes into the repository.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

#: The registered identity of this view; the value a fragment's
#: ``native_episode.solver_hints.view`` must carry.
SCENARIO_HINTS_VIEW_ID = "scenario-hints-v1"

#: Document schemas of the three released files.
SCENARIO_HINTS_RELEASE_SCHEMA = "saea-scenario-hints-release-v1"
SCENARIO_HINTS_VIEW_SCHEMA = "saea-scenario-hints-view-v1"
SCENARIO_HINTS_COMPLETION_SCHEMA = "saea-scenario-hints-completion-v1"

#: The per-contact receipt block ``rails.node_context_policy`` seals beside the
#: boundary's own ``saea-node-context-policy-v1`` row.
SCENARIO_HINTS_RECEIPT_SCHEMA = "saea-solver-scenario-hints-v1"

#: The builder that produced the released table
#: (``scripts/build_slurp_scenario_hints_view.py``).
SCENARIO_HINTS_BUILDER_POLICY_ID = "saea-scenario-hints-construction-confusion-v1"

# -- the derivation rule, committed in code and mirrored in the snapshot ----
#
# Every one of these is part of the view's IDENTITY, not a runtime knob: a
# different value is a different view id, because the table it produces is a
# different analysis. The runtime may only narrow what is RENDERED, through
# :class:`ScenarioHintsBounds`.

#: The neighbourhood size the leakage rate is measured over, leave-one-out.
NEIGHBOUR_K = 10
#: The floor a (intent, neighbour) leakage share must reach to be tabled.
NEIGHBOUR_MIN_LEAKAGE_SHARE = 0.05
#: The most neighbours the TABLE keeps per intent.
NEIGHBOUR_LIMIT = 3
#: The most cue words the TABLE keeps per (intent, neighbour) pair.
CUE_LIMIT = 3
#: A cue word must occur in at least this many of the intent's own
#: construction rows (document frequency, never a token count).
CUE_MIN_ROWS = 3
#: The additive prior of the log-odds score, on both sides of both ratios.
CUE_PRIOR = 1

#: The most Perception candidates the rendered block covers. It is a property
#: of the BLOCK, not of the table, which is why it is a module constant and
#: not a config field: a cell that widens it is a different block.
SCENARIO_HINTS_MAX_CANDIDATES = 3

#: Decimal places a stored share or score keeps. The FILTERS always run on the
#: exact integer ratio (or the exact float score); only the recorded number is
#: rounded, exactly as ``rails.slot_audit`` does for its own shares.
_SHARE_DIGITS = 6

#: What counts as a word at all: an alphabetic token of at least two
#: characters, an internal apostrophe allowed. Everything else -- a digit, a
#: punctuation mark, a single letter -- is not a cue candidate.
_WORD_PATTERN = re.compile(r"^[a-z][a-z']*$")
_WORD_MIN_LENGTH = 2

#: The closed English stopword list cue selection removes, committed here so
#: the rule is auditable offline and identical on every machine. It is a plain
#: function-word list and deliberately carries no task vocabulary: the view's
#: identity would otherwise depend on a judgement about which SLURP words are
#: "interesting", which is exactly the kind of fitting section 16 forbids.
STOPWORDS: frozenset[str] = frozenset({
    "a", "about", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can", "could", "did", "do",
    "does", "doing", "down", "during", "each", "few", "for", "from",
    "further", "had", "has", "have", "having", "he", "her", "here", "hers",
    "herself", "him", "himself", "his", "how", "i", "if", "in", "into", "is",
    "it", "its", "itself", "just", "me", "more", "most", "my", "myself",
    "no", "nor", "not", "now", "of", "off", "on", "once", "only", "or",
    "other", "our", "ours", "ourselves", "out", "over", "own", "please",
    "same", "she", "should", "so", "some", "such", "than", "that", "the",
    "their", "theirs", "them", "themselves", "then", "there", "these",
    "they", "this", "those", "through", "to", "too", "under", "until", "up",
    "very", "was", "we", "were", "what", "when", "where", "which", "while",
    "who", "whom", "why", "will", "with", "would", "you", "your", "yours",
    "yourself", "yourselves",
})

#: The bound names a fragment may declare, their defaults and their ceilings.
#: A bound may only NARROW what the table already holds, never widen it.
SCENARIO_HINTS_BOUND_KEYS: tuple[str, ...] = ("max_cues", "max_neighbours")
SCENARIO_HINTS_BOUND_CEILINGS: Mapping[str, int] = {
    "max_neighbours": NEIGHBOUR_LIMIT,
    "max_cues": CUE_LIMIT,
}
SCENARIO_HINTS_DEFAULT_BOUNDS: Mapping[str, int] = {
    "max_neighbours": NEIGHBOUR_LIMIT,
    "max_cues": CUE_LIMIT,
}

#: The two closed English phrases the block may emit beside table values. They
#: are the scenario-hints half of the policy's own closed vocabulary, so the
#: "adds no information" property test over this block stays a finite check.
NO_CUES = "(no cue word reaches the count floor)"
NO_NEIGHBOUR = "(no construction neighbour reaches the leakage floor)"
SCENARIO_HINTS_VOCABULARY: tuple[str, ...] = (NO_CUES, NO_NEIGHBOUR)

_PIN_KEYS = frozenset({"relpath", "root", "sha256"})
#: The released view lives under the controlled data root, never in the
#: repository: it carries construction WORDS.
PIN_ROOT = "data"
#: Every pinned file must sit inside this namespace.
PIN_NAMESPACE = "knowledge/slurp/semantic/"


class ScenarioHintsError(ValueError):
    """A scenario-hints table, pin, bound or selection input is invalid."""


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _share(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, _SHARE_DIGITS)


def render_leakage(leaked: int, of_neighbours: int) -> str:
    """``"6.4 % (60 of 940 nearest neighbours)"`` -- the one rendering of a
    leakage rate.

    Integer-exact: the percentage is formatted from the integer ratio and the
    counts travel beside it, so a reader can re-derive the number and no float
    ever crosses a platform boundary unrounded.
    """

    if of_neighbours <= 0:
        return f"0.0 % (0 of {of_neighbours} nearest neighbours)"
    return (
        f"{100.0 * leaked / of_neighbours:.1f} % "
        f"({leaked} of {of_neighbours} nearest neighbours)"
    )


def render_cues(cues: Sequence[str]) -> str:
    """The cue list as one comma-separated line, or the closed empty phrase."""

    words = [str(word) for word in cues]
    if not words:
        return NO_CUES
    return ", ".join(words)


def is_cue_candidate(word: str) -> bool:
    """Whether a lower-cased token may be a cue at all.

    Character classes and a closed stopword list, nothing else -- a harness
    predicate, never a model's opinion about what is interesting.
    """

    if not isinstance(word, str):
        raise ScenarioHintsError("a construction token must be text")
    if len(word) < _WORD_MIN_LENGTH:
        return False
    if word in STOPWORDS:
        return False
    return _WORD_PATTERN.fullmatch(word) is not None


def cue_log_odds(
    rows: int, intent_rows: int, neighbour_rows: int, neighbour_intent_rows: int,
) -> float:
    """The ``+1``-prior log-odds of one word between two intents.

    ``rows`` / ``neighbour_rows`` are DOCUMENT frequencies -- how many of the
    intent's construction utterances contain the word at least once -- so a
    word repeated inside one utterance cannot inflate its own score.
    """

    for name, value in (
        ("rows", rows),
        ("intent_rows", intent_rows),
        ("neighbour_rows", neighbour_rows),
        ("neighbour_intent_rows", neighbour_intent_rows),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ScenarioHintsError(f"cue log-odds {name} must be a count")
    if rows > intent_rows or neighbour_rows > neighbour_intent_rows:
        raise ScenarioHintsError(
            "a cue's document frequency cannot exceed its intent's row count"
        )
    left = math.log(
        (rows + CUE_PRIOR) / (intent_rows - rows + CUE_PRIOR)
    )
    right = math.log(
        (neighbour_rows + CUE_PRIOR)
        / (neighbour_intent_rows - neighbour_rows + CUE_PRIOR)
    )
    return left - right


@dataclass(frozen=True)
class ScenarioHintsBounds:
    """The declared render bounds, validated and canonically ordered."""

    max_cues: int
    max_neighbours: int

    def as_json(self) -> dict[str, int]:
        return {
            "max_candidates": SCENARIO_HINTS_MAX_CANDIDATES,
            "max_cues": self.max_cues,
            "max_neighbours": self.max_neighbours,
        }


def scenario_hints_bounds(declared: Mapping[str, object] | None = None) -> ScenarioHintsBounds:
    """Resolve declared bounds, or the registered defaults.

    Fail-closed: an unknown key, a non-integer, a boolean, a negative value
    and a value above the table's own ceiling are each refused by name, before
    any contact. A bound may only NARROW the released table.
    """

    values = dict(SCENARIO_HINTS_DEFAULT_BOUNDS)
    if declared is not None:
        if not isinstance(declared, Mapping):
            raise ScenarioHintsError("solver_hints bounds must be an object")
        unknown = sorted(set(declared) - set(SCENARIO_HINTS_BOUND_KEYS))
        if unknown:
            raise ScenarioHintsError(
                f"solver_hints carries unknown bound(s) {unknown}; the declared set "
                f"is {list(SCENARIO_HINTS_BOUND_KEYS)}"
            )
        for name, value in declared.items():
            if isinstance(value, bool) or not isinstance(value, int):
                raise ScenarioHintsError(f"solver_hints.{name} must be an integer")
            ceiling = SCENARIO_HINTS_BOUND_CEILINGS[name]
            if not 0 <= value <= ceiling:
                raise ScenarioHintsError(
                    f"solver_hints.{name} must lie in [0, {ceiling}]; the released "
                    "table holds no more than that and a bound may only narrow it"
                )
            values[name] = int(value)
    return ScenarioHintsBounds(**values)


@dataclass(frozen=True)
class ScenarioHintCue:
    """One discriminating construction word of an (intent, neighbour) pair."""

    word: str
    rows: int
    neighbour_rows: int
    log_odds: float

    def as_json(self) -> dict[str, object]:
        return {
            "word": self.word,
            "rows": self.rows,
            "neighbour_rows": self.neighbour_rows,
            "log_odds": self.log_odds,
        }


@dataclass(frozen=True)
class ScenarioHintNeighbour:
    """One intent's confusion neighbour, as the table stores it."""

    intent: str
    leaked: int
    of_neighbours: int
    cues: tuple[ScenarioHintCue, ...]

    @property
    def leakage_share(self) -> float:
        return _share(self.leaked, self.of_neighbours)

    def as_json(self) -> dict[str, object]:
        return {
            "intent": self.intent,
            "leaked": self.leaked,
            "of_neighbours": self.of_neighbours,
            "leakage_share": self.leakage_share,
            "cues": [cue.as_json() for cue in self.cues],
        }


@dataclass(frozen=True)
class ScenarioHintProfile:
    """One intent's construction confusion profile."""

    intent: str
    rows: int
    #: Most leaked first, ties by neighbour id. At most
    #: :data:`NEIGHBOUR_LIMIT`, every one at or above the leakage floor.
    neighbours: tuple[ScenarioHintNeighbour, ...]

    def as_json(self) -> dict[str, object]:
        return {
            "intent": self.intent,
            "rows": self.rows,
            "neighbours": [
                neighbour.as_json() for neighbour in self.neighbours
            ],
        }


@dataclass(frozen=True)
class ScenarioHintsTable:
    """The released, pinned construction table the Solver block renders."""

    view_id: str
    builder_policy_id: str
    source_split: str
    source_split_identity_hash: str
    construction_utterance_count: int
    neighbour_k: int
    min_leakage_share: float
    intents: Mapping[str, ScenarioHintProfile]
    release_sha256: str
    snapshot_sha256: str

    @property
    def intent_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self.intents))

    def profile(self, intent_id: str) -> ScenarioHintProfile | None:
        return self.intents.get(intent_id)

    def content_hash(self) -> str:
        """Canonical-JSON sha256 of the table's own content, independent of
        the released files' byte framing."""

        return _sha256_bytes(
            json.dumps(
                {
                    "view_id": self.view_id,
                    "builder_policy_id": self.builder_policy_id,
                    "source_split": self.source_split,
                    "source_split_identity_hash": self.source_split_identity_hash,
                    "construction_utterance_count": self.construction_utterance_count,
                    "neighbour_k": self.neighbour_k,
                    "min_leakage_share": self.min_leakage_share,
                    "intents": [
                        self.intents[intent].as_json() for intent in self.intent_ids
                    ],
                },
                sort_keys=True,
                ensure_ascii=False,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        )

    def pins(self) -> dict[str, str]:
        return {
            "release_sha256": self.release_sha256,
            "snapshot_sha256": self.snapshot_sha256,
            "table_content_hash": self.content_hash(),
        }


@dataclass(frozen=True)
class ScenarioHintLine:
    """One rendered neighbour line: a pair and its bounded cue list."""

    intent: str
    neighbour: str
    leaked: int
    of_neighbours: int
    cues: tuple[str, ...]

    @property
    def leakage(self) -> str:
        return render_leakage(self.leaked, self.of_neighbours)

    def as_json(self) -> dict[str, object]:
        return {
            "intent": self.intent,
            "neighbour": self.neighbour,
            "leaked": self.leaked,
            "of_neighbours": self.of_neighbours,
            "cues": list(self.cues),
        }


@dataclass(frozen=True)
class ScenarioHint:
    """One candidate's bounded hint: its row count and its neighbour lines."""

    intent: str
    rows: int
    lines: tuple[ScenarioHintLine, ...]

    def as_json(self) -> dict[str, object]:
        return {
            "intent": self.intent,
            "rows": self.rows,
            "neighbours": [line.as_json() for line in self.lines],
        }


def _pin(value: object, *, field_name: str) -> Mapping[str, str]:
    if (
        not isinstance(value, Mapping)
        or set(value) != _PIN_KEYS
        or not isinstance(value["relpath"], str)
        or not isinstance(value["root"], str)
        or not isinstance(value["sha256"], str)
    ):
        raise ScenarioHintsError(
            f"{field_name} must be a pin declaring exactly relpath, root and sha256"
        )
    relpath = value["relpath"]
    root = value["root"]
    digest = value["sha256"]
    if root != PIN_ROOT:
        raise ScenarioHintsError(
            f"{field_name}.root must be {PIN_ROOT!r}; the released scenario-hints "
            "view lives under the controlled data root"
        )
    if (
        not relpath.startswith(PIN_NAMESPACE)
        or relpath.startswith("/")
        or "\\" in relpath
        or ".." in Path(relpath).parts
    ):
        raise ScenarioHintsError(
            f"{field_name}.relpath must be a plain relative POSIX path under "
            f"{PIN_NAMESPACE}"
        )
    if len(digest) != 64 or any(
        character not in "0123456789abcdef" for character in digest
    ):
        raise ScenarioHintsError(f"{field_name}.sha256 must be a lower-case sha256")
    return {"relpath": relpath, "root": root, "sha256": digest}


def validate_scenario_hints_pin(
    value: object, *, field_name: str,
) -> Mapping[str, str]:
    """The one pin validator, public because the config loader checks a pin's
    SHAPE before any released file needs to exist -- so a fragment can be
    validated, and its hash composed, on a machine with no data root."""

    return _pin(value, field_name=field_name)


def _read_pinned(data_root: Path, pin: Mapping[str, str], *, field_name: str) -> object:
    root = Path(data_root).resolve()
    path = (root / pin["relpath"]).resolve()
    try:
        path.relative_to(root)
    except ValueError:
        raise ScenarioHintsError(f"{field_name} escapes the data root") from None
    if not path.is_file():
        raise ScenarioHintsError(f"{field_name} names no file: {path}")
    raw = path.read_bytes()
    measured = _sha256_bytes(raw)
    if measured != pin["sha256"]:
        raise ScenarioHintsError(
            f"{field_name} hashes to {measured}, not the pinned {pin['sha256']}"
        )
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeError, ValueError) as error:
        raise ScenarioHintsError(f"{field_name} is not JSON: {error}") from error


def load_scenario_hints_table(
    data_root: Path, *, release: object, snapshot: object, view_id: str,
) -> ScenarioHintsTable:
    """Load the released table from its two pinned data-root files.

    Fail-closed on every axis: each file's bytes must hash to its declared
    pin, the release must name this view id and the snapshot's own pin, and
    the two documents must agree on the builder policy, the derivation rule
    and the construction identity. No network, no repository, no model.
    """

    release_pin = _pin(release, field_name="solver_hints.release")
    snapshot_pin = _pin(snapshot, field_name="solver_hints.snapshot")
    release_document = _read_pinned(
        data_root, release_pin, field_name="solver_hints.release"
    )
    snapshot_document = _read_pinned(
        data_root, snapshot_pin, field_name="solver_hints.snapshot"
    )
    if (
        not isinstance(release_document, Mapping)
        or release_document.get("schema") != SCENARIO_HINTS_RELEASE_SCHEMA
        or release_document.get("view_id") != view_id
        or release_document.get("snapshot_sha256") != snapshot_pin["sha256"]
    ):
        raise ScenarioHintsError(
            "solver_hints.release is not this view's release, or does not pin the "
            "declared snapshot"
        )
    if (
        not isinstance(snapshot_document, Mapping)
        or snapshot_document.get("schema") != SCENARIO_HINTS_VIEW_SCHEMA
        or snapshot_document.get("view_id") != view_id
    ):
        raise ScenarioHintsError("solver_hints.snapshot is not this view's snapshot")
    if release_document.get("builder_policy_id") != snapshot_document.get(
        "builder_policy_id"
    ) or release_document.get("source_split_identity_hash") != snapshot_document.get(
        "source_split_identity_hash"
    ):
        raise ScenarioHintsError(
            "solver_hints release and snapshot disagree on the construction identity"
        )
    return _table_from_documents(
        snapshot_document,
        release_sha256=release_pin["sha256"],
        snapshot_sha256=snapshot_pin["sha256"],
    )


def _neighbour_policy(snapshot: Mapping[str, object]) -> tuple[int, float]:
    """The snapshot's declared derivation rule, checked against this module's.

    The rule is the view's IDENTITY: a table built with another ``k`` or
    another leakage floor is another analysis, so a snapshot that declares one
    is refused rather than rendered.
    """

    policy = snapshot.get("neighbour_policy")
    if not isinstance(policy, Mapping):
        raise ScenarioHintsError("solver_hints snapshot declares no neighbour policy")
    if policy.get("k") != NEIGHBOUR_K:
        raise ScenarioHintsError(
            f"solver_hints snapshot declares k={policy.get('k')!r}; this module "
            f"registers k={NEIGHBOUR_K}"
        )
    floor = policy.get("min_leakage_share")
    if isinstance(floor, bool) or not isinstance(floor, (int, float)):
        raise ScenarioHintsError(
            "solver_hints snapshot min_leakage_share must be a number"
        )
    if float(floor) != NEIGHBOUR_MIN_LEAKAGE_SHARE:
        raise ScenarioHintsError(
            f"solver_hints snapshot declares a leakage floor of {floor!r}; this "
            f"module registers {NEIGHBOUR_MIN_LEAKAGE_SHARE}"
        )
    for name, registered in (
        ("max_neighbours", NEIGHBOUR_LIMIT),
        ("max_cues", CUE_LIMIT),
        ("cue_min_rows", CUE_MIN_ROWS),
        ("cue_prior", CUE_PRIOR),
    ):
        if policy.get(name) != registered:
            raise ScenarioHintsError(
                f"solver_hints snapshot declares {name}={policy.get(name)!r}; this "
                f"module registers {registered}"
            )
    return NEIGHBOUR_K, NEIGHBOUR_MIN_LEAKAGE_SHARE


def _table_from_documents(
    snapshot: Mapping[str, object],
    *,
    release_sha256: str,
    snapshot_sha256: str,
) -> ScenarioHintsTable:
    neighbour_k, min_leakage_share = _neighbour_policy(snapshot)
    declared_intents = snapshot.get("intents")
    if not isinstance(declared_intents, list) or not declared_intents:
        raise ScenarioHintsError("solver_hints snapshot declares no intent profile")
    intents: dict[str, ScenarioHintProfile] = {}
    for entry in declared_intents:
        if not isinstance(entry, Mapping) or set(entry) != {
            "intent", "rows", "neighbours",
        }:
            raise ScenarioHintsError(
                "solver_hints intent profile has unknown or missing fields"
            )
        intent = entry["intent"]
        rows = entry["rows"]
        if (
            not isinstance(intent, str)
            or not intent
            or intent in intents
            or isinstance(rows, bool)
            or not isinstance(rows, int)
            or rows < 0
        ):
            raise ScenarioHintsError("solver_hints intent profile id or rows is invalid")
        declared_neighbours = entry["neighbours"]
        if not isinstance(declared_neighbours, list):
            raise ScenarioHintsError(
                f"solver_hints intent {intent!r} neighbours must be a list"
            )
        if len(declared_neighbours) > NEIGHBOUR_LIMIT:
            raise ScenarioHintsError(
                f"solver_hints intent {intent!r} lists more than {NEIGHBOUR_LIMIT} "
                "neighbours"
            )
        neighbours: list[ScenarioHintNeighbour] = []
        seen: set[str] = set()
        for row in declared_neighbours:
            neighbours.append(
                _neighbour_from_document(row, intent=intent, rows=rows, seen=seen)
            )
        intents[intent] = ScenarioHintProfile(
            intent=intent, rows=rows, neighbours=tuple(neighbours),
        )
    count = snapshot.get("construction_utterance_count")
    if isinstance(count, bool) or not isinstance(count, int) or count <= 0:
        raise ScenarioHintsError("solver_hints construction_utterance_count is invalid")
    split = snapshot.get("source_split")
    if split != "train":
        raise ScenarioHintsError(
            "solver_hints snapshot must be mined from the TRAIN construction pool"
        )
    return ScenarioHintsTable(
        view_id=str(snapshot["view_id"]),
        builder_policy_id=str(snapshot["builder_policy_id"]),
        source_split=split,
        source_split_identity_hash=str(snapshot["source_split_identity_hash"]),
        construction_utterance_count=count,
        neighbour_k=neighbour_k,
        min_leakage_share=min_leakage_share,
        intents=intents,
        release_sha256=release_sha256,
        snapshot_sha256=snapshot_sha256,
    )


def _neighbour_from_document(
    row: object, *, intent: str, rows: int, seen: set[str],
) -> ScenarioHintNeighbour:
    if not isinstance(row, Mapping) or set(row) != {
        "intent", "leaked", "of_neighbours", "leakage_share", "cues",
    }:
        raise ScenarioHintsError(
            f"solver_hints intent {intent!r} neighbour row has unknown fields"
        )
    neighbour_id = row["intent"]
    leaked = row["leaked"]
    of_neighbours = row["of_neighbours"]
    if (
        not isinstance(neighbour_id, str)
        or not neighbour_id
        or neighbour_id == intent
        or neighbour_id in seen
        or isinstance(leaked, bool)
        or not isinstance(leaked, int)
        or isinstance(of_neighbours, bool)
        or not isinstance(of_neighbours, int)
        or of_neighbours != rows * NEIGHBOUR_K
        or not 1 <= leaked <= of_neighbours
    ):
        raise ScenarioHintsError(
            f"solver_hints intent {intent!r} neighbour row is invalid"
        )
    if leaked / of_neighbours < NEIGHBOUR_MIN_LEAKAGE_SHARE:
        raise ScenarioHintsError(
            f"solver_hints intent {intent!r} tables neighbour {neighbour_id!r} below "
            "the declared leakage floor"
        )
    if row["leakage_share"] != _share(leaked, of_neighbours):
        raise ScenarioHintsError(
            f"solver_hints intent {intent!r} neighbour {neighbour_id!r} records a "
            "leakage share that is not its own integer ratio"
        )
    seen.add(neighbour_id)
    declared_cues = row["cues"]
    if not isinstance(declared_cues, list) or len(declared_cues) > CUE_LIMIT:
        raise ScenarioHintsError(
            f"solver_hints intent {intent!r} neighbour {neighbour_id!r} lists more "
            f"than {CUE_LIMIT} cues"
        )
    cues: list[ScenarioHintCue] = []
    words: set[str] = set()
    for cue in declared_cues:
        if not isinstance(cue, Mapping) or set(cue) != {
            "word", "rows", "neighbour_rows", "log_odds",
        }:
            raise ScenarioHintsError(
                f"solver_hints cue of {intent!r} -> {neighbour_id!r} has unknown fields"
            )
        word = cue["word"]
        cue_rows = cue["rows"]
        neighbour_rows = cue["neighbour_rows"]
        log_odds = cue["log_odds"]
        if (
            not isinstance(word, str)
            or word in words
            or not is_cue_candidate(word)
            or isinstance(cue_rows, bool)
            or not isinstance(cue_rows, int)
            or cue_rows < CUE_MIN_ROWS
            or isinstance(neighbour_rows, bool)
            or not isinstance(neighbour_rows, int)
            or neighbour_rows < 0
            or isinstance(log_odds, bool)
            or not isinstance(log_odds, (int, float))
        ):
            raise ScenarioHintsError(
                f"solver_hints cue of {intent!r} -> {neighbour_id!r} is invalid"
            )
        words.add(word)
        cues.append(ScenarioHintCue(
            word=word,
            rows=cue_rows,
            neighbour_rows=neighbour_rows,
            log_odds=float(log_odds),
        ))
    return ScenarioHintNeighbour(
        intent=neighbour_id,
        leaked=leaked,
        of_neighbours=of_neighbours,
        cues=tuple(cues),
    )


def scenario_hints(
    *,
    candidate_ids: Sequence[str],
    table: ScenarioHintsTable,
    bounds: ScenarioHintsBounds,
) -> tuple[ScenarioHint, ...]:
    """The bounded hints for one row's Perception candidate list.

    Pure, deterministic and zero-contact. The candidates are read in
    PERCEPTION'S OWN ORDER and capped at
    :data:`SCENARIO_HINTS_MAX_CANDIDATES`; a repeated candidate is rendered
    once; a candidate the table does not carry is skipped, because an intent
    with no construction rows has no construction neighbour to state.
    """

    if isinstance(candidate_ids, (str, bytes)):
        raise ScenarioHintsError("candidate_ids must be a sequence of intent ids")
    hints: list[ScenarioHint] = []
    rendered: set[str] = set()
    for candidate in candidate_ids:
        if not isinstance(candidate, str) or not candidate:
            raise ScenarioHintsError("every Perception candidate id must be text")
        if candidate in rendered:
            continue
        profile = table.profile(candidate)
        if profile is None or profile.rows <= 0:
            continue
        rendered.add(candidate)
        lines = tuple(
            ScenarioHintLine(
                intent=candidate,
                neighbour=neighbour.intent,
                leaked=neighbour.leaked,
                of_neighbours=neighbour.of_neighbours,
                cues=tuple(
                    cue.word for cue in neighbour.cues[: bounds.max_cues]
                ),
            )
            for neighbour in profile.neighbours[: bounds.max_neighbours]
        )
        hints.append(ScenarioHint(
            intent=candidate, rows=profile.rows, lines=lines,
        ))
        if len(hints) >= SCENARIO_HINTS_MAX_CANDIDATES:
            break
    return tuple(hints)


def hint_counts(hints: Sequence[ScenarioHint]) -> dict[str, int]:
    """The three block sizes a receipt row always carries, including zeros."""

    return {
        "candidates": len(hints),
        "neighbours": sum(len(hint.lines) for hint in hints),
        "cues": sum(len(line.cues) for hint in hints for line in hint.lines),
    }


__all__ = [
    "CUE_LIMIT",
    "CUE_MIN_ROWS",
    "CUE_PRIOR",
    "NEIGHBOUR_K",
    "NEIGHBOUR_LIMIT",
    "NEIGHBOUR_MIN_LEAKAGE_SHARE",
    "NO_CUES",
    "NO_NEIGHBOUR",
    "PIN_NAMESPACE",
    "PIN_ROOT",
    "SCENARIO_HINTS_BOUND_CEILINGS",
    "SCENARIO_HINTS_BOUND_KEYS",
    "SCENARIO_HINTS_BUILDER_POLICY_ID",
    "SCENARIO_HINTS_COMPLETION_SCHEMA",
    "SCENARIO_HINTS_DEFAULT_BOUNDS",
    "SCENARIO_HINTS_MAX_CANDIDATES",
    "SCENARIO_HINTS_RECEIPT_SCHEMA",
    "SCENARIO_HINTS_RELEASE_SCHEMA",
    "SCENARIO_HINTS_VIEW_ID",
    "SCENARIO_HINTS_VIEW_SCHEMA",
    "SCENARIO_HINTS_VOCABULARY",
    "STOPWORDS",
    "ScenarioHint",
    "ScenarioHintCue",
    "ScenarioHintLine",
    "ScenarioHintNeighbour",
    "ScenarioHintProfile",
    "ScenarioHintsBounds",
    "ScenarioHintsError",
    "ScenarioHintsTable",
    "cue_log_odds",
    "hint_counts",
    "is_cue_candidate",
    "load_scenario_hints_table",
    "render_cues",
    "render_leakage",
    "scenario_hints",
    "scenario_hints_bounds",
    "validate_scenario_hints_pin",
]
