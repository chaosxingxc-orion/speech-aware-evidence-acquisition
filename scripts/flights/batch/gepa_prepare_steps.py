#!/usr/bin/env python3
"""Helper steps of the GEPA runbook (``scripts/flights/batch/gepa_prepare.sh``).

MODEL-FREE. Zero frozen-core, tool, embedding, encoder, tokenizer, scorer, GPU
and network contacts: every byte read is an already-sealed or committed local
file (the prepared GEPA groups artifact and the committed R01C roster receipt)
and everything written is ids, counts and digests. No utterance text,
transcript, gold label, statement text, scenario answer or model output is
read, printed or persisted.

Four steps, all idempotent:

``roster``
    Write ``docs/receipts/rosters/slurp-stage3-gepa-r01c-carriers-v1.json``: the
    construction-role roster over exactly the CARRIER rows of the prepared GEPA
    groups artifact. It is a PURE SELECTION of the R01C receipt -- every
    surviving item is the parent's item verbatim, in the parent's order -- the
    same shape ``adv1_prepare_steps.py`` builds for ADV-1's disagreeing rows and
    for the same reason: ``construction-advantage-text`` is a
    construction-visible arm, so
    ``contracts.gate_exposure._require_construction_role_for_visible_targets``
    refuses the touch unless the FLYING cell's own ``split_identity_hash`` is
    that of a committed ``roster_role='construction'`` receipt of carrier
    ``slurp``.

``groups-roster``
    Write ``docs/receipts/rosters/slurp-stage3-gepa-r01c-groups-v1.json``: the
    construction-role roster over the UNION of the groups' ``row_sample_ids``
    -- the rows whose rollout trajectories and construction gold a GEPA contact
    was actually shown. That union, not the carriers, is the SOURCE population
    of the GEPA delta store: ``core.semantic_knowledge_preparation`` verifies a
    release registration's ``permitted_roster`` as a committed
    ``roster_role='construction'`` receipt AND requires its split identity to
    equal the registration's ``source_split_identity_hash``, so the store's
    source population needs a committed receipt of its own. The two rosters are
    different populations and both are committed: the CARRIERS receipt is what
    FLEW (one contact per carrier row) and the GROUPS receipt is what the
    store's content may CITE.

``smoke-roster``
    Write ``docs/receipts/rosters/slurp-stage3-gepa-r01c-carriers-smoke-4-v1
    .json``: the carriers of the FIRST SCENARIO's four groups, in the groups
    artifact's own order, as a construction-role roster of their own. Four rows
    that are one scenario's four NODES is the form smoke that exercises all four
    current-delta slices and all four node-fixed parsers at once; the gate knows
    nothing about parent rosters, so those four rows need a committed receipt of
    their own.

``verify``
    Assert that the committed GEPA fragments agree with the freshly built
    artifacts: the groups digest, the two split identities, the contact count
    and the speech-second ceiling. Nothing is filled -- a disagreement is
    printed and exits non-zero, which is what stops a silently re-derived group
    set from flying under a registration that pinned a different one.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

REPO_DEFAULT = Path(__file__).resolve().parents[3]

PARENT_ROSTER = "docs/receipts/rosters/slurp-stage3-construction-r01c.json"
ROSTER_OUT = "docs/receipts/rosters/slurp-stage3-gepa-r01c-carriers-v1.json"
ROSTER_ID = "SLURP-STAGE3-GEPA-R01C-CARRIERS-V1"
GROUPS_ROSTER_OUT = "docs/receipts/rosters/slurp-stage3-gepa-r01c-groups-v1.json"
GROUPS_ROSTER_ID = "SLURP-STAGE3-GEPA-R01C-GROUPS-V1"
SMOKE_ROSTER_OUT = "docs/receipts/rosters/slurp-stage3-gepa-r01c-carriers-smoke-4-v1.json"
SMOKE_ROSTER_ID = "SLURP-STAGE3-GEPA-R01C-CARRIERS-SMOKE-4-V1"
SMOKE_ROWS = 4
CARRIER = "slurp"
DESIGN_NOTE = "docs/superpowers/specs/2026-09-24-slurp-stage3-gepa-arm-design.md"
EXPERIMENT = "configs/experiment/slurp-native-stage3-gepa-r01-v1.json"
SMOKE_EXPERIMENT = "configs/experiment/slurp-native-stage3-gepa-r01-smoke-4-v1.json"
BASELINE = "configs/baseline/slurp-native-stage3-gepa-baseline-v1.json"
SMOKE_BASELINE = "configs/baseline/slurp-native-stage3-gepa-smoke-4-baseline-v1.json"


#: The ``roster_role`` note of the FLOWN rosters: the carrier row is the
#: flight's row identity, the material it carries is its group's.
CARRIER_ROLE_NOTE = (
    "construction: the GEPA contact sees the construction gold of its GROUP's rows "
    "and produces an artifact (a delta proposal), never an answer to an evaluated "
    "row (owner decision 82). The CARRIER row is the flight's row identity; the "
    "material it carries is the group's."
)
#: The ``roster_role`` note of the STORE SOURCE roster: the group rows themselves.
GROUP_ROWS_ROLE_NOTE = (
    "construction: these rows' own construction gold and rollout trajectories were "
    "rendered into the GEPA contact, which produced an artifact (a delta proposal) and "
    "never an answer to an evaluated row (owner decision 82). This roster is the SOURCE "
    "population of the GEPA delta store -- the rows an authored delta may cite -- not "
    "the flown population, which is the carriers receipt."
)


class GepaPrepareError(RuntimeError):
    """An input is missing or does not have the shape this helper needs."""


def _import_repo(repo_root: Path):
    src = repo_root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    from speech_aware_evidence_acquisition.core import roster as roster_module  # noqa: PLC0415
    from speech_aware_evidence_acquisition.data import splits  # noqa: PLC0415

    return roster_module, splits


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise GepaPrepareError(f"{path} is unreadable: {error}") from error


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def group_row_ids(groups_document: Mapping[str, Any]) -> list[str]:
    """The ascending UNION of the groups' ``row_sample_ids``.

    These are the rows a GEPA contact was shown -- their rollout trajectories
    and their construction gold -- and therefore the rows an authored GEPA
    delta may cite. The artifact's own ``group_row_sample_ids`` summary is
    cross-checked against the union rather than trusted, so a re-derived groups
    artifact whose summary drifted from its groups is refused instead of
    silently minting a roster over one of the two.
    """

    groups = groups_document.get("groups")
    if not isinstance(groups, list) or not groups:
        raise GepaPrepareError("the groups artifact carries no non-empty 'groups'")
    union: set[str] = set()
    for index, group in enumerate(groups):
        if not isinstance(group, Mapping):
            raise GepaPrepareError(f"groups[{index}] must be an object")
        rows = group.get("row_sample_ids")
        if not isinstance(rows, list) or not rows:
            raise GepaPrepareError(f"groups[{index}] carries no row_sample_ids")
        for row in rows:
            if not isinstance(row, str) or not row:
                raise GepaPrepareError(f"groups[{index}] has an empty row sample id")
            union.add(row)
    declared = groups_document.get("group_row_sample_ids")
    if declared is not None:
        if not isinstance(declared, list):
            raise GepaPrepareError("group_row_sample_ids must be a list when present")
        if set(declared) != union:
            raise GepaPrepareError(
                "the groups artifact's group_row_sample_ids disagrees with the union of "
                f"the groups' own row_sample_ids ({len(set(declared))} vs {len(union)})"
            )
    return sorted(union)


def carrier_ids(groups_document: Mapping[str, Any]) -> list[str]:
    """The carrier sample ids, in the groups artifact's own (group) order."""

    groups = groups_document.get("groups")
    if not isinstance(groups, list) or not groups:
        raise GepaPrepareError("the groups artifact carries no non-empty 'groups'")
    ids: list[str] = []
    for index, group in enumerate(groups):
        if not isinstance(group, Mapping):
            raise GepaPrepareError(f"groups[{index}] must be an object")
        carrier = group.get("carrier_sample_id")
        if not isinstance(carrier, str) or not carrier:
            raise GepaPrepareError(f"groups[{index}] has no carrier_sample_id")
        ids.append(carrier)
    if len(set(ids)) != len(ids):
        raise GepaPrepareError("the groups artifact repeats a carrier sample id")
    return ids


