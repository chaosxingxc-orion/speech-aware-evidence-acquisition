"""The KU-S4N narrowing view: a gold-free intent candidate set per DEV row.

Cell KU-S4N of the 2026-09-08 owner Decision 10 intent family. The mechanism
is *narrowing*: instead of asking the frozen core to pick one of the 60 legal
SLURP intents, the SYSTEM offers ``k`` of them and asks the core to choose
among those. Nothing here writes prompt text into an instruction -- the
candidates travel the traced-supply channel as typed content blocks, exactly
as ``rails.phase_supply`` and ``rails.runner._agent_messages`` already carry a
knowledge value (KU-S3's precedent).

Two halves, both model-free and both computed BEFORE any flight.

The candidate rule (gold-free, by construction)
-----------------------------------------------

For one DEV row:

1. the **predicted scenario's legal intents**, TRAIN prior first, capped at
   :data:`DEFAULT_SCENARIO_LEAD` -- read off the sealed comparator's own
   response through ``reproduction.slurp_scoring.project_slu_label_v2``, which
   is the paper-facing scorer's own label path;
2. then the **speech-vector neighbours' distinct intents** in cosine rank
   order, skipping repeats, until the set holds ``k``.

Neither half sees a gold label: half (1) is the arm's own prediction and half
(2) is a cosine over sealed vectors whose query is the row's OWN recording.
MF-8 priced the rule (``docs/readiness/2026-09-08-mf8-speech-to-knowledge-
audit-v1.md`` section 2.4): at ``k = 8`` with ``scenario_lead = 3`` the gold
intent is inside the set on **95.80 %** of all rows and **86.62 %** of the
rows the comparator gets wrong, at a **13.33 %** narrowing ratio.

:func:`compose_candidate_set` is that rule. It is deliberately a re-statement
of ``scripts/mf8_speech_to_knowledge_audit.compose_candidates`` rather than an
import (the audit script is a one-shot receipt producer, not a library), and
``tests/unit/test_slurp_intent_candidates.py`` pins the two to byte equality
for as long as the script exists.

The twin rule (form control)
----------------------------

:func:`compose_twin_set` draws the SAME number of intents uniformly at random
from the 60 legal intents, **excluding every intent the arm's own set chose**,
under one seed (:data:`TWIN_SEED`) whose only entry point is the sample id.
The twin is therefore the same mechanism with the wrong candidates: same
program, same control turn, same block count, same block template, same
supply channel. It is the lock (owner ruling 2026-09-06: lock the score
against a token-matched control, not against a token count); the block's
character volume is reported beside every contrast as a covariate.

Excluding the arm's own choices is what makes the twin a control rather than
a weaker arm: a random draw that could contain the gold candidate the arm
found would measure "does narrowing help" twice instead of "does the RIGHT
narrowing help".

What a block says
-----------------

One value per legal intent, one fixed template
(:data:`CANDIDATE_BLOCK_TEMPLATE`), so that arm and twin differ only in WHICH
sixty-way choice was made. The block is self-describing -- it says it is a
candidate for the spoken command in this request -- because the instruction
is held byte-identical to the sealed comparator's and may not be told about
the mechanism.

The bank
--------

A :class:`CandidateBank` is the sealed, sha256-pinned per-row decision: one
JSON object per line carrying both the arm's ordered candidates and the
twin's. It is produced once, model-free, by ``scripts/slurp_kus4_prep.py``,
lives under ``SPEECHRL_DATA_DIR`` (never in Git), and is re-hashed at
preflight. That is the same discipline ``rails.phase_supply`` states for a
sealed vector file, applied to a decision that a cosine alone cannot express.
"""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from .errors import RailsError
from .knowledge import KeyFacet, KnowledgeSnapshot, ValueBundle

#: The candidate-set size the family registers, and it is a **CAP, not a
#: count**. MF-8 measured 3, 5 and 8; the family flies 8 because it is the
#: reach the narrowing buys (95.80 % of all rows, 86.62 % of the error rows)
#: and because the KU-S4a coverage stratum -- the only place k matters for
#: power -- is a SECONDARY read, not the decision population.
#:
#: Measured on the real roster (preparation receipt
#: ``2026-09-09-slurp-kus4-prep``), the rule runs out of DISTINCT neighbour
#: intents before it fills eight slots on most rows: the mean offer is 5.94
#: and only 417 of 1,000 rows reach eight, so the realized narrowing ratio is
#: 9.89 % rather than 13.33 %. Deepening the neighbour list closes that gap
#: and buys nothing where it matters -- at depth 400 the mean offer is 8.00
#: and recall on the ERROR rows is still exactly 86.62 -- which is why the
#: depth stays where MF-8 priced it and the per-row offer is a covariate.
DEFAULT_K = 8

