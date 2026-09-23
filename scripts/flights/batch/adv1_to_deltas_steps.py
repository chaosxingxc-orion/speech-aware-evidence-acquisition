#!/usr/bin/env python3
"""Helper steps of the delta-store runbook (``scripts/flights/batch/adv1_to_deltas.sh``).

MODEL-FREE. Zero frozen-core, tool, embedding, encoder, tokenizer, scorer, GPU
and network contacts. No statement text, utterance text, gold label or model
output is printed or persisted by this helper -- only relpaths, counts and
digests, the discipline ``scripts/build_slurp_stage3_delta_store.py`` keeps for
its own console output.

Four steps:

``registration``
    Materialise a committed release-registration TEMPLATE into a RUNNABLE copy
    BESIDE it in the repository, with the release source document's real digest
    and the scope / permitted-roster digests root's own S3-5 preparations
    produced. ``core.semantic_knowledge_preparation.
    prepare_semantic_knowledge_store`` verifies every one of those pins by
    SHA-256, so the template -- which carries ``PENDING_`` tokens -- is never
    passed to it and is never edited in place. The forbidden-roster pins the
    template carries are re-verified against the committed receipts and a
    mismatch fails closed.

    The runnable copy is a REPOSITORY path, not a data-root one: the preparer
    records the registration by its repo-relative path
    (``_registration``: ``path.resolve().relative_to(repo_root)``) and refuses
    outright any registration that is not confined to ``repo_root``.

    ``authored_source`` must already be the WRAPPED release source document
    (``saea-authored-semantic-knowledge-source-v1``), which
    ``scripts/build_slurp_stage3_delta_source.py`` -- or the curator's own
    ``--out-source`` -- writes from the curated authored-deltas document. A
    curation document pinned directly would be refused deep inside the
    preparer, so it is refused here, by name, with the command that fixes it.

``cell1-values``
    Read the released store's ``release.json`` / ``snapshot.json`` (and the
    twin's) and write the CELL-1 fill values file
    ``scripts/flights/batch/roll1_fill_placeholders.py`` consumes.

    THE SNAPSHOT VALUE IS THE SNAPSHOT'S **CONTENT** HASH, never the
    ``snapshot.json`` file digest (commit ``fb4d8915``; the first release
    supplied the file digest and every one of the six cells then refused with
    ``knowledge store stage3-deltas snapshot SHA-256 mismatch``).
    ``rails.knowledge_stores`` checks the pin against BOTH
    ``KnowledgeSnapshot.content_hash()`` and the release document's own
    ``snapshot_sha256`` -- which are the same number and are NOT the file
    digest, because ``snapshot.json`` carries that hash as a field of itself.
    This step reads it out of ``release.json``, cross-checks it against
    ``snapshot.json``'s own copy, and prints the file digests beside it for
    the record so the two can never be confused again.

``reach``
    The MODEL-FREE supply-reach expectation of a released store: per node,
    how many values carry at least one ``associated_facet_ids`` entry among
    the registered SLURP candidate intents -- the upper bound on what a
    candidate-bound route can ever select -- plus the per-intent facet
    histogram. Counts and ids only, never statement text. With
    ``--release-pins`` the block is written into the release-pins document.

``repoint``
    Rewrite the CELL-1 fragments' ``stage3-deltas`` store pins (the four
    baselines' ``knowledge_stores`` entries and the two experiment
    fragments' ``preparation`` readiness requirements) onto a released
    namespace. It is the successor of the PENDING-token substitution: once a
    fragment carries real digests there is no token left for
    ``roll1_fill_placeholders.py`` to replace, and a store re-release still
    has to reach every pin exactly once.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Mapping

REPO_DEFAULT = Path(__file__).resolve().parents[3]
TEMPLATE_KEYS_DROPPED = ("template_note", "what_the_pins_are")
#: The only ``authored_source`` shape ``core.semantic_knowledge_preparation``
#: accepts, and its exact top-level key set (checked there for equality).
AUTHORED_SOURCE_SCHEMA = "saea-authored-semantic-knowledge-source-v1"
AUTHORED_SOURCE_KEYS = frozenset(
    {"schema", "builder_policy_id", "source_split_identity_hash", "rows"}
)


#: The nodes a delta row may be addressed to, spelled as PHASE names
#: (restated from ``rails.stage3_delta_supply.STAGE3_DELTA_NODES``; this
#: helper keeps no import of the runtime, exactly as that module restates
#: ``rails.stage3_advantage.LEGAL_DELTA_NODES``).
STAGE3_DELTA_NODES = ("perception", "solver", "reviewer", "planner")


class Adv1DeltaStepError(RuntimeError):
    """An input is missing or does not have the shape this helper needs."""


def retag(value: str, *, name: str, tag: str, old: str = "v1") -> str:
    """Re-point one ``...-v1`` artifact name, namespace or namespaced file at
    ``tag``.

    Three shapes, in this order: a document name (``source-...-v1.json``), a
    bare name or namespace (``...-v1``), and a file INSIDE a versioned
    namespace (``.../stage3-deltas-v1/snapshot.json``, where the version is
    the last path component ending in ``-<old>``).

    Fail-closed: a value carrying the version anywhere else is refused rather
    than silently left at the old version -- which is how the first v1r pass
    caught its own ``--snapshot-relpath`` default. ``tag == old`` is the
    identity.
    """

    if tag == old:
        return value
    for suffix in (f"-{old}.json", f"-{old}"):
        if value.endswith(suffix):
            return value[: -len(suffix)] + f"-{tag}" + suffix[len(f"-{old}"):]
    marker = f"-{old}/"
    if marker in value:
        head, _, tail = value.rpartition(marker)
        return f"{head}-{tag}/{tail}"
    raise Adv1DeltaStepError(
        f"{name} is {value!r}, which carries no '-{old}' name, namespace or "
        "namespace component; refusing to guess where the version tag lives"
    )


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise Adv1DeltaStepError(f"{path} is unreadable: {error}") from error


def sha256_file(path: Path) -> str:
    if not path.is_file():
        raise Adv1DeltaStepError(f"missing {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _resolve(pin: Mapping[str, Any], *, repo_root: Path, data_root: Path) -> Path:
    root = str(pin.get("root", "data"))
    base = repo_root if root in ("repo", "repository") else data_root
    return base / str(pin["relpath"])


def _verify_authored_source(
    path: Path, *, builder_policy_id: str, source_split_identity_hash: str
) -> int:
    """Fail closed unless ``path`` is the WRAPPED release source document the
    preparer will accept, and unless its two identity headers equal the
    registration's own. Returns the row count (a count, never a row).

    This duplicates no rule: it is the same contract
    ``core.semantic_knowledge_preparation._source_rows`` enforces, checked
    one step earlier so the operator is told which command to run rather than
    reading "authored_source has unsupported schema" out of a release that
    already touched the knowledge namespace.
    """

    document = _read_json(path)
    if not isinstance(document, Mapping):
        raise Adv1DeltaStepError(f"{path} must be a JSON object")
    schema = document.get("schema")
    if schema != AUTHORED_SOURCE_SCHEMA:
        raise Adv1DeltaStepError(
            f"{path} carries schema {schema!r}, but a release registration's "
            f"authored_source must be {AUTHORED_SOURCE_SCHEMA!r}. Wrap the curated "
            "authored-deltas document first: scripts/build_slurp_stage3_delta_"
            "source.py --authored <curated> --out <this path> "
            "--source-split-identity-hash <split>, or pass --out-source to "
            "scripts/build_slurp_stage3_delta_store.py"
        )
    if set(document) != AUTHORED_SOURCE_KEYS:
        raise Adv1DeltaStepError(
            f"{path} fields differ from {AUTHORED_SOURCE_SCHEMA}: the preparer "
            "checks that key set for exact equality"
        )
    if document["builder_policy_id"] != builder_policy_id:
        raise Adv1DeltaStepError(
            f"{path} names builder {document['builder_policy_id']!r}, the "
            f"registration names {builder_policy_id!r}"
        )
    if document["source_split_identity_hash"] != source_split_identity_hash:
        raise Adv1DeltaStepError(
            f"{path} carries a different source_split_identity_hash than the "
            "registration; refusing to release a store against another population"
        )
    rows = document["rows"]
    if not isinstance(rows, list) or not rows:
        raise Adv1DeltaStepError(f"{path} carries no rows")
    return len(rows)


def cmd_registration(args: argparse.Namespace) -> int:
    repo_root, data_root = Path(args.repo_root), Path(args.data_root)
    registration = _read_json(repo_root / args.template)
    for key in TEMPLATE_KEYS_DROPPED:
        registration.pop(key, None)

    tag = args.version_tag
    if tag != "v1":
        # The committed templates name version 1 in three places. Each is
        # re-pointed explicitly and fail-closed; nothing else moves, so the
        # v1r registration differs from the v1 one in exactly its identity,
        # its source document and its output namespace.
        registration["registration_id"] = retag(
            registration["registration_id"], name="registration_id",
            tag=tag.upper(), old="V1",
        )
        registration["authored_source"]["relpath"] = retag(
            registration["authored_source"]["relpath"],
            name="authored_source.relpath", tag=tag,
        )
        registration["output_namespace"] = retag(
            registration["output_namespace"], name="output_namespace", tag=tag
        )
    registration["source_split_identity_hash"] = args.source_split_identity_hash
    authored_source_path = _resolve(
        registration["authored_source"], repo_root=repo_root, data_root=data_root
    )
    registration["authored_source"]["sha256"] = sha256_file(authored_source_path)
    authored_source_rows = _verify_authored_source(
        authored_source_path,
        builder_policy_id=registration["builder_policy_id"],
        source_split_identity_hash=args.source_split_identity_hash,
    )
    registration["construction_scope"]["sha256"] = sha256_file(
        _resolve(registration["construction_scope"], repo_root=repo_root, data_root=data_root)
    )
    registration["permitted_roster"]["sha256"] = sha256_file(
        _resolve(registration["permitted_roster"], repo_root=repo_root, data_root=data_root)
    )
    for index, pin in enumerate(registration.get("forbidden_rosters", ())):
        measured = sha256_file(_resolve(pin, repo_root=repo_root, data_root=data_root))
        if measured != pin["sha256"]:
            raise Adv1DeltaStepError(
                f"forbidden_rosters[{index}] {pin['relpath']} is {measured}, the template pins "
                f"{pin['sha256']}; refusing to release against a moved evaluation roster"
            )

    text = json.dumps(registration, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if "PENDING_" in text:
        raise Adv1DeltaStepError("the runnable registration still carries a PENDING_ token")
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8", newline="\n")
    print(json.dumps({
        "stage": "registration",
        "out": str(out_path),
        "sha256": sha256_file(out_path),
        "output_namespace": registration["output_namespace"],
        "registration_id": registration["registration_id"],
        "version_tag": args.version_tag,
        "authored_source_relpath": registration["authored_source"]["relpath"],
        "authored_source_sha256": registration["authored_source"]["sha256"],
        "authored_source_rows": authored_source_rows,
    }, indent=2, sort_keys=True))
    return 0


def snapshot_content_hash(release_path: Path, snapshot_path: Path) -> str:
    """The snapshot's CONTENT hash -- what a fragment's ``snapshot.sha256``
    pin must carry -- read out of the release document and cross-checked
    against the snapshot's own copy of it.

    ``rails.knowledge_stores`` verifies a store by BOTH
    ``KnowledgeSnapshot.content_hash() == snapshot_pin["sha256"]`` and
    ``release["snapshot_sha256"] == snapshot_pin["sha256"]``. The
    ``snapshot.json`` FILE digest is a third, different number (the file
    contains that hash as one of its own fields) and pinning it refuses every
    cell at load. Fail-closed on any disagreement rather than emitting a
    value that would be discovered only by a refused flight.
    """

    release = _read_json(release_path)
    snapshot = _read_json(snapshot_path)
    if not isinstance(release, Mapping) or not isinstance(snapshot, Mapping):
        raise Adv1DeltaStepError(f"{release_path} / {snapshot_path} must be JSON objects")
    content = release.get("snapshot_sha256")
    if not isinstance(content, str) or len(content) != 64:
        raise Adv1DeltaStepError(f"{release_path} carries no snapshot_sha256")
    if snapshot.get("snapshot_sha256") != content:
        raise Adv1DeltaStepError(
            f"{snapshot_path} names a different snapshot_sha256 than {release_path}; "
            "refusing to emit a content hash the two documents disagree on"
        )
    return content


def cmd_cell1_values(args: argparse.Namespace) -> int:
    data_root = Path(args.data_root)
    tag = args.version_tag
    release_relpath = retag(args.release_relpath, name="--release-relpath", tag=tag)
    snapshot_relpath = retag(args.snapshot_relpath, name="--snapshot-relpath", tag=tag)
    twin_release_relpath = retag(
        args.twin_release_relpath, name="--twin-release-relpath", tag=tag
    )
    twin_snapshot_relpath = retag(
        args.twin_snapshot_relpath, name="--twin-snapshot-relpath", tag=tag
    )
    values = {
        # The RELEASE pin IS the release.json file digest.
        "PENDING_S3_5_RELEASE_JSON_SHA256": sha256_file(data_root / release_relpath),
        # The SNAPSHOT pin is the snapshot's CONTENT hash, not the file digest.
        "PENDING_S3_5_SNAPSHOT_JSON_SHA256": snapshot_content_hash(
            data_root / release_relpath, data_root / snapshot_relpath
        ),
        "PENDING_S3_6_TWIN_RELEASE_JSON_SHA256": sha256_file(
            data_root / twin_release_relpath
        ),
        "PENDING_S3_6_TWIN_SNAPSHOT_JSON_SHA256": snapshot_content_hash(
            data_root / twin_release_relpath, data_root / twin_snapshot_relpath
        ),
    }
    print(json.dumps({
        "stage": "cell1-fill-values",
        "version_tag": tag,
        "release_relpath": release_relpath,
        "snapshot_relpath": snapshot_relpath,
        "twin_release_relpath": twin_release_relpath,
        "twin_snapshot_relpath": twin_snapshot_relpath,
        "what_the_snapshot_value_is": (
            "the snapshot CONTENT hash (release.snapshot_sha256 == "
            "KnowledgeSnapshot.content_hash()), never the snapshot.json file digest"
        ),
        "snapshot_json_file_sha256_for_the_record": sha256_file(
            data_root / snapshot_relpath
        ),
        "twin_snapshot_json_file_sha256_for_the_record": sha256_file(
            data_root / twin_snapshot_relpath
        ),
        **values,
    }, indent=2, sort_keys=True))
    out_path = Path(args.values_out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(values, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    print(f"cell1-values  values -> {out_path}")
    return 0


def _node_of(task_target: object) -> str | None:
    if not isinstance(task_target, str) or not task_target:
        return None
    head = task_target.split(":", 1)[0]
    return head if head in STAGE3_DELTA_NODES else None


def measure_supply_reach(
    snapshot: Mapping[str, Any], *, legal_intents: frozenset
) -> dict[str, Any]:
    """The model-free reach of one released snapshot: COUNTS AND IDS ONLY.

    A candidate-bound route selects a value only when one of its
    ``associated_facet_ids`` EQUALS one of the row's Perception candidate
    INTENT ids, so the number of values carrying at least one facet inside
    the registered intent vocabulary is the upper bound on what that route
    can ever supply -- whatever the row. The Perception route is
    unconditional and has no such bound; it is reported as ``n/a`` with its
    pool size.
    """

    values = snapshot.get("values")
    if not isinstance(values, list) or not values:
        raise Adv1DeltaStepError("the snapshot carries no values")
    per_node: dict[str, dict[str, Any]] = {}
    histogram: dict[str, int] = {}
    reachable_total = 0
    for value in values:
        node = _node_of(value.get("task_target")) or "unattributed"
        facets = [f for f in value.get("associated_facet_ids", ()) if isinstance(f, str)]
        matched = sorted({facet for facet in facets if facet in legal_intents})
        entry = per_node.setdefault(
            node, {"values": 0, "reachable_by_a_candidate_intent": 0, "_intents": set()}
        )
        entry["values"] += 1
        if matched:
            entry["reachable_by_a_candidate_intent"] += 1
            entry["_intents"].update(matched)
            reachable_total += 1
        for facet in matched:
            histogram[facet] = histogram.get(facet, 0) + 1
    report: dict[str, Any] = {}
    for node, entry in sorted(per_node.items()):
        intents = entry.pop("_intents")
        entry["distinct_intents_covered"] = len(intents)
        entry["share"] = round(
            entry["reachable_by_a_candidate_intent"] / entry["values"], 4
        )
        if node == "perception":
            entry["binding"] = "unconditional (no candidate bound applies)"
        report[node] = entry
    report["total"] = {
        "values": len(values),
        "reachable_by_a_candidate_intent": reachable_total,
        "share": round(reachable_total / len(values), 4),
        "distinct_intents_covered": len(histogram),
        "intent_vocabulary": len(legal_intents),
    }
    report["per_intent_facet_histogram"] = dict(sorted(histogram.items()))
    return report


def _legal_intents(path: Path) -> frozenset:
    document = _read_json(path)
    if isinstance(document, Mapping) and isinstance(document.get("profiles"), list):
        ids = [
            profile["candidate_id"]
            for profile in document["profiles"]
            if isinstance(profile, Mapping) and isinstance(profile.get("candidate_id"), str)
        ]
    elif isinstance(document, Mapping):
        ids = [key for key in document if isinstance(key, str) and key]
    elif isinstance(document, list):
        ids = [item for item in document if isinstance(item, str) and item]
    else:
        raise Adv1DeltaStepError(f"{path} is not an intent vocabulary")
    if not ids:
        raise Adv1DeltaStepError(f"{path} names no intent id")
    return frozenset(ids)


def cmd_reach(args: argparse.Namespace) -> int:
    data_root = Path(args.data_root)
    tag = args.version_tag
    snapshot_relpath = retag(args.snapshot_relpath, name="--snapshot-relpath", tag=tag)
    twin_snapshot_relpath = retag(
        args.twin_snapshot_relpath, name="--twin-snapshot-relpath", tag=tag
    )
    legal = _legal_intents(Path(args.intent_vocabulary))
    block = {
        "schema": "saea-stage3-delta-supply-reach-v1",
        "what_this_is": (
            "A MODEL-FREE upper bound on what each candidate-bound route can ever "
            "select: the values whose associated_facet_ids intersect the registered "
            "SLURP candidate intent vocabulary. Counts and intent ids only; no "
            "statement text is read, printed or persisted."
        ),
        "intent_vocabulary": {
            "relpath": str(args.intent_vocabulary),
            "count": len(legal),
        },
        "arm": measure_supply_reach(
            _read_json(data_root / snapshot_relpath), legal_intents=legal
        ),
        "twin": measure_supply_reach(
            _read_json(data_root / twin_snapshot_relpath), legal_intents=legal
        ),
        "snapshot_relpath": snapshot_relpath,
        "twin_snapshot_relpath": twin_snapshot_relpath,
    }
    print(json.dumps({"stage": "reach", **block}, indent=2, sort_keys=True))
    if args.release_pins:
        pins_path = Path(args.release_pins)
        pins = _read_json(pins_path)
        if not isinstance(pins, Mapping):
            raise Adv1DeltaStepError(f"{pins_path} is not a release-pins document")
        pins = dict(pins)
        pins["supply_reach"] = block
        pins_path.write_text(
            json.dumps(pins, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8", newline="\n",
        )
        print(f"reach  supply_reach -> {pins_path}")
    return 0


#: Which JSON paths of which CELL-1 fragment carry the stage3-deltas store's
#: two pins. A baseline carries the store itself; an experiment fragment
#: carries one ``preparation`` readiness requirement per cell, pinning the
#: release document the cell is held on.
REPOINT_BASELINES = {
    "configs/baseline/slurp-native-stage3-delta-cell-baseline-v1.json": "arm",
    "configs/baseline/slurp-native-stage3-delta-cell-smoke-4-baseline-v1.json": "arm",
    "configs/baseline/slurp-native-stage3-delta-cell-twin-baseline-v1.json": "twin",
    "configs/baseline/slurp-native-stage3-delta-cell-twin-smoke-4-baseline-v1.json": "twin",
}
REPOINT_EXPERIMENTS = (
    "configs/experiment/slurp-native-stage3-delta-cell-r01-v1.json",
    "configs/experiment/slurp-native-stage3-delta-cell-smoke-4-v1.json",
)


def cmd_repoint(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root)
    values = _read_json(Path(args.values))
    tag, old = args.version_tag, args.from_version_tag
    pins = {
        "arm": {
            "release": f"knowledge/slurp/semantic/stage3-deltas-{tag}/release.json",
            "release_sha256": values["PENDING_S3_5_RELEASE_JSON_SHA256"],
            "snapshot": f"knowledge/slurp/semantic/stage3-deltas-{tag}/snapshot.json",
            "snapshot_sha256": values["PENDING_S3_5_SNAPSHOT_JSON_SHA256"],
        },
        "twin": {
            "release": f"knowledge/slurp/semantic/stage3-deltas-twin-{tag}/release.json",
            "release_sha256": values["PENDING_S3_6_TWIN_RELEASE_JSON_SHA256"],
            "snapshot": f"knowledge/slurp/semantic/stage3-deltas-twin-{tag}/snapshot.json",
            "snapshot_sha256": values["PENDING_S3_6_TWIN_SNAPSHOT_JSON_SHA256"],
        },
    }
    old_release = {
        "arm": f"knowledge/slurp/semantic/stage3-deltas-{old}/release.json",
        "twin": f"knowledge/slurp/semantic/stage3-deltas-twin-{old}/release.json",
    }
    touched: dict[str, int] = {}
    for relpath, side in sorted(REPOINT_BASELINES.items()):
        path = repo_root / relpath
        document = _read_json(path)
        store = document["knowledge_stores"]["stage3-deltas"]
        store["release"] = {"relpath": pins[side]["release"], "sha256": pins[side]["release_sha256"]}
        store["snapshot"] = {"relpath": pins[side]["snapshot"], "sha256": pins[side]["snapshot_sha256"]}
        # sort_keys=False: a fragment's key ORDER is not this step's business.
        # json.load preserves it and assigning to an existing key keeps that
        # key's position, so the diff shows the pins that moved and nothing
        # else. The composed hash is taken over the canonical form anyway.
        path.write_text(
            json.dumps(document, indent=2, ensure_ascii=False, sort_keys=False) + "\n",
            encoding="utf-8", newline="\n",
        )
        touched[relpath] = 2
    for relpath in REPOINT_EXPERIMENTS:
        path = repo_root / relpath
        document = _read_json(path)
        changed = 0
        for cell in document["cells"]:
            for requirement in cell.get("readiness", {}).get("requirements", ()):
                for side, previous in old_release.items():
                    if requirement.get("relpath") == previous:
                        requirement["relpath"] = pins[side]["release"]
                        requirement["sha256"] = pins[side]["release_sha256"]
                        changed += 1
        if not changed:
            raise Adv1DeltaStepError(
                f"{relpath} carries no readiness requirement on {old_release['arm']} "
                f"or {old_release['twin']}; refusing a silent no-op"
            )
        # sort_keys=False: a fragment's key ORDER is not this step's business.
        # json.load preserves it and assigning to an existing key keeps that
        # key's position, so the diff shows the pins that moved and nothing
        # else. The composed hash is taken over the canonical form anyway.
        path.write_text(
            json.dumps(document, indent=2, ensure_ascii=False, sort_keys=False) + "\n",
            encoding="utf-8", newline="\n",
        )
        touched[relpath] = changed
    print(json.dumps({
        "stage": "repoint", "version_tag": tag, "from_version_tag": old,
        "pins": pins, "requirements_repointed": touched,
    }, indent=2, sort_keys=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(REPO_DEFAULT))
    parser.add_argument("--data-root", required=True)
    sub = parser.add_subparsers(dest="command", required=True)

    registration = sub.add_parser("registration", help="materialise a runnable release registration")
    registration.add_argument("--template", required=True, help="committed template, repo-root relative")
    registration.add_argument(
        "--out", required=True,
        help=(
            "runnable copy; it MUST be inside the repository root -- the preparer "
            "records the registration by its repo-relative path and refuses any "
            "path outside it"
        ),
    )
    registration.add_argument(
        "--source-split-identity-hash", required=True,
        help="the ADV-1 population's split identity (the disagreeing-row construction roster's)",
    )
    registration.add_argument(
        "--version-tag", default="v1",
        help=(
            "re-point the template's registration_id, authored_source.relpath and "
            "output_namespace from version v1 onto this tag (default v1: the "
            "identity). Fail-closed if the template does not end in '-v1'."
        ),
    )
    registration.set_defaults(func=cmd_registration)

    values = sub.add_parser("cell1-values", help="write the CELL-1 fill values from the two releases")
    values.add_argument("--release-relpath", default="knowledge/slurp/semantic/stage3-deltas-v1/release.json")
    values.add_argument("--snapshot-relpath", default="knowledge/slurp/semantic/stage3-deltas-v1/snapshot.json")
    values.add_argument("--twin-release-relpath", default="knowledge/slurp/semantic/stage3-deltas-twin-v1/release.json")
    values.add_argument("--twin-snapshot-relpath", default="knowledge/slurp/semantic/stage3-deltas-twin-v1/snapshot.json")
    values.add_argument("--values-out", required=True)
    values.add_argument(
        "--version-tag", default="v1",
        help="re-point the four default relpaths from version v1 onto this tag",
    )
    values.set_defaults(func=cmd_cell1_values)

    reach = sub.add_parser(
        "reach", help="the model-free supply-reach expectation of a released store"
    )
    reach.add_argument(
        "--snapshot-relpath",
        default="knowledge/slurp/semantic/stage3-deltas-v1/snapshot.json",
    )
    reach.add_argument(
        "--twin-snapshot-relpath",
        default="knowledge/slurp/semantic/stage3-deltas-twin-v1/snapshot.json",
    )
    reach.add_argument(
        "--intent-vocabulary", required=True,
        help=(
            "the registered SLURP candidate intents a Perception candidate list "
            "can name (prepared/SAEA-SLURP-NATIVE-CANDIDATE-CONTRACTS-PREPARE-V1/"
            "catalog.json), a JSON list, or a JSON object keyed by id"
        ),
    )
    reach.add_argument(
        "--release-pins", default=None,
        help="also write the measured block into this release-pins document",
    )
    reach.add_argument("--version-tag", default="v1")
    reach.set_defaults(func=cmd_reach)

    repoint = sub.add_parser(
        "repoint", help="re-point the CELL-1 fragments' stage3-deltas store pins"
    )
    repoint.add_argument("--values", required=True, help="a cell1-values output")
    repoint.add_argument("--version-tag", required=True)
    repoint.add_argument(
        "--from-version-tag", default="v1",
        help="the namespace version the fragments currently pin",
    )
    repoint.set_defaults(func=cmd_repoint)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Adv1DeltaStepError as error:
        print(f"adv1_to_deltas_steps: FAIL: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
