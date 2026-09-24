"""Stage-3 layer A, the GEPA arm: the flight-time per-GROUP material.

The SIBLING of ``rails.stage3_advantage_material`` on the SAME
``construction_material_resolver`` seam and the SAME construction-visible arm.
What differs is the unit: ADV-1 renders one instruction per disagreeing ROW,
this module renders one instruction per (scenario, node) GROUP, carried by that
group's CARRIER row (the flight's row id; see
``scripts/build_slurp_stage3_gepa_groups.py`` for why a group needs one).

Nothing here is rebuilt that ADV-1 already built. The four row renderers
(``render_candidate_list``, ``render_rollout_answer``, ``render_construction_gold``,
``render_reviewer_verdicts``, ``render_planner_route``), the sealed-custody
reader and the per-sample digest verification are imported from
``rails.stage3_advantage_material`` and used unchanged, so one row of a
trajectory reads identically in both arms and neither arm owns a second copy of
the grammar.

What it reads, all of it committed or hash-pinned by the composed config:

* ``gepa_groups`` -- the prepared groups artifact under the DATA root, pinned by
  ``sha256`` and bound to the rollout ``run_id``/``attempt_id`` that produced the
  trajectories it indexes;
* the artifact's OWN pins, each verified here rather than trusted: S3-3's
  ``pairs.json`` (the trajectories and the per-sample answer digests) and the
  released v1r authored-deltas document (the node's CURRENT statements);
* that same rollout's SEALED ``<run_id>.outputs.jsonl`` custody, from which every
  group row's best and worst Solver answers are re-rendered and then VERIFIED
  against the digest ``pairs.json`` pinned;
* each group row's own CONSTRUCTION GOLD, read at flight time from the governed
  SLURP TRAIN metadata (owner decision 82; the flying cell's split identity is
  bound to a committed ``roster_role == "construction"`` receipt by
  ``contracts.gate_exposure._require_construction_role_for_visible_targets``).

Where the rendered text goes: into ONE place, the contact's ``instruction``,
through ``rails.stage3_gepa.render_gepa_instruction``. Nothing this module
returns for a receipt carries an utterance, an answer, a gold label or a delta
statement: :meth:`GepaContact.as_json` seals identities, counts and digests
only.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from .stage3_advantage import (
    AdvantagePair,
    AdvantagePairs,
    Stage3AdvantageError,
    load_advantage_pairs,
)
from .stage3_advantage_material import (
    Stage3AdvantageMaterialError,
    _delivered_answer,
    _sealed_rollout_rows,
    _rendered_sample,
    _trajectories,
    render_candidate_list,
    render_construction_gold,
    render_planner_route,
    render_reviewer_verdicts,
)
from .stage3_gepa import (
    LEGAL_GEPA_NODES,
    STAGE3_GEPA_ARM,
    STAGE3_GEPA_PHASE_NAME,
    STAGE3_GEPA_TEMPLATE_RELPATH,
    render_current_deltas,
    render_gepa_instruction,
    render_group_row_block,
)

GEPA_MATERIAL_SCHEMA = "saea-stage3-gepa-material-v1"
GEPA_CONTACT_SCHEMA = "saea-stage3-gepa-contact-v1"
GROUPS_SCHEMA = "saea-stage3-gepa-groups-v1"

#: The carrier this material can read gold for, exactly as ADV-1 declares it.
GEPA_CARRIER_LOCK_KEY = "slurp"

#: The exact keys the baseline fragment's ``gepa_groups`` block must carry.
_REQUIRED_GROUPS_KEYS = (
    "relpath",
    "sha256",
    "rollout_run_id",
    "rollout_attempt_id",
)

WORSE_LABEL = "WORSE OUTCOME"
BETTER_LABEL = "BETTER OUTCOME"


class Stage3GepaMaterialError(Stage3AdvantageMaterialError):
    """A ``gepa_groups`` declaration, a pinned input, a sealed custody read or a
    per-group render is malformed or disagrees with what the artifact pinned.

    A SUBCLASS of the ADV-1 error on purpose: ``core.flight.runtime`` already
    converts that error into a ``FlightRuntimeError`` at the seam, so the GEPA
    branch fails closed through the same clause rather than through a second
    one that could drift.
    """


# ---------------------------------------------------------------------------
# The contact and the material.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GepaContact:
    """One rendered, flyable GEPA reflection contact.

    ``instruction`` is the whole rendered per-group phase instruction and is the
    ONLY place this group's trajectories, construction gold and current delta
    statements are ever combined. It is never written to a receipt:
    :meth:`as_json` is what a receipt may record.
    """

    group_id: str
    scenario: str
    node: str
    sample_id: str
    carrier_from: str
    instruction: str
    prompt_sha256: str
    construction_target_ids: tuple
    worst_sample_ids: tuple
    best_sample_ids: tuple
    current_delta_value_ids: tuple
    row_digests: tuple

    @property
    def draw_id(self) -> str:
        """The contact's own stable id -- the group, not the carrier row."""

        return self.group_id

    def as_json(self) -> dict:
        """Everything a receipt may record about this contact -- identity,
        counts and digests, never the rendered text."""

        return {
            "schema": GEPA_CONTACT_SCHEMA,
            "draw_id": self.draw_id,
            "group_id": self.group_id,
            "scenario": self.scenario,
            "node": self.node,
            "sample_id": self.sample_id,
            "carrier_from": self.carrier_from,
            "carrier_is_a_group_row": self.sample_id in self.construction_target_ids,
            "worst_sample_ids": list(self.worst_sample_ids),
            "best_sample_ids": list(self.best_sample_ids),
            "row_count": len(self.construction_target_ids),
            "current_delta_value_ids": list(self.current_delta_value_ids),
            "current_delta_count": len(self.current_delta_value_ids),
            "rows": [dict(row) for row in self.row_digests],
            "prompt_sha256": self.prompt_sha256,
            "prompt_characters": len(self.instruction),
            "declared_construction_targets": len(self.construction_target_ids),
        }