#: How many of the k slots the predicted scenario's legal list leads with.
DEFAULT_SCENARIO_LEAD = 3

#: The seed the twin draw uses, and the only seed in this module. Same value
#: every other SLURP twin in this repository uses (KV-3, EVO-S1, MF-10).
TWIN_SEED = 20260903

#: The 60 legal intents are the whole label space; a candidate set is k of
#: them, so the narrowing ratio is k / 60 (MF-8 section 2.4).
LEGAL_INTENT_SPACE = 60

#: The one block template. Only the intent, its scenario and its action vary,
#: so arm and twin blocks are the same form by construction and differ only in
#: the label they name.
CANDIDATE_BLOCK_TEMPLATE = (
    "Candidate intent for the spoken command in this request: {intent} "
    '(scenario "{scenario}", action "{action}").'
)

#: The facet (KEY) side. It is deliberately NOT the bare intent name:
#: ``rails.runner._protected_knowledge_material`` protects every facet
#: representation of 8 characters or more, and the comparator's own closed
#: label inventory already names all sixty intents, so a bare-name facet would
#: make the containment fold refuse the very instruction this family holds
#: byte-identical. The prefix keeps the key unique to the snapshot while the
#: name it carries stays readable.
FACET_REPRESENTATION_TEMPLATE = "intent candidate key: {intent}"

#: The snapshot this module builds, and the builder policy id its provenance
#: records. Not a ``core.base.KNOWLEDGE_BUILDERS`` entry: the artifact is 60
#: TRAIN-mined label cards, not a KB build, and it is produced by the
#: model-free preparation pass rather than by a flight.
SNAPSHOT_ID = "saea-slurp-intent-candidates-v1"
BUILDER_POLICY_ID = "saea-slurp-intent-candidates-v1"

#: Facet and value id prefixes. One facet and one value per legal intent.
FACET_ID_PREFIX = "facet:intent:"
VALUE_ID_PREFIX = "value:intent-candidate:"

#: The bank file's schema string, written into every bank and re-checked on
#: load, so a bank produced by a different rule cannot be silently consumed.
BANK_SCHEMA = "saea-slurp-intent-candidate-bank-v1"

#: The two selections a fragment may name. The value rides the config hash,
#: exactly as ``fill_params.view`` does for the KV family, so an arm and its
#: twin can never resolve to the same cell identity.
BANK_SELECTIONS = ("candidates", "twin_candidates")


class SlurpIntentCandidateError(RailsError):
    """A candidate set, twin draw, bank file or candidate snapshot violated
    the shape this module requires."""


# ---------------------------------------------------------------------------
# The rule
# ---------------------------------------------------------------------------


def intent_name(scenario: str, action: str) -> str:
    """``SlurpRecord.intent``'s own spelling."""

    return f"{scenario}_{action}"


def scenario_legal_intents(
    actions_by_scenario: Mapping[str, Sequence[str]],
    intent_prior: Mapping[str, int],
) -> dict[str, tuple[str, ...]]:
    """``{scenario: (intent, ...)}`` with each scenario's legal intents in
    TRAIN-prior order, ties broken by the intent name.

    The same ordering ``scripts/mf8_speech_to_knowledge_audit.py`` used to
    price source (b); stated here as a function so the flight-side rule and
    the audit's own number come from one expression.
    """

    ordered: dict[str, tuple[str, ...]] = {}
    for scenario in sorted(actions_by_scenario):
        actions = sorted(
            actions_by_scenario[scenario],
            key=lambda action: (-int(intent_prior.get(f"{scenario}_{action}", 0)), action),
        )
        ordered[scenario] = tuple(intent_name(scenario, action) for action in actions)
    return ordered


def compose_candidate_set(
    scenario_candidates: Sequence[str],
    neighbour_candidates: Sequence[str],
    k: int = DEFAULT_K,
    *,
    scenario_lead: int = DEFAULT_SCENARIO_LEAD,
) -> tuple[str, ...]:
    """The gold-free candidate set an arm actually offers.

    ``scenario_lead`` entries come from the PREDICTED scenario's legal list
    (TRAIN prior first); the rest are filled from the speech-vector
    neighbours' distinct intents in cosine rank order, skipping repeats. Both
    halves are built without the gold label.

    Byte-identical to ``scripts/mf8_speech_to_knowledge_audit.
    compose_candidates`` for every input; a unit test pins that equality.
    """

    if isinstance(k, bool) or not isinstance(k, int) or k <= 0:
        raise SlurpIntentCandidateError("candidate count k must be a positive integer")
    if isinstance(scenario_lead, bool) or not isinstance(scenario_lead, int) or scenario_lead < 0:
        raise SlurpIntentCandidateError("scenario_lead must be a non-negative integer")
    chosen: list[str] = []
    for intent in list(scenario_candidates)[: min(scenario_lead, k)]:
        if intent not in chosen:
            chosen.append(intent)
    for intent in neighbour_candidates:
        if len(chosen) >= k:
            break
        if intent not in chosen:
            chosen.append(intent)
    return tuple(chosen[:k])


