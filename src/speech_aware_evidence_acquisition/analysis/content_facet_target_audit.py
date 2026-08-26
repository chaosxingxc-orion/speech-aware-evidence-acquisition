"""Zero-contact correctness audit of ``content_facet_target``.

Exposure row: ``SAEA-SN-MF-CONTENT-FACET-TARGET-AUDIT`` (model-free-check),
registered before any input is opened.

THE SUBJECT.  ``analysis.contrast_fewshot_preanalysis.SnapshotBundle.content_facet_target``
is built by iterating every :class:`~rails.knowledge.ValueBundle` that carries a
non-``None`` ``task_target`` and calling ``setdefault(facet_id, task_target)`` over
that value's ENTIRE ``associated_facet_ids`` tuple.  ``associated_facet_ids`` spans
every KB-BUILD dimension the value touches, so the mapping is keyed by label and
prior facets as well as content facets -- while its NAME asserts the restriction
to content facets.  ``analysis.a2t_lexical_ceiling.content_facet_targets`` builds
the SAME mapping and then filters it to ``facet.dimension == "content"``; that
function is this audit's content-restricted reference, so the two readings are
never two reimplementations of one idea.

THIS MODULE DIAGNOSES AND DOES NOT REPAIR.  It changes no knob, writes nothing
under ``rails/``, ``core/`` or ``configs/``, rebuilds no snapshot and displaces no
receipt.  It reads the two pinned TRAIN snapshots (VALUE vectors stay sealed) and
the already-committed reports whose numbers it re-derives.

WHAT IS MEASURED.

1. ``key_composition`` -- the mapping's actual keys, resolved against each
   facet's own declared ``KeyFacet.dimension``, reported as counts per dimension
   on both carriers.

2. ``admitted_set_scope`` -- the exhaustive set fact that decides every
   admitted-set call site at once.  ``multidim_recall`` gives a facet a
   NON-prior-mass dimension score only when ``facet_vectors(facet_id)`` returns
   that dimension, and both carriers' lookup
   (``contrast_fewshot_preanalysis._facet_vector_lookup``) returns ``{}`` for
   every facet id outside the landed content-facet NPZ.  The registered fuser
   admits a facet only when its maximum non-prior-mass score reaches
   ``tau`` (0.65 > 0), which a facet carrying no cosine dimension at all can
   never reach.  So ``admitted_facet_ids`` is a subset of the NPZ id set; the
   audit measures that the NPZ id set contains NO non-content facet, over every
   facet in each snapshot, which makes every admitted-set site an exact identity
   under both readings without replaying one sample.

3. ``landed_number_recompute`` -- the two landed A2T quantities that read the
   mapping WITHOUT a content restriction, recomputed both ways from the pinned
   snapshot: ``kb_shape.content_facets_with_a_task_target`` and the per-sample
   ``kb_facets_for_gold`` of ``q1_build_versus_ranking.case_b_ranking_recall_defect``.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from . import a2t_admission_scale_sweep as a2t
from . import a2t_lexical_ceiling as lex
from . import contrast_fewshot_preanalysis as cf
from . import dev100_damage_channel_analysis as dc
from . import dev100_reviewer_audit as ra
from ..rails import kb_policy as kb

SCHEMA = "saea-content-facet-target-audit-v1"
EXPOSURE_ROW_ID = "SAEA-SN-MF-CONTENT-FACET-TARGET-AUDIT"

#: The registered fuse threshold both carriers flew at. Read, never set here.
FROZEN_TAU = dc.ROUND2_FUSE.tau

#: The two committed reports whose numbers this audit re-derives.
A2T_GOLD_ABSENCE_REPORT = (
    "docs/checks/speech-aware-evidence-acquisition/2026-08-25-a2t-gold-absence/"
    "diagnosis-report.json"
)
A2T_ORACLE_REPORT = (
    "docs/checks/speech-aware-evidence-acquisition/2026-08-25-a2t-oracle-query-bound/"
    "oracle-query-bound-report.json"
)


class AuditError(RuntimeError):
    """Raised when a pinned input or a re-derived landed number does not match."""


def _sha256_file(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


# ---------------------------------------------------------------------------
# 1. The mapping's actual keys
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class KeyComposition:
    """One carrier's measured ``content_facet_target`` key composition."""

    carrier: str
    snapshot_sha256: str
    facets_total: int
    facets_by_dimension: Mapping[str, int]
    values_total: int
    values_with_task_target: int
    keys_total: int
    keys_by_dimension: Mapping[str, int]
    keys_not_declared_as_a_facet: int
    content_keys: int
    non_content_keys: int
    npz_ids_total: int
    npz_ids_by_dimension: Mapping[str, int]
    non_content_keys_inside_the_npz: int
    content_keys_outside_the_npz: int
    reference_content_keys: int