@dataclass(frozen=True)
class GepaMaterial:
    """Every contact one GEPA flight makes, plus the gold it may show.

    ``bound_targets`` is the UNION of every group's rows and their construction
    gold -- what ``rails.core_client.FrozenCoreClient`` is constructed with --
    and each contact then names EXACTLY its own group's rows, so a request
    narrows the bound set and can never widen it (the invariant
    ``rails.evolution.ProposerMaterial`` and
    ``rails.stage3_advantage_material.AdvantageMaterial`` both document).
    """

    contacts: tuple
    bound_targets: tuple
    groups_binding: Mapping[str, object]
    pairs_binding: Mapping[str, object]
    deltas_binding: Mapping[str, object]
    rollout_run_id: str
    rollout_attempt_id: str
    template_relpath: str
    template_sha256: str

    def by_sample(self) -> dict:
        return {contact.sample_id: contact for contact in self.contacts}

    def by_group(self) -> dict:
        return {contact.group_id: contact for contact in self.contacts}

    def instruction_by_sample(self) -> dict:
        """``{carrier sample_id: rendered instruction}`` -- the ONE accessor a
        phase binding uses. Text, never a receipt value."""

        return {contact.sample_id: contact.instruction for contact in self.contacts}

    def as_json(self) -> dict:
        return {
            "schema": GEPA_MATERIAL_SCHEMA,
            "arm": STAGE3_GEPA_ARM,
            "phase": STAGE3_GEPA_PHASE_NAME,
            "rollout_run_id": self.rollout_run_id,
            "rollout_attempt_id": self.rollout_attempt_id,
            "groups": dict(self.groups_binding),
            "pairs": dict(self.pairs_binding),
            "deltas": dict(self.deltas_binding),
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
# Reading the pinned inputs.
# ---------------------------------------------------------------------------


def _groups_declaration(values: Mapping[str, object]) -> Mapping[str, object]:
    block = values.get("gepa_groups")
    if not isinstance(block, Mapping) or not block:
        raise Stage3GepaMaterialError(
            "a GEPA flight's baseline fragment must declare a 'gepa_groups' object "
            "(the prepared groups artifact: its data-root relpath, its sha256 and the "
            "rollout run/attempt whose sealed trajectories it indexes)"
        )
    missing = [key for key in _REQUIRED_GROUPS_KEYS if not str(block.get(key) or "")]
    if missing:
        raise Stage3GepaMaterialError(
            f"gepa_groups is missing {missing}; the required keys are "
            f"{list(_REQUIRED_GROUPS_KEYS)}"
        )
    relpath = str(block["relpath"])
    if Path(relpath).is_absolute() or ".." in Path(relpath).parts:
        raise Stage3GepaMaterialError(
            f"gepa_groups.relpath {relpath!r} is not a plain relative path under the "
            "data root"
        )
    return block


def _load_pinned_json(path: Path, expected_sha256: str, *, what: str) -> Mapping[str, object]:
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise Stage3GepaMaterialError(f"{what} is missing: {path}") from error
    digest = hashlib.sha256(raw).hexdigest()
    if expected_sha256 and digest != expected_sha256:
        raise Stage3GepaMaterialError(
            f"{what} {path} hashes to {digest}, not the pinned {expected_sha256}"
        )
    try:
        document = json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise Stage3GepaMaterialError(f"{what} is not valid UTF-8 JSON: {error}") from error
    if not isinstance(document, Mapping):
        raise Stage3GepaMaterialError(f"{what} must be a JSON object")
    return document


def _template(values: Mapping[str, object], repo_root: Path) -> tuple:
    """``(relpath, text, sha256)`` for the phase's own per-group template.

    Read through the fragment's ``phase_material.gepa.instruction_template`` and
    then REFUSED unless it is the pinned module constant: a launcher and a
    fragment that drift apart silently is the defect this check exists for
    (``rails.stage3_advantage_material._template``, same rule).
    """

    material = values.get("phase_material")
    entry = material.get(STAGE3_GEPA_PHASE_NAME) if isinstance(material, Mapping) else None
    declared = entry.get("instruction_template") if isinstance(entry, Mapping) else None
    if not isinstance(declared, str) or not declared:
        raise Stage3GepaMaterialError(
            "a GEPA flight's baseline fragment must declare "
            f"phase_material[{STAGE3_GEPA_PHASE_NAME!r}].instruction_template"
        )
    if declared != STAGE3_GEPA_TEMPLATE_RELPATH:
        raise Stage3GepaMaterialError(
            f"phase_material[{STAGE3_GEPA_PHASE_NAME!r}].instruction_template is "
            f"{declared!r}, not the pinned {STAGE3_GEPA_TEMPLATE_RELPATH!r}; the "
            "fragment and rails.stage3_gepa must name one template"
        )
    path = Path(repo_root) / "configs" / declared
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise Stage3GepaMaterialError(f"gepa instruction template missing: {path}") from error
    text = raw.decode("utf-8")
    if not text.strip():
        raise Stage3GepaMaterialError(f"gepa instruction template is empty: {path}")
    return declared, text, hashlib.sha256(raw).hexdigest()


def _delta_contents(document: Mapping[str, object]) -> dict:
    """``{value_id: content}`` from the pinned authored-deltas document.

    The ONE place delta statement text is read. It goes into the instruction
    and nowhere else.
    """

    rows = document.get("rows")
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)) or not rows:
        raise Stage3GepaMaterialError("the authored-deltas document carries no rows")
    out: dict = {}
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise Stage3GepaMaterialError(f"authored rows[{index}] must be an object")
        value_id = row.get("value_id")
        content = row.get("content")
        if not isinstance(value_id, str) or not value_id:
            raise Stage3GepaMaterialError(f"authored rows[{index}] has no value_id")
        if not isinstance(content, str) or not content:
            raise Stage3GepaMaterialError(f"authored rows[{index}] has no content")
        out[value_id] = content
    return out