def compose_twin_set(
    candidates: Sequence[str],
    legal_intents: Sequence[str],
    *,
    sample_id: str,
    seed: int = TWIN_SEED,
) -> tuple[str, ...]:
    """The form twin: ``len(candidates)`` intents drawn uniformly at random
    from ``legal_intents``, EXCLUDING every intent ``candidates`` names.

    Reproducible from ``(seed, sample_id, sorted legal intents, the arm's own
    set)`` and from nothing else. The draw is returned in the drawn order, so
    the twin's block order is as arbitrary as its content -- a twin that
    re-sorted its draw would carry an ordering signal the arm does not.
    """

    if not isinstance(sample_id, str) or not sample_id:
        raise SlurpIntentCandidateError("compose_twin_set needs a non-empty sample id")
    arm = tuple(candidates)
    pool = [intent for intent in sorted(set(legal_intents)) if intent not in set(arm)]
    if len(pool) < len(arm):
        raise SlurpIntentCandidateError(
            f"the twin pool for {sample_id!r} holds {len(pool)} intents but the arm "
            f"offers {len(arm)}; a form twin must match the arm's block count"
        )
    rng = random.Random(f"{seed}:{sample_id}")
    return tuple(rng.sample(pool, len(arm)))


def narrowing_ratio(k: int, label_space: int = LEGAL_INTENT_SPACE) -> float:
    """``k / label_space`` -- the share of the label decision the SYSTEM
    leaves to the core. Reported beside every recall number (MF-8 2.4)."""

    if isinstance(k, bool) or not isinstance(k, int) or k <= 0:
        raise SlurpIntentCandidateError("k must be a positive integer")
    if isinstance(label_space, bool) or not isinstance(label_space, int) or label_space <= 0:
        raise SlurpIntentCandidateError("label_space must be a positive integer")
    return k / label_space


# ---------------------------------------------------------------------------
# The blocks and the snapshot
# ---------------------------------------------------------------------------


def render_candidate_block(intent: str) -> str:
    """One candidate's typed block text.

    ``intent`` is the ``<scenario>_<action>`` spelling; the scenario is the
    part before the FIRST underscore, which is how ``data.slurp`` spells every
    SLURP intent (``alarm_set``, ``qa_factoid``, ``social_post``) -- an action
    may itself carry an underscore, the scenario never does.
    """

    if not isinstance(intent, str) or "_" not in intent:
        raise SlurpIntentCandidateError(
            f"intent {intent!r} is not a '<scenario>_<action>' label"
        )
    scenario, action = intent.split("_", 1)
    if not scenario or not action:
        raise SlurpIntentCandidateError(
            f"intent {intent!r} names an empty scenario or action"
        )
    return CANDIDATE_BLOCK_TEMPLATE.format(intent=intent, scenario=scenario, action=action)


def facet_id_for(intent: str) -> str:
    return f"{FACET_ID_PREFIX}{intent}"


def value_id_for(intent: str) -> str:
    return f"{VALUE_ID_PREFIX}{intent}"


def train_split_identity_hash(sample_ids: Sequence[str]) -> str:
    """``sha256("\n".join(sorted(ids)))`` -- the identity
    ``rails.knowledge_build.build_knowledge_snapshot`` computes for its own
    source set, restated here so a snapshot built outside that builder carries
    the SAME kind of identity rather than a borrowed constant."""

    return hashlib.sha256(
        "\n".join(sorted(set(sample_ids))).encode("utf-8")
    ).hexdigest()


