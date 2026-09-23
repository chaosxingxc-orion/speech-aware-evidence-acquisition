"""Stage-3 S3-4s: ADV-1's flight-time per-row material -- the root follow-up
``rails.stage3_advantage``'s module docstring left open ("wiring
:func:`build_advantage_instruction_for_row` into
``core.flight.FlightRuntime.bind_phase_program_material`` is left as a
documented root follow-up").

This module is the SECOND ``construction_material_resolver`` of this study.
``core.flight.runtime._default_construction_material`` now dispatches on the
composed baseline's own ``arm``: ``"construction-proposer-text"`` keeps the
Audio2Tool/SLURP proposer path byte for byte, and
``"construction-advantage-text"`` resolves here.

What it reads, all of it committed or hash-pinned by the composed config:

* ``advantage_pairs`` -- S3-3's ``pairs.json`` under the DATA root, pinned by
  ``sha256`` and bound to the rollout ``run_id``/``attempt_id`` that produced
  it (``rails.stage3_advantage.load_advantage_pairs`` does the pinning);
* that same rollout's SEALED ``<run_id>.outputs.jsonl`` custody, from which
  the BEST and WORST Solver sample answers are rendered again, byte for byte,
  in the canonical delivered form -- and then VERIFIED against the per-row
  ``response_text_sha256`` ``pairs.json`` carries, so a custody drift is a
  refusal rather than a silently different prompt;
* ``pairs.json``'s per-row ``trajectory`` block (S3-4s), for the Perception
  candidate ids, the Reviewer verdict LABELS and the Planner route LABELS --
  ids, labels and counts, never text;
* the row's own CONSTRUCTION GOLD, read at flight time from the governed
  SLURP TRAIN metadata (``data.slurp.load_slurp_train_construction_rows``),
  exactly the way the proposer arm reads its gold at flight time and legal
  for exactly the same reason (owner decision 82; the flying cell's split
  identity is bound to a committed ``roster_role == "construction"`` receipt
  by ``contracts.gate_exposure._require_construction_role_for_visible_targets``).

Where the rendered text goes: into ONE place, the contact's
``instruction``, through ``rails.stage3_advantage.
build_advantage_instruction_for_row_v2``. Nothing this module returns for a
receipt ever carries an utterance, an answer or the gold --
:meth:`AdvantageContact.as_json` seals identities, counts and digests only,
the same discipline ``rails.evolution.ProposerContact.as_json`` documents and
the same one ``construction_draws`` documents at the wire-check receipt.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from .errors import RailsError
from .stage3_advantage import (
    STAGE3_ADVANTAGE_ARM,
    STAGE3_ADVANTAGE_PHASE_NAME,
    STAGE3_ADVANTAGE_TEMPLATE_RELPATH_V2,
    AdvantagePair,
    AdvantagePairs,
    Stage3AdvantageError,
    build_advantage_instruction_for_row_v2,
    load_advantage_pairs,
)

ADVANTAGE_MATERIAL_SCHEMA = "saea-stage3-advantage-material-v1"
ADVANTAGE_CONTACT_SCHEMA = "saea-stage3-advantage-contact-v1"

#: The carrier this material can read gold for. The gold reader below is
#: SLURP TRAIN's own one-reader entry point; a fragment naming any other
#: carrier is refused here rather than silently handed an empty gold.
ADVANTAGE_CARRIER_LOCK_KEY = "slurp"

#: The exact keys the baseline fragment's ``advantage_pairs`` block must
#: carry for a flight (the note keys are documentation and are ignored).
_REQUIRED_PAIRS_KEYS = (
    "relpath",
    "sha256",
    "rollout_run_id",
    "rollout_attempt_id",
)

#: The canonical empty answer, byte for byte the one
#: ``scripts/analysis/stage3_rollout_score.py`` writes for a sample whose
#: parse failed (``EMPTY_ANSWER``).
EMPTY_ANSWER = json.dumps(
    {"scenario": "", "action": "", "entities": []}, ensure_ascii=False, sort_keys=True
)

#: What the instruction says when the sealed trajectory carries no item of a
#: kind. Stated rather than omitted: an empty block that reads as an absent
#: section would make the contact guess whether the node ran at all.
_NOTHING_TO_SHOW = "(none recorded in the sealed trajectory)"


class Stage3AdvantageMaterialError(RailsError):
    """An ``advantage_pairs`` declaration, a sealed rollout custody read, or a
    per-row render is malformed or disagrees with what ``pairs.json`` pinned."""


# ---------------------------------------------------------------------------
# The canonical answer rendering -- proved equal, never assumed equal.
# ---------------------------------------------------------------------------


def render_rollout_answer(payload: Mapping[str, object] | None) -> str:
    """One sealed Solver sample's parsed answer, in the canonical delivered
    form: ``json.dumps({"scenario", "action", "entities": [{"type",
    "filler"}]}, ensure_ascii=False, sort_keys=True)``.

    The same form ``analysis.native_commit_replay.replay_row``,
    ``scripts/analysis/slurp_verifier_measurement.render_answer`` and
    ``scripts/analysis/stage3_rollout_score.render_answer`` write. This
    module does not TRUST that equality: every rendered answer is hashed and
    compared against the ``response_text_sha256`` ``pairs.json`` pinned for
    that exact sample index (:func:`build_advantage_material`), so a drift in
    any of the four renderings is a refusal before the first contact.
    """

    if payload is None:
        return EMPTY_ANSWER
    if not isinstance(payload, Mapping):
        raise Stage3AdvantageMaterialError(
            "a sealed parsed_answer must be an object or absent"
        )
    entities = payload.get("entities", [])
    if not isinstance(entities, Sequence) or isinstance(entities, (str, bytes)):
        raise Stage3AdvantageMaterialError("a sealed parsed_answer's entities must be a list")
    body = {
        "scenario": payload.get("scenario", ""),
        "action": payload.get("action", ""),
        "entities": [
            {"type": entity["type"], "filler": entity["filler"]}
            for entity in entities
        ],
    }
    return json.dumps(body, ensure_ascii=False, sort_keys=True)


def render_construction_gold(row: Mapping[str, object]) -> str:
    """This row's construction gold, in the SAME canonical form the three
    shown answers carry.

    Deliberately the same shape: ANSWER A, ANSWER B, the DELIVERED answer and
    the CORRECT answer are then four values of one grammar, so the contact
    compares content rather than formatting. ``entities`` are the governed
    annotation's own ``(type, filler)`` pairs in the annotation's own order
    (``data.slurp.load_slurp_train_construction_rows``).
    """

    entities = row.get("entities") or ()
    return json.dumps(
        {
            "scenario": str(row.get("scenario", "")),
            "action": str(row.get("action", "")),
            "entities": [
                {"type": str(entity_type), "filler": str(filler)}
                for entity_type, filler in entities
            ],
        },
        ensure_ascii=False,
        sort_keys=True,
    )


def render_candidate_list(
    intent_ids: Sequence[str], *, raw_count: object = None
) -> str:
    """The Perception node's ordered candidate ids, one per line.

    First-occurrence distinct ids WITH the raw count beside them
    (preregistration section 3 item 1): a duplicate the trajectory's own
    projection folded is then visible to the contact rather than invisible.
    """

    ordered = [str(item) for item in intent_ids if isinstance(item, str) and item]
    if not ordered:
        return _NOTHING_TO_SHOW
    lines = [f"{index + 1}. {item}" for index, item in enumerate(ordered)]
    if isinstance(raw_count, int) and not isinstance(raw_count, bool) and raw_count > 0:
        lines.append(
            f"({raw_count} candidate(s) proposed; {len(ordered)} distinct id(s) above, "
            "in first-occurrence order)"
        )
    return "\n".join(lines)


def render_reviewer_verdicts(marks: Sequence[Mapping[str, object]]) -> str:
    """One line per review visit: the visit index and the verdict LABEL.

    Only the closed-vocabulary token and the disposition the sealed
    trajectory carries -- never the Reviewer's free-text rationale, which
    ``pairs.json`` never recorded and this module never opens.
    """

    lines: list[str] = []
    for mark in marks:
        if not isinstance(mark, Mapping):
            continue
        visit = mark.get("visit")
        token = mark.get("token")
        disposition = mark.get("disposition")
        label = str(token) if isinstance(token, str) and token else str(disposition or "unavailable")
        lines.append(f"visit {visit}: {label}")
    return "\n".join(lines) if lines else _NOTHING_TO_SHOW


def render_planner_route(
    routes: Sequence[Mapping[str, object]],
    *,
    delivered_kind: str | None = None,
    revision_count: object = None,
) -> str:
    """One line per planner route: the action LABEL, its legality and the
    revision count at that point, closed by the episode's own DELIVERY KIND
    and total revision count (preregistration section 3 item 3)."""

    lines: list[str] = []
    for index, route in enumerate(routes):
        if not isinstance(route, Mapping):
            continue
        action = str(route.get("action") or "unavailable")
        legal = "legal" if route.get("legal", True) else "illegal"
        revisions = route.get("revision_count")
        suffix = "" if revisions is None else f", revisions so far {revisions}"
        lines.append(f"{index + 1}. {action} ({legal}{suffix})")
    if not lines:
        lines = [_NOTHING_TO_SHOW]
    tail: list[str] = []
    if delivered_kind:
        tail.append(f"delivery: {delivered_kind}")
    if isinstance(revision_count, int) and not isinstance(revision_count, bool):
        tail.append(f"revisions: {revision_count}")
    if tail:
        lines.append("(" + "; ".join(tail) + ")")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# The material.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AdvantageContact:
    """One rendered, flyable advantage contact.

    ``instruction`` is the whole rendered per-row phase instruction and is
    the ONLY place this row's rollout answers, delivered answer and
    construction gold are ever combined. It is never written to a receipt:
    :meth:`as_json` is what a receipt may record.
    """

    sample_id: str
    instruction: str
    prompt_sha256: str
    construction_target_ids: tuple[str, ...]
    best_sample_index: int
    worst_sample_index: int
    best_answer_sha256: str
    worst_answer_sha256: str
    delivered_answer_sha256: str
    gold_sha256: str
    candidate_intent_ids: tuple[str, ...]
    reviewer_verdict_dispositions: tuple[str, ...]
    planner_actions: tuple[str, ...]
    delivered_kind: str
    revision_count: int
    trajectory_available: bool

    @property
    def draw_id(self) -> str:
        """The contact's own stable id, the field ``ProposerContact.draw_id``
        plays for the proposer arm (the wire check prints it)."""

        return f"adv-{self.sample_id}"

    def as_json(self) -> dict[str, object]:
        """Everything a receipt may record about this contact -- identity,
        counts and digests, never the rendered text."""

        return {
            "schema": ADVANTAGE_CONTACT_SCHEMA,
            "draw_id": self.draw_id,
            "sample_id": self.sample_id,
            "best_sample_index": self.best_sample_index,
            "worst_sample_index": self.worst_sample_index,
            "best_answer_sha256": self.best_answer_sha256,
            "worst_answer_sha256": self.worst_answer_sha256,
            "delivered_answer_sha256": self.delivered_answer_sha256,
            "gold_sha256": self.gold_sha256,
            "candidate_intent_ids": list(self.candidate_intent_ids),
            "candidate_count": len(self.candidate_intent_ids),
            "reviewer_verdict_dispositions": list(self.reviewer_verdict_dispositions),
            "reviewer_visit_count": len(self.reviewer_verdict_dispositions),
            "planner_actions": list(self.planner_actions),
            "planner_route_length": len(self.planner_actions),
            "delivered_kind": self.delivered_kind,
            "revision_count": self.revision_count,
            "trajectory_available": self.trajectory_available,
            "prompt_sha256": self.prompt_sha256,
            "prompt_characters": len(self.instruction),
            "declared_construction_targets": len(self.construction_target_ids),
        }


@dataclass(frozen=True)
class AdvantageMaterial:
    """Every contact one ADV-1 flight makes, plus the gold it may show.

    ``bound_targets`` is what ``rails.core_client.FrozenCoreClient`` is
    constructed with -- one entry per flown row, its own construction gold --
    and each contact then names EXACTLY its own row, so a request narrows the
    bound set to a single row and can never widen it (the same invariant
    ``rails.evolution.ProposerMaterial`` documents).
    """

    contacts: tuple[AdvantageContact, ...]
    bound_targets: tuple[Mapping[str, str], ...]
    pairs_binding: Mapping[str, object]
    rollout_run_id: str
    rollout_attempt_id: str
    template_relpath: str
    template_sha256: str

    def by_sample(self) -> dict[str, AdvantageContact]:
        return {contact.sample_id: contact for contact in self.contacts}

    def instruction_by_sample(self) -> dict[str, str]:
        """``{sample_id: rendered instruction}`` -- the ONE accessor a phase
        binding uses to make each row's instruction its own. Text, never a
        receipt value."""

        return {contact.sample_id: contact.instruction for contact in self.contacts}

    def as_json(self) -> dict[str, object]:
        return {
            "schema": ADVANTAGE_MATERIAL_SCHEMA,
            "arm": STAGE3_ADVANTAGE_ARM,
            "phase": STAGE3_ADVANTAGE_PHASE_NAME,
            "rollout_run_id": self.rollout_run_id,
            "rollout_attempt_id": self.rollout_attempt_id,
            "pairs": dict(self.pairs_binding),
            "instruction_template": {
                "relpath": self.template_relpath,
                "sha256": self.template_sha256,
            },
            "contacts": [contact.as_json() for contact in self.contacts],
            "bound_target_count": len(self.bound_targets),
            "bound_target_sample_ids": [
                str(entry["sample_id"]) for entry in self.bound_targets
            ],
        }


# ---------------------------------------------------------------------------
# Building it.
# ---------------------------------------------------------------------------


def _pairs_declaration(values: Mapping[str, object]) -> Mapping[str, object]:
    block = values.get("advantage_pairs")
    if not isinstance(block, Mapping) or not block:
        raise Stage3AdvantageMaterialError(
            "a construction-advantage flight's baseline fragment must declare an "
            "'advantage_pairs' object (S3-3's pairs.json: its data-root relpath, its "
            "sha256 and the rollout run/attempt it was built from)"
        )
    missing = [key for key in _REQUIRED_PAIRS_KEYS if not str(block.get(key) or "")]
    if missing:
        raise Stage3AdvantageMaterialError(
            f"advantage_pairs is missing {missing}; the required keys are "
            f"{list(_REQUIRED_PAIRS_KEYS)}"
        )
    relpath = str(block["relpath"])
    if Path(relpath).is_absolute() or ".." in Path(relpath).parts:
        raise Stage3AdvantageMaterialError(
            f"advantage_pairs.relpath {relpath!r} is not a plain relative path under "
            "the data root"
        )
    return block


def _template(values: Mapping[str, object], repo_root: Path) -> tuple[str, str, str]:
    """``(relpath, text, sha256)`` for the phase's own per-row template.

    Read through the fragment's ``phase_material.advantage.instruction_template``
    rather than through the module constant alone, and then REFUSED unless the
    two agree: that is what stops a launcher and a fragment drifting apart
    silently (``rails.stage3_advantage.STAGE3_ADVANTAGE_TEMPLATE_RELPATH_V2``).
    """

    material = values.get("phase_material")
    entry = material.get(STAGE3_ADVANTAGE_PHASE_NAME) if isinstance(material, Mapping) else None
    declared = entry.get("instruction_template") if isinstance(entry, Mapping) else None
    if not isinstance(declared, str) or not declared:
        raise Stage3AdvantageMaterialError(
            "a construction-advantage flight's baseline fragment must declare "
            f"phase_material[{STAGE3_ADVANTAGE_PHASE_NAME!r}].instruction_template"
        )
    if declared != STAGE3_ADVANTAGE_TEMPLATE_RELPATH_V2:
        raise Stage3AdvantageMaterialError(
            f"phase_material[{STAGE3_ADVANTAGE_PHASE_NAME!r}].instruction_template is "
            f"{declared!r}, not the pinned "
            f"{STAGE3_ADVANTAGE_TEMPLATE_RELPATH_V2!r}; the fragment and "
            "rails.stage3_advantage must name one template"
        )
    path = Path(repo_root) / "configs" / declared
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise Stage3AdvantageMaterialError(
            f"advantage instruction template missing: {path}"
        ) from error
    text = raw.decode("utf-8")
    if not text.strip():
        raise Stage3AdvantageMaterialError(f"advantage instruction template is empty: {path}")
    return declared, text, hashlib.sha256(raw).hexdigest()


def _trajectories(document: Mapping[str, object]) -> dict[str, Mapping[str, object]]:
    """``{sample_id: trajectory}`` from ``pairs.json``'s own ``pairs`` array.

    A v1 ``pairs.json`` carries no ``pairs`` array at all; this returns an
    empty map for it and every row then renders its trajectory sections as
    ``(none recorded in the sealed trajectory)`` rather than refusing -- the
    same "retain, mark, never drop" discipline the v2 parser follows.
    """

    rows = document.get("pairs")
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        return {}
    out: dict[str, Mapping[str, object]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        sample_id = row.get("sample_id")
        trajectory = row.get("trajectory")
        if isinstance(sample_id, str) and sample_id and isinstance(trajectory, Mapping):
            out[sample_id] = trajectory
    return out


def _sealed_rollout_rows(
    data_root: Path, run_id: str, attempt_id: str, wanted: Sequence[str]
) -> dict[str, Mapping[str, object]]:
    """The sealed rollout rows of EXACTLY ``wanted``, streamed from the
    sealed ``<run_id>.outputs.jsonl`` custody.

    Read-only, one pass, and nothing outside ``wanted`` is retained. The
    sealed bundle is never written, moved or re-sealed here.
    """

    directory = Path(data_root) / "runs" / str(run_id) / str(attempt_id)
    path = directory / f"{run_id}.outputs.jsonl"
    if not path.is_file():
        raise Stage3AdvantageMaterialError(
            f"the sealed rollout custody this material renders from is missing: {path}"
        )
    keep = set(wanted)
    rows: dict[str, Mapping[str, object]] = {}
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as error:
                raise Stage3AdvantageMaterialError(
                    f"sealed rollout custody {path} carries a malformed row: {error}"
                ) from error
            if not isinstance(row, Mapping):
                continue
            sample_id = row.get("sample_id")
            if isinstance(sample_id, str) and sample_id in keep:
                rows[sample_id] = row
    missing = sorted(keep - set(rows))
    if missing:
        raise Stage3AdvantageMaterialError(
            f"{len(missing)} flown row(s) have no sealed rollout custody in {path}; "
            f"first: {missing[0]}"
        )
    return rows


def _rendered_sample(
    row: Mapping[str, object], sample_id: str, index: int, expected_sha256: str
) -> str:
    """Render sample ``index`` of ``row``'s ``solver_group`` custody and prove
    it is the exact text ``pairs.json`` pinned."""

    group = row.get("solver_group")
    records = group.get("samples") if isinstance(group, Mapping) else None
    if not isinstance(records, Sequence) or isinstance(records, (str, bytes)):
        raise Stage3AdvantageMaterialError(
            f"sealed row {sample_id!r} carries no solver_group custody to render"
        )
    by_index = {
        int(record["sample_index"]): record
        for record in records
        if isinstance(record, Mapping)
        and isinstance(record.get("sample_index"), int)
        and not isinstance(record.get("sample_index"), bool)
    }
    record = by_index.get(index)
    if record is None:
        raise Stage3AdvantageMaterialError(
            f"sealed row {sample_id!r} carries no solver sample {index}"
        )
    payload = record.get("parsed_answer") if record.get("parse_status") == "ok" else None
    text = render_rollout_answer(payload)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    if digest != expected_sha256:
        raise Stage3AdvantageMaterialError(
            f"row {sample_id!r} sample {index} renders to {digest}, not the "
            f"{expected_sha256} pairs.json pinned; the sealed custody and the prepared "
            "pair artifact disagree and no contact may be made on either"
        )
    return text


def _delivered_answer(row: Mapping[str, object], sample_id: str) -> str:
    text = row.get("text")
    if not isinstance(text, str) or not text:
        raise Stage3AdvantageMaterialError(
            f"sealed row {sample_id!r} carries no delivered answer text"
        )
    return text


def build_advantage_material(
    values: Mapping[str, object],
    *,
    lock: Mapping[str, object] | None,
    data_root: Path,
    repo_root: Path,
    samples: Sequence[object],
) -> AdvantageMaterial:
    """Render every ADV-1 contact this flight will make.

    The ``construction_material_resolver`` seam's second implementation, with
    the SAME signature the proposer default has, so
    ``core.flight.FlightRuntime.construction_material`` dispatches on the arm
    and nothing else changes.
    """

    from ..data.slurp import load_slurp_train_construction_rows  # noqa: PLC0415

    carrier = str(values.get("carrier_lock_key") or "")
    if carrier and carrier != ADVANTAGE_CARRIER_LOCK_KEY:
        raise Stage3AdvantageMaterialError(
            f"the construction-advantage arm reads gold through SLURP TRAIN's own "
            f"governed loader; carrier {carrier!r} has no reader here"
        )
    if lock is None:
        raise Stage3AdvantageMaterialError(
            "the construction-advantage arm needs the umbrella lock to resolve the "
            "governed SLURP TRAIN metadata its gold is read from"
        )

    block = _pairs_declaration(values)
    relpath = str(block["relpath"])
    pairs_path = Path(data_root) / relpath
    template_relpath, template_text, template_sha256 = _template(values, repo_root)

    try:
        pairs: AdvantagePairs = load_advantage_pairs(
            pairs_path,
            repo_root=repo_root,
            expected_sha256=str(block["sha256"]),
            expected_rollout_run_id=str(block["rollout_run_id"]),
        )
    except Stage3AdvantageError as error:
        raise Stage3AdvantageMaterialError(str(error)) from None
    by_sample = pairs.by_sample()

    try:
        document = json.loads(pairs_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise Stage3AdvantageMaterialError(f"pairs.json unreadable: {error}") from error
    trajectories = _trajectories(document if isinstance(document, Mapping) else {})

    sample_ids: list[str] = []
    for sample in samples:
        sample_id = getattr(sample, "sample_id", None)
        if not isinstance(sample_id, str) or not sample_id:
            raise Stage3AdvantageMaterialError(
                "every flown sample must carry a non-empty sample_id"
            )
        sample_ids.append(sample_id)
    if not sample_ids:
        raise Stage3AdvantageMaterialError(
            "a construction-advantage flight resolved zero rows; there is nothing to fly"
        )
    if len(set(sample_ids)) != len(sample_ids):
        raise Stage3AdvantageMaterialError("this flight's split repeats a sample id")
    outside = [sample_id for sample_id in sample_ids if sample_id not in by_sample]
    if outside:
        raise Stage3AdvantageMaterialError(
            f"{len(outside)} flown row(s) are not in the disagreeing population "
            f"pairs.json names; first: {outside[0]}. The cell's population must be a "
            "subset of the prepared pairs"
        )

    sealed = _sealed_rollout_rows(
        data_root, str(block["rollout_run_id"]), str(block["rollout_attempt_id"]), sample_ids
    )
    gold_rows = load_slurp_train_construction_rows(lock, Path(data_root), sample_ids)

    contacts: list[AdvantageContact] = []
    bound: dict[str, str] = {}
    for sample_id in sample_ids:
        pair: AdvantagePair = by_sample[sample_id]
        row = sealed[sample_id]
        trajectory = trajectories.get(sample_id) or {}
        best_text = _rendered_sample(
            row, sample_id, pair.best.sample_index, pair.best.response_text_sha256
        )
        worst_text = _rendered_sample(
            row, sample_id, pair.worst.sample_index, pair.worst.response_text_sha256
        )
        delivered_text = _delivered_answer(row, sample_id)
        gold_row = gold_rows.get(sample_id)
        if gold_row is None:
            raise Stage3AdvantageMaterialError(
                f"row {sample_id!r} has no governed SLURP TRAIN construction gold"
            )
        gold_text = render_construction_gold(gold_row)

        perception = trajectory.get("perception")
        candidate_ids = tuple(
            str(item)
            for item in (
                perception.get("candidate_intent_ids", ())
                if isinstance(perception, Mapping)
                else ()
            )
            if isinstance(item, str) and item
        )
        delivered = trajectory.get("delivered")
        delivered = delivered if isinstance(delivered, Mapping) else {}
        marks = delivered.get("reviewer_verdicts")
        marks = [m for m in marks if isinstance(m, Mapping)] if isinstance(marks, list) else []
        routes = delivered.get("planner_actions")
        routes = [r for r in routes if isinstance(r, Mapping)] if isinstance(routes, list) else []
        revision_count = delivered.get("revision_count")
        revision_count = (
            int(revision_count)
            if isinstance(revision_count, int) and not isinstance(revision_count, bool)
            else 0
        )

        raw_candidate_count = (
            perception.get("raw_candidate_count") if isinstance(perception, Mapping) else None
        )
        delivered_kind = str(delivered.get("kind") or "unavailable")
        instruction = build_advantage_instruction_for_row_v2(
            template_text,
            pair,
            candidate_list_text=render_candidate_list(
                candidate_ids, raw_count=raw_candidate_count
            ),
            best_answer_text=best_text,
            worst_answer_text=worst_text,
            delivered_answer_text=delivered_text,
            reviewer_verdicts_text=render_reviewer_verdicts(marks),
            planner_route_text=render_planner_route(
                routes, delivered_kind=delivered_kind, revision_count=revision_count
            ),
            gold_text=gold_text,
        )
        contacts.append(
            AdvantageContact(
                sample_id=sample_id,
                instruction=instruction,
                prompt_sha256=hashlib.sha256(instruction.encode("utf-8")).hexdigest(),
                construction_target_ids=(sample_id,),
                best_sample_index=pair.best.sample_index,
                worst_sample_index=pair.worst.sample_index,
                best_answer_sha256=pair.best.response_text_sha256,
                worst_answer_sha256=pair.worst.response_text_sha256,
                delivered_answer_sha256=hashlib.sha256(
                    delivered_text.encode("utf-8")
                ).hexdigest(),
                gold_sha256=hashlib.sha256(gold_text.encode("utf-8")).hexdigest(),
                candidate_intent_ids=candidate_ids,
                reviewer_verdict_dispositions=tuple(
                    str(mark.get("token") or mark.get("disposition") or "unavailable")
                    for mark in marks
                ),
                planner_actions=tuple(
                    str(route.get("action") or "unavailable") for route in routes
                ),
                delivered_kind=delivered_kind,
                revision_count=revision_count,
                trajectory_available=bool(trajectory.get("available")),
            )
        )
        bound[sample_id] = gold_text

    return AdvantageMaterial(
        contacts=tuple(contacts),
        bound_targets=tuple(
            {"sample_id": sample_id, "target": bound[sample_id]}
            for sample_id in sorted(bound)
        ),
        pairs_binding=pairs.receipt(),
        rollout_run_id=str(block["rollout_run_id"]),
        rollout_attempt_id=str(block["rollout_attempt_id"]),
        template_relpath=template_relpath,
        template_sha256=template_sha256,
    )


__all__ = [
    "ADVANTAGE_CONTACT_SCHEMA",
    "ADVANTAGE_MATERIAL_SCHEMA",
    "EMPTY_ANSWER",
    "AdvantageContact",
    "AdvantageMaterial",
    "Stage3AdvantageMaterialError",
    "build_advantage_material",
    "render_candidate_list",
    "render_construction_gold",
    "render_planner_route",
    "render_reviewer_verdicts",
    "render_rollout_answer",
]