def _validate_groups(document: Mapping[str, object]) -> list:
    if str(document.get("schema") or "") != GROUPS_SCHEMA:
        raise Stage3GepaMaterialError(
            f"the groups artifact must declare schema {GROUPS_SCHEMA!r}"
        )
    groups = document.get("groups")
    if not isinstance(groups, Sequence) or isinstance(groups, (str, bytes)) or not groups:
        raise Stage3GepaMaterialError("the groups artifact carries no non-empty 'groups'")
    seen_ids = set()
    seen_carriers = set()
    out = []
    for index, group in enumerate(groups):
        if not isinstance(group, Mapping):
            raise Stage3GepaMaterialError(f"groups[{index}] must be an object")
        group_id = group.get("group_id")
        node = group.get("node")
        scenario = group.get("scenario")
        carrier = group.get("carrier_sample_id")
        rows = group.get("row_sample_ids")
        if not isinstance(group_id, str) or not group_id:
            raise Stage3GepaMaterialError(f"groups[{index}] has no group_id")
        if node not in LEGAL_GEPA_NODES:
            raise Stage3GepaMaterialError(
                f"groups[{index}] node {node!r} is not one of {list(LEGAL_GEPA_NODES)}"
            )
        if not isinstance(scenario, str) or not scenario:
            raise Stage3GepaMaterialError(f"groups[{index}] has no scenario")
        if not isinstance(carrier, str) or not carrier:
            raise Stage3GepaMaterialError(f"groups[{index}] has no carrier_sample_id")
        if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)) or not rows:
            raise Stage3GepaMaterialError(f"groups[{index}] has no row_sample_ids")
        if group_id in seen_ids:
            raise Stage3GepaMaterialError(f"the groups artifact repeats {group_id!r}")
        if carrier in seen_carriers:
            raise Stage3GepaMaterialError(
                f"carrier {carrier!r} is used by two groups; a flight makes one contact "
                "per flown row"
            )
        seen_ids.add(group_id)
        seen_carriers.add(carrier)
        out.append(group)
    return out