def _selection_receipt(
    *,
    parent: Mapping[str, Any],
    ids: list[str],
    roster_id: str,
    authority: str,
    selection_rule: str,
    draw_method: str,
    source_pin: Mapping[str, Any],
    splits,
    roster_role_note: str = CARRIER_ROLE_NOTE,
) -> dict[str, Any]:
    """A pure selection of the parent receipt over ``ids``; no draw, no rng."""

    keep = set(ids)
    parent_items = parent.get("items")
    if not isinstance(parent_items, list) or not parent_items:
        raise GepaPrepareError(f"{PARENT_ROSTER} carries no items")
    items = [item for item in parent_items if str(item["sample_id"]) in keep]
    missing = keep - {str(item["sample_id"]) for item in items}
    if missing:
        raise GepaPrepareError(
            f"{len(missing)} selected sample id(s) are not in {PARENT_ROSTER}: "
            f"{sorted(missing)[:3]}"
        )
    counts = dict(sorted(Counter(str(item["stratum"]) for item in items).items()))
    receipt: dict[str, Any] = {
        "schema": parent["schema"],
        "roster_id": roster_id,
        "carrier_lock_key": CARRIER,
        "split_role": "discovery",
        "roster_role": "construction",
        "seed": parent.get("seed"),
        "per_stratum": counts,
        "strata_counts": counts,
        "items": items,
        "excluded_count": len(parent_items) - len(items),
        "split_identity_hash": splits.split_identity_hash(splits.prefixed(CARRIER, ids)),
        "authority": authority,
        "roster_role_note": roster_role_note,
        "draw_method": draw_method,
        "selection_rule": selection_rule,
        "generator": "scripts/flights/batch/gepa_prepare_steps.py",
        "parent": {
            "roster_id": parent.get("roster_id"),
            "count": len(parent_items),
            "relpath": PARENT_ROSTER,
            "split_identity_hash": parent.get("split_identity_hash"),
        },
        "selection_source": dict(source_pin),
        "offline_guard": {"attempted_targets": [], "outbound_connection_attempts": 0},
    }
    for carried in ("d1_supplement", "disjointness_proof", "knowledge_source_guard"):
        if carried in parent:
            receipt[carried] = parent[carried]
    return receipt