def key_composition(bundle: cf.SnapshotBundle, *, carrier: str) -> KeyComposition:
    """Resolve every key of ``content_facet_target`` to its declared dimension.

    The content-restricted count is taken from
    :func:`a2t_lexical_ceiling.content_facet_targets`, which already applies the
    ``facet.dimension == "content"`` filter this mapping's name implies, so the
    two readings come from two INDEPENDENT pieces of landed code rather than
    from one written twice."""

    snapshot = bundle.snapshot
    dimension_of = {facet.facet_id: facet.dimension for facet in snapshot.facets}
    facets_by_dimension = Counter(facet.dimension for facet in snapshot.facets)

    keys_by_dimension: Counter[str] = Counter()
    dangling = 0
    for facet_id in bundle.content_facet_target:
        dimension = dimension_of.get(facet_id)
        if dimension is None:
            dangling += 1
            continue
        keys_by_dimension[dimension] += 1

    npz_ids = set(bundle.facet_ids)
    npz_by_dimension = Counter(
        dimension_of.get(facet_id, "<not-a-declared-facet>") for facet_id in npz_ids
    )
    non_content_keys_in_npz = sum(
        1
        for facet_id in bundle.content_facet_target
        if facet_id in npz_ids and dimension_of.get(facet_id) != "content"
    )
    content_keys_outside_npz = sum(
        1
        for facet_id in bundle.content_facet_target
        if facet_id not in npz_ids and dimension_of.get(facet_id) == "content"
    )

    reference = lex.content_facet_targets(snapshot)

    return KeyComposition(
        carrier=carrier,
        snapshot_sha256=bundle.snapshot_sha256,
        facets_total=len(snapshot.facets),
        facets_by_dimension=dict(sorted(facets_by_dimension.items())),
        values_total=len(snapshot.values),
        values_with_task_target=sum(
            1 for value in snapshot.values if value.task_target is not None
        ),
        keys_total=len(bundle.content_facet_target),
        keys_by_dimension=dict(sorted(keys_by_dimension.items())),
        keys_not_declared_as_a_facet=dangling,
        content_keys=keys_by_dimension.get("content", 0),
        non_content_keys=len(bundle.content_facet_target)
        - keys_by_dimension.get("content", 0),
        npz_ids_total=len(npz_ids),
        npz_ids_by_dimension=dict(sorted(npz_by_dimension.items())),
        non_content_keys_inside_the_npz=non_content_keys_in_npz,
        content_keys_outside_the_npz=content_keys_outside_npz,
        reference_content_keys=len(reference),
    )


# ---------------------------------------------------------------------------
# 2. The set fact that decides every admitted-set call site
# ---------------------------------------------------------------------------