# ---------------------------------------------------------------------------
# Building it.
# ---------------------------------------------------------------------------


def _row_block(
    *,
    position: int,
    label: str,
    pair: AdvantagePair,
    sealed_row: Mapping[str, object],
    trajectory: Mapping[str, object],
    gold_text: str,
) -> tuple:
    """``(rendered block, digest record)`` for ONE row of a group."""

    sample_id = pair.sample_id
    best_text = _rendered_sample(
        sealed_row, sample_id, pair.best.sample_index, pair.best.response_text_sha256
    )
    worst_text = _rendered_sample(
        sealed_row, sample_id, pair.worst.sample_index, pair.worst.response_text_sha256
    )
    delivered_text = _delivered_answer(sealed_row, sample_id)

    perception = trajectory.get("perception")
    perception = perception if isinstance(perception, Mapping) else {}
    candidate_ids = tuple(
        str(item)
        for item in (perception.get("candidate_intent_ids") or ())
        if isinstance(item, str) and item
    )
    delivered = trajectory.get("delivered")
    delivered = delivered if isinstance(delivered, Mapping) else {}
    marks = delivered.get("reviewer_verdicts")
    marks = [mark for mark in marks if isinstance(mark, Mapping)] if isinstance(marks, list) else []
    routes = delivered.get("planner_actions")
    routes = [route for route in routes if isinstance(route, Mapping)] if isinstance(routes, list) else []
    revision_count = delivered.get("revision_count")
    revision_count = (
        int(revision_count)
        if isinstance(revision_count, int) and not isinstance(revision_count, bool)
        else 0
    )
    delivered_kind = str(delivered.get("kind") or "unavailable")

    block = render_group_row_block(
        position=position,
        label=label,
        candidate_list_text=render_candidate_list(
            candidate_ids, raw_count=perception.get("raw_candidate_count")
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
    digest = {
        "sample_id": sample_id,
        "side": label,
        "position": position,
        "best_sample_index": pair.best.sample_index,
        "worst_sample_index": pair.worst.sample_index,
        "best_answer_sha256": pair.best.response_text_sha256,
        "worst_answer_sha256": pair.worst.response_text_sha256,
        "delivered_answer_sha256": hashlib.sha256(
            delivered_text.encode("utf-8")
        ).hexdigest(),
        "gold_sha256": hashlib.sha256(gold_text.encode("utf-8")).hexdigest(),
        "candidate_count": len(candidate_ids),
        "reviewer_visit_count": len(marks),
        "planner_route_length": len(routes),
        "delivered_kind": delivered_kind,
        "revision_count": revision_count,
        "trajectory_available": bool(trajectory.get("available")),
    }
    return block, digest


def build_gepa_material(
    values: Mapping[str, object],
    *,
    lock: Mapping[str, object] | None,
    data_root: Path,
    repo_root: Path,
    samples: Sequence[object],
) -> GepaMaterial:
    """Render every GEPA contact this flight will make.

    The THIRD implementation of the ``construction_material_resolver`` seam,
    with the SAME signature the other two have, so
    ``core.flight.FlightRuntime.construction_material`` dispatches and nothing
    else changes.
    """

    from ..data.slurp import load_slurp_train_construction_rows  # noqa: PLC0415

    carrier = str(values.get("carrier_lock_key") or "")
    if carrier and carrier != GEPA_CARRIER_LOCK_KEY:
        raise Stage3GepaMaterialError(
            "the GEPA arm reads gold through SLURP TRAIN's own governed loader; "
            f"carrier {carrier!r} has no reader here"
        )
    if lock is None:
        raise Stage3GepaMaterialError(
            "the GEPA arm needs the umbrella lock to resolve the governed SLURP TRAIN "
            "metadata its gold is read from"
        )

    block = _groups_declaration(values)
    data_root = Path(data_root)
    groups_path = data_root / str(block["relpath"])
    groups_document = _load_pinned_json(
        groups_path, str(block["sha256"]), what="the GEPA groups artifact"
    )
    template_relpath, template_text, template_sha256 = _template(values, Path(repo_root))

    declared_run = str(block["rollout_run_id"])
    declared_attempt = str(block["rollout_attempt_id"])
    if str(groups_document.get("rollout_run_id") or "") != declared_run:
        raise Stage3GepaMaterialError(
            "the groups artifact was built from rollout run "
            f"{groups_document.get('rollout_run_id')!r}, not the declared {declared_run!r}"
        )
    if str(groups_document.get("rollout_attempt_id") or "") != declared_attempt:
        raise Stage3GepaMaterialError(
            "the groups artifact was built from rollout attempt "
            f"{groups_document.get('rollout_attempt_id')!r}, not the declared "
            f"{declared_attempt!r}"
        )

    # The artifact's OWN pins, verified rather than trusted.
    pairs_pin = groups_document.get("pairs")
    deltas_pin = groups_document.get("deltas")
    if not isinstance(pairs_pin, Mapping) or not isinstance(deltas_pin, Mapping):
        raise Stage3GepaMaterialError(
            "the groups artifact must pin both 'pairs' and 'deltas' by relpath and sha256"
        )
    pairs_path = data_root / str(pairs_pin.get("relpath") or "")
    deltas_path = data_root / str(deltas_pin.get("relpath") or "")
    pairs_document = _load_pinned_json(
        pairs_path, str(pairs_pin.get("sha256") or ""), what="S3-3's pairs.json"
    )
    deltas_document = _load_pinned_json(
        deltas_path,
        str(deltas_pin.get("sha256") or ""),
        what="the authored-deltas document the groups artifact pins",
    )
    delta_contents = _delta_contents(deltas_document)

    try:
        pairs: AdvantagePairs = load_advantage_pairs(
            pairs_path, repo_root=repo_root, expected_rollout_run_id=declared_run
        )
    except Stage3AdvantageError as error:
        raise Stage3GepaMaterialError(str(error)) from None
    pair_by_sample = pairs.by_sample()
    trajectories = _trajectories(pairs_document)

    groups = _validate_groups(groups_document)
    by_carrier = {str(group["carrier_sample_id"]): group for group in groups}

    sample_ids = []
    for sample in samples:
        sample_id = getattr(sample, "sample_id", None)
        if not isinstance(sample_id, str) or not sample_id:
            raise Stage3GepaMaterialError(
                "every flown sample must carry a non-empty sample_id"
            )
        sample_ids.append(sample_id)
    if not sample_ids:
        raise Stage3GepaMaterialError(
            "a GEPA flight resolved zero rows; there is nothing to fly"
        )
    if len(set(sample_ids)) != len(sample_ids):
        raise Stage3GepaMaterialError("this flight's split repeats a sample id")
    outside = [sample_id for sample_id in sample_ids if sample_id not in by_carrier]
    if outside:
        raise Stage3GepaMaterialError(
            f"{len(outside)} flown row(s) carry no GEPA group in the prepared artifact; "
            f"first: {outside[0]}. The cell's population must be exactly the carrier rows"
        )

    flown_groups = [by_carrier[sample_id] for sample_id in sample_ids]
    needed_rows = sorted(
        {str(row) for group in flown_groups for row in group["row_sample_ids"]}
    )
    unpaired = [row for row in needed_rows if row not in pair_by_sample]
    if unpaired:
        raise Stage3GepaMaterialError(
            f"{len(unpaired)} group row(s) are not in the disagreeing population "
            f"pairs.json names; first: {unpaired[0]}"
        )
    sealed = _sealed_rollout_rows(data_root, declared_run, declared_attempt, needed_rows)
    gold_rows = load_slurp_train_construction_rows(lock, data_root, needed_rows)
    gold_text_by_sample = {}
    for sample_id in needed_rows:
        gold_row = gold_rows.get(sample_id)
        if gold_row is None:
            raise Stage3GepaMaterialError(
                f"row {sample_id!r} has no governed SLURP TRAIN construction gold"
            )
        gold_text_by_sample[sample_id] = render_construction_gold(gold_row)

    contacts = []
    for group in flown_groups:
        scenario = str(group["scenario"])
        node = str(group["node"])
        worst_ids = [str(row) for row in (group.get("worst_sample_ids") or ())]
        best_ids = [str(row) for row in (group.get("best_sample_ids") or ())]
        ordered = [str(row) for row in group["row_sample_ids"]]
        current_ids = [str(item) for item in (group.get("current_delta_value_ids") or ())]
        missing_delta = [item for item in current_ids if item not in delta_contents]
        if missing_delta:
            raise Stage3GepaMaterialError(
                f"group {group['group_id']!r} pins {len(missing_delta)} delta value id(s) "
                f"the authored document does not carry; first: {missing_delta[0]}"
            )

        blocks_worst = []
        blocks_best = []
        digests = []
        for position, sample_id in enumerate(worst_ids, start=1):
            block_text, digest = _row_block(
                position=position,
                label=WORSE_LABEL,
                pair=pair_by_sample[sample_id],
                sealed_row=sealed[sample_id],
                trajectory=trajectories.get(sample_id) or {},
                gold_text=gold_text_by_sample[sample_id],
            )
            blocks_worst.append(block_text)
            digests.append(digest)
        for position, sample_id in enumerate(best_ids, start=1):
            block_text, digest = _row_block(
                position=position,
                label=BETTER_LABEL,
                pair=pair_by_sample[sample_id],
                sealed_row=sealed[sample_id],
                trajectory=trajectories.get(sample_id) or {},
                gold_text=gold_text_by_sample[sample_id],
            )
            blocks_best.append(block_text)
            digests.append(digest)

        instruction = render_gepa_instruction(
            template_text,
            scenario=scenario,
            node=node,
            current_deltas_text=render_current_deltas(
                [delta_contents[item] for item in current_ids]
            ),
            worst_rows_text="\n\n".join(blocks_worst),
            best_rows_text="\n\n".join(blocks_best),
        )
        contacts.append(
            GepaContact(
                group_id=str(group["group_id"]),
                scenario=scenario,
                node=node,
                sample_id=str(group["carrier_sample_id"]),
                carrier_from=str(group.get("carrier_from") or "group"),
                instruction=instruction,
                prompt_sha256=hashlib.sha256(instruction.encode("utf-8")).hexdigest(),
                construction_target_ids=tuple(ordered),
                worst_sample_ids=tuple(worst_ids),
                best_sample_ids=tuple(best_ids),
                current_delta_value_ids=tuple(current_ids),
                row_digests=tuple(digests),
            )
        )

    bound = {
        sample_id: gold_text_by_sample[sample_id] for sample_id in sorted(needed_rows)
    }
    return GepaMaterial(
        contacts=tuple(contacts),
        bound_targets=tuple(
            {"sample_id": sample_id, "target": bound[sample_id]}
            for sample_id in sorted(bound)
        ),
        groups_binding={
            "relpath": str(block["relpath"]),
            "sha256": str(block["sha256"]),
            "group_count": len(groups),
            "flown_group_count": len(flown_groups),
            "k": groups_document.get("k"),
            "rank_metric": groups_document.get("rank_metric"),
            "scenarios": list(groups_document.get("scenarios") or ()),
            "excluded_scenarios": [
                str(row.get("scenario"))
                for row in (groups_document.get("excluded_scenarios") or ())
                if isinstance(row, Mapping)
            ],
        },
        pairs_binding=pairs.receipt(),
        deltas_binding={
            "relpath": str(deltas_pin.get("relpath") or ""),
            "sha256": str(deltas_pin.get("sha256") or ""),
            "iteration": deltas_pin.get("iteration"),
            "row_count": len(delta_contents),
        },
        rollout_run_id=declared_run,
        rollout_attempt_id=declared_attempt,
        template_relpath=template_relpath,
        template_sha256=template_sha256,
    )


__all__ = [
    "BETTER_LABEL",
    "GEPA_CONTACT_SCHEMA",
    "GEPA_MATERIAL_SCHEMA",
    "GROUPS_SCHEMA",
    "WORSE_LABEL",
    "GepaContact",
    "GepaMaterial",
    "Stage3GepaMaterialError",
    "build_gepa_material",
]