def _write_receipt(
    *, roster_module, receipt: Mapping[str, Any], out_relpath: str, repo_root: Path, write: bool
) -> str:
    measured = roster_module.verify_roster(receipt)
    out_path = repo_root / out_relpath
    if out_path.is_file():
        existing = _read_json(out_path)
        if existing.get("split_identity_hash") != measured:
            raise GepaPrepareError(
                f"{out_relpath} already exists with a different split identity "
                f"({existing.get('split_identity_hash')!r} vs {measured!r}); refusing to rewrite"
            )
        print(f"roster  {out_relpath} already present and identical ({measured})")
    elif write:
        roster_module.write_roster(receipt, out_path)
        print(
            f"roster  wrote {out_relpath} rows={len(receipt['items'])} "
            f"split_identity={measured}"
        )
    else:
        print(
            f"roster  (dry) would write {out_relpath} rows={len(receipt['items'])} "
            f"split_identity={measured}"
        )
    print(
        "roster  file_sha256="
        f"{sha256_file(out_path) if out_path.is_file() else '(not written)'}"
    )
    return measured


def _source_pin(args: argparse.Namespace, groups_document: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "relpath": args.groups_relpath,
        "root": "data",
        "sha256": sha256_file(Path(args.groups)),
        "schema": groups_document.get("schema"),
        "rollout_run_id": groups_document.get("rollout_run_id"),
        "rollout_attempt_id": groups_document.get("rollout_attempt_id"),
        "scorer_id": groups_document.get("scorer_id"),
        "k": groups_document.get("k"),
        "rank_metric": groups_document.get("rank_metric"),
    }


def cmd_roster(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root)
    roster_module, splits = _import_repo(repo_root)
    groups_document = _read_json(Path(args.groups))
    ids = carrier_ids(groups_document)
    parent = _read_json(repo_root / PARENT_ROSTER)
    roster_module.verify_roster(parent)
    receipt = _selection_receipt(
        parent=parent,
        ids=ids,
        roster_id=ROSTER_ID,
        authority=(
            f"Stage-3 layer A, the GEPA arm ({DESIGN_NOTE}; owner decision 101): the reflective "
            "proposal contact runs once per (scenario, node) group and the flight makes one "
            "contact per FLOWN ROW, so the flown population is exactly the groups' carrier rows. "
            "construction-advantage-text is a construction-visible arm, so "
            "contracts.gate_exposure._require_construction_role_for_visible_targets requires "
            "this population to be a committed roster_role='construction' roster of its own; the "
            "precedent is SLURP-STAGE3-ADVANTAGE-R01C-DISAGREEING-V1."
        ),
        selection_rule=(
            "R01C restricted to the CARRIER rows of the prepared GEPA groups artifact (one per "
            "(scenario, node) group; carrier i of a scenario is the i-th row of that scenario's "
            "ordered group, topped up from the scenario's own remaining R01C rows when the group "
            "has fewer rows than nodes); order preserved."
        ),
        draw_method=(
            "No draw. This receipt is a pure SELECTION of the parent receipt's frozen items: "
            "every surviving item is the parent's item verbatim, in the parent's order "
            "(ascending sample_id). The seed is the parent's and is carried for provenance only "
            "-- no rng is consulted anywhere in this build."
        ),
        source_pin=_source_pin(args, groups_document),
        splits=splits,
    )
    _write_receipt(
        roster_module=roster_module,
        receipt=receipt,
        out_relpath=args.roster_out,
        repo_root=repo_root,
        write=args.write,
    )
    return 0