def admitted_set_scope(bundle: cf.SnapshotBundle, *, carrier: str) -> dict[str, object]:
    """Measure, over EVERY facet in the snapshot, what a facet-vector lookup
    can return -- and therefore which facets the fuser can ever admit.

    ``_facet_vector_lookup`` is the callable both carriers hand to
    ``kb_policy.multidim_recall``. A facet it answers with ``{}`` gets no
    cosine-family dimension at all, so ``dev100_damage_channel_analysis._max_cosine``
    returns 0.0 for it and the admission test ``>= tau`` refuses it for any
    positive ``tau``."""

    lookup = cf._facet_vector_lookup(bundle)
    npz_ids = set(bundle.facet_ids)
    dimension_of = {facet.facet_id: facet.dimension for facet in bundle.snapshot.facets}

    facets_probed = 0
    empty_outside_npz = 0
    unexpected_vector_outside_npz: list[str] = []
    dimensions_returned: Counter[str] = Counter()
    non_content_facets_with_a_vector: list[str] = []
    for facet in bundle.snapshot.facets:
        facets_probed += 1
        returned = lookup(facet.facet_id)
        if facet.facet_id not in npz_ids:
            if returned:
                unexpected_vector_outside_npz.append(facet.facet_id)
            else:
                empty_outside_npz += 1
            continue
        for dimension in returned:
            dimensions_returned[dimension] += 1
        if returned and dimension_of.get(facet.facet_id) != "content":
            non_content_facets_with_a_vector.append(facet.facet_id)

    cosine_family_dimensions = sorted(
        dimension for dimension in dimensions_returned if dimension not in kb.PRIOR_MASS_DIMENSIONS
    )
    return {
        "carrier": carrier,
        "facets_probed": facets_probed,
        "facets_outside_the_npz_answered_with_no_vector": empty_outside_npz,
        "facets_outside_the_npz_answered_with_a_vector": len(unexpected_vector_outside_npz),
        "vector_dimensions_returned": dict(sorted(dimensions_returned.items())),
        "cosine_family_dimensions_returned": cosine_family_dimensions,
        "prior_mass_dimensions": sorted(kb.PRIOR_MASS_DIMENSIONS),
        "non_content_facets_carrying_a_vector": len(non_content_facets_with_a_vector),
        "frozen_tau": FROZEN_TAU,
        "reading": (
            "a facet outside the landed content-facet NPZ receives no cosine-family "
            "dimension from multidim_recall, so its max non-prior-mass score is 0.0 "
            f"and the admission test (>= tau = {FROZEN_TAU}) refuses it; every "
            "admitted_facet_ids set is therefore a subset of the NPZ id set"
        ),
    }


# ---------------------------------------------------------------------------
# 3. The landed numbers, recomputed both ways
# ---------------------------------------------------------------------------


def _both_readings_for_target(
    bundle: cf.SnapshotBundle, dimension_of: Mapping[str, str], target: str
) -> tuple[int, int]:
    """``(all-facet reading, content-facet-only reading)`` for one task target."""

    all_facets = 0
    content_facets = 0
    for facet_id, facet_target in bundle.content_facet_target.items():
        if facet_target != target:
            continue
        all_facets += 1
        if dimension_of.get(facet_id) == "content":
            content_facets += 1
    return all_facets, content_facets


def landed_number_recompute(
    bundle: cf.SnapshotBundle, *, repo_root: Path
) -> dict[str, object]:
    """Re-derive the two landed A2T numbers that read the mapping unrestricted."""

    dimension_of = {facet.facet_id: facet.dimension for facet in bundle.snapshot.facets}
    reference = lex.content_facet_targets(bundle.snapshot)

    all_facet_reading = len(bundle.content_facet_target)
    content_only_reading = len(reference)

    gold_absence_path = Path(repo_root) / A2T_GOLD_ABSENCE_REPORT
    oracle_path = Path(repo_root) / A2T_ORACLE_REPORT
    gold_absence = json.loads(gold_absence_path.read_text(encoding="utf-8"))
    oracle = json.loads(oracle_path.read_text(encoding="utf-8"))

    landed_gold_absence = int(gold_absence["kb_shape"]["content_facets_with_a_task_target"])
    landed_oracle = int(oracle["kb_shape"]["content_facets_with_a_task_target"])
    if landed_gold_absence != all_facet_reading or landed_oracle != all_facet_reading:
        raise AuditError(
            "the landed kb_shape numbers are not reproduced by the all-facet reading: "
            f"landed {landed_gold_absence}/{landed_oracle} against {all_facet_reading}"
        )

    rows = gold_absence["q1_build_versus_ranking"]["case_b_ranking_recall_defect"]["rows"]
    per_row: list[dict[str, object]] = []
    for row in rows:
        target = str(row["gold_primary_tool"])
        all_facets, content_facets = _both_readings_for_target(bundle, dimension_of, target)
        landed = int(row["kb_facets_for_gold"])
        if landed != all_facets:
            raise AuditError(
                f"{row['sample_id']}: landed kb_facets_for_gold {landed} is not the "
                f"all-facet reading {all_facets}"
            )
        per_row.append(
            {
                "sample_id": str(row["sample_id"]),
                "gold_primary_tool": target,
                "landed_all_facet_reading": landed,
                "content_facet_only_reading": content_facets,
                "difference": landed - content_facets,
                "landed_kb_vectored_facets_for_gold": int(row["kb_vectored_facets_for_gold"]),
            }
        )

    differences = sorted({int(row["difference"]) for row in per_row})
    content_only_equals_vectored = all(
        row["content_facet_only_reading"] == row["landed_kb_vectored_facets_for_gold"]
        for row in per_row
    )
    return {
        "carrier": "audio2tool",
        "kb_shape_content_facets_with_a_task_target": {
            "landed_all_facet_reading": all_facet_reading,
            "content_facet_only_reading": content_only_reading,
            "difference": all_facet_reading - content_only_reading,
            "landed_in": [
                f"{A2T_GOLD_ABSENCE_REPORT} (sha256 {_sha256_file(gold_absence_path)})",
                f"{A2T_ORACLE_REPORT} (sha256 {_sha256_file(oracle_path)})",
            ],
        },
        "case_b_kb_facets_for_gold": {
            "n_rows": len(per_row),
            "rows": per_row,
            "landed_all_facet_range": [
                min(int(row["landed_all_facet_reading"]) for row in per_row),
                max(int(row["landed_all_facet_reading"]) for row in per_row),
            ],
            "content_facet_only_range": [
                min(int(row["content_facet_only_reading"]) for row in per_row),
                max(int(row["content_facet_only_reading"]) for row in per_row),
            ],
            "distinct_differences": differences,
            "content_only_reading_equals_landed_vectored_count": content_only_equals_vectored,
        },
    }


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------