def build_candidate_snapshot(
    *,
    legal_intents: Sequence[str],
    train_sample_ids_by_intent: Mapping[str, Sequence[str]],
    governed_train_relpath: str,
) -> KnowledgeSnapshot:
    """A frozen 60-facet / 60-value snapshot: one candidate card per legal
    intent, bound to the TRAIN recordings that intent was mined from.

    TRAIN only. ``train_sample_ids_by_intent`` carries, per intent, the
    RECORDING ids that evidence it -- the same granularity
    ``saea-kb-distmodel-v1``'s own snapshots bind -- and the snapshot's
    ``source_sample_ids`` is their union, which is what makes every value's
    ``source_sample_ids`` a subset of the snapshot's own
    (``KnowledgeSnapshot.validate``). The split identity is derived from that
    union by :func:`train_split_identity_hash`, so it is a fact about the
    artifact rather than a constant copied from another one. No devel or test
    id may appear anywhere, and this function refuses one by name.
    """

    intents = tuple(sorted(set(legal_intents)))
    if not intents:
        raise SlurpIntentCandidateError("build_candidate_snapshot needs legal intents")
    facets: list[KeyFacet] = []
    values: list[ValueBundle] = []
    all_sources: list[str] = []
    for intent in intents:
        sources = tuple(sorted(set(train_sample_ids_by_intent.get(intent, ()))))
        if not sources:
            raise SlurpIntentCandidateError(
                f"intent {intent!r} has no TRAIN utterance to bind its card to"
            )
        for source in sources:
            if ":devel:" in source or ":test:" in source:
                raise SlurpIntentCandidateError(
                    f"candidate snapshot source {source!r} is not a TRAIN id"
                )
        all_sources.extend(sources)
        facets.append(
            KeyFacet(
                facet_id=facet_id_for(intent),
                dimension="intent",
                representation_kind="text",
                representation=FACET_REPRESENTATION_TEMPLATE.format(intent=intent),
                source_sample_ids=sources,
            ).validate()
        )
        values.append(
            ValueBundle(
                value_id=value_id_for(intent),
                content=render_candidate_block(intent),
                associated_facet_ids=(facet_id_for(intent),),
                source_sample_ids=sources,
                provenance_refs=(
                    f"governed-jsonl:{governed_train_relpath}#intent={intent}",
                ),
                task_target=intent,
                prior_score=None,
            ).validate()
        )
    return KnowledgeSnapshot(
        snapshot_id=SNAPSHOT_ID,
        source_split_identity_hash=train_split_identity_hash(all_sources),
        source_sample_ids=tuple(sorted(set(all_sources))),
        builder_policy_id=BUILDER_POLICY_ID,
        facets=tuple(facets),
        values=tuple(values),
    ).validate()


# ---------------------------------------------------------------------------
# The bank
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CandidateBank:
    """The sealed per-row decision: ``sample_id -> (arm set, twin set)``.

    Both selections live in ONE file so that the twin's exclusion rule --
    "drawn from the 60 legal intents excluding the arm's own choices" -- is
    verifiable from the artifact itself rather than from two files a reader
    has to trust were produced together. A fragment names which selection its
    cell reads (:data:`BANK_SELECTIONS`), and that name rides the config hash.
    """

    k: int
    scenario_lead: int
    seed: int
    candidates: Mapping[str, tuple[str, ...]]
    twin_candidates: Mapping[str, tuple[str, ...]]
    sha256: str

    def validate(self) -> "CandidateBank":
        if isinstance(self.k, bool) or not isinstance(self.k, int) or self.k <= 0:
            raise SlurpIntentCandidateError("CandidateBank.k must be a positive integer")
        if set(self.candidates) != set(self.twin_candidates):
            raise SlurpIntentCandidateError(
                "CandidateBank arm and twin selections cover different sample sets"
            )
        if not self.candidates:
            raise SlurpIntentCandidateError("CandidateBank carries no rows")
        for sample_id, arm in self.candidates.items():
            twin = self.twin_candidates[sample_id]
            if len(arm) != len(twin):
                raise SlurpIntentCandidateError(
                    f"{sample_id}: twin offers {len(twin)} candidates against the arm's "
                    f"{len(arm)}; a form twin must match the arm's block count"
                )
            if len(set(arm)) != len(arm) or len(set(twin)) != len(twin):
                raise SlurpIntentCandidateError(f"{sample_id}: a selection repeats an intent")
            overlap = sorted(set(arm) & set(twin))
            if overlap:
                raise SlurpIntentCandidateError(
                    f"{sample_id}: the twin draw shares {overlap} with the arm's own set; "
                    "the twin is drawn from the legal intents the arm did NOT choose"
                )
        return self

    def selection(self, name: str) -> Mapping[str, tuple[str, ...]]:
        if name not in BANK_SELECTIONS:
            raise SlurpIntentCandidateError(
                f"unknown bank selection {name!r}; known: {list(BANK_SELECTIONS)}"
            )
        return self.candidates if name == "candidates" else self.twin_candidates