def cmd_groups_roster(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root)
    roster_module, splits = _import_repo(repo_root)
    groups_document = _read_json(Path(args.groups))
    ids = group_row_ids(groups_document)
    parent = _read_json(repo_root / PARENT_ROSTER)
    roster_module.verify_roster(parent)
    receipt = _selection_receipt(
        parent=parent,
        ids=ids,
        roster_id=GROUPS_ROSTER_ID,
        authority=(
            f"Stage-3 layer A, the GEPA arm ({DESIGN_NOTE}; owner decisions 83 and 101): the "
            "SOURCE population of the GEPA delta store. A GEPA contact is rendered from its "
            "GROUP's rows -- their rollout trajectories and their construction gold -- so the "
            "rows an authored GEPA delta may cite are the union of the groups' row_sample_ids. "
            "core.semantic_knowledge_preparation verifies a release registration's "
            "permitted_roster as a committed roster_role='construction' receipt AND requires "
            "its split identity to equal the registration's source_split_identity_hash, so this "
            "population needs a committed receipt of its own. The FLOWN population is the "
            "different, also committed SLURP-STAGE3-GEPA-R01C-CARRIERS-V1 (one contact per "
            "carrier row). The precedent is SLURP-STAGE3-ADVANTAGE-R01C-DISAGREEING-V1, where "
            "the flown population and the store source are the same rows; the GEPA arm "
            "separates them because a group shows more rows than its carrier."
        ),
        selection_rule=(
            "R01C restricted to the UNION of the prepared GEPA groups artifact's "
            "row_sample_ids -- every row any group showed its contact. A carrier topped up "
            "from the roster, from which no proposal was rendered, is not in this roster "
            "unless some group also showed it; order preserved."
        ),
        draw_method=(
            "No draw. This receipt is a pure SELECTION of the parent receipt's frozen items: "
            "every surviving item is the parent's item verbatim, in the parent's order "
            "(ascending sample_id). The seed is the parent's and is carried for provenance "
            "only -- no rng is consulted anywhere in this build, and no score, quality or "
            "label is read."
        ),
        source_pin=_source_pin(args, groups_document),
        splits=splits,
        roster_role_note=GROUP_ROWS_ROLE_NOTE,
    )
    _write_receipt(
        roster_module=roster_module,
        receipt=receipt,
        out_relpath=args.groups_roster_out,
        repo_root=repo_root,
        write=args.write,
    )
    return 0