def run(*, repo_root: Path, data_root: Path) -> dict[str, object]:
    """The whole audit, as a JSON-ready mapping. Offline guard armed first."""

    import time

    started = time.time()
    attempts = ra.arm_offline_guard()

    slurp = cf.load_snapshot_bundle(data_root=data_root, repo_root=repo_root)
    a2t_bundle = a2t.load_a2t_bundle(data_root=data_root, repo_root=repo_root)

    compositions = {
        "slurp": key_composition(slurp, carrier="slurp"),
        "audio2tool": key_composition(a2t_bundle, carrier="audio2tool"),
    }
    scopes = {
        "slurp": admitted_set_scope(slurp, carrier="slurp"),
        "audio2tool": admitted_set_scope(a2t_bundle, carrier="audio2tool"),
    }
    landed = landed_number_recompute(a2t_bundle, repo_root=repo_root)

    return {
        "schema": SCHEMA,
        "study": "speech-aware-evidence-acquisition",
        "exposure_row_id": EXPOSURE_ROW_ID,
        "execution_profile": "model-free-check",
        "contacts": {
            "frozen_core": 0,
            "pinned_tool_embedding": 0,
            "tokenizer": 0,
            "http_or_socket": 0,
            "outbound_connection_attempts": attempts.count,
            "outbound_connection_targets": list(attempts.targets),
        },
        "subject": (
            "analysis.contrast_fewshot_preanalysis.SnapshotBundle.content_facet_target "
            "and every read of a mapping built the same way"
        ),
        "key_composition": {
            name: vars(composition) for name, composition in compositions.items()
        },
        "admitted_set_scope": scopes,
        "landed_number_recompute": landed,
        "artifact_hashes": {
            "slurp_snapshot": slurp.snapshot_sha256,
            "slurp_content_facet_npz": slurp.npz_sha256,
            "audio2tool_snapshot": a2t_bundle.snapshot_sha256,
            "audio2tool_content_facet_npz": a2t_bundle.npz_sha256,
            A2T_GOLD_ABSENCE_REPORT: _sha256_file(Path(repo_root) / A2T_GOLD_ABSENCE_REPORT),
            A2T_ORACLE_REPORT: _sha256_file(Path(repo_root) / A2T_ORACLE_REPORT),
        },
        "hard_stop": (
            "DIAGNOSIS ONLY. No knob changed, nothing written under rails/, core/ or "
            "configs/, no snapshot rebuilt, no receipt displaced, no repair designed. "
            "Anything read over the SLURP unexposed 500 is a SECONDARY READING and must "
            "not revise, re-tune or restate the lock."
        ),
        "wall_seconds": round(time.time() - started, 1),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="content_facet_target correctness audit")
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    report = run(repo_root=args.repo_root, data_root=args.data_root)
    payload = json.dumps(report, indent=1, sort_keys=True, default=str)
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload + "\n", encoding="utf-8", newline="\n")
        print("written: %s" % args.out)
        print("sha256 : %s" % _sha256_file(args.out))
    else:
        print(payload)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