def bank_rows(
    candidates: Mapping[str, Sequence[str]],
    twin_candidates: Mapping[str, Sequence[str]],
    *,
    k: int,
    scenario_lead: int,
    seed: int = TWIN_SEED,
) -> list[dict[str, object]]:
    """The bank file's lines, in sorted sample order: one header, then one row
    per sample. Deterministic: the same inputs always serialize to the same
    bytes, which is what makes the file's sha256 a config-pinnable identity."""

    header = {
        "schema": BANK_SCHEMA,
        "k": int(k),
        "scenario_lead": int(scenario_lead),
        "seed": int(seed),
        "rows": len(candidates),
    }
    lines: list[dict[str, object]] = [header]
    for sample_id in sorted(candidates):
        lines.append(
            {
                "sample_id": sample_id,
                "candidates": list(candidates[sample_id]),
                "twin_candidates": list(twin_candidates[sample_id]),
            }
        )
    return lines


def serialize_bank(rows: Sequence[Mapping[str, object]]) -> str:
    return (
        "\n".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            for row in rows
        )
        + "\n"
    )


def load_candidate_bank(path: Path, *, expected_sha256: str) -> CandidateBank:
    """Read and hash-verify a bank file.

    Fail-closed on: a missing file, a sha256 that is not the configured one, a
    malformed or missing header, a duplicate sample id, a row whose two
    selections disagree in size, and a twin that overlaps its own arm.
    """

    resolved = Path(path)
    if not resolved.is_file():
        raise SlurpIntentCandidateError(f"candidate bank {resolved} does not exist")
    raw = resolved.read_bytes()
    measured = hashlib.sha256(raw).hexdigest()
    if measured != str(expected_sha256):
        raise SlurpIntentCandidateError(
            f"candidate bank {resolved} hashes to {measured}, not the configured "
            f"{expected_sha256}"
        )
    lines = [line for line in raw.decode("utf-8").splitlines() if line.strip()]
    if not lines:
        raise SlurpIntentCandidateError(f"candidate bank {resolved} is empty")
    header = json.loads(lines[0])
    if not isinstance(header, Mapping) or header.get("schema") != BANK_SCHEMA:
        raise SlurpIntentCandidateError(
            f"candidate bank {resolved} does not open with a {BANK_SCHEMA!r} header"
        )
    arm: dict[str, tuple[str, ...]] = {}
    twin: dict[str, tuple[str, ...]] = {}
    for number, line in enumerate(lines[1:], start=2):
        record = json.loads(line)
        if not isinstance(record, Mapping) or set(record) != {
            "sample_id",
            "candidates",
            "twin_candidates",
        }:
            raise SlurpIntentCandidateError(
                f"{resolved} line {number} must carry exactly sample_id, candidates and "
                "twin_candidates"
            )
        sample_id = record["sample_id"]
        if not isinstance(sample_id, str) or not sample_id:
            raise SlurpIntentCandidateError(f"{resolved} line {number}: bad sample id")
        if sample_id in arm:
            raise SlurpIntentCandidateError(
                f"{resolved} has a duplicate sample id {sample_id!r}"
            )
        for field_name in ("candidates", "twin_candidates"):
            entry = record[field_name]
            if not isinstance(entry, list) or not entry or any(
                not isinstance(item, str) or not item for item in entry
            ):
                raise SlurpIntentCandidateError(
                    f"{resolved} line {number}: {field_name} must be a non-empty list of "
                    "intent names"
                )
        arm[sample_id] = tuple(record["candidates"])
        twin[sample_id] = tuple(record["twin_candidates"])
    return CandidateBank(
        k=int(header.get("k", 0)),
        scenario_lead=int(header.get("scenario_lead", 0)),
        seed=int(header.get("seed", 0)),
        candidates=arm,
        twin_candidates=twin,
        sha256=measured,
    ).validate()


__all__ = [
    "BANK_SCHEMA",
    "BANK_SELECTIONS",
    "BUILDER_POLICY_ID",
    "CANDIDATE_BLOCK_TEMPLATE",
    "DEFAULT_K",
    "DEFAULT_SCENARIO_LEAD",
    "FACET_ID_PREFIX",
    "FACET_REPRESENTATION_TEMPLATE",
    "LEGAL_INTENT_SPACE",
    "SNAPSHOT_ID",
    "TWIN_SEED",
    "VALUE_ID_PREFIX",
    "CandidateBank",
    "SlurpIntentCandidateError",
    "bank_rows",
    "build_candidate_snapshot",
    "compose_candidate_set",
    "compose_twin_set",
    "facet_id_for",
    "intent_name",
    "load_candidate_bank",
    "narrowing_ratio",
    "render_candidate_block",
    "scenario_legal_intents",
    "serialize_bank",
    "train_split_identity_hash",
    "value_id_for",
]