def cmd_smoke_roster(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root)
    roster_module, splits = _import_repo(repo_root)
    groups_document = _read_json(Path(args.groups))
    ids = carrier_ids(groups_document)[: args.rows]
    if len(ids) != args.rows:
        raise GepaPrepareError(
            f"--rows {args.rows} exceeds the {len(carrier_ids(groups_document))} carriers"
        )
    parent = _read_json(repo_root / PARENT_ROSTER)
    roster_module.verify_roster(parent)
    scenarios = sorted(
        {
            str(group["scenario"])
            for group in groups_document["groups"]
            if str(group["carrier_sample_id"]) in set(ids)
        }
    )
    receipt = _selection_receipt(
        parent=parent,
        ids=ids,
        roster_id=SMOKE_ROSTER_ID,
        authority=(
            f"Stage-3 layer A, the GEPA arm ({DESIGN_NOTE}) plus the program's own four-row form "
            "smoke rule (study CLAUDE.md, owner 2026-09-03: a NEW module form flies a four-row "
            "smoke before its full cell). The gate knows nothing about parent rosters, so the "
            "four smoke rows need a committed roster_role='construction' receipt of their own."
        ),
        selection_rule=(
            f"the first {args.rows} CARRIER rows of the prepared GEPA groups artifact, in that "
            f"artifact's own group order -- the four groups of scenario(s) {scenarios}, i.e. one "
            "carrier per NODE, which is the form smoke that exercises all four node-fixed "
            "current-delta slices at once. A structural form smoke, never a quality-based "
            "selection."
        ),
        draw_method=(
            "No draw. A pure SELECTION of the parent receipt's frozen items, each item verbatim, "
            "in the parent's own order (ascending sample_id). No rng is consulted and no score, "
            "quality or label is read."
        ),
        source_pin=_source_pin(args, groups_document),
        splits=splits,
    )
    _write_receipt(
        roster_module=roster_module,
        receipt=receipt,
        out_relpath=args.smoke_roster_out,
        repo_root=repo_root,
        write=args.write,
    )
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    """Assert the committed fragments agree with the built artifacts."""

    repo_root = Path(args.repo_root)
    groups_path = Path(args.groups)
    groups_document = _read_json(groups_path)
    groups_sha256 = sha256_file(groups_path)
    ids = carrier_ids(groups_document)
    audio_ceiling = math.ceil(
        sum(float(group["carrier_audio_seconds"]) for group in groups_document["groups"])
    )

    problems: list[str] = []
    checks: list[dict[str, Any]] = []

    def check(name: str, got: Any, want: Any) -> None:
        ok = got == want
        checks.append({"check": name, "got": got, "expected": want, "ok": ok})
        if not ok:
            problems.append(f"{name}: fragment says {got!r}, the artifacts say {want!r}")

    baseline = _read_json(repo_root / BASELINE)
    smoke_baseline = _read_json(repo_root / SMOKE_BASELINE)
    experiment = _read_json(repo_root / EXPERIMENT)
    smoke_experiment = _read_json(repo_root / SMOKE_EXPERIMENT)

    for name, document in (("arm", baseline), ("smoke", smoke_baseline)):
        block = document.get("gepa_groups")
        if not isinstance(block, Mapping):
            problems.append(f"{name} baseline declares no gepa_groups block")
            continue
        check(f"{name} baseline gepa_groups.sha256", block.get("sha256"), groups_sha256)
        check(
            f"{name} baseline gepa_groups.rollout_run_id",
            block.get("rollout_run_id"),
            groups_document.get("rollout_run_id"),
        )

    roster_path = repo_root / args.roster_out
    smoke_roster_path = repo_root / args.smoke_roster_out
    if roster_path.is_file():
        check(
            "arm population.split_identity_hash",
            experiment.get("population", {}).get("split_identity_hash"),
            _read_json(roster_path).get("split_identity_hash"),
        )
    if smoke_roster_path.is_file():
        check(
            "smoke population.split_identity_hash",
            smoke_experiment.get("population", {}).get("split_identity_hash"),
            _read_json(smoke_roster_path).get("split_identity_hash"),
        )
    check("arm population.count", experiment.get("population", {}).get("count"), len(ids))
    check(
        "arm planned_model_calls",
        experiment.get("execution_plan", {}).get("planned_model_calls"),
        len(ids),
    )
    check(
        "arm planned_speech_audio_seconds",
        experiment.get("execution_plan", {}).get("planned_speech_audio_seconds"),
        audio_ceiling,
    )

    report = {
        "schema": "saea-stage3-gepa-verify-v1",
        "groups": {"relpath": args.groups_relpath, "sha256": groups_sha256},
        "carriers": len(ids),
        "carrier_audio_seconds_ceiling": audio_ceiling,
        "checks": checks,
        "problems": problems,
        "passed": not problems,
    }
    print(json.dumps(report, indent=2, sort_keys=True))  # noqa: T201 -- ids/counts only
    return 0 if not problems else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_DEFAULT)
    parser.add_argument("--groups", required=True, type=Path)
    parser.add_argument(
        "--groups-relpath",
        default="prepared/SAEA-SLURP-STAGE3-DELTAS-GEPA-V1/gepa-groups-v1.json",
    )
    parser.add_argument("--roster-out", default=ROSTER_OUT)
    parser.add_argument("--groups-roster-out", default=GROUPS_ROSTER_OUT)
    parser.add_argument("--smoke-roster-out", default=SMOKE_ROSTER_OUT)
    parser.add_argument("--rows", default=SMOKE_ROWS, type=int)
    parser.add_argument("--write", action="store_true")
    parser.add_argument(
        "command", choices=("roster", "groups-roster", "smoke-roster", "verify")
    )
    args = parser.parse_args(argv)
    if args.command == "roster":
        return cmd_roster(args)
    if args.command == "groups-roster":
        return cmd_groups_roster(args)
    if args.command == "smoke-roster":
        return cmd_smoke_roster(args)
    return cmd_verify(args)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except GepaPrepareError as error:  # pragma: no cover - CLI surface
        print(f"gepa_prepare_steps: FAIL: {error}", file=sys.stderr)
        raise SystemExit(2) from None
