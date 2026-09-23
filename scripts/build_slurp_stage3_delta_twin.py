#!/usr/bin/env python3
"""CLI: Stage-3 S3-6, the stage3-deltas store's derangement TWIN (the form
control for the delta-cell read, docs/superpowers/specs/2026-09-22-stage3-
tfrl-base-loop-engineering.md section S3-6; the same twin idiom as B1's
``scripts/build_slurp_exemplar_twin_vectors.py`` and IDXT's
``docs/readiness/2026-09-20-slurp-b1-index-twin-v1/``).

MODEL-FREE. Zero frozen-core, tool, embedding, GPU or network contacts:
every byte read and written is a permutation of an already-curated authored-
deltas document (S3-5's own ``--out-authored`` output).

What the twin is
-----------------
A delta's CONTENT (statement text, task_target, prior_score, provenance)
stays byte-identical; only its ``associated_facet_ids`` -- which candidate
intents the row router may attach it to -- is reassigned from ANOTHER row's
by a seeded derangement (Sattolo's algorithm: a single n-cycle over the row
order, so no delta keeps its own facet ids and every row of two or more has
zero fixed points by construction). This answers exactly the question the
B1/IDXT twins answer: does it matter that a delta is attached to the RIGHT
target, or would ANY delta of the store move the number by the same amount.

Refuses (fail-closed) a document with fewer than two rows: a derangement of
one element does not exist.

S3-4s (owner decision 106, 2026-09-23)
--------------------------------------
A v2 (``saea-stage3-authored-deltas-v2``) document carries ``node_target``
per row, and the two route shapes need two different form controls:

* CANDIDATE-BOUND nodes (solver / reviewer / planner) keep the v1 twin: the
  facet attachment is deranged, so the question stays "does it matter that a
  delta is attached to the RIGHT candidate intent".
* The UNCONDITIONAL node (perception) has no facet binding at flight time --
  every row of the split receives the same capped list -- so deranging its
  facets would change nothing that is read. Its form control is a
  derangement of the TARGET field instead (``task_target``'s third field,
  and the ``associated_facet_ids`` entry that mirrors it), so the twin says
  the same things ABOUT THE WRONG TARGETS.

Both are PERMUTATIONS within their own group, so the twin's token count is
identical to the parent's by construction: no statement text is edited and
the multiset of targets is preserved. :func:`authored_token_count` states
that invariant and ``tests/unit/test_stage3_delta_twin_v2.py`` proves it.

S3-5 revision v1r (2026-09-23)
------------------------------
Under the curator's ``source-intent`` facet rule a row may carry MORE THAN
ONE facet id (its source rows' construction gold intents, plus TARGET when
TARGET is itself a legal intent). Both derangements therefore move a row's
WHOLE ATTACHMENT AS ONE UNIT -- the entire ``associated_facet_ids`` tuple,
never a single position, and for the unconditional group the donor's TARGET
field together with the donor's whole tuple. That choice, and not a
per-position shuffle, is what keeps the invariant exact: a permutation of
whole tuples preserves the MULTISET of tuples, so both the number of facet
entries and the total token count are equal on the two sides whatever the
per-row facet counts are. :func:`facet_count_multiset` states that second
invariant beside :func:`authored_token_count`.

On a ``target-only`` document the two rules coincide byte for byte (a
target-only row's single facet IS its TARGET field), so this is not a change
of behaviour for any store released before v1r.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Mapping, MutableMapping, Sequence

REPO_SRC = Path(__file__).resolve().parent.parent / "src"
if str(REPO_SRC) not in sys.path:
    sys.path.insert(0, str(REPO_SRC))

from speech_aware_evidence_acquisition.rails.hashing import (  # noqa: E402
    canonical_json_bytes,
)

AUTHORED_SCHEMA = "saea-stage3-authored-deltas-v1"
AUTHORED_SCHEMA_V2 = "saea-stage3-authored-deltas-v2"
#: The nodes whose route is candidate-bound (facet derangement) and the one
#: whose route is unconditional (TARGET derangement). Restated here rather
#: than imported: this CLI is a pure permutation over an authored document
#: and keeps no dependency on the supply side.
CANDIDATE_BOUND_NODES = ("solver", "reviewer", "planner")
UNCONDITIONAL_NODES = ("perception",)


class Stage3DeltaTwinError(RuntimeError):
    """The authored-deltas document cannot be deranged as given."""


def _sattolo_cycle(n: int, *, seed: int) -> list[int]:
    """A single n-cycle permutation of ``range(n)`` (Sattolo's algorithm):
    zero fixed points for any n >= 2."""

    if n < 2:
        raise Stage3DeltaTwinError("a derangement requires at least two rows")
    order = list(range(n))
    rng = random.Random(seed)
    for i in range(n - 1, 0, -1):
        j = rng.randrange(0, i)
        order[i], order[j] = order[j], order[i]
    return order


def derange_facet_assignment(
    rows: Sequence[Mapping[str, object]], *, seed: int
) -> list[dict[str, object]]:
    """Reassign every row's ``associated_facet_ids`` from a DIFFERENT row's,
    by a seeded Sattolo derangement over the row order. Every other field is
    copied byte-identical (deep-equal on read-back).

    The WHOLE tuple moves as one unit, so a row carrying two or three facet
    ids (the v1r ``source-intent`` rule) hands over all of them together and
    the multiset of tuples -- hence the facet count and the token count -- is
    preserved exactly."""

    order = _sattolo_cycle(len(rows), seed=seed)
    twinned: list[dict[str, object]] = []
    for index, row in enumerate(rows):
        donor = rows[order[index]]
        new_row: MutableMapping[str, object] = dict(row)
        new_row["associated_facet_ids"] = list(donor["associated_facet_ids"])
        twinned.append(dict(new_row))
    return twinned


def _attachment_key(row: Mapping[str, object], group_name: str) -> str:
    """What the twin MOVES for this group: the facet attachment for a
    candidate-bound row, the TARGET field for an unconditional one."""

    if group_name == "candidate-bound":
        return "\u0000".join(sorted(str(item) for item in row["associated_facet_ids"]))
    return _target_field(row["task_target"])


def _target_field(task_target: str) -> str:
    """The TARGET field of a v2 ``NODE:DELTA-KIND:TARGET`` row."""

    parts = str(task_target).split(":", 2)
    if len(parts) != 3 or not parts[2]:
        raise Stage3DeltaTwinError(
            "a v2 row's task_target must be 'NODE:DELTA-KIND:TARGET'"
        )
    return parts[2]


def permute_target_fields(
    rows: Sequence[Mapping[str, object]], *, seed: int
) -> list[dict[str, object]]:
    """Reassign every row's TARGET from a DIFFERENT row's, by a seeded
    Sattolo derangement over the row order.

    Rewrites ``task_target``'s third field and takes the donor's WHOLE
    ``associated_facet_ids`` tuple with it, and touches nothing else:
    ``content``, ``node_target``, ``prior_score``, ``source_sample_ids`` and
    ``provenance_refs`` are copied byte-identical, so the twin says the same
    sentences about the wrong targets -- and carries the same facet count and
    the same token count.

    On a ``target-only`` document the donor's tuple IS ``[donor_target]``, so
    this is byte-identical to the pre-v1r rule that wrote that literal.
    """

    order = _sattolo_cycle(len(rows), seed=seed)
    twinned: list[dict[str, object]] = []
    for index, row in enumerate(rows):
        donor = rows[order[index]]
        donor_target = _target_field(donor["task_target"])
        node, kind, _own = str(row["task_target"]).split(":", 2)
        new_row: MutableMapping[str, object] = dict(row)
        new_row["task_target"] = f"{node}:{kind}:{donor_target}"
        new_row["associated_facet_ids"] = list(donor["associated_facet_ids"])
        twinned.append(dict(new_row))
    return twinned


def count_value_fixed_points(
    rows: Sequence[Mapping[str, object]], twinned: Sequence[Mapping[str, object]]
) -> int:
    """How many rows kept their own attachment VALUE (not their own slot)."""

    return sum(
        1
        for original, twin in zip(rows, twinned)
        if set(original["associated_facet_ids"]) == set(twin["associated_facet_ids"])
    )


def authored_token_count(document: Mapping[str, object]) -> int:
    """The document's total whitespace-token count over every field a supply
    packet can render -- ``content``, ``task_target`` and every
    ``associated_facet_ids`` entry.

    The S3-4s form-control invariant: a twin must differ from its parent in
    WHAT IS ATTACHED TO WHAT and in nothing else, so this number must be
    equal on both sides. Both twin operations are permutations within a
    group, so equality holds by construction; the test asserts it rather
    than trusting the construction.
    """

    total = 0
    for row in document.get("rows", ()):  # type: ignore[union-attr]
        total += len(str(row["content"]).split())
        total += len(str(row["task_target"]).split())
        for facet_id in row["associated_facet_ids"]:
            total += len(str(facet_id).split())
    return total


def facet_count_multiset(document: Mapping[str, object]) -> tuple[int, ...]:
    """The sorted multiset of per-row facet COUNTS.

    The second S3-5 v1r form-control invariant: both derangements move whole
    attachment tuples, so this multiset -- and therefore the number of facet
    ids a supply packet can ever render -- is equal on parent and twin
    however many facets a row carries.
    """

    return tuple(
        sorted(
            len(row["associated_facet_ids"])
            for row in document.get("rows", ())  # type: ignore[union-attr]
        )
    )


def derange_v2_rows(
    rows: Sequence[Mapping[str, object]], *, seed: int
) -> list[dict[str, object]]:
    """S3-4s: derange the candidate-bound nodes' FACETS and the
    unconditional node's TARGETS, each within its own group, and put the
    rows back in their original order.

    A group of fewer than two rows has no derangement, so it is refused
    rather than silently left as a fixed point -- a twin with fixed points
    is not a form control.
    """

    groups: dict[str, list[int]] = {}
    for index, row in enumerate(rows):
        node = row.get("node_target")
        if node in CANDIDATE_BOUND_NODES:
            groups.setdefault("candidate-bound", []).append(index)
        elif node in UNCONDITIONAL_NODES:
            groups.setdefault("unconditional", []).append(index)
        else:
            raise Stage3DeltaTwinError(
                f"row {index} carries an unknown node_target {node!r}"
            )
    twinned: list[dict[str, object]] = [dict(row) for row in rows]
    for group_name, indices in sorted(groups.items()):
        if len(indices) < 2:
            raise Stage3DeltaTwinError(
                f"the {group_name} group has {len(indices)} row(s); a derangement "
                "requires at least two"
            )
        # A group whose rows all name the SAME attachment cannot be twinned:
        # every permutation of it is the identity in effect, and a twin that
        # is the identity in effect is not a form control. Refused rather
        # than released as a vacuous control.
        keys = {
            _attachment_key(rows[index], group_name) for index in indices
        }
        if len(keys) < 2:
            raise Stage3DeltaTwinError(
                f"the {group_name} group names one distinct attachment; every "
                "permutation of it is the identity in effect"
            )
        subset = [rows[index] for index in indices]
        # A per-group seed, so one group's size never silently re-orders the
        # other's permutation.
        group_seed = seed + (0 if group_name == "candidate-bound" else 1)
        if group_name == "candidate-bound":
            deranged = derange_facet_assignment(subset, seed=group_seed)
        else:
            deranged = permute_target_fields(subset, seed=group_seed)
        for position, index in enumerate(indices):
            twinned[index] = deranged[position]
    return twinned


def build_twin_document(
    document: Mapping[str, object], *, seed: int
) -> dict[str, object]:
    schema = document.get("schema")
    if schema not in (AUTHORED_SCHEMA, AUTHORED_SCHEMA_V2):
        raise Stage3DeltaTwinError(
            f"expected schema {AUTHORED_SCHEMA!r} or {AUTHORED_SCHEMA_V2!r}"
        )
    rows = document.get("rows")
    if not isinstance(rows, list) or not rows:
        raise Stage3DeltaTwinError("authored document has no rows")
    if schema == AUTHORED_SCHEMA_V2:
        twinned_rows = derange_v2_rows(rows, seed=seed)
    else:
        twinned_rows = derange_facet_assignment(rows, seed=seed)
    fixed_points = count_value_fixed_points(rows, twinned_rows)
    if schema == AUTHORED_SCHEMA_V2:
        # A v2 store legitimately carries several deltas per target (three
        # solver lessons about alarm_set, say), so a POSITIONAL derangement
        # -- which is what holds the token count -- can still leave a
        # duplicate row attached to the same value. That is arithmetic, not a
        # defect: Sattolo guarantees no row keeps its OWN slot, and
        # ``derange_v2_rows`` has already refused a group with one distinct
        # attachment. Refuse only a twin that moved nothing at all.
        if fixed_points >= len(rows):
            raise Stage3DeltaTwinError(
                "the derangement changed no row's attachment; refusing a twin that "
                "is not a form control"
            )
    elif fixed_points:
        raise Stage3DeltaTwinError(
            f"derangement produced {fixed_points} fixed point(s); refusing a twin "
            "that is not a genuine derangement"
        )
    twin: dict[str, object] = {
        "schema": schema,
        "iteration": document.get("iteration"),
        "twin_of_seed": seed,
        "rows": twinned_rows,
    }
    # The parent's facet rule travels with the twin, so the released form
    # control says on its face which rule attached the facets it deranged.
    # Absent on a pre-v1r document, and then absent here too: the twin of an
    # earlier release reproduces byte for byte.
    if document.get("facet_rule") is not None:
        twin["facet_rule"] = document["facet_rule"]
    parent_tokens = authored_token_count(document)
    twin_tokens = authored_token_count(twin)
    if parent_tokens != twin_tokens:
        raise Stage3DeltaTwinError(
            f"twin token count {twin_tokens} differs from the parent's "
            f"{parent_tokens}; a form control must hold the token count"
        )
    if facet_count_multiset(document) != facet_count_multiset(twin):
        raise Stage3DeltaTwinError(
            "the twin's per-row facet counts are not a permutation of the "
            "parent's; a form control must hold the attachment volume"
        )
    return twin


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authored", required=True, type=Path)
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--out", required=True, type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    document = json.loads(args.authored.read_text(encoding="utf-8"))
    twin = build_twin_document(document, seed=args.seed)
    raw = canonical_json_bytes(twin)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(raw)
    import hashlib

    report = {
        "schema": "saea-stage3-delta-twin-report-v1",
        "seed": args.seed,
        "authored_schema": twin["schema"],
        "row_count": len(twin["rows"]),
        "facet_rule": twin.get("facet_rule"),
        "token_count": authored_token_count(twin),
        "parent_token_count": authored_token_count(document),
        "facet_count_multiset_held": (
            facet_count_multiset(document) == facet_count_multiset(twin)
        ),
        "facet_entries": sum(facet_count_multiset(twin)),
        "value_fixed_points": count_value_fixed_points(
            document["rows"], twin["rows"]
        ),
        "out": {"relpath": str(args.out), "sha256": hashlib.sha256(raw).hexdigest()},
    }
    print(json.dumps(report, indent=2, sort_keys=True))  # noqa: T201 -- ids/counts/hashes only
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
